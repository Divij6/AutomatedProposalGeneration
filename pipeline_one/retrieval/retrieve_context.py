"""
Retrieval entry point for proposal generation.

This module preserves the historical retrieve_section_context(...) contract while
fixing query embedding mode, enriching weak section-title queries, and applying
prompt-safe context assembly guardrails.
"""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

try:
    from qdrant_client.models import MatchAny
except Exception:  # pragma: no cover - older qdrant-client compatibility
    MatchAny = None

from config import (
    RETRIEVAL_COMPANY_MAX_CHUNKS,
    RETRIEVAL_DEBUG,
    RETRIEVAL_ENABLE_NEIGHBORS,
    RETRIEVAL_MAX_CONTEXT_CHUNKS,
    RETRIEVAL_MAX_CONTEXT_WORDS,
    RETRIEVAL_MIN_SCORE,
    RETRIEVAL_NEIGHBOR_WINDOW,
    RETRIEVAL_TENDER_MAX_CHUNKS,
)
from pipeline_one.embedding.cohere_embedder import embed_query
from pipeline_one.retrieval.context_assembler import assemble_context_items
from pipeline_one.retrieval.query_builder import build_retrieval_query

logger = logging.getLogger(__name__)


def _chunk_type_condition(chunk_types: list[str] | tuple[str, ...] | None):
    if not chunk_types:
        return None
    cleaned = [str(value).strip() for value in chunk_types if str(value).strip()]
    if not cleaned:
        return None
    if len(cleaned) == 1 or MatchAny is None:
        return FieldCondition(key="chunk_type", match=MatchValue(value=cleaned[0]))
    return FieldCondition(key="chunk_type", match=MatchAny(any=cleaned))


def _build_filter(
    company_id: str,
    *,
    doc_id: str | None = None,
    chunk_types: list[str] | tuple[str, ...] | None = None,
) -> Filter:
    conditions = [
        FieldCondition(key="company_id", match=MatchValue(value=company_id)),
    ]
    if doc_id:
        conditions.append(FieldCondition(key="doc_id", match=MatchValue(value=doc_id)))
    chunk_type_condition = _chunk_type_condition(chunk_types)
    if chunk_type_condition is not None:
        conditions.append(chunk_type_condition)
    return Filter(must=conditions)


def _point_to_context(point, source: str, rank: int) -> dict:
    payload = getattr(point, "payload", None) or {}
    return {
        "source": source,
        "text": payload.get("text", ""),
        "chunk_id": payload.get("chunk_id"),
        "doc_id": payload.get("doc_id"),
        "section_title": payload.get("section_title"),
        "section_id": payload.get("section_id"),
        "section_path": payload.get("section_path"),
        "page_start": payload.get("page_start"),
        "page_end": payload.get("page_end"),
        "chunk_type": payload.get("chunk_type"),
        "score": getattr(point, "score", None),
        "retrieval_rank": rank,
    }


def _parse_chunk_number(chunk_id: str | None) -> int | None:
    if not chunk_id or "_" not in str(chunk_id):
        return None
    try:
        return int(str(chunk_id).split("_", 1)[1])
    except (TypeError, ValueError):
        return None


def _fetch_neighbor_context(
    client: QdrantClient,
    payload: dict,
    *,
    window: int,
    rank_base: int,
) -> list[dict]:
    """
    Controlled neighbor expansion.

    Neighbor chunks are accepted only from the same document, section, and chunk
    type. This avoids the previous blind previous/next injection that polluted
    prompts across section boundaries.
    """

    if window <= 0:
        return []

    numeric_id = _parse_chunk_number(payload.get("chunk_id"))
    doc_id = payload.get("doc_id")
    section_id = payload.get("section_id")
    chunk_type = payload.get("chunk_type")

    if numeric_id is None or not doc_id:
        return []

    contexts: list[dict] = []
    rank = rank_base

    for delta in range(-window, window + 1):
        if delta == 0:
            continue
        neighbor_id = f"c_{numeric_id + delta:05d}"
        conditions = [
            FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
            FieldCondition(key="chunk_id", match=MatchValue(value=neighbor_id)),
        ]
        if section_id:
            conditions.append(FieldCondition(key="section_id", match=MatchValue(value=section_id)))
        if chunk_type:
            conditions.append(FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type)))

        try:
            neighbor_points, _ = client.scroll(
                collection_name="tender_chunks",
                scroll_filter=Filter(must=conditions),
                limit=1,
            )
        except Exception as exc:
            logger.debug("Neighbor lookup failed for %s: %s", neighbor_id, exc)
            continue

        if not neighbor_points:
            continue
        rank += 1
        item = _point_to_context(neighbor_points[0], "tender", rank)
        item["neighbor_of"] = payload.get("chunk_id")
        item["score"] = None
        contexts.append(item)

    return contexts


def retrieve_section_context(
    section_title: str,
    company_id: str,
    cohere_key: str,
    qdrant_url: str,
    qdrant_key: str,
    top_k: int = 5,
    doc_id: str | None = None,
    *,
    requirement_text: str | None = None,
    table_headers: list[str] | tuple[str, ...] | None = None,
    parent_titles: list[str] | tuple[str, ...] | None = None,
    nearby_clause_context: str | None = None,
    mode: str | None = None,
    min_score: float | None = None,
    max_results: int | None = None,
    max_context_words: int | None = None,
    include_neighbors: bool | None = None,
    neighbor_window: int | None = None,
    chunk_types: list[str] | tuple[str, ...] | None = None,
) -> list[dict]:
    """
    Retrieve bounded context for one proposal section or table row.

    Existing positional arguments are unchanged. New keyword-only arguments are
    optional so legacy callers continue to work.
    """

    min_score = RETRIEVAL_MIN_SCORE if min_score is None else min_score
    max_results = RETRIEVAL_MAX_CONTEXT_CHUNKS if max_results is None else max_results
    max_context_words = (
        RETRIEVAL_MAX_CONTEXT_WORDS if max_context_words is None else max_context_words
    )
    include_neighbors = (
        RETRIEVAL_ENABLE_NEIGHBORS if include_neighbors is None else include_neighbors
    )
    neighbor_window = (
        RETRIEVAL_NEIGHBOR_WINDOW if neighbor_window is None else neighbor_window
    )

    query_text = build_retrieval_query(
        section_title=section_title,
        requirement_text=requirement_text,
        table_headers=table_headers,
        parent_titles=parent_titles,
        nearby_clause_context=nearby_clause_context,
        mode=mode,
    )

    # Critical correctness fix: queries must use Cohere search_query mode, not
    # document embedding mode. embed_query wraps input_type="search_query".
    query_vector = embed_query(text=query_text, api_key=cohere_key)
    if not query_vector:
        logger.warning("Query embedding returned no vector for section '%s'", section_title)
        return []

    client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
    tender_filter = _build_filter(company_id, doc_id=doc_id, chunk_types=chunk_types)
    company_filter = _build_filter(company_id, chunk_types=chunk_types)

    logger.info(
        "Retrieving context | title=%s mode=%s top_k=%s min_score=%s max_results=%s",
        section_title,
        mode,
        top_k,
        min_score,
        max_results,
    )
    if RETRIEVAL_DEBUG:
        logger.debug("Enriched retrieval query: %s", query_text)

    tender_points = client.query_points(
        collection_name="tender_chunks",
        query=query_vector,
        limit=top_k,
        query_filter=tender_filter,
    ).points

    raw_context: list[dict] = []
    rank = 0
    for point in tender_points:
        rank += 1
        payload = getattr(point, "payload", None) or {}
        raw_context.append(_point_to_context(point, "tender", rank))
        if include_neighbors:
            raw_context.extend(
                _fetch_neighbor_context(
                    client,
                    payload,
                    window=max(0, int(neighbor_window or 0)),
                    rank_base=rank,
                )
            )

    company_points = client.query_points(
        collection_name="company_knowledge",
        query=query_vector,
        limit=top_k,
        query_filter=company_filter,
    ).points

    for point in company_points:
        rank += 1
        raw_context.append(_point_to_context(point, "company", rank))

    assembled = assemble_context_items(
        raw_context,
        max_chunks=max_results,
        max_words=max_context_words,
        min_score=min_score,
        source_limits={
            "tender": RETRIEVAL_TENDER_MAX_CHUNKS,
            "company": RETRIEVAL_COMPANY_MAX_CHUNKS,
        },
    )

    logger.info(
        "Retrieved context assembled | raw=%s final=%s tender=%s company=%s",
        len(raw_context),
        len(assembled),
        sum(1 for item in assembled if item.get("source") == "tender"),
        sum(1 for item in assembled if item.get("source") == "company"),
    )
    return assembled
