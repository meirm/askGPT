#!/bin/bash
# Example: Using askGPT API with curl
# This script demonstrates how to interact with the askGPT web server using curl

BASE_URL="http://localhost:8000/api/v1"

echo "=== askGPT REST API Examples with curl ===\n"

# Health check
echo "1. Health check:"
curl -s "${BASE_URL}/health" | jq .
echo "\n"

# Create a session
echo "2. Creating a new session:"
SESSION_RESPONSE=$(curl -s -X POST "${BASE_URL}/sessions" \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "gpt-oss:20b"}')
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Session ID: $SESSION_ID"
echo "\n"

# Send a chat message
echo "3. Sending a chat message:"
curl -s -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello! Can you tell me a short joke?\", \"session_id\": \"$SESSION_ID\"}" | jq .
echo "\n"

# Continue conversation
echo "4. Continuing the conversation:"
curl -s -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"That's funny! Can you explain why it's funny?\", \"session_id\": \"$SESSION_ID\"}" | jq .
echo "\n"

# List sessions
echo "5. Listing recent sessions:"
curl -s "${BASE_URL}/sessions?limit=5" | jq .
echo "\n"

# Get session details
echo "6. Getting session details:"
curl -s "${BASE_URL}/sessions/$SESSION_ID" | jq .
echo "\n"

# SSE streaming example
echo "7. SSE streaming example:"
echo "Message: 'Write a haiku about programming'"
curl -s -N "${BASE_URL}/chat/stream?message=Write%20a%20haiku%20about%20programming" | \
  grep -E "^data: " | sed 's/^data: //' | jq -r '.chunk' | tr -d '\n'
echo "\n\n"

echo "=== Examples complete ==="
