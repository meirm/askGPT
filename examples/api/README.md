# askGPT API Examples

This directory contains examples demonstrating how to use the askGPT REST API server.

## Quick Start

1. **Start the API server:**
   ```bash
   # Using Podman (recommended)
   podman run -d --name askgpt-api --replace \
     -p 8010:8010 \
     -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
     -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
     -e ASKGPT_PORT=8010 \
     askgpt-api
   
   # Or using the CLI
   askgpt serve --host 0.0.0.0 --port 8010
   ```

2. **Test the API:**
   ```bash
   curl http://localhost:8010/api/v1/health
   ```

## Examples

### 1. Hello World (`curl_hello_world.sh`)

Simple "Hello World" example using curl:

```bash
./examples/api/curl_hello_world.sh
```

**Features:**
- Health check
- Basic chat message
- Multi-turn conversation
- Session management

### 2. REST API (`api_usage_rest.py`)

Python example using the `requests` library:

```bash
python examples/api/api_usage_rest.py
```

**Features:**
- Create sessions
- Send chat messages
- List sessions
- Get session details

### 3. WebSocket Streaming (`api_usage_websocket.py`)

Real-time streaming using WebSocket:

```bash
python examples/api/api_usage_websocket.py
```

**Features:**
- Real-time response streaming
- Low-latency communication
- Session continuation

### 4. Server-Sent Events (`api_usage_sse.py`)

HTTP-based streaming using SSE:

```bash
python examples/api/api_usage_sse.py
```

**Features:**
- HTTP-based streaming
- Works through proxies
- Simple to use

### 5. Python Client Library (`api_usage_client.py`)

Direct Python library usage (no HTTP):

```bash
python examples/api/api_usage_client.py
```

**Features:**
- No HTTP overhead
- Direct API access
- Type-safe

### 6. cURL Examples (`api_usage_curl.sh`)

Command-line examples using curl:

```bash
./examples/api/api_usage_curl.sh
```

**Features:**
- No dependencies (just curl and jq)
- Easy to understand
- Good for testing

### 7. Test Scripts

- **`test_chat.sh`** - Test chat endpoint with error handling
- **`test_api_simple.sh`** - Simple test without jq dependency
- **`debug_connection.sh`** - Debug connectivity issues
- **`troubleshoot.sh`** - Comprehensive troubleshooting

## API Endpoints

### REST Endpoints

- `GET /api/v1/health` - Health check
- `POST /api/v1/chat` - Send chat message
- `GET /api/v1/sessions` - List sessions
- `GET /api/v1/sessions/{session_id}` - Get session details
- `POST /api/v1/sessions` - Create new session
- `DELETE /api/v1/sessions/{session_id}` - Delete session
- `GET /api/v1/models` - List available models

### Streaming Endpoints

- `WS /api/v1/chat/stream` - WebSocket streaming
- `GET /api/v1/chat/stream` - Server-Sent Events streaming

## Request/Response Formats

### Chat Request

```json
{
  "message": "Hello, how are you?",
  "session_id": "optional-session-id",
  "model": "optional-model-override",
  "provider": "optional-provider-override",
  "temperature": 0.7,
  "max_tokens": 1000,
  "agent_name": "optional-agent-name",
  "read_only": false
}
```

### Chat Response

```json
{
  "response": "I'm doing well, thank you!",
  "session_id": "session-id",
  "metadata": {
    "execution_time": 1.23,
    "tokens_used": 150,
    "model": "gpt-oss:20b",
    "provider": "ollama"
  },
  "success": true
}
```

## Configuration

The API server loads configuration from:
1. `ASKGPT_CONFIG_PATH` environment variable
2. `/root/.askgpt/config_orig.yaml` (recommended mount location)
3. `/app/config/config_orig.yaml` (alternative location)
4. Default configuration

See `../CONFIG_MOUNTING.md` for detailed configuration instructions.

## Docker/Podman Deployment

### Quick Start

```bash
# Build the image
podman build -f Dockerfile.api -t askgpt-api .

# Run with config
podman run -d --name askgpt-api \
  -p 8010:8010 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  -e ASKGPT_PORT=8010 \
  askgpt-api
```

### Environment Variables

- `ASKGPT_HOST` - Host to bind to (default: `0.0.0.0`)
- `ASKGPT_PORT` - Port to bind to (default: `8000`)
- `ASKGPT_WORKERS` - Number of worker processes (default: `1`)
- `ASKGPT_RELOAD` - Enable auto-reload (default: `false`)
- `OLLAMA_API_BASE` - Ollama API URL
  - Podman: `http://host.containers.internal:11434/v1`
  - Docker: `http://host.docker.internal:11434/v1`

## Troubleshooting

### Connection Errors

If you get connection errors:

1. **Check if Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Check container connectivity:**
   ```bash
   podman exec askgpt-api python3 -c "import urllib.request; r = urllib.request.urlopen('http://host.containers.internal:11434/api/tags'); print('OK')"
   ```

3. **Run troubleshooting script:**
   ```bash
   ./examples/api/troubleshoot.sh
   ```

### Port Issues

- **Port already in use:** Change `ASKGPT_PORT` or stop the conflicting service
- **Port not accessible:** Use `-p 8010:8010` for bridge network (Podman on macOS)

### Config Issues

- **Config not loading:** Check mount path and file permissions
- **Wrong Ollama URL:** Verify `OLLAMA_API_BASE` matches your network setup

## Documentation

- **`../HELLO_WORLD.md`** - Getting started guide
- **`../CONFIG_MOUNTING.md`** - Configuration file mounting
- **`../PODMAN_QUICKSTART.md`** - Podman deployment guide
- **`../PODMAN_NETWORKING.md`** - Network configuration

## Next Steps

- See `../README.md` for more examples
- Check `docs/api.md` for full API documentation
- Review `config/examples/web_server.yaml` for server configuration
