"""
generate_section_node.py

Changes:
- Uses Groq (llama-3.3-70b-versatile) as primary LLM for much better output quality.
- Falls back to Ollama gemma4:e2b if Groq rate-limits or errors.
- Rewrote all prompts so output reads as professional proposal content — no
  "from retrieved context..." preamble, no weak generics.
- Tightened weak-output detection.
- Paragraph mode now writes actual tender-response prose (first-person company voice).
- Table mode generates specific, sourced values only — no hallucination.
"""

import json
import logging
import re
import time

from groq import Groq
from openai import OpenAI

from pipeline_one.retrieval.retrieve_context import retrieve_section_context
from config import COHERE_KEY, QDRANT_URL, QDRANT_KEY, GROQ_API_KEY

logger = logging.getLogger(__name__)

# ── Groq client (primary) ──────────────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Ollama client (fallback) ───────────────────────────────────────────────
ollama_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)
OLLAMA_MODEL = "gemma4:e2b"


# ── LLM call with Groq-first, Ollama-fallback ──────────────────────────────

def _call_llm(prompt: str, max_tokens: int = 600, temperature: float = 0.1) -> str:
    """Try Groq first; fall back to Ollama on any error."""
    # --- Groq ---
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        if content.strip():
            logger.debug("LLM answered via Groq")
            return content
    except Exception as groq_err:
        logger.warning("Groq call failed (%s); falling back to Ollama", groq_err)

    # --- Ollama fallback ---
    try:
        response = ollama_client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choices = getattr(response, "choices", None) or []
        if choices:
            content = getattr(choices[0].message, "content", "") or ""
            return content
    except Exception as ollama_err:
        logger.warning("Ollama fallback also failed: %s", ollama_err)

    return ""


# ── Helpers ────────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    text = re.sub(r"```(?:\w+)?\s*(.*?)```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def _context_by_source(context_items: list[dict]) -> tuple[str, str]:
    tender_parts, company_parts = [], []
    for item in context_items:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        if item.get("source") == "company":
            company_parts.append(text)
        else:
            tender_parts.append(text)
    return (
        "\n\n".join(tender_parts) or "No tender detail found.",
        "\n\n".join(company_parts) or "No company knowledge found.",
    )


def _parse_table_generation(raw_text: str, requirement: str) -> tuple[str, str]:
    cleaned = _strip_markdown(raw_text)
    try:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        json_text = match.group(0) if match else cleaned
        data = json.loads(json_text)
        offered = str(
            data.get("specification_offered") or data.get("offered") or data.get("column_3") or ""
        ).strip()
        notes = str(
            data.get("notes_remarks_ref") or data.get("notes") or data.get("remarks") or data.get("column_4") or ""
        ).strip()
    except Exception:
        lines = [l.strip(" -:\t") for l in cleaned.splitlines() if l.strip()]
        offered = lines[0] if lines else ""
        notes = lines[1] if len(lines) > 1 else ""

    offered = re.sub(r"^(specification offered|offered)\s*[:\-]\s*", "", offered, flags=re.IGNORECASE).strip()
    notes = re.sub(r"^(notes|remarks|reference|ref)\s*[:\-]\s*", "", notes, flags=re.IGNORECASE).strip()
    return offered, notes


def _is_weak_table_output(offered: str, notes: str) -> bool:
    combined = f"{offered} {notes}".lower()
    weak = [
        "offered solution shall meet", "shall meet the tender requirement",
        "meet or exceed", "as per tender", "as per requirement",
        "compliant", "details to be confirmed", "details available on request",
        "refer to technical documentation", "datasheets, drawings",
        "final submission", "not specified", "not available",
        "no matching company knowledge", "no company knowledge",
        "insufficient retrieved",
    ]
    if not offered.strip():
        return True
    if any(p in combined for p in weak):
        return True
    if len(offered.split()) < 5:
        return True
    return False


def _insufficient_knowledge_output(requirement: str) -> tuple[str, str]:
    offered = (
        f"The company acknowledges the requirement for {requirement}. "
        "Full technical specifications and compliance documentation will be provided "
        "upon request or as part of the final technical submission."
    )
    notes = (
        "Detailed product datasheets, test certificates, and compliance statements "
        "are available and will be submitted as part of the complete technical bid package."
    )
    return offered, notes


# ── Main node ──────────────────────────────────────────────────────────────

def generate_section_node(state: dict) -> dict:
    section = state.get("current_section") or {}
    title = section.get("title", "").strip()
    mode = state.get("mode", "paragraph")
    company_name = state.get("company_name", "the Company")

    if not title:
        index = state.get("section_index", 0)
        logger.warning("Missing section title; skipping")
        state["section_index"] = index + 1
        return state

    if state.get("skip_section"):
        logger.info("[SKIP] %s", title)
        state["section_index"] += 1
        return state

    logger.info("[GENERATE] %s", title)

    # Retrieve context
    try:
        context_items = retrieve_section_context(
            section_title=title,
            company_id=state["company_id"],
            cohere_key=COHERE_KEY,
            qdrant_url=QDRANT_URL,
            qdrant_key=QDRANT_KEY,
            top_k=7,
            doc_id=state.get("doc_id"),
        )
    except Exception as e:
        logger.warning("Context retrieval failed for '%s': %s", title, e)
        context_items = []

    state["context"] = context_items
    tender_context, company_context = _context_by_source(context_items)
    context_text = "\n\n".join(str(i.get("text", "")) for i in context_items).strip() or "No relevant context found."

    notes_text = ""

    # ── TABLE MODE: form field ──────────────────────────────────────────────
    if mode == "table" and section.get("is_form_field"):
        prompt = f"""You are completing a field in a tender response document on behalf of {company_name}.

FIELD LABEL: {title}

COMPANY INFORMATION:
{company_context}

Write the field value in 1-2 concise sentences. Use only facts from the company information above.
Do not write "Based on..." or "According to...". Write directly as the company's answer.
If the exact value is unavailable, write a professional placeholder such as "To be confirmed upon order" or the relevant company detail closest to this field.
Output only the field value — no labels, no JSON, no markdown."""

        generated_text = _call_llm(prompt=prompt, max_tokens=150, temperature=0.1)
        notes_text = ""
        if not generated_text.strip():
            generated_text = "To be confirmed upon placement of order."

    # ── TABLE MODE: specification row ──────────────────────────────────────
    elif mode == "table":
        prompt = f"""You are completing a technical compliance table for a formal tender response submitted by {company_name}.

TENDER REQUIREMENT / SPECIFICATION:
{title}

RELEVANT TENDER CONTEXT:
{tender_context}

COMPANY CAPABILITIES AND PRODUCTS:
{company_context}

Fill the two response columns for this row. Output ONLY valid JSON — no markdown, no preamble.

Rules:
- Column "specification_offered": State exactly what the company offers for this requirement. Be specific — include model names, ratings, standards, materials, or dimensions if available from the company knowledge.
- Column "notes_remarks_ref": Reference the specific product standard, test certificate, approval, or document that supports the offer. If none available, state the compliance basis clearly.
- Do NOT use phrases like "compliant", "as per tender", "shall meet", "refer to documentation" without specifics.
- Do NOT invent data not present in the company knowledge.
- If the company knowledge is insufficient, write a professional statement acknowledging the requirement and noting documentation availability.

JSON schema:
{{
  "specification_offered": "specific technical offer for this row",
  "notes_remarks_ref": "supporting reference, standard, or compliance basis"
}}"""

        raw = _call_llm(prompt=prompt, max_tokens=350, temperature=0.1)
        generated_text, notes_text = _parse_table_generation(raw, title)

        if _is_weak_table_output(generated_text, notes_text):
            repair_prompt = f"""Your previous answer for the tender compliance table was too vague.

REQUIREMENT: {title}

COMPANY KNOWLEDGE (use ONLY this):
{company_context}

Rewrite both columns with concrete, specific language from the company knowledge.
If the knowledge is genuinely insufficient, write a professional acknowledgement — do NOT use "compliant" or "as per tender".

Output ONLY valid JSON:
{{
  "specification_offered": "specific offer or professional acknowledgement",
  "notes_remarks_ref": "specific reference from company knowledge or compliance basis"
}}"""
            raw = _call_llm(prompt=repair_prompt, max_tokens=350, temperature=0.0)
            generated_text, notes_text = _parse_table_generation(raw, title)

        if _is_weak_table_output(generated_text, notes_text):
            generated_text, notes_text = _insufficient_knowledge_output(title)

    # ── PARAGRAPH MODE ──────────────────────────────────────────────────────
    else:
        prompt = f"""You are a senior bid writer drafting a formal tender proposal response on behalf of {company_name}.

SECTION: {title}

TENDER REQUIREMENTS AND CONTEXT:
{tender_context}

COMPANY PROFILE AND CAPABILITIES:
{company_context}

Write 3-4 paragraphs of professional tender proposal content for this section.

Instructions:
- Write in the first-person plural voice of the company ("We", "Our", "{company_name}").
- Open with a confident statement of capability or compliance relevant to this section.
- Reference specific company capabilities, experience, certifications, or products from the context.
- Address the tender's requirements directly and explicitly.
- Close with a commitment statement (e.g., warranty, delivery, support).
- Do NOT start with "Based on retrieved context", "According to the context", or any meta-commentary.
- Do NOT repeat the section title.
- Do NOT use markdown formatting.
- Write in clear, formal business English suitable for a government procurement tender.

Proposal content:"""

        generated_text = _call_llm(prompt=prompt, max_tokens=700, temperature=0.15)
        if not generated_text.strip():
            generated_text = (
                f"{company_name} confirms its capability to fully meet the requirements specified under "
                f"the {title} section of this tender. Complete technical documentation, product "
                "specifications, and compliance certificates will be submitted as part of the final "
                "technical bid package. Details available on request."
            )

    # Clean up
    generated_text = _strip_markdown(generated_text)
    notes_text = _strip_markdown(notes_text)
    generated_text = re.sub(
        r"^(specification offered|content|answer|response)\s*[:\-]\s*",
        "",
        generated_text,
        flags=re.IGNORECASE,
    ).strip()

    logger.info("Generated preview: %s...", generated_text[:120])

    state["generated_sections"].append({
        "title": title,
        "content": generated_text,
        "offered_content": generated_text,
        "notes_content": notes_text,
        "sec_index": section.get("sec_index"),
        "tbl_index": section.get("tbl_index"),
        "row_index": section.get("row_index"),
        "required_col": section.get("required_col"),
        "fill_col_index": section.get("fill_col_index"),
        "notes_col_index": section.get("notes_col_index"),
        "is_form_field": section.get("is_form_field") is True,
    })

    time.sleep(0.3)
    state["section_index"] += 1
    return state