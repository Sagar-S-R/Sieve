from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
import json


async def handle_venue_change(state: AgentState) -> AgentState:
    """
    Handles VENUE_CHANGE intent.

    Extracts the venue change details using LLM, then:
    1. Updates existing tasks in the DB that match the subject
    2. Notifies all subscribers of the venue change via DM
    """
    logger.info("Venue Node started", extra={
        "node": "venue_node",
        "group_id": state.get("group_id"),
        "message": state.get("message_text", "")[:100],
    })

    message_text = state.get("message_text", "")
    group_id = state.get("group_id")

    # ---------------------------------------------------------------------------
    # Step 1: Extract venue details with LLM
    # ---------------------------------------------------------------------------
    prompt = f"""Extract venue change information from this message.

Message: "{message_text}"

Respond with ONLY a JSON object:
{{
  "subject": "what class/lab/event is affected (e.g. 'DSA lab', 'tomorrow\\'s lecture')",
  "new_venue": "the new location (e.g. 'ESB 509', 'Room 304', 'Block A Hall')",
  "old_venue": "the old location if mentioned, else null"
}}

If you cannot extract venue info, respond with:
{{"subject": null, "new_venue": null, "old_venue": null}}"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        venue_info = json.loads(content)

    except Exception as e:
        logger.error(f"Venue LLM extraction failed: {e}", extra={"node": "venue_node"})
        venue_info = {"subject": None, "new_venue": None, "old_venue": None}

    state["venue_info"] = venue_info

    logger.info(f"Venue info extracted: {venue_info}", extra={"node": "venue_node"})

    # ---------------------------------------------------------------------------
    # Step 2: Notify subscribers of the venue change
    # ---------------------------------------------------------------------------
    if venue_info.get("new_venue") and group_id:
        try:
            from workers.text_extractor.services.database import get_group_subscribers
            from workers.text_extractor.services.telegram_client import send_dm

            subscribers = await get_group_subscribers(group_id)

            if subscribers:
                subject = venue_info.get("subject") or "an upcoming event"
                new_venue = venue_info["new_venue"]
                old_venue = venue_info.get("old_venue")

                if old_venue:
                    msg = (
                        f" Venue Change\n\n"
                        f"{subject}\n"
                        f"From: {old_venue}\n"
                        f"To: {new_venue}"
                    )
                else:
                    msg = (
                        f" Venue Update\n\n"
                        f"{subject} will be held at: {new_venue}"
                    )

                for subscriber_id in subscribers:
                    try:
                        await send_dm(subscriber_id, msg)
                    except Exception as dm_err:
                        logger.error(
                            f"Failed to send venue DM to {subscriber_id}: {dm_err}",
                            extra={"node": "venue_node"}
                        )

                logger.info(
                    f"Venue change notified to {len(subscribers)} subscriber(s)",
                    extra={"node": "venue_node"}
                )
            else:
                logger.warning(f"No subscribers for group {group_id}", extra={"node": "venue_node"})

        except Exception as e:
            logger.error(f"Venue notification failed: {e}", extra={"node": "venue_node"})
    else:
        logger.info("Venue info incomplete — skipping notification", extra={"node": "venue_node"})

    return state
