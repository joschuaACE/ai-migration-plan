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
`.migration/inventory.json` validate, and the lifecycle state is `discover` (or a validated
resume to `discover`).

## Procedure

### Step 1: Establish a Reproducible Discovery Scope

1. Read and validate the complete `.migration/` state before scanning. Confirm the source
   root and selected profiles match `config.json`.
2. Record the source revision or content checksum, scan exclusions, generated-code roots,
   submodules, vendored sources, and every supported build variant. Do not silently inspect
   only the developer's current configuration.
3. Enumerate candidate files in deterministic relative-path order. Treat build metadata,
   schemas, scripts, resources, tests, and public headers/modules as discoverable units when
   they affect behavior, packaging, or compatibility.
4. On refresh, match units by retained identity and path history. Reuse the existing
   `SRC-NNNN` ID for a renamed or moved logical unit when evidence supports the match;
   allocate a new ID for a new unit and never renumber surviving records.

### Step 2: Detect Builds and Products

{{> standards/sources/{{source_language_id}}/detection-rules.md#build-system-detection}}

5. Inventory {{source_build_systems}} declarations, package-manager metadata
   ({{source_package_managers}}), toolchain files, compiler/linker flags, generated-source
   steps, build presets, feature flags, and conditional targets.
6. For each supported variant, record inputs, output products, compiler/runtime assumptions,
   tests, dependencies, and platform. A successful default build does not prove other
   variants are irrelevant.

{{> standards/sources/{{source_language_id}}/detection-rules.md#output-type-detection}}

7. Compare detected products with the configured `output_profile`:

   - `service` requires a continuously running deployable boundary;
   - `library` requires a reusable consumer API and optional SPI;
   - `sdk` adds a supported external developer experience and compatibility promise; and
   - `cli` requires command, stream, exit-code, and installed-launcher contracts.

   Mixed products may require multiple migrations or an accepted scoping decision. A
   conflict is not resolved by forcing every product into the service architecture.

### Step 3: Discover Dependencies and Platform Boundaries

{{> standards/sources/{{source_language_id}}/detection-rules.md#dependency-category-detection}}

8. Resolve declared and observed dependencies, versions/ranges, linkage mode, licenses,
   integrity metadata, callers, and usage locations. Distinguish project-internal,
   language-standard, third-party, generated, native/binary, and platform dependencies.
9. Scan all source units for `{{source_include_directive}}`, dynamic loading, FFI/ABI calls,
   subprocesses, filesystem/network I/O, databases, serialization, environment access,
   global state, and external side effects. Count usage by stable source-unit ID, not only
   by textual occurrence.
10. For every dependency, record the candidate {{target_language}} substitution, confidence,
    semantic mismatches, coexistence option, license/security constraints, and whether a
    compatibility process or retained native boundary may be required.

{{> standards/sources/{{source_language_id}}/detection-rules.md#platform-conditional-detection}}

11. Record operating-system, architecture, compiler, endianness, locale, charset, time-zone,
    filesystem, terminal, and deployment assumptions with source locations and build
    variants. Unsupported platforms require a scoped `EXC-NNNN` proposal and named owner;
    they are never silently dropped.

### Step 4: Discover Semantics and Characterization Surfaces

{{> standards/sources/{{source_language_id}}/detection-rules.md#language-version-detection}}

12. Inventory public APIs, SPIs, protocol/message schemas, command surfaces, file formats,
    database effects, logging/metrics relied on by operators, callbacks, plugins, and
    process lifecycle behavior appropriate to the selected output profile.
13. Inventory source tests from {{source_test_frameworks}}, fixtures, snapshots, sample
    clients, integration environments, benchmarks, and production-observation sources.
    Classify each as candidate characterization evidence; do not yet claim it proves a
    behavioral contract.
14. Identify {{source_language}} semantic hazards, including ownership and RAII, object
    lifetime, macros and generated code, templates/metaprogramming, concurrency and memory
    ordering, numeric/serialization behavior, exception/error models, undefined or
    implementation-defined behavior, platform conditionals, ABI/plugin boundaries, and
    binary-only dependencies.
15. Set `reachability` conservatively:

    - `reachable` when a supported entry point, build target, consumer, or observed path
      reaches the unit;
    - `dead` only with reproducible reachability evidence across supported variants; and
    - `unknown` when evidence is incomplete.

    Proposed omission of dead or unreachable code requires an `EXC-NNNN` record with
    category `dead-code`, impact, mitigation, approval, and exit criteria. Unknown is not
    dead.

### Step 5: Write and Validate Discovery Artifacts

16. Update `.migration/inventory.json` using only fields allowed by its schema. Each unit has
    a stable `SRC-NNNN` ID, relative path, kind, reachability, initially known behavior IDs,
    dependency references, and risk/finding references. Preserve records that are still
    referenced; supersede them in narrative history rather than deleting them.
17. Write ID-bearing narrative views under `.migration/research/`:

    - `legacy-stack.md` — source revision, build variants, products, language/toolchain,
      public surfaces, tests, platforms, and hazard findings;
    - `dependency-map.md` — dependency, usage IDs, candidate replacement or coexistence
      boundary, confidence, unsupported status, and required decision;
    - `risk-matrix.md` — stable finding ID, affected `SRC` IDs, impact, likelihood,
      detectability, mitigation, owner, and escalation threshold; and
    - `characterization-plan.md` — public APIs and observable behaviors that must be turned
      into `BEH-NNNN` contracts in migrate-analyze.

18. Create schema-valid proposed exceptions for unsupported dependencies/platforms and
    confirmed dead-code omissions. If an unresolved item prevents reliable
    characterization, transition `discover -> blocked`, set `resume_to: "discover"`, and
    reference the exception IDs in `blocked_by`. A failed scanner or validator transitions
    to `failed` with reproducible diagnostics, rollback/retry action, and a scoped
    `quality-gate` exception referenced by `blocked_by`; neither condition is a partial
    success.
19. Stage all inventory, exception, research, and state changes together. Validate every
    JSON artifact and the full reference graph, then promote atomically.
20. When discovery is complete, apply the validated `discover -> characterize` transition.
    Report inventory counts by kind/reachability, build variants, public surfaces, highest
    risks, unresolved exception IDs, and the next action: migrate-analyze.

## Outputs

- `.migration/inventory.json` — schema-valid stable source-unit inventory.
- `.migration/research/legacy-stack.md` — build, product, platform, test, and surface view.
- `.migration/research/dependency-map.md` — dependency substitution/coexistence analysis.
- `.migration/research/risk-matrix.md` — prioritized, owned discovery risks.
- `.migration/research/characterization-plan.md` — behavior surfaces still requiring proof.
- `.migration/exceptions/EXC-NNNN.json` — proposed scoped exclusions or unsupported items.
- `.migration/state.json` — validated transition to `characterize`, `blocked`, or `failed`.

## Success Criteria

- Every relevant source, test, build, generated, resource, and public-surface unit has one
  stable `SRC-NNNN` identity, with refreshes preserving existing IDs.
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
