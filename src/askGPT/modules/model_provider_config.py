"""Configuration management for model providers."""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""

    name: str
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    cache_ttl: int = 300  # 5 minutes default
    timeout: int = 30  # Request timeout in seconds
    max_retries: int = 3
    extra: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConfig":
        """Create from dictionary."""
        # Extract known fields
        known_fields = {
            "name",
            "enabled",
            "api_key",
            "base_url",
            "cache_ttl",
            "timeout",
            "max_retries",
        }

        config_data = {}
        extra_data = {}

        for key, value in data.items():
            if key in known_fields:
                config_data[key] = value
            else:
                extra_data[key] = value

        if extra_data:
            config_data["extra"] = extra_data

        return cls(**config_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "name": self.name,
            "enabled": self.enabled,
            "cache_ttl": self.cache_ttl,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

        if self.api_key:
            data["api_key"] = self.api_key
        if self.base_url:
            data["base_url"] = self.base_url
        if self.extra:
            data.update(self.extra)

        return data


class ModelProviderConfigManager:
    """Manages configuration for all model providers."""

    # Default configurations for known providers
    DEFAULT_CONFIGS = {
        "openai": {
            "name": "openai",
            "enabled": True,
            "base_url": "https://api.openai.com/v1",
            "cache_ttl": 300,
            "timeout": 30,
            "max_retries": 3,
        },
        "anthropic": {
            "name": "anthropic",
            "enabled": True,
            "base_url": "https://api.anthropic.com/v1",
            "cache_ttl": 300,
            "timeout": 30,
            "max_retries": 3,
        },
        "ollama": {
            "name": "ollama",
            "enabled": True,
            "base_url": "http://127.0.0.1:11434/v1",
            "cache_ttl": 60,  # Shorter cache for local models
            "timeout": 60,  # Longer timeout for local models
            "max_retries": 2,
        },
        "lmstudio": {
            "name": "lmstudio",
            "enabled": True,
            "base_url": "http://localhost:1234/v1",
            "cache_ttl": 60,
            "timeout": 60,
            "max_retries": 2,
        },
    }

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file or self._get_default_config_file()
        self.configs: Dict[str, ProviderConfig] = {}

        # Load configurations
        self._load_default_configs()
        self._load_file_configs()
        self._load_env_configs()

    def _get_default_config_file(self) -> Path:
        """Get default configuration file path."""
        # Check for nano-cli config directory
        config_dir = Path.home() / ".askgpt"
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

        return config_dir / "provider_config.json"

    def _load_default_configs(self):
        """Load default configurations."""
        for name, config_data in self.DEFAULT_CONFIGS.items():
            self.configs[name] = ProviderConfig.from_dict(config_data)
            logger.debug(f"Loaded default config for {name}")

    def _load_file_configs(self):
        """Load configurations from file."""
        if not self.config_file.exists():
            logger.debug(f"Config file not found: {self.config_file}")
            return

        try:
            with open(self.config_file, "r") as f:
                file_configs = json.load(f)

            for name, config_data in file_configs.items():
                if isinstance(config_data, dict):
                    # Merge with existing config if present
                    if name in self.configs:
                        existing = self.configs[name].to_dict()
                        existing.update(config_data)
                        self.configs[name] = ProviderConfig.from_dict(existing)
                    else:
                        config_data["name"] = name
                        self.configs[name] = ProviderConfig.from_dict(config_data)

                    logger.debug(f"Loaded file config for {name}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")

    def _load_env_configs(self):
        """Load configurations from environment variables."""
        # OpenAI
        if "OPENAI_API_KEY" in os.environ:
            if "openai" in self.configs:
                self.configs["openai"].api_key = os.environ["OPENAI_API_KEY"]

        if "OPENAI_API_BASE" in os.environ:
            if "openai" in self.configs:
                self.configs["openai"].base_url = os.environ["OPENAI_API_BASE"]

        # Anthropic
        if "ANTHROPIC_API_KEY" in os.environ:
            if "anthropic" in self.configs:
                self.configs["anthropic"].api_key = os.environ["ANTHROPIC_API_KEY"]

        # Ollama
        if "OLLAMA_API_URL" in os.environ:
            if "ollama" in self.configs:
                self.configs["ollama"].base_url = os.environ["OLLAMA_API_URL"]

        # LMStudio
        if "LMSTUDIO_API_URL" in os.environ:
            if "lmstudio" in self.configs:
                self.configs["lmstudio"].base_url = os.environ["LMSTUDIO_API_URL"]

    def get_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """
        Get configuration for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            ProviderConfig or None if not found
        """
        return self.configs.get(provider_name.lower())

    def set_config(self, provider_name: str, config: ProviderConfig):
        """
        Set configuration for a provider.

        Args:
            provider_name: Name of the provider
            config: Provider configuration
        """
        self.configs[provider_name.lower()] = config
        logger.debug(f"Set config for {provider_name}")

    def update_config(self, provider_name: str, **kwargs):
        """
        Update configuration for a provider.

        Args:
            provider_name: Name of the provider
            **kwargs: Configuration fields to update
        """
        config = self.get_config(provider_name)

        if not config:
            # Create new config
            kwargs["name"] = provider_name
            config = ProviderConfig.from_dict(kwargs)
            self.configs[provider_name.lower()] = config
        else:
            # Update existing config
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    config.extra[key] = value

        logger.debug(f"Updated config for {provider_name}")

    def save_to_file(self):
        """Save current configurations to file."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data for saving
            save_data = {}
            for name, config in self.configs.items():
                # Don't save API keys to file for security
                config_dict = config.to_dict()
                if "api_key" in config_dict:
                    del config_dict["api_key"]
                save_data[name] = config_dict

            # Write to file
            with open(self.config_file, "w") as f:
                json.dump(save_data, f, indent=2)

            logger.info(f"Saved provider configs to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config file: {e}")

    def list_providers(self) -> list:
        """List all configured providers."""
        return list(self.configs.keys())

    def list_enabled_providers(self) -> list:
        """List only enabled providers."""
        return [name for name, config in self.configs.items() if config.enabled]
