"""
Tests for the files module path resolution.
"""

import os
from pathlib import Path

import pytest
from askgpt.modules.files import (ensure_parent_exists,
                                      format_path_for_display,
                                      get_working_directory, is_path_safe,
                                      resolve_path)


class TestPathResolution:
    """Test path resolution functions."""

    def test_resolve_relative_path(self):
        """Test resolving a relative path."""
        # Get current directory
        cwd = Path.cwd()

        # Test simple relative path
        resolved = resolve_path("test.txt")
        assert resolved == cwd / "test.txt"
        assert resolved.is_absolute()

        # Test nested relative path
        resolved = resolve_path("subdir/file.txt")
        assert resolved == cwd / "subdir" / "file.txt"
        assert resolved.is_absolute()

    def test_resolve_absolute_path(self):
        """Test resolving an absolute path."""
        # Create an absolute path
        abs_path = Path("/tmp/test/file.txt")

        # Should return the same path (resolved)
        resolved = resolve_path(str(abs_path))
        assert resolved == abs_path.resolve()
        assert resolved.is_absolute()

    def test_resolve_path_with_dots(self):
        """Test resolving paths with . and .. components."""
        cwd = Path.cwd()

        # Test current directory reference
        resolved = resolve_path("./test.txt")
        assert resolved == cwd / "test.txt"

        # Test parent directory reference
        resolved = resolve_path("../test.txt")
        assert resolved == cwd.parent / "test.txt"

        # Test complex path
        resolved = resolve_path("./subdir/../test.txt")
        assert resolved == cwd / "test.txt"

    def test_get_working_directory(self):
        """Test getting the working directory."""
        wd = get_working_directory()
        assert wd == Path.cwd()
        assert wd.is_absolute()
        assert wd.is_dir()


class TestPathSafety:
    """Test path safety checks."""

    def test_is_path_safe_existing_file(self, tmp_path):
        """Test safety check for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        assert is_path_safe(test_file) is True

    def test_is_path_safe_nonexistent_file(self, tmp_path):
        """Test safety check for non-existent file with accessible parent."""
        test_file = tmp_path / "new_file.txt"

        # Parent exists and is accessible
        assert is_path_safe(test_file) is True

    def test_is_path_safe_inaccessible(self):
        """Test safety check for inaccessible path."""
        # Try a path that likely doesn't exist and has no accessible parent
        test_path = Path("/root/super/secret/file.txt")

        assert is_path_safe(test_path) is False


class TestPathFormatting:
    """Test path formatting for display."""

    def test_format_relative_path(self, tmp_path):
        """Test formatting a path relative to cwd."""
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create a subdirectory and file
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            test_file = subdir / "test.txt"

            # Should show as relative
            formatted = format_path_for_display(test_file)
            assert formatted == "subdir/test.txt"

            # Test current directory
            formatted = format_path_for_display(tmp_path)
            assert formatted == "./"
        finally:
            os.chdir(original_cwd)

    def test_format_absolute_path(self):
        """Test formatting a path not relative to cwd."""
        # Use a path definitely not relative to cwd
        test_path = Path("/tmp/some/other/path.txt")

        # Should return absolute path
        formatted = format_path_for_display(test_path)
        assert formatted == str(test_path)

    def test_format_parent_directory_path(self):
        """Test formatting a path in parent directory."""
        cwd = Path.cwd()
        parent_file = cwd.parent / "test.txt"

        # Should return absolute since it's not under cwd
        formatted = format_path_for_display(parent_file)
        assert formatted == str(parent_file)


class TestEnsureParentExists:
    """Test parent directory creation."""

    def test_ensure_parent_exists_new_directory(self, tmp_path):
        """Test creating parent directories."""
        test_file = tmp_path / "new" / "nested" / "dir" / "file.txt"

        # Parent doesn't exist yet
        assert not test_file.parent.exists()

        # Create parent directories
        ensure_parent_exists(test_file)

        # Now parent should exist
        assert test_file.parent.exists()
        assert test_file.parent.is_dir()

    def test_ensure_parent_exists_existing_directory(self, tmp_path):
        """Test with already existing parent directory."""
        test_file = tmp_path / "file.txt"

        # Parent already exists
        assert test_file.parent.exists()

        # Should not raise an error
        ensure_parent_exists(test_file)

        # Parent still exists
        assert test_file.parent.exists()


class TestIntegration:
    """Integration tests using the files module with nano_agent_tools."""

    @pytest.fixture(autouse=True)
    def setup_test_dir(self, tmp_path):
        """Set up a test directory and change to it."""
        self.original_cwd = os.getcwd()
        os.chdir(tmp_path)
        yield
        os.chdir(self.original_cwd)

    def test_tool_with_relative_path(self):
        """Test that tools work with relative paths."""
        from askgpt.modules.nano_agent_tools import (read_file_raw,
                                                         write_file_raw)

        # Write with relative path
        result = write_file_raw("test.txt", "Hello, World!")
        assert "Successfully wrote" in result

        # Read with relative path
        content = read_file_raw("test.txt")
        assert content == "Hello, World!"

    def test_tool_with_nested_path(self):
        """Test tools with nested relative paths."""
        from askgpt.modules.nano_agent_tools import (read_file_raw,
                                                         write_file_raw)

        # Write to nested path (should create directories)
        result = write_file_raw("subdir/nested/file.txt", "Nested content")
        assert "Successfully wrote" in result

        # Read from nested path
        content = read_file_raw("subdir/nested/file.txt")
        assert content == "Nested content"

    def test_tool_with_absolute_path(self, tmp_path):
        """Test tools with absolute paths."""
        from askgpt.modules.nano_agent_tools import (read_file_raw,
                                                         write_file_raw)

        # Use absolute path
        abs_path = tmp_path / "absolute_test.txt"

        # Write with absolute path
        result = write_file_raw(str(abs_path), "Absolute path content")
        assert "Successfully wrote" in result

        # Read with absolute path
        content = read_file_raw(str(abs_path))
        assert content == "Absolute path content"

    def test_list_directory_formatting(self):
        """Test that list_directory shows paths correctly."""
        from askgpt.modules.nano_agent_tools import (list_directory_raw,
                                                         write_file_raw)

        # Create some files
        write_file_raw("file1.txt", "content1")
        write_file_raw("subdir/file2.txt", "content2")

        # List current directory
        result = list_directory_raw(".")
        assert "Directory: ./" in result or "Directory: ." in result
        assert "file1.txt" in result
        assert "[DIR]  subdir/" in result

    def test_file_info_paths(self):
        """Test that get_file_info returns proper paths."""
        import json

        from askgpt.modules.nano_agent_tools import (get_file_info_raw,
                                                         write_file_raw)

        # Create a file
        write_file_raw("info_test.txt", "test content")

        # Get file info
        info_json = get_file_info_raw("info_test.txt")
        info = json.loads(info_json)

        # Should have both display path and absolute path
        assert "path" in info
        assert "absolute_path" in info
        assert info["path"] == "info_test.txt"  # Relative display
        assert Path(info["absolute_path"]).is_absolute()  # Absolute path
