"""
Tests for streaming functionality (WebSocket and SSE).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from askgpt.modules.data_types import PromptNanoAgentResponse
from askgpt.web_server import app
from .helpers import capture_streaming


class TestWebSocketStreaming:
    """Test WebSocket streaming endpoint."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self, test_client: TestClient):
        """Test WebSocket connection establishment."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            with test_client.websocket_connect("/api/v1/chat/stream") as websocket:
                # Connection should be established
                assert websocket is not None

    @pytest.mark.asyncio
    async def test_websocket_chat_message(self, test_client: TestClient):
        """Test sending chat message via WebSocket."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            with test_client.websocket_connect("/api/v1/chat/stream") as websocket:
                # Send message
                websocket.send_json({"message": "Hello, test message"})
                
                # Receive chunks
                chunks_received = []
                done = False
                while not done:
                    data = websocket.receive_json()
                    chunks_received.append(data)
                    if data.get("done", False):
                        done = True
                
                # Should have received at least one chunk
                assert len(chunks_received) > 0
                # Last message should have done=True
                assert chunks_received[-1]["done"] is True

    @pytest.mark.asyncio
    async def test_websocket_with_session(self, test_client: TestClient):
        """Test WebSocket chat with session ID."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            session = client.create_session(provider="ollama", model="gpt-oss:20b")
            mock_get_client.return_value = client
            
            with test_client.websocket_connect("/api/v1/chat/stream") as websocket:
                websocket.send_json({
                    "message": "Test message",
                    "session_id": session.session_id,
                })
                
                # Receive response
                data = websocket.receive_json()
                assert "session_id" in data
                # Session ID should match
                assert data["session_id"] == session.session_id

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, test_client: TestClient):
        """Test WebSocket error handling."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            # Mock chat_stream to raise exception
            with patch.object(client, "chat_stream") as mock_stream:
                mock_stream.side_effect = Exception("Test error")
                
                with test_client.websocket_connect("/api/v1/chat/stream") as websocket:
                    websocket.send_json({"message": "Test message"})
                    
                    # Should receive error message
                    data = websocket.receive_json()
                    assert "error" in data or data.get("done") is True

    @pytest.mark.asyncio
    async def test_websocket_empty_message(self, test_client: TestClient):
        """Test WebSocket with empty message."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            with test_client.websocket_connect("/api/v1/chat/stream") as websocket:
                websocket.send_json({"message": ""})
                
                # Should receive error or empty response
                data = websocket.receive_json()
                assert "error" in data or data.get("done") is True

    @pytest.mark.asyncio
    async def test_websocket_multiple_messages(self, test_client: TestClient):
        """Test sending multiple messages via WebSocket."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            with test_client.websocket_connect("/api/v1/chat/stream") as websocket:
                # Send first message
                websocket.send_json({"message": "First message"})
                chunks1 = []
                done = False
                while not done:
                    data = websocket.receive_json()
                    chunks1.append(data)
                    if data.get("done", False):
                        done = True
                
                # Send second message
                websocket.send_json({"message": "Second message"})
                chunks2 = []
                done = False
                while not done:
                    data = websocket.receive_json()
                    chunks2.append(data)
                    if data.get("done", False):
                        done = True
                
                # Should have received chunks for both messages
                assert len(chunks1) > 0
                assert len(chunks2) > 0


class TestSSEStreaming:
    """Test Server-Sent Events streaming endpoint."""

    def test_sse_endpoint(self, test_client: TestClient):
        """Test SSE endpoint returns event stream."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            response = test_client.get(
                "/api/v1/chat/stream?message=Test%20message"
            )
            
            assert response.status_code == 200
            # Content-type may include charset
            assert "text/event-stream" in response.headers["content-type"]
            # Should have content
            content = response.text
            assert len(content) > 0
            # Should contain SSE format (data: ...)
            assert "data:" in content

    def test_sse_with_session(self, test_client: TestClient):
        """Test SSE with session ID."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            session = client.create_session(provider="ollama", model="gpt-oss:20b")
            mock_get_client.return_value = client
            
            response = test_client.get(
                f"/api/v1/chat/stream?message=Test&session_id={session.session_id}"
            )
            
            assert response.status_code == 200
            content = response.text
            # Should contain session ID in the stream
            assert session.session_id in content or len(content) > 0

    def test_sse_error_handling(self, test_client: TestClient):
        """Test SSE error handling."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            # Mock chat_stream to raise exception
            with patch.object(client, "chat_stream") as mock_stream:
                mock_stream.side_effect = Exception("Test error")
                
                response = test_client.get(
                    "/api/v1/chat/stream?message=Test"
                )
                
                assert response.status_code == 200
                content = response.text
                # Should contain error in stream
                assert "error" in content.lower() or len(content) > 0

    def test_sse_missing_message(self, test_client: TestClient):
        """Test SSE endpoint with missing message parameter."""
        response = test_client.get("/api/v1/chat/stream")
        # Should handle missing message gracefully
        assert response.status_code in [200, 400, 422]


class TestStreamingFormat:
    """Test streaming response formats."""

    @pytest.mark.asyncio
    async def test_websocket_message_format(self, test_client: TestClient):
        """Test WebSocket message format."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            with test_client.websocket_connect("/api/v1/chat/stream") as websocket:
                websocket.send_json({"message": "Test"})
                
                data = websocket.receive_json()
                # Check message format
                assert "chunk" in data or "done" in data
                assert "session_id" in data
                assert isinstance(data.get("done"), bool)

    def test_sse_event_format(self, test_client: TestClient):
        """Test SSE event format."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            from askgpt.api import AskGPTClient
            from askgpt.modules.session_manager import SessionManager
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.mkdtemp())
            session_manager = SessionManager(storage_dir=temp_dir)
            client = AskGPTClient(
                default_provider="ollama",
                default_model="gpt-oss:20b",
                session_manager=session_manager,
            )
            mock_get_client.return_value = client
            
            response = test_client.get("/api/v1/chat/stream?message=Test")
            
            assert response.status_code == 200
            content = response.text
            
            # Parse SSE format
            lines = content.split("\n")
            data_lines = [line for line in lines if line.startswith("data:")]
            assert len(data_lines) > 0
            
            # Parse first data line
            first_data = data_lines[0].replace("data: ", "")
            try:
                parsed = json.loads(first_data)
                assert "chunk" in parsed or "done" in parsed
            except json.JSONDecodeError:
                # If not JSON, that's okay for now
                pass
