import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.database import get_db
from src.models import Base


# Create a temporary database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as c:
        yield c
    
    # Drop tables after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_message():
    return {
        "recipient_id": "john.doe@example.com",
        "content": "Hello, this is a test message!",
    }

class TestMessageSvcAPI:
    
    def test_health_check(self, client):
        response = client.get("/")
        assert response.status_code == 200

    
    def test_submit_message(self, client, sample_message):
        """Should be able to submit a valid message"""
        response = client.post("/messages", json=sample_message)
        assert response.status_code == 200
        
        data = response.json()
        assert data["recipient_id"] == sample_message["recipient_id"]
        assert data["content"] == sample_message["content"]
        assert "id" in data
        assert data["seen"] == False

    def test_submit_message_validation_error(self, client):
        """Should return 422 for empty recipient_id"""
        invalid_message = {
            "recipient_id": "",
            "content": "test"
        }
        response = client.post("/messages", json=invalid_message)
        assert response.status_code == 422

    def test_submit_message_validation_error(self, client):
        """Should return 422 for empty content"""
        invalid_message = {
            "recipient_id": "test@example.com",
            "content": ""
        }
        response = client.post("/messages", json=invalid_message)
        assert response.status_code == 422

    # fetch new messages should be empty when no messages exist

    # new message should be included in fetch new messages

    # already fetched message should not be included in fetch new messages

    # should be able to delete specified message

    # should return 404 when deleting non-existent message

    # should be able to delete multiple messages

    # should return 422 when deleting with empty message_ids

    # should be able to fetch messages with start, stop index

    # messages should be returned in ascending order of id