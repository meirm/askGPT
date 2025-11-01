"""
Configuration Validation for Nano Agent CLI and MCP Server.

Provides comprehensive validation, error handling, and schema validation
for configuration files and settings.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def add_issue(self, level: ValidationLevel, message: str, path: str = ""):
        """Add a validation issue."""
        full_message = f"{path}: {message}" if path else message

        if level == ValidationLevel.ERROR:
            self.errors.append(full_message)
            self.valid = False
        elif level == ValidationLevel.WARNING:
            self.warnings.append(full_message)
        elif level == ValidationLevel.INFO:
            self.info.append(full_message)

    def has_issues(self) -> bool:
        """Check if there are any validation issues."""
        return bool(self.errors or self.warnings)

    def get_summary(self) -> str:
        """Get a summary of validation results."""
        if not self.has_issues():
            return "✅ Configuration is valid"

        summary_parts = []
        if self.errors:
            summary_parts.append(f"❌ {len(self.errors)} errors")
        if self.warnings:
            summary_parts.append(f"⚠️ {len(self.warnings)} warnings")
        if self.info:
            summary_parts.append(f"ℹ️ {len(self.info)} info")

        return ", ".join(summary_parts)


class ConfigValidator:
    """Configuration validator with extensible schema support."""

    def __init__(self):
        self.validators: Dict[str, Callable] = {
            # Basic type validators
            "string": self._validate_string,
            "integer": self._validate_integer,
            "number": self._validate_number,
            "boolean": self._validate_boolean,
            "array": self._validate_array,
            "object": self._validate_object,
            # Specialized validators
            "path": self._validate_path,
            "url": self._validate_url,
            "email": self._validate_email,
            "port": self._validate_port,
            "model_name": self._validate_model_name,
            "provider_name": self._validate_provider_name,
            "temperature": self._validate_temperature,
            "timeout": self._validate_timeout,
            "mcp_server": self._validate_mcp_server,
            "tool_name": self._validate_tool_name,
        }

    def validate_config(
        self, config: Dict[str, Any], schema: Dict[str, Any], path: str = ""
    ) -> ValidationResult:
        """
        Validate configuration against schema.

        Args:
            config: Configuration to validate
            schema: Validation schema
            path: Current path in config (for error reporting)

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()

        # Validate required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in config:
                result.add_issue(
                    ValidationLevel.ERROR, f"Required field '{field}' is missing", path
                )

        # Validate each field in the config
        properties = schema.get("properties", {})
        for field_name, field_value in config.items():
            field_path = f"{path}.{field_name}" if path else field_name

            if field_name in properties:
                field_schema = properties[field_name]
                field_result = self._validate_field(
                    field_value, field_schema, field_path
                )
                self._merge_results(result, field_result)
            elif not schema.get("additionalProperties", True):
                result.add_issue(
                    ValidationLevel.WARNING,
                    f"Unknown field '{field_name}' (not in schema)",
                    path,
                )

        return result

    def _validate_field(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        """Validate a single field against its schema."""
        result = ValidationResult()

        # Check field type
        field_type = schema.get("type")
        if field_type and field_type in self.validators:
            type_result = self.validators[field_type](value, schema, path)
            self._merge_results(result, type_result)

        # Check enum values
        enum_values = schema.get("enum")
        if enum_values and value not in enum_values:
            result.add_issue(
                ValidationLevel.ERROR,
                f"Value '{value}' not in allowed values: {enum_values}",
                path,
            )

        # Check custom validator
        custom_validator = schema.get("validator")
        if custom_validator and custom_validator in self.validators:
            custom_result = self.validators[custom_validator](value, schema, path)
            self._merge_results(result, custom_result)

        # Validate nested objects
        if isinstance(value, dict) and "properties" in schema:
            nested_result = self.validate_config(value, schema, path)
            self._merge_results(result, nested_result)

        # Validate array items
        if isinstance(value, list) and "items" in schema:
            items_schema = schema["items"]
            for i, item in enumerate(value):
                item_path = f"{path}[{i}]"
                item_result = self._validate_field(item, items_schema, item_path)
                self._merge_results(result, item_result)

        return result

    def _merge_results(self, target: ValidationResult, source: ValidationResult):
        """Merge validation results."""
        target.errors.extend(source.errors)
        target.warnings.extend(source.warnings)
        target.info.extend(source.info)
        if not source.valid:
            target.valid = False

    # Type validators
    def _validate_string(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, str):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Expected string, got {type(value).__name__}",
                path,
            )
            return result

        # Check string length
        min_length = schema.get("minLength", 0)
        max_length = schema.get("maxLength")
        if len(value) < min_length:
            result.add_issue(
                ValidationLevel.ERROR, f"String too short (min: {min_length})", path
            )
        if max_length and len(value) > max_length:
            result.add_issue(
                ValidationLevel.ERROR, f"String too long (max: {max_length})", path
            )

        # Check pattern
        pattern = schema.get("pattern")
        if pattern and not re.match(pattern, value):
            result.add_issue(
                ValidationLevel.ERROR, f"String doesn't match pattern: {pattern}", path
            )

        return result

    def _validate_integer(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, int) or isinstance(value, bool):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Expected integer, got {type(value).__name__}",
                path,
            )
            return result

        # Check range
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            result.add_issue(
                ValidationLevel.ERROR, f"Value {value} below minimum {minimum}", path
            )
        if maximum is not None and value > maximum:
            result.add_issue(
                ValidationLevel.ERROR, f"Value {value} above maximum {maximum}", path
            )

        return result

    def _validate_number(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Expected number, got {type(value).__name__}",
                path,
            )
            return result

        # Check range
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            result.add_issue(
                ValidationLevel.ERROR, f"Value {value} below minimum {minimum}", path
            )
        if maximum is not None and value > maximum:
            result.add_issue(
                ValidationLevel.ERROR, f"Value {value} above maximum {maximum}", path
            )

        return result

    def _validate_boolean(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, bool):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Expected boolean, got {type(value).__name__}",
                path,
            )
        return result

    def _validate_array(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, list):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Expected array, got {type(value).__name__}",
                path,
            )
            return result

        # Check array length
        min_items = schema.get("minItems", 0)
        max_items = schema.get("maxItems")
        if len(value) < min_items:
            result.add_issue(
                ValidationLevel.ERROR, f"Array too short (min: {min_items})", path
            )
        if max_items and len(value) > max_items:
            result.add_issue(
                ValidationLevel.ERROR, f"Array too long (max: {max_items})", path
            )

        return result

    def _validate_object(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, dict):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Expected object, got {type(value).__name__}",
                path,
            )
        return result

    # Specialized validators
    def _validate_path(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, str):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Path must be string, got {type(value).__name__}",
                path,
            )
            return result

        # Check if path is valid format
        try:
            path_obj = Path(value)
            # Check if path should exist
            if schema.get("mustExist", False) and not path_obj.exists():
                result.add_issue(
                    ValidationLevel.WARNING, f"Path does not exist: {value}", path
                )
        except Exception as e:
            result.add_issue(ValidationLevel.ERROR, f"Invalid path format: {e}", path)

        return result

    def _validate_url(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, str):
            result.add_issue(
                ValidationLevel.ERROR,
                f"URL must be string, got {type(value).__name__}",
                path,
            )
            return result

        # Basic URL format validation
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, value):
            result.add_issue(
                ValidationLevel.ERROR, f"Invalid URL format: {value}", path
            )

        return result

    def _validate_email(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, str):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Email must be string, got {type(value).__name__}",
                path,
            )
            return result

        # Basic email format validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            result.add_issue(
                ValidationLevel.ERROR, f"Invalid email format: {value}", path
            )

        return result

    def _validate_port(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()

        # Accept both string and integer ports
        if isinstance(value, str):
            try:
                port_num = int(value)
            except ValueError:
                result.add_issue(
                    ValidationLevel.ERROR, f"Port must be numeric, got: {value}", path
                )
                return result
        elif isinstance(value, int):
            port_num = value
        else:
            result.add_issue(
                ValidationLevel.ERROR,
                f"Port must be string or int, got {type(value).__name__}",
                path,
            )
            return result

        # Validate port range
        if not (1 <= port_num <= 65535):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Port {port_num} out of valid range (1-65535)",
                path,
            )

        return result

    def _validate_model_name(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, str):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Model name must be string, got {type(value).__name__}",
                path,
            )
            return result

        # Basic model name validation
        valid_patterns = [
            r"^gpt-[45]",  # GPT models
            r"^claude-",  # Claude models
            r"^gpt-oss:",  # OSS models
            r"^[a-zA-Z0-9-_]+$",  # Generic model names
        ]

        if not any(re.match(pattern, value) for pattern in valid_patterns):
            result.add_issue(
                ValidationLevel.WARNING, f"Unusual model name format: {value}", path
            )

        return result

    def _validate_provider_name(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, str):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Provider name must be string, got {type(value).__name__}",
                path,
            )
            return result

        # Valid provider names
        valid_providers = ["openai", "anthropic", "ollama", "ollama-native", "lmstudio"]
        if value not in valid_providers:
            result.add_issue(
                ValidationLevel.WARNING,
                f"Unknown provider: {value}. Valid: {valid_providers}",
                path,
            )

        return result

    def _validate_temperature(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, (int, float)):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Temperature must be number, got {type(value).__name__}",
                path,
            )
            return result

        # Temperature should be between 0 and 2
        if not (0 <= value <= 2):
            result.add_issue(
                ValidationLevel.WARNING,
                f"Temperature {value} outside recommended range (0-2)",
                path,
            )

        return result

    def _validate_timeout(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()

        # Accept string or integer
        if isinstance(value, str):
            try:
                timeout_val = int(value)
            except ValueError:
                result.add_issue(
                    ValidationLevel.ERROR,
                    f"Timeout must be numeric, got: {value}",
                    path,
                )
                return result
        elif isinstance(value, int):
            timeout_val = value
        else:
            result.add_issue(
                ValidationLevel.ERROR,
                f"Timeout must be string or int, got {type(value).__name__}",
                path,
            )
            return result

        # Timeout should be positive
        if timeout_val <= 0:
            result.add_issue(
                ValidationLevel.ERROR,
                f"Timeout must be positive, got: {timeout_val}",
                path,
            )
        elif timeout_val > 300000:  # 5 minutes
            result.add_issue(
                ValidationLevel.WARNING, f"Very long timeout: {timeout_val}ms", path
            )

        return result

    def _validate_mcp_server(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, dict):
            result.add_issue(
                ValidationLevel.ERROR,
                f"MCP server must be object, got {type(value).__name__}",
                path,
            )
            return result

        # Check required fields
        if "command" not in value:
            result.add_issue(
                ValidationLevel.ERROR,
                "MCP server missing required 'command' field",
                path,
            )

        # Validate optional fields
        if "args" in value and not isinstance(value["args"], list):
            result.add_issue(
                ValidationLevel.ERROR, "MCP server 'args' must be array", path
            )

        if "env" in value and not isinstance(value["env"], dict):
            result.add_issue(
                ValidationLevel.ERROR, "MCP server 'env' must be object", path
            )

        if "enabled" in value and not isinstance(value["enabled"], bool):
            result.add_issue(
                ValidationLevel.ERROR, "MCP server 'enabled' must be boolean", path
            )

        return result

    def _validate_tool_name(
        self, value: Any, schema: Dict[str, Any], path: str
    ) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(value, str):
            result.add_issue(
                ValidationLevel.ERROR,
                f"Tool name must be string, got {type(value).__name__}",
                path,
            )
            return result

        # Tool names should be valid identifiers
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", value):
            result.add_issue(
                ValidationLevel.WARNING,
                f"Tool name should be valid identifier: {value}",
                path,
            )

        return result


# Configuration schemas for different components
NANO_CLI_SCHEMA = {
    "type": "object",
    "properties": {
        "default_model": {
            "type": "string",
            "validator": "model_name",
            "description": "Default AI model to use",
        },
        "default_provider": {
            "type": "string",
            "validator": "provider_name",
            "description": "Default AI provider",
        },
        "temperature": {
            "validator": "temperature",
            "description": "Default temperature for AI responses",
        },
        "max_tokens": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100000,
            "description": "Maximum tokens per response",
        },
        "commands_directory": {
            "type": "string",
            "validator": "path",
            "description": "Directory containing command files",
        },
        "mcp_servers": {
            "type": "object",
            "additionalProperties": {"validator": "mcp_server"},
            "description": "MCP server configurations",
        },
    },
    "additionalProperties": True,
}

ASKGPT_SCHEMA = {
    "type": "object",
    "properties": {
        "mcp_servers": {
            "type": "object",
            "additionalProperties": {"validator": "mcp_server"},
            "description": "MCP server configurations",
        },
        "tool_settings": {
            "type": "object",
            "properties": {
                "auto_apply_edits": {"type": "boolean"},
                "safe_mode": {"type": "boolean"},
                "max_terminal_timeout": {"validator": "timeout"},
            },
            "additionalProperties": True,
        },
        "agent_settings": {
            "type": "object",
            "properties": {
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 100},
                "enable_tracing": {"type": "boolean"},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}

PROJECT_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "mcp_servers": {
            "type": "object",
            "additionalProperties": {"validator": "mcp_server"},
        },
        "disabled_tools": {"type": "array", "items": {"validator": "tool_name"}},
        "restricted_paths": {"type": "array", "items": {"type": "string"}},
        "commands_directory": {"type": "string", "validator": "path"},
        "search_settings": {
            "type": "object",
            "properties": {
                "excluded_directories": {"type": "array", "items": {"type": "string"}},
                "indexed_extensions": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "additionalProperties": True,
}


def validate_askgpt_config(config: Dict[str, Any]) -> ValidationResult:
    """Validate askGPT configuration."""
    validator = ConfigValidator()
    return validator.validate_config(config, NANO_CLI_SCHEMA)


# Legacy function names kept for backward compatibility during migration
def validate_nano_cli_config(config: Dict[str, Any]) -> ValidationResult:
    """Validate nano-cli configuration (deprecated, use validate_askgpt_config)."""
    return validate_askgpt_config(config)


def validate_nano_agent_config(config: Dict[str, Any]) -> ValidationResult:
    """Validate nano-agent configuration (deprecated, MCP server removed)."""
    validator = ConfigValidator()
    return validator.validate_config(config, ASKGPT_SCHEMA)


def validate_project_config(config: Dict[str, Any]) -> ValidationResult:
    """Validate project configuration."""
    validator = ConfigValidator()
    return validator.validate_config(config, PROJECT_CONFIG_SCHEMA)


# Export main classes and functions
__all__ = [
    "ValidationLevel",
    "ValidationResult",
    "ConfigValidator",
    "validate_askgpt_config",
    "validate_nano_cli_config",
    "validate_nano_agent_config",
    "validate_project_config",
    "NANO_CLI_SCHEMA",
    "ASKGPT_SCHEMA",
    "PROJECT_CONFIG_SCHEMA",
]
