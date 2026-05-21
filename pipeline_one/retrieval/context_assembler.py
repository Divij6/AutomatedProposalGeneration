"""
Context assembly guardrails for proposal generation.

Retrieval can return many overlapping chunks. This module applies score
filtering, source balancing, near-duplicate suppression, and word budgets before
prompt construction. It deliberately keeps the existing context item dict shape
and only adds metadata fields.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Iterable

logger = logging.getLogger(__name__)


def _word_count(text: str) -> int:
    return len(str(text or "").split())


def _trim_words(text: str, max_words: int) -> str:
    words = str(text or "").split()
    if len(words) <= max_words:
        return str(text or "")
    return " ".join(words[:max_words]).rstrip() + " ..."


def _normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _token_fingerprint(text: str) -> set[str]:
    normalised = _normalise_text(text)
    tokens = re.findall(r"[a-z0-9]{4,}", normalised)
    return set(tokens)


def _is_near_duplicate(text: str, fingerprints: Iterable[set[str]]) -> bool:
    current = _token_fingerprint(text)
    if not current:
        return False
    for existing in fingerprints:
        if not existing:
            continue
        overlap = len(current & existing) / max(1, min(len(current), len(existing)))
        if overlap >= 0.88:
            return True
    return False


def _score_allowed(item: dict, min_score: float) -> bool:
    if min_score <= 0:
        return True
    score = item.get("score")
    if score is None:
        return True
    try:
        return float(score) >= min_score
    except (TypeError, ValueError):
        return True


def assemble_context_items(
    context_items: list[dict],
    *,
    max_chunks: int,
    max_words: int,
    min_score: float = 0.0,
    source_limits: dict[str, int] | None = None,
) -> list[dict]:
    """
    Return a prompt-safe context list with stable source separation.

    The function is intentionally deterministic: it preserves retrieval order
    within each source and emits tender chunks before company chunks, matching
    the previous generation behavior while enforcing hard limits.
    """

    if not context_items:
        return []

    max_chunks = max(1, int(max_chunks or 1))
    max_words = max(1, int(max_words or 1))
    source_limits = source_limits or {}

    filtered: list[dict] = []
    exact_seen: set[str] = set()
    fingerprints: list[set[str]] = []
    diagnostics = defaultdict(int)

    for rank, item in enumerate(context_items, start=1):
        text = str(item.get("text", "")).strip()
        if not text:
            diagnostics["empty"] += 1
            continue
        if not _score_allowed(item, min_score):
            diagnostics["below_score"] += 1
            continue

        exact = _normalise_text(text)
        if exact in exact_seen:
            diagnostics["exact_duplicate"] += 1
            continue
        if _is_near_duplicate(text, fingerprints):
            diagnostics["near_duplicate"] += 1
            continue

        exact_seen.add(exact)
        fingerprints.append(_token_fingerprint(text))
        enriched = dict(item)
        enriched.setdefault("retrieval_rank", rank)
        enriched.setdefault("word_count", _word_count(text))
        filtered.append(enriched)

    by_source: dict[str, list[dict]] = defaultdict(list)
    for item in filtered:
        by_source[str(item.get("source") or "unknown")].append(item)

    selected: list[dict] = []
    selected_ids: set[int] = set()

    # Keep tender and company logically separated while preventing one source
    # from consuming the entire prompt budget.
    for source in ("tender", "company", "unknown"):
        limit = source_limits.get(source, max_chunks)
        for item in by_source.get(source, [])[: max(0, limit)]:
            selected.append(item)
            selected_ids.add(id(item))
            if len(selected) >= max_chunks:
                break
        if len(selected) >= max_chunks:
            break

    if len(selected) < max_chunks:
        for item in filtered:
            if id(item) in selected_ids:
                continue
            selected.append(item)
            selected_ids.add(id(item))
            if len(selected) >= max_chunks:
                break

    budgeted: list[dict] = []
    remaining_words = max_words

    for item in selected:
        text = str(item.get("text", "")).strip()
        words = _word_count(text)
        if remaining_words <= 0:
            diagnostics["over_word_budget"] += 1
            break
        budget_item = dict(item)
        if words > remaining_words:
            if remaining_words <= 0:
                diagnostics["over_word_budget"] += 1
                break
            budget_item["text"] = _trim_words(text, remaining_words)
            budget_item["context_truncated"] = True
            budget_item["original_word_count"] = words
            words = _word_count(budget_item["text"])
        budget_item["word_count"] = words
        budgeted.append(budget_item)
        remaining_words -= words

    logger.info(
        "Context assembly: input=%s kept=%s words=%s diagnostics=%s",
        len(context_items),
        len(budgeted),
        sum(int(item.get("word_count", 0)) for item in budgeted),
        dict(diagnostics),
    )
    return budgeted
