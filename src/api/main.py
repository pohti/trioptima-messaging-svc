import os
import socket
import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from src.shared.database import get_db, init_database
from src.shared.rabbit_mq import rabbitmq_manager
from src.consumer import message_processor
from typing import List
from src.shared.models import (
    MessageCreateReq, 
    MessageResponse, 
    MessagesFetchResponse
)
from .service import MessageService
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTANCE_ID = os.getenv("HOSTNAME", socket.gethostname())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_database()
    
    # Initialize RabbitMQ
    try:
        await rabbitmq_manager.connect()
        await rabbitmq_manager.declare_queue(MessageService.MESSAGE_QUEUE)
        
        # Start message consumer in background
        # TODO: run this service as a separate container using docker-compose
        asyncio.create_task(message_processor.start_consumer())
        logger.info("RabbitMQ initialized and consumer started")
    except Exception as e:
        logger.error(f"Failed to initialize RabbitMQ: {e}")
        # You might want to decide whether to continue without RabbitMQ or fail here
    
    print(f"Starting messaging service instance: {INSTANCE_ID}")
    yield
    
    # Shutdown logic
    try:
        await rabbitmq_manager.close()
        logger.info("RabbitMQ connection closed")
    except Exception as e:
        logger.error(f"Error closing RabbitMQ connection: {e}")
    
    print(f"Shutting down messaging service instance: {INSTANCE_ID}")

app = FastAPI(
    title="Messaging Service API",
    description="A REST API for sending and retrieving messages",
    version="1.0.0",
    lifespan=lifespan
)

# Health check endpoint
@app.get("/", summary="Health check endpoint")
def health_check(request: Request):
    # return instance id and request headers for debugging
    return {
        "message": f"Hello World! This is V2 of messaging service.",
        "instance_id": INSTANCE_ID,
        "host": request.headers.get("host"),
    }

# Submit a message (async with RabbitMQ)
@app.post("/messages", summary="Submit a message (async)")
async def submit_message_async(
    message: MessageCreateReq,     
):
    try:
        result = await MessageService.queue_message(message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error queuing message: {str(e)}")

# Fetch new messages by user email
@app.get("/messages/{recipient_id}/new", response_model=MessagesFetchResponse, summary="Fetch new messages")
async def fetch_new_messages(
    recipient_id: str,
    db: Session = Depends(get_db)
):
    try:
        return MessageService.fetch_new_messages(recipient_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching new messages: {str(e)}")

# Delete a single message by message id
@app.delete("/messages/{message_id}", summary="Delete a message")
async def delete_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    try:
        result = MessageService.delete_message(message_id, db)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting message: {str(e)}")

# Delete multiple messages by message ids
@app.delete("/messages", summary="Delete multiple messages")
async def delete_multiple_messages(
    message_ids: List[int] = Query(...),
    db: Session = Depends(get_db)
):
    try:
        result = MessageService.delete_multiple_messages(message_ids, db)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting messages: {str(e)}")

# Fetch multiple messages (according to start and stop index, ordered by time)
# note: could improve this by allowing filtering by created_at range
@app.get("/messages/{recipient_id}", response_model=MessagesFetchResponse, summary="Fetch multiple messages")
async def fetch_multiple_messages(
    recipient_id: str,
    start: int = Query(1, ge=1, description="Start index for pagination (0-based)"),
    stop: int = Query(9, ge=1, description="Stop index for pagination (inclusive)"),
    db: Session = Depends(get_db)
):
    try:
        if stop < start:
            raise HTTPException(
                status_code=400, 
                detail="stop must be greater than or equal to start"
            )
        
        return MessageService.fetch_messages_by_index(recipient_id, start, stop, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")