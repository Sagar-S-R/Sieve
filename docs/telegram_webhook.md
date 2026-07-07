# Telegram Webhook Setup Guide

In order for Telegram to send chat messages to your local Sieve API Gateway, you need to expose your local port `8000` to the internet and register that URL with Telegram.

## 1. Exposing Localhost (Development)

For local development, `cloudflared` is recommended as it provides a free and secure HTTPS tunnel.

1. Ensure your Docker cluster is running (`docker-compose up -d`).
2. Run Cloudflare Tunnel pointing to your API Gateway container port:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
3. Cloudflare will output an HTTPS URL in the console (e.g., `https://random-words.trycloudflare.com`). Note this URL down.

## 2. Registering the Webhook

Once you have your public HTTPS URL (either from Cloudflare or your production domain), you must register it with Telegram's API.

Run this `curl` command in your terminal, replacing the placeholders:
- `<YOUR_BOT_TOKEN>` with your actual Telegram bot token.
- `<YOUR_PUBLIC_URL>` with your Cloudflare URL.

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "<YOUR_PUBLIC_URL>/webhook"}'
```

**Note:** Ensure you append `/webhook` to the end of your URL, as this matches the route defined in the API Gateway.

## 3. Verification

If successful, Telegram will respond with:
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

Now, any message sent to a group containing your bot will be forwarded directly to your API Gateway!
