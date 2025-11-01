"""
Properly designed hook executor that respects async/sync boundaries.

This module implements hook execution with proper separation of concerns:
- Blocking hooks run synchronously with subprocess.run()
- Non-blocking hooks use subprocess.Popen() with proper cleanup
- No mixing of event loops
"""

import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from .hook_types import HookConfig, HookEventData, HookExecutionResult

logger = logging.getLogger(__name__)

# Default timeout for non-blocking hooks (in seconds)
DEFAULT_NON_BLOCKING_TIMEOUT = 30.0


class HookExecutorV2:
    """
    Properly designed hook executor that avoids event loop issues.

    Key design decisions:
    1. No asyncio for fire-and-forget hooks - use subprocess.Popen
    2. Blocking hooks use subprocess.run() synchronously
    3. Background process monitoring via threading, not asyncio
    4. Clean separation of sync and async contexts
    """

    def __init__(self):
        """Initialize the executor."""
        self._background_processes: Dict[int, dict] = {}  # pid -> process info
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
        self._lock = threading.Lock()

    def execute_hook(
        self,
        hook_config: HookConfig,
        event_data: HookEventData,
        wait_for_completion: bool = True
    ) -> HookExecutionResult:
        """
        Execute a hook based on its configuration.

        Args:
            hook_config: Hook configuration
            event_data: Event data to pass to hook
            wait_for_completion: Whether to wait for the hook to complete
                                (ignored for blocking hooks - they always wait)

        Returns:
            HookExecutionResult with execution details
        """
        # Skip if hook is disabled
        if not hook_config.enabled:
            return HookExecutionResult(
                hook_name=hook_config.name,
                success=True,
                exit_code=0,
                stdout="Hook disabled",
                execution_time=0.0,
            )

        # Blocking hooks always wait
        if hook_config.blocking or wait_for_completion:
            return self._execute_blocking_hook(hook_config, event_data)
        else:
            return self._execute_non_blocking_hook(hook_config, event_data)

    def _execute_blocking_hook(
        self,
        hook_config: HookConfig,
        event_data: HookEventData
    ) -> HookExecutionResult:
        """
        Execute a blocking hook synchronously using subprocess.run().

        This avoids any event loop complications by being purely synchronous.
        """
        start_time = time.time()

        # Prepare environment and input
        env = self._prepare_environment(event_data)
        input_json = json.dumps(event_data.to_dict(), indent=2)

        # Expand command path
        command = os.path.expanduser(hook_config.command)

        logger.debug(f"Executing blocking hook '{hook_config.name}': {command}")

        try:
            # Use subprocess.run for synchronous execution
            result = subprocess.run(
                command,
                input=input_json,
                capture_output=True,
                text=True,
                shell=True,
                env=env,
                cwd=event_data.working_dir,
                timeout=hook_config.timeout
            )

            execution_time = time.time() - start_time

            # Check if hook blocked execution (for blocking hooks with non-zero exit)
            blocked = result.returncode != 0 and hook_config.blocking

            logger.debug(
                f"Blocking hook '{hook_config.name}' completed with exit code {result.returncode}"
            )

            return HookExecutionResult(
                hook_name=hook_config.name,
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout.strip() if result.stdout else "",
                stderr=result.stderr.strip() if result.stderr else "",
                error=result.stderr.strip() if result.returncode != 0 else None,
                execution_time=execution_time,
                blocked=blocked,
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            error_msg = f"Hook execution timed out after {hook_config.timeout} seconds"
            logger.warning(error_msg)

            return HookExecutionResult(
                hook_name=hook_config.name,
                success=False,
                exit_code=-1,
                error=error_msg,
                execution_time=execution_time,
                blocked=hook_config.blocking,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Hook execution failed: {str(e)}"
            logger.error(f"Error executing blocking hook '{hook_config.name}': {e}")

            return HookExecutionResult(
                hook_name=hook_config.name,
                success=False,
                exit_code=-1,
                error=error_msg,
                execution_time=execution_time,
                blocked=hook_config.blocking,
            )

    def _execute_non_blocking_hook(
        self,
        hook_config: HookConfig,
        event_data: HookEventData
    ) -> HookExecutionResult:
        """
        Execute a non-blocking hook using subprocess.Popen.

        This creates a truly independent process that won't be affected
        by event loop lifecycle.
        """
        # Prepare environment and input
        env = self._prepare_environment(event_data)
        input_json = json.dumps(event_data.to_dict(), indent=2)

        # Expand command path
        command = os.path.expanduser(hook_config.command)

        # Get timeout
        timeout = getattr(hook_config, 'non_blocking_timeout', None) or DEFAULT_NON_BLOCKING_TIMEOUT

        logger.debug(f"Starting non-blocking hook '{hook_config.name}': {command}")

        try:
            # Create a detached process that won't be affected by parent termination
            if os.name == 'posix':
                # On Unix, use double-fork technique for true daemon
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True,
                    env=env,
                    cwd=event_data.working_dir,
                    preexec_fn=os.setsid  # Create new session
                )
            else:
                # On Windows, use CREATE_NEW_PROCESS_GROUP
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True,
                    env=env,
                    cwd=event_data.working_dir,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )

            # Send input and close stdin immediately
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

            # Track the process for timeout monitoring
            with self._lock:
                self._background_processes[process.pid] = {
                    'process': process,
                    'start_time': time.time(),
                    'timeout': timeout,
                    'name': hook_config.name
                }

            # Start monitor thread if needed
            self._ensure_monitor_running()

            logger.debug(f"Non-blocking hook '{hook_config.name}' started with PID {process.pid}")

            return HookExecutionResult(
                hook_name=hook_config.name,
                success=True,
                exit_code=0,
                stdout=f"Started in background (PID: {process.pid})",
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

    def _prepare_environment(self, event_data: HookEventData) -> dict:
        """Prepare environment variables for hook execution."""
        env = os.environ.copy()
        env.update({
            "NANO_CLI_EVENT": event_data.event,
            "NANO_CLI_CONTEXT": event_data.context,
            "NANO_CLI_WORKING_DIR": event_data.working_dir,
            "NANO_CLI_SESSION_ID": event_data.session_id or "",
            "NANO_CLI_MODEL": event_data.model or "",
            "NANO_CLI_PROVIDER": event_data.provider or "",
        })

        if event_data.mcp_request_id:
            env["NANO_MCP_REQUEST_ID"] = event_data.mcp_request_id

        return env

    def _ensure_monitor_running(self):
        """Ensure the background process monitor thread is running."""
        with self._lock:
            if self._monitor_thread is None or not self._monitor_thread.is_alive():
                self._stop_monitor.clear()
                self._monitor_thread = threading.Thread(
                    target=self._monitor_processes,
                    daemon=True
                )
                self._monitor_thread.start()

    def _monitor_processes(self):
        """Monitor background processes for timeout and cleanup."""
        while not self._stop_monitor.is_set():
            current_time = time.time()

            with self._lock:
                pids_to_remove = []

                for pid, info in list(self._background_processes.items()):
                    process = info['process']

                    # Check if process has terminated
                    if process.poll() is not None:
                        pids_to_remove.append(pid)
                        logger.debug(f"Non-blocking hook '{info['name']}' (PID: {pid}) completed")

                    # Check for timeout
                    elif current_time - info['start_time'] > info['timeout']:
                        logger.warning(f"Non-blocking hook '{info['name']}' (PID: {pid}) timed out")
                        try:
                            process.terminate()
                            # Give it a moment to terminate
                            time.sleep(0.5)
                            if process.poll() is None:
                                process.kill()
                        except (ProcessLookupError, OSError):
                            pass
                        pids_to_remove.append(pid)

                # Remove completed/timed out processes
                for pid in pids_to_remove:
                    self._background_processes.pop(pid, None)

            # Sleep before next check
            time.sleep(1)

    def cleanup(self):
        """Clean up resources."""
        # Stop monitor thread
        self._stop_monitor.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

        # Terminate any remaining processes
        with self._lock:
            for pid, info in list(self._background_processes.items()):
                try:
                    process = info['process']
                    if process.poll() is None:
                        logger.debug(f"Terminating hook '{info['name']}' (PID: {pid}) during cleanup")
                        process.terminate()
                except (ProcessLookupError, OSError):
                    pass

            self._background_processes.clear()