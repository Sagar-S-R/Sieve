import httpx
from api_gateway.core.config import settings


async def send_telegram_dm(user_id: int, text: str) -> bool:
    """
    Send a direct message to a Telegram user.
    
    Args:
        user_id: Telegram user ID
        text: Message text to send
        
    Returns:
        True if sent successfully, False otherwise
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": user_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("ok", False)
            
    except Exception as e:
        print(f"Error sending DM to user {user_id}: {e}")
        return False
