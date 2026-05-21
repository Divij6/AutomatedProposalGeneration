from __future__ import annotations

import pytest


@pytest.mark.xfail(
    reason="Phase 5 will add recursive page-offset correction after Docling chunk parsing.",
    strict=False,
)
def test_docling_page_offset_helper_applies_offsets_recursively():
    from pipeline_one.parsing import docling_parser

    apply_page_offset = getattr(docling_parser, "_apply_page_offset")
    sections = [
        {
            "page_start": 2,
            "page_end": 3,
            "tables": [{"page_number": 2}],
            "children": [{"page_start": 3, "page_end": 3, "tables": [], "children": []}],
        }
    ]

    apply_page_offset(sections, offset=10)

    assert sections[0]["page_start"] == 12
    assert sections[0]["page_end"] == 13
    assert sections[0]["tables"][0]["page_number"] == 12
    assert sections[0]["children"][0]["page_start"] == 13
