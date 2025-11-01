"""
Tests for skill fallback functionality in command execution.

Tests that skills can be called as commands via /<skill-name> syntax
when no command with that name exists.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from askgpt.modules.cascade_command_loader import CascadeCommandLoader
from askgpt.modules.skill_loader import SkillLoader


class TestSkillCommandFallback:
    """Test skill fallback when command not found."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def command_loader(self, temp_dir):
        """Create a CommandLoader with temporary directories."""
        loader = CascadeCommandLoader(
            working_dir=temp_dir / "project",
            allowed_tools=None,  # Allow all for testing
        )
        # Patch directories to use temp dirs
        loader.global_commands_dir = temp_dir / "global_commands"
        loader.project_commands_dir = temp_dir / "project_commands"
        loader.global_commands_dir.mkdir(parents=True, exist_ok=True)
        loader.project_commands_dir.mkdir(parents=True, exist_ok=True)
        return loader

    @pytest.fixture
    def skill_loader(self, temp_dir):
        """Create a SkillLoader with temporary directories."""
        loader = SkillLoader(
            working_dir=temp_dir / "project",
            allowed_tools=["skill"],  # Enable skills system
        )
        # Patch directories to use temp dirs
        loader.global_skills_dir = temp_dir / "global_skills"
        loader.project_skills_dir = temp_dir / "project_skills"
        loader.builtin_skills_dir = temp_dir / "builtin_skills"
        loader.global_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.project_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.builtin_skills_dir.mkdir(parents=True, exist_ok=True)
        return loader

    def test_skill_fallback_when_command_not_found(self, command_loader, skill_loader):
        """Test that skill is loaded when command not found."""
        # Create a test skill
        skill_dir = skill_loader.global_skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: test-skill
description: A test skill for command fallback
---

# Test Skill

This is a test skill that can be called as a command.

Follow these instructions when using this skill.
""")

        # Load skills metadata
        skill_loader.load_skills_metadata()

        # Create command loader with skill_loader
        command_loader.skill_loader = skill_loader

        # Try to execute skill as command
        result = command_loader.execute_command("test-skill", "test arguments")

        # Should return skill instructions
        assert result is not None
        assert "This is a test skill" in result
        assert "Follow these instructions" in result

    def test_command_priority_over_skill(self, command_loader, skill_loader):
        """Test that command takes priority over skill with same name."""
        # Create a command file
        command_file = command_loader.global_commands_dir / "shared-name.md"
        command_file.write_text("""# Shared Name Command

This is a command file.

## Prompt Template

Execute command: $ARGUMENTS
""")

        # Create a skill with same name
        skill_dir = skill_loader.global_skills_dir / "shared-name"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: shared-name
description: A skill with same name as command
---

# Shared Name Skill

This is a skill file.
""")

        # Load both
        skill_loader.load_skills_metadata()
        command_loader.load_commands_cascade()

        # Create command loader with skill_loader
        command_loader.skill_loader = skill_loader

        # Execute - should use command, not skill
        result = command_loader.execute_command("shared-name", "test")

        # Should return command prompt, not skill instructions
        assert result is not None
        assert "Execute command: test" in result
        assert "This is a skill file" not in result

    def test_argument_substitution_in_skills(self, command_loader, skill_loader):
        """Test that $ARGUMENTS is substituted in skill instructions."""
        # Create a skill with $ARGUMENTS placeholder
        skill_dir = skill_loader.global_skills_dir / "substitute-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: substitute-skill
description: A skill with argument substitution
---

# Substitute Skill

Process the following: $ARGUMENTS

Complete the task as specified.
""")

        skill_loader.load_skills_metadata()
        command_loader.skill_loader = skill_loader

        result = command_loader.execute_command("substitute-skill", "my task")

        assert result is not None
        assert "Process the following: my task" in result
        assert "$ARGUMENTS" not in result

    def test_arguments_appended_when_no_substitution_pattern(self, command_loader, skill_loader):
        """Test that arguments are appended when no $ARGUMENTS pattern in skill."""
        # Create a skill without $ARGUMENTS placeholder
        skill_dir = skill_loader.global_skills_dir / "append-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: append-skill
description: A skill without argument substitution pattern
---

# Append Skill

This skill will have arguments appended.

Follow the instructions.
""")

        skill_loader.load_skills_metadata()
        command_loader.skill_loader = skill_loader

        result = command_loader.execute_command("append-skill", "my task details")

        assert result is not None
        assert "Follow the instructions" in result
        assert "Task: my task details" in result

    def test_no_arguments_in_skill(self, command_loader, skill_loader):
        """Test skill execution with no arguments."""
        # Create a skill
        skill_dir = skill_loader.global_skills_dir / "no-args-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: no-args-skill
description: A skill used without arguments
---

# No Args Skill

Use this skill as needed.
""")

        skill_loader.load_skills_metadata()
        command_loader.skill_loader = skill_loader

        result = command_loader.execute_command("no-args-skill", "")

        assert result is not None
        assert "Use this skill as needed" in result
        assert "Task:" not in result

    def test_disabled_skill_not_executed(self, command_loader, skill_loader):
        """Test that disabled skills are not executed."""
        # Create a skill that will be disabled (requires tools not allowed)
        skill_dir = skill_loader.global_skills_dir / "disabled-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: disabled-skill
description: A disabled skill
allowed-tools: blocked-tool
---

# Disabled Skill

This skill requires blocked tools.
""")

        # Create skill loader that blocks this tool
        blocked_skill_loader = SkillLoader(
            working_dir=skill_loader.working_dir,
            allowed_tools=["skill"],  # Skills enabled but blocked-tool not allowed
        )
        blocked_skill_loader.global_skills_dir = skill_loader.global_skills_dir
        blocked_skill_loader.project_skills_dir = skill_loader.project_skills_dir
        blocked_skill_loader.builtin_skills_dir = skill_loader.builtin_skills_dir

        blocked_skill_loader.load_skills_metadata()
        command_loader.skill_loader = blocked_skill_loader

        # Should not find skill (it's disabled)
        result = command_loader.execute_command("disabled-skill", "")

        assert result is None

    def test_skill_not_found_returns_none(self, command_loader, skill_loader):
        """Test that None is returned when neither command nor skill found."""
        skill_loader.load_skills_metadata()
        command_loader.skill_loader = skill_loader

        result = command_loader.execute_command("nonexistent", "test")

        assert result is None

    def test_skill_without_skill_loader_returns_none(self, command_loader):
        """Test that command loader without skill_loader doesn't fall back to skills."""
        # Don't set skill_loader
        result = command_loader.execute_command("any-skill-name", "test")

        # Should return None since no command exists and no skill_loader
        assert result is None

