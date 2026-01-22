#!/bin/bash
# Hello World example for askGPT API server
# This demonstrates the simplest possible interaction with the API

BASE_URL="http://localhost:8010/api/v1"

echo "=== askGPT API Hello World Example ==="
echo ""

# Step 1: Health check
echo "1. Checking API health..."
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Health check failed with HTTP $HTTP_CODE"
    echo "Response: $HEALTH_BODY"
    echo ""
    echo "Is the server running? Check: podman ps | grep askgpt-api"
    exit 1
fi

echo "$HEALTH_BODY" | jq . 2>/dev/null || echo "$HEALTH_BODY"
echo ""
echo ""

# Step 2: Send a simple "Hello" message
echo "2. Sending 'Hello' message to askGPT..."
echo ""

RESPONSE=$(curl -s -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Can you respond with a simple greeting?"
  }')

# Display the response
echo "Response:"
if echo "$RESPONSE" | jq . > /dev/null 2>&1; then
    echo "$RESPONSE" | jq .
else
    echo "Raw response (not JSON):"
    echo "$RESPONSE"
fi
echo ""

# Check for errors
if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo "ERROR: $(echo "$RESPONSE" | jq -r '.error')"
    exit 1
elif echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "ERROR: $(echo "$RESPONSE" | jq -r '.detail')"
    exit 1
fi

# Extract just the response text
echo "Response text:"
echo "$RESPONSE" | jq -r '.response' 2>/dev/null || echo "(no response field)"
echo ""

# Extract session ID for follow-up
SESSION_ID=$(echo "$RESPONSE" | jq -r '.session_id' 2>/dev/null)
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    echo "Session ID: $SESSION_ID"
else
    echo "Session ID: (none)"
fi
echo ""

# Step 3: Continue the conversation
echo "3. Continuing the conversation..."
echo ""

RESPONSE2=$(curl -s -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"What is 2+2?\",
    \"session_id\": \"$SESSION_ID\"
  }")

echo "Response:"
echo "$RESPONSE2" | jq -r '.response'
echo ""

echo "=== Example complete ==="
