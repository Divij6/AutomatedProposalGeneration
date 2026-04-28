from openai import OpenAI
import json
import re
import time

from pipeline_one.retrieval.retrieve_context import retrieve_section_context
from config import COHERE_KEY, QDRANT_URL, QDRANT_KEY


client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)
OLLAMA_MODEL = "gemma4:e2b"


def _strip_markdown(text: str) -> str:
    """Remove common markdown artifacts from LLM output."""
    # Preserve fenced JSON/content while removing the fence wrapper.
    text = re.sub(
        r"```(?:\w+)?\s*(.*?)```",
        r"\1",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def _context_by_source(context_items: list[dict]) -> tuple[str, str]:
    tender_parts = []
    company_parts = []

    for item in context_items:
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        if item.get("source") == "company":
            company_parts.append(text)
        else:
            tender_parts.append(text)

    tender_text = "\n\n".join(tender_parts).strip()
    company_text = "\n\n".join(company_parts).strip()

    return (
        tender_text or "No matching tender detail found.",
        company_text or "No matching company knowledge found.",
    )


def _parse_table_generation(raw_text: str, requirement: str) -> tuple[str, str]:
    cleaned = _strip_markdown(raw_text)

    try:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        json_text = match.group(0) if match else cleaned
        data = json.loads(json_text)
        offered = str(
            data.get("specification_offered")
            or data.get("offered")
            or data.get("column_3")
            or ""
        ).strip()
        notes = str(
            data.get("notes_remarks_ref")
            or data.get("notes")
            or data.get("remarks")
            or data.get("column_4")
            or ""
        ).strip()
    except Exception:
        lines = [line.strip(" -:\t") for line in cleaned.splitlines() if line.strip()]
        offered = lines[0] if lines else ""
        notes = lines[1] if len(lines) > 1 else ""

    offered = re.sub(
        r"^(specification offered|offered)\s*[:\-]\s*",
        "",
        offered,
        flags=re.IGNORECASE,
    ).strip()
    notes = re.sub(
        r"^(notes|remarks|reference|ref)\s*[:\-]\s*",
        "",
        notes,
        flags=re.IGNORECASE,
    ).strip()

    return offered, notes


def _is_weak_table_output(offered: str, notes: str) -> bool:
    combined = f"{offered} {notes}".lower()

    weak_phrases = [
        "offered solution shall meet",
        "shall meet the tender requirement",
        "meet or exceed the tender requirement",
        "as per tender",
        "as per requirement",
        "compliant",
        "yes",
        "details to be confirmed",
        "details available on request",
        "refer to technical documentation",
        "datasheets, drawings, and compliance statement",
        "final submission",
        "not specified",
        "not available",
        "no matching company knowledge",
    ]

    if not offered.strip() or not notes.strip():
        return True

    if any(phrase in combined for phrase in weak_phrases):
        return True

    # Very short answers rarely satisfy this tender's "detail what is offered" instruction.
    return len(offered.split()) < 6 or len(notes.split()) < 4


def _insufficient_knowledge_output(requirement: str) -> tuple[str, str]:
    message = f"Insufficient retrieved company knowledge to provide a verified offer for {requirement}."
    notes = "No specific supporting reference was found in the retrieved company knowledge chunks."
    return message, notes


def _call_llm(prompt: str, max_tokens: int = 300, temperature: float = 0.1) -> str:
    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def generate_section_node(state: dict) -> dict:
    section = state["current_section"]
    title = section["title"]
    mode = state.get("mode", "paragraph")

    if state.get("skip_section"):
        print(f"  [SKIP] {title}")
        state["section_index"] += 1
        return state

    print(f"\n  [GENERATE] {title}\n")

    context_items = retrieve_section_context(
        section_title=title,
        company_id=state["company_id"],
        cohere_key=COHERE_KEY,
        qdrant_url=QDRANT_URL,
        qdrant_key=QDRANT_KEY,
        top_k=5,
        doc_id=state.get("doc_id"),
    )
    state["context"] = context_items

    context_text = "\n\n".join(str(item.get("text", "")) for item in context_items)
    tender_context, company_context = _context_by_source(context_items)

    if not context_text.strip():
        context_text = "No relevant context found."

    notes_text = ""

    if mode == "table":
        prompt = f"""You are filling a technical offer table in a tender response document.

SPECIFICATION REQUIRED BY TENDER:
{title}

RELEVANT TENDER DETAILS:
{tender_context}

RELEVANT COMPANY KNOWLEDGE:
{company_context}

YOUR TASK:
Fill BOTH tenderer columns for this row:
1. "Specifications offered"
2. "Notes, remarks, ref to documentation"

STRICT RULES:
- Output ONLY valid JSON. No markdown.
- Use the tender details only to understand what is required.
- Use retrieved company knowledge as the only source for what the company offers.
- Do not leave either field blank.
- Do not answer with "compliant", "yes", "as per tender", "shall meet", "meet or exceed", or similar generic wording.
- Do not invent a brand, model, certificate, value, warranty, document, or drawing that is not present in the retrieved company knowledge.
- If the retrieved company knowledge does not contain enough information, write exactly:
  "Insufficient retrieved company knowledge to provide a verified offer for this row."
- The notes field must cite or summarize the specific retrieved company knowledge used. Do not say "refer to technical documentation" unless the retrieved company knowledge explicitly mentions that document.

JSON schema:
{{
  "specification_offered": "technical offered value for column 3",
  "notes_remarks_ref": "notes, remarks, or document references for column 4"
}}"""

        raw_generation = _call_llm(prompt=prompt, max_tokens=260, temperature=0.1)
        generated_text, notes_text = _parse_table_generation(raw_generation, title)

        if _is_weak_table_output(generated_text, notes_text):
            repair_prompt = f"""Your previous table-row answer was too generic or unsupported.

SPECIFICATION REQUIRED BY TENDER:
{title}

RETRIEVED COMPANY KNOWLEDGE ONLY:
{company_context}

Rewrite the two response columns using ONLY concrete facts from the retrieved company knowledge.

Rules:
- Output ONLY valid JSON.
- No "shall meet", "as per tender", "compliant", "refer to technical documentation", or generic document references.
- If concrete company facts are missing, use exactly:
  "Insufficient retrieved company knowledge to provide a verified offer for this row."

JSON schema:
{{
  "specification_offered": "specific company-backed offer or the exact insufficient-knowledge sentence",
  "notes_remarks_ref": "specific supporting fact/reference from retrieved company knowledge or the exact insufficient-knowledge sentence"
}}"""
            raw_generation = _call_llm(prompt=repair_prompt, max_tokens=260, temperature=0.0)
            generated_text, notes_text = _parse_table_generation(raw_generation, title)

        if _is_weak_table_output(generated_text, notes_text):
            generated_text, notes_text = _insufficient_knowledge_output(title)

    else:
        prompt = f"""You are writing a section of a formal tender proposal document.

SECTION TITLE:
{title}

COMPANY KNOWLEDGE BASE AND TENDER CONTEXT:
{context_text}

INSTRUCTIONS:
- Write 2-4 paragraphs of professional, formal tender proposal content.
- Use facts from the context above.
- Do not invent specific certifications, model numbers, or quantities not present in the context.
- If a specific detail is needed but absent, write "details available on request".
- Do not repeat the section title in your response.
- No markdown.
- Write in third person.

Content:"""

        generated_text = _call_llm(prompt=prompt, max_tokens=400, temperature=0.1)

    generated_text = _strip_markdown(generated_text)
    notes_text = _strip_markdown(notes_text)

    generated_text = re.sub(
        r"^(specification offered|content)\s*[:\-]\s*",
        "",
        generated_text,
        flags=re.IGNORECASE,
    ).strip()

    print(f"  -> {generated_text[:120]}...")

    state["generated_sections"].append({
        "title": title,
        "content": generated_text,
        "offered_content": generated_text,
        "notes_content": notes_text,
        "sec_index": section.get("sec_index"),
        "tbl_index": section.get("tbl_index"),
        "row_index": section.get("row_index"),
        "required_col": section.get("required_col"),
    })

    time.sleep(1)
    state["section_index"] += 1

    return state
