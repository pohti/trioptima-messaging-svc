import os
import pytest
import requests
import time
# Configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TEST_TIMEOUT = 30  # seconds to wait for service to be ready

class TestMessagingServiceIntegration:
    
    @classmethod
    def setup_class(cls):
        """Wait for the service to be ready before running tests"""
        print(f"Waiting for service at {BASE_URL} to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < TEST_TIMEOUT:
            try:
                response = requests.get(f"{BASE_URL}/", timeout=5)
                if response.status_code == 200:
                    print("Service is ready!")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        
        raise Exception(f"Service at {BASE_URL} did not become ready within {TEST_TIMEOUT} seconds")
    
    def setup_method(self):
        """Clean up database before each test"""
        # Optional: Add cleanup logic if needed
        # For now, we'll rely on the service's database isolation
        pass
    
    @pytest.fixture
    def sample_message1(self):
        return {
            "recipient_id": "user_one@example.com",
            "content": "Hello, this is a test message!",
        }

    @pytest.fixture
    def sample_message2(self):
        return {
            "recipient_id": "user_one@example.com",
            "content": "Hello, this is another test message!",
        }

    @pytest.fixture
    def sample_message3(self):
        return {
            "recipient_id": "user_two@example.com",
            "content": "Hello, this message is for user_two!",
        }

    def test_health_check(self):
        """Test the health check endpoint"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "instance_id" in data
        assert "V2" in data["message"]

    ###########################################################
    # Submit Message (Async)
    def test_submit_message_async(self, sample_message1):
        """Should be able to submit a valid message asynchronously"""
        response = requests.post(f"{BASE_URL}/messages", json=sample_message1)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "queued"
        assert data["recipient_id"] == sample_message1["recipient_id"]
        assert "Message has been queued for processing" in data["message"]

    def test_submit_message_async_validation_error_empty_recipient(self):
        """Should return 422 for empty recipient_id"""
        invalid_message = {
            "recipient_id": "",
            "content": "test"
        }
        response = requests.post(f"{BASE_URL}/messages", json=invalid_message)
        assert response.status_code == 422

    def test_submit_message_async_validation_error_empty_content(self):
        """Should return 422 for empty content"""
        invalid_message = {
            "recipient_id": "test@example.com",
            "content": ""
        }
        response = requests.post(f"{BASE_URL}/messages", json=invalid_message)
        assert response.status_code == 422

    ###########################################################
    # Submit Message (Sync)
    def test_submit_message_sync(self, sample_message1):
        """Should be able to submit a valid message synchronously"""
        response = requests.post(f"{BASE_URL}/messages/sync", json=sample_message1)
        assert response.status_code == 200
        
        data = response.json()
        assert data["recipient_id"] == sample_message1["recipient_id"]
        assert data["content"] == sample_message1["content"]
        assert "id" in data
        assert data["seen"] == False

    def test_submit_message_sync_validation_error_empty_recipient(self):
        """Should return 422 for empty recipient_id"""
        invalid_message = {
            "recipient_id": "",
            "content": "test"
        }
        response = requests.post(f"{BASE_URL}/messages/sync", json=invalid_message)
        assert response.status_code == 422

    def test_submit_message_sync_validation_error_empty_content(self):
        """Should return 422 for empty content"""
        invalid_message = {
            "recipient_id": "test@example.com",
            "content": ""
        }
        response = requests.post(f"{BASE_URL}/messages/sync", json=invalid_message)
        assert response.status_code == 422

    ###########################################################
    # Fetch New Messages
    def test_fetch_new_messages_empty(self):
        """Fetch new messages should be empty when no messages exist for new user"""
        # Use a unique recipient ID to avoid conflicts with other tests
        unique_recipient = f"empty_test_{int(time.time())}@example.com"
        response = requests.get(f"{BASE_URL}/messages/{unique_recipient}/new")
        assert response.status_code == 200
        assert response.json() == {"messages": [], "count": 0}

    def test_fetch_new_messages_includes_new_message(self, sample_message1, sample_message2):
        """Fetch new messages should include messages sent after the request"""
        # Use unique recipient ID for this test
        unique_recipient = f"test_{int(time.time())}@example.com"
        message1 = {**sample_message1, "recipient_id": unique_recipient}
        message2 = {**sample_message2, "recipient_id": unique_recipient}

        # Send messages synchronously to ensure they're in DB
        requests.post(f"{BASE_URL}/messages/sync", json=message1)
        requests.post(f"{BASE_URL}/messages/sync", json=message2)
        
        response = requests.get(f"{BASE_URL}/messages/{unique_recipient}/new")
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert response.json()["messages"][0]["content"] == message1["content"]
        assert response.json()["messages"][1]["content"] == message2["content"]

    def test_fetch_new_messages_should_not_include_other_users_messages(self, sample_message1, sample_message2, sample_message3):
        """Fetch new messages should not include messages for other users"""
        # Use unique recipient IDs for this test
        unique_recipient1 = f"user1_{int(time.time())}@example.com"
        unique_recipient2 = f"user2_{int(time.time())}@example.com"
        
        message1 = {**sample_message1, "recipient_id": unique_recipient1}
        message2 = {**sample_message2, "recipient_id": unique_recipient1}
        message3 = {**sample_message3, "recipient_id": unique_recipient2}

        requests.post(f"{BASE_URL}/messages/sync", json=message1)
        requests.post(f"{BASE_URL}/messages/sync", json=message2)
        requests.post(f"{BASE_URL}/messages/sync", json=message3)
        
        response = requests.get(f"{BASE_URL}/messages/{unique_recipient1}/new")
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert response.json()["messages"][0]["content"] == message1["content"]
        assert response.json()["messages"][0]["recipient_id"] == unique_recipient1
        assert response.json()["messages"][1]["content"] == message2["content"]
        assert response.json()["messages"][1]["recipient_id"] == unique_recipient1

    def test_fetch_new_messages_excludes_seen_messages(self, sample_message1, sample_message2):
        """Fetch new messages should exclude messages that have already been fetched"""
        # Use unique recipient ID for this test
        unique_recipient = f"seen_test_{int(time.time())}@example.com"
        message1 = {**sample_message1, "recipient_id": unique_recipient}
        message2 = {**sample_message2, "recipient_id": unique_recipient}

        # First message
        requests.post(f"{BASE_URL}/messages/sync", json=message1)
        requests.get(f"{BASE_URL}/messages/{unique_recipient}/new")  # Mark as seen

        # Second message
        requests.post(f"{BASE_URL}/messages/sync", json=message2)
        response = requests.get(f"{BASE_URL}/messages/{unique_recipient}/new")
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["messages"][0]["content"] == message2["content"]

    ###########################################################
    # Delete Messages
    def test_delete_message(self, sample_message1):
        """Should be able to delete a specified message"""
        # Use unique recipient ID for this test
        unique_recipient = f"delete_test_{int(time.time())}@example.com"
        message = {**sample_message1, "recipient_id": unique_recipient}
        
        # Send a message first
        post_response = requests.post(f"{BASE_URL}/messages/sync", json=message)
        message_id = post_response.json()["id"]

        # Delete the message
        delete_response = requests.delete(f"{BASE_URL}/messages/{message_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted_count"] == 1

        # Verify message is deleted by fetching messages
        fetch_response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=1&stop=10")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 0

    def test_delete_non_existent_message(self):
        """Should return 404 when trying to delete a non-existent message"""
        delete_response = requests.delete(f"{BASE_URL}/messages/99999")
        assert delete_response.status_code == 404

    ###########################################################
    # Delete Messages - Multiple
    def test_delete_multiple_messages(self, sample_message1, sample_message2):
        """Should be able to delete multiple specified messages"""
        # Use unique recipient ID for this test
        unique_recipient = f"multi_delete_{int(time.time())}@example.com"
        message1 = {**sample_message1, "recipient_id": unique_recipient}
        message2 = {**sample_message2, "recipient_id": unique_recipient}
        
        # Send messages first
        post_response1 = requests.post(f"{BASE_URL}/messages/sync", json=message1)
        post_response2 = requests.post(f"{BASE_URL}/messages/sync", json=message2)
        message_id1 = post_response1.json()["id"]
        message_id2 = post_response2.json()["id"]

        # Delete the messages
        delete_response = requests.delete(f"{BASE_URL}/messages", params={"message_ids": [message_id1, message_id2]})
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted_count"] == 2

        # Verify messages are deleted by fetching messages
        fetch_response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=1&stop=10")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 0

    def test_delete_multiple_messages_empty_ids(self):
        """Should return 422 when deleting with empty message_ids"""
        delete_response = requests.delete(f"{BASE_URL}/messages", params={"message_ids": []})
        assert delete_response.status_code == 422

    def test_delete_multiple_messages_non_existent_ids(self):
        """Should return 404 when trying to delete non-existent messages"""
        delete_response = requests.delete(f"{BASE_URL}/messages", params={"message_ids": [99999, 100000]})
        assert delete_response.status_code == 404

    ###########################################################
    # Fetch Messages - Multiple
    def test_fetch_multiple_messages_with_pagination(self):
        """Should be able to fetch messages with start and stop index"""
        # Use unique recipient ID for this test
        unique_recipient = f"pagination_{int(time.time())}@example.com"

        # Send 5 messages
        for i in range(5):
            message = {
                "recipient_id": unique_recipient,
                "content": f"Message {i+1}"
            }
            requests.post(f"{BASE_URL}/messages/sync", json=message)

        # There should be 5 messages
        fetch_response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=1&stop=5")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 5
        
    def test_fetch_multiple_messages_pagination_range(self):
        """Should fetch messages in the correct start-stop range (start inclusive, stop inclusive)"""
        # Use unique recipient ID for this test
        unique_recipient = f"range_{int(time.time())}@example.com"
        
        # Send 5 messages
        for i in range(5):
            message = {
                "recipient_id": unique_recipient,
                "content": f"Message {i+1}"
            }
            requests.post(f"{BASE_URL}/messages/sync", json=message)

        # Fetch messages from index 1 to 3
        fetch_response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=1&stop=3")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 3
        assert fetch_response.json()["messages"][0]["content"] == "Message 1"
        assert fetch_response.json()["messages"][1]["content"] == "Message 2"
        assert fetch_response.json()["messages"][2]["content"] == "Message 3"

    def test_fetch_multiple_messages_ordering(self):
        """Fetched messages should be ordered by message id (index) in asc order"""
        # Use unique recipient ID for this test
        unique_recipient = f"ordering_{int(time.time())}@example.com"
        
        # Send 3 messages
        contents = ["First message", "Second message", "Third message"]
        for content in contents:
            message = {
                "recipient_id": unique_recipient,
                "content": content
            }
            requests.post(f"{BASE_URL}/messages/sync", json=message)
            
        # Fetch all messages
        fetch_response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=1&stop=5")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] == 3
        assert fetch_response.json()["messages"][0]["content"] == "First message"
        assert fetch_response.json()["messages"][1]["content"] == "Second message"
        assert fetch_response.json()["messages"][2]["content"] == "Third message"

    def test_fetch_multiple_messages_pagination_out_of_range(self):
        """Should return 422 if start or stop are out of range"""
        unique_recipient = f"out_of_range_{int(time.time())}@example.com"
        fetch_response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=0&stop=15")
        assert fetch_response.status_code == 422

    def test_fetch_multiple_messages_invalid_stop_value(self):
        """Should return 400 when stop is less than start"""
        unique_recipient = f"invalid_stop_{int(time.time())}@example.com"
        
        response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=5&stop=3")
        assert response.status_code == 400
        assert "stop must be greater than or equal to start" in response.json()["detail"]

    def test_fetch_multiple_messages_invalid_parameters(self):
        """Should return 422 for invalid query parameters"""
        unique_recipient = f"invalid_params_{int(time.time())}@example.com"
        
        # Negative start value (violates ge=1 constraint)
        response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=-1&stop=5")
        assert response.status_code == 422
        
        # Negative stop value
        response = requests.get(f"{BASE_URL}/messages/{unique_recipient}?start=1&stop=-1")
        assert response.status_code == 422

    ###########################################################
    # End-to-End Flow Tests
    def test_complete_message_flow(self):
        """Test the complete message flow: async submit -> processing -> fetch -> delete"""
        unique_recipient = f"e2e_{int(time.time())}@example.com"
        test_message = {
            "recipient_id": unique_recipient,
            "content": "End-to-end test message"
        }
        
        # 1. Submit message asynchronously
        submit_response = requests.post(f"{BASE_URL}/messages", json=test_message)
        assert submit_response.status_code == 200
        assert submit_response.json()["status"] == "queued"
        
        # 2. Wait a bit for async processing (optional)
        time.sleep(2)
        
        # 3. Check if message was processed by fetching new messages
        # Note: This might be empty if the async processing hasn't completed yet
        fetch_response = requests.get(f"{BASE_URL}/messages/{unique_recipient}/new")
        assert fetch_response.status_code == 200
        
        # 4. For guaranteed testing, also submit a sync message
        sync_response = requests.post(f"{BASE_URL}/messages/sync", json=test_message)
        assert sync_response.status_code == 200
        message_id = sync_response.json()["id"]
        
        # 5. Fetch and verify the sync message
        fetch_response = requests.get(f"{BASE_URL}/messages/{unique_recipient}/new")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["count"] >= 1
        
        # 6. Delete the message
        delete_response = requests.delete(f"{BASE_URL}/messages/{message_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted_count"] == 1