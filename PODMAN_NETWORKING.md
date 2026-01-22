# Podman Networking for askGPT API

## The Problem

When running askGPT API in Podman, the container needs to access Ollama running on the host. The `host.containers.internal` address may not work by default in Podman.

## Solutions

### Solution 1: Use Host Network (Recommended for Local Development)

Run the container with `--network=host` to share the host's network:

```bash
podman run -d \
  --name askgpt-api \
  --network=host \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://localhost:11434/v1 \
  askgpt-api
```

**Pros:**
- Simplest solution
- Works immediately
- No network configuration needed

**Cons:**
- Less isolation (shares host network)
- Port conflicts possible

### Solution 2: Use host.containers.internal with Podman 4.1+

If you have Podman 4.1+, `host.containers.internal` should work:

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api
```

**Check your Podman version:**
```bash
podman --version
```

### Solution 3: Use Host IP Address

Find your host's IP and use it directly:

```bash
# Get host IP (macOS/Linux)
HOST_IP=$(ip route get 1.1.1.1 | awk '{print $7; exit}' 2>/dev/null || \
          ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

# Or on macOS, use:
HOST_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "192.168.1.1")

podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://${HOST_IP}:11434/v1 \
  askgpt-api
```

### Solution 4: Run Ollama in Podman Too

Run both Ollama and askGPT in Podman containers on the same network:

```bash
# Create a network
podman network create askgpt-net

# Run Ollama
podman run -d \
  --name ollama \
  --network askgpt-net \
  -p 11434:11434 \
  -v ollama-data:/root/.ollama \
  docker.io/ollama/ollama:latest

# Run askGPT API
podman run -d \
  --name askgpt-api \
  --network askgpt-net \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://ollama:11434/v1 \
  askgpt-api
```

## Testing Connectivity

### From Host
```bash
curl http://localhost:11434/api/tags
```

### From Container (with host network)
```bash
podman exec askgpt-api curl http://localhost:11434/api/tags
```

### From Container (with bridge network)
```bash
podman exec askgpt-api curl http://host.containers.internal:11434/api/tags
```

## Quick Fix for Current Issue

If you're getting connection errors, try this:

```bash
# Stop current container
podman stop askgpt-api
podman rm askgpt-api

# Run with host network
podman run -d \
  --name askgpt-api \
  --network=host \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://localhost:11434/v1 \
  askgpt-api

# Test
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

## Recommended Setup

For local development, use **Solution 1** (host network):

```bash
podman run -d \
  --name askgpt-api \
  --network=host \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://localhost:11434/v1 \
  askgpt-api
```

This is the simplest and most reliable for local development.
