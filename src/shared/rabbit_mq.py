import os
import json
import logging
from typing import Optional, Callable, Any
from contextlib import asynccontextmanager
import aio_pika
from aio_pika import connect_robust, Message, DeliveryMode
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue

logger = logging.getLogger(__name__)

class RabbitMQManager:
    def __init__(self):
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.url = os.getenv("RABBITMQ_URL")
        
    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            if not self.url:
                raise ValueError("RABBITMQ_URL environment variable not set")

            self.connection = await connect_robust(self.url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=1)
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def close(self):
        """Close RabbitMQ connection"""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
        logger.info("RabbitMQ connection closed")
    
    async def declare_queue(self, queue_name: str, durable: bool = True) -> AbstractQueue:
        """Declare a queue"""
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not initialized")
        
        queue = await self.channel.declare_queue(
            queue_name,
            durable=durable,
            auto_delete=False
        )
        return queue
    
    async def publish_message(self, queue_name: str, message_data: dict, durable: bool = True):
        """Publish a message to a queue"""
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not initialized")
        
        message_body = json.dumps(message_data).encode()
        message = Message(
            message_body,
            delivery_mode=DeliveryMode.PERSISTENT if durable else DeliveryMode.NOT_PERSISTENT
        )
        
        await self.channel.default_exchange.publish(
            message,
            routing_key=queue_name
        )
        logger.info(f"Published message to queue {queue_name}: {message_data}")
    
    async def consume_messages(
        self, 
        queue_name: str, 
        callback: Callable[[dict], Any],
        auto_ack: bool = False
    ):
        """Consume messages from a queue"""
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not initialized")
        
        queue = await self.declare_queue(queue_name)
        
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process(ignore_processed=True):
                try:
                    message_data = json.loads(message.body.decode())
                    logger.info(f"Processing message from {queue_name}: {message_data}")
                    
                    # Call the callback function
                    await callback(message_data)
                    
                    if not auto_ack:
                        await message.ack()  
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    if not auto_ack:
                        await message.nack(requeue=True)
                    raise
        
        await queue.consume(process_message, no_ack=auto_ack)
        logger.info(f"Started consuming messages from {queue_name}")

# Global RabbitMQ manager instance
rabbitmq_manager = RabbitMQManager()

@asynccontextmanager
async def get_rabbitmq_manager():
    """Context manager for RabbitMQ operations"""
    if not rabbitmq_manager.connection:
        await rabbitmq_manager.connect()
    yield rabbitmq_manager