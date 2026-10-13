#!/usr/bin/env python3
"""Build a single-file standalone executable for skills-cli."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
BIN = ROOT / "bin"
BIN.mkdir(exist_ok=True)

OUTPUT = BIN / "skills-cli"

HEADER = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"skills-cli: Token-efficient dynamic skill discovery & on-demand context loading for AI agents.

Modeled on mcp-cli to keep unnecessary skills out of model context windows.
Version: 1.0.0
\"\"\"

from __future__ import annotations
"""

# Order matters for dependencies: parser, discovery, matcher, cache, cli
MODULES = ["parser.py", "discovery.py", "matcher.py", "cache.py", "cli.py"]

combined_code = [HEADER]

for mod_name in MODULES:
    mod_path = SRC / mod_name
    lines = mod_path.read_text(encoding="utf-8").splitlines()
    clean_lines = []
    for line in lines:
        # Strip relative imports
        if line.startswith("from ."):
            continue
        if line.startswith("from __future__"):
            continue
        clean_lines.append(line)
    
    combined_code.append(f"\n# --- BEGIN MODULE: {mod_name} ---\n")
    combined_code.append("\n".join(clean_lines))
    combined_code.append(f"\n# --- END MODULE: {mod_name} ---\n")

OUTPUT.write_text("\n".join(combined_code), encoding="utf-8")
OUTPUT.chmod(0o755)

print(f"Built standalone binary: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
