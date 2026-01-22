#!/usr/bin/env python3
"""
Example usage of askGPT as a library.

This demonstrates how to use AskGPTClient in your own Python applications.
"""

import asyncio
from askgpt import AskGPTClient


async def example_basic_chat():
    """Example: Basic chat interaction."""
    print("=" * 60)
    print("Example 1: Basic Chat")
    print("=" * 60)
    
    client = AskGPTClient()
    
    response = await client.chat("Hello, how are you?")
    
    if response.success:
        print(f"Response: {response.result}")
        print(f"Execution time: {response.execution_time_seconds:.2f}s")
    else:
        print(f"Error: {response.error}")


async def example_streaming_chat():
    """Example: Streaming chat responses."""
    print("\n" + "=" * 60)
    print("Example 2: Streaming Chat")
    print("=" * 60)
    
    client = AskGPTClient()
    
    print("Response (streaming): ", end="", flush=True)
    async for chunk in client.chat_stream("Tell me a short story about a robot"):
        print(chunk, end="", flush=True)
    print()  # New line after streaming


async def example_session_management():
    """Example: Session management for multi-turn conversations."""
    print("\n" + "=" * 60)
    print("Example 3: Session Management")
    print("=" * 60)
    
    client = AskGPTClient()
    
    # Create a session
    session = client.create_session(provider="ollama", model="gpt-oss:20b")
    print(f"Created session: {session.session_id}")
    
    # First message
    response1 = await client.chat(
        "My name is Alice and I like programming",
        session_id=session.session_id,
    )
    print(f"First response: {response1.result[:100]}...")
    
    # Follow-up message (uses same session)
    response2 = await client.chat(
        "What's my name and what do I like?",
        session_id=session.session_id,
    )
    print(f"Follow-up response: {response2.result[:100]}...")
    
    # List sessions
    sessions = client.list_sessions(limit=5)
    print(f"\nRecent sessions: {len(sessions)}")
    for s in sessions:
        print(f"  - {s.session_id}: {s.model} ({len(s.conversation)} messages)")


async def example_with_parameters():
    """Example: Using additional parameters."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Parameters")
    print("=" * 60)
    
    client = AskGPTClient()
    
    response = await client.chat(
        "Explain quantum computing in simple terms",
        temperature=0.7,  # More creative
        max_tokens=500,   # Limit response length
        read_only=True,   # Safe mode - no file operations
    )
    
    if response.success:
        print(f"Response: {response.result[:200]}...")
        print(f"Metadata: {response.metadata}")


async def example_error_handling():
    """Example: Error handling."""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)
    
    client = AskGPTClient()
    
    # This might fail if Ollama is not running
    response = await client.chat(
        "Test message",
        provider="ollama",
        model="gpt-oss:20b",
    )
    
    if response.success:
        print("Success!")
        print(f"Response: {response.result}")
    else:
        print(f"Error occurred: {response.error}")
        print("This is expected if Ollama is not running locally")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("askGPT Library Usage Examples")
    print("=" * 60)
    print("\nNote: These examples use Ollama by default (no API keys required)")
    print("Make sure Ollama is running: ollama serve\n")
    
    try:
        await example_basic_chat()
        await example_streaming_chat()
        await example_session_management()
        await example_with_parameters()
        await example_error_handling()
        
        print("\n" + "=" * 60)
        print("Examples completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure Ollama is running or configure a different provider")


if __name__ == "__main__":
    asyncio.run(main())
