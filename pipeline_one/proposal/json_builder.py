"""
json_builder.py

Converts extracted proposal
into structured JSON format.
"""

import logging

logger = logging.getLogger(__name__)


def _normalise_row(row: list[str]) -> list[str]:
    return [str(cell).strip().lower() for cell in row]


def _is_empty_row(row: list[str]) -> bool:
    return all(not str(cell).strip() for cell in row)


def build_proposal_json(parsed_doc):
    """
    Convert parsed proposal into JSON structure.

    Args:
        parsed_doc: ParsedDocument

    Returns:
        JSON dict
    """

    proposal_json = {

        "sections": []

    }

    def walk_sections(section_list):

        for sec in section_list:

            section_data = {

                "title": sec.title,

                "page_start": sec.page_start,

                "page_end": sec.page_end,

                "text_preview": sec.content[:200],

                "tables": []

            }

            # Add full table structure. The generation pipeline must see every
            # row; a two-row sample is useful for previews but cannot fill a bid.
            for table in sec.tables:
                rows = [[str(cell) for cell in row] for row in table.rows]
                headers = [str(header) for header in table.headers]

                rows = [row for row in rows if not _is_empty_row(row)]

                if not headers and rows:
                    headers = rows[0]
                    rows = rows[1:]
                    logger.debug("Inferred headers from first row in section: %s", sec.title)

                if headers and rows:
                    first_row_normalised = _normalise_row(rows[0])
                    header_normalised = _normalise_row(headers)
                    if first_row_normalised == header_normalised:
                        rows = rows[1:]
                        logger.debug("Removed duplicate header row from table in section: %s", sec.title)

                section_data["tables"].append({

                    "headers": headers,

                    "rows": rows,

                    "sample_rows": rows[:2],

                    "row_count": len(rows),

                    "source_section_title": sec.title,

                    "source_page_start": sec.page_start,

                    "source_page_end": sec.page_end

                })

            proposal_json["sections"].append(
                section_data
            )

            if sec.children:
                walk_sections(sec.children)

    walk_sections(parsed_doc.sections)

    return proposal_json
