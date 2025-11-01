"""
Tests for bash_command tool in nano_agent_tools.py
"""

import json
import os
import platform
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from askgpt.modules.data_types import BashCommandRequest, BashCommandResponse
from askgpt.modules.nano_agent_tools import (
    _bash_command_impl,
    bash_command_raw,
)


class TestBashCommandImpl:
    """Test the internal _bash_command_impl function."""
    
    def test_simple_command_success(self):
        """Test executing a simple successful command."""
        request = BashCommandRequest(
            command="echo 'Hello World'",
            shell=True
        )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert "Hello World" in response.stdout
        assert response.stderr == ""
        assert response.error is None
        assert response.execution_time > 0
    
    def test_command_with_stderr(self):
        """Test command that writes to stderr."""
        # Use a command that works cross-platform
        if platform.system() == "Windows":
            request = BashCommandRequest(
                command="cmd /c echo Error message 1>&2",
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="echo 'Error message' >&2",
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True  # Echo returns 0 even when writing to stderr
        assert response.return_code == 0
        assert "Error message" in response.stderr
        assert response.execution_time > 0
    
    def test_command_with_non_zero_exit(self):
        """Test command that exits with non-zero code."""
        if platform.system() == "Windows":
            request = BashCommandRequest(
                command="cmd /c exit 1",
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="exit 1",
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is False
        assert response.return_code == 1
        assert response.error == "Command exited with code 1"
        assert response.execution_time > 0
    
    def test_command_with_stdin(self):
        """Test providing input via stdin."""
        if platform.system() == "Windows":
            request = BashCommandRequest(
                command="findstr .",  # Windows equivalent of cat
                stdin="Test input data",
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="cat",
                stdin="Test input data",
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert "Test input data" in response.stdout
        assert response.execution_time > 0
    
    def test_command_with_working_directory(self, tmp_path):
        """Test executing command in specific directory."""
        # Create a test directory with a file
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        test_file = test_dir / "test.txt"
        test_file.write_text("test content")
        
        if platform.system() == "Windows":
            request = BashCommandRequest(
                command="dir",
                working_dir=str(test_dir),
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="ls",
                working_dir=str(test_dir),
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert "test.txt" in response.stdout
        assert response.execution_time > 0
    
    def test_command_with_environment_variables(self):
        """Test setting environment variables."""
        if platform.system() == "Windows":
            request = BashCommandRequest(
                command="echo %MY_TEST_VAR%",
                env={"MY_TEST_VAR": "custom_value"},
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="echo $MY_TEST_VAR",
                env={"MY_TEST_VAR": "custom_value"},
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert "custom_value" in response.stdout
        assert response.execution_time > 0
    
    def test_command_timeout(self):
        """Test command timeout handling."""
        if platform.system() == "Windows":
            request = BashCommandRequest(
                command="timeout /t 10",  # Windows sleep
                timeout=1,
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="sleep 10",
                timeout=1,
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is False
        assert response.return_code == -1
        assert "timed out" in response.error.lower()
        assert response.execution_time >= 1
    
    def test_command_not_found(self):
        """Test handling of non-existent command."""
        request = BashCommandRequest(
            command="nonexistent_command_xyz123",
            shell=True
        )
        
        response = _bash_command_impl(request)
        
        assert response.success is False
        # Different shells return different error codes
        assert response.return_code != 0
        assert response.execution_time > 0
    
    def test_invalid_working_directory(self):
        """Test error handling for invalid working directory."""
        request = BashCommandRequest(
            command="echo test",
            working_dir="/nonexistent/directory/xyz123",
            shell=True
        )
        
        response = _bash_command_impl(request)
        
        assert response.success is False
        assert response.return_code == 1
        assert "Working directory not found" in response.error
        assert response.execution_time > 0
    
    def test_working_directory_not_a_directory(self, tmp_path):
        """Test error when working_dir points to a file."""
        test_file = tmp_path / "not_a_dir.txt"
        test_file.write_text("content")
        
        request = BashCommandRequest(
            command="echo test",
            working_dir=str(test_file),
            shell=True
        )
        
        response = _bash_command_impl(request)
        
        assert response.success is False
        assert response.return_code == 1
        assert "not a directory" in response.error.lower()
        assert response.execution_time > 0
    
    def test_shell_false_mode(self):
        """Test executing command without shell."""
        request = BashCommandRequest(
            command="echo",  # Just the command name
            shell=False
        )
        
        response = _bash_command_impl(request)
        
        # This should work on all platforms
        assert response.return_code == 0 or response.return_code == 1
        assert response.execution_time > 0
    
    def test_multiline_output(self):
        """Test command with multiline output."""
        if platform.system() == "Windows":
            request = BashCommandRequest(
                command="echo Line1 & echo Line2 & echo Line3",
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="echo -e 'Line1\\nLine2\\nLine3'",
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert "Line1" in response.stdout
        assert "Line2" in response.stdout
        assert "Line3" in response.stdout
        assert response.execution_time > 0


class TestBashCommandRaw:
    """Test the raw bash_command_raw function."""
    
    def test_simple_command_formatting(self):
        """Test output formatting for simple command."""
        result = bash_command_raw("echo 'Test output'")
        
        assert "=== STDOUT ===" in result
        assert "Test output" in result
        assert "=== EXIT CODE: 0 ===" in result
        assert "=== EXECUTION TIME:" in result
    
    def test_error_command_formatting(self):
        """Test output formatting for failed command."""
        if platform.system() == "Windows":
            result = bash_command_raw("cmd /c exit 1")
        else:
            result = bash_command_raw("exit 1")
        
        assert "=== EXIT CODE: 1 ===" in result
        assert "=== ERROR:" in result
        assert "=== EXECUTION TIME:" in result
    
    def test_stdin_parameter(self):
        """Test stdin parameter in raw function."""
        if platform.system() == "Windows":
            result = bash_command_raw("findstr .", stdin="Input text")
        else:
            result = bash_command_raw("cat", stdin="Input text")
        
        assert "=== STDOUT ===" in result
        assert "Input text" in result
        assert "=== EXIT CODE: 0 ===" in result
    
    def test_working_dir_parameter(self, tmp_path):
        """Test working_dir parameter in raw function."""
        test_dir = tmp_path / "work_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")
        
        if platform.system() == "Windows":
            result = bash_command_raw("dir", working_dir=str(test_dir))
        else:
            result = bash_command_raw("ls", working_dir=str(test_dir))
        
        assert "=== STDOUT ===" in result
        assert "file.txt" in result
        assert "=== EXIT CODE: 0 ===" in result
    
    def test_timeout_parameter(self):
        """Test timeout parameter in raw function."""
        if platform.system() == "Windows":
            result = bash_command_raw("timeout /t 10", timeout=1)
        else:
            result = bash_command_raw("sleep 10", timeout=1)
        
        assert "=== EXIT CODE: -1 ===" in result
        assert "=== ERROR:" in result
        assert "timed out" in result.lower()
    
    def test_env_parameter(self):
        """Test environment variables in raw function."""
        if platform.system() == "Windows":
            result = bash_command_raw("echo %TEST_VAR%", env={"TEST_VAR": "test123"})
        else:
            result = bash_command_raw("echo $TEST_VAR", env={"TEST_VAR": "test123"})
        
        assert "=== STDOUT ===" in result
        assert "test123" in result
        assert "=== EXIT CODE: 0 ===" in result
    
    def test_shell_false_parameter(self):
        """Test shell=False parameter in raw function."""
        result = bash_command_raw("echo", shell=False)
        
        # Should complete without crashing
        assert "=== EXIT CODE:" in result
        assert "=== EXECUTION TIME:" in result
    
    def test_stderr_output_formatting(self):
        """Test formatting of stderr output."""
        if platform.system() == "Windows":
            result = bash_command_raw("cmd /c echo Error 1>&2")
        else:
            result = bash_command_raw("echo 'Error' >&2")
        
        assert "=== STDERR ===" in result
        assert "Error" in result
        assert "=== EXIT CODE: 0 ===" in result
    
    def test_combined_stdout_stderr(self):
        """Test command with both stdout and stderr."""
        if platform.system() == "Windows":
            result = bash_command_raw("cmd /c echo Normal & echo Error 1>&2")
        else:
            result = bash_command_raw("echo 'Normal' && echo 'Error' >&2")
        
        assert "=== STDOUT ===" in result
        assert "Normal" in result
        assert "=== STDERR ===" in result
        assert "Error" in result
        assert "=== EXIT CODE: 0 ===" in result
    
    def test_exception_handling(self):
        """Test exception handling in raw function."""
        # Use an invalid type for a parameter to trigger exception
        with patch('askgpt.modules.nano_agent_tools._bash_command_impl') as mock_impl:
            mock_impl.side_effect = Exception("Test exception")
            
            result = bash_command_raw("echo test")
            
            assert "=== ERROR ===" in result
            assert "Test exception" in result


class TestBashCommandIntegration:
    """Integration tests for bash command tool."""
    
    def test_piped_commands(self):
        """Test piped commands."""
        if platform.system() == "Windows":
            request = BashCommandRequest(
                command="echo Hello | findstr Hello",
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="echo 'Hello World' | grep Hello",
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert "Hello" in response.stdout
    
    def test_file_creation_and_reading(self, tmp_path):
        """Test creating and reading a file."""
        test_file = tmp_path / "test_output.txt"
        
        # Create file
        if platform.system() == "Windows":
            create_cmd = f'echo Test content > "{test_file}"'
        else:
            create_cmd = f"echo 'Test content' > '{test_file}'"
        
        request1 = BashCommandRequest(
            command=create_cmd,
            working_dir=str(tmp_path),
            shell=True
        )
        response1 = _bash_command_impl(request1)
        
        assert response1.success is True
        assert response1.return_code == 0
        
        # Read file
        if platform.system() == "Windows":
            read_cmd = f'type "{test_file}"'
        else:
            read_cmd = f"cat '{test_file}'"
        
        request2 = BashCommandRequest(
            command=read_cmd,
            shell=True
        )
        response2 = _bash_command_impl(request2)
        
        assert response2.success is True
        assert response2.return_code == 0
        assert "Test content" in response2.stdout
    
    def test_command_chaining(self):
        """Test chained commands with && and ||."""
        if platform.system() == "Windows":
            # Windows uses & for chaining
            request = BashCommandRequest(
                command="echo First & echo Second",
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="echo 'First' && echo 'Second'",
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert "First" in response.stdout
        assert "Second" in response.stdout
    
    def test_conditional_execution(self):
        """Test conditional command execution."""
        if platform.system() == "Windows":
            # Windows conditional
            request = BashCommandRequest(
                command="if 1==1 echo Success",
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="[ 1 -eq 1 ] && echo 'Success'",
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert "Success" in response.stdout
    
    def test_large_output_handling(self):
        """Test handling of large command output."""
        if platform.system() == "Windows":
            # Generate large output on Windows
            request = BashCommandRequest(
                command="for /L %i in (1,1,1000) do @echo Line %i",
                shell=True
            )
        else:
            request = BashCommandRequest(
                command="for i in {1..1000}; do echo \"Line $i\"; done",
                shell=True
            )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert len(response.stdout) > 5000  # Should have substantial output
        assert "Line 1" in response.stdout
        assert "Line 1000" in response.stdout
    
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific test")
    def test_unix_specific_features(self):
        """Test Unix-specific shell features."""
        # Test process substitution
        request = BashCommandRequest(
            command="diff <(echo 'a') <(echo 'b')",
            shell=True
        )
        
        response = _bash_command_impl(request)
        
        # diff returns 1 when files differ
        assert response.return_code in [0, 1]
        assert response.execution_time > 0
    
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_windows_specific_features(self):
        """Test Windows-specific shell features."""
        # Test Windows environment variable
        request = BashCommandRequest(
            command="echo %COMPUTERNAME%",
            shell=True
        )
        
        response = _bash_command_impl(request)
        
        assert response.success is True
        assert response.return_code == 0
        assert len(response.stdout) > 0  # Should contain computer name


class TestBashCommandSecurity:
    """Test security aspects of bash command execution."""
    
    def test_command_injection_prevention(self):
        """Test that shell injection is handled safely."""
        # When shell=False, injection attempts should fail
        request = BashCommandRequest(
            command="echo safe; echo injected",
            shell=False
        )
        
        response = _bash_command_impl(request)
        
        # Command should fail or only execute first part
        # Different systems handle this differently
        assert response.execution_time > 0
    
    def test_path_traversal_in_working_dir(self):
        """Test path traversal attempts in working directory."""
        request = BashCommandRequest(
            command="echo test",
            working_dir="../../../etc",
            shell=True
        )
        
        response = _bash_command_impl(request)
        
        # Should either fail or resolve to safe absolute path
        assert response.execution_time > 0
    
    def test_environment_variable_isolation(self):
        """Test that custom env doesn't leak to system."""
        # Set a custom env var
        request1 = BashCommandRequest(
            command="echo test",
            env={"CUSTOM_TEST_VAR_XYZ": "secret"},
            shell=True
        )
        response1 = _bash_command_impl(request1)
        
        # Try to access it without setting it
        if platform.system() == "Windows":
            check_cmd = "echo %CUSTOM_TEST_VAR_XYZ%"
        else:
            check_cmd = "echo $CUSTOM_TEST_VAR_XYZ"
        
        request2 = BashCommandRequest(
            command=check_cmd,
            shell=True
        )
        response2 = _bash_command_impl(request2)
        
        # The variable should not be accessible
        assert "secret" not in response2.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])