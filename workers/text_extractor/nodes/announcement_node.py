from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.logger import logger


async def handle_announcement(state: AgentState) -> AgentState:
    """
    Handles GROUP_ANNOUNCEMENT intent.

    Group announcements are informational messages that the whole group
    should see but don't require individual task creation.
    Currently logs them for visibility; could be extended to forward
    to a digest channel or notify group admins.
    """
    logger.info("Announcement Node started", extra={
        "node": "announcement_node",
        "group_id": state.get("group_id"),
        "message": state.get("message_text", "")[:100],
    })

    # Store the announcement text in state for downstream use if needed
    state["announcement_text"] = state.get("message_text", "")

    logger.info("Group announcement logged — no task created", extra={
        "node": "announcement_node",
        "group_id": state.get("group_id"),
    })

    return state
