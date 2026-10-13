# ⚡ skills-cli

**Token-Optimized Dynamic Skill Discovery & On-Demand Context Loading for AI Agents**

Modeled after [`mcp-cli`](https://github.com/philschmid/mcp-cli), `skills-cli` eliminates context bloat and prompt token exhaustion caused by static skill instructions.

---

## 💡 Why skills-cli?

In modern AI agent platforms (Google Antigravity, Claude Code, OpenAI Codex, OpenCode, Cursor), skills are markdown guides (`SKILL.md`) that teach agents specialized procedures.

### The Problem
* **Prompt Saturation:** If you have 20–50 skills installed, the agent framework injects their names and descriptions into the system prompt on *every single turn*. That burns **1,500 – 4,000 tokens per turn** just on metadata.
* **Instruction Bloat:** Loading an entire 3,000-token skill when the agent only needs a 10-line styling rule wastes 95% of the context window.
* **Degraded Reasoning:** Cluttered context windows dilute the LLM's attention on your actual codebase.

### The Solution: `skills-cli`
1. **Dynamic Task Routing (`match`):** Finds the exact skill needed for a task using BM25 relevance scoring and identifies the specific section.
2. **Selective Extraction (`load --section`):** Extracts *only* the relevant subsection into context, achieving **85–98% token savings**.
3. **Hybrid Tiering (`tiers`, `pin`, `unpin`):** Keeps essential meta-skills in the active prompt while moving domain-specific skills to an on-demand library (`~/.config/skills`) where they consume **0 tokens** until invoked.

---

## 🚀 Quick Start (10-Second Setup)

### 1. Requirements
* Linux or macOS (or Windows via WSL)
* Python 3.8+ (uses standard library only — **zero `pip` dependencies**)

### 2. Run the Installer
In this directory, run:
```bash
./install.sh
```

The installer will:
1. Install `skills-cli` to `~/.local/bin` (or `~/.config/Antigravity/bin` if detected).
2. Set up the Tier B on-demand skills directory at `~/.config/skills`.
3. If Antigravity or Claude Code is detected, register the agent rule and skill automatically.
4. Verify the installation.

### 3. Verify
```bash
skills-cli --version
skills-cli tiers
```

*(If `skills-cli` is not found, ensure `~/.local/bin` is in your `PATH`: `export PATH="$HOME/.local/bin:$PATH"`)*

---

## 📖 Command Reference

### 1. Smart Task Router (`match`)
Ask `skills-cli` which skill is needed for a prompt or task:
```bash
skills-cli match "build a responsive landing page with tailwind and shadcn"
```
**Example Output:**
```text
1. ui-styling [Confidence: 99%] (~2.2k tokens)
   Desc:   Create beautiful, accessible user interfaces with shadcn/ui components...
   Match:  responsive, tailwind, ui
   Focus:  Styling Layer: Tailwind CSS
   Action: skills-cli load ui-styling --section "Styling Layer: Tailwind CSS"

2. design-system [Confidence: 65%] (~1.5k tokens)
   Desc:   Design tokens, color palettes, spacing...
   Focus:  Tokens Reference
   Action: skills-cli load design-system --section "Tokens Reference"
```

---

### 2. Granular Context Loading (`load`)
Never dump a whole 500-line markdown file when you only need a piece.

```bash
# Load ONLY a specific section (saves 90-98% tokens):
skills-cli load ui-styling --section "Styling Layer: Tailwind CSS"

# View structure outline and frontmatter only:
skills-cli load ui-styling --summary

# Load with a strict token budget:
skills-cli load ui-styling --max-tokens 500

# Full skill loading (when entire procedure is required):
skills-cli load ui-styling
```

---

### 3. Hybrid Tier Management (`tiers`, `pin`, `unpin`)

Organize your skills into two tiers:
* **Tier A (Active in Prompt):** Essential meta-skills (e.g. `skills-cli`, `mcp-cli`, `planning-with-files`) residing in your agent's auto-loaded config (`~/.gemini/config/skills/`).
* **Tier B (On-Demand Library):** Domain specialists (e.g. `ui-ux-pro-max`, `banner-design`, `slides`, `deep-research`) residing in `~/.config/skills/`. They consume **0 prompt tokens** until called.

```bash
# Check current tier status across all roots:
skills-cli tiers

# Demote a skill to Tier B (frees up prompt tokens):
skills-cli unpin ui-ux-pro-max

# Promote a skill to Tier A (makes it always visible in prompt):
skills-cli pin ui-ux-pro-max
```

---

### 4. Skill Inspection & Search

```bash
# List all skills with estimated token footprints:
skills-cli list

# List with full descriptions:
skills-cli list -d

# Inspect table of contents and metadata without reading the whole file:
skills-cli info ui-styling

# Glob/pattern match:
skills-cli grep "*design*"

# Full-text keyword search:
skills-cli search "color palette"

# Token footprint analytics:
skills-cli stats

# Force re-index cache (~2ms):
skills-cli sync
```

---

## 🤖 Teaching Your AI Agent to Use `skills-cli`

To ensure your agent (Antigravity, Claude Code, Codex, Cursor) uses `skills-cli` automatically, add the following rule to your agent's system prompt or rule file (`AGENTS.md` / `.cursorrules` / `CLAUDE.md`):

```markdown
# Dynamic Skill Discovery & Context Optimization

Avoid bloating the prompt context with full skill manuals or dozens of static instructions.
Use `skills-cli` to discover and load skills dynamically on demand:

1. Task Matching: When handling a specialized workflow (design, research, planning, testing, slides, UI), check available skills using:
   skills-cli match "<task description>"

2. Progressive Disclosure: Do not dump entire skill files if only a specific section or procedure is needed. Inspect the outline with `skills-cli info <skill>` and load the exact section via:
   skills-cli load <skill> --section "<heading>"

3. Context Economy: Load instructions for the active step only, then proceed with execution without carrying unnecessary procedural text across subsequent turns.
```

---

## 🛠 Directory Layout

```
skills-cli-export/
├── bin/
│   └── skills-cli              # Standalone single-file binary (zero pip dependencies)
├── install.sh                  # One-click installer
├── uninstall.sh                # Clean uninstaller
├── README.md                   # Complete usage guide
├── README.me                   # Symlink / mirror of README
├── agent-skill/                # Agent-invocable skill definition (SKILL.md)
│   └── SKILL.md
├── plugin/                     # Ready-to-use Antigravity plugin bundle
│   ├── plugin.json
│   ├── rules/AGENTS.md
│   └── skills/skills-cli/SKILL.md
├── src/                        # Modular Python source code
│   ├── parser.py               # YAML frontmatter & markdown heading parser
│   ├── discovery.py            # Multi-root skill scanner
│   ├── matcher.py              # BM25 relevance & token scoring engine
│   ├── cache.py                # High-speed mtime-validated cache (~/.cache/skills-cli)
│   └── cli.py                  # CLI argument parser & subcommand handlers
├── tests/                      # Automated test suite
│   └── test_skills_cli.py
└── build_standalone.py         # Script to bundle src/ into bin/skills-cli
```

---

## 🧪 Developer: Running Tests & Rebuilding

### Run Test Suite
```bash
python3 -m unittest discover -s tests
```
*(All 12 unit and integration tests execute in ~50ms without external dependencies).*

### Rebuild Standalone Binary
If you edit files in `src/`, rebuild the standalone single-file binary with:
```bash
python3 build_standalone.py
```
This merges all modules into `bin/skills-cli` while stripping relative imports, preserving zero-dependency standalone portability.

---

## 📄 License
MIT License. Free to share, modify, and distribute with your team and friends!
