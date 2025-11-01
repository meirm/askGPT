"""
Configuration Loader for askGPT CLI.

Handles configuration loading hierarchy:
1. askgpt loads from ~/.askgpt/config.yaml (global)
2. Merges with project .askgpt/config.yaml (project-specific)
3. Project config overrides global config
4. Environment variable resolution in config files
"""

import json
import logging
import os
import re
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config_validation import (ValidationResult, validate_askgpt_config,
                                validate_project_config)

logger = logging.getLogger(__name__)


# BinaryType enum removed - askGPT only supports CLI, no MCP server


@dataclass
class ConfigPaths:
    """Configuration file paths for a specific binary type."""

    global_config_dir: Path
    global_config_file: Path
    project_config_dir: Path
    project_config_file: Path
    global_commands_dir: Path
    project_commands_dir: Path


@dataclass
class LoadedConfiguration:
    """Container for loaded and merged configuration."""

    config: Dict[str, Any] = field(default_factory=dict)
    global_config_path: Optional[Path] = None
    project_config_path: Optional[Path] = None
    global_config_loaded: bool = False
    project_config_loaded: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_result: Optional[ValidationResult] = None


class ConfigurationError(Exception):
    """Exception raised for configuration loading errors."""

    pass


class EnvironmentVariableResolver:
    """Handles environment variable resolution in configuration files."""

    # Regex patterns for different environment variable syntaxes
    VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")
    FALLBACK_PATTERN = re.compile(r"^([^:]+):-(.*)$")
    REQUIRED_PATTERN = re.compile(r"^([^:]+):\?(.*)$")

    @classmethod
    def resolve_variables(cls, config_data: Any, max_depth: int = 10) -> Any:
        """
        Resolve environment variables in configuration data.

        Supports:
        - ${VAR_NAME}: Basic substitution
        - ${VAR_NAME:-default}: Fallback to default if unset
        - ${VAR_NAME:?error_message}: Required variable (error if unset)

        Args:
            config_data: Configuration data (dict, list, or string)
            max_depth: Maximum resolution depth to prevent infinite loops

        Returns:
            Configuration data with variables resolved

        Raises:
            ConfigurationError: If required variables are missing or circular references detected
        """
        if max_depth <= 0:
            raise ConfigurationError(
                "Maximum environment variable resolution depth exceeded (possible circular reference)"
            )

        if isinstance(config_data, dict):
            return {
                key: cls.resolve_variables(value, max_depth - 1)
                for key, value in config_data.items()
            }
        elif isinstance(config_data, list):
            return [cls.resolve_variables(item, max_depth - 1) for item in config_data]
        elif isinstance(config_data, str):
            return cls._resolve_string_variables(config_data)
        else:
            return config_data

    @classmethod
    def _resolve_string_variables(cls, text: str) -> str:
        """Resolve environment variables in a string."""

        def replace_var(match):
            var_expr = match.group(1)

            # Check for required syntax: VAR:?error_message
            required_match = cls.REQUIRED_PATTERN.match(var_expr)
            if required_match:
                var_name, error_msg = required_match.groups()
                value = os.environ.get(var_name)
                if value is None:
                    raise ConfigurationError(
                        f"Required environment variable '{var_name}' is not set: {error_msg}"
                    )
                return value

            # Check for fallback syntax: VAR:-default
            fallback_match = cls.FALLBACK_PATTERN.match(var_expr)
            if fallback_match:
                var_name, default = fallback_match.groups()
                return os.environ.get(var_name, default)

            # Basic substitution: VAR
            return os.environ.get(
                var_expr, f"${{{var_expr}}}"
            )  # Leave unresolved if not found

        # Handle escaped dollar signs ($$) first
        text = text.replace("$$", "\x00ESCAPED_DOLLAR\x00")

        # Resolve variables
        resolved = cls.VAR_PATTERN.sub(replace_var, text)

        # Restore escaped dollar signs
        resolved = resolved.replace("\x00ESCAPED_DOLLAR\x00", "$")

        return resolved


class ConfigLoader:
    """Main configuration loader class for askGPT."""

    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize configuration loader.

        Args:
            working_dir: Working directory for project config (defaults to current dir)
        """
        self.working_dir = working_dir or Path.cwd()
        self.paths = self._setup_paths()

    def _setup_paths(self) -> ConfigPaths:
        """Setup configuration paths for askGPT."""
        home_dir = Path.home()
        global_config_dir = home_dir / ".askgpt"
        project_config_dir = self.working_dir / ".askgpt"

        return ConfigPaths(
            global_config_dir=global_config_dir,
            global_config_file=global_config_dir / "config.yaml",
            project_config_dir=project_config_dir,
            project_config_file=project_config_dir / "config.yaml",
            global_commands_dir=global_config_dir / "commands",
            project_commands_dir=project_config_dir / "commands",
        )

    def load_configuration(self) -> LoadedConfiguration:
        """
        Load and merge configuration with proper hierarchy.

        Returns:
            LoadedConfiguration object with merged config and metadata
        """
        result = LoadedConfiguration()

        # Load global configuration
        global_config = self._load_global_config(result)

        # Load project configuration
        project_config = self._load_project_config(result)

        # Merge configurations (project overrides global)
        result.config = self._merge_configs(global_config, project_config)

        # Resolve environment variables
        try:
            result.config = EnvironmentVariableResolver.resolve_variables(result.config)
        except ConfigurationError as e:
            result.errors.append(f"Environment variable resolution failed: {e}")

        # Validate final configuration
        result.validation_result = self._validate_config(result)

        return result

    def _load_global_config(self, result: LoadedConfiguration) -> Dict[str, Any]:
        """Load global configuration file."""
        if not self.paths.global_config_file.exists():
            logger.debug(
                f"Global config file not found: {self.paths.global_config_file}"
            )
            return self._get_default_config()

        try:
            with open(self.paths.global_config_file, "r", encoding="utf-8") as f:
                # Support both YAML and JSON formats
                if self.paths.global_config_file.suffix in (".yaml", ".yml"):
                    config = yaml.safe_load(f) or {}
                else:
                    config = json.load(f)

            result.global_config_path = self.paths.global_config_file
            result.global_config_loaded = True
            logger.debug(f"Loaded global config from: {self.paths.global_config_file}")

            return config
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            error_msg = (
                f"Invalid config file {self.paths.global_config_file}: {e}"
            )
            result.errors.append(error_msg)
            logger.error(error_msg)
            return self._get_default_config()
        except Exception as e:
            error_msg = (
                f"Failed to load global config {self.paths.global_config_file}: {e}"
            )
            result.errors.append(error_msg)
            logger.error(error_msg)
            return self._get_default_config()

    def _load_project_config(self, result: LoadedConfiguration) -> Dict[str, Any]:
        """Load project-specific configuration file."""
        if not self.paths.project_config_file.exists():
            logger.debug(
                f"Project config file not found: {self.paths.project_config_file}"
            )
            return {}

        try:
            with open(self.paths.project_config_file, "r", encoding="utf-8") as f:
                # Support both YAML and JSON formats
                if self.paths.project_config_file.suffix in (".yaml", ".yml"):
                    config = yaml.safe_load(f) or {}
                else:
                    config = json.load(f)

            result.project_config_path = self.paths.project_config_file
            result.project_config_loaded = True
            logger.debug(
                f"Loaded project config from: {self.paths.project_config_file}"
            )

            return config
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            error_msg = (
                f"Invalid config file {self.paths.project_config_file}: {e}"
            )
            result.errors.append(error_msg)
            logger.error(error_msg)
            return {}
        except Exception as e:
            error_msg = (
                f"Failed to load project config {self.paths.project_config_file}: {e}"
            )
            result.errors.append(error_msg)
            logger.error(error_msg)
            return {}

    def _merge_configs(
        self, global_config: Dict[str, Any], project_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge global and project configurations.

        Project config takes precedence over global config.
        Nested dictionaries are merged recursively.
        """
        return self._deep_merge(global_config, project_config)

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.

        Values from override take precedence over base.
        Nested dictionaries are merged recursively.
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for askGPT (offline-first)."""
        return {
            "default_model": "gpt-oss:20b",
            "default_provider": "ollama",
            "temperature": 0.2,
            "max_tokens": 4000,
            "commands_directory": "~/.askgpt/commands",
            "tool_settings": {
                "auto_apply_edits": False,
                "safe_mode": False,
                "max_terminal_timeout": 30,
            },
        }

    def _validate_config(self, result: LoadedConfiguration) -> ValidationResult:
        """Validate the merged configuration using schema validation."""
        config = result.config
        validation_result = validate_askgpt_config(config)

        # Also validate project-specific settings if present
        project_fields = [
            "disabled_tools",
            "restricted_paths",
            "search_settings",
            "project_settings",
        ]
        if any(field in config for field in project_fields):
            project_validation = validate_project_config(config)
            # Merge project validation results
            validation_result.errors.extend(project_validation.errors)
            validation_result.warnings.extend(project_validation.warnings)
            validation_result.info.extend(project_validation.info)
            if not project_validation.valid:
                validation_result.valid = False

        # Add validation issues to the result
        result.errors.extend(validation_result.errors)
        result.warnings.extend(validation_result.warnings)

        logger.debug(f"Configuration validation: {validation_result.get_summary()}")

        return validation_result


def load_configuration(working_dir: Optional[Path] = None) -> LoadedConfiguration:
    """
    Convenience function to load configuration for askGPT.

    Args:
        working_dir: Working directory for project config

    Returns:
        LoadedConfiguration object
    """
    loader = ConfigLoader(working_dir)
    return loader.load_configuration()


# Export main classes and functions
__all__ = [
    "ConfigPaths",
    "LoadedConfiguration",
    "ConfigurationError",
    "EnvironmentVariableResolver",
    "ConfigLoader",
    "load_configuration",
]
