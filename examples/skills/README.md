# Skill Examples

Skills are modular capabilities that extend nano-agent's functionality by providing domain-specific expertise, workflows, and best practices that the agent automatically uses when relevant.

## What are Skills?

Skills are directories containing `SKILL.md` files stored in `~/.askgpt/skills/` that:
- **Package expertise**: Bundle instructions, metadata, and resources
- **Auto-trigger**: Automatically matched based on user prompts
- **Progressive disclosure**: Load content in stages (metadata → instructions → resources)
- **Extend capabilities**: Transform general-purpose agents into specialists

Think of Skills as "onboarding guides" - they teach the AI how to perform specific tasks by providing structured instructions, examples, and context.

## Skill Directory Structure

Skills are directories with at least a `SKILL.md` file:

```
skill-name/
├── SKILL.md          # Main skill file (required)
├── examples/         # Optional: Example files
├── templates/        # Optional: Template files
└── scripts/          # Optional: Helper scripts
```

## SKILL.md Format

Skills must use YAML frontmatter with metadata:

```markdown
---
name: skill-name
description: When and how to use this skill. Use when the user asks to [trigger keywords].
tools: ["read_file", "write_file", "list_directory"]
---

# Skill Name

## Instructions

Detailed instructions for performing [skill task].

### Step 1: [First step]

[Instructions for first step]

### Step 2: [Second step]

[Instructions for second step]

## Output Format

[How to format the output]

## Examples

[Example scenarios and outputs]

## Notes

[Additional context or requirements]
```

### YAML Frontmatter (Required)

- **name**: Skill identifier (must match directory name)
- **description**: When to use this skill - include trigger keywords
- **tools**: List of required tools for permission validation
  - Use `[]` if no specific tools are needed
  - Examples: `["read_file"]`, `["read_file", "write_file", "list_directory"]`

**Important**: The description should include "Use when..." to help the matching system identify when to trigger the skill.

## Progressive Disclosure

Skills load content in three stages:

### Level 1: Metadata (Always Loaded)
- YAML frontmatter (name, description, tools)
- ~100 tokens
- Used for skill discovery and matching

### Level 2: Instructions (When Triggered)
- Full `SKILL.md` content
- ~5k tokens
- Loaded when user prompt matches skill description

### Level 3: Resources (As Needed)
- Additional files (scripts, templates, examples)
- Unlimited tokens
- Loaded on-demand when referenced

This approach allows you to have many skills installed without context penalty - only relevant skills consume context.

## Example Skills

### API Testing Skill
**Directory**: `api-testing/`

Generates comprehensive API tests including:
- Endpoint testing with various HTTP methods
- Request/response validation
- Authentication and authorization tests
- Integration test scenarios

**Tools**: `["read_file", "write_file", "grep_search"]`

**Triggers**: "test API", "API tests", "endpoint testing", "validate API"

### Data Analysis Skill
**Directory**: `data-analysis/`

Performs data analysis tasks including:
- Data exploration and cleaning
- Statistical analysis
- Visualization generation
- Insight extraction

**Tools**: `["read_file", "write_file", "list_directory"]`

**Triggers**: "analyze data", "data analysis", "statistical analysis", "create visualizations"

### Security Audit Skill
**Directory**: `security-audit-example/`

Audits code for security vulnerabilities:
- Authentication/authorization review
- Input validation checks
- Cryptography assessment
- Vulnerability identification

**Tools**: `["read_file", "grep_search", "list_directory"]`

**Triggers**: "security audit", "check vulnerabilities", "security review"

## Usage

Skills are automatically matched based on user prompts. No explicit invocation needed!

```bash
# The skill automatically triggers when you ask relevant questions
askgpt run "Generate API tests for this endpoint"
# → Automatically uses api-testing skill

askgpt run "Analyze this sales data and create visualizations"
# → Automatically uses data-analysis skill

askgpt run "Perform a security audit on this codebase"
# → Automatically uses security-audit skill
```

### Manual Skill Management

```bash
# List all available skills
askgpt skills list

# Show skill details
askgpt skills show api-testing

# Show skill instructions
askgpt skills show api-testing --full

# Install built-in skills
askgpt skills install-builtin
```

## Creating Your Own Skill

1. **Create directory**: `mkdir ~/.askgpt/skills/my-skill`
2. **Create SKILL.md**: Write instructions with YAML frontmatter
3. **Add resources** (optional): Include scripts, templates, examples
4. **Test matching**: Ask questions that should trigger the skill

### Example Template

```markdown
---
name: my-skill
description: Perform [task]. Use when the user asks to [trigger keywords].
tools: ["read_file", "write_file"]
---

# My Skill

## Instructions

You are a [role] specializing in [domain].

### Step 1: [Initial Action]

[What to do first]

### Step 2: [Main Process]

[Main workflow]

### Step 3: [Output]

[How to format results]

## Output Format

[Expected output structure]

## Examples

[Example scenarios]

## Notes

[Additional context]
```

### Key Writing Tips

1. **Clear triggers**: Include trigger keywords in description
2. **Structured steps**: Break down complex tasks into steps
3. **Specific instructions**: Be explicit about what to do
4. **Examples**: Show expected outputs
5. **Tool usage**: Document which tools to use when

## Installation

### Manual Installation

Copy skill directories to `~/.askgpt/skills/`:

```bash
# Copy a single skill
cp -r examples/skills/api-testing ~/.askgpt/skills/

# Copy all example skills
cp -r examples/skills/* ~/.askgpt/skills/
```

### Built-in Skills

Built-in skills are automatically installed on first run:
- `readme-generator`
- `code-formatting-checker`
- `write-release-notes`
- `security-audit`

## Permission System

Skills can specify required tools in their metadata. If `allowed_tools` is configured:
- Skills without `tools:` metadata are allowed when Skills system is enabled
- Skills with `tools:` require all listed tools to be in `allowed_tools`
- Skills with missing tools will be disabled with a reason

**Example**:
```yaml
tools: ["read_file", "write_file"]
```

The Skills system is enabled if `"skill"` is in `allowed_tools`.

## Skill Matching

Skills are automatically matched based on:
- **Keyword matching**: Words in user prompt vs skill description
- **Phrase matching**: Multi-word phrases in skill description
- **Relevance scoring**: Higher scores for better matches

Only enabled skills (those with required tools available) are matched.

## Advanced Features

### Resources

Skills can include additional files:

```
my-skill/
├── SKILL.md
├── templates/
│   └── example-template.py
├── scripts/
│   └── helper.sh
└── examples/
    └── sample-output.json
```

Resources are loaded on-demand when the agent needs them (Level 3).

### Cascade System

Skills can be defined in two locations:
1. **Global**: `~/.askgpt/skills/` (available everywhere)
2. **Project**: `.askgpt/skills/` (project-specific, overrides global)

Project skills take precedence over global skills with the same name.

## Tips

- **Be specific in descriptions**: Include trigger keywords ("Use when...")
- **Structure instructions**: Break complex tasks into clear steps
- **Provide examples**: Show expected outputs and usage
- **Specify tools**: Always list required tools in metadata
- **Keep focused**: One skill, one domain
- **Document well**: Clear instructions = better results

## Best Practices

1. **Naming**: Use lowercase with hyphens (`api-testing`, not `ApiTesting`)
2. **Descriptions**: Include "Use when..." with trigger keywords
3. **Instructions**: Be specific and actionable
4. **Tools**: Only specify tools actually needed
5. **Resources**: Include examples and templates for complex skills
6. **Testing**: Test skill matching with various prompts

## Skill vs Command vs Agent

**Skills** are:
- Complex, multi-step workflows
- Auto-triggered by matching user prompts
- Progressive disclosure (metadata → instructions → resources)
- Domain-specific expertise packages

**Commands** are:
- Simple prompt templates
- User-invoked with `/command`
- Direct substitution and execution
- Single-shot prompts

**Agents** are:
- Personality extensions
- Change how AI communicates and behaves
- Always active when selected
- Affect all responses, not specific tasks

Use skills for complex, reusable workflows. Use commands for simple prompt templates. Use agents for personality customization.

## See Also

- Main documentation: `apps/nano_agent_mcp_server/docs/SKILLS.md`
- Built-in skills: `apps/nano_agent_mcp_server/src/nano_agent/data/builtin_skills/`
- Example skills in this directory

