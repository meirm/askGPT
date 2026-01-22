#!/usr/bin/env python3
"""
Example: Using askGPT Python Client Library

This example demonstrates how to use the AskGPTClient class directly
in Python applications without making HTTP requests.
"""

import asyncio
from askgpt import AskGPTClient


async def main():
    """Example usage of the Python client library."""
    print("=== askGPT Python Client Example ===\n")
    
    # Initialize client
    # Client will automatically load config from ~/.askgpt/config.yaml
    client = AskGPTClient()
    
    print("1. Client initialized with defaults from config")
    print(f"   Default provider: {client.default_provider}")
    print(f"   Default model: {client.default_model}\n")
    
    # Send a chat message
    print("2. Sending a chat message:")
    response = await client.chat("What is 2+2? Explain your reasoning.")
    
    if response.success:
        print(f"   Response: {response.result}\n")
    else:
        print(f"   Error: {response.error}\n")
    
    # Create a session explicitly
    print("3. Creating a new session:")
    session = client.create_session(provider="ollama", model="gpt-oss:20b")
    session_id = session.session_id
    print(f"   Session ID: {session_id}\n")
    
    # Use the session for a conversation
    print("4. Multi-turn conversation:")
    
    # First message
    response = await client.chat(
        "Hello! I'm learning Python. Can you help me?",
        session_id=session_id
    )
    if response.success:
        print(f"   User: Hello! I'm learning Python. Can you help me?")
        print(f"   Bot: {response.result[:100]}...\n")
    
    # Second message (continues conversation)
    response = await client.chat(
        "What's the difference between a list and a tuple?",
        session_id=session_id
    )
    if response.success:
        print(f"   User: What's the difference between a list and a tuple?")
        print(f"   Bot: {response.result[:100]}...\n")
    
    # Stream responses
    print("5. Streaming response:")
    print("   Message: 'Count from 1 to 5'")
    print("   Response (streaming): ", end="", flush=True)
    
    async for chunk in client.chat_stream("Count from 1 to 5", session_id=session_id):
        print(chunk, end="", flush=True)
    
    print("\n")
    
    # List sessions
    print("6. Listing recent sessions:")
    sessions = client.list_sessions(limit=5)
    for sess in sessions:
        print(f"   - {sess.session_id}: {sess.model} ({len(sess.conversation)} messages)")
    
    print("\n=== Example complete ===")


if __name__ == "__main__":
    asyncio.run(main())
