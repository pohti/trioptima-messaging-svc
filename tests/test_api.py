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
def sample_message1():
    return {
        "recipient_id": "user_one@example.com",
        "content": "Hello, this is a test message!",
    }

@pytest.fixture
def sample_message2():
    return {
        "recipient_id": "user_one@example.com",
        "content": "Hello, this is another test message!",
    }

@pytest.fixture
def sample_message3():
    return {
        "recipient_id": "user_two@example.com",
        "content": "Hello, this message is for user_two!",
    }

class TestMessageSvcAPI:
    
    def test_health_check(self, client):
        response = client.get("/")
        assert response.status_code == 200

    
    def test_submit_message(self, client, sample_message1):
        """Should be able to submit a valid message"""
        response = client.post("/messages", json=sample_message1)
        assert response.status_code == 200
        
        data = response.json()
        assert data["recipient_id"] == sample_message1["recipient_id"]
        assert data["content"] == sample_message1["content"]
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

    def test_fetch_new_messages_empty(self, client):
        """Fetch new messages should be empty when no messages exist"""
        response = client.get("/messages/new", params={"recipient_id": "user_one@example.com"})
        assert response.status_code == 200
        assert response.json() == {"messages": [], "count": 0}

    def test_fetch_new_messages_includes_new_message(self, client, sample_message1, sample_message2):
        """Fetch new messages should include messages sent after the request"""
        user_email = "user_one@example.com"

        client.post("/messages", json=sample_message1)
        client.post("/messages", json=sample_message2)
        response = client.get(f"/messages/{user_email}/new")
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert response.json()["messages"][0]["content"] == sample_message1["content"]
        assert response.json()["messages"][1]["content"] == sample_message2["content"]

    def test_fetch_new_messages_should_not_include_other_users_messages(self, client, sample_message1, sample_message2, sample_message3):
        """Fetch new messages should not include messages for other users"""
        user_one_email = "user_one@example.com"

        client.post("/messages", json=sample_message1)
        client.post("/messages", json=sample_message2)
        client.post("/messages", json=sample_message3)
        response = client.get(f"/messages/{user_one_email}/new")
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert response.json()["messages"][0]["content"] == sample_message1["content"]
        assert response.json()["messages"][0]["recipient_id"] == user_one_email
        assert response.json()["messages"][1]["content"] == sample_message2["content"]
        assert response.json()["messages"][1]["recipient_id"] == user_one_email

    # already fetched message should not be included in fetch new messages
    def test_fetch_new_messages_excludes_seen_messages(self, client, sample_message1, sample_message2):
        """Fetch new messages should exclude messages that have already been fetched"""
        user_email = "user_one@example.com"

        # first message
        client.post("/messages", json=sample_message1)
        client.get(f"/messages/{user_email}/new") # seen

        # second message
        client.post("/messages", json=sample_message2)
        response = client.get(f"/messages/{user_email}/new")
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["messages"][0]["content"] == sample_message2["content"]

    # should be able to delete specified message

    # should return 404 when deleting non-existent message

    # should be able to delete multiple messages

    # should return 422 when deleting with empty message_ids

    # should be able to fetch messages with start, stop index

    # messages should be returned in ascending order of id