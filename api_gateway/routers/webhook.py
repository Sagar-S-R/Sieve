from fastapi import APIRouter, Request, HTTPException
from api_gateway.services.redis_client import get_hitl_lock, delete_hitl_lock
from api_gateway.services.database import save_completed_task
from api_gateway.services.rabbitmq import publish_to_queue
from api_gateway.services.telegram import send_telegram_dm
import hmac

router = APIRouter()


def verify_telegram_webhook(request: Request, bot_token: str):
    """
    Verify Telegram webhook signature to prevent unauthorized access.
    
    Note: Telegram's secret token must be set when configuring the webhook.
    If not set, this check is skipped (for backward compatibility).
    """
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    
    # If no secret token in header, skip verification (webhook not configured with secret)
    # In production, you should always set a secret token
    if not secret_token:
        return  # Skip verification
    
    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(secret_token, bot_token):
        raise HTTPException(status_code=403, detail="Invalid Telegram signature")


# Zero-cost triage keywords - expanded to catch more reminder-like messages
TRIAGE_KEYWORDS = [
    # Deadlines & Time
    "due", "deadline", "by", "before", "until", "tomorrow", "today", "tonight",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "next week", "this week", "later", "soon",
    
    # Academic/Work
    "assignment", "homework", "test", "exam", "quiz", "midterm", "final",
    "hackathon", "submit", "submission", "paper", "project", "report",
    "presentation", "lecture", "class", "lab",
    
    # Events & Meetings
    "meeting", "meet", "call", "conference", "event", "appointment",
    "session", "interview", "discussion", "standup", "sync",
    
    # Actions
    "remind", "reminder", "remember", "don't forget", "dont forget",
    "need to", "have to", "must", "should", "gotta", "got to",
    "attend", "join", "participate", "complete", "finish", "do",
    
    # Tasks
    "task", "todo", "to-do", "to do", "work on", "follow up", "followup"
]


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Main webhook endpoint for Telegram updates.
    
    Flow:
    1. Bot added to group → Auto-subscribe the adder
    2. Private DM → Check HITL lock → Save task if lock exists
    3. Group message with media → Route to heavy_media_queue
    4. Group message with text → Triage keywords → Route to fast_text_queue or drop
    """
    try:
        # CRITICAL: Verify Telegram webhook signature
        from api_gateway.core.config import settings
        verify_telegram_webhook(request, settings.TELEGRAM_BOT_TOKEN)
        
        data = await request.json()
        
        # Handle callback queries (button clicks)
        callback_query = data.get("callback_query")
        if callback_query:
            from api_gateway.services.database import unsubscribe_from_group
            import httpx
            
            query_id = callback_query.get("id")
            user_id = callback_query.get("from", {}).get("id")
            callback_data = callback_query.get("data", "")
            
            # Handle unsubscribe button
            if callback_data.startswith("unsub_"):
                group_id = int(callback_data.replace("unsub_", ""))
                success = await unsubscribe_from_group(group_id, user_id)
                
                if success:
                    response_text = "✅ Unsubscribed successfully!"
                else:
                    response_text = "ℹ️ You weren't subscribed to this group."
                
                # Answer callback query
                answer_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
                
                async with httpx.AsyncClient() as client:
                    await client.post(answer_url, json={
                        "callback_query_id": query_id,
                        "text": response_text,
                        "show_alert": False
                    })
                
                # Update message
                await send_telegram_dm(user_id, f"{response_text}\n\nSend /unsubscribe to manage other subscriptions.")
                
                return {"status": "ok"}
        
        # Extract message data
        message = data.get("message", {})
        if not message:
            return {"status": "ok"}
        
        user_id = message.get("from", {}).get("id")
        chat = message.get("chat", {})
        chat_type = chat.get("type")  # "private", "group", "supergroup"
        text = message.get("text", "")
        
        # Check for media
        photo = message.get("photo")
        document = message.get("document")
        
        # ============================================
        # BOT ADDED TO GROUP - SEND WELCOME WITH DEEP LINK
        # ============================================
        new_chat_members = message.get("new_chat_members", [])
        if new_chat_members and chat_type in ["group", "supergroup"]:
            from api_gateway.services.database import subscribe_to_group
            
            # Check if our bot was added
            bot_username = "sieve7_bot"
            for member in new_chat_members:
                if member.get("username") == bot_username or member.get("is_bot"):
                    group_id = chat.get("id")
                    group_title = chat.get("title", "this group")
                    
                    # Auto-subscribe the person who added the bot
                    await subscribe_to_group(group_id, user_id)
                    
                    # Send welcome message IN THE GROUP with deep link button
                    deep_link = f"https://t.me/{bot_username}?start=sub_{group_id}"
                    
                    group_welcome = (
                        f"🤖 <b>Sieve Bot Activated</b>\n\n"
                        f"I'm now monitoring this group for tasks and deadlines.\n\n"
                        f"💡 <b>How it works:</b>\n"
                        f"• Anyone can mention tasks naturally in chat\n"
                        f"• I'll extract deadlines automatically\n"
                        f"• Subscribers get private DM reminders\n\n"
                        f"🔔 <b>Want reminders?</b>\n"
                        f"Click the button below to enable private notifications!"
                    )
                    
                    inline_keyboard = {
                        "inline_keyboard": [[
                            {
                                "text": "🔔 Enable My Reminders",
                                "url": deep_link
                            }
                        ]]
                    }
                    
                    # Send to group (not DM)
                    from api_gateway.core.config import settings as api_settings
                    import httpx
                    
                    send_url = f"https://api.telegram.org/bot{api_settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                    async with httpx.AsyncClient() as client:
                        await client.post(send_url, json={
                            "chat_id": group_id,
                            "text": group_welcome,
                            "parse_mode": "HTML",
                            "reply_markup": inline_keyboard
                        })
                    
                    # Also send DM to the person who added it
                    welcome_dm = (
                        f"🎉 <b>Thanks for adding me to {group_title}!</b>\n\n"
                        f"You're now subscribed to reminders from this group.\n\n"
                        f"💡 <b>Want others to get reminders too?</b>\n"
                        f"They can click the button I posted in the group!"
                    )
                    await send_telegram_dm(user_id, welcome_dm)
                    
                    return {"status": "ok"}
        
        # ============================================
        # PRIVATE DM - DEEP LINK SUBSCRIPTION & HITL
        # ============================================
        if chat_type == "private":
            # Handle /start command with deep link subscription
            if text and text.startswith("/start"):
                # Check if it's a deep link subscription (e.g., /start sub_-100123456789)
                if text.startswith("/start sub_"):
                    from api_gateway.services.database import subscribe_to_group
                    
                    # Extract group ID from deep link
                    group_id_str = text.replace("/start sub_", "").strip()
                    
                    try:
                        group_id = int(group_id_str)
                        
                        # Subscribe user to the group
                        success = await subscribe_to_group(group_id, user_id)
                        
                        if success:
                            confirmation_msg = (
                                f"✅ <b>Subscription Confirmed!</b>\n\n"
                                f"You're now subscribed to reminders from this group.\n\n"
                                f"💡 <b>What happens next:</b>\n"
                                f"• When tasks are mentioned in the group, I'll extract them\n"
                                f"• If I need clarification, I'll DM you\n"
                                f"• You'll get reminders 24h, 1h, and at deadline\n\n"
                                f"🔕 <b>Want to unsubscribe?</b>\n"
                                f"Send /unsubscribe to manage your subscriptions."
                            )
                        else:
                            confirmation_msg = "✅ You're already subscribed to this group!"
                        
                        await send_telegram_dm(user_id, confirmation_msg)
                        return {"status": "ok"}
                        
                    except ValueError:
                        error_msg = "❌ Invalid subscription link. Please use the button from the group."
                        await send_telegram_dm(user_id, error_msg)
                        return {"status": "ok"}
                
                # Regular /start (no deep link) - Simple welcome message
                welcome_message = (
                    "👋 <b>Welcome to Sieve!</b>\n\n"
                    "I'm your smart reminder assistant. I can help you:\n"
                    "• Extract reminders from conversations\n"
                    "• Set deadlines automatically\n"
                    "• Send you notifications when tasks are due\n\n"
                    "🚀 <b>Get Started:</b>\n"
                    "1. Add me to your group using the button below\n"
                    "2. I'll auto-subscribe you to that group\n"
                    "3. Just chat naturally and mention tasks\n"
                    "4. I'll extract and remind you automatically!\n\n"
                    "💡 <b>Example:</b>\n"
                    "\"Remind me to submit assignment tomorrow at 5pm\"\n\n"
                    "📋 <b>Commands:</b>\n"
                    "/unsubscribe - Manage your subscriptions\n"
                    "/help - Show help message"
                )
                
                bot_username = "sieve7_bot"
                inline_keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "➕ Add to Group",
                                "url": f"https://t.me/{bot_username}?startgroup=start"
                            }
                        ]
                    ]
                }
                
                await send_telegram_dm(user_id, welcome_message, reply_markup=inline_keyboard)
                return {"status": "ok"}
            
            # Handle /unsubscribe command
            if text and text.startswith("/unsubscribe"):
                from api_gateway.services.database import get_user_subscriptions
                
                subscriptions = await get_user_subscriptions(user_id)
                
                if not subscriptions:
                    msg = "ℹ️ You're not subscribed to any groups yet."
                    await send_telegram_dm(user_id, msg)
                    return {"status": "ok"}
                
                # Build inline keyboard with unsubscribe buttons
                keyboard_buttons = []
                for sub in subscriptions:
                    group_id = sub['group_id']
                    button_text = f"🔕 Unsubscribe from Group {group_id}"
                    callback_data = f"unsub_{group_id}"
                    
                    keyboard_buttons.append([{
                        "text": button_text,
                        "callback_data": callback_data
                    }])
                
                inline_keyboard = {"inline_keyboard": keyboard_buttons}
                
                msg = (
                    "📋 <b>Your Subscriptions</b>\n\n"
                    f"You're subscribed to {len(subscriptions)} group(s).\n"
                    "Click a button below to unsubscribe:"
                )
                
                await send_telegram_dm(user_id, msg, reply_markup=inline_keyboard)
                return {"status": "ok"}
            
            # Handle /help command
            if text and text.startswith("/help"):
                help_message = (
                    "📖 <b>How to use Sieve:</b>\n\n"
                    "<b>In Groups:</b>\n"
                    "Just chat naturally! I'll detect reminders like:\n"
                    "• \"Remind me to call John at 3pm\"\n"
                    "• \"Don't forget the meeting tomorrow\"\n"
                    "• \"Submit assignment by Friday\"\n\n"
                    "<b>Commands:</b>\n"
                    "/start - Show welcome message\n"
                    "/tasks - List your tasks\n"
                    "/delete <id> - Delete a task\n"
                    "/edit <id> - Edit task deadline\n"
                    "/unsubscribe - Manage subscriptions\n"
                    "/help - Show this help message\n\n"
                    "Need more help? Contact @YourSupportUsername"
                )
                
                await send_telegram_dm(user_id, help_message)
                return {"status": "ok"}
            
            # Handle /tasks command
            if text and text.strip() == "/tasks":
                await handle_tasks_command(user_id)
                return {"status": "ok"}
            
            # Handle /delete command
            if text and text.startswith("/delete"):
                await handle_delete_command(user_id, text)
                return {"status": "ok"}
            
            # Handle /edit command
            if text and text.startswith("/edit"):
                await handle_edit_command(user_id, text)
                return {"status": "ok"}
            
            # Check if user is in edit mode (replying with new deadline)
            from api_gateway.services.redis_client import get_edit_task_state
            edit_state = await get_edit_task_state(user_id)
            if edit_state:
                await handle_edit_reply(user_id, text)
                return {"status": "ok"}
            
            # Check for HITL lock
            hitl_lock = await get_hitl_lock(user_id)
            
            if hitl_lock:
                # User is responding to clarification request
                print(f"[HITL] User {user_id} responding to clarification")
                
                # Send the user's response back to text_extractor for processing
                # The worker will merge the clarification with saved state
                payload = {
                    "user_id": user_id,
                    "group_id": hitl_lock.get("group_id"),
                    "message_text": text,
                    "is_hitl_response": True  # Flag to indicate this is a HITL response
                }
                
                print(f"[HITL] Routing clarification to text_extractor")
                await publish_to_queue("fast_text_queue", payload)
                
                return {"status": "ok"}
            
            # No HITL lock - ignore private messages for now
            return {"status": "ok"}
        
        # ============================================
        # GROUP MESSAGE - ROUTING LOGIC
        # ============================================
        if chat_type in ["group", "supergroup"]:
            group_id = chat.get("id")
            
            # Prepare base payload
            payload = {
                "user_id": user_id,
                "group_id": group_id,
                "message_text": text,
                "message_id": message.get("message_id")  # For deduplication
            }
            
            # Check for media (images or documents)
            if photo or document:
                # Route to heavy_media_queue
                if photo:
                    # Get highest resolution photo
                    file_id = photo[-1].get("file_id")
                    payload["file_id"] = file_id
                    payload["media_type"] = "image"
                elif document:
                    file_id = document.get("file_id")
                    payload["file_id"] = file_id
                    payload["media_type"] = "document"
                
                print(f"[ROUTE] Media message → heavy_media_queue")
                await publish_to_queue("heavy_media_queue", payload)
                return {"status": "ok"}
            
            # Pure text message - apply zero-cost triage
            if text:
                text_lower = text.lower()
                
                # Check for triage keywords
                has_keywords = any(keyword in text_lower for keyword in TRIAGE_KEYWORDS)
                
                if has_keywords:
                    # Route to fast_text_queue
                    print(f"[ROUTE] Text with keywords → fast_text_queue")
                    await publish_to_queue("fast_text_queue", payload)
                else:
                    # Drop message to save LLM costs
                    print(f"[DROP] Text without keywords - dropped")
                
                return {"status": "ok"}
        
        return {"status": "ok"}
        
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions (like 403 from signature verification)
        raise http_exc
    except Exception as e:
        import traceback
        print(f"[ERROR] Webhook error: {e}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# TASK MANAGEMENT COMMAND HANDLERS
# ============================================================================

def format_deadline(deadline) -> str:
    """
    Format deadline in user-friendly IST format.
    
    Args:
        deadline: UTC datetime
        
    Returns:
        Formatted string like "May 12, 2026 at 5:30 PM"
    """
    from datetime import timezone, timedelta
    
    # Convert to IST
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    deadline_ist = deadline.astimezone(ist_tz)
    
    # Format and remove leading zero from hour
    formatted = deadline_ist.strftime("%B %d, %Y at %I:%M %p")
    return formatted.replace(" 0", " ")


async def handle_tasks_command(user_id: int):
    """
    Handle /tasks command - show user's tasks.
    """
    from api_gateway.services.database import get_user_tasks
    
    # Fetch user's tasks
    tasks = await get_user_tasks(user_id)
    
    # Build response message
    response = "📋 <b>Your Tasks</b>\n\n"
    
    # Upcoming tasks
    if tasks['upcoming']:
        response += f"⏰ <b>Upcoming ({len(tasks['upcoming'])})</b>\n"
        response += "━━━━━━━━━━━━━━━━\n"
        for task in tasks['upcoming']:
            response += f"#{task['id']} - {task['title']}\n"
            response += f"📅 Deadline: {format_deadline(task['deadline'])}\n"
            response += f"👥 Group: {task['group_id']}\n\n"
    
    # Overdue tasks
    if tasks['overdue']:
        response += f"🔴 <b>Overdue ({len(tasks['overdue'])})</b>\n"
        response += "━━━━━━━━━━━━━━━━\n"
        for task in tasks['overdue']:
            response += f"#{task['id']} - {task['title']}\n"
            response += f"📅 Deadline: {format_deadline(task['deadline'])} (overdue)\n"
            response += f"👥 Group: {task['group_id']}\n\n"
    
    # No tasks
    if not tasks['upcoming'] and not tasks['overdue']:
        response += "✅ No tasks found\n\n"
    
    # Usage instructions
    response += "Use /delete &lt;id&gt; to delete a task\n"
    response += "Use /edit &lt;id&gt; to edit deadline"
    
    await send_telegram_dm(user_id, response)


async def handle_delete_command(user_id: int, message_text: str):
    """
    Handle /delete <task_id> command.
    """
    from api_gateway.services.database import delete_task
    
    # Parse command
    parts = message_text.split()
    
    # Validate format
    if len(parts) != 2:
        await send_telegram_dm(
            user_id,
            "Usage: /delete &lt;task_id&gt;\nExample: /delete 5"
        )
        return
    
    # Validate task_id is integer
    try:
        task_id = int(parts[1])
    except ValueError:
        await send_telegram_dm(
            user_id,
            "❌ Invalid task ID. Must be a number."
        )
        return
    
    # Delete task (with ownership check)
    deleted_task = await delete_task(task_id, user_id)
    
    if deleted_task:
        response = f"✅ Task deleted successfully!\n\n"
        response += f'"{deleted_task["title"]}"\n'
        response += f"Deadline: {format_deadline(deleted_task['deadline'])}"
        await send_telegram_dm(user_id, response)
    else:
        await send_telegram_dm(
            user_id,
            "❌ Task not found or you don't have permission to delete it."
        )


async def handle_edit_command(user_id: int, message_text: str):
    """
    Handle /edit <task_id> command - start edit flow.
    """
    from api_gateway.services.database import get_task_by_id
    from api_gateway.services.redis_client import set_edit_task_state
    
    # Parse command
    parts = message_text.split()
    
    # Validate format
    if len(parts) != 2:
        await send_telegram_dm(
            user_id,
            "Usage: /edit &lt;task_id&gt;\nExample: /edit 5"
        )
        return
    
    # Validate task_id is integer
    try:
        task_id = int(parts[1])
    except ValueError:
        await send_telegram_dm(
            user_id,
            "❌ Invalid task ID. Must be a number."
        )
        return
    
    # Get task (with ownership check)
    task = await get_task_by_id(task_id)
    
    if not task or task['user_id'] != user_id:
        await send_telegram_dm(
            user_id,
            "❌ Task not found or you don't have permission to edit it."
        )
        return
    
    # Store edit state in Redis
    await set_edit_task_state(user_id, {
        'task_id': task_id,
        'task_title': task['title'],
        'current_deadline': task['deadline'].isoformat(),
        'group_id': task['group_id']
    })
    
    # Ask for new deadline
    response = f"📝 <b>Editing task #{task_id}</b>\n\n"
    response += f'"{task["title"]}"\n'
    response += f"Current deadline: {format_deadline(task['deadline'])}\n\n"
    response += "Please send the new deadline (e.g., \"tomorrow 5pm\", \"May 15 EOD\")"
    
    await send_telegram_dm(user_id, response)


async def handle_edit_reply(user_id: int, message_text: str):
    """
    Handle user's reply with new deadline during edit flow.
    """
    from api_gateway.services.redis_client import get_edit_task_state, clear_edit_task_state
    from api_gateway.services.database import update_task_deadline
    
    # Get edit state
    edit_state = await get_edit_task_state(user_id)
    
    if not edit_state:
        return  # Not in edit mode
    
    try:
        # Parse new deadline using LLM
        new_deadline = await parse_deadline_from_text(message_text)
        
        if not new_deadline:
            await send_telegram_dm(
                user_id,
                "❌ Could not understand the deadline. Please try again.\n"
                "Example: \"tomorrow 5pm\", \"May 15 EOD\""
            )
            return
        
        # Update task
        success = await update_task_deadline(
            edit_state['task_id'],
            user_id,
            new_deadline,
            edit_state['group_id']
        )
        
        if success:
            response = f"✅ Task updated successfully!\n\n"
            response += f"New deadline: {format_deadline(new_deadline)}"
            await send_telegram_dm(user_id, response)
        else:
            await send_telegram_dm(
                user_id,
                "❌ Failed to update task. Please try again."
            )
    
    except Exception as e:
        print(f"[EDIT] Error parsing deadline: {e}")
        await send_telegram_dm(
            user_id,
            "❌ Error processing deadline. Please try again."
        )
    
    finally:
        # Clear edit state
        await clear_edit_task_state(user_id)


async def parse_deadline_from_text(text: str):
    """
    Parse deadline from natural language text using LLM.
    
    Args:
        text: Natural language deadline (e.g., "tomorrow 5pm", "May 15 EOD")
        
    Returns:
        UTC datetime object or None if parsing fails
    """
    from api_gateway.core.llm import call_llm
    from datetime import datetime, timezone, timedelta
    import json
    
    # Get current date in IST for context
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
        
        # Parse the datetime
        deadline_ist = datetime.fromisoformat(response)
        
        # Add IST timezone if not present
        if deadline_ist.tzinfo is None:
            deadline_ist = deadline_ist.replace(tzinfo=ist_tz)
        
        # Convert to UTC
        deadline_utc = deadline_ist.astimezone(timezone.utc)
        
        return deadline_utc
        
    except Exception as e:
        print(f"[LLM] Error parsing deadline: {e}")
        return None
