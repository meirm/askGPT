# askGPT - Offline-First AI Agent CLI

```
                           :|11;                             _     ____ ____ _____
                          20;::20                   __ _ ___| | __/ ___|  _ \_   _|
                          10|:;2$                  / _` / __| |/ / |  _| |_) || |
                            |&2'                  | (_| \__ \   <| |_| |  __/ | |
                '''''''''''':&1 '''''''''''        \__,_|___/_|\_\\____|_|    |_|
             |21111111111111111111111111111121
            18:                              20
            0$     ';;;             :;;:     |&:
         2218$    22|;101         :01;;10:   |&12
        :&; $$    82:':02         ;8|''|8;   |&
        :&; $$     ;111:           '|11|'    |&
         1218$           :211|112|           |&22
            $$             ':::'             |&:
            18;                             '$$
             ;2212:    ';11111111111111111112|
                 82 ;1221:
                 0021;
                 ''
 
                                                            

 ```
**Multi-provider LLM support • Offline-first • Session management • Tool execution**

askGPT is a powerful command-line interface for autonomous AI agents that can perform complex tasks including file operations, code analysis, and system commands. With offline-first defaults, askGPT works seamlessly with local models (Ollama) and cloud providers (OpenAI, Anthropic).

## What is askGPT?

askGPT is a CLI tool that provides autonomous AI agents with file system capabilities, session persistence, and multi-provider LLM support. By default, askGPT uses local models (via Ollama) for offline-first usage, while still supporting cloud providers when needed.

### Why askGPT?

- **🌐 Offline-First**: Defaults to local Ollama models - no API keys required
- **⚡ Multi-Provider**: Supports OpenAI, Anthropic, Ollama, and custom endpoints
- **🔐 Enterprise Security**: Fine-grained permissions, path restrictions, read-only mode
- **💬 Interactive Mode**: Rich terminal UI with session management
- **🎯 Commands & Agents**: Extensible markdown-based commands and agent profiles
- **🧠 Agent Skills**: Modular, auto-triggered capabilities
- **💰 Cost Tracking**: Token usage and cost estimation
- **📦 Quick Setup**: Install in 5 minutes

## Quick Start

### Install in 5 Minutes

```bash
# Preferred: Install from PyPI
pip install askgpt

# Or install from repository
git clone https://github.com/meirm/askGPT.git
cd askGPT
uv sync
uv tool install --force .

# Or use the installation script
curl -fsSL https://raw.githubusercontent.com/meirm/askGPT/main/install.sh | bash
```

### Try It Out

```bash
# Interactive mode with rich terminal UI (default when no arguments)
askgpt

# Quick prompt (defaults to local Ollama model)
askgpt -p "Create a hello world script"

# Use specific local model
askgpt -p "Analyze this codebase" --model gpt-oss:20b --provider ollama

# Use cloud provider (requires API key)
askgpt -p "Write a function" --model gpt-5-mini --provider openai

# Safe exploration with read-only mode
askgpt -p "Analyze this codebase" --read-only

# List available models
askgpt list-models --provider ollama

# Continue conversation with session persistence
askgpt -p "Add error handling to that function" --continue

# Use custom commands
askgpt -p '/analyze "Review this code for security issues"'

# Use specialized agents
askgpt -p "Explain this code" --agent analyst

# Skills automatically trigger based on your prompt
askgpt -p "Generate a README for this project"
askgpt -p "Check code formatting and style"
askgpt -p "Write release notes for version 1.0"
```

## Core Features

### 🌐 Offline-First Design

askGPT defaults to using local Ollama models for zero external dependencies:

```bash
# Works offline with local models (no API key needed)
askgpt -p "Your task here"
# Defaults to: provider=ollama, model=gpt-oss:20b

# Switch to cloud providers when needed
askgpt -p "Task" --provider openai --model gpt-5-mini
```

### 🤖 Multi-Provider Support

**Use ANY model from ANY provider** - no hardcoded restrictions:

| Provider | Example Models | Configuration |
|----------|---------------|---------------|
| **Ollama** (default) | gpt-oss:20b, llama3.2:latest, mistral | No API key needed |
| **OpenAI** | GPT-5, GPT-4o | API key required |
| **Anthropic** | Claude models | API key required |
| **Custom** | Your own endpoints | Fully configurable |

```bash
# Local models (offline-first)
askgpt -p "Task" --provider ollama --model gpt-oss:20b
askgpt -p "Task" --model llama3.2:latest  # provider defaults to ollama

# Cloud models
askgpt -p "Task" --provider openai --model gpt-5
askgpt -p "Task" --provider anthropic --model claude-3-haiku-20240307
```

### 🔐 Enterprise Security

**Fine-Grained Permissions**

```bash
# Read-only mode for safe exploration
askgpt -p "Audit the codebase for vulnerabilities" --read-only

# Limit tool calls for safety
askgpt -p "Analyze project" --max-tool-calls 10

# Unlimited calls for complex operations
askgpt -p "Refactor entire codebase" --unlimited-tool-calls
```

### 💬 Session Management

**Persistent Conversations**

```bash
# Start a project
askgpt -p "Create a Flask API" --new
# Returns: session_abc123

# Continue with context (agent remembers everything)
askgpt -p "Add user authentication" --continue
askgpt -p "Add input validation" --continue

# Or use specific session
askgpt -p "Add logging" --session session_abc123
```

**Session Features**
- Conversation history preservation
- Token usage tracking per session
- Model/provider settings persistence
- Multi-project management
- Cost tracking and analytics

### 🎯 Commands & Agents

```bash
# Create custom command templates
askgpt commands create code-review
askgpt -p '/code-review "src/auth"'

# Use specialized agents
askgpt -p "Analyze code" --agent analyst
askgpt -p "Write tests" --agent coder
askgpt -p "Generate ideas" --agent creative

# List available commands and agents
askgpt commands list
askgpt agents list
```

### 🧠 Agent Skills System

**Modular, auto-triggered capabilities** - Skills automatically activate when relevant:

```bash
# List all available skills
askgpt skills list

# Show details about a specific skill
askgpt skills show generating-readmes

# Skills automatically trigger when you ask relevant questions:
askgpt -p "Generate a README for this project"
# → Automatically uses generating-readmes skill

askgpt -p "Check code formatting across all Python files"
# → Automatically uses checking-code-formatting skill
```

## Installation

### Requirements
- Python 3.12+
- 5 minutes of your time

### Supported Platforms
- ✅ macOS (Intel & Apple Silicon)
- ✅ Linux (Ubuntu, Debian, CentOS, Arch)
- ✅ Windows 10/11
- ✅ WSL2

### Quick Install

```bash
# Preferred: Install from PyPI
pip install askgpt

# Or install from repository
git clone https://github.com/meirm/askGPT.git
cd askGPT
uv sync
uv tool install --force .

# Or use the installation script
curl -fsSL https://raw.githubusercontent.com/meirm/askGPT/main/install.sh | bash
./install.sh --local  # For local repository
```

### Provider Setup

**Ollama (Local - Recommended for Offline Use)**
```bash
# Install Ollama from ollama.ai
ollama pull gpt-oss:20b
# No API key needed! This is the default provider.
```

**OpenAI (Cloud)**
```bash
export OPENAI_API_KEY=sk-your-key-here
```

**Anthropic (Cloud)**
```bash
export ANTHROPIC_API_KEY=your-anthropic-key
```

## Configuration

### Default Configuration

askGPT defaults to offline-first mode. Configuration file: `~/.askgpt/config.yaml`

```yaml
# Default settings (offline-first)
default_provider: ollama
default_model: gpt-oss:20b

providers:
  ollama:
    api_base: http://localhost:11434/v1
    allow_unknown_models: true
    discover_models: true
    
  openai:
    api_key_env: OPENAI_API_KEY
    allow_unknown_models: true
    
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    api_base: https://api.anthropic.com/v1
    allow_unknown_models: true

# Agent configuration
max_tool_calls: 20
temperature: 0.2
```

### Using Different Providers

```bash
# Use local model (default)
askgpt -p "Task"

# Switch to cloud provider
askgpt -p "Task" --provider openai --model gpt-5-mini

# TODO: Future feature - online/offline mode switching
# This will allow easy toggling between local and cloud providers
```

## CLI Reference

### Basic Usage

```bash
# Interactive mode (default)
askgpt

# Quick prompt
askgpt -p "Your prompt here"

# With options
askgpt -p "Task" --model gpt-5 --provider openai --verbose

# Read-only mode
askgpt -p "Analyze codebase" --read-only

# Session management
askgpt -p "Task" --continue        # Continue last session
askgpt -p "Task" --session <id>   # Use specific session
askgpt -p "Task" --new             # Force new session
```

### Commands

```bash
askgpt list-models                 # List all available models
askgpt list-models --provider ollama  # List models for provider
askgpt commands list               # List command templates
askgpt skills list                 # List available skills
askgpt sessions list              # List sessions
askgpt sessions show <id>         # Show session details
```

## Architecture

askGPT uses a sophisticated agent architecture:

```text
┌─────────────────────────────────────────┐
│ askGPT CLI                               │
│   • Session management                   │
│   • Permission enforcement               │
│   • Provider abstraction                 │
│   • Token tracking                       │
└─────────────────────────────────────────┘
                    │
            Creates & Manages
                    ▼
┌─────────────────────────────────────────┐
│ Inner Agent (OpenAI SDK)                │
│   • File system tools                   │
│   • Autonomous execution                │
│   • Multi-turn reasoning                │
│   • Tool chaining                       │
└─────────────────────────────────────────┘
```

## Use Cases

### 🔍 Code Analysis & Auditing
```bash
# Security audit without modification risk
askgpt -p "Scan for OWASP top 10 vulnerabilities and generate report" --read-only

# Architecture analysis
askgpt -p "Create a dependency graph and identify circular dependencies" --read-only
```

### 🚀 Autonomous Development
```bash
# Build complete features
askgpt -p "Implement REST API with authentication, validation, and tests"

# Iterative refinement with sessions
askgpt -p "Create a Flask API" --new
askgpt -p "Add rate limiting" --continue
askgpt -p "Add caching" --continue
```

### 📊 Multi-Model Comparison
```bash
# Compare different models on the same task
for model in gpt-5-mini claude-3-haiku gpt-oss:20b; do
  askgpt -p "Optimize this function" --model $model
done
```

## Advanced Features

### Tool Restrictions
```bash
# Development with guardrails
askgpt -p "Refactor the payment module" \
  --max-tool-calls 10 \
  --read-only
```

### Cost Tracking
```bash
# View session costs
askgpt sessions show <session_id>
# Shows: tokens, costs, model used, etc.
```

### Output Formats
```bash
askgpt -p "Task" -f rich      # Beautiful terminal output (default)
askgpt -p "Task" -f json      # Structured JSON for scripts
askgpt -p "Task" -f simple    # Plain text for piping
askgpt -p "Task" -f markdown  # Formatted markdown output
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
git clone https://github.com/meirm/askGPT.git
cd askGPT
uv sync --extra test
uv run pytest tests/ -v
```

## Roadmap

### Coming Soon
- [ ] Streaming responses for real-time feedback
- [ ] Batch operations for multiple prompts
- [ ] Online/offline mode switching (toggle between local and cloud)
- [ ] Resource quotas and rate limiting
- [ ] Custom system prompts
- [ ] Webhook notifications

### Under Consideration
- [ ] Vector database integration
- [ ] Multi-file context windows
- [ ] Agent collaboration protocols
- [ ] Visual Studio Code extension

## Documentation

### Guides
- **[CLI Usage Guide](docs/ASKGPT_USAGE.md)** - Complete CLI reference
- **[Configuration Guide](docs/CONFIG.md)** - Setup and customization
- **[Commands Guide](docs/COMMANDS.md)** - Custom commands and agents
- **[Skills Documentation](docs/SKILLS.md)** - Agent skills system

## Support

- **Documentation**: See guides above
- **Issues**: [GitHub Issues](https://github.com/meirm/askGPT/issues)
- **Discussions**: [GitHub Discussions](https://github.com/meirm/askGPT/discussions)

## License

MIT License - See [LICENSE](LICENSE) for details.

---

**Ready to supercharge your AI development?** Install askGPT in 5 minutes and experience the power of offline-first AI agents.

```bash
# Get started now!
pip install askgpt
```
