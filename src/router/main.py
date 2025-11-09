import os
import socket
import logging
import httpx
import json  # Add this import
from fastapi import FastAPI, HTTPException, Request, Query
from typing import List
from src.shared.models import (
    MessageCreateReq,
    MessagesFetchResponse
)
from src.shared.rabbit_mq import rabbitmq_manager
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTANCE_ID = os.getenv("HOSTNAME", socket.gethostname())

# Service URLs (only read and delete services)
READ_SERVICE_URL = os.getenv("READ_SERVICE_URL", "http://read-lb") 
DELETE_SERVICE_URL = os.getenv("DELETE_SERVICE_URL", "http://delete-lb")

# Queue name for write operations
MESSAGE_QUEUE = "message_processing_queue"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize RabbitMQ for publishing write messages
    try:
        await rabbitmq_manager.connect()
        await rabbitmq_manager.declare_queue(MESSAGE_QUEUE)
        logger.info("RabbitMQ initialized for message publishing")
    except Exception as e:
        logger.error(f"Failed to initialize RabbitMQ: {e}")
    
    print(f"Starting API Gateway instance: {INSTANCE_ID}")
    yield
    
    # Cleanup
    try:
        await rabbitmq_manager.close()
        logger.info("RabbitMQ connection closed")
    except Exception as e:
        logger.error(f"Error closing RabbitMQ connection: {e}")
    
    print(f"Shutting down API Gateway instance: {INSTANCE_ID}")

app = FastAPI(
    title="Messaging Service API Gateway",
    description="API Gateway for messaging microservices",
    version="1.0.0",
    lifespan=lifespan
)

# Health check endpoint
@app.get("/", summary="Health check endpoint")
def health_check(request: Request):
    return {
        "message": "Messaging Service",
        "instance_id": INSTANCE_ID,
    }

# Write operations - Publish directly to RabbitMQ
@app.post("/messages", summary="Submit a message (async)")
async def submit_message_async(message: MessageCreateReq):
    try:
        message_data = {
            "recipient_id": message.recipient_id,
            "content": message.content,
        }
        
        # Ensure RabbitMQ connection
        if not rabbitmq_manager.connection:
            await rabbitmq_manager.connect()
        
        # Declare queue if not exists
        await rabbitmq_manager.declare_queue(MESSAGE_QUEUE)
        
        # Publish message to queue
        await rabbitmq_manager.publish_message(MESSAGE_QUEUE, message_data)
        
        logger.info(f"Message queued successfully for recipient {message.recipient_id}")
        return {
            "status": "queued",
            "message": "Message has been queued for processing",
            "recipient_id": message.recipient_id
        }
        
    except Exception as e:
        logger.error(f"Failed to queue message: {e}")
        raise HTTPException(status_code=500, detail=f"Error queuing message: {str(e)}")

# Note: Removing /messages/sync endpoint since we're going fully async
# If you need sync, you can add it back by calling the write service directly

# Read operations - Route to Read Service
@app.get("/messages/{recipient_id}/new", response_model=MessagesFetchResponse, summary="Fetch new messages")
async def fetch_new_messages(recipient_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{READ_SERVICE_URL}/messages/{recipient_id}/new",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to read service: {e}")
        raise HTTPException(status_code=503, detail="Read service unavailable")
    except httpx.HTTPStatusError as e:
        logger.error(f"Read service error: {e.response.status_code} - {e.response.text}")
        
        # FIX: Parse the JSON response instead of using raw text
        try:
            error_detail = e.response.json()
            detail = error_detail.get("detail", "Read service error")
        except json.JSONDecodeError:
            detail = e.response.text
        
        raise HTTPException(status_code=e.response.status_code, detail=detail)

@app.get("/messages/{recipient_id}", response_model=MessagesFetchResponse, summary="Fetch multiple messages")
async def fetch_multiple_messages(
    recipient_id: str,
    start: int = Query(1, ge=1, description="Start index for pagination"),
    stop: int = Query(9, ge=1, description="Stop index for pagination")
):
    try:
        if stop < start:
            raise HTTPException(status_code=400, detail="stop must be greater than or equal to start")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{READ_SERVICE_URL}/messages/{recipient_id}",
                params={"start": start, "stop": stop},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Error connecting to read service: {e}")
        raise HTTPException(status_code=503, detail="Read service unavailable")
    except httpx.HTTPStatusError as e:
        logger.error(f"Read service error: {e.response.status_code} - {e.response.text}")
        
        # FIX: Parse the JSON response instead of using raw text
        try:
            error_detail = e.response.json()
            detail = error_detail.get("detail", "Read service error")
        except json.JSONDecodeError:
            detail = e.response.text
        
        raise HTTPException(status_code=e.response.status_code, detail=detail)

# Delete operations - Route to Delete Service (FIXED)
@app.delete("/messages/{message_id}", summary="Delete a message")
async def delete_message(message_id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{DELETE_SERVICE_URL}/messages/{message_id}",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to delete service: {e}")
        raise HTTPException(status_code=503, detail="Delete service unavailable")
    except httpx.HTTPStatusError as e:
        logger.error(f"Delete service error: {e.response.status_code} - {e.response.text}")
        
        # FIX: Parse the JSON response instead of using raw text
        try:
            error_detail = e.response.json()
            # Extract the actual detail message
            detail = error_detail.get("detail", "Delete service error")
        except json.JSONDecodeError:
            # Fallback if response is not JSON
            detail = e.response.text
        
        raise HTTPException(status_code=e.response.status_code, detail=detail)

@app.delete("/messages", summary="Delete multiple messages")
async def delete_multiple_messages(message_ids: List[int] = Query(...)):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{DELETE_SERVICE_URL}/messages",
                params={"message_ids": message_ids},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to delete service: {e}")
        raise HTTPException(status_code=503, detail="Delete service unavailable")
    except httpx.HTTPStatusError as e:
        logger.error(f"Delete service error: {e.response.status_code} - {e.response.text}")
        
        # FIX: Parse the JSON response instead of using raw text
        try:
            error_detail = e.response.json()
            # Extract the actual detail message
            detail = error_detail.get("detail", "Delete service error")
        except json.JSONDecodeError:
            # Fallback if response is not JSON
            detail = e.response.text
        
        raise HTTPException(status_code=e.response.status_code, detail=detail)