"""
Concrete implementations of model providers for different AI services.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .model_providers import (ModelInfo, ModelProvider,
                              ProviderAuthenticationError,
                              ProviderConnectionError, ProviderRateLimitError,
                              ProviderRegistry)

logger = logging.getLogger(__name__)


# ============================================================================
# OpenAI Provider
# ============================================================================


class OpenAIProvider(ModelProvider):
    """Provider for OpenAI models."""

    # Model metadata (context length, costs, capabilities)
    MODEL_METADATA = {
        "gpt-4-turbo-preview": {
            "context_length": 128000,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.01,
            "output_cost_per_1k": 0.03,
            "capabilities": ["chat", "function_calling", "vision"],
        },
        "gpt-4": {
            "context_length": 8192,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.03,
            "output_cost_per_1k": 0.06,
            "capabilities": ["chat", "function_calling"],
        },
        "gpt-4-32k": {
            "context_length": 32768,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.06,
            "output_cost_per_1k": 0.12,
            "capabilities": ["chat", "function_calling"],
        },
        "gpt-3.5-turbo": {
            "context_length": 16385,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.0005,
            "output_cost_per_1k": 0.0015,
            "capabilities": ["chat", "function_calling"],
        },
        "gpt-3.5-turbo-16k": {
            "context_length": 16385,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.003,
            "output_cost_per_1k": 0.004,
            "capabilities": ["chat", "function_calling"],
        },
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        **kwargs,
    ):
        """Initialize OpenAI provider."""
        super().__init__(**kwargs)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url

    async def list_models(self, **kwargs) -> List[ModelInfo]:
        """List available OpenAI models."""
        if not self.api_key:
            raise ProviderAuthenticationError(
                "OpenAI API key not configured", provider="openai"
            )

        url = f"{self.base_url}/models"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 401:
                        raise ProviderAuthenticationError(
                            "Invalid OpenAI API key", provider="openai"
                        )
                    elif response.status == 429:
                        retry_after = response.headers.get("Retry-After", 60)
                        raise ProviderRateLimitError(
                            "OpenAI rate limit exceeded",
                            provider="openai",
                            retry_after=int(retry_after),
                        )
                    elif response.status != 200:
                        text = await response.text()
                        raise ProviderConnectionError(
                            f"OpenAI API error: {response.status} - {text}",
                            provider="openai",
                        )

                    data = await response.json()
                    models = []

                    for model_data in data.get("data", []):
                        model_id = model_data.get("id", "")

                        # Filter for chat models
                        if any(x in model_id for x in ["gpt", "davinci", "turbo"]):
                            model = ModelInfo(
                                id=model_id,
                                name=model_id,
                                provider="openai",
                                created_at=datetime.fromtimestamp(
                                    model_data.get("created", 0)
                                ),
                            )

                            # Enrich with metadata
                            model = self._enrich_model_info(model)
                            models.append(model)

                    return models

        except aiohttp.ClientConnectorError as e:
            raise ProviderConnectionError(
                f"Failed to connect to OpenAI API: {e}", provider="openai"
            )
        except asyncio.TimeoutError:
            raise ProviderConnectionError(
                "OpenAI API request timed out", provider="openai"
            )

    async def validate_connection(self) -> bool:
        """Validate connection to OpenAI."""
        if not self.api_key:
            return False

        try:
            # Try to list models with a short timeout
            await asyncio.wait_for(self.list_models(), timeout=5)
            return True
        except Exception:
            return False

    def _enrich_model_info(self, model: ModelInfo) -> ModelInfo:
        """Enrich model info with metadata."""
        # Check for exact match first
        if model.id in self.MODEL_METADATA:
            metadata = self.MODEL_METADATA[model.id]
            model.context_length = metadata["context_length"]
            model.max_output_tokens = metadata["max_output_tokens"]
            model.input_cost_per_1k = metadata["input_cost_per_1k"]
            model.output_cost_per_1k = metadata["output_cost_per_1k"]
            model.capabilities = metadata["capabilities"]
        else:
            # Check for partial matches (e.g., gpt-4-vision matches gpt-4)
            for key, metadata in self.MODEL_METADATA.items():
                if key in model.id or model.id.startswith(key.split("-")[0]):
                    model.context_length = metadata.get("context_length")
                    model.capabilities = metadata.get("capabilities", ["chat"])
                    break

        return model


# ============================================================================
# Anthropic Provider
# ============================================================================


class AnthropicProvider(ModelProvider):
    """Provider for Anthropic Claude models."""

    # Hardcoded model list since Anthropic doesn't have a models endpoint
    MODELS = [
        {
            "id": "claude-3-opus-20240229",
            "name": "Claude 3 Opus",
            "context_length": 200000,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.015,
            "output_cost_per_1k": 0.075,
            "capabilities": ["chat", "vision"],
        },
        {
            "id": "claude-3-sonnet-20240229",
            "name": "Claude 3 Sonnet",
            "context_length": 200000,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.003,
            "output_cost_per_1k": 0.015,
            "capabilities": ["chat", "vision"],
        },
        {
            "id": "claude-3-haiku-20240307",
            "name": "Claude 3 Haiku",
            "context_length": 200000,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.00025,
            "output_cost_per_1k": 0.00125,
            "capabilities": ["chat", "vision"],
        },
        {
            "id": "claude-2.1",
            "name": "Claude 2.1",
            "context_length": 200000,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.008,
            "output_cost_per_1k": 0.024,
            "capabilities": ["chat"],
            "deprecated": True,
            "replacement_model": "claude-3-sonnet-20240229",
        },
        {
            "id": "claude-2.0",
            "name": "Claude 2.0",
            "context_length": 100000,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.008,
            "output_cost_per_1k": 0.024,
            "capabilities": ["chat"],
            "deprecated": True,
            "replacement_model": "claude-3-sonnet-20240229",
        },
        {
            "id": "claude-instant-1.2",
            "name": "Claude Instant 1.2",
            "context_length": 100000,
            "max_output_tokens": 4096,
            "input_cost_per_1k": 0.0008,
            "output_cost_per_1k": 0.0024,
            "capabilities": ["chat"],
            "deprecated": True,
            "replacement_model": "claude-3-haiku-20240307",
        },
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com/v1",
        **kwargs,
    ):
        """Initialize Anthropic provider."""
        super().__init__(**kwargs)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = base_url

    async def list_models(self, **kwargs) -> List[ModelInfo]:
        """List available Anthropic models."""
        models = []

        for model_data in self.MODELS:
            model = ModelInfo(
                id=model_data["id"],
                name=model_data["name"],
                provider="anthropic",
                context_length=model_data.get("context_length"),
                max_output_tokens=model_data.get("max_output_tokens"),
                input_cost_per_1k=model_data.get("input_cost_per_1k"),
                output_cost_per_1k=model_data.get("output_cost_per_1k"),
                capabilities=model_data.get("capabilities", ["chat"]),
                deprecated=model_data.get("deprecated", False),
                replacement_model=model_data.get("replacement_model"),
            )
            models.append(model)

        return models

    async def validate_connection(self) -> bool:
        """Validate Anthropic configuration."""
        # Since we use hardcoded models, just check for API key
        return bool(self.api_key)


# ============================================================================
# Ollama Provider
# ============================================================================


class OllamaProvider(ModelProvider):
    """Provider for Ollama local models."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", **kwargs):
        """Initialize Ollama provider."""
        super().__init__(cache_ttl=60, **kwargs)  # Shorter cache for local models
        self.base_url = os.environ.get("OLLAMA_API_URL", base_url)

        # Remove /v1 suffix if present (we'll add it as needed)
        if self.base_url.endswith("/v1"):
            self.base_url = self.base_url[:-3]

    async def list_models(self, **kwargs) -> List[ModelInfo]:
        """List available Ollama models."""
        # Try the native Ollama API first, then OpenAI-compatible endpoint
        urls_to_try = [
            f"{self.base_url}/api/tags",  # Native Ollama API
            f"{self.base_url}/v1/models",  # OpenAI-compatible endpoint
        ]

        last_error = None

        for url in urls_to_try:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._parse_models(data, url)
            except aiohttp.ClientConnectorError:
                last_error = ProviderConnectionError(
                    f"Ollama server not running at {self.base_url}", provider="ollama"
                )
            except asyncio.TimeoutError:
                last_error = ProviderConnectionError(
                    "Ollama server request timed out", provider="ollama"
                )
            except Exception as e:
                last_error = e

        # If we get here, all attempts failed
        if last_error:
            raise last_error
        else:
            raise ProviderConnectionError(
                f"Failed to connect to Ollama at {self.base_url}", provider="ollama"
            )

    def _parse_models(self, data: Dict[str, Any], url: str) -> List[ModelInfo]:
        """Parse models from Ollama response."""
        models = []

        # Check if it's native Ollama format
        if "models" in data:
            for model_data in data["models"]:
                model = ModelInfo(
                    id=model_data.get("name", model_data.get("model", "unknown")),
                    name=model_data.get("name", model_data.get("model", "unknown")),
                    provider="ollama",
                    description=f"Size: {self._format_size(model_data.get('size', 0))}",
                )

                # Try to infer context length from model name
                model = self._infer_model_metadata(model)
                models.append(model)

        # Check if it's OpenAI-compatible format
        elif "data" in data:
            for model_data in data["data"]:
                model = ModelInfo(
                    id=model_data.get("id", "unknown"),
                    name=model_data.get("id", "unknown"),
                    provider="ollama",
                )
                model = self._infer_model_metadata(model)
                models.append(model)

        return models

    def _infer_model_metadata(self, model: ModelInfo) -> ModelInfo:
        """Infer model metadata from model name."""
        model_name_lower = model.id.lower()

        # Common model context lengths
        if "llama" in model_name_lower:
            if "70b" in model_name_lower:
                model.context_length = 4096
            elif "13b" in model_name_lower or "7b" in model_name_lower:
                model.context_length = 2048
        elif "mistral" in model_name_lower:
            model.context_length = 8192
        elif "mixtral" in model_name_lower:
            model.context_length = 32768
        elif "gemma" in model_name_lower:
            model.context_length = 8192
        elif "phi" in model_name_lower:
            model.context_length = 2048

        # All Ollama models support chat
        model.capabilities = ["chat"]

        return model

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"

    async def validate_connection(self) -> bool:
        """Validate connection to Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                # Check if Ollama is running
                async with session.get(
                    f"{self.base_url}/api/tags", timeout=5
                ) as response:
                    return response.status == 200
        except Exception:
            return False


# ============================================================================
# LMStudio Provider
# ============================================================================


class LMStudioProvider(ModelProvider):
    """Provider for LMStudio local models."""

    def __init__(self, base_url: str = "http://localhost:1234", **kwargs):
        """Initialize LMStudio provider."""
        super().__init__(cache_ttl=60, **kwargs)  # Shorter cache for local models
        self.base_url = os.environ.get("LMSTUDIO_API_URL", base_url)

        # Ensure we have the /v1 suffix
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"

    async def list_models(self, **kwargs) -> List[ModelInfo]:
        """List available LMStudio models."""
        url = f"{self.base_url}/models"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        raise ProviderConnectionError(
                            f"LMStudio server returned {response.status}",
                            provider="lmstudio",
                        )

                    data = await response.json()
                    models = []

                    # LMStudio uses OpenAI-compatible format
                    if "data" in data:
                        for model_data in data["data"]:
                            model = ModelInfo(
                                id=model_data.get("id", "unknown"),
                                name=model_data.get("id", "unknown"),
                                provider="lmstudio",
                                capabilities=["chat"],
                            )
                            models.append(model)
                    # Alternative format with models key
                    elif "models" in data:
                        for model_data in data["models"]:
                            model_id = model_data.get("id") or model_data.get(
                                "name", "unknown"
                            )
                            model = ModelInfo(
                                id=model_id,
                                name=model_data.get("name", model_id),
                                provider="lmstudio",
                                capabilities=["chat"],
                            )
                            models.append(model)

                    return models

        except aiohttp.ClientConnectorError:
            raise ProviderConnectionError(
                f"LMStudio server not running at {self.base_url}", provider="lmstudio"
            )
        except asyncio.TimeoutError:
            raise ProviderConnectionError(
                "LMStudio server request timed out", provider="lmstudio"
            )

    async def validate_connection(self) -> bool:
        """Validate connection to LMStudio."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models", timeout=5
                ) as response:
                    return response.status == 200
        except Exception:
            return False


# ============================================================================
# Provider Initialization and Auto-Detection
# ============================================================================


async def auto_detect_providers() -> List[str]:
    """Auto-detect which providers are available."""
    available = []

    # Check for API key-based providers
    if os.environ.get("OPENAI_API_KEY"):
        available.append("openai")

    if os.environ.get("ANTHROPIC_API_KEY"):
        available.append("anthropic")

    # Check for local providers
    ollama = OllamaProvider()
    if await ollama.validate_connection():
        available.append("ollama")

    lmstudio = LMStudioProvider()
    if await lmstudio.validate_connection():
        available.append("lmstudio")

    logger.info(f"Auto-detected providers: {available}")
    return available


def initialize_providers(
    providers: Optional[List[str]] = None,
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
    lmstudio_base_url: Optional[str] = None,
):
    """
    Initialize and register model providers.

    Args:
        providers: List of provider names to initialize (default: all)
        openai_api_key: OpenAI API key
        anthropic_api_key: Anthropic API key
        ollama_base_url: Ollama server URL
        lmstudio_base_url: LMStudio server URL
    """
    registry = ProviderRegistry()

    # Default to all providers if not specified
    if providers is None:
        providers = ["openai", "anthropic", "ollama", "lmstudio"]

    # Convert to lowercase for comparison
    providers = [p.lower() for p in providers]

    # Initialize each provider
    if "openai" in providers:
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if api_key:
            provider = OpenAIProvider(api_key=api_key)
            registry.register("openai", provider)
            logger.info("Registered OpenAI provider")

    if "anthropic" in providers:
        api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        # Anthropic provider can list hardcoded models even without API key
        provider = AnthropicProvider(api_key=api_key)
        registry.register("anthropic", provider)
        logger.info("Registered Anthropic provider")

    if "ollama" in providers:
        kwargs = {}
        if ollama_base_url:
            kwargs["base_url"] = ollama_base_url
        provider = OllamaProvider(**kwargs)
        registry.register("ollama", provider)
        logger.info("Registered Ollama provider")

    if "lmstudio" in providers:
        kwargs = {}
        if lmstudio_base_url:
            kwargs["base_url"] = lmstudio_base_url
        provider = LMStudioProvider(**kwargs)
        registry.register("lmstudio", provider)
        logger.info("Registered LMStudio provider")
