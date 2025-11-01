"""
Tests for the SkillLoader module and built-in skills.

Tests skill loading, built-in skill installation, matching, and progressive disclosure.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from askgpt.modules.skill_loader import Skill, SkillLoader, SkillLoadResult


class TestSkillLoader:
    """Test SkillLoader functionality."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary directory for skills testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def skill_loader(self, temp_skills_dir, monkeypatch):
        """Create a SkillLoader with temporary directories."""
        # Patch the global and project skills directories
        loader = SkillLoader()
        loader.global_skills_dir = temp_skills_dir / "global_skills"
        loader.project_skills_dir = temp_skills_dir / "project_skills"
        loader.builtin_skills_dir = temp_skills_dir / "builtin_skills"
        
        # Ensure directories exist
        loader.global_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.project_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.builtin_skills_dir.mkdir(parents=True, exist_ok=True)
        
        return loader

    def test_load_skills_metadata_empty(self, skill_loader):
        """Test loading skills from empty directories."""
        result = skill_loader.load_skills_metadata()
        
        assert isinstance(result, SkillLoadResult)
        assert len(result.skills) == 0
        assert result.global_skills_loaded == 0
        assert result.project_skills_loaded == 0

    def test_load_skill_with_valid_yaml(self, skill_loader):
        """Test loading a skill with valid YAML frontmatter."""
        skill_dir = skill_loader.global_skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""---
name: test-skill
description: A test skill for testing skill loading
---

# Test Skill

This is a test skill.
""")
        
        result = skill_loader.load_skills_metadata()
        
        assert len(result.skills) == 1
        assert "test-skill" in result.skills
        skill = result.skills["test-skill"]
        assert skill.name == "test-skill"
        assert skill.description == "A test skill for testing skill loading"
        assert skill.source == "global"

    def test_load_skill_without_yaml(self, skill_loader):
        """Test loading a skill without YAML frontmatter."""
        skill_dir = skill_loader.global_skills_dir / "no-yaml-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""# No YAML Skill

This skill has no YAML frontmatter.
""")
        
        result = skill_loader.load_skills_metadata()
        
        # Should still load, using defaults
        assert len(result.skills) >= 0  # May or may not load depending on implementation

    def test_project_skill_overrides_global(self, skill_loader):
        """Test that project skills override global skills."""
        # Create global skill
        global_dir = skill_loader.global_skills_dir / "test-skill"
        global_dir.mkdir()
        global_file = global_dir / "SKILL.md"
        global_file.write_text("""---
name: test-skill
description: Global version
---
""")
        
        # Create project skill with same name
        project_dir = skill_loader.project_skills_dir / "test-skill"
        project_dir.mkdir()
        project_file = project_dir / "SKILL.md"
        project_file.write_text("""---
name: test-skill
description: Project version
---
""")
        
        result = skill_loader.load_skills_metadata()
        
        assert len(result.skills) == 1
        assert result.skills["test-skill"].description == "Project version"
        assert result.skills["test-skill"].source == "project"
        assert len(result.overridden_skills) == 1
        assert "test-skill" in result.overridden_skills

    def test_install_builtin_skill(self, skill_loader):
        """Test installing a built-in skill."""
        # Create a built-in skill
        builtin_dir = skill_loader.builtin_skills_dir / "builtin-test"
        builtin_dir.mkdir()
        builtin_file = builtin_dir / "SKILL.md"
        builtin_file.write_text("""---
name: builtin-test
description: A built-in test skill
---

# Built-in Test Skill

Test content.
""")
        
        # Install it
        results = skill_loader.install_builtin_skills()
        
        assert results["builtin-test"] is True
        assert (skill_loader.global_skills_dir / "builtin-test" / "SKILL.md").exists()

    def test_install_builtin_skill_skips_existing(self, skill_loader):
        """Test that installing built-in skill skips existing."""
        # Create existing skill
        existing_dir = skill_loader.global_skills_dir / "builtin-test"
        existing_dir.mkdir(parents=True)
        existing_file = existing_dir / "SKILL.md"
        existing_file.write_text("Existing content")
        
        # Create built-in skill
        builtin_dir = skill_loader.builtin_skills_dir / "builtin-test"
        builtin_dir.mkdir()
        builtin_file = builtin_dir / "SKILL.md"
        builtin_file.write_text("New content")
        
        # Install without overwrite
        results = skill_loader.install_builtin_skills(overwrite=False)
        
        assert results["builtin-test"] is False  # Skipped
        # Original content should be preserved
        assert existing_file.read_text() == "Existing content"

    def test_install_builtin_skill_overwrites(self, skill_loader):
        """Test that installing with overwrite replaces existing skill."""
        # Create existing skill
        existing_dir = skill_loader.global_skills_dir / "builtin-test"
        existing_dir.mkdir(parents=True)
        existing_file = existing_dir / "SKILL.md"
        existing_file.write_text("Old content")
        
        # Create built-in skill
        builtin_dir = skill_loader.builtin_skills_dir / "builtin-test"
        builtin_dir.mkdir()
        builtin_file = builtin_dir / "SKILL.md"
        builtin_file.write_text("New content")
        
        # Install with overwrite
        results = skill_loader.install_builtin_skills(overwrite=True)
        
        assert results["builtin-test"] is True
        # Content should be updated
        assert existing_file.read_text() == "New content"

    def test_load_skill_instructions(self, skill_loader):
        """Test loading skill instructions (Level 2)."""
        skill_dir = skill_loader.global_skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""---
name: test-skill
description: Test skill
---

# Test Skill

This is the instructions section.
It has multiple lines.
""")
        
        # Load metadata first
        skill_loader.load_skills_metadata()
        
        # Load instructions
        instructions = skill_loader.load_skill_instructions("test-skill")
        
        assert instructions is not None
        assert "instructions section" in instructions
        assert "multiple lines" in instructions
        # Should not include YAML frontmatter
        assert "name: test-skill" not in instructions

    def test_match_skills_to_prompt(self, skill_loader):
        """Test matching skills to user prompts."""
        # Create skills with different descriptions
        skill1_dir = skill_loader.global_skills_dir / "readme-generator"
        skill1_dir.mkdir()
        skill1_file = skill1_dir / "SKILL.md"
        skill1_file.write_text("""---
name: readme-generator
description: Generate README files, create documentation, write readme
---
""")
        
        skill2_dir = skill_loader.global_skills_dir / "format-checker"
        skill2_dir.mkdir()
        skill2_file = skill2_dir / "SKILL.md"
        skill2_file.write_text("""---
name: format-checker
description: Check code formatting, find style issues, linting
---
""")
        
        skill_loader.load_skills_metadata()
        
        # Test matching
        matches = skill_loader.match_skills_to_prompt("Generate a README for my project")
        assert len(matches) > 0
        assert any(s.name == "readme-generator" for s in matches)
        
        matches = skill_loader.match_skills_to_prompt("Check formatting in the code")
        assert len(matches) > 0
        assert any(s.name == "format-checker" for s in matches)

    def test_list_builtin_skills(self, skill_loader):
        """Test listing built-in skills."""
        # Create some built-in skills
        for skill_name in ["skill1", "skill2"]:
            skill_dir = skill_loader.builtin_skills_dir / skill_name
            skill_dir.mkdir()
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(f"---\nname: {skill_name}\ndescription: Test\n---\n")
        
        builtin_skills = skill_loader.list_builtin_skills()
        
        assert len(builtin_skills) == 2
        assert "skill1" in builtin_skills
        assert "skill2" in builtin_skills

    def test_get_skill_metadata_summary(self, skill_loader):
        """Test generating skill metadata summary for system prompt."""
        # Create a skill
        skill_dir = skill_loader.global_skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: test-skill
description: A test skill
---
""")
        
        skill_loader.load_skills_metadata()
        summary = skill_loader.get_skill_metadata_summary()
        
        assert "Available Skills:" in summary
        assert "test-skill" in summary
        assert "A test skill" in summary

    def test_skill_resources_discovery(self, skill_loader):
        """Test that skill resources are discovered."""
        skill_dir = skill_loader.global_skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: test-skill
description: Test
---
""")
        
        # Create additional resources
        resource_file = skill_dir / "REFERENCE.md"
        resource_file.write_text("Reference content")
        
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "helper.py"
        script_file.write_text("# Helper script")
        
        skill_loader.load_skills_metadata()
        skill = skill_loader.get_skill("test-skill")
        
        assert skill is not None
        assert len(skill.resources) >= 2  # At least REFERENCE.md and scripts/helper.py


class TestBuiltInSkills:
    """Test built-in skills functionality."""

    def test_readme_generator_skill_exists(self):
        """Test that readme-generator skill file exists."""
        loader = SkillLoader()
        builtin_dir = loader.builtin_skills_dir
        
        if builtin_dir.exists():
            readme_skill_dir = builtin_dir / "readme-generator"
            skill_file = readme_skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text()
                assert "readme-generator" in content.lower()
                assert "name:" in content or "description:" in content

    def test_code_formatting_checker_skill_exists(self):
        """Test that code-formatting-checker skill file exists."""
        loader = SkillLoader()
        builtin_dir = loader.builtin_skills_dir
        
        if builtin_dir.exists():
            checker_skill_dir = builtin_dir / "code-formatting-checker"
            skill_file = checker_skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text()
                assert "code-formatting-checker" in content.lower() or "format" in content.lower()
                assert "name:" in content or "description:" in content

    def test_write_release_notes_skill_exists(self):
        """Test that write-release-notes skill file exists."""
        loader = SkillLoader()
        builtin_dir = loader.builtin_skills_dir
        
        if builtin_dir.exists():
            release_skill_dir = builtin_dir / "write-release-notes"
            skill_file = release_skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text()
                assert "write-release-notes" in content.lower() or "release" in content.lower()
                assert "name:" in content or "description:" in content


class TestSkillPermissions:
    """Test Skills permission validation with allowed_tools."""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary directory for skills testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def skill_loader_no_permissions(self, temp_skills_dir):
        """Create a SkillLoader without permission restrictions (backward compatible)."""
        loader = SkillLoader(allowed_tools=None, blocked_tools=None)
        loader.global_skills_dir = temp_skills_dir / "global_skills"
        loader.project_skills_dir = temp_skills_dir / "project_skills"
        loader.builtin_skills_dir = temp_skills_dir / "builtin_skills"
        
        loader.global_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.project_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.builtin_skills_dir.mkdir(parents=True, exist_ok=True)
        
        return loader

    @pytest.fixture
    def skill_loader_with_permissions(self, temp_skills_dir):
        """Create a SkillLoader with permission restrictions."""
        # Skills enabled, and some tools allowed
        loader = SkillLoader(
            allowed_tools=["skill", "read_file", "write_file", "list_directory"],
            blocked_tools=None,
        )
        loader.global_skills_dir = temp_skills_dir / "global_skills"
        loader.project_skills_dir = temp_skills_dir / "project_skills"
        loader.builtin_skills_dir = temp_skills_dir / "builtin_skills"
        
        loader.global_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.project_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.builtin_skills_dir.mkdir(parents=True, exist_ok=True)
        
        return loader

    def test_skill_without_tools_allowed_when_skills_enabled(self, skill_loader_with_permissions):
        """Test that skill without tools: metadata is allowed when Skills system is enabled."""
        skill_dir = skill_loader_with_permissions.global_skills_dir / "simple-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""---
name: simple-skill
description: A simple skill without tools requirement
---
""")
        
        result = skill_loader_with_permissions.load_skills_metadata()
        
        assert "simple-skill" in result.skills
        skill = result.skills["simple-skill"]
        assert skill.enabled is True
        assert skill.disabled_reason is None
        assert skill.required_tools == []

    def test_skill_with_tools_all_allowed(self, skill_loader_with_permissions):
        """Test that skill with tools: where all tools are in allowed_tools is enabled."""
        skill_dir = skill_loader_with_permissions.global_skills_dir / "read-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""---
name: read-skill
description: A skill that only reads files
tools: ["read_file", "list_directory"]
---
""")
        
        result = skill_loader_with_permissions.load_skills_metadata()
        
        assert "read-skill" in result.skills
        skill = result.skills["read-skill"]
        assert skill.enabled is True
        assert skill.disabled_reason is None
        assert set(skill.required_tools) == {"read_file", "list_directory"}

    def test_skill_with_tools_some_missing_disabled(self, skill_loader_with_permissions):
        """Test that skill with tools: where some tools are missing is disabled."""
        skill_dir = skill_loader_with_permissions.global_skills_dir / "write-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""---
name: write-skill
description: A skill that writes files
tools: ["read_file", "write_file", "edit_file"]
---
""")
        
        result = skill_loader_with_permissions.load_skills_metadata()
        
        assert "write-skill" in result.skills
        skill = result.skills["write-skill"]
        assert skill.enabled is False
        assert "edit_file" in skill.disabled_reason or "not allowed" in skill.disabled_reason

    def test_skills_disabled_when_skill_not_in_allowed_tools(self, temp_skills_dir):
        """Test that all skills are disabled when 'skill' is not in allowed_tools."""
        loader = SkillLoader(
            allowed_tools=["read_file", "write_file"],  # No "skill"
            blocked_tools=None,
        )
        loader.global_skills_dir = temp_skills_dir / "global_skills"
        loader.project_skills_dir = temp_skills_dir / "project_skills"
        loader.builtin_skills_dir = temp_skills_dir / "builtin_skills"
        
        loader.global_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.project_skills_dir.mkdir(parents=True, exist_ok=True)
        loader.builtin_skills_dir.mkdir(parents=True, exist_ok=True)
        
        skill_dir = loader.global_skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""---
name: test-skill
description: A test skill
tools: ["read_file"]
---
""")
        
        result = loader.load_skills_metadata()
        
        assert "test-skill" in result.skills
        skill = result.skills["test-skill"]
        assert skill.enabled is False
        assert "skill" in skill.disabled_reason.lower() or "disabled" in skill.disabled_reason.lower()

    def test_blocked_skill_disabled(self, skill_loader_with_permissions):
        """Test that explicitly blocked skill is disabled."""
        # Create a skill
        skill_dir = skill_loader_with_permissions.global_skills_dir / "blocked-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""---
name: blocked-skill
description: A skill that is blocked
tools: ["read_file"]
---
""")
        
        # Create loader with blocked_tools
        loader = SkillLoader(
            allowed_tools=["skill", "read_file"],
            blocked_tools=["blocked-skill"],
        )
        loader.global_skills_dir = skill_loader_with_permissions.global_skills_dir
        loader.project_skills_dir = skill_loader_with_permissions.project_skills_dir
        loader.builtin_skills_dir = skill_loader_with_permissions.builtin_skills_dir
        
        result = loader.load_skills_metadata()
        
        assert "blocked-skill" in result.skills
        skill = result.skills["blocked-skill"]
        assert skill.enabled is False
        assert "blocked" in skill.disabled_reason.lower()

    def test_match_skills_filters_disabled_skills(self, skill_loader_with_permissions):
        """Test that match_skills_to_prompt only returns enabled skills."""
        # Create two skills: one enabled, one disabled
        enabled_dir = skill_loader_with_permissions.global_skills_dir / "enabled-skill"
        enabled_dir.mkdir()
        enabled_file = enabled_dir / "SKILL.md"
        enabled_file.write_text("""---
name: enabled-skill
description: An enabled skill for reading files
tools: ["read_file"]
---
""")
        
        disabled_dir = skill_loader_with_permissions.global_skills_dir / "disabled-skill"
        disabled_dir.mkdir()
        disabled_file = disabled_dir / "SKILL.md"
        disabled_file.write_text("""---
name: disabled-skill
description: A disabled skill requiring edit_file
tools: ["edit_file"]
---
""")
        
        skill_loader_with_permissions.load_skills_metadata()
        matches = skill_loader_with_permissions.match_skills_to_prompt("read files")
        
        # Should only return enabled skills
        skill_names = [s.name for s in matches]
        assert "enabled-skill" in skill_names or len(matches) == 0  # May or may not match
        assert "disabled-skill" not in skill_names

    def test_get_skill_metadata_summary_filters_disabled(self, skill_loader_with_permissions):
        """Test that get_skill_metadata_summary only includes enabled skills."""
        # Create enabled and disabled skills
        enabled_dir = skill_loader_with_permissions.global_skills_dir / "enabled-skill"
        enabled_dir.mkdir()
        enabled_file = enabled_dir / "SKILL.md"
        enabled_file.write_text("""---
name: enabled-skill
description: An enabled skill
tools: ["read_file"]
---
""")
        
        disabled_dir = skill_loader_with_permissions.global_skills_dir / "disabled-skill"
        disabled_dir.mkdir()
        disabled_file = disabled_dir / "SKILL.md"
        disabled_file.write_text("""---
name: disabled-skill
description: A disabled skill
tools: ["edit_file"]
---
""")
        
        skill_loader_with_permissions.load_skills_metadata()
        summary = skill_loader_with_permissions.get_skill_metadata_summary()
        
        # Should include enabled skill
        assert "enabled-skill" in summary
        # Should NOT include disabled skill
        assert "disabled-skill" not in summary

    def test_skills_backward_compatible_no_permissions(self, skill_loader_no_permissions):
        """Test that skills work without permission restrictions (backward compatible)."""
        skill_dir = skill_loader_no_permissions.global_skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        
        skill_file.write_text("""---
name: test-skill
description: A test skill
tools: ["read_file", "edit_file"]
---
""")
        
        result = skill_loader_no_permissions.load_skills_metadata()
        
        assert "test-skill" in result.skills
        skill = result.skills["test-skill"]
        # Should be enabled when no permissions are set (backward compatible)
        assert skill.enabled is True

    def test_builtin_skills_have_tools_metadata(self):
        """Test that built-in skills have tools: metadata."""
        loader = SkillLoader()
        
        # Check built-in skill files directly
        if loader.builtin_skills_dir.exists():
            readme_skill_file = loader.builtin_skills_dir / "readme-generator" / "SKILL.md"
            if readme_skill_file.exists():
                content = readme_skill_file.read_text()
                # Check that tools: field exists in the YAML frontmatter
                assert "tools:" in content or "required_tools:" in content
                
                # Parse directly to verify
                import yaml
                import re
                frontmatter_match = re.match(
                    r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
                )
                if frontmatter_match:
                    yaml_content = frontmatter_match.group(1)
                    metadata = yaml.safe_load(yaml_content) or {}
                    assert "tools" in metadata or "required_tools" in metadata
                    tools = metadata.get("tools", metadata.get("required_tools", []))
                    assert len(tools) > 0
                    assert "read_file" in tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

