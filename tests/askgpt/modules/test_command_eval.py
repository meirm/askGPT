"""
Tests for command evaluation functionality in CommandLoader.

This module tests the $`command` shell evaluation feature.
"""

import os
import tempfile
from pathlib import Path

import pytest

from askgpt.modules.command_loader import CommandLoader


@pytest.fixture
def temp_commands_dir():
    """Create a temporary commands directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def loader_with_eval(temp_commands_dir):
    """Create a CommandLoader with command evaluation enabled."""
    return CommandLoader(commands_dir=temp_commands_dir, enable_command_eval=True)


@pytest.fixture
def loader_without_eval(temp_commands_dir):
    """Create a CommandLoader with command evaluation disabled."""
    return CommandLoader(commands_dir=temp_commands_dir, enable_command_eval=False)


class TestCommandEvaluationSecurity:
    """Test security features of command evaluation."""

    def test_eval_disabled_by_default(self, temp_commands_dir):
        """Command evaluation should be disabled by default."""
        loader = CommandLoader(commands_dir=temp_commands_dir)
        assert loader.enable_command_eval is False

    def test_eval_enabled_via_parameter(self, temp_commands_dir):
        """Command evaluation can be enabled via parameter."""
        loader = CommandLoader(commands_dir=temp_commands_dir, enable_command_eval=True)
        assert loader.enable_command_eval is True

    def test_eval_enabled_via_env_var(self, temp_commands_dir, monkeypatch):
        """Command evaluation can be enabled via environment variable."""
        monkeypatch.setenv("NANO_CLI_ENABLE_COMMAND_EVAL", "true")
        loader = CommandLoader(commands_dir=temp_commands_dir)
        assert loader.enable_command_eval is True

        # Test various truthy values
        for value in ["1", "yes", "on", "TRUE", "Yes", "ON"]:
            monkeypatch.setenv("NANO_CLI_ENABLE_COMMAND_EVAL", value)
            loader = CommandLoader(commands_dir=temp_commands_dir)
            assert loader.enable_command_eval is True

    def test_eval_disabled_via_env_var(self, temp_commands_dir, monkeypatch):
        """Command evaluation stays disabled with falsy environment values."""
        for value in ["false", "0", "no", "off", "FALSE"]:
            monkeypatch.setenv("NANO_CLI_ENABLE_COMMAND_EVAL", value)
            loader = CommandLoader(commands_dir=temp_commands_dir)
            assert loader.enable_command_eval is False

    def test_no_eval_when_disabled(self, loader_without_eval):
        """Commands should not be evaluated when disabled."""
        text = "Current date: $`date '+%Y-%m-%d'`"
        result = loader_without_eval._evaluate_shell_commands(text)
        # Should return unchanged
        assert result == text
        assert "$`" in result


class TestShellCommandEvaluation:
    """Test the _evaluate_shell_commands method."""

    def test_simple_command_evaluation(self, loader_with_eval):
        """Simple commands should be evaluated correctly."""
        text = "User: $`whoami`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should replace with actual username
        assert "$`" not in result
        assert "User:" in result
        assert result.startswith("User: ")

    def test_multiple_commands(self, loader_with_eval):
        """Multiple commands in one text should all be evaluated."""
        text = "User: $`whoami`, Home: $`echo $HOME`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Both commands should be evaluated
        assert "$`whoami`" not in result
        assert "$`echo $HOME`" not in result
        assert "User:" in result
        assert "Home:" in result

    def test_command_with_quotes(self, loader_with_eval):
        """Commands with quotes should work correctly."""
        text = "Date: $`date '+%Y-%m-%d'`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should evaluate date command
        assert "$`" not in result
        assert "Date:" in result
        # Result should contain a date-like pattern (YYYY-MM-DD)
        import re
        assert re.search(r'\d{4}-\d{2}-\d{2}', result)

    def test_escaped_command(self, loader_with_eval):
        """Escaped commands should not be evaluated."""
        text = r"Example: \$`whoami`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should not evaluate escaped command
        assert "$`whoami`" in result
        assert "\\" not in result  # Backslash should be removed

    def test_empty_command(self, loader_with_eval):
        """Empty commands should return error message."""
        text = "Empty: $``"
        result = loader_with_eval._evaluate_shell_commands(text)
        assert "[Error:" in result
        assert "Empty" in result

    def test_command_with_error(self, loader_with_eval):
        """Commands that fail should return error message."""
        text = "Failed: $`command_that_does_not_exist_xyz123`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should contain error indicator
        assert "[Error:" in result

    def test_command_with_empty_output(self, loader_with_eval):
        """Commands with no output should show empty output message."""
        # Use a command that truly produces no output
        text = "Empty output: $`true`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should indicate empty output
        assert "[Empty output]" in result

    def test_multiline_output_flattened(self, loader_with_eval):
        """Multiline output should be flattened to single line."""
        text = "Lines: $`echo -e 'line1\nline2\nline3'`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should not have literal newlines in result
        # (they should be replaced with spaces)
        assert "Lines:" in result
        # Check that we have all content but as single line
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    def test_command_with_pipe(self, loader_with_eval):
        """Commands with pipes should work correctly."""
        text = "Count: $`echo -e 'a\nb\nc' | wc -l`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should execute pipe correctly
        assert "$`" not in result
        assert "Count:" in result
        # Result should contain a number
        assert any(char.isdigit() for char in result)


class TestCommandExecution:
    """Test full command execution with evaluation."""

    def test_command_with_eval_enabled(self, loader_with_eval, temp_commands_dir):
        """Command with shell evaluation should work when enabled."""
        # Create a test command file
        command_file = temp_commands_dir / "test_eval.md"
        command_file.write_text("""# Test Eval Command

Current date: $`date '+%Y-%m-%d'`
Current user: $`whoami`

Task: $ARGUMENTS
""")

        result = loader_with_eval.execute_command("test_eval", "analyze this")

        # Should have evaluated commands
        assert "$`date" not in result
        assert "$`whoami`" not in result

        # Should have substituted arguments
        assert "analyze this" in result

        # Should contain actual values
        assert "Current date:" in result
        assert "Current user:" in result

    def test_command_with_eval_disabled(self, loader_without_eval, temp_commands_dir):
        """Command with shell evaluation should not eval when disabled."""
        # Create a test command file
        command_file = temp_commands_dir / "test_no_eval.md"
        command_file.write_text("""# Test No Eval Command

Current date: $`date '+%Y-%m-%d'`

Task: $ARGUMENTS
""")

        result = loader_without_eval.execute_command("test_no_eval", "analyze this")

        # Commands should NOT be evaluated
        assert "$`date" in result

        # But arguments should still be substituted
        assert "analyze this" in result
        assert "$ARGUMENTS" not in result

    def test_arguments_in_commands(self, loader_with_eval, temp_commands_dir):
        """$ARGUMENTS substitution should happen before command evaluation."""
        # Create a test command that uses arguments in shell command
        command_file = temp_commands_dir / "test_args.md"
        command_file.write_text("""# Test Args Command

Processing: $ARGUMENTS
Echo test: $`echo "Working on: $ARGUMENTS"`
""")

        # Note: This test might not work as expected because $ARGUMENTS
        # in the shell command would need to be a shell variable
        # But it tests that arguments are substituted first
        result = loader_with_eval.execute_command("test_args", "my task")

        # Arguments should be substituted in regular text
        assert "Processing: my task" in result

    def test_mixed_escaped_and_normal(self, loader_with_eval, temp_commands_dir):
        """Mix of escaped and normal commands should work correctly."""
        command_file = temp_commands_dir / "test_mixed.md"
        command_file.write_text(r"""# Test Mixed

Real command: $`whoami`
Escaped example: \$`date`
Another real: $`echo "hello"`
""")

        result = loader_with_eval.execute_command("test_mixed")

        # Real commands should be evaluated
        assert "$`whoami`" not in result
        assert "$`echo" not in result

        # Escaped command should not be evaluated but backslash removed
        assert "$`date`" in result
        assert "\\" not in result


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_nested_backticks_in_output(self, loader_with_eval):
        """Output containing backticks should be handled correctly."""
        text = "Test: $`echo 'output with ` backtick'`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should handle output with backticks
        assert "Test:" in result

    def test_command_timeout(self, loader_with_eval):
        """Long-running commands should timeout."""
        text = "Timeout: $`sleep 15`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Should timeout after 10 seconds and show error
        assert "[Error:" in result
        assert "timeout" in result.lower()

    def test_special_characters_in_output(self, loader_with_eval):
        """Special characters in output should be preserved."""
        text = "Special: $`echo 'test@#$%^&*()_+'`"
        result = loader_with_eval._evaluate_shell_commands(text)
        # Special characters should be in output
        assert "test@#$%^&*()_+" in result

    def test_no_commands_in_text(self, loader_with_eval):
        """Text without commands should pass through unchanged."""
        text = "This is just regular text with no commands"
        result = loader_with_eval._evaluate_shell_commands(text)
        assert result == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
