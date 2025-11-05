# Messaging Service API

A REST API for sending and retrieving messages built with FastAPI and SQLAlchemy.

## What's in this repo?

- **NGINX**: As reverse proxy round-robin load balancer
- **FastAPI Application**: REST API framework
- **SQLAlchemy Models**: Database models
- **RabbitMQ**: To decouple how messages are processed
- **PostgreSQL**: Database for persisting messages
- **Docker Support**: `docker-compose` to orchestrate multiple containers (nginx, messaging service, rabbitMQ and postgres)


## Project Structure

```
├── src/
│   ├── main.py          
│   ├── models.py        
│   ├── service.py       
│   └── database.py      
├── requirements.txt    # python dependencies
├── Dockerfile          
├── docker-compose.yml  
└── Makefile
```

## Prerequisites

- **Docker** (version 20.0+)
- **Docker Compose** (version 2.0+)

## How to run the service (using docker-compose)

### 1. Clone and Build
```bash
# Clone the repository
git clone <repository-url>
cd trioptima-messaging-svc

# Build and start the service
docker-compose up --build
```

### 2. Access the API
- **API Base URL**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/

> Import [`api.postman_collection.json`](postman_collection.json) into Postman to test all API endpoints with pre-configured requests.
`baseUrl` value needs to be set in collection variables.

## Development Workflow

### Running in Development Mode (Recommended)
```bash
# Start with hot-reload (rebuilds on code changes)
docker-compose up --build

# or use make command
make up
```

## How to run locally (without Docker)

### Prerequisites
- Python 3.14+
- pip

### Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Using Make commands
```bash
make up # to build and run the service as docker container

make install # to install dependencies in the .venv folder

make clean # to clean up venv, db files and coverage files to start fresh
```

> If you are running the service for the first time, run `make install` first before you run `make python` or `make test`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/messages` | Create a new message |
| GET | `/messages/{recipient_id}/new` | Fetch new messages for a user |
| GET | `/messages/{recipient_id}?start=0&stop=10` | Fetch paginated messages (start and stop are inclusive) |
| DELETE | `/messages/{id}` | Delete a specific message |
| DELETE | `/messages` | Delete multiple messages |

### Example Usage
```bash
# Create a message
curl --location 'http://localhost:8000/messages' \
--header 'Content-Type: application/json' \
--data '{
    "recipient_id": "receiver",
    "content": "test"
}'

# Fetch messages
curl "http://localhost:8000/messages?recipient_id=receiver&start=0&stop=9"
```