import httpx
import os
from pathlib import Path


async def download_telegram_file(file_id: str, bot_token: str) -> str:
    """
    Download a file from Telegram and save it locally.
    
    Args:
        file_id: Telegram file ID
        bot_token: Telegram bot token
        
    Returns:
        Local file path where the file was saved
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get file info
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"
        response = await client.get(get_file_url, params={"file_id": file_id})
        response.raise_for_status()
        
        file_info = response.json()
        if not file_info.get("ok"):
            raise Exception(f"Telegram API error: {file_info.get('description')}")
        
        file_path = file_info["result"]["file_path"]
        
        # Download the file
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        file_response = await client.get(download_url)
        file_response.raise_for_status()
        
        # Save to /tmp
        tmp_dir = Path("/tmp/media_extractor")
        tmp_dir.mkdir(exist_ok=True)
        
        local_filename = f"{file_id}_{Path(file_path).name}"
        local_path = tmp_dir / local_filename
        
        with open(local_path, "wb") as f:
            f.write(file_response.content)
        
        return str(local_path)
