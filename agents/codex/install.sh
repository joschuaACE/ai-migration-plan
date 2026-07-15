#!/bin/bash
set -euo pipefail

# Codex Agent Installer — C++ to Java Migration Toolkit
# Copies docs/ (standards + skills) and generates hooks for auto-discovery.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║  Codex (OpenAI) — C++ to Java Migration Toolkit ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Toolkit:  $TOOLKIT_DIR"
echo "Target:   $TARGET_DIR"
echo ""

DOCS_DIR="$TOOLKIT_DIR/docs/standards"

# --- Copy docs/ ---

echo "→ Copying docs/ directory ..."
mkdir -p "$TARGET_DIR/docs"
cp "$DOCS_DIR"/*.md "$TARGET_DIR/docs/"
echo "  ✓ All docs copied to $TARGET_DIR/docs/"
echo "  Note: Codex auto-discovers files in subdirectories"

# --- Copy docs/skills/ ---

SKILLS_DIR="$TOOLKIT_DIR/docs/skills"
if [ -d "$SKILLS_DIR" ] && ls "$SKILLS_DIR"/*.md >/dev/null 2>&1; then
    echo ""
    echo "→ Copying docs/skills/ directory ..."
    mkdir -p "$TARGET_DIR/docs/skills"
    cp "$SKILLS_DIR"/*.md "$TARGET_DIR/docs/skills/"
    echo "  ✓ All skill workflows copied to $TARGET_DIR/docs/skills/"
    echo "  Note: Codex auto-discovers these as workflow references"
fi

# --- Generate .codex/hooks.json ---

HOOKS_DIR="$TOOLKIT_DIR/docs/hooks"
if [ -d "$HOOKS_DIR" ] && ls "$HOOKS_DIR"/*.md >/dev/null 2>&1; then
    echo ""
    echo "→ Generating .codex/hooks.json ..."
    mkdir -p "$TARGET_DIR/.codex"
    bash "$TOOLKIT_DIR/agents/parse-hooks.sh" codex "$HOOKS_DIR" app \
        > "$TARGET_DIR/.codex/hooks.json"
    echo "  ✓ Hooks generated (.codex/hooks.json)"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "✓ Codex installation complete!"
echo "  docs/ directory with all standards (auto-discovered)."
echo "  Hooks configured in .codex/hooks.json."
echo "═══════════════════════════════════════════════════"
