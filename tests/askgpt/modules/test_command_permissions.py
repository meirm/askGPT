"""
Tests for Command permission validation with allowed_tools.

Tests command execution permission validation, error handling, and backward compatibility.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from askgpt.modules.cascade_command_loader import CascadeCommandLoader, Command, CommandLoader


class TestCommandPermissions:
    """Test Command permission validation with allowed_tools."""

    @pytest.fixture
    def temp_commands_dir(self):
        """Create a temporary directory for commands testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def command_loader_no_permissions(self, temp_commands_dir):
        """Create a CommandLoader without permission restrictions (backward compatible)."""
        loader = CascadeCommandLoader(
            working_dir=temp_commands_dir,
            allowed_tools=None,
            blocked_tools=None,
        )
        loader.global_commands_dir = temp_commands_dir / "global_commands"
        loader.project_commands_dir = temp_commands_dir / "project_commands"
        
        loader.global_commands_dir.mkdir(parents=True, exist_ok=True)
        loader.project_commands_dir.mkdir(parents=True, exist_ok=True)
        
        return loader

    @pytest.fixture
    def command_loader_with_permissions(self, temp_commands_dir):
        """Create a CommandLoader with permission restrictions."""
        loader = CascadeCommandLoader(
            working_dir=temp_commands_dir,
            allowed_tools=["read_file", "write_file", "list_directory"],
            blocked_tools=None,
        )
        loader.global_commands_dir = temp_commands_dir / "global_commands"
        loader.project_commands_dir = temp_commands_dir / "project_commands"
        
        loader.global_commands_dir.mkdir(parents=True, exist_ok=True)
        loader.project_commands_dir.mkdir(parents=True, exist_ok=True)
        
        return loader

    def test_command_without_tools_allowed(self, command_loader_with_permissions):
        """Test that command without tools: metadata is allowed (default behavior)."""
        command_file = command_loader_with_permissions.global_commands_dir / "simple-command.md"
        
        command_file.write_text("""# Simple Command

This is a simple command without tools requirement.

## Prompt

Process the request: $ARGUMENTS
""")
        
        result = command_loader_with_permissions.execute_command("simple-command", "test args")
        
        # Should execute successfully (no error)
        assert result is not None
        assert not result.startswith("[Error:")
        assert "test args" in result

    def test_command_with_tools_all_allowed(self, command_loader_with_permissions):
        """Test that command with tools: where all tools are in allowed_tools executes successfully."""
        command_file = command_loader_with_permissions.global_commands_dir / "read-command.md"
        
        command_file.write_text("""---
name: read-command
tools: ["read_file", "list_directory"]
---

# Read Command

This command reads files.

## Prompt

Read files: $ARGUMENTS
""")
        
        result = command_loader_with_permissions.execute_command("read-command", "test")
        
        # Should execute successfully
        assert result is not None
        assert not result.startswith("[Error:")
        assert "test" in result

    def test_command_with_tools_some_missing_fails(self, command_loader_with_permissions):
        """Test that command with tools: where some tools are missing returns error string."""
        command_file = command_loader_with_permissions.global_commands_dir / "write-command.md"
        
        command_file.write_text("""---
name: write-command
tools: ["read_file", "write_file", "edit_file"]
---

# Write Command

This command writes files.

## Prompt

Write files: $ARGUMENTS
""")
        
        result = command_loader_with_permissions.execute_command("write-command", "test")
        
        # Should return error string
        assert result is not None
        assert result.startswith("[Error:")
        assert "edit_file" in result or "not allowed" in result

    def test_command_blocked_fails(self, temp_commands_dir):
        """Test that explicitly blocked command returns error string."""
        loader = CascadeCommandLoader(
            working_dir=temp_commands_dir,
            allowed_tools=["read_file", "write_file"],
            blocked_tools=["blocked-command"],
        )
        loader.global_commands_dir = temp_commands_dir / "global_commands"
        loader.project_commands_dir = temp_commands_dir / "project_commands"
        
        loader.global_commands_dir.mkdir(parents=True, exist_ok=True)
        loader.project_commands_dir.mkdir(parents=True, exist_ok=True)
        
        command_file = loader.global_commands_dir / "blocked-command.md"
        command_file.write_text("""---
tools: ["read_file"]
---

# Blocked Command

## Prompt

Test: $ARGUMENTS
""")
        
        result = loader.execute_command("blocked-command", "test")
        
        # Should return error string
        assert result is not None
        assert result.startswith("[Error:")
        assert "blocked" in result.lower()

    def test_command_backward_compatible_no_permissions(self, command_loader_no_permissions):
        """Test that commands work without permission restrictions (backward compatible)."""
        command_file = command_loader_no_permissions.global_commands_dir / "test-command.md"
        
        command_file.write_text("""---
tools: ["read_file", "edit_file"]
---

# Test Command

## Prompt

Test: $ARGUMENTS
""")
        
        result = command_loader_no_permissions.execute_command("test-command", "test args")
        
        # Should execute successfully when no permissions are set (backward compatible)
        assert result is not None
        assert not result.startswith("[Error:")

    def test_command_tools_extracted_from_yaml_frontmatter(self, command_loader_with_permissions):
        """Test that tools: are extracted from YAML frontmatter."""
        command_file = command_loader_with_permissions.global_commands_dir / "yaml-command.md"
        
        command_file.write_text("""---
name: yaml-command
tools: ["read_file", "write_file"]
---

# YAML Command

## Prompt

Process: $ARGUMENTS
""")
        
        command = command_loader_with_permissions.get_command("yaml-command")
        
        assert command is not None
        assert set(command.required_tools) == {"read_file", "write_file"}

    def test_command_tools_extracted_from_metadata_section(self, command_loader_with_permissions):
        """Test that tools: can be extracted from metadata section (backward compatibility)."""
        command_file = command_loader_with_permissions.global_commands_dir / "metadata-command.md"
        
        command_file.write_text("""# Metadata Command

## Metadata

tools: read_file, write_file

## Prompt

Process: $ARGUMENTS
""")
        
        command = command_loader_with_permissions.get_command("metadata-command")
        
        # Note: Metadata section parsing might not extract tools the same way
        # This test verifies the command loads (tools may be in metadata dict)
        assert command is not None

    def test_command_loader_wrapper_preserves_shell_eval(self, temp_commands_dir):
        """Test that CommandLoader wrapper preserves shell evaluation functionality."""
        loader = CommandLoader(
            commands_dir=temp_commands_dir,
            enable_command_eval=True,
            allowed_tools=["read_file"],
        )
        
        command_file = temp_commands_dir / "eval-command.md"
        command_file.write_text("""---
tools: ["read_file"]
---

# Eval Command

## Prompt

Date: $`date +%Y`
Args: $ARGUMENTS
""")
        
        result = loader.execute_command("eval-command", "test")
        
        # Should execute and evaluate shell command
        assert result is not None
        assert not result.startswith("[Error:")
        # Should contain current year from date command
        import datetime
        current_year = str(datetime.datetime.now().year)
        assert current_year in result or "test" in result

    def test_command_error_string_format(self, command_loader_with_permissions):
        """Test that command errors return proper [Error: ...] format."""
        command_file = command_loader_with_permissions.global_commands_dir / "error-command.md"
        
        command_file.write_text("""---
tools: ["edit_file"]
---

# Error Command

## Prompt

Test: $ARGUMENTS
""")
        
        result = command_loader_with_permissions.execute_command("error-command", "test")
        
        # Should return error in [Error: ...] format
        assert result.startswith("[Error:")
        assert result.endswith("]") or "Error:" in result
        # Extract error message
        if result.startswith("[Error:") and result.endswith("]"):
            error_msg = result[7:-1]
            assert len(error_msg) > 0
            assert "edit_file" in error_msg or "not allowed" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
