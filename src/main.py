from fastapi import FastAPI, Query
from typing import List
from .models import (
    MessageCreate, 
    MessageResponse, 
)

app = FastAPI(
    title="Messaging Service API",
    description="A REST API for sending and retrieving messages",
    version="1.0.0"
)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Hello world! The service is up and running."}


# Post message
@app.post("/messages", response_model=MessageResponse, summary="Submit a message")
async def submit_message(message: MessageCreate):
    return MessageResponse(
        id=1,
        recipient_email=message.recipient_email,
        content=message.content,
        sender_email=message.sender_email,
        created_at="2024-01-01T00:00:00Z",
        seen=False
    )

# Fetch new messages by user email
@app.get("/messages/new", response_model=List[MessageResponse], summary="Fetch new messages")
async def fetch_messages(email: str):
    return [
        MessageResponse(
            id=1,
            recipient_email=email,
            content="Hello!",
            sender_email="user@example.com",
            created_at="2024-01-01T00:00:00Z",
            seen=False
        ),
        MessageResponse(
            id=2,
            recipient_email=email,
            content="How are you?",
            sender_email=None,
            created_at="2024-01-02T00:00:00Z",
            seen=False
        )
    ]

# Delete a single message by message id
@app.delete("/messages/{message_id}", summary="Delete a message")
async def delete_message(message_id: int):
    return {"message": f"Message with id {message_id} deleted."}

# Delete multiple messages by message ids
@app.delete("/messages", summary="Delete multiple messages")
async def delete_multiple_messages(message_ids: List[int] = Query(...)):
    return {"message": f"Messages with ids {message_ids} deleted."}

# Fetch multiple messages (according to start and stop index, ordered by time)
# note: could improve this by allowing filtering by created_at range
@app.get("/messages", response_model=List[MessageResponse], summary="Fetch multiple messages")
async def fetch_multiple_messages(start: int = 0, stop: int = 10):
    messages = []
    for i in range(start, stop):
        messages.append(
            MessageResponse(
                id=i,
                recipient_email="user@example.com",
                content=f"Message {i}",
                sender_email=None,
                created_at="2024-01-01T00:00:00Z",
                seen=False
            )
        )
    return messages