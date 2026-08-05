import httpx
from api_gateway.core.config import settings
from typing import Optional, List, Dict


async def send_telegram_dm(user_id: int, text: str, reply_markup: Optional[Dict] = None) -> bool:
    """
    Send a direct message to a Telegram user.

    Args:
        user_id: Telegram user ID
        text: Message text to send
        reply_markup: Optional inline keyboard markup

    Returns:
        True if sent successfully, False otherwise
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": user_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            return result.get("ok", False)

    except Exception as e:
        print(f"Error sending DM to user {user_id}: {e}")
        return False


async def send_group_message(chat_id: int, text: str, reply_markup: Optional[Dict] = None) -> bool:
    """
    Send a message to a group or supergroup chat.

    Args:
        chat_id: Telegram group/supergroup chat ID (negative integer)
        text: Message text to send
        reply_markup: Optional inline keyboard markup

    Returns:
        True if sent successfully, False otherwise
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("ok", False)

    except Exception as e:
        print(f"Error sending group message to {chat_id}: {e}")
        return False


async def answer_callback_query(query_id: str, text: str, show_alert: bool = False) -> bool:
    """
    Answer a Telegram callback query (inline button click).

    Args:
        query_id: The callback query ID from Telegram
        text: Notification text to show the user
        show_alert: If True, show as an alert popup instead of a toast

    Returns:
        True if answered successfully, False otherwise
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json={
                "callback_query_id": query_id,
                "text": text,
                "show_alert": show_alert
            })
            response.raise_for_status()
            return response.json().get("ok", False)

    except Exception as e:
        print(f"Error answering callback query {query_id}: {e}")
        return False
