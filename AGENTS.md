# AGENTS.md — cpp-to-java-ai-framework

You are working on the framework itself — a portable knowledge base and installer
system that equips AI coding agents to migrate C++ applications to Java 25.

This repo contains NO Java code, NO Gradle, NO C++ source. It contains markdown
documents, bash scripts, and hook definitions.

## Key Commands

- Run Kiro installer: `bash agents/kiro/install.sh /path/to/target`
- Run Claude installer: `bash agents/claude/install.sh /path/to/target`
- Run Codex installer: `bash agents/codex/install.sh /path/to/target`
- Test hook generation: `bash agents/parse-hooks.sh kiro docs/hooks app`
- Test hook generation: `bash agents/parse-hooks.sh claude docs/hooks app`
- Test hook generation: `bash agents/parse-hooks.sh codex docs/hooks app`
- Validate JSON output: `bash agents/parse-hooks.sh kiro docs/hooks app | python3 -m json.tool`
- Syntax check scripts: `bash -n agents/kiro/install.sh`

## Project Structure

```
docs/standards/    ← Architectural standards (the knowledge)
docs/skills/       ← Workflow procedures (step-by-step migration guides)
docs/hooks/        ← Quality hook definitions (portable, machine-parseable)
agents/            ← Agent-specific installers + shared hook compiler
```

## What Each Installer Does

- **kiro**: Reads docs/standards/ → adds YAML frontmatter → writes .kiro/steering/.
  Reads docs/skills/ → wraps with Kiro SKILL.md frontmatter → writes .kiro/skills/.
  Reads docs/hooks/ → generates .kiro/hooks/ JSON via parse-hooks.sh.
- **claude**: Concatenates key standards into CLAUDE.md. Appends skills as workflow
  sections. Generates .claude/settings.json hooks via parse-hooks.sh.
- **codex**: Copies docs/ (standards + skills) for auto-discovery.
  Generates .codex/hooks.json via parse-hooks.sh.

## Editing Rules

### Standards (docs/standards/*.md)
- Pure markdown. No agent-specific metadata.
- Use `{target_root}` for the Java project directory (default: ./app/).
- Use `{source_root}` for the C++ source directory.
- Never reference .kiro/, CLAUDE.md, or .codex/ in portable docs.

### Skills (docs/skills/*.md)
- One file per workflow command (migrate-init, migrate-analyze, etc.)
- Format: heading, description, When to Use, Inputs, Procedure, Outputs, Success Criteria.
- Write steps as numbered instructions any LLM can follow.
- Never use slash-command syntax or agent-specific invocation patterns.

### Hooks (docs/hooks/*.md)
- Machine-parseable format. Each hook is a ## section with `- key: value` fields.
- Required fields: trigger, matcher, type, description.
- For type=command: include `command` field.
- For type=agent: include `prompt` field.
- parse-hooks.sh reads this and emits agent-native JSON.

## Boundaries

### ✅ Always
- Edit any file in docs/
- Run installers against test directories
- Run parse-hooks.sh to verify output

### ⚠️ Ask first
- Change installer logic (agents/*/install.sh)
- Change parse-hooks.sh (shared by all agents)
- Add a new agent adapter

### 🚫 Never
- Put agent-specific syntax in docs/ files
- Hardcode paths (use {target_root}, {source_root})
- Generate docs from LLM — all content is human-curated
