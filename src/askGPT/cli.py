#!/usr/bin/env python
"""
askGPT CLI - Command-line interface for askGPT AI agent.

This provides a command-line interface to interact with askGPT agents
with various commands and interactive modes. Defaults to offline/local mode.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Enable flexible configuration system
try:
    from .modules.config_integration import enable_flexible_configuration

    enable_flexible_configuration()
except ImportError:
    # Fallback if config_integration is not available
    pass

from .modules.cascade_command_loader import CommandLoader, parse_command_syntax
from .modules.constants import (DEFAULT_MODEL, DEFAULT_PROVIDER,
                                DEFAULT_TEMPERATURE, DEMO_PROMPTS, MAX_TOKENS)
from .modules.data_types import PromptNanoAgentRequest
from .modules.nano_agent import _execute_nano_agent
from .modules.output_formats import (AgentResponse, BillingInfo, OutputFormat,
                                     create_formatter)
from .modules.session_manager import SessionManager
from .modules.user_tools import list_user_tools, run_user_tool

# Import version from package
try:
    from . import __version__
except ImportError:
    __version__ = "1.0.0"  # Fallback version

app = typer.Typer()
console = Console()
console_stderr = Console(stderr=True)


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print(f"askgpt version {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    _version: Optional[bool] = typer.Option(
        None,
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
    prompt: Optional[str] = typer.Option(
        None,
        "-p",
        "--prompt",
        help="Run a prompt directly (replaces 'askgpt run')",
    ),
    model: Optional[str] = typer.Option(None, help="Model to use"),
    provider: Optional[str] = typer.Option(None, help="Provider to use"),
    agent: Optional[str] = typer.Option(None, help="Agent personality to use"),
    api_base: Optional[str] = typer.Option(
        None, help="API base URL (overrides environment variables)"
    ),
    api_key: Optional[str] = typer.Option(None, help="API key (overrides environment variables)"),
    verbose: bool = typer.Option(False, help="Show detailed output"),
    read_only: bool = typer.Option(
        False, "--read-only", help="Disable file system modifications (safe exploration mode)"
    ),
    max_tool_calls: Optional[int] = typer.Option(
        None, "--max-tool-calls", help="Maximum number of tool calls allowed (default: 20)"
    ),
    unlimited_tool_calls: bool = typer.Option(
        False, "--unlimited-tool-calls", help="Allow unlimited tool calls (use with caution)"
    ),
    # Claude-inspired options
    continue_session: bool = typer.Option(
        False, "--continue", "-c", help="Continue the last session"
    ),
    session: Optional[str] = typer.Option(
        None, "--session", "-s", help="Use a specific session ID"
    ),
    new_session: bool = typer.Option(False, "--new", "-n", help="Force a new session"),
    temperature: Optional[float] = typer.Option(
        None, "--temperature", "-t", help="Model temperature (0.0-2.0)"
    ),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens", help="Maximum response tokens"
    ),
    save: bool = typer.Option(
        True, "--save/--no-save", help="Save conversation to session history"
    ),
    enable_trace: bool = typer.Option(
        False, "--enable-trace", help="Enable OpenAI agent tracing"
    ),
    # New output control options
    billing: bool = typer.Option(
        False, "--billing", help="Show token usage and cost information"
    ),
    output_format: str = typer.Option(
        "simple",
        "--output-format",
        "-f",
        help="Output format: simple (default), json, or rich",
    ),
    output_thinking: bool = typer.Option(
        False, "--output-thinking", help="Show agent thinking and reasoning text"
    ),
    panel_width: Optional[int] = typer.Option(
        None,
        "--panel-width",
        help="Maximum width for rich output panels (default: auto-detect)",
    ),
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Development mode - show detailed error messages for debugging",
    ),
    simple: bool = typer.Option(False, help="Use simple mode without autocompletion"),
):
    """askGPT CLI - Multi-provider AI agent CLI with offline-first support.

    By default, enters interactive mode. Use -p/--prompt to run a single prompt.
    Defaults to offline/local mode (Ollama).
    """
    # If a subcommand was invoked, let it handle execution
    if ctx.invoked_subcommand is not None:
        return

    # If prompt is provided, run it directly (like 'askgpt run')
    if prompt is not None:
        _run_prompt(
            prompt=prompt,
            model=model,
            provider=provider,
            agent=agent,
            api_base=api_base,
            api_key=api_key,
            verbose=verbose,
            read_only=read_only,
            max_tool_calls=max_tool_calls,
            unlimited_tool_calls=unlimited_tool_calls,
            continue_session=continue_session,
            session=session,
            new_session=new_session,
            temperature=temperature,
            max_tokens=max_tokens,
            save=save,
            enable_trace=enable_trace,
            billing=billing,
            output_format=output_format,
            output_thinking=output_thinking,
            panel_width=panel_width,
            dev=dev,
        )
    else:
        # No prompt and no subcommand - enter interactive mode
        _run_interactive_default(
            model=model,
            provider=provider,
            agent=agent,
            api_base=api_base,
            api_key=api_key,
            simple=simple,
            enable_trace=enable_trace,
            verbose=verbose,
            read_only=read_only,
        )


def get_log_console(verbose: bool = False) -> Console:
    """Get the appropriate console for logging messages.

    Args:
        verbose: If True, returns stderr console. If False, returns stdout console.

    Returns:
        Console instance for logging output
    """
    return console_stderr if verbose else console


def _run_prompt(
    prompt: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    agent: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False,
    read_only: bool = False,
    max_tool_calls: Optional[int] = None,
    unlimited_tool_calls: bool = False,
    continue_session: bool = False,
    session: Optional[str] = None,
    new_session: bool = False,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    save: bool = True,
    enable_trace: bool = False,
    billing: bool = False,
    output_format: str = "simple",
    output_thinking: bool = False,
    panel_width: Optional[int] = None,
    dev: bool = False,
):
    """Internal function to run a prompt (shared by main callback and run command)."""
    # Determine provider first before checking API key
    if provider is None:
        config_file = Path.home() / ".askgpt" / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    provider = config.get("default_provider", DEFAULT_PROVIDER)
            except Exception:
                provider = DEFAULT_PROVIDER
        else:
            provider = DEFAULT_PROVIDER

    check_api_key(provider)

    # Load config defaults if not specified
    config_file = Path.home() / ".askgpt" / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                if model is None:
                    model = config.get("default_model", DEFAULT_MODEL)
                if provider is None:
                    provider = config.get("default_provider", DEFAULT_PROVIDER)
                if agent is None:
                    agent = config.get("default_agent")
        except Exception:
            pass

    # Final fallbacks
    if model is None:
        model = DEFAULT_MODEL
    if provider is None:
        provider = DEFAULT_PROVIDER

    # Session management (Claude-inspired feature)
    session_manager = SessionManager()
    chat_history = []

    if continue_session and not new_session:
        # Continue the last session
        last_session = session_manager.get_last_session()
        if last_session:
            get_log_console(verbose).print(
                f"[dim]Continuing session: {last_session.session_id}[/dim]"
            )
            chat_history = session_manager.get_conversation_context()
            # Use session's model/provider if not overridden
            if model == DEFAULT_MODEL:
                model = last_session.model
            if provider == DEFAULT_PROVIDER:
                provider = last_session.provider
    elif session and not new_session:
        # Load specific session
        loaded_session = session_manager.load_session(session)
        if loaded_session:
            get_log_console(verbose).print(f"[dim]Loaded session: {session}[/dim]")
            chat_history = session_manager.get_conversation_context()
            # Use session's model/provider if not overridden
            if model == DEFAULT_MODEL:
                model = loaded_session.model
            if provider == DEFAULT_PROVIDER:
                provider = loaded_session.provider
        else:
            get_log_console(verbose).print(
                f"[yellow]Warning: Session '{session}' not found, starting new session[/yellow]"
            )

    if save and session_manager.current_session is None:
        # Create new session if saving and no session loaded
        session_manager.create_session(provider, model)

    # Parse output format early to control all output
    format_type = OutputFormat.from_string(output_format)

    # Check if this is a command syntax
    command_name, arguments = parse_command_syntax(prompt)

    if command_name:
        # Load and execute command
        from .modules.config_manager import get_config_manager
        from .modules.user_tools import get_allowed_tools
        config = get_config_manager().config
        allowed_tools = get_allowed_tools()
        loader = CommandLoader(
            enable_command_eval=config.enable_command_eval,
            allowed_tools=allowed_tools,
        )
        final_prompt = loader.execute_command(command_name, arguments)

        if final_prompt is None:
            if format_type == OutputFormat.JSON:
                console.print(
                    json.dumps(
                        {
                            "success": False,
                            "error": f"Command '/{command_name}' not found",
                        }
                    )
                )
            else:
                get_log_console(verbose).print(
                    f"[red]Command '/{command_name}' not found.[/red]"
                )
                get_log_console(verbose).print(
                    "[dim]Available commands can be listed with: askgpt commands list[/dim]"
                )
            sys.exit(1)

        # Check for permission errors
        if final_prompt.startswith("[Error:"):
            error_msg = final_prompt[7:-1] if final_prompt.endswith("]") else final_prompt[7:]
            if format_type == OutputFormat.JSON:
                console.print(
                    json.dumps(
                        {
                            "success": False,
                            "error": error_msg,
                        }
                    )
                )
            else:
                get_log_console(verbose).print(
                    f"[red]Command execution failed: {error_msg}[/red]"
                )
            sys.exit(1)

        # Only show panel in rich mode and verbose
        if format_type == OutputFormat.RICH and verbose:
            get_log_console(verbose).print(
                Panel(
                    f"[cyan]Running Command: /{command_name}[/cyan]\n"
                    f"Arguments: {arguments if arguments else '(none)'}\n"
                    f"Model: {model}\n"
                    f"Provider: {provider}",
                    expand=False,
                )
            )
    else:
        final_prompt = prompt
        # Only show panel in rich mode and verbose
        if format_type == OutputFormat.RICH and verbose:
            get_log_console(verbose).print(
                Panel(
                    f"[cyan]Running askGPT[/cyan]\nModel: {model}\nProvider: {provider}",
                    expand=False,
                )
            )

    # Only show prompt in rich mode and verbose
    if format_type == OutputFormat.RICH and verbose:
        get_log_console(verbose).print(f"\n[yellow]Prompt:[/yellow] {final_prompt}\n")

    # Handle tool call limits
    if unlimited_tool_calls:
        max_tool_calls_value = -1
    elif max_tool_calls is not None:
        max_tool_calls_value = max_tool_calls
    else:
        max_tool_calls_value = None  # Use default

    # Create request with the final prompt (either direct or from command)
    request = PromptNanoAgentRequest(
        agentic_prompt=final_prompt,
        model=model,
        provider=provider,
        agent_name=agent,
        api_base=api_base,
        api_key=api_key,
        chat_history=chat_history if chat_history else None,
        temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
        max_tokens=max_tokens if max_tokens is not None else MAX_TOKENS,
        enable_trace=enable_trace,
        read_only=read_only,
        max_tool_calls=max_tool_calls_value,
        dev_mode=dev,
    )

    # Disable rich logging for simple/json formats
    enable_rich = format_type == OutputFormat.RICH

    # Execute agent without progress spinner (rich logging will show progress)
    response = _execute_nano_agent(
        request, enable_rich_logging=enable_rich, verbose=verbose
    )

    # Create console with specified width if provided
    output_console = Console(width=panel_width) if panel_width else console

    # Create formatter based on output format
    formatter = create_formatter(
        format_type,
        show_billing=billing,
        verbose=verbose,
        show_thinking=output_thinking,
        console=output_console,
    )

    # Convert response to AgentResponse format
    agent_response = AgentResponse(
        success=response.success,
        message="Agent completed successfully" if response.success else "Agent failed",
        data=response.result if response.success else None,
        error=response.error if not response.success else None,
        metadata=response.metadata,
        execution_time=response.execution_time_seconds,
        session_id=session_manager.current_session.session_id
        if session_manager.current_session
        else None,
    )

    # Extract billing information if available
    if response.metadata and "token_usage" in response.metadata:
        usage = response.metadata["token_usage"]
        agent_response.billing = BillingInfo(
            total_tokens=usage.get("total_tokens", 0),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cached_tokens=usage.get("cached_tokens", 0),
            total_cost=usage.get("total_cost", 0.0),
            input_cost=usage.get("input_cost", 0.0),
            output_cost=usage.get("output_cost", 0.0),
            cached_savings=usage.get("cached_savings", 0.0),
        )

    # Format and display the response
    output = formatter.format_response(agent_response)
    if output:  # SimpleFormatter and JSONFormatter return strings
        console.print(output)

    # Save to session if enabled
    if response.success and save and session_manager.current_session:
        session_manager.add_exchange(final_prompt, response.result, response.metadata)
        if (
            format_type == OutputFormat.RICH and verbose
        ):  # Only show session info in rich mode and verbose
            get_log_console(verbose).print(
                f"[dim]Session saved: {session_manager.current_session.session_id}[/dim]"
            )

    # Only show additional metadata panel if verbose AND using rich format
    if verbose and format_type == OutputFormat.RICH:
        # Format metadata as a single JSON object
        metadata_display = response.metadata.copy() if response.metadata else {}

        # Remove token usage from metadata if already shown via billing
        if "token_usage" in metadata_display and billing:
            del metadata_display["token_usage"]

        # Only show metadata panel if there's something to show
        if metadata_display:
            # Pretty print the combined metadata
            metadata_json = json.dumps(metadata_display, indent=2)

            get_log_console(verbose).print(
                Panel(
                    Syntax(metadata_json, "json", theme="monokai", line_numbers=False),
                    title="🔍 Additional Metadata",
                    border_style="dim",
                    expand=False,
                )
            )


def _run_interactive_default(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    agent: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    simple: bool = False,
    enable_trace: bool = False,
    verbose: bool = False,
    read_only: bool = False,
):
    """Run interactive mode (internal helper for main callback)."""
    # Determine provider first before checking API key
    if provider is None:
        config_file = Path.home() / ".askgpt" / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    provider = config.get("default_provider", DEFAULT_PROVIDER)
            except Exception:
                provider = DEFAULT_PROVIDER
        else:
            provider = DEFAULT_PROVIDER

    check_api_key(provider)

    # Load config defaults if not specified
    config_file = Path.home() / ".askgpt" / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                if model is None:
                    model = config.get("default_model", DEFAULT_MODEL)
                if provider is None:
                    provider = config.get("default_provider", DEFAULT_PROVIDER)
                if agent is None:
                    agent = config.get("default_agent")
        except Exception:
            pass

    # Final fallbacks
    if model is None:
        model = DEFAULT_MODEL
    if provider is None:
        provider = DEFAULT_PROVIDER

    # Use simple mode if requested or if prompt_toolkit is not available
    if simple:
        _run_simple_interactive(model, provider, verbose, api_base, api_key, read_only)
    else:
        try:
            from .modules.interactive_mode import InteractiveSession

            session = InteractiveSession(
                initial_model=model,
                initial_provider=provider,
                initial_agent=agent,
                api_base=api_base,
                api_key=api_key,
                enable_trace=enable_trace,
                read_only=read_only,
            )
            session.run()
        except ImportError:
            (console_stderr if verbose else console).print(
                "[yellow]Enhanced interactive mode not available. Install with: uv sync[/yellow]"
            )
            (console_stderr if verbose else console).print(
                "[dim]Falling back to simple mode...[/dim]\n"
            )
            _run_simple_interactive(model, provider, verbose, api_base, api_key, read_only)


def check_api_key(provider: str = None):
    """Check if required API key is set based on provider."""
    # If no provider specified, try to determine from context
    if provider is None:
        provider = DEFAULT_PROVIDER

    # Only check API keys for providers that require them
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            console_stderr.print(
                "[red]Error: OPENAI_API_KEY environment variable is not set[/red]"
            )
            console_stderr.print(
                "Please set it with: export OPENAI_API_KEY=your-api-key"
            )
            sys.exit(1)
    elif provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            console_stderr.print(
                "[red]Error: ANTHROPIC_API_KEY environment variable is not set[/red]"
            )
            console_stderr.print(
                "Please set it with: export ANTHROPIC_API_KEY=your-api-key"
            )
            sys.exit(1)
    # Ollama, ollama-native, and lmstudio don't require API keys by default
    # They may use them for authentication but it's optional


@app.command()
def test_tools():
    """Test individual tool functions."""
    # Import the raw tool functions from nano_agent_tools
    from .modules.nano_agent_tools import (edit_file_raw, get_file_info_raw,
                                           list_directory_raw, read_file_raw,
                                           write_file_raw, grep_search_raw, search_files_raw, bash_command_raw)

    console.print(Panel("[cyan]Testing askGPT Tools[/cyan]", expand=False))

    # Test list_directory (call the raw function, not the FunctionTool)
    console.print("\n[yellow]1. Testing list_directory:[/yellow]")
    result = list_directory_raw(".")
    console.print(result[:500] + "..." if len(result) > 500 else result)

    # Test write_file
    console.print("\n[yellow]2. Testing write_file:[/yellow]")
    test_file = "test_nano_agent.txt"
    result = write_file_raw(
        test_file, "Hello from askGPT!\nThis is line 2\nThis is line 3"
    )
    console.print(result)

    # Test read_file
    console.print("\n[yellow]3. Testing read_file:[/yellow]")
    result = read_file_raw(test_file)
    console.print(f"Content: {result}")

    # Test grep_search
    console.print("\n[yellow]4. Testing grep_search:[/yellow]")
    result = grep_search_raw("This is line 2", "*.txt")
    console.print(f"Search result: {result}")

    # Test search_files
    console.print("\n[yellow]5. Testing search_files:[/yellow]")
    result = search_files_raw("test_nano_agent")
    console.print(f"Search result: {result}")

    # Test bash_command
    console.print("\n[yellow]6. Testing bash_command:[/yellow]")
    result = bash_command_raw("ls -l")
    console.print(f"Command result: {result}")

    # Test edit_file
    console.print("\n[yellow]4. Testing edit_file:[/yellow]")
    result = edit_file_raw(test_file, "This is line 2", "This is the EDITED line 2")
    console.print(f"Edit result: {result}")
    result = read_file_raw(test_file)
    console.print(f"Content after edit: {result}")

    # Test get_file_info
    console.print("\n[yellow]5. Testing get_file_info:[/yellow]")
    result = get_file_info_raw(test_file)
    info = json.loads(result)
    console.print(json.dumps(info, indent=2))

    # Clean up
    Path(test_file).unlink(missing_ok=True)
    console.print("\n[green]✓ All tool tests completed successfully![/green]")


@app.command(hidden=True)
def run(
    prompt: str,
    model: str = typer.Option(None, help="Model to use"),
    provider: str = typer.Option(None, help="Provider to use"),
    agent: str = typer.Option(None, help="Agent personality to use"),
    api_base: str = typer.Option(
        None, help="API base URL (overrides environment variables)"
    ),
    api_key: str = typer.Option(None, help="API key (overrides environment variables)"),
    verbose: bool = typer.Option(False, help="Show detailed output"),
    read_only: bool = typer.Option(
        False, "--read-only", help="Disable file system modifications (safe exploration mode)"
    ),
    max_tool_calls: Optional[int] = typer.Option(
        None, "--max-tool-calls", help="Maximum number of tool calls allowed (default: 20)"
    ),
    unlimited_tool_calls: bool = typer.Option(
        False, "--unlimited-tool-calls", help="Allow unlimited tool calls (use with caution)"
    ),
    # Claude-inspired options
    continue_session: bool = typer.Option(
        False, "--continue", "-c", help="Continue the last session"
    ),
    session: str = typer.Option(
        None, "--session", "-s", help="Use a specific session ID"
    ),
    new_session: bool = typer.Option(False, "--new", "-n", help="Force a new session"),
    temperature: float = typer.Option(
        None, "--temperature", "-t", help="Model temperature (0.0-2.0)"
    ),
    max_tokens: int = typer.Option(
        None, "--max-tokens", help="Maximum response tokens"
    ),
    save: bool = typer.Option(
        True, "--save/--no-save", help="Save conversation to session history"
    ),
    enable_trace: bool = typer.Option(
        False, "--enable-trace", help="Enable OpenAI agent tracing"
    ),
    # New output control options
    billing: bool = typer.Option(
        False, "--billing", help="Show token usage and cost information"
    ),
    output_format: str = typer.Option(
        "simple",
        "--output-format",
        "-f",
        help="Output format: simple (default), json, or rich",
    ),
    output_thinking: bool = typer.Option(
        False, "--output-thinking", help="Show agent thinking and reasoning text"
    ),
    panel_width: Optional[int] = typer.Option(
        None,
        "--panel-width",
        help="Maximum width for rich output panels (default: auto-detect)",
    ),
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Development mode - show detailed error messages for debugging",
    ),
):
    """[Alternative] Run askGPT with a prompt. Supports /command syntax for command files.

    NOTE: The recommended way is to use 'askgpt -p "prompt"' or 'askgpt --prompt "prompt"'.
    This command is kept for backward compatibility.
    """
    _run_prompt(
        prompt=prompt,
        model=model,
        provider=provider,
        agent=agent,
        api_base=api_base,
        api_key=api_key,
        verbose=verbose,
        read_only=read_only,
        max_tool_calls=max_tool_calls,
        unlimited_tool_calls=unlimited_tool_calls,
        continue_session=continue_session,
        session=session,
        new_session=new_session,
        temperature=temperature,
        max_tokens=max_tokens,
        save=save,
        enable_trace=enable_trace,
        billing=billing,
        output_format=output_format,
        output_thinking=output_thinking,
        panel_width=panel_width,
        dev=dev,
    )


@app.command()
def sessions(
    action: str = typer.Argument("list", help="Action to perform: list, show, clear"),
    session_id: str = typer.Option(None, "--id", help="Session ID for 'show' action"),
    days: int = typer.Option(30, "--days", help="Days to keep for 'clear' action"),
):
    """Manage conversation sessions (Claude-inspired feature)."""
    session_manager = SessionManager()

    if action == "list":
        # List recent sessions
        sessions = session_manager.get_recent_sessions(limit=20)
        if not sessions:
            console.print("[yellow]No sessions found.[/yellow]")
            return

        table = Table(title="Recent Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Created", style="green")
        table.add_column("Last Updated", style="yellow")
        table.add_column("Provider/Model", style="magenta")
        table.add_column("Messages", style="blue")

        for session in sessions:
            created = (
                session["created_at"].split("T")[0]
                if "T" in session["created_at"]
                else session["created_at"]
            )
            updated = (
                session["last_updated"].split("T")[0]
                if "T" in session["last_updated"]
                else session["last_updated"]
            )
            model_info = f"{session['provider']}/{session['model']}"
            table.add_row(
                session["session_id"],
                created,
                updated,
                model_info,
                str(session.get("message_count", 0)),
            )

        console.print(table)
        console.print(
            "\n[dim]Use 'askgpt run --continue' to resume the last session[/dim]"
        )
        console.print(
            "[dim]Use 'askgpt sessions show --id <session_id>' to view a specific session[/dim]"
        )

    elif action == "show":
        # Show a specific session
        if not session_id:
            console.print("[red]Error: --id required for 'show' action[/red]")
            return

        session = session_manager.load_session(session_id)
        if not session:
            console.print(f"[red]Session '{session_id}' not found[/red]")
            return

        console.print(
            Panel(
                f"[cyan]Session: {session.session_id}[/cyan]\n"
                f"Created: {session.created_at}\n"
                f"Provider: {session.provider} | Model: {session.model}\n"
                f"Messages: {len(session.conversation)}",
                title="Session Details",
                expand=False,
            )
        )

        # Display conversation history
        for msg in session.conversation:
            if msg.role == "user":
                console.print("\n[blue]👤 User:[/blue]")
                console.print(
                    msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                )
            elif msg.role == "assistant":
                console.print("\n[green]🤖 Assistant:[/green]")
                console.print(
                    msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                )

    elif action == "clear":
        # Clear old sessions
        deleted = session_manager.clear_old_sessions(days=days)
        console.print(
            f"[green]Cleared {deleted} sessions older than {days} days[/green]"
        )

    else:
        console_stderr.print(f"[red]Unknown action: {action}[/red]")
        console_stderr.print("Available actions: list, show, clear")


@app.command()
def demo():
    """Run a demo showing various agent capabilities."""
    check_api_key(DEFAULT_PROVIDER)

    console.print(Panel("[cyan]askGPT Demo[/cyan]", expand=False))

    for i, (prompt, model) in enumerate(DEMO_PROMPTS, 1):
        console.print(f"\n[yellow]Demo {i}:[/yellow] {prompt}")

        request = PromptNanoAgentRequest(
            agentic_prompt=prompt, model=model, provider=DEFAULT_PROVIDER
        )

        # Execute without progress spinner
        response = _execute_nano_agent(request)

        if response.success:
            console.print(f"[green]✓[/green] {response.result[:200]}...")
        else:
            console.print(f"[red]✗[/red] {response.error}")

    # Clean up
    Path("demo.txt").unlink(missing_ok=True)
    console.print("\n[green]✓ Demo completed![/green]")


@app.command(hidden=True)
def interactive(
    model: str = typer.Option(None, help="Initial model to use"),
    provider: str = typer.Option(None, help="Initial provider to use"),
    agent: str = typer.Option(None, help="Initial agent personality to use"),
    api_base: str = typer.Option(
        None, help="API base URL (overrides environment variables)"
    ),
    api_key: str = typer.Option(None, help="API key (overrides environment variables)"),
    simple: bool = typer.Option(False, help="Use simple mode without autocompletion"),
    enable_trace: bool = typer.Option(
        False, "--enable-trace", help="Enable OpenAI agent tracing"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    read_only: bool = typer.Option(
        False, "--read-only", help="Disable file system modifications (safe exploration mode)"
    ),
):
    """[Alternative] Run the agent in enhanced interactive mode with autocompletion.

    NOTE: You can also just run 'askgpt' without any arguments to enter interactive mode.
    This command allows you to specify initial configuration options.
    """
    # Determine provider first before checking API key
    if provider is None:
        config_file = Path.home() / ".askgpt" / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    provider = config.get("default_provider", DEFAULT_PROVIDER)
            except Exception:
                provider = DEFAULT_PROVIDER
        else:
            provider = DEFAULT_PROVIDER

    check_api_key(provider)

    # Load config defaults if not specified
    config_file = Path.home() / ".askgpt" / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                if model is None:
                    model = config.get("default_model", DEFAULT_MODEL)
                if provider is None:
                    provider = config.get("default_provider", DEFAULT_PROVIDER)
                if agent is None:
                    agent = config.get("default_agent")
        except Exception:
            pass

    # Final fallbacks
    if model is None:
        model = DEFAULT_MODEL
    if provider is None:
        provider = DEFAULT_PROVIDER

    # Use simple mode if requested or if prompt_toolkit is not available
    if simple:
        _run_simple_interactive(model, provider, verbose, api_base, api_key, read_only)
    else:
        try:
            from .modules.interactive_mode import InteractiveSession

            session = InteractiveSession(
                initial_model=model,
                initial_provider=provider,
                initial_agent=agent,
                api_base=api_base,
                api_key=api_key,
                enable_trace=enable_trace,
                read_only=read_only,
            )
            session.run()
        except ImportError:
            (console_stderr if verbose else console).print(
                "[yellow]Enhanced interactive mode not available. Install with: uv sync[/yellow]"
            )
            (console_stderr if verbose else console).print(
                "[dim]Falling back to simple mode...[/dim]\n"
            )
            _run_simple_interactive(model, provider, verbose, api_base, api_key, read_only)


def _run_simple_interactive(
    model: str,
    provider: str,
    verbose: bool = False,
    api_base: str = None,
    api_key: str = None,
    read_only: bool = False,
):
    """Run simple interactive mode without autocompletion."""
    mode_text = "[cyan]askGPT Interactive Mode (Simple)[/cyan]"
    if read_only:
        mode_text += "\n[yellow]🔒 Read-Only Mode - File modifications disabled[/yellow]"
    mode_text += "\nType 'exit' to quit"
    
    (console_stderr if verbose else console).print(
        Panel(
            mode_text,
            expand=False,
        )
    )

    from .modules.config_manager import get_config_manager
    from .modules.user_tools import get_allowed_tools
    config = get_config_manager().config
    allowed_tools = get_allowed_tools()
    loader = CommandLoader(
        enable_command_eval=config.enable_command_eval,
        allowed_tools=allowed_tools,
    )

    while True:
        try:
            prompt = typer.prompt("\n[yellow]Enter prompt[/yellow]")

            if prompt.lower() in ["exit", "quit", "q"]:
                (console_stderr if verbose else console).print("[dim]Goodbye![/dim]")
                break

            # Handle special commands (both slash and non-slash)
            if prompt.lower() in ["help", "/help"]:
                (console_stderr if verbose else console).print(
                    "[cyan]Built-in Commands:[/cyan]"
                )
                (console_stderr if verbose else console).print(
                    "  /help           - Show this help"
                )
                (console_stderr if verbose else console).print(
                    "  /commands       - List available command files"
                )
                (console_stderr if verbose else console).print(
                    "  /clear          - Clear the screen"
                )
                (console_stderr if verbose else console).print(
                    "  /<command> args - Run a command file"
                )
                (console_stderr if verbose else console).print("")
                (console_stderr if verbose else console).print(
                    "[cyan]Shell Commands:[/cyan]"
                )
                (console_stderr if verbose else console).print(
                    "  !<command>      - Execute shell command (e.g., !ls)"
                )
                (console_stderr if verbose else console).print("")
                (console_stderr if verbose else console).print(
                    "[cyan]Other Commands:[/cyan]"
                )
                (console_stderr if verbose else console).print(
                    "  exit/quit/q     - Exit interactive mode"
                )
                (console_stderr if verbose else console).print("")
                (console_stderr if verbose else console).print(
                    "[dim]Type any text to send directly to the agent[/dim]"
                )
                continue

            if prompt.lower() in ["commands", "/commands"]:
                loader.display_commands_table()
                continue

            # Handle /commands show
            if prompt.lower().startswith(
                "/commands show "
            ) or prompt.lower().startswith("commands show "):
                parts = prompt.split()
                if len(parts) >= 3:
                    cmd_to_show = parts[2]
                    if cmd_to_show.startswith("/"):
                        cmd_to_show = cmd_to_show[1:]

                    command = loader.load_command(cmd_to_show)
                    if command:
                        try:
                            content = command.path.read_text()
                            console.print(
                                Panel(
                                    content,
                                    title=f"📋 Command File: /{command.name}",
                                    subtitle=str(command.path),
                                    border_style="cyan",
                                    expand=False,
                                )
                            )
                        except Exception as e:
                            console.print(f"[red]Error reading command file: {e}[/red]")
                    else:
                        console.print(f"[red]Command '{cmd_to_show}' not found.[/red]")
                else:
                    console.print(
                        "[yellow]Usage: /commands show <command_name>[/yellow]"
                    )
                continue

            if prompt.lower() in ["clear", "/clear"]:
                console.clear()
                continue

            # Handle shell commands with ! prefix
            if prompt.startswith("!"):
                shell_cmd = prompt[1:].strip()
                if shell_cmd:
                    user_shell = os.environ.get("SHELL", "/bin/bash")
                    (console_stderr if verbose else console).print(
                        f"[dim]Executing: {shell_cmd} (using {user_shell})[/dim]"
                    )
                    try:
                        import subprocess

                        result = subprocess.run(
                            [user_shell, "-c", shell_cmd],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        if result.stdout:
                            console.print("[green]Output:[/green]")
                            console.print(result.stdout)
                        if result.stderr:
                            console.print("[yellow]Error output:[/yellow]")
                            console.print(result.stderr)
                        (console_stderr if verbose else console).print(
                            f"[dim]Exit code: {result.returncode}[/dim]"
                        )
                    except subprocess.TimeoutExpired:
                        (console_stderr if verbose else console).print(
                            "[red]Command timed out after 30 seconds[/red]"
                        )
                    except Exception as e:
                        (console_stderr if verbose else console).print(
                            f"[red]Error: {e}[/red]"
                        )
                else:
                    (console_stderr if verbose else console).print(
                        "[yellow]Usage: !<shell command>[/yellow]"
                    )
                continue

            # Check for /command syntax
            command_name, arguments = parse_command_syntax(prompt)

            if command_name:
                final_prompt = loader.execute_command(command_name, arguments)
                if final_prompt is None:
                    (console_stderr if verbose else console).print(
                        f"[red]Command '/{command_name}' not found.[/red]"
                    )
                    continue
                (console_stderr if verbose else console).print(
                    f"[dim]Using command: /{command_name}[/dim]"
                )
            else:
                final_prompt = prompt

            request = PromptNanoAgentRequest(
                agentic_prompt=final_prompt,
                model=model,
                provider=provider,
                api_base=api_base,
                api_key=api_key,
                read_only=read_only,
            )

            # Execute without progress spinner
            response = _execute_nano_agent(request)

            if response.success:
                console.print(
                    Panel(
                        response.result,
                        title="💬 Agent Response",
                        border_style="cyan",
                        expand=False,
                    )
                )
            else:
                console.print(
                    Panel(
                        response.error,
                        title="❌ Error",
                        border_style="red",
                        expand=False,
                    )
                )

        except KeyboardInterrupt:
            (console_stderr if verbose else console).print(
                "\n[dim]Interrupted. Type 'exit' to quit.[/dim]"
            )
        except Exception as e:
            (console_stderr if verbose else console).print(
                f"\n[red]Error:[/red] {str(e)}"
            )


@app.command("list-models")
def list_models(
    provider: str = typer.Option(
        None, "--provider", "-p", help="List models from a specific provider"
    ),
    all_providers: bool = typer.Option(
        False, "--all", "-a", help="List models from all providers"
    ),
    format_type: str = typer.Option(
        "table", "--format", "-f", help="Output format: table or json"
    ),
    capability: str = typer.Option(
        None, "--capability", "-c", help="Filter models by capability"
    ),
    show_deprecated: bool = typer.Option(
        False, "--show-deprecated", help="Include deprecated models"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed information"
    ),
):
    """List available models from AI providers."""
    import json

    from rich.table import Table

    from .modules.model_providers import ProviderRegistry
    from .modules.provider_implementations import initialize_providers

    # Initialize providers
    initialize_providers()

    # Get registry instance
    registry = ProviderRegistry()

    async def fetch_models():
        """Fetch models based on parameters."""
        if all_providers:
            return await registry.list_all_models()
        elif provider:
            return await registry.list_provider_models(provider)
        else:
            # Default to listing from all providers
            return await registry.list_all_models()

    try:
        # Fetch models
        models = asyncio.run(fetch_models())

        # Filter by capability if specified
        if capability:
            models = [m for m in models if capability in m.capabilities]

        # Filter out deprecated models unless requested
        if not show_deprecated:
            models = [m for m in models if not m.deprecated]

        # Format output
        if format_type == "json":
            # JSON output
            output = [
                {
                    "id": m.id,
                    "name": m.name,
                    "provider": m.provider,
                    "context_length": m.context_length,
                    "capabilities": m.capabilities,
                    "deprecated": m.deprecated,
                    "replacement_model": m.replacement_model,
                }
                for m in models
            ]
            console.print(json.dumps(output, indent=2))
        else:
            # Table output
            if not models:
                console.print("[yellow]No models found matching the criteria.[/yellow]")
                return

            table = Table(title="Available Models")
            table.add_column("Provider", style="cyan")
            table.add_column("Model ID", style="green")
            table.add_column("Name", style="white")

            if verbose:
                table.add_column("Context", style="yellow")
                table.add_column("Capabilities", style="blue")

            if show_deprecated:
                table.add_column("Status", style="red")

            for model in models:
                row = [model.provider, model.id, model.name or model.id]

                if verbose:
                    context = (
                        f"{model.context_length:,}" if model.context_length else "N/A"
                    )
                    capabilities = (
                        ", ".join(model.capabilities) if model.capabilities else "N/A"
                    )
                    row.extend([context, capabilities])

                if show_deprecated:
                    status = "DEPRECATED" if model.deprecated else "Active"
                    row.append(status)

                table.add_row(*row)

            console.print(table)

            # Show summary
            provider_counts = {}
            for m in models:
                provider_counts[m.provider] = provider_counts.get(m.provider, 0) + 1

            if verbose:
                console.print(f"\n[dim]Total models: {len(models)}[/dim]")
                for p, count in provider_counts.items():
                    console.print(f"[dim]  {p}: {count} models[/dim]")

    except Exception as e:
        from .modules.model_providers import (ProviderAuthenticationError,
                                              ProviderConnectionError,
                                              ProviderNotFoundError)

        if isinstance(e, ProviderNotFoundError):
            console.print(f"[red]Error: Provider '{e.provider_name}' not found[/red]")
            console.print(
                "[dim]Available providers: openai, anthropic, ollama, lmstudio[/dim]"
            )
        elif isinstance(e, ProviderConnectionError):
            console.print(f"[red]Error: Could not connect to {e.provider}[/red]")
            console.print(f"[dim]{str(e)}[/dim]")
        elif isinstance(e, ProviderAuthenticationError):
            console.print(f"[red]Error: Authentication failed for {e.provider}[/red]")
            console.print(f"[dim]{str(e)}[/dim]")
        else:
            console.print(f"[red]Error: {str(e)}[/red]")
            if verbose:
                import traceback

                console.print(f"[dim]{traceback.format_exc()}[/dim]")

        sys.exit(1)


# Create a sub-app for command management
commands_app = typer.Typer()
app.add_typer(commands_app, name="commands", help="Manage askgpt command files")

skills_app = typer.Typer()
app.add_typer(skills_app, name="skills", help="Manage Agent Skills")


@commands_app.command("list")
def list_commands():
    """List all available command files."""
    from .modules.config_manager import get_config_manager
    from .modules.user_tools import get_allowed_tools
    config = get_config_manager().config
    allowed_tools = get_allowed_tools()
    loader = CommandLoader(
        enable_command_eval=config.enable_command_eval,
        allowed_tools=allowed_tools,
    )
    loader.display_commands_table()


@commands_app.command("create")
def create_command(
    name: str = typer.Argument(..., help="Name of the command to create"),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing command"
    ),
):
    """Create a new command template file."""
    from .modules.config_manager import get_config_manager
    from .modules.user_tools import get_allowed_tools
    config = get_config_manager().config
    allowed_tools = get_allowed_tools()
    loader = CommandLoader(
        enable_command_eval=config.enable_command_eval,
        allowed_tools=allowed_tools,
    )
    success = loader.create_command_template(name, overwrite)
    if not success:
        sys.exit(1)


@commands_app.command("show")
def show_command(name: str = typer.Argument(..., help="Name of the command to show")):
    """Show the content of a command file."""
    from .modules.config_manager import get_config_manager
    from .modules.user_tools import get_allowed_tools
    config = get_config_manager().config
    allowed_tools = get_allowed_tools()
    loader = CommandLoader(
        enable_command_eval=config.enable_command_eval,
        allowed_tools=allowed_tools,
    )
    command = loader.load_command(name)

    if command is None:
        console.print(f"[red]Command '{name}' not found.[/red]")
        sys.exit(1)

    console.print(
        Panel(
            f"[green]{command.description}[/green]",
            title=f"📋 Command: /{command.name}",
            border_style="cyan",
        )
    )

    console.print("\n[yellow]Prompt Template:[/yellow]")
    console.print(Panel(command.prompt_template, border_style="dim"))

    if command.metadata:
        console.print("\n[yellow]Metadata:[/yellow]")
        for key, value in command.metadata.items():
            console.print(f"  {key}: {value}")

    console.print(f"\n[dim]File: {command.path}[/dim]")
    console.print(f'[dim]Usage: askgpt /{command.name} "arguments"[/dim]')


@commands_app.command("edit")
def edit_command(name: str = typer.Argument(..., help="Name of the command to edit")):
    """Open a command file in the default editor."""
    from .modules.config_manager import get_config_manager
    from .modules.user_tools import get_allowed_tools
    config = get_config_manager().config
    allowed_tools = get_allowed_tools()
    loader = CommandLoader(
        enable_command_eval=config.enable_command_eval,
        allowed_tools=allowed_tools,
    )
    command = loader.load_command(name)

    if command is None:
        console.print(f"[red]Command '{name}' not found.[/red]")
        console.print(f"[dim]Create it with: askgpt commands create {name}[/dim]")
        sys.exit(1)

    # Try to open in default editor
    import platform
    import subprocess

    if platform.system() == "Windows":
        os.startfile(command.path)
    elif platform.system() == "Darwin":  # macOS
        subprocess.call(["open", command.path])
    else:  # Linux and others
        # Try common editors in order of preference
        editors = ["nano", "vim", "vi", "emacs"]
        editor = os.environ.get("EDITOR")

        if editor:
            subprocess.call([editor, command.path])
        else:
            for ed in editors:
                if subprocess.call(["which", ed], stdout=subprocess.DEVNULL) == 0:
                    subprocess.call([ed, command.path])
                    break
            else:
                console.print(
                    f"[yellow]No editor found. Please edit manually: {command.path}[/yellow]"
                )


# Skills commands
@skills_app.command("list")
def list_skills():
    """List all available Agent Skills."""
    from .modules.skill_loader import SkillLoader
    from .modules.user_tools import get_allowed_tools
    from rich.table import Table

    # Get allowed_tools from configuration
    allowed_tools = get_allowed_tools()
    skill_loader = SkillLoader(allowed_tools=allowed_tools)
    skills = skill_loader.list_skills()

    if not skills:
        console.print(
            Panel(
                "[yellow]No skills found.[/yellow]\n\n"
                "Create your first skill with:\n"
                "  askgpt skills create <name>\n\n"
                "Skills directories:\n"
                f"  Global: {skill_loader.global_skills_dir}\n"
                f"  Project: {skill_loader.project_skills_dir}",
                title="📚 Agent Skills",
                border_style="yellow",
            )
        )
        return

    table = Table(title="Available Skills", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Status", style="cyan", no_wrap=True)
    table.add_column("Source", style="blue", no_wrap=True)
    table.add_column("Resources", style="magenta", no_wrap=True)

    for skill in skills:
        # Truncate long descriptions
        desc = skill.description
        if len(desc) > 60:
            desc = desc[:60] + "..."

        # Status column
        if skill.enabled:
            status = "[green]✓ Enabled[/green]"
        else:
            reason = skill.disabled_reason or "Disabled"
            status = f"[red]✗ Disabled[/red]\n[dim]{reason[:40]}...[/dim]" if len(reason) > 40 else f"[red]✗ {reason}[/red]"

        table.add_row(
            skill.name,
            desc,
            status,
            skill.source,
            str(len(skill.resources)),
        )

    console.print(table)

    # Show summary
    global_count = sum(1 for s in skills if s.source == "global")
    project_count = sum(1 for s in skills if s.source == "project")
    enabled_count = sum(1 for s in skills if s.enabled)
    disabled_count = len(skills) - enabled_count

    console.print(
        f"\n[dim]Total: {len(skills)} skills "
        f"({enabled_count} enabled, {disabled_count} disabled, "
        f"{global_count} global, {project_count} project)[/dim]"
    )
    console.print(f"[dim]Global directory: {skill_loader.global_skills_dir}[/dim]")
    console.print(f"[dim]Project directory: {skill_loader.project_skills_dir}[/dim]")


@skills_app.command("show")
def show_skill(name: str = typer.Argument(..., help="Name of the skill to show")):
    """Show detailed information about a skill."""
    from .modules.skill_loader import SkillLoader
    from .modules.user_tools import get_allowed_tools

    # Get allowed_tools from configuration
    allowed_tools = get_allowed_tools()
    skill_loader = SkillLoader(allowed_tools=allowed_tools)
    skill = skill_loader.get_skill(name)

    if skill is None:
        console.print(f"[red]Skill '{name}' not found.[/red]")
        console.print(f"[dim]Create it with: askgpt skills create {name}[/dim]")
        sys.exit(1)

    # Load Level 2 instructions
    instructions = skill_loader.load_skill_instructions(name)

    # Show enabled/disabled status
    if skill.enabled:
        status_text = "[green]✓ Enabled[/green]"
    else:
        status_text = f"[red]✗ Disabled[/red]"
        if skill.disabled_reason:
            status_text += f" - {skill.disabled_reason}"

    console.print(
        Panel(
            f"[green]{skill.description}[/green]\n\n{status_text}",
            title=f"📚 Skill: {skill.name}",
            border_style="cyan",
        )
    )

    console.print("\n[yellow]Metadata:[/yellow]")
    console.print(f"  Source: {skill.source}")
    console.print(f"  Path: {skill.path}")
    console.print(f"  Skill File: {skill.skill_file}")
    console.print(f"  Resources: {len(skill.resources)}")
    console.print(f"  Status: {'[green]Enabled[/green]' if skill.enabled else '[red]Disabled[/red]'}")

    # Show required tools if present
    if skill.required_tools:
        console.print(f"  Required Tools: {', '.join(skill.required_tools)}")

    if skill.metadata:
        for key, value in skill.metadata.items():
            if key not in ["source", "file", "directory", "tools", "required_tools"]:
                console.print(f"  {key}: {value}")

    if instructions:
        console.print("\n[yellow]Instructions:[/yellow]")
        console.print(Panel(instructions, border_style="dim"))

    if skill.resources:
        console.print("\n[yellow]Resources:[/yellow]")
        for resource in skill.resources[:10]:  # Show first 10
            console.print(f"  - {resource}")
        if len(skill.resources) > 10:
            console.print(f"  ... and {len(skill.resources) - 10} more")


@skills_app.command("create")
def create_skill(
    name: str = typer.Argument(..., help="Name of the skill to create"),
    global_skill: bool = typer.Option(
        False, "--global", "-g", help="Create in global directory (~/.askgpt/skills/)"
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing skill"
    ),
):
    """Create a new skill template directory with SKILL.md."""
    from .modules.skill_loader import SkillLoader
    from pathlib import Path

    skill_loader = SkillLoader()

    # Choose directory
    if global_skill:
        target_dir = skill_loader.global_skills_dir
        location = "global"
    else:
        target_dir = skill_loader.project_skills_dir
        location = "project"

    # Ensure directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    skill_dir = target_dir / name.lower().replace("_", "-")
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists() and not overwrite:
        console.print(
            f"[yellow]Skill '{name}' already exists in {location}. "
            f"Use --overwrite to replace.[/yellow]"
        )
        sys.exit(1)

    # Create skill directory
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Generate SKILL.md template
    skill_name_normalized = name.lower().replace("_", "-")
    template = f"""---
name: {skill_name_normalized}
description: Brief description of what this skill does and when to use it. Include keywords that will help match this skill to user prompts.
---

# {name.title().replace('_', ' ').replace('-', ' ')}

## Instructions

Clear, step-by-step guidance for the agent to follow when using this skill.

### Quick Start

Basic usage example or workflow:

```python
# Example code or commands
```

### Advanced Usage

For more complex scenarios, see [ADVANCED.md](ADVANCED.md).

## Examples

Concrete examples of when and how this skill is used.

## Notes

Additional context, requirements, or limitations.
"""

    try:
        skill_file.write_text(template, encoding="utf-8")
        console.print(
            f"[green]✓ Created {location} skill template: {skill_dir}[/green]"
        )
        console.print(f"[dim]Edit the skill: {skill_file}[/dim]")

        # Invalidate cache to force reload
        skill_loader.refresh_cache()

    except Exception as e:
        console.print(f"[red]Error creating skill template: {e}[/red]")
        sys.exit(1)


@skills_app.command("install-builtin")
def install_builtin_skills(
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing built-in skills"
    ),
    skill: Optional[str] = typer.Option(
        None, "--skill", "-s", help="Install specific skill by name"
    ),
):
    """Install built-in skills from the package."""
    from .modules.skill_loader import SkillLoader
    from rich.table import Table

    skill_loader = SkillLoader()
    builtin_skills = skill_loader.list_builtin_skills()

    if not builtin_skills:
        console.print(
            Panel(
                "[yellow]No built-in skills found in package.[/yellow]",
                title="📚 Built-in Skills",
                border_style="yellow",
            )
        )
        return

    # Filter by specific skill if requested
    skill_names = [skill] if skill else None
    if skill and skill not in builtin_skills:
        console.print(f"[red]Built-in skill '{skill}' not found.[/red]")
        console.print(f"[dim]Available skills: {', '.join(builtin_skills)}[/dim]")
        sys.exit(1)

    # Check which skills are already installed
    installed_skills = skill_loader.list_skills()
    installed_names = {s.name for s in installed_skills}

    # Install skills
    results = skill_loader.install_builtin_skills(
        overwrite=overwrite, skill_names=skill_names
    )

    # Display results
    table = Table(title="Built-in Skills Installation", show_header=True, header_style="bold cyan")
    table.add_column("Skill", style="green", no_wrap=True)
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")

    for skill_name in (skill_names or builtin_skills):
        if skill_name not in results:
            continue

        success = results[skill_name]
        was_installed = skill_name in installed_names

        if success:
            if was_installed and not overwrite:
                status = "[yellow]Skipped[/yellow]"
                details = "Already installed (use --overwrite to replace)"
            else:
                status = "[green]Installed[/green]"
                details = f"Installed to {skill_loader.global_skills_dir / skill_name}"
        else:
            if was_installed:
                status = "[yellow]Skipped[/yellow]"
                details = "Already exists (use --overwrite to replace)"
            else:
                status = "[red]Failed[/red]"
                details = "Installation failed - check logs"

        table.add_row(skill_name, status, details)

    console.print(table)

    # Summary
    installed_count = sum(1 for r in results.values() if r)
    skipped_count = sum(1 for r in results.values() if not r)
    total_count = len(results)

    console.print(
        f"\n[dim]Summary: {installed_count} installed, {skipped_count} skipped of {total_count} total[/dim]"
    )
    console.print(f"[dim]Skills location: {skill_loader.global_skills_dir}[/dim]")


@app.command("init")
def init(
    provider: str = typer.Option(
        None, "--provider", "-p", help="Set default provider (e.g., openai, anthropic, ollama)"
    ),
    model: str = typer.Option(
        None, "--model", "-m", help="Set default model (e.g., gpt-5-mini, claude-3-haiku, llama3.2:latest)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing config file"
    ),
):
    """Initialize or regenerate the askgpt configuration file.
    
    Creates ~/.config/askgpt/config.yaml with default settings.
    If the file already exists, prints the configuration to stdout instead of overwriting.
    """
    import yaml
    from pathlib import Path
    
    # Determine config directory and file path
    config_dir = Path.home() / ".config" / "askgpt"
    config_file = config_dir / "config.yaml"
    
    # Create default configuration
    default_config = {
        "default_provider": provider or "ollama",
        "default_model": model or "gpt-oss:20b",
        "providers": {
            "openai": {
                "api_base": "https://api.openai.com/v1",
                "api_key_env": "OPENAI_API_KEY",
                "known_models": [
                    "gpt-5-mini",
                    "gpt-5-nano", 
                    "gpt-5",
                    "gpt-4o",
                    "gpt-4o-mini"
                ],
                "allow_unknown_models": True
            },
            "anthropic": {
                "api_base": "https://api.anthropic.com/v1",
                "api_key_env": "ANTHROPIC_API_KEY",
                "known_models": [
                    "claude-3-haiku-20240307",
                    "claude-3-sonnet-20240229",
                    "claude-3-opus-20240229"
                ],
                "allow_unknown_models": True
            },
            "ollama": {
                "api_base": "http://localhost:11434/v1",
                "allow_unknown_models": True,
                "known_models": [
                    "gpt-oss:20b",
                    "gpt-oss:120b",
                    "llama3.2:latest",
                    "mistral:latest",
                    "qwen2.5-coder:3b"
                ]
            },
            "ollama-native": {
                "api_base": "http://localhost:11434",
                "allow_unknown_models": True
            },
            "lmstudio": {
                "api_base": "http://localhost:1234/v1",
                "allow_unknown_models": True
            }
        },
        "model_aliases": {
            "llama": "llama3.2:latest",
            "qwen": "qwen2.5-coder:3b",
            "gpt5": "gpt-5-mini",
            "claude": "claude-3-haiku-20240307"
        },
        "max_tool_calls": 20,
        "session_timeout": 1800,
        "log_level": "INFO",
        "enable_command_eval": False
    }
    
    # Check if config file exists
    if config_file.exists() and not force:
        console.print(f"[yellow]Configuration file already exists at: {config_file}[/yellow]")
        console.print("[yellow]Use --force to overwrite, or here's the configuration that would be created:[/yellow]\n")
        
        # Print the configuration to stdout in YAML format
        yaml_output = yaml.dump(default_config, default_flow_style=False, sort_keys=False)
        syntax = Syntax(yaml_output, "yaml", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title="askGPT Configuration", expand=False))
        
        console.print("\n[dim]To use this configuration, either:[/dim]")
        console.print("[dim]1. Delete the existing file and run 'askgpt init' again[/dim]")
        console.print("[dim]2. Use 'askgpt init --force' to overwrite[/dim]")
        console.print("[dim]3. Copy the above configuration manually to your config file[/dim]")
    else:
        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Write the configuration file
        with open(config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        
        console.print(f"[green]✓ Configuration file created at: {config_file}[/green]")
        
        if provider:
            console.print(f"[green]  Default provider set to: {provider}[/green]")
        if model:
            console.print(f"[green]  Default model set to: {model}[/green]")
        
        console.print("\n[dim]You can now use askgpt with your configured defaults.[/dim]")
        console.print("[dim]Edit the config file to customize providers, models, and aliases.[/dim]")
        
        # Show a hint about API keys if needed
        if provider == "openai":
            console.print("\n[yellow]Note: Remember to set OPENAI_API_KEY environment variable[/yellow]")
        elif provider == "anthropic":
            console.print("\n[yellow]Note: Remember to set ANTHROPIC_API_KEY environment variable[/yellow]")


@app.command("list-user-tools")
def list_user_tools_cmd():
    """
    List user-defined tools found in ~/.askgpt/tools.
    Shows name, type, path and optional description.
    """
    try:
        tools = list_user_tools()
        if not tools:
            console.print("[yellow]No user tools found in ~/.askgpt/tools[/yellow]")
            return
        table = Table(title="User Tools", show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Path")
        table.add_column("Description")
        for name, meta in sorted(tools.items()):
            table.add_row(name, meta.get("type") or "", meta.get("path") or "", str(meta.get("description") or ""))
        console.print(table)
    except Exception as e:
        console_stderr.print(f"[red]Error listing user tools:[/red] {e}")


@app.command("run-user-tool")
def run_user_tool_cmd(
    tool: str,
    input: Optional[str] = typer.Option(None, "--input", "-i", help="JSON input string"),
    input_file: Optional[str] = typer.Option(None, "--input-file", "-f", help="JSON input file path"),
):
    """
    Run a user-defined tool by name. Input may be provided as a JSON string or a path to a JSON file.
    """
    try:
        data = {}
        if input_file:
            data = json.loads(Path(input_file).read_text())
        elif input:
            data = json.loads(input)
    except Exception as e:
        console_stderr.print(f"[red]Failed to parse input JSON:[/red] {e}")
        raise typer.Exit(code=2)

    try:
        result = run_user_tool(tool, data)
        console.print_json(data=result)
    except KeyError:
        console_stderr.print(f"[red]Tool not found: {tool}[/red]")
        raise typer.Exit(code=3)
    except Exception as e:
        console_stderr.print(f"[red]Tool error:[/red] {e}")
        raise typer.Exit(code=4)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
