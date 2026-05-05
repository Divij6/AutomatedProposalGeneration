# from pipeline_one.retrieval.retrieve_context import (
#     retrieve_section_context
# )
#
# from config import (
#     COHERE_KEY,
#     QDRANT_URL,
#     QDRANT_KEY
# )
#
#
# def process_section_node(state):
#
#     sections = state["proposal_sections"]
#
#     index = state["section_index"]
#
#     if index >= len(sections):
#
#         print("All sections processed")
#
#         return state
#
#     current_section = sections[index]
#
#     title = current_section["title"]
#
#     print(
#         f"\nProcessing section {index + 1}: {title}"
#     )
#     title = current_section["title"]
#
#
#     if state.get("skip_section"):
#         print(
#             f"Skipping section: {title}"
#         )
#
#         state["section_index"] += 1
#
#         return state
#     context = retrieve_section_context(
#
#         section_title=title,
#
#         company_id=state["company_id"],
#
#         cohere_key=COHERE_KEY,
#
#         qdrant_url=QDRANT_URL,
#
#         qdrant_key=QDRANT_KEY,
#
#         top_k=3
#
#     )
#
#     state["current_section"] = current_section
#
#     state["context"] = context
#
#     state["section_index"] += 1
#
#     return state

from pipeline_one.retrieval.retrieve_context import (
    retrieve_section_context
)

import logging

from config import (
    COHERE_KEY,
    QDRANT_URL,
    QDRANT_KEY
)

logger = logging.getLogger(__name__)


def process_section_node(state: dict) -> dict:
    sections = state.get("proposal_sections") or []
    index = state.get("section_index", 0)

    logger.debug("Proposal sections length: %s", len(sections))
    logger.debug("Accessing proposal_sections index: %s", index)

    if index < 0:
        logger.warning("Negative section_index %s; resetting to 0", index)
        index = 0
        state["section_index"] = index

    if index >= len(sections):
        logger.info("All sections processed")
        return state

    current_section = sections[index]
    if not isinstance(current_section, dict):
        logger.warning("Invalid section at index %s; skipping", index)
        state["current_section"] = {}
        state["section_index"] = index + 1
        return state

    title = current_section.get("title", f"Section {index + 1}")

    logger.info("Processing section %s/%s: %s", index + 1, len(sections), title)

    state["current_section"] = current_section
    state["skip_section"] = False  # always reset

    return state
