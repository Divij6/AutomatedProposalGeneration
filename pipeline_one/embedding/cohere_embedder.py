"""
cohere_embedder.py

Converts chunk texts into dense vectors using Cohere's
embed-multilingual-v3.0 model.

Why Cohere embed-multilingual-v3.0:
  - Supports 100+ languages — handles Hindi, Marathi, mixed tenders
  - 1024-dimensional vectors — good balance of accuracy vs storage
  - Free tier: 1000 calls/min — plenty for our use case
  - input_type matters:
      search_document → used HERE when embedding chunks for storage
      search_query    → used in Phase 5 when agent searches

Usage:
    from embedding.cohere_embedder import embed_chunks
    vectors = embed_chunks(chunks, api_key="your-key")
"""

import logging
import time
from typing import List
import cohere

from ..chunking.models.chunk_model import Chunk

logger = logging.getLogger(__name__)

# Cohere's hard limit per request is 96 texts
COHERE_BATCH_SIZE = 96

# Sleep between batches to respect free tier rate limits
BATCH_SLEEP_SECONDS = 0.5


def _batch_texts(texts: List[str], batch_size: int) -> List[List[str]]:
    """
    Splits a flat list of texts into batches of batch_size.

    Example:
        _batch_texts(["a","b","c","d"], batch_size=2)
        → [["a","b"], ["c","d"]]
    """
    return [
        texts[i : i + batch_size]
        for i in range(0, len(texts), batch_size)
    ]


def embed_chunks(
    chunks  : List[Chunk],
    api_key : str,
) -> List[List[float]]:
    """
    Embed a list of Chunk objects using Cohere's multilingual model.

    Sends texts in batches of 96 to stay within API limits.
    Returns vectors in the SAME ORDER as input chunks.

    Args:
        chunks  : list of Chunk objects from Phase 2
        api_key : your Cohere API key

    Returns:
        List of 1024-dimensional vectors, one per chunk.
        vectors[i] corresponds to chunks[i].

    Raises:
        RuntimeError: if Cohere API call fails after retries
    """

    if not chunks:
        logger.warning("embed_chunks called with empty chunk list — returning []")
        return []

    logger.info(f"Embedding {len(chunks)} chunks with Cohere...")

    # ── Initialise Cohere client ──────────────────────────────────────────────
    client = cohere.ClientV2(api_key=api_key)

    # ── Extract texts in order ────────────────────────────────────────────────
    texts   = [chunk.text for chunk in chunks]
    batches = _batch_texts(texts, COHERE_BATCH_SIZE)

    logger.info(
        f"Split into {len(batches)} batches "
        f"of up to {COHERE_BATCH_SIZE} texts each"
    )

    # ── Embed each batch ──────────────────────────────────────────────────────
    all_vectors: List[List[float]] = []

    for i, batch in enumerate(batches):
        logger.info(f"Embedding batch {i + 1}/{len(batches)} ({len(batch)} texts)...")

        try:
            response = client.embed(
                texts      = batch,
                model      = "embed-multilingual-v3.0",
                input_type = "search_document",  # storing — not querying
                embedding_types = ["float"],
            )

            # Extract float vectors from response
            batch_vectors = response.embeddings.float
            all_vectors.extend(batch_vectors)

            logger.info(f"Batch {i + 1} done — {len(batch_vectors)} vectors received")

        except Exception as e:
            raise RuntimeError(
                f"Cohere embedding failed on batch {i + 1}/{len(batches)}: {e}"
            )

        # Sleep between batches to respect rate limits
        if i < len(batches) - 1:
            time.sleep(BATCH_SLEEP_SECONDS)

    if not all_vectors:
        logger.warning("Embedding completed with zero vectors")
        return []

    logger.info("DEBUG all_vectors length: %s", len(all_vectors))
    logger.info("DEBUG accessing all_vectors index: 0")

    logger.info(
        f"Embedding complete — "
        f"{len(all_vectors)} vectors, "
        f"each {len(all_vectors[0])} dimensions"
    )

    return all_vectors

def embed_query(
    text: str,
    api_key: str
) -> List[float]:

    """
    Embed a single query string
    using search_query mode.

    Used during retrieval.

    Args:
        text: query string (e.g. section title)
        api_key: Cohere API key

    Returns:
        1024-d vector
    """

    client = cohere.ClientV2(
        api_key=api_key
    )

    try:

        response = client.embed(

            texts=[text],

            model="embed-multilingual-v3.0",

            input_type="search_query",

            embedding_types=["float"],

        )

        vectors = response.embeddings.float
        logger.info("DEBUG query embedding vectors length: %s", len(vectors))
        logger.info("DEBUG accessing query embedding vectors index: 0")
        if not vectors:
            raise RuntimeError("Query embedding returned no vectors")
        return vectors[0]

    except Exception as e:

        raise RuntimeError(
            f"Query embedding failed: {e}"
        )
