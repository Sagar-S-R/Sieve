# Monitoring Guide

This guide explains how to monitor the health and performance of the Sieve system. Sieve operates as a set of distributed workers processing asynchronous queues.

## 1. Checking Container Health

You can check if all services are running and healthy using Docker Compose:
```bash
docker-compose ps
```

## 2. Viewing Service Logs

All services use structured logging. You can view the logs in real-time to monitor the pipeline.

**View all logs:**
```bash
docker-compose logs -f
```

**View specific component logs:**
- **API Gateway** (Check for incoming Telegram webhooks and dropped messages):
  ```bash
  docker-compose logs -f api_gateway
  ```
- **Text Extractor** (Check LangGraph intent classification and Gemini extractions):
  ```bash
  docker-compose logs -f text_extractor
  ```
- **Media Extractor** (Check Vision LLM extractions from images/PDFs):
  ```bash
  docker-compose logs -f media_extractor
  ```
- **Cron Notifier** (Check if reminders are being sent):
  ```bash
  docker-compose logs -f cron_notifier
  ```

## 3. RabbitMQ Message Queue Monitoring

RabbitMQ provides a web management UI. You can use it to see if messages are backing up in the queues (which indicates workers are down or overwhelmed).

1. Open a browser and navigate to `http://localhost:15672`.
2. Login with the default credentials (`guest` / `guest`).
3. Click on the **Queues** tab.
4. You should see two queues:
   - `fast_text_queue`: Should generally stay near 0 unless under heavy load.
   - `heavy_media_queue`: May have a small backlog during bulk image processing.

## 4. Database Verification

You can query PostgreSQL to check the status of tasks.

1. Connect to the database:
   ```bash
   docker exec -it sieve_postgres psql -U user -d sieve
   ```
2. Check total processed tasks:
   ```sql
   SELECT COUNT(*) FROM tasks;
   ```
3. Check for pending reminders (tasks where the deadline has passed but the reminder has not been sent):
   ```sql
   SELECT * FROM tasks WHERE deadline <= NOW() AND is_sent = FALSE;
   ```
   If this query returns results and they are not clearing out, check the `cron_notifier` logs for errors.
