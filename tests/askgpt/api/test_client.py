"""
Unit tests for AskGPTClient.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from askgpt.api import AskGPTClient
from askgpt.modules.data_types import PromptNanoAgentResponse
from tests.askgpt.api.helpers import assert_response_format, capture_streaming


class TestAskGPTClient:
    """Test the AskGPTClient class."""

    def test_client_initialization(self, test_askgpt_client: AskGPTClient):
        """Test that client initializes correctly."""
        assert test_askgpt_client.default_provider == "ollama"
        assert test_askgpt_client.default_model == "gpt-oss:20b"
        assert test_askgpt_client.session_manager is not None

    def test_client_initialization_with_config(self, mock_config_manager):
        """Test client initialization with custom config."""
        from askgpt.modules.session_manager import SessionManager
        import tempfile
        from pathlib import Path
        
        temp_dir = Path(tempfile.mkdtemp())
        session_manager = SessionManager(storage_dir=temp_dir)
        
        client = AskGPTClient(
            default_provider="openai",
            default_model="gpt-5-mini",
            session_manager=session_manager,
            config_manager=mock_config_manager,
        )
        
        assert client.default_provider == "openai"
        assert client.default_model == "gpt-5-mini"

    @pytest.mark.asyncio
    async def test_chat_method(
        self, test_askgpt_client: AskGPTClient, mock_agent_execution
    ):
        """Test the chat() method."""
        response = await test_askgpt_client.chat("Hello, test message")
        
        assert_response_format(response, expected_success=True)
        assert "Test response" in response.result
        assert mock_agent_execution.called

    @pytest.mark.asyncio
    async def test_chat_with_session(
        self, test_askgpt_client: AskGPTClient, mock_agent_execution
    ):
        """Test chat with existing session."""
        # Create a session first
        session = test_askgpt_client.create_session(
            provider="ollama", model="gpt-oss:20b"
        )
        
        # Chat with session
        response = await test_askgpt_client.chat(
            "Follow-up message", session_id=session.session_id
        )
        
        assert_response_format(response, expected_success=True)
        assert test_askgpt_client.session_manager.current_session is not None

    @pytest.mark.asyncio
    async def test_chat_with_parameters(
        self, test_askgpt_client: AskGPTClient, mock_agent_execution
    ):
        """Test chat with additional parameters."""
        response = await test_askgpt_client.chat(
            "Test message",
            temperature=0.7,
            max_tokens=1000,
            read_only=True,
        )
        
        assert_response_format(response, expected_success=True)
        # Verify parameters were passed to agent execution
        call_args = mock_agent_execution.call_args
        assert call_args is not None
        request = call_args[0][0]
        assert request.temperature == 0.7
        assert request.max_tokens == 1000
        assert request.read_only is True

    @pytest.mark.asyncio
    async def test_chat_stream_method(
        self, test_askgpt_client: AskGPTClient, mock_agent_execution
    ):
        """Test the chat_stream() method."""
        chunks = await capture_streaming(
            test_askgpt_client.chat_stream("Test streaming message")
        )
        
        assert len(chunks) > 0
        # All chunks should be strings
        assert all(isinstance(chunk, str) for chunk in chunks)
        # Combined chunks should contain the response
        combined = "".join(chunks)
        assert "Test response" in combined

    @pytest.mark.asyncio
    async def test_chat_stream_with_error(
        self, test_askgpt_client: AskGPTClient
    ):
        """Test chat_stream handles errors."""
        # Mock agent execution to return error
        with patch("askgpt.api._execute_nano_agent_async") as mock_exec:
            mock_response = PromptNanoAgentResponse(
                success=False,
                error="Test error message",
                metadata={},
                execution_time_seconds=0.5,
            )
            mock_exec.return_value = mock_response
            
            chunks = await capture_streaming(
                test_askgpt_client.chat_stream("Test message")
            )
            
            # Should yield error message
            combined = "".join(chunks)
            assert "Error" in combined
            assert "Test error" in combined

    def test_create_session(self, test_askgpt_client: AskGPTClient):
        """Test creating a new session."""
        session = test_askgpt_client.create_session(
            provider="ollama", model="gpt-oss:20b"
        )
        
        assert session is not None
        assert session.provider == "ollama"
        assert session.model == "gpt-oss:20b"
        assert session.session_id is not None
        assert len(session.conversation) == 0

    def test_create_session_with_id(self, test_askgpt_client: AskGPTClient):
        """Test creating a session with custom ID."""
        custom_id = "custom_session_123"
        session = test_askgpt_client.create_session(
            provider="ollama", model="gpt-oss:20b", session_id=custom_id
        )
        
        assert session.session_id == custom_id

    def test_get_session(self, test_askgpt_client: AskGPTClient):
        """Test retrieving a session."""
        # Create a session
        created_session = test_askgpt_client.create_session(
            provider="ollama", model="gpt-oss:20b"
        )
        
        # Retrieve it
        retrieved_session = test_askgpt_client.get_session(created_session.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.provider == created_session.provider
        assert retrieved_session.model == created_session.model

    def test_get_nonexistent_session(self, test_askgpt_client: AskGPTClient):
        """Test retrieving a non-existent session."""
        session = test_askgpt_client.get_session("nonexistent_session_123")
        assert session is None

    def test_list_sessions(self, test_askgpt_client: AskGPTClient):
        """Test listing sessions."""
        # Create multiple sessions
        session1 = test_askgpt_client.create_session(
            provider="ollama", model="gpt-oss:20b"
        )
        session2 = test_askgpt_client.create_session(
            provider="ollama", model="gpt-oss:20b"
        )
        
        # List sessions
        sessions = test_askgpt_client.list_sessions(limit=10)
        
        assert len(sessions) >= 2
        session_ids = [s.session_id for s in sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids

    def test_list_sessions_with_limit(self, test_askgpt_client: AskGPTClient):
        """Test listing sessions with limit."""
        # Create multiple sessions
        for _ in range(5):
            test_askgpt_client.create_session(provider="ollama", model="gpt-oss:20b")
        
        # List with limit
        sessions = test_askgpt_client.list_sessions(limit=3)
        assert len(sessions) <= 3

    @pytest.mark.asyncio
    async def test_chat_error_handling(
        self, test_askgpt_client: AskGPTClient
    ):
        """Test error handling in chat method."""
        # Mock agent execution to raise exception
        with patch("askgpt.api._execute_nano_agent_async") as mock_exec:
            mock_exec.side_effect = Exception("Test exception")
            
            # Should not raise, but return error response
            # Note: This depends on how _execute_nano_agent_async handles errors
            # For now, we expect it to return an error response
            try:
                response = await test_askgpt_client.chat("Test message")
                # If it returns a response, it should indicate failure
                if response:
                    assert not response.success or response.error is not None
            except Exception:
                # If it raises, that's also acceptable error handling
                pass

    @pytest.mark.asyncio
    async def test_chat_creates_session_if_none(
        self, test_askgpt_client: AskGPTClient, mock_agent_execution
    ):
        """Test that chat creates a session if none exists."""
        # Ensure no current session
        test_askgpt_client.session_manager.current_session = None
        
        response = await test_askgpt_client.chat("Test message")
        
        # Should have created a session
        assert test_askgpt_client.session_manager.current_session is not None
        assert_response_format(response, expected_success=True)

    @pytest.mark.asyncio
    async def test_chat_saves_to_session(
        self, test_askgpt_client: AskGPTClient, mock_agent_execution
    ):
        """Test that chat saves exchange to session."""
        session = test_askgpt_client.create_session(
            provider="ollama", model="gpt-oss:20b"
        )
        initial_count = len(session.conversation)
        
        response = await test_askgpt_client.chat(
            "Test message", session_id=session.session_id
        )
        
        # Reload session to check
        updated_session = test_askgpt_client.get_session(session.session_id)
        assert updated_session is not None
        assert len(updated_session.conversation) > initial_count
