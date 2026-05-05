"""
load_sections_node.py

Responsibilities:
1. Pull sections from proposal_json.
2. Detect whether the response format is table or paragraph.
3. For table mode, flatten every fillable row into one generation item.
4. Preserve raw sections so compile_proposal_node can rebuild the original tables.
"""


def _table_rows(table: dict) -> list[list[str]]:
    if not isinstance(table, dict):
        print("WARNING: invalid table object; expected dict")
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

            header_idx = _find_header_index(rows)
            print("DEBUG table rows length:", len(rows))
            print("DEBUG accessing table header index:", header_idx)
            if header_idx >= len(rows):
                print(f"WARNING: header index {header_idx} outside rows length {len(rows)}")
                continue
            header = rows[header_idx]
            required_col = _find_required_col(header, rows)

            for row_idx, row in enumerate(rows):
                if row_idx <= header_idx or len(row) <= required_col:
                    continue

                cell_text = str(row[required_col]).strip()
                if not cell_text:
                    continue

                items.append({
                    "title": cell_text,
                    "sec_index": sec_idx,
                    "tbl_index": tbl_idx,
                    "row_index": row_idx,
                    "required_col": required_col,
                    "header_row_index": header_idx,
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
    print("\nLoading proposal sections...\n")

    proposal_json = state.get("proposal_json")
    if not proposal_json:
        print("WARNING: No proposal_json found in state")
        state["proposal_sections"] = []
        state["raw_sections"] = []
        state["status"] = "no_proposal_json"
        state["section_index"] = 0
        return state

    sections = proposal_json.get("sections", [])
    if not sections:
        print("WARNING: No sections found inside proposal_json")
        state["proposal_sections"] = []
        state["raw_sections"] = []
        state["status"] = "no_sections"
        state["section_index"] = 0
        return state

    mode = detect_table_mode(sections)
    state["mode"] = mode

    print(f"Detected mode: {mode}")

    if mode == "table":
        table_items = _extract_table_items(sections)

        if not table_items:
            print("WARNING: Table mode detected but no rows extracted - falling back to paragraph mode")
            state["mode"] = "paragraph"
            state["proposal_sections"] = sections
        else:
            state["proposal_sections"] = table_items
            print(f"Extracted {len(table_items)} table rows to fill")
    else:
        state["proposal_sections"] = sections
        print(f"Loaded {len(sections)} paragraph sections")

    state["raw_sections"] = sections
    state["status"] = "sections_loaded"
    state["section_index"] = 0

    return state
