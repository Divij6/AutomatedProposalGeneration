import logging

logger = logging.getLogger(__name__)


def test_node(state):
    logger.info("LangGraph test node running")
    return state
