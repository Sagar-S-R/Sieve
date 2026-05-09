import pika
import json
import logging
import time
import sys
import asyncio
import threading
from prometheus_client import start_http_server
from workers.text_extractor.core.config import settings
from workers.text_extractor.core.metrics import workflow_duration
from workers.text_extractor.graph.workflow import app
from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.redis_client import check_hitl_lock, clear_hitl_lock
from workers.text_extractor.services.database import save_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_message(ch, method, properties, body):
    """Process message from RabbitMQ."""
    logger.info(f"[x] Received {body.decode()}")
    
    workflow_start_time = time.time()
    
    try:
        data = json.loads(body)
        user_id = data.get("user_id", 0)
        
        # Check for HITL lock
        saved_state = check_hitl_lock(user_id)
        
        if saved_state:
            # User is replying to clarification request
            logger.info(f"[HITL] Loading saved state for user {user_id}")
            
            # Import merge node
            from workers.text_extractor.nodes.hitl_merge_node import merge_hitl_clarification
            
            # Reconstruct state with saved data
            state: AgentState = {
                "user_id": saved_state.get("user_id", user_id),
                "group_id": saved_state.get("group_id"),
                "message_text": data.get("message_text", ""),  # User's clarification
                "intent": "NEW",  # Force NEW intent
                "db_context": saved_state.get("message_text", ""),  # Original message
                "extracted_data": saved_state.get("extracted_data"),
                "validation_error": None,
                "needs_human": False,
                "hitl_prompt": None
            }
            
            # Merge clarification with original extraction
            state = merge_hitl_clarification(state)
            
            # Skip workflow, go straight to saving
            result = state
        else:
            # New message
            state: AgentState = {
                "user_id": user_id,
                "group_id": data.get("group_id"),
                "message_text": data.get("message_text", ""),
                "intent": None,
                "db_context": None,
                "extracted_data": None,
                "validation_error": None,
                "needs_human": False,
                "hitl_prompt": None
            }
            
            # Run workflow
            result = app.invoke(state)
        
        # Track workflow duration
        workflow_duration.observe(time.time() - workflow_start_time)
        
        logger.info(f"[x] Workflow finished. Intent: {result.get('intent')}")
        
        if result.get("needs_human"):
            logger.info(f"[!] HITL triggered for user {result.get('user_id')}")
        elif result.get("intent") == "NEW" and not result.get("needs_human"):
            # Save task
            extracted_data = result.get('extracted_data')
            if extracted_data:
                task_data = {
                    'user_id': result.get('user_id'),
                    'group_id': result.get('group_id'),
                    'title': extracted_data.title,
                    'action_required': extracted_data.action_required,
                    'deadline': extracted_data.deadline
                }
                asyncio.run(save_task(task_data))
                logger.info("[✓] Task saved!")
                
                # Clear HITL lock if this was a resolution
                if saved_state:
                    clear_hitl_lock(result.get('user_id'))
                    logger.info("[✓] HITL lock cleared")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"[x] Error: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def connect_to_rabbitmq():
    """Connect to RabbitMQ with retry."""
    max_retries = settings.RABBITMQ_MAX_RETRIES
    initial_delay = settings.RABBITMQ_INITIAL_RETRY_DELAY
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[*] Connecting to RabbitMQ (attempt {attempt}/{max_retries})...")
            connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue='fast_text_queue', durable=True)
            logger.info("[✓] Connected to RabbitMQ")
            return connection, channel
        except Exception as e:
            logger.error(f"[x] Connection failed: {e}")
            if attempt == max_retries:
                logger.critical("[!] Max retries exhausted. Exiting.")
                sys.exit(1)
            delay = initial_delay * (2 ** (attempt - 1))
            logger.info(f"[*] Retrying in {delay} seconds...")
            time.sleep(delay)


def main():
    # Start Prometheus metrics server
    metrics_port = getattr(settings, 'PROMETHEUS_PORT', 8001)
    start_http_server(metrics_port)
    logger.info(f"[✓] Prometheus metrics exposed on port {metrics_port}")
    
    connection, channel = connect_to_rabbitmq()
    logger.info('[*] Waiting for messages. To exit press CTRL+C')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='fast_text_queue', on_message_callback=process_message)
    channel.start_consuming()


if __name__ == '__main__':
    main()
