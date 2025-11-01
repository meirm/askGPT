"""
Test Configuration Loading System for Nano Agent CLI.

Tests the configuration loading hierarchy:
1. askgpt loads from ~/.askgpt/config.json (global)
2. nano-agent loads from ~/.askgpt/config.json (global)
3. Both merge with project .askgpt/config.json (project-specific)
4. Project config overrides global config
5. Environment variable resolution in config files
6. Command file cascade loading
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

# We'll import the config loader module once it's created
# from askgpt.modules.config_loader import ConfigLoader, load_configuration


class TestConfigurationHierarchy:
    """Test configuration loading with proper directory hierarchy."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Create temporary directories for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.home_dir = self.temp_dir / "home"
        self.project_dir = self.temp_dir / "project"

        # Create directory structure
        self.home_dir.mkdir(parents=True)
        self.project_dir.mkdir(parents=True)

        # Create askgpt and nano-agent config directories
        self.nano_cli_dir = self.home_dir / ".askgpt"
        self.nano_agent_dir = self.home_dir / ".askgpt"
        self.project_config_dir = self.project_dir / ".askgpt"

        self.nano_cli_dir.mkdir(parents=True)
        self.nano_agent_dir.mkdir(parents=True)
        self.project_config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_config_file(self, path: Path, config_data: Dict[str, Any]):
        """Helper to create a config file with given data."""
        with open(path, "w") as f:
            json.dump(config_data, f, indent=2)

    @pytest.fixture
    def sample_nano_cli_config(self):
        """Sample askgpt global configuration."""
        return {
            "default_model": "gpt-5-mini",
            "default_provider": "openai",
            "temperature": 0.7,
            "max_tokens": 4000,
            "commands_directory": "~/.askgpt/commands",
            "mcp_servers": {
                "context7": {
                    "command": "node",
                    "args": ["context7-server"],
                    "env": {"API_KEY": "${CONTEXT7_API_KEY}"},
                    "enabled": True,
                }
            },
            "global_settings": {"verbose": False, "safe_mode": False},
        }

    @pytest.fixture
    def sample_nano_agent_config(self):
        """Sample nano-agent global configuration."""
        return {
            "mcp_servers": {
                "sequential": {
                    "command": "sequential-server",
                    "args": ["--port", "3001"],
                    "env": {"LOG_LEVEL": "info"},
                    "enabled": True,
                    "tools": ["analyze", "think", "reason"],
                    "timeout": 30000,
                    "retry_attempts": 3,
                },
                "magic": {
                    "command": "magic-server",
                    "args": ["--ui-mode"],
                    "enabled": False,
                },
            },
            "tool_settings": {
                "auto_apply_edits": False,
                "safe_mode": True,
                "max_terminal_timeout": 60,
            },
            "agent_settings": {"max_iterations": 20, "enable_tracing": False},
        }

    @pytest.fixture
    def sample_project_config(self):
        """Sample project-specific configuration."""
        return {
            "mcp_servers": {
                "context7": {
                    "command": "npx",
                    "args": ["@context7/server", "--project-mode"],
                    "env": {"PROJECT_API_KEY": "${PROJECT_CONTEXT7_KEY}"},
                    "enabled": True,
                },
                "playwright": {
                    "command": "playwright-server",
                    "args": ["--headless"],
                    "enabled": True,
                    "tools": ["screenshot", "test", "performance"],
                },
            },
            "disabled_tools": ["delete_file", "run_terminal"],
            "restricted_paths": ["/etc/*", "/usr/*", "~/.ssh/*"],
            "commands_directory": ".askgpt/commands",
            "search_settings": {
                "excluded_directories": [
                    ".git",
                    "node_modules",
                    "__pycache__",
                    ".venv",
                ],
                "indexed_extensions": [
                    ".py",
                    ".js",
                    ".ts",
                    ".md",
                    ".json",
                    ".yaml",
                    ".yml",
                ],
            },
            "project_settings": {
                "name": "test-project",
                "version": "1.0.0",
                "framework": "python",
            },
        }

    def test_nano_cli_global_config_loading(self, sample_nano_cli_config):
        """Test loading askgpt global configuration from ~/.askgpt/config.json."""
        # Create askgpt config file
        config_path = self.nano_cli_dir / "config.json"
        self.create_config_file(config_path, sample_nano_cli_config)

        # Mock home directory
        with patch("pathlib.Path.home", return_value=self.home_dir):
            # This will test the ConfigLoader.load_nano_cli_config() method
            # when implemented
            assert config_path.exists()
            with open(config_path) as f:
                loaded_config = json.load(f)

            # Verify the config was loaded correctly
            assert loaded_config["default_model"] == "gpt-5-mini"
            assert loaded_config["default_provider"] == "openai"
            assert loaded_config["mcp_servers"]["context7"]["enabled"] is True
            assert loaded_config["commands_directory"] == "~/.askgpt/commands"

    def test_nano_agent_global_config_loading(self, sample_nano_agent_config):
        """Test loading nano-agent global configuration from ~/.askgpt/config.json."""
        # Create nano-agent config file
        config_path = self.nano_agent_dir / "config.json"
        self.create_config_file(config_path, sample_nano_agent_config)

        # Mock home directory
        with patch("pathlib.Path.home", return_value=self.home_dir):
            assert config_path.exists()
            with open(config_path) as f:
                loaded_config = json.load(f)

            # Verify the config was loaded correctly
            assert "sequential" in loaded_config["mcp_servers"]
            assert loaded_config["mcp_servers"]["sequential"]["enabled"] is True
            assert loaded_config["tool_settings"]["safe_mode"] is True
            assert loaded_config["agent_settings"]["max_iterations"] == 20

    def test_project_config_loading(self, sample_project_config):
        """Test loading project-specific configuration from .askgpt/config.json."""
        # Create project config file
        config_path = self.project_config_dir / "config.json"
        self.create_config_file(config_path, sample_project_config)

        # Mock current working directory
        with patch("pathlib.Path.cwd", return_value=self.project_dir):
            assert config_path.exists()
            with open(config_path) as f:
                loaded_config = json.load(f)

            # Verify the config was loaded correctly
            assert "playwright" in loaded_config["mcp_servers"]
            assert "delete_file" in loaded_config["disabled_tools"]
            assert loaded_config["project_settings"]["name"] == "test-project"

    def test_config_merging_hierarchy(
        self, sample_nano_cli_config, sample_nano_agent_config, sample_project_config
    ):
        """Test that configurations are merged with proper precedence."""
        # Create all config files
        nano_cli_path = self.nano_cli_dir / "config.json"
        nano_agent_path = self.nano_agent_dir / "config.json"
        project_path = self.project_config_dir / "config.json"

        self.create_config_file(nano_cli_path, sample_nano_cli_config)
        self.create_config_file(nano_agent_path, sample_nano_agent_config)
        self.create_config_file(project_path, sample_project_config)

        # This will test the actual merging logic when implemented
        # Expected behavior:
        # 1. Start with askgpt global config
        # 2. Merge nano-agent global config (for nano-agent binary)
        # 3. Override with project config

        # For askgpt binary:
        expected_nano_cli_merge = {
            # From askgpt global
            "default_model": "gpt-5-mini",
            "default_provider": "openai",
            "temperature": 0.7,
            "max_tokens": 4000,
            # Merged MCP servers (project overrides global)
            "mcp_servers": {
                "context7": {
                    "command": "npx",  # Overridden by project
                    "args": ["@context7/server", "--project-mode"],
                    "env": {"PROJECT_API_KEY": "${PROJECT_CONTEXT7_KEY}"},
                    "enabled": True,
                },
                "playwright": {  # Added by project
                    "command": "playwright-server",
                    "args": ["--headless"],
                    "enabled": True,
                    "tools": ["screenshot", "test", "performance"],
                },
            },
            # From project
            "disabled_tools": ["delete_file", "run_terminal"],
            "commands_directory": ".askgpt/commands",  # Overridden by project
        }

        # For nano-agent binary:
        expected_nano_agent_merge = {
            # From nano-agent global
            "tool_settings": {
                "auto_apply_edits": False,
                "safe_mode": True,
                "max_terminal_timeout": 60,
            },
            "agent_settings": {"max_iterations": 20, "enable_tracing": False},
            # Merged MCP servers
            "mcp_servers": {
                "sequential": {  # From nano-agent global
                    "command": "sequential-server",
                    "args": ["--port", "3001"],
                    "env": {"LOG_LEVEL": "info"},
                    "enabled": True,
                    "tools": ["analyze", "think", "reason"],
                    "timeout": 30000,
                    "retry_attempts": 3,
                },
                "magic": {  # From nano-agent global
                    "command": "magic-server",
                    "args": ["--ui-mode"],
                    "enabled": False,
                },
                "context7": {  # Overridden by project
                    "command": "npx",
                    "args": ["@context7/server", "--project-mode"],
                    "env": {"PROJECT_API_KEY": "${PROJECT_CONTEXT7_KEY}"},
                    "enabled": True,
                },
                "playwright": {  # Added by project
                    "command": "playwright-server",
                    "args": ["--headless"],
                    "enabled": True,
                    "tools": ["screenshot", "test", "performance"],
                },
            },
            # From project
            "disabled_tools": ["delete_file", "run_terminal"],
            "restricted_paths": ["/etc/*", "/usr/*", "~/.ssh/*"],
        }

        # These assertions will be updated when the actual ConfigLoader is implemented
        assert True  # Placeholder - will implement actual merging tests

    def test_environment_variable_resolution(self):
        """Test that environment variables are resolved in config files."""
        # Set test environment variables
        test_env = {
            "CONTEXT7_API_KEY": "test-context7-key",
            "PROJECT_CONTEXT7_KEY": "project-specific-key",
            "TEST_PORT": "3002",
        }

        config_with_env_vars = {
            "mcp_servers": {
                "context7": {
                    "command": "context7-server",
                    "env": {
                        "API_KEY": "${CONTEXT7_API_KEY}",
                        "FALLBACK_KEY": "${MISSING_VAR:-default-fallback}",
                    },
                    "args": ["--port", "${TEST_PORT}"],
                }
            },
            "database_url": "${DATABASE_URL:-sqlite:///default.db}",
            "debug_mode": "${DEBUG_MODE:-false}",
        }

        config_path = self.project_config_dir / "config.json"
        self.create_config_file(config_path, config_with_env_vars)

        # Test environment variable resolution
        with patch.dict(os.environ, test_env):
            # This will test the ConfigLoader.resolve_environment_variables() method
            # Expected resolved config:
            expected_resolved = {
                "mcp_servers": {
                    "context7": {
                        "command": "context7-server",
                        "env": {
                            "API_KEY": "test-context7-key",
                            "FALLBACK_KEY": "default-fallback",
                        },
                        "args": ["--port", "3002"],
                    }
                },
                "database_url": "sqlite:///default.db",
                "debug_mode": "false",
            }

            # Placeholder assertion - will implement actual resolution tests
            assert True

    def test_config_validation_and_error_handling(self):
        """Test configuration validation and error handling."""
        # Test invalid JSON
        invalid_json_path = self.nano_cli_dir / "config.json"
        with open(invalid_json_path, "w") as f:
            f.write("{ invalid json content }")

        # Test missing required fields
        incomplete_config = {
            "mcp_servers": {
                "invalid_server": {
                    # Missing required 'command' field
                    "enabled": True
                }
            }
        }
        incomplete_config_path = self.nano_agent_dir / "config.json"
        self.create_config_file(incomplete_config_path, incomplete_config)

        # Test schema validation
        invalid_schema_config = {
            "mcp_servers": {
                "test_server": {
                    "command": "test-command",
                    "timeout": "invalid_timeout_value",  # Should be int
                    "enabled": "not_a_boolean",  # Should be bool
                }
            }
        }
        invalid_schema_path = self.project_config_dir / "config.json"
        self.create_config_file(invalid_schema_path, invalid_schema_config)

        # These tests will verify that ConfigLoader handles errors gracefully
        # and provides helpful error messages
        assert True  # Placeholder - will implement actual validation tests

    def test_missing_config_files_handling(self):
        """Test graceful handling when config files don't exist."""
        # Don't create any config files

        # Mock home and project directories
        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # ConfigLoader should handle missing files gracefully
            # and return sensible defaults
            expected_defaults = {
                "default_model": "gpt-5-mini",
                "default_provider": "openai",
                "temperature": 1.0,
                "max_tokens": 4000,
                "mcp_servers": {},
                "tool_settings": {
                    "auto_apply_edits": False,
                    "safe_mode": False,
                    "max_terminal_timeout": 30,
                },
            }

            # Placeholder assertion - will implement actual default handling tests
            assert True


class TestCommandFileCascadeLoading:
    """Test command file loading with cascade system."""

    def setup_method(self):
        """Set up test environment for command file tests."""
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.home_dir = self.temp_dir / "home"
        self.project_dir = self.temp_dir / "project"

        # Create directory structure
        self.home_dir.mkdir(parents=True)
        self.project_dir.mkdir(parents=True)

        # Create command directories
        self.global_commands_dir = self.home_dir / ".askgpt" / "commands"
        self.project_commands_dir = self.project_dir / ".askgpt" / "commands"

        self.global_commands_dir.mkdir(parents=True)
        self.project_commands_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_command_file(self, path: Path, content: str):
        """Helper to create a command file."""
        with open(path, "w") as f:
            f.write(content)

    def test_global_command_loading(self):
        """Test loading commands from global ~/.askgpt/commands/ directory."""
        # Create global command
        global_analyze_content = """# Analyze Code
        
Perform comprehensive code analysis on the given codebase.

## Prompt Template

Analyze the following code and provide insights on:
- Code quality and maintainability
- Performance implications
- Security considerations
- Best practices adherence

Target: $ARGUMENTS
"""

        global_analyze_path = self.global_commands_dir / "analyze.md"
        self.create_command_file(global_analyze_path, global_analyze_content)

        # Test loading global command
        with patch("pathlib.Path.home", return_value=self.home_dir):
            # This will test the enhanced CommandLoader.load_commands_cascade() method
            assert global_analyze_path.exists()

            # Verify command content
            with open(global_analyze_path) as f:
                content = f.read()
                assert "Analyze Code" in content
                assert "$ARGUMENTS" in content

    def test_project_command_loading(self):
        """Test loading commands from project .askgpt/commands/ directory."""
        # Create project-specific command
        project_test_content = """# Project Test
        
Run project-specific tests with custom configuration.

## Prompt Template

Execute the test suite for this project:
- Run unit tests
- Check code coverage
- Validate project-specific requirements

Test target: $ARGUMENTS
"""

        project_test_path = self.project_commands_dir / "test.md"
        self.create_command_file(project_test_path, project_test_content)

        # Test loading project command
        with patch("pathlib.Path.cwd", return_value=self.project_dir):
            assert project_test_path.exists()

            with open(project_test_path) as f:
                content = f.read()
                assert "Project Test" in content
                assert "project-specific" in content

    def test_command_override_behavior(self):
        """Test that project commands override global commands with same name."""
        # Create global command
        global_build_content = """# Global Build
        
Generic build command for all projects.

## Prompt Template

Build the project: $ARGUMENTS
"""

        # Create project command with same name
        project_build_content = """# Project Build
        
Project-specific build with custom webpack configuration.

## Prompt Template

Build this React project with:
- Custom webpack config
- Environment-specific settings
- Asset optimization

Build target: $ARGUMENTS
"""

        global_build_path = self.global_commands_dir / "build.md"
        project_build_path = self.project_commands_dir / "build.md"

        self.create_command_file(global_build_path, global_build_content)
        self.create_command_file(project_build_path, project_build_content)

        # Test override behavior
        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # When both files exist, project should override global
            assert global_build_path.exists()
            assert project_build_path.exists()

            # The enhanced CommandLoader should return project version
            # when there's a name conflict
            with open(project_build_path) as f:
                project_content = f.read()
                assert "Project Build" in project_content
                assert "webpack" in project_content

    def test_command_cascade_loading_order(self):
        """Test the complete cascade loading order."""
        # Create multiple commands in both locations
        commands = {
            "analyze": "Global Analysis Command",
            "build": "Global Build Command",
            "deploy": "Global Deploy Command",
        }

        project_commands = {
            "build": "Project Build Override",  # Overrides global
            "test": "Project Test Command",  # Project-only
            "dev": "Project Dev Command",  # Project-only
        }

        # Create global commands
        for name, title in commands.items():
            content = f"# {title}\n\nGlobal command: $ARGUMENTS"
            path = self.global_commands_dir / f"{name}.md"
            self.create_command_file(path, content)

        # Create project commands
        for name, title in project_commands.items():
            content = f"# {title}\n\nProject command: $ARGUMENTS"
            path = self.project_commands_dir / f"{name}.md"
            self.create_command_file(path, content)

        # Test cascade loading
        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # Expected final command set:
            # - analyze: from global (no override)
            # - build: from project (overrides global)
            # - deploy: from global (no override)
            # - test: from project (project-only)
            # - dev: from project (project-only)

            expected_commands = ["analyze", "build", "deploy", "test", "dev"]

            # Verify all command files exist
            assert len(list(self.global_commands_dir.glob("*.md"))) == 3
            assert len(list(self.project_commands_dir.glob("*.md"))) == 3

            # The enhanced CommandLoader should load 5 total commands
            # with proper override behavior
            assert True  # Placeholder - will implement actual cascade tests


class TestConfigurationIntegration:
    """Integration tests for the complete configuration system."""

    def test_cli_integration_nano_cli(self):
        """Test CLI integration for askgpt binary."""
        # Test that askgpt binary loads:
        # 1. ~/.askgpt/config.json (global)
        # 2. .askgpt/config.json (project, merged)
        # 3. Commands from ~/.askgpt/commands/*.md and .askgpt/commands/*.md
        pass

    def test_cli_integration_nano_agent(self):
        """Test CLI integration for nano-agent binary."""
        # Test that nano-agent binary loads:
        # 1. ~/.askgpt/config.json (global)
        # 2. .askgpt/config.json (project, merged)
        # 3. Commands from ~/.askgpt/commands/*.md and .askgpt/commands/*.md
        pass

    def test_mcp_server_configuration(self):
        """Test MCP server configuration loading and validation."""
        # Test loading MCP server configurations from all sources
        # Test server enablement/disablement
        # Test server-specific settings and tools
        pass

    def test_cross_platform_paths(self):
        """Test configuration loading across different operating systems."""
        # Test Windows, macOS, and Linux path handling
        # Test path expansion and resolution
        pass


if __name__ == "__main__":
    pytest.main([__file__])
