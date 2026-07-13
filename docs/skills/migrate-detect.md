# migrate-detect

Discover the complete {{source_language}} system, its build variants, public boundaries,
dependencies, platforms, and observable surfaces before behavior characterization begins.

## When to Use

- Immediately after migrate-init, while `state.json.status` is `discover`.
- With `--refresh` when the source revision or supported build matrix changes.
- When resume validation returns to `discover` because the inventory is incomplete or stale.

## Inputs

- **Path to scan** (optional) — `{source_root}` from `.migration/config.json` by default.
- **--deep flag** (optional) — inspect function-level usage, generated code, native/ABI
  boundaries, and reachability in addition to declarations and build metadata.
- **--refresh flag** (optional) — reconcile against the existing inventory without
  renumbering or deleting stable source-unit IDs.
- **Build variants** (optional) — user-declared supported configurations to supplement
  discovered compiler, platform, feature, and dependency variants.

**Required state:** `.migration/config.json`, `.migration/state.json`, and
`.migration/scope.json`, `.migration/inventory.json`, and `.migration/target-inventory.json`
validate, and the lifecycle state is `discover` (or a validated resume to `discover`).

## Procedure

### Step 1: Establish a Reproducible Discovery Scope

1. Structurally validate the current `.migration/` state before scanning:

   ```bash
   python3 .migration-framework/bin/migrationctl.py validate .migration
   ```

   Confirm the source root and selected profiles match `config.json`; read completion policy,
   source root/snapshot, excluded-file records, boundary decision IDs, and per-source
   dispositions from `scope.json`;
   and read any initial product, variant, platform, consumer, or exclusion assumptions from
   accepted decisions. Structural validity is not proof that the source census is complete.
   Refuse bounded discovery unless every boundary decision exists, is accepted, and has durable
   human approval; a scanner may not create its own smaller denominator.
2. Capture the deterministic workspace snapshot from the project root:

   ```bash
   python3 .migration-framework/bin/migrationctl.py snapshot .migration --project-root .
   ```

   Record the schema-defined source root, revision, capture time, digest, per-file paths and
   checksums, and exception-backed excluded-file records in `scope.json.source_snapshot`.
   Record generated-code roots, submodules, vendored sources, and supported build variants in
   inventory and discovery research. Do not silently inspect only the developer's current
   configuration.
3. Enumerate every snapshot candidate in deterministic relative-path order. Treat build metadata,
   schemas, scripts, resources, tests, and public headers/modules as discoverable units when
   they affect behavior, packaging, or compatibility.
4. Reconcile the source census before semantic scanning. Every snapshot file is exactly one of:
   represented by a stable inventory unit, explicitly excluded by the scope contract with its
   approved exception, or unresolved. An ignored, unknown, unreadable, or unclassified candidate
   is unresolved and blocks the transition. Report the accounted numerator and declared
   denominator; file extensions and build success may not narrow either value.
5. On refresh, match units by retained identity and path history. Reuse the existing
   `SRC-NNNN` ID for a renamed or moved logical unit when evidence supports the match;
   allocate a new ID for a new unit and never renumber surviving records.

### Step 2: Detect Builds and Products

{{> standards/sources/{{source_language_id}}/detection-rules.md#build-system-detection}}

6. Inventory {{source_build_systems}} declarations, package-manager metadata
   ({{source_package_managers}}), toolchain files, compiler/linker flags, generated-source
   steps, build presets, feature flags, and conditional targets.
7. For each supported variant, record inputs, output products, compiler/runtime assumptions,
   tests, dependencies, and platform. A successful default build does not prove other
   variants are irrelevant.

{{> standards/sources/{{source_language_id}}/detection-rules.md#output-type-detection}}

8. Compare detected products with the configured `output_profile`:

   - `service` requires a continuously running deployable boundary;
   - `library` requires a reusable consumer API and optional SPI;
   - `sdk` adds a supported external developer experience and compatibility promise; and
   - `cli` requires command, stream, exit-code, and installed-launcher contracts.

   Mixed products may require multiple migrations, but each detected product remains in the
   declared denominator until an approved umbrella decision assigns it to a specific migration.
   A scoping decision can make one migration narrower; it cannot support an unqualified claim
   that the whole legacy project migrated. A conflict is not resolved by forcing every product
   into the service architecture.

### Step 3: Discover Dependencies and Platform Boundaries

{{> standards/sources/{{source_language_id}}/detection-rules.md#dependency-category-detection}}

9. Resolve declared and observed dependencies, versions/ranges, linkage mode, licenses,
   integrity metadata, callers, and usage locations. Distinguish project-internal,
   language-standard, third-party, generated, native/binary, and platform dependencies.
10. Scan all source units for `{{source_include_directive}}`, dynamic loading, FFI/ABI calls,
   subprocesses, filesystem/network I/O, databases, serialization, environment access,
   global state, and external side effects. Count usage by stable source-unit ID, not only
   by textual occurrence.
11. For every dependency, record the candidate {{target_language}} substitution, confidence,
    semantic mismatches, coexistence option, license/security constraints, and whether a
    compatibility process or retained native boundary may be required.

{{> standards/sources/{{source_language_id}}/detection-rules.md#platform-conditional-detection}}

12. Record operating-system, architecture, compiler, endianness, locale, charset, time-zone,
    filesystem, terminal, and deployment assumptions with source locations and build
    variants. Unsupported platforms require a scoped `EXC-NNNN` proposal and named owner;
    they are never silently dropped.

### Step 4: Discover Semantics and Characterization Surfaces

{{> standards/sources/{{source_language_id}}/detection-rules.md#language-version-detection}}

13. Inventory public APIs, SPIs, protocol/message schemas, command surfaces, file formats,
    database effects, logging/metrics relied on by operators, callbacks, plugins, and
    process lifecycle behavior appropriate to the selected output profile.
14. Inventory source tests from {{source_test_frameworks}}, fixtures, snapshots, sample
    clients, integration environments, benchmarks, and production-observation sources.
    Classify each as candidate characterization evidence; do not yet claim it proves a
    behavioral contract.
15. Identify {{source_language}} semantic hazards, including ownership and RAII, object
    lifetime, macros and generated code, templates/metaprogramming, concurrency and memory
    ordering, numeric/serialization behavior, exception/error models, undefined or
    implementation-defined behavior, platform conditionals, ABI/plugin boundaries, and
    binary-only dependencies.
16. Set `reachability` conservatively:

    - `reachable` when a supported entry point, build target, consumer, or observed path
      reaches the unit;
    - `dead` only with reproducible reachability evidence across supported variants; and
    - `unknown` when evidence is incomplete.

    Proposed omission of dead or unreachable code requires an `EXC-NNNN` record with
    category `dead-code`, impact, mitigation, approval, and exit criteria. Unknown is not
    dead.

### Step 5: Write and Validate Discovery Artifacts

17. Update `.migration/inventory.json` using only fields allowed by its schema. Each unit has
    a stable `SRC-NNNN` ID, relative path, kind, reachability, initially known behavior IDs,
    dependency references, and risk/finding references. Preserve records that are still
    referenced; supersede them in narrative history rather than deleting them.
18. Update `scope.json.units` so every stable source identity has an explicit current
    disposition, target/decision/exception references where already known, and rationale.
    The stored `pending` disposition and audit-derived `unknown` census/inventory gaps remain
    visible and cannot count as accounted. Retained and approved-removed items can count as
    accounted only when the selected policy permits them; neither counts as migrated.
19. Write ID-bearing narrative views under `.migration/research/`:

    - `legacy-stack.md` — source revision, build variants, products, language/toolchain,
      public surfaces, tests, platforms, and hazard findings;
    - `dependency-map.md` — dependency, usage IDs, candidate replacement or coexistence
      boundary, confidence, unsupported status, and required decision;
    - `risk-matrix.md` — stable finding ID, affected `SRC` IDs, impact, likelihood,
      detectability, mitigation, owner, and escalation threshold; and
    - `characterization-plan.md` — public APIs and observable behaviors that must be turned
      into `BEH-NNNN` contracts in migrate-analyze.

20. Create schema-valid proposed exceptions for unsupported dependencies/platforms and
    confirmed dead-code omissions. If an unresolved item prevents reliable
    characterization, transition `discover -> blocked`, set `resume_to: "discover"`, and
    reference the exception IDs in `blocked_by`. A failed scanner or validator transitions
    to `failed` with reproducible diagnostics, rollback/retry action, and a scoped
    `quality-gate` exception referenced by `blocked_by`; neither condition is a partial
    success.
21. Stage scope snapshot/dispositions, inventory, exception, research, and state changes
    together. Validate every JSON artifact and the current full reference graph, then promote
    atomically.
22. Rerun `python3 .migration-framework/bin/migrationctl.py snapshot .migration --project-root
    .` and installed structural validation against the promoted artifacts.
    The discovery gate passes only when every deterministic candidate reconciles and the source
    digest remains unchanged during the scan.
23. When the source census and discovery gate are complete, apply the validated
    `discover -> characterize` transition. Report declared candidates, inventoried, excluded,
    pending, unknown, and accounted counts; inventory counts by kind/reachability; build
    variants; products; public surfaces; highest risks; unresolved exception IDs; the selected
    completion claim; and the next action: migrate-analyze.

## Outputs

- `.migration/scope.json` — deterministic source snapshot, denominator, and source dispositions.
- `.migration/inventory.json` — schema-valid stable source-unit inventory.
- `.migration/research/legacy-stack.md` — build, product, platform, test, and surface view.
- `.migration/research/dependency-map.md` — dependency substitution/coexistence analysis.
- `.migration/research/risk-matrix.md` — prioritized, owned discovery risks.
- `.migration/research/characterization-plan.md` — behavior surfaces still requiring proof.
- `.migration/exceptions/EXC-NNNN.json` — proposed scoped exclusions or unsupported items.
- `.migration/state.json` — validated transition to `characterize`, `blocked`, or `failed`.

## Success Criteria

- Every deterministic source-census candidate is inventoried with one stable `SRC-NNNN`
  identity or appears in an approved scope exclusion; refreshes preserve existing IDs.
- Declared, inventoried, excluded, pending, unknown, and accounted denominators reconcile
  exactly, with zero unresolved candidates before characterization.
- Supported build variants, products, toolchains, dependencies, native/ABI boundaries, and
  platform conditionals are explicit.
- Reachability is evidence-based; dead code, unsupported dependencies, and unsupported
  platforms are neither silently omitted nor falsely accepted.
- The selected output profile agrees with the actual delivery contract or has an explicit
  scoping decision.
- Every public/observable surface has a characterization task, but no untested equivalence
  claim has been made.
- All staged JSON and cross-references validate, and successful state ends in
  `characterize`.
- Discovery reports 100% accounted only under the selected policy and never reports source
  accounting, structural validity, or a stable snapshot as 100% migrated.
