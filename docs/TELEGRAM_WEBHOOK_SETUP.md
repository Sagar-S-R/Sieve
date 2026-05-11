# Telegram Webhook Setup Guide

This guide explains how to connect your local Sieve bot to Telegram using webhooks.

## Prerequisites

- Telegram bot token (from BotFather)
- Cloudflare Tunnel running (or ngrok as alternative)
- API Gateway running on localhost:8000

## Step 1: Start Cloudflare Tunnel

Run Cloudflare Tunnel to expose your local API Gateway:

```bash
cloudflared tunnel --url http://localhost:8000
```

This will output a public URL like: `https://random-subdomain.trycloudflare.com`

## Step 2: Set Telegram Webhook

Use the provided script to set the webhook URL:

```bash
python scripts/set_webhook.py
```

The script will:
1. Read your `TELEGRAM_BOT_TOKEN` from `.env`
2. Prompt you for the Cloudflare Tunnel URL
3. Set the webhook to `https://your-tunnel-url.trycloudflare.com/webhook`
4. Verify the webhook was set successfully

### Manual Webhook Setup (Alternative)

If you prefer to set the webhook manually:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-tunnel-url.trycloudflare.com/webhook"}'
```

Replace:
- `<YOUR_BOT_TOKEN>` with your actual bot token
- `your-tunnel-url.trycloudflare.com` with your Cloudflare Tunnel URL

## Step 3: Verify Webhook

Check webhook status:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

You should see:
- `url`: Your webhook URL
- `has_custom_certificate`: false
- `pending_update_count`: 0 (if no pending messages)

## Step 4: Test the Bot

1. Open Telegram and search for `@sieve7_bot`
2. Send `/start` to the bot
3. Add the bot to a group
4. Send a message like: "Submit assignment tomorrow at 5pm"
5. Check Docker logs: `docker-compose logs -f text_extractor`

## Important Notes

### Cloudflare Tunnel Must Stay Running

The Cloudflare Tunnel process must remain active for the webhook to work. If you close the terminal or stop the tunnel, Telegram cannot reach your local server.

### Bot Privacy Mode

For the bot to read all messages in a group (not just commands), you must disable Privacy Mode:

1. Open BotFather in Telegram
2. Send `/mybots`
3. Select your bot
4. Go to Bot Settings > Group Privacy
5. Turn OFF Privacy Mode

### Webhook vs Polling

This system uses webhooks (push-based) instead of polling (pull-based). Webhooks are more efficient and provide real-time message delivery.

## Troubleshooting

### Webhook not receiving messages

1. Check Cloudflare Tunnel is running
2. Verify webhook URL is correct: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
3. Check API Gateway logs: `docker-compose logs -f api_gateway`
4. Ensure Privacy Mode is disabled in BotFather

### "Connection refused" errors

- Make sure API Gateway is running: `docker-compose ps`
- Verify port 8000 is accessible: `curl http://localhost:8000/health`

### Messages not being processed

1. Check RabbitMQ is running: `docker-compose ps rabbitmq`
2. Check text_extractor logs: `docker-compose logs -f text_extractor`
3. Verify message contains triage keywords (see `api_gateway/routers/webhook.py`)

## Bot Information

- Bot Username: `@sieve7_bot`
- Bot Token: `8775207286:AAEJ8qKopU_TS0AVzWC-bqLylxPgtIJyw0U`
- Webhook Endpoint: `/webhook`
- API Gateway Port: `8000`

## Quick Reference Commands

```bash
# Start Cloudflare Tunnel
cloudflared tunnel --url http://localhost:8000

# Set webhook
python scripts/set_webhook.py

# Check webhook status
curl "https://api.telegram.org/bot8775207286:AAEJ8qKopU_TS0AVzWC-bqLylxPgtIJyw0U/getWebhookInfo"

# Delete webhook (switch to polling)
curl -X POST "https://api.telegram.org/bot8775207286:AAEJ8qKopU_TS0AVzWC-bqLylxPgtIJyw0U/deleteWebhook"

# View API Gateway logs
docker-compose logs -f api_gateway

# View text_extractor logs
docker-compose logs -f text_extractor
```
