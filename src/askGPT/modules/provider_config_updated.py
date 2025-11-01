"""
Provider Configuration for Multi-Model Support with ConfigManager Integration.

This module provides a thin abstraction layer for creating agents
with different model providers (OpenAI, Anthropic, Ollama) using
the flexible configuration system.
"""

import logging
import os
# Import the new ConfigManager
import sys
from pathlib import Path
from typing import List, Optional

import requests
from agents import (Agent, ModelSettings, OpenAIChatCompletionsModel,
                    set_tracing_disabled)
from openai import AsyncOpenAI

# Apply typing fixes for Python 3.12+ compatibility

# Add parent directory to path to import config_manager from modules directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class ProviderConfig:
    """Configuration for different model providers using ConfigManager."""

    def __init__(self):
        """Initialize with ConfigManager."""
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        self._model_cache = {}  # Cache for discovered models

    def get_model_settings(
        self, model: str, provider: str, base_settings: dict
    ) -> ModelSettings:
        """Get appropriate model settings for a given model and provider.

        Args:
            model: Model identifier
            provider: Provider name
            base_settings: Base settings dictionary with temperature, max_tokens, etc.

        Returns:
            ModelSettings configured appropriately for the model
        """
        # Resolve model alias
        model = self.config_manager.resolve_model_alias(model)

        # Get provider configuration
        provider_config = self.config_manager.get_provider_config(provider)
        if not provider_config:
            logger.warning(
                f"No configuration found for provider {provider}, using base settings"
            )
            return ModelSettings(**base_settings)

        # Start with base settings
        filtered_settings = base_settings.copy()

        # Apply model-specific configuration if available
        if model in provider_config.models:
            model_config = provider_config.models[model]
            if model_config.max_tokens:
                filtered_settings["max_tokens"] = model_config.max_tokens
            if model_config.temperature is not None:
                filtered_settings["temperature"] = model_config.temperature

        # Special handling for GPT-5 models
        if model.startswith("gpt-5"):
            logger.debug(
                f"Configuring GPT-5 model {model} - using max_completion_tokens"
            )
            # GPT-5 uses max_completion_tokens instead of max_tokens
            if "max_tokens" in filtered_settings:
                filtered_settings["max_completion_tokens"] = filtered_settings.pop(
                    "max_tokens"
                )
            # GPT-5 models only support temperature=1 (default)
            filtered_settings.pop("temperature", None)

        logger.debug(f"Model settings for {model}: {filtered_settings}")
        return ModelSettings(**filtered_settings)

    def create_agent(
        self,
        name: str,
        instructions: str,
        tools: list,
        model: str,
        provider: str,
        model_settings: Optional[ModelSettings] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Agent:
        """Create an agent with the appropriate provider configuration.

        Args:
            name: Agent name
            instructions: System instructions for the agent
            tools: List of tool functions
            model: Model identifier
            provider: Provider name
            model_settings: Optional model settings
            api_base: Optional API base URL (overrides configuration)
            api_key: Optional API key (overrides configuration)

        Returns:
            Configured Agent instance

        Raises:
            ValueError: If provider is not supported
        """
        # Resolve model alias
        model = self.config_manager.resolve_model_alias(model)

        # Get provider configuration
        provider_config = self.config_manager.get_provider_config(provider)
        if not provider_config:
            # Check if it's a custom provider that might be allowed
            if provider not in [
                "openai",
                "anthropic",
                "ollama",
                "lmstudio",
                "ollama-native",
            ]:
                raise ValueError(f"Unsupported provider: {provider}")

        # Use configuration values as defaults
        if provider_config:
            if not api_base and provider_config.api_base:
                api_base = provider_config.api_base
            if not api_key and provider_config.api_key_env:
                api_key = os.getenv(provider_config.api_key_env)

        if provider == "openai":
            # OpenAI configuration
            logger.debug(f"Creating OpenAI agent with model: {model}")
            if api_base or api_key:
                # Use custom client if api_base or api_key provided
                openai_client = AsyncOpenAI(
                    base_url=api_base if api_base else None,
                    api_key=api_key if api_key else os.getenv("OPENAI_API_KEY"),
                )
                return Agent(
                    name=name,
                    instructions=instructions,
                    tools=tools,
                    model=OpenAIChatCompletionsModel(
                        model=model, openai_client=openai_client
                    ),
                    model_settings=model_settings,
                )
            else:
                # Use default OpenAI configuration
                return Agent(
                    name=name,
                    instructions=instructions,
                    tools=tools,
                    model=model,
                    model_settings=model_settings,
                )

        elif provider == "anthropic":
            # Use OpenAI SDK with Anthropic's OpenAI-compatible endpoint
            logger.debug(f"Creating Anthropic agent with model: {model}")
            anthropic_client = AsyncOpenAI(
                base_url=api_base if api_base else "https://api.anthropic.com/v1/",
                api_key=api_key if api_key else os.getenv("ANTHROPIC_API_KEY"),
            )
            return Agent(
                name=name,
                instructions=instructions,
                tools=tools,
                model=OpenAIChatCompletionsModel(
                    model=model, openai_client=anthropic_client
                ),
                model_settings=model_settings,
            )

        elif provider == "ollama":
            # Use OpenAI-compatible endpoint for Ollama
            logger.debug(f"Creating Ollama agent with model: {model}")

            # Use configuration or fallback to defaults
            if api_base:
                ollama_url = api_base
            else:
                ollama_url = (
                    provider_config.api_base
                    if provider_config
                    else "http://localhost:11434/v1"
                )

            # Ensure URL ends with /v1 for OpenAI compatibility
            if not ollama_url.endswith("/v1"):
                ollama_url = f"{ollama_url.rstrip('/')}/v1"

            # Use provided api_key or fall back to environment variable or default
            ollama_api_key = (
                api_key if api_key else os.getenv("OLLAMA_API_KEY", "ollama")
            )

            logger.debug(f"Ollama URL: {ollama_url}")
            ollama_client = AsyncOpenAI(base_url=ollama_url, api_key=ollama_api_key)
            return Agent(
                name=name,
                instructions=instructions,
                tools=tools,
                model=OpenAIChatCompletionsModel(
                    model=model, openai_client=ollama_client
                ),
                model_settings=model_settings,
            )

        elif provider == "lmstudio":
            # Use OpenAI-compatible endpoint for LMStudio
            logger.debug(f"Creating LMStudio agent with model: {model}")

            # Use provided api_base or fall back to environment variable or default
            if api_base:
                lmstudio_url = api_base
            else:
                lmstudio_url = os.getenv("LMSTUDIO_API_URL", "http://localhost:1234")

            # Ensure URL ends with /v1 for OpenAI compatibility
            if not lmstudio_url.endswith("/v1"):
                lmstudio_url = f"{lmstudio_url.rstrip('/')}/v1"

            # Use provided api_key or fall back to environment variable or default
            lmstudio_api_key = (
                api_key if api_key else os.getenv("LMSTUDIO_API_KEY", "lmstudio")
            )

            lmstudio_client = AsyncOpenAI(
                base_url=lmstudio_url, api_key=lmstudio_api_key
            )
            return Agent(
                name=name,
                instructions=instructions,
                tools=tools,
                model=OpenAIChatCompletionsModel(
                    model=model, openai_client=lmstudio_client
                ),
                model_settings=model_settings,
            )

        elif provider == "ollama-native":
            # Use native Ollama Python client with wrapper
            logger.debug(f"Creating Ollama-native agent with model: {model}")

            from .ollama_wrapper import AsyncOllamaOpenAIWrapper

            # Use configuration or fallback to defaults
            if api_base:
                ollama_host = api_base
            else:
                ollama_host = (
                    provider_config.api_base
                    if provider_config
                    else "http://localhost:11434"
                )

            # Remove /v1 suffix if present since native Ollama doesn't use it
            if ollama_host.endswith("/v1"):
                ollama_host = ollama_host.rstrip("/v1")

            # Prepare headers with API key if provided
            headers = {}
            if api_key:
                headers["Authorization"] = api_key
            elif os.getenv("OLLAMA_API_KEY"):
                headers["Authorization"] = os.getenv("OLLAMA_API_KEY")

            logger.debug(f"Ollama-native host: {ollama_host}")

            # Create wrapped client
            ollama_client = AsyncOllamaOpenAIWrapper(
                host=ollama_host, headers=headers if headers else None
            )

            return Agent(
                name=name,
                instructions=instructions,
                tools=tools,
                model=OpenAIChatCompletionsModel(
                    model=model, openai_client=ollama_client
                ),
                model_settings=model_settings,
            )
        else:
            # Try to create agent for custom provider using OpenAI-compatible endpoint
            if provider_config and provider_config.api_base:
                logger.info(
                    f"Creating agent for custom provider {provider} with model: {model}"
                )

                custom_url = api_base if api_base else provider_config.api_base
                if not custom_url.endswith("/v1"):
                    custom_url = f"{custom_url.rstrip('/')}/v1"

                custom_api_key = api_key
                if not custom_api_key and provider_config.api_key_env:
                    custom_api_key = os.getenv(provider_config.api_key_env, "custom")

                custom_client = AsyncOpenAI(
                    base_url=custom_url,
                    api_key=custom_api_key if custom_api_key else "custom",
                )

                return Agent(
                    name=name,
                    instructions=instructions,
                    tools=tools,
                    model=OpenAIChatCompletionsModel(
                        model=model, openai_client=custom_client
                    ),
                    model_settings=model_settings,
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")

    def setup_provider(self, provider: str, enable_trace: bool = False) -> None:
        """Setup provider-specific configurations.

        Args:
            provider: Provider name
            enable_trace: If True, explicitly enable tracing (requires OPENAI_API_KEY)
        """
        # If tracing is explicitly requested
        if enable_trace:
            # Check if we have an OpenAI API key for tracing
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key or openai_key == "sk-none":
                logger.warning(
                    "Tracing requested but no valid OpenAI API key found. Disabling tracing."
                )
                set_tracing_disabled(True)
            else:
                logger.info(f"Tracing explicitly enabled for {provider} provider")
                set_tracing_disabled(False)
        else:
            # Default behavior: disable tracing for all non-OpenAI providers
            if provider in ["ollama", "lmstudio", "ollama-native"]:
                # Always disable tracing for local models
                logger.info(f"Disabling tracing for {provider} provider (local model)")
                set_tracing_disabled(True)
            elif provider != "openai":
                # Disable tracing for other non-OpenAI providers by default
                logger.info(f"Disabling tracing for {provider} provider (not OpenAI)")
                set_tracing_disabled(True)
            else:
                # For OpenAI provider, enable tracing by default if API key is available
                openai_key = os.getenv("OPENAI_API_KEY")
                if not openai_key or openai_key == "sk-none":
                    logger.info(
                        "Disabling tracing for OpenAI provider (no valid API key)"
                    )
                    set_tracing_disabled(True)
                else:
                    logger.debug("Tracing enabled for OpenAI provider")

    def discover_models(self, provider: str) -> List[str]:
        """Discover available models from a provider.

        Args:
            provider: Provider name

        Returns:
            List of available model names
        """
        # Check cache first
        cache_key = f"{provider}_models"
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        provider_config = self.config_manager.get_provider_config(provider)
        if not provider_config:
            return []

        discovered_models = []

        # If discovery is enabled and we have an endpoint
        if provider_config.discover_models and provider_config.discovery_endpoint:
            if provider == "ollama" or provider == "ollama-native":
                try:
                    # Get Ollama URL
                    ollama_url = provider_config.api_base or "http://localhost:11434"
                    # Remove /v1 suffix if present for API endpoint
                    api_url = ollama_url.rstrip("/").removesuffix("/v1")

                    response = requests.get(
                        f"{api_url}{provider_config.discovery_endpoint}",
                        timeout=provider_config.timeout or 30,
                    )

                    if response.status_code == 200:
                        models_data = response.json()
                        discovered_models = [
                            m["name"] for m in models_data.get("models", [])
                        ]
                        logger.info(
                            f"Discovered {len(discovered_models)} models from Ollama"
                        )
                except Exception as e:
                    logger.warning(f"Failed to discover models from {provider}: {e}")

        # Combine discovered models with known models
        all_models = list(set(provider_config.known_models + discovered_models))

        # Cache the result
        self._model_cache[cache_key] = all_models

        return all_models

    def validate_model_provider_combination(
        self, provider: str, model: str, strict: bool = False
    ) -> tuple[bool, Optional[str]]:
        """Validate that a model can be used with a provider.

        Args:
            provider: Provider name
            model: Model identifier
            strict: If True, only allow known models. If False, allow unknown models
                   if provider configuration allows it.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Resolve model alias
        model = self.config_manager.resolve_model_alias(model)

        # Get provider configuration
        provider_config = self.config_manager.get_provider_config(provider)
        if not provider_config:
            # Check if it's a built-in provider we support
            if provider not in [
                "openai",
                "anthropic",
                "ollama",
                "lmstudio",
                "ollama-native",
            ]:
                return False, f"Unknown provider: {provider}"
            # For built-in providers without config, allow any model
            logger.warning(
                f"No configuration for provider {provider}, allowing model {model}"
            )
            return True, None

        # If strict mode, only allow known models
        if strict:
            # Get all known models (including discovered ones)
            all_models = self.discover_models(provider)
            if model not in all_models:
                return False, (
                    f"Model {model} not in known models for {provider}. "
                    f"Available models: {', '.join(all_models[:5])}"
                    f"{f'... and {len(all_models)-5} more' if len(all_models) > 5 else ''}"
                )
        else:
            # Non-strict mode: check if unknown models are allowed
            if not provider_config.allow_unknown_models:
                # Must be in known models
                all_models = self.discover_models(provider)
                if model not in all_models:
                    return False, (
                        f"Model {model} not available for {provider}. "
                        f"Provider does not allow unknown models. "
                        f"Available models: {', '.join(all_models[:5])}"
                        f"{f'... and {len(all_models)-5} more' if len(all_models) > 5 else ''}"
                    )
            else:
                # Unknown models are allowed - show a warning but allow it
                all_models = self.discover_models(provider)
                if model not in all_models:
                    logger.info(
                        f"Model {model} not in known models for {provider}, "
                        f"but provider allows unknown models. Proceeding..."
                    )

        # Check if model is deprecated
        if model in provider_config.models:
            model_config = provider_config.models[model]
            if model_config.deprecated:
                logger.warning(
                    f"Model {model} is deprecated. {model_config.deprecation_message or ''}"
                )

        return True, None

    def validate_provider_setup(
        self, provider: str, model: str
    ) -> tuple[bool, Optional[str]]:
        """Validate that provider is properly configured and accessible.

        Args:
            provider: Provider name
            model: Model identifier

        Returns:
            Tuple of (is_valid, error_message)
        """
        # First check if the model/provider combination is valid
        is_valid, error = self.validate_model_provider_combination(
            provider, model, strict=False
        )
        if not is_valid:
            return False, error

        # Get provider configuration
        provider_config = self.config_manager.get_provider_config(provider)

        # Check API keys
        if provider_config and provider_config.api_key_env:
            api_key = os.getenv(provider_config.api_key_env)
            if not api_key:
                return (
                    False,
                    f"Missing environment variable: {provider_config.api_key_env}",
                )

        # Check service availability for local providers
        if provider in ["ollama", "ollama-native"]:
            try:
                # Get Ollama URL from configuration
                ollama_url = (
                    provider_config.api_base
                    if provider_config
                    else "http://localhost:11434"
                )
                # Remove /v1 suffix if present for API endpoint
                api_url = ollama_url.rstrip("/").removesuffix("/v1")

                response = requests.get(
                    f"{api_url}/api/tags",
                    timeout=provider_config.timeout if provider_config else 1,
                )

                if response.status_code == 200:
                    models = [m["name"] for m in response.json().get("models", [])]
                    if model not in models:
                        # Model not pulled, but we can still allow it if configured to
                        if not provider_config or provider_config.allow_unknown_models:
                            logger.warning(
                                f"Model {model} not pulled in Ollama. "
                                f"You may need to run: ollama pull {model}"
                            )
                        else:
                            return (
                                False,
                                f"Model {model} not pulled in Ollama. Run: ollama pull {model}",
                            )
            except requests.ConnectionError:
                return False, "Ollama service not running. Start with: ollama serve"
            except requests.Timeout:
                return (
                    False,
                    "Ollama service timeout. Check if service is running: ollama serve",
                )
            except Exception as e:
                logger.warning(f"Could not check Ollama availability: {e}")
                # Don't fail if we can't check - let it fail later if needed

        elif provider == "lmstudio":
            try:
                lmstudio_url = (
                    provider_config.api_base
                    if provider_config
                    else "http://localhost:1234"
                )
                if not lmstudio_url.endswith("/v1"):
                    lmstudio_url = f"{lmstudio_url.rstrip('/')}/v1"

                response = requests.get(
                    f"{lmstudio_url}/models",
                    timeout=provider_config.timeout if provider_config else 1,
                )

                if response.status_code == 200:
                    models = [m["id"] for m in response.json().get("data", [])]
                    if model not in models and (
                        not provider_config or not provider_config.allow_unknown_models
                    ):
                        return False, f"Model {model} not available in LMStudio"
            except requests.ConnectionError:
                return False, "LMStudio service not running"
            except Exception as e:
                logger.warning(f"Could not check LMStudio availability: {e}")

        return True, None


# Global instance for backward compatibility
_provider_config: Optional[ProviderConfig] = None


def get_provider_config() -> ProviderConfig:
    """Get global ProviderConfig instance."""
    global _provider_config
    if _provider_config is None:
        _provider_config = ProviderConfig()
    return _provider_config


# Backward compatibility static methods
def get_model_settings(model: str, provider: str, base_settings: dict) -> ModelSettings:
    """Backward compatibility wrapper."""
    return get_provider_config().get_model_settings(model, provider, base_settings)


def create_agent(
    name: str,
    instructions: str,
    tools: list,
    model: str,
    provider: str,
    model_settings: Optional[ModelSettings] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Agent:
    """Backward compatibility wrapper."""
    return get_provider_config().create_agent(
        name, instructions, tools, model, provider, model_settings, api_base, api_key
    )


def setup_provider(provider: str, enable_trace: bool = False) -> None:
    """Backward compatibility wrapper."""
    return get_provider_config().setup_provider(provider, enable_trace)


def validate_provider_setup(provider: str, model: str) -> tuple[bool, Optional[str]]:
    """Backward compatibility wrapper."""
    return get_provider_config().validate_provider_setup(provider, model)


def validate_model_provider_combination(
    provider: str, model: str, strict: bool = False
) -> tuple[bool, Optional[str]]:
    """Backward compatibility wrapper."""
    return get_provider_config().validate_model_provider_combination(
        provider, model, strict
    )
