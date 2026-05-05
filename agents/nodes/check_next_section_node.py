"""
check_next_section_node.py - unchanged logic, cleaner code.
"""

import logging

logger = logging.getLogger(__name__)


def check_next_section_node(state: dict) -> str:
    index = state["section_index"]
    total = len(state["proposal_sections"])

    logger.info("[CHECK] section %s/%s", index, total)

    if index < total:
        return "process_section"

    logger.info("All sections processed - compiling")
    return "end"
