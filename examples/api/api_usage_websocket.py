#!/usr/bin/env python3
"""
Example: Using askGPT WebSocket API

This example demonstrates how to interact with the askGPT web server
using WebSocket for streaming responses.
"""

import asyncio
import json
from typing import Optional

import websockets


async def chat_stream(
    message: str,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    uri: str = "ws://localhost:8000/api/v1/chat/stream"
):
    """
    Send a chat message via WebSocket and stream the response.
    
    Args:
        message: The user's message
        session_id: Optional session ID to continue conversation
        model: Optional model override
        uri: WebSocket URI
        
    Yields:
        Response chunks as they arrive
    """
    async with websockets.connect(uri) as websocket:
        # Send message
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        if model:
            payload["model"] = model
        
        await websocket.send(json.dumps(payload))
        
        # Receive streaming chunks
        full_response = ""
        current_session_id = None
        
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)
                
                if "error" in data:
                    print(f"Error: {data['error']}")
                    break
                
                chunk = data.get("chunk", "")
                done = data.get("done", False)
                current_session_id = data.get("session_id")
                
                if chunk:
                    full_response += chunk
                    yield chunk
                
                if done:
                    break
                    
            except websockets.exceptions.ConnectionClosed:
                break
        
        return full_response, current_session_id


async def main():
    """Example usage of the WebSocket API."""
    print("=== askGPT WebSocket API Example ===\n")
    
    # First message
    print("1. Sending first message (streaming):")
    print("   Message: 'Tell me a short story about a robot'")
    print("   Response (streaming): ", end="", flush=True)
    
    full_response = ""
    session_id = None
    
    async for chunk in chat_stream("Tell me a short story about a robot"):
        print(chunk, end="", flush=True)
        full_response += chunk
    
    print("\n")
    
    # Continue conversation (if we had a session_id)
    if session_id:
        print(f"\n2. Continuing conversation (session: {session_id}):")
        print("   Message: 'Make it funnier'")
        print("   Response (streaming): ", end="", flush=True)
        
        async for chunk in chat_stream("Make it funnier", session_id=session_id):
            print(chunk, end="", flush=True)
    
    print("\n\n=== Example complete ===")


if __name__ == "__main__":
    asyncio.run(main())
