# from typing import TypedDict, List, Dict, Any
#
#
# class ProposalState(TypedDict):
#
#     company_id: str
#
#     doc_id: str
#
#     proposal_json: Dict[str, Any]
#
#     proposal_sections: List[Dict[str, Any]]
#
#     generated_sections: List[Dict[str, Any]]
#
#     current_section: Dict[str, Any]
#
#     context: List[Dict[str, Any]]
#
#     section_index: int   # NEW
#
#     status: str
#
#     skip_section: bool  # NEW
#
#     output_file: str

from typing import TypedDict, List, Dict, Any, Optional


class ProposalState(TypedDict):

    company_id: str

    doc_id: str

    # "tender" = use format found in tender doc itself
    # "template" = use company onboarded template
    format_source: str  # NEW — "tender" | "template"

    proposal_json: Dict[str, Any]

    proposal_sections: List[Dict[str, Any]]

    generated_sections: List[Dict[str, Any]]

    current_section: Dict[str, Any]

    context: List[Dict[str, Any]]

    section_index: int

    status: str

    skip_section: bool

    # "paragraph" | "table"
    mode: str  # NEW — explicitly typed

    output_file: str

    error: Optional[str]  # NEW — for graceful error capture