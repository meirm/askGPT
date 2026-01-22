#!/bin/bash
# Simple test script for askGPT API chat endpoint

BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"

echo "=== Testing askGPT API Chat Endpoint ==="
echo "Using: $BASE_URL"
echo ""

# Health check first
echo "1. Health check..."
HEALTH=$(curl -s "${BASE_URL}/health")
echo "$HEALTH" | jq .
echo ""

# Check available models
echo "2. Available models..."
MODELS=$(curl -s "${BASE_URL}/models")
echo "$MODELS" | jq .
echo ""

# Send a simple chat message
echo "3. Sending chat message..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Say hi back in one sentence."
  }')

echo "Full response:"
echo "$RESPONSE" | jq .
echo ""

# Check for errors
if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo "ERROR FOUND:"
    echo "$RESPONSE" | jq -r '.error'
    echo ""
    echo "Check container logs: podman logs askgpt-api"
elif echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "ERROR DETAIL:"
    echo "$RESPONSE" | jq -r '.detail'
    echo ""
    echo "Check container logs: podman logs askgpt-api"
else
    echo "Response text:"
    echo "$RESPONSE" | jq -r '.response'
    echo ""
    SESSION_ID=$(echo "$RESPONSE" | jq -r '.session_id')
    echo "Session ID: $SESSION_ID"
fi
