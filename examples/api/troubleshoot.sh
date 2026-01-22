#!/bin/bash
# Comprehensive troubleshooting script for askGPT API

echo "=========================================="
echo "askGPT API Troubleshooting"
echo "=========================================="
echo ""

# 1. Check if container is running
echo "1. Checking container status..."
if podman ps | grep -q askgpt-api; then
    echo "✓ Container is running"
    podman ps | grep askgpt-api
else
    echo "✗ Container is NOT running"
    echo "  Start it with: podman start askgpt-api"
    exit 1
fi
echo ""

# 2. Check what's using port 8000
echo "2. Checking what's using port 8000..."
if command -v lsof > /dev/null 2>&1; then
    PORT_8000=$(lsof -i :8000 2>/dev/null | grep -v COMMAND)
    if [ -n "$PORT_8000" ]; then
        echo "⚠ Port 8000 is in use:"
        echo "$PORT_8000"
    else
        echo "✓ Port 8000 is free"
    fi
elif command -v netstat > /dev/null 2>&1; then
    PORT_8000=$(netstat -tlnp 2>/dev/null | grep :8000 || netstat -tln 2>/dev/null | grep :8000)
    if [ -n "$PORT_8000" ]; then
        echo "⚠ Port 8000 is in use:"
        echo "$PORT_8000"
    else
        echo "✓ Port 8000 is free"
    fi
else
    echo "? Cannot check port (lsof/netstat not available)"
fi
echo ""

# 3. Check port 8010
echo "3. Checking port 8010..."
if command -v lsof > /dev/null 2>&1; then
    PORT_8010=$(lsof -i :8010 2>/dev/null | grep -v COMMAND)
    if [ -n "$PORT_8010" ]; then
        echo "⚠ Port 8010 is in use:"
        echo "$PORT_8010"
    else
        echo "✓ Port 8010 is free"
    fi
fi
echo ""

# 4. Check container logs
echo "4. Recent container logs (last 10 lines)..."
podman logs askgpt-api --tail 10 2>&1 | tail -10
echo ""

# 5. Test health endpoint on different ports
echo "5. Testing health endpoints..."
echo "   Port 8000:"
HEALTH_8000=$(curl -s -w "\nHTTP:%{http_code}" http://localhost:8000/health 2>&1)
HTTP_8000=$(echo "$HEALTH_8000" | grep "HTTP:" | cut -d: -f2)
BODY_8000=$(echo "$HEALTH_8000" | sed '/HTTP:/d')
if [ "$HTTP_8000" = "200" ]; then
    echo "   ✓ Port 8000 responding: $BODY_8000"
else
    echo "   ✗ Port 8000: HTTP $HTTP_8000 - $BODY_8000"
fi

echo "   Port 8010:"
HEALTH_8010=$(curl -s -w "\nHTTP:%{http_code}" http://localhost:8010/api/v1/health 2>&1)
HTTP_8010=$(echo "$HEALTH_8010" | grep "HTTP:" | cut -d: -f2)
BODY_8010=$(echo "$HEALTH_8010" | sed '/HTTP:/d')
if [ "$HTTP_8010" = "200" ]; then
    echo "   ✓ Port 8010 responding: $BODY_8010"
else
    echo "   ✗ Port 8010: HTTP $HTTP_8010"
    if [ -n "$BODY_8010" ]; then
        echo "     Response: $BODY_8010"
    fi
fi
echo ""

# 6. Check container environment variables
echo "6. Container environment variables..."
podman inspect askgpt-api --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E "ASKGPT|OLLAMA" || echo "  (none found)"
echo ""

# 7. Check Ollama on host
echo "7. Checking Ollama on host..."
OLLAMA_HOST=$(curl -s http://localhost:11434/api/tags 2>&1)
if echo "$OLLAMA_HOST" | grep -q "models"; then
    echo "✓ Ollama is running on host"
    MODEL_COUNT=$(echo "$OLLAMA_HOST" | jq '.models | length' 2>/dev/null || echo "?")
    echo "  Models available: $MODEL_COUNT"
else
    echo "✗ Ollama is NOT accessible on host"
    echo "  Response: $OLLAMA_HOST"
    echo "  Start Ollama: ollama serve"
fi
echo ""

# 8. Check config in container
echo "8. Checking config in container..."
CONFIG_CHECK=$(podman exec askgpt-api cat /root/.askgpt/config.yaml 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ Config file exists"
    OLLAMA_BASE=$(echo "$CONFIG_CHECK" | grep -A 2 "ollama:" | grep "api_base" || echo "  (not found)")
    echo "  Ollama api_base: $OLLAMA_BASE"
else
    echo "✗ Cannot read config: $CONFIG_CHECK"
fi
echo ""

# 9. Check network mode
echo "9. Container network mode..."
NETWORK=$(podman inspect askgpt-api --format '{{.HostConfig.NetworkMode}}' 2>&1)
echo "  Network: $NETWORK"
if [ "$NETWORK" = "host" ]; then
    echo "  → Using host network (container shares host network)"
    echo "  → Ollama should be accessible at localhost:11434"
elif [ "$NETWORK" = "bridge" ] || [ "$NETWORK" = "default" ]; then
    echo "  → Using bridge network"
    echo "  → Ollama should be accessible at host.containers.internal:11434"
fi
echo ""

# 10. Recommendations
echo "=========================================="
echo "RECOMMENDATIONS"
echo "=========================================="

if [ "$HTTP_8000" = "200" ] && echo "$BODY_8000" | grep -q "Brainiac"; then
    echo "⚠ Port 8000 is used by another service (Brainiac)"
    echo "  → Use port 8010: podman run ... -e ASKGPT_PORT=8010 ..."
    echo "  → Or stop the other service on port 8000"
fi

if [ "$HTTP_8010" != "200" ]; then
    echo "⚠ Port 8010 is not responding"
    echo "  → Check if ASKGPT_PORT=8010 is set"
    echo "  → Check container logs: podman logs askgpt-api"
fi

if echo "$OLLAMA_HOST" | grep -q "models"; then
    if [ "$NETWORK" = "host" ]; then
        echo "✓ Ollama is accessible, using host network"
        echo "  → Config should use: api_base: http://localhost:11434/v1"
    else
        echo "✓ Ollama is accessible, using bridge network"
        echo "  → Config should use: api_base: http://host.containers.internal:11434/v1"
    fi
else
    echo "✗ Ollama is not accessible"
    echo "  → Start Ollama: ollama serve"
fi

echo ""
echo "=========================================="
echo "Quick Fix Commands"
echo "=========================================="
echo ""
echo "# Stop and restart on port 8010:"
echo "podman stop askgpt-api && podman rm askgpt-api"
echo "podman run -d --name askgpt-api --network=host \\"
echo "  -v \$(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \\"
echo "  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \\"
echo "  -e ASKGPT_PORT=8010 \\"
echo "  askgpt-api"
echo ""
echo "# Test:"
echo "curl http://localhost:8010/api/v1/health"
echo ""
