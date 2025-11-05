from httpx import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch
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
    
    ###########################################################
    # Submit Message
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

    @patch('src.main.MessageService.create_message')
    def test_submit_message_service_exception(self, mock_create_message, client, sample_message1):
        """Should return 500 when MessageService.create_message raises an exception"""
        mock_create_message.side_effect = Exception("Database connection failed")
        
        response = client.post("/messages", json=sample_message1)
        assert response.status_code == 500
        assert "Error creating message: Database connection failed" in response.json()["detail"]

    ###########################################################
    # Fetch New Messages
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

    @patch('src.main.MessageService.fetch_new_messages')
    def test_fetch_new_messages_service_exception(self, mock_fetch_new_messages, client):
        """Should return 500 when MessageService.fetch_new_messages raises an exception"""
        mock_fetch_new_messages.side_effect = Exception("Query execution failed")
        
        response = client.get("/messages/user@example.com/new")
        assert response.status_code == 500
        assert "Error fetching new messages: Query execution failed" in response.json()["detail"]

    ###########################################################
    # Delete Messages
    def test_delete_message(self, client, sample_message1):
        """Should be able to delete a specified message"""
        # send a message first
        post_response = client.post("/messages", json=sample_message1)
        message_id = post_response.json()["id"]

        # delete the message
        delete_response = client.delete(f"/messages/{message_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted_count"] == 1

        # verify message is deleted by fetching messages
        fetch_response = client.get(f"/messages/{sample_message1['recipient_id']}?start=1&stop=10")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 0

    def test_delete_non_existent_message(self, client):
        """Should return 404 when trying to delete a non-existent message"""
        delete_response = client.delete("/messages/9999")
        assert delete_response.status_code == 404

    @patch('src.main.MessageService.delete_message')
    def test_delete_message_service_exception(self, mock_delete_message, client):
        """Should return 500 when MessageService.delete_message raises an exception"""
        mock_delete_message.side_effect = Exception("Delete operation failed")
        
        response = client.delete("/messages/123")
        assert response.status_code == 500
        assert "Error deleting message: Delete operation failed" in response.json()["detail"]

    ###########################################################
    # Delete Messages - Multiple
    def test_delete_multiple_messages(self, client, sample_message1, sample_message2):
        """Should be able to delete multiple specified messages"""
        # send messages first
        post_response1 = client.post("/messages", json=sample_message1)
        post_response2 = client.post("/messages", json=sample_message2)
        message_id1 = post_response1.json()["id"]
        message_id2 = post_response2.json()["id"]

        # delete the messages
        delete_response = client.delete("/messages", params={"message_ids": [message_id1, message_id2]})
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted_count"] == 2

        # verify messages are deleted by fetching messages
        fetch_response = client.get(f"/messages/{sample_message1['recipient_id']}?start=1&stop=10")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 0

    def test_delete_multiple_messages_empty_ids(self, client):
        """Should return 422 when deleting with empty message_ids"""
        delete_response = client.delete("/messages", params={"message_ids": []})
        assert delete_response.status_code == 422

    def test_delete_multiple_messages_non_existent_ids(self, client):
        """Should return 404 when trying to delete non-existent messages"""
        delete_response = client.delete("/messages", params={"message_ids": [9999, 10000]})
        assert delete_response.status_code == 404

    @patch('src.main.MessageService.delete_multiple_messages')
    def test_delete_multiple_messages_service_exception(self, mock_delete_multiple, client):
        """Should return 500 when MessageService.delete_multiple_messages raises an exception"""
        mock_delete_multiple.side_effect = Exception("Bulk delete failed")
        
        response = client.delete("/messages", params={"message_ids": [1, 2, 3]})
        assert response.status_code == 500
        assert "Error deleting messages: Bulk delete failed" in response.json()["detail"]

    ###########################################################
    # Fetch Messages - Multiple
    def test_fetch_multiple_messages_with_pagination(self, client, sample_message1, sample_message2):
        """Should be able to fetch messages with start and stop index"""
        user_email = "user@eg.com"

        # send 5 messages
        for i in range(5):
            message = {
                "recipient_id": user_email,
                "content": f"Message {i+1}"
            }
            client.post("/messages", json=message)

        # there should be 5 messages
        fetch_response = client.get(f"/messages/{user_email}?start=1&stop=5")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 5
        
    def test_fetch_multiple_messages_pagination_range(self, client):
        """Should fetch messages in the correct start-stop range (start inclusive, stop inclusive)"""
        user_email = "user@eg.com"
        # send 5 messages
        for i in range(5):
            message = {
                "recipient_id": user_email,
                "content": f"Message {i+1}"
            }
            client.post("/messages", json=message)

        # fetch messages from index 1 to 3
        fetch_response = client.get(f"/messages/{user_email}?start=1&stop=3")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 3
        assert fetch_response.json()["messages"][0]["content"] == "Message 1"
        assert fetch_response.json()["messages"][1]["content"] == "Message 2"
        assert fetch_response.json()["messages"][2]["content"] == "Message 3"

    def test_fetch_multiple_messages_ordering(self, client):
        """Fetched messages should be ordered by message id (index) in asc order"""
        user_email = "user@eg.com"
        # send 3 messages
        contents = ["First message", "Second message", "Third message"]
        for content in contents:
            message = {
                "recipient_id": user_email,
                "content": content
            }
            client.post("/messages", json=message)
        # fetch all messages
        fetch_response = client.get(f"/messages/{user_email}?start=1&stop=5")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 3
        assert fetch_response.json()["messages"][0]["content"] == "First message"
        assert fetch_response.json()["messages"][1]["content"] == "Second message"
        assert fetch_response.json()["messages"][2]["content"] == "Third message"

    def test_fetch_multiple_messages_pagination_out_of_range(self, client):
        """Should return 422 if start or stop are out of range"""
        user_email = "user@eg.com"
        fetch_response = client.get(f"/messages/{user_email}?start=0&stop=15")
        assert fetch_response.status_code == 422

    def test_fetch_multiple_messages_invalid_stop_value(self, client):
        """Should return 400 when stop is less than start"""
        user_email = "user@eg.com"
        
        response = client.get(f"/messages/{user_email}?start=5&stop=3")
        assert response.status_code == 400
        assert "stop must be greater than or equal to start" in response.json()["detail"]

    def test_fetch_multiple_messages_invalid_parameters(self, client):
        """Should return 422 for invalid query parameters"""
        user_email = "user@example.com"
        
        #  negative start value (violates ge=1 constraint)
        response = client.get(f"/messages/{user_email}?start=-1&stop=5")
        assert response.status_code == 422
        
        # negative stop value
        response = client.get(f"/messages/{user_email}?start=1&stop=-1")
        assert response.status_code == 422

    @patch('src.main.MessageService.fetch_messages_by_index')
    def test_fetch_multiple_messages_service_exception(self, mock_fetch_messages, client):
        """Should return 500 when MessageService.fetch_messages_by_index raises an exception"""
        mock_fetch_messages.side_effect = Exception("Pagination query failed")
        
        response = client.get("/messages/user@example.com?start=1&stop=5")
        assert response.status_code == 500
        assert "Error fetching messages: Pagination query failed" in response.json()["detail"]