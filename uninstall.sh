#!/usr/bin/env bash
# ==============================================================================
# skills-cli Uninstaller
# ==============================================================================

set -e

echo "Uninstalling skills-cli..."

# Remove binary from common locations
BIN_LOCATIONS=(
    "$HOME/.config/Antigravity/bin/skills-cli"
    "$HOME/.local/bin/skills-cli"
    "$HOME/bin/skills-cli"
    "/usr/local/bin/skills-cli"
)

REMOVED=0
for loc in "${BIN_LOCATIONS[@]}"; do
    if [ -f "$loc" ]; then
        rm -f "$loc"
        echo "[+] Removed binary: $loc"
        REMOVED=1
    fi
done

if [ "$REMOVED" -eq 0 ]; then
    echo "[-] No installed binary found in standard locations."
fi

# Remove cache
if [ -d "$HOME/.cache/skills-cli" ]; then
    rm -rf "$HOME/.cache/skills-cli"
    echo "[+] Removed cache: ~/.cache/skills-cli"
fi

# Clean up Antigravity registrations
if [ -d "$HOME/.gemini/config/skills/skills-cli" ]; then
    rm -rf "$HOME/.gemini/config/skills/skills-cli"
    echo "[+] Removed skill from ~/.gemini/config/skills/skills-cli"
fi

if [ -d "$HOME/.gemini/config/plugins/skills-cli" ]; then
    rm -rf "$HOME/.gemini/config/plugins/skills-cli"
    echo "[+] Removed plugin from ~/.gemini/config/plugins/skills-cli"
fi

if [ -d "$HOME/.agents/skills/skills-cli" ]; then
    rm -rf "$HOME/.agents/skills/skills-cli"
    echo "[+] Removed skill from ~/.agents/skills/skills-cli"
fi

echo ""
echo "[*] Note: ~/.config/skills (Tier B library) has been preserved so you do not lose your custom skills."
echo "    If you wish to remove it manually, run: rm -rf ~/.config/skills"
echo ""
echo "[+] Uninstallation complete."
