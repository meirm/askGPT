"""
Test helper functions for API tests.
"""

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

from askgpt.modules.data_types import PromptNanoAgentResponse


def create_test_client(
    default_provider: str = "ollama",
    default_model: str = "gpt-oss:20b",
    **kwargs,
) -> Any:
    """
    Create a configured test client.
    
    Args:
        default_provider: Default provider to use
        default_model: Default model to use
        **kwargs: Additional arguments for AskGPTClient
        
    Returns:
        Configured AskGPTClient instance
    """
    from askgpt.api import AskGPTClient
    from askgpt.modules.session_manager import SessionManager
    import tempfile
    from pathlib import Path
    
    temp_dir = Path(tempfile.mkdtemp())
    session_manager = SessionManager(storage_dir=temp_dir)
    
    return AskGPTClient(
        default_provider=default_provider,
        default_model=default_model,
        session_manager=session_manager,
        **kwargs,
    )


async def wait_for_response(
    coro: Any, timeout: float = 30.0
) -> Any:
    """
    Wait for an async response with timeout.
    
    Args:
        coro: Coroutine to await
        timeout: Maximum time to wait in seconds
        
    Returns:
        Result of the coroutine
        
    Raises:
        asyncio.TimeoutError: If the operation times out
    """
    return await asyncio.wait_for(coro, timeout=timeout)


async def capture_streaming(
    stream: AsyncIterator[str],
    max_chunks: Optional[int] = None,
) -> List[str]:
    """
    Capture streaming output into a list.
    
    Args:
        stream: Async iterator of strings
        max_chunks: Maximum number of chunks to capture (None for all)
        
    Returns:
        List of captured chunks
    """
    chunks = []
    count = 0
    
    async for chunk in stream:
        chunks.append(chunk)
        count += 1
        if max_chunks is not None and count >= max_chunks:
            break
    
    return chunks


def assert_response_format(
    response: PromptNanoAgentResponse,
    expected_success: bool = True,
    require_result: bool = True,
) -> None:
    """
    Validate response structure.
    
    Args:
        response: Response to validate
        expected_success: Whether response should be successful
        require_result: Whether result field is required
        
    Raises:
        AssertionError: If response format is invalid
    """
    assert isinstance(response, PromptNanoAgentResponse), "Response must be PromptNanoAgentResponse"
    assert response.success == expected_success, f"Expected success={expected_success}, got {response.success}"
    
    if expected_success and require_result:
        assert response.result is not None, "Response result should not be None"
        assert isinstance(response.result, str), "Response result should be a string"
    
    if not expected_success:
        assert response.error is not None, "Error response should have error message"
    
    assert response.metadata is not None, "Response should have metadata"
    assert isinstance(response.metadata, dict), "Response metadata should be a dictionary"


def create_mock_session(
    session_id: str = "test_session_123",
    provider: str = "ollama",
    model: str = "gpt-oss:20b",
    message_count: int = 0,
) -> Dict[str, Any]:
    """
    Create test session data.
    
    Args:
        session_id: Session identifier
        provider: Provider name
        model: Model name
        message_count: Number of messages in conversation
        
    Returns:
        Dictionary with session data
    """
    from datetime import datetime
    
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "conversation": [],
        "metadata": {
            "total_tokens": 0,
            "total_cost": 0.0,
            "message_count": message_count,
        },
    }
