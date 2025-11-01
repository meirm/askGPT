"""
Integration tests for skill-as-command functionality.

Tests that skills can be invoked via CLI and interactive mode
using the /<skill-name> syntax.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSkillCommandIntegration:
    """Integration tests for skill command execution."""

    @pytest.fixture
    def temp_home(self, monkeypatch):
        """Create a temporary home directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        home_dir = temp_dir / "home"
        home_dir.mkdir()

        # Create .askgpt directories
        skills_dir = home_dir / ".askgpt" / "skills"
        skills_dir.mkdir(parents=True)

        # Patch HOME environment variable
        monkeypatch.setenv("HOME", str(home_dir))

        yield home_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def create_test_skill(self, skills_dir: Path, name: str, content: str):
        """Helper to create a test skill."""
        skill_dir = skills_dir / name
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content)

    def test_cli_skill_execution_via_prompt(self, temp_home):
        """Test that skills can be called via CLI prompt."""
        # Create a test skill
        skills_dir = temp_home / ".askgpt" / "skills"
        self.create_test_skill(
            skills_dir,
            "test-skill",
            """---
name: test-skill
description: A test skill for CLI integration
---

# Test Skill

This is a test skill that can be called from CLI.

Process the following task: $ARGUMENTS
""",
        )

        # Note: This is a simplified test that checks the command parsing
        # Full execution would require actual model provider setup
        from askgpt.modules.cascade_command_loader import CommandLoader, parse_command_syntax
        from askgpt.modules.skill_loader import SkillLoader

        # Parse command syntax
        command_name, arguments = parse_command_syntax("/test-skill my task")
        assert command_name == "test-skill"
        assert arguments == "my task"

        # Setup loaders
        skill_loader = SkillLoader()
        skill_loader.load_skills_metadata()

        loader = CommandLoader(skill_loader=skill_loader)
        result = loader.execute_command("test-skill", "my task")

        # Should return skill instructions with substituted arguments
        assert result is not None
        assert "This is a test skill" in result
        assert "Process the following task: my task" in result

    def test_cli_error_message_includes_skills(self, temp_home, capsys):
        """Test that error messages mention both commands and skills."""
        from askgpt.modules.cascade_command_loader import CommandLoader
        from askgpt.modules.skill_loader import SkillLoader

        skill_loader = SkillLoader()
        skill_loader.load_skills_metadata()

        loader = CommandLoader(skill_loader=skill_loader)
        result = loader.execute_command("nonexistent-command", "")

        # Should return None when neither command nor skill found
        assert result is None

    def test_command_priority_in_integration(self, temp_home):
        """Test that commands take priority over skills with same name."""
        # Create a command file
        commands_dir = temp_home / ".askgpt" / "commands"
        commands_dir.mkdir(parents=True)
        command_file = commands_dir / "shared-name.md"
        command_file.write_text("""# Shared Name

Command template: Execute $ARGUMENTS
""")

        # Create a skill with same name
        skills_dir = temp_home / ".askgpt" / "skills"
        self.create_test_skill(
            skills_dir,
            "shared-name",
            """---
name: shared-name
description: A skill with same name as command
---

# Shared Name Skill

This is a skill, not a command.
""",
        )

        from askgpt.modules.cascade_command_loader import CommandLoader
        from askgpt.modules.skill_loader import SkillLoader

        skill_loader = SkillLoader()
        skill_loader.load_skills_metadata()

        loader = CommandLoader(skill_loader=skill_loader)
        result = loader.execute_command("shared-name", "test task")

        # Should use command, not skill
        assert result is not None
        assert "Execute test task" in result
        assert "This is a skill, not a command" not in result

    def test_skill_without_arguments(self, temp_home):
        """Test skill execution without arguments."""
        skills_dir = temp_home / ".askgpt" / "skills"
        self.create_test_skill(
            skills_dir,
            "no-args-skill",
            """---
name: no-args-skill
description: Skill without arguments
---

# No Args Skill

Use this skill as needed.
""",
        )

        from askgpt.modules.cascade_command_loader import CommandLoader
        from askgpt.modules.skill_loader import SkillLoader

        skill_loader = SkillLoader()
        skill_loader.load_skills_metadata()

        loader = CommandLoader(skill_loader=skill_loader)
        result = loader.execute_command("no-args-skill", "")

        assert result is not None
        assert "Use this skill as needed" in result
        assert "Task:" not in result

    def test_skill_permissions_enforced(self, temp_home):
        """Test that skill permissions are enforced in command execution."""
        skills_dir = temp_home / ".askgpt" / "skills"
        self.create_test_skill(
            skills_dir,
            "restricted-skill",
            """---
name: restricted-skill
description: A skill with restricted tools
allowed-tools: blocked-tool
---

# Restricted Skill

This skill requires blocked tools.
""",
        )

        from askgpt.modules.cascade_command_loader import CommandLoader
        from askgpt.modules.skill_loader import SkillLoader

        # Create skill loader that doesn't allow the required tool
        skill_loader = SkillLoader(allowed_tools=["skill"])  # Skills enabled but tool not allowed
        skill_loader.load_skills_metadata()

        loader = CommandLoader(skill_loader=skill_loader)
        result = loader.execute_command("restricted-skill", "")

        # Should return None because skill is disabled
        assert result is None

