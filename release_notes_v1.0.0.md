# Release Notes - askGPT v1.0.0

## 🚀 Version 1.0.0 - Initial Release (November 1st, 2025)

## Overview

**askGPT v1.0.0** is the first stable release of askGPT, a powerful command-line interface for autonomous AI agents. askGPT provides AI agent capabilities with an **offline-first** approach, making advanced AI interactions accessible without requiring cloud API keys.

Built with a focus on simplicity, privacy, and flexibility, askGPT enables developers to leverage AI agents for code development, analysis, documentation, and problem-solving—all from the command line.

## 🎯 Key Highlights

- **🌐 Offline-First Design**: Works immediately with local Ollama models - no API keys required
- **⚡ Multi-Provider Support**: Seamlessly switch between local (Ollama) and cloud providers (OpenAI, Anthropic)
- **💬 Rich Interactive Mode**: Enhanced terminal UI with autocompletion, history, and session management
- **🎯 Extensible Commands**: Markdown-based command system for custom workflows
- **🧠 Agent Skills**: Modular, auto-triggered capabilities for specialized tasks
- **💰 Cost Tracking**: Built-in token usage and cost estimation
- **🔐 Security Features**: Fine-grained permissions, path restrictions, and read-only mode

## ✨ Core Features

### 🌐 Offline-First Architecture

askGPT defaults to using local Ollama models, providing immediate functionality without any cloud dependencies:

```bash
# Works immediately, no setup needed!
askgpt "Create a hello world script"

# Uses local Ollama model (gpt-oss:20b by default)
askgpt -p "Analyze this codebase"
```

**Benefits**:
- Zero external dependencies for basic usage
- No API key configuration required
- Privacy-first - all processing happens locally
- Works completely offline
- Cost-free for local operations

### ⚡ Multi-Provider Support

Easily switch between local and cloud providers as needed:

```bash
# Local model (default)
askgpt -p "Explain this code" --provider ollama --model gpt-oss:20b

# Cloud providers (when you need more power)
askgpt -p "Write a complex function" --provider openai --model gpt-5-mini
askgpt -p "Analyze requirements" --provider anthropic --model claude-3-haiku-20240307
```

**Supported Providers**:
- **Ollama** (local, default) - Offline models like `gpt-oss:20b`, `qwen2.5-coder:3b`
- **OpenAI** - GPT models including `gpt-5-mini`, `gpt-5-nano`, `gpt-5`, `gpt-4o`
- **Anthropic** - Claude models including `claude-3-haiku`, `claude-opus-4`, `claude-sonnet-4`
- **LM Studio** - Custom local endpoints
- **Custom Endpoints** - Support for any OpenAI-compatible API

### 💬 Enhanced Interactive Mode

askGPT provides a rich, interactive terminal experience:

```bash
askgpt  # Launches interactive mode
```

**Features**:
- Tab completion for commands, models, and providers
- Command history with arrow key navigation
- Real-time autosuggestions
- Customizable prompt (PS1)
- Session persistence
- Built-in help system

**Interactive Commands**:
- `/help` - Show available commands and help
- `/commands` - List and manage custom command files
- `/skills` - Browse and inspect Agent Skills
- `/agents` - View and switch agent personalities
- `/model <name>` - Change AI model on the fly
- `/provider <name>` - Switch providers
- `/verbose [on/off]` - Toggle detailed output
- `/clear` - Clear the screen
- `/exit` or `/quit` - Exit interactive mode

### 🎯 Command System

Create reusable command templates for common workflows:

```bash
# Use built-in commands
askgpt -p "/analyze Review this code for security issues"

# Create custom commands
askgpt commands create my-workflow
# Edit ~/.askgpt/commands/my-workflow.md

# Use your custom command
askgpt -p "/my-workflow Process this data"
```

Commands are simple markdown files that can include:
- Prompt templates with placeholders
- Metadata and descriptions
- Multi-step workflows

### 🧠 Agent Skills System

Agent Skills are modular capabilities that automatically trigger based on your prompts:

```bash
# Skills automatically activate for relevant tasks
askgpt -p "Generate a README for this project"
# → readme-generator skill activates

askgpt -p "Check code formatting and style"
# → code-formatting-checker skill activates

askgpt -p "Write release notes for version 1.0"
# → write-release-notes skill activates
```

**Built-in Skills** (installable):
- `readme-generator` - Generate project README files
- `code-formatting-checker` - Check and suggest code formatting
- `security-audit` - Perform security analysis
- `write-release-notes` - Generate release notes

**Custom Skills**: Create your own skills in `~/.askgpt/skills/`

### 🔐 Security Features

askGPT includes enterprise-grade security features:

**Read-Only Mode**:
```bash
askgpt -p "Analyze this codebase" --read-only
# Agent can read files but cannot modify anything
```

**Permission System**:
- Fine-grained tool permissions
- Path restrictions (allowed/blocked paths)
- Tool whitelisting and blacklisting
- Safe exploration mode

**Configuration Security**:
- API keys stored in environment variables
- SSL validation by default
- Configurable security settings

### 💰 Cost Tracking

Track token usage and estimate costs across providers:

```bash
askgpt -p "Analyze this code" --billing
```

**Features**:
- Token usage per request
- Cost estimation
- Cached token savings
- Multi-provider cost comparison

### 📊 Session Management

Maintain conversation context across multiple interactions:

```bash
# Start a conversation
askgpt -p "Design a user authentication system"

# Continue the conversation
askgpt -p "Add password reset functionality" --continue

# Load a specific session
askgpt -p "Review the API design" --session <session-id>

# List recent sessions
askgpt sessions list

# View session details
askgpt sessions show <session-id>
```

## ⚙️ Configuration

### Quick Setup

Generate a default configuration:

```bash
askgpt init
```

This creates `~/.askgpt/config.yaml` with sensible defaults.

### Configuration File

Location: `~/.askgpt/config.yaml`

**Example Configuration**:
```yaml
# Default provider and model (offline-first)
default_provider: ollama
default_model: gpt-oss:20b

# Provider configurations
providers:
  ollama:
    api_base: http://localhost:11434/v1
    known_models:
      - gpt-oss:20b
      - gpt-oss:120b
      - qwen2.5-coder:3b
      - llama3.2:latest
    allow_unknown_models: true
    discover_models: true

  openai:
    api_key_env: OPENAI_API_KEY
    api_base: https://api.openai.com/v1
    known_models:
      - gpt-5-mini
      - gpt-5-nano
      - gpt-5
      - gpt-4o
    allow_unknown_models: true

  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    api_base: https://api.anthropic.com/v1
    known_models:
      - claude-3-haiku-20240307
      - claude-opus-4-20250514
      - claude-sonnet-4-20250514
    allow_unknown_models: true

# Model aliases for convenience
model_aliases:
  gpt5: gpt-5-mini
  claude: claude-3-haiku-20240307
  qwen: qwen2.5-coder:3b
  llama: llama3.2:latest

# Agent settings
max_tool_calls: 20
max_turns: 20
session_timeout: 1800

# Logging
log_level: INFO

# Performance
cache_enabled: true
cache_ttl: 3600

# Security
validate_ssl: true
allow_http: false
```

### Environment Variables

Configure via environment variables:

```bash
# Default provider and model
export ASKGPT_DEFAULT_PROVIDER=ollama
export ASKGPT_DEFAULT_MODEL=gpt-oss:20b

# Provider-specific settings
export ASKGPT_PROVIDER_OLLAMA_API_BASE=http://localhost:11434/v1

# Logging
export ASKGPT_LOG_LEVEL=DEBUG
```

### Directory Structure

askGPT uses the following directory structure:

```
~/.askgpt/
├── config.yaml          # Main configuration file
├── commands/            # Custom command templates
├── agents/              # Custom agent personalities
├── skills/              # Custom Agent Skills
├── hooks/               # Custom hooks (advanced)
└── sessions/            # Conversation session data
```

## 📥 Installation

### Quick Install

```bash
# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/meirm/askGPT/main/install.sh | bash

# From local repository
./install.sh --local
```

### Requirements

- **Python**: 3.12 or higher
- **uv**: Python package manager (installed automatically if missing)
- **Ollama** (optional): For local models (can be installed via the installer)

### Installation Methods

**1. Install Script** (Recommended):
```bash
curl -fsSL https://raw.githubusercontent.com/meirm/askGPT/main/install.sh | bash
```

**2. Manual Installation**:
```bash
git clone https://github.com/meirm/askGPT.git
cd askGPT
uv sync
uv tool install -e .
```

## 🚀 Quick Start

### 1. Install askGPT

```bash
curl -fsSL https://raw.githubusercontent.com/meirm/askGPT/main/install.sh | bash
```

### 2. Try Interactive Mode

```bash
askgpt
```

### 3. Run Your First Prompt

```bash
# Offline mode (works immediately)
askgpt -p "Create a Python hello world script"

# With specific model
askgpt -p "Explain this code" --model gpt-oss:20b --provider ollama

# Safe exploration (read-only)
askgpt -p "Analyze this codebase" --read-only
```

### 4. Set Up Cloud Providers (Optional)

```bash
# Configure API keys
export OPENAI_API_KEY=your-key-here
export ANTHROPIC_API_KEY=your-key-here

# Use cloud providers
askgpt -p "Complex analysis" --provider openai --model gpt-5-mini
```

## 📚 Documentation

- **README**: Comprehensive guide in `README.md`
- **Help**: Run `askgpt --help` for command-line options
- **Interactive Help**: Type `/help` in interactive mode
- **Examples**: See `examples/` directory for use cases

## 🔧 Advanced Features

### Custom Commands

Create reusable command templates:

```bash
# Create a command
askgpt commands create code-review

# Edit the template
askgpt commands edit code-review

# Use the command
askgpt -p "/code-review This pull request"
```

### Agent Personalities

Switch between specialized agent personalities:

```bash
# Use built-in agents
askgpt -p "Write clean code" --agent coder
askgpt -p "Analyze data" --agent analyst

# Create custom agents
# Edit ~/.askgpt/agents/your-agent.md
```

### Agent Skills

Install and use built-in skills:

```bash
# List available skills
askgpt skills list

# Install built-in skills
askgpt skills install-builtin

# Create custom skills
askgpt skills create my-skill
```

## 🐛 Known Issues

- Some models may require additional configuration
- Ollama must be running for local model usage
- Large files may take longer to process

## 🔮 Roadmap

Planned for future releases:

- [ ] Online/offline mode switching command
- [ ] Additional local model support
- [ ] Enhanced model discovery
- [ ] Performance optimizations
- [ ] More built-in agent skills
- [ ] Plugin system for extensibility
- [ ] Web UI (optional)

## 🙏 Acknowledgments

Thank you to all contributors, early adopters, and the open-source community for making this release possible.

## 📞 Support

- **GitHub Issues**: https://github.com/meirm/askGPT/issues
- **Documentation**: See README.md in the repository
- **Help Command**: `askgpt --help`
- **Interactive Help**: Run `askgpt` and type `/help`

---

**Release Date**: January 2025  
**Version**: 1.0.0  
**License**: See LICENSE file
