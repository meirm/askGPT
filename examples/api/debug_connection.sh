#!/bin/bash
# Debug script to check askGPT API and Ollama connectivity

echo "=== askGPT API Connection Debug ==="
echo ""

# Check if API is running
echo "1. Checking API health..."
HEALTH=$(curl -s http://localhost:8000/api/v1/health)
echo "$HEALTH" | jq .
echo ""

# Check available models
echo "2. Checking available models from API..."
MODELS=$(curl -s http://localhost:8000/api/v1/models)
echo "$MODELS" | jq .
echo ""

# Check Ollama on host
echo "3. Checking Ollama on host (localhost)..."
OLLAMA_HOST=$(curl -s http://localhost:11434/api/tags 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ Ollama is accessible on host"
    echo "$OLLAMA_HOST" | jq -r '.models[].name' | head -5
else
    echo "✗ Cannot reach Ollama on host: $OLLAMA_HOST"
fi
echo ""

# Check if container can reach host Ollama
echo "4. Testing container connectivity to Ollama..."
CONTAINER_TEST=$(podman exec askgpt-api curl -s http://host.containers.internal:11434/api/tags 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ Container can reach Ollama via host.containers.internal"
    echo "$CONTAINER_TEST" | jq -r '.models[].name' | head -5
else
    echo "✗ Container cannot reach Ollama: $CONTAINER_TEST"
fi
echo ""

# Check config in container
echo "5. Checking config in container..."
CONFIG=$(podman exec askgpt-api cat /root/.askgpt/config.yaml 2>&1)
if [ $? -eq 0 ]; then
    echo "Config file exists. Ollama API base:"
    echo "$CONFIG" | grep -A 5 "ollama:" | grep api_base || echo "No api_base found for ollama"
else
    echo "✗ Cannot read config: $CONFIG"
fi
echo ""

# Check environment variables
echo "6. Checking environment variables in container..."
podman exec askgpt-api env | grep -E "OLLAMA|ASKGPT" || echo "No relevant env vars found"
echo ""

echo "=== Debug complete ==="
echo ""
echo "If Ollama is not accessible:"
echo "  1. Make sure Ollama is running: ollama serve"
echo "  2. Test: curl http://localhost:11434/api/tags"
echo "  3. Check container logs: podman logs askgpt-api"
echo ""
echo "If container can't reach Ollama:"
echo "  1. Verify OLLAMA_API_BASE is set correctly"
echo "  2. Try: podman exec askgpt-api curl http://host.containers.internal:11434/api/tags"
echo "  3. Check if you need to use a different host address"
