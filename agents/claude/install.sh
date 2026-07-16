#!/bin/bash
set -euo pipefail

# Claude Code Agent Installer — C++ to Java Migration Toolkit
# Generates a CLAUDE.md in the target project by concatenating key docs.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║  Claude Code — C++ to Java Migration Toolkit    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Toolkit:  $TOOLKIT_DIR"
echo "Target:   $TARGET_DIR"
echo ""

DOCS_DIR="$TOOLKIT_DIR/docs/standards"
OUTPUT="$TARGET_DIR/CLAUDE.md"

echo "→ Generating CLAUDE.md ..."

cat > "$OUTPUT" << 'HEADER'
# C++ → Java Migration Toolkit

This project uses an AI-agent-powered migration toolkit for converting C++ applications
to modern Java 25. The toolkit produces Spring Boot services, plain JAR libraries, SDKs,
or CLI tools depending on the `output_type` configured in `.migration/config.json`.

## How to Use

1. Read the standards below — they govern ALL generated code
2. For output-type-specific standards, see the `docs/` directory:
   - `docs/java-service-profile.md` — Spring Boot 4.x services
   - `docs/java-library-profile.md` — Plain JAR libraries
   - `docs/java-sdk-profile.md` — SDKs with docs + stability annotations
   - `docs/java-cli-profile.md` — CLI tools with picocli
3. Additional reference docs in `docs/`:
   - `docs/gradle-version-catalog.md` — Version catalog templates
   - `docs/archunit-templates.md` — Architecture test templates
   - `docs/test-porting-guide.md` — C++ test → JUnit 5 mapping
   - `docs/translation-examples.md` — Worked translation examples
   - `docs/migration-agents.md` — Sub-agent definitions

---

HEADER

# Append migration philosophy
if [ -f "$DOCS_DIR/migration-philosophy.md" ]; then
    echo "" >> "$OUTPUT"
    cat "$DOCS_DIR/migration-philosophy.md" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "---" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "  ✓ Included: migration-philosophy.md"
fi

# Append java target standards
if [ -f "$DOCS_DIR/java-target-standards.md" ]; then
    echo "" >> "$OUTPUT"
    cat "$DOCS_DIR/java-target-standards.md" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "---" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "  ✓ Included: java-target-standards.md"
fi

# Append migration agents
if [ -f "$DOCS_DIR/migration-agents.md" ]; then
    echo "" >> "$OUTPUT"
    cat "$DOCS_DIR/migration-agents.md" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "  ✓ Included: migration-agents.md"
fi

# --- Append workflow commands from portable skills ---

SKILLS_DIR="$TOOLKIT_DIR/docs/skills"
if [ -d "$SKILLS_DIR" ] && ls "$SKILLS_DIR"/*.md >/dev/null 2>&1; then
    echo ""
    echo "→ Appending workflow commands from docs/skills/ ..."
    {
        echo ""
        echo "---"
        echo ""
        echo "## Workflow Commands"
        echo ""
        echo "The following workflows are available. Invoke them by asking (e.g., \"run migrate-init on ./src\"):"
        echo ""
    } >> "$OUTPUT"

    for skill_file in "$SKILLS_DIR"/*.md; do
        skill_name="$(basename "$skill_file" .md)"
        {
            echo "### $skill_name"
            echo ""
            cat "$skill_file"
            echo ""
        } >> "$OUTPUT"
        echo "  ✓ Skill: $skill_name"
    done
fi

# --- Copy docs/ for profile reference ---

echo ""
echo "→ Copying docs/ directory for profile reference ..."
mkdir -p "$TARGET_DIR/docs"
cp "$DOCS_DIR"/*.md "$TARGET_DIR/docs/"
if [ -d "$SKILLS_DIR" ]; then
    mkdir -p "$TARGET_DIR/docs/skills"
    cp "$SKILLS_DIR"/*.md "$TARGET_DIR/docs/skills/"
    echo "  ✓ All docs + skills copied to $TARGET_DIR/docs/"
else
    echo "  ✓ All docs copied to $TARGET_DIR/docs/"
fi

# --- Generate .claude/settings.json with hooks ---

HOOKS_DIR="$TOOLKIT_DIR/docs/hooks"
if [ -d "$HOOKS_DIR" ] && ls "$HOOKS_DIR"/*.md >/dev/null 2>&1; then
    echo ""
    echo "→ Generating .claude/settings.json with hooks ..."
    mkdir -p "$TARGET_DIR/.claude"
    bash "$TOOLKIT_DIR/agents/parse-hooks.sh" claude "$HOOKS_DIR" app \
        > "$TARGET_DIR/.claude/settings.json"
    echo "  ✓ Hooks generated (.claude/settings.json)"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "✓ Claude Code installation complete!"
echo "  CLAUDE.md created at project root."
echo "  Hooks configured in .claude/settings.json."
echo "  Profile docs available in docs/ directory."
echo "═══════════════════════════════════════════════════"
