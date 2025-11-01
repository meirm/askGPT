"""Tests for specific model provider implementations."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
from askgpt.modules.model_providers import (ModelInfo,
                                                ProviderAuthenticationError,
                                                ProviderConnectionError,
                                                ProviderRateLimitError)
from askgpt.modules.provider_implementations import (AnthropicProvider,
                                                         LMStudioProvider,
                                                         OllamaProvider,
                                                         OpenAIProvider,
                                                         auto_detect_providers,
                                                         initialize_providers)


class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    @pytest.mark.asyncio
    @patch("askgpt.modules.provider_implementations.aiohttp.ClientSession")
    async def test_list_models_success(self, mock_session_class):
        """Test successful model listing from OpenAI."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "data": [
                    {"id": "gpt-4", "created": 1687882410, "owned_by": "openai"},
                    {
                        "id": "gpt-3.5-turbo",
                        "created": 1677610602,
                        "owned_by": "openai",
                    },
                ]
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        # Configure mock session
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        # Test
        provider = OpenAIProvider(api_key="test-key")
        models = await provider.list_models()

        assert len(models) == 2
        assert any(m.id == "gpt-4" for m in models)
        assert any(m.id == "gpt-3.5-turbo" for m in models)
        assert all(m.provider == "openai" for m in models)

    @pytest.mark.asyncio
    @patch("askgpt.modules.provider_implementations.aiohttp.ClientSession")
    async def test_list_models_authentication_error(self, mock_session_class):
        """Test authentication error handling."""
        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Invalid API key")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        provider = OpenAIProvider(api_key="invalid-key")

        with pytest.raises(ProviderAuthenticationError) as exc_info:
            await provider.list_models()

        assert (
            "openai" in str(exc_info.value).lower()
            or exc_info.value.provider == "openai"
        )

    @pytest.mark.asyncio
    @patch("askgpt.modules.provider_implementations.aiohttp.ClientSession")
    async def test_list_models_rate_limit(self, mock_session_class):
        """Test rate limit error handling."""
        # Mock 429 response
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        provider = OpenAIProvider(api_key="test-key")

        with pytest.raises(ProviderRateLimitError) as exc_info:
            await provider.list_models()

        assert exc_info.value.retry_after == 60

    def test_enrich_model_info(self):
        """Test model info enrichment with OpenAI metadata."""
        provider = OpenAIProvider(api_key="test-key")

        model = ModelInfo(id="gpt-4", name="gpt-4", provider="openai")
        enriched = provider._enrich_model_info(model)

        assert enriched.context_length == 8192
        assert enriched.capabilities == ["chat", "function_calling"]
        assert enriched.input_cost_per_1k > 0
        assert enriched.output_cost_per_1k > 0


class TestAnthropicProvider:
    """Test Anthropic provider implementation."""

    @pytest.mark.asyncio
    async def test_list_models_hardcoded(self):
        """Test that Anthropic returns hardcoded models."""
        provider = AnthropicProvider(api_key="test-key")
        models = await provider.list_models()

        assert len(models) > 0
        assert any("claude" in m.id.lower() for m in models)
        assert all(m.provider == "anthropic" for m in models)

        # Check for expected models
        model_ids = [m.id for m in models]
        assert "claude-3-opus-20240229" in model_ids
        assert "claude-3-sonnet-20240229" in model_ids
        assert "claude-3-haiku-20240307" in model_ids

    @pytest.mark.asyncio
    async def test_validate_connection_with_api_key(self):
        """Test connection validation with API key."""
        provider = AnthropicProvider(api_key="test-key")
        is_valid = await provider.validate_connection()
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_without_api_key(self):
        """Test connection validation without API key."""
        provider = AnthropicProvider(api_key=None)
        is_valid = await provider.validate_connection()
        assert is_valid is False


class TestOllamaProvider:
    """Test Ollama provider implementation."""

    @pytest.mark.asyncio
    @patch("askgpt.modules.provider_implementations.aiohttp.ClientSession")
    async def test_list_models_success(self, mock_session_class):
        """Test successful model listing from Ollama."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "models": [
                    {
                        "name": "llama2:latest",
                        "size": 3825819519,
                        "digest": "sha256:abc123",
                        "modified_at": "2024-01-01T00:00:00Z",
                    },
                    {
                        "name": "mistral:7b",
                        "size": 4109855319,
                        "digest": "sha256:def456",
                        "modified_at": "2024-01-02T00:00:00Z",
                    },
                ]
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        provider = OllamaProvider()
        models = await provider.list_models()

        assert len(models) == 2
        assert any(m.id == "llama2:latest" for m in models)
        assert any(m.id == "mistral:7b" for m in models)
        assert all(m.provider == "ollama" for m in models)

    @pytest.mark.asyncio
    @patch("askgpt.modules.provider_implementations.aiohttp.ClientSession")
    async def test_list_models_connection_error(self, mock_session_class):
        """Test connection error when Ollama is not running."""
        # Mock connection error
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(
            side_effect=aiohttp.ClientConnectorError(
                connection_key=Mock(), os_error=OSError("Connection refused")
            )
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        provider = OllamaProvider()

        with pytest.raises(ProviderConnectionError) as exc_info:
            await provider.list_models()

        assert (
            "ollama" in str(exc_info.value).lower()
            or exc_info.value.provider == "ollama"
        )

    @pytest.mark.asyncio
    @patch("askgpt.modules.provider_implementations.aiohttp.ClientSession")
    async def test_validate_connection_success(self, mock_session_class):
        """Test successful connection validation."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        provider = OllamaProvider()
        is_valid = await provider.validate_connection()
        assert is_valid is True


class TestLMStudioProvider:
    """Test LMStudio provider implementation."""

    @pytest.mark.asyncio
    @patch("askgpt.modules.provider_implementations.aiohttp.ClientSession")
    async def test_list_models_success(self, mock_session_class):
        """Test successful model listing from LMStudio."""
        # Mock response (OpenAI-compatible format)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "data": [
                    {"id": "local-model-1", "created": 1234567890, "owned_by": "local"},
                    {"id": "local-model-2", "created": 1234567891, "owned_by": "local"},
                ]
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        provider = LMStudioProvider()
        models = await provider.list_models()

        assert len(models) == 2
        assert any(m.id == "local-model-1" for m in models)
        assert any(m.id == "local-model-2" for m in models)
        assert all(m.provider == "lmstudio" for m in models)

    @pytest.mark.asyncio
    @patch("askgpt.modules.provider_implementations.aiohttp.ClientSession")
    async def test_list_models_alternative_format(self, mock_session_class):
        """Test model listing with alternative response format."""
        # Mock response (alternative format with models key)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "models": [
                    {"name": "model-1", "id": "model-1"},
                    {"name": "model-2", "id": "model-2"},
                ]
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        provider = LMStudioProvider()
        models = await provider.list_models()

        assert len(models) == 2
        assert any(m.id == "model-1" for m in models)
        assert any(m.id == "model-2" for m in models)


class TestProviderInitialization:
    """Test provider initialization and auto-detection."""

    @pytest.mark.asyncio
    @patch(
        "askgpt.modules.provider_implementations.OllamaProvider.validate_connection"
    )
    @patch(
        "askgpt.modules.provider_implementations.LMStudioProvider.validate_connection"
    )
    async def test_auto_detect_providers(self, mock_lm_validate, mock_ollama_validate):
        """Test auto-detection of available providers."""
        # Mock Ollama as available, LMStudio as not available
        mock_ollama_validate.return_value = True
        mock_lm_validate.return_value = False

        available = await auto_detect_providers()

        assert "ollama" in available
        assert "lmstudio" not in available

        # OpenAI and Anthropic depend on API keys
        import os

        if os.environ.get("OPENAI_API_KEY"):
            assert "openai" in available
        if os.environ.get("ANTHROPIC_API_KEY"):
            assert "anthropic" in available

    def test_initialize_providers(self):
        """Test provider initialization and registration."""
        from askgpt.modules.model_providers import ProviderRegistry

        registry = ProviderRegistry()
        registry.clear()

        # Initialize with test API keys
        initialize_providers(
            openai_api_key="test-openai-key", anthropic_api_key="test-anthropic-key"
        )

        # Check providers are registered
        provider_names = registry.list_provider_names()
        assert "openai" in provider_names
        assert "anthropic" in provider_names
        assert "ollama" in provider_names
        assert "lmstudio" in provider_names

    def test_initialize_providers_selective(self):
        """Test selective provider initialization."""
        from askgpt.modules.model_providers import ProviderRegistry

        registry = ProviderRegistry()
        registry.clear()

        # Initialize only specific providers
        initialize_providers(
            providers=["ollama", "lmstudio"],
            openai_api_key=None,
            anthropic_api_key=None,
        )

        provider_names = registry.list_provider_names()
        assert "ollama" in provider_names
        assert "lmstudio" in provider_names
        assert "openai" not in provider_names
        assert "anthropic" not in provider_names
