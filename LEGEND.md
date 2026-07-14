# Framework Legend

This is the reading key for the AI Migration Framework. It explains the concepts,
identifiers, placeholders, and symbols used across the repository and in compiled migration
bundles. It is explanatory rather than normative: when this legend and a machine contract
disagree, [`framework.json`](framework.json) and the applicable file under [`schemas/`](schemas/)
are authoritative.

## The System at a Glance

```text
curated standards + workflows + profiles
                    │ compose and compile
                    ▼
          verified portable bundle
                    │ package through an adapter
                    ▼
     agent-native files + .migration-framework/
                    │ run migration workflows
                    ▼
              live .migration/ state

source units → behavioral contracts → target units + tests → evidence → approval
                                                                    │
                                                                    ▼
                                                        cutover → decommission
```

The framework does not translate an application by itself. It compiles and installs a
specialized handbook, schemas, checks, and state tooling that an AI coding agent uses while
migrating a separate application repository.

## Framework Concepts

| Term | Meaning |
|---|---|
| **Framework** | This repository: the portable knowledge base, compiler, schemas, validators, installers, and adapter definitions. |
| **Standard** | Curated guidance or a rule that applies to a migration. Generic standards apply to every language pair; source and target standards add language-specific policy. |
| **Workflow / skill** | An agent-neutral, ordered migration procedure such as discover, plan, verify, or cut over. A skill describes work; it is not an application source file or an automatic proof of completion. |
| **Profile** | A versioned manifest that contributes documents, capabilities, and typed template values for one composition layer. |
| **Source profile** | Knowledge about the language and ecosystem being migrated from. |
| **Target profile** | Knowledge about the language, runtime, build, test, and tooling ecosystem being migrated to. |
| **Pair profile** | Rules that exist only because a particular source and target are combined, such as semantic mappings and dependency substitutions. |
| **Output profile** | The delivery contract of the result: `service`, `library`, `sdk`, or `cli`. It determines architecture and product-specific quality gates. |
| **Project decision** | An explicit last-mile choice for one migration. It may refine permitted configuration, but it cannot change profile identity or silently weaken framework invariants. |
| **Composition** | The validated merge of the selected profile layers and project decisions into one complete set of values and documents. |
| **Capability** | A named feature that a profile or adapter provides or requires. Composition fails when selected profiles cannot satisfy a required capability. |
| **Manifest** | A versioned machine-readable catalog. Qualify the term: `framework.json` catalogs the framework, `profile.json` describes a composition layer, `capabilities.json` describes an adapter, and a bundle's `manifest.json` binds compiled content and checksums. |
| **Bundle** | The deterministic, checksum-manifested output of compilation. It contains resolved standards, workflows, hooks, schemas, state templates, provenance, and runtime tooling. |
| **Adapter** | Packaging and capability translation for Codex, Claude, Kiro, or another agent. An agent adapter changes presentation and activation, not migration policy. This is distinct from an architecture adapter, which is an application component connecting a port to I/O. |
| **Hook** | A portable check associated with an event. A command hook is reproducible; an agent hook requires judgment. Whether an event is native, approximate, or instructional depends on the adapter. |
| **Schema** | A machine-readable structural contract for a manifest or migration artifact. |
| **Validator** | Deterministic code that checks schemas plus relationships and invariants that a single schema cannot express. |
| **Artifact** | A named framework output or migration record. The surrounding path matters: a bundle artifact is compiled support content, while a `.migration/` artifact is live project state. |

Profile composition always uses this precedence:

```text
generic → source → target → pair → output → project
```

The arrow means “compose next.” A later layer may supply its owned values under the profile
contract. The adapter is deliberately outside this precedence chain because packaging cannot
override the composed knowledge.

## Migration Concepts

### Observable Behavior and Behavioral Contracts

**Observable behavior** is anything a supported consumer can detect: accepted inputs,
returned values, errors, events, files, messages, state changes, ordering, concurrency,
serialization, timing or resource guarantees, and public compatibility promises.

A **behavioral contract** records one coherent stimulus and its observable outcomes, including
preconditions, evidence, and known gaps. It describes what must be preserved or intentionally
changed without requiring the source and target to share an internal design. Existing tests are
evidence for a contract, not proof that every behavior has been discovered.

### Seams and Slices

A **seam** is a boundary where the legacy or target implementation can be selected and
observed. It may be an API or facade, command launcher, message or job boundary, file format,
library binding, plugin selector, native process boundary, data owner, or traffic route.

A **migration slice** is the smallest useful, dependency-bounded set of characterized behavior
that can move across a real seam. A valid slice is:

- independently buildable and testable;
- observable at its boundary;
- selectable, releasable, or enableable without unrelated unfinished work;
- reversible through a concrete rollback procedure;
- linked to source units, behavioral contracts, target units, tests, gates, and evidence; and
- assigned a stable `SLICE-NNNN` identity, dependencies, approvals, and decommission duties.

A slice is **not** an arbitrary batch of files, a package, an architectural layer, a project
phase, or a synonym for the whole migration. For example, one routable API capability with its
contracts, target implementation, tests, selector, gates, and rollback can be a slice. “Migrate
the persistence layer” is not a safe slice merely because those files share a directory.

Slice dependencies form a **DAG** (directed acyclic graph): a slice may depend on earlier
slices, but dependency cycles must be removed through boundary redesign and, when needed, an
explicit decision. Only one slice is active in global state at a time, even when several ready
slices have been planned.

### Coexistence, Cutover, Rollback, and Decommission

| Term | Meaning |
|---|---|
| **Coexistence** | Legacy and target implementations remain available while a selector chooses the path. Shadow execution is a coexistence technique only when duplicate side effects are isolated. |
| **Cutover** | Authority for a declared scope moves to the target path after verification, review, approval, and rollback preflight. A bounded slice cutover can be recorded while the global lifecycle remains `approve`; the `cut_over` state is reserved for certificate-gated final cutover. |
| **Rollback** | A tested way to return authority to the safe path and reconcile any state or data. “Revert the commit” is insufficient after consumers, traffic, schemas, or state have changed. |
| **Decommission** | The legacy path and its assets are removed, transferred, archived, or explicitly retained only after cutover evidence, observation, recovery, and approval obligations are met. It is separate from cutover. |
| **Strangler Fig pattern** | The default gradual-replacement strategy: introduce a boundary, move capabilities incrementally, then retire the legacy path. The boundary need not be an HTTP route. |

### Gates, Evidence, Verification, and Review

| Term | Meaning |
|---|---|
| **Quality gate** | A named pass condition that protects a characterized behavior or delivery risk, such as build, tests, architecture, dependency integrity, API compatibility, or human approval. Gates come from profiles and project risk, not a universal coverage percentage. |
| **Evidence** | An immutable record of what was actually run or observed. A v3 command evidence record contains one command, one working directory, its exit code, environment, checksummed outputs, linked contracts, and time. Several commands require several evidence records. |
| **Deterministic verification** | Execution of reproducible gates. It answers “did the specified check pass under the recorded conditions?” |
| **Judgment review** | Human or agent assessment of semantic fidelity, target-language quality, architecture intent, risk, and justified modernization. It answers questions a deterministic command cannot settle. |
| **Audit** | Whole-scope reconciliation of the declared denominator, inventories, traceability, plans, evidence, and lifecycle. Validation asks whether the current graph is well formed; audit asks what progress or completion claim the entire graph supports. |
| **Approval** | Recorded authority to accept a bounded decision or advance a slice. Approval does not create missing evidence and does not establish whole-project completion. |
| **Known gap** | A declared area where behavior is not yet characterized or evidence is incomplete. A known gap is not a passing result. |

Verification and review are deliberately separate. Review cannot turn a failing required gate
into a pass, and rerunning commands cannot replace a semantic judgment.

### Decisions, Exceptions, and Traceability

| Term | Meaning |
|---|---|
| **Decision** | A durable choice with context, consequences, affected behavioral contracts, status, and approval references. Examples include architecture boundaries or an intentional compatibility policy. |
| **Exception** | A scoped departure, unsupported condition, blocker, or waiver with rationale, impact, mitigation, approvals, and optional expiry. An approved exception makes the departure explicit; it does not make excluded or retained work “migrated.” |
| **Traceability** | The validated relationship from source units through behaviors to target units, tests, decisions or exceptions, and evidence. Relationships are many-to-many; the framework does not require one target file per source file. |
| **Provenance** | Why a normative framework rule exists, where it applies, how it is enforced, what proves compliance, who owns it, and which version was reviewed. |

The usual trace is summarized as:

```text
source → behavior → target → test → decision/exception → evidence
```

This is a relationship map, not permission to skip lifecycle stages.

## Installed Support and Live State

The two similarly named hidden directories have different owners:

| Directory | Owner | Purpose |
|---|---|---|
| `.migration-framework/` | Framework installer/upgrader | Installed bundle manifest, ownership checksums, schemas, blank templates, provenance, and `migrationctl.py`. These are framework-managed support files. |
| `.migration/` | Project migration workflows | Live, evolving configuration, scope, inventories, plans, decisions, evidence, traceability, lifecycle state, and completion certification. The upgrader validates but does not own this directory. |

The configured roots are also real boundaries. `{source_root}` identifies the legacy source
area to census and characterize. `{target_root}` identifies the complete target project area,
not just its production-source folder: target source, tests, build definitions and launchers,
dependency metadata, project-local caches, reports, and packaged output belong beneath it unless
an accepted orchestration decision says otherwise.

The main `.migration/` artifacts are:

| Artifact | Question it answers |
|---|---|
| `config.json` | Which profiles, roots, strategy, strictness, gates, and project decisions apply? |
| `scope.json` | What is the declared source denominator, snapshot, completion policy, and disposition of each source unit? |
| `state.json` | Where is the migration in its lifecycle, which slice is active, and how did it transition here? |
| `inventory.json` | Which stable source units, variants, dependencies, behaviors, and risks exist? |
| `target-inventory.json` | Which target and test units are planned, present, or removed, and at which paths and checksums? Only truthful `present` entries with current checksums support actual implementation claims. |
| `behaviors/*.json` | What observable contracts were characterized, and where are the gaps? |
| `plans/*.json` | Which dependency-seamed slices, gates, dependencies, and rollback boundaries are planned? |
| `decisions/*.json` | Which intentional choices were proposed, accepted, rejected, or superseded? |
| `exceptions/*.json` | Which scoped departures or blockers were proposed, approved, rejected, or expired? |
| `evidence/*.json` | Which exact characterization, verification, cutover, or decommission operations ran? |
| `traceability.json` | Do source, behavior, target, test, decision, exception, and evidence references join up? |
| `completion-certificate.json` | Does a fresh, machine-generated whole-scope claim hold for the exact current digests and lifecycle revision? |

JSON is authoritative for state and cross-references. Markdown reports, headings, and
checkboxes may explain or summarize that state, but they do not change it.

Scope, census, inventory, and traceability are related but not interchangeable. **Scope** sets
the boundary and denominator. The **source census** is a checksummed snapshot of candidate
files and assets inside that boundary. The **inventory** assigns stable logical identities to
what was found. **Traceability** connects those identities to behavior, target work, tests, and
proof.

Version fields are also separate axes. `framework_version`, an artifact's `schema_version`, a
profile or adapter version, and a bundle format version describe different contracts. A single
framework release may legitimately carry both v2 and v3 artifact schemas.

## Stable Identifiers

Migration records use monotonically allocated identifiers. `NNNN` means “replace this with the
next numeric value of at least four digits,” for example `SRC-0001`. An ID represents logical
identity, survives file renames and retries, and is never reused after rejection, removal, or
supersession.

| Form | Identifies |
|---|---|
| `SRC-NNNN` | A logical source unit in the inventory; it is not necessarily one file. |
| `BEH-NNNN` | One characterized observable behavioral contract. |
| `TGT-NNNN` | A logical target implementation, build, resource, configuration, or delivery unit. |
| `TEST-NNNN` | A concrete target test or verification harness unit, not the result of running it. |
| `DEC-NNNN` | A migration decision. |
| `SLICE-NNNN` | A dependency-seamed migration plan and its stable work identity. |
| `EVID-NNNN` | One immutable evidence record for an independently reproducible operation. |
| `EXC-NNNN` | A scoped migration policy exception or blocker. |

Normative **rule IDs** use a different namespace. Examples such as `GEN-MIG-001`,
`TGT-JAVA25-ARCH-003`, or `OUT-SERVICE-...` identify framework obligations, not live
migration artifacts. Their prefixes identify the owning layer:

| Prefix | Rule owner |
|---|---|
| `GEN-` | Generic framework policy |
| `SRC-<profile>-` | Source-language profile |
| `TGT-<profile>-` | Target-language profile |
| `PAIR-<profile>-` | Language-pair profile |
| `OUT-<profile>-` | Output profile |
| `ADAPTER-<profile>-` | Agent adapter capability or packaging policy |

## Lifecycle States

The normal global lifecycle is:

```text
initialize → discover → characterize → map → plan → execute → verify → review
           → approve → cut_over → decommissioned
```

| State | Meaning |
|---|---|
| `initialize` | Establish schema-valid configuration, roots, scope policy, and blank live state. |
| `discover` | Reconcile the source census, products, variants, dependencies, surfaces, and risks. |
| `characterize` | Turn observed source behavior into evidence-backed contracts. |
| `map` | Design target units and tests for the contracts without implementing them yet. |
| `plan` | Partition mapped work into dependency-ready, reversible slices. |
| `execute` | Implement the active, human-authorized slice boundary; execution cannot approve its own result. |
| `verify` | Run and record deterministic gates for the active slice. |
| `review` | Apply semantic, idiomatic, architectural, and risk judgment. |
| `approve` | Mark a slice eligible for its bounded cutover. If required implementation work remains, the lifecycle returns to `plan`. |
| `cut_over` | Record certificate-authorized final target authority for the declared whole scope. |
| `decommissioned` | Terminal whole-scope state after cutover coverage and legacy-asset closure are certified. |
| `blocked` | Progress needs a named decision, dependency, approval, or external condition; `resume_to` records the safe return state. |
| `failed` | A validator, execution, or cutover operation failed; recovery evidence and `resume_to` are required. |

`blocked` and `failed` are exceptional states, not shortcuts. Resuming is a validated
transition back to the recorded state.

Statuses belong to their artifact and must not be treated as one shared progression:

| Status domain | Values |
|---|---|
| Global lifecycle (`state.json`) | `initialize`, `discover`, `characterize`, `map`, `plan`, `execute`, `verify`, `review`, `approve`, `cut_over`, `decommissioned`, `blocked`, `failed` |
| Slice plan | `planned`, `in-progress`, `blocked`, `failed`, `verified`, `approved` |
| Trace link | `unmapped`, `planned`, `implemented`, `verified`, `approved`, `excepted` |
| Evidence result | `pass`, `fail`, `waived` |
| Decision | `proposed`, `accepted`, `rejected`, `superseded` |
| Exception | `proposed`, `approved`, `rejected`, `expired` |
| Source reachability | `reachable`, `dead`, `unknown` |
| Target inventory | `planned`, `present`, `removed` |
| Structural validation | `unvalidated`, `valid`, `invalid` |

An `approved` plan, an `approved` exception, and a `pass` evidence record therefore make
different claims. Evidence also has a separate `phase`—`characterize`, `verify`, `cut_over`, or
`decommission`—that states when and why the operation ran.

Use the nouns precisely: the migration has a lifecycle **state**, evidence has a **phase**, and
a completion certificate has an `implementation` or `decommission` **stage**. Cross-cutting
workflows such as audit, resume, and framework update are not lifecycle states.

## Scope, Dispositions, and Completion

The **declared denominator** is the source scope against which progress is measured. A
`whole-source-root` policy covers the reconciled root. A `bounded` policy deliberately narrows
it and therefore requires accepted, human-approved boundary decisions.

Two related disposition vocabularies occur in the framework:

| Context | Values | Purpose |
|---|---|---|
| Difficult behavior handling | `preserve`, `normalize`, `remove`, `defer`, `block` | States what policy should apply to an observed behavior. |
| Stored source-unit disposition in `scope.json` | `pending`, `migrated`, `replaced`, `removed`, `retained` | States what ultimately happened to an inventoried source unit. |

`replaced` means an approved replacement whose intentional semantic change remains explicit.
`retained` means a legacy or native boundary remains. `unknown` is an audit finding for a census,
inventory, or behavior gap; it is not a stored source-unit disposition.

The framework reports **accounted** and **migrated** separately:

```text
accounted = (migrated + replaced + retained + policy-approved removed) / declared scope
migrated  = (migrated + replaced) / declared scope
```

Accounting says every item has an explicit evidence-backed disposition. Migration says the
required behavior has an approved target implementation and evidence. Retained or removed work
may be accounted when policy allows, but never increases the migrated numerator. Strict “100%
migrated” also requires zero pending, unknown, retained, removed, and unverified items.

These milestones must not be conflated:

| Milestone | Proves | Does not prove |
|---|---|---|
| **Structurally valid** | Current JSON shapes and populated references satisfy schemas and validators. | The census is exhaustive or migration work is complete. |
| **Slice implemented** | Target code and tests exist for one slice. | Its gates passed. |
| **Slice verified** | Required deterministic gates passed for that slice. | Judgment approval, cutover, or remaining-work closure. |
| **Slice approved** | Verification, review, and bounded approval succeeded. | Other slices are complete. |
| **Scope accounted** | Every declared item has an allowed disposition. | Every item migrated. |
| **Implementation certified** | A fresh global audit proves the chosen whole-scope implementation claim at current digests. | Traffic has moved or legacy assets are retired. |
| **Decommission certified** | A fresh global audit also proves cutover coverage and legacy-asset closure. | Nothing beyond the exact declared scope and evidence. |

A completion certificate is generated by the installed validator and is bound to exact source,
target, migration, and state digests. An agent-authored statement, a clean build, or an approved
slice cannot substitute for it, and relevant state or workspace changes make it stale.

## Notation and Symbols

| Notation | How to read it |
|---|---|
| `C++ → Java 25` | Migration direction: source language to target language. |
| `A → B` or `A -> B` | A flow, valid lifecycle transition, relationship, or composition order as stated by the surrounding section. It does not always mean data is copied. |
| `A ← B` | Read as “A receives from” or “B points to A”; in directory listings it often labels what a path contains. |
| `↓` or `▼` | Continue to the next step or lower node in a process diagram. |
| `{{target_language}}` | Compile-time template variable. Strict compilation replaces it with a scalar value from the composed profiles. Unresolved double braces are an error. |
| `{{#if name == 'value'}} … {{#else}} … {{/if}}` | Compile-time conditional. Only the selected branch appears in the bundle. |
| `{{> path.md#optional-section-anchor}}` | Compile-time inclusion of another permitted template document, optionally limited to one heading section. |
| `{source_root}`, `{target_root}`, `{class}` | Project-time or command-time placeholder intentionally preserved after framework compilation. Replace or resolve it from migration configuration or command context. Single braces are not profile variables. |
| `<accounted|migrated>` | Command metavariable: choose one listed value and omit the angle brackets. Do not type it literally because shells treat angle brackets specially. |
| `DEC-NNNN` | An identifier pattern in instructions. Substitute the actual allocated ID, such as `DEC-0007`. |
| `...` or `…` | Omitted or continuing content, not literal command text unless explicitly stated. |
| `/path/to/project` | Example absolute path that must be replaced with the real project path. |
| `*.json` | Usually a glob meaning matching files. In a hook matcher, `.*` is commonly a regular-expression fragment; interpret wildcards according to the stated tool. |
| `cd {target_root} && <command>` | Change to the target build root, then run the chosen command only if the directory change succeeds. |
| `├──`, `└──`, `│` | Directory-tree drawing characters showing sibling, final-child, and continuing-parent relationships. |
| `` `text` `` | Literal identifier, status, field, path, command, or code token. |
| `$schema` | A JSON field naming the schema for an artifact. The `$` is part of the field name, not a shell variable. |
| `SHA-256`, checksum, digest | Content identity used to detect drift and bind evidence. A file checksum covers one file; an aggregate digest can cover a canonical set of artifacts. |
| `null` | An explicit absence of a value allowed by the schema; it is not automatically equivalent to unknown, empty, failed, or not applicable. |
| `[ ]` / `[x]` | Unchecked and checked narrative checklist items. They are helpful views, never authoritative migration state. |
| `[LANGUAGE_NAME]` or `<!-- fill in -->` | Maintainer scaffolding found in `_template/` documents. It is not canonical template-engine syntax. |
| `cut_over` / “cut over” | `cut_over` is the exact JSON lifecycle or evidence literal; “cut over” is ordinary prose. |
| `✅` / `⚠️` / `🚫` | Allowed or expected / requires caution or prior approval / forbidden in repository instructions. These are policy cues, not lifecycle statuses. |

In hook definitions, `type: command` plus `enforcement: deterministic` means a reproducible
command check. `type: agent` plus `enforcement: judgment` means a review instruction. The
`required` field states policy intent; the selected adapter's capability manifest determines
whether that event can actually be enforced automatically.

For normative rules, **schema** and **validator** mean deterministic enforcement, a **hook**
invokes enforcement at an adapter-supported event, a **review gate** requires recorded judgment,
and **advisory** means instruction only. Advisory or approximate behavior must not be described
as equivalent automatic enforcement.

## Further Reading

- [`HUMAN.md`](HUMAN.md) — narrative explanation of how the complete system fits together.
- [`README.md`](README.md) — installation, compilation, lifecycle, and repository reference.
- [`migration-philosophy.md`](docs/standards/generic/migration-philosophy.md) — behavioral fidelity and evidence principles.
- [`incremental-modernization.md`](docs/standards/generic/incremental-modernization.md) — seams, coexistence, routing, rollback, and gradual replacement.
- [`migration-state-files.md`](docs/standards/generic/migration-state-files.md) — authoritative artifacts and lifecycle rules.
- [`migration-completeness.md`](docs/standards/generic/migration-completeness.md) — denominators, accounted versus migrated, audits, and certificates.
- [`rule-metadata.md`](docs/provenance/rule-metadata.md) — rule IDs, provenance, and enforcement vocabulary.
