"""
Extract detected proposal-format sections into one navigable PDF.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)


def _walk_section_pages(section, total_pages: int) -> set[int]:
    pages = set()
    page_start = max(1, int(getattr(section, "page_start", 1) or 1))
    page_end = min(total_pages, int(getattr(section, "page_end", page_start) or page_start))

    for page_number in range(page_start, page_end + 1):
        pages.add(page_number - 1)

    expanded_page = page_end + 1
    if expanded_page <= total_pages:
        pages.add(expanded_page - 1)

    for child in getattr(section, "children", []) or []:
        pages.update(_walk_section_pages(child, total_pages))

    return pages


def extract_proposal_pdf(
    original_pdf_path,
    proposal_sections,
    parsed_doc,
    output_dir="extracted_proposals",
) -> Path | None:
    if not proposal_sections:
        logger.warning("No proposal sections supplied; extracted PDF was not created")
        return None

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    doc = fitz.open(original_pdf_path)
    new_pdf = fitz.open()

    try:
        total_pages = len(doc)
        collected_pages: set[int] = set()
        section_pages: list[tuple[object, set[int]]] = []

        for section in proposal_sections:
            pages = _walk_section_pages(section, total_pages)
            valid_pages = set()
            for page_index in pages:
                if 0 <= page_index < total_pages:
                    valid_pages.add(page_index)
                else:
                    logger.warning(
                        "Skipping out-of-bounds proposal page index %s for section %s",
                        page_index,
                        getattr(section, "title", ""),
                    )

            if valid_pages:
                section_pages.append((section, valid_pages))
                collected_pages.update(valid_pages)

        sorted_pages = sorted(collected_pages)
        if not sorted_pages:
            logger.warning("No valid proposal pages found; extracted PDF was not created")
            return None

        output_page_by_source = {}
        for output_index, source_page in enumerate(sorted_pages):
            new_pdf.insert_pdf(doc, from_page=source_page, to_page=source_page)
            output_page_by_source[source_page] = output_index + 1

        toc = []
        for section, pages in section_pages:
            section_output_pages = [
                output_page_by_source[page] for page in sorted(pages) if page in output_page_by_source
            ]
            if not section_output_pages:
                continue
            title = getattr(section, "title", "") or "Proposal Format"
            toc.append([1, str(title), min(section_output_pages)])

        if toc:
            new_pdf.set_toc(toc)

        proposal_path = output_dir / f"proposal_{uuid.uuid4().hex[:8]}.pdf"
        new_pdf.save(proposal_path)
        return proposal_path
    finally:
        doc.close()
        new_pdf.close()
