# """
# qdrant_store.py
#
# Stores chunk vectors and metadata in Qdrant Cloud.
#
# Each chunk becomes one point in Qdrant with:
#     - id      : unique integer
#     - vector  : 1024-dim float vector from Cohere
#     - payload : chunk text + all metadata for filtering
#
# Collection name: tender_chunks
#     This is where ALL tender document chunks live.
#     Filtered by doc_id during retrieval so each tender's
#     chunks are logically separated even in one collection.
#
# Usage:
#     from embedding.qdrant_store import get_or_create_collection, upsert_chunks
# """
#
# import logging
# from typing import List
#
# from qdrant_client import QdrantClient
# from qdrant_client.models import (
#     Distance,
#     VectorParams,
#     PointStruct,
#     PayloadSchemaType,
# )
#
# from ..chunking.models.chunk_model import Chunk
#
# logger = logging.getLogger(__name__)
#
# # Collection name in Qdrant — all tender chunks go here
# # Separated logically by doc_id in the payload
# COLLECTION_NAME = "tender_chunks"
#
# # How many points to upsert per request — keeps free tier happy
# UPSERT_BATCH_SIZE = 20
#
#
# def get_or_create_collection(client: QdrantClient) -> None:
#     """
#     Ensures the tender_chunks collection exists in Qdrant.
#     Creates it if it doesn't exist. Skips safely if it does.
#
#     Collection settings:
#         - vector size : 1024  (Cohere embed-multilingual-v3.0 output)
#         - distance    : Cosine (best for semantic text similarity)
#
#     Args:
#         client: connected QdrantClient instance
#     """
#
#     existing = [c.name for c in client.get_collections().collections]
#
#     if COLLECTION_NAME in existing:
#         logger.info(f"Collection '{COLLECTION_NAME}' already exists — skipping creation")
#         return
#
#     logger.info(f"Creating collection '{COLLECTION_NAME}'...")
#
#     client.create_collection(
#         collection_name = COLLECTION_NAME,
#         vectors_config  = VectorParams(
#             size     = 1024,          # Cohere multilingual vector size
#             distance = Distance.COSINE,
#         ),
#     )
#
#     # Create payload indexes for fast filtered search
#     # These let agents filter by doc_id, chunk_type, language
#     # without scanning every point in the collection
#     for field, schema in [
#         ("doc_id",     PayloadSchemaType.KEYWORD),
#         ("chunk_type", PayloadSchemaType.KEYWORD),
#         ("language",   PayloadSchemaType.KEYWORD),
#         ("section_id", PayloadSchemaType.KEYWORD),
#         ("page_start", PayloadSchemaType.INTEGER),
#     ]:
#         client.create_payload_index(
#             collection_name = COLLECTION_NAME,
#             field_name      = field,
#             field_schema    = schema,
#         )
#         logger.debug(f"Payload index created: {field}")
#
#     logger.info(f"Collection '{COLLECTION_NAME}' created with 5 payload indexes")
#
#
# def upsert_chunks(
#     client  : QdrantClient,
#     chunks  : List[Chunk],
#     vectors : List[List[float]],
#     doc_id  : str,
# ) -> int:
#     """
#     Store chunks and their vectors into Qdrant.
#
#     Each point payload contains:
#         - chunk_id      : original chunk ID e.g. 'c_00001'
#         - doc_id        : document this chunk belongs to
#         - text          : full chunk text (for retrieval without re-fetching PDF)
#         - is_table      : bool
#         - language      : ISO language code
#         - section_title : section heading
#         - section_id    : for sibling chunk retrieval
#         - section_path  : breadcrumb path
#         - page_start    : start page
#         - page_end      : end page
#         - chunk_type    : 'text' or 'table'
#         - source_file   : original PDF filename
#
#     Args:
#         client  : connected QdrantClient instance
#         chunks  : list of Chunk objects from Phase 2
#         vectors : list of vectors from cohere_embedder — same order as chunks
#         doc_id  : document ID (used for logging only — already in chunk metadata)
#
#     Returns:
#         Total number of points successfully upserted.
#
#     Raises:
#         ValueError  : if chunks and vectors lengths don't match
#         RuntimeError: if Qdrant upsert fails
#     """
#
#     if len(chunks) != len(vectors):
#         raise ValueError(
#             f"Chunks and vectors length mismatch: "
#             f"{len(chunks)} chunks vs {len(vectors)} vectors"
#         )
#
#     if not chunks:
#         logger.warning("upsert_chunks called with empty list — nothing to store")
#         return 0
#
#     logger.info(f"Upserting {len(chunks)} points into '{COLLECTION_NAME}'...")
#
#     # ── Build PointStruct list ────────────────────────────────────────────────
#     # Qdrant needs integer IDs — we use the chunk's position in the list
#     # offset by a hash of doc_id to avoid ID collisions across documents
#     import hashlib
#     doc_hash   = int(hashlib.md5(doc_id.encode()).hexdigest()[:8], 16)
#     id_offset  = doc_hash % 10_000_000  # keep IDs manageable
#
#     points = []
#     for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
#
#         # Build payload — merge chunk fields + metadata dict
#         payload = {
#             "chunk_id"  : chunk.chunk_id,
#             "text"      : chunk.text,
#             "is_table"  : chunk.is_table,
#             "language"  : chunk.language,
#             **chunk.metadata,   # spreads doc_id, section_title, page_start etc.
#         }
#
#         points.append(
#             PointStruct(
#                 id      = id_offset + i,
#                 vector  = vector,
#                 payload = payload,
#             )
#         )
#
#     # ── Upsert in batches ─────────────────────────────────────────────────────
#     total_upserted = 0
#
#     for batch_start in range(0, len(points), UPSERT_BATCH_SIZE):
#         batch = points[batch_start : batch_start + UPSERT_BATCH_SIZE]
#
#         try:
#             client.upsert(
#                 collection_name = COLLECTION_NAME,
#                 points          = batch,
#             )
#             total_upserted += len(batch)
#             logger.info(
#                 f"Upserted batch {batch_start // UPSERT_BATCH_SIZE + 1} — "
#                 f"{total_upserted}/{len(points)} points stored"
#             )
#
#         except Exception as e:
#             raise RuntimeError(
#                 f"Qdrant upsert failed at batch starting index {batch_start}: {e}"
#             )
#
#     logger.info(f"Upsert complete — {total_upserted} points stored for doc_id='{doc_id}'")
#     return total_upserted
#
#
# def get_collection_info(client: QdrantClient) -> dict:
#     """
#     Returns basic stats about the tender_chunks collection.
#     Used by pipeline.py for the summary log.
#
#     Returns:
#         dict with keys: name, vectors_count, status
#     """
#
#     try:
#         info = client.get_collection(COLLECTION_NAME)
#         return {
#             "name"         : COLLECTION_NAME,
#             "vectors_count": info.vectors_count,
#             "status"       : str(info.status),
#         }
#     except Exception as e:
#         logger.warning(f"Could not fetch collection info: {e}")
#         return {
#             "name"         : COLLECTION_NAME,
#             "vectors_count": "unknown",
#             "status"       : "unknown",
#         }

"""
qdrant_store.py

Stores chunk vectors and metadata in Qdrant Cloud.

Supports multiple collections:
    - tender_chunks
    - company_knowledge
"""

import logging
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
)

from ..chunking.models.chunk_model import Chunk

logger = logging.getLogger(__name__)

# Default collection names
DEFAULT_COLLECTION_NAME = "tender_chunks"
COMPANY_COLLECTION_NAME = "company_knowledge"

UPSERT_BATCH_SIZE = 20


# =========================================================
# Create Collection
# =========================================================

def get_or_create_collection(
        client: QdrantClient,
        collection_name: str = DEFAULT_COLLECTION_NAME
) -> None:

    existing = [
        c.name
        for c in client.get_collections().collections
    ]

    if collection_name in existing:
        logger.info(
            f"Collection '{collection_name}' already exists — skipping"
        )
        return

    logger.info(
        f"Creating collection '{collection_name}'..."
    )

    client.create_collection(

        collection_name=collection_name,

        vectors_config=VectorParams(
            size=1024,
            distance=Distance.COSINE,
        ),

    )

    # Create indexes
    for field, schema in [

        ("doc_id", PayloadSchemaType.KEYWORD),

        ("chunk_type", PayloadSchemaType.KEYWORD),

        ("language", PayloadSchemaType.KEYWORD),

        ("section_id", PayloadSchemaType.KEYWORD),

        ("page_start", PayloadSchemaType.INTEGER),

        ("company_id", PayloadSchemaType.KEYWORD),

    ]:

        client.create_payload_index(

            collection_name=collection_name,

            field_name=field,

            field_schema=schema,

        )

        logger.debug(
            f"Payload index created: {field}"
        )

    logger.info(
        f"Collection '{collection_name}' created successfully"
    )


# =========================================================
# Upsert Chunks
# =========================================================

def upsert_chunks(

    client: QdrantClient,

    chunks: List[Chunk],

    vectors: List[List[float]],

    doc_id: str,

    collection_name: str = DEFAULT_COLLECTION_NAME

) -> int:

    if len(chunks) != len(vectors):

        raise ValueError(

            f"Chunks and vectors length mismatch: "

            f"{len(chunks)} chunks vs {len(vectors)} vectors"

        )

    if not chunks:

        logger.warning(
            "upsert_chunks called with empty list"
        )

        return 0

    logger.info(
        f"Upserting {len(chunks)} points into '{collection_name}'..."
    )

    # Unique ID offset
    import hashlib

    doc_hash = int(
        hashlib.md5(doc_id.encode()).hexdigest()[:8],
        16
    )

    id_offset = doc_hash % 10_000_000

    points = []

    for i, (chunk, vector) in enumerate(

        zip(chunks, vectors)

    ):

        payload = {

            "chunk_id": chunk.chunk_id,

            "text": chunk.text,

            "is_table": chunk.is_table,

            "language": chunk.language,

            # Important for company filtering
            "company_id":
                chunk.metadata.get(
                    "company_id"
                ),

            **chunk.metadata,

        }

        points.append(

            PointStruct(

                id=id_offset + i,

                vector=vector,

                payload=payload,

            )

        )

    total_upserted = 0

    for batch_start in range(

        0,

        len(points),

        UPSERT_BATCH_SIZE

    ):

        batch = points[
            batch_start:
            batch_start + UPSERT_BATCH_SIZE
        ]

        try:

            client.upsert(

                collection_name=collection_name,

                points=batch,

            )

            total_upserted += len(batch)

            logger.info(

                f"Upserted "

                f"{total_upserted}/{len(points)} points"

            )

        except Exception as e:

            raise RuntimeError(

                f"Qdrant upsert failed: {e}"

            )

    logger.info(

        f"Upsert complete — "

        f"{total_upserted} stored "

        f"for doc_id='{doc_id}'"

    )

    return total_upserted


# =========================================================
# Get Collection Info
# =========================================================

def get_collection_info(

        client: QdrantClient,

        collection_name: str = DEFAULT_COLLECTION_NAME

) -> dict:

    try:

        info = client.get_collection(

            collection_name

        )

        return {

            "name": collection_name,

            "vectors_count":
                info.vectors_count,

            "status":
                str(info.status),

        }

    except Exception as e:

        logger.warning(

            f"Could not fetch info: {e}"

        )

        return {

            "name": collection_name,

            "vectors_count": "unknown",

            "status": "unknown",

        }