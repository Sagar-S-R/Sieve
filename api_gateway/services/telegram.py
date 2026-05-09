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
