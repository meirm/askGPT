#!/bin/bash
# Quick fix for Ollama config in running container

echo "=== Fixing Ollama Config ==="
echo ""

# Update the config to use host.containers.internal (which we know works)
echo "Updating Ollama api_base to host.containers.internal..."
podman exec askgpt-api sed -i 's|api_base: http://localhost:11434/v1|api_base: http://host.containers.internal:11434/v1|g' /root/.askgpt/config.yaml

echo "✓ Config updated"
echo ""

# Verify the change
echo "Updated config:"
podman exec askgpt-api grep -A 2 "ollama:" /root/.askgpt/config.yaml | grep api_base
echo ""

echo "=== Done ==="
echo "The config is now fixed. Try your chat request again!"
