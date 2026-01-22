#!/bin/bash
# Simple API test without jq dependency

BASE_URL="${BASE_URL:-http://localhost:8010/api/v1}"

echo "=== Simple API Test ==="
echo "Testing: $BASE_URL"
echo ""

# Test 1: Health check (no jq needed)
echo "1. Health check (raw curl)..."
curl -v "${BASE_URL}/health" 2>&1 | grep -E "(HTTP|status|healthy)"
echo ""
echo ""

# Test 2: Health check with jq if available
if command -v jq > /dev/null 2>&1; then
    echo "2. Health check (with jq)..."
    curl -s "${BASE_URL}/health" | jq .
else
    echo "2. Health check (jq not available, showing raw)..."
    curl -s "${BASE_URL}/health"
fi
echo ""
echo ""

# Test 3: Chat request
echo "3. Sending chat request..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}')

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

echo "HTTP Status: $HTTP_STATUS"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
    if command -v jq > /dev/null 2>&1; then
        echo "Response:"
        echo "$BODY" | jq .
        echo ""
        echo "Response text:"
        echo "$BODY" | jq -r '.response'
    else
        echo "Response (raw):"
        echo "$BODY"
    fi
else
    echo "ERROR: Request failed"
    echo "Response:"
    echo "$BODY"
fi
