"""
LLM-backed proposal format detection.

The existing keyword detector is retained as a fallback. This module builds a
compact section map for the tender and asks Groq to identify bidder-fillable
proposal formats semantically.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
try:
    from groq import Groq
except Exception:  # pragma: no cover - handled at runtime for graceful fallback
    Groq = None

from pipeline_one.proposal.detector import detect_proposal_sections

logger = logging.getLogger(__name__)

load_dotenv()


SYSTEM_PROMPT = (
    "You are a specialist in government and commercial tender documents. Your "
    "job is to identify every section in a tender document that is a PROPOSAL "
    "FORMAT - meaning a section that a bidder must fill in and return as part "
    "of their bid submission. This includes but is not limited to: Technical "
    "Proposal sheets, Financial Proposal sheets, Price Bid tables, Bill of "
    "Quantities (BOQ), Schedule of Rates, Annexures requiring bidder input, "
    "Form of Bid, Compliance Statements, Deviation Statements, Technical "
    "Specification response tables, Make and Model declaration sheets, "
    "Experience Certificates formats, Bank Guarantee formats, Undertaking "
    "formats, and any table or form where a bidder must write their offer or "
    "response. Sections that are purely informational, contain only tender "
    "terms and conditions, scope of work descriptions, or eligibility criteria "
    "WITHOUT a fill-in component are NOT proposal formats."
)


def clean_llm_json(text: str) -> str:
    """Remove common markdown fences and surrounding whitespace before parsing."""
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(
        r"```(?:json)?\s*(.*?)```",
        r"\1",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return cleaned.strip()


def _set_dynamic_attr(obj: Any, name: str, value: Any) -> None:
    try:
        setattr(obj, name, value)
    except Exception:
        object.__setattr__(obj, name, value)


def _walk_sections(section_list: list, depth: int = 0) -> list[tuple[Any, dict]]:
    flat = []
    for section in section_list or []:
        tables = getattr(section, "tables", []) or []
        summary = {
            "title": getattr(section, "title", ""),
            "page_start": getattr(section, "page_start", None),
            "page_end": getattr(section, "page_end", None),
            "has_tables": bool(tables),
            "table_count": len(tables),
            "text_snippet": (getattr(section, "content", "") or "")[:300].strip(),
            "depth": depth,
        }
        flat.append((section, summary))
        flat.extend(_walk_sections(getattr(section, "children", []) or [], depth + 1))
    return flat


def _fallback(parsed_doc):
    logger.warning("LLM detection failed, falling back to keyword detector")
    sections = detect_proposal_sections(parsed_doc)
    for section in sections:
        _set_dynamic_attr(section, "detection_method", "keyword_fallback")
    return sections


def _match_section(item: dict, flat_sections: list[tuple[Any, dict]]):
    title = str(item.get("title", "")).strip()
    page_start = item.get("page_start")

    for section, summary in flat_sections:
        if summary["title"] == title and summary["page_start"] == page_start:
            return section

    if page_start is None:
        return None

    candidates = []
    for section, summary in flat_sections:
        section_page = summary.get("page_start")
        if section_page is None:
            continue
        delta = abs(int(section_page) - int(page_start))
        if delta <= 2:
            candidates.append((delta, section))

    if not candidates:
        return None

    candidates.sort(key=lambda value: value[0])
    return candidates[0][1]


def detect_proposal_formats_with_llm(
    parsed_doc,
    groq_model: str = "llama-3.3-70b-versatile",
) -> list:
    flat_sections = _walk_sections(getattr(parsed_doc, "sections", []) or [])
    section_map = [summary for _, summary in flat_sections]

    try:
        if Groq is None:
            raise RuntimeError("groq Python package is not installed")
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        user_prompt = (
            f"Total page count: {getattr(parsed_doc, 'total_pages', 0)}\n\n"
            "Full flat section map:\n"
            f"{json.dumps(section_map, indent=2, ensure_ascii=False)}\n\n"
            "Return ONLY a JSON array, no markdown fences, no explanation. Each "
            "element must have exactly this shape:\n"
            "{\n"
            '  "title": "exact section title from the map",\n'
            '  "page_start": int,\n'
            '  "page_end": int,\n'
            '  "format_type": one of ["technical_proposal", '
            '"financial_proposal", "boq", "schedule_of_rates", "annexure", '
            '"form_of_bid", "compliance_sheet", "experience_format", '
            '"bank_guarantee_format", "undertaking_format", '
            '"other_fill_format"],\n'
            '  "confidence": one of ["high", "medium", "low"],\n'
            '  "reason": "one sentence explaining why this is a proposal format"\n'
            "}\n"
            "If no proposal formats are found, return an empty array []."
        )
        response = client.chat.completions.create(
            model=groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=3000,
            timeout=60,
        )
        choices = getattr(response, "choices", None) or []
        content = getattr(getattr(choices[0], "message", None), "content", "") if choices else ""
        data = json.loads(clean_llm_json(content))
        if not isinstance(data, list):
            raise ValueError("LLM response was not a JSON array")

        if len(data) >= 3:
            data = [item for item in data if str(item.get("confidence", "")).lower() != "low"]

        matched_sections = []
        seen = set()
        for item in data:
            section = _match_section(item, flat_sections)
            if section is None:
                logger.warning(
                    "LLM detected format could not be matched to a section: %s",
                    item,
                )
                continue
            key = (getattr(section, "title", ""), getattr(section, "page_start", None))
            if key in seen:
                continue
            seen.add(key)
            _set_dynamic_attr(section, "format_type", item.get("format_type", "other_fill_format"))
            _set_dynamic_attr(section, "llm_reason", item.get("reason", ""))
            _set_dynamic_attr(section, "detection_method", "llm")
            matched_sections.append(section)

        return matched_sections
    except Exception as exc:
        logger.warning(
            "LLM proposal detection failed (%s): %s",
            type(exc).__name__,
            exc,
        )
        return _fallback(parsed_doc)
