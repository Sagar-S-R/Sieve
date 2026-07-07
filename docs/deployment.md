# Deployment Guide

This guide covers how to deploy the Sieve platform. Sieve relies on a microservices architecture running via Docker Compose. 

## Requirements
- Docker and Docker Compose installed
- A Telegram Bot Token (from BotFather)
- A Google API Key (for Gemini)

## Local Deployment (Docker Compose)

The easiest way to get Sieve running is via the provided `docker-compose.yml` file. This will spin up the database, message broker, cache, and all custom Python workers.

1. **Clone the repository and set up environment variables:**
   ```bash
   git clone <repo-url>
   cd Sieve
   cp .env.example .env
   ```
   Edit `.env` and insert your `TELEGRAM_BOT_TOKEN`, `GOOGLE_API_KEY`, and `GROQ_API_KEY`.

2. **Start the cluster:**
   ```bash
   docker-compose up -d --build
   ```

3. **Verify running containers:**
   ```bash
   docker-compose ps
   ```
   You should see:
   - `sieve_postgres`
   - `sieve_redis`
   - `sieve_rabbitmq`
   - `sieve_api_gateway`
   - `sieve_text_extractor`
   - `sieve_media_extractor`
   - `sieve_cron_notifier`

## Production Deployment Considerations

If deploying to a production environment (like AWS, GCP, or a Kubernetes cluster):

1. **Database:** Swap out the local PostgreSQL and Redis containers for managed services (e.g., AWS RDS and Elasticache). Update the `.env` database URLs accordingly.
2. **RabbitMQ:** Ensure RabbitMQ is configured with persistent storage and appropriate resource limits.
3. **Scaling:** The text and media extractor workers are completely stateless. You can scale them horizontally in Kubernetes or Docker Swarm depending on the volume of incoming messages.
4. **Secrets:** Do not use a `.env` file in production. Use a secrets manager (like AWS Secrets Manager or Kubernetes Secrets) to inject the environment variables.

For setting up the Telegram Webhook so the bot actually receives messages, please refer to [docs/TELEGRAM_WEBHOOK.md](TELEGRAM_WEBHOOK.md).
