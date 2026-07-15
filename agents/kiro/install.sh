#!/bin/bash
set -euo pipefail

# Kiro Agent Installer — C++ to Java Migration Toolkit
# Installs steering files (with Kiro frontmatter), skills, and hooks into target project.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║  Kiro Agent — C++ to Java Migration Toolkit     ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Toolkit:  $TOOLKIT_DIR"
echo "Target:   $TARGET_DIR"
echo ""

# --- Install steering files with Kiro frontmatter ---

STEERING_DIR="$TARGET_DIR/.kiro/steering"
mkdir -p "$STEERING_DIR"
echo "→ Creating .kiro/steering/ ..."

# Frontmatter definitions per file (name, description, inclusion)
declare -A FM_NAME FM_DESC FM_INCLUSION

FM_NAME[migration-philosophy]="migration-philosophy"
FM_DESC[migration-philosophy]="C++ to Spring Boot Migration Philosophy"
FM_INCLUSION[migration-philosophy]="always"

FM_NAME[java-target-standards]="java-target-standards"
FM_DESC[java-target-standards]="Target Java 25 Standards"
FM_INCLUSION[java-target-standards]="always"

FM_NAME[migration-agents]="migration-agents"
FM_DESC[migration-agents]="Migration Agent Definitions"
FM_INCLUSION[migration-agents]="always"

FM_NAME[java-service-profile]="java-service-profile"
FM_DESC[java-service-profile]="Spring Boot 4.x service standards — controllers, observability, security, application.yml. Use when output_type is service or when generating REST/gRPC endpoints, Spring Boot configuration, or service adapters."
FM_INCLUSION[java-service-profile]="auto"

FM_NAME[java-library-profile]="java-library-profile"
FM_DESC[java-library-profile]="Plain JAR library standards — module-info.java, java-library plugin, api/internal/spi layering, no Spring Boot in production code. Use when output_type is library or when generating library code, public API interfaces, or SPI contracts."
FM_INCLUSION[java-library-profile]="auto"

FM_NAME[java-sdk-profile]="java-sdk-profile"
FM_DESC[java-sdk-profile]="SDK standards — comprehensive Javadoc, stability annotations, binary compatibility, samples directory, consumer empathy. Use when output_type is sdk or when generating published API documentation, stability markers, or developer-facing libraries."
FM_INCLUSION[java-sdk-profile]="auto"

FM_NAME[java-cli-profile]="java-cli-profile"
FM_DESC[java-cli-profile]="CLI tool standards — picocli commands, exit codes, GraalVM native image, stdout/stderr conventions, composability. Use when output_type is cli or when generating command-line interfaces, argument parsers, or CLI adapters."
FM_INCLUSION[java-cli-profile]="auto"

FM_NAME[gradle-version-catalog]="gradle-version-catalog"
FM_DESC[gradle-version-catalog]="Gradle version catalog (libs.versions.toml) templates per output type. Use when generating the project skeleton, adding dependencies, or configuring the build system."
FM_INCLUSION[gradle-version-catalog]="auto"

FM_NAME[archunit-templates]="archunit-templates"
FM_DESC[archunit-templates]="ArchUnit test templates for hexagonal architecture enforcement. Use when generating the project skeleton, creating architecture tests, or verifying hexagonal boundaries."
FM_INCLUSION[archunit-templates]="auto"

FM_NAME[test-porting-guide]="test-porting-guide"
FM_DESC[test-porting-guide]="C++ test framework (gtest, catch2, doctest) to JUnit 5 + AssertJ translation guide. Use when porting C++ tests to Java, writing test code, or translating test assertions."
FM_INCLUSION[test-porting-guide]="auto"

FM_NAME[translation-examples]="translation-examples"
FM_DESC[translation-examples]="Worked C++ to Java translation examples per output type. Use when executing translation plans, writing Java code from C++ source, or when the translator agent needs concrete before/after references."
FM_INCLUSION[translation-examples]="auto"

FM_NAME[poc-validation-standards]="poc-validation-standards"
FM_DESC[poc-validation-standards]="PoC validation methodology — Golden Master comparison, functional equivalence criteria, ZOT variant selection. Use when running golden master tests, validating PoC criteria, or comparing C++ vs Java outputs."
FM_INCLUSION[poc-validation-standards]="auto"

DOCS_DIR="$TOOLKIT_DIR/docs/standards"

for file in migration-philosophy java-target-standards java-service-profile java-library-profile java-sdk-profile java-cli-profile gradle-version-catalog archunit-templates test-porting-guide translation-examples poc-validation-standards migration-agents; do
    src="$DOCS_DIR/${file}.md"
    dst="$STEERING_DIR/${file}.md"

    if [ ! -f "$src" ]; then
        echo "  ⚠ WARNING: $src not found, skipping"
        continue
    fi

    inclusion="${FM_INCLUSION[$file]}"
    name="${FM_NAME[$file]}"
    desc="${FM_DESC[$file]}"

    # Write frontmatter + content
    {
        echo "---"
        echo "inclusion: $inclusion"
        echo "name: $name"
        echo "description: $desc"
        echo "---"
        echo ""
        cat "$src"
    } > "$dst"

    echo "  ✓ $file.md (inclusion: $inclusion)"
done

# --- Generate skills from docs/skills/ ---

SKILLS_DOCS="$TOOLKIT_DIR/docs/skills"
if [ -d "$SKILLS_DOCS" ]; then
    echo ""
    echo "→ Generating .kiro/skills/ ..."

    # Kiro-specific metadata per skill
    declare -A SK_HINT SK_EFFORT SK_TOOLS
    SK_HINT[migrate-init]='<path-to-cpp-source> [--auto] [--poc]'
    SK_HINT[migrate-detect]='[path] [--deep] [--refresh]'
    SK_HINT[migrate-analyze]='<phase-number> [--focus memory|concurrency|io|api|all]'
    SK_HINT[migrate-plan]='<phase-number> [--strategy conservative|modern|hybrid]'
    SK_HINT[migrate-execute]='<phase-number> [--wave N] [--interactive] [--dry-run]'
    SK_HINT[migrate-verify]='<phase-number> [--deep] [--report-only]'
    SK_HINT[migrate-review]='<phase-number> [--scope diff|full] [--fix]'
    SK_HINT[migrate-map]='[--refresh] [--style hexagonal|modular-hexagonal]'
    SK_HINT[migrate-resume]=''
    SK_HINT[migrate-golden-master]='<test-data-path> [--variants all|<list>] [--tolerance strict|numeric-epsilon]'
    SK_HINT[migrate-validate-poc]='[--criteria all|1|2|3|4|5|6] [--report-only]'

    SK_EFFORT[migrate-init]='max'
    SK_EFFORT[migrate-detect]=''
    SK_EFFORT[migrate-analyze]='max'
    SK_EFFORT[migrate-plan]='max'
    SK_EFFORT[migrate-execute]='max'
    SK_EFFORT[migrate-verify]='max'
    SK_EFFORT[migrate-review]=''
    SK_EFFORT[migrate-map]=''
    SK_EFFORT[migrate-resume]=''
    SK_EFFORT[migrate-golden-master]='max'
    SK_EFFORT[migrate-validate-poc]='max'

    SK_TOOLS[migrate-init]='Read, Write, Bash, Glob, Grep, Agent, AskUserQuestion'
    SK_TOOLS[migrate-detect]='Read, Bash, Glob, Grep, Write'
    SK_TOOLS[migrate-analyze]='Read, Bash, Glob, Grep, Agent, Write'
    SK_TOOLS[migrate-plan]='Read, Write, Agent, AskUserQuestion, Glob, Grep'
    SK_TOOLS[migrate-execute]='Read, Write, Edit, Bash, Glob, Grep'
    SK_TOOLS[migrate-verify]='Read, Bash, Glob, Grep, Agent, Write'
    SK_TOOLS[migrate-review]='Read, Bash, Glob, Grep, Agent, Write, AskUserQuestion'
    SK_TOOLS[migrate-map]='Read, Write, Glob, Grep, Agent'
    SK_TOOLS[migrate-resume]='Read, Write, Bash'
    SK_TOOLS[migrate-golden-master]='Read, Write, Bash, Glob, Grep, Agent'
    SK_TOOLS[migrate-validate-poc]='Read, Write, Bash, Glob, Grep, Agent'

    skill_count=0
    for skill_file in "$SKILLS_DOCS"/*.md; do
        skill_name="$(basename "$skill_file" .md)"
        skill_dir="$TARGET_DIR/.kiro/skills/$skill_name"
        mkdir -p "$skill_dir"

        # Extract first line after heading as description
        desc=$(sed -n '3p' "$skill_file" | head -c 200)

        hint="${SK_HINT[$skill_name]:-}"
        effort="${SK_EFFORT[$skill_name]:-}"
        tools="${SK_TOOLS[$skill_name]:-Read, Write, Bash, Glob, Grep}"

        # Generate SKILL.md with Kiro frontmatter + portable content
        {
            echo "---"
            echo "name: $skill_name"
            echo "description: \"$desc\""
            [ -n "$hint" ] && echo "argument-hint: \"$hint\""
            [ -n "$effort" ] && echo "effort: $effort"
            echo "allowed-tools:"
            IFS=',' read -ra tool_arr <<< "$tools"
            for t in "${tool_arr[@]}"; do
                echo "  - $(echo "$t" | xargs)"
            done
            echo "---"
            echo ""
            cat "$skill_file"
        } > "$skill_dir/SKILL.md"

        skill_count=$((skill_count + 1))
    done
    echo "  ✓ Generated $skill_count skills from docs/skills/"
else
    echo "  ⚠ No docs/skills/ found in toolkit"
fi

# --- Generate hooks ---

HOOKS_DOCS="$TOOLKIT_DIR/docs/hooks"
if [ -d "$HOOKS_DOCS" ] && ls "$HOOKS_DOCS"/*.md >/dev/null 2>&1; then
    echo ""
    echo "→ Generating .kiro/hooks/ ..."
    mkdir -p "$TARGET_DIR/.kiro/hooks"
    bash "$TOOLKIT_DIR/agents/parse-hooks.sh" kiro "$HOOKS_DOCS" app \
        > "$TARGET_DIR/.kiro/hooks/migration-quality.json"
    echo "  ✓ Hooks generated (migration-quality.json)"
else
    echo "  ⚠ No docs/hooks/ found in toolkit"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "✓ Kiro installation complete!"
echo "  Open the target project in Kiro to begin."
echo "  Steering files auto-load based on inclusion rules."
echo "═══════════════════════════════════════════════════"
