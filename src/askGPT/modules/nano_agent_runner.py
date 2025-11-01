"""
Proper runner for nano agent that manages event loops correctly.
"""

import asyncio
import logging
from typing import Optional

from .data_types import PromptNanoAgentRequest, PromptNanoAgentResponse
from .nano_agent import _execute_nano_agent

logger = logging.getLogger(__name__)


def run_nano_agent_properly(
    request: PromptNanoAgentRequest,
    enable_rich_logging: bool = True,
    verbose: bool = False
) -> PromptNanoAgentResponse:
    """
    Run the nano agent with proper event loop management.

    Runner.run_sync() needs to manage its own event loop,
    so we just make sure we're not in an async context.
    """
    # Just run the agent directly - let Runner.run_sync() manage the loop
    return _execute_nano_agent(request, enable_rich_logging, verbose)


def cleanup_nano_agent():
    """
    Clean up any resources used by nano agent.

    This should be called when the application is shutting down.
    """
    # Import hook manager and clean it up
    try:
        from .hook_manager_simplified import get_simple_hook_manager
        hook_manager = get_simple_hook_manager()
        hook_manager.cleanup()
    except:
        pass

    # Clean up HTTP clients
    try:
        from .provider_config import ProviderConfig
        ProviderConfig.cleanup_clients()
    except:
        pass

    # Any other cleanup needed
    logger.debug("Nano agent cleanup completed")