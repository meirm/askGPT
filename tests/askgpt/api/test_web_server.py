"""
Integration tests for FastAPI web server endpoints.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from askgpt.modules.data_types import PromptNanoAgentResponse
from askgpt.web_server import app


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_check(self, test_client: TestClient):
        """Test health check endpoint."""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestChatEndpoint:
    """Test the chat REST endpoint."""

    def test_chat_endpoint_success(
        self, test_client: TestClient, mock_agent_execution
    ):
        """Test successful chat request."""
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
            
            response = test_client.post(
                "/api/v1/chat",
                json={"message": "Hello, test message"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "session_id" in data
            assert "metadata" in data
            assert data["success"] is True

    def test_chat_endpoint_with_session(
        self, test_client: TestClient, mock_agent_execution
    ):
        """Test chat with existing session."""
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
            # Create a session first
            session = client.create_session(provider="ollama", model="gpt-oss:20b")
            mock_get_client.return_value = client
            
            response = test_client.post(
                "/api/v1/chat",
                json={
                    "message": "Follow-up message",
                    "session_id": session.session_id,
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session.session_id

    def test_chat_endpoint_with_parameters(
        self, test_client: TestClient, mock_agent_execution
    ):
        """Test chat with additional parameters."""
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
            
            response = test_client.post(
                "/api/v1/chat",
                json={
                    "message": "Test message",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "read_only": True,
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_chat_endpoint_error_handling(self, test_client: TestClient):
        """Test chat endpoint error handling."""
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
            
            # Mock agent execution to return error
            with patch("askgpt.api._execute_nano_agent_async") as mock_exec:
                mock_response = PromptNanoAgentResponse(
                    success=False,
                    error="Test error message",
                    metadata={},
                    execution_time_seconds=0.5,
                )
                mock_exec.return_value = mock_response
                
                response = test_client.post(
                    "/api/v1/chat",
                    json={"message": "Test message"},
                )
                
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data

    def test_chat_endpoint_missing_message(self, test_client: TestClient):
        """Test chat endpoint with missing message."""
        response = test_client.post("/api/v1/chat", json={})
        assert response.status_code == 422  # Validation error

    def test_chat_endpoint_empty_message(self, test_client: TestClient):
        """Test chat endpoint with empty message."""
        response = test_client.post("/api/v1/chat", json={"message": ""})
        assert response.status_code == 422  # Validation error


class TestSessionEndpoints:
    """Test session management endpoints."""

    def test_create_session(self, test_client: TestClient):
        """Test creating a new session."""
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
            
            response = test_client.post(
                "/api/v1/sessions",
                json={"provider": "ollama", "model": "gpt-oss:20b"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert data["provider"] == "ollama"
            assert data["model"] == "gpt-oss:20b"

    def test_get_session(self, test_client: TestClient):
        """Test getting a session by ID."""
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
            
            response = test_client.get(f"/api/v1/sessions/{session.session_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session.session_id

    def test_get_nonexistent_session(self, test_client: TestClient):
        """Test getting a non-existent session."""
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
            
            response = test_client.get("/api/v1/sessions/nonexistent_session")
            
            assert response.status_code == 404

    def test_list_sessions(self, test_client: TestClient):
        """Test listing sessions."""
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
            # Create a few sessions
            client.create_session(provider="ollama", model="gpt-oss:20b")
            client.create_session(provider="ollama", model="gpt-oss:20b")
            mock_get_client.return_value = client
            
            response = test_client.get("/api/v1/sessions?limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 2

    def test_delete_session(self, test_client: TestClient):
        """Test deleting a session."""
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
            
            response = test_client.delete(f"/api/v1/sessions/{session.session_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data

    def test_delete_nonexistent_session(self, test_client: TestClient):
        """Test deleting a non-existent session."""
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
            
            response = test_client.delete("/api/v1/sessions/nonexistent_session")
            
            assert response.status_code == 404


class TestModelsEndpoint:
    """Test the models endpoint."""

    def test_list_models(self, test_client: TestClient):
        """Test listing available models."""
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
            
            response = test_client.get("/api/v1/models")
            
            assert response.status_code == 200
            data = response.json()
            assert "default_provider" in data
            assert "default_model" in data
            assert "providers" in data


class TestCORSMiddleware:
    """Test CORS middleware."""

    def test_cors_headers(self, test_client: TestClient):
        """Test that CORS headers are present."""
        response = test_client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight should be handled
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """Test error handling in web server."""

    def test_internal_server_error(self, test_client: TestClient):
        """Test handling of internal server errors."""
        with patch("askgpt.web_server.get_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Test error")
            
            response = test_client.post(
                "/api/v1/chat",
                json={"message": "Test message"},
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
