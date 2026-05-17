"""
compile_proposal_node.py

Changes vs previous:
- Company name threaded through from state for personalised headings.
- Paragraph mode: each section gets a proper heading, content split by
  sentence/paragraph is cleaned (no double-blank lines).
- Table mode: unchanged logic but header styling improved.
- Added a cover note paragraph at the top of the document.
"""

import logging
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)


def _set_cell_background(cell, hex_color: str):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def _style_header_row(row):
    for cell in row.cells:
        _set_cell_background(cell, "1F4E79")
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def _style_subheader_row(row):
    for cell in row.cells:
        _set_cell_background(cell, "D6E4F0")
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
        if "offered" in joined or "required" in joined or "specification" in joined or "item no" in joined:
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
    return fallback if fallback < num_cols else num_cols - 1


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


def _add_cover_paragraph(doc: Document, company_name: str, tender_title: str):
    """Add a professional cover note at the top of the proposal."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(
        f"This proposal is submitted by {company_name} in response to the tender for "
        f"{tender_title}. The information contained herein is accurate and complete to the "
        "best of our knowledge. We confirm our unconditional acceptance of all terms and "
        "conditions stipulated in the tender document and commit to fulfilling all "
        "requirements within the specified timelines and quality standards."
    )
    run.font.size = Pt(11)
    doc.add_paragraph("")


def compile_proposal_node(state: dict) -> dict:
    logger.info("Compiling proposal document")

    generated_sections = state.get("generated_sections") or []
    mode = state.get("mode", "paragraph")
    proposal_json = state.get("proposal_json", {})
    raw_sections = state.get("raw_sections", proposal_json.get("sections", []))
    company_name = state.get("company_name", "the Bidder")
    tender_title = proposal_json.get("title", "the above-mentioned tender")

    doc = Document()

    # ── Cover heading ──────────────────────────────────────────────────────
    title_para = doc.add_heading("TENDER PROPOSAL RESPONSE", level=1)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run(tender_title.upper())
    subtitle_run.bold = True
    subtitle_run.font.size = Pt(12)

    doc.add_paragraph("")
    company_para = doc.add_paragraph()
    company_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c_run = company_para.add_run(f"Submitted by: {company_name}")
    c_run.bold = True
    c_run.font.size = Pt(11)

    doc.add_paragraph("")
    _add_cover_paragraph(doc, company_name, tender_title)

    # ── TABLE MODE ─────────────────────────────────────────────────────────
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

                if header_idx >= len(rows):
                    logger.warning("Header index %s outside rows length %s; resetting", header_idx, len(rows))
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

                # Style rows
                for row_idx, word_row in enumerate(word_table.rows):
                    row_metadata = _row_metadata_for(table, row_idx, len(rows))
                    if row_idx <= header_idx:
                        _style_header_row(word_row)
                    elif row_metadata.get("is_subheader"):
                        _style_subheader_row(word_row)

                doc.add_paragraph("")

    # ── PARAGRAPH MODE ─────────────────────────────────────────────────────
    else:
        if not generated_sections:
            logger.warning("No generated sections; writing fallback")
            doc.add_paragraph(
                f"{company_name} submits this proposal in full compliance with the tender requirements. "
                "Detailed technical and commercial information will be provided as part of the complete bid submission."
            )

        for section in generated_sections:
            title = section.get("title") or "General"
            content = section.get("content") or (
                f"{company_name} confirms its capability and commitment to fulfil all requirements "
                f"under the {title} section. Details available on request."
            )

            heading = doc.add_heading(title, level=2)
            heading.alignment = WD_ALIGN_PARAGRAPH.LEFT

            # Split on double newlines or single newlines into separate paragraphs
            paragraphs = [p.strip() for p in re.split(r"\n{2,}|\n", content) if p.strip()]
            for para_text in paragraphs:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                run = p.add_run(para_text)
                run.font.size = Pt(11)

            doc.add_paragraph("")

    output_file = state.get("output_file") or "generated_proposal.docx"
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    logger.info("Proposal saved: %s", output_path)

    state["output_file"] = str(output_path)
    return state


import re  # noqa: E402  (needed for paragraph splitting in paragraph mode)
