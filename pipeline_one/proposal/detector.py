"""
detector.py

Detects whether a tender document contains
proposal formats such as:

- Technical Proposal
- Financial Proposal
- Annexure
- BOQ
- Bid Format
"""

def detect_proposal_sections(parsed_doc):
    """
    Detect proposal-related sections using keywords.

    Args:
        parsed_doc: ParsedDocument object

    Returns:
        List of proposal sections
    """

    keywords = [
        "annex",
        "ANNEX",
        "proposal",
        "bid format",
        "financial proposal",
        "technical proposal",
        "annexure",
        "price bid",
        "form of bid",
        "schedule of rates",
        "bill of quantity",
        "boq",
        "appendix",
        "format"

    ]

    proposal_sections = []

    def walk_sections(section_list):

        for section in section_list:

            title = section.title.lower()

            if any(k in title for k in keywords):

                proposal_sections.append(section)

            # check child sections
            if section.children:
                walk_sections(section.children)

    walk_sections(parsed_doc.sections)

    return proposal_sections