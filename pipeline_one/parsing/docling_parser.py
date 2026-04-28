"""
docling_parser.py

Primary parser for Phase 1. Uses Docling (by IBM) to extract structured
content from digital PDF files with high accuracy.

What Docling gives us that regular parsers cannot:
  - Full document hierarchy (headings → subheadings → content)
  - Accurate table extraction via TableFormer deep learning model
  - Correct reading order even in multi-column layouts
  - Structured output (not just flat text)

GPU note for RTX 4050 6GB:
  - Docling's new RT-DETRv2 layout model requires ~5-6GB VRAM alone
  - We force the layout model to run on CPU to avoid OOM crashes
  - TableFormer (table extraction) also runs on CPU — stable for our doc sizes
  - Always run Docling to COMPLETION before starting the embedding phase

Output:
  - Returns a dict with keys: sections, all_tables, total_pages, language_hint
  - This raw dict is passed to normaliser.py which converts it to ParsedDocument
  - On failure, raises DoclingParserError so pipeline.py can trigger fallback
"""
import fitz  # PyMuPDF — add this at the top of the file with other imports
import tempfile
import shutil
import logging
import re
from pathlib import Path
import requests
logger = logging.getLogger(__name__)


# ─── CUSTOM EXCEPTION ─────────────────────────────────────────────────────────
# Raised when Docling fails so pipeline.py knows to trigger the fallback parser.

class DoclingParserError(Exception):
    pass


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _table_to_markdown(headers: list[str], rows: list[list[str]]) -> str:
    """
    Converts table headers + rows into a clean markdown table string.
    This markdown string is what gets embedded by Cohere in Phase 3.

    Example output:
        | Item   | Qty | Rate  |
        |--------|-----|-------|
        | Laptop | 10  | 45000 |
        | Mouse  | 10  | 500   |
    """
    if not headers and not rows:
        return ""

    # If no headers provided, use column indices as headers
    if not headers and rows:
        headers = [f"Col {i+1}" for i in range(len(rows[0]))]

    # Build header row
    header_row = "| " + " | ".join(str(h).strip() for h in headers) + " |"

    # Build separator row
    separator = "| " + " | ".join("---" for _ in headers) + " |"

    # Build data rows — pad or trim cells to match header count
    data_rows = []
    for row in rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        padded = padded[:len(headers)]
        data_rows.append("| " + " | ".join(str(c).strip() for c in padded) + " |")

    return "\n".join([header_row, separator] + data_rows)


def _detect_language(text: str) -> str:
    """
    Quick language detection from the first 2000 characters of extracted text.
    Returns an ISO 639-1 language code e.g. 'en', 'hi', 'fr'.
    Falls back to 'en' if detection fails or text is too short.
    """
    try:
        from langdetect import detect
        sample = text[:2000].strip()
        if len(sample) < 50:
            return "en"
        return detect(sample)
    except Exception:
        return "en"

def _extract_pdf_links(pdf_path: Path):

    links = []

    try:
        doc = fitz.open(str(pdf_path))

        for page in doc:

            page_links = page.get_links()

            for link in page_links:

                if "uri" in link:

                    url = link["uri"]

                    # Only keep PDF links
                    if url.lower().endswith(".pdf"):

                        links.append(url)

        doc.close()

    except Exception as e:

        logger.warning(
            f"Could not extract links from {pdf_path.name}: {e}"
        )

    return links


def _download_pdf(url: str, save_dir: Path):

    try:

        file_name = url.split("/")[-1]

        save_path = save_dir / file_name

        # Skip if already downloaded
        if save_path.exists():
            return save_path

        response = requests.get(url, timeout=30)

        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        logger.info(
            f"Downloaded linked PDF: {file_name}"
        )

        return save_path

    except Exception as e:

        logger.warning(
            f"Failed to download {url}: {e}"
        )

        return None
# ─── DOCLING PIPELINE SETUP ───────────────────────────────────────────────────

def _get_docling_pipeline():
    """
    Initialises and returns a configured Docling DocumentConverter.

    Why CPU and not GPU?
      Docling recently upgraded its default layout model to RT-DETRv2.
      This model alone needs ~5-6GB VRAM which fills the RTX 4050 6GB
      completely, leaving no room for actual page processing.
      Running on CPU is slower (~2-5 min for 60 pages) but stable.

    Pipeline options:
      - do_table_structure  = True  → TableFormer ON for table extraction
      - do_ocr              = False → all our PDFs are digital, not scanned
      - generate_page_images= False → saves memory, we don't need screenshots
    """
    try:
        # ── All Docling imports live here ─────────────────────────────────
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            AcceleratorOptions,
            AcceleratorDevice,
        )

        # ── Configure pipeline options ────────────────────────────────────
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_table_structure   = True   # TableFormer ON
        pipeline_options.do_ocr               = True  # digital PDFs only
        pipeline_options.generate_page_images = False  # saves memory
        pipeline_options.images_scale = 1.0
        # Force layout model to CPU — RT-DETRv2 is too large for 6GB VRAM
        import torch
        device = AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU
        logger.info(f"Docling initialising on device: {device.name}")

        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=4,
            device=device
        )

        # ── Build and return the converter ────────────────────────────────
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        logger.info("Docling converter built — layout on CPU, TableFormer ON, OCR OFF")
        return converter

    except ImportError as e:
        raise DoclingParserError(
            f"Docling is not installed. Run: pip install docling\nError: {e}"
        )
    except Exception as e:
        raise DoclingParserError(f"Failed to initialise Docling pipeline: {e}")


# ─── SECTION EXTRACTION ───────────────────────────────────────────────────────

def _extract_sections_from_docling(docling_doc) -> tuple[list[dict], list[dict]]:
    """
    Walks the Docling document object and builds:
      1. A nested list of section dicts (preserving document hierarchy)
      2. A flat list of all table dicts (for quick access)

    Docling represents documents as a list of elements with labels like:
      - 'section_header' → heading
      - 'text'           → body text / paragraph
      - 'table'          → table
      - 'list_item'      → bullet/numbered list item
      - 'caption'        → figure/table caption
      - 'page_header'    → page header (skipped)
      - 'page_footer'    → page footer (skipped)
    """
    sections        = []   # top-level sections (level 1 headings)
    all_tables      = []   # flat list of every table found
    table_counter   = 1
    section_counter = 1

    # Stack tracks the current open section at each heading depth
    section_stack: list[dict] = []

    def current_section() -> dict | None:
        return section_stack[-1] if section_stack else None

    def make_section(title: str, level: int, page: int) -> dict:
        nonlocal section_counter
        s = {
            "section_id": f"s_{section_counter:03d}",
            "title":      title,
            "level":      level,
            "page_start": page,
            "page_end":   page,
            "content":    "",
            "tables":     [],
            "children":   [],
        }
        section_counter += 1
        return s

    def make_table(headers, rows, page, section_title) -> dict:
        nonlocal table_counter
        md = _table_to_markdown(headers, rows)
        t = {
            "table_id":      f"t_{table_counter:03d}",
            "page_number":   page,
            "section_title": section_title,
            "headers":       headers,
            "rows":          rows,
            "raw_markdown":  md,
        }
        table_counter += 1
        return t

    def add_section(section: dict, level: int):
        """Places a new section in the correct spot in the hierarchy."""
        while len(section_stack) >= level:
            section_stack.pop()

        if section_stack:
            section_stack[-1]["children"].append(section)
        else:
            sections.append(section)

        section_stack.append(section)

    # ── Walk every element Docling found in reading order ───────────────────
    try:
        items = list(docling_doc.iterate_items())
    except Exception:
        items = []

    for item, _level in items:
        label    = getattr(item, "label", "")
        page_num = 1

        # Get page number from item's provenance
        try:
            if hasattr(item, "prov") and item.prov:
                page_num = item.prov[0].page_no
        except Exception:
            pass

        # ── HEADING → start a new section ───────────────────────────────────
        if label in ("section_header", "title"):
            heading_text  = item.text.strip() if hasattr(item, "text") else "Untitled"
            heading_level = getattr(_level, "value", 1) if _level else 1
            heading_level = max(1, min(heading_level, 3))  # clamp to 1–3

            new_section = make_section(heading_text, heading_level, page_num)
            add_section(new_section, heading_level)

            if current_section():
                current_section()["page_end"] = page_num

        # ── BODY TEXT → append to current section content ───────────────────
        elif label in ("text", "list_item", "caption"):
            text = item.text.strip() if hasattr(item, "text") else ""
            if not text:
                continue

            if label == "list_item":
                text = f"• {text}"

            if current_section():
                if current_section()["content"]:
                    current_section()["content"] += "\n\n" + text
                else:
                    current_section()["content"] = text
                current_section()["page_end"] = page_num
            else:
                # Text before any heading → create implicit intro section
                intro = make_section("Introduction", 1, page_num)
                sections.append(intro)
                section_stack.append(intro)
                current_section()["content"] = text

        # ── TABLE → extract and attach to current section ───────────────────
        elif label == "table":
            headers = []
            rows    = []

            try:
                table_data = item.data
                if table_data and hasattr(table_data, "grid"):
                    grid = table_data.grid
                    if grid:
                        first_row = [cell.text.strip() for cell in grid[0]]
                        looks_like_header = all(
                            len(c) < 60 and not re.match(r"^\d+[\.,]?\d*$", c)
                            for c in first_row if c
                        )
                        if looks_like_header:
                            headers = first_row
                            rows    = [
                                [cell.text.strip() for cell in row]
                                for row in grid[1:]
                            ]
                        else:
                            rows = [
                                [cell.text.strip() for cell in row]
                                for row in grid
                            ]
            except Exception as e:
                logger.warning(f"Could not extract table data at page {page_num}: {e}")

            sec_title  = current_section()["title"] if current_section() else "Unknown"
            table_dict = make_table(headers, rows, page_num, sec_title)

            if current_section():
                current_section()["tables"].append(table_dict)
                current_section()["page_end"] = page_num

            all_tables.append(table_dict)

        # ── PAGE HEADER / FOOTER → skip entirely ────────────────────────────
        elif label in ("page_header", "page_footer"):
            continue

    return sections, all_tables


# ─── MAIN PARSE FUNCTION ──────────────────────────────────────────────────────
def _split_pdf_to_chunks(pdf_path: Path, chunk_size: int = 10) -> list[Path]:
    """
    Splits a large PDF into smaller temporary PDFs of chunk_size pages each.
    Temporary files are saved to a temp directory and deleted after processing.

    Why chunking?
      Docling renders each page into RAM as an image before processing.
      On low-RAM systems this exhausts memory on large documents.
      Processing 10 pages at a time keeps RAM usage flat and stable.
    """
    doc = fitz.open(str(pdf_path))
    chunks = []
    temp_dir = Path(tempfile.mkdtemp())

    for start in range(0, len(doc), chunk_size):
        end = min(start + chunk_size, len(doc))
        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
        chunk_path = temp_dir / f"chunk_{start:04d}_{end:04d}.pdf"
        chunk_doc.save(str(chunk_path))
        chunk_doc.close()
        chunks.append((chunk_path, start + 1))  # (path, page_offset for logging)

    doc.close()
    logger.info(f"Split PDF into {len(chunks)} chunks of up to {chunk_size} pages each")
    return chunks, temp_dir

# def parse_with_docling(pdf_path: str | Path) -> dict:
#     """
#     Main entry point for the Docling parser.
#
#     Args:
#         pdf_path: Path to the PDF file to parse.
#
#     Returns:
#         A raw dict with keys:
#             - sections      : list of nested section dicts
#             - all_tables    : flat list of all table dicts
#             - total_pages   : int
#             - language_hint : str (ISO 639-1 code)
#
#     Raises:
#         DoclingParserError: If Docling fails to initialise or parse.
#                             pipeline.py catches this and triggers the fallback.
#     """
#     pdf_path = Path(pdf_path)
#
#     if not pdf_path.exists():
#         raise DoclingParserError(f"PDF file not found: {pdf_path}")
#
#     if not pdf_path.suffix.lower() == ".pdf":
#         raise DoclingParserError(f"Expected a .pdf file, got: {pdf_path.suffix}")
#
#     logger.info(f"Docling parser starting on: {pdf_path.name}")
#
#     # ── Step 1: Initialise Docling pipeline ───────────────────────────────────
#     converter = _get_docling_pipeline()
#
#     # ── Step 2: Run Docling on the PDF ────────────────────────────────────────
#     try:
#         logger.info("Running Docling conversion (this may take a few minutes on CPU)...")
#         result      = converter.convert(str(pdf_path))
#         docling_doc = result.document
#         logger.info("Docling conversion complete.")
#     except Exception as e:
#         raise DoclingParserError(f"Docling failed to convert PDF: {e}")
#
#     # ── Step 3: Get total page count ──────────────────────────────────────────
#     try:
#         total_pages = len(result.pages) if hasattr(result, "pages") else 0
#         if total_pages == 0:
#             total_pages = len(docling_doc.pages) if hasattr(docling_doc, "pages") else 1
#         logger.info(f"Total pages detected: {total_pages}")
#     except Exception:
#         total_pages = 1
#
#     # ── Step 4: Extract sections and tables ───────────────────────────────────
#     logger.info("Extracting sections and tables from Docling output...")
#     sections, all_tables = _extract_sections_from_docling(docling_doc)
#     logger.info(f"Extracted {len(sections)} top-level sections, {len(all_tables)} tables.")
#
#     # ── Step 5: Detect document language ─────────────────────────────────────
#     sample_text = ""
#     for section in sections[:5]:
#         sample_text += section.get("content", "")
#         if len(sample_text) >= 2000:
#             break
#     language_hint = _detect_language(sample_text)
#     logger.info(f"Detected language: {language_hint}")
#
#     return {
#         "sections":      sections,
#         "all_tables":    all_tables,
#         "total_pages":   total_pages,
#         "language_hint": language_hint,
#     }

def parse_with_docling(pdf_path: str | Path, visited_links: set | None = None) -> dict:
    """
    Main entry point for the Docling parser.
    Processes PDF in chunks of 10 pages to avoid RAM exhaustion.

    Args:
        pdf_path: Path to the PDF file to parse.

    Returns:
        A raw dict with keys:
            - sections      : list of nested section dicts
            - all_tables    : flat list of all table dicts
            - total_pages   : int
            - language_hint : str (ISO 639-1 code)

    Raises:
        DoclingParserError: If Docling fails to initialise or parse.
    """
    pdf_path = Path(pdf_path)
    if visited_links is None:
        visited_links = set()
    visited_links.add(str(pdf_path))
    if not pdf_path.exists():
        raise DoclingParserError(f"PDF file not found: {pdf_path}")

    if not pdf_path.suffix.lower() == ".pdf":
        raise DoclingParserError(f"Expected a .pdf file, got: {pdf_path.suffix}")

    logger.info(f"Docling parser starting on: {pdf_path.name}")

    # ── Step 1: Get true page count before splitting ──────────────────────────
    try:
        full_doc    = fitz.open(str(pdf_path))
        total_pages = full_doc.page_count
        full_doc.close()
        logger.info(f"Total pages: {total_pages}")
    except Exception:
        total_pages = 1

    # ── Step 2: Initialise Docling pipeline ───────────────────────────────────
    converter = _get_docling_pipeline()
    # ── Step 3: Extract hyperlinks ─────────────────────

    links = _extract_pdf_links(pdf_path)
    logger.info(
        f"Found {len(links)} PDF hyperlinks"
    )
    downloaded_pdfs = []

    for url in links:

        downloaded = _download_pdf(
            url,
            pdf_path.parent
        )

        if downloaded:

            if str(downloaded) in visited_links:
                continue

            visited_links.add(str(downloaded))

            downloaded_pdfs.append(downloaded)


    # ── Step 3: Split PDF into 10-page chunks ─────────────────────────────────
    chunks, temp_dir = _split_pdf_to_chunks(pdf_path, chunk_size=10)

    # ── Step 4: Process each chunk and merge results ──────────────────────────
    all_sections : list[dict] = []
    all_tables   : list[dict] = []

    try:
        for i, (chunk_path, page_offset) in enumerate(chunks):
            logger.info(
                f"Processing chunk {i + 1}/{len(chunks)} "
                f"(pages {page_offset}–{page_offset + 9})..."
            )
            try:
                result      = converter.convert(str(chunk_path))
                docling_doc = result.document
                sections, tables = _extract_sections_from_docling(docling_doc)
                for sec in sections:
                    sec["source_pdf"] = pdf_path.name
                all_sections.extend(sections)
                all_tables.extend(tables)
                logger.info(
                    f"Chunk {i + 1} done — "
                    f"{len(sections)} sections, {len(tables)} tables"
                )
            except Exception as e:
                # One bad chunk should NOT kill the whole pipeline
                # Log the error and continue with remaining chunks
                logger.warning(
                    f"Chunk {i + 1} failed — skipping. Error: {e}"
                )
                continue

    finally:
        # Always clean up temp files even if something crashes midway
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("Temporary chunk files cleaned up")
    # ── Step 5: Parse linked PDFs ─────────────────────────────

    for linked_pdf in downloaded_pdfs:

        if str(linked_pdf) == str(pdf_path):
            logger.info(
                f"Skipping already parsed PDF: {linked_pdf.name}"
            )

            continue

        visited_links.add(str(linked_pdf))

        logger.info(
            f"Parsing linked PDF: {linked_pdf.name}"
        )

        try:

            linked_output = parse_with_docling(
                linked_pdf,
                visited_links=visited_links
            )

            all_sections.extend(
                linked_output["sections"]
            )

            all_tables.extend(
                linked_output["all_tables"]
            )

            logger.info(
                f"Linked PDF merged: {linked_pdf.name}"
            )

        except Exception as e:

            logger.warning(
                f"Failed parsing linked PDF "
                f"{linked_pdf.name}: {e}"
            )


    # ── Step 5: Detect language from first few sections ───────────────────────
    sample_text = ""
    for section in all_sections[:5]:
        sample_text += section.get("content", "")
        if len(sample_text) >= 2000:
            break
    language_hint = _detect_language(sample_text)
    logger.info(f"Detected language: {language_hint}")

    logger.info(
        f"Docling complete — {total_pages} pages | "
        f"{len(all_sections)} sections | {len(all_tables)} tables"

    )

    return {
        "sections"     : all_sections,
        "all_tables"   : all_tables,
        "total_pages"  : total_pages,
        "language_hint": language_hint,
    }
