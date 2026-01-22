"""
Shared pytest fixtures for API tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from askgpt.api import AskGPTClient
from askgpt.modules.config_manager import ConfigManager
from askgpt.modules.data_types import PromptNanoAgentResponse
from askgpt.modules.session_manager import SessionManager
from askgpt.web_server import app, get_client


@pytest.fixture
def temp_session_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for session storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def ollama_config() -> dict:
    """Fixture to configure Ollama as default provider (no API keys needed)."""
    return {
        "default_provider": "ollama",
        "default_model": "gpt-oss:20b",
        "providers": {
            "ollama": {
                "api_base": "http://localhost:11434/v1",
                "allow_unknown_models": True,
                "discover_models": True,
                "timeout": 120,
            }
        },
    }


@pytest.fixture
def mock_config_manager(ollama_config: dict) -> Generator[ConfigManager, None, None]:
    """Create a mock ConfigManager with Ollama defaults."""
    with patch("askgpt.api.get_config_manager") as mock_get:
        config_manager = MagicMock(spec=ConfigManager)
        config = MagicMock()
        config.default_provider = ollama_config["default_provider"]
        config.default_model = ollama_config["default_model"]
        config.providers = {}
        config.model_aliases = {}
        config_manager.config = config
        mock_get.return_value = config_manager
        yield config_manager


@pytest.fixture
def test_askgpt_client(temp_session_dir: Path, mock_config_manager: ConfigManager) -> AskGPTClient:
    """Create an AskGPTClient instance configured with Ollama for testing."""
    session_manager = SessionManager(storage_dir=temp_session_dir)
    return AskGPTClient(
        default_provider="ollama",
        default_model="gpt-oss:20b",
        session_manager=session_manager,
        config_manager=mock_config_manager,
    )


@pytest.fixture
def mock_agent_execution() -> Generator[AsyncMock, None, None]:
    """Mock agent execution for unit tests."""
    with patch("askgpt.api._execute_nano_agent_async") as mock_exec:
        mock_response = PromptNanoAgentResponse(
            success=True,
            result="Test response from agent",
            metadata={"test": True},
            execution_time_seconds=1.0,
        )
        mock_exec.return_value = mock_response
        yield mock_exec


@pytest.fixture
def sample_chat_request() -> dict:
    """Sample chat request data."""
    return {
        "message": "Hello, how are you?",
        "model": "gpt-oss:20b",
        "provider": "ollama",
    }


@pytest.fixture
def sample_chat_response() -> dict:
    """Sample chat response data."""
    return {
        "response": "Hello! I'm doing well, thank you for asking.",
        "session_id": "test_session_123",
        "metadata": {"test": True},
        "success": True,
    }


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a FastAPI test client."""
    # Reset the global client before each test
    import askgpt.web_server
    askgpt.web_server._client = None
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def ollama_available() -> bool:
    """Check if Ollama is available for testing."""
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 11434))
        sock.close()
        return result == 0
    except Exception:
        return False


@pytest.fixture(autouse=True)
def reset_web_client():
    """Reset the web server's global client before each test."""
    import askgpt.web_server
    original_client = askgpt.web_server._client
    askgpt.web_server._client = None
    yield
    askgpt.web_server._client = original_client
