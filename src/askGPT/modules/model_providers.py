"""
Model provider abstraction layer for listing available models.

This module provides a unified interface for querying available models
from different AI providers (OpenAI, Anthropic, Ollama, LMStudio, etc.).
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class ModelInfo:
    """Information about an AI model."""

    # Required fields
    id: str
    name: str
    provider: str

    # Optional metadata
    context_length: Optional[int] = None
    max_output_tokens: Optional[int] = None
    input_cost_per_1k: Optional[float] = None
    output_cost_per_1k: Optional[float] = None
    capabilities: List[str] = field(default_factory=list)
    deprecated: bool = False
    replacement_model: Optional[str] = None

    # Additional metadata
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        if data.get("created_at"):
            data["created_at"] = data["created_at"].isoformat()
        if data.get("updated_at"):
            data["updated_at"] = data["updated_at"].isoformat()
        return data

    def __eq__(self, other):
        """Compare ModelInfo instances by id and provider."""
        if not isinstance(other, ModelInfo):
            return False
        return self.id == other.id and self.provider == other.provider

    def __hash__(self):
        """Hash based on id and provider."""
        return hash((self.id, self.provider))


class ModelCapability(Enum):
    """Standard model capabilities."""

    CHAT = "chat"
    COMPLETION = "completion"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    AUDIO = "audio"
    CODE = "code"
    EMBEDDINGS = "embeddings"
    FINE_TUNING = "fine_tuning"


# ============================================================================
# Error Hierarchy
# ============================================================================


class ModelProviderError(Exception):
    """Base exception for model provider errors."""

    pass


class ProviderConnectionError(ModelProviderError):
    """Error connecting to provider API."""

    def __init__(self, message: str, provider: str = None):
        super().__init__(message)
        self.provider = provider


class ProviderAuthenticationError(ModelProviderError):
    """Authentication error with provider."""

    def __init__(self, message: str, provider: str = None):
        super().__init__(message)
        self.provider = provider


class ProviderRateLimitError(ModelProviderError):
    """Rate limit exceeded for provider."""

    def __init__(self, message: str, provider: str = None, retry_after: int = None):
        super().__init__(message)
        self.provider = provider
        self.retry_after = retry_after  # Seconds to wait before retry


class ProviderNotFoundError(ModelProviderError):
    """Provider not found or not registered."""

    def __init__(self, provider_name: str):
        super().__init__(f"Provider '{provider_name}' not found")
        self.provider_name = provider_name


# ============================================================================
# Abstract Provider Interface
# ============================================================================


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    def __init__(self, cache_ttl: int = 300):
        """
        Initialize provider.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache_ttl = cache_ttl
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None

    @abstractmethod
    async def list_models(self, **kwargs) -> List[ModelInfo]:
        """
        List available models from the provider.

        Args:
            **kwargs: Provider-specific parameters

        Returns:
            List of ModelInfo objects

        Raises:
            ProviderConnectionError: If connection fails
            ProviderAuthenticationError: If authentication fails
            ProviderRateLimitError: If rate limited
        """
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate connection to the provider.

        Returns:
            True if connection is valid, False otherwise
        """
        pass

    async def get_models(
        self, force_refresh: bool = False, **kwargs
    ) -> List[ModelInfo]:
        """
        Get models with caching support.

        Args:
            force_refresh: Force cache refresh
            **kwargs: Provider-specific parameters

        Returns:
            List of ModelInfo objects
        """
        # Check cache validity
        if not force_refresh and self._is_cache_valid():
            logger.debug(f"Using cached models for {self.__class__.__name__}")
            return self._cache["models"]

        # Fetch fresh data
        logger.debug(f"Fetching fresh models for {self.__class__.__name__}")
        try:
            models = await self.list_models(**kwargs)

            # Update cache
            self._cache = {"models": models, "timestamp": datetime.now()}
            self._cache_timestamp = datetime.now()

            return models
        except Exception as e:
            logger.error(f"Error fetching models from {self.__class__.__name__}: {e}")

            # Return cached data if available, even if expired
            if self._cache and self._cache.get("models"):
                logger.warning(f"Returning stale cache for {self.__class__.__name__}")
                return self._cache["models"]

            raise

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache or not self._cache_timestamp:
            return False

        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self.cache_ttl

    def clear_cache(self):
        """Clear the cache."""
        self._cache = None
        self._cache_timestamp = None


# ============================================================================
# Provider Factory
# ============================================================================


class ProviderFactory:
    """Factory for creating model provider instances."""

    def __init__(self):
        self._providers: Dict[str, Type[ModelProvider]] = {}

    def register_provider(self, name: str, provider_class: Type[ModelProvider]):
        """
        Register a provider class.

        Args:
            name: Provider name (e.g., 'openai', 'anthropic')
            provider_class: Provider class type
        """
        self._providers[name.lower()] = provider_class
        logger.debug(f"Registered provider: {name}")

    def create_provider(self, name: str, **kwargs) -> ModelProvider:
        """
        Create a provider instance.

        Args:
            name: Provider name
            **kwargs: Provider-specific configuration

        Returns:
            Provider instance

        Raises:
            ProviderNotFoundError: If provider not registered
        """
        provider_name = name.lower()

        if provider_name not in self._providers:
            raise ProviderNotFoundError(provider_name)

        provider_class = self._providers[provider_name]
        return provider_class(**kwargs)

    def list_providers(self) -> List[str]:
        """List registered provider names."""
        return list(self._providers.keys())


# ============================================================================
# Provider Registry (Singleton)
# ============================================================================


class ProviderRegistry:
    """Singleton registry for managing all model providers."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._providers: Dict[str, ModelProvider] = {}
        self._factory = ProviderFactory()
        self._initialized = True
        logger.debug("Initialized ProviderRegistry singleton")

    def register(self, name: str, provider: ModelProvider):
        """
        Register a provider instance.

        Args:
            name: Provider name
            provider: Provider instance
        """
        self._providers[name.lower()] = provider
        logger.debug(f"Registered provider instance: {name}")

    def get_provider(self, name: str) -> Optional[ModelProvider]:
        """
        Get a registered provider.

        Args:
            name: Provider name

        Returns:
            Provider instance or None
        """
        return self._providers.get(name.lower())

    async def list_all_models(self, skip_errors: bool = True) -> List[ModelInfo]:
        """
        List models from all registered providers.

        Args:
            skip_errors: Skip providers that fail instead of raising

        Returns:
            Combined list of models from all providers
        """
        all_models = []
        tasks = []

        for name, provider in self._providers.items():
            tasks.append(self._fetch_provider_models(name, provider, skip_errors))

        results = await asyncio.gather(*tasks)

        for models in results:
            if models:
                all_models.extend(models)

        return all_models

    async def list_provider_models(self, provider_name: str) -> List[ModelInfo]:
        """
        List models from a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            List of models from the provider

        Raises:
            ProviderNotFoundError: If provider not registered
        """
        provider = self.get_provider(provider_name)

        if not provider:
            raise ProviderNotFoundError(provider_name)

        return await provider.get_models()

    async def _fetch_provider_models(
        self, name: str, provider: ModelProvider, skip_errors: bool
    ) -> Optional[List[ModelInfo]]:
        """Fetch models from a provider with error handling."""
        try:
            logger.debug(f"Fetching models from {name}")
            return await provider.get_models()
        except Exception as e:
            logger.error(f"Error fetching models from {name}: {e}")

            if not skip_errors:
                raise

            return None

    def clear(self):
        """Clear all registered providers."""
        self._providers.clear()
        logger.debug("Cleared all providers from registry")

    def list_provider_names(self) -> List[str]:
        """List names of registered providers."""
        return list(self._providers.keys())
