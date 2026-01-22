#!/usr/bin/env python3
"""
Example: Using askGPT REST API

This example demonstrates how to interact with the askGPT web server
using standard HTTP REST API calls.
"""

import json
import requests
from typing import Optional

# Base URL for the API server
BASE_URL = "http://localhost:8000/api/v1"


def chat(message: str, session_id: Optional[str] = None, model: Optional[str] = None) -> dict:
    """
    Send a chat message to the API.
    
    Args:
        message: The user's message
        session_id: Optional session ID to continue conversation
        model: Optional model override
        
    Returns:
        Response dictionary with 'response', 'session_id', and 'metadata'
    """
    url = f"{BASE_URL}/chat"
    payload = {
        "message": message,
    }
    
    if session_id:
        payload["session_id"] = session_id
    if model:
        payload["model"] = model
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def create_session(provider: Optional[str] = None, model: Optional[str] = None) -> dict:
    """Create a new chat session."""
    url = f"{BASE_URL}/sessions"
    payload = {}
    if provider:
        payload["provider"] = provider
    if model:
        payload["model"] = model
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def list_sessions(limit: int = 10) -> list:
    """List recent sessions."""
    url = f"{BASE_URL}/sessions"
    response = requests.get(url, params={"limit": limit})
    response.raise_for_status()
    return response.json()


def get_session(session_id: str) -> dict:
    """Get session details."""
    url = f"{BASE_URL}/sessions/{session_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def health_check() -> dict:
    """Check API health."""
    url = f"{BASE_URL}/health"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def main():
    """Example usage of the REST API."""
    print("=== askGPT REST API Example ===\n")
    
    # Check health
    print("1. Health check:")
    health = health_check()
    print(f"   Status: {health['status']}, Version: {health['version']}\n")
    
    # Create a session
    print("2. Creating a new session:")
    session = create_session(provider="ollama", model="gpt-oss:20b")
    session_id = session["session_id"]
    print(f"   Session ID: {session_id}\n")
    
    # Send a chat message
    print("3. Sending a chat message:")
    response = chat("Hello! Can you tell me a short joke?", session_id=session_id)
    print(f"   Response: {response['response'][:100]}...")
    print(f"   Session ID: {response['session_id']}\n")
    
    # Continue conversation
    print("4. Continuing the conversation:")
    response = chat("That's funny! Can you explain why it's funny?", session_id=session_id)
    print(f"   Response: {response['response'][:100]}...\n")
    
    # List sessions
    print("5. Listing recent sessions:")
    sessions = list_sessions(limit=5)
    for sess in sessions:
        print(f"   - {sess['session_id']}: {sess['model']} ({sess['message_count']} messages)")
    
    print("\n=== Example complete ===")


if __name__ == "__main__":
    main()
