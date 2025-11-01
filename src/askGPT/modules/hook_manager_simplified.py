"""
Simplified hook manager that properly handles sync/async boundaries.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .hook_executor_v2 import HookExecutorV2
from .hook_types import (HookConfig, HookEvent, HookEventData,
                         HookExecutionResult, HookResult, HooksConfiguration)

logger = logging.getLogger(__name__)


class SimpleHookManager:
    """
    Simplified hook manager with proper sync/async separation.

    Key principles:
    1. Core methods are synchronous
    2. Hooks are executed synchronously or fire-and-forget
    3. No event loop management here
    4. Async wrappers just call sync methods
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the hook manager."""
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_configuration()
        self.context = self._detect_context()
        self.executor = HookExecutorV2()

        logger.info(f"SimpleHookManager initialized with context: {self.context}")

    def _get_default_config_path(self) -> Path:
        """Get the default configuration path."""
        # Check for config in standard locations
        config_locations = [
            Path.home() / ".askgpt" / "hooks.json",
            Path.home() / ".config" / "nano-cli" / "hooks.json",
        ]

        for location in config_locations:
            if location.exists():
                return location

        # Default to first location if none exist
        return config_locations[0]

    def _load_configuration(self) -> HooksConfiguration:
        """Load hooks configuration from file."""
        if not self.config_path.exists():
            # Return default empty configuration
            return HooksConfiguration(enabled=False, hooks={})

        try:
            import json
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            # Parse configuration
            config = HooksConfiguration(
                enabled=data.get('enabled', False),
                hooks={}
            )

            # Parse hooks
            for event_name, hook_list in data.get('hooks', {}).items():
                config.hooks[event_name] = []
                for hook_data in hook_list:
                    hook = HookConfig(
                        name=hook_data.get('name', 'unnamed'),
                        command=hook_data.get('command', ''),
                        event=event_name,  # Add the required event parameter
                        enabled=hook_data.get('enabled', True),
                        blocking=hook_data.get('blocking', False),
                        timeout=hook_data.get('timeout', 30),
                        matcher=hook_data.get('matcher'),
                        condition=hook_data.get('condition')
                    )
                    config.hooks[event_name].append(hook)

            return config

        except Exception as e:
            logger.error(f"Failed to load hooks configuration: {e}")
            return HooksConfiguration(enabled=False, hooks={})

    def _detect_context(self) -> str:
        """Detect the execution context."""
        # Check if running as MCP server
        if os.environ.get("ASKGPT_MCP_MODE") == "true":
            return "mcp"

        # Check if running in CLI
        if "nano-cli" in str(Path.cwd()) or "nano_cli" in str(Path.cwd()):
            return "cli"

        return "cli"  # Default to CLI

    def trigger_hook_sync(
        self,
        event: HookEvent,
        data: HookEventData,
        wait_for_completion: bool = False
    ) -> HookResult:
        """Synchronous hook trigger."""
        return self._trigger_hook_impl(event, data, wait_for_completion)

    def _trigger_hook_impl(
        self,
        event: HookEvent,
        data: HookEventData,
        wait_for_completion: bool = False
    ) -> HookResult:
        """
        Trigger hooks for a specific event.

        This is a SYNCHRONOUS method that executes hooks either:
        - Synchronously (blocking hooks or wait_for_completion=True)
        - Fire-and-forget (non-blocking hooks with wait_for_completion=False)

        Args:
            event: Hook event type
            data: Event data to pass to hooks
            wait_for_completion: Whether to wait for non-blocking hooks

        Returns:
            HookResult with execution details
        """
        # Skip if hooks are disabled
        if not self.config.enabled:
            return HookResult(event=event, hooks_executed=0, results=[])

        # Ensure context is set in data
        data.context = self.context
        data.timestamp = datetime.now().isoformat()

        # Get hooks for this event
        event_hooks = self.config.hooks.get(event.value, [])

        # Filter hooks based on matcher and condition
        applicable_hooks = [hook for hook in event_hooks if hook.matches(data)]

        if not applicable_hooks:
            return HookResult(event=event, hooks_executed=0, results=[])

        logger.debug(f"Triggering {len(applicable_hooks)} hooks for event {event.value}")

        # Execute hooks
        results = []
        total_time = 0.0
        blocked = False

        for hook in applicable_hooks:
            # Blocking hooks always wait
            should_wait = hook.blocking or wait_for_completion

            result = self.executor.execute_hook(hook, data, wait_for_completion=should_wait)
            results.append(result)
            total_time += result.execution_time

            # If a blocking hook fails, stop execution
            if result.blocked:
                blocked = True
                logger.info(f"Hook '{hook.name}' blocked further execution")
                break

        return HookResult(
            event=event,
            hooks_executed=len(results),
            results=results,
            blocked=blocked,
            total_time=total_time
        )

    async def trigger_hook(
        self,
        event: HookEvent,
        data: HookEventData,
        wait_for_completion: bool = False,
        blocking: bool = None  # For compatibility
    ) -> HookResult:
        """
        Async wrapper for trigger_hook_sync.

        This just runs the sync method in the current event loop's executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._trigger_hook_impl,
            event,
            data,
            wait_for_completion
        )

    def cleanup(self):
        """Clean up resources."""
        if self.executor:
            self.executor.cleanup()


# Global instance
_simple_hook_manager = None


def get_simple_hook_manager() -> SimpleHookManager:
    """Get the global simple hook manager instance."""
    global _simple_hook_manager
    if _simple_hook_manager is None:
        _simple_hook_manager = SimpleHookManager()
    return _simple_hook_manager