#!/usr/bin/env bash
# ==============================================================================
# skills-cli Installer
# Dynamic Skill Discovery & On-Demand Context Loading for AI Agents
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_SRC="$SCRIPT_DIR/bin/skills-cli"

echo "============================================================"
echo "          skills-cli: Agent Context Optimizer Setup         "
echo "============================================================"

# 1. Check Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[-] Error: python3 is required but was not found in PATH."
    echo "    Please install Python 3.8+ and re-run this script."
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_COMPAT=$(python3 -c "import sys; print(1 if sys.version_info >= (3, 8) else 0)")
if [ "$PY_COMPAT" -ne 1 ]; then
    echo "[-] Error: Python 3.8 or higher is required (found $PYTHON_VER)."
    exit 1
fi
echo "[+] Detected Python $PYTHON_VER (compatible)"

# 2. Determine target binary directory
TARGET_DIR=""

# Check command line argument --prefix or --dir
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir|--prefix)
            TARGET_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./install.sh [--dir <installation-directory>]"
            echo "Options:"
            echo "  --dir PATH    Install binary into PATH (default: ~/.local/bin or ~/.config/Antigravity/bin)"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

if [ -z "$TARGET_DIR" ]; then
    if [ -d "$HOME/.config/Antigravity/bin" ]; then
        TARGET_DIR="$HOME/.config/Antigravity/bin"
    elif [ -d "$HOME/.local/bin" ] || [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
        TARGET_DIR="$HOME/.local/bin"
    elif [ -d "$HOME/bin" ]; then
        TARGET_DIR="$HOME/bin"
    else
        TARGET_DIR="$HOME/.local/bin"
    fi
fi

mkdir -p "$TARGET_DIR"
echo "[+] Installing binary into: $TARGET_DIR"

if [ ! -f "$BIN_SRC" ]; then
    echo "[*] Compiling standalone binary..."
    python3 "$SCRIPT_DIR/build_standalone.py"
fi

cp "$BIN_SRC" "$TARGET_DIR/skills-cli"
chmod +x "$TARGET_DIR/skills-cli"
echo "[+] Installed: $TARGET_DIR/skills-cli"

# 3. Setup Tier B on-demand skills directory
SKILLS_LIB="$HOME/.config/skills"
mkdir -p "$SKILLS_LIB"
echo "[+] Configured Tier B (on-demand library) at: $SKILLS_LIB"

# 4. Integrate with AI Agent environments (Antigravity / Claude Code / Codex)
# Antigravity Global Skill
if [ -d "$HOME/.gemini" ]; then
    AGY_SKILL_DIR="$HOME/.gemini/config/skills/skills-cli"
    mkdir -p "$AGY_SKILL_DIR" 2>/dev/null || true
    if cp "$SCRIPT_DIR/agent-skill/SKILL.md" "$AGY_SKILL_DIR/SKILL.md" 2>/dev/null; then
        echo "[+] Registered global skill for Antigravity at: $AGY_SKILL_DIR"
    fi

    # Antigravity Plugin
    AGY_PLUGIN_DIR="$HOME/.gemini/config/plugins/skills-cli"
    mkdir -p "$AGY_PLUGIN_DIR/rules" "$AGY_PLUGIN_DIR/skills/skills-cli" 2>/dev/null || true
    cp "$SCRIPT_DIR/plugin/plugin.json" "$AGY_PLUGIN_DIR/plugin.json" 2>/dev/null || true
    cp "$SCRIPT_DIR/plugin/rules/AGENTS.md" "$AGY_PLUGIN_DIR/rules/AGENTS.md" 2>/dev/null || true
    if cp "$SCRIPT_DIR/plugin/skills/skills-cli/SKILL.md" "$AGY_PLUGIN_DIR/skills/skills-cli/SKILL.md" 2>/dev/null; then
        echo "[+] Registered Antigravity plugin at: $AGY_PLUGIN_DIR"
    fi
fi

# Generic / Claude / Codex agents directory
if [ -d "$HOME/.agents" ]; then
    AGENTS_DIR="$HOME/.agents/skills/skills-cli"
    mkdir -p "$AGENTS_DIR" 2>/dev/null || true
    if cp "$SCRIPT_DIR/agent-skill/SKILL.md" "$AGENTS_DIR/SKILL.md" 2>/dev/null; then
        echo "[+] Registered agent skill at: $AGENTS_DIR"
    fi
fi

# 5. Check PATH
case ":$PATH:" in
    *":$TARGET_DIR:"*)
        IN_PATH=1
        ;;
    *)
        IN_PATH=0
        ;;
esac

echo ""
echo "============================================================"
echo "                   Verification & Status                    "
echo "============================================================"

"$TARGET_DIR/skills-cli" --version

if [ "$IN_PATH" -eq 1 ]; then
    echo "[+] skills-cli is in your PATH and ready to run!"
else
    echo "[!] NOTE: $TARGET_DIR is not currently in your PATH."
    echo "    Add it to your ~/.bashrc or ~/.zshrc by running:"
    echo "    export PATH=\"$TARGET_DIR:\$PATH\""
fi

echo ""
echo "Quick Test:"
"$TARGET_DIR/skills-cli" tiers

echo ""
echo "============================================================"
echo " Installation Complete! "
echo " Try: skills-cli match \"design a landing page\""
echo " See README.md (or README.me) for complete usage instructions."
echo "============================================================"
