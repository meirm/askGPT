"""
File path resolution and handling for Nano Agent.

This module provides consistent path resolution for all file operations,
ensuring paths are always resolved relative to the current working directory
and returned as absolute paths.
"""

from pathlib import Path
from typing import Union


def resolve_path(path_input: Union[str, Path]) -> Path:
    """
    Resolve a path to an absolute path.

    If the input is relative, it's resolved relative to os.getcwd().
    If the input is absolute, it's returned as-is (but as a Path object).

    Args:
        path_input: A string or Path object representing a file/directory path

    Returns:
        An absolute Path object
    """
    path = Path(path_input)

    if path.is_absolute():
        # Already absolute, just resolve to handle .. and symlinks
        return path.resolve()
    else:
        # Relative path - resolve relative to current working directory
        return (Path.cwd() / path).resolve()


def get_working_directory() -> Path:
    """
    Get the current working directory as a Path object.

    Returns:
        The current working directory as an absolute Path
    """
    return Path.cwd()


def is_path_safe(path: Path) -> bool:
    """
    Check if a path is safe to access.

    For existing paths, checks if accessible.
    For non-existent paths, checks if parent directory is accessible.

    Args:
        path: An absolute Path object

    Returns:
        True if the path is safe to access
    """
    try:
        # Try to access the path
        path.stat()
        return True
    except FileNotFoundError:
        # File doesn't exist - check if parent is accessible
        try:
            path.parent.stat()
            return True
        except (PermissionError, OSError, FileNotFoundError):
            return False
    except (PermissionError, OSError):
        # Path exists but not accessible
        return False


def format_path_for_display(path: Path, relative_to_cwd: bool = True) -> str:
    """
    Format a path for display to the user.

    Args:
        path: An absolute Path object
        relative_to_cwd: If True, show relative to cwd when possible

    Returns:
        A string representation of the path
    """
    if relative_to_cwd:
        try:
            # Try to make it relative to cwd for cleaner display
            cwd = Path.cwd()
            rel_path = path.relative_to(cwd)
            # If it's in the current directory, use ./ prefix for clarity
            if str(rel_path) == ".":
                return "./"
            elif not str(rel_path).startswith(".."):
                return str(rel_path)
        except ValueError:
            # Path is not relative to cwd, use absolute
            pass

    return str(path)


def ensure_parent_exists(path: Path) -> None:
    """
    Ensure the parent directory of a path exists.

    Creates parent directories if they don't exist.

    Args:
        path: An absolute Path object

    Raises:
        OSError: If parent directory cannot be created
    """
    path.parent.mkdir(parents=True, exist_ok=True)
