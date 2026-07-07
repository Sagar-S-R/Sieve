from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
import json


async def handle_schedule_change(state: AgentState) -> AgentState:
    """
    Handles SCHEDULE_CHANGE intent (cancellations, postponements).

    1. Extracts what was cancelled/postponed and when
    2. Attempts to find and update matching tasks in DB
    3. Notifies subscribers
    """
    logger.info("Schedule Node started", extra={
        "node": "schedule_node",
        "group_id": state.get("group_id"),
        "message": state.get("message_text", "")[:100],
    })

    message_text = state.get("message_text", "")
    group_id = state.get("group_id")

    # ---------------------------------------------------------------------------
    # Step 1: Extract schedule change details
    # ---------------------------------------------------------------------------
    prompt = f"""Extract schedule change information from this message.

Message: "{message_text}"

Respond with ONLY a JSON object:
{{
  "change_type": "cancelled" | "postponed" | "rescheduled" | "no_class",
  "subject": "what is affected (e.g. 'tomorrow\\'s class', 'DSA lab', 'Friday lecture')",
  "new_time": "new time if rescheduled, else null",
  "reason": "reason if mentioned, else null"
}}

If you cannot determine change details, respond with:
{{"change_type": "cancelled", "subject": null, "new_time": null, "reason": null}}"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        change_info = json.loads(content)

    except Exception as e:
        logger.error(f"Schedule LLM extraction failed: {e}", extra={"node": "schedule_node"})
        change_info = {"change_type": "cancelled", "subject": None, "new_time": None, "reason": None}

    state["schedule_change_info"] = change_info

    logger.info(f"Schedule change info: {change_info}", extra={"node": "schedule_node"})

    # ---------------------------------------------------------------------------
    # Step 2: Notify subscribers
    # ---------------------------------------------------------------------------
    if group_id and change_info.get("subject"):
        try:
            from workers.text_extractor.services.database import get_group_subscribers
            from workers.text_extractor.services.telegram_client import send_dm

            subscribers = await get_group_subscribers(group_id)

            if subscribers:
                change_type = change_info.get("change_type", "cancelled")
                subject = change_info["subject"]
                new_time = change_info.get("new_time")
                reason = change_info.get("reason")

                # Build notification message
                icon = {
                    "cancelled":    "",
                    "postponed":    "",
                    "rescheduled":  "",
                    "no_class":     "",
                }.get(change_type, "")

                msg = f"{icon} Schedule Update\n\n{subject} is {change_type}."

                if new_time:
                    msg += f"\nRescheduled to: {new_time}"

                if reason:
                    msg += f"\nReason: {reason}"

                for subscriber_id in subscribers:
                    try:
                        await send_dm(subscriber_id, msg)
                    except Exception as dm_err:
                        logger.error(
                            f"Failed to send schedule DM to {subscriber_id}: {dm_err}",
                            extra={"node": "schedule_node"}
                        )

                logger.info(
                    f"Schedule change notified to {len(subscribers)} subscriber(s)",
                    extra={"node": "schedule_node"}
                )
            else:
                logger.warning(f"No subscribers for group {group_id}", extra={"node": "schedule_node"})

        except Exception as e:
            logger.error(f"Schedule notification failed: {e}", extra={"node": "schedule_node"})

    return state
