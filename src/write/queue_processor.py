import logging
from typing import Dict, Any
from src.shared.database import get_db_session
from src.shared.models import MessageDB, MessageResponse
from src.shared.rabbit_mq import rabbitmq_manager
from src.shared.redis import redis_cache

logger = logging.getLogger(__name__)

class MessageProcessor:
    QUEUE_NAME = "message_processing_queue"
    
    @staticmethod
    async def process_message_from_queue(message_data: Dict[str, Any]):
        """Process a message received from RabbitMQ queue"""
        try:
            # Extract message data
            recipient_id = message_data.get("recipient_id")
            content = message_data.get("content")
            
            if not recipient_id or not content:
                logger.error(f"Invalid message data: {message_data}")
                return
            
            # Create message in database
            with get_db_session() as db:
                new_message = MessageDB(
                    recipient_id=recipient_id,
                    content=content,
                )
                db.add(new_message)
                db.commit()
                db.refresh(new_message)
                
                # Convert to response model for caching
                message_response = MessageResponse.model_validate(new_message)
                
                logger.info(f"Successfully processed message {new_message.id} for recipient {recipient_id}")
                
                # Cache the new message
                await redis_cache.cache_new_message(message_response)
                
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            raise
    
    @staticmethod
    async def start_consumer():
        """Start consuming messages from the queue"""
        try:
            # Connect to Redis cache
            await redis_cache.connect()
            
            await rabbitmq_manager.connect()
            await rabbitmq_manager.declare_queue(MessageProcessor.QUEUE_NAME)
            await rabbitmq_manager.consume_messages(
                MessageProcessor.QUEUE_NAME,
                MessageProcessor.process_message_from_queue
            )
            logger.info("Message Queue consumer started")
        except Exception as e:
            logger.error(f"Failed to start message queue consumer: {e}")
            raise

message_processor = MessageProcessor()