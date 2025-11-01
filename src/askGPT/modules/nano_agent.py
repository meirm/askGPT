"""
Nano Agent - MCP Server Tool with OpenAI Agent SDK.

This module implements the nano agent using OpenAI's Agent SDK for
autonomous task execution with file system tools.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# OpenAI Agent SDK imports (required)
from agents import RunConfig, Runner
from agents.lifecycle import RunHooksBase
from agents.exceptions import ModelBehaviorError
# OpenAI exceptions for error handling
from openai import InternalServerError
# Rich logging imports
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

# Token tracking
from .token_tracking import TokenTracker, format_cost, format_token_count

# Hook support
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
    logger.debug("Hooks not available (hook modules not found)")

from .constants import (AVAILABLE_MODELS, AVAILABLE_TOOLS, DEFAULT_MODEL,
                        DEFAULT_PROVIDER, DEFAULT_TEMPERATURE, MAX_AGENT_TURNS,
                        MAX_TOKENS, ASKGPT_SYSTEM_PROMPT,
                        PROVIDER_REQUIREMENTS, SUCCESS_AGENT_COMPLETE, VERSION)
from .data_types import (PromptNanoAgentRequest, PromptNanoAgentResponse,
                         ToolPermissions)
# Import tools from nano_agent_tools
from .nano_agent_tools import get_nano_agent_tools
# Import provider configuration
from .provider_config import ProviderConfig

# Initialize logger and rich console
logger = logging.getLogger(__name__)
console = Console()


class TokenTrackingHooks(RunHooksBase):
    """Minimal hooks for token tracking without rich output."""

    def __init__(self, token_tracker: Optional[TokenTracker] = None):
        """Initialize with token tracker."""
        self.token_tracker = token_tracker

    async def on_agent_start(self, context, agent):
        """Track initial token usage if available."""
        if self.token_tracker and hasattr(context, "usage"):
            self.token_tracker.update(context.usage)

    async def on_agent_end(self, context, agent, output):
        """Track final token usage."""
        if self.token_tracker and hasattr(context, "usage"):
            self.token_tracker.update(context.usage)


class RichLoggingHooks(RunHooksBase):
    """Custom lifecycle hooks for rich logging of tool calls and token tracking."""

    def __init__(
        self, token_tracker: Optional[TokenTracker] = None, verbose: bool = False
    ):
        """Initialize the hooks with a console instance and optional token tracker.

        Args:
            token_tracker: Optional TokenTracker for monitoring usage
            verbose: Whether to show rich logging panels
        """
        self.tool_call_count = 0
        self.tool_call_map = {}  # Map tool call number to tool name
        self.token_tracker = token_tracker
        self.verbose = verbose

    async def on_agent_start(self, context, agent):
        """Called when the agent starts."""
        if self.verbose:
            console.print(
                Panel(
                    Text(f"Agent: {agent.name}", style="bold cyan"),
                    title="🚀 Agent Started",
                    border_style="blue",
                )
            )

        # Track initial token usage if available
        if self.token_tracker and hasattr(context, "usage"):
            self.token_tracker.update(context.usage)
            logger.debug(f"Initial tokens: {context.usage.total_tokens}")

    def _truncate_value(self, value, max_length=100):
        """Truncate a value and add ellipsis if needed."""
        str_value = str(value)
        if len(str_value) > max_length:
            return str_value[: max_length - 3] + "..."
        return str_value

    def _format_tool_args(self, tool_name):
        """Format tool arguments for display."""
        # For now, return empty dict since we can't access args directly
        # In real implementation, we'd extract from context
        return {}

    async def on_tool_start(self, context, agent, tool):
        """Called before a tool is invoked."""
        self.tool_call_count += 1

        # Extract tool name
        tool_name = getattr(tool, "name", "Unknown Tool")

        # Store mapping for later use
        self.tool_call_map[self.tool_call_count] = tool_name
        self.current_tool_number = self.tool_call_count
        self.current_tool_name = tool_name
        self.current_tool_start_time = time.time()

        # Try multiple methods to get tool arguments
        tool_args = {}

        # Method 1: Check if tool has call attributes
        if hasattr(tool, "call") and hasattr(tool.call, "function"):
            try:
                if hasattr(tool.call.function, "arguments"):
                    tool_args = json.loads(tool.call.function.arguments)
                    logger.debug(f"Found args in tool.call.function: {tool_args}")
            except Exception as e:
                logger.debug(f"Failed to get args from tool.call: {e}")

        # Method 2: Look in context for recent tool calls
        if not tool_args and hasattr(context, "messages"):
            try:
                # Get the last few messages and look for tool calls
                for msg in reversed(list(context.messages)[-3:]):
                    if hasattr(msg, "tool_calls"):
                        for tc in msg.tool_calls:
                            if (
                                hasattr(tc, "function")
                                and tc.function.name == tool_name
                            ):
                                if hasattr(tc.function, "arguments"):
                                    tool_args = json.loads(tc.function.arguments)
                                    logger.debug(
                                        f"Found args in context messages: {tool_args}"
                                    )
                                    break
                        if tool_args:
                            break
            except Exception as e:
                logger.debug(f"Failed to get args from context: {e}")

        # Method 3: Check the tool object directly
        if not tool_args:
            # Log what the tool object contains for debugging
            logger.debug(
                f"Tool type: {type(tool)}, dir: {[x for x in dir(tool) if not x.startswith('_')][:10]}"
            )
            if hasattr(tool, "__dict__"):
                logger.debug(f"Tool dict: {list(tool.__dict__.keys())[:10]}")

        # Display the tool call with or without arguments
        if tool_args:
            # Truncate values that are too long
            formatted_args = {}
            for key, value in tool_args.items():
                formatted_args[key] = self._truncate_value(value, 100)

            args_str = json.dumps(formatted_args, indent=2)
            display_text = f"{tool_name}(\n{args_str}\n)"

            console.print(
                Panel(
                    Syntax(display_text, "python", theme="monokai", line_numbers=False),
                    title=f"🔧 Tool Call #{self.tool_call_count}",
                    border_style="cyan",
                )
            )
        else:
            # Fallback to simple display
            console.print(
                Panel(
                    Text(f"Invoking: {tool_name}", style="cyan"),
                    title=f"🔧 Tool Call #{self.tool_call_count}",
                    border_style="cyan",
                )
            )

        # Store args for later use if found
        self.current_tool_args = tool_args

    async def on_tool_end(self, context, agent, tool, result):
        """Called after a tool is invoked."""
        tool_name = getattr(tool, "name", "Unknown Tool")
        tool_number = getattr(self, "current_tool_number", 0)

        # Calculate execution time
        exec_time = time.time() - getattr(self, "current_tool_start_time", time.time())

        # Try to get the captured arguments from our tools module
        tool_args = {}
        try:
            from .nano_agent_tools import _last_tool_args

            if tool_name in _last_tool_args:
                tool_args = _last_tool_args[tool_name]
                # Clear after use to avoid showing stale args
                del _last_tool_args[tool_name]
        except:
            pass

        # Process the result for display
        result_str = str(result)

        # Determine if result was truncated
        was_truncated = False
        max_result_length = 200

        # Format the result based on its content
        truncation_note = ""
        if "Error:" in result_str:
            # Display errors prominently
            if len(result_str) > max_result_length:
                display_result = result_str[: max_result_length - 3] + "..."
                truncation_note = f" (truncated, {len(result_str)} chars total)"
                was_truncated = True
            else:
                display_result = result_str
            result_color = "red"
        elif result_str.startswith("{") and result_str.endswith("}"):
            # Try to parse as JSON for better formatting
            try:
                json_result = json.loads(result_str)
                formatted_json = json.dumps(json_result, indent=2)
                if len(formatted_json) > max_result_length:
                    # Truncate JSON intelligently
                    display_result = formatted_json[: max_result_length - 3] + "..."
                    truncation_note = f" (truncated, {len(result_str)} chars total)"
                    was_truncated = True
                else:
                    display_result = formatted_json
                result_color = "green"
            except:
                if len(result_str) > max_result_length:
                    display_result = result_str[: max_result_length - 3] + "..."
                    truncation_note = f" (truncated, {len(result_str)} chars total)"
                    was_truncated = True
                else:
                    display_result = result_str
                result_color = "green"
        else:
            # Regular text result
            if len(result_str) > max_result_length:
                display_result = result_str[: max_result_length - 3] + "..."
                truncation_note = f" (truncated, {len(result_str)} chars total)"
                was_truncated = True
            else:
                display_result = result_str
            result_color = "green"

        # Format the function call with arguments and return value
        if tool_args:
            # Truncate argument values that are too long
            formatted_args = {}
            for key, value in tool_args.items():
                formatted_args[key] = self._truncate_value(value, 100)

            args_str = json.dumps(formatted_args, indent=2)
            call_display = (
                f"{tool_name}({args_str}) -> {display_result}{truncation_note}"
            )
        else:
            call_display = f"{tool_name}() -> {display_result}{truncation_note}"

        # Create panel with tool call number and execution time (no per-tool tokens)
        console.print(
            Panel(
                Syntax(call_display, "python", theme="monokai", line_numbers=False)
                if tool_args
                else Text(call_display, style=result_color),
                title=f"✅ Tool Call #{tool_number} ({exec_time:.2f}s)",
                border_style="green" if result_color == "green" else "red",
            )
        )

    async def on_agent_end(self, context, agent, output):
        """Called when the agent produces final output."""
        # Track final token usage
        if self.token_tracker and hasattr(context, "usage"):
            self.token_tracker.update(context.usage)

            # Show usage summary
            report = self.token_tracker.generate_report()
            usage_text = (
                f"Tokens: {format_token_count(report.total_tokens)} | "
                f"Cost: {format_cost(report.total_cost)}"
            )
            if self.verbose:
                console.print(
                    Panel(
                        Text(
                            f"Agent completed successfully\n{usage_text}",
                            style="bold green",
                        ),
                        title="🎯 Agent Finished",
                        border_style="green",
                    )
                )
        else:
            if self.verbose:
                console.print(
                    Panel(
                        Text("Agent completed successfully", style="bold green"),
                        title="🎯 Agent Finished",
                        border_style="green",
                    )
                )


async def _execute_nano_agent_async(
    request: PromptNanoAgentRequest,
    enable_rich_logging: bool = True,
    verbose: bool = False,
) -> PromptNanoAgentResponse:
    """
    Execute the nano agent using OpenAI Agent SDK (async version).

    This method uses the OpenAI Agent SDK for a robust agent experience
    with better tool handling and conversation management.

    Args:
        request: The validated request containing prompt and configuration
        enable_rich_logging: Whether to enable rich console logging for tool calls

    Returns:
        Response with execution results or error information
    """
    start_time = time.time()

    # Trigger pre-agent start hook if available
    if HOOKS_AVAILABLE:
        try:
            hook_manager = get_hook_manager()
            event_data = HookEventData(
                event="pre_agent_start",
                timestamp=datetime.now().isoformat(),
                context=hook_manager.context,
                working_dir=os.getcwd(),
                model=request.model,
                provider=request.provider,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                prompt=request.agentic_prompt,
            )

            pre_result = await hook_manager.trigger_hook(
                HookEvent.PRE_AGENT_START, event_data, blocking=True
            )

            if pre_result.blocked:
                return PromptNanoAgentResponse(
                    success=False,
                    error=pre_result.blocking_reason
                    or "Agent execution blocked by hook",
                    execution_time_seconds=time.time() - start_time,
                )
        except Exception as e:
            logger.warning(f"Error in pre-agent hook: {e}")

    try:
        logger.info(
            f"Executing nano agent with Agent SDK: {request.agentic_prompt[:100]}..."
        )
        logger.debug(f"Model: {request.model}, Provider: {request.provider}")

        # Validate provider and model combination
        is_valid, error_msg = ProviderConfig.validate_provider_setup(
            request.provider, request.model, AVAILABLE_MODELS, PROVIDER_REQUIREMENTS
        )
        if not is_valid:
            return PromptNanoAgentResponse(
                success=False,
                error=error_msg,
                execution_time_seconds=time.time() - start_time,
            )

        # Setup provider-specific configurations
        ProviderConfig.setup_provider(
            request.provider, enable_trace=request.enable_trace
        )

        # Create tool permissions from request
        permissions = ToolPermissions(
            allowed_tools=request.allowed_tools,
            blocked_tools=request.blocked_tools,
            allowed_paths=request.allowed_paths,
            blocked_paths=request.blocked_paths,
            read_only=request.read_only,
        )

        # Get tools for the agent with permission system
        tools = get_nano_agent_tools(permissions=permissions)

        # Configure model settings based on model capabilities
        base_settings = {
            "temperature": request.temperature
            if request.temperature is not None
            else DEFAULT_TEMPERATURE,
            "max_tokens": request.max_tokens
            if request.max_tokens is not None
            else MAX_TOKENS,
        }

        # Get filtered settings for the specific model
        model_settings = ProviderConfig.get_model_settings(
            model=request.model, provider=request.provider, base_settings=base_settings
        )

        # Get the system prompt (possibly extended with agent personality)
        system_prompt = ASKGPT_SYSTEM_PROMPT
        if request.agent_name:
            from .agent_loader import AgentLoader

            agent_loader = AgentLoader()
            if agent_loader.switch_agent(request.agent_name):
                system_prompt = agent_loader.get_extended_system_prompt(
                    ASKGPT_SYSTEM_PROMPT
                )
                logger.info(
                    f"Using extended system prompt with agent: {request.agent_name}"
                )

        # Create agent using the provider configuration
        agent = ProviderConfig.create_agent(
            name="NanoAgent",
            instructions=system_prompt,
            tools=tools,
            model=request.model,
            provider=request.provider,
            model_settings=model_settings,
            api_base=request.api_base,
            api_key=request.api_key,
        )

        # Create token tracker and hooks for rich logging if enabled
        # Always create token tracker for billing info
        token_tracker = TokenTracker(model=request.model, provider=request.provider)
        # Use RichLoggingHooks for rich output or TokenTrackingHooks for minimal tracking
        if enable_rich_logging:
            hooks = RichLoggingHooks(token_tracker=token_tracker, verbose=verbose)
        else:
            hooks = TokenTrackingHooks(token_tracker=token_tracker)

        # Prepare the prompt with chat history context
        # Since Runner.run doesn't support messages parameter directly,
        # we'll format the chat history as part of the prompt
        if request.chat_history and len(request.chat_history) > 0:
            # Build a conversation context string
            conversation_lines = []
            conversation_lines.append("Previous conversation context:")
            conversation_lines.append("---")
            for msg in request.chat_history:
                role_label = (
                    "User"
                    if msg.role == "user"
                    else "Assistant"
                    if msg.role == "assistant"
                    else msg.role.capitalize()
                )
                conversation_lines.append(f"{role_label}: {msg.content}")
            conversation_lines.append("---")
            conversation_lines.append("Current request:")
            conversation_lines.append(request.agentic_prompt)

            # Combine into a single prompt with context
            full_prompt = "\n".join(conversation_lines)
            has_history = "true"  # Use string for trace metadata
        else:
            full_prompt = request.agentic_prompt
            has_history = "false"  # Use string for trace metadata

        # Determine max turns
        if request.max_tool_calls is not None:
            if request.max_tool_calls == -1:
                max_turns = 999  # Effectively unlimited
            else:
                max_turns = request.max_tool_calls
        else:
            max_turns = MAX_AGENT_TURNS

        # Run the agent asynchronously
        result = await Runner.run(
            agent,
            full_prompt,
            max_turns=max_turns,
            run_config=RunConfig(
                workflow_name="nano_agent_task",
                trace_metadata={
                    "model": request.model,
                    "provider": request.provider,
                    "timestamp": datetime.now().isoformat(),
                    "has_history": has_history,  # Now a string
                },
            ),
            hooks=hooks,
        )

        execution_time = time.time() - start_time

        # Extract the final output
        final_output = (
            result.final_output if hasattr(result, "final_output") else str(result)
        )

        # Check if result has usage information
        if hasattr(result, "usage") and token_tracker:
            token_tracker.add_usage(
                input_tokens=result.usage.get("prompt_tokens", 0),
                output_tokens=result.usage.get("completion_tokens", 0),
            )

        # Prepare metadata
        metadata = {
            "model": request.model,
            "provider": request.provider,
            "turns": len(result.messages) if hasattr(result, "messages") else 0,
        }

        # Add token usage if available
        if token_tracker:
            metadata["token_usage"] = token_tracker.get_summary()

        logger.info(f"Agent completed successfully in {execution_time:.2f}s")

        # Trigger post-agent complete hook if available
        if HOOKS_AVAILABLE:
            try:
                hook_manager = get_hook_manager()
                event_data = HookEventData(
                    event="post_agent_complete",
                    timestamp=datetime.now().isoformat(),
                    context=hook_manager.context,
                    working_dir=os.getcwd(),
                    model=request.model,
                    provider=request.provider,
                    prompt=request.agentic_prompt,
                    agent_response=final_output,
                    token_usage=metadata.get("token_usage"),
                    execution_time=execution_time,
                )

                await hook_manager.trigger_hook(
                    HookEvent.POST_AGENT_COMPLETE, event_data
                )
            except Exception as e:
                logger.warning(f"Error in post-agent hook: {e}")

        return PromptNanoAgentResponse(
            success=True,
            result=final_output,
            metadata=metadata,
            execution_time_seconds=execution_time,
            permissions_used=permissions,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        
        # Handle MaxTurnsExceeded specifically
        if "Max turns" in str(e) or "MaxTurnsExceeded" in type(e).__name__:
            error_msg = f"Maximum tool calls ({max_turns}) reached. The agent needs more iterations to complete the task."
            logger.info(f"Agent reached max tool calls limit: {max_turns}")
            
            # Trigger agent error hook if available
            if HOOKS_AVAILABLE:
                try:
                    hook_manager = get_hook_manager()
                    event_data = HookEventData(
                        event="agent_error",
                        timestamp=datetime.now().isoformat(),
                        context=hook_manager.context,
                        working_dir=os.getcwd(),
                        model=request.model,
                        provider=request.provider,
                        prompt=request.agentic_prompt,
                        error=error_msg,
                        execution_time=execution_time,
                    )
                    await hook_manager.trigger_hook(HookEvent.AGENT_ERROR, event_data)
                except Exception as hook_error:
                    logger.warning(f"Error in agent error hook: {hook_error}")
            
            return PromptNanoAgentResponse(
                success=False,
                error=error_msg,
                metadata={
                    "error_type": "MaxToolCallsReached",
                    "max_tool_calls": max_turns,
                    "model": request.model,
                    "provider": request.provider,
                    "agent_sdk": True,
                },
                execution_time_seconds=execution_time,
            )
        
        # Generic error handling
        import traceback
        full_traceback = traceback.format_exc()
        logger.error(
            f"Agent SDK execution failed: {str(e)}\nFull traceback:\n{full_traceback}"
        )

        # Trigger agent error hook if available
        if HOOKS_AVAILABLE:
            try:
                hook_manager = get_hook_manager()
                event_data = HookEventData(
                    event="agent_error",
                    timestamp=datetime.now().isoformat(),
                    context=hook_manager.context,
                    working_dir=os.getcwd(),
                    model=request.model,
                    provider=request.provider,
                    prompt=request.agentic_prompt,
                    error=str(e),
                    execution_time=execution_time,
                )

                await hook_manager.trigger_hook(HookEvent.AGENT_ERROR, event_data)
            except Exception as hook_error:
                logger.warning(f"Error in agent error hook: {hook_error}")

        return PromptNanoAgentResponse(
            success=False,
            error=f"Agent SDK execution failed: {str(e)}",
            metadata={
                "model": request.model,
                "provider": request.provider,
                "error_type": type(e).__name__,
            },
            execution_time_seconds=execution_time,
        )
    finally:
        # Clean up HTTP clients to prevent event loop errors
        try:
            from .provider_config import ProviderConfig as PC
            PC.cleanup_clients()
        except Exception as e:
            logger.debug(f"Error during client cleanup in async function: {e}")


def _execute_nano_agent(
    request: PromptNanoAgentRequest,
    enable_rich_logging: bool = True,
    verbose: bool = False,
) -> PromptNanoAgentResponse:
    """
    Execute the nano agent using OpenAI Agent SDK.

    This method uses the OpenAI Agent SDK for a robust agent experience
    with better tool handling and conversation management.

    Args:
        request: The validated request containing prompt and configuration
        enable_rich_logging: Whether to enable rich console logging for tool calls

    Returns:
        Response with execution results or error information
    """
    start_time = time.time()

    # Trigger pre-agent start hook if available
    if HOOKS_AVAILABLE:
        try:
            hook_manager = get_hook_manager()
            event_data = HookEventData(
                event="pre_agent_start",
                timestamp=datetime.now().isoformat(),
                context=hook_manager.context,
                working_dir=os.getcwd(),
                model=request.model,
                provider=request.provider,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                prompt=request.agentic_prompt,
            )

            pre_result = hook_manager.trigger_hook_sync(
                HookEvent.PRE_AGENT_START, event_data, wait_for_completion=True
            )

            if pre_result.blocked:
                return PromptNanoAgentResponse(
                    success=False,
                    error=pre_result.blocking_reason
                    or "Agent execution blocked by hook",
                    execution_time_seconds=time.time() - start_time,
                )
        except Exception as e:
            logger.warning(f"Error in pre-agent hook: {e}")

    try:
        logger.info(
            f"Executing nano agent with Agent SDK: {request.agentic_prompt[:100]}..."
        )
        logger.debug(f"Model: {request.model}, Provider: {request.provider}")

        # Validate provider and model combination
        is_valid, error_msg = ProviderConfig.validate_provider_setup(
            request.provider, request.model, AVAILABLE_MODELS, PROVIDER_REQUIREMENTS
        )
        if not is_valid:
            return PromptNanoAgentResponse(
                success=False,
                error=error_msg,
                execution_time_seconds=time.time() - start_time,
            )

        # Setup provider-specific configurations
        ProviderConfig.setup_provider(
            request.provider, enable_trace=request.enable_trace
        )

        # Configure model settings based on model capabilities
        base_settings = {
            "temperature": request.temperature
            if request.temperature is not None
            else DEFAULT_TEMPERATURE,
            "max_tokens": request.max_tokens
            if request.max_tokens is not None
            else MAX_TOKENS,
        }

        # Get filtered settings for the specific model
        model_settings = ProviderConfig.get_model_settings(
            model=request.model, provider=request.provider, base_settings=base_settings
        )

        # Get the system prompt (possibly extended with agent personality)
        system_prompt = ASKGPT_SYSTEM_PROMPT
        if request.agent_name:
            from .agent_loader import AgentLoader

            agent_loader = AgentLoader()
            if agent_loader.switch_agent(request.agent_name):
                system_prompt = agent_loader.get_extended_system_prompt(
                    ASKGPT_SYSTEM_PROMPT
                )
                logger.info(
                    f"Using extended system prompt with agent: {request.agent_name}"
                )

        # Load and integrate Agent Skills metadata (Level 1 - progressive disclosure)
        # Skills provide modular capabilities that extend nano-agent functionality
        from .skill_loader import SkillLoader

        skill_loader = SkillLoader(
            allowed_tools=request.allowed_tools,
            blocked_tools=request.blocked_tools,
        )
        skill_metadata_summary = skill_loader.get_skill_metadata_summary()
        if skill_metadata_summary:
            system_prompt = f"{system_prompt}\n\n{skill_metadata_summary}"
            enabled_skills = [s for s in skill_loader.list_skills() if s.enabled]
            logger.debug(f"Added skill metadata to system prompt: {len(enabled_skills)} enabled skills")

        # Create tool permissions from request
        permissions = ToolPermissions(
            allowed_tools=request.allowed_tools,
            blocked_tools=request.blocked_tools,
            allowed_paths=request.allowed_paths,
            blocked_paths=request.blocked_paths,
            read_only=request.read_only,
        )

        # Create agent with provider-specific configuration
        agent = ProviderConfig.create_agent(
            name="NanoAgent",
            instructions=system_prompt,
            tools=get_nano_agent_tools(permissions=permissions),
            model=request.model,
            provider=request.provider,
            model_settings=model_settings,
            api_base=request.api_base,
            api_key=request.api_key,
        )

        # Create token tracker and hooks for rich logging if enabled
        # Always create token tracker for billing info
        token_tracker = TokenTracker(model=request.model, provider=request.provider)
        # Use RichLoggingHooks for rich output or TokenTrackingHooks for minimal tracking
        if enable_rich_logging:
            hooks = RichLoggingHooks(token_tracker=token_tracker, verbose=verbose)
        else:
            hooks = TokenTrackingHooks(token_tracker=token_tracker)

        # Run the agent synchronously
        # Runner.run_sync() needs an event loop to exist (it calls get_event_loop())
        # So we ensure one exists
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            # Create a new event loop if none exists or it's closed
            # This is needed for Runner.run_sync() to work
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Match skills to user prompt and load instructions if relevant (Level 2 - progressive disclosure)
        # Skills are triggered when the user prompt matches their description keywords
        matching_skills = skill_loader.match_skills_to_prompt(request.agentic_prompt)
        skill_instructions = []

        if matching_skills:
            logger.info(
                f"Matched {len(matching_skills)} skills to prompt: {[s.name for s in matching_skills]}"
            )
            for skill in matching_skills:
                instructions = skill_loader.load_skill_instructions(skill.name)
                if instructions:
                    # Format skill instructions for inclusion in prompt
                    skill_context = f"\n\n---\nSkill: {skill.name}\n{instructions}\n---\n"
                    skill_instructions.append(skill_context)
                    logger.debug(f"Loaded Level 2 instructions for skill: {skill.name}")

        # Prepare the prompt with chat history context
        # Since Runner.run_sync doesn't support messages parameter directly,
        # we'll format the chat history as part of the prompt
        if request.chat_history and len(request.chat_history) > 0:
            # Build a conversation context string
            conversation_lines = []
            conversation_lines.append("Previous conversation context:")
            conversation_lines.append("---")
            for msg in request.chat_history:
                role_label = (
                    "User"
                    if msg.role == "user"
                    else "Assistant"
                    if msg.role == "assistant"
                    else msg.role.capitalize()
                )
                conversation_lines.append(f"{role_label}: {msg.content}")
            conversation_lines.append("---")
            conversation_lines.append("Current request:")
            conversation_lines.append(request.agentic_prompt)

            # Add skill instructions if any were matched
            if skill_instructions:
                conversation_lines.append("\n--- Relevant Skills ---")
                conversation_lines.extend(skill_instructions)

            # Combine into a single prompt with context
            full_prompt = "\n".join(conversation_lines)
            has_history = "true"  # Use string for trace metadata
        else:
            # No chat history - prepend skill instructions to the prompt
            if skill_instructions:
                skill_context = "\n".join(skill_instructions)
                full_prompt = f"{skill_context}\n\nUser request: {request.agentic_prompt}"
            else:
                full_prompt = request.agentic_prompt
            has_history = "false"  # Use string for trace metadata

        # Determine max turns
        if request.max_tool_calls is not None:
            if request.max_tool_calls == -1:
                max_turns = 999  # Effectively unlimited
            else:
                max_turns = request.max_tool_calls
        else:
            max_turns = MAX_AGENT_TURNS
        
        # Retry logic for JSON parsing errors
        max_retries = 2
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # If this is a retry after a JSON parsing error, modify the prompt
                if retry_count > 0 and last_error:
                    retry_prompt = (
                        f"{full_prompt}\n\n"
                        f"IMPORTANT: The previous attempt failed because of improper tool calling format. "
                        f"Remember to output ONLY valid JSON when calling tools, with no explanatory text before it. "
                        f"For example, to read a file, output only: {{\"file_path\": \"/path/to/file\"}}"
                    )
                    logger.info(f"Retrying with clarification (attempt {retry_count + 1}/{max_retries + 1})")
                else:
                    retry_prompt = full_prompt
                
                result = Runner.run_sync(
                    agent,
                    retry_prompt,
                    max_turns=max_turns,
                    run_config=RunConfig(
                        workflow_name="nano_agent_task",
                        trace_metadata={
                            "model": request.model,
                            "provider": request.provider,
                            "timestamp": datetime.now().isoformat(),
                            "has_history": has_history,  # Now a string
                            "retry_attempt": str(retry_count),
                        },
                    ),
                    hooks=hooks,
                )
                # Success - break out of retry loop
                break
                
            except InternalServerError as e:
                error_str = str(e)
                # Check if this is a JSON parsing error from tool calls
                if "error parsing tool call" in error_str and "invalid character" in error_str:
                    last_error = e
                    retry_count += 1
                    
                    if retry_count > max_retries:
                        logger.error(f"Failed after {max_retries} retries for JSON parsing error")
                        # Re-raise the error after exhausting retries
                        raise
                    else:
                        logger.warning(f"JSON parsing error in tool call, retrying ({retry_count}/{max_retries}): {error_str[:200]}")
                        # Continue to next iteration for retry
                        continue
                else:
                    # Not a JSON parsing error, re-raise immediately
                    raise
            except RuntimeError as e:
                # This shouldn't happen now that we ensure an event loop exists
                logger.error(f"Runtime error in agent execution: {e}")
                raise

        execution_time = time.time() - start_time

        # Extract the final output
        final_output = (
            result.final_output if hasattr(result, "final_output") else str(result)
        )

        # Check if result has usage information
        if hasattr(result, "usage") and token_tracker:
            logger.debug(f"Result has usage: {result.usage}")
            token_tracker.update(result.usage)

        # Build metadata including token usage
        metadata = {
            "model": request.model,
            "provider": request.provider,
            "timestamp": datetime.now().isoformat(),
            "agent_sdk": True,
            "turns_used": len(result.messages) if hasattr(result, "messages") else None,
        }

        # Add token usage information if available
        if token_tracker:
            report = token_tracker.generate_report()
            metadata["token_usage"] = {
                "total_tokens": report.total_tokens,
                "input_tokens": report.total_input_tokens,
                "output_tokens": report.total_output_tokens,
                "cached_tokens": report.cached_input_tokens,
                "total_cost": round(report.total_cost, 4),
            }

        response = PromptNanoAgentResponse(
            success=True,
            result=final_output,
            metadata=metadata,
            execution_time_seconds=execution_time,
            permissions_used=permissions,
        )

        # Trigger post-agent complete hook if available
        if HOOKS_AVAILABLE:
            try:
                hook_manager = get_hook_manager()
                event_data = HookEventData(
                    event="post_agent_complete",
                    timestamp=datetime.now().isoformat(),
                    context=hook_manager.context,
                    working_dir=os.getcwd(),
                    model=request.model,
                    provider=request.provider,
                    prompt=request.agentic_prompt,
                    agent_response=final_output,  # Use agent_response instead of result
                    execution_time=execution_time,
                    token_usage=metadata.get("token_usage"),
                )

                # For post-completion, don't wait for non-blocking hooks like bell sounds
                # They can run in the background while user sees the response
                hook_manager.trigger_hook_sync(
                    HookEvent.POST_AGENT_COMPLETE, event_data, wait_for_completion=False
                )
            except Exception as e:
                logger.warning(f"Error in post-agent hook: {e}")

        logger.info(
            f"Agent SDK execution completed successfully in {execution_time:.2f} seconds"
        )
        return response

    except ModelBehaviorError as e:
        execution_time = time.time() - start_time
        
        # Handle tool not found errors specifically
        error_str = str(e)
        if "Tool" in error_str and "not found" in error_str:
            # Extract the tool name that was attempted
            import re
            match = re.search(r'Tool (\w+) not found', error_str)
            attempted_tool = match.group(1) if match else "unknown"
            
            # In dev mode, provide detailed error information
            if request.dev_mode:
                # Get the list of available tools based on permissions
                available_tool_names = []
                tools = get_nano_agent_tools(permissions=permissions)
                for tool in tools:
                    # Get the function name from the tool
                    if hasattr(tool, '__name__'):
                        available_tool_names.append(tool.__name__)
                
                error_msg = (
                    f"Tool '{attempted_tool}' not found. "
                    f"Available tools: {', '.join(available_tool_names)}. "
                    f"To list available tools, run: list_directory() to see what tools are available."
                )
                logger.warning(f"Model attempted to use non-existent tool: {attempted_tool}")
                
                return PromptNanoAgentResponse(
                    success=False,
                    error=error_msg,
                    metadata={
                        "error_type": "ToolNotFound",
                        "attempted_tool": attempted_tool,
                        "available_tools": available_tool_names,
                        "model": request.model,
                        "provider": request.provider,
                        "agent_sdk": True,
                    },
                    execution_time_seconds=execution_time,
                )
            else:
                # In non-dev mode, don't return an error - let the model retry
                # Log the issue for debugging but don't fail the request
                logger.info(f"Model attempted non-existent tool '{attempted_tool}', allowing retry")
                
                # Re-raise the exception to let the agent SDK handle it naturally
                # This allows the model to self-correct and try again
                raise
        
        # Other ModelBehaviorError cases
        if request.dev_mode:
            # In dev mode, return detailed error
            error_msg = f"Model behavior error: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Trigger agent error hook if available
            if HOOKS_AVAILABLE:
                try:
                    hook_manager = get_hook_manager()
                    event_data = HookEventData(
                        event="agent_error",
                        timestamp=datetime.now().isoformat(),
                        context=hook_manager.context,
                        working_dir=os.getcwd(),
                        model=request.model,
                        provider=request.provider,
                        prompt=request.agentic_prompt,
                        error=error_msg,
                        execution_time=execution_time,
                    )

                    hook_manager.trigger_hook_sync(HookEvent.AGENT_ERROR, event_data)
                except Exception as hook_error:
                    logger.warning(f"Error in agent error hook: {hook_error}")

            return PromptNanoAgentResponse(
                success=False,
                error=error_msg,
                metadata={
                    "error_type": "ModelBehaviorError",
                    "model": request.model,
                    "provider": request.provider,
                    "agent_sdk": True,
                },
                execution_time_seconds=execution_time,
            )
        else:
            # In non-dev mode, let the model retry
            logger.info(f"Model behavior error: {str(e)}, allowing retry")
            raise
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        # Handle MaxTurnsExceeded specifically
        if "Max turns" in str(e) or "MaxTurnsExceeded" in type(e).__name__:
            error_msg = f"Maximum tool calls ({max_turns}) reached. The agent needs more iterations to complete the task."
            logger.info(f"Agent reached max tool calls limit: {max_turns}")

            # Trigger agent error hook if available
            if HOOKS_AVAILABLE:
                try:
                    hook_manager = get_hook_manager()
                    event_data = HookEventData(
                        event="agent_error",
                        timestamp=datetime.now().isoformat(),
                        context=hook_manager.context,
                        working_dir=os.getcwd(),
                        model=request.model,
                        provider=request.provider,
                        prompt=request.agentic_prompt,
                        error=error_msg,
                        execution_time=execution_time,
                    )

                    hook_manager.trigger_hook_sync(HookEvent.AGENT_ERROR, event_data)
                except Exception as hook_error:
                    logger.warning(f"Error in agent error hook: {hook_error}")

            return PromptNanoAgentResponse(
                success=False,
                error=error_msg,
                metadata={
                    "error_type": "MaxToolCallsReached",
                    "max_tool_calls": max_turns,
                    "model": request.model,
                    "provider": request.provider,
                    "agent_sdk": True,
                },
                execution_time_seconds=execution_time,
            )
        
        # Generic error handling
        error_msg = f"Agent SDK execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Trigger agent error hook if available
        if HOOKS_AVAILABLE:
            try:
                hook_manager = get_hook_manager()
                event_data = HookEventData(
                    event="agent_error",
                    timestamp=datetime.now().isoformat(),
                    context=hook_manager.context,
                    working_dir=os.getcwd(),
                    model=request.model,
                    provider=request.provider,
                    prompt=request.agentic_prompt,
                    error=error_msg,
                    execution_time=execution_time,
                )

                hook_manager.trigger_hook_sync(HookEvent.AGENT_ERROR, event_data)
            except Exception as hook_error:
                logger.warning(f"Error in agent error hook: {hook_error}")

        return PromptNanoAgentResponse(
            success=False,
            error=error_msg,
            metadata={
                "error_type": type(e).__name__,
                "model": request.model,
                "provider": request.provider,
                "agent_sdk": True,
            },
            execution_time_seconds=execution_time,
        )
    finally:
        # Clean up HTTP clients to prevent event loop errors
        try:
            from .provider_config import ProviderConfig as PC
            PC.cleanup_clients()
        except Exception as e:
            logger.debug(f"Error during client cleanup: {e}")


async def prompt_nano_agent(
    agentic_prompt: str,
    model: str = DEFAULT_MODEL,
    provider: str = DEFAULT_PROVIDER,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    allowed_tools: Optional[List[str]] = None,
    blocked_tools: Optional[List[str]] = None,
    allowed_paths: Optional[List[str]] = None,
    blocked_paths: Optional[List[str]] = None,
    read_only: bool = False,
    # Session management
    session_id: Optional[str] = None,
    clear_history: bool = False,
    ctx: Any = None,  # Context will be injected by FastMCP when registered
) -> Dict[str, Any]:
    """
    Execute an autonomous agent with a natural language prompt.

    This tool creates an AI agent that can perform complex, multi-step tasks
    autonomously based on your natural language description. The agent has
    access to file system tools and can read existing files, create new files,
    and perform various data processing and code generation tasks.

    This implementation uses the OpenAI Agent SDK for robust tool handling
    and conversation management.

    Args:
        agentic_prompt: Natural language description of the work to be done.
                       Be specific and detailed for best results.
                       Examples:
                       - "Read all Python files in src/ and create a summary document"
                       - "Generate unit tests for the data_processing module"
                       - "Create a REST API with CRUD operations for a todo list"

        model: The LLM model to use for the agent. Options vary by provider:
               OpenAI: gpt-5-mini (default), gpt-5-nano, gpt-5, gpt-4o
               Anthropic: claude-opus-4-1-20250805, claude-sonnet-4-20250514, etc.
               Ollama: gpt-oss:20b, gpt-oss:120b (local models)

        provider: The LLM provider. Options:
                 - "openai" (default): OpenAI's GPT models
                 - "anthropic": Anthropic's Claude models via LiteLLM
                 - "ollama": Local models via Ollama

        temperature: Model temperature (0.0-2.0). Controls randomness in responses.
                    Lower values = more focused, higher values = more creative.

        max_tokens: Maximum number of tokens in the response. Controls output length.

        allowed_tools: List of tools the agent is allowed to use (whitelist).
                      Example: ["read_file", "list_directory"]

        blocked_tools: List of tools the agent cannot use (blacklist).
                      Example: ["write_file", "edit_file"]

        allowed_paths: List of path patterns the agent can access (whitelist).
                      Example: ["./src", "/tmp/sandbox"]

        blocked_paths: List of path patterns the agent cannot access (blacklist).
                      Example: ["/etc", "~/.ssh", "/System"]

        read_only: If True, disables all write operations (write_file, edit_file).
                  Useful for safe exploration and analysis tasks.

        session_id: Optional session ID to continue a conversation. If provided,
                   the agent will have access to previous conversation context.

        clear_history: If True, clears the conversation history for the session.
                      Useful for starting fresh while keeping session settings.

        ctx: MCP context (automatically injected)

    Returns:
        Dictionary containing:
        - success: Whether the agent completed successfully
        - result: The agent's execution result or output
        - error: Error message if the execution failed
        - metadata: Additional execution information
        - execution_time_seconds: Total time taken

    Examples:
        >>> await prompt_nano_agent(
        ...     "Create a Python function that calculates fibonacci numbers"
        ... )
        {"success": True, "result": "Created fibonacci.py with optimized function"}

        >>> await prompt_nano_agent(
        ...     "Analyze all JSON files and create a schema document",
        ...     model="gpt-5"
        ... )
        {"success": True, "result": "Created schema.md with 15 JSON schemas analyzed"}
    """
    try:
        # Initialize MCP session manager if in MCP context
        mcp_session = None
        chat_history = []
        client_id = "unknown"

        if ctx:
            # Get client identifier from context
            client_id = (
                getattr(ctx, "client_id", None)
                or getattr(ctx, "client_name", None)
                or "mcp-client"
            )

            # Initialize session manager
            from .mcp_session_manager import MCPSessionManager

            session_manager = MCPSessionManager()

            # Get or create session
            mcp_session = await session_manager.get_or_create_session(
                client_id=client_id, session_id=session_id, create_new=clear_history
            )

            # Clear history if requested
            if clear_history:
                mcp_session.conversation = []

            # Get conversation context
            if not clear_history and mcp_session.conversation:
                chat_history = await session_manager.get_conversation_context(
                    client_id=client_id,
                    session_id=mcp_session.session_id,
                    max_messages=20,
                )

            # Apply session settings if not overridden
            if model == DEFAULT_MODEL and mcp_session.model:
                model = mcp_session.model
            if provider == DEFAULT_PROVIDER and mcp_session.provider:
                provider = mcp_session.provider
            if temperature is None and mcp_session.temperature is not None:
                temperature = mcp_session.temperature
            if max_tokens is None and mcp_session.max_tokens is not None:
                max_tokens = mcp_session.max_tokens

            # Apply session permissions if not overridden
            if allowed_tools is None and mcp_session.allowed_tools:
                allowed_tools = mcp_session.allowed_tools
            if blocked_tools is None and mcp_session.blocked_tools:
                blocked_tools = mcp_session.blocked_tools
            if allowed_paths is None and mcp_session.allowed_paths:
                allowed_paths = mcp_session.allowed_paths
            if blocked_paths is None and mcp_session.blocked_paths:
                blocked_paths = mcp_session.blocked_paths
            if not read_only and mcp_session.read_only:
                read_only = mcp_session.read_only

        # Trigger MCP request received hook if available
        if HOOKS_AVAILABLE and ctx:
            try:
                hook_manager = get_hook_manager()
                # Get MCP client info if available from context
                mcp_client = (
                    getattr(ctx, "client_id", None)
                    or getattr(ctx, "client_name", None)
                    or "mcp-client"
                )
                mcp_request_id = getattr(ctx, "request_id", None) or str(id(ctx))

                event_data = HookEventData(
                    event="mcp_request_received",
                    timestamp=datetime.now().isoformat(),
                    context="mcp",  # Force MCP context
                    working_dir=os.getcwd(),
                    model=model,
                    provider=provider,
                    prompt=agentic_prompt,
                    mcp_client=mcp_client,
                    mcp_request_id=mcp_request_id,
                )

                pre_result = await hook_manager.trigger_hook(
                    HookEvent.MCP_REQUEST_RECEIVED, event_data, blocking=True
                )

                if pre_result.blocked:
                    return {
                        "success": False,
                        "error": pre_result.blocking_reason
                        or "MCP request blocked by hook",
                        "execution_time_seconds": 0.0,
                    }
            except Exception as e:
                logger.warning(f"Error in MCP request hook: {e}")

        # Report progress if context is available
        if ctx:
            await ctx.report_progress(0.1, 1.0, "Initializing agent...")

        # Create and validate request
        request = PromptNanoAgentRequest(
            agentic_prompt=agentic_prompt,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            allowed_tools=allowed_tools,
            blocked_tools=blocked_tools,
            allowed_paths=allowed_paths,
            blocked_paths=blocked_paths,
            read_only=read_only,
            chat_history=chat_history,
        )

        if ctx:
            await ctx.report_progress(0.3, 1.0, "Executing agent task...")

        # Execute the agent (disable rich logging when called via MCP to avoid interference)
        # Use async version if we're already in an async context
        # Check if we're running as MCP server via environment variable
        is_mcp_mode = os.environ.get("ASKGPT_MCP_MODE", "false").lower() == "true"
        response = await _execute_nano_agent_async(
            request, enable_rich_logging=(not is_mcp_mode)
        )

        if ctx:
            await ctx.report_progress(1.0, 1.0, "Task completed")
            if response.success:
                await ctx.info(
                    SUCCESS_AGENT_COMPLETE.format(response.execution_time_seconds)
                )
            else:
                await ctx.error(f"Agent failed: {response.error}")

        # Trigger MCP response ready hook if available
        if HOOKS_AVAILABLE and ctx:
            try:
                hook_manager = get_hook_manager()
                mcp_client = (
                    getattr(ctx, "client_id", None)
                    or getattr(ctx, "client_name", None)
                    or "mcp-client"
                )
                mcp_request_id = getattr(ctx, "request_id", None) or str(id(ctx))

                event_data = HookEventData(
                    event="mcp_response_ready",
                    timestamp=datetime.now().isoformat(),
                    context="mcp",  # Force MCP context
                    working_dir=os.getcwd(),
                    model=model,
                    provider=provider,
                    prompt=agentic_prompt,
                    agent_response=response.result
                    if response.success
                    else response.error,
                    mcp_client=mcp_client,
                    mcp_request_id=mcp_request_id,
                    execution_time=response.execution_time_seconds,
                )

                await hook_manager.trigger_hook(
                    HookEvent.MCP_RESPONSE_READY, event_data
                )
            except Exception as e:
                logger.warning(f"Error in MCP response hook: {e}")

        # Update session if in MCP context
        if mcp_session and ctx:
            try:
                await session_manager.update_session(
                    client_id=client_id,
                    session_id=mcp_session.session_id,
                    user_prompt=agentic_prompt,
                    agent_response=response.result
                    if response.success
                    else response.error,
                    metadata=response.metadata,
                )

                # Update session settings for future requests
                await session_manager.update_session_settings(
                    client_id=client_id,
                    session_id=mcp_session.session_id,
                    model=model,
                    provider=provider,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    allowed_tools=allowed_tools,
                    blocked_tools=blocked_tools,
                    allowed_paths=allowed_paths,
                    blocked_paths=blocked_paths,
                    read_only=read_only,
                )
            except Exception as e:
                logger.warning(f"Error updating MCP session: {e}")

        # Add session info to response metadata
        response_dict = response.model_dump()
        if mcp_session:
            response_dict["session_info"] = {
                "session_id": mcp_session.session_id,
                "message_count": len(mcp_session.conversation)
                + 2,  # +2 for current exchange
                "client_id": client_id,
            }

        # Convert response to dictionary for MCP protocol
        return response_dict

    except Exception as e:
        logger.error(f"Error in prompt_nano_agent: {str(e)}", exc_info=True)

        if ctx:
            await ctx.error(f"Execution failed: {str(e)}")

        # Return error response
        error_response = PromptNanoAgentResponse(
            success=False, error=str(e), metadata={"error_type": type(e).__name__}
        )
        return error_response.model_dump()


async def prompt_nano_agent_readonly(
    agentic_prompt: str,
    model: str = DEFAULT_MODEL,
    provider: str = DEFAULT_PROVIDER,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    allowed_paths: Optional[List[str]] = None,
    blocked_paths: Optional[List[str]] = None,
    # Session management
    session_id: Optional[str] = None,
    clear_history: bool = False,
    ctx: Any = None,  # Context will be injected by FastMCP when registered
) -> Dict[str, Any]:
    """
    Execute an autonomous agent in READ-ONLY mode with a natural language prompt.

    This is a safe version of prompt_nano_agent that prevents any file system modifications.
    The agent can only read files, list directories, and analyze content - perfect for
    exploration, analysis, and reporting tasks without risk of changing anything.

    The agent CANNOT:
    - Write or create files
    - Edit existing files
    - Create directories
    - Delete anything
    - Make any file system modifications

    The agent CAN:
    - Read any file content
    - List directory contents
    - Get file information (size, permissions, etc.)
    - Analyze and report on code or data
    - Generate suggestions and recommendations

    Args:
        agentic_prompt: Natural language description of the analysis or exploration task.
                       Examples:
                       - "Analyze the codebase structure and create a report"
                       - "Find all Python files and summarize their functionality"
                       - "Review the code for security vulnerabilities"
                       - "Explain how the authentication system works"

        model: The LLM model to use (defaults from environment or constants)
        provider: The LLM provider (defaults from environment or constants)
        temperature: Model temperature for response randomness (0.0-2.0)
        max_tokens: Maximum response length in tokens
        allowed_paths: List of paths the agent can access (whitelist)
        blocked_paths: List of paths the agent cannot access (blacklist)
        session_id: Optional session ID for conversation continuity
        clear_history: If True, clears conversation history for the session
        ctx: MCP context (automatically injected)

    Returns:
        Dictionary with execution results, same format as prompt_nano_agent

    Examples:
        >>> await prompt_nano_agent_readonly(
        ...     "Analyze all Python files and identify unused imports"
        ... )
        {"success": True, "result": "Found 5 files with unused imports..."}

        >>> await prompt_nano_agent_readonly(
        ...     "Create a dependency graph of the modules"
        ... )
        {"success": True, "result": "Module dependency analysis..."}
    """
    # Call the main function with read_only=True and blocked write tools
    blocked_tools = ["write_file", "edit_file", "create_directory", "delete_file"]

    return await prompt_nano_agent(
        agentic_prompt=agentic_prompt,
        model=model,
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        allowed_tools=None,  # Let all read tools be available
        blocked_tools=blocked_tools,  # Block all write operations
        allowed_paths=allowed_paths,
        blocked_paths=blocked_paths,
        read_only=True,  # Enforce read-only mode
        session_id=session_id,
        clear_history=clear_history,
        ctx=ctx,
    )


# Additional utility functions


async def get_agent_status() -> Dict[str, Any]:
    """
    Get the current status of the nano agent system.

    This is a utility function for monitoring and debugging.
    """
    return {
        "status": "operational",
        "version": VERSION,
        "available_models": AVAILABLE_MODELS,
        "available_providers": list(AVAILABLE_MODELS.keys()),
        "tools_available": AVAILABLE_TOOLS,
        "agent_sdk": True,
        "agent_sdk_version": "0.2.5",  # From openai-agents package
    }


def validate_model_provider_combination(model: str, provider: str) -> bool:
    """
    Validate that the model and provider combination is supported.

    Args:
        model: The model identifier
        provider: The provider name

    Returns:
        True if the combination is valid, False otherwise
    """
    return provider in AVAILABLE_MODELS and model in AVAILABLE_MODELS[provider]


# Export raw tools for direct use in CLI (these are the rich versions)
