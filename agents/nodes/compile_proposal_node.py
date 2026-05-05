"""
compile_proposal_node.py

Rebuilds the proposal document. In table mode it preserves the original table
shape from the tender/template and fills only the "Specification offered" cells.
"""

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


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
        print("WARNING: invalid table object in compile; expected dict")
        return []
    rows = table.get("rows") or table.get("sample_rows") or []
    return [[str(cell).strip() for cell in row] for row in rows if row]


def _find_header_index(rows: list[list[str]]) -> int:
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


def compile_proposal_node(state: dict) -> dict:
    print("\nCompiling proposal document...\n")

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
                header_idx = _find_header_index(rows)
                print("DEBUG compile table rows length:", len(rows))
                print("DEBUG compile accessing header index:", header_idx)
                if header_idx >= len(rows):
                    print(f"WARNING: compile header index {header_idx} outside rows length {len(rows)}")
                    header_idx = 0
                header = rows[header_idx]
                required_col = _find_required_col(header, rows)
                offered_col = _find_offered_col(header, required_col, num_cols)
                notes_col = _find_notes_col(header, offered_col, num_cols)

                word_table = doc.add_table(rows=0, cols=num_cols)
                word_table.style = "Table Grid"

                for row_idx, row_data in enumerate(rows):
                    word_row = word_table.add_row()

                    for col_idx in range(num_cols):
                        cell_value = row_data[col_idx] if col_idx < len(row_data) else ""
                        cell = word_row.cells[col_idx]

                        if row_idx <= header_idx:
                            cell.text = str(cell_value)
                        elif col_idx == offered_col:
                            key = (sec_idx, tbl_idx, row_idx)
                            generated = fill_map.get(key, {})
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
            print("WARNING: No generated sections available; writing fallback paragraph")
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

    print(f"Proposal saved as: {output_file}")

    state["output_file"] = output_file
    return state
