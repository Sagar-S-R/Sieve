import asyncio
import aio_pika
import json
import logging
from workers.media_extractor.core.config import settings
from workers.media_extractor.services.file_handler import download_telegram_file
from workers.media_extractor.services.database import (
    init_pool, close_pool, get_group_subscribers, save_tasks_atomic
)
from workers.media_extractor.graph.workflow import app
from workers.media_extractor.graph.state import AgentState
from workers.text_extractor.services.redis_client import is_message_processed, mark_message_processed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_message(message: aio_pika.IncomingMessage):
    """Process a message from the heavy_media_queue."""
    async with message.process(requeue=False):
        try:
            data = json.loads(message.body)
            file_id = data.get("file_id")
            user_id = data.get("user_id", 0)
            group_id = data.get("group_id")

            # Idempotency check — prevent duplicate processing
            message_id = data.get("message_id")
            if message_id and group_id:
                if is_message_processed(message_id, group_id):
                    logger.info(f"[!] Message {message_id} already processed. Skipping.")
                    return
                mark_message_processed(message_id, group_id)

            if not file_id:
                logger.error("No file_id in message")
                return

            # Download the file
            logger.info(f"[*] Downloading file {file_id}...")
            file_path = await download_telegram_file(file_id, settings.TELEGRAM_BOT_TOKEN)
            logger.info(f"[✓] File downloaded to {file_path}")

            # Create initial state
            state: AgentState = {
                "user_id": user_id,
                "group_id": group_id,
                "file_id": file_id,
                "file_path": file_path,
                "media_type": "",
                "raw_text": None,
                "extracted_data": None,
                "validation_error": None,
                "needs_human": False,
                "hitl_prompt": None
            }

            # Run the LangGraph workflow
            logger.info("[*] Starting media workflow...")
            result = await app.ainvoke(state)

            logger.info(f"[✓] Workflow finished. Media type: {result.get('media_type')}")

            if result.get("needs_human"):
                logger.info(f"[!] HITL triggered for user {result.get('user_id')}")
            elif result.get("extracted_data") and not result.get("needs_human"):
                # Fan-out to all group subscribers
                extracted = result.get("extracted_data")
                subscribers = await get_group_subscribers(group_id)
                if subscribers:
                    await save_tasks_atomic(
                        subscribers=subscribers,
                        group_id=group_id,
                        message_sender_id=user_id,
                        title=extracted.title,
                        action_required=extracted.action_required,
                        deadline=extracted.deadline
                    )
                    logger.info(f"[✓] Media task saved for {len(subscribers)} subscribers")
                else:
                    logger.warning(f"[!] No subscribers found for group {group_id}")

        except Exception as e:
            logger.error(f"[x] Error processing media message: {e}", exc_info=True)
            raise  # aio_pika will nack


async def main():
    logger.info("[*] Initializing DB pool...")
    await init_pool()
    logger.info("[✓] DB pool initialized")

    logger.info("[*] Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue('heavy_media_queue', durable=True)
    await queue.consume(process_message)

    logger.info("[✓] Consuming from heavy_media_queue. Press CTRL+C to exit.")
    await asyncio.Future()  # run forever


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[!] Shutting down...")
