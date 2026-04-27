import httpx
from workers.cron_notifier.core.config import settings
from workers.cron_notifier.core.logger import logger


async def send_telegram_dm(user_id: int, message_text: str) -> bool:
    """
    Send a direct message to a Telegram user.
    
    Args:
        user_id: Telegram user ID
        message_text: Message to send
        
    Returns:
        True if message sent successfully, False otherwise
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": user_id,
        "text": message_text,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"✓ DM sent to user {user_id}")
                return True
            else:
                logger.error(f"✗ Telegram API error for user {user_id}: {result.get('description')}")
                return False
                
    except httpx.HTTPStatusError as e:
        logger.error(f"✗ HTTP error sending DM to user {user_id}: {e.response.status_code}")
        return False
    except Exception as e:
        logger.error(f"✗ Error sending DM to user {user_id}: {e}")
        return False
