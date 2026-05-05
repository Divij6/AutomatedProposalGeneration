"""
compile_proposal_node.py

Rebuilds the proposal document. In table mode it preserves the original table
shape from the tender/template and fills only the "Specification offered" cells.
"""

import logging

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

logger = logging.getLogger(__name__)


def _set_cell_background(cell, hex_color: str):
    """Set a table cell's background shading."""
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def _style_header_row(row):
    """Make header row bold with light grey background."""
    for cell in row.cells:
        _set_cell_background(cell, "D9D9D9")
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True


def _table_rows(table: dict) -> list[list[str]]:
    if not isinstance(table, dict):
        logger.warning("Invalid table object in compile; expected dict")
        return []
    rows = table.get("rows") or table.get("sample_rows") or []
    rows = [[str(cell).strip() for cell in row] for row in rows if row]
    headers = [str(cell).strip() for cell in table.get("headers", []) or []]
    if headers:
        first_row = [str(cell).strip().lower() for cell in rows[0]] if rows else []
        header_row = [str(cell).strip().lower() for cell in headers]
        if first_row != header_row:
            rows = [headers] + rows
    return rows


def _find_header_index(rows: list[list[str]], table: dict | None = None) -> int:
    if isinstance(table, dict) and isinstance(table.get("header_row_index"), int):
        return table["header_row_index"]

    for idx, row in enumerate(rows[:3]):
        joined = " ".join(str(cell).lower() for cell in row)
        if (
            "offered" in joined
            or "required" in joined
            or "specification" in joined
            or "item no" in joined
        ):
            return idx
    return 0


def _find_required_col(header: list[str], rows: list[list[str]]) -> int:
    for i, cell in enumerate(header):
        text = str(cell).lower()
        if "required" in text or ("specification" in text and "offered" not in text):
            return i

    if rows and max(len(row) for row in rows) >= 3:
        return 1
    return 0


def _find_offered_col(header: list[str], required_col: int, num_cols: int) -> int:
    for i, cell in enumerate(header):
        if "offered" in str(cell).lower():
            return i

    fallback = required_col + 1
    if fallback < num_cols:
        return fallback
    return num_cols - 1


def _find_notes_col(header: list[str], offered_col: int, num_cols: int) -> int | None:
    for i, cell in enumerate(header):
        text = str(cell).lower()
        if "note" in text or "remark" in text or "documentation" in text or "ref" in text:
            return i

    fallback = offered_col + 1
    if fallback < num_cols:
        return fallback
    return None


def _row_metadata_for(table: dict, row_idx: int, row_count: int) -> dict:
    metadata = table.get("row_metadata") or []
    if not isinstance(metadata, list):
        return {}
    if row_idx < len(metadata) and isinstance(metadata[row_idx], dict):
        return metadata[row_idx]
    if len(metadata) == row_count - 1 and row_idx > 0 and isinstance(metadata[row_idx - 1], dict):
        return metadata[row_idx - 1]
    return {}


def compile_proposal_node(state: dict) -> dict:
    logger.info("Compiling proposal document")

    generated_sections = state.get("generated_sections") or []
    mode = state.get("mode", "paragraph")
    proposal_json = state.get("proposal_json", {})
    raw_sections = state.get("raw_sections", proposal_json.get("sections", []))

    doc = Document()
    doc.add_heading("Tender Proposal", level=1)

    if mode == "table":
        fill_map = {}
        for gen in generated_sections:
            key = (gen.get("sec_index"), gen.get("tbl_index"), gen.get("row_index"))
            fill_map[key] = {
                "offered": gen.get("offered_content") or gen.get("content", ""),
                "notes": gen.get("notes_content", ""),
                "is_form_field": gen.get("is_form_field") is True,
            }

        for sec_idx, section in enumerate(raw_sections):
            sec_title = section.get("title", "")
            if sec_title:
                doc.add_heading(sec_title, level=2)

            for para_text in section.get("paragraphs", []):
                if para_text.strip():
                    doc.add_paragraph(para_text)

            for tbl_idx, table in enumerate(section.get("tables", [])):
                rows = _table_rows(table)
                if not rows:
                    continue

                num_cols = max(len(row) for row in rows)
                header_idx = _find_header_index(rows, table)
                logger.debug("Compile table rows length: %s", len(rows))
                logger.debug("Compile using header index: %s", header_idx)
                if header_idx >= len(rows):
                    logger.warning("Compile header index %s outside rows length %s", header_idx, len(rows))
                    header_idx = 0
                header = rows[header_idx]
                required_col = _find_required_col(header, rows)
                offered_col = (
                    table.get("fill_col_index")
                    if isinstance(table.get("fill_col_index"), int)
                    else _find_offered_col(header, required_col, num_cols)
                )
                notes_col = (
                    table.get("notes_col_index")
                    if isinstance(table.get("notes_col_index"), int)
                    else _find_notes_col(header, offered_col, num_cols)
                )
                offered_col = min(max(offered_col, 0), num_cols - 1)
                if notes_col is not None and not 0 <= notes_col < num_cols:
                    notes_col = None

                word_table = doc.add_table(rows=0, cols=num_cols)
                word_table.style = "Table Grid"

                for row_idx, row_data in enumerate(rows):
                    word_row = word_table.add_row()
                    row_metadata = _row_metadata_for(table, row_idx, len(rows))
                    is_subheader = row_metadata.get("is_subheader") is True

                    for col_idx in range(num_cols):
                        cell_value = row_data[col_idx] if col_idx < len(row_data) else ""
                        cell = word_row.cells[col_idx]

                        if is_subheader:
                            cell.text = str(cell_value) if cell_value else ""
                            _set_cell_background(cell, "EFEFEF")
                        elif row_idx <= header_idx:
                            cell.text = str(cell_value)
                        elif col_idx == offered_col:
                            key = (sec_idx, tbl_idx, row_idx)
                            generated = fill_map.get(key, {})
                            if generated.get("is_form_field"):
                                cell.text = generated.get("offered", "")
                            else:
                                cell.text = generated.get("offered") or (str(cell_value) if cell_value else "")
                        elif notes_col is not None and col_idx == notes_col:
                            key = (sec_idx, tbl_idx, row_idx)
                            generated = fill_map.get(key, {})
                            cell.text = generated.get("notes") or (str(cell_value) if cell_value else "")
                        else:
                            cell.text = str(cell_value) if cell_value else ""

                if word_table.rows and header_idx < len(word_table.rows):
                    _style_header_row(word_table.rows[header_idx])

                doc.add_paragraph("")

    else:
        if not generated_sections:
            logger.warning("No generated sections available; writing fallback paragraph")
            doc.add_paragraph("No proposal sections were generated.")

        for section in generated_sections:
            title = section.get("title") or "Untitled section"
            content = section.get("content") or "Details available on request."

            doc.add_heading(title, level=2)
            for para in content.split("\n"):
                if para.strip():
                    doc.add_paragraph(para)

    output_file = "generated_proposal.docx"
    doc.save(output_file)

    logger.info("Proposal saved as: %s", output_file)

    state["output_file"] = output_file
    return state
