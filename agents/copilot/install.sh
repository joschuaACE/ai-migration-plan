#!/bin/bash
set -euo pipefail

# GitHub Copilot Agent Installer — C++ to Java Migration Toolkit
# Generates .github/copilot-instructions.md + workspace rules in the target project.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║  GitHub Copilot — C++ to Java Migration Toolkit ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Toolkit:  $TOOLKIT_DIR"
echo "Target:   $TARGET_DIR"
echo ""

DOCS_DIR="$TOOLKIT_DIR/docs/standards"
SKILLS_DIR="$TOOLKIT_DIR/docs/skills"
HOOKS_DIR="$TOOLKIT_DIR/docs/hooks"

# --- Generate .github/copilot-instructions.md ---

echo "→ Generating .github/copilot-instructions.md ..."
mkdir -p "$TARGET_DIR/.github"

OUTPUT="$TARGET_DIR/.github/copilot-instructions.md"

cat > "$OUTPUT" << 'HEADER'
# C++ → Java Migration Toolkit — Copilot Instructions

This project uses an AI-agent-powered migration toolkit for converting C++ applications
to modern Java 25. You must follow the standards, workflows, and quality gates defined
in this file and the referenced docs/ directory.

## Output Types

The toolkit produces one of these depending on `output_type` in `.migration/config.json`:
- **Service** — Spring Boot 4.x with hexagonal architecture
- **Library** — Plain JAR with api/internal/spi layering, module-info.java
- **SDK** — Library + Javadoc + stability annotations + samples
- **CLI** — Picocli + GraalVM native image, stdout/stderr contracts

## Reference Documentation

- `docs/java-service-profile.md` — Spring Boot 4.x services
- `docs/java-library-profile.md` — Plain JAR libraries
- `docs/java-sdk-profile.md` — SDKs with stability annotations
- `docs/java-cli-profile.md` — CLI tools with picocli
- `docs/gradle-version-catalog.md` — Version catalog templates
- `docs/archunit-templates.md` — Architecture test templates
- `docs/test-porting-guide.md` — C++ test → JUnit 5 mapping
- `docs/translation-examples.md` — Worked translation examples
- `docs/migration-agents.md` — Sub-agent role definitions

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

if [ -d "$SKILLS_DIR" ] && ls "$SKILLS_DIR"/*.md >/dev/null 2>&1; then
    echo ""
    echo "→ Appending workflow commands from docs/skills/ ..."
    {
        echo ""
        echo "---"
        echo ""
        echo "## Workflow Commands"
        echo ""
        echo "The following workflows are available. Invoke them by asking"
        echo "(e.g., \"run migrate-init on ./src\"):"
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

# --- Generate .github/copilot-workspace.json for workspace context ---

echo ""
echo "→ Generating .github/copilot-workspace.json ..."

cat > "$TARGET_DIR/.github/copilot-workspace.json" << 'EOF'
{
  "name": "C++ to Java Migration",
  "description": "AI-augmented migration from C++ to Java 25 using structured workflows and quality gates",
  "instructions": ".github/copilot-instructions.md",
  "context": {
    "include": [
      "docs/**/*.md",
      ".migration/**/*.md",
      ".migration/config.json"
    ],
    "exclude": [
      "source/**",
      "node_modules/**",
      "build/**"
    ]
  }
}
EOF
echo "  ✓ copilot-workspace.json created"

# --- Generate quality hooks as VS Code tasks (Copilot can invoke them) ---

if [ -d "$HOOKS_DIR" ] && ls "$HOOKS_DIR"/*.md >/dev/null 2>&1; then
    echo ""
    echo "→ Generating .vscode/tasks.json with quality hooks ..."
    mkdir -p "$TARGET_DIR/.vscode"
    cat > "$TARGET_DIR/.vscode/tasks.json" << 'EOF'
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "migration: compile-on-save",
      "type": "shell",
      "command": "./gradlew compileJava",
      "group": "build",
      "presentation": { "reveal": "silent" },
      "problemMatcher": ["$javac"],
      "runOptions": { "runOn": "folderOpen" }
    },
    {
      "label": "migration: domain-purity-check",
      "type": "shell",
      "command": "./gradlew test --tests '*ArchitectureTest*'",
      "group": "test",
      "presentation": { "reveal": "silent" },
      "problemMatcher": []
    },
    {
      "label": "migration: run-all-tests",
      "type": "shell",
      "command": "./gradlew test",
      "group": "test",
      "presentation": { "reveal": "always" },
      "problemMatcher": []
    },
    {
      "label": "migration: full-verification",
      "type": "shell",
      "command": "./gradlew check",
      "group": "test",
      "presentation": { "reveal": "always" },
      "problemMatcher": ["$javac"]
    }
  ]
}
EOF
    echo "  ✓ VS Code tasks generated (.vscode/tasks.json)"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "✓ GitHub Copilot installation complete!"
echo ""
echo "  Installed:"
echo "    .github/copilot-instructions.md  ← Copilot reads this automatically"
echo "    .github/copilot-workspace.json   ← Workspace context config"
echo "    .vscode/tasks.json               ← Quality hooks as VS Code tasks"
echo "    docs/                            ← Full reference documentation"
echo ""
echo "  Usage:"
echo "    Open project in VS Code with Copilot enabled."
echo "    Ask: \"run migrate-init on ./src\""
echo "═══════════════════════════════════════════════════"
