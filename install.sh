#!/bin/bash

# askGPT CLI - Production Installation Script
# This script installs askgpt CLI tool for command-line AI agent interactions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$HOME/.askgpt"
CONFIG_DIR="$HOME/.askgpt"
SERVICE_NAME="askgpt"
GITHUB_REPO="https://github.com/meirm/askgpt"
VERSION="latest"

print_header() {
    echo -e "\n${BOLD}${BLUE}🤖 askGPT CLI - Production Installation${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_step() {
    echo -e "${BOLD}${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

check_requirements() {
    print_step "Checking system requirements..."
    
    # Check Python 3.9+
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
        REQUIRED_VERSION="3.9"
        
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_success "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.9+ required. Found: $PYTHON_VERSION"
            echo "Please install Python 3.9 or higher from https://python.org"
            exit 1
        fi
    else
        print_error "Python 3 not found"
        echo "Please install Python 3.9+ from https://python.org"
        exit 1
    fi
    
    # Check uv (Python package manager)
    if ! command -v uv >/dev/null 2>&1; then
        print_warning "uv not found. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
        
        if ! command -v uv >/dev/null 2>&1; then
            print_error "Failed to install uv"
            echo "Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        fi
        print_success "uv installed successfully"
    else
        print_success "uv found"
    fi
    
    # Check if running on supported OS
    OS=$(uname -s)
    case "$OS" in
        Darwin*)
            print_success "macOS detected"
            ;;
        Linux*)
            print_success "Linux detected"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            print_success "Windows detected"
            ;;
        *)
            print_warning "Unsupported OS: $OS (continuing anyway)"
            ;;
    esac
}

install_askgpt() {
    print_step "Installing askGPT CLI..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Determine if we're installing from internet or local repo
    if [ -n "$INSTALL_FROM_LOCAL" ]; then
        # Installing from local repository
        print_step "Installing from local repository..."
        
        # Determine the source directory and repo root
        SOURCE_DIR=""
        REPO_ROOT=""
        if [ -f "$(pwd)/pyproject.toml" ] && [ -d "$(pwd)/src/askgpt" ]; then
            # We're in the root askgpt directory
            SOURCE_DIR="$(pwd)"
            REPO_ROOT="$(pwd)"
        else
            print_error "Unable to find askgpt source code"
            echo "Please run this script from the askgpt root directory"
            exit 1
        fi
        
        # Install the package directly from source (installs to ~/.local/bin)
        print_step "Installing askgpt package..."
        cd "$SOURCE_DIR"
        
        # Install dependencies and tool
        if [ -f ".env.sample" ] && [ ! -f ".env" ]; then
            cp .env.sample .env
            print_success "Created .env file from template"
        elif [ -f ".env" ]; then
            print_success "Existing .env file preserved (not overwritten)"
        fi
        
        uv sync
        uv tool install --force .
        print_success "askgpt command installed to ~/.local/bin"
        
        # Create ~/.askgpt directory structure and copy builtins
        print_step "Setting up ~/.askgpt with builtin commands, agents, and skills..."
        mkdir -p "$INSTALL_DIR/commands"
        mkdir -p "$INSTALL_DIR/agents"
        mkdir -p "$INSTALL_DIR/skills"
        
        # Copy builtin skills from src/askgpt/data/builtin_skills/
        if [ -d "$SOURCE_DIR/src/askgpt/data/builtin_skills" ]; then
            print_step "Copying builtin skills..."
            for skill_dir in "$SOURCE_DIR/src/askgpt/data/builtin_skills"/*; do
                if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
                    skill_name="$(basename "$skill_dir")"
                    cp -r "$skill_dir" "$INSTALL_DIR/skills/$skill_name"
                    print_success "Installed builtin skill: $skill_name"
                fi
            done
        fi
        
        # Copy example commands if they exist (treat them as builtins)
        if [ -d "$REPO_ROOT/examples/dot.askgpt/commands" ]; then
            print_step "Copying builtin commands..."
            for cmd_file in "$REPO_ROOT/examples/dot.askgpt/commands"/*.md; do
                if [ -f "$cmd_file" ]; then
                    cmd_name="$(basename "$cmd_file")"
                    cp "$cmd_file" "$INSTALL_DIR/commands/$cmd_name"
                fi
            done
            print_success "Installed builtin commands"
        fi
        
        # Copy example agents if they exist (treat them as builtins)
        if [ -d "$REPO_ROOT/examples/dot.askgpt/agents" ]; then
            print_step "Copying builtin agents..."
            for agent_file in "$REPO_ROOT/examples/dot.askgpt/agents"/*.md; do
                if [ -f "$agent_file" ]; then
                    agent_name="$(basename "$agent_file")"
                    cp "$agent_file" "$INSTALL_DIR/agents/$agent_name"
                fi
            done
            print_success "Installed builtin agents"
        fi
        
        # Copy builtin hooks if they exist
        if [ -d "$SOURCE_DIR/examples/hooks" ]; then
            print_step "Copying builtin hooks..."
            mkdir -p "$INSTALL_DIR/hooks"
            for hook_file in "$SOURCE_DIR/examples/hooks"/*; do
                if [ -f "$hook_file" ]; then
                    hook_name="$(basename "$hook_file")"
                    cp "$hook_file" "$INSTALL_DIR/hooks/$hook_name"
                fi
            done
            print_success "Installed builtin hooks"
        fi
        
        # Set INSTALL_PATH for compatibility with rest of script
        INSTALL_PATH="$SOURCE_DIR"
    else
        # Installing from internet (GitHub)
        if [ -d "$INSTALL_DIR/askgpt" ]; then
            print_step "Updating existing installation..."
            cd "$INSTALL_DIR/askgpt"
            git pull origin main || {
                print_warning "Git pull failed, removing and re-cloning..."
                cd "$HOME"
                rm -rf "$INSTALL_DIR/askgpt"
                git clone "$GITHUB_REPO.git" "$INSTALL_DIR/askgpt"
            }
        else
            print_step "Downloading askGPT from GitHub..."
            git clone "$GITHUB_REPO.git" "$INSTALL_DIR/askgpt"
        fi
        INSTALL_PATH="$INSTALL_DIR/askgpt"
        
        # Change to installation directory
        cd "$INSTALL_PATH"
        
        # Install dependencies
        print_step "Installing dependencies..."
        if [ -f ".env.sample" ] && [ ! -f ".env" ]; then
            cp .env.sample .env
            print_success "Created .env file from template"
        elif [ -f ".env" ]; then
            print_success "Existing .env file preserved (not overwritten)"
        fi
        
        uv sync
        print_success "Dependencies installed"
        
        # Install as a tool
        print_step "Installing askgpt command..."
        uv tool install --force .
        print_success "askgpt command installed"
        
        # Copy builtins to ~/.askgpt (for remote installs)
        print_step "Setting up ~/.askgpt with builtin commands, agents, and skills..."
        mkdir -p "$INSTALL_DIR/commands"
        mkdir -p "$INSTALL_DIR/agents"
        mkdir -p "$INSTALL_DIR/skills"
        
        # Copy builtin skills
        if [ -d "$INSTALL_PATH/src/askgpt/data/builtin_skills" ]; then
            print_step "Copying builtin skills..."
            for skill_dir in "$INSTALL_PATH/src/askgpt/data/builtin_skills"/*; do
                if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
                    skill_name="$(basename "$skill_dir")"
                    cp -r "$skill_dir" "$INSTALL_DIR/skills/$skill_name"
                fi
            done
            print_success "Installed builtin skills"
        fi
        
        # Copy example commands and agents if they exist
        REPO_ROOT_INSTALL="$INSTALL_DIR/askgpt"
        if [ -d "$REPO_ROOT_INSTALL/examples/dot.askgpt/commands" ]; then
            print_step "Copying builtin commands..."
            cp "$REPO_ROOT_INSTALL/examples/dot.askgpt/commands"/*.md "$INSTALL_DIR/commands/" 2>/dev/null || true
            print_success "Installed builtin commands"
        fi
        
        if [ -d "$REPO_ROOT_INSTALL/examples/dot.askgpt/agents" ]; then
            print_step "Copying builtin agents..."
            cp "$REPO_ROOT_INSTALL/examples/dot.askgpt/agents"/*.md "$INSTALL_DIR/agents/" 2>/dev/null || true
            print_success "Installed builtin agents"
        fi
        
        # Copy builtin hooks if they exist
        if [ -d "$INSTALL_PATH/examples/hooks" ]; then
            print_step "Copying builtin hooks..."
            mkdir -p "$INSTALL_DIR/hooks"
            cp "$INSTALL_PATH/examples/hooks"/* "$INSTALL_DIR/hooks/" 2>/dev/null || true
            print_success "Installed builtin hooks"
        fi
    fi
}

setup_configuration() {
    print_step "Setting up configuration..."
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    
    # Check if config.yaml already exists
    if [ -f "$CONFIG_DIR/config.yaml" ]; then
        print_info "Existing configuration found at $CONFIG_DIR/config.yaml"
        
        # Copy sample config to .package file for reference
        if [ -n "$INSTALL_FROM_LOCAL" ]; then
            # Installing from local repository
            if [ -f "./config/sample_config.yaml" ]; then
                cp "./config/sample_config.yaml" "$CONFIG_DIR/config.yaml.package"
                print_info "Sample configuration saved to $CONFIG_DIR/config.yaml.package for reference"
            fi
        else
            # Installing from internet - create sample config
            cat > "$CONFIG_DIR/config.yaml.package" << 'EOF'
# Nano CLI Configuration
# This is a sample configuration file for askgpt
# Copy this file to ~/.askgpt/config.yaml and customize as needed

# Default provider and model settings (offline-first)
default_provider: ollama
default_model: gpt-oss:20b

# Provider configurations
providers:
  openai:
    api_key_env: OPENAI_API_KEY
    known_models:
      - gpt-5-nano
      - gpt-5-mini
      - gpt-5
      - gpt-4o
    allow_unknown_models: true
    
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    api_base: https://api.anthropic.com/v1
    known_models:
      - claude-3-haiku-20240307
      - claude-opus-4-20250514
      - claude-opus-4-1-20250805
      - claude-sonnet-4-20250514
    allow_unknown_models: true
    
  ollama:
    api_base: http://localhost:11434/v1
    known_models:
      - gpt-oss:20b
      - gpt-oss:120b
      - qwen2.5-coder:3b
      - llama3.2:3b
      - mistral-small3.2
    allow_unknown_models: true
    discover_models: true

# Agent configuration
max_tool_calls: 20  # Maximum tool calls per agent run
max_turns: 20       # Maximum conversation turns
session_timeout: 1800  # Session timeout in seconds

# Model aliases for convenience
model_aliases:
  gpt5: gpt-5
  gpt5mini: gpt-5-mini
  gpt5nano: gpt-5-nano
  claude3haiku: claude-3-haiku-20240307
  opus4: claude-opus-4-20250514
  opus41: claude-opus-4-1-20250805
  sonnet4: claude-sonnet-4-20250514
  qwen: qwen2.5-coder:3b
  llama: llama3.2:3b
  mistral: mistral-small3.2

# Logging configuration
log_level: INFO

# Performance settings
cache_enabled: true
cache_ttl: 3600

# Security settings
validate_ssl: true
allow_http: false
EOF
            print_info "Sample configuration saved to $CONFIG_DIR/config.yaml.package for reference"
        fi
    else
        # Create new configuration
        if [ -n "$INSTALL_FROM_LOCAL" ]; then
            # Installing from local repository
            if [ -f "./config/sample_config.yaml" ]; then
                cp "./config/sample_config.yaml" "$CONFIG_DIR/config.yaml"
                print_success "Configuration created at $CONFIG_DIR/config.yaml"
            else
                # Fallback to creating inline
                create_default_config
            fi
        else
            # Installing from internet - create inline
            create_default_config
        fi
    fi
}

create_default_config() {
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# Nano CLI Configuration
# This is a sample configuration file for askgpt

# Default provider and model settings (offline-first)
default_provider: ollama
default_model: gpt-oss:20b

# Provider configurations
providers:
  openai:
    api_key_env: OPENAI_API_KEY
    known_models:
      - gpt-5-nano
      - gpt-5-mini
      - gpt-5
      - gpt-4o
    allow_unknown_models: true
    
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    api_base: https://api.anthropic.com/v1
    known_models:
      - claude-3-haiku-20240307
      - claude-opus-4-20250514
      - claude-opus-4-1-20250805
      - claude-sonnet-4-20250514
    allow_unknown_models: true
    
  ollama:
    api_base: http://localhost:11434/v1
    known_models:
      - gpt-oss:20b
      - gpt-oss:120b
      - qwen2.5-coder:3b
      - llama3.2:3b
      - mistral-small3.2
    allow_unknown_models: true
    discover_models: true

# Agent configuration
max_tool_calls: 20
max_turns: 20
session_timeout: 1800

# Model aliases for convenience
model_aliases:
  gpt5: gpt-5
  gpt5mini: gpt-5-mini
  gpt5nano: gpt-5-nano
  claude3haiku: claude-3-haiku-20240307
  opus4: claude-opus-4-20250514
  opus41: claude-opus-4-1-20250805
  sonnet4: claude-sonnet-4-20250514
  qwen: qwen2.5-coder:3b
  llama: llama3.2:3b
  mistral: mistral-small3.2

# Logging configuration
log_level: INFO

# Performance settings
cache_enabled: true
cache_ttl: 3600

# Security settings
validate_ssl: true
allow_http: false
EOF
    print_success "Configuration created at $CONFIG_DIR/config.yaml"
    
    # Setup example hooks if user wants them
    HOOKS_SETUP=""
    if [ -n "$INSTALL_FROM_LOCAL" ] && [ -f "$SOURCE_DIR/examples/setup_hooks.sh" ]; then
        HOOKS_SETUP="$SOURCE_DIR/examples/setup_hooks.sh"
        HOOKS_DIR="$SOURCE_DIR"
    elif [ -f "$INSTALL_DIR/askgpt/examples/setup_hooks.sh" ]; then
        HOOKS_SETUP="$INSTALL_DIR/askgpt/examples/setup_hooks.sh"
        HOOKS_DIR="$INSTALL_DIR/askgpt"
    fi
    
    if [ -n "$HOOKS_SETUP" ]; then
        echo
        read -p "$(echo -e "${YELLOW}Would you like to install example hooks? (y/N): ${NC}")" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$HOOKS_DIR"
            ./examples/setup_hooks.sh
            print_success "Example hooks installed"
        fi
    fi
}

# Claude Desktop integration removed - askGPT is CLI-only
# This function is no longer needed as askGPT doesn't support MCP server mode

setup_api_keys() {
    print_step "Setting up API keys..."
    
    echo
    echo -e "${BOLD}API Key Setup${NC}"
    echo "askGPT supports multiple AI providers. You need at least one API key:"
    echo
    echo "1. ${BOLD}OpenAI${NC} (GPT models) - Get key from: https://platform.openai.com/api-keys"
    echo "2. ${BOLD}Anthropic${NC} (Claude models) - Get key from: https://console.anthropic.com/"
    echo "3. ${BOLD}Ollama${NC} (Local models) - Install from: https://ollama.ai"
    echo
    
    # Determine .env file location based on install type
    if [ -n "$INSTALL_FROM_LOCAL" ]; then
        ENV_FILE="$SOURCE_DIR/.env"
    else
        ENV_FILE="$INSTALL_DIR/askgpt/.env"
    fi
    
    if [ -f "$ENV_FILE" ]; then
        echo "Current API key status:"
        
        if grep -q "OPENAI_API_KEY=sk-" "$ENV_FILE" 2>/dev/null; then
            print_success "OpenAI API key is configured"
        else
            echo -e "${YELLOW}  OpenAI API key: Not configured${NC}"
        fi
        
        if grep -q "ANTHROPIC_API_KEY=" "$ENV_FILE" && grep -v "ANTHROPIC_API_KEY=$" "$ENV_FILE" >/dev/null 2>&1; then
            print_success "Anthropic API key is configured"
        else
            echo -e "${YELLOW}  Anthropic API key: Not configured${NC}"
        fi
        
        # Check if Ollama is running
        if command -v ollama >/dev/null 2>&1 && pgrep ollama >/dev/null 2>&1; then
            print_success "Ollama is installed and running"
        else
            echo -e "${YELLOW}  Ollama: Not running or not installed${NC}"
        fi
    fi
    
    echo
    read -p "$(echo -e "${YELLOW}Would you like to configure API keys now? (y/N): ${NC}")" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        configure_api_keys
    else
        echo "You can configure API keys later by editing: $ENV_FILE"
    fi
}

configure_api_keys() {
    # Determine .env file location based on install type
    if [ -n "$INSTALL_FROM_LOCAL" ]; then
        ENV_FILE="$SOURCE_DIR/.env"
    else
        ENV_FILE="$INSTALL_DIR/askgpt/.env"
    fi
    
    echo
    echo "Enter your API keys (press Enter to skip):"
    echo
    
    # OpenAI API Key
    read -p "OpenAI API Key (sk-...): " OPENAI_KEY
    if [ -n "$OPENAI_KEY" ]; then
        if grep -q "OPENAI_API_KEY=" "$ENV_FILE"; then
            sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_KEY/" "$ENV_FILE"
        else
            echo "OPENAI_API_KEY=$OPENAI_KEY" >> "$ENV_FILE"
        fi
        print_success "OpenAI API key configured"
    fi
    
    # Anthropic API Key
    read -p "Anthropic API Key: " ANTHROPIC_KEY
    if [ -n "$ANTHROPIC_KEY" ]; then
        if grep -q "ANTHROPIC_API_KEY=" "$ENV_FILE"; then
            sed -i.bak "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$ANTHROPIC_KEY/" "$ENV_FILE"
        else
            echo "ANTHROPIC_API_KEY=$ANTHROPIC_KEY" >> "$ENV_FILE"
        fi
        print_success "Anthropic API key configured"
    fi
    
    # Ollama setup
    echo
    read -p "$(echo -e "${YELLOW}Would you like to install Ollama for local models? (y/N): ${NC}")" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_ollama
    fi
}

install_ollama() {
    print_step "Installing Ollama..."
    
    if command -v ollama >/dev/null 2>&1; then
        print_success "Ollama already installed"
    else
        # Install Ollama
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if command -v brew >/dev/null 2>&1; then
                brew install ollama
            else
                curl -fsSL https://ollama.ai/install.sh | sh
            fi
        else
            # Linux and others
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
        
        if command -v ollama >/dev/null 2>&1; then
            print_success "Ollama installed successfully"
        else
            print_warning "Ollama installation may have failed. Please visit https://ollama.ai for manual installation"
            return
        fi
    fi
    
    # Start Ollama service
    print_step "Starting Ollama service..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - start as background process
        nohup ollama serve >/dev/null 2>&1 &
    else
        # Linux - try to start as service or background process
        if command -v systemctl >/dev/null 2>&1; then
            sudo systemctl start ollama || nohup ollama serve >/dev/null 2>&1 &
        else
            nohup ollama serve >/dev/null 2>&1 &
        fi
    fi
    
    sleep 3  # Wait for service to start
    
    # Download default model
    print_step "Downloading default model (gpt-oss:20b)..."
    echo "This may take several minutes..."
    
    if ollama pull gpt-oss:20b; then
        print_success "Default model downloaded successfully"
    else
        print_warning "Failed to download model. You can do this later with: ollama pull gpt-oss:20b"
    fi
}

test_installation() {
    print_step "Testing installation..."
    
    # Test that askgpt command is available
    if command -v askgpt >/dev/null 2>&1; then
        print_success "askgpt command is available"
    else
        print_warning "askgpt command not found in PATH"
        echo "You may need to restart your terminal or add $(uv tool dir)/bin to your PATH"
    fi
    
    # Test basic functionality
    echo "Testing basic functionality..."
    
    # Create a simple test
    cd /tmp
    mkdir -p askgpt-test
    cd askgpt-test
    
    # Test CLI if available
    if command -v askgpt >/dev/null 2>&1; then
        echo "Running basic test..."
        if timeout 30 askgpt --help >/dev/null 2>&1; then
            print_success "askgpt CLI is working"
        else
            print_warning "askgpt CLI test timed out or failed"
        fi
    fi
    
    # Cleanup
    cd /tmp
    rm -rf askgpt-test
}

show_completion_message() {
    clear
    
    # Determine .env file location based on install type
    if [ -n "$INSTALL_FROM_LOCAL" ]; then
        ENV_LOCATION="$SOURCE_DIR/.env"
        DOCS_BASE="your source directory"
    else
        ENV_LOCATION="$INSTALL_DIR/askgpt/.env"
        DOCS_BASE="$INSTALL_DIR/askgpt"
    fi
    
    echo -e "
${BOLD}${GREEN}🎉 Installation Complete!${NC}

${BOLD}askGPT CLI has been successfully installed!${NC}

${BOLD}📍 Installation Locations:${NC}
• Builtin files: $INSTALL_DIR/ (commands, agents, skills, hooks)
• Configuration: $CONFIG_DIR
• Command: $(command -v askgpt 2>/dev/null || echo "$(uv tool dir)/bin/askgpt")"

    if [ -n "$INSTALL_FROM_LOCAL" ]; then
        echo "• Source code: $SOURCE_DIR"
    else
        echo "• Program files: $INSTALL_DIR/askgpt"
    fi
    
    echo -e "
${BOLD}🚀 What's Next:${NC}

${BOLD}1. For CLI users:${NC}
   • Run: askgpt run \"your prompt here\"
   • Examples:
     askgpt run \"Create a Python hello world script\"
     askgpt run \"Analyze the files in this directory\" --read-only

${BOLD}2. Configure API Keys (if not done):${NC}
   • Edit: $ENV_LOCATION
   • Add your OpenAI, Anthropic, or setup Ollama"

    if [ -z "$INSTALL_FROM_LOCAL" ]; then
        echo -e "
${BOLD}📚 Documentation:${NC}
   • Usage Guide: $DOCS_BASE/README.md
   • Hooks System: $DOCS_BASE/HOOKS.md"
    fi
    
    echo -e "
${BOLD}🆘 Need Help?${NC}
   • Run: askgpt --help
   • Check: askgpt run \"test connection\"
   • Issues: https://github.com/meirm/askgpt/issues

${GREEN}Happy coding with askgpt! 🤖✨${NC}
"
}

# Parse command line arguments
parse_args() {
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --local) INSTALL_FROM_LOCAL=1 ;;
            --help) 
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --local    Install from local repository (for development)"
                echo "  --help     Show this help message"
                echo ""
                echo "Examples:"
                echo "  # Install from internet (production):"
                echo "  curl -fsSL https://raw.githubusercontent.com/meirm/askgpt/main/install.sh | bash"
                echo ""
                echo "  # Install from local repository (development):"
                echo "  ./install.sh --local"
                exit 0
                ;;
            --no-confirm) NO_CONFIRM=1 ;;
            --no-test) NO_TEST=1 ;;
            --no-api-config) NO_API_CONFIG=1 ;;
            *) echo "Unknown parameter: $1"; exit 1 ;;

        esac
        shift
    done
}

# Main installation flow
main() {
    parse_args "$@"
    
    print_header
    
    if [ -n "$INSTALL_FROM_LOCAL" ]; then
        echo "Installing from LOCAL REPOSITORY (development mode)."
    else
        echo "Installing from INTERNET (production mode)."
    fi
    echo "This script will install askGPT CLI tool."
    echo
    if [ -z "$NO_CONFIRM" ]; then
        read -p "$(echo -e "${YELLOW}Continue with installation? (y/N): ${NC}")" -n 1 -r
    else
        REPLY="Y"
    fi
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    check_requirements
    install_askgpt
    setup_configuration
    if [ -z "$NO_API_CONFIG" ]; then
        setup_api_keys
    fi
    if [ -z "$NO_TEST" ]; then
        test_installation
    fi
    show_completion_message
}

# Handle script interruption
trap 'echo -e "\n${RED}Installation interrupted.${NC}"; exit 1' INT TERM

# Run main installation
main "$@"