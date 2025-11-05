from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .database import get_db, init_database
from typing import List
from .models import (
    MessageCreate, 
    MessageResponse, 
    MessagesFetchResponse
)
from .service import MessageService
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_database()

    yield
    # Shutdown logic

app = FastAPI(
    title="Messaging Service API",
    description="A REST API for sending and retrieving messages",
    version="1.0.0",
    lifespan=lifespan
)


# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Hello world! The service is up and running."}


# Submit a message
@app.post("/messages", response_model=MessageResponse, summary="Submit a message")
async def submit_message(
    message: MessageCreate,     
    db: Session = Depends(get_db)
):
    try:
        return MessageService.create_message(message, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating message: {str(e)}")

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