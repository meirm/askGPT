# Command Examples

Commands are reusable prompt templates that simplify common tasks by packaging frequently-used prompts into easy-to-invoke commands.

## What are Commands?

Commands are markdown files stored in `~/.askgpt/commands/` that:
- **Template prompts**: Define reusable prompt structures
- **Accept arguments**: Use `$ARGUMENTS` placeholder for user input
- **Support shell evaluation**: Can execute shell commands (optional)
- **Include metadata**: YAML frontmatter with name, description, and tools

Think of commands as "prompt shortcuts" - instead of typing a long prompt every time, you create a command once and reuse it.

## Command File Format

Commands must use YAML frontmatter with metadata:

```markdown
---
name: command-name
description: Brief description of what the command does.
tools: ["read_file", "write_file"]
---

# Command Title

Description of what this command does.

## Prompt Template

Your prompt template here with $ARGUMENTS placeholder.

The $ARGUMENTS will be replaced with whatever
the user passes after the command name.

## Usage

Examples of how to use this command.

## Notes

Additional context or requirements.
```

### YAML Frontmatter (Required)

- **name**: Command identifier (must match filename)
- **description**: Brief description (shown in `commands list`)
- **tools**: List of required tools for permission validation
  - Use `[]` if no specific tools are needed
  - Examples: `["read_file"]`, `["read_file", "write_file"]`

### Prompt Template

The main prompt content that will be executed. Use `$ARGUMENTS` (or `${ARGUMENTS}`) as a placeholder for user-provided arguments.

## Usage

### Basic Command Execution

```bash
# Execute a command with arguments
askgpt /code-review "$(cat src/main.py)"

# Command with inline arguments
askgpt /test-generator "def add(a, b): return a + b"

# Command with multiple lines
askgpt /documentation "$(cat - <<EOF
class MyClass:
    def method(self):
        pass
EOF
)"
```

### Using Commands in Interactive Mode

```bash
# In interactive mode
nano-agent> /code-review "$(cat src/file.py)"
nano-agent> /test-generator "def function(): pass"
```

## Example Commands

### Code Review Command
**File**: `example-code-review.md`

Performs comprehensive code reviews focusing on:
- Code quality and readability
- Best practices compliance
- Potential bugs and issues
- Refactoring suggestions

**Tools**: `["read_file", "grep_search"]`

**Usage**: `askgpt /code-review "$(cat src/main.py)"`

### Test Generator Command
**File**: `example-test-generator.md`

Generates comprehensive unit tests including:
- Main functionality tests
- Edge cases and error handling
- Integration scenarios
- Proper test structure

**Tools**: `["read_file", "write_file"]`

**Usage**: `askgpt /test-generator "$(cat utils/helper.py)"`

### Documentation Command
**File**: `example-documentation.md`

Generates documentation including:
- Code docstrings
- API documentation
- README files
- Inline comments

**Tools**: `["read_file", "write_file"]`

**Usage**: `askgpt /documentation "$(cat api/endpoints.py)"`

## Advanced Features

### Shell Command Evaluation

Commands can include shell command evaluation using `` $`command` `` syntax:

```markdown
## Prompt Template

Current date: $`date "+%Y-%m-%d"`
User: $`whoami`
Task: $ARGUMENTS
```

**Note**: Shell evaluation must be enabled via `NANO_CLI_ENABLE_COMMAND_EVAL=true` or `enable_command_eval=True`.

**Security**: Shell evaluation is disabled by default for security. Only enable it if you trust your command files.

### Argument Substitution

Multiple syntaxes are supported:
- `$ARGUMENTS` - Simple substitution
- `${ARGUMENTS}` - Braced syntax
- `$arguments` - Lowercase variant
- `${arguments}` - Lowercase braced

All variants are replaced with the same value.

### Escaping

To show a literal `$ARGUMENTS` without substitution, escape it:
- `\$ARGUMENTS` - Shows as `$ARGUMENTS` in output

## Creating Your Own Command

1. **Choose a name**: Use lowercase with hyphens (e.g., `my-command.md`)
2. **Define purpose**: What does this command do?
3. **Write prompt template**: Use `$ARGUMENTS` where user input goes
4. **Specify tools**: List required tools in metadata
5. **Add usage examples**: Show how to use it

### Example Template

```markdown
---
name: my-command
description: Brief description of what this command does.
tools: ["read_file"]
---

# My Command

Description of what this command does.

## Prompt Template

Please perform the following task: $ARGUMENTS

Provide detailed output with:
- Point 1
- Point 2
- Point 3

## Usage

```bash
askgpt /my-command "task description"
```

## Examples

```bash
# Example 1
askgpt /my-command "example input"

# Example 2
askgpt /my-command "$(cat input.txt)"
```

## Notes

Additional context or requirements.
```

## Installation

Copy command files to `~/.askgpt/commands/`:

```bash
# Copy a single command
cp examples/commands/example-code-review.md ~/.askgpt/commands/code-review.md

# Copy all example commands
cp examples/commands/*.md ~/.askgpt/commands/
```

## Command Management

```bash
# List all commands
askgpt commands list

# Show command details
askgpt commands show code-review

# Create new command template
askgpt commands create my-new-command

# Edit a command (opens in default editor)
askgpt commands edit code-review
```

## Permission System

Commands can specify required tools in their metadata. If `allowed_tools` is configured:
- Commands without `tools:` metadata are allowed by default
- Commands with `tools:` require all listed tools to be in `allowed_tools`
- Commands with missing tools will fail with a clear error message

**Example**:
```yaml
tools: ["read_file", "write_file"]
```

If `read_file` or `write_file` is not in `allowed_tools`, the command will fail with:
```
[Error: Command requires tools not allowed: write_file]
```

## Tips

- **Keep templates focused**: One command, one purpose
- **Use descriptive names**: Make it clear what the command does
- **Include examples**: Help users understand how to use it
- **Specify tools**: Always list required tools in metadata
- **Test thoroughly**: Ensure `$ARGUMENTS` works as expected
- **Document usage**: Provide clear usage examples

## Best Practices

1. **Naming**: Use lowercase with hyphens (`code-review`, not `CodeReview`)
2. **Arguments**: Always document what arguments the command expects
3. **Tools**: Only specify tools actually needed by the command
4. **Security**: Be careful with shell evaluation - validate inputs
5. **Clarity**: Make prompt templates clear and actionable

## Command vs Skill

**Commands** are:
- Simple prompt templates
- Direct substitution and execution
- User-invoked with `/command`
- Single-shot prompts

**Skills** are:
- Complex instructions with progressive disclosure
- Automatically matched based on user prompt
- Can include resources and scripts
- Loaded on-demand when relevant

Use commands for simple, reusable prompts. Use skills for complex, multi-step workflows.

## See Also

- Main documentation: `apps/nano_agent_mcp_server/COMMANDS.md`
- Example commands in this directory
- User commands in `examples/dot.askgpt/commands/`

