# AGENTS.md — ai-migration-framework

You are working on the framework itself — a portable knowledge base and installer
system that equips AI coding agents to migrate applications between programming languages.

This repo contains NO application code, NO build files, NO source projects. It contains
markdown documents, bash scripts, a Python template engine, and hook definitions.

Currently supported: C++ → Java 25. The architecture supports any language pair.

## Key Commands

- Run Kiro installer: `bash agents/kiro/install.sh /path/to/target`
- Run Claude installer: `bash agents/claude/install.sh /path/to/target`
- Run Codex installer: `bash agents/codex/install.sh /path/to/target`
- Validate the framework: `python3 agents/framework.py check`
- Compile templates: `bash agents/compile-templates.sh cpp-to-java-25 /tmp/migration-bundle`
- Test hook generation: `bash agents/parse-hooks.sh kiro /tmp/migration-bundle/hooks app`
- Test hook generation: `bash agents/parse-hooks.sh claude /tmp/migration-bundle/hooks app`
- Test hook generation: `bash agents/parse-hooks.sh codex /tmp/migration-bundle/hooks app`
- Validate JSON output: `bash agents/parse-hooks.sh kiro /tmp/migration-bundle/hooks app | python3 -m json.tool`
- Syntax check scripts: `bash -n agents/kiro/install.sh`

## Project Structure

```
docs/templates/            ← v1 compatibility variable definitions (variables.json)
docs/profiles/             ← Versioned source, target, pair, and output manifests
schemas/                   ← JSON Schemas for manifests, bundles, hooks, state, and fixtures
docs/standards/generic/    ← Language-agnostic standards (always included)
docs/standards/sources/    ← Source-language detection profiles (e.g., sources/cpp/)
docs/standards/targets/    ← Target-language standards (e.g., targets/java-25/)
docs/pairs/                ← Pair-specific guides (e.g., pairs/cpp-to-java-25/)
docs/skills/               ← Workflow procedures (templated, compiled per pair)
docs/hooks/                ← Quality hook definitions (templated, machine-parseable)
agents/compile-templates.sh ← Template compiler entry point
agents/compile-engine.py   ← Python variable substitution engine
agents/framework.py        ← Validator, compiler, managed installer, upgrade, state CLI
agents/parse-hooks.sh      ← Shared hook compiler (reads docs/hooks/, emits JSON)
agents/*/install.sh        ← Agent-specific installers
```

## What Each Installer Does

- **kiro**: Compiles templates for the selected pair. Reads docs/standards/ → adds YAML
  frontmatter → writes .kiro/steering/. Reads docs/skills/ → wraps with Kiro SKILL.md
  frontmatter → writes .kiro/skills/. Reads docs/hooks/ → generates .kiro/hooks/ JSON
  via parse-hooks.sh.
- **claude**: Compiles templates for the selected pair. Concatenates key standards into
  CLAUDE.md. Appends skills as workflow sections. Generates .claude/settings.json hooks
  via parse-hooks.sh.
- **codex**: Compiles templates for the selected pair. Copies docs/ (standards + skills)
  for auto-discovery. Generates .codex/hooks.json via parse-hooks.sh.

## Template Variables

Skills, hooks, and some standards use `{{double_brace}}` template variables that resolve
from the selected v2 source, target, pair, and output manifests. The typed canonical contract
is in `framework.json`. `docs/templates/variables.json` remains a v1 compatibility input only.

Example variables (C++ → Java 25):
- `{{source_language}}` → `C++`
- `{{target_language}}` → `Java 25`
- `{{target_build_tool}}` → `Gradle`
- `{{compile_command}}` → `./gradlew compileJava`
- `{{target_test_framework}}` → `JUnit 5 and AssertJ`
- `{{source_test_frameworks}}` → `GoogleTest, Catch2, doctest, Boost.Test`

The compile pipeline validates profile capabilities and schemas, merges variables in the
documented precedence order, invokes the strict template engine, validates all output, and
atomically promotes a checksum-manifested bundle.

## Editing Rules

### Standards — Generic (docs/standards/generic/*.md)
- Pure markdown. No agent-specific metadata. No language-specific content.
- These are included for ALL language pairs.

### Standards — Sources (docs/standards/sources/<lang>/*.md)
- Source-language detection profiles and idiom catalogs.
- May use `{{source_lang}}` template variables.

### Standards — Targets (docs/standards/targets/<lang>/*.md)
- Target-language architecture rules, tooling, and quality standards.
- May use `{{target_lang}}`, `{{build_tool}}`, `{{compile_command}}`, etc.
- Use `{target_root}` for the target project directory (default: ./app/).
- Use `{source_root}` for the source directory.

### Pair-Specific (docs/pairs/<src>-to-<tgt>/*.md)
- Guides specific to a source+target combination (translation examples, test porting).
- May use any template variable from the pair.

### Skills (docs/skills/*.md)
- One file per workflow command (migrate-init, migrate-analyze, etc.)
- Format: heading, description, When to Use, Inputs, Procedure, Outputs, Success Criteria.
- Write steps as numbered instructions any LLM can follow.
- Use `{{template_variables}}` for language-specific values.
- Never use slash-command syntax or agent-specific invocation patterns.

### Hooks (docs/hooks/*.md)
- Machine-parseable format. Each hook is a ## section with `- key: value` fields.
- Required fields: trigger, matcher, type, description, required, enforcement.
- For type=command: include `command` field (may use `{{compile_command}}` etc.).
- For type=agent: include `prompt` field.
- parse-hooks.sh reads this and emits agent-native JSON.

## Boundaries

### ✅ Always
- Edit any file in docs/
- Run installers against test directories
- Run parse-hooks.sh to verify output
- Run compile-templates.sh to verify variable substitution
- Add new language profiles in sources/, targets/, or pairs/

### ⚠️ Ask first
- Change installer logic (agents/*/install.sh)
- Change parse-hooks.sh or compile-templates.sh (shared by all agents)
- Change compile-engine.py (affects all template resolution)
- Add a new agent adapter

### 🚫 Never
- Put agent-specific syntax in docs/ files
- Hardcode paths (use {target_root}, {source_root})
- Put language-specific content in generic/ standards
- Generate docs from LLM — all content is human-curated
