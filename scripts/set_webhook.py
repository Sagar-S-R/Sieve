#!/usr/bin/env python3
"""
Script to set Telegram webhook URL
"""
import requests
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env file")
    sys.exit(1)

# Cloudflare tunnel URL
TUNNEL_URL = "https://parts-coding-park-logging.trycloudflare.com"
WEBHOOK_URL = f"{TUNNEL_URL}/webhook"

def set_webhook():
    """Set the webhook URL for the Telegram bot"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {
        "url": WEBHOOK_URL,
        "drop_pending_updates": True  # Clear any pending updates
    }
    
    print(f"Setting webhook to: {WEBHOOK_URL}")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            print("✓ Webhook set successfully!")
            print(f"  URL: {WEBHOOK_URL}")
            return True
        else:
            print(f"✗ Failed to set webhook: {result.get('description')}")
            return False
    else:
        print(f"✗ HTTP Error {response.status_code}: {response.text}")
        return False

def get_webhook_info():
    """Get current webhook information"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    response = requests.get(url)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            info = result.get("result", {})
            print("\nCurrent Webhook Info:")
            print(f"  URL: {info.get('url', 'Not set')}")
            print(f"  Pending updates: {info.get('pending_update_count', 0)}")
            print(f"  Last error: {info.get('last_error_message', 'None')}")
            return info
    return None

def delete_webhook():
    """Delete the current webhook"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    response = requests.post(url)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            print("✓ Webhook deleted successfully!")
            return True
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("Telegram Webhook Setup")
    print("=" * 60)
    
    # Show current webhook info
    print("\n[1] Checking current webhook...")
    get_webhook_info()
    
    # Set new webhook
    print("\n[2] Setting new webhook...")
    if set_webhook():
        print("\n[3] Verifying new webhook...")
        get_webhook_info()
        print("\n" + "=" * 60)
        print("SUCCESS! Your bot is now connected to:")
        print(f"  {WEBHOOK_URL}")
        print("=" * 60)
        print("\nYou can now test your bot:")
        print("  1. Open Telegram")
        print("  2. Search for @sieve7_bot")
        print("  3. Send /start")
        print("=" * 60)
    else:
        print("\nFailed to set webhook. Please check your bot token and try again.")
        sys.exit(1)
