"""
Integration module to connect ConfigManager with existing code.

This module provides a bridge between the new flexible configuration system
and the existing codebase, allowing gradual migration.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

from .config_manager import get_config_manager
from .provider_config import ProviderConfig as OriginalProviderConfig

logger = logging.getLogger(__name__)


class FlexibleProviderConfig(OriginalProviderConfig):
    """Extended ProviderConfig that uses ConfigManager for validation."""

    @staticmethod
    def validate_provider_setup(
        provider: str,
        model: str,
        available_models: Optional[Dict] = None,  # Ignored, uses ConfigManager
        provider_requirements: Optional[Dict] = None,  # Ignored, uses ConfigManager
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate provider setup using ConfigManager.

        This method overrides the original to use flexible configuration
        instead of hardcoded model lists.

        Args:
            provider: Provider name
            model: Model identifier
            available_models: Ignored (kept for compatibility)
            provider_requirements: Ignored (kept for compatibility)

        Returns:
            Tuple of (is_valid, error_message)
        """
        config_manager = get_config_manager()

        # Resolve model alias
        model = config_manager.resolve_model_alias(model)

        # Check if model is allowed for provider
        if not config_manager.is_model_allowed(provider, model):
            # Get provider config for better error message
            provider_config = config_manager.get_provider_config(provider)
            if not provider_config:
                return False, f"Unknown provider: {provider}"

            # If unknown models are not allowed, show available models
            if not provider_config.allow_unknown_models:
                known_models = provider_config.known_models[:5]  # Show first 5
                models_str = ", ".join(known_models)
                if len(provider_config.known_models) > 5:
                    models_str += (
                        f", ... and {len(provider_config.known_models) - 5} more"
                    )
                return (
                    False,
                    f"Model {model} not available for {provider}. Available models: {models_str}",
                )
            else:
                # Unknown models are allowed, but warn the user
                logger.info(
                    f"Model {model} not in known models for {provider}, but provider allows unknown models"
                )

        # For API key and service checks, we need to bypass the model validation
        # but still check the provider setup
        
        # Check API keys
        provider_config = config_manager.get_provider_config(provider)
        if provider_config and provider_config.api_key_env:
            if not os.getenv(provider_config.api_key_env):
                return False, f"Missing environment variable: {provider_config.api_key_env}"
        
        # Check Ollama availability (if it's Ollama)
        if provider == "ollama":
            import requests
            try:
                # Get Ollama URL from config or environment
                ollama_url = provider_config.api_base or os.getenv("OLLAMA_API_URL", "http://localhost:11434")
                # Remove /v1 suffix if present for API endpoint
                api_url = ollama_url.rstrip("/").removesuffix("/v1")
                
                # Check if Ollama is running
                response = requests.get(f"{api_url}/api/tags", timeout=2)
                if response.status_code == 200:
                    # Check if the specific model is available
                    tags = response.json()
                    available = [m["name"] for m in tags.get("models", [])]
                    if model not in available and not provider_config.allow_unknown_models:
                        return False, f"Model {model} not pulled in Ollama. Run: ollama pull {model}"
                else:
                    return False, f"Ollama API returned status {response.status_code}"
            except requests.exceptions.ConnectionError:
                return False, "Ollama is not running. Start it with: ollama serve"
            except Exception as e:
                return False, f"Error checking Ollama: {str(e)}"
        
        # For other providers, just return success if we got here
        return True, None


def get_available_models_from_config() -> Dict[str, List[str]]:
    """
    Get available models from ConfigManager instead of hardcoded constants.

    Returns:
        Dictionary mapping provider names to lists of available models
    """
    config_manager = get_config_manager()
    config = config_manager.config

    available_models = {}
    for provider_name, provider_config in config.providers.items():
        # Combine known models with configured models
        models = list(provider_config.known_models)

        # Add any models defined in the models dict
        if provider_config.models:
            for model_name in provider_config.models.keys():
                if model_name not in models:
                    models.append(model_name)

        available_models[provider_name] = models

    return available_models


def get_provider_requirements_from_config() -> Dict[str, Optional[str]]:
    """
    Get provider API key requirements from ConfigManager.

    Returns:
        Dictionary mapping provider names to required environment variables
    """
    config_manager = get_config_manager()
    config = config_manager.config

    requirements = {}
    for provider_name, provider_config in config.providers.items():
        requirements[provider_name] = provider_config.api_key_env

    return requirements


def patch_constants():
    """
    Patch the constants module to use ConfigManager values.

    This function replaces the hardcoded AVAILABLE_MODELS and PROVIDER_REQUIREMENTS
    with dynamic values from ConfigManager.
    """
    from . import constants

    # Replace with dynamic values from ConfigManager
    constants.AVAILABLE_MODELS = get_available_models_from_config()
    constants.PROVIDER_REQUIREMENTS = get_provider_requirements_from_config()

    # Update defaults from config
    config = get_config_manager().config
    constants.DEFAULT_PROVIDER = config.default_provider
    constants.DEFAULT_MODEL = config.default_model

    logger.info("Constants patched with ConfigManager values")


def enable_flexible_configuration():
    """
    Enable flexible configuration system.

    This function patches the necessary modules to use ConfigManager
    instead of hardcoded values.
    """
    # Patch constants with dynamic values
    patch_constants()

    # Replace ProviderConfig validation
    from . import provider_config as provider_module

    provider_module.ProviderConfig = FlexibleProviderConfig

    logger.info("Flexible configuration system enabled")
