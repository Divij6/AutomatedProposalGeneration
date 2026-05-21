"""
generate_section_node.py

Generates proposal content for one section or table row.

This node intentionally keeps the LangGraph state contract unchanged. The only
behavior changed in this phase is generation policy: prompts now produce concise
enterprise tender compliance language instead of sales or company-profile prose.
"""

from __future__ import annotations

import json
import logging
import re
import time

from groq import Groq
from openai import OpenAI

from agents.prompt_builders import (
    build_form_field_prompt,
    build_paragraph_prompt,
    build_style_repair_prompt,
    build_table_prompt,
    build_table_repair_prompt,
    contains_banned_marketing,
    word_count,
)
from config import (
    COHERE_KEY,
    GROQ_API_KEY,
    PROPOSAL_RESPONSE_VERBOSITY,
    QDRANT_KEY,
    QDRANT_URL,
)
from pipeline_one.retrieval.retrieve_context import retrieve_section_context

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"

ollama_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)
OLLAMA_MODEL = "gemma4:e2b"


def _call_llm(prompt: str, max_tokens: int = 600, temperature: float = 0.1) -> str:
    """Try Groq first; fall back to Ollama on any error."""
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

    try:
        response = ollama_client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choices = getattr(response, "choices", None) or []
        if choices:
            return getattr(choices[0].message, "content", "") or ""
    except Exception as ollama_err:
        logger.warning("Ollama fallback also failed: %s", ollama_err)

    return ""


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


def _nearby_context_from_section(section: dict) -> str:
    """Use compact local proposal context to strengthen retrieval queries."""
    if section.get("nearby_clause_context"):
        return str(section.get("nearby_clause_context", ""))
    paragraphs = section.get("paragraphs") or []
    if isinstance(paragraphs, list):
        return " ".join(str(p).strip() for p in paragraphs[:2] if str(p).strip())
    return ""


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
    weak = [
        "offered solution shall meet",
        "shall meet the tender requirement",
        "meet or exceed",
        "as per tender",
        "as per requirement",
        "compliant",
        "details to be confirmed",
        "details available on request",
        "refer to technical documentation",
        "datasheets, drawings",
        "final submission",
        "not specified",
        "not available",
        "no matching company knowledge",
        "no company knowledge",
        "insufficient retrieved",
    ]
    if not offered.strip():
        return True
    if offered.strip() == "No explicit supporting evidence was retrieved.":
        return False
    if any(phrase in combined for phrase in weak):
        return True
    if len(offered.split()) < 5:
        return True
    return False


def _insufficient_knowledge_output(requirement: str) -> tuple[str, str]:
    offered = (
        f"The requirement for {requirement} is noted. "
        "No explicit supporting evidence was retrieved."
    )
    notes = "No explicit supporting evidence was retrieved."
    return offered, notes


def _fallback_paragraph_output(company_name: str, title: str) -> str:
    return (
        f"{company_name} notes the requirement under this clause. "
        "No explicit supporting evidence was retrieved."
    )


def _maybe_repair_style(title: str, generated_text: str, policy: dict) -> str:
    """Run one focused style repair if the LLM ignored compliance constraints."""
    max_words = int(policy.get("max_words", 120))
    if not generated_text.strip():
        return generated_text
    if not contains_banned_marketing(generated_text) and word_count(generated_text) <= max_words:
        return generated_text

    logger.info(
        "Repairing generated style for '%s' | words=%s max_words=%s banned=%s",
        title,
        word_count(generated_text),
        max_words,
        contains_banned_marketing(generated_text),
    )
    repair_prompt = build_style_repair_prompt(
        section_title=title,
        generated_text=generated_text,
        max_words=max_words,
    )
    repaired = _call_llm(prompt=repair_prompt, max_tokens=policy.get("max_tokens", 220), temperature=0.0)
    return repaired.strip() or generated_text


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

    try:
        context_items = retrieve_section_context(
            section_title=title,
            company_id=state["company_id"],
            cohere_key=COHERE_KEY,
            qdrant_url=QDRANT_URL,
            qdrant_key=QDRANT_KEY,
            top_k=7,
            doc_id=state.get("doc_id"),
            requirement_text=title if mode == "table" else None,
            table_headers=section.get("table_headers"),
            parent_titles=section.get("parent_titles"),
            nearby_clause_context=_nearby_context_from_section(section),
            mode=mode,
        )
    except Exception as exc:
        logger.warning("Context retrieval failed for '%s': %s", title, exc)
        context_items = []

    state["context"] = context_items
    tender_context, company_context = _context_by_source(context_items)
    notes_text = ""

    if mode == "table" and section.get("is_form_field"):
        prompt = build_form_field_prompt(
            company_name=company_name,
            field_label=title,
            company_context=company_context,
        )
        generated_text = _call_llm(prompt=prompt, max_tokens=90, temperature=0.0)
        notes_text = ""
        if not generated_text.strip():
            generated_text = "No explicit supporting evidence was retrieved."

    elif mode == "table":
        prompt = build_table_prompt(
            company_name=company_name,
            requirement=title,
            tender_context=tender_context,
            company_context=company_context,
        )
        raw = _call_llm(prompt=prompt, max_tokens=260, temperature=0.0)
        generated_text, notes_text = _parse_table_generation(raw, title)

        if _is_weak_table_output(generated_text, notes_text):
            repair_prompt = build_table_repair_prompt(
                requirement=title,
                company_context=company_context,
            )
            raw = _call_llm(prompt=repair_prompt, max_tokens=230, temperature=0.0)
            generated_text, notes_text = _parse_table_generation(raw, title)

        if _is_weak_table_output(generated_text, notes_text):
            generated_text, notes_text = _insufficient_knowledge_output(title)

    else:
        prompt, policy = build_paragraph_prompt(
            company_name=company_name,
            section_title=title,
            tender_context=tender_context,
            company_context=company_context,
            verbosity=PROPOSAL_RESPONSE_VERBOSITY,
        )
        generated_text = _call_llm(
            prompt=prompt,
            max_tokens=policy.get("max_tokens", 220),
            temperature=0.0,
        )
        if not generated_text.strip():
            generated_text = _fallback_paragraph_output(company_name, title)
        else:
            generated_text = _maybe_repair_style(title, generated_text, policy)

    generated_text = _strip_markdown(generated_text)
    notes_text = _strip_markdown(notes_text)
    generated_text = re.sub(
        r"^(specification offered|content|answer|response)\s*[:\-]\s*",
        "",
        generated_text,
        flags=re.IGNORECASE,
    ).strip()

    logger.info("Generated preview: %s...", generated_text[:120])

    state["generated_sections"].append(
        {
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
        }
    )

    time.sleep(0.3)
    state["section_index"] += 1
    return state
