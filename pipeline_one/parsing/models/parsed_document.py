"""
models/parsed_document.py

Defines the unified data shape for the entire Phase 1 pipeline.
Both Docling and pdfplumber outputs are normalised into these models.
Everything downstream (Phase 2 chunking) only ever sees these models —
it never needs to know which parser ran.

Model hierarchy:
    ParsedDocument
        ├── quality_report  → QualityReport
        │       └── parser_used → ParserUsed (enum)
        ├── sections        → List[ParsedSection]
        │       ├── tables   → List[ParsedTable]
        │       └── children → List[ParsedSection]  (recursive)
        └── all_tables      → List[ParsedTable]  (flat list for quick access)
"""

from __future__ import annotations  # allows ParsedSection to reference itself
from enum import Enum
from pydantic import BaseModel, Field


# ─── MODEL 1: ParserUsed ──────────────────────────────────────────────────────
# Simple enum — tells downstream which parser ultimately produced the output.
# Stored in both QualityReport and ParsedDocument for full traceability.

class ParserUsed(str, Enum):
    DOCLING  = "docling"   # Docling ran successfully and passed quality checks
    FALLBACK = "fallback"  # pdfplumber + pdfminer ran because Docling failed checks


# ─── MODEL 2: ParsedTable ─────────────────────────────────────────────────────
# Represents one extracted table from the PDF.
# Tables are ALWAYS kept as atomic units — never split across chunks in Phase 2.
# The raw_markdown field is what gets embedded in Phase 3.

class ParsedTable(BaseModel):
    table_id: str = Field(
        description="Unique table ID e.g. 't_001'. Format: t_{3-digit-number}"
    )
    page_number: int = Field(
        description="Page number where this table appears in the PDF (1-indexed)"
    )
    section_title: str = Field(
        description="Title of the section this table belongs to. "
                    "Used as context during retrieval."
    )
    headers: list[str] = Field(
        default_factory=list,
        description="List of column header strings e.g. ['Item', 'Quantity', 'Unit Rate']. "
                    "Empty list if table has no detectable header row."
    )
    rows: list[list[str]] = Field(
        default_factory=list,
        description="List of rows. Each row is a list of cell strings. "
                    "e.g. [['Laptop', '10', '45000'], ['Mouse', '10', '500']]"
    )
    raw_markdown: str = Field(
        default="",
        description="The entire table rendered as a markdown string. "
                    "This is what gets stored in Qdrant and embedded by Cohere."
    )


# ─── MODEL 3: ParsedSection ───────────────────────────────────────────────────
# Represents one section of the document (heading + its content).
# This is a RECURSIVE model — a section can contain child sections.
# That recursion is what preserves the full document hierarchy.
#
# Example hierarchy:
#   Section (level=1): "3. Technical Requirements"
#       Section (level=2): "3.1 Hardware Specifications"
#           Section (level=3): "3.1.1 Server Requirements"

class ParsedSection(BaseModel):
    section_id: str = Field(
        description="Unique section ID e.g. 's_001'. Format: s_{3-digit-number}"
    )
    title: str = Field(
        description="The heading text of this section e.g. 'Eligibility Criteria'"
    )
    level: int = Field(
        description="Heading level. 1 = main heading, 2 = subheading, 3 = sub-subheading. "
                    "Used by Phase 2 to determine chunk boundaries."
    )
    page_start: int = Field(
        description="Page number where this section starts (1-indexed)"
    )
    page_end: int = Field(
        description="Page number where this section ends (1-indexed). "
                    "Equal to page_start if section fits on one page."
    )
    content: str = Field(
        default="",
        description="The full plain text content of this section, "
                    "excluding child section content. "
                    "Tables are excluded from here — they are in the tables field."
    )
    tables: list[ParsedTable] = Field(
        default_factory=list,
        description="All tables found directly inside this section. "
                    "Tables inside child sections are stored in those child sections."
    )
    children: list[ParsedSection] = Field(
        default_factory=list,
        description="Child sections nested under this section. "
                    "This recursion preserves the full document hierarchy."
    )


# Required by Pydantic v2 for recursive models — tells Pydantic to fully
# resolve the ParsedSection → children → ParsedSection self-reference.
ParsedSection.model_rebuild()


# ─── MODEL 4: QualityReport ───────────────────────────────────────────────────
# The result of running all 4 quality checks after Docling parses the document.
# If passed=False, the pipeline triggers the pdfplumber fallback parser.



# ─── MODEL 5: ParsedDocument ──────────────────────────────────────────────────
# The top-level output of the entire Phase 1 pipeline.
# This is the ONLY object that pipeline.py returns.
# Phase 2 (chunking) takes this as its input and nothing else.

class ParsedDocument(BaseModel):
    doc_id: str = Field(
        description="Unique document ID generated at upload time. "
                    "e.g. 'tender_abc123' or 'company_data_001'. "
                    "Used as the primary key in Qdrant and PostgreSQL."
    )
    file_name: str = Field(
        description="Original filename of the uploaded PDF "
                    "e.g. 'tender_mumbai_metro_2024.pdf'"
    )
    total_pages: int = Field(
        description="Total number of pages in the PDF as reported by the parser."
    )
    parser_used: ParserUsed = Field(
        description="Which parser ultimately produced this document's content. "
                    "Either ParserUsed.DOCLING or ParserUsed.FALLBACK."
    )
    language_hint: str = Field(
        default="en",
        description="Best-guess language of the document. "
                    "Detected from the first 2000 characters of extracted text. "
                    "e.g. 'en', 'hi', 'fr'. "
                    "Used by Phase 2 for language-aware chunking."
    )
    sections: list[ParsedSection] = Field(
        default_factory=list,
        description="Full document tree as a list of top-level sections. "
                    "Each section can have children (nested sections). "
                    "This is the primary structure Phase 2 works with."
    )
    all_tables: list[ParsedTable] = Field(
        default_factory=list,
        description="Flat list of ALL tables across the entire document. "
                    "Duplicate of tables inside sections — kept here for quick "
                    "access without needing to walk the full section tree."
    )

    metadata: dict = Field(
        default_factory=dict,
        description="Flexible dict for any extra information. "
                    "Populated by pipeline.py with: "
                    "{'file_size_mb': 2.4, 'parse_time_seconds': 18.3, "
                    "'docling_version': '1.x', "
                    "'upload_timestamp': '2024-01-01T10:00:00'}"
    )