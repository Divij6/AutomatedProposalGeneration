"""
json_builder.py

Converts extracted proposal
into structured JSON format.
"""

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

                if headers:
                    first_row = [cell.strip().lower() for cell in rows[0]] if rows else []
                    header_row = [cell.strip().lower() for cell in headers]
                    if first_row != header_row:
                        rows = [headers] + rows

                section_data["tables"].append({

                    "headers": headers,

                    "rows": rows,

                    "sample_rows": rows[:2],

                    "row_count": len(rows)

                })

            proposal_json["sections"].append(
                section_data
            )

            if sec.children:
                walk_sections(sec.children)

    walk_sections(parsed_doc.sections)

    return proposal_json
