"""Persistent JSON cache for instant mtime-validated skill indexing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .discovery import scan_skills
from .parser import ParsedSkill, SkillMeta, Section, parse_skill_file

CACHE_VERSION = 1


def get_cache_dir() -> Path:
    """Return user cache directory (~/.cache/skills-cli)."""
    p = Path.home() / ".cache" / "skills-cli"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_cache_file() -> Path:
    return get_cache_dir() / "index.json"


def serialize_skill(skill: ParsedSkill) -> dict[str, Any]:
    """Convert ParsedSkill to JSON-serializable dict."""
    return {
        "path": str(skill.path),
        "mtime": skill.mtime,
        "word_count": skill.word_count,
        "token_estimate": skill.token_estimate,
        "meta": {
            "name": skill.meta.name,
            "description": skill.meta.description,
            "version": skill.meta.version,
            "license": skill.meta.license,
            "allowed_tools": skill.meta.allowed_tools,
            "user_invocable": skill.meta.user_invocable,
            "compatibility": skill.meta.compatibility,
            "tags": skill.meta.tags,
            "raw_frontmatter": skill.meta.raw_frontmatter,
        },
        "sections": [
            {
                "title": s.title,
                "level": s.level,
                "start_line": s.start_line,
                "end_line": s.end_line,
            }
            for s in skill.sections
        ],
    }


def deserialize_skill(data: dict[str, Any]) -> ParsedSkill:
    """Reconstruct ParsedSkill from cached dict (body read lazily on load)."""
    p = Path(data["path"])
    meta_dict = data["meta"]
    meta = SkillMeta(
        name=meta_dict["name"],
        description=meta_dict.get("description", ""),
        version=meta_dict.get("version", ""),
        license=meta_dict.get("license", ""),
        allowed_tools=meta_dict.get("allowed_tools", ""),
        user_invocable=meta_dict.get("user_invocable", True),
        compatibility=meta_dict.get("compatibility", ""),
        tags=meta_dict.get("tags", []),
        raw_frontmatter=meta_dict.get("raw_frontmatter", {}),
    )
    sections = [
        Section(
            title=s["title"],
            level=s["level"],
            start_line=s["start_line"],
            end_line=s["end_line"],
        )
        for s in data["sections"]
    ]
    return ParsedSkill(
        path=p,
        meta=meta,
        sections=sections,
        full_text="",  # Lazy loaded if needed
        word_count=data["word_count"],
        token_estimate=data["token_estimate"],
        mtime=data["mtime"],
    )


def load_cached_skills(workspace_dir: Path | None = None, force_reindex: bool = False) -> list[ParsedSkill]:
    """Load skills using cached index when valid, incrementally updating changed files."""
    cache_path = get_cache_file()
    cached_entries: dict[str, dict[str, Any]] = {}

    if not force_reindex and cache_path.exists():
        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            if raw.get("version") == CACHE_VERSION:
                cached_entries = raw.get("skills", {})
        except Exception:
            cached_entries = {}

    refs = scan_skills(workspace_dir)
    skills: list[ParsedSkill] = []
    dirty = False
    current_paths: set[str] = set()

    for ref in refs:
        path_str = str(ref.path)
        current_paths.add(path_str)
        try:
            curr_mtime = ref.path.stat().st_mtime
        except OSError:
            continue

        cached = cached_entries.get(path_str)
        if cached and abs(cached.get("mtime", 0) - curr_mtime) < 1e-4:
            # Valid cache hit
            skill = deserialize_skill(cached)
            skills.append(skill)
        else:
            # Parse fresh
            dirty = True
            try:
                skill = parse_skill_file(ref.path)
                skills.append(skill)
                cached_entries[path_str] = serialize_skill(skill)
            except Exception:
                continue

    # Remove stale cache entries
    stale = [p for p in cached_entries if p not in current_paths]
    if stale:
        dirty = True
        for p in stale:
            del cached_entries[p]

    if dirty:
        try:
            payload = {
                "version": CACHE_VERSION,
                "timestamp": str(Path(cache_path).stat().st_mtime if cache_path.exists() else 0),
                "skills": cached_entries,
            }
            cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

    return skills
