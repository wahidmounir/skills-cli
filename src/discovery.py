"""Discovery of skill roots and SKILL.md files across Antigravity, Claude, and Codex."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SkillScope = Literal["workspace", "plugin", "global", "library", "builtin", "custom"]


@dataclass
class DiscoveredSkillRef:
    name: str
    path: Path
    scope: SkillScope
    plugin_name: str | None = None
    priority: int = 0  # higher number = higher priority


def get_default_roots(workspace_dir: Path | None = None) -> list[tuple[Path, SkillScope, int]]:
    """Return all standard discovery roots with their scopes and precedence."""
    home = Path.home()
    roots: list[tuple[Path, SkillScope, int]] = []

    # Priority 1: Workspace project (highest)
    ws = (workspace_dir or Path.cwd()).resolve()
    current = ws
    while True:
        # Check standard workspace subdirs
        ws_candidates = [
            (current / ".agents" / "skills", 100),
            (current / ".gemini" / "skills", 95),
            (current / ".claude" / "skills", 90),
            (current / "skills", 85),
        ]
        for candidate, prio in ws_candidates:
            if candidate.is_dir():
                roots.append((candidate, "workspace", prio))

        parent = current.parent
        if parent == current:
            break
        # Stop at git root or filesystem root
        if (current / ".git").exists():
            break
        current = parent

    # Priority 2: Custom SKILLS_PATH environment variable
    custom_env = os.environ.get("SKILLS_PATH")
    if custom_env:
        for p in custom_env.split(":"):
            if p.strip() and Path(p.strip()).is_dir():
                roots.append((Path(p.strip()), "custom", 80))

    # Priority 3: Antigravity Plugins
    plugins_dir = home / ".gemini" / "config" / "plugins"
    if plugins_dir.is_dir():
        for plugin_folder in plugins_dir.iterdir():
            if plugin_folder.is_dir():
                plugin_skills = plugin_folder / "skills"
                if plugin_skills.is_dir():
                    roots.append((plugin_skills, "plugin", 70))

    # Priority 4: User Global Configurations (Tier A - active in prompt)
    roots.append((home / ".gemini" / "config" / "skills", "global", 65))
    roots.append((home / ".agents" / "skills", "global", 60))
    roots.append((home / ".claude" / "skills", "global", 55))

    # Priority 5: On-Demand Skills Library (Tier B - outside prompt auto-discovery)
    roots.append((home / ".config" / "skills", "library", 50))

    # Priority 6: Builtin Antigravity Skills
    roots.append((home / ".gemini" / "antigravity" / "builtin" / "skills", "builtin", 40))

    return roots


def scan_skills(workspace_dir: Path | None = None) -> list[DiscoveredSkillRef]:
    """Scan all roots and return discovered skills deduplicated by name."""
    roots = get_default_roots(workspace_dir)
    discovered: dict[str, DiscoveredSkillRef] = {}
    seen_paths: set[Path] = set()

    for root_dir, scope, prio in roots:
        if not root_dir.exists():
            continue

        # Look for SKILL.md in direct subdirectories: root/<skill_name>/SKILL.md
        # and also recursively
        for skill_file in root_dir.glob("**/SKILL.md"):
            resolved = skill_file.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)

            # Skill name derived from folder name by default
            skill_name = skill_file.parent.name
            plugin_name = None
            if scope == "plugin":
                # Path: .../plugins/<plugin_name>/skills/<skill_name>/SKILL.md
                try:
                    rel = skill_file.relative_to(Path.home() / ".gemini" / "config" / "plugins")
                    plugin_name = rel.parts[0]
                except ValueError:
                    plugin_name = None

            ref = DiscoveredSkillRef(
                name=skill_name,
                path=resolved,
                scope=scope,
                plugin_name=plugin_name,
                priority=prio,
            )

            # Deduplication: higher priority wins
            if skill_name not in discovered or prio > discovered[skill_name].priority:
                discovered[skill_name] = ref

    return sorted(discovered.values(), key=lambda r: (r.name, -r.priority))
