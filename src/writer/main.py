import asyncio
import signal
import sys
import os
import logging
from sqlalchemy import text
from src.shared.database import init_database, get_db_session
from .queue_processor import message_processor
from src.shared.rabbit_mq import rabbitmq_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WriteService:
    def __init__(self):
        self.running = False
        self.instance_id = os.getenv("HOSTNAME", "consumer-unknown")
        
    async def start(self):
        """Start the message queue consumer service"""
        self.running = True
        logger.info(f"Starting Writer Service - Instance: {self.instance_id}")
        
        try:
            # Initialize database
            init_database()
            logger.info("Database initialized")
            
            # Test database connection
            with get_db_session() as db:
                db.execute(text("SELECT 1"))
            logger.info("Database connection verified")
            
            # Start consuming messages
            await message_processor.start_consumer()
            logger.info("Message queue consumer started successfully")
            
            # Keep the consumer running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Writer service error: {e}")
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
        """Stop the writer service"""
        self.running = False
        logger.info("Writer service stop requested")

# Global writer instance
write_service = WriteService()

def signal_handler(signum):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    write_service.stop()

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(write_service.start())
    except KeyboardInterrupt:
        logger.error("Writer service stopped by user")
    except Exception as e:
        logger.error(f"Writer service failed: {e}")
        sys.exit(1)
    
    logger.info("Writer service shutdown complete")