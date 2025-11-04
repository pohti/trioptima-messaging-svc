from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Messaging Service API",
    description="A REST API for sending and retrieving messages",
    version="1.0.0"
)

# Simple data model
class Item(BaseModel):
    name: str
    price: float
    description: str = None

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Hello world! The service is up and running."}

# TODO: 
# Post message

# Fetch new messages by user id

# Delete a single message by message id

# Delete multiple messages by message ids

# Fetch multiple messages (according to start and stop index, ordered by time)