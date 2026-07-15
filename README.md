# cpp-to-java-ai-framework

An opinionated AI-agent framework for migrating C++ applications to modern Java 25.

---

## What This Is

A structured knowledge base, workflow engine, and automated quality system that guides
AI coding agents through migrating C++ codebases to Java 25. The framework enforces
architectural standards, behavioral equivalence, and code quality at every step.

### Output Types

| Type | What it produces |
|------|-----------------|
| **Service** | Spring Boot 4.x with hexagonal architecture, full observability |
| **Library** | Plain JAR with api/internal/spi layering, module-info.java |
| **SDK** | Library + Javadoc + stability annotations + samples + binary compatibility |
| **CLI** | Picocli + GraalVM native image, stdout/stderr contracts, exit codes |

### Opinionated Core

This framework is not configuration-neutral. It adopts and enforces:

- **Java 25** — Records, sealed interfaces, virtual threads, pattern matching, scoped values
- **Hexagonal architecture** for services — domain purity enforced by ArchUnit
- **api/internal/spi layering** for libraries — module-info.java as hard API boundary
- **Behavioral equivalence** — migrated code must produce identical outputs for identical inputs
- **Test-first migration** — every translated file gets test coverage before moving on
- **Wave-based execution** — domain first, then ports, then services, then adapters
- **Automated quality hooks** — compile-on-save, domain purity checks, architecture direction validation

---

## Supported Agents

| Agent | Mechanism | Standards | Skills | Hooks |
|-------|-----------|-----------|--------|-------|
| **Kiro** | `.kiro/steering/` + `.kiro/skills/` + `.kiro/hooks/` | ✓ | ✓ (slash commands) | ✓ (native) |
| **Claude** | `CLAUDE.md` + `.claude/settings.json` | ✓ | ✓ (workflow sections) | ✓ (native) |
| **Codex** | `AGENTS.md` + `docs/` + `.codex/hooks.json` | ✓ | ✓ (auto-discovered) | ✓ (native) |

All three agents receive the same standards, workflows, and quality hooks — formatted
for each agent's native conventions. One source, three outputs.

---

## Quick Start

```bash
git clone <repo> cpp-to-java-ai-framework
cd cpp-to-java-ai-framework

# Interactive — asks which agent and target path
./install.sh
```

After installation, start the migration:

```
# Kiro
/migrate-init ./src

# Claude or Codex — just ask:
"run migrate-init on ./src"
```

---

## Project Structure

```
cpp-to-java-ai-framework/
├── docs/
│   ├── standards/              ← Architectural standards & rules
│   │   ├── migration-philosophy.md
│   │   ├── java-target-standards.md
│   │   ├── java-service-profile.md
│   │   ├── java-library-profile.md
│   │   ├── java-sdk-profile.md
│   │   ├── java-cli-profile.md
│   │   ├── gradle-version-catalog.md
│   │   ├── archunit-templates.md
│   │   ├── test-porting-guide.md
│   │   ├── translation-examples.md
│   │   ├── poc-validation-standards.md
│   │   └── migration-agents.md
│   ├── skills/                 ← Workflow procedures
│   │   ├── migrate-init.md
│   │   ├── migrate-analyze.md
│   │   ├── migrate-plan.md
│   │   ├── migrate-execute.md
│   │   ├── migrate-verify.md
│   │   ├── migrate-review.md
│   │   ├── migrate-detect.md
│   │   ├── migrate-map.md
│   │   └── migrate-resume.md
│   └── hooks/                  ← Quality automation definitions
│       └── migration-quality.md
├── agents/
│   ├── kiro/install.sh         ← Generates .kiro/ (steering + skills + hooks)
│   ├── claude/install.sh       ← Generates CLAUDE.md + .claude/settings.json
│   ├── codex/install.sh        ← Copies AGENTS.md + docs/ + .codex/hooks.json
│   └── parse-hooks.sh          ← Shared hook compiler (reads docs/hooks/, emits JSON)
├── install.sh                  ← Interactive installer
├── AGENTS.md                   ← Full usage guide
└── README.md
```

### Architecture

```
docs/                    ← Single source of truth (portable markdown)
  │
  ├── standards/         → becomes: steering files / CLAUDE.md sections / AGENTS.md context
  ├── skills/            → becomes: slash commands / workflow sections / auto-discovered docs
  └── hooks/             → becomes: .kiro/hooks/ JSON / .claude/settings.json / .codex/hooks.json
  │
agents/parse-hooks.sh    ← Shared compiler: reads portable hooks, emits agent-native JSON
agents/*/install.sh      ← Thin adapters: format docs/ for each agent's conventions
```

---

## Knowledge Base

| Document | Purpose |
|----------|---------|
| `migration-philosophy.md` | Iron laws, the migration ladder, behavioral equivalence |
| `java-target-standards.md` | Java 25 features, architecture rules, code quality |
| `java-service-profile.md` | Spring Boot 4.x service — hexagonal, observability, security |
| `java-library-profile.md` | Plain JAR — api/internal/spi, module-info.java, zero framework lock-in |
| `java-sdk-profile.md` | SDK — Javadoc, @Stable/@Beta/@Internal, binary compatibility, samples |
| `java-cli-profile.md` | CLI — picocli, exit codes, GraalVM, stdout/stderr contracts |
| `gradle-version-catalog.md` | libs.versions.toml templates per output type |
| `archunit-templates.md` | ArchUnit tests enforcing architectural boundaries |
| `test-porting-guide.md` | gtest/catch2/doctest → JUnit 5 + AssertJ mapping |
| `translation-examples.md` | Worked C++ → Java examples per output type |
| `poc-validation-standards.md` | Golden master comparison methodology |
| `migration-agents.md` | Specialized sub-agent role definitions |
| `migration-state-files.md` | `.migration/` directory structure, state.md schema, file naming convention |

---

## Workflows

| Command | Purpose |
|---------|---------|
| `migrate-init` | Scan source, detect tech, generate roadmap and project skeleton |
| `migrate-detect` | Detect C++ technologies, libraries, platform dependencies |
| `migrate-map` | Map C++ namespaces to Java packages |
| `migrate-analyze` | Deep-analyze a phase — data flow, patterns, risks |
| `migrate-plan` | Generate translation plans with wave ordering |
| `migrate-execute` | Execute translation with wave-based parallelism |
| `migrate-verify` | Verify semantic equivalence (C++ vs Java) |
| `migrate-review` | Two-pass code review — fidelity + minimalism |
| `migrate-resume` | Resume after session break or context compaction |

---

## Quality Hooks

Automated checks that run during migration, generated from `docs/hooks/migration-quality.md`:

| Hook | Trigger | What it does |
|------|---------|-------------|
| compile-on-save | File saved | Runs `gradlew compileJava` immediately |
| domain-purity-check | File created in domain/ | Rejects Spring/Jakarta imports in domain layer |
| architecture-direction-check | File saved in adapter/in/ | Validates dependency direction (no impl leaks) |
| test-companion-reminder | File created | Ensures test file exists for every production class |

Each agent receives these in its native hook format — no manual setup.

---

## How It Works

1. **You edit** `docs/` — standards, skills, or hooks
2. **You run** `./install.sh` (or `agents/<name>/install.sh /path/to/project`)
3. **The installer** reads `docs/`, transforms to the agent's native format, writes to target
4. **The agent** loads the generated files and follows the standards/workflows/hooks

The knowledge is the same everywhere. Only the packaging differs.

---

## Updating Projects

```bash
# Edit the source
vim docs/standards/java-library-profile.md

# Push to all your projects
./agents/kiro/install.sh /path/to/project-a
./agents/claude/install.sh /path/to/project-b
./agents/codex/install.sh /path/to/project-c
```

Installers are idempotent — safe to re-run anytime.

---

## Contributing

### Updating Standards or Skills

1. Edit the source in `docs/standards/`, `docs/skills/`, or `docs/hooks/`
2. Run the relevant installer to verify output
3. All changes propagate to every agent on next install

### Principles

- `docs/` is the single source of truth — never edit generated files
- Agent adapters are thin formatters, not content authors
- Hooks are compiled dynamically from `docs/hooks/` by `parse-hooks.sh`
- All standards apply equally regardless of which agent runs
