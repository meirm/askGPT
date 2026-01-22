"""
Public API for using askGPT as a library.

This module provides a clean interface for integrating askGPT into applications,
web services, and other Python projects.
"""

import logging
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from .modules.config_manager import ConfigManager, get_config_manager
from .modules.data_types import (
    ChatMessage,
    PromptNanoAgentRequest,
    PromptNanoAgentResponse,
)
from .modules.nano_agent import _execute_nano_agent_async
from .modules.session_manager import Session, SessionManager

logger = logging.getLogger(__name__)


class AskGPTClient:
    """
    Main client interface for askGPT.
    
    Provides a clean API for sending chat messages, managing sessions,
    and interacting with the askGPT agent system.
    
    Example:
        ```python
        from askgpt import AskGPTClient
        
        client = AskGPTClient()
        response = await client.chat("Hello, how are you?")
        print(response.result)
        ```
    """

    def __init__(
        self,
        default_model: Optional[str] = None,
        default_provider: Optional[str] = None,
        session_manager: Optional[SessionManager] = None,
        config_manager: Optional[ConfigManager] = None,
    ):
        """
        Initialize the askGPT client.

        Args:
            default_model: Default model to use (loads from config if None)
            default_provider: Default provider to use (loads from config if None)
            session_manager: Optional SessionManager instance (creates new if None)
            config_manager: Optional ConfigManager instance (uses global if None)
        """
        # Use provided config manager or get the global one
        self.config_manager = config_manager or get_config_manager()
        self.config = self.config_manager.config

        # Set defaults from config if not provided
        self.default_provider = default_provider or self.config.default_provider
        self.default_model = default_model or self.config.default_model

        # Initialize session manager
        self.session_manager = session_manager or SessionManager()

        logger.debug(
            f"AskGPTClient initialized with provider={self.default_provider}, "
            f"model={self.default_model}"
        )

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs,
    ) -> PromptNanoAgentResponse:
        """
        Send a chat message and get response.

        Args:
            message: The user's message/prompt
            session_id: Optional session ID to continue conversation
            model: Optional model override (uses default if not provided)
            provider: Optional provider override (uses default if not provided)
            **kwargs: Additional parameters passed to agent execution:
                - temperature: Model temperature (0.0-2.0)
                - max_tokens: Maximum response tokens
                - agent_name: Agent personality to use
                - allowed_tools: List of allowed tools
                - blocked_tools: List of blocked tools
                - allowed_paths: List of allowed path patterns
                - blocked_paths: List of blocked path patterns
                - read_only: Disable write operations
                - enable_trace: Enable OpenAI agent tracing
                - max_tool_calls: Maximum tool calls allowed

        Returns:
            PromptNanoAgentResponse with the agent's response

        Example:
            ```python
            response = await client.chat("What is 2+2?")
            if response.success:
                print(response.result)
            ```
        """
        # Load or create session
        session: Optional[Session] = None
        chat_history: List[ChatMessage] = []

        if session_id:
            session = self.session_manager.load_session(session_id)
            if session:
                chat_history = self.session_manager.get_conversation_context()
                # Use session's model/provider if not overridden
                if model is None:
                    model = session.model
                if provider is None:
                    provider = session.provider
            else:
                logger.warning(f"Session {session_id} not found, creating new session")

        # Create new session if needed
        if session is None:
            provider = provider or self.default_provider
            model = model or self.default_model
            session = self.session_manager.create_session(provider, model)

        # Use defaults if not specified
        model = model or self.default_model
        provider = provider or self.default_provider

        # Get api_base from config if not provided in kwargs
        api_base = kwargs.get("api_base")
        if not api_base and provider in self.config.providers:
            provider_config = self.config.providers[provider]
            # ProviderConfig has api_base attribute
            if provider_config.api_base:
                api_base = provider_config.api_base
                kwargs["api_base"] = api_base

        # Create request
        request = PromptNanoAgentRequest(
            agentic_prompt=message,
            model=model,
            provider=provider,
            chat_history=chat_history if chat_history else None,
            **kwargs,
        )

        # Execute agent (disable rich logging for API usage)
        response = await _execute_nano_agent_async(
            request, enable_rich_logging=False, verbose=False
        )

        # Save to session
        if session and response.success:
            self.session_manager.add_exchange(
                message,
                response.result or "",
                metadata=response.metadata,
            )

        return response

    async def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream chat responses in real-time.

        Args:
            message: The user's message/prompt
            session_id: Optional session ID to continue conversation
            **kwargs: Additional parameters (same as chat() method)

        Yields:
            Response chunks as strings

        Example:
            ```python
            async for chunk in client.chat_stream("Tell me a story"):
                print(chunk, end="", flush=True)
            ```
        """
        # For now, we'll use the non-streaming execution and yield the full result
        # TODO: Implement actual streaming when _execute_nano_agent_streaming is available
        response = await self.chat(message, session_id=session_id, **kwargs)

        if response.success and response.result:
            # Yield the result in chunks (simple implementation)
            # In the future, this will stream from the agent execution
            chunk_size = 50  # Characters per chunk
            result = response.result
            for i in range(0, len(result), chunk_size):
                yield result[i : i + chunk_size]
        elif response.error:
            yield f"Error: {response.error}"

    def create_session(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """
        Create a new chat session.

        Args:
            provider: Provider name (uses default if not provided)
            model: Model name (uses default if not provided)
            session_id: Optional session ID (generates one if not provided)

        Returns:
            New Session object

        Example:
            ```python
            session = client.create_session(provider="ollama", model="gpt-oss:20b")
            print(f"Created session: {session.session_id}")
            ```
        """
        provider = provider or self.default_provider
        model = model or self.default_model
        return self.session_manager.create_session(provider, model, session_id)

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session object if found, None otherwise

        Example:
            ```python
            session = client.get_session("session_20240101_120000_abc123")
            if session:
                print(f"Session has {len(session.conversation)} messages")
            ```
        """
        return self.session_manager.load_session(session_id)

    def list_sessions(self, limit: int = 10) -> List[Session]:
        """
        List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of Session objects, sorted by most recent first

        Example:
            ```python
            sessions = client.list_sessions(limit=5)
            for session in sessions:
                print(f"{session.session_id}: {session.model}")
            ```
        """
        session_summaries = self.session_manager.get_recent_sessions(limit=limit)
        sessions = []
        for summary in session_summaries:
            session = self.session_manager.load_session(summary["session_id"])
            if session:
                sessions.append(session)
        return sessions
