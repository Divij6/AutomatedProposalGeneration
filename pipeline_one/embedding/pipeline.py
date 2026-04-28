"""
embedding/pipeline.py

Orchestrator for Phase 3 embedding.
The only file you call from outside the embedding module.

Usage:
    from embedding.pipeline import run_embedding_pipeline

    result = run_embedding_pipeline(
        chunks      = chunks,
        doc_id      = parsed_doc.doc_id,
        cohere_key  = "your-cohere-key",
        qdrant_url  = "https://xyz.aws.cloud.qdrant.io",
        qdrant_key  = "your-qdrant-key",
    )

    print(result["total_chunks"])
    print(result["vectors_in_collection"])
"""

import logging
import time
from typing import List

from qdrant_client import QdrantClient

from ..chunking.models.chunk_model import Chunk
from .cohere_embedder import embed_chunks
from .qdrant_store import (
    get_or_create_collection,
    upsert_chunks,
    get_collection_info,
)

logger = logging.getLogger(__name__)


def _get_qdrant_client(qdrant_url: str, qdrant_key: str) -> QdrantClient:
    """
    Creates a QdrantClient connected to Qdrant Cloud.
    Tests the connection immediately — fails fast if credentials are wrong.

    Args:
        qdrant_url : your Qdrant Cloud cluster URL
        qdrant_key : your Qdrant Cloud API key

    Returns:
        Connected QdrantClient

    Raises:
        RuntimeError: if connection fails
    """

    logger.info(f"Connecting to Qdrant at: {qdrant_url}")

    try:
        client = QdrantClient(
            url    = qdrant_url,
            api_key= qdrant_key,
            timeout=60,
        )

        # Test connection immediately
        client.get_collections()
        logger.info("Qdrant connection successful")
        return client

    except Exception as e:
        raise RuntimeError(
            f"Failed to connect to Qdrant at '{qdrant_url}': {e}\n"
            f"Check your QDRANT_URL and QDRANT_API_KEY."
        )


def run_embedding_pipeline(
    chunks     : List[Chunk],
    doc_id     : str,
    cohere_key : str,
    qdrant_url : str,
    qdrant_key : str,
    collection_name : str="tender_chunks"
) -> dict:
    """
    Main entry point for Phase 3.

    Takes chunks from Phase 2, embeds them with Cohere,
    and stores them in Qdrant Cloud.

    Args:
        chunks     : list of Chunk objects from run_chunking_pipeline()
        doc_id     : document ID — used for logging and deduplication
        cohere_key : Cohere API key
        qdrant_url : Qdrant Cloud cluster URL
        qdrant_key : Qdrant Cloud API key

    Returns:
        Summary dict with keys:
            - doc_id
            - total_chunks
            - text_chunks
            - table_chunks
            - vectors_stored
            - vectors_in_collection
            - duration_seconds

    Raises:
        ValueError  : if chunks list is empty
        RuntimeError: if Cohere or Qdrant calls fail
    """

    if not chunks:
        raise ValueError(
            f"No chunks provided for doc_id='{doc_id}'. "
            f"Run Phase 2 chunking first."
        )

    start = time.time()

    logger.info("=" * 60)
    logger.info(f"Phase 3 Embedding starting for doc_id: {doc_id}")
    logger.info(f"Total chunks to embed: {len(chunks)}")
    logger.info("=" * 60)

    # ── Step 1: Connect to Qdrant ─────────────────────────────────────────────
    logger.info("Step 1/4 — Connecting to Qdrant...")
    client = _get_qdrant_client(qdrant_url, qdrant_key)

    # ── Step 2: Ensure collection exists ─────────────────────────────────────
    logger.info("Step 2/4 — Ensuring collection exists...")
    get_or_create_collection(client,collection_name)

    # ── Step 3: Embed all chunks with Cohere ──────────────────────────────────
    logger.info("Step 3/4 — Embedding chunks with Cohere...")
    vectors = embed_chunks(chunks, api_key=cohere_key)

    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"Vector count mismatch after embedding: "
            f"{len(vectors)} vectors for {len(chunks)} chunks"
        )

    # ── Step 4: Upsert into Qdrant ────────────────────────────────────────────
    logger.info("Step 4/4 — Storing vectors in Qdrant...")
    vectors_stored = upsert_chunks(
        client  = client,
        chunks  = chunks,
        vectors = vectors,
        doc_id  = doc_id,
        collection_name=collection_name
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    duration     = round(time.time() - start, 2)
    text_chunks  = len([c for c in chunks if not c.is_table])
    table_chunks = len([c for c in chunks if c.is_table])
    coll_info    = get_collection_info(client, collection_name)

    logger.info("=" * 60)
    logger.info("Phase 3 Embedding COMPLETE")
    logger.info(f"  doc_id               : {doc_id}")
    logger.info(f"  total chunks         : {len(chunks)}")
    logger.info(f"  text chunks          : {text_chunks}")
    logger.info(f"  table chunks         : {table_chunks}")
    logger.info(f"  vectors stored       : {vectors_stored}")
    logger.info(f"  total in collection  : {coll_info['vectors_count']}")
    logger.info(f"  duration             : {duration}s")
    logger.info("=" * 60)

    return {
        "doc_id"               : doc_id,
        "total_chunks"         : len(chunks),
        "text_chunks"          : text_chunks,
        "table_chunks"         : table_chunks,
        "vectors_stored"       : vectors_stored,
        "vectors_in_collection": coll_info["vectors_count"],
        "duration_seconds"     : duration,
    }