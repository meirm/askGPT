"""
Tests for Internal Agent Tools.

Tests the tools that the OpenAI Agent SDK agent uses during execution.
"""

from datetime import datetime
from unittest.mock import mock_open, patch

import sys
from pathlib import Path
# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from askgpt.modules.data_types import CreateFileRequest, ReadFileRequest
from askgpt.modules.nano_agent_tools import (_create_file_impl,
                                                 _read_file_impl,
                                                 get_file_metadata, list_files,
                                                 read_file_raw, write_file_raw)


class TestReadFileImplementation:
    """Test the internal _read_file_impl function."""

    def test_read_file_success(self, tmp_path):
        """Test successful file reading."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        request = ReadFileRequest(file_path=str(test_file), encoding="utf-8")

        response = _read_file_impl(request)

        assert response.content == test_content
        assert response.error is None
        assert response.file_size_bytes == len(test_content)
        assert isinstance(response.last_modified, datetime)

    def test_read_file_not_found(self):
        """Test reading a non-existent file."""
        request = ReadFileRequest(file_path="/non/existent/file.txt", encoding="utf-8")

        response = _read_file_impl(request)

        assert response.content is None
        assert "File not found" in response.error
        assert response.file_size_bytes is None

    def test_read_file_directory(self, tmp_path):
        """Test attempting to read a directory."""
        request = ReadFileRequest(file_path=str(tmp_path), encoding="utf-8")

        response = _read_file_impl(request)

        assert response.content is None
        assert "not a file" in response.error

    def test_read_file_encoding_error(self, tmp_path):
        """Test reading a file with wrong encoding."""
        # Create a file with non-UTF-8 content
        test_file = tmp_path / "binary.dat"
        test_file.write_bytes(b"\x80\x81\x82\x83")

        request = ReadFileRequest(file_path=str(test_file), encoding="utf-8")

        response = _read_file_impl(request)

        assert response.content is None
        assert "Failed to decode" in response.error

    def test_read_file_permission_error(self, tmp_path):
        """Test reading a file without permission."""
        test_file = tmp_path / "restricted.txt"
        test_file.write_text("secret")

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            request = ReadFileRequest(file_path=str(test_file), encoding="utf-8")

            response = _read_file_impl(request)

            assert response.content is None
            assert "Permission denied" in response.error


class TestCreateFileImplementation:
    """Test the internal _create_file_impl function."""

    def test_create_file_success(self, tmp_path):
        """Test successful file creation."""
        test_file = tmp_path / "new_file.txt"
        test_content = "New content"

        request = CreateFileRequest(
            file_path=str(test_file),
            content=test_content,
            encoding="utf-8",
            overwrite=False,
        )

        response = _create_file_impl(request)

        assert response.success is True
        assert response.error is None
        assert response.bytes_written == len(test_content)
        assert test_file.read_text() == test_content

    def test_create_file_with_directories(self, tmp_path):
        """Test creating a file with non-existent parent directories."""
        test_file = tmp_path / "deep" / "nested" / "dir" / "file.txt"
        test_content = "Deep content"

        request = CreateFileRequest(
            file_path=str(test_file),
            content=test_content,
            encoding="utf-8",
            overwrite=False,
        )

        response = _create_file_impl(request)

        assert response.success is True
        assert test_file.exists()
        assert test_file.read_text() == test_content

    def test_create_file_exists_no_overwrite(self, tmp_path):
        """Test creating a file that already exists without overwrite."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("Original content")

        request = CreateFileRequest(
            file_path=str(test_file),
            content="New content",
            encoding="utf-8",
            overwrite=False,
        )

        response = _create_file_impl(request)

        assert response.success is False
        assert "already exists" in response.error
        assert test_file.read_text() == "Original content"  # Unchanged

    def test_create_file_exists_with_overwrite(self, tmp_path):
        """Test creating a file that already exists with overwrite."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("Original content")
        new_content = "Replaced content"

        request = CreateFileRequest(
            file_path=str(test_file),
            content=new_content,
            encoding="utf-8",
            overwrite=True,
        )

        response = _create_file_impl(request)

        assert response.success is True
        assert response.error is None
        assert test_file.read_text() == new_content

    def test_create_file_encoding_error(self, tmp_path):
        """Test creating a file with encoding issues."""
        test_file = tmp_path / "encoding_test.txt"

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.return_value.write.side_effect = UnicodeEncodeError(
                "ascii", "test", 0, 1, "ordinal not in range"
            )

            request = CreateFileRequest(
                file_path=str(test_file),
                content="Test content",
                encoding="ascii",
                overwrite=False,
            )

            response = _create_file_impl(request)

            assert response.success is False
            assert "Failed to encode" in response.error

    def test_create_file_permission_error(self, tmp_path):
        """Test creating a file without permission."""
        test_file = tmp_path / "no_permission.txt"

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            request = CreateFileRequest(
                file_path=str(test_file),
                content="Test",
                encoding="utf-8",
                overwrite=False,
            )

            response = _create_file_impl(request)

            assert response.success is False
            assert "Permission denied" in response.error


class TestAgentTools:
    """Test the tool functions used by agents."""

    def test_read_file_tool(self, tmp_path):
        """Test the read_file tool function."""
        test_file = tmp_path / "agent_test.txt"
        test_content = "Agent readable content"
        test_file.write_text(test_content)

        result = read_file_raw(str(test_file))

        assert result == test_content

    def test_read_file_tool_error(self):
        """Test read_file tool with error."""
        result = read_file_raw("/non/existent/file.txt")

        assert "Error: File not found" in result

    def test_write_file_tool(self, tmp_path):
        """Test the write_file tool function."""
        test_file = tmp_path / "agent_created.txt"
        test_content = "Content created by agent"

        result = write_file_raw(str(test_file), test_content)

        assert "Successfully wrote" in result
        assert test_file.read_text() == test_content

    def test_write_file_tool_with_overwrite(self, tmp_path):
        """Test write_file tool with overwrite."""
        test_file = tmp_path / "overwrite_test.txt"
        test_file.write_text("Old content")
        new_content = "New content from agent"

        result = write_file_raw(str(test_file), new_content)

        assert "Successfully wrote" in result
        assert test_file.read_text() == new_content


class TestUtilityFunctions:
    """Test utility functions."""

    def test_list_files(self, tmp_path):
        """Test listing files in a directory."""
        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        # List all files
        files = list_files(str(tmp_path))
        assert len(files) == 2
        assert str(tmp_path / "file1.txt") in files
        assert str(tmp_path / "file2.py") in files

        # List with pattern
        txt_files = list_files(str(tmp_path), "*.txt")
        assert len(txt_files) == 1
        assert str(tmp_path / "file1.txt") in txt_files

    def test_list_files_non_existent_directory(self):
        """Test listing files in non-existent directory."""
        files = list_files("/non/existent/directory")
        assert files == []

    def test_list_files_not_a_directory(self, tmp_path):
        """Test listing files when path is not a directory."""
        test_file = tmp_path / "not_a_dir.txt"
        test_file.write_text("content")

        files = list_files(str(test_file))
        assert files == []

    def test_get_file_metadata(self, tmp_path):
        """Test getting file metadata."""
        test_file = tmp_path / "info_test.md"
        test_content = "File for info test"
        test_file.write_text(test_content)

        info = get_file_metadata(str(test_file))

        assert info is not None
        assert info["name"] == "info_test.md"
        assert info["extension"] == ".md"
        assert info["size_bytes"] == len(test_content)
        assert "last_modified" in info
        assert "created" in info
        assert str(test_file.absolute()) == info["path"]

    def test_get_file_metadata_non_existent(self):
        """Test getting info for non-existent file."""
        info = get_file_metadata("/non/existent/file.txt")
        assert info is None

    def test_get_file_metadata_directory(self, tmp_path):
        """Test getting info for a directory."""
        info = get_file_metadata(str(tmp_path))
        assert info is None
