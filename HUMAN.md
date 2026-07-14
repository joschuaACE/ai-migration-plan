# How the Framework Works

This framework is a compiler and installer for an AI migration handbook.
It does not translate application code itself. It equips an AI coding agent with the right
rules, workflows, checks, and record-keeping system to perform a migration safely.

For a quick reference while reading, see the [framework legend](LEGEND.md).

## The Overall Flow

```text
Choose migration profiles
        ↓
Assemble and validate the guidance
        ↓
Compile a reproducible bundle
        ↓
Package it for Codex, Claude, or Kiro
        ↓
Install it in the application repository
        ↓
The AI agent executes an evidence-backed migration
```

## 1. Profiles Describe the Migration

The framework builds its handbook from several layers:

- **Generic rules:** Discover before translating, preserve observable behavior, work
  incrementally, keep rollback possible, and record evidence.
- **Source profile:** Knowledge about the old language. The C++ profile knows about headers,
  build systems, test frameworks, ownership, undefined behavior, native boundaries, and
  similar hazards.
- **Target profile:** Knowledge about the new language. The Java 25 profile supplies Gradle,
  JUnit, compilation, testing, coverage, architecture, and static-analysis commands.
- **Pair profile:** Knowledge specific to C++ → Java, such as translating RAII, ownership,
  concurrency, libraries, tests, and numeric behavior.
- **Output profile:** Whether the result is a service, library, SDK, or CLI. A service gets
  Spring Boot and modular hexagonal guidance; a library does not.
- **Project decisions:** Explicit last-mile choices for a particular migration.

The framework verifies that these profiles are compatible. For example, a service profile
can require architecture validation, and compilation fails if the selected target cannot
provide it. The main contract lives in [`framework.json`](framework.json).

## 2. The Compiler Specializes the Handbook

Suppose you select:

```text
C++ → Java 25
Output: service
Agent: Codex
```

The compiler gathers the relevant Markdown documents and replaces values such as:

```text
{{source_language}}       → C++
{{target_language}}       → Java 25
{{compile_command}}       → ./gradlew compileJava
{{target_test_framework}} → JUnit 5 and AssertJ
```

It also removes irrelevant conditional sections. Service instructions remain; library, SDK,
and CLI branches disappear.

The result is a portable bundle containing standards, workflows, hooks, schemas, state
templates, provenance, and the installed whole-scope validator. Every input and output receives
a checksum, and the bundle gets
an aggregate digest. Identical inputs produce identical bundles. Compilation happens in a
staging directory and is promoted atomically only after it succeeds. This is implemented in
[`agents/framework.py`](agents/framework.py).

## 3. An Adapter Packages It for the Chosen Agent

The underlying knowledge remains agent-neutral, but each coding agent expects a different
layout:

- **Codex** receives `AGENTS.md`, `docs/standards/`, `docs/skills/`, and
  `.codex/hooks.json`.
- **Claude** receives a combined `CLAUDE.md` and `.claude/settings.json`.
- **Kiro** receives steering documents, individual `SKILL.md` workflows, and Kiro hook
  definitions.

Hooks are translated honestly. A compile-on-save hook can become an executable command. A
judgment hook such as "review this domain class for framework leakage" may be native on one
agent but only a written review instruction on another. The framework never pretends an
unsupported AI judgment is a deterministic command.

## 4. The Installed Agent Follows a Controlled Migration Lifecycle

Once installed in a real application repository, the AI follows the portable workflows:

```text
initialize → discover → characterize → map → plan → execute
           → verify → review → approve → cut_over → decommissioned
```

In practical terms:

- **Discover** inventories the real source system, including build variants and
  dependencies.
- **Characterize** records what the old application actually does.
- **Map** designs corresponding target units and tests without writing code yet.
- **Plan** divides the migration into small, independently reversible slices.
- **Execute** implements one approved slice while keeping the legacy path available.
- **Verify** runs reproducible commands: build, tests, architecture checks, coverage,
  linting, dependency checks, and behavioral comparisons.
- **Review** uses human or AI judgment to assess semantic fidelity, target-language quality,
  and justified modernization.
- **Cut over** moves an approved scope to the new implementation.
- **Decommission** removes the old path only after observation, recovery, and final approval
  requirements are satisfied.

The workflows themselves live under [`docs/skills/`](docs/skills/).

## 5. The Migrated Application Stays Inside Its Target Root

`target_root` is a real filesystem and command boundary, not just the folder for source code.
If `.migration/config.json` says `"target_root": "./app/"`, the target build belongs in
`app/`: its source and tests, build files, build launcher or wrapper, dependency metadata,
local caches, reports, and packaged output. Target commands run as `cd app && <command>`.

For Java/Gradle, that means `settings.gradle.kts`, `build.gradle.kts`, `gradlew`, `gradle/`,
`.gradle/`, and `build/` stay under `app/` by default. The agent must not make the repository
root a Gradle multi-project build merely to include `app`. A real shared-root orchestrator is
allowed only through an accepted project decision that records its paths, ownership,
commands, and rollback.

## 6. The Two Hidden Directories Have Different Jobs

The similar names are intentional:

| Directory | Managed by | Purpose |
|---|---|---|
| `.migration-framework/` | The framework installer and upgrader | Installed support files: ownership checksums, bundle manifest, schemas, blank state templates, provenance, and the runnable migration validator |
| `.migration/` | The migration workflows for this project | Live migration state: configuration, scope snapshot, source/target inventories, decisions, plans, evidence, traceability, lifecycle history, and generated completion certificate |

The installer creates `.migration-framework/`. The migrate-init workflow later creates
`.migration/`. In particular, `.migration-framework/state/templates/` contains starting
templates; it is not where active migration state is stored. Managed upgrades may replace
framework support files, but they do not own or overwrite `.migration/`.

### `.migration/` Acts as the Project's Flight Recorder

The AI does not mark work complete merely because files appeared. It records structured
artifacts such as:

- source inventory;
- a checksummed source census and explicit source dispositions;
- observable behavioral contracts;
- concrete target/test inventory and mappings;
- accepted decisions and exceptions;
- migration slice plans;
- test and command evidence;
- source-to-target traceability; and
- lifecycle state and complete transition history; and
- separate accounted-versus-migrated completion counts.

These files have stable IDs such as `SRC-0001`, `BEH-0001`, `SLICE-0001`, and `EVID-0001`.
JSON Schemas and cross-reference validation catch missing evidence, invalid transitions,
dangling references, plan cycles, or unapproved exceptions. The installed validator additionally
reconciles the workspace and refuses final cutover or decommission without a fresh generated
certificate. A clean build or an approved slice cannot create that certificate by itself.

## 7. Installation and Upgrades Protect User Work

The installer records exactly which files it owns and their checksums. During an upgrade:

- unchanged owned files may be replaced;
- locally edited files become conflicts;
- unrelated files are left alone;
- obsolete owned files are removed only when safe;
- `--dry-run` reports the proposed changes;
- `--force` is required to overwrite conflicts, and `forced_replacements` lists their exact
  paths in the report; and
- a failed promotion restores the previous files.

### Updating the Installed Handbook

Run upgrades from a trusted framework checkout. The normal update is deliberately short:

```bash
python3 agents/framework.py check
python3 agents/framework.py upgrade --target /path/to/project --dry-run
```

The second command reads the installed agent adapter, migration pair, output profile, and
project overrides from checksum-verified `.migration-framework/` metadata. It does not ask
you to remember the original options, and it does not silently replace them with today's
defaults. Review the dry-run, then repeat that exact command without `--dry-run`.

The root wrapper provides the same non-interactive upgrade path:

```bash
./install.sh --upgrade --target /path/to/project --dry-run
```

If you really intend to change the configuration, say so with `--reconfigure` and provide
the new adapter, pair, output profile, or override. Use `--set KEY=VALUE` to add or replace an
override and `--unset KEY` to remove one. A precompiled bundle follows the same rule: a
configuration-changing bundle is rejected unless the change is explicit. The bundle already
contains its profiles and overrides, so it cannot be combined with `--pair`,
`--output-profile`, `--set`, or `--unset`.

Older v2 installations did not record overrides separately. During their first v3 upgrade,
the framework compares their resolved values with current defaults and preserves differences
as visible `legacy-inferred` overrides. Removed or type-incompatible values stop the upgrade
instead of being guessed.

If `.migration/` exists, the upgrader validates it but never edits it. A move to a new major
framework version may be previewed, but applying it requires both `--allow-major` and
`--decision DEC-NNNN`. That decision must already be accepted, referenced by the migration
configuration as `project_decisions.framework_upgrade`, and contain an approval reference.
The CLI checks that a reference exists; the portable update workflow confirms that it records
human review. This is a one-time gate for an active migration adopting a new installed major;
same-major follow-up updates and terminal migrations do not repeat it. The
[`migrate-framework-update`](docs/skills/migrate-framework-update.md) workflow walks through
the trust check, dry-run, approval, update, and final proof that `.migration/` stayed
unchanged.

The essential idea is:

> Take curated migration knowledge, specialize it for a language pair and product type,
> install it in the chosen AI agent's native format, and make the agent migrate in small,
> traceable, reversible steps instead of performing a blind rewrite.
