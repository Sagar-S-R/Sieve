import pika
import json
import logging
import asyncio
from workers.media_extractor.core.config import settings
from workers.media_extractor.services.file_handler import download_telegram_file
from workers.media_extractor.services.database import save_task
from workers.media_extractor.graph.workflow import app
from workers.media_extractor.graph.state import AgentState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_message(ch, method, properties, body):
    """Process a message from the heavy_media_queue."""
    logger.info(f"[x] Received {body.decode()}")
    
    try:
        data = json.loads(body)
        file_id = data.get("file_id")
        user_id = data.get("user_id", 0)
        group_id = data.get("group_id")
        
        if not file_id:
            logger.error("No file_id in message")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        
        # Download the file
        logger.info(f"[*] Downloading file {file_id}...")
        file_path = asyncio.run(download_telegram_file(file_id, settings.TELEGRAM_BOT_TOKEN))
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
        
        # Run the workflow
        logger.info("[*] Starting workflow...")
        result = app.invoke(state)
        
        logger.info(f"[x] Workflow finished. Media type: {result.get('media_type')}")
        
        if result.get("needs_human"):
            logger.info(f"[!] HITL triggered for user {result.get('user_id')}")
        elif result.get("extracted_data") and not result.get("needs_human"):
            # Save to database
            extracted = result.get("extracted_data")
            task_data = {
                "user_id": user_id,
                "group_id": group_id,
                "title": extracted.title,
                "action_required": extracted.action_required,
                "deadline": extracted.deadline
            }
            asyncio.run(save_task(task_data))
            logger.info("[✓] Task saved to DB!")
        
        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"[x] Error processing message: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    logger.info("[*] Connecting to RabbitMQ...")
    connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
    channel = connection.channel()
    
    channel.queue_declare(queue='heavy_media_queue', durable=True)
    
    logger.info('[*] Waiting for messages. To exit press CTRL+C')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='heavy_media_queue', on_message_callback=process_message)
    
    channel.start_consuming()


if __name__ == '__main__':
    main()
