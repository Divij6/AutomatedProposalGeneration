"""
pipeline.py

Orchestrator for Phase 2 chunking.
The only file you call from outside the chunking module.

Usage:
    from chunking.pipeline import run_chunking_pipeline

    chunks = run_chunking_pipeline(parsed_doc)
    print(len(chunks))
    print(chunks[0].chunk_id)
    print(chunks[0].text)
    print(chunks[0].metadata)
"""

import logging
import time
from typing import List

from ..parsing.models.parsed_document import ParsedDocument
from pipeline_one.chunking.models.chunk_model import Chunk
from .chunker import chunk_document

logger = logging.getLogger(__name__)


def run_chunking_pipeline(parsed_doc: ParsedDocument) -> List[Chunk]:
    """
    Main entry point for Phase 2.
    Takes a ParsedDocument from Phase 1 and returns a flat list of Chunks.

    Args:
        parsed_doc: ParsedDocument produced by run_parsing_pipeline()

    Returns:
        List[Chunk] — ready for Phase 3 embedding

    Raises:
        ValueError: if parsed_doc has no sections at all
    """

    logger.info("=" * 60)
    logger.info(f"Phase 2 Chunking starting for: {parsed_doc.file_name}")
    logger.info("=" * 60)

    if not parsed_doc.sections:
        raise ValueError(
            f"ParsedDocument '{parsed_doc.doc_id}' has no sections. "
            f"Phase 1 may have failed silently."
        )

    start = time.time()

    # ── Run chunking ──────────────────────────────────────────────────────────
    chunks = chunk_document(parsed_doc)

    duration = round(time.time() - start, 2)

    # ── Summary ───────────────────────────────────────────────────────────────
    text_chunks  = [c for c in chunks if not c.is_table]
    table_chunks = [c for c in chunks if c.is_table]

    logger.info("=" * 60)
    logger.info("Phase 2 Chunking COMPLETE")
    logger.info(f"  doc_id        : {parsed_doc.doc_id}")
    logger.info(f"  total chunks  : {len(chunks)}")
    logger.info(f"  text chunks   : {len(text_chunks)}")
    logger.info(f"  table chunks  : {len(table_chunks)}")
    logger.info(f"  time          : {duration}s")
    logger.info("=" * 60)

    return chunks