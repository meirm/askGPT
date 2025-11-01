"""
Provider Configuration for Multi-Model Support.

This module provides a thin abstraction layer for creating agents
with different model providers (OpenAI, Anthropic, Ollama).
"""

import logging
import os
from typing import Optional

import requests
from agents import (Agent, ModelSettings, OpenAIChatCompletionsModel,
                    set_tracing_disabled)
from openai import AsyncOpenAI

# Apply typing fixes for Python 3.12+ compatibility

logger = logging.getLogger(__name__)


class ProviderConfig:
    """Configuration for different model providers."""

    # Track created clients for cleanup
    _active_clients = []

    @staticmethod
    def get_model_settings(
        model: str, provider: str, base_settings: dict
    ) -> ModelSettings:
        """Get appropriate model settings for a given model and provider.

        Args:
            model: Model identifier
            provider: Provider name
            base_settings: Base settings dictionary with temperature, max_tokens, etc.

        Returns:
            ModelSettings configured appropriately for the model
        """
        # Filter settings based on model capabilities
        filtered_settings = {}

        # GPT-5 models have special requirements
        if model.startswith("gpt-5"):
            logger.debug(
                f"Configuring GPT-5 model {model} - using max_completion_tokens"
            )
            # GPT-5 uses max_completion_tokens instead of max_tokens
            if "max_tokens" in base_settings:
                filtered_settings["max_completion_tokens"] = base_settings["max_tokens"]
            # GPT-5 models only support temperature=1 (default)
            # Don't include temperature in settings
        else:
            # Other models support all settings
            filtered_settings = base_settings.copy()

        # Anthropic models use the same parameters via OpenAI-compatible endpoint
        if provider == "anthropic":
            pass

        logger.debug(f"Model settings for {model}: {filtered_settings}")
        return ModelSettings(**filtered_settings)

    @staticmethod
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
        """Create an agent with the appropriate provider configuration.

        Args:
            name: Agent name
            instructions: System instructions for the agent
            tools: List of tool functions
            model: Model identifier
            provider: Provider name ('openai', 'anthropic', 'ollama', 'lmstudio', 'ollama-native')
            model_settings: Optional model settings
            api_base: Optional API base URL (overrides environment variables)
            api_key: Optional API key (overrides environment variables)

        Returns:
            Configured Agent instance

        Raises:
            ValueError: If provider is not supported
        """

        if provider == "openai":
            # OpenAI configuration
            logger.debug(f"Creating OpenAI agent with model: {model}")
            if api_base or api_key:
                # Use custom client if api_base or api_key provided
                openai_client = AsyncOpenAI(
                    base_url=api_base if api_base else None,
                    api_key=api_key if api_key else os.getenv("OPENAI_API_KEY"),
                )
                ProviderConfig._active_clients.append(openai_client)
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
            ProviderConfig._active_clients.append(anthropic_client)
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

            # Use provided api_base or fall back to environment variable or default
            if api_base:
                ollama_url = api_base
            else:
                ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")

            # Ensure URL ends with /v1 for OpenAI compatibility
            if not ollama_url.endswith("/v1"):
                ollama_url = f"{ollama_url.rstrip('/')}/v1"

            # Use provided api_key or fall back to environment variable or default
            ollama_api_key = (
                api_key if api_key else os.getenv("OLLAMA_API_KEY", "ollama")
            )

            logger.debug(f"Ollama URL: {ollama_url}")
            ollama_client = AsyncOpenAI(base_url=ollama_url, api_key=ollama_api_key)
            ProviderConfig._active_clients.append(ollama_client)
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
            ProviderConfig._active_clients.append(lmstudio_client)
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

            # Use provided api_base or fall back to environment variable or default
            if api_base:
                ollama_host = api_base
            else:
                ollama_host = os.getenv("OLLAMA_API_URL", "http://localhost:11434")

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
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def cleanup_clients() -> None:
        """Clean up all active HTTP clients.

        This should be called before the event loop is closed to prevent
        RuntimeError exceptions from unclosed HTTP connections.
        """
        import asyncio

        async def close_clients():
            """Close all active clients asynchronously."""
            for client in ProviderConfig._active_clients:
                try:
                    await client.close()
                except Exception as e:
                    logger.debug(f"Error closing client: {e}")
            ProviderConfig._active_clients.clear()

        # Try to close clients if there's an event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the cleanup for later
                loop.create_task(close_clients())
            else:
                # Run it now
                loop.run_until_complete(close_clients())
        except RuntimeError:
            # No event loop or it's closed, can't clean up async clients
            logger.debug("Could not cleanup HTTP clients - no event loop available")
            ProviderConfig._active_clients.clear()

    @staticmethod
    def setup_provider(provider: str, enable_trace: bool = False) -> None:
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

    @staticmethod
    def validate_provider_setup(
        provider: str, model: str, available_models: dict, provider_requirements: dict
    ) -> tuple[bool, Optional[str]]:
        """Validate that provider is properly configured.

        Args:
            provider: Provider name
            model: Model identifier
            available_models: Dictionary of available models per provider
            provider_requirements: Dictionary of API key requirements

        Returns:
            Tuple of (is_valid, error_message)
        """

        # Check model availability
        if provider not in available_models:
            return False, f"Unknown provider: {provider}"

        if model not in available_models[provider]:
            return (
                False,
                f"Model {model} not available for {provider}. Available models: {', '.join(available_models[provider])}",
            )

        # Check API keys
        required_key = provider_requirements.get(provider)
        if required_key and not os.getenv(required_key):
            return False, f"Missing environment variable: {required_key}"

        # Check Ollama availability
        if provider == "ollama":
            try:
                # Get Ollama URL from environment variable with default
                ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
                # Remove /v1 suffix if present for API endpoint
                api_url = ollama_url.rstrip("/").removesuffix("/v1")
                response = requests.get(f"{api_url}/api/tags", timeout=1)
                models = [m["name"] for m in response.json().get("models", [])]
                if model not in models:
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
                return False, f"Error checking Ollama availability: {str(e)}"

        elif provider == "ollama-native":
            # Check Ollama-native availability using native client
            try:
                import ollama

                # Get Ollama URL from environment variable with default
                ollama_host = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
                # Remove /v1 suffix if present since native doesn't use it
                if ollama_host.endswith("/v1"):
                    ollama_host = ollama_host.rstrip("/v1")

                client = ollama.Client(host=ollama_host)
                models_info = client.list()
                # Ollama client returns ListResponse with .models attribute containing Model objects
                model_names = (
                    [m.model for m in models_info.models]
                    if hasattr(models_info, "models")
                    else []
                )

                if model not in model_names:
                    return (
                        False,
                        f"Model {model} not pulled in Ollama. Run: ollama pull {model}",
                    )
            except ImportError:
                return (
                    False,
                    "Ollama Python package not installed. Run: pip install ollama",
                )
            except Exception as e:
                return False, f"Error checking Ollama-native availability: {str(e)}"

        elif provider == "lmstudio":
            # Check LMStudio availability
            try:
                response = requests.get("http://localhost:1234/v1/models", timeout=1)
                models = [m["id"] for m in response.json().get("data", [])]
                if model not in models:
                    return (
                        False,
                        f"Model {model} not pulled in LMStudio. Run: lmstudio get {model}",
                    )
            except requests.ConnectionError:
                return False, "LMStudio service not running. Start with: lmstudio serve"

        return True, None
