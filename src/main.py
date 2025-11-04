from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Simple data model
class Item(BaseModel):
    name: str
    price: float
    description: str = None

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Get endpoint with path parameter
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "query": q}

# Post endpoint
@app.post("/items/")
def create_item(item: Item):
    return {"item_name": item.name, "item_price": item.price}

# Get endpoint returning a list
@app.get("/users/")
def read_users():
    return [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"}
    ]

# Put endpoint
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_id": item_id, "item": item}

# Delete endpoint
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    return {"message": f"Item {item_id} deleted"}