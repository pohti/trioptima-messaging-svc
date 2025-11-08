import os
import socket
import logging
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from src.shared.database import get_db, init_database
from typing import List
from src.shared.models import (
    MessageResponse, 
    MessagesFetchResponse
)
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
    print(f"Starting messaging Reader service instance: {INSTANCE_ID}")
    yield
    print(f"Shutting down messaging Reader service instance: {INSTANCE_ID}")

app = FastAPI(
    title="Messaging Service Reader API",
    description="A REST API for reading and deleting messages",
    version="1.0.0",
    lifespan=lifespan
)

# Fetch new messages by user email
@app.get("/messages/{recipient_id}/new", response_model=MessagesFetchResponse, summary="Fetch new messages")
async def fetch_new_messages(
    recipient_id: str,
    db: Session = Depends(get_db)
):
    try:
        return ReaderService.fetch_new_messages(recipient_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching new messages: {str(e)}")


# Fetch multiple messages (according to start and stop index, ordered by time)
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
        
        return ReaderService.fetch_messages_by_index(recipient_id, start, stop, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")