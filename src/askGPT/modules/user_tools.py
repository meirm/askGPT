"""
User-defined tools module for nano-cli.

This module handles loading and executing user-defined tools from ~/.askgpt/tools/.
Supports both Python modules and executable scripts.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

console = Console()


def get_tools_directory() -> Path:
    """Get the user tools directory path."""
    return Path.home() / ".askgpt" / "tools"


def get_allowed_tools() -> Optional[list]:
    """Get the list of allowed tools from ~/.askgpt/allowed-tools.json if it exists."""
    allowlist_path = Path.home() / ".askgpt" / "allowed-tools.json"
    if allowlist_path.exists():
        try:
            with open(allowlist_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            console.print(f"[yellow]Warning: Could not read allowlist from {allowlist_path}[/yellow]")
    return None


def list_user_tools() -> Dict[str, Dict[str, Any]]:
    """
    List all available user-defined tools.
    
    Returns:
        Dictionary mapping tool names to their metadata
    """
    tools_dir = get_tools_directory()
    tools = {}
    
    if not tools_dir.exists():
        return tools
    
    # Get allowed tools list if it exists
    allowed_tools = get_allowed_tools()
    
    # Scan for Python modules
    for py_file in tools_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
            
        tool_name = py_file.stem
        if allowed_tools and tool_name not in allowed_tools:
            continue
            
        try:
            # Import the module to get metadata
            sys.path.insert(0, str(tools_dir))
            module = __import__(tool_name)
            sys.path.pop(0)
            
            if hasattr(module, 'name') and hasattr(module, 'run'):
                tools[tool_name] = {
                    "type": "python",
                    "path": str(py_file),
                    "description": getattr(module, 'description', ''),
                    "module": module
                }
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load Python tool {tool_name}: {e}[/yellow]")
    
    # Scan for executable scripts
    for script_file in tools_dir.glob("*"):
        if script_file.name.startswith("__") or script_file.suffix == ".py":
            continue
            
        if not script_file.is_file():
            continue
            
        # Check if file is executable
        if not os.access(script_file, os.X_OK):
            continue
            
        tool_name = script_file.name
        if allowed_tools and tool_name not in allowed_tools:
            continue
            
        tools[tool_name] = {
            "type": "executable",
            "path": str(script_file),
            "description": ""
        }
    
    return tools


def run_user_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a user-defined tool with the given arguments.
    
    Args:
        tool_name: Name of the tool to run
        args: Arguments to pass to the tool
        
    Returns:
        Dictionary containing the tool's output
        
    Raises:
        KeyError: If tool is not found
        Exception: If tool execution fails
    """
    tools = list_user_tools()
    
    if tool_name not in tools:
        raise KeyError(f"Tool '{tool_name}' not found")
    
    tool_meta = tools[tool_name]
    
    if tool_meta["type"] == "python":
        # Run Python module
        module = tool_meta["module"]
        if not hasattr(module, 'run'):
            raise Exception(f"Python tool '{tool_name}' does not have a 'run' function")
        
        try:
            result = module.run(args)
            return result
        except Exception as e:
            raise Exception(f"Python tool '{tool_name}' failed: {e}")
    
    elif tool_meta["type"] == "executable":
        # Run executable script
        script_path = tool_meta["path"]
        
        try:
            # Prepare input JSON
            input_json = json.dumps(args)
            
            # Run the script with JSON input
            result = subprocess.run(
                [script_path],
                input=input_json,
                text=True,
                capture_output=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Script failed with exit code {result.returncode}: {result.stderr}")
            
            # Parse JSON output
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise Exception(f"Script output is not valid JSON: {e}")
                
        except subprocess.TimeoutExpired:
            raise Exception(f"Script timed out after 30 seconds")
        except Exception as e:
            raise Exception(f"Executable tool '{tool_name}' failed: {e}")
    
    else:
        raise Exception(f"Unknown tool type: {tool_meta['type']}")


def create_tools_directory():
    """Create the user tools directory if it doesn't exist."""
    tools_dir = get_tools_directory()
    tools_dir.mkdir(parents=True, exist_ok=True)
    return tools_dir


def create_example_tools():
    """Create example tools to help users get started."""
    tools_dir = create_tools_directory()
    
    # Create example Python tool
    python_example = tools_dir / "hello.py"
    if not python_example.exists():
        python_example.write_text('''"""
Example Python tool for nano-cli.

This tool demonstrates how to create a user-defined tool.
"""

name = "hello"
description = "A simple greeting tool"

def run(args):
    """
    Run the hello tool.
    
    Args:
        args: Dictionary containing tool arguments
        
    Returns:
        Dictionary with greeting message
    """
    name = args.get("name", "World")
    return {"result": f"Hello, {name}!"}
''')
    
    # Create example shell script
    shell_example = tools_dir / "greet"
    if not shell_example.exists():
        shell_example.write_text('''#!/bin/bash
# Example shell script tool for nano-cli
# This script reads JSON from stdin and outputs JSON to stdout

# Read JSON input
read input

# Parse the name from JSON (requires jq)
name=$(echo "$input" | jq -r '.name // "World"')

# Output JSON result
echo "{\"result\": \"Greetings, $name!\"}"
''')
        
        # Make the script executable
        os.chmod(shell_example, 0o755)
    
    console.print(f"[green]Created example tools in {tools_dir}[/green]")
    console.print("[dim]Example tools:[/dim]")
    console.print("  - hello.py (Python tool)")
    console.print("  - greet (Shell script tool)")
    console.print("\n[dim]Usage:[/dim]")
    console.print("  nano-cli list-user-tools")
    console.print('  nano-cli run-user-tool hello --input \'{"name": "Alice"}\'')
    console.print('  nano-cli run-user-tool greet --input \'{"name": "Bob"}\'')
