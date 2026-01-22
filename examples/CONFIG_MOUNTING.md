# Mounting Configuration Files to askGPT API Container

This guide explains how to mount configuration files to the askGPT API container so it knows how to serve your models.

## Why Mount a Config File?

By mounting a config file (like `config_sample.yaml`), you can:
- Configure multiple providers (Ollama, OpenAI, Anthropic, etc.)
- Define available models for each provider
- Set default provider and model
- Configure model aliases
- Set provider-specific settings (API keys, timeouts, etc.)

## Config File Locations

The container checks for config files in this order (first found wins):

1. **`ASKGPT_CONFIG_PATH`** environment variable (if set and file exists)
2. **`/root/.askgpt/config_orig.yaml`** (recommended mount location)
3. **`/app/config/config_orig.yaml`** (alternative mount location)
4. **`/root/.askgpt/config.yaml`** (if writable, not recommended for mounts)
5. **`/app/config/config.yaml`** (alternative location)
6. **Default config** (if none of the above exist)

**Note:** Mounting as `config_orig.yaml` is recommended because the container needs to copy and potentially modify the config file. Mounting directly to `config.yaml` can cause issues with read-only mounts.

## Mounting Methods

### Method 1: Mount as config_orig.yaml (Recommended)

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api
```

**Pros:**
- Avoids conflicts with the final config location
- Container can copy and modify the config safely
- Works with read-only mounts
- Recommended approach

### Method 2: Mount to Alternative Location

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/app/config/config.yaml:ro \
  askgpt-api
```

**Pros:**
- Keeps config separate from user directory
- Good for multi-user setups

### Method 3: Use Environment Variable

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/app/config/custom.yaml:ro \
  -e ASKGPT_CONFIG_PATH=/app/config/custom.yaml \
  askgpt-api
```

**Pros:**
- Most flexible
- Can use any filename
- Good for testing different configs

## Automatic Ollama URL Updates

The entrypoint script automatically updates Ollama `api_base` URLs in your config file:

- If `OLLAMA_API_BASE` environment variable is set, it replaces:
  - `http://localhost:11434/v1` → Your `OLLAMA_API_BASE` value
  - `http://127.0.0.1:11434/v1` → Your `OLLAMA_API_BASE` value

This makes it easy to use the same config file for:
- **Local development**: `api_base: http://localhost:11434/v1`
- **Podman**: Set `OLLAMA_API_BASE=http://host.containers.internal:11434/v1`
- **Docker**: Set `OLLAMA_API_BASE=http://host.docker.internal:11434/v1`

### Example with Automatic URL Update

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/config_sample.yaml:/root/.askgpt/config.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  askgpt-api
```

Your `config_sample.yaml` can have:
```yaml
providers:
  ollama:
    api_base: http://localhost:11434/v1  # Will be auto-updated
```

And it will automatically become:
```yaml
providers:
  ollama:
    api_base: http://host.containers.internal:11434/v1
```

## Example: Complete Setup

### 1. Prepare Your Config File

Copy and customize `config_sample.yaml`:

```bash
cp config_sample.yaml my_config.yaml
# Edit my_config.yaml with your settings
```

### 2. Update Ollama URL (if needed)

If your config has `localhost` for Ollama, you can either:
- Let the container auto-update it (set `OLLAMA_API_BASE`)
- Manually change it to `host.containers.internal` before mounting

### 3. Run Container with Mounted Config

```bash
podman run -d \
  --name askgpt-api \
  -p 8000:8000 \
  -v $(pwd)/my_config.yaml:/root/.askgpt/config_orig.yaml:ro \
  -e OLLAMA_API_BASE=http://host.containers.internal:11434/v1 \
  -v askgpt-sessions:/app/sessions \
  askgpt-api
```

**Important:** Mount as `config_orig.yaml` (not `config.yaml`) to allow the container to copy and modify the file.

### 4. Verify Config is Loaded

```bash
# Check logs
podman logs askgpt-api

# List available models
curl http://localhost:8000/api/v1/models
```

## Docker Compose Example

```yaml
services:
  askgpt-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    volumes:
      # Mount your config file
      - ./config_sample.yaml:/root/.askgpt/config.yaml:ro
      # Persistent sessions
      - askgpt-sessions:/app/sessions
    environment:
      - OLLAMA_API_BASE=http://host.containers.internal:11434/v1
    ports:
      - "8000:8000"
```

## Config File Structure

Your config file should follow this structure:

```yaml
# Default provider and model
default_provider: ollama
default_model: gpt-oss:20b

# Provider configurations
providers:
  ollama:
    api_base: http://localhost:11434/v1  # Will be auto-updated
    known_models:
      - gpt-oss:20b
      - gpt-oss:120b
    allow_unknown_models: true
    discover_models: true
    
  openai:
    api_key_env: OPENAI_API_KEY
    known_models:
      - gpt-5-nano
      - gpt-5-mini
    allow_unknown_models: true

# Model aliases
model_aliases:
  gpt5: gpt-5
  qwen: qwen2.5-coder:3b
```

## Troubleshooting

### Config Not Loading

1. **Check file exists:**
   ```bash
   podman exec askgpt-api ls -la /root/.askgpt/config.yaml
   ```

2. **Check logs:**
   ```bash
   podman logs askgpt-api | grep -i config
   ```

3. **Verify mount:**
   ```bash
   podman inspect askgpt-api | grep -A 10 Mounts
   ```

### Ollama Connection Issues

1. **Verify URL was updated:**
   ```bash
   podman exec askgpt-api cat /root/.askgpt/config.yaml | grep api_base
   ```

2. **Check OLLAMA_API_BASE is set:**
   ```bash
   podman exec askgpt-api env | grep OLLAMA
   ```

3. **Test Ollama connectivity:**
   ```bash
   podman exec askgpt-api curl http://host.containers.internal:11434/api/tags
   ```

### Models Not Showing

1. **Check config syntax:**
   ```bash
   # Validate YAML
   python -c "import yaml; yaml.safe_load(open('config_sample.yaml'))"
   ```

2. **Verify models endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/models | jq .
   ```

## Best Practices

1. **Use read-only mounts** (`:ro`) to prevent accidental modifications
2. **Keep config files in version control** (without API keys)
3. **Use environment variables for secrets** (API keys)
4. **Test config locally** before mounting to container
5. **Document your config** for team members

## Example Config Files

- `config_sample.yaml` - Basic configuration template
- `config/examples/web_server.yaml` - Web server specific config
- `config/examples/ollama-only.yaml` - Ollama-only setup
- `config/examples/multi-provider.yaml` - Multiple providers
