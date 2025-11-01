"""
Hook manager for nano-agent hooks system.

Manages loading, filtering, and executing user-defined hooks.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .hook_types import (HookConfig, HookEvent, HookEventData,
                         HookExecutionResult, HookResult, HooksConfiguration)

logger = logging.getLogger(__name__)

# Import the new redesigned executor
try:
    from .hook_executor_v2 import HookExecutorV2
    USE_NEW_EXECUTOR = True
except ImportError:
    try:
        from .hook_executor import HookExecutor as NewHookExecutor
        USE_NEW_EXECUTOR = True
    except ImportError:
        USE_NEW_EXECUTOR = False


class HookExecutor:
    """Executes individual hook commands."""

    def __init__(self):
        """Initialize the executor."""
        self._active_processes = set()

    async def cleanup_processes(self):
        """Clean up any remaining active processes."""
        if self._active_processes:
            # Create a list to avoid modification during iteration
            processes_to_clean = list(self._active_processes)

            for process in processes_to_clean:
                try:
                    if process.returncode is None:
                        # First try to terminate gracefully
                        try:
                            process.terminate()
                        except ProcessLookupError:
                            # Process already gone
                            continue

                        # Give it a moment to terminate
                        try:
                            await asyncio.wait_for(process.wait(), timeout=0.1)
                        except asyncio.TimeoutError:
                            # Force kill if it doesn't terminate
                            try:
                                process.kill()
                                # Don't wait after kill, it might hang
                            except ProcessLookupError:
                                pass  # Process already gone
                except Exception:
                    pass  # Ignore any other errors during cleanup

            self._active_processes.clear()

    def cleanup(self):
        """Synchronous cleanup method for compatibility."""
        # Try to clean up processes if possible
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.cleanup_processes())
            finally:
                loop.close()
        except Exception:
            # If async cleanup fails, just clear the set
            self._active_processes.clear()

    async def execute_hook(
        self, hook_config: HookConfig, event_data: HookEventData
    ) -> HookExecutionResult:
        """Execute a single hook command.

        Args:
            hook_config: Hook configuration
            event_data: Event data to pass to hook

        Returns:
            HookExecutionResult with execution details
        """
        start_time = time.time()

        # Skip if hook is disabled
        if not hook_config.enabled:
            return HookExecutionResult(
                hook_name=hook_config.name,
                success=True,
                exit_code=0,
                stdout="Hook disabled",
                execution_time=0.0,
            )

        # Prepare JSON input
        input_json = json.dumps(event_data.to_dict(), indent=2)

        # Prepare environment variables
        env = os.environ.copy()
        env.update(
            {
                "NANO_CLI_EVENT": event_data.event,
                "NANO_CLI_CONTEXT": event_data.context,
                "NANO_CLI_WORKING_DIR": event_data.working_dir,
                "NANO_CLI_SESSION_ID": event_data.session_id or "",
                "NANO_CLI_MODEL": event_data.model or "",
                "NANO_CLI_PROVIDER": event_data.provider or "",
            }
        )

        # Add MCP-specific variables if in MCP context
        if event_data.context == "mcp":
            env["NANO_MCP_CONTEXT"] = "true"
            if event_data.mcp_client:
                env["NANO_MCP_CLIENT"] = event_data.mcp_client
            if event_data.mcp_request_id:
                env["NANO_MCP_REQUEST_ID"] = event_data.mcp_request_id

        process = None
        try:
            # Expand command path if it starts with ~
            command = hook_config.command
            if command.startswith("~"):
                command = os.path.expanduser(command)

            logger.debug(f"Executing hook '{hook_config.name}': {command}")

            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=event_data.working_dir,
            )

            # Store process reference for cleanup
            self._active_processes.add(process)

            # Send input and wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_json.encode()),
                    timeout=hook_config.timeout,
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()

                return HookExecutionResult(
                    hook_name=hook_config.name,
                    success=False,
                    exit_code=-1,
                    error=f"Hook execution timed out after {hook_config.timeout} seconds",
                    execution_time=time.time() - start_time,
                    blocked=hook_config.blocking,
                )
            finally:
                # Remove from active processes and ensure process is fully closed
                if process:
                    # Ensure the process pipes are closed
                    try:
                        if process.stdin:
                            process.stdin.close()
                        if process.stdout:
                            process.stdout.close()
                        if process.stderr:
                            process.stderr.close()
                    except:
                        pass

                    # Remove from tracking
                    if process in self._active_processes:
                        self._active_processes.discard(process)

            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()

            # Check if hook blocked execution
            blocked = process.returncode != 0 and hook_config.blocking

            logger.debug(
                f"Hook '{hook_config.name}' completed with exit code {process.returncode}"
            )
            if stdout_str:
                logger.debug(f"  stdout: {stdout_str[:200]}")
            if stderr_str:
                logger.debug(f"  stderr: {stderr_str[:200]}")

            return HookExecutionResult(
                hook_name=hook_config.name,
                success=process.returncode == 0,
                exit_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time=time.time() - start_time,
                blocked=blocked,
            )

        except Exception as e:
            logger.error(f"Error executing hook '{hook_config.name}': {e}")

            # Clean up the process if it exists
            if process:
                try:
                    if process.returncode is None:
                        process.kill()
                    # Close pipes
                    if process.stdin:
                        process.stdin.close()
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
                except:
                    pass

                # Remove from tracking
                if process in self._active_processes:
                    self._active_processes.discard(process)

            return HookExecutionResult(
                hook_name=hook_config.name,
                success=False,
                exit_code=-1,
                error=str(e),
                execution_time=time.time() - start_time,
                blocked=hook_config.blocking,
            )


class HookManager:
    """Manages hook registration and execution."""

    # Singleton instance
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize hook manager.

        Args:
            config_path: Optional path to configuration file
        """
        # Only initialize once
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self.config_path = config_path
        self.config = self._load_configuration()
        if USE_NEW_EXECUTOR:
            try:
                self.executor = HookExecutorV2()
            except NameError:
                self.executor = NewHookExecutor()
        else:
            self.executor = HookExecutor()

        # Detect execution context
        self.context = self._detect_context()

    def __del__(self):
        """Cleanup when the hook manager is destroyed."""
        if hasattr(self, 'executor') and hasattr(self.executor, 'cleanup'):
            try:
                self.executor.cleanup()
            except Exception:
                pass  # Ignore errors during cleanup

        logger.info(f"HookManager initialized with context: {self.context}")
        if self.config.enabled:
            logger.info(
                f"Hooks enabled with {len(self.config.hooks)} event types configured"
            )
        else:
            logger.info("Hooks are disabled")

    def _detect_context(self) -> str:
        """Detect if running in CLI or MCP context.

        Returns:
            "cli" or "mcp"
        """
        # Check various indicators for MCP context
        if any(
            [
                os.getenv("MCP_SERVER_NAME") == "nano-agent",
                os.getenv("CLAUDE_DESKTOP"),
                "nano-agent" in (os.getenv("_", "") or ""),
                # Check if running as MCP server (via FastMCP)
                any("mcp" in str(arg).lower() for arg in os.sys.argv),
            ]
        ):
            return "mcp"
        return "cli"

    def _load_configuration(self) -> HooksConfiguration:
        """Load and merge hook configurations.

        Returns:
            Merged hooks configuration
        """
        configs = []

        # 1. Load global configuration
        global_config_path = Path.home() / ".askgpt" / "hooks.json"
        if global_config_path.exists():
            try:
                with open(global_config_path, "r") as f:
                    data = json.load(f)
                configs.append(data)
                logger.debug(f"Loaded global hooks from {global_config_path}")
            except Exception as e:
                logger.error(f"Error loading global hooks: {e}")

        # 2. Load project-specific configuration
        project_config_path = Path.cwd() / ".askgpt" / "hooks.json"
        if project_config_path.exists():
            try:
                with open(project_config_path, "r") as f:
                    data = json.load(f)
                configs.append(data)
                logger.debug(f"Loaded project hooks from {project_config_path}")
            except Exception as e:
                logger.error(f"Error loading project hooks: {e}")

        # 3. Load from specified path if provided
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                configs.append(data)
                logger.debug(f"Loaded hooks from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading hooks from {self.config_path}: {e}")

        # Merge configurations (later configs override earlier ones)
        merged = self._merge_configs(configs)

        # Convert to HooksConfiguration object
        if merged:
            return HooksConfiguration.from_dict(merged)
        else:
            # Return empty configuration if no configs found
            return HooksConfiguration(enabled=False)

    def _merge_configs(self, configs: List[Dict]) -> Dict:
        """Merge multiple configuration dictionaries.

        Args:
            configs: List of configuration dictionaries

        Returns:
            Merged configuration
        """
        if not configs:
            return {}

        # Start with first config
        merged = configs[0].copy()

        # Merge subsequent configs
        for config in configs[1:]:
            # Override top-level settings
            for key in ["version", "enabled", "timeout_seconds", "parallel_execution"]:
                if key in config:
                    merged[key] = config[key]

            # Merge hooks (project hooks override global)
            if "hooks" in config:
                if "hooks" not in merged:
                    merged["hooks"] = {}

                for event_name, hook_list in config["hooks"].items():
                    # Replace entire hook list for this event
                    merged["hooks"][event_name] = hook_list

        return merged

    async def trigger_hook(
        self, event: HookEvent, data: HookEventData, wait_for_completion: bool = False
    ) -> HookResult:
        """Trigger hooks for a specific event.

        Args:
            event: Hook event type
            data: Event data to pass to hooks
            wait_for_completion: Whether to wait for non-blocking hooks to complete
                                 (blocking hooks are always waited for)

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

        logger.debug(
            f"Triggering {len(applicable_hooks)} hooks for event {event.value}"
        )

        # Execute hooks
        results = []
        total_time = 0.0
        blocked = False
        fire_and_forget_tasks = []

        # Separate blocking and non-blocking hooks
        blocking_hooks = [h for h in applicable_hooks if h.blocking]
        non_blocking_hooks = [h for h in applicable_hooks if not h.blocking]

        # Always execute blocking hooks first and wait for them
        for hook in blocking_hooks:
            result = await self.executor.execute_hook(hook, data)
            results.append(result)
            total_time += result.execution_time

            if result.blocked:
                blocked = True
                break  # Stop on first blocking hook that fails

        # If not blocked, execute non-blocking hooks
        if not blocked and non_blocking_hooks:
            if self.config.parallel_execution:
                # Execute non-blocking hooks in parallel
                tasks = [
                    self.executor.execute_hook(hook, data)
                    for hook in non_blocking_hooks
                ]

                if wait_for_completion:
                    # Wait for all non-blocking hooks to complete
                    parallel_results = await asyncio.gather(*tasks)
                    results.extend(parallel_results)
                    if parallel_results:
                        total_time = max(total_time, max(r.execution_time for r in parallel_results))
                else:
                    # Fire and forget - start tasks but don't wait for completion
                    # We need to ensure they at least start before we return
                    for task in tasks:
                        fire_and_forget_tasks.append(asyncio.ensure_future(task))

                    # Add placeholder results for non-blocking hooks
                    for hook in non_blocking_hooks:
                        results.append(HookExecutionResult(
                            hook_name=hook.name,
                            success=True,  # Assume success since we're not waiting
                            exit_code=0,
                            stdout="Executing in background",
                            execution_time=0.0,
                        ))
            else:
                # Execute non-blocking hooks sequentially
                if wait_for_completion:
                    for hook in non_blocking_hooks:
                        result = await self.executor.execute_hook(hook, data)
                        results.append(result)
                        total_time += result.execution_time
                else:
                    # Fire and forget sequential execution
                    for hook in non_blocking_hooks:
                        task = asyncio.ensure_future(self.executor.execute_hook(hook, data))
                        fire_and_forget_tasks.append(task)
                        results.append(HookExecutionResult(
                            hook_name=hook.name,
                            success=True,
                            exit_code=0,
                            stdout="Executing in background",
                            execution_time=0.0,
                        ))

        # Store fire-and-forget tasks for potential cleanup later
        if fire_and_forget_tasks:
            self._background_tasks = getattr(self, '_background_tasks', set())
            self._background_tasks.update(fire_and_forget_tasks)
            # Clean up completed tasks
            self._background_tasks = {t for t in self._background_tasks if not t.done()}

        return HookResult(
            event=event,
            hooks_executed=len(results),
            results=results,
            blocked=blocked,
            total_time=total_time,
        )

    def reload_configuration(self):
        """Reload hook configuration from files."""
        logger.info("Reloading hook configuration")
        self.config = self._load_configuration()

    def trigger_hook_sync(
        self, event: HookEvent, data: HookEventData, wait_for_completion: bool = True
    ) -> HookResult:
        """Synchronous wrapper for trigger_hook.

        This is used when running in synchronous contexts like the CLI.

        Args:
            event: Hook event type
            data: Event data to pass to hooks
            wait_for_completion: Whether to wait for non-blocking hooks to complete.
                                 Default is True for sync contexts to ensure clean shutdown.
                                 Blocking hooks are always waited for.

        Returns:
            HookResult with execution details
        """
        try:
            # Create a new event loop for hook execution
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Run the async hook trigger
                # For sync contexts, we generally want to wait for hooks to avoid
                # premature termination, but respect the wait_for_completion flag
                result = loop.run_until_complete(
                    self.trigger_hook(event, data, wait_for_completion)
                )

                # If a hook blocked execution, we need to clean up immediately
                if result.blocked:
                    # Clean up processes right away
                    if hasattr(self.executor, 'cleanup'):
                        self.executor.cleanup()
                    elif hasattr(self.executor, 'cleanup_processes'):
                        loop.run_until_complete(self.executor.cleanup_processes())
                    return result

                # Give fire-and-forget tasks a brief moment to start
                # This helps avoid immediate termination of background tasks
                if not wait_for_completion:
                    loop.run_until_complete(asyncio.sleep(0.05))

                # Clean up any remaining processes
                if hasattr(self.executor, 'cleanup'):
                    self.executor.cleanup()
                elif hasattr(self.executor, 'cleanup_processes'):
                    loop.run_until_complete(self.executor.cleanup_processes())

                # If waiting for completion, ensure all tasks finish
                if wait_for_completion:
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        # Wait for tasks to finish
                        try:
                            loop.run_until_complete(
                                asyncio.wait_for(
                                    asyncio.gather(*pending, return_exceptions=True),
                                    timeout=1.0
                                )
                            )
                        except asyncio.TimeoutError:
                            pass  # It's ok if they don't finish in time

                return result

            finally:
                # Ensure clean shutdown
                try:
                    # Make sure to clean up subprocess transports first
                    # This is critical to avoid "Exception ignored" errors
                    try:
                        if hasattr(self.executor, 'cleanup'):
                            self.executor.cleanup()
                        elif hasattr(self.executor, 'cleanup_processes'):
                            loop.run_until_complete(self.executor.cleanup_processes())
                    except Exception:
                        pass

                    # Give subprocess transports time to close properly
                    loop.run_until_complete(asyncio.sleep(0.01))

                    # Shutdown all async generators first
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except Exception:
                        pass

                    # Cancel any remaining tasks
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        for task in pending:
                            task.cancel()

                        # Wait for cancellation with a short timeout
                        loop.run_until_complete(
                            asyncio.wait(pending, timeout=0.1, return_when=asyncio.ALL_COMPLETED)
                        )

                    # Shutdown the default executor
                    try:
                        loop.run_until_complete(loop.shutdown_default_executor())
                    except Exception:
                        pass

                    # Final pause to let everything settle
                    loop.run_until_complete(asyncio.sleep(0))

                    # Stop and close the loop
                    loop.stop()
                    loop.close()
                except Exception:
                    # If all else fails, just close it
                    try:
                        loop.close()
                    except:
                        pass

        except Exception as e:
            logger.error(f"Error triggering hook synchronously: {e}")
            return HookResult(event=event, hooks_executed=0, results=[])


# Global singleton instance
_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance.

    Returns:
        Global HookManager instance
    """
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager
