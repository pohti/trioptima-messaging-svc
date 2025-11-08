import os
import socket
import logging
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from src.shared.database import get_db, init_database
from typing import List
from .service import DeleteService
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTANCE_ID = os.getenv("HOSTNAME", socket.gethostname())

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    print(f"Starting Delete service instance: {INSTANCE_ID}")
    yield
    print(f"Shutting down Delete service instance: {INSTANCE_ID}")

app = FastAPI(
    title="Messaging Delete Service",
    description="Microservice for deleting messages",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", summary="Health check endpoint")
def health_check(request: Request):
    return {
        "message": "Delete Service",
        "instance_id": INSTANCE_ID,
        "host": request.headers.get("host"),
    }

@app.delete("/messages/{message_id}", summary="Delete a message")
async def delete_message(message_id: int, db: Session = Depends(get_db)):
    try:
        result = DeleteService.delete_message(message_id, db)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting message: {str(e)}")

@app.delete("/messages", summary="Delete multiple messages")
async def delete_multiple_messages(message_ids: List[int] = Query(...), db: Session = Depends(get_db)):
    try:
        result = DeleteService.delete_multiple_messages(message_ids, db)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting messages: {str(e)}")