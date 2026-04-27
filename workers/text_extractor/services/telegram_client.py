import httpx
import asyncio
from typing import Optional
from workers.text_extractor.core.config import settings
from workers.text_extractor.core.logger import logger


class TelegramClientError(Exception):
    """Exception raised when Telegram API operations fail."""
    pass


async def send_dm(
    user_id: int,
    prompt: str,
    task_context: Optional[str] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[int] = None
) -> dict:
    """
    Send a direct message to a Telegram user using the Bot API.
    
    Args:
        user_id: The Telegram user ID to send the message to
        prompt: The clarification prompt to send
        task_context: Optional context about the task needing clarification
        max_retries: Maximum number of retry attempts (defaults to config value)
        retry_delay: Delay in seconds between retries (defaults to config value)
    
    Returns:
        dict: The response from the Telegram API
    
    Raises:
        TelegramClientError: If the message fails to send after all retries
    """
    if max_retries is None:
        max_retries = settings.TELEGRAM_MAX_RETRIES
    if retry_delay is None:
        retry_delay = settings.TELEGRAM_RETRY_DELAY
    
    # Format the message with task context if provided
    message = prompt
    if task_context:
        message = f"{task_context}\n\n{prompt}"
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            logger.info(
                "Sending Telegram DM",
                extra={
                    "user_id": user_id,
                    "attempt": attempt + 1,
                    "max_retries": max_retries
                }
            )
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if not result.get("ok"):
                    error_description = result.get("description", "Unknown error")
                    raise TelegramClientError(
                        f"Telegram API returned error: {error_description}"
                    )
                
                logger.info(
                    "Telegram DM sent successfully",
                    extra={
                        "user_id": user_id,
                        "message_id": result.get("result", {}).get("message_id")
                    }
                )
                
                return result
                
        except httpx.HTTPStatusError as e:
            last_error = e
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.warning(
                "Telegram API HTTP error",
                extra={
                    "user_id": user_id,
                    "attempt": attempt + 1,
                    "error": error_msg
                }
            )
            
        except httpx.RequestError as e:
            last_error = e
            logger.warning(
                "Telegram API request error",
                extra={
                    "user_id": user_id,
                    "attempt": attempt + 1,
                    "error": str(e)
                }
            )
            
        except TelegramClientError as e:
            last_error = e
            logger.warning(
                "Telegram API error",
                extra={
                    "user_id": user_id,
                    "attempt": attempt + 1,
                    "error": str(e)
                }
            )
        
        # Wait before retrying (except on last attempt)
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
    
    # All retries exhausted
    error_message = f"Failed to send Telegram DM after {max_retries} attempts: {last_error}"
    logger.error(
        "Telegram DM sending failed",
        extra={
            "user_id": user_id,
            "max_retries": max_retries,
            "last_error": str(last_error)
        }
    )
    
    raise TelegramClientError(error_message)
