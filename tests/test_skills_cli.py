"""Unit and integration tests for skills-cli."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.parser import (
    _parse_yaml_minimal,
    parse_frontmatter,
    parse_sections,
    parse_skill_file,
    estimate_tokens,
    extract_section,
    ParsedSkill,
    SkillMeta,
)
from src.matcher import SkillMatcher, tokenize
from src.discovery import scan_skills
from src.cache import load_cached_skills, serialize_skill, deserialize_skill
from src.cli import main


class TestParser(unittest.TestCase):
    def test_estimate_tokens(self):
        text = "Hello world this is a test"
        tokens = estimate_tokens(text)
        self.assertGreater(tokens, 0)
        self.assertEqual(estimate_tokens(""), 0)

    def test_parse_yaml_minimal(self):
        raw = """
name: test-skill
description: A wonderful skill for testing
version: 1.2.3
user-invocable: true
allowed-tools: [Bash, Read]
tags:
  - testing
  - automation
multiline: >
  This is a folded
  multiline string
"""
        res = _parse_yaml_minimal(raw)
        self.assertEqual(res["name"], "test-skill")
        self.assertEqual(res["description"], "A wonderful skill for testing")
        self.assertEqual(res["version"], "1.2.3")
        self.assertTrue(res["user-invocable"])
        self.assertEqual(res["allowed-tools"], ["Bash", "Read"])
        self.assertEqual(res["tags"], ["testing", "automation"])
        self.assertIn("This is a folded multiline string", res["multiline"])

    def test_parse_sections(self):
        markdown = """
# Main Title
Intro text

## Section 1
Content 1

### Subsection 1.1
Content 1.1

## Section 2
Content 2
"""
        sections = parse_sections(markdown)
        self.assertGreaterEqual(len(sections), 3)
        titles = [s.title for s in sections]
        self.assertIn("Main Title", titles)
        self.assertIn("Section 1", titles)
        self.assertIn("Subsection 1.1", titles)
        self.assertIn("Section 2", titles)

    def test_extract_section(self):
        markdown = """
# Guide
Intro

## Quick Start
Do this step first.

## Advanced
Do this step later.
"""
        sections = parse_sections(markdown)
        skill = ParsedSkill(
            path=Path("/tmp/SKILL.md"),
            meta=SkillMeta(name="guide"),
            sections=sections,
            full_text=markdown,
            word_count=20,
            token_estimate=30,
            mtime=0,
        )
        sec = extract_section(skill, "quick start")
        self.assertIsNotNone(sec)
        self.assertEqual(sec.title, "Quick Start")
        self.assertIn("Do this step first.", sec.content)

        missing = extract_section(skill, "Nonexistent")
        self.assertIsNone(missing)


class TestMatcher(unittest.TestCase):
    def setUp(self):
        self.skill1 = ParsedSkill(
            path=Path("/tmp/banner.md"),
            meta=SkillMeta(
                name="banner-design",
                description="Design banners for Twitter, LinkedIn and ads",
                tags=["banner", "design", "social"],
            ),
            sections=parse_sections("## Banner Setup\nConfigure banners.\n## Generation\nCreate banners."),
            full_text="Design beautiful banners for social media",
            word_count=50,
            token_estimate=70,
            mtime=0,
        )
        self.skill2 = ParsedSkill(
            path=Path("/tmp/research.md"),
            meta=SkillMeta(
                name="deep-research",
                description="Deep research and literature review with citation verification",
                tags=["research", "literature"],
            ),
            sections=parse_sections("## Research Pipeline\nStep 1: Literature search."),
            full_text="Deep research multi-source synthesis",
            word_count=50,
            token_estimate=70,
            mtime=0,
        )
        self.matcher = SkillMatcher([self.skill1, self.skill2])

    def test_task_match(self):
        results = self.matcher.match("I want to design a banner for LinkedIn")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].skill.meta.name, "banner-design")
        self.assertIn("banner", results[0].matched_terms)

    def test_research_match(self):
        results = self.matcher.match("Perform a literature search on deep learning")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].skill.meta.name, "deep-research")
        self.assertIn("literature", results[0].matched_terms)


class TestCLIIntegration(unittest.TestCase):
    def test_cli_list(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            code = main(["list"])
        self.assertEqual(code, 0)
        output = f.getvalue()
        self.assertIn("Discovered", output)
        self.assertIn("planning-with-files", output)

    def test_cli_stats(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            code = main(["stats"])
        self.assertEqual(code, 0)
        output = f.getvalue()
        self.assertIn("Token & Context Analytics", output)
        self.assertIn("Tokens Saved", output)

    def test_cli_grep(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            code = main(["grep", "*design*"])
        self.assertEqual(code, 0)
        output = f.getvalue()
        self.assertIn("banner-design", output)

    def test_cli_match(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            code = main(["match", "design a logo and banner"])
        self.assertEqual(code, 0)
        output = f.getvalue()
        self.assertIn("Task Match Results", output)

    def test_cli_info(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            code = main(["info", "planning-with-files"])
        self.assertEqual(code, 0)
        output = f.getvalue()
        self.assertIn("Skill: planning-with-files", output)
        self.assertIn("Sections (TOC)", output)

    def test_cli_load_section(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            code = main(["load", "planning-with-files", "--section", "Quick Start"])
        self.assertEqual(code, 0)
        output = f.getvalue()
        self.assertIn("Quick Start", output)
        self.assertIn("templates/task_plan.md", output)


if __name__ == "__main__":
    unittest.main()
