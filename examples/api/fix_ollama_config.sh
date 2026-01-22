#!/bin/bash
# Fix Ollama config in running container

echo "=== Fixing Ollama Config ==="
echo ""

# Check current config
echo "1. Current Ollama config:"
podman exec askgpt-api cat /root/.askgpt/config.yaml | grep -A 3 "ollama:" | head -5
echo ""

# Check if using host network
echo "2. Checking network mode..."
NETWORK=$(podman inspect askgpt-api --format '{{.HostConfig.NetworkMode}}')
echo "Network mode: $NETWORK"
echo ""

if [ "$NETWORK" = "host" ]; then
    echo "Container is using host network - should use localhost"
    echo "3. Updating config to use localhost..."
    podman exec askgpt-api sed -i 's|api_base: http://host.containers.internal:11434/v1|api_base: http://localhost:11434/v1|g' /root/.askgpt/config.yaml
    echo "✓ Updated to localhost"
else
    echo "Container is using bridge network - should use host.containers.internal"
    echo "3. Updating config to use host.containers.internal..."
    podman exec askgpt-api sed -i 's|api_base: http://localhost:11434/v1|api_base: http://host.containers.internal:11434/v1|g' /root/.askgpt/config.yaml
    echo "✓ Updated to host.containers.internal"
fi

echo ""
echo "4. Updated config:"
podman exec askgpt-api cat /root/.askgpt/config.yaml | grep -A 3 "ollama:" | head -5
echo ""
echo "=== Config fixed ==="
echo "You may need to restart the container for changes to take effect,"
echo "or the next request should use the updated config."
