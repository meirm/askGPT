# Quick Start: Running askGPT API with Podman

This guide shows you how to build and run the askGPT API server using Podman.

## Prerequisites

- Podman installed and running
- Ollama running on your host machine (accessible at `http://localhost:11434`)
- Network access (if using cloud providers like OpenAI)

## Step 1: Build the Container Image

Build the askGPT API image from the Dockerfile:

```bash
podman build -f Dockerfile.api -t askgpt-api .
```

This will:
- Create a multi-stage build
- Install all dependencies
- Set up the runtime environment
- Configure the entrypoint to run `askgpt serve`

## Step 2: Run the Container

### Basic Run

Start the container with default settings:

**Option 1: Host Network (Recommended for local development)**
```bash
podman run -d \
  --name askgpt-api \
  --network=host \
  -e OLLAMA_API_BASE=http://localhost:11434/v1 \
  askgpt-api
```

**Option 2: Bridge Network (if host.containers.internal works)**
```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api
```

The API will be available at `http://localhost:8000`

**Note:** If you get connection errors, use `--network=host` (Option 1). See `PODMAN_NETWORKING.md` for details.

### With Custom Configuration

Run with custom environment variables:

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -e DEFAULT_PROVIDER=ollama \
  -e DEFAULT_MODEL=gpt-oss:20b \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api
```

### With Persistent Sessions

Mount a volume to persist chat sessions:

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v askgpt-sessions:/app/sessions \
  askgpt-api
```

### With Custom Config File

Mount your own configuration file (e.g., `config_sample.yaml`):

**Option 1: Mount as config_orig.yaml (Recommended)**
```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  -v askgpt-sessions:/app/sessions \
  askgpt-api
```

**Option 2: Mount to alternative location**
```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/app/config/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  -v askgpt-sessions:/app/sessions \
  askgpt-api
```

**Option 3: Use environment variable**
```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/app/config/custom_config.yaml:ro \
  -e ASKGPT_CONFIG_PATH=/app/config/custom_config.yaml \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  -v askgpt-sessions:/app/sessions \
  askgpt-api
```

**Note:** 
- Mounting as `config_orig.yaml` is recommended to avoid conflicts with the final config location
- The entrypoint script will automatically copy and update the config file
- It will update `localhost` in the Ollama `api_base` to `host.containers.internal` if `OLLAMA_API_BASE` is set

### With Multiple Workers (Production)

Run with multiple worker processes for better performance:

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -e ASKGPT_WORKERS=4 \
  askgpt-api
```

## Step 3: Verify It's Running

### Check Container Status

```bash
podman ps
```

You should see the `askgpt-api` container running.

### Check Logs

View the container logs:

```bash
podman logs askgpt-api
```

Or follow logs in real-time:

```bash
podman logs -f askgpt-api
```

### Test Health Endpoint

Test that the API is responding:

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

### Test Chat Endpoint

Send a test message:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! Can you tell me a short joke?"}'
```

## Step 4: Access the API

The API is now available at:
- **REST API**: `http://localhost:8000/api/v1/`
- **WebSocket**: `ws://localhost:8000/api/v1/chat/stream`
- **SSE**: `http://localhost:8000/api/v1/chat/stream?message=Hello`

## Common Operations

### Stop the Container

```bash
podman stop askgpt-api
```

### Start a Stopped Container

```bash
podman start askgpt-api
```

### Restart the Container

```bash
podman restart askgpt-api
```

### Remove the Container

```bash
podman stop askgpt-api
podman rm askgpt-api
```

### Update and Rebuild

```bash
# Stop and remove old container
podman stop askgpt-api
podman rm askgpt-api

# Rebuild image
podman build -f Dockerfile.api -t askgpt-api .

# Run new container
podman run -d --name askgpt-api -p 8000:8000 askgpt-api
```

## Environment Variables

You can customize the container behavior with these environment variables:

### Server Configuration
- `ASKGPT_HOST` - Host to bind to (default: `0.0.0.0`)
- `ASKGPT_PORT` - Port to bind to (default: `8000`)
- `ASKGPT_WORKERS` - Number of worker processes (default: `1`)
- `ASKGPT_RELOAD` - Enable auto-reload (default: `false`)

### Provider Configuration
- `DEFAULT_PROVIDER` - Default provider (default: `ollama`)
- `DEFAULT_MODEL` - Default model (default: `gpt-oss:20b`)
- `OLLAMA_API_BASE` - Ollama API URL (default: `http://host.containers.internal:11434/v1`)

### API Keys (Optional)
- `OPENAI_API_KEY` - For OpenAI provider
- `ANTHROPIC_API_KEY` - For Anthropic provider

## Example: Complete Setup with Ollama and Config File

```bash
# 1. Build the image
podman build -f Dockerfile.api -t askgpt-api .

# 2. Run with mounted config_sample.yaml and persistent storage
# Note: Using --network=host for easier Ollama access (see PODMAN_NETWORKING.md for alternatives)
podman run -d \
  --name askgpt-api \
  --network=host \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://localhost:11434/v1 \
  -v askgpt-sessions:/app/sessions \
  askgpt-api

# 3. Check it's running
podman logs askgpt-api

# 4. Test the API
curl http://localhost:8000/api/v1/health

# 5. List available models from config
curl http://localhost:8000/api/v1/models
```

The mounted `config_sample.yaml` will provide all the model configurations, and the container will automatically:
- Copy it to `/root/.askgpt/config.yaml` (writable location)
- Update the Ollama API base URL to work with Podman

## Example: Using Podman Compose

If you prefer using compose files:

```bash
# Start services
podman-compose -f docker-compose.api.yml up -d

# View logs
podman-compose -f docker-compose.api.yml logs -f

# Stop services
podman-compose -f docker-compose.api.yml down
```

## Troubleshooting

### Container Won't Start

Check the logs:
```bash
podman logs askgpt-api
```

### Can't Connect to Ollama

Verify Ollama is running on the host:
```bash
curl http://localhost:11434/api/tags
```

If Ollama is running, the container should be able to access it via `host.containers.internal`.

### Port Already in Use

If port 8000 is already in use, change it:
```bash
podman run -d \
  --name askgpt-api \
  -p 8080:8000 \
  -e ASKGPT_PORT=8000 \
  askgpt-api
```

Then access at `http://localhost:8080`

### Permission Issues

If you encounter permission issues with volumes:
```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  --userns=keep-id \
  askgpt-api
```

## Next Steps

- See `examples/README_API_USAGE.md` for API usage examples
- Check `examples/api_usage_*.py` for code examples
- Review `config/examples/web_server.yaml` for configuration options
