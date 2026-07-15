#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║  C++ → Java Migration Toolkit — Installer       ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Which agent are you using?"
echo ""
echo "  1) Kiro    (steering + slash commands + hooks)"
echo "  2) Claude  (CLAUDE.md with workflows)"
echo "  3) Codex   (AGENTS.md + docs/)"
echo ""
read -rp "Select [1-3]: " choice

echo ""
read -rp "Target project path [.]: " target
target="${target:-.}"

case "$choice" in
    1) bash "$SCRIPT_DIR/agents/kiro/install.sh" "$target" ;;
    2) bash "$SCRIPT_DIR/agents/claude/install.sh" "$target" ;;
    3) bash "$SCRIPT_DIR/agents/codex/install.sh" "$target" ;;
    *) echo "Invalid choice."; exit 1 ;;
esac
