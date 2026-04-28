"""
extractor.py

Extracts proposal-related pages
into a separate PDF.
"""

import fitz
from pathlib import Path
import uuid

def extract_proposal_pdf(
        original_pdf_path,
        proposal_sections,
        parsed_doc,
        output_dir="extracted_proposals"
):

    import fitz
    from pathlib import Path
    import uuid

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    doc = fitz.open(original_pdf_path)

    new_pdf = fitz.open()

    used_pages = set()

    max_pages = len(doc)

    for sec in proposal_sections:

        start_page = sec.page_start - 1

        current_page = start_page

        empty_table_count = 0

        while current_page < max_pages:

            # Check if this page contains tables
            tables_on_page = []

            for section in parsed_doc.sections:

                if (
                    section.page_start - 1
                    <= current_page
                    <= section.page_end - 1
                ):

                    tables_on_page.extend(
                        section.tables
                    )

            if tables_on_page:

                empty_table_count = 0

            else:

                empty_table_count += 1

            # Stop if no tables for 2 pages
            if empty_table_count >= 2:

                break

            if current_page not in used_pages:

                new_pdf.insert_pdf(
                    doc,
                    from_page=current_page,
                    to_page=current_page
                )

                used_pages.add(current_page)

            current_page += 1

    proposal_file_name = (
        f"proposal_{uuid.uuid4().hex[:8]}.pdf"
    )

    proposal_path = output_dir / proposal_file_name

    new_pdf.save(proposal_path)

    doc.close()
    new_pdf.close()

    return proposal_path