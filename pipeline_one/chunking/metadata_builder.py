"""
metadata_builder.py

Builds metadata dictionaries for chunks.

This ensures all chunks follow a consistent metadata structure
before being embedded and stored in the vector database.
"""

from typing import Optional
from pipeline_one.parsing.models.parsed_document import ParsedSection


def build_metadata(
    chunk_id: str,
    doc_id: str,
    source_file: str,
    section: ParsedSection,
    language: str,
    chunk_type: str = "text",
    parent_section: Optional[str] = None,
    table_id: Optional[str] = None
) -> dict:
    """
    Create metadata dictionary for a chunk.

    Args:
        doc_id: ID of the document
        section: ParsedSection object
        language: detected language
        chunk_type: text | table | table_summary
        parent_section: optional parent section title

    Returns:
        metadata dict
    """

    metadata = {
        "chunk_id" : chunk_id,
        "doc_id": doc_id,
        "source_file": source_file,
        "section_title": section.title,

        "section_path": (
            [parent_section, section.title]
            if parent_section
            else [section.title]
        ),

        "page_start": section.page_start,
        "page_end": section.page_end,

        "language": language,
        "chunk_type": chunk_type
    }

    if parent_section:
        metadata["parent_section"] = parent_section
    if table_id:
        metadata["table_id"] = table_id
    metadata["section_id"] = section.section_id
    return metadata