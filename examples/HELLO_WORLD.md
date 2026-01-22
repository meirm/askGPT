# Hello World - askGPT API Examples

Simple examples to get started with the askGPT API server.

## Prerequisites

- askGPT API server running on `http://localhost:8000`
- `curl` installed
- `jq` installed (optional, for pretty JSON output)

## Quick Start

### 1. Health Check

Verify the server is running:

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.4"
}
```

### 2. Simple Hello Message

Send a basic chat message:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

### 3. Hello World with Pretty Output

Using `jq` for formatted output:

```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! Can you respond with a simple greeting?"}' \
  | jq .
```

### 4. Extract Just the Response Text

```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}' \
  | jq -r '.response'
```

### 5. Complete Hello World Script

Run the included script:

```bash
./examples/curl_hello_world.sh
```

Or manually:

```bash
# Health check
curl http://localhost:8000/api/v1/health | jq .

# Send message
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}' | jq .
```

## Response Format

A successful response looks like:

```json
{
  "response": "Hello! How can I help you today?",
  "session_id": "session_20240101_120000_abc123",
  "metadata": {
    "execution_time": 1.23,
    "tokens_used": 15
  },
  "success": true
}
```

## Multi-Turn Conversation

Continue a conversation using the session ID:

```bash
# First message
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}')

# Extract session ID
SESSION_ID=$(echo "$RESPONSE" | jq -r '.session_id')

# Continue conversation
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What is 2+2?\", \"session_id\": \"$SESSION_ID\"}" \
  | jq -r '.response'
```

## Without jq

If you don't have `jq` installed:

```bash
# Simple POST request
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

The response will be in JSON format (not pretty-printed).

## Troubleshooting

### Connection Error

If you get `"Agent SDK execution failed: Connection error."`:

1. **Check if Ollama is running on the host:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Check if container can reach Ollama:**
   ```bash
   podman exec askgpt-api curl http://host.containers.internal:11434/api/tags
   ```

3. **Run the debug script:**
   ```bash
   ./examples/debug_connection.sh
   ```

4. **Check container logs:**
   ```bash
   podman logs askgpt-api
   ```

5. **Verify OLLAMA_API_BASE is set:**
   ```bash
   podman exec askgpt-api env | grep OLLAMA
   ```

6. **Check the config file:**
   ```bash
   podman exec askgpt-api cat /root/.askgpt/config.yaml | grep -A 3 ollama
   ```

### Connection Refused

Make sure the server is running:
```bash
podman ps | grep askgpt-api
```

### Empty Response

Check the server logs:
```bash
podman logs askgpt-api
```

### Timeout

The request might be taking longer if using a local model. Wait a bit longer or check if Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

## Next Steps

- See `examples/README_API_USAGE.md` for more advanced examples
- Check `examples/api_usage_*.py` for Python examples
- Review `examples/CONFIG_MOUNTING.md` for configuration options
