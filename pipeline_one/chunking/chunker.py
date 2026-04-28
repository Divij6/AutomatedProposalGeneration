"""
chunker.py

Main chunking logic for Phase 2.

Converts ParsedDocument → List[Chunk].

Pipeline:
    ParsedDocument
        ↓
    Walk section hierarchy
        ↓
    Split large text sections
        ↓
    Keep tables atomic
        ↓
    Attach metadata
        ↓
    Return chunks ready for embeddings
"""

from typing import List
import itertools

from pipeline_one.parsing.models.parsed_document import ParsedDocument
from pipeline_one.chunking.models.chunk_model import Chunk
from .section_walker import walk_sections
from .language_detector import detect_language
from .metadata_builder import build_metadata


# ─── CONFIG ───────────────────────────────────────────────────────────────

CHUNK_SIZE = 350
CHUNK_OVERLAP = 50


# ─── TEXT SPLITTING ──────────────────────────────────────────────────────

def split_text(text: str) -> List[str]:
    """
    Splits text into overlapping chunks.

    Uses simple token approximation based on words.
    """

    words = text.split()

    if len(words) <= CHUNK_SIZE:
        return [" ".join(words)]

    chunks = []
    start = 0

    while start < len(words):
        end = start + CHUNK_SIZE
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


# ─── MAIN FUNCTION ───────────────────────────────────────────────────────

def chunk_document(parsed_doc: ParsedDocument) -> List[Chunk]:
    """
    Convert ParsedDocument → List[Chunk]
    """

    chunks: List[Chunk] = []
    chunk_counter = itertools.count(1)

    for section, parent in walk_sections(parsed_doc.sections):

        # Detect language
        language = detect_language(
            section.content,
            parsed_doc.language_hint
        )

        # ── TEXT CHUNKS ─────────────────────────────────────────────

        if section.content:

            # prepend section title for context
            text_with_context = f"{section.title}\n\n{section.content}"

            text_chunks = split_text(text_with_context)

            for text_part in text_chunks:

                chunk_id = f"c_{next(chunk_counter):05d}"

                metadata = build_metadata(
                    chunk_id=chunk_id,
                    doc_id=parsed_doc.doc_id,
                    source_file=parsed_doc.file_name,
                    section=section,
                    language=language,
                    chunk_type="text",
                    parent_section=parent

                )

                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        text=text_part,
                        is_table=False,
                        language=language,
                        metadata=metadata
                    )
                )

        # ── TABLE CHUNKS (atomic) ───────────────────────────────────

        for table in section.tables:

            chunk_id = f"c_{next(chunk_counter):05d}"

            metadata = build_metadata(
                chunk_id=chunk_id,
                doc_id=parsed_doc.doc_id,
                source_file=parsed_doc.file_name,
                section=section,
                language=language,
                chunk_type="table",
                parent_section=parent
            )

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=table.raw_markdown,
                    is_table = True,
                    language = language,
                    metadata=metadata
                )
            )

    return chunks