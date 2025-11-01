"""
Tests for the edit_file tool functionality.

This module tests the edit_file_raw function to ensure it correctly:
- Replaces exact text matches
- Handles whitespace and indentation correctly
- Provides helpful error messages
- Handles edge cases properly
"""

import os

from askgpt.modules.constants import SUCCESS_FILE_EDIT
# Import the function to test
from askgpt.modules.nano_agent_tools import edit_file_raw


class TestEditFile:
    """Test suite for the edit_file functionality."""

    def test_simple_edit(self, tmp_path):
        """Test a simple single-line edit."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world\nThis is a test\nGoodbye world")

        # Edit the file
        result = edit_file_raw(
            str(test_file), "This is a test", "This is an edited test"
        )

        # Check the result
        assert result == SUCCESS_FILE_EDIT
        assert (
            test_file.read_text()
            == "Hello world\nThis is an edited test\nGoodbye world"
        )

    def test_multiline_edit(self, tmp_path):
        """Test editing multiple lines at once."""
        # Create a test file
        test_file = tmp_path / "test.py"
        content = """def hello():
    print("Hello")
    return True

def goodbye():
    print("Goodbye")"""
        test_file.write_text(content)

        # Edit multiple lines
        old_text = """def hello():
    print("Hello")
    return True"""
        new_text = """def hello():
    print("Hello, World!")
    return False"""

        result = edit_file_raw(str(test_file), old_text, new_text)

        assert result == SUCCESS_FILE_EDIT
        expected = """def hello():
    print("Hello, World!")
    return False

def goodbye():
    print("Goodbye")"""
        assert test_file.read_text() == expected

    def test_exact_match_required(self, tmp_path):
        """Test that exact text matching is required."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def function():\n    pass")

        # Try to edit with non-existent text
        result = edit_file_raw(
            str(test_file), "def other_function():", "def new_function():"
        )

        # Should fail - text not found
        assert "not found" in result.lower()

        # Now with correct text
        result = edit_file_raw(str(test_file), "def function():", "def new_function():")

        assert result == SUCCESS_FILE_EDIT
        assert "def new_function():" in test_file.read_text()

    def test_file_not_found(self):
        """Test error when file doesn't exist."""
        result = edit_file_raw("nonexistent_file.txt", "old", "new")

        assert "Error: File not found" in result

    def test_text_not_found(self, tmp_path):
        """Test error when text to replace isn't found."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world")

        result = edit_file_raw(str(test_file), "Goodbye world", "Hello universe")

        assert "Error:" in result
        assert "not found" in result

    def test_multiple_occurrences(self, tmp_path):
        """Test error when text appears multiple times."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("apple\napple\napple")

        result = edit_file_raw(str(test_file), "apple", "orange")

        assert "Error:" in result
        assert "3 occurrences" in result
        assert "provide more context" in result

    def test_substring_replacement(self, tmp_path):
        """Test that substrings can be replaced correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("The quick brown fox jumps over the lazy dog")

        # Replace a substring
        result = edit_file_raw(str(test_file), "brown fox", "red fox")

        assert result == SUCCESS_FILE_EDIT
        assert test_file.read_text() == "The quick red fox jumps over the lazy dog"

    def test_empty_file(self, tmp_path):
        """Test editing an empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        result = edit_file_raw(str(test_file), "something", "something else")

        assert "Error:" in result
        assert "not found" in result

    def test_replace_with_empty(self, tmp_path):
        """Test replacing text with empty string (deletion)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3")

        result = edit_file_raw(str(test_file), "\nline2", "")

        assert result == SUCCESS_FILE_EDIT
        assert test_file.read_text() == "line1\nline3"

    def test_special_characters(self, tmp_path):
        """Test editing text with special characters."""
        test_file = tmp_path / "test.txt"
        test_file.write_text('value = "Hello $USER!"')

        result = edit_file_raw(str(test_file), '"Hello $USER!"', '"Hello ${USER}!"')

        assert result == SUCCESS_FILE_EDIT
        assert test_file.read_text() == 'value = "Hello ${USER}!"'

    def test_line_ending_preservation(self, tmp_path):
        """Test that line endings are handled correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3")

        # Edit with proper line endings
        result = edit_file_raw(str(test_file), "line2", "edited_line2")

        assert result == SUCCESS_FILE_EDIT
        assert test_file.read_text() == "line1\nedited_line2\nline3"

    def test_unicode_content(self, tmp_path):
        """Test editing files with Unicode characters."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello 世界 🌍", encoding="utf-8")

        result = edit_file_raw(str(test_file), "世界", "World")

        assert result == SUCCESS_FILE_EDIT
        assert test_file.read_text(encoding="utf-8") == "Hello World 🌍"

    def test_large_file_context(self, tmp_path):
        """Test that unique context is required for large files."""
        test_file = tmp_path / "test.txt"

        # Create a file with repeated patterns
        lines = []
        for i in range(10):
            lines.append(f"function_{i}():")
            lines.append("    return True")
            lines.append("")

        test_file.write_text("\n".join(lines))

        # Try to edit a non-unique pattern
        result = edit_file_raw(str(test_file), "    return True", "    return False")

        # Should fail due to multiple occurrences
        assert "Error:" in result
        assert "10 occurrences" in result

        # Now with unique context
        result = edit_file_raw(
            str(test_file),
            "function_5():\n    return True",
            "function_5():\n    return False",
        )

        assert result == SUCCESS_FILE_EDIT
        content = test_file.read_text()
        assert "function_5():\n    return False" in content
        # Check only one was changed
        assert content.count("return False") == 1

    def test_permission_error(self, tmp_path):
        """Test handling permission errors."""
        test_file = tmp_path / "readonly.txt"
        test_file.write_text("original content")

        # Make file read-only
        test_file.chmod(0o444)

        try:
            result = edit_file_raw(str(test_file), "original content", "new content")

            # Should get permission error
            assert "Error:" in result
            assert "Permission denied" in result or "Failed to write" in result
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)

    def test_directory_instead_of_file(self, tmp_path):
        """Test error when path is a directory."""
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()

        result = edit_file_raw(str(test_dir), "old", "new")

        assert "Error:" in result
        assert "not a file" in result

    def test_relative_path(self, tmp_path):
        """Test that relative paths work correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")

        # Change to tmp_path directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Use relative path
            result = edit_file_raw("test.txt", "original", "edited")  # Relative path

            assert result == SUCCESS_FILE_EDIT
            assert test_file.read_text() == "edited"
        finally:
            os.chdir(original_cwd)


def test_edit_file_cli_integration():
    """Test that edit_file can be used via the CLI tool testing."""
    # This is a basic smoke test - the full integration is tested elsewhere
    # Just verify the tool is registered and callable
    from askgpt.modules.nano_agent_tools import get_nano_agent_tools

    tools = get_nano_agent_tools()
    # FunctionTool objects have a name attribute, not __name__
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]

    assert "edit_file" in tool_names
