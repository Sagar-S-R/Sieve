import aio_pika
import json
from api_gateway.core.config import settings


async def publish_to_queue(queue_name: str, payload: dict) -> bool:
    """
    Publish message to RabbitMQ queue.
    
    Args:
        queue_name: Name of the queue (fast_text_queue or heavy_media_queue)
        payload: Message payload as dictionary
        
    Returns:
        True if published successfully, False otherwise
    """
    try:
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        
        async with connection:
            # Create channel
            channel = await connection.channel()
            
            # Declare queue (idempotent)
            queue = await channel.declare_queue(queue_name, durable=True)
            
            # Publish message
            message = aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            
            await channel.default_exchange.publish(
                message,
                routing_key=queue_name
            )
        
        return True
        
    except Exception as e:
        print(f"Error publishing to {queue_name}: {e}")
        return False
