"""
Skill Loader Module for Nano Agent.

This module manages loading and using Agent Skills - modular capabilities
that extend nano-agent functionality through filesystem-based skill directories.
Skills follow a progressive disclosure pattern:
- Level 1: Metadata (loaded at startup, ~100 tokens)
- Level 2: Instructions (loaded when triggered, ~5k tokens)
- Level 3: Resources (loaded as needed, effectively unlimited)
"""

import logging
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class Skill:
    """Represents a loaded skill with metadata and instructions."""

    name: str
    path: Path  # Path to skill directory
    skill_file: Path  # Path to SKILL.md file
    description: str
    instructions: Optional[str] = None  # SKILL.md content (Level 2, loaded when triggered)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "global"  # "global" or "project"
    resources: List[Path] = field(default_factory=list)  # Additional files in skill directory
    required_tools: List[str] = field(default_factory=list)  # Tools required by this skill (from tools: metadata)
    enabled: bool = True  # Whether skill is enabled based on permissions
    disabled_reason: Optional[str] = None  # Reason if skill is disabled

    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure name is valid (lowercase, hyphens only)
        self.name = self.name.lower().replace("_", "-")

        # Validate name constraints (max 64 chars, no XML tags, no reserved words)
        if len(self.name) > 64:
            logger.warning(f"Skill name '{self.name}' exceeds 64 characters, truncating")
            self.name = self.name[:64]

        if any(reserved in self.name.lower() for reserved in ["anthropic", "claude"]):
            logger.warning(f"Skill name '{self.name}' contains reserved words, skipping")
            self.name = ""

        # Ensure description is valid
        if not self.description:
            self.description = f"Skill: {self.name}"

        if len(self.description) > 1024:
            logger.warning(f"Skill description exceeds 1024 characters, truncating")
            self.description = self.description[:1024]


@dataclass
class SkillLoadResult:
    """Result of skill loading operations."""

    skills: Dict[str, Skill] = field(default_factory=dict)
    global_skills_loaded: int = 0
    project_skills_loaded: int = 0
    overridden_skills: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SkillLoader:
    """
    Manages loading and using Agent Skills with progressive disclosure.

    Skills are loaded from:
    - Global: ~/.askgpt/skills/
    - Project: .askgpt/skills/ (overrides global)

    Progressive disclosure:
    - Level 1 (always): Metadata (name, description from YAML frontmatter)
    - Level 2 (when triggered): SKILL.md instructions
    - Level 3 (as needed): Additional resources (scripts, docs, etc.)
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        allowed_tools: Optional[List[str]] = None,
        blocked_tools: Optional[List[str]] = None,
    ):
        """
        Initialize the skill loader.

        Args:
            working_dir: Working directory for project skills (defaults to current dir)
            allowed_tools: Optional list of allowed tools. Skills system enabled if "skill" is in this list.
            blocked_tools: Optional list of blocked tools or skill names.
        """
        self.working_dir = working_dir or Path.cwd()
        self.global_skills_dir = Path.home() / ".askgpt" / "skills"
        self.project_skills_dir = self.working_dir / ".askgpt" / "skills"

        # Permission configuration
        self.allowed_tools = allowed_tools
        self.blocked_tools = blocked_tools

        # Cache for skill metadata (Level 1 - always loaded)
        self._skills_metadata_cache: Dict[str, Skill] = {}
        # Cache for skill instructions (Level 2 - loaded when triggered)
        self._skills_instructions_cache: Dict[str, str] = {}
        # Cache validity flag
        self._cache_valid = False

        # Get built-in skills directory from package
        # Try multiple strategies to find the builtin_skills directory
        current_file = Path(__file__)
        # Strategy 1: Relative to this file (development)
        self.builtin_skills_dir = current_file.parent.parent / "data" / "builtin_skills"
        
        if not self.builtin_skills_dir.exists():
            # Strategy 2: Try via import (installed package)
            try:
                import importlib.resources as pkg_resources
                try:
                    # Python 3.9+
                    with pkg_resources.path("askgpt.data.builtin_skills", "") as path:
                        self.builtin_skills_dir = Path(path)
                except (ImportError, TypeError, AttributeError):
                    # Fallback: try direct import
                    try:
                        from askgpt.data import builtin_skills
                        if hasattr(builtin_skills, "__file__") and builtin_skills.__file__:
                            self.builtin_skills_dir = Path(builtin_skills.__file__).parent
                    except (ImportError, AttributeError):
                        pass
            except ImportError:
                pass
        
        if not self.builtin_skills_dir.exists():
            # Strategy 3: Alternative relative path
            self.builtin_skills_dir = current_file.parent.parent.parent / "data" / "builtin_skills"

        # Ensure global skills directory exists and install built-in skills
        self._ensure_global_skills_dir()
        self.install_builtin_skills()

    def load_skills_metadata(self) -> SkillLoadResult:
        """
        Load skill metadata (Level 1 - progressive disclosure).

        This loads only the YAML frontmatter (name, description) from all skills.
        The actual SKILL.md content is loaded on-demand when a skill is triggered.

        Returns:
            SkillLoadResult with all loaded skill metadata
        """
        result = SkillLoadResult()

        # Load global skills first
        global_skills = self._load_skills_metadata_from_directory(
            self.global_skills_dir, source="global"
        )
        result.global_skills_loaded = len(global_skills)

        # Load project skills
        project_skills = self._load_skills_metadata_from_directory(
            self.project_skills_dir, source="project"
        )
        result.project_skills_loaded = len(project_skills)

        # Merge with project skills overriding global ones
        result.skills = global_skills.copy()

        for name, project_skill in project_skills.items():
            if name in result.skills:
                result.overridden_skills.append(name)
                logger.debug(f"Project skill '{name}' overrides global skill")
            result.skills[name] = project_skill

        # Update cache
        self._skills_metadata_cache = result.skills
        self._cache_valid = True

        # Log summary
        total_skills = len(result.skills)
        logger.info(
            f"Loaded {total_skills} skill metadata entries "
            f"({result.global_skills_loaded} global, "
            f"{result.project_skills_loaded} project, "
            f"{len(result.overridden_skills)} overridden)"
        )

        return result

    def _load_skills_metadata_from_directory(
        self, directory: Path, source: str
    ) -> Dict[str, Skill]:
        """
        Load skill metadata from a specific directory.

        Args:
            directory: Directory containing skill subdirectories
            source: Source identifier ("global" or "project")

        Returns:
            Dictionary of skill name -> Skill object (metadata only)
        """
        skills = {}

        if not directory.exists():
            logger.debug(f"Skills directory not found: {directory}")
            return skills

        # Ensure directory exists
        directory.mkdir(parents=True, exist_ok=True)

        # Find all skill directories (subdirectories containing SKILL.md)
        for skill_dir in directory.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                logger.debug(f"Skipping {skill_dir}: no SKILL.md found")
                continue

            try:
                skill_name = skill_dir.name
                skill = self._parse_skill_metadata(skill_name, skill_dir, skill_file, source)
                if skill and skill.name:  # Only add if name is valid
                    skills[skill.name] = skill
                    logger.debug(f"Loaded {source} skill metadata: {skill.name}")
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_dir}: {e}")

        return skills

    def _parse_skill_metadata(
        self, name: str, skill_dir: Path, skill_file: Path, source: str
    ) -> Optional[Skill]:
        """
        Parse skill metadata (YAML frontmatter) from SKILL.md.

        This is Level 1 loading - only metadata, not the full instructions.

        Args:
            name: Skill directory name
            skill_dir: Path to skill directory
            skill_file: Path to SKILL.md file
            source: Source identifier ("global" or "project")

        Returns:
            Skill object with metadata only, or None if parsing failed
        """
        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read skill file {skill_file}: {e}")
            return None

        # Parse YAML frontmatter
        metadata = {}
        instructions = None  # Level 2 - not loaded yet

        # Pattern to detect YAML frontmatter: ---\n...\n---\n
        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
        )

        if frontmatter_match:
            # Parse YAML frontmatter
            yaml_content = frontmatter_match.group(1)
            # Store instructions content for later (Level 2 loading)
            instructions_raw = frontmatter_match.group(2)

            try:
                metadata = yaml.safe_load(yaml_content) or {}
            except yaml.YAMLError as e:
                logger.warning(f"Error parsing YAML frontmatter in {skill_file}: {e}")
                metadata = {}
        else:
            # No frontmatter found - use defaults
            logger.warning(
                f"Skill {skill_file} has no YAML frontmatter, using defaults"
            )
            instructions_raw = content

        # Extract required fields from metadata
        skill_name = metadata.get("name", name.lower().replace("_", "-"))
        description = metadata.get("description", "")
        if not description:
            # Try to extract from first line or heading
            if instructions_raw:
                first_line = instructions_raw.strip().split("\n")[0]
                if first_line.startswith("# "):
                    description = first_line[2:].strip()
                else:
                    description = first_line[:100]  # Limit description length

        # Validate required fields
        if not skill_name:
            logger.error(f"Skill {skill_file} has no name")
            return None

        if not description:
            description = f"Skill: {skill_name}"

        # Extract required tools from metadata
        # Support both "tools:" and "required_tools:" for flexibility
        required_tools = []
        if "tools" in metadata:
            tools_value = metadata.get("tools", [])
            if isinstance(tools_value, list):
                required_tools = [str(t).strip() for t in tools_value if t]
            elif isinstance(tools_value, str):
                # Handle comma-separated string
                required_tools = [t.strip() for t in tools_value.split(",") if t.strip()]
        elif "required_tools" in metadata:
            tools_value = metadata.get("required_tools", [])
            if isinstance(tools_value, list):
                required_tools = [str(t).strip() for t in tools_value if t]
            elif isinstance(tools_value, str):
                required_tools = [t.strip() for t in tools_value.split(",") if t.strip()]

        # Discover resources (Level 3 - for on-demand loading)
        resources = []
        for item in skill_dir.iterdir():
            if item.is_file() and item.name != "SKILL.md":
                resources.append(item)
            elif item.is_dir():
                # Include directory and its contents
                for subitem in item.rglob("*"):
                    if subitem.is_file():
                        resources.append(subitem)

        # Add source information to metadata
        metadata["source"] = source
        metadata["file"] = str(skill_file)
        metadata["directory"] = str(skill_dir)

        # Create skill object
        skill = Skill(
            name=skill_name,
            path=skill_dir,
            skill_file=skill_file,
            description=description,
            instructions=None,  # Level 2 - loaded on demand
            metadata=metadata,
            source=source,
            resources=resources,
            required_tools=required_tools,
        )

        # Validate permissions and set enabled status
        enabled, disabled_reason = self._validate_skill_permissions(skill)
        skill.enabled = enabled
        skill.disabled_reason = disabled_reason

        return skill

    def _validate_skill_permissions(self, skill: Skill) -> Tuple[bool, Optional[str]]:
        """
        Validate if a skill can be enabled based on allowed_tools configuration.

        Logic:
        1. If allowed_tools is None: enable all skills (backward compatible)
        2. If allowed_tools is set but "skill" not in it: disable all skills
        3. If skill has no tools: metadata: always enable (when Skills system is on)
        4. If skill has tools: metadata: all tools must be in allowed_tools

        Returns:
            (enabled: bool, disabled_reason: Optional[str])
        """
        # No restrictions - backward compatible
        if self.allowed_tools is None:
            return True, None

        # Check if Skills system is enabled
        if "skill" not in [t.lower() for t in self.allowed_tools]:
            return False, 'Skills system disabled ("skill" not in allowed_tools)'

        # Check if skill is explicitly blocked
        if self.blocked_tools and skill.name in [t.lower() for t in self.blocked_tools]:
            return False, f"Skill '{skill.name}' is blocked"

        # If skill has no tools requirement, allow it
        if not skill.required_tools:
            return True, None

        # Validate all required tools are in allowed_tools
        missing_tools = [t for t in skill.required_tools if t not in self.allowed_tools]
        if missing_tools:
            return False, f"Required tools not allowed: {', '.join(missing_tools)}"

        return True, None

    def load_skill_instructions(self, skill_name: str) -> Optional[str]:
        """
        Load skill instructions (Level 2 - progressive disclosure).

        This loads the full SKILL.md content (excluding YAML frontmatter)
        when a skill is triggered.

        Args:
            skill_name: Name of the skill to load instructions for

        Returns:
            Skill instructions content, or None if skill not found or failed to load
        """
        # Check cache first
        if skill_name in self._skills_instructions_cache:
            return self._skills_instructions_cache[skill_name]

        # Get skill metadata to find the skill file
        skill = self.get_skill(skill_name)
        if not skill:
            logger.warning(f"Skill '{skill_name}' not found for instruction loading")
            return None

        try:
            content = skill.skill_file.read_text(encoding="utf-8")

            # Extract instructions (remove YAML frontmatter)
            frontmatter_match = re.match(
                r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
            )

            if frontmatter_match:
                instructions = frontmatter_match.group(2).strip()
            else:
                # No frontmatter, use entire content
                instructions = content.strip()

            # Cache the instructions
            self._skills_instructions_cache[skill_name] = instructions

            logger.debug(f"Loaded Level 2 instructions for skill: {skill_name}")
            return instructions

        except Exception as e:
            logger.error(f"Failed to load instructions for skill '{skill_name}': {e}")
            return None

    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """
        Get a skill by name (metadata only - Level 1).

        Args:
            skill_name: Name of the skill

        Returns:
            Skill object if found, None otherwise
        """
        # Load skills if cache is not valid
        if not self._cache_valid:
            self.load_skills_metadata()

        return self._skills_metadata_cache.get(skill_name)

    def list_skills(self) -> List[Skill]:
        """
        List all available skills (metadata only - Level 1).

        Returns:
            List of Skill objects sorted by name
        """
        # Load skills if cache is not valid
        if not self._cache_valid:
            self.load_skills_metadata()

        return sorted(self._skills_metadata_cache.values(), key=lambda s: s.name)

    def match_skills_to_prompt(self, prompt: str) -> List[Skill]:
        """
        Match user prompt to relevant skills using description keywords.

        This determines which skills should be triggered based on the user's request.

        Args:
            prompt: User prompt text

        Returns:
            List of matching skills, ordered by relevance
        """
        prompt_lower = prompt.lower()
        all_skills = self.list_skills()
        matches = []

        for skill in all_skills:
            # Simple keyword matching on description
            description_lower = skill.description.lower()

            # Count matches
            match_count = 0
            description_words = set(description_lower.split())
            prompt_words = set(prompt_lower.split())

            # Check for word overlaps
            common_words = description_words.intersection(prompt_words)
            if len(common_words) >= 2:  # Require at least 2 matching words
                match_count = len(common_words)

            # Also check if key phrases from description appear in prompt
            # Split description into key phrases (2-3 word combinations)
            description_phrases = []
            words = description_lower.split()
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                description_phrases.append(phrase)

            for phrase in description_phrases:
                if phrase in prompt_lower:
                    match_count += 2  # Phrase matches are weighted higher

            if match_count > 0:
                matches.append((match_count, skill))

        # Sort by match count (descending)
        matches.sort(key=lambda x: x[0], reverse=True)

        # Return just the enabled skills, ordered by relevance
        return [skill for _, skill in matches if skill.enabled]

    def get_skill_metadata_summary(self) -> str:
        """
        Get a formatted summary of all available enabled skills for system prompt.

        Returns:
            String with skill metadata formatted for system prompt inclusion
        """
        all_skills = self.list_skills()
        # Filter to only enabled skills
        skills = [s for s in all_skills if s.enabled]

        if not skills:
            return ""

        lines = ["Available Skills:"]
        for skill in skills:
            lines.append(f"- {skill.name}: {skill.description}")

        return "\n".join(lines)

    def refresh_cache(self):
        """Refresh the skills cache."""
        self._cache_valid = False
        self._skills_instructions_cache.clear()  # Clear Level 2 cache too
        self.load_skills_metadata()

    def _ensure_global_skills_dir(self):
        """Ensure the global skills directory exists."""
        self.global_skills_dir.mkdir(parents=True, exist_ok=True)

    def install_builtin_skills(
        self, overwrite: bool = False, skill_names: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Install built-in skills from package to user directory.

        Args:
            overwrite: If True, overwrite existing skills. If False, skip existing ones.
            skill_names: Optional list of specific skill names to install. If None, install all.

        Returns:
            Dictionary mapping skill name to installation success status
        """
        results = {}

        if not self.builtin_skills_dir.exists():
            logger.warning(
                f"Built-in skills directory not found: {self.builtin_skills_dir}"
            )
            return results

        # Find all skill directories in builtin_skills
        for skill_dir in self.builtin_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name
            skill_file = skill_dir / "SKILL.md"

            # Filter by skill_names if provided
            if skill_names and skill_name not in skill_names:
                continue

            if not skill_file.exists():
                logger.debug(f"Skipping {skill_dir}: no SKILL.md found")
                continue

            # Target location
            target_dir = self.global_skills_dir / skill_name
            target_file = target_dir / "SKILL.md"

            # Check if already exists
            if target_dir.exists() and not overwrite:
                results[skill_name] = False  # Skipped
                logger.debug(f"Skipping {skill_name}: already exists (use overwrite=True to replace)")
                continue

            try:
                # Create target directory
                target_dir.mkdir(parents=True, exist_ok=True)

                # Copy SKILL.md
                shutil.copy2(skill_file, target_file)
                logger.debug(f"Installed built-in skill: {skill_name}")

                # Copy any additional files in the skill directory
                for item in skill_dir.iterdir():
                    if item.is_file() and item.name != "SKILL.md":
                        target_item = target_dir / item.name
                        shutil.copy2(item, target_item)
                        logger.debug(f"Copied resource: {item.name}")

                # Also copy subdirectories (for scripts, resources, etc.)
                for item in skill_dir.iterdir():
                    if item.is_dir():
                        target_subdir = target_dir / item.name
                        shutil.copytree(
                            item, target_subdir, dirs_exist_ok=True
                        )
                        logger.debug(f"Copied subdirectory: {item.name}")

                results[skill_name] = True
                logger.info(f"Installed built-in skill: {skill_name}")

            except Exception as e:
                logger.error(f"Failed to install built-in skill '{skill_name}': {e}")
                results[skill_name] = False

        return results

    def list_builtin_skills(self) -> List[str]:
        """
        List available built-in skills in the package.

        Returns:
            List of built-in skill names
        """
        skills = []

        if not self.builtin_skills_dir.exists():
            return skills

        for skill_dir in self.builtin_skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append(skill_dir.name)

        return sorted(skills)


# Export main classes
__all__ = ["Skill", "SkillLoadResult", "SkillLoader"]

