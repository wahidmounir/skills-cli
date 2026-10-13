"""Main CLI implementation for skills-cli."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import NoReturn

from .cache import load_cached_skills, get_cache_file
from .matcher import SkillMatcher
from .parser import parse_skill_file, extract_section

VERSION = "1.0.0"


def format_tokens(n: int) -> str:
    """Format token count with clean human-readable units."""
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def cmd_list(skills: list, args: argparse.Namespace) -> int:
    """List skills concisely with token estimates."""
    if args.json:
        out = [
            {
                "name": s.meta.name,
                "description": s.meta.description,
                "tokens": s.token_estimate,
                "path": str(s.path),
                "tags": s.meta.tags,
            }
            for s in skills
        ]
        print(json.dumps(out, indent=2))
        return 0

    print(f"\nDiscovered {len(skills)} skills:")
    for s in sorted(skills, key=lambda x: x.meta.name):
        tok_str = f"~{format_tokens(s.token_estimate)} tok"
        tags_str = f"[{', '.join(s.meta.tags)}]" if s.meta.tags else ""
        print(f"  • {s.meta.name:<24} {tok_str:>9}   {tags_str}")
        if args.with_descriptions and s.meta.description:
            # Wrap description cleanly
            clean_desc = " ".join(s.meta.description.split())
            if len(clean_desc) > 90:
                clean_desc = clean_desc[:87] + "..."
            print(f"      {clean_desc}")

    print("\nTip: Use 'skills-cli info <skill>' or 'skills-cli match \"<task>\"'\n")
    return 0


def cmd_info(skills: list, args: argparse.Namespace) -> int:
    """Show detailed metadata and table of contents for a single skill."""
    target = args.skill.strip().lower()
    match = next((s for s in skills if s.meta.name.lower() == target), None)
    if not match:
        # Try substring
        matches = [s for s in skills if target in s.meta.name.lower()]
        if len(matches) == 1:
            match = matches[0]
        elif matches:
            print(f"Ambiguous skill name '{args.skill}'. Did you mean one of:")
            for m in matches:
                print(f"  • {m.meta.name}")
            return 1
        else:
            print(f"Error: Skill '{args.skill}' not found.")
            return 1

    if args.json:
        out = {
            "name": match.meta.name,
            "description": match.meta.description,
            "version": match.meta.version,
            "license": match.meta.license,
            "allowed_tools": match.meta.allowed_tools,
            "tokens": match.token_estimate,
            "words": match.word_count,
            "path": str(match.path),
            "tags": match.meta.tags,
            "sections": [{"title": s.title, "level": s.level} for s in match.sections],
        }
        print(json.dumps(out, indent=2))
        return 0

    print(f"\nSkill: {match.meta.name}")
    print(f"Path:  {match.path}")
    print(f"Size:  ~{format_tokens(match.token_estimate)} tokens ({match.word_count:,} words)")
    if match.meta.version:
        print(f"Ver:   {match.meta.version}")
    if match.meta.license:
        print(f"Lic:   {match.meta.license}")
    if match.meta.allowed_tools:
        print(f"Tools: {match.meta.allowed_tools}")
    if match.meta.tags:
        print(f"Tags:  {', '.join(match.meta.tags)}")

    if match.meta.description:
        print(f"\nDescription:\n  {match.meta.description.strip()}")

    if match.sections:
        print("\nSections (TOC):")
        for sec in match.sections:
            indent = "  " * sec.level
            print(f"{indent}- {sec.title}")
            print(f"{indent}    -> skills-cli load {match.meta.name} --section \"{sec.title}\"")

    print(f"\nFull load command:\n  skills-cli load {match.meta.name}\n")
    return 0


def cmd_grep(skills: list, args: argparse.Namespace) -> int:
    """Filter skills using glob pattern on name, tags, or path."""
    pat = args.pattern.strip().lower()
    matched = []
    for s in skills:
        haystack = f"{s.meta.name} {' '.join(s.meta.tags)} {s.path}".lower()
        if fnmatch.fnmatch(s.meta.name.lower(), pat) or fnmatch.fnmatch(haystack, pat) or pat in s.meta.name.lower():
            matched.append(s)

    if args.json:
        print(json.dumps([s.meta.name for s in matched], indent=2))
        return 0

    if not matched:
        print(f"No skills matched pattern: '{args.pattern}'")
        return 1

    print(f"\nMatched {len(matched)} skills for pattern '{args.pattern}':")
    for s in matched:
        tok_str = f"~{format_tokens(s.token_estimate)} tok"
        print(f"  • {s.meta.name:<24} {tok_str:>9}")
        if args.with_descriptions and s.meta.description:
            print(f"      {s.meta.description[:90]}...")
    print()
    return 0


def cmd_search(skills: list, args: argparse.Namespace) -> int:
    """Full-text keyword search across skills."""
    matcher = SkillMatcher(skills)
    results = matcher.match(args.query, limit=args.limit, min_score=0.1)

    if args.json:
        out = [
            {
                "skill": r.skill.meta.name,
                "score": r.score,
                "confidence": r.confidence_pct,
                "matched_terms": r.matched_terms,
                "path": str(r.skill.path),
            }
            for r in results
        ]
        print(json.dumps(out, indent=2))
        return 0

    if not results:
        print(f"No skills found matching search: '{args.query}'")
        return 1

    print(f"\nSearch results for '{args.query}':")
    for r in results:
        tok_str = f"~{format_tokens(r.skill.token_estimate)} tok"
        print(f"  • {r.skill.meta.name:<22} [{r.confidence_pct}% match] {tok_str:>9}")
        if r.matched_terms:
            print(f"      Terms: {', '.join(r.matched_terms[:6])}")
        if r.skill.meta.description:
            print(f"      {r.skill.meta.description[:85]}...")
    print()
    return 0


def cmd_match(skills: list, args: argparse.Namespace) -> int:
    """AI task router: evaluate task prompt and recommend top relevant skills."""
    matcher = SkillMatcher(skills)
    results = matcher.match(args.task, limit=args.limit, min_score=0.2)

    if args.json:
        out = [
            {
                "skill": r.skill.meta.name,
                "confidence": r.confidence_pct,
                "score": r.score,
                "tokens": r.skill.token_estimate,
                "matched_terms": r.matched_terms,
                "matched_headings": r.matched_headings,
                "recommended_action": r.recommended_action,
                "description": r.skill.meta.description,
            }
            for r in results
        ]
        print(json.dumps(out, indent=2))
        return 0

    if not results:
        print(f"\nNo matching specialized skill found for task:")
        print(f"  \"{args.task}\"")
        print("Recommendation: Proceed with standard instructions or inspect with 'skills-cli'\n")
        return 0

    print(f"\nTask Match Results for:")
    print(f"  \"{args.task}\"\n")

    for idx, r in enumerate(results, 1):
        tok_str = f"~{format_tokens(r.skill.token_estimate)} tokens"
        print(f"{idx}. {r.skill.meta.name} [Confidence: {r.confidence_pct}%] ({tok_str})")
        if r.skill.meta.description:
            desc = " ".join(r.skill.meta.description.split())
            if len(desc) > 110:
                desc = desc[:107] + "..."
            print(f"   Desc:   {desc}")
        if r.matched_terms:
            print(f"   Match:  {', '.join(r.matched_terms[:6])}")
        if r.matched_headings:
            print(f"   Focus:  {', '.join(r.matched_headings[:2])}")
        print(f"   Action: {r.recommended_action}")
        print()

    return 0


def cmd_load(skills: list, args: argparse.Namespace) -> int:
    """Load skill instructions (full, section, or summary) directly into stdout."""
    target = args.skill.strip().lower()
    match = next((s for s in skills if s.meta.name.lower() == target), None)
    if not match:
        matches = [s for s in skills if target in s.meta.name.lower()]
        if len(matches) == 1:
            match = matches[0]
        elif matches:
            print(f"Error: Ambiguous skill '{args.skill}'. Options: {', '.join(m.meta.name for m in matches)}", file=sys.stderr)
            return 1
        else:
            print(f"Error: Skill '{args.skill}' not found.", file=sys.stderr)
            return 1

    # Ensure full text is loaded
    parsed = parse_skill_file(match.path)

    # 1. Summary mode
    if args.summary:
        print(f"# Skill: {parsed.meta.name}")
        if parsed.meta.description:
            print(f"\n{parsed.meta.description}\n")
        print("## Available Sections:")
        for sec in parsed.sections:
            print(f"  {'  ' * (sec.level - 1)}- {sec.title}")
        print(f"\nTo load a section: skills-cli load {parsed.meta.name} --section \"<title>\"")
        return 0

    # 2. Section extraction
    if args.section:
        sec = extract_section(parsed, args.section)
        if not sec:
            print(f"Error: Section '{args.section}' not found in skill '{parsed.meta.name}'.", file=sys.stderr)
            print("Available sections:", file=sys.stderr)
            for s in parsed.sections:
                print(f"  - {s.title}", file=sys.stderr)
            return 1

        sec_tokens = int(len(sec.content.split()) * 1.33)
        if not args.plain:
            print(f"<!-- Loaded section '{sec.title}' from {parsed.meta.name} (~{sec_tokens} tokens) -->\n")
        print(sec.content)
        return 0

    # 3. Full text with token budget
    content = parsed.full_text
    if args.max_tokens and parsed.token_estimate > args.max_tokens:
        words = content.split()
        max_words = int(args.max_tokens / 1.33)
        truncated = " ".join(words[:max_words])
        if not args.plain:
            print(f"<!-- Truncated to ~{args.max_tokens} tokens (original was ~{parsed.token_estimate} tokens) -->\n")
        print(truncated)
        print("\n\n... [Truncated due to --max-tokens budget. Use --section to read specific parts]")
        return 0

    if not args.plain:
        print(f"<!-- Loaded skill: {parsed.meta.name} (~{parsed.token_estimate} tokens) -->\n")
    print(content)
    return 0


def cmd_stats(skills: list, args: argparse.Namespace) -> int:
    """Output analytics and token impact of dynamic skill loading."""
    total_skills = len(skills)
    total_tokens = sum(s.token_estimate for s in skills)
    total_words = sum(s.word_count for s in skills)
    avg_tokens = total_tokens // max(1, total_skills)

    if args.json:
        print(json.dumps({
            "total_skills": total_skills,
            "total_tokens": total_tokens,
            "total_words": total_words,
            "average_tokens_per_skill": avg_tokens,
        }, indent=2))
        return 0

    print("\nskills-cli Token & Context Analytics:")
    print("=" * 45)
    print(f"  Total Indexed Skills:        {total_skills:,}")
    print(f"  Total Skill Content Size:    {total_tokens:,} tokens ({total_words:,} words)")
    print(f"  Average Skill Size:          ~{avg_tokens:,} tokens")
    print("-" * 45)
    print(f"  Tokens Saved per Turn:       ~{total_tokens:,} tokens")
    print("  Mechanism:                   On-Demand Dynamic Loading (via skills-cli)")
    print("=" * 45 + "\n")
    return 0


def get_skill_tier(path: Path) -> tuple[str, str]:
    """Classify skill into Hybrid Tier based on resolved file path."""
    p_str = str(path.resolve())
    home_str = str(Path.home())
    if f"{home_str}/.config/skills" in p_str:
        return ("Tier B", "On-Demand Library (0 prompt overhead)")
    elif (
        f"{home_str}/.gemini/config/skills" in p_str
        or f"{home_str}/.gemini/antigravity/skills" in p_str
        or f"{home_str}/.agents/skills" in p_str
    ):
        return ("Tier A", "Active in Prompt (<skills> block)")
    elif "/builtin/skills" in p_str:
        return ("Built-in", "Antigravity Product Shipped")
    elif "/plugins/" in p_str:
        return ("Plugin", "Bundled with Installed Plugin")
    else:
        return ("Workspace", "Project Workspace")


def cmd_tiers(skills: list, args: argparse.Namespace) -> int:
    """List skills grouped by their Hybrid Tier (Tier A: Prompt vs Tier B: Library)."""
    groups: dict[str, list] = {
        "Tier A (Active in Prompt)": [],
        "Tier B (On-Demand Library)": [],
        "Plugins & Built-ins": [],
    }
    for s in skills:
        tier, _ = get_skill_tier(s.path)
        if tier == "Tier A":
            groups["Tier A (Active in Prompt)"].append(s)
        elif tier == "Tier B":
            groups["Tier B (On-Demand Library)"].append(s)
        else:
            groups["Plugins & Built-ins"].append(s)

    if args.json:
        out = {}
        for gname, slist in groups.items():
            out[gname] = [
                {"name": s.meta.name, "tokens": s.token_estimate, "path": str(s.path)}
                for s in slist
            ]
        print(json.dumps(out, indent=2))
        return 0

    print("\nskills-cli Hybrid Tier Status:")
    print("=" * 60)

    for gname, slist in groups.items():
        tot_tok = sum(s.token_estimate for s in slist)
        print(f"\n{gname} ({len(slist)} skills, ~{format_tokens(tot_tok)} tokens):")
        if not slist:
            print("  (none)")
            continue
        for s in sorted(slist, key=lambda x: x.meta.name):
            tok_str = f"~{format_tokens(s.token_estimate)} tok"
            print(f"  • {s.meta.name:<22} {tok_str:>9}")

    print("\n" + "=" * 60)
    print("Management: Use 'skills-cli pin <skill>' or 'skills-cli unpin <skill>'\n")
    return 0


def cmd_pin(skills: list, args: argparse.Namespace) -> int:
    """Pin a skill to Tier A (~/.gemini/config/skills) so it is active in prompt."""
    import shutil

    target_name = args.skill.strip().lower()
    skill = next((s for s in skills if s.meta.name.lower() == target_name), None)
    if not skill:
        print(f"Error: Skill '{args.skill}' not found.", file=sys.stderr)
        return 1

    tier, _ = get_skill_tier(skill.path)
    if tier == "Tier A":
        print(f"Skill '{skill.meta.name}' is already in Tier A (active in prompt).")
        return 0

    dest_root = Path.home() / ".gemini" / "config" / "skills"
    dest_root.mkdir(parents=True, exist_ok=True)
    dest_dir = dest_root / skill.meta.name

    if skill.path.parent == dest_dir:
        print(f"Skill '{skill.meta.name}' is already at {dest_dir}")
        return 0

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(skill.path.parent, dest_dir)
    print(f"Pinned '{skill.meta.name}' to Tier A: {dest_dir}")
    print("Rebuilding cache...")
    load_cached_skills(force_reindex=True)
    return 0


def cmd_unpin(skills: list, args: argparse.Namespace) -> int:
    """Unpin a skill from Tier A to Tier B (~/.config/skills) for on-demand use."""
    import shutil

    target_name = args.skill.strip().lower()
    skill = next((s for s in skills if s.meta.name.lower() == target_name), None)
    if not skill:
        print(f"Error: Skill '{args.skill}' not found.", file=sys.stderr)
        return 1

    tier, _ = get_skill_tier(skill.path)
    if tier == "Tier B":
        print(f"Skill '{skill.meta.name}' is already in Tier B (on-demand library).")
        return 0
    if tier in ("Built-in", "Plugin"):
        print(f"Cannot unpin {tier} skill '{skill.meta.name}'.", file=sys.stderr)
        return 1

    lib_root = Path.home() / ".config" / "skills"
    lib_root.mkdir(parents=True, exist_ok=True)
    lib_dir = lib_root / skill.meta.name

    # Copy to library first
    if lib_dir.exists():
        shutil.rmtree(lib_dir)
    shutil.copytree(skill.path.parent, lib_dir)

    # Remove from global config
    if skill.path.parent.exists() and (Path.home() / ".gemini" / "config" / "skills" in skill.path.parents):
        shutil.rmtree(skill.path.parent)

    print(f"Unpinned '{skill.meta.name}' to Tier B: {lib_dir}")
    print(f"Prompt overhead reduced: {skill.meta.name} will not be injected into system prompt.")
    print("Rebuilding cache...")
    load_cached_skills(force_reindex=True)
    return 0


def cmd_sync(skills: list, args: argparse.Namespace) -> int:
    """Force re-index all skills and update cache."""
    cache_file = get_cache_file()
    fresh = load_cached_skills(force_reindex=True)
    print(f"Successfully reindexed {len(fresh)} skills.")
    print(f"Cache updated at: {cache_file}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skills-cli",
        description="skills-cli: Token-efficient dynamic skill discovery & on-demand context loading for AI agents.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=f"skills-cli v{VERSION}")
    parser.add_argument("-d", "--with-descriptions", action="store_true", help="Include full descriptions in listings")
    parser.add_argument("-j", "--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("-w", "--workspace", type=Path, default=None, help="Custom workspace directory to scan")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # list
    p_list = subparsers.add_parser("list", help="List all discovered skills")
    p_list.set_defaults(func=cmd_list)

    # info
    p_info = subparsers.add_parser("info", help="Show skill metadata, TOC, and stats")
    p_info.add_argument("skill", help="Name of skill to inspect")
    p_info.set_defaults(func=cmd_info)

    # grep
    p_grep = subparsers.add_parser("grep", help="Search skills by pattern/glob")
    p_grep.add_argument("pattern", help="Glob pattern or substring (e.g., '*design*')")
    p_grep.set_defaults(func=cmd_grep)

    # search
    p_search = subparsers.add_parser("search", help="Full-text keyword search across skills")
    p_search.add_argument("query", help="Search text query")
    p_search.add_argument("-l", "--limit", type=int, default=10, help="Max results (default: 10)")
    p_search.set_defaults(func=cmd_search)

    # match
    p_match = subparsers.add_parser("match", help="Smart AI task router: recommend skills for a task")
    p_match.add_argument("task", help="Task description or user prompt")
    p_match.add_argument("-l", "--limit", type=int, default=4, help="Max recommendations (default: 4)")
    p_match.set_defaults(func=cmd_match)

    # load / read
    p_load = subparsers.add_parser("load", aliases=["read"], help="Load skill instructions into stdout")
    p_load.add_argument("skill", help="Name of skill to load")
    p_load.add_argument("-s", "--section", help="Extract only the specified section/heading")
    p_load.add_argument("--summary", action="store_true", help="Output frontmatter + TOC outline only")
    p_load.add_argument("--max-tokens", type=int, default=None, help="Truncate content to max token budget")
    p_load.add_argument("--plain", action="store_true", help="Output raw text without header comments")
    p_load.set_defaults(func=cmd_load)

    # stats
    p_stats = subparsers.add_parser("stats", aliases=["gain"], help="Show token analytics & context savings")
    p_stats.set_defaults(func=cmd_stats)

    # tiers / status
    p_tiers = subparsers.add_parser("tiers", aliases=["status"], help="List skills by Hybrid Tier (Tier A: Prompt vs Tier B: On-Demand)")
    p_tiers.set_defaults(func=cmd_tiers)

    # pin
    p_pin = subparsers.add_parser("pin", help="Promote a skill to Tier A (~/.gemini/config/skills) to activate in prompt")
    p_pin.add_argument("skill", help="Name of skill to pin")
    p_pin.set_defaults(func=cmd_pin)

    # unpin
    p_unpin = subparsers.add_parser("unpin", help="Demote a skill to Tier B (~/.config/skills) for on-demand use only")
    p_unpin.add_argument("skill", help="Name of skill to unpin")
    p_unpin.set_defaults(func=cmd_unpin)

    # sync
    p_sync = subparsers.add_parser("sync", help="Force cache rebuild")
    p_sync.set_defaults(func=cmd_sync)

    args = parser.parse_args(argv)

    skills = load_cached_skills(workspace_dir=args.workspace)

    if not args.command:
        # Default behavior: list skills
        return cmd_list(skills, args)

    if hasattr(args, "func"):
        return args.func(skills, args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
