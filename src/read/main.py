import os
import socket
import logging
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from src.shared.database import get_db, init_database
from src.shared.redis import redis_cache
from src.shared.models import MessagesFetchResponse
from .service import ReaderService
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTANCE_ID = os.getenv("HOSTNAME", socket.gethostname())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_database()
    
    # Connect to Redis cache
    try:
        await redis_cache.connect()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.error(f"Failed to connect to Redis cache: {e}")
        # Continue without cache
    
    print(f"Starting messaging Reader service instance: {INSTANCE_ID}")
    yield
    
    # Cleanup
    try:
        await redis_cache.close()
        logger.info("Redis cache connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis cache: {e}")
    
    print(f"Shutting down messaging Reader service instance: {INSTANCE_ID}")

app = FastAPI(
    title="Messaging Service Reader API",
    description="A REST API for reading messages with Redis caching",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", summary="Health check endpoint")
def health_check(request: Request):
    return {
        "message": "Reader Service with Redis Cache",
        "instance_id": INSTANCE_ID,
        "host": request.headers.get("host"),
    }

# Fetch new messages by user email
@app.get("/messages/{recipient_id}/new", response_model=MessagesFetchResponse, summary="Fetch new messages")
async def fetch_new_messages(
    recipient_id: str,
    db: Session = Depends(get_db)
):
    try:
        return await ReaderService.fetch_new_messages(recipient_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching new messages: {str(e)}")

# Fetch multiple messages (according to start and stop index, ordered by time)
@app.get("/messages/{recipient_id}", response_model=MessagesFetchResponse, summary="Fetch multiple messages")
async def fetch_multiple_messages(
    recipient_id: str,
    start: int = Query(1, ge=1, description="Start index for pagination"),
    stop: int = Query(9, ge=1, description="Stop index for pagination"),
    db: Session = Depends(get_db)
):
    try:
        if stop < start:
            raise HTTPException(
                status_code=400, 
                detail="stop must be greater than or equal to start"
            )
        
        return ReaderService.fetch_messages_by_index(recipient_id, start, stop, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")