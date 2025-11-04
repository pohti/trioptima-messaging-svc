from fastapi import FastAPI
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
        is_fetched=False
    )

# Fetch new messages by user email
# @app.get("/messages", response_model=List[MessageResponse], summary="Fetch new messages")
# async def fetch_messages(email: str):
#     pass  # Implement message fetching logic here

# Delete a single message by message id

# Delete multiple messages by message ids

# Fetch multiple messages (according to start and stop index, ordered by time)