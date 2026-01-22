#!/usr/bin/env python3
"""
Example: Using askGPT Server-Sent Events (SSE) API

This example demonstrates how to interact with the askGPT web server
using Server-Sent Events for streaming responses.
"""

import json
import urllib.parse
from typing import Optional

import requests


def chat_stream_sse(
    message: str,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
    base_url: str = "http://localhost:8000/api/v1/chat/stream"
):
    """
    Send a chat message via SSE and stream the response.
    
    Args:
        message: The user's message
        session_id: Optional session ID to continue conversation
        model: Optional model override
        base_url: Base URL for the SSE endpoint
        
    Yields:
        Response chunks as they arrive
    """
    # Build query parameters
    params = {"message": message}
    if session_id:
        params["session_id"] = session_id
    if model:
        params["model"] = model
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    # Make request with stream=True
    response = requests.get(url, stream=True, headers={"Accept": "text/event-stream"})
    response.raise_for_status()
    
    # Parse SSE stream
    buffer = ""
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        
        if line.startswith("data: "):
            data_str = line[6:]  # Remove "data: " prefix
            try:
                data = json.loads(data_str)
                chunk = data.get("chunk", "")
                done = data.get("done", False)
                
                if chunk:
                    yield chunk
                
                if done:
                    break
                    
            except json.JSONDecodeError:
                continue


def main():
    """Example usage of the SSE API."""
    print("=== askGPT SSE API Example ===\n")
    
    # Send a message and stream response
    print("1. Sending message via SSE (streaming):")
    print("   Message: 'Write a haiku about programming'")
    print("   Response (streaming): ", end="", flush=True)
    
    full_response = ""
    for chunk in chat_stream_sse("Write a haiku about programming"):
        print(chunk, end="", flush=True)
        full_response += chunk
    
    print("\n\n=== Example complete ===")


if __name__ == "__main__":
    main()
