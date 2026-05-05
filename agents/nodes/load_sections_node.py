"""
load_sections_node.py

Responsibilities:
1. Pull sections from proposal_json.
2. Detect whether the response format is table or paragraph.
3. For table mode, flatten every fillable row into one generation item.
4. Preserve raw sections so compile_proposal_node can rebuild the original tables.
"""

import logging

logger = logging.getLogger(__name__)


def _normalise_row(row: list[str]) -> list[str]:
    return [str(cell).strip().lower() for cell in row]


def _table_rows(table: dict) -> list[list[str]]:
    if not isinstance(table, dict):
        logger.warning("Invalid table object; expected dict")
        return []
    rows = table.get("rows") or table.get("sample_rows") or []
    rows = [[str(cell).strip() for cell in row] for row in rows if row]
    headers = [str(cell).strip() for cell in table.get("headers", []) or []]
    if headers and (not rows or _normalise_row(rows[0]) != _normalise_row(headers)):
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

    # Most tender response tables are: item number, requirement, offered value, notes.
    if rows and max(len(row) for row in rows) >= 3:
        return 1
    return 0


def _extract_table_items(sections: list) -> list:
    """
    Walk all sections -> all tables -> all rows.
    Return one item per non-empty required/specification cell.
    """
    items = []

    for sec_idx, section in enumerate(sections):
        tables = section.get("tables", [])
        for tbl_idx, table in enumerate(tables):
            rows = _table_rows(table)
            if not rows:
                continue

            header_idx = _find_header_index(rows, table)
            logger.debug("Table rows length: %s", len(rows))
            logger.debug("Using table header index: %s", header_idx)
            if header_idx >= len(rows):
                logger.warning("Header index %s outside rows length %s", header_idx, len(rows))
                continue
            header = rows[header_idx]
            if isinstance(table.get("fill_col_index"), int):
                required_col = table["fill_col_index"]
            else:
                required_col = _find_required_col(header, rows)
            notes_col_index = table.get("notes_col_index", None)
            is_synthesised = table.get("is_synthesised") is True

            for row_idx, row in enumerate(rows):
                if row_idx <= header_idx:
                    continue

                cell_text = str(row[required_col]).strip() if len(row) > required_col else ""
                if not cell_text:
                    if is_synthesised and row:
                        cell_text = str(row[0]).strip()
                    else:
                        left_cells = [str(cell).strip() for cell in row[:required_col] if str(cell).strip()]
                        cell_text = left_cells[-1] if left_cells else ""
                if not cell_text:
                    continue

                items.append({
                    "title": cell_text,
                    "sec_index": sec_idx,
                    "tbl_index": tbl_idx,
                    "row_index": row_idx,
                    "required_col": required_col,
                    "fill_col_index": table.get("fill_col_index"),
                    "header_row_index": header_idx,
                    "notes_col_index": notes_col_index,
                    "is_form_field": is_synthesised,
                    "original_row": row,
                })

    return items


def detect_table_mode(sections: list) -> str:
    """Return 'table' if any section contains at least one table with data rows."""
    for section in sections:
        for table in section.get("tables", []):
            rows = _table_rows(table)
            if len(rows) >= 2:
                return "table"
    return "paragraph"


def load_sections_node(state: dict) -> dict:
    logger.info("Loading proposal sections")

    proposal_json = state.get("proposal_json")
    if not proposal_json:
        logger.warning("No proposal_json found in state")
        state["proposal_sections"] = []
        state["raw_sections"] = []
        state["status"] = "no_proposal_json"
        state["section_index"] = 0
        return state

    sections = proposal_json.get("sections", [])
    if not sections:
        logger.warning("No sections found inside proposal_json")
        state["proposal_sections"] = []
        state["raw_sections"] = []
        state["status"] = "no_sections"
        state["section_index"] = 0
        return state

    mode = detect_table_mode(sections)
    state["mode"] = mode

    logger.info("Detected proposal mode: %s", mode)

    if mode == "table":
        table_items = _extract_table_items(sections)

        if not table_items:
            logger.warning("Table mode detected but no rows extracted - falling back to paragraph mode")
            state["mode"] = "paragraph"
            state["proposal_sections"] = sections
        else:
            state["proposal_sections"] = table_items
            logger.info("Extracted %s table rows to fill", len(table_items))
    else:
        state["proposal_sections"] = sections
        logger.info("Loaded %s paragraph sections", len(sections))

    state["raw_sections"] = sections
    state["status"] = "sections_loaded"
    state["section_index"] = 0

    return state
