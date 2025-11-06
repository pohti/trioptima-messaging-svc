import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from src.shared.database import get_db_session
from src.shared.models import MessageDB, MessageCreate
from src.shared.rabbit_mq import rabbitmq_manager

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
                
                logger.info(f"Successfully processed message {new_message.id} for recipient {recipient_id}")
                
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            raise
    
    @staticmethod
    async def start_consumer():
        """Start consuming messages from the queue"""
        try:
            await rabbitmq_manager.connect()
            await rabbitmq_manager.declare_queue(MessageProcessor.QUEUE_NAME)
            await rabbitmq_manager.consume_messages(
                MessageProcessor.QUEUE_NAME,
                MessageProcessor.process_message_from_queue
            )
            logger.info("Message consumer started")
        except Exception as e:
            logger.error(f"Failed to start message consumer: {e}")
            raise

message_processor = MessageProcessor()