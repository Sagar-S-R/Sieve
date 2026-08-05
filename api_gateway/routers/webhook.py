import hmac
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException

from api_gateway.core.config import settings
from api_gateway.services.rabbitmq import publish_to_queue
from api_gateway.services.telegram import (
    send_telegram_dm,
    send_group_message,
    answer_callback_query,
)
from api_gateway.services.triage import triage_message
from api_gateway.services.command_handlers import (
    handle_tasks_command,
    handle_delete_command,
    handle_edit_command,
    handle_edit_reply,
)
from shared.database import (
    subscribe_to_group,
    unsubscribe_from_group,
    get_user_subscriptions,
)
from shared.redis_client import (
    get_edit_task_state,
    get_hitl_lock,
    check_group_hitl_lock,
    clear_group_hitl_lock,
    push_raw_message,
)

router = APIRouter()

_BOT_USERNAME = "sieve7_bot"


def verify_telegram_webhook(request: Request, bot_token: str):
    """Verify Telegram webhook signature to prevent unauthorized access."""
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret_token:
        return
    if not hmac.compare_digest(secret_token, bot_token):
        raise HTTPException(status_code=403, detail="Invalid Telegram signature")


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Main webhook endpoint for Telegram updates.

    Flow:
    1. Callback query (button click) -> Handle unsubscribe
    2. Bot added to group           -> Auto-subscribe adder, send welcome
    3. Private DM                   -> Commands / HITL resolution / personal task
    4. Group message with media     -> Route to heavy_media_queue
    5. Group message with text      -> Triage -> fast_text_queue or drop
    """
    try:
        verify_telegram_webhook(request, settings.TELEGRAM_BOT_TOKEN)
        data = await request.json()

        # ── Callback queries (inline button presses) ──────────────────────────
        callback_query = data.get("callback_query")
        if callback_query:
            query_id  = callback_query.get("id")
            user_id   = callback_query.get("from", {}).get("id")
            cb_data   = callback_query.get("data", "")

            if cb_data.startswith("unsub_"):
                group_id = int(cb_data.replace("unsub_", ""))
                success  = await unsubscribe_from_group(group_id, user_id)
                text     = " Unsubscribed successfully!" if success else " You weren't subscribed to this group."

                await answer_callback_query(query_id, text)
                await send_telegram_dm(user_id, f"{text}\n\nSend /unsubscribe to manage other subscriptions.")

            return {"status": "ok"}

        # ── Extract common fields ──────────────────────────────────────────────
        message = data.get("message", {})
        if not message:
            return {"status": "ok"}

        user_id    = message.get("from", {}).get("id")
        chat       = message.get("chat", {})
        chat_type  = chat.get("type")   # "private" | "group" | "supergroup"
        text       = message.get("text", "")
        message_id = message.get("message_id")

        # ── Bot added to a group ───────────────────────────────────────────────
        new_chat_members = message.get("new_chat_members", [])
        if new_chat_members and chat_type in ["group", "supergroup"]:
            for member in new_chat_members:
                if member.get("username") == _BOT_USERNAME or member.get("is_bot"):
                    group_id    = chat.get("id")
                    group_title = chat.get("title", "this group")
                    deep_link   = f"https://t.me/{_BOT_USERNAME}?start=sub_{group_id}"

                    await subscribe_to_group(group_id, user_id)

                    group_welcome = (
                        f" <b>Sieve Bot Activated</b>\n\n"
                        f"I'm now monitoring this group for tasks and deadlines.\n\n"
                        f" <b>How it works:</b>\n"
                        f"• Anyone can mention tasks naturally in chat\n"
                        f"• I'll extract deadlines automatically\n"
                        f"• Subscribers get private DM reminders\n\n"
                        f" <b>Want reminders?</b>\n"
                        f"Click the button below to enable private notifications!"
                    )
                    inline_kb = {"inline_keyboard": [[{"text": " Enable My Reminders", "url": deep_link}]]}
                    await send_group_message(group_id, group_welcome, reply_markup=inline_kb)

                    welcome_dm = (
                        f" <b>Thanks for adding me to {group_title}!</b>\n\n"
                        f"You're now subscribed to reminders from this group.\n\n"
                        f" <b>Want others to get reminders too?</b>\n"
                        f"They can click the button I posted in the group!"
                    )
                    await send_telegram_dm(user_id, welcome_dm)
                    return {"status": "ok"}

        # ── Private DM ─────────────────────────────────────────────────────────
        if chat_type == "private":
            # /start (with or without deep link)
            if text and text.startswith("/start"):
                if text.startswith("/start sub_"):
                    group_id_str = text.replace("/start sub_", "").strip()
                    try:
                        group_id = int(group_id_str)
                        success  = await subscribe_to_group(group_id, user_id)
                        if success:
                            msg = (
                                f" <b>Subscription Confirmed!</b>\n\n"
                                f"You're now subscribed to reminders from this group.\n\n"
                                f" <b>What happens next:</b>\n"
                                f"• When tasks are mentioned in the group, I'll extract them\n"
                                f"• If I need clarification, I'll DM you\n"
                                f"• You'll get reminders 24h, 1h, and at deadline\n\n"
                                f" <b>Want to unsubscribe?</b>\n"
                                f"Send /unsubscribe to manage your subscriptions."
                            )
                        else:
                            msg = " You're already subscribed to this group!"
                        await send_telegram_dm(user_id, msg)
                    except ValueError:
                        await send_telegram_dm(user_id, " Invalid subscription link. Please use the button from the group.")
                    return {"status": "ok"}

                # Plain /start
                welcome = (
                    " <b>Welcome to Sieve!</b>\n\n"
                    "I'm your smart reminder assistant. I can help you:\n"
                    "• Extract reminders from conversations\n"
                    "• Set deadlines automatically\n"
                    "• Send you notifications when tasks are due\n\n"
                    " <b>Get Started:</b>\n"
                    "1. Add me to your group using the button below\n"
                    "2. I'll auto-subscribe you to that group\n"
                    "3. Just chat naturally and mention tasks\n"
                    "4. I'll extract and remind you automatically!\n\n"
                    " <b>Commands:</b>\n"
                    "/unsubscribe - Manage your subscriptions\n"
                    "/help - Show help message"
                )
                inline_kb = {"inline_keyboard": [[{"text": " Add to Group", "url": f"https://t.me/{_BOT_USERNAME}?startgroup=start"}]]}
                await send_telegram_dm(user_id, welcome, reply_markup=inline_kb)
                return {"status": "ok"}

            # /unsubscribe
            if text and text.startswith("/unsubscribe"):
                subscriptions = await get_user_subscriptions(user_id)
                if not subscriptions:
                    await send_telegram_dm(user_id, " You're not subscribed to any groups yet.")
                    return {"status": "ok"}

                keyboard_buttons = [[{
                    "text": f" Unsubscribe from Group {sub['group_id']}",
                    "callback_data": f"unsub_{sub['group_id']}"
                }] for sub in subscriptions]

                await send_telegram_dm(
                    user_id,
                    f" <b>Your Subscriptions</b>\n\nYou're subscribed to {len(subscriptions)} group(s).\nClick a button below to unsubscribe:",
                    reply_markup={"inline_keyboard": keyboard_buttons}
                )
                return {"status": "ok"}

            # /help
            if text and text.startswith("/help"):
                help_msg = (
                    " <b>How to use Sieve:</b>\n\n"
                    "<b>In Groups:</b>\n"
                    "Just chat naturally! I'll detect reminders like:\n"
                    "• \"Remind me to call John at 3pm\"\n"
                    "• \"Don't forget the meeting tomorrow\"\n"
                    "• \"Submit assignment by Friday\"\n\n"
                    "<b>Commands:</b>\n"
                    "/start - Show welcome message\n"
                    "/tasks - List your tasks\n"
                    "/delete &lt;id&gt; - Delete a task\n"
                    "/edit &lt;id&gt; - Edit task deadline\n"
                    "/unsubscribe - Manage subscriptions\n"
                    "/help - Show this help message\n\n"
                    "Need more help? Contact @YourSupportUsername"
                )
                await send_telegram_dm(user_id, help_msg)
                return {"status": "ok"}

            # /tasks
            if text and text.strip() == "/tasks":
                await handle_tasks_command(user_id)
                return {"status": "ok"}

            # /delete
            if text and text.startswith("/delete"):
                await handle_delete_command(user_id, text)
                return {"status": "ok"}

            # /edit
            if text and text.startswith("/edit"):
                await handle_edit_command(user_id, text)
                return {"status": "ok"}

            # Edit reply flow (user is sending a new deadline)
            edit_state = await get_edit_task_state(user_id)
            if edit_state:
                await handle_edit_reply(user_id, text)
                return {"status": "ok"}

            # HITL personal lock — user is replying to a clarification request
            hitl_lock = await get_hitl_lock(user_id)
            if hitl_lock:
                print(f"[HITL] User {user_id} responding to clarification")
                payload = {
                    "user_id": user_id,
                    "group_id": hitl_lock.get("group_id"),
                    "message_text": text,
                    "is_hitl_response": True,
                    "is_personal": hitl_lock.get("is_personal", False),
                    "saved_state": hitl_lock,
                }
                await publish_to_queue("fast_text_queue", payload)
                return {"status": "ok"}

            # Personal task creation (free text, not a command)
            if text and not text.startswith("/"):
                payload = {
                    "user_id": user_id,
                    "group_id": None,
                    "message_id": message_id,
                    "message_text": text,
                    "is_personal": True,
                    "is_hitl_response": False,
                }
                await publish_to_queue("fast_text_queue", payload)
                print(f"[PERSONAL] Task request from user {user_id}: {text[:50]}")

            return {"status": "ok"}

        # ── Group message ───────────────────────────────────────────────────────
        if chat_type in ["group", "supergroup"]:
            group_id = chat.get("id")

            # HITL group reply — someone replied to the bot's clarification message
            reply_to = message.get("reply_to_message")
            if reply_to and reply_to.get("from", {}).get("id") == settings.TELEGRAM_BOT_ID:
                saved_state = check_group_hitl_lock(group_id)
                if saved_state:
                    bot_message_id      = saved_state.get("bot_message_id")
                    reply_to_message_id = reply_to.get("message_id")
                    if bot_message_id and reply_to_message_id == bot_message_id:
                        clear_group_hitl_lock(group_id)
                        payload = {
                            "user_id": user_id,
                            "group_id": group_id,
                            "message_id": message_id,
                            "message_text": text,
                            "is_hitl_response": True,
                            "is_group_hitl": True,
                            "saved_state": saved_state,
                        }
                        await publish_to_queue("fast_text_queue", payload)
                        return {"status": "ok"}

            # Media routing — photo, document, voice, video, audio
            photo    = message.get("photo")
            document = message.get("document")
            voice    = message.get("voice")
            video    = message.get("video")
            audio    = message.get("audio")

            if photo or document or voice or video or audio:
                payload = {
                    "user_id": user_id,
                    "group_id": group_id,
                    "message_text": text,
                    "message_id": message_id,
                }
                if photo:
                    payload["file_id"]    = photo[-1].get("file_id")
                    payload["media_type"] = "image"
                elif document:
                    payload["file_id"]    = document.get("file_id")
                    payload["media_type"] = "document"
                elif voice:
                    payload["file_id"]    = voice.get("file_id")
                    payload["media_type"] = "voice"
                elif video:
                    payload["file_id"]    = video.get("file_id")
                    payload["media_type"] = "video"
                elif audio:
                    payload["file_id"]    = audio.get("file_id")
                    payload["media_type"] = "audio"

                print(f"[ROUTE] {payload['media_type']} message -> heavy_media_queue")
                await publish_to_queue("heavy_media_queue", payload)
                return {"status": "ok"}

            # Pure text — two-stage triage
            if text:
                await push_raw_message(group_id, {
                    "user_id": user_id,
                    "message_text": text,
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": message_id,
                })

                should_drop, reason = triage_message(text)

                if should_drop:
                    print(f"[DROP] Pure noise -> dropped | msg='{text[:60]}'")
                else:
                    print(f"[ROUTE] {reason} -> fast_text_queue | msg='{text[:60]}'")
                    payload = {
                        "user_id": user_id,
                        "group_id": group_id,
                        "message_text": text,
                        "message_id": message_id,
                        "triage_signal": reason,
                    }
                    await publish_to_queue("fast_text_queue", payload)

        return {"status": "ok"}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        import traceback
        print(f"[ERROR] Webhook error: {e}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
