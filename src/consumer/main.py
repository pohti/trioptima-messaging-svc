import asyncio
import logging
import signal
import sys
import os
from src.shared.database import init_database, get_db_session
from src.consumer.main import message_processor
from src.shared.rabbit_mq import rabbitmq_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/consumer.log') if os.path.exists('/app/logs') else logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ConsumerService:
    def __init__(self):
        self.running = False
        self.instance_id = os.getenv("HOSTNAME", "consumer-unknown")
        
    async def start(self):
        """Start the message consumer service"""
        self.running = True
        logger.info(f"Starting Consumer Service - Instance: {self.instance_id}")
        
        try:
            # Initialize database
            init_database()
            logger.info("Database initialized")
            
            # Test database connection
            with get_db_session() as db:
                db.execute("SELECT 1")
            logger.info("Database connection verified")
            
            # Start consuming messages
            await message_processor.start_consumer()
            logger.info("Message consumer started successfully")
            
            # Keep the consumer running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Consumer service error: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            await rabbitmq_manager.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def stop(self):
        """Stop the consumer service"""
        self.running = False
        logger.info("Consumer service stop requested")

# Global consumer instance
consumer_service = ConsumerService()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    consumer_service.stop()

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(consumer_service.start())
    except KeyboardInterrupt:
        logger.info("Consumer service stopped by user")
    except Exception as e:
        logger.error(f"Consumer service failed: {e}")
        sys.exit(1)
    
    logger.info("Consumer service shutdown complete")