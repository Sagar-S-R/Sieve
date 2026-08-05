"""
Telegram command handlers for private DM commands.

Extracted from webhook.py to keep the router clean.
Handles: /tasks, /delete, /edit, and the edit reply flow.
Also contains the LLM deadline parser used by the edit flow.
"""

from datetime import datetime, timezone, timedelta

from api_gateway.core.llm import call_llm
from api_gateway.services.telegram import send_telegram_dm
from shared.database import (
    get_user_tasks,
    delete_task,
    get_task_by_id,
    update_task_deadline,
)
from shared.redis_client import (
    get_edit_task_state,
    set_edit_task_state,
    clear_edit_task_state,
)


def format_deadline(deadline) -> str:
    """Format a UTC datetime into a user-friendly IST string."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    deadline_ist = deadline.astimezone(ist_tz)
    formatted = deadline_ist.strftime("%B %d, %Y at %I:%M %p")
    return formatted.replace(" 0", " ")


async def handle_tasks_command(user_id: int):
    """Handle /tasks command - show user's tasks."""
    tasks = await get_user_tasks(user_id)

    response = " <b>Your Tasks</b>\n\n"

    if tasks['upcoming']:
        response += f" <b>Upcoming ({len(tasks['upcoming'])})</b>\n"
        response += "━━━━━━━━━━━━━━━━\n"
        for task in tasks['upcoming']:
            response += f"#{task['id']} - {task['title']}\n"
            response += f" Deadline: {format_deadline(task['deadline'])}\n"
            response += f" Group: {task['group_id']}\n\n"

    if tasks['overdue']:
        response += f" <b>Overdue ({len(tasks['overdue'])})</b>\n"
        response += "━━━━━━━━━━━━━━━━\n"
        for task in tasks['overdue']:
            response += f"#{task['id']} - {task['title']}\n"
            response += f" Deadline: {format_deadline(task['deadline'])} (overdue)\n"
            response += f" Group: {task['group_id']}\n\n"

    if not tasks['upcoming'] and not tasks['overdue']:
        response += " No tasks found\n\n"

    response += "Use /delete &lt;id&gt; to delete a task\n"
    response += "Use /edit &lt;id&gt; to edit deadline"

    await send_telegram_dm(user_id, response)


async def handle_delete_command(user_id: int, message_text: str):
    """Handle /delete <task_id> command."""
    parts = message_text.split()

    if len(parts) != 2:
        await send_telegram_dm(user_id, "Usage: /delete &lt;task_id&gt;\nExample: /delete 5")
        return

    try:
        task_id = int(parts[1])
    except ValueError:
        await send_telegram_dm(user_id, " Invalid task ID. Must be a number.")
        return

    deleted_task = await delete_task(task_id, user_id)

    if deleted_task:
        response = f" Task deleted successfully!\n\n"
        response += f'"{deleted_task["title"]}"\n'
        response += f"Deadline: {format_deadline(deleted_task['deadline'])}"
        await send_telegram_dm(user_id, response)
    else:
        await send_telegram_dm(user_id, " Task not found or you don't have permission to delete it.")


async def handle_edit_command(user_id: int, message_text: str):
    """Handle /edit <task_id> command - start the edit flow."""
    parts = message_text.split()

    if len(parts) != 2:
        await send_telegram_dm(user_id, "Usage: /edit &lt;task_id&gt;\nExample: /edit 5")
        return

    try:
        task_id = int(parts[1])
    except ValueError:
        await send_telegram_dm(user_id, " Invalid task ID. Must be a number.")
        return

    task = await get_task_by_id(task_id)

    if not task or task['user_id'] != user_id:
        await send_telegram_dm(user_id, " Task not found or you don't have permission to edit it.")
        return

    await set_edit_task_state(user_id, {
        'task_id': task_id,
        'task_title': task['title'],
        'current_deadline': task['deadline'].isoformat(),
        'group_id': task['group_id']
    })

    response = f" <b>Editing task #{task_id}</b>\n\n"
    response += f'"{task["title"]}"\n'
    response += f"Current deadline: {format_deadline(task['deadline'])}\n\n"
    response += 'Please send the new deadline (e.g., "tomorrow 5pm", "May 15 EOD")'

    await send_telegram_dm(user_id, response)


async def handle_edit_reply(user_id: int, message_text: str):
    """Handle user's reply with new deadline during the edit flow."""
    edit_state = await get_edit_task_state(user_id)

    if not edit_state:
        return

    try:
        new_deadline = await parse_deadline_from_text(message_text)

        if not new_deadline:
            await send_telegram_dm(
                user_id,
                " Could not understand the deadline. Please try again.\n"
                'Example: "tomorrow 5pm", "May 15 EOD"'
            )
            return

        success = await update_task_deadline(
            edit_state['task_id'],
            user_id,
            new_deadline,
            edit_state['group_id']
        )

        if success:
            response = f" Task updated successfully!\n\n"
            response += f"New deadline: {format_deadline(new_deadline)}"
            await send_telegram_dm(user_id, response)
        else:
            await send_telegram_dm(user_id, " Failed to update task. Please try again.")

    except Exception as e:
        print(f"[EDIT] Error parsing deadline: {e}")
        await send_telegram_dm(user_id, " Error processing deadline. Please try again.")

    finally:
        await clear_edit_task_state(user_id)


async def parse_deadline_from_text(text: str):
    """
    Parse a deadline from natural language text using the LLM.

    Returns a UTC datetime object, or None if parsing fails.
    """
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist_tz)
    current_date_str = now_ist.strftime("%Y-%m-%d")
    current_time_str = now_ist.strftime("%H:%M")

    prompt = f"""Extract the deadline from this text and return it in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).

Current date: {current_date_str}
Current time: {current_time_str}
Timezone: IST (India Standard Time, UTC+5:30)

Text: "{text}"

TIME INTERPRETATION RULES:
- "EOD" (End of Day) = 23:59:59 (11:59 PM)
- "COB" (Close of Business) = 17:00:00 (5 PM)
- "by today" = 23:59:59 today
- "by tonight" = 23:59:59 today
- "midnight" = 23:59:59 (NOT 00:00:00)
- If no time specified, use 23:59:59

Return ONLY the datetime in format: YYYY-MM-DDTHH:MM:SS
Example: 2026-05-15T17:00:00

If you cannot extract a deadline, return: NONE"""

    try:
        response = await call_llm(prompt)
        response = response.strip()

        if response == "NONE" or not response:
            return None

        deadline_ist = datetime.fromisoformat(response)

        if deadline_ist.tzinfo is None:
            deadline_ist = deadline_ist.replace(tzinfo=ist_tz)

        return deadline_ist.astimezone(timezone.utc)

    except Exception as e:
        print(f"[LLM] Error parsing deadline: {e}")
        return None
