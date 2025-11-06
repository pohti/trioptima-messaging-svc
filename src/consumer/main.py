import asyncio
import signal
import sys
import os
from sqlalchemy import text
from src.shared.database import init_database, get_db_session
from .consumer import message_processor
from src.shared.rabbit_mq import rabbitmq_manager

class ConsumerService:
    def __init__(self):
        self.running = False
        self.instance_id = os.getenv("HOSTNAME", "consumer-unknown")
        
    async def start(self):
        """Start the message consumer service"""
        self.running = True
        print(f"Starting Consumer Service - Instance: {self.instance_id}")
        
        try:
            # Initialize database
            init_database()
            print("Database initialized")
            
            # Test database connection
            with get_db_session() as db:
                db.execute(text("SELECT 1"))
            print("Database connection verified")
            
            # Start consuming messages
            await message_processor.start_consumer()
            print("Message consumer started successfully")
            
            # Keep the consumer running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Consumer service error: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            await rabbitmq_manager.close()
            print("RabbitMQ connection closed")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def stop(self):
        """Stop the consumer service"""
        self.running = False
        print("Consumer service stop requested")

# Global consumer instance
consumer_service = ConsumerService()

def signal_handler(signum):
    """Handle shutdown signals"""
    print(f"Received signal {signum}")
    consumer_service.stop()

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(consumer_service.start())
    except KeyboardInterrupt:
        print("Consumer service stopped by user")
    except Exception as e:
        print(f"Consumer service failed: {e}")
        sys.exit(1)
    
    print("Consumer service shutdown complete")