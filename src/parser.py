"""Parser for SKILL.md frontmatter, markdown sections, and structure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


@dataclass
class Section:
    title: str
    level: int
    start_line: int
    end_line: int
    content: str = ""


@dataclass
class SkillMeta:
    name: str
    description: str = ""
    version: str = ""
    license: str = ""
    allowed_tools: str = ""
    user_invocable: bool = True
    compatibility: str = ""
    tags: list[str] = field(default_factory=list)
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedSkill:
    path: Path
    meta: SkillMeta
    sections: list[Section]
    full_text: str
    word_count: int
    token_estimate: int
    mtime: float


def estimate_tokens(text: str) -> int:
    """Fast, accurate token estimation (~1.33 tokens per word or ~4 chars/token)."""
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    # Average of word-based and char-based heuristics
    return max(1, int((words * 1.33 + chars / 4.0) / 2.0))


def _parse_yaml_minimal(raw: str) -> dict[str, Any]:
    """Lightweight zero-dependency YAML parser for standard frontmatter."""
    result: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or line.startswith("#"):
            i += 1
            continue

        # Match key: value
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue

        key, val = m.group(1), m.group(2).strip()

        # Folded or literal multiline block (> or |)
        if val in (">", ">-", "|", "|-"):
            block_lines = []
            i += 1
            indent = None
            while i < len(lines):
                subline = lines[i]
                if not subline.strip():
                    block_lines.append("")
                    i += 1
                    continue
                current_indent = len(subline) - len(subline.lstrip())
                if indent is None:
                    if current_indent == 0:
                        break
                    indent = current_indent
                elif current_indent < indent:
                    break
                block_lines.append(subline[indent:])
                i += 1
            join_char = " " if val.startswith(">") else "\n"
            result[key] = join_char.join(l.strip() if val.startswith(">") else l for l in block_lines).strip()
            continue

        # Inline list [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            items = [item.strip().strip("'\"") for item in val[1:-1].split(",") if item.strip()]
            result[key] = items
            i += 1
            continue

        # Multiline list (- item)
        if not val and (i + 1 < len(lines)) and re.match(r"^\s*-\s+", lines[i + 1]):
            items = []
            i += 1
            while i < len(lines) and re.match(r"^\s*-\s+(.*)$", lines[i]):
                item_val = re.match(r"^\s*-\s+(.*)$", lines[i]).group(1).strip().strip("'\"")
                items.append(item_val)
                i += 1
            result[key] = items
            continue

        # Primitive values
        val_lower = val.lower()
        if val_lower == "true":
            result[key] = True
        elif val_lower == "false":
            result[key] = False
        elif val.isdigit():
            result[key] = int(val)
        else:
            # Strip outer quotes if present
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            result[key] = val

        i += 1

    return result


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract frontmatter and remaining body."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not m:
        return {}, content

    header_raw, body = m.group(1), m.group(2)
    if HAVE_YAML:
        try:
            data = yaml.safe_load(header_raw)
            if isinstance(data, dict):
                return data, body
        except Exception:
            pass

    # Fallback to zero-dependency minimal parser
    return _parse_yaml_minimal(header_raw), body


def parse_sections(text: str) -> list[Section]:
    """Parse markdown headings into structured Section objects with absolute line numbers."""
    lines = text.splitlines()
    sections: list[Section] = []
    in_frontmatter = False
    in_code_block = False
    fm_delimiters = 0

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped == "---":
            fm_delimiters += 1
            in_frontmatter = (fm_delimiters < 2)
            continue
        if in_frontmatter:
            continue

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            sections.append(
                Section(
                    title=heading_match.group(2).strip(),
                    level=len(heading_match.group(1)),
                    start_line=idx,
                    end_line=idx,
                )
            )

    return sections


def parse_skill_file(path: Path) -> ParsedSkill:
    """Parse a SKILL.md file completely into structured format."""
    text = path.read_text(encoding="utf-8", errors="replace")
    mtime = path.stat().st_mtime
    frontmatter, body = parse_frontmatter(text)

    # Derive name if missing
    name = str(frontmatter.get("name", "")).strip()
    if not name:
        name = path.parent.name

    desc = str(frontmatter.get("description", "")).strip()
    if not desc and body:
        # Fallback to first non-empty paragraph
        for p in body.split("\n\n"):
            clean = p.strip().lstrip("#").strip()
            if clean:
                desc = clean[:200]
                break

    # Extract tags from frontmatter or infer from description
    tags: list[str] = []
    raw_tags = frontmatter.get("tags")
    if isinstance(raw_tags, list):
        tags.extend(str(t) for t in raw_tags)
    elif isinstance(raw_tags, str):
        tags.extend(t.strip() for t in raw_tags.split(",") if t.strip())

    sections = parse_sections(text)
    word_count = len(text.split())
    token_est = estimate_tokens(text)

    metadata_obj = frontmatter.get("metadata")
    version_val = frontmatter.get("version")
    if not version_val and isinstance(metadata_obj, dict):
        version_val = metadata_obj.get("version")

    meta = SkillMeta(
        name=name,
        description=desc,
        version=str(version_val or ""),
        license=str(frontmatter.get("license") or ""),
        allowed_tools=str(frontmatter.get("allowed-tools") or ""),
        user_invocable=bool(frontmatter.get("user-invocable", True)),
        compatibility=str(frontmatter.get("compatibility") or ""),
        tags=sorted(list(set(tags))),
        raw_frontmatter=frontmatter if isinstance(frontmatter, dict) else {},
    )

    return ParsedSkill(
        path=path.resolve(),
        meta=meta,
        sections=sections,
        full_text=text,
        word_count=word_count,
        token_estimate=token_est,
        mtime=mtime,
    )


def extract_section(parsed: ParsedSkill, query: str) -> Section | None:
    """Extract a specific section by name, including its child subsections."""
    q_clean = query.strip().lower()
    target_sec = None
    for sec in parsed.sections:
        if sec.title.lower() == q_clean:
            target_sec = sec
            break
    if not target_sec:
        for sec in parsed.sections:
            if q_clean in sec.title.lower():
                target_sec = sec
                break
    if not target_sec:
        return None

    if parsed.full_text:
        lines = parsed.full_text.splitlines()
        start_idx = max(0, target_sec.start_line - 1)
        end_idx = len(lines)
        for other in parsed.sections:
            if other.start_line > target_sec.start_line and other.level <= target_sec.level:
                end_idx = other.start_line - 1
                break
        content = "\n".join(lines[start_idx:end_idx]).strip()
        return Section(
            title=target_sec.title,
            level=target_sec.level,
            start_line=target_sec.start_line,
            end_line=end_idx,
            content=content,
        )

    return target_sec
