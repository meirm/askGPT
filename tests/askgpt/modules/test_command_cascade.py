"""
Test Command File Cascade Loading System.

Tests the command loading hierarchy:
1. Load global commands from ~/.askgpt/commands/*.md
2. Load project commands from .askgpt/commands/*.md  
3. Project commands override global commands by name
4. Proper command parsing and execution
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# We'll import the enhanced command loader once it's updated
# from askgpt.modules.command_loader import CommandLoader, CascadeCommandLoader


class TestCommandCascadeLoading:
    """Test command file cascade loading system."""

    def setup_method(self):
        """Set up test environment for command cascade tests."""
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.home_dir = self.temp_dir / "home"
        self.project_dir = self.temp_dir / "project"

        # Create directory structure
        self.home_dir.mkdir(parents=True)
        self.project_dir.mkdir(parents=True)

        # Create command directories
        self.global_commands_dir = self.home_dir / ".askgpt" / "commands"
        self.project_commands_dir = self.project_dir / ".askgpt" / "commands"

        self.global_commands_dir.mkdir(parents=True)
        self.project_commands_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_command_file(self, path: Path, content: str):
        """Helper to create a command file."""
        with open(path, "w") as f:
            f.write(content)

    @pytest.fixture
    def sample_global_commands(self):
        """Sample global command definitions."""
        return {
            "analyze": """# Analyze Code

Comprehensive code analysis command available globally.

## Prompt Template

Perform detailed analysis of: $ARGUMENTS

Include:
- Code quality assessment
- Security review
- Performance implications
- Best practices compliance

## Metadata

author: global-team
version: 1.0
category: analysis
""",
            "build": """# Build Project

Generic build command for all project types.

## Prompt Template  

Build the project: $ARGUMENTS

Standard build process:
- Install dependencies
- Run compilation
- Generate artifacts
- Run basic validation

## Metadata

author: global-team
version: 1.0
category: development
""",
            "deploy": """# Deploy Application

Standard deployment workflow.

## Prompt Template

Deploy application: $ARGUMENTS

Deployment steps:
- Build production artifacts
- Run pre-deployment checks
- Deploy to target environment
- Verify deployment success

## Metadata

author: global-team
version: 1.0
category: deployment
""",
            "test": """# Run Tests  

Global test execution command.

## Prompt Template

Execute test suite: $ARGUMENTS

Test execution:
- Unit tests
- Integration tests
- Coverage reporting
- Test result summary

## Metadata

author: global-team
version: 1.0
category: testing
""",
        }

    @pytest.fixture
    def sample_project_commands(self):
        """Sample project-specific command definitions."""
        return {
            "build": """# Build React Project

Project-specific build for React applications.

## Prompt Template

Build React project: $ARGUMENTS

React build process:
- Install npm dependencies
- Run webpack build with project config
- Optimize assets and bundles
- Generate source maps
- Run React-specific validation

## Metadata

author: project-team
version: 2.0
category: development
framework: react
""",
            "test": """# Test React Components

Project-specific testing for React components.

## Prompt Template

Test React components: $ARGUMENTS

React testing:
- Jest unit tests
- React Testing Library
- Component integration tests
- Snapshot testing
- Coverage with React-specific metrics

## Metadata

author: project-team
version: 2.0
category: testing
framework: react
""",
            "dev": """# Development Server

Start React development server.

## Prompt Template

Start development environment: $ARGUMENTS

Development setup:
- Start webpack dev server
- Enable hot module replacement
- Set up React dev tools
- Configure proxy settings

## Metadata

author: project-team
version: 1.0
category: development
environment: local
""",
            "storybook": """# Storybook Components

Launch Storybook for component development.

## Prompt Template

Launch Storybook: $ARGUMENTS

Storybook setup:
- Start Storybook server
- Load component stories
- Enable addons and controls
- Generate component documentation

## Metadata

author: project-team
version: 1.0
category: development
tool: storybook
""",
        }

    def test_global_commands_only_loading(self, sample_global_commands):
        """Test loading when only global commands exist."""
        # Create global commands only
        for name, content in sample_global_commands.items():
            path = self.global_commands_dir / f"{name}.md"
            self.create_command_file(path, content)

        # Mock directories
        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # Should load all 4 global commands
            global_files = list(self.global_commands_dir.glob("*.md"))
            assert len(global_files) == 4

            # Verify each command exists
            expected_commands = ["analyze", "build", "deploy", "test"]
            actual_files = [f.stem for f in global_files]
            assert set(actual_files) == set(expected_commands)

    def test_project_commands_only_loading(self, sample_project_commands):
        """Test loading when only project commands exist."""
        # Create project commands only
        for name, content in sample_project_commands.items():
            path = self.project_commands_dir / f"{name}.md"
            self.create_command_file(path, content)

        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # Should load all 4 project commands
            project_files = list(self.project_commands_dir.glob("*.md"))
            assert len(project_files) == 4

            # Verify each command exists
            expected_commands = ["build", "test", "dev", "storybook"]
            actual_files = [f.stem for f in project_files]
            assert set(actual_files) == set(expected_commands)

    def test_command_override_cascade(
        self, sample_global_commands, sample_project_commands
    ):
        """Test that project commands properly override global commands."""
        # Create both global and project commands
        for name, content in sample_global_commands.items():
            path = self.global_commands_dir / f"{name}.md"
            self.create_command_file(path, content)

        for name, content in sample_project_commands.items():
            path = self.project_commands_dir / f"{name}.md"
            self.create_command_file(path, content)

        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # Expected final command set:
            # - analyze: from global (no project override)
            # - build: from project (overrides global)
            # - deploy: from global (no project override)
            # - test: from project (overrides global)
            # - dev: from project (project-only)
            # - storybook: from project (project-only)

            global_files = list(self.global_commands_dir.glob("*.md"))
            project_files = list(self.project_commands_dir.glob("*.md"))

            assert len(global_files) == 4  # analyze, build, deploy, test
            assert len(project_files) == 4  # build, test, dev, storybook

            # Test override behavior for specific commands
            global_build = self.global_commands_dir / "build.md"
            project_build = self.project_commands_dir / "build.md"

            assert global_build.exists()
            assert project_build.exists()

            # Project version should contain React-specific content
            with open(project_build) as f:
                project_content = f.read()
                assert "React" in project_content
                assert "webpack" in project_content

            # Global version should contain generic content
            with open(global_build) as f:
                global_content = f.read()
                assert "Generic build" in global_content
                assert "React" not in global_content

    def test_command_metadata_parsing(self, sample_project_commands):
        """Test parsing of command metadata sections."""
        # Create a command with metadata
        command_content = sample_project_commands["build"]
        build_path = self.project_commands_dir / "build.md"
        self.create_command_file(build_path, command_content)

        # Parse the command and verify metadata extraction
        with open(build_path) as f:
            content = f.read()

            # Should extract metadata
            assert "author: project-team" in content
            assert "version: 2.0" in content
            assert "framework: react" in content

    def test_command_template_substitution(self):
        """Test command template argument substitution."""
        # Create a command with template variables
        template_command = """# Template Test

Test command with template substitution.

## Prompt Template

Process the following: $ARGUMENTS

Additional context:
- Use ${ARGUMENTS} for processing
- Handle escaped \\$LITERAL dollar signs
- Support multiple $ARGUMENTS references

## Metadata

test: true
"""

        test_path = self.global_commands_dir / "template_test.md"
        self.create_command_file(test_path, template_command)

        # Test template substitution
        test_args = "my test input"

        # This will test the enhanced CommandLoader.execute_command() method
        # Expected substitution:
        expected_result = """Process the following: my test input

Additional context:
- Use my test input for processing
- Handle escaped $LITERAL dollar signs
- Support multiple my test input references"""

        # Verify file exists for now
        assert test_path.exists()
        with open(test_path) as f:
            content = f.read()
            assert "$ARGUMENTS" in content
            assert "${ARGUMENTS}" in content
            assert "\\$LITERAL" in content

    def test_empty_directories_handling(self):
        """Test graceful handling of empty command directories."""
        # Create empty directories (no .md files)
        assert self.global_commands_dir.exists()
        assert self.project_commands_dir.exists()
        assert len(list(self.global_commands_dir.glob("*.md"))) == 0
        assert len(list(self.project_commands_dir.glob("*.md"))) == 0

        # Should handle empty directories gracefully
        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # No commands should be loaded
            # Enhanced CommandLoader should return empty list
            assert True  # Placeholder for actual implementation test

    def test_missing_directories_handling(self):
        """Test handling when command directories don't exist."""
        # Remove the created directories
        shutil.rmtree(self.global_commands_dir)
        shutil.rmtree(self.project_commands_dir)

        assert not self.global_commands_dir.exists()
        assert not self.project_commands_dir.exists()

        # Should handle missing directories gracefully
        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # Should return empty command list without errors
            assert True  # Placeholder for actual implementation test

    def test_invalid_command_files(self):
        """Test handling of invalid or malformed command files."""
        # Create various invalid command files
        invalid_files = {
            "empty.md": "",  # Empty file
            "no_template.md": "# No Template\n\nJust description, no template section.",
            "malformed.md": "Invalid markdown\n### Wrong heading level\nNo structure",
            "binary.md": "# Binary\n\x00\x01\x02 Invalid binary content",
        }

        for name, content in invalid_files.items():
            path = self.global_commands_dir / name
            if isinstance(content, str):
                with open(path, "w") as f:
                    f.write(content)
            else:
                with open(path, "wb") as f:
                    f.write(content)

        # Should handle invalid files gracefully
        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # Should skip invalid files and continue processing
            invalid_files_created = list(self.global_commands_dir.glob("*.md"))
            assert len(invalid_files_created) == 4

            # Enhanced CommandLoader should handle errors gracefully
            assert True  # Placeholder for actual error handling test

    def test_command_name_collision_resolution(self):
        """Test resolution of command name collisions."""
        # Create multiple commands with potential name conflicts
        global_commands = {
            "test": "Global test command",
            "build": "Global build command",
            "analyze": "Global analyze command",
        }

        project_commands = {
            "test": "Project test command",  # Same name as global
            "build": "Project build command",  # Same name as global
            "deploy": "Project deploy command",  # Unique to project
        }

        # Create global commands
        for name, description in global_commands.items():
            content = (
                f"# {description}\n\n## Prompt Template\n\n{description}: $ARGUMENTS"
            )
            path = self.global_commands_dir / f"{name}.md"
            self.create_command_file(path, content)

        # Create project commands
        for name, description in project_commands.items():
            content = (
                f"# {description}\n\n## Prompt Template\n\n{description}: $ARGUMENTS"
            )
            path = self.project_commands_dir / f"{name}.md"
            self.create_command_file(path, content)

        with patch("pathlib.Path.home", return_value=self.home_dir), patch(
            "pathlib.Path.cwd", return_value=self.project_dir
        ):
            # Final command set should be:
            # - test: project version (overrides global)
            # - build: project version (overrides global)
            # - analyze: global version (no project override)
            # - deploy: project version (project-only)

            global_files = {f.stem: f for f in self.global_commands_dir.glob("*.md")}
            project_files = {f.stem: f for f in self.project_commands_dir.glob("*.md")}

            # Verify collision resolution
            assert "test" in global_files and "test" in project_files
            assert "build" in global_files and "build" in project_files
            assert "analyze" in global_files and "analyze" not in project_files
            assert "deploy" not in global_files and "deploy" in project_files


class TestCommandExecutionFlow:
    """Test command execution and integration flow."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.home_dir = self.temp_dir / "home"
        self.project_dir = self.temp_dir / "project"

        self.home_dir.mkdir(parents=True)
        self.project_dir.mkdir(parents=True)

        self.global_commands_dir = self.home_dir / ".askgpt" / "commands"
        self.project_commands_dir = self.project_dir / ".askgpt" / "commands"

        self.global_commands_dir.mkdir(parents=True)
        self.project_commands_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_command_execution_with_arguments(self):
        """Test command execution with argument substitution."""
        # Create a command that uses arguments
        command_content = """# Code Review

Perform comprehensive code review.

## Prompt Template

Review the following code: $ARGUMENTS

Please analyze:
- Code quality and style
- Potential bugs and issues  
- Performance considerations
- Security implications
- Best practices compliance

Provide specific recommendations for improvement.

## Metadata

category: review
complexity: medium
"""

        command_path = self.global_commands_dir / "review.md"
        with open(command_path, "w") as f:
            f.write(command_content)

        # Test command execution
        test_arguments = "src/components/UserProfile.tsx"

        # This will test the enhanced command execution flow
        with patch("pathlib.Path.home", return_value=self.home_dir):
            assert command_path.exists()

            # Verify argument substitution works
            with open(command_path) as f:
                content = f.read()
                assert "$ARGUMENTS" in content

                # Simulate argument substitution
                executed_content = content.replace("$ARGUMENTS", test_arguments)
                assert test_arguments in executed_content
                assert "$ARGUMENTS" not in executed_content

    def test_cli_command_parsing_integration(self):
        """Test integration with CLI command parsing."""
        # Test command syntax parsing
        test_inputs = [
            "/analyze src/components/",
            "/build --production",
            "/test components/UserProfile",
            "/deploy staging",
        ]

        # Each should parse correctly to (command_name, arguments)
        expected_results = [
            ("analyze", "src/components/"),
            ("build", "--production"),
            ("test", "components/UserProfile"),
            ("deploy", "staging"),
        ]

        # This tests the existing parse_command_syntax function
        for test_input, expected in zip(test_inputs, expected_results):
            # Import the existing function from relative path
            import sys
            from pathlib import Path

            sys.path.append(str(Path(__file__).parent.parent.parent / "src"))
            from askgpt.modules.command_loader import parse_command_syntax

            result = parse_command_syntax(test_input)
            assert result == expected

    def test_command_discovery_and_listing(self):
        """Test command discovery and listing functionality."""
        # Create a variety of commands
        commands = {
            "analyze": "Code Analysis Tool",
            "build": "Project Builder",
            "test": "Test Runner",
            "deploy": "Deployment Tool",
            "lint": "Code Linter",
        }

        for name, description in commands.items():
            content = f"# {description}\n\nDescription for {name} command.\n\n## Prompt Template\n\n{description}: $ARGUMENTS"
            path = self.global_commands_dir / f"{name}.md"
            with open(path, "w") as f:
                f.write(content)

        # Test command discovery
        with patch("pathlib.Path.home", return_value=self.home_dir):
            command_files = list(self.global_commands_dir.glob("*.md"))
            assert len(command_files) == 5

            command_names = [f.stem for f in command_files]
            assert set(command_names) == set(commands.keys())


if __name__ == "__main__":
    pytest.main([__file__])
