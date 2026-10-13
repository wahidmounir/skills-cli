---
name: skills-cli
description: "CLI tool for dynamic skill discovery, task-aware matching, and on-demand context loading. Modeled on mcp-cli to keep irrelevant skills out of the model's context window. Use to find relevant skills for any task, inspect metadata/TOC without token bloat, and extract specific sections with up to 98% token savings."
user-invocable: true
allowed-tools: "Bash Read"
metadata:
  version: "1.0.0"
---

# skills-cli: Dynamic Skill Discovery & Context Optimization

`skills-cli` is a high-performance CLI utility for dynamic skill discovery and on-demand context loading, designed to conserve model attention and context window capacity.

Just as `mcp-cli` keeps unnecessary MCP tool definitions out of your context window until needed, `skills-cli` prevents context bloat from dozens of static skill instructions.

---

## 1. When to Use skills-cli

Use `skills-cli` whenever you:
- Are asked to perform a specialized task (e.g. banner design, deep research, presentations, planning, generative UI) and want to discover if a specialized skill exists.
- Want to inspect a skill's instructions without dumping a 5,000-word file into your context.
- Need only a specific section of a skill (e.g. "Quick Start", "Critical Rules", "Templates").
- Want to see token consumption analytics for active skills.

---

## 2. Command Reference

### Task-Aware Matching (Smart Router)
Find the best skills for a specific user request:
```bash
skills-cli match "<task description or user query>"
```
*Output includes confidence percentages, matched terms, and suggested loading commands.*

### Listing & Searching Skills
```bash
# Concise list of all skills with token estimates:
skills-cli

# With descriptions:
skills-cli -d

# Search by pattern or tag (glob):
skills-cli grep "*design*"

# Full-text keyword search:
skills-cli search "literature review"
```

### Inspecting Skill Structure
Inspect metadata, prerequisites, and the Table of Contents **without loading the file content**:
```bash
skills-cli info <skill-name>
```

### Progressive On-Demand Loading
Load only what is needed for the current step:
```bash
# 1. Section extraction (recommended - saves 90-98% tokens):
skills-cli load <skill-name> --section "<heading>"

# 2. Structural summary (frontmatter + outline):
skills-cli load <skill-name> --summary

# 3. Budget-capped loading:
skills-cli load <skill-name> --max-tokens 500

# 4. Full skill loading (when full procedure is required):
skills-cli load <skill-name>
```

### Token Analytics
Inspect total token footprint and context savings:
```bash
skills-cli stats
```

---

## 3. Best Practices for Antigravity Agents

1. **Route before guessing**: When a user request touches a domain (e.g., social media banners, slides, academic research, UI design), run `skills-cli match "<user request>"` before trying to invent instructions.
2. **Prefer section extraction**: Most 40KB skills only have 1 or 2 sections relevant to your immediate turn. Use `skills-cli info <skill>` to see the TOC, then load only `--section "<target>"`.
3. **Keep context clean**: After finishing with a skill, you do not need to persist its raw text; keep only your findings and artifacts.
