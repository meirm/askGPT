# askGPT API Usage Examples

This directory contains examples demonstrating how to use the askGPT REST API service.

## Quick Start

1. **Start the API server:**
   ```bash
   askgpt serve --host 0.0.0.0 --port 8000
   ```

2. **Or use Docker:**
   ```bash
   docker build -f Dockerfile.api -t askgpt-api .
   docker run -p 8000:8000 askgpt-api
   ```

3. **Or use Docker Compose:**
   ```bash
   docker-compose -f docker-compose.api.yml up
   ```

## Examples

### 1. REST API (Python)

**File:** `api_usage_rest.py`

Basic HTTP REST API usage with the `requests` library.

```bash
python examples/api_usage_rest.py
```

**Features:**
- Health check
- Create sessions
- Send chat messages
- List sessions
- Get session details

### 2. WebSocket API (Python)

**File:** `api_usage_websocket.py`

Streaming chat using WebSocket connections.

```bash
python examples/api_usage_websocket.py
```

**Features:**
- Real-time streaming responses
- Session continuation
- Low-latency communication

### 3. Server-Sent Events (SSE) (Python)

**File:** `api_usage_sse.py`

Streaming chat using Server-Sent Events.

```bash
python examples/api_usage_sse.py
```

**Features:**
- HTTP-based streaming
- Simple to use with standard HTTP clients
- Works through proxies and load balancers

### 4. Python Client Library

**File:** `api_usage_client.py`

Direct Python library usage without HTTP.

```bash
python examples/api_usage_client.py
```

**Features:**
- No HTTP overhead
- Direct access to all features
- Type-safe API

### 5. cURL Examples

**File:** `api_usage_curl.sh`

Command-line examples using curl.

```bash
chmod +x examples/api_usage_curl.sh
./examples/api_usage_curl.sh
```

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
    "tokens_used": 150
  },
  "success": true
}
```

### WebSocket Message Format

**Client → Server:**
```json
{
  "message": "Hello!",
  "session_id": "optional-session-id",
  "model": "optional-model",
  "provider": "optional-provider"
}
```

**Server → Client:**
```json
{
  "chunk": "Response text chunk",
  "done": false,
  "session_id": "session-id"
}
```

## Docker/Podman Deployment

### Building the Image

**With Docker:**
```bash
docker build -f Dockerfile.api -t askgpt-api .
```

**With Podman:**
```bash
podman build -f Dockerfile.api -t askgpt-api .
```

### Running the Container

**Basic usage (Podman):**
```bash
podman run -p 8000:8000 askgpt-api
```

**Basic usage (Docker):**
```bash
docker run -p 8000:8000 askgpt-api
```

**Note:** The default `OLLAMA_API_BASE` is set to `http://host.containers.internal:11434/v1` for Podman compatibility. 
For Docker, you may need to override it:
```bash
docker run -p 8000:8000 \
  -e OLLAMA_API_BASE=http://host.docker.internal:11434/v1 \
  askgpt-api
```

**With custom config (mount config_sample.yaml):**
```bash
# Podman (recommended: mount as config_orig.yaml)
podman run -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api

# Docker (recommended: mount as config_orig.yaml)
docker run -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.docker.internal:11434/v1 \
  askgpt-api
```

The container will automatically:
- Load the mounted config file
- Update Ollama `api_base` from `localhost` to `host.containers.internal` (Podman) or `host.docker.internal` (Docker) if `OLLAMA_API_BASE` is set
- Use the config to serve the configured models

**With environment variables (Podman):**
```bash
podman run -p 8000:8000 \
  -e DEFAULT_PROVIDER=ollama \
  -e DEFAULT_MODEL=gpt-oss:20b \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api
```

**With environment variables (Docker):**
```bash
docker run -p 8000:8000 \
  -e DEFAULT_PROVIDER=ollama \
  -e DEFAULT_MODEL=gpt-oss:20b \
  -e OLLAMA_API_BASE=http://host.docker.internal:11434/v1 \
  askgpt-api
```

**With persistent sessions:**
```bash
docker run -p 8000:8000 \
  -v askgpt-sessions:/app/sessions \
  askgpt-api
```

### Docker Compose

**With Docker Compose:**
```bash
docker-compose -f docker-compose.api.yml up -d
```

**With Podman Compose:**
```bash
podman-compose -f docker-compose.api.yml up -d
```

**Note:** The docker-compose file is configured for Podman by default (uses `host.containers.internal`). 
For Docker, you may need to change `OLLAMA_API_BASE` to `http://host.docker.internal:11434/v1`.

## Environment Variables

The Docker container supports the following environment variables:

### Server Configuration
- `ASKGPT_HOST` - Host to bind to (default: `0.0.0.0`)
- `ASKGPT_PORT` - Port to bind to (default: `8000`)
- `ASKGPT_WORKERS` - Number of worker processes (default: `1`)
- `ASKGPT_RELOAD` - Enable auto-reload for development (default: `false`)

### Provider Configuration
- `DEFAULT_PROVIDER` - Default provider (default: `ollama`)
- `DEFAULT_MODEL` - Default model (default: `gpt-oss:20b`)
- `OLLAMA_API_BASE` - Ollama API base URL
  - Podman: `http://host.containers.internal:11434/v1` (default)
  - Docker: `http://host.docker.internal:11434/v1`
  - Local: `http://localhost:11434/v1`
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `OPENAI_API_BASE` - OpenAI API base URL (optional)
- `ANTHROPIC_API_KEY` - Anthropic API key (optional)
- `ANTHROPIC_API_BASE` - Anthropic API base URL (optional)

## Configuration

The API server loads configuration from (in order of priority):
1. `ASKGPT_CONFIG_PATH` environment variable (if set and file exists)
2. `/root/.askgpt/config_orig.yaml` (recommended mount location)
3. `/app/config/config_orig.yaml` (alternative mount location)
4. `/root/.askgpt/config.yaml` (if writable)
5. `/app/config/config.yaml` (alternative location)
6. Default configuration (if no config file exists)

### Mounting Config Files

You can mount `config_sample.yaml` or any custom config file:

```bash
# Mount config_sample.yaml (recommended: as config_orig.yaml)
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api
```

The entrypoint script will:
- Automatically detect the mounted config file
- Update Ollama `api_base` URLs from `localhost` to the container-appropriate host address if `OLLAMA_API_BASE` is set
- Use the config to serve all configured models and providers

See `config/examples/web_server.yaml` or `config_sample.yaml` for configuration examples.

## Testing the API

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Send a Chat Message
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

### Stream with SSE
```bash
curl -N "http://localhost:8000/api/v1/chat/stream?message=Hello"
```

## Production Deployment

For production deployment, consider:

1. **Use multiple workers:**
   ```bash
   docker run -e ASKGPT_WORKERS=4 askgpt-api
   ```

2. **Use a reverse proxy** (nginx, Traefik, etc.) for:
   - SSL/TLS termination
   - Rate limiting
   - Load balancing
   - Request logging

3. **Use external session storage** (Redis, database) for:
   - Session persistence across restarts
   - Multi-instance deployments
   - Better scalability

4. **Set up monitoring** for:
   - Health checks
   - Performance metrics
   - Error tracking

5. **Configure CORS** appropriately in `config.yaml`:
   ```yaml
   cors:
     allowed_origins:
       - "https://yourdomain.com"
   ```

## Troubleshooting

### Connection Refused
- Ensure the server is running: `askgpt serve`
- Check the port: `curl http://localhost:8000/api/v1/health`

### Ollama Connection Issues
- If using Podman, use `host.containers.internal:11434` to access host Ollama
- If using Docker, use `host.docker.internal:11434` to access host Ollama
- Check `OLLAMA_API_BASE` environment variable
- Default in Dockerfile is set for Podman: `http://host.containers.internal:11434/v1`

### Config Not Loading
- Check config file path: `~/.askgpt/config.yaml`
- Verify YAML syntax
- Check file permissions

### Session Not Persisting
- Ensure sessions directory is mounted as a volume
- Check write permissions on sessions directory
