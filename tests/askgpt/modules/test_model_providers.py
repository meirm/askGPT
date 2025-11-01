"""Tests for model provider abstraction layer."""

import asyncio
from typing import List

import pytest
# These will be imported from the actual implementation
from askgpt.modules.model_providers import (ModelInfo, ModelProvider,
                                                ModelProviderError,
                                                ProviderAuthenticationError,
                                                ProviderConnectionError,
                                                ProviderFactory,
                                                ProviderNotFoundError,
                                                ProviderRateLimitError,
                                                ProviderRegistry)


class TestModelInfo:
    """Test the ModelInfo data structure."""

    def test_model_info_creation(self):
        """Test creating a ModelInfo instance with all fields."""
        model = ModelInfo(
            id="gpt-4",
            name="GPT-4",
            provider="openai",
            context_length=8192,
            max_output_tokens=4096,
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06,
            capabilities=["chat", "function_calling"],
            deprecated=False,
            replacement_model=None,
        )

        assert model.id == "gpt-4"
        assert model.name == "GPT-4"
        assert model.provider == "openai"
        assert model.context_length == 8192
        assert model.max_output_tokens == 4096
        assert model.input_cost_per_1k == 0.03
        assert model.output_cost_per_1k == 0.06
        assert "chat" in model.capabilities
        assert "function_calling" in model.capabilities
        assert model.deprecated is False
        assert model.replacement_model is None

    def test_model_info_optional_fields(self):
        """Test ModelInfo with minimal required fields."""
        model = ModelInfo(id="test-model", name="Test Model", provider="test")

        assert model.id == "test-model"
        assert model.name == "Test Model"
        assert model.provider == "test"
        assert model.context_length is None
        assert model.max_output_tokens is None
        assert model.input_cost_per_1k is None
        assert model.output_cost_per_1k is None
        assert model.capabilities == []
        assert model.deprecated is False
        assert model.replacement_model is None

    def test_model_info_to_dict(self):
        """Test converting ModelInfo to dictionary."""
        model = ModelInfo(
            id="claude-3",
            name="Claude 3",
            provider="anthropic",
            context_length=200000,
            capabilities=["chat", "vision"],
        )

        model_dict = model.to_dict()

        assert model_dict["id"] == "claude-3"
        assert model_dict["name"] == "Claude 3"
        assert model_dict["provider"] == "anthropic"
        assert model_dict["context_length"] == 200000
        assert model_dict["capabilities"] == ["chat", "vision"]

    def test_model_info_equality(self):
        """Test ModelInfo equality comparison."""
        model1 = ModelInfo(id="model-1", name="Model 1", provider="provider1")
        model2 = ModelInfo(id="model-1", name="Model 1", provider="provider1")
        model3 = ModelInfo(id="model-2", name="Model 2", provider="provider1")

        assert model1 == model2
        assert model1 != model3


class TestModelProvider:
    """Test the abstract ModelProvider class."""

    def test_provider_abstract_methods(self):
        """Test that ModelProvider enforces abstract methods."""
        with pytest.raises(TypeError):
            # Cannot instantiate abstract class
            ModelProvider()

    @pytest.mark.asyncio
    async def test_provider_list_models(self):
        """Test the list_models abstract method."""

        class TestProvider(ModelProvider):
            async def list_models(self, **kwargs) -> List[ModelInfo]:
                return [
                    ModelInfo(id="test-1", name="Test 1", provider="test"),
                    ModelInfo(id="test-2", name="Test 2", provider="test"),
                ]

            async def validate_connection(self) -> bool:
                return True

        provider = TestProvider()
        models = await provider.list_models()

        assert len(models) == 2
        assert models[0].id == "test-1"
        assert models[1].id == "test-2"

    @pytest.mark.asyncio
    async def test_provider_validate_connection(self):
        """Test the validate_connection abstract method."""

        class TestProvider(ModelProvider):
            async def list_models(self, **kwargs) -> List[ModelInfo]:
                return []

            async def validate_connection(self) -> bool:
                return True

        provider = TestProvider()
        is_valid = await provider.validate_connection()

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_provider_with_cache(self):
        """Test provider with caching enabled."""

        class CachedProvider(ModelProvider):
            def __init__(self):
                super().__init__(cache_ttl=60)  # 60 second cache
                self.call_count = 0

            async def list_models(self, **kwargs) -> List[ModelInfo]:
                self.call_count += 1
                return [
                    ModelInfo(id="cached-model", name="Cached Model", provider="test")
                ]

            async def validate_connection(self) -> bool:
                return True

        provider = CachedProvider()

        # First call should hit the actual method
        models1 = await provider.get_models()
        assert provider.call_count == 1
        assert len(models1) == 1

        # Second call should use cache
        models2 = await provider.get_models()
        assert provider.call_count == 1  # Should not increase
        assert models1 == models2

    @pytest.mark.asyncio
    async def test_provider_cache_invalidation(self):
        """Test cache invalidation."""

        class CachedProvider(ModelProvider):
            def __init__(self):
                super().__init__(cache_ttl=0.1)  # 100ms cache
                self.call_count = 0

            async def list_models(self, **kwargs) -> List[ModelInfo]:
                self.call_count += 1
                return [
                    ModelInfo(
                        id=f"model-{self.call_count}",
                        name=f"Model {self.call_count}",
                        provider="test",
                    )
                ]

            async def validate_connection(self) -> bool:
                return True

        provider = CachedProvider()

        # First call
        models1 = await provider.get_models()
        assert provider.call_count == 1

        # Wait for cache to expire
        await asyncio.sleep(0.2)

        # Should hit the actual method again
        models2 = await provider.get_models()
        assert provider.call_count == 2
        assert models1[0].id != models2[0].id


class TestProviderFactory:
    """Test the ProviderFactory pattern."""

    def test_factory_create_provider(self):
        """Test creating providers through factory."""
        factory = ProviderFactory()

        # Register a test provider
        class TestProvider(ModelProvider):
            async def list_models(self, **kwargs) -> List[ModelInfo]:
                return []

            async def validate_connection(self) -> bool:
                return True

        factory.register_provider("test", TestProvider)

        # Create instance
        provider = factory.create_provider("test")
        assert isinstance(provider, TestProvider)

    def test_factory_unknown_provider(self):
        """Test factory with unknown provider."""
        factory = ProviderFactory()

        with pytest.raises(ProviderNotFoundError):
            factory.create_provider("unknown")

    def test_factory_with_config(self):
        """Test factory with provider configuration."""
        factory = ProviderFactory()

        class ConfigurableProvider(ModelProvider):
            def __init__(self, api_key: str = None, base_url: str = None):
                super().__init__()
                self.api_key = api_key
                self.base_url = base_url

            async def list_models(self, **kwargs) -> List[ModelInfo]:
                return []

            async def validate_connection(self) -> bool:
                return self.api_key is not None

        factory.register_provider("configurable", ConfigurableProvider)

        # Create with config
        provider = factory.create_provider(
            "configurable", api_key="test-key", base_url="http://test.com"
        )

        assert provider.api_key == "test-key"
        assert provider.base_url == "http://test.com"


class TestProviderRegistry:
    """Test the ProviderRegistry singleton."""

    def test_registry_singleton(self):
        """Test that ProviderRegistry is a singleton."""
        registry1 = ProviderRegistry()
        registry2 = ProviderRegistry()

        assert registry1 is registry2

    @pytest.mark.asyncio
    async def test_registry_list_all_models(self):
        """Test listing models from all registered providers."""
        registry = ProviderRegistry()
        registry.clear()  # Clear any existing providers

        # Create mock providers
        class Provider1(ModelProvider):
            async def list_models(self, **kwargs) -> List[ModelInfo]:
                return [
                    ModelInfo(
                        id="p1-model1", name="Provider1 Model1", provider="provider1"
                    ),
                    ModelInfo(
                        id="p1-model2", name="Provider1 Model2", provider="provider1"
                    ),
                ]

            async def validate_connection(self) -> bool:
                return True

        class Provider2(ModelProvider):
            async def list_models(self, **kwargs) -> List[ModelInfo]:
                return [
                    ModelInfo(
                        id="p2-model1", name="Provider2 Model1", provider="provider2"
                    )
                ]

            async def validate_connection(self) -> bool:
                return True

        registry.register("provider1", Provider1())
        registry.register("provider2", Provider2())

        # List all models
        all_models = await registry.list_all_models()

        assert len(all_models) == 3
        assert any(m.id == "p1-model1" for m in all_models)
        assert any(m.id == "p1-model2" for m in all_models)
        assert any(m.id == "p2-model1" for m in all_models)

    @pytest.mark.asyncio
    async def test_registry_list_provider_models(self):
        """Test listing models from specific provider."""
        registry = ProviderRegistry()
        registry.clear()

        class TestProvider(ModelProvider):
            async def list_models(self, **kwargs) -> List[ModelInfo]:
                return [ModelInfo(id="test-model", name="Test Model", provider="test")]

            async def validate_connection(self) -> bool:
                return True

        registry.register("test", TestProvider())

        # List specific provider models
        models = await registry.list_provider_models("test")

        assert len(models) == 1
        assert models[0].id == "test-model"

    @pytest.mark.asyncio
    async def test_registry_handle_provider_errors(self):
        """Test registry handles provider errors gracefully."""
        registry = ProviderRegistry()
        registry.clear()

        # Provider that fails
        class FailingProvider(ModelProvider):
            async def list_models(self, **kwargs) -> List[ModelInfo]:
                raise ProviderConnectionError("Connection failed")

            async def validate_connection(self) -> bool:
                return False

        # Provider that works
        class WorkingProvider(ModelProvider):
            async def list_models(self, **kwargs) -> List[ModelInfo]:
                return [
                    ModelInfo(
                        id="working-model", name="Working Model", provider="working"
                    )
                ]

            async def validate_connection(self) -> bool:
                return True

        registry.register("failing", FailingProvider())
        registry.register("working", WorkingProvider())

        # Should return models from working provider and skip failing one
        all_models = await registry.list_all_models(skip_errors=True)

        assert len(all_models) == 1
        assert all_models[0].id == "working-model"


class TestErrorHandling:
    """Test error handling hierarchy."""

    def test_base_error(self):
        """Test base ModelProviderError."""
        error = ModelProviderError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_connection_error(self):
        """Test ProviderConnectionError."""
        error = ProviderConnectionError("Cannot connect", provider="test")
        assert "Cannot connect" in str(error)
        assert error.provider == "test"
        assert isinstance(error, ModelProviderError)

    def test_authentication_error(self):
        """Test ProviderAuthenticationError."""
        error = ProviderAuthenticationError("Invalid API key", provider="openai")
        assert "Invalid API key" in str(error)
        assert error.provider == "openai"
        assert isinstance(error, ModelProviderError)

    def test_rate_limit_error(self):
        """Test ProviderRateLimitError."""
        error = ProviderRateLimitError(
            "Rate limit exceeded", provider="anthropic", retry_after=60
        )
        assert "Rate limit exceeded" in str(error)
        assert error.provider == "anthropic"
        assert error.retry_after == 60
        assert isinstance(error, ModelProviderError)

    def test_not_found_error(self):
        """Test ProviderNotFoundError."""
        error = ProviderNotFoundError("unknown-provider")
        assert "unknown-provider" in str(error)
        assert isinstance(error, ModelProviderError)
