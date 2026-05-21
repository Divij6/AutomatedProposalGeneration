"""
Query construction helpers for tender proposal retrieval.

The public retrieval API still accepts a section title, but section titles alone
are often too weak ("Warranty", "Performance Guarantee"). This module enriches
queries with the available row, header, parent, and mode context without changing
Qdrant schema or caller contracts.
"""

from __future__ import annotations

import re
from typing import Iterable


DOMAIN_HINTS = {
    "warranty": (
        "warranty obligations, defect liability period, support obligations, "
        "maintenance support, after sales service"
    ),
    "performance guarantee": (
        "performance guarantee compliance, operational assurance, testing "
        "requirements, guarantee period, performance security"
    ),
    "guarantee": (
        "guarantee compliance, assurance obligations, performance security, "
        "testing and acceptance requirements"
    ),
    "delivery": (
        "delivery schedule, implementation timeline, supply obligations, "
        "installation and commissioning"
    ),
    "support": (
        "technical support, maintenance support, helpdesk, service response, "
        "post implementation assistance"
    ),
}


def _clean_piece(value: object, max_words: int = 60) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text


def _clean_many(values: Iterable[object] | None, max_items: int = 6) -> list[str]:
    if not values:
        return []
    cleaned = []
    for value in values:
        text = _clean_piece(value, max_words=24)
        if text and text.lower() not in {item.lower() for item in cleaned}:
            cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _domain_hint_for(section_title: str, requirement_text: str = "") -> str:
    haystack = f"{section_title} {requirement_text}".lower()
    for marker, hint in DOMAIN_HINTS.items():
        if marker in haystack:
            return hint
    return ""


def build_retrieval_query(
    section_title: str,
    requirement_text: str | None = None,
    table_headers: Iterable[object] | None = None,
    parent_titles: Iterable[object] | None = None,
    nearby_clause_context: str | None = None,
    mode: str | None = None,
) -> str:
    """
    Build a compact semantic query while preserving backward compatibility.

    The returned string intentionally favors natural language phrases over a
    large JSON blob because Cohere query embeddings perform better on concise
    retrieval intent text.
    """

    title = _clean_piece(section_title, max_words=30)
    requirement = _clean_piece(requirement_text, max_words=80)
    headers = _clean_many(table_headers, max_items=8)
    parents = _clean_many(parent_titles, max_items=4)
    nearby = _clean_piece(nearby_clause_context, max_words=70)
    mode_text = _clean_piece(mode, max_words=3)
    hint = _domain_hint_for(title, requirement)

    parts = []
    if title:
        parts.append(f"Section: {title}")
    if requirement and requirement.lower() != title.lower():
        parts.append(f"Requirement: {requirement}")
    if parents:
        parts.append(f"Parent context: {' > '.join(parents)}")
    if headers:
        parts.append(f"Table headers: {', '.join(headers)}")
    if nearby:
        parts.append(f"Nearby clause context: {nearby}")
    if mode_text:
        parts.append(f"Proposal mode: {mode_text}")
    if hint:
        parts.append(f"Domain intent: {hint}")

    return " | ".join(parts) if parts else title
