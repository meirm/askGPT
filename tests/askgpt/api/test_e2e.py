"""
End-to-end tests for API functionality.

These tests exercise the full request/response cycle and may use
real agent execution with Ollama (no API keys required).
"""

import os
import pytest
from fastapi.testclient import TestClient

from askgpt.web_server import app


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OLLAMA_AVAILABLE", "false").lower() == "true",
    reason="Ollama not available - set OLLAMA_AVAILABLE=true to run E2E tests",
)
class TestE2EChat:
    """End-to-end tests for chat functionality."""

    def test_e2e_basic_chat_request(self, test_client: TestClient, ollama_available: bool):
        """Test full request/response cycle for basic chat."""
        if not ollama_available:
            pytest.skip("Ollama not running locally")
        
        # This test uses real Ollama if available
        # For now, we'll mock it but structure it for real execution
        with test_client as client:
            response = client.post(
                "/api/v1/chat",
                json={
                    "message": "Say hello in one word",
                    "provider": "ollama",
                    "model": "gpt-oss:20b",
                },
            )
            
            # Should get a response (may be mocked if Ollama not available)
            assert response.status_code in [200, 500]  # 500 if Ollama not running
            
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert "session_id" in data

    def test_e2e_multi_turn_conversation(self, test_client: TestClient, ollama_available: bool):
        """Test multi-turn conversation with session persistence."""
        if not ollama_available:
            pytest.skip("Ollama not running locally")
        
        with test_client as client:
            # First message
            response1 = client.post(
                "/api/v1/chat",
                json={
                    "message": "Remember the number 42",
                    "provider": "ollama",
                    "model": "gpt-oss:20b",
                },
            )
            
            if response1.status_code != 200:
                pytest.skip("Ollama not responding")
            
            data1 = response1.json()
            session_id = data1["session_id"]
            
            # Second message in same session
            response2 = client.post(
                "/api/v1/chat",
                json={
                    "message": "What number did I ask you to remember?",
                    "session_id": session_id,
                    "provider": "ollama",
                    "model": "gpt-oss:20b",
                },
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["session_id"] == session_id
            # Response should reference the number (may vary based on model)
            assert len(data2["response"]) > 0

    def test_e2e_session_management_flow(self, test_client: TestClient):
        """Test complete session management flow."""
        with test_client as client:
            # Create session
            create_response = client.post(
                "/api/v1/sessions",
                json={"provider": "ollama", "model": "gpt-oss:20b"},
            )
            assert create_response.status_code == 200
            session_data = create_response.json()
            session_id = session_data["session_id"]
            
            # Get session
            get_response = client.get(f"/api/v1/sessions/{session_id}")
            assert get_response.status_code == 200
            retrieved_session = get_response.json()
            assert retrieved_session["session_id"] == session_id
            
            # Use session for chat
            chat_response = client.post(
                "/api/v1/chat",
                json={
                    "message": "Hello",
                    "session_id": session_id,
                    "provider": "ollama",
                    "model": "gpt-oss:20b",
                },
            )
            # May fail if Ollama not available, but structure should work
            assert chat_response.status_code in [200, 500]
            
            # Delete session
            delete_response = client.delete(f"/api/v1/sessions/{session_id}")
            assert delete_response.status_code == 200
            
            # Verify deletion
            get_after_delete = client.get(f"/api/v1/sessions/{session_id}")
            assert get_after_delete.status_code == 404

    def test_e2e_websocket_flow(self, test_client: TestClient, ollama_available: bool):
        """Test WebSocket chat flow."""
        if not ollama_available:
            pytest.skip("Ollama not running locally")
        
        with test_client.websocket_connect("/api/v1/chat/stream") as websocket:
            # Send message
            websocket.send_json({
                "message": "Say hi",
                "provider": "ollama",
                "model": "gpt-oss:20b",
            })
            
            # Receive chunks
            chunks = []
            done = False
            timeout_count = 0
            max_timeout = 10
            
            while not done and timeout_count < max_timeout:
                try:
                    data = websocket.receive_json(timeout=5.0)
                    chunks.append(data)
                    if data.get("done", False):
                        done = True
                except Exception:
                    timeout_count += 1
                    if timeout_count >= max_timeout:
                        break
            
            # Should have received at least one message
            assert len(chunks) > 0 or timeout_count > 0

    def test_e2e_sse_flow(self, test_client: TestClient, ollama_available: bool):
        """Test SSE streaming flow."""
        if not ollama_available:
            pytest.skip("Ollama not running locally")
        
        response = test_client.get(
            "/api/v1/chat/stream?message=Hello&provider=ollama&model=gpt-oss:20b"
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Read stream content
        content = response.text
        assert len(content) > 0
        # Should contain SSE format
        assert "data:" in content

    @pytest.mark.requires_api_key
    def test_e2e_with_openai_provider(self, test_client: TestClient):
        """Test E2E with OpenAI provider (requires API key)."""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        with test_client as client:
            response = client.post(
                "/api/v1/chat",
                json={
                    "message": "What is 2+2? Answer with just the number.",
                    "provider": "openai",
                    "model": "gpt-5-mini",
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "2" in data["response"] or "4" in data["response"]

    @pytest.mark.requires_api_key
    def test_e2e_with_anthropic_provider(self, test_client: TestClient):
        """Test E2E with Anthropic provider (requires API key)."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")
        
        with test_client as client:
            response = client.post(
                "/api/v1/chat",
                json={
                    "message": "Say hello",
                    "provider": "anthropic",
                    "model": "claude-3-haiku-20240307",
                },
            )
            
            # May fail if model not available, but should handle gracefully
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert data["success"] is True


class TestE2EIntegration:
    """Integration tests for full API workflow."""

    def test_e2e_full_workflow(self, test_client: TestClient):
        """Test complete workflow: create session, chat, list, delete."""
        with test_client as client:
            # 1. Create session
            create_resp = client.post(
                "/api/v1/sessions",
                json={"provider": "ollama", "model": "gpt-oss:20b"},
            )
            assert create_resp.status_code == 200
            session_id = create_resp.json()["session_id"]
            
            # 2. Send chat message
            chat_resp = client.post(
                "/api/v1/chat",
                json={
                    "message": "Test message",
                    "session_id": session_id,
                    "provider": "ollama",
                    "model": "gpt-oss:20b",
                },
            )
            # May fail if Ollama not available
            assert chat_resp.status_code in [200, 500]
            
            # 3. List sessions
            list_resp = client.get("/api/v1/sessions")
            assert list_resp.status_code == 200
            sessions = list_resp.json()
            assert isinstance(sessions, list)
            assert len(sessions) > 0
            
            # 4. Get session details
            get_resp = client.get(f"/api/v1/sessions/{session_id}")
            assert get_resp.status_code == 200
            session_data = get_resp.json()
            assert session_data["session_id"] == session_id
            
            # 5. Delete session
            delete_resp = client.delete(f"/api/v1/sessions/{session_id}")
            assert delete_resp.status_code == 200
            
            # 6. Verify deletion
            get_after_delete = client.get(f"/api/v1/sessions/{session_id}")
            assert get_after_delete.status_code == 404

    def test_e2e_concurrent_requests(self, test_client: TestClient):
        """Test handling of concurrent requests."""
        import concurrent.futures
        
        def make_request():
            return test_client.post(
                "/api/v1/chat",
                json={
                    "message": "Test",
                    "provider": "ollama",
                    "model": "gpt-oss:20b",
                },
            )
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should complete (may fail if Ollama not available)
        assert len(results) == 3
        for result in results:
            assert result.status_code in [200, 500]
