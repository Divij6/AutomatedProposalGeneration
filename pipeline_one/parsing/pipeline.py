"""
pipeline.py

The orchestrator for Phase 1. This is the ONLY file you call from outside.
Everything else in phase1_parsing/ is an implementation detail.

Usage:
    from phase1_parsing.pipeline import run_parsing_pipeline

    result = run_parsing_pipeline(
        pdf_path = "path/to/tender.pdf",
        doc_id   = "tender_mumbai_2024",
    )

    # result is a ParsedDocument object
    print(result.total_pages)
    print(result.parser_used)
    print(len(result.sections))
    print(len(result.all_tables))

Full flow:
    1. Validate the PDF file exists and is readable
    2. Run Docling parser (GPU-accelerated)
    3. Run quality checks on Docling output
    4. If quality checks fail → run pdfplumber fallback parser
    5. If fallback also fails → raise PipelineError (unrecoverable)
    6. Normalise whichever parser's output into ParsedDocument
    7. Return ParsedDocument

Logging:
    Set LOG_LEVEL=DEBUG for detailed per-step output.
    Set LOG_LEVEL=INFO (default) for summary output.
    All steps log clearly so you can follow exactly what's happening.
"""

import logging
import os
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

from .docling_parser  import parse_with_docling,  DoclingParserError
from .normaliser      import normalise
from .models.parsed_document import ParsedDocument, ParserUsed

# ─── LOGGING SETUP ────────────────────────────────────────────────────────────
# Uses the LOG_LEVEL environment variable if set, defaults to INFO.

log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(
    level   = log_level,
    format  = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── CUSTOM EXCEPTION ─────────────────────────────────────────────────────────

class PipelineError(Exception):
    """
    Raised when the pipeline cannot produce a valid ParsedDocument.
    This means BOTH Docling AND the fallback parser failed.
    Should never happen with well-formed digital PDFs.
    """
    pass


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _get_file_size_mb(path: Path) -> float:
    """Returns file size in megabytes, rounded to 2 decimal places."""
    try:
        return round(path.stat().st_size / (1024 * 1024), 2)
    except Exception:
        return 0.0


def _generate_doc_id(file_name: str, prefix: str = "doc") -> str:
    """
    Generates a unique document ID.
    Format: {prefix}_{first8charsofUUID}
    e.g. "doc_a3f2c1b4" or "tender_a3f2c1b4"

    The prefix should be passed by the caller to indicate doc type:
      - "tender"  for tender documents
      - "company" for company knowledge documents
    """
    short_uuid = str(uuid.uuid4()).replace("-", "")[:8]
    return f"{prefix}_{short_uuid}"


# ─── MAIN PIPELINE FUNCTION ───────────────────────────────────────────────────

def run_parsing_pipeline(
    pdf_path:  str | Path,
    doc_id:    str | None = None,
    doc_prefix: str = "doc",
) -> ParsedDocument:
    """
    Main entry point for Phase 1. Parses a PDF and returns a ParsedDocument.

    Args:
        pdf_path:   Path to the PDF file to parse. Can be str or Path object.
        doc_id:     Optional. Unique ID for this document. Auto-generated if not provided.
                    Use meaningful prefixes: "tender_mumbai_2024", "company_data_001"
        doc_prefix: Prefix for auto-generated doc_id if doc_id is not provided.
                    e.g. "tender" → generates "tender_a3f2c1b4"

    Returns:
        ParsedDocument — fully validated output ready for Phase 2 (chunking).

    Raises:
        PipelineError — if both Docling AND the fallback parser fail.
                        This should be treated as a hard error requiring manual review.
        FileNotFoundError — if the PDF file does not exist.
        ValueError — if the file is not a PDF.
    """
    pdf_path  = Path(pdf_path)
    start_time = time.time()

    # ── STEP 0: Validate input ───────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"Phase 1 Pipeline starting for: {pdf_path.name}")
    logger.info("=" * 60)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {pdf_path.suffix}")

    file_size_mb = _get_file_size_mb(pdf_path)
    logger.info(f"File size: {file_size_mb} MB")

    # Auto-generate doc_id if not provided
    if not doc_id:
        doc_id = _generate_doc_id(pdf_path.name, prefix=doc_prefix)
    logger.info(f"Document ID: {doc_id}")

    file_name = pdf_path.name

    # ── STEP 1: Try Docling (primary parser) ─────────────────────────────────
    docling_output   = None
    # docling_error    = None
    # docling_duration = 0.0

    try:
        logger.info("STEP 1: Running Docling parser (primary)...")
        t0 = time.time()
        docling_output   = parse_with_docling(pdf_path)
        docling_duration = round(time.time() - t0, 2)
        logger.info(f"Docling completed in {docling_duration}s")

    except DoclingParserError as e:
        raise PipelineError(
            f"Docling failed to parse '{file_name}': {e}\n"
            f"Check that the PDF is a valid, non-corrupted digital document."
        )


    parser_used = ParserUsed.DOCLING


    # ── STEP 4: Normalise into ParsedDocument ────────────────────────────────
    logger.info(f"STEP 4: Normalising output (parser used: {parser_used.value})...")

    total_duration = round(time.time() - start_time, 2)

    metadata = {
        "file_size_mb":       file_size_mb,
        "parse_time_seconds": total_duration,
        "upload_timestamp":   datetime.now(timezone.utc).isoformat(),
        "docling_attempted":  True,
        "docling_error":     None,
    }

    parsed_doc = normalise(
        raw_output     = docling_output,
        doc_id         = doc_id,
        file_name      = file_name,
        parser_used    = parser_used.DOCLING,
        metadata       = metadata,
    )

    # ── STEP 5: Summary log ──────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Phase 1 Pipeline COMPLETE")
    logger.info(f"  Document ID    : {parsed_doc.doc_id}")
    logger.info(f"  File           : {parsed_doc.file_name}")
    logger.info(f"  Pages          : {parsed_doc.total_pages}")
    logger.info(f"  Parser used    : {parsed_doc.parser_used.value.upper()}")
    logger.info(f"  Sections       : {len(parsed_doc.sections)} (top-level)")
    logger.info(f"  Tables         : {len(parsed_doc.all_tables)} (total)")
    logger.info(f"  Language       : {parsed_doc.language_hint}")
    logger.info(f"  Total time     : {total_duration}s")
    logger.info("=" * 60)

    return parsed_doc