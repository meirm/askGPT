"""
Redesigned hook executor that handles non-blocking hooks properly.

This module provides a clean separation between blocking and non-blocking hooks,
using subprocess.Popen for non-blocking hooks to avoid asyncio event loop issues.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import time
from typing import Dict, Optional, Set, Tuple

from .hook_types import HookConfig, HookEventData, HookExecutionResult

logger = logging.getLogger(__name__)

# Default timeout for non-blocking hooks (in seconds)
DEFAULT_NON_BLOCKING_TIMEOUT = 30.0


class NonBlockingProcessManager:
    """Manages non-blocking subprocess execution without asyncio."""

    def __init__(self):
        """Initialize the process manager."""
        self._processes: Dict[int, Tuple[subprocess.Popen, float, str]] = {}  # pid -> (process, start_time, hook_name)
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()

    def execute_non_blocking(
        self,
        hook_config: HookConfig,
        event_data: HookEventData,
        timeout: Optional[float] = None
    ) -> HookExecutionResult:
        """Execute a hook in a non-blocking way using subprocess.Popen.

        This avoids asyncio subprocess issues by using the synchronous subprocess API.
        The process will be automatically terminated after the timeout.

        Args:
            hook_config: Hook configuration
            event_data: Event data to pass to hook
            timeout: Maximum time to allow the hook to run (defaults to DEFAULT_NON_BLOCKING_TIMEOUT)

        Returns:
            HookExecutionResult indicating the hook was started
        """
        # Use provided timeout or hook's timeout or default
        timeout = timeout or getattr(hook_config, 'non_blocking_timeout', None) or DEFAULT_NON_BLOCKING_TIMEOUT

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
        if event_data.mcp_request_id:
            env["NANO_MCP_REQUEST_ID"] = event_data.mcp_request_id

        # Expand command path if it starts with ~
        command = hook_config.command
        if command.startswith("~"):
            command = os.path.expanduser(command)

        logger.debug(f"Starting non-blocking hook '{hook_config.name}': {command}")

        try:
            # Use subprocess.Popen for fire-and-forget execution
            # But capture output to files for potential debugging
            with open(os.devnull, 'w') as devnull:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=devnull,
                    stderr=devnull,
                    shell=True,
                    env=env,
                    cwd=event_data.working_dir,
                    # Don't use start_new_session so we can manage the process
                    start_new_session=False
                )

            # Send input and immediately close stdin
            if input_json:
                try:
                    process.stdin.write(input_json.encode())
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
                finally:
                    try:
                        process.stdin.close()
                    except:
                        pass

            # Store process with timeout info
            start_time = time.time()
            self._processes[process.pid] = (process, start_time + timeout, hook_config.name)

            # Start cleanup thread if not running
            self._start_cleanup_thread()

            logger.debug(f"Non-blocking hook '{hook_config.name}' started with PID {process.pid}, timeout in {timeout}s")

            return HookExecutionResult(
                hook_name=hook_config.name,
                success=True,
                exit_code=0,
                stdout=f"Started in background (PID: {process.pid}, timeout: {timeout}s)",
                execution_time=0.0,
            )

        except Exception as e:
            logger.error(f"Failed to start non-blocking hook '{hook_config.name}': {e}")
            return HookExecutionResult(
                hook_name=hook_config.name,
                success=False,
                exit_code=-1,
                error=str(e),
                execution_time=0.0,
            )

    def _start_cleanup_thread(self):
        """Start the cleanup thread if not already running."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup.clear()
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
            logger.debug("Started cleanup thread for non-blocking hooks")

    def _cleanup_worker(self):
        """Worker thread that monitors and cleans up timed-out processes."""
        while not self._stop_cleanup.is_set():
            current_time = time.time()
            pids_to_remove = []

            for pid, (process, timeout_time, hook_name) in list(self._processes.items()):
                # Check if process has already terminated
                if process.poll() is not None:
                    pids_to_remove.append(pid)
                    logger.debug(f"Non-blocking hook '{hook_name}' (PID: {pid}) completed with code {process.returncode}")
                # Check if process has timed out
                elif current_time >= timeout_time:
                    try:
                        logger.warning(f"Non-blocking hook '{hook_name}' (PID: {pid}) timed out, terminating...")
                        process.terminate()
                        # Give it a moment to terminate gracefully
                        time.sleep(0.5)
                        if process.poll() is None:
                            # Force kill if still running
                            process.kill()
                            logger.warning(f"Force killed non-blocking hook '{hook_name}' (PID: {pid})")
                    except (ProcessLookupError, OSError) as e:
                        logger.debug(f"Process {pid} already gone: {e}")
                    finally:
                        pids_to_remove.append(pid)

            # Remove cleaned up processes
            for pid in pids_to_remove:
                self._processes.pop(pid, None)

            # Sleep for a short interval before next check
            time.sleep(1)

    def cleanup(self):
        """Clean up any tracked processes and stop the cleanup thread."""
        # Stop the cleanup thread
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2)

        # Terminate any remaining processes
        for pid, (process, _, hook_name) in list(self._processes.items()):
            try:
                if process.poll() is None:
                    logger.debug(f"Terminating non-blocking hook '{hook_name}' (PID: {pid}) during cleanup")
                    process.terminate()
                    # Don't wait, just terminate
            except (ProcessLookupError, OSError):
                pass

        # Clear the process tracking
        self._processes.clear()
        logger.debug("Cleaned up all non-blocking hook processes")


class HookExecutor:
    """Executes individual hook commands with proper blocking/non-blocking handling."""

    def __init__(self):
        """Initialize the executor."""
        self._non_blocking_manager = NonBlockingProcessManager()

    async def execute_blocking_hook(
        self, hook_config: HookConfig, event_data: HookEventData
    ) -> HookExecutionResult:
        """Execute a blocking hook using asyncio subprocess.

        Blocking hooks need to complete and return results, so we use
        the asyncio subprocess API for them.

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
        if event_data.mcp_request_id:
            env["NANO_MCP_REQUEST_ID"] = event_data.mcp_request_id

        try:
            # Expand command path if it starts with ~
            command = hook_config.command
            if command.startswith("~"):
                command = os.path.expanduser(command)

            logger.debug(f"Executing blocking hook '{hook_config.name}': {command}")

            # Create subprocess for blocking execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=event_data.working_dir,
            )

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

            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()

            # Check if hook blocked execution
            blocked = process.returncode != 0 and hook_config.blocking

            logger.debug(
                f"Blocking hook '{hook_config.name}' completed with exit code {process.returncode}"
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
                error=stderr_str if process.returncode != 0 else None,
                execution_time=time.time() - start_time,
                blocked=blocked,
            )

        except Exception as e:
            error_msg = f"Hook execution failed: {str(e)}"
            logger.error(f"Error executing blocking hook '{hook_config.name}': {e}")

            return HookExecutionResult(
                hook_name=hook_config.name,
                success=False,
                exit_code=-1,
                error=error_msg,
                execution_time=time.time() - start_time,
                blocked=hook_config.blocking,
            )

    def execute_non_blocking_hook(
        self, hook_config: HookConfig, event_data: HookEventData, timeout: Optional[float] = None
    ) -> HookExecutionResult:
        """Execute a non-blocking hook using subprocess.Popen.

        This method delegates to the NonBlockingProcessManager to avoid
        asyncio event loop issues.

        Args:
            hook_config: Hook configuration
            event_data: Event data to pass to hook
            timeout: Optional timeout override (defaults to 30 seconds)

        Returns:
            HookExecutionResult indicating the hook was started
        """
        return self._non_blocking_manager.execute_non_blocking(hook_config, event_data, timeout)

    async def execute_hook(self, hook_config: HookConfig, event_data: HookEventData) -> HookExecutionResult:
        """Execute a hook (blocking or non-blocking based on configuration).

        Args:
            hook_config: Hook configuration
            event_data: Event data to pass to hook

        Returns:
            HookExecutionResult with execution details
        """
        if hook_config.blocking:
            return await self.execute_blocking_hook(hook_config, event_data)
        else:
            # For non-blocking, we use the synchronous method
            return self.execute_non_blocking_hook(hook_config, event_data)

    def cleanup(self):
        """Clean up the executor."""
        self._non_blocking_manager.cleanup()