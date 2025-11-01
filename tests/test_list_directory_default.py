"""
Tests for list_directory_raw default behavior.

This test validates that list_directory_raw properly defaults to the
current working directory when no path is provided.
"""

import os
import tempfile
from pathlib import Path

from askgpt.modules.nano_agent_tools import list_directory_raw


def test_list_directory_no_argument():
    """Test that list_directory_raw with no argument lists current working directory."""
    # Get the current working directory
    cwd = Path.cwd()

    # Call without arguments
    result = list_directory_raw()

    # Should show the current working directory
    assert "Directory:" in result
    # The path should be absolute (not "." or "./")
    assert str(cwd) in result or cwd.name in result

    # Should list contents of current directory
    # At minimum we should see some project files
    assert "Total items:" in result


def test_list_directory_none_argument():
    """Test that list_directory_raw with None lists current working directory."""
    # Get the current working directory
    cwd = Path.cwd()

    # Call with None
    result = list_directory_raw(None)

    # Should show the current working directory
    assert "Directory:" in result
    # The path should be absolute (not "." or "./")
    assert str(cwd) in result or cwd.name in result

    # Should list contents of current directory
    assert "Total items:" in result


def test_list_directory_with_path():
    """Test that list_directory_raw with a path still works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some test files
        test_dir = Path(tmpdir)
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.py").write_text("content2")
        (test_dir / "subdir").mkdir()

        # List the directory
        result = list_directory_raw(str(test_dir))

        # Should show the directory path
        assert "Directory:" in result
        assert "Total items: 3" in result
        assert "[FILE] file1.txt" in result
        assert "[FILE] file2.py" in result
        assert "[DIR]  subdir/" in result


def test_list_directory_relative_path():
    """Test that list_directory_raw with relative path resolves correctly."""
    # Use "." which should resolve to current working directory
    result_dot = list_directory_raw(".")
    result_none = list_directory_raw(None)

    # Both should list the same directory (current working directory)
    # Extract the directory path from both results
    import re

    # Extract directory paths
    dir_pattern = r"Directory: ([^\n]+)"
    match_dot = re.search(dir_pattern, result_dot)
    match_none = re.search(dir_pattern, result_none)

    if match_dot and match_none:
        path_dot = match_dot.group(1)
        path_none = match_none.group(1)

        # The absolute paths should be equivalent
        # (they might be formatted differently but should refer to the same directory)
        assert Path(path_dot).resolve() == Path(path_none).resolve()


def test_list_directory_error_handling():
    """Test error handling with None default."""
    # Test with non-existent directory
    result = list_directory_raw("/this/path/does/not/exist")
    assert "Error: Directory not found" in result

    # Test with a file instead of directory
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        try:
            result = list_directory_raw(tmpfile.name)
            assert "Error: Path is not a directory" in result
        finally:
            os.unlink(tmpfile.name)


def test_list_directory_in_different_cwd():
    """Test that list_directory defaults to actual CWD even when changed."""
    original_cwd = os.getcwd()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            test_dir = Path(tmpdir)
            (test_dir / "test_file.txt").write_text("test")
            sub_dir = test_dir / "subdir"
            sub_dir.mkdir()
            (sub_dir / "sub_file.txt").write_text("sub")

            # Change to the temp directory
            os.chdir(tmpdir)

            # List without arguments - should show temp directory contents
            result = list_directory_raw()
            assert "test_file.txt" in result
            assert "[DIR]  subdir/" in result

            # Change to subdirectory
            os.chdir(sub_dir)

            # List without arguments - should show subdirectory contents
            result = list_directory_raw()
            assert "sub_file.txt" in result
            assert "test_file.txt" not in result  # Parent file shouldn't be visible

    finally:
        # Restore original working directory
        os.chdir(original_cwd)


if __name__ == "__main__":
    # Run a quick validation
    print("Testing list_directory_raw default behavior...")

    # Test 1: No argument
    result = list_directory_raw()
    print(f"✓ No argument test: {len(result)} chars")
    assert "Directory:" in result

    # Test 2: None argument
    result = list_directory_raw(None)
    print(f"✓ None argument test: {len(result)} chars")
    assert "Directory:" in result

    # Test 3: Explicit path
    result = list_directory_raw(".")
    print(f"✓ Explicit '.' test: {len(result)} chars")
    assert "Directory:" in result

    print("\nAll basic tests passed! Run pytest for comprehensive testing.")
