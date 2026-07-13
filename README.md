# AI Migration Framework

A portable, validated knowledge and installation framework for AI-assisted legacy
modernization. The reference capability is **C++ → Java 25**; the compiler and profile
contracts are language-pair neutral.

This repository is guidance-driven. It does not translate code or orchestrate deployments.
It gives an AI coding agent versioned standards, lifecycle workflows, evidence contracts,
quality hooks, and safe state/install semantics so a migration can be executed and audited.

Current framework version: `3.1.0`.

## Production-pilot scope

- strict profile composition and template compilation;
- service, library, SDK, and CLI output profiles;
- incremental replacement, coexistence, cutover, rollback, and decommission guidance;
- schema-valid migration state with end-to-end traceability;
- source-snapshot reconciliation and machine-generated completion certification;
- Kiro, Claude, and Codex packaging with explicit hook capability differences;
- deterministic bundles, managed upgrades, conflict detection, and transaction rollback;
- conformance fixtures and a realistic multi-module golden lifecycle.

The C++ → Java 25 guidance is production-pilot ready only after the release checklist's
automated and human review gates pass. Semantic fidelity and justified modernization still
require expert judgment.

## Quick start

Requirements: Bash and Python 3.11 or newer. The framework has no third-party runtime
dependencies.

```bash
# Validate schemas, profiles, templates, hooks, fixtures, and every composition
python3 agents/framework.py validate

# Run the full deterministic conformance suite
python3 agents/framework.py check

# See manifest-backed identifiers
python3 agents/framework.py list all
```

Preflight an installation before changing the target:

```bash
python3 agents/framework.py install \
  --pair cpp-to-java-25 \
  --output-profile service \
  --adapter codex \
  --target /path/to/project \
  --dry-run
```

Remove `--dry-run` to perform a fresh install. For an existing managed installation, first
preview a configuration-aware upgrade:

```bash
python3 agents/framework.py upgrade \
  --target /path/to/project \
  --dry-run
```

The upgrader reads the installed adapter, pair, output profile, and project overrides from
verified `.migration-framework/` metadata. Review the report, then run the same command
without `--dry-run`. It does not substitute current framework defaults for omitted installed
configuration.

Changing configuration is a separate, explicit operation. Supply the intended values and
`--reconfigure`, then preview again:

```bash
python3 agents/framework.py upgrade \
  --target /path/to/project \
  --output-profile library \
  --reconfigure \
  --dry-run
```

`--set KEY=VALUE` adds or replaces a project override; `--unset KEY` removes one. An active
migration crossing a framework major-version boundary additionally requires `--allow-major`
and an accepted `--decision DEC-NNNN` referenced by
`.migration/config.json` as `project_decisions.framework_upgrade`, with an approval reference.
The CLI checks that the reference exists; the update workflow verifies that it records human
review. The approval is required once when an active migration adopts the new major; later
updates within that installed major do not ask for it again. Terminal migrations are validated
but do not require cross-major approval. The dry-run explains when those flags are required.

`--force` is the only way to replace a reported collision or locally modified generated
file. When it is supplied, the dry-run's `forced_replacements` field lists the exact paths
that would be replaced. The operation stages and verifies every file before promotion and
rolls back if a promotion fails.

The interactive wrapper remains available for fresh installs, and upgrade mode does not
prompt again for installed configuration:

```bash
./install.sh
./install.sh --upgrade --target /path/to/project --dry-run
```

To install an already compiled artifact exactly, compile it for the adapter and pass the
verified bundle explicitly:

```bash
python3 agents/framework.py compile \
  --pair cpp-to-java-25 --output-profile service --adapter codex \
  --output /tmp/cpp-java-codex-bundle
python3 agents/framework.py install \
  --adapter codex --target /path/to/project \
  --bundle /tmp/cpp-java-codex-bundle --dry-run
```

## Compile a bundle

```bash
python3 agents/framework.py compile \
  --pair cpp-to-java-25 \
  --output-profile library \
  --adapter portable \
  --output /tmp/cpp-java-library-bundle
```

Compilation is strict and atomic. Unknown variables, malformed conditionals, missing or
cyclic includes, unsafe include paths, missing capabilities, and unresolved tokens are
fatal. Repeating the same compilation produces byte-identical files.

Compatibility forms are retained:

```bash
bash agents/compile-templates.sh cpp-to-java-25 /tmp/compiled
bash agents/compile-templates.sh cpp java25 docs/skills/migrate-init.md
```

The second form prints one compiled document and exists for valid v1 tooling. New tooling
should use `agents/framework.py compile`.

## Framework model

Composition has one fixed precedence order:

```text
generic core → source profile → target profile → pair profile → output profile → project decisions
```

Each layer has one responsibility:

| Layer | Owns |
|---|---|
| Generic | Discovery, characterization, incremental delivery, traceability, reversibility, evidence, and explicit decisions |
| Source | Detection, build/test variants, idioms, ownership, undefined behavior, platform and native hazards |
| Target | Toolchain capabilities, runtime compatibility, modules, build/test/static-analysis and dependency-integrity policy |
| Pair | Semantic mappings, dependency substitutions, interop risks, test porting, and equivalence policy |
| Output | Service, library, SDK, or CLI architecture and delivery contracts |
| Project | Explicit, scalar decisions for one migration; profile identity cannot be overridden |
| Adapter | Packaging and truthful capability declarations only |

The authoritative catalog is [framework.json](framework.json). Composable manifests live
under `docs/profiles/`, adapter capabilities under `agents/*/capabilities.json`, and formal
contracts under `schemas/`.

### Output profiles

| Profile | Default architecture | Additional contracts |
|---|---|---|
| `service` | Feature-oriented modular hexagonal | Network boundaries, composition roots, observability, deployability, rollback routing |
| `library` | API / internal / SPI | Consumer API, module exports, framework-free runtime, dependency exposure |
| `sdk` | API / internal / SPI | Library rules plus compatibility, documentation, examples, and consumer-contract gates |
| `cli` | Command core with boundary adapters | Arguments, stdin/stdout/stderr, exit codes, non-interactive behavior, packaging |

Hexagonal architecture is therefore a service profile rule, not a universal migration rule.
Within services, ports model capabilities, use cases own orchestration, adapters own I/O,
and wiring stays in an explicit composition root.

## Compiled bundle contract

```text
bundle/
├── manifest.json
├── standards/
│   ├── generic/
│   ├── source/
│   ├── target/
│   ├── pair/
│   ├── output/
│   └── output-target/
├── workflows/
├── hooks/
├── schemas/
├── state/templates/
├── bin/migrationctl.py
├── runtime.json
└── provenance/
```

`manifest.json` records the framework and bundle format versions, selected profiles,
adapter capabilities, resolved variables, source checksums, generated-file checksums, and
an aggregate digest. It intentionally contains no timestamp, so builds are reproducible.

## Safe installation and upgrades

An install writes framework-managed support files under `.migration-framework/` in the
target: the verified bundle manifest, schemas, blank state templates, provenance, the
installed `bin/migrationctl.py` validator, and `ownership.json` plus its checksum. The
ownership record contains only paths generated by this framework and their checksums.

This is not the live migration state. The migrate-init workflow separately creates
`.migration/`, the project-owned record that evolves during discovery, planning, execution,
verification, cutover, and decommissioning. Files under
`.migration-framework/state/templates/` are starting templates for that record, not active
state. The upgrader may validate `.migration/` for compatibility, but it never writes or
deletes anything there.

- Fresh install fails on existing `AGENTS.md`, `CLAUDE.md`, settings, hooks, or any other
  planned path unless replacement is explicitly forced.
- Upgrade infers omitted adapter, pair, output profile, and project overrides from verified
  ownership metadata. Any effective change requires `--reconfigure`.
- A v2 installation's non-default resolved values are retained as visible
  `legacy-inferred` overrides when its metadata is upgraded to v3.
- Invalid live migration state blocks an upgrade. A cross-major update with `.migration/`
  may be previewed, but applying it requires `--allow-major --decision DEC-NNNN` and a valid,
  accepted decision referenced by migration configuration with at least one approval reference.
  The portable update workflow confirms that the reference records human review; the CLI does
  not infer a reviewer's identity from an opaque reference.
- Upgrade changes only owned files. A local modification is a conflict, not an overwrite.
- Obsolete owned files are removed only when unchanged or explicitly forced.
- All writes are staged and checksum-verified. Existing files are journaled and restored
  if promotion fails.
- Symlink escapes and traversal paths are rejected.

Adapter wrappers remain available for direct installs and preserve their fixed adapter during
smart upgrades:

```bash
bash agents/kiro/install.sh /path/to/project
bash agents/claude/install.sh /path/to/project
bash agents/codex/install.sh /path/to/project
bash agents/codex/install.sh /path/to/project --upgrade --dry-run
```

An exact precompiled bundle may also be supplied to `upgrade`. Its effective configuration
must match the installation unless the command includes `--reconfigure`; bundle checksums and
digest are verified before any target file changes. Because the bundle already contains its
exact profiles and overrides, `--bundle` cannot be combined with `--pair`, `--output-profile`,
`--set`, or `--unset`.

The portable [migrate-framework-update workflow](docs/skills/migrate-framework-update.md)
covers source trust, validation, dry-run review, explicit approval, major-version policy, and
post-upgrade proof that `.migration/` was not changed.

## Hook capabilities

Portable hooks distinguish reproducible command enforcement from LLM judgment. The
compiler never turns an unsupported judgment hook into a pretend command.

| Adapter | Command hooks | Judgment hooks | File events |
|---|---|---|---|
| Kiro | Native | Native | Native |
| Claude | Native | Native, adapter-declared stability | Tool-event approximation for file lifecycle events |
| Codex | Native | Explicit review instructions | Tool-event approximation for file lifecycle events |

Normal mode emits machine-readable warnings/instructions for non-equivalent semantics.
`--strict-hooks` fails whenever the selected adapter cannot provide an exact native mapping.
Capability evidence and activation requirements are recorded in each adapter manifest.

Hook definitions remain portable Markdown. Compile them before invoking the low-level
adapter parser:

```bash
bash agents/compile-templates.sh cpp-to-java-25 /tmp/migration-hooks
bash agents/parse-hooks.sh kiro /tmp/migration-hooks/hooks app | python3 -m json.tool
bash agents/parse-hooks.sh claude /tmp/migration-hooks/hooks app | python3 -m json.tool
bash agents/parse-hooks.sh codex /tmp/migration-hooks/hooks app | python3 -m json.tool
```

## Migration lifecycle and state

The versioned lifecycle is:

```text
initialize → discover → characterize → map → plan → execute → verify → review
           → approve → cut_over → decommissioned
```

Every active state can enter `blocked` or `failed` and resume only to its recorded state.
Use the installed directory-aware transition command instead of editing status fields by
hand. State-only cutover and decommission transitions are forbidden:

```bash
cd /path/to/project
python3 .migration-framework/bin/migrationctl.py transition \
  --migration .migration \
  --to discover \
  --reason "Initialization evidence accepted"
```

`.migration/` separates concerns into schema-valid artifacts:

- `config.json` — profile selection, strategy, roots, project decisions, validation status;
- `scope.json` — completion policy, frozen source census, and per-source disposition;
- `state.json` — revisioned current state and complete transition history;
- `inventory.json` — stable source-unit IDs, reachability, dependencies, behaviors, risks;
- `target-inventory.json` — concrete target and test IDs, paths, states, and checksums;
- `behaviors/*.json` — characterized observable contracts and known gaps;
- `decisions/*.json` — accepted or rejected intentional choices;
- `plans/*.json` — independently releasable dependency-seam slices and rollback;
- `traceability.json` — source → behavior → target → test → decision/exception → evidence;
- `evidence/*.json` — exact commands, environment, artifacts, and deterministic gate results;
- `exceptions/*.json` — approved dead code, intentional divergence, unspecified behavior,
  unsupported dependency/platform, or quality-gate exceptions.
- `completion-certificate.json` — generated whole-scope proof for one exact artifact and
  workspace snapshot; never an agent-authored assertion.

Validate the populated graph, refresh the source snapshot, and inspect strict migration
readiness:

```bash
python3 .migration-framework/bin/migrationctl.py validate .migration
python3 .migration-framework/bin/migrationctl.py snapshot .migration --project-root .
python3 .migration-framework/bin/migrationctl.py audit .migration --claim migrated
```

Structural validation and slice approval are not completion claims. `accounted` certification
allows only policy-approved non-target dispositions and reports them separately; strict
`migrated` certification requires zero pending, unknown, retained, removed, or unverified
scope. Final cutover and decommission require fresh implementation and decommission-stage
certificates respectively. The implementation-stage certificate proves whole-scope target
implementation, verification, and approval; only the decommission-stage certificate also proves
completed cutover authority and legacy-asset closure.

Translation cannot begin until characterization evidence exists. Source tests are preferred;
golden-master or differential tests, public API inventories, observable side effects, and
known gaps fill the contract where source tests are absent. Verification records reproducible
gate evidence. Review performs semantic and idiomatic judgment without duplicating those gates.

## Quality policy

Slice quality uses profile-configured gates rather than a universal coverage percentage or
one-test-per-method rule. Gates may combine behavioral-contract coverage, changed-code
coverage, build/tests, architecture, static analysis, dependency analysis and integrity,
public API compatibility, documentation/examples, packaging, and human approval.

Whole-scope completeness is separate: the runtime reconciles the declared source census,
source dispositions, concrete target/test inventory, plans, evidence, and lifecycle state.
Passing tests are necessary evidence for covered behavior, not proof that omitted legacy work
does not exist.

For Java/Gradle projects, catalogs centralize requested coordinates but do not enforce the
resolved graph; use platforms or constraints for alignment, locking where reproducibility
requires it, and reviewed dependency verification metadata for integrity. See the official
[Gradle version catalog](https://docs.gradle.org/current/userguide/version_catalogs.html) and
[dependency verification](https://docs.gradle.org/current/userguide/dependency_verification.html)
guidance.

Java 25 migrations must inventory removed APIs/tools, runtime and charset differences,
modules, supported versus preview features, and deployment-platform compatibility. The
target profile records the review source in Oracle's
[JDK 25 migration guide](https://docs.oracle.com/en/java/javase/25/migrate/getting-started.html).

Incremental modernization is the default. The framework's seams, coexistence, routing,
rollback, and decommission rules follow the gradual replacement rationale of the
[Strangler Fig pattern](https://martinfowler.com/bliki/StranglerFigApplication.html).

## Extending the framework

Adding a language pair does not require changing the compiler:

1. Add a source manifest and source standards under `docs/profiles/sources/<id>/` and
   `docs/standards/sources/<id>/`.
2. Add a target manifest and target standards under `docs/profiles/targets/<id>/` and
   `docs/standards/targets/<id>/`.
3. Add a pair manifest and semantic guides under `docs/profiles/pairs/<source>-to-<target>/`
   and `docs/pairs/<source>-to-<target>/`.
4. Add target-specific documents for every supported output profile.
5. Declare every provided and required capability and every scalar template variable.
6. Run `python3 agents/framework.py check`.

Valid v1 `docs/templates/variables.json` data remains loadable. `build_command` is accepted
only by that compatibility loader and is normalized to canonical `compile_command`; v2
documents and manifests may not use the deprecated alias.

## Repository layout

```text
framework.json                 Versioned framework catalog and lifecycle
schemas/                       JSON Schemas for profiles, bundles, hooks, state, and fixtures
docs/profiles/                 Source, target, pair, and output manifests
docs/standards/                Generic/source/target knowledge
docs/pairs/                    Pair-specific mappings and examples
docs/output-profiles/          Language-neutral output contracts
docs/skills/                   Portable lifecycle workflows
docs/hooks/                    Portable hook definitions
docs/state/templates/          Valid artifact starting points
docs/provenance/               Rule metadata contract
agents/framework.py            Validator, compiler, installer, upgrade and state CLI
agents/migration_runtime.py    Installed whole-scope validator and certificate CLI
agents/compile-engine.py       Strict template engine
agents/parse-hooks.sh          Capability-aware hook compiler
agents/*/install.sh            Thin compatibility wrappers
fixtures/                      Descriptor matrix and golden expected state
tests/                         Unit, security, determinism and conformance tests
```

Release compatibility rules are in
[semantic-versioning.md](docs/release/semantic-versioning.md); production-pilot release
criteria are in [checklist.md](docs/release/checklist.md).
