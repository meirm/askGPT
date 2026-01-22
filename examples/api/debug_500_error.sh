#!/bin/bash
# Debug script for 500 Internal Server Error

BASE_URL="${BASE_URL:-http://localhost:8010/api/v1}"

echo "=== Debugging 500 Internal Server Error ==="
echo ""

# 1. Check health
echo "1. Health check..."
curl -s "${BASE_URL}/health" | jq .
echo ""

# 2. Check models endpoint
echo "2. Models endpoint..."
curl -s "${BASE_URL}/models" | jq .
echo ""

# 3. Try a chat request and capture full error
echo "3. Testing chat endpoint with verbose output..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

echo "HTTP Status: $HTTP_CODE"
echo "Response body:"
echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
echo ""

# 4. Check container logs
echo "4. Recent container logs (last 30 lines)..."
echo "Run this manually: podman logs askgpt-api --tail 30"
echo ""

# 5. Check Ollama connectivity from container
echo "5. Testing Ollama connectivity from container..."
echo "Run this manually: podman exec askgpt-api curl -s http://localhost:11434/api/tags"
echo ""

# 6. Check config
echo "6. Checking Ollama config in container..."
echo "Run this manually: podman exec askgpt-api cat /root/.askgpt/config.yaml | grep -A 5 ollama"
echo ""

echo "=== Debug info collected ==="
echo ""
echo "To see full error details, check container logs:"
echo "  podman logs askgpt-api --tail 50"
