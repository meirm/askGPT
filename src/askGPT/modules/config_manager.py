"""
Configuration Manager for askGPT

Provides hierarchical configuration loading with the following precedence:
1. Command-line arguments (highest priority)
2. Environment variables
3. Project-level config (.askgpt/config.yaml in current directory)
4. User-level config (~/.askgpt/config.yaml)
5. System-level config (/etc/askgpt/config.yaml)
6. Default configuration (lowest priority)
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a specific model"""

    name: str
    aliases: List[str] = field(default_factory=list)
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    description: Optional[str] = None
    deprecated: bool = False
    deprecation_message: Optional[str] = None


@dataclass
class ProviderConfig:
    """Configuration for a provider"""

    name: str
    api_base: Optional[str] = None
    api_key_env: Optional[str] = None
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    known_models: List[str] = field(default_factory=list)
    allow_unknown_models: bool = True
    discover_models: bool = False
    discovery_endpoint: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3


@dataclass
class NanoAgentConfig:
    """Main configuration object for Nano Agent"""

    default_provider: str = "ollama"
    default_model: str = "gpt-oss:20b"

    providers: Dict[str, ProviderConfig] = field(default_factory=dict)

    # Model aliases for backward compatibility
    model_aliases: Dict[str, str] = field(default_factory=dict)

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Performance settings
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds

    # Security settings
    validate_ssl: bool = True
    allow_http: bool = False

    # Session settings
    max_turns: int = 20
    max_tool_calls: int = 20  # Maximum tool calls per agent run
    session_timeout: int = 1800  # seconds

    # Command evaluation settings
    enable_command_eval: bool = False  # Shell command evaluation in command files (disabled by default for security)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NanoAgentConfig":
        """Create config from dictionary"""
        # Create a copy to avoid modifying the original
        data = data.copy()

        # Remove unknown fields to prevent errors
        # Get the fields that are actually defined in the dataclass

        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}

        # Filter out any unknown fields
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        # Log warning for removed fields (for debugging)
        removed_fields = set(data.keys()) - set(filtered_data.keys())
        if removed_fields:
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Ignoring unknown config fields: {removed_fields}")

        # Convert provider dicts to ProviderConfig objects
        if "providers" in filtered_data:
            providers = {}
            for name, provider_data in filtered_data["providers"].items():
                if isinstance(provider_data, dict):
                    # Convert model dicts to ModelConfig objects
                    if "models" in provider_data:
                        models = {}
                        for model_name, model_data in provider_data["models"].items():
                            if isinstance(model_data, dict):
                                models[model_name] = ModelConfig(**model_data)
                            else:
                                models[model_name] = model_data
                        provider_data["models"] = models
                    providers[name] = ProviderConfig(name=name, **provider_data)
                else:
                    providers[name] = provider_data
            filtered_data["providers"] = providers

        return cls(**filtered_data)


class ConfigManager:
    """Manages configuration loading and merging from multiple sources"""

    # Configuration hierarchy:
    # For askGPT CLI: env vars > ~/.askgpt/config.yaml > defaults

    def __init__(
        self, config_path: Optional[Path] = None, app_name: str = "askgpt"
    ):
        """
        Initialize ConfigManager

        Args:
            config_path: Optional explicit config file path
            app_name: Application name (default: 'askgpt')
        """
        self.app_name = app_name
        # Set config paths for askGPT
        self.user_config_dir = Path.home() / ".askgpt"
        self.user_config_path = self.user_config_dir / "config.yaml"
        self.USER_CONFIG_DIR = self.user_config_dir  # Alias for compatibility
        self.USER_CONFIG_PATH = self.user_config_path  # Alias for compatibility
        self.explicit_config_path = config_path
        self._config: Optional[NanoAgentConfig] = None
        self._config_sources: List[str] = []

    @property
    def config(self) -> NanoAgentConfig:
        """Get the current configuration, loading if necessary"""
        if self._config is None:
            self.load_config()
        return self._config

    def load_config(self) -> NanoAgentConfig:
        """
        Load configuration with simplified hierarchy:
        - askGPT: Defaults > ~/.askgpt/config.yaml > Environment variables

        Returns:
            Merged configuration object
        """
        # Start with default configuration
        config_dict = self._get_default_config()
        self._config_sources = ["defaults"]

        # Load explicit config file if provided
        if self.explicit_config_path and self.explicit_config_path.exists():
            explicit_config = self._load_config_file(self.explicit_config_path)
            if explicit_config:
                config_dict = self._merge_configs(config_dict, explicit_config)
                self._config_sources.append(f"explicit:{self.explicit_config_path}")
        # Otherwise load user config file for askGPT
        elif (
            self.user_config_path
            and self.user_config_path.exists()
        ):
            user_config = self._load_config_file(self.user_config_path)
            if user_config:
                config_dict = self._merge_configs(config_dict, user_config)
                self._config_sources.append(f"user:{self.user_config_path}")

        # Apply environment variables (always highest priority)
        env_config = self._load_env_config()
        if env_config:
            config_dict = self._merge_configs(config_dict, env_config)
            self._config_sources.append("environment")

        # Create configuration object
        self._config = NanoAgentConfig.from_dict(config_dict)

        logger.debug(
            f"[{self.app_name}] Configuration loaded from sources: {', '.join(self._config_sources)}"
        )

        return self._config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "default_provider": "ollama",
            "default_model": "gpt-oss:20b",
            "providers": {
                "openai": {
                    "api_key_env": "OPENAI_API_KEY",
                    "known_models": ["gpt-5-nano", "gpt-5-mini", "gpt-5", "gpt-4o"],
                    "allow_unknown_models": True,
                    "discover_models": False,
                },
                "anthropic": {
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "api_base": "https://api.anthropic.com/v1",
                    "known_models": [
                        "claude-3-haiku-20240307",
                        "claude-opus-4-20250514",
                        "claude-opus-4-1-20250805",
                        "claude-sonnet-4-20250514",
                    ],
                    "allow_unknown_models": True,
                    "discover_models": False,
                },
                "ollama": {
                    "api_base": "http://localhost:11434/v1",
                    "known_models": ["gpt-oss:20b", "gpt-oss:120b"],
                    "allow_unknown_models": True,
                    "discover_models": True,
                    "discovery_endpoint": "/api/tags",
                },
            },
            "model_aliases": {
                "gpt5": "gpt-5",
                "gpt5mini": "gpt-5-mini",
                "gpt5nano": "gpt-5-nano",
                "claude3haiku": "claude-3-haiku-20240307",
                "opus4": "claude-opus-4-20250514",
                "opus4.1": "claude-opus-4-1-20250805",
                "sonnet4": "claude-sonnet-4-20250514",
            },
            "log_level": "INFO",
            "cache_enabled": True,
            "cache_ttl": 3600,
            "validate_ssl": True,
            "allow_http": False,
            "max_turns": 20,
            "max_tool_calls": 20,
            "session_timeout": 1800,
            "enable_command_eval": False,
        }

    def _load_config_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """
        Load configuration from a file

        Args:
            path: Path to configuration file

        Returns:
            Configuration dictionary or None if failed
        """
        try:
            with open(path, "r") as f:
                if path.suffix in [".yaml", ".yml"]:
                    return yaml.safe_load(f)
                elif path.suffix == ".json":
                    return json.load(f)
                else:
                    # Try YAML first, then JSON
                    content = f.read()
                    try:
                        return yaml.safe_load(content)
                    except yaml.YAMLError:
                        try:
                            return json.loads(content)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Could not parse config file {path} as YAML or JSON"
                            )
                            return None
        except Exception as e:
            logger.warning(f"Failed to load config file {path}: {e}")
            return None

    def _load_env_config(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables

        Environment variables should be prefixed with ASKGPT_
        Examples:
            ASKGPT_DEFAULT_PROVIDER=ollama
            ASKGPT_DEFAULT_MODEL=gpt-oss:120b
            ASKGPT_LOG_LEVEL=DEBUG

        Returns:
            Configuration dictionary from environment
        """
        config = {}
        prefix = "ASKGPT_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix) :].lower()

                # Handle nested keys (e.g., ASKGPT_PROVIDER_OLLAMA_API_BASE)
                if "_" in config_key:
                    parts = config_key.split("_")

                    # Special handling for provider configurations
                    if parts[0] == "provider" and len(parts) >= 3:
                        provider_name = parts[1]
                        provider_key = "_".join(parts[2:])

                        if "providers" not in config:
                            config["providers"] = {}
                        if provider_name not in config["providers"]:
                            config["providers"][provider_name] = {}

                        # Convert boolean strings
                        if value.lower() in ["true", "false"]:
                            value = value.lower() == "true"
                        # Convert numeric strings
                        elif value.isdigit():
                            value = int(value)

                        config["providers"][provider_name][provider_key] = value
                    else:
                        # Regular nested key
                        config[config_key] = value
                else:
                    # Simple key
                    config[config_key] = value

        return config

    def _merge_configs(
        self, base: Dict[str, Any], overlay: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries

        Args:
            base: Base configuration
            overlay: Configuration to overlay on top

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in overlay.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge dictionaries
                result[key] = self._merge_configs(result[key], value)
            else:
                # Override value
                result[key] = value

        return result

    def save_user_config(self, config: Optional[NanoAgentConfig] = None) -> None:
        """
        Save configuration to user config file

        Args:
            config: Configuration to save (uses current if not provided)
        """
        if config is None:
            config = self.config

        # Ensure user config directory exists
        self.USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary and save as YAML
        config_dict = config.to_dict()
        with open(self.USER_CONFIG_PATH, "w") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Configuration saved to {self.USER_CONFIG_PATH}")

    def save_project_config(self, config: Optional[NanoAgentConfig] = None) -> None:
        """
        Save configuration to project config file

        Args:
            config: Configuration to save (uses current if not provided)
        """
        if config is None:
            config = self.config

        # Use project config directory
        config_path = Path.cwd() / ".askgpt" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary and save as YAML
        config_dict = config.to_dict()
        with open(config_path, "w") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Configuration saved to {config_path}")

    def get_config_sources(self) -> List[str]:
        """Get list of configuration sources that were loaded"""
        return self._config_sources.copy()

    def resolve_model_alias(self, model: str) -> str:
        """
        Resolve model alias to actual model name

        Args:
            model: Model name or alias

        Returns:
            Resolved model name
        """
        return self.config.model_aliases.get(model, model)

    def get_provider_config(self, provider: str) -> Optional[ProviderConfig]:
        """
        Get configuration for a specific provider

        Args:
            provider: Provider name

        Returns:
            Provider configuration or None if not found
        """
        return self.config.providers.get(provider)

    def is_model_allowed(self, provider: str, model: str) -> bool:
        """
        Check if a model is allowed for a provider

        Args:
            provider: Provider name
            model: Model name

        Returns:
            True if model is allowed, False otherwise
        """
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            return False

        # Resolve alias
        model = self.resolve_model_alias(model)

        # Check if model is in known models
        if model in provider_config.known_models:
            return True

        # Check if model is defined in models dict
        if model in provider_config.models:
            return True

        # Check if unknown models are allowed
        return provider_config.allow_unknown_models

    @lru_cache(maxsize=128)
    def discover_provider_models(self, provider: str) -> List[str]:
        """
        Discover available models from a provider

        Args:
            provider: Provider name

        Returns:
            List of available model names
        """
        provider_config = self.get_provider_config(provider)
        if not provider_config or not provider_config.discover_models:
            return provider_config.known_models if provider_config else []

        # This is a placeholder - actual discovery logic would go here
        # For now, return known models
        logger.info(f"Model discovery for {provider} not yet implemented")
        return provider_config.known_models


# Global instance for convenience
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global ConfigManager instance"""
    global _config_manager
    if _config_manager is None:
        # Default to askgpt CLI
        app_name = "askgpt"
        _config_manager = ConfigManager(app_name=app_name)
    return _config_manager


def get_config() -> NanoAgentConfig:
    """Get current configuration"""
    return get_config_manager().config
