"""
Internal Agent Tools for Nano Agent.

This module contains tools that the OpenAI Agent SDK agent will use
to complete its work. These are not exposed directly via MCP but are
available to the agent during execution.
"""

import asyncio
import difflib
import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, Optional

# Import function_tool decorator from agents SDK
try:
    from agents import function_tool
except ImportError:
    # Fallback if agents SDK not available
    def function_tool(func):
        return func


# Import hook system (optional - gracefully degrade if not available)
try:
    try:
        from .hook_manager_simplified import get_simple_hook_manager as get_hook_manager
    except ImportError:
        from .hook_manager import get_hook_manager
    from .hook_types import HookEvent, HookEventData

    HOOKS_AVAILABLE = True
except ImportError:
    HOOKS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.debug("Hooks system not available")

from .constants import (ERROR_DIR_NOT_FOUND, ERROR_FILE_NOT_FOUND,
                        ERROR_NOT_A_DIR, ERROR_NOT_A_FILE, SUCCESS_FILE_EDIT,
                        SUCCESS_FILE_WRITE)
from .data_types import (CreateFileRequest, CreateFileResponse,
                         ReadFileRequest, ReadFileResponse, GrepSearchRequest, GrepSearchResponse, 
                         SearchFilesRequest, SearchFilesResponse, BashCommandRequest, BashCommandResponse)
from .files import (ensure_parent_exists, format_path_for_display,
                    get_working_directory, resolve_path)

# Initialize logger
logger = logging.getLogger(__name__)

def _grep_search_impl(request: GrepSearchRequest) -> GrepSearchResponse:
    """
    Internal implementation of grep_search tool.
    
    Args:
        request: Validated request with pattern, file_pattern, and context_lines
    
    Returns:
        Response with formatted search results or error information
    """
    try:
        # Get the working directory to search in
        search_dir = get_working_directory()
        
        # Compile the regex pattern
        try:
            pattern = re.compile(request.pattern, re.MULTILINE)
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{request.pattern}': {e}")
            return GrepSearchResponse(
                content="",
                error=f"Invalid regex pattern '{request.pattern}': {str(e)}"
            )
        
        results = []
        total_matches = 0
        
        # Determine which files to search
        if request.file_pattern:
            # Use glob pattern to filter files
            try:
                file_paths = list(search_dir.rglob(request.file_pattern))
            except Exception as e:
                logger.warning(f"Invalid file pattern '{request.file_pattern}': {e}")
                return GrepSearchResponse(
                    content="",
                    error=f"Invalid file pattern '{request.file_pattern}': {str(e)}"
                )
        else:
            # Search all text files (exclude common binary and hidden files)
            file_paths = []
            for file_path in search_dir.rglob('*'):
                if (file_path.is_file() and 
                    not file_path.name.startswith('.') and
                    not any(file_path.name.endswith(ext) for ext in 
                           ['.pyc', '.pyo', '.so', '.dylib', '.dll', '.exe', '.bin',
                            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
                            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.zip', '.tar',
                            '.gz', '.bz2', '.pdf', '.doc', '.docx'])):
                    file_paths.append(file_path)
        
        # Search in each file
        for file_path in file_paths:
            if not file_path.is_file():
                continue
                
            try:
                # Try to read the file as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError, OSError):
                # Skip binary files, permission denied, or other I/O errors
                continue
            
            lines = content.splitlines()
            file_matches = []
            
            # Search for pattern in each line
            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    # Calculate context range
                    start_line = max(1, line_num - request.context_lines)
                    end_line = min(len(lines), line_num + request.context_lines)
                    
                    # Get context lines
                    context_lines = []
                    for ctx_line_num in range(start_line, end_line + 1):
                        ctx_line = lines[ctx_line_num - 1]  # Convert to 0-based index
                        if ctx_line_num == line_num:
                            # Mark the matching line
                            context_lines.append(f"{ctx_line_num}:>{ctx_line}")
                        else:
                            context_lines.append(f"{ctx_line_num}: {ctx_line}")
                    
                    file_matches.append({
                        'line_number': line_num,
                        'line': line,
                        'context': context_lines
                    })
                    total_matches += 1
            
            # Add file results if there were matches
            if file_matches:
                display_path = format_path_for_display(file_path)
                results.append({
                    'file': display_path,
                    'matches': file_matches
                })
        
        # Format the results
        if not results:
            content = f"No matches found for pattern: '{request.pattern}'"
            if request.file_pattern:
                content += f" in files matching: '{request.file_pattern}'"
        else:
            formatted_lines = []
            formatted_lines.append(f"Found {total_matches} matches for pattern: '{request.pattern}'")
            if request.file_pattern:
                formatted_lines.append(f"In files matching: '{request.file_pattern}'")
            formatted_lines.append("")
            
            for result in results:
                formatted_lines.append(f"=== {result['file']} ===")
                for match in result['matches']:
                    formatted_lines.extend(match['context'])
                    formatted_lines.append("")  # Empty line between matches
            
            content = "\n".join(formatted_lines)
        
        logger.info(f"Grep search completed: {total_matches} matches found")
        return GrepSearchResponse(content=content)
        
    except Exception as e:
        error_msg = f"Error during grep search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return GrepSearchResponse(content="", error=error_msg)

def _search_files_impl(request: SearchFilesRequest) -> SearchFilesResponse:
    """
    Internal implementation of search_files tool.
    
    Args:
        request: Validated request with name_query and max_results
    
    Returns:
        Response with JSON-formatted file search results or error information
    """
    try:
        # Get the working directory to search in
        search_dir = get_working_directory()
        
        # Collect all files recursively (excluding hidden files by default)
        all_files = []
        for file_path in search_dir.rglob('*'):
            if (file_path.is_file() and 
                not file_path.name.startswith('.') and
                not any(part.startswith('.') for part in file_path.parts)):
                all_files.append(file_path)
        
        # Calculate similarity scores using difflib
        query = request.name_query.lower()
        scored_files = []
        
        for file_path in all_files:
            filename = file_path.name.lower()
            
            # Calculate different similarity metrics
            # 1. Exact match gets highest score
            if filename == query:
                score = 1.0
            # 2. Starts with query gets high score
            elif filename.startswith(query):
                score = 0.9
            # 3. Contains query gets medium score
            elif query in filename:
                score = 0.8
            # 4. Use sequence matcher for fuzzy matching
            else:
                # Use difflib.SequenceMatcher for similarity scoring
                matcher = difflib.SequenceMatcher(None, query, filename)
                score = matcher.ratio()
                
                # Also check if query matches any part of the path
                path_str = str(file_path).lower()
                if query in path_str:
                    # Boost score if query appears in full path
                    score = max(score, 0.7)
            
            # Only include files with reasonable similarity
            if score > 0.1:  # Minimum threshold
                display_path = format_path_for_display(file_path)
                scored_files.append({
                    'path': display_path,
                    'score': score,
                    'name': file_path.name
                })
        
        # Sort by score (descending) and limit results
        scored_files.sort(key=lambda x: x['score'], reverse=True)
        limited_results = scored_files[:request.max_results]
        
        # Format as JSON
        result_data = {
            'query': request.name_query,
            'total_found': len(scored_files),
            'results_shown': len(limited_results),
            'files': limited_results
        }
        
        content = json.dumps(result_data, indent=2)
        
        logger.info(
            f"File search completed: {len(limited_results)} results for query '{request.name_query}'"
        )
        return SearchFilesResponse(content=content)
        
    except Exception as e:
        error_msg = f"Error during file search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return SearchFilesResponse(content="", error=error_msg)


def _bash_command_impl(request: BashCommandRequest) -> BashCommandResponse:
    """
    Internal implementation of bash_command tool.
    
    Executes shell commands with full control over stdin, stdout, and stderr.
    
    Args:
        request: Validated request with command and execution parameters
        
    Returns:
        Response with command output, error streams, and exit code
    """
    start_time = time.time()
    
    try:
        # Resolve working directory if provided
        working_dir = None
        if request.working_dir:
            working_dir_path = resolve_path(request.working_dir)
            if not working_dir_path.exists():
                error_msg = f"Working directory not found: {request.working_dir}"
                logger.warning(error_msg)
                return BashCommandResponse(
                    stdout="",
                    stderr=error_msg,
                    return_code=1,
                    success=False,
                    error=error_msg,
                    execution_time=time.time() - start_time
                )
            if not working_dir_path.is_dir():
                error_msg = f"Path is not a directory: {request.working_dir}"
                logger.warning(error_msg)
                return BashCommandResponse(
                    stdout="",
                    stderr=error_msg,
                    return_code=1,
                    success=False,
                    error=error_msg,
                    execution_time=time.time() - start_time
                )
            working_dir = str(working_dir_path.absolute())
        else:
            working_dir = str(get_working_directory())
        
        # Prepare environment variables
        env = os.environ.copy()
        if request.env:
            env.update(request.env)
        
        # Log command execution
        logger.info(f"Executing command: {request.command[:100]}... in {working_dir}")
        
        # Execute the command
        try:
            result = subprocess.run(
                request.command if request.shell else request.command.split(),
                input=request.stdin,
                capture_output=True,
                text=True,
                shell=request.shell,
                cwd=working_dir,
                env=env,
                timeout=request.timeout
            )
            
            execution_time = time.time() - start_time
            
            logger.info(
                f"Command completed with exit code {result.returncode} in {execution_time:.2f}s"
            )
            
            return BashCommandResponse(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                success=(result.returncode == 0),
                error=None if result.returncode == 0 else f"Command exited with code {result.returncode}",
                execution_time=execution_time
            )
            
        except subprocess.TimeoutExpired as e:
            execution_time = time.time() - start_time
            error_msg = f"Command timed out after {request.timeout} seconds"
            logger.warning(error_msg)
            
            # Try to get partial output if available
            stdout = e.stdout.decode('utf-8', errors='replace') if e.stdout else ""
            stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ""
            
            return BashCommandResponse(
                stdout=stdout,
                stderr=stderr + f"\n{error_msg}",
                return_code=-1,
                success=False,
                error=error_msg,
                execution_time=execution_time
            )
            
        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            error_msg = f"Command failed: {str(e)}"
            logger.error(error_msg)
            
            return BashCommandResponse(
                stdout=e.stdout if e.stdout else "",
                stderr=e.stderr if e.stderr else str(e),
                return_code=e.returncode,
                success=False,
                error=error_msg,
                execution_time=execution_time
            )
            
    except PermissionError as e:
        execution_time = time.time() - start_time
        error_msg = f"Permission denied: {str(e)}"
        logger.error(error_msg)
        return BashCommandResponse(
            stdout="",
            stderr=error_msg,
            return_code=126,  # Standard code for permission denied
            success=False,
            error=error_msg,
            execution_time=execution_time
        )
        
    except FileNotFoundError as e:
        execution_time = time.time() - start_time
        error_msg = f"Command not found: {request.command.split()[0] if not request.shell else request.command}"
        logger.error(error_msg)
        return BashCommandResponse(
            stdout="",
            stderr=error_msg,
            return_code=127,  # Standard code for command not found
            success=False,
            error=error_msg,
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Unexpected error executing command: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return BashCommandResponse(
            stdout="",
            stderr=error_msg,
            return_code=-1,
            success=False,
            error=error_msg,
            execution_time=execution_time
        )


def _read_file_impl(request: ReadFileRequest) -> ReadFileResponse:
    """
    Internal implementation of read_file tool.

    Isolated for testing and reusability.

    Args:
        request: Validated request with file path and encoding

    Returns:
        Response with file content or error information
    """
    try:
        # Resolve to absolute path
        file_path = resolve_path(request.file_path)

        # Check if file exists
        if not file_path.exists():
            logger.warning(f"File not found: {request.file_path}")
            return ReadFileResponse(error=f"File not found: {request.file_path}")

        # Check if it's a file (not directory)
        if not file_path.is_file():
            logger.warning(f"Path is not a file: {request.file_path}")
            return ReadFileResponse(error=f"Path is not a file: {request.file_path}")

        # Get file metadata
        stat = file_path.stat()
        file_size = stat.st_size
        last_modified = datetime.fromtimestamp(stat.st_mtime)

        # Read file content
        try:
            with open(file_path, "r", encoding=request.encoding) as f:
                content = f.read()

            logger.info(
                f"Successfully read file: {request.file_path} ({file_size} bytes)"
            )

            return ReadFileResponse(
                content=content, file_size_bytes=file_size, last_modified=last_modified
            )

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading {request.file_path}: {e}")
            return ReadFileResponse(
                error=f"Failed to decode file with {request.encoding} encoding: {str(e)}"
            )

    except PermissionError as e:
        logger.error(f"Permission denied reading {request.file_path}: {e}")
        return ReadFileResponse(error=f"Permission denied: {request.file_path}")
    except Exception as e:
        logger.error(
            f"Unexpected error reading {request.file_path}: {e}", exc_info=True
        )
        return ReadFileResponse(error=f"Unexpected error: {str(e)}")


def _create_file_impl(request: CreateFileRequest) -> CreateFileResponse:
    """
    Internal implementation of create_file tool.

    Isolated for testing and reusability.

    Args:
        request: Validated request with file path, content, and options

    Returns:
        Response with success status or error information
    """
    try:
        # Resolve to absolute path
        file_path = resolve_path(request.file_path)

        # Check if file exists and overwrite is not allowed
        if file_path.exists() and not request.overwrite:
            logger.warning(f"File exists and overwrite=False: {request.file_path}")
            return CreateFileResponse(
                success=False,
                file_path=request.file_path,
                error=f"File already exists: {request.file_path}. Set overwrite=True to replace.",
            )

        # Create parent directories if they don't exist
        ensure_parent_exists(file_path)

        # Write file content
        try:
            with open(file_path, "w", encoding=request.encoding) as f:
                f.write(request.content)
                bytes_written = f.tell()

            logger.info(
                f"Successfully created file: {request.file_path} ({bytes_written} bytes)"
            )

            return CreateFileResponse(
                success=True,
                file_path=str(file_path.absolute()),
                bytes_written=bytes_written,
            )

        except UnicodeEncodeError as e:
            logger.error(f"Encoding error writing {request.file_path}: {e}")
            return CreateFileResponse(
                success=False,
                file_path=request.file_path,
                error=f"Failed to encode content with {request.encoding} encoding: {str(e)}",
            )

    except PermissionError as e:
        logger.error(f"Permission denied writing {request.file_path}: {e}")
        return CreateFileResponse(
            success=False,
            file_path=request.file_path,
            error=f"Permission denied: {request.file_path}",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error creating {request.file_path}: {e}", exc_info=True
        )
        return CreateFileResponse(
            success=False,
            file_path=request.file_path,
            error=f"Unexpected error: {str(e)}",
        )

# Raw tool implementations (not rich)
# Raw tool implementations for grep search and search files

def grep_search_raw(pattern: str, file_pattern: Optional[str] = None, context_lines: int = 3) -> str:
    """
    Search for patterns in files using regex.
    
    Args:
        pattern: Regex pattern or literal string to search for
        file_pattern: Optional glob pattern to filter files (e.g., '*.py')
        context_lines: Number of surrounding lines to include (default: 3)
    
    Returns:
        Formatted string with search results or error message
    """
    try:
        request = GrepSearchRequest(
            pattern=pattern,
            file_pattern=file_pattern,
            context_lines=context_lines
        )
        response = _grep_search_impl(request)
        
        if response.error:
            return f"Error: {response.error}"
        
        return response.content
        
    except Exception as e:
        error_msg = f"Error in grep_search_raw: {str(e)}"
        logger.error(error_msg)
        return error_msg

def search_files_raw(name_query: str, max_results: int = 20) -> str:
    """
    Search for files by name using fuzzy matching.
    
    Args:
        name_query: Partial or complete filename to search for
        max_results: Maximum number of results to return (default: 20)
    
    Returns:
        JSON string with file paths and similarity scores or error message
    """
    try:
        request = SearchFilesRequest(
            name_query=name_query,
            max_results=max_results
        )
        response = _search_files_impl(request)
        
        if response.error:
            return f"Error: {response.error}"
        
        return response.content
        
    except Exception as e:
        error_msg = f"Error in search_files_raw: {str(e)}"
        logger.error(error_msg)
        return error_msg


def bash_command_raw(
    command: str,
    stdin: Optional[str] = None,
    working_dir: Optional[str] = None,
    timeout: int = 30,
    shell: bool = True,
    env: Optional[Dict[str, str]] = None
) -> str:
    """
    Execute a shell command with control over stdin, stdout, and stderr.
    
    Args:
        command: Shell command to execute
        stdin: Optional input to provide to stdin
        working_dir: Optional working directory for command execution
        timeout: Timeout in seconds (default: 30)
        shell: Whether to run command through shell (default: True)
        env: Optional environment variables to set
        
    Returns:
        Formatted string with command output, stderr, and exit code
    """
    try:
        request = BashCommandRequest(
            command=command,
            stdin=stdin,
            working_dir=working_dir,
            timeout=timeout,
            shell=shell,
            env=env
        )
        response = _bash_command_impl(request)
        
        # Format the response for display
        result = []
        
        if response.stdout:
            result.append(f"=== STDOUT ===\n{response.stdout}")
        
        if response.stderr:
            result.append(f"=== STDERR ===\n{response.stderr}")
        
        result.append(f"=== EXIT CODE: {response.return_code} ===")
        result.append(f"=== EXECUTION TIME: {response.execution_time:.2f}s ===")
        
        if response.error:
            result.append(f"=== ERROR: {response.error} ===")
        
        return "\n".join(result)
        
    except Exception as e:
        error_msg = f"Error in bash_command_raw: {str(e)}"
        logger.error(error_msg)
        return f"=== ERROR ===\n{error_msg}"


def read_file_raw(file_path: str) -> str:
    """
    Read the contents of a file.

    Args:
        file_path: Path to the file to read (relative or absolute)

    Returns:
        File contents as string, or error message if failed
    """
    try:
        # Resolve to absolute path
        path = resolve_path(file_path)

        if not path.exists():
            return ERROR_FILE_NOT_FOUND.format(file_path)
        if not path.is_file():
            return ERROR_NOT_A_FILE.format(file_path)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Log with both display path and absolute path for clarity
        display_path = format_path_for_display(path)
        logger.info(
            f"Successfully read file: {display_path} ({len(content)} chars) [absolute: {path}]"
        )
        return content
    except Exception as e:
        error_msg = f"Error reading file {file_path}: {str(e)}"
        logger.error(error_msg)
        return error_msg


def write_file_raw(file_path: str, content: str) -> str:
    """
    Write content to a file.

    Args:
        file_path: Path where the file should be written (relative or absolute)
        content: Content to write to the file

    Returns:
        Success message or error
    """
    try:
        # Resolve to absolute path
        path = resolve_path(file_path)

        # Ensure parent directories exist
        ensure_parent_exists(path)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        size = len(content)
        display_path = format_path_for_display(path)
        logger.info(
            f"Successfully wrote file: {display_path} ({size} bytes) [absolute: {path}]"
        )
        return SUCCESS_FILE_WRITE.format(size, display_path)
    except Exception as e:
        error_msg = f"Error writing file {file_path}: {str(e)}"
        logger.error(error_msg)
        return error_msg


def list_directory_raw(directory_path: Optional[str] = None) -> str:
    """
    List contents of a directory.

    Args:
        directory_path: Path to directory (default: current working directory)

    Returns:
        Formatted directory listing or error message
    """
    try:
        # Default to current working directory if no path provided
        if directory_path is None:
            path = get_working_directory()
        else:
            # Resolve to absolute path
            path = resolve_path(directory_path)

        if not path.exists():
            dir_display = directory_path if directory_path else str(path)
            return ERROR_DIR_NOT_FOUND.format(dir_display)
        if not path.is_dir():
            dir_display = directory_path if directory_path else str(path)
            return ERROR_NOT_A_DIR.format(dir_display)

        items = []
        for item in sorted(path.iterdir()):
            if item.is_dir():
                items.append(f"[DIR]  {item.name}/")
            else:
                size = item.stat().st_size
                items.append(f"[FILE] {item.name} ({size} bytes)")

        # When no directory_path was provided, show absolute path
        if directory_path is None:
            display_path = str(path)  # Show absolute path
        else:
            display_path = format_path_for_display(path)
        result = f"Directory: {display_path}\n"
        result += f"Total items: {len(items)}\n"
        result += "\n".join(items) if items else "Empty directory"

        logger.info(
            f"Listed directory: {display_path} ({len(items)} items) [absolute: {path}]"
        )
        return result
    except Exception as e:
        error_msg = f"Error listing directory {directory_path}: {str(e)}"
        logger.error(error_msg)
        return error_msg


def edit_file_raw(file_path: str, old_str: str, new_str: str) -> str:
    """
    Edit a file by replacing exact text matches.

    Args:
        file_path: Path to the file to edit (relative or absolute)
        old_str: The exact text to find and replace (must match exactly including whitespace)
        new_str: The new text to insert in place of old_str

    Returns:
        Success message or detailed error message
    """
    try:
        # Resolve to absolute path
        path = resolve_path(file_path)

        # Check if file exists
        if not path.exists():
            return f"Error: File not found: {file_path}"

        # Check if it's a file (not directory)
        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read the current content
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError as e:
            return f"Error: Cannot read file (encoding issue): {str(e)}"

        # Check if old_str exists in the file
        if old_str not in content:
            # Provide helpful feedback
            lines = old_str.split("\n")
            if len(lines) > 1:
                # Multi-line search - check if any lines exist
                found_lines = []
                for line in lines:
                    if line.strip() and line.strip() in content:
                        found_lines.append(line.strip())

                if found_lines:
                    return (
                        f"Error: Exact text not found in file. "
                        f"Found similar lines but not exact match. "
                        f"Check whitespace and indentation. "
                        f"Found: {found_lines[:3]}"
                    )  # Show first 3 matches
                else:
                    return "Error: Text not found in file. None of the lines exist in the file."
            else:
                # Single line search - provide more context
                stripped = old_str.strip()
                if stripped and stripped in content:
                    return (
                        f"Error: Found similar text but not exact match. "
                        f"Check whitespace and indentation around: '{stripped[:50]}...'"
                    )
                else:
                    return f"Error: Text not found in file: '{old_str[:100]}...'"

        # Check for multiple occurrences
        occurrences = content.count(old_str)
        if occurrences > 1:
            return (
                f"Error: Found {occurrences} occurrences of the text. "
                f"Please provide more context to make the match unique, "
                f"or use a different tool to replace all occurrences."
            )

        # Perform the replacement
        new_content = content.replace(
            old_str, new_str, 1
        )  # Replace only first occurrence

        # Write the updated content back
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            return f"Error: Failed to write file: {str(e)}"

        # Log the operation
        display_path = format_path_for_display(path)
        logger.info(f"Successfully edited file: {display_path} [absolute: {path}]")

        return SUCCESS_FILE_EDIT

    except PermissionError:
        return f"Error: Permission denied when accessing file: {file_path}"
    except Exception as e:
        error_msg = f"Error editing file {file_path}: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_file_info_raw(file_path: str) -> str:
    """
    Get detailed information about a file.

    Args:
        file_path: Path to the file (relative or absolute)

    Returns:
        JSON string with file information or error message
    """
    try:
        # Resolve to absolute path
        path = resolve_path(file_path)

        if not path.exists():
            return ERROR_FILE_NOT_FOUND.format(file_path)

        stat = path.stat()
        display_path = format_path_for_display(path)

        info = {
            "path": display_path,
            "absolute_path": str(path),
            "name": path.name,
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "size_bytes": stat.st_size if path.is_file() else None,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": path.suffix if path.is_file() else None,
        }

        logger.info(f"Got file info for: {display_path} [absolute: {path}]")
        return json.dumps(info, indent=2)
    except Exception as e:
        error_msg = f"Error getting file info for {file_path}: {str(e)}"
        logger.error(error_msg)
        return error_msg


# Additional utility functions


def list_files(directory: str, pattern: str = "*") -> list[str]:
    """
    List files in a directory matching a pattern.

    This is a utility function that might be useful for agents.

    Args:
        directory: Directory path to list (relative or absolute)
        pattern: Glob pattern to match (default: "*" for all files)

    Returns:
        List of file paths matching the pattern (as display paths)
    """
    try:
        # Resolve to absolute path
        dir_path = resolve_path(directory)

        if not dir_path.is_dir():
            return []

        files = []
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                # Return display paths for cleaner output
                files.append(format_path_for_display(file_path))

        return sorted(files)
    except Exception as e:
        logger.error(f"Error listing files in {directory}: {e}")
        return []


def get_file_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata about a file without reading its content.
    Utility function, not exposed as a tool.

    Args:
        file_path: Path to the file (relative or absolute)

    Returns:
        Dictionary with file metadata or None if file doesn't exist
    """
    try:
        # Resolve to absolute path
        path = resolve_path(file_path)

        if not path.exists() or not path.is_file():
            return None

        stat = path.stat()
        display_path = format_path_for_display(path)

        return {
            "path": display_path,
            "absolute_path": str(path),
            "size_bytes": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "extension": path.suffix,
            "name": path.name,
        }
    except Exception as e:
        logger.error(f"Error getting file metadata for {file_path}: {e}")
        return None


# Global storage for tool call arguments (for lifecycle hook access)
_last_tool_args = {}
_pending_tool_args = {}  # Args set before tool execution


def capture_args(tool_name: str, **kwargs):
    """Capture tool arguments for lifecycle hooks."""
    global _last_tool_args, _pending_tool_args
    _last_tool_args[tool_name] = kwargs
    _pending_tool_args[tool_name] = kwargs
    logger.debug(f"Captured args for {tool_name}: {kwargs}")


# Async wrapper functions with hook support
async def _execute_tool_with_hooks(
    tool_name: str, tool_func, tool_kwargs: Dict[str, Any]
) -> Any:
    """Execute a tool with hook support.

    Args:
        tool_name: Name of the tool being executed
        tool_func: The actual tool function to execute
        tool_kwargs: Arguments for the tool

    Returns:
        Tool execution result
    """
    if not HOOKS_AVAILABLE:
        # No hooks available, execute directly
        return tool_func()

    try:
        hook_manager = get_hook_manager()

        # Prepare event data
        event_data = HookEventData(
            event="pre_tool_use",
            timestamp=datetime.now().isoformat(),
            context=hook_manager.context,
            working_dir=os.getcwd(),
            tool_name=tool_name,
            tool_args=tool_kwargs,
        )

        # Trigger pre-tool hook
        pre_result = await hook_manager.trigger_hook(
            HookEvent.PRE_TOOL_USE, event_data, blocking=True
        )

        # Check if execution was blocked
        if pre_result.blocked:
            error_msg = pre_result.blocking_reason or "Tool execution blocked by hook"
            logger.warning(f"Tool {tool_name} blocked: {error_msg}")
            return f"Error: {error_msg}"

        # Execute the tool
        try:
            result = tool_func()

            # Trigger post-tool hook
            event_data.tool_result = result
            await hook_manager.trigger_hook(HookEvent.POST_TOOL_USE, event_data)

            return result

        except Exception as e:
            # Trigger tool error hook
            event_data.error = str(e)
            await hook_manager.trigger_hook(HookEvent.TOOL_ERROR, event_data)
            raise

    except Exception as e:
        logger.error(f"Error in hook execution for {tool_name}: {e}")
        # Fall back to direct execution if hooks fail
        return tool_func()


def run_async(coro):
    """Helper to run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running (e.g., in Jupyter), create task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(coro)


# Decorated tool functions for OpenAI Agent SDK
@function_tool
def read_file(file_path: str) -> str:
    """Read the contents of a file."""
    capture_args("read_file", file_path=file_path)
    if HOOKS_AVAILABLE:
        return run_async(
            _execute_tool_with_hooks(
                "read_file", lambda: read_file_raw(file_path), {"file_path": file_path}
            )
        )
    return read_file_raw(file_path)


@function_tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    capture_args("write_file", file_path=file_path, content=content)
    if HOOKS_AVAILABLE:
        return run_async(
            _execute_tool_with_hooks(
                "write_file",
                lambda: write_file_raw(file_path, content),
                {"file_path": file_path, "content": content},
            )
        )
    return write_file_raw(file_path, content)


@function_tool
def list_directory(directory_path: Optional[str] = None) -> str:
    """List contents of a directory (defaults to current working directory)."""
    if directory_path is not None:
        capture_args("list_directory", directory_path=directory_path)
    else:
        capture_args("list_directory", directory_path="<current working directory>")

    if HOOKS_AVAILABLE:
        kwargs = (
            {"directory_path": directory_path} if directory_path is not None else {}
        )
        return run_async(
            _execute_tool_with_hooks(
                "list_directory", lambda: list_directory_raw(directory_path), kwargs
            )
        )
    return list_directory_raw(directory_path)


@function_tool
def get_file_info(file_path: str) -> str:
    """Get detailed information about a file."""
    capture_args("get_file_info", file_path=file_path)
    if HOOKS_AVAILABLE:
        return run_async(
            _execute_tool_with_hooks(
                "get_file_info",
                lambda: get_file_info_raw(file_path),
                {"file_path": file_path},
            )
        )
    return get_file_info_raw(file_path)


@function_tool
def grep_search(pattern: str, file_pattern: Optional[str] = None, context_lines: int = 3) -> str:
    """Search for patterns in files using regex.
    
    Args:
        pattern: Regex pattern or literal string to search for
        file_pattern: Optional glob pattern to filter files (e.g., '*.py')
        context_lines: Number of surrounding lines to include (default: 3)
    
    Returns:
        Formatted string with search results, showing matching lines with context
    """
    capture_args("grep_search", pattern=pattern, file_pattern=file_pattern, context_lines=context_lines)
    if HOOKS_AVAILABLE:
        return run_async(
            _execute_tool_with_hooks(
                "grep_search",
                lambda: grep_search_raw(pattern, file_pattern, context_lines),
                {"pattern": pattern, "file_pattern": file_pattern, "context_lines": context_lines},
            )
        )
    return grep_search_raw(pattern, file_pattern, context_lines)


@function_tool
def search_files(name_query: str, max_results: int = 20) -> str:
    """Search for files by name using fuzzy matching.
    
    Args:
        name_query: Partial or complete filename to search for
        max_results: Maximum number of results to return (default: 20)
    
    Returns:
        JSON string with file paths ranked by similarity score
    """
    capture_args("search_files", name_query=name_query, max_results=max_results)
    if HOOKS_AVAILABLE:
        return run_async(
            _execute_tool_with_hooks(
                "search_files",
                lambda: search_files_raw(name_query, max_results),
                {"name_query": name_query, "max_results": max_results},
            )
        )
    return search_files_raw(name_query, max_results)


@function_tool(strict_mode=False)
def bash_command(
    command: str,
    stdin: Optional[str] = None,
    working_dir: Optional[str] = None,
    timeout: int = 30,
    shell: bool = True,
    env: Optional[Dict[str, str]] = None
) -> str:
    """Execute a shell command with control over stdin, stdout, and stderr.
    
    IMPORTANT: This tool executes system commands and can modify the system state.
    
    Args:
        command: The shell command to execute
        stdin: Optional input to provide to the command's stdin
        working_dir: Directory to execute the command in (defaults to current directory)
        timeout: Maximum seconds to wait for command completion (default: 30)
        shell: Whether to run command through shell (default: True)
        env: Optional environment variables to set for the command
        
    Returns:
        Formatted output containing:
        - STDOUT: Standard output from the command
        - STDERR: Standard error output
        - EXIT CODE: Command exit code (0 = success)
        - EXECUTION TIME: How long the command took
        - ERROR: Any error message if command failed
        
    Examples:
        # Simple command
        bash_command("ls -la")
        
        # Command with stdin
        bash_command("cat > file.txt", stdin="Hello World")
        
        # Command with custom working directory
        bash_command("npm install", working_dir="/path/to/project")
        
        # Command with environment variables
        bash_command("echo $MY_VAR", env={"MY_VAR": "value"})
        bash_command("echo $A $B", env={"A": "hello", "B": "world"})
    """
    capture_args("bash_command", command=command, stdin=stdin, working_dir=working_dir,
                 timeout=timeout, shell=shell, env=env)
    if HOOKS_AVAILABLE:
        return run_async(
            _execute_tool_with_hooks(
                "bash_command",
                lambda: bash_command_raw(command, stdin, working_dir, timeout, shell, env),
                {"command": command, "stdin": stdin, "working_dir": working_dir,
                 "timeout": timeout, "shell": shell, "env": env}
            )
        )
    return bash_command_raw(command, stdin, working_dir, timeout, shell, env)


@function_tool
def edit_file(file_path: str, old_str: str, new_str: str) -> str:
    """Edit a file by replacing exact text with new text.

    IMPORTANT: This tool performs exact string matching including all whitespace and indentation.

    Args:
        file_path: The path to the file to modify (relative or absolute)
        old_str: The exact text to find and replace. Must match EXACTLY including:
                - All spaces and tabs
                - Line breaks
                - Indentation
                Use the read_file tool first to get the exact text format.
        new_str: The new text to insert in place of old_str

    Returns:
        'Successfully updated file' on success, or a detailed error message explaining:
        - If the file doesn't exist
        - If the old_str wasn't found (with hints about similar text)
        - If multiple matches were found (asks for more context)
        - Any permission or encoding issues

    Example usage:
        1. First read the file to see exact formatting:
           read_file('config.py')
        2. Then edit with exact match:
           edit_file('config.py', 'DEBUG = False', 'DEBUG = True')

    Common issues:
        - Spaces vs tabs: The text must match exactly
        - Line endings: Include \n if matching multiple lines
        - Hidden whitespace: Copy exactly from read_file output
    """
    capture_args("edit_file", file_path=file_path, old_str=old_str, new_str=new_str)
    if HOOKS_AVAILABLE:
        return run_async(
            _execute_tool_with_hooks(
                "edit_file",
                lambda: edit_file_raw(file_path, old_str, new_str),
                {"file_path": file_path, "old_str": old_str, "new_str": new_str},
            )
        )
    return edit_file_raw(file_path, old_str, new_str)


# Export all tools for the agent
def get_nano_agent_tools(permissions=None):
    """
    Get all tools for the nano agent with optional permission enforcement.

    Args:
        permissions: Optional ToolPermissions object to enforce restrictions

    Returns:
        List of tool functions rich with @function_tool
    """
    if permissions is None:
        # No restrictions - return all tools
        return [read_file, write_file, list_directory, get_file_info, edit_file, grep_search, search_files, bash_command]

    # Create permission-aware wrapper functions
    tools = []

    # Define base tools and their names
    available_tools = {
        "read_file": read_file,
        "write_file": write_file,
        "list_directory": list_directory,
        "get_file_info": get_file_info,
        "edit_file": edit_file,
        "grep_search": grep_search,
        "search_files": search_files,
        "bash_command": bash_command,
    }

    for tool_name, tool_func in available_tools.items():
        # Check if tool is allowed
        allowed, reason = permissions.check_tool_permission(tool_name)
        if allowed:
            # Create a permission-aware wrapper
            wrapped_tool = _create_permission_wrapper(tool_name, tool_func, permissions)
            tools.append(wrapped_tool)
        # If not allowed, simply don't include the tool

    return tools


def _create_permission_wrapper(tool_name: str, original_tool, permissions):
    """Create a permission-aware wrapper for a tool function.

    Args:
        tool_name: Name of the tool
        original_tool: The original tool function
        permissions: ToolPermissions object

    Returns:
        Wrapped tool function with permission checks
    """
    # Create specific wrappers for each tool type to avoid OpenAI SDK issues
    if tool_name == "read_file":

        @function_tool
        def read_file_permission_wrapper(file_path: str) -> str:
            """Read the contents of a file (with permission checks)."""
            allowed, reason = permissions.check_tool_permission(
                "read_file", {"file_path": file_path}
            )
            if not allowed:
                return f"Permission denied: {reason}"
            return read_file_raw(file_path)

        return read_file_permission_wrapper

    elif tool_name == "write_file":

        @function_tool
        def write_file_permission_wrapper(file_path: str, content: str) -> str:
            """Write content to a file (with permission checks)."""
            allowed, reason = permissions.check_tool_permission(
                "write_file", {"file_path": file_path}
            )
            if not allowed:
                return f"Permission denied: {reason}"
            return write_file_raw(file_path, content)

        return write_file_permission_wrapper

    elif tool_name == "list_directory":

        @function_tool
        def list_directory_permission_wrapper(
            directory_path: Optional[str] = None,
        ) -> str:
            """List contents of a directory (with permission checks)."""
            args = (
                {"directory_path": directory_path} if directory_path is not None else {}
            )
            allowed, reason = permissions.check_tool_permission("list_directory", args)
            if not allowed:
                return f"Permission denied: {reason}"
            return list_directory_raw(directory_path)

        return list_directory_permission_wrapper

    elif tool_name == "get_file_info":

        @function_tool
        def get_file_info_permission_wrapper(file_path: str) -> str:
            """Get detailed information about a file (with permission checks)."""
            allowed, reason = permissions.check_tool_permission(
                "get_file_info", {"file_path": file_path}
            )
            if not allowed:
                return f"Permission denied: {reason}"
            return get_file_info_raw(file_path)

        return get_file_info_permission_wrapper

    elif tool_name == "edit_file":

        @function_tool
        def edit_file_permission_wrapper(
            file_path: str, old_str: str, new_str: str
        ) -> str:
            """Edit a file by replacing exact text (with permission checks)."""
            allowed, reason = permissions.check_tool_permission(
                "edit_file", {"file_path": file_path}
            )
            if not allowed:
                return f"Permission denied: {reason}"
            return edit_file_raw(file_path, old_str, new_str)

        return edit_file_permission_wrapper

    elif tool_name == "grep_search":

        @function_tool
        def grep_search_permission_wrapper(
            pattern: str, file_pattern: Optional[str] = None, context_lines: int = 3
        ) -> str:
            """Search for patterns in files (with permission checks)."""
            allowed, reason = permissions.check_tool_permission(
                "grep_search", {"pattern": pattern}
            )
            if not allowed:
                return f"Permission denied: {reason}"
            return grep_search_raw(pattern, file_pattern, context_lines)

        return grep_search_permission_wrapper

    elif tool_name == "search_files":

        @function_tool
        def search_files_permission_wrapper(
            name_query: str, max_results: int = 20
        ) -> str:
            """Search for files by name (with permission checks)."""
            allowed, reason = permissions.check_tool_permission(
                "search_files", {"name_query": name_query}
            )
            if not allowed:
                return f"Permission denied: {reason}"
            return search_files_raw(name_query, max_results)

        return search_files_permission_wrapper

    elif tool_name == "bash_command":

        @function_tool(strict_mode=False)
        def bash_command_permission_wrapper(
            command: str,
            stdin: Optional[str] = None,
            working_dir: Optional[str] = None,
            timeout: int = 30,
            shell: bool = True,
            env: Optional[Dict[str, str]] = None
        ) -> str:
            """Execute a shell command (with permission checks)."""
            allowed, reason = permissions.check_tool_permission(
                "bash_command", {"command": command, "working_dir": working_dir}
            )
            if not allowed:
                return f"Permission denied: {reason}"
            return bash_command_raw(command, stdin, working_dir, timeout, shell, env)

        return bash_command_permission_wrapper

    else:
        # Fallback - should not happen
        @function_tool
        def unknown_tool_wrapper():
            return f"Error: Unknown tool '{tool_name}'"

        return unknown_tool_wrapper

