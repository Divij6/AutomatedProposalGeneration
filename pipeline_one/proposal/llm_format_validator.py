"""
LLM-backed proposal JSON validation and normalisation.
"""

from __future__ import annotations

import json
import logging
import os
import re
from copy import deepcopy

from dotenv import load_dotenv
try:
    from groq import Groq
except Exception:  # pragma: no cover - handled at runtime for graceful fallback
    Groq = None

logger = logging.getLogger(__name__)

load_dotenv()


SYSTEM_PROMPT = (
    "You are a document structure analyst specialising in government and "
    "commercial tender proposal formats. You will receive a JSON object "
    "representing tables extracted from a tender document. Your job is to "
    "validate and normalise every table so that a generation AI can reliably "
    "fill in the bidder's response column without any ambiguity."
)


def clean_llm_json(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(
        r"```(?:json)?\s*(.*?)```",
        r"\1",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return cleaned.strip()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _is_empty_row(row: list) -> bool:
    return all(not str(cell).strip() for cell in row)


def _find_header_index(rows: list[list[str]], headers: list[str]) -> int:
    header_markers = (
        "item",
        "sr",
        "description",
        "required",
        "offered",
        "offer",
        "bidder",
        "compliance",
        "remarks",
        "quantity",
        "rate",
        "amount",
    )
    if headers:
        return 0
    for idx, row in enumerate(rows[:5]):
        joined = _norm(" ".join(str(cell) for cell in row))
        non_empty = [cell for cell in row if str(cell).strip()]
        if len(non_empty) > 1 and any(marker in joined for marker in header_markers):
            return idx
    return 0


def _find_fill_col(headers: list[str]) -> int:
    explicit_markers = (
        "specification offered",
        "our offer",
        "offered value",
        "bidder's response",
        "bidders response",
        "bidder response",
        "to be filled",
        "vendor's offer",
        "vendors offer",
        "compliance",
    )
    for idx, header in enumerate(headers):
        text = _norm(header)
        if any(marker in text for marker in explicit_markers):
            return idx

    for idx, header in enumerate(headers):
        text = _norm(header)
        if "specification required" in text or "description" in text or "required" in text:
            return min(idx + 1, max(len(headers) - 1, 0))

    return 1 if len(headers) > 1 else 0


def _find_notes_col(headers: list[str], fill_col: int) -> int | None:
    markers = ("remarks", "notes", "documentation", "reference", "comments", "deviation")
    for idx, header in enumerate(headers):
        if idx == fill_col:
            continue
        if any(marker in _norm(header) for marker in markers):
            return idx
    return None


def _row_metadata(rows: list[list[str]]) -> list[dict]:
    metadata = []
    for row in rows:
        non_empty = [str(cell).strip() for cell in row if str(cell).strip()]
        metadata.append({"is_subheader": len(non_empty) == 1 and len(row) > 1})
    return metadata


def _ensure_table_metadata(proposal_json: dict) -> dict:
    normalised = deepcopy(proposal_json)
    for section in normalised.get("sections", []):
        for table in section.get("tables", []) or []:
            rows = table.get("rows") or []
            rows = [[str(cell) for cell in row] for row in rows if not _is_empty_row(row)]
            headers = [str(header) for header in table.get("headers", []) or []]
            max_cols = max([len(headers)] + [len(row) for row in rows] + [0])

            if max_cols:
                headers = headers + [""] * (max_cols - len(headers))
                rows = [row + [""] * (max_cols - len(row)) for row in rows]

            if headers and rows and [_norm(cell) for cell in rows[0]] == [_norm(cell) for cell in headers]:
                rows = rows[1:]

            header_idx = table.get("header_row_index")
            if not isinstance(header_idx, int):
                header_idx = _find_header_index(rows, headers)

            if not headers and rows:
                header_source = rows[header_idx] if header_idx < len(rows) else rows[0]
                headers = list(header_source)
                if header_idx < len(rows):
                    rows = rows[:header_idx] + rows[header_idx + 1 :]
                header_idx = 0

            fill_col = table.get("fill_col_index")
            if not isinstance(fill_col, int):
                fill_col = _find_fill_col(headers)

            notes_col = table.get("notes_col_index")
            if notes_col is not None and not isinstance(notes_col, int):
                notes_col = None
            if notes_col is None:
                notes_col = _find_notes_col(headers, fill_col)

            table["headers"] = headers
            table["rows"] = rows
            table["fill_col_index"] = fill_col
            table["notes_col_index"] = notes_col
            table["header_row_index"] = header_idx
            table["row_count"] = len(rows)
            table["is_synthesised"] = table.get("is_synthesised") is True
            table.setdefault("normalisation_notes", "metadata verified")
            table.setdefault("row_metadata", _row_metadata(rows))
    return normalised


def validate_and_normalise_proposal_json(
    raw_proposal_json: dict,
    groq_model: str = "llama-3.3-70b-versatile",
) -> dict:
    try:
        if Groq is None:
            raise RuntimeError("groq Python package is not installed")
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        user_prompt = f"""Raw proposal JSON:
{json.dumps(raw_proposal_json, indent=2, ensure_ascii=False)}

For every table in every section, apply these normalisation rules:

RULE 1 - IDENTIFY THE TRUE HEADER ROW.
The header row contains column labels such as: Item No, Sr No, Description, Specification Required, Specification Offered, Make/Brand, Unit, Quantity, Rate, Amount, Remarks, Compliance, Deviation, Bidder's Response, Our Offer, or similar column name patterns. It is never a title row that spans all columns with a single merged cell of text. Set header_row_index to the 0-based index of this row within the rows array.

RULE 2 - REMOVE DUPLICATE HEADER IN ROWS.
If the first entry in rows is identical (case-insensitive, whitespace-normalised) to the headers array, remove it from rows.

RULE 3 - REMOVE EMPTY ROWS.
Remove any row where every cell is an empty string or whitespace.

RULE 4 - IDENTIFY THE FILL COLUMN.
This is the column the bidding company must fill. It is labelled "Specification Offered", "Our Offer", "Offered Value", "Bidder's Response", "To Be Filled", "Vendor's Offer", "Compliance (Yes/No/Partial)", or is the column immediately to the right of the "Specification Required" or "Description" column if no explicit offer column label exists. Set fill_col_index as a 0-based integer.

RULE 5 - IDENTIFY THE NOTES COLUMN.
If a column labelled "Remarks", "Notes", "Documentation Required", "Reference", "Comments", or "Deviation" exists, set notes_col_index as a 0-based integer. Otherwise set it to null.

RULE 6 - FIX HEADERS ARRAY.
Ensure headers is a flat list of strings with exactly as many entries as the maximum column count across all rows. If headers is empty but rows exist, infer headers from the identified header row. If column count mismatches exist, pad with empty strings.

RULE 7 - DETECT FORM FIELDS IN TEXT.
If a section has no tables but text_preview contains patterns like "Name: ___", "Date: ___", "Signature: ___", "Address:", or lines ending in multiple underscores or dots (form fill patterns), synthesise a table:
  headers: ["Field", "Value"]
  rows: one row per detected field, where column 0 is the field label and column 1 is an empty string.
  fill_col_index: 1
  notes_col_index: null
  is_synthesised: true

RULE 8 - ADD METADATA FIELDS TO EACH TABLE.
Each normalised table must have:
  - fill_col_index: int
  - notes_col_index: int or null
  - header_row_index: int
  - row_count: int (data rows only, excluding header)
  - is_synthesised: bool (true only for RULE 7 tables)
  - normalisation_notes: str (brief note on what was changed, or "no changes" if nothing was modified)

RULE 9 - PRESERVE CELL CONTENT EXACTLY.
Do not paraphrase, summarise, translate, or alter any cell text. Cell content must be byte-for-byte identical to the input.

RULE 10 - HANDLE MERGED/SPANNING CELLS.
If a row appears to be a sub-header or section label within the table (single non-empty cell, all others empty, text is descriptive not a value), mark the row with a field is_subheader: true in a parallel row_metadata array on the table. Do not remove these rows - they carry meaning.

Return ONLY the normalised JSON object with the same top-level shape: {{ "sections": [...] }}. No explanation. No markdown. No preamble."""

        response = client.chat.completions.create(
            model=groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=6000,
            timeout=60,
        )
        choices = getattr(response, "choices", None) or []
        content = getattr(getattr(choices[0], "message", None), "content", "") if choices else ""
        normalised = json.loads(clean_llm_json(content))
        if not isinstance(normalised, dict) or not isinstance(normalised.get("sections"), list):
            raise ValueError("Normalised response did not match {sections: [...]}")
        return _ensure_table_metadata(normalised)
    except Exception as exc:
        logger.warning(
            "LLM proposal JSON normalisation failed (%s): %s",
            type(exc).__name__,
            exc,
        )
        return raw_proposal_json
