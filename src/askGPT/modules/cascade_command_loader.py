"""
Cascade Command Loader for Nano Agent CLI.

Handles command loading with cascade system:
1. Load global commands from ~/.askgpt/commands/*.md
2. Load project commands from .askgpt/commands/*.md  
3. Project commands override global commands by name
4. Proper command parsing and execution with metadata support
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class Command:
    """Represents a loaded command with metadata."""

    name: str
    path: Path
    description: str
    prompt_template: str
    metadata: Dict[str, str] = field(default_factory=dict)
    source: str = "global"  # "global" or "project"
    required_tools: List[str] = field(default_factory=list)  # Tools required by this command (from tools: metadata)

    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure prompt template is properly formatted
        if not self.prompt_template:
            self.prompt_template = self.description

        # Set default metadata
        if "category" not in self.metadata:
            self.metadata["category"] = "general"


@dataclass
class CascadeCommandResult:
    """Result of cascade command loading."""

    commands: Dict[str, Command] = field(default_factory=dict)
    global_commands_loaded: int = 0
    project_commands_loaded: int = 0
    overridden_commands: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CascadeCommandLoader:
    """Manages loading and executing command files with cascade support."""

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        allowed_tools: Optional[List[str]] = None,
        blocked_tools: Optional[List[str]] = None,
    ):
        """
        Initialize the cascade command loader.

        Args:
            working_dir: Working directory for project commands (defaults to current dir)
            allowed_tools: Optional list of allowed tools. Commands will validate against this.
            blocked_tools: Optional list of blocked tools or command names.
        """
        self.working_dir = working_dir or Path.cwd()
        self.global_commands_dir = Path.home() / ".askgpt" / "commands"
        self.project_commands_dir = self.working_dir / ".askgpt" / "commands"

        # Permission configuration
        self.allowed_tools = allowed_tools
        self.blocked_tools = blocked_tools

        self._commands_cache: Dict[str, Command] = {}
        self._cache_valid = False

    def load_commands_cascade(self) -> CascadeCommandResult:
        """
        Load commands with cascade system.

        Returns:
            CascadeCommandResult with all loaded commands and metadata
        """
        result = CascadeCommandResult()

        # Load global commands first
        global_commands = self._load_commands_from_directory(
            self.global_commands_dir, source="global"
        )
        result.global_commands_loaded = len(global_commands)

        # Load project commands
        project_commands = self._load_commands_from_directory(
            self.project_commands_dir, source="project"
        )
        result.project_commands_loaded = len(project_commands)

        # Merge with project commands overriding global ones
        result.commands = global_commands.copy()

        for name, project_command in project_commands.items():
            if name in result.commands:
                result.overridden_commands.append(name)
                logger.debug(f"Project command '{name}' overrides global command")
            result.commands[name] = project_command

        # Update cache
        self._commands_cache = result.commands
        self._cache_valid = True

        # Log summary
        total_commands = len(result.commands)
        logger.info(
            f"Loaded {total_commands} commands ({result.global_commands_loaded} global, "
            f"{result.project_commands_loaded} project, {len(result.overridden_commands)} overridden)"
        )

        return result

    def _load_commands_from_directory(
        self, directory: Path, source: str
    ) -> Dict[str, Command]:
        """
        Load all commands from a specific directory.

        Args:
            directory: Directory containing command files
            source: Source identifier ("global" or "project")

        Returns:
            Dictionary of command name -> Command object
        """
        commands = {}

        if not directory.exists():
            logger.debug(f"Commands directory not found: {directory}")
            return commands

        # Ensure directory exists
        directory.mkdir(parents=True, exist_ok=True)

        # Load all .md files
        for file_path in directory.glob("*.md"):
            try:
                command_name = file_path.stem
                command = self._parse_command_file(command_name, file_path, source)
                if command:
                    commands[command_name] = command
                    logger.debug(f"Loaded {source} command: {command_name}")
            except Exception as e:
                logger.error(f"Failed to load command file {file_path}: {e}")

        return commands

    def _normalize_tool_name(self, tool_name: str) -> str:
        """
        Normalize tool names with alias support.
        
        Maps tool aliases to their canonical names. For example:
        - "Bash" or "bash" -> "bash_command"
        
        Args:
            tool_name: Tool name to normalize
            
        Returns:
            Normalized tool name (lowercase)
        """
        tool_lower = tool_name.strip().lower()
        # Alias mapping - case-insensitive
        aliases = {
            "bash": "bash_command",
        }
        return aliases.get(tool_lower, tool_name.strip().lower())

    def _parse_command_file(
        self, name: str, path: Path, source: str
    ) -> Optional[Command]:
        """
        Parse a command file's content.

        Args:
            name: Command name
            path: Path to command file
            source: Source identifier ("global" or "project")

        Returns:
            Parsed Command object or None if parsing failed
        """
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read command file {path}: {e}")
            return None

        # Parse YAML frontmatter if present
        yaml_metadata = {}
        content_after_frontmatter = content

        # Pattern to detect YAML frontmatter: ---\n...\n---\n
        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
        )

        if frontmatter_match:
            # Parse YAML frontmatter
            yaml_content = frontmatter_match.group(1)
            content_after_frontmatter = frontmatter_match.group(2)

            try:
                yaml_metadata = yaml.safe_load(yaml_content) or {}
            except yaml.YAMLError as e:
                logger.warning(f"Error parsing YAML frontmatter in {path}: {e}")
                yaml_metadata = {}

        lines = content_after_frontmatter.strip().split("\n")

        # Initialize parsing state
        description = ""
        prompt_template = ""
        metadata = {}
        # Start with YAML frontmatter metadata
        if yaml_metadata:
            metadata.update(yaml_metadata)

        # State tracking
        in_prompt_section = False
        in_metadata_section = False
        current_section = None

        for line in lines:
            line = line.rstrip()

            # Skip empty lines in metadata section
            if in_metadata_section and not line.strip():
                continue

            # Check for section headers
            if line.startswith("# ") and not description:
                # Main title - use as description
                description = line[2:].strip()
                continue
            elif line.startswith("## "):
                # Section header
                section = line[3:].strip().lower()
                current_section = section

                # Determine section type
                in_prompt_section = any(
                    keyword in section for keyword in ["prompt", "template", "content"]
                )
                in_metadata_section = any(
                    keyword in section
                    for keyword in ["metadata", "variables", "config", "settings"]
                )

                # Reset other sections
                if not in_prompt_section:
                    in_prompt_section = False
                if not in_metadata_section:
                    in_metadata_section = False

                continue

            # Process content based on current section
            if in_prompt_section:
                if line.strip():  # Non-empty line
                    if prompt_template:
                        prompt_template += "\n" + line
                    else:
                        prompt_template = line
            elif in_metadata_section:
                # Parse metadata key-value pairs
                if ":" in line and not line.strip().startswith("#"):
                    try:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()
                    except ValueError:
                        # Skip malformed metadata lines
                        continue
            elif (
                not current_section
                and not description
                and line.strip()
                and not line.startswith("#")
            ):
                # First non-header paragraph as description if no title found
                description = line.strip()

        # Fallback to entire content if no prompt template found
        if not prompt_template:
            # Filter out metadata and section headers for cleaner template
            clean_lines = []
            skip_line = False
            for line in lines:
                if line.startswith("## Metadata") or line.startswith("## Variables"):
                    skip_line = True
                    continue
                elif line.startswith("## "):
                    skip_line = False
                    continue
                elif skip_line and ":" in line and not line.startswith("#"):
                    continue  # Skip metadata lines
                elif not skip_line:
                    clean_lines.append(line)

            prompt_template = "\n".join(clean_lines).strip()

        # Set default values
        if not description:
            description = f"Command: {name}"

        # Add source information to metadata
        metadata["source"] = source
        metadata["file"] = str(path)

        # Extract required tools from metadata
        # Priority: allowed-tools (with hyphen) > tools > required_tools
        # Support comma-separated string format and apply normalization
        required_tools = []
        if "allowed-tools" in metadata:
            tools_value = metadata.get("allowed-tools", "")
            if isinstance(tools_value, str):
                # Handle comma-separated string (primary format)
                required_tools = [
                    self._normalize_tool_name(t.strip()) 
                    for t in tools_value.split(",") if t.strip()
                ]
            elif isinstance(tools_value, list):
                # Also support list format for backward compatibility
                required_tools = [
                    self._normalize_tool_name(str(t).strip()) 
                    for t in tools_value if t
                ]
        elif "tools" in metadata:
            tools_value = metadata.get("tools", [])
            if isinstance(tools_value, list):
                required_tools = [
                    self._normalize_tool_name(str(t).strip()) 
                    for t in tools_value if t
                ]
            elif isinstance(tools_value, str):
                # Handle comma-separated string
                required_tools = [
                    self._normalize_tool_name(t.strip()) 
                    for t in tools_value.split(",") if t.strip()
                ]
        elif "required_tools" in metadata:
            tools_value = metadata.get("required_tools", [])
            if isinstance(tools_value, list):
                required_tools = [
                    self._normalize_tool_name(str(t).strip()) 
                    for t in tools_value if t
                ]
            elif isinstance(tools_value, str):
                required_tools = [
                    self._normalize_tool_name(t.strip()) 
                    for t in tools_value.split(",") if t.strip()
                ]

        return Command(
            name=name,
            path=path,
            description=description,
            prompt_template=prompt_template,
            metadata=metadata,
            source=source,
            required_tools=required_tools,
        )

    def _validate_command_permissions(self, command: Command) -> Tuple[bool, Optional[str]]:
        """
        Validate if a command can be executed based on allowed_tools configuration.

        Logic:
        1. If allowed_tools is None: allow all commands (backward compatible)
        2. If command has no tools: metadata: always allow (default behavior)
        3. If command has tools: metadata: all tools must be in allowed_tools

        Returns:
            (allowed: bool, error_message: Optional[str])
        """
        # No restrictions - backward compatible
        if self.allowed_tools is None:
            return True, None

        # If command has no tools requirement, allow it
        if not command.required_tools:
            return True, None

        # Check if command is explicitly blocked
        if self.blocked_tools and command.name in [t.lower() for t in self.blocked_tools]:
            return False, f"Command '{command.name}' is blocked"

        # Normalize both required tools and allowed_tools for comparison
        # This ensures aliases like "Bash" match "bash_command" in allowed_tools
        normalized_required = [self._normalize_tool_name(t) for t in command.required_tools]
        normalized_allowed = [self._normalize_tool_name(t) for t in self.allowed_tools] if self.allowed_tools else []
        
        # Validate all required tools are in allowed_tools (both normalized)
        missing_tools = [t for t in normalized_required if t not in normalized_allowed]
        if missing_tools:
            return False, f"Command requires tools not allowed: {', '.join(missing_tools)}"

        return True, None

    def get_command(self, command_name: str) -> Optional[Command]:
        """
        Get a command by name.

        Args:
            command_name: Name of the command

        Returns:
            Command object if found, None otherwise
        """
        # Load commands if cache is not valid
        if not self._cache_valid:
            self.load_commands_cascade()

        return self._commands_cache.get(command_name)

    def list_commands(self) -> List[Command]:
        """
        List all available commands.

        Returns:
            List of Command objects sorted by name
        """
        # Load commands if cache is not valid
        if not self._cache_valid:
            self.load_commands_cascade()

        return sorted(self._commands_cache.values(), key=lambda c: c.name)

    def execute_command(self, command_name: str, arguments: str = "") -> Optional[str]:
        """
        Execute a command by substituting arguments.

        Args:
            command_name: Name of the command to execute
            arguments: Arguments to substitute for $ARGUMENTS

        Returns:
            Final prompt with substitutions, or None if command not found.
            Returns error string with [Error: prefix if command cannot be executed due to permissions.
        """
        command = self.get_command(command_name)
        if not command:
            return None

        # Validate command permissions before execution
        allowed, error_message = self._validate_command_permissions(command)
        if not allowed:
            return f"[Error: {error_message}]"

        # Substitute arguments in the prompt template
        prompt = command.prompt_template

        # Handle various argument syntaxes
        substitutions = [
            ("$ARGUMENTS", arguments),
            ("${ARGUMENTS}", arguments),
            ("$arguments", arguments),
            ("${arguments}", arguments),
        ]

        for pattern, replacement in substitutions:
            prompt = prompt.replace(pattern, replacement)

        # Handle escaped dollar signs (restore them after substitution)
        prompt = prompt.replace("\\$", "$")

        return prompt.strip()

    def search_commands(self, query: str) -> List[Command]:
        """
        Search commands by name or description.

        Args:
            query: Search query

        Returns:
            List of matching commands
        """
        query_lower = query.lower()
        commands = self.list_commands()

        matches = []
        for command in commands:
            if (
                query_lower in command.name.lower()
                or query_lower in command.description.lower()
                or any(
                    query_lower in value.lower() for value in command.metadata.values()
                )
            ):
                matches.append(command)

        return matches

    def get_commands_by_category(self, category: str) -> List[Command]:
        """
        Get commands by category.

        Args:
            category: Category name

        Returns:
            List of commands in the specified category
        """
        commands = self.list_commands()
        return [
            cmd
            for cmd in commands
            if cmd.metadata.get("category", "general").lower() == category.lower()
        ]

    def display_commands_table(self, category_filter: Optional[str] = None):
        """
        Display available commands in a formatted table.

        Args:
            category_filter: Optional category filter
        """
        if category_filter:
            commands = self.get_commands_by_category(category_filter)
            title = f"Commands - {category_filter.title()} Category"
        else:
            commands = self.list_commands()
            title = "All Available Commands"

        if not commands:
            if category_filter:
                message = f"No commands found in '{category_filter}' category."
            else:
                message = "No commands found."

            console.print(
                Panel(
                    f"[yellow]{message}[/yellow]\n\n"
                    f"Create your first command with:\n"
                    f"  nano-cli commands create <name>\n\n"
                    f"Commands directories:\n"
                    f"  Global: {self.global_commands_dir}\n"
                    f"  Project: {self.project_commands_dir}",
                    title="📋 Nano CLI Commands",
                    border_style="yellow",
                )
            )
            return

        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("Command", style="green", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Source", style="blue", no_wrap=True)
        table.add_column("Category", style="magenta", no_wrap=True)
        table.add_column("File", style="dim")

        for cmd in commands:
            # Truncate long descriptions
            desc = cmd.description
            if len(desc) > 60:
                desc = desc[:60] + "..."

            # Make path relative to home if possible
            try:
                display_path = cmd.path.relative_to(Path.home())
                display_path = f"~/{display_path}"
            except ValueError:
                display_path = str(cmd.path)

            # Get category from metadata
            category = cmd.metadata.get("category", "general")

            table.add_row(f"/{cmd.name}", desc, cmd.source, category, display_path)

        console.print(table)

        # Show summary
        global_count = sum(1 for cmd in commands if cmd.source == "global")
        project_count = sum(1 for cmd in commands if cmd.source == "project")

        console.print(
            f"\n[dim]Total: {len(commands)} commands "
            f"({global_count} global, {project_count} project)[/dim]"
        )
        console.print(f"[dim]Global directory: {self.global_commands_dir}[/dim]")
        console.print(f"[dim]Project directory: {self.project_commands_dir}[/dim]")
        console.print('[dim]Usage: nano-cli /<command> "arguments"[/dim]')

    def create_command_template(
        self,
        command_name: str,
        category: str = "general",
        overwrite: bool = False,
        global_command: bool = False,
    ) -> bool:
        """
        Create a new command template file.

        Args:
            command_name: Name for the new command
            category: Category for the command
            overwrite: Whether to overwrite existing command
            global_command: Whether to create in global directory

        Returns:
            True if created successfully, False otherwise
        """
        # Choose directory
        if global_command:
            target_dir = self.global_commands_dir
            location = "global"
        else:
            target_dir = self.project_commands_dir
            location = "project"

        # Ensure directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        command_path = target_dir / f"{command_name}.md"

        if command_path.exists() and not overwrite:
            console.print(
                f"[yellow]Command '{command_name}' already exists in {location}. "
                f"Use --overwrite to replace.[/yellow]"
            )
            return False

        # Generate template
        template = f"""# {command_name.title().replace('_', ' ').replace('-', ' ')}

Brief description of what this {command_name} command does.

## Prompt Template

Perform the following task: $ARGUMENTS

Please be thorough and provide detailed output.

## Usage

```bash
nano-cli /{command_name} "your arguments here"
```

## Examples

```bash
nano-cli /{command_name} "example input"
```

## Metadata

category: {category}
author: user
version: 1.0
created: {Path(__file__).stat().st_mtime if Path(__file__).exists() else 'unknown'}

## Notes

Add any additional context or requirements here.
"""

        try:
            command_path.write_text(template, encoding="utf-8")
            console.print(
                f"[green]✓ Created {location} command template: {command_path}[/green]"
            )

            # Invalidate cache to force reload
            self._cache_valid = False

            return True
        except Exception as e:
            console.print(f"[red]Error creating command template: {e}[/red]")
            return False

    def refresh_cache(self):
        """Refresh the commands cache."""
        self._cache_valid = False
        self.load_commands_cascade()


# Maintain backward compatibility with existing CommandLoader
class CommandLoader(CascadeCommandLoader):
    """Backward compatibility wrapper for CascadeCommandLoader."""

    def __init__(
        self,
        commands_dir: Optional[Path] = None,
        enable_command_eval: bool = None,
        allowed_tools: Optional[List[str]] = None,
        blocked_tools: Optional[List[str]] = None,
    ):
        """Initialize with backward compatibility."""
        if commands_dir is not None:
            # If specific commands_dir provided, use it as global directory
            working_dir = Path.cwd()
            super().__init__(
                working_dir=working_dir,
                allowed_tools=allowed_tools,
                blocked_tools=blocked_tools,
            )
            self.global_commands_dir = commands_dir
        else:
            super().__init__(
                allowed_tools=allowed_tools,
                blocked_tools=blocked_tools,
            )
        # Store enable_command_eval for shell evaluation (used by old CommandLoader)
        self.enable_command_eval = enable_command_eval

    def load_command(self, command_name: str) -> Optional[Command]:
        """Load a single command by name (backward compatibility)."""
        return self.get_command(command_name)

    def execute_command(self, command_name: str, arguments: str = "") -> Optional[str]:
        """
        Execute command with shell evaluation support (backward compatibility).
        
        Overrides parent to add shell command evaluation if enabled.
        """
        # Call parent to get the prompt (which includes permission validation)
        result = super().execute_command(command_name, arguments)
        
        # If parent returned error or None, return as-is
        if result is None or result.startswith("[Error:"):
            return result
        
        # Evaluate shell commands if enabled
        if self.enable_command_eval:
            result = self._evaluate_shell_commands(result)
        
        return result

    def _evaluate_shell_commands(self, text: str) -> str:
        """
        Evaluate shell commands in text and replace with their output.
        
        This is copied from the old CommandLoader for backward compatibility.
        
        Detects patterns like $`command` and executes them, replacing with output.
        """
        import os
        import subprocess
        
        if not self.enable_command_eval:
            return text
        
        # Pattern to match $`command` (but not \$`command` which is escaped)
        pattern = r'(?<!\\)\$`([^`]*)`'
        
        def evaluate_command(match):
            """Execute a single shell command and return its output."""
            command = match.group(1).strip()
            
            if not command:
                return "[Error: Empty command]"
            
            try:
                # Execute the command with timeout for safety
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10,  # 10 second timeout
                    check=False
                )
                
                # Get output (prefer stdout, fall back to stderr if empty)
                output = result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
                
                # Handle errors
                if result.returncode != 0:
                    if output:
                        return f"[Error: {output}]"
                    else:
                        return f"[Error: Command exited with code {result.returncode}]"
                
                # Handle empty output
                if not output:
                    return "[Empty output]"
                
                # For multiline output, replace newlines with spaces to keep it inline
                if '\n' in output:
                    output = output.replace('\n', ' ')
                
                return output
                
            except subprocess.TimeoutExpired:
                return "[Error: Command timed out after 10 seconds]"
            except Exception as e:
                return f"[Error: {str(e)}]"
        
        # Replace all command patterns with their output
        result = re.sub(pattern, evaluate_command, text)
        
        # Handle escaped patterns: \$`command` becomes $`command`
        result = result.replace(r'\$`', '$`')
        
        return result


def parse_command_syntax(input_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse input to detect command syntax.

    Args:
        input_str: Input string to parse

    Returns:
        Tuple of (command_name, arguments) if command syntax detected,
        (None, None) otherwise
    """
    # Check for /command syntax
    if input_str.startswith("/"):
        parts = input_str[1:].split(None, 1)
        command_name = parts[0] if parts else ""
        arguments = parts[1] if len(parts) > 1 else ""
        return command_name, arguments

    return None, None


# Export main classes and functions
__all__ = [
    "Command",
    "CascadeCommandResult",
    "CascadeCommandLoader",
    "CommandLoader",  # Backward compatibility
    "parse_command_syntax",
]
