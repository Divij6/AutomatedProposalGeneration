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

from config import (
    COHERE_KEY,
    QDRANT_URL,
    QDRANT_KEY
)


def process_section_node(state: dict) -> dict:
    sections = state.get("proposal_sections") or []
    index = state.get("section_index", 0)

    print("DEBUG proposal_sections length:", len(sections))
    print("DEBUG accessing proposal_sections index:", index)

    if index < 0:
        print(f"WARNING: negative section_index {index}; resetting to 0")
        index = 0
        state["section_index"] = index

    if index >= len(sections):
        print("All sections processed")
        return state

    current_section = sections[index]
    if not isinstance(current_section, dict):
        print(f"WARNING: invalid section at index {index}; skipping")
        state["current_section"] = {}
        state["section_index"] = index + 1
        return state

    title = current_section.get("title", f"Section {index + 1}")

    print(f"\nProcessing section {index + 1}/{len(sections)}: {title}")

    state["current_section"] = current_section
    state["skip_section"] = False  # always reset

    return state
