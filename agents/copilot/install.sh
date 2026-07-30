#!/bin/bash
set -euo pipefail

# GitHub Copilot Agent Installer — C++ to Java Migration Toolkit
# Generates 2026-native Copilot structure:
#   .github/copilot-instructions.md  ← Repository-wide instructions
#   .github/instructions/*.instructions.md  ← Path-specific instructions
#   .github/skills/  ← Agent skills (open standard)
#   .github/hooks/*.json  ← Native hook JSON files

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║  GitHub Copilot — C++ to Java Migration Toolkit ║"
echo "║  (2026 Native Structure)                        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Toolkit:  $TOOLKIT_DIR"
echo "Target:   $TARGET_DIR"
echo ""

DOCS_DIR="$TOOLKIT_DIR/docs/standards"
SKILLS_DIR="$TOOLKIT_DIR/docs/skills"
HOOKS_DIR="$TOOLKIT_DIR/docs/hooks"
PARSE_HOOKS="$TOOLKIT_DIR/agents/parse-hooks.sh"

# --- Generate .github/copilot-instructions.md ---

echo "→ Generating .github/copilot-instructions.md ..."
mkdir -p "$TARGET_DIR/.github"

OUTPUT="$TARGET_DIR/.github/copilot-instructions.md"

cat > "$OUTPUT" << 'HEADER'
# C++ → Java Migration Toolkit — Copilot Instructions

This project uses an AI-agent-powered migration toolkit for converting C++ applications
to modern Java 25. You must follow the standards, workflows, and quality gates defined
in this file and the associated .github/ directories.

## Output Types

The toolkit produces one of these depending on `output_type` in `.migration/config.json`:
- **Service** — Spring Boot 4.x with hexagonal architecture
- **Library** — Plain JAR with api/internal/spi layering, module-info.java
- **SDK** — Library + Javadoc + stability annotations + samples
- **CLI** — Picocli + GraalVM native image, stdout/stderr contracts

## Project Structure

- `.github/copilot-instructions.md` — This file (repository-wide instructions)
- `.github/instructions/` — Path-specific instructions per file pattern
- `.github/skills/` — Reusable agent skills for migration workflows
- `.github/hooks/` — Native hook configurations for quality automation
- `docs/` — Full reference documentation

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

# --- Generate .github/instructions/ for path-specific rules ---

echo ""
echo "→ Generating .github/instructions/ (path-specific instructions) ..."
mkdir -p "$TARGET_DIR/.github/instructions"

# Domain layer instructions
cat > "$TARGET_DIR/.github/instructions/domain-purity.instructions.md" << 'EOF'
---
applyTo: "**/domain/**/*.java"
---

# Domain Layer Purity Rules

Files in the domain layer MUST follow these strict rules:

## Forbidden Imports
- NO Spring imports (`org.springframework.*`)
- NO Jakarta imports (`jakarta.*`)
- NO persistence annotations
- NO HTTP/REST annotations
- NO framework-specific code

## Allowed Dependencies
- java.* (core Java only)
- Project-internal domain types
- Value objects from this package

## Patterns
- Use records for value objects
- Use sealed interfaces for domain hierarchies
- Pure functions where possible
- Domain services must be stateless

## Testing
- All domain logic must have unit tests
- Tests should not require Spring context
EOF
echo "  ✓ Created: domain-purity.instructions.md"

# Adapter layer instructions
cat > "$TARGET_DIR/.github/instructions/adapter-layer.instructions.md" << 'EOF'
---
applyTo: "**/adapter/**/*.java,**/adapters/**/*.java"
---

# Adapter Layer Rules

Adapters implement ports and connect to external systems.

## Dependency Direction
- Adapters depend on domain (via ports)
- Domain NEVER depends on adapters
- Adapters may depend on frameworks (Spring, JPA, etc.)

## Inbound Adapters (adapter/in/)
- REST controllers
- gRPC service implementations
- Message listeners
- CLI commands

## Outbound Adapters (adapter/out/)
- Repository implementations
- HTTP clients
- Message publishers
- File system access

## Testing
- Integration tests for external system interaction
- Use @SpringBootTest only when necessary
- Mock external dependencies at the boundary
EOF
echo "  ✓ Created: adapter-layer.instructions.md"

# Test file instructions
cat > "$TARGET_DIR/.github/instructions/test-standards.instructions.md" << 'EOF'
---
applyTo: "**/test/**/*.java,**/*Test.java,**/*Tests.java"
---

# Test Standards

Follow these conventions for all test code.

## Naming
- Test class: `{ClassName}Test` or `{ClassName}Tests`
- Test method: `should{ExpectedBehavior}_when{Condition}`

## Structure
- Arrange-Act-Assert (AAA) pattern
- One assertion concept per test
- Use @Nested for grouping related tests

## Assertions
- Use AssertJ: `assertThat(actual).isEqualTo(expected)`
- Avoid JUnit `assertEquals` in favor of AssertJ

## Mocking
- Use Mockito for mocks
- Prefer fakes over mocks for domain tests
- Never mock domain objects

## Coverage
- Every production class needs a companion test
- Domain layer: >90% coverage
- Adapters: cover critical paths
EOF
echo "  ✓ Created: test-standards.instructions.md"

# Migration state files
cat > "$TARGET_DIR/.github/instructions/migration-state.instructions.md" << 'EOF'
---
applyTo: ".migration/**/*"
---

# Migration State Files

Files in .migration/ track migration progress and decisions.

## File Types
- `config.json` — Output type, paths, settings
- `state.md` — Current phase, wave, progress
- `inventory.md` — All C++ files classified
- `decisions.md` — Architectural divergences

## Editing Rules
- Never edit state files manually during automated migration
- Workflow commands update state atomically
- Decisions must include rationale and date

## migrate-resume
When resuming after session break, read:
1. `state.md` for current progress
2. `decisions.md` for constraints
3. Phase-specific `*-progress.md` files
EOF
echo "  ✓ Created: migration-state.instructions.md"

# --- Generate .github/skills/ directory ---

echo ""
echo "→ Generating .github/skills/ (agent skills) ..."
mkdir -p "$TARGET_DIR/.github/skills"

if [ -d "$SKILLS_DIR" ] && ls "$SKILLS_DIR"/*.md >/dev/null 2>&1; then
    for skill_file in "$SKILLS_DIR"/*.md; do
        skill_name="$(basename "$skill_file" .md)"
        skill_dir="$TARGET_DIR/.github/skills/$skill_name"
        mkdir -p "$skill_dir"
        
        # Create SKILL.md with proper frontmatter
        cat > "$skill_dir/SKILL.md" << SKILL_HEADER
---
name: $skill_name
description: Migration workflow skill for $skill_name
---

SKILL_HEADER
        cat "$skill_file" >> "$skill_dir/SKILL.md"
        
        echo "  ✓ Skill: $skill_name"
    done
else
    echo "  ⚠ No skills found in $SKILLS_DIR"
fi

# --- Generate .github/hooks/ native JSON ---

echo ""
echo "→ Generating .github/hooks/ (native hook JSON) ..."
mkdir -p "$TARGET_DIR/.github/hooks"

# Use parse-hooks.sh if available, otherwise generate manually
if [ -f "$PARSE_HOOKS" ] && [ -d "$HOOKS_DIR" ]; then
    bash "$PARSE_HOOKS" copilot "$HOOKS_DIR" app > "$TARGET_DIR/.github/hooks/migration-quality.json"
    echo "  ✓ Generated via parse-hooks.sh"
else
    # Generate native Copilot hooks JSON directly
    cat > "$TARGET_DIR/.github/hooks/migration-quality.json" << 'EOF'
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "bash": "if [[ \"$TOOL_NAME\" == \"edit\" && \"$FILE_PATH\" =~ /domain/ ]]; then if grep -q 'org\\.springframework\\|jakarta\\.' \"$FILE_PATH\" 2>/dev/null; then echo '{\"decision\": \"deny\", \"reason\": \"Domain layer cannot import Spring/Jakarta\"}'; exit 0; fi; fi",
        "timeoutSec": 5
      }
    ],
    "postToolUse": [
      {
        "type": "command",
        "bash": "if [[ \"$TOOL_NAME\" == \"edit\" && \"$FILE_PATH\" =~ \\.java$ ]]; then ./gradlew compileJava --quiet 2>/dev/null || true; fi",
        "timeoutSec": 30
      }
    ],
    "sessionStart": [
      {
        "type": "command",
        "bash": "echo \"Migration session started at $(date)\" >> .migration/session.log",
        "timeoutSec": 5
      }
    ],
    "sessionEnd": [
      {
        "type": "command",
        "bash": "echo \"Migration session ended at $(date)\" >> .migration/session.log",
        "timeoutSec": 5
      }
    ]
  }
}
EOF
    echo "  ✓ Generated: migration-quality.json (manual)"
fi

# Additional hooks for architecture validation
cat > "$TARGET_DIR/.github/hooks/architecture-guard.json" << 'EOF'
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "bash": "if [[ \"$TOOL_NAME\" == \"edit\" ]]; then case \"$FILE_PATH\" in */adapter/in/*) if grep -q 'import.*\\.adapter\\.out\\.' \"$FILE_PATH\" 2>/dev/null; then echo '{\"decision\": \"deny\", \"reason\": \"Inbound adapters cannot import outbound adapters\"}'; fi;; */adapter/out/*) if grep -q 'import.*\\.adapter\\.in\\.' \"$FILE_PATH\" 2>/dev/null; then echo '{\"decision\": \"deny\", \"reason\": \"Outbound adapters cannot import inbound adapters\"}'; fi;; esac; fi",
        "timeoutSec": 5
      }
    ]
  }
}
EOF
echo "  ✓ Generated: architecture-guard.json"

# Test companion hook
cat > "$TARGET_DIR/.github/hooks/test-companion.json" << 'EOF'
{
  "version": 1,
  "hooks": {
    "postToolUse": [
      {
        "type": "command",
        "bash": "if [[ \"$TOOL_NAME\" == \"create\" && \"$FILE_PATH\" =~ src/main/java/.*\\.java$ && ! \"$FILE_PATH\" =~ Test\\.java$ ]]; then TEST_PATH=$(echo \"$FILE_PATH\" | sed 's|src/main/java|src/test/java|' | sed 's|\\.java$|Test.java|'); if [ ! -f \"$TEST_PATH\" ]; then echo \"REMINDER: Create test companion at $TEST_PATH\"; fi; fi",
        "timeoutSec": 5
      }
    ]
  }
}
EOF
echo "  ✓ Generated: test-companion.json"

# --- Copy docs/ for full reference ---

echo ""
echo "→ Copying docs/ directory for reference ..."
mkdir -p "$TARGET_DIR/docs"
cp "$DOCS_DIR"/*.md "$TARGET_DIR/docs/" 2>/dev/null || true
if [ -d "$SKILLS_DIR" ]; then
    mkdir -p "$TARGET_DIR/docs/skills"
    cp "$SKILLS_DIR"/*.md "$TARGET_DIR/docs/skills/" 2>/dev/null || true
fi
if [ -d "$HOOKS_DIR" ]; then
    mkdir -p "$TARGET_DIR/docs/hooks"
    cp "$HOOKS_DIR"/*.md "$TARGET_DIR/docs/hooks/" 2>/dev/null || true
fi
echo "  ✓ All docs copied to $TARGET_DIR/docs/"

# --- Generate .github/copilot-workspace.json ---

echo ""
echo "→ Generating .github/copilot-workspace.json ..."

cat > "$TARGET_DIR/.github/copilot-workspace.json" << 'EOF'
{
  "name": "C++ to Java Migration",
  "description": "AI-augmented migration from C++ to Java 25 using structured workflows and quality gates",
  "instructions": ".github/copilot-instructions.md",
  "context": {
    "include": [
      ".github/instructions/**/*.md",
      ".github/skills/**/*.md",
      "docs/**/*.md",
      ".migration/**/*.md",
      ".migration/config.json"
    ],
    "exclude": [
      "source/**",
      "node_modules/**",
      "build/**",
      "target/**"
    ]
  }
}
EOF
echo "  ✓ copilot-workspace.json created"

echo ""
echo "═══════════════════════════════════════════════════"
echo "✓ GitHub Copilot 2026 installation complete!"
echo ""
echo "  Installed (native 2026 structure):"
echo "    .github/copilot-instructions.md    ← Repository-wide instructions"
echo "    .github/instructions/*.md          ← Path-specific instructions"
echo "    .github/skills/                    ← Agent skills (open standard)"
echo "    .github/hooks/*.json               ← Native Copilot hooks"
echo "    .github/copilot-workspace.json     ← Workspace context config"
echo "    docs/                              ← Full reference documentation"
echo ""
echo "  Native Features:"
echo "    • Path-specific instructions for domain/adapter/test layers"
echo "    • Agent skills for each migration workflow"
echo "    • Hook-based quality gates (preToolUse, postToolUse)"
echo "    • Architecture validation via hooks"
echo ""
echo "  Usage:"
echo "    Open project in VS Code/JetBrains with Copilot enabled."
echo "    Ask: \"run migrate-init on ./src\""
echo "═══════════════════════════════════════════════════"
