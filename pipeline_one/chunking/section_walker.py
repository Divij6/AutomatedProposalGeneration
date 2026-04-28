"""
section_walker.py

Utility for walking the ParsedSection tree produced by Phase 1.

ParsedDocument.sections contains only top-level sections.
Each section may contain child sections recursively.

This module flattens the hierarchy while preserving parent context.
"""

from typing import Generator, Optional
from pipeline_one.parsing.models.parsed_document import ParsedSection


def walk_sections(
    sections: list[ParsedSection],
    parent_title: Optional[str] = None,
) -> Generator[tuple[ParsedSection, Optional[str]], None, None]:
    """
    Recursively walks the section tree and yields sections one by one.

    Returns:
        Generator of (section, parent_title)

    Example output:
        (Section: Eligibility Criteria, None)
        (Section: Financial Eligibility, "Eligibility Criteria")
        (Section: Technical Requirements, None)
    """

    for section in sections:

        yield section, parent_title

        # walk children recursively
        if section.children:
            yield from walk_sections(
                section.children,
                parent_title=section.title
            )