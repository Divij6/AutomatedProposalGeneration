# from langgraph.graph import StateGraph, END
#
# from agents.state import ProposalState
#
# from agents.nodes.load_sections_node import (
#     load_sections_node
# )
#
# from agents.nodes.process_section_node import (
#     process_section_node
# )
#
# from agents.nodes.validate_section_node import (
#     validate_section_node
# )
#
# from agents.nodes.generate_section_node import (
#     generate_section_node
# )
#
# from agents.nodes.check_next_section_node import (
#     check_next_section_node
# )
#
# from agents.nodes.compile_proposal_node import (
#     compile_proposal_node
# )
#
#
# def route_after_validation(state):
#
#     if state.get("skip_section"):
#
#         return "skip"
#
#     return "generate"
#
#
# def route_after_check(state):
#
#     result = check_next_section_node(state)
#
#     if result == "end":
#
#         return "compile"
#
#     return "process"
#
#
# def build_graph():
#
#     workflow = StateGraph(
#         ProposalState
#     )
#
#     # -------------------
#     # Add Nodes
#     # -------------------
#
#     workflow.add_node(
#         "load_sections",
#         load_sections_node
#     )
#
#     workflow.add_node(
#         "process_section",
#         process_section_node
#     )
#
#     workflow.add_node(
#         "validate_section",
#         validate_section_node
#     )
#
#     workflow.add_node(
#         "generate_section",
#         generate_section_node
#     )
#
#     workflow.add_node(
#         "compile_proposal",
#         compile_proposal_node
#     )
#
#     # -------------------
#     # Entry
#     # -------------------
#
#     workflow.set_entry_point(
#         "load_sections"
#     )
#
#     # -------------------
#     # Edges
#     # -------------------
#
#     workflow.add_edge(
#         "load_sections",
#         "process_section"
#     )
#
#     workflow.add_edge(
#         "process_section",
#         "validate_section"
#     )
#
#     # After validation
#     workflow.add_conditional_edges(
#
#         "validate_section",
#
#         route_after_validation,
#
#         {
#
#             "skip": "process_section",
#
#             "generate": "generate_section"
#
#         }
#
#     )
#
#     # After generation
#     workflow.add_conditional_edges(
#
#         "generate_section",
#
#         route_after_check,
#
#         {
#
#             "process": "process_section",
#
#             "compile": "compile_proposal"
#
#         }
#
#     )
#
#     # Final step
#     workflow.add_edge(
#         "compile_proposal",
#         END
#     )
#
#     graph = workflow.compile()
#
#     return graph

"""
graph.py

Changes vs old version:
- route_after_check no longer re-calls check_next_section_node (it was
  calling the function directly AND using it as a conditional edge — double-call bug).
  Now it reads state directly.
- format_source is threaded through initial_state (set by api.py before invoking).
"""

import logging

from langgraph.graph import StateGraph, END

from agents.state import ProposalState
from agents.nodes.load_sections_node import load_sections_node
from agents.nodes.process_section_node import process_section_node
from agents.nodes.validate_section_node import validate_section_node
from agents.nodes.generate_section_node import generate_section_node
from agents.nodes.check_next_section_node import check_next_section_node
from agents.nodes.compile_proposal_node import compile_proposal_node

logger = logging.getLogger(__name__)


def route_after_validation(state: dict) -> str:
    if state.get("skip_section"):
        return "skip"
    return "generate"


def route_after_process(state: dict) -> str:
    sections = state.get("proposal_sections") or []
    index = state.get("section_index", 0)
    logger.debug("route_after_process sections length: %s", len(sections))
    logger.debug("route_after_process accessing index: %s", index)
    if index >= len(sections):
        return "compile"
    if not state.get("current_section"):
        return "process"
    return "validate"


def route_after_generation(state: dict) -> str:
    """
    Called after generate_section_node.
    Checks if there are more sections to process.
    """
    sections = state.get("proposal_sections") or []
    index = state.get("section_index", 0)
    total = len(sections)
    logger.debug("route_after_generation sections length: %s", total)
    logger.debug("route_after_generation next index: %s", index)

    if index < total:
        return "process"
    else:
        return "compile"


def build_graph():

    workflow = StateGraph(ProposalState)

    # ── Nodes ──────────────────────────────────────────────────────
    workflow.add_node("load_sections",    load_sections_node)
    workflow.add_node("process_section",  process_section_node)
    workflow.add_node("validate_section", validate_section_node)
    workflow.add_node("generate_section", generate_section_node)
    workflow.add_node("compile_proposal", compile_proposal_node)

    # ── Entry ──────────────────────────────────────────────────────
    workflow.set_entry_point("load_sections")

    # ── Edges ──────────────────────────────────────────────────────
    workflow.add_edge("load_sections", "process_section")
    workflow.add_conditional_edges(
        "process_section",
        route_after_process,
        {
            "validate": "validate_section",
            "compile": "compile_proposal",
        },
    )

    # After validation: SKIP loops back to process_section (index already bumped)
    #                   GENERATE goes to generate_section
    workflow.add_conditional_edges(
        "validate_section",
        route_after_validation,
        {
            "skip":     "process_section",
            "generate": "generate_section",
        },
    )

    # After generation: more sections → process_section, done → compile
    workflow.add_conditional_edges(
        "generate_section",
        route_after_generation,
        {
            "process": "process_section",
            "compile": "compile_proposal",
        },
    )

    workflow.add_edge("compile_proposal", END)

    return workflow.compile()
