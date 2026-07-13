# migrate-map

Map characterized {{source_language}} contracts to stable {{target_language}} units and
output-profile-specific boundaries without generating implementation code.

## When to Use

- After migrate-analyze has completed and `state.json.status` is `map`.
- With `--refresh` after accepted source, behavior, output-profile, or architecture changes.
- When verification/review returns the lifecycle to mapping because a target boundary was
  wrong, not merely because implementation had a local defect.

## Inputs

- **Behavior or source-unit IDs** (optional) — limit a refresh to affected `BEH-NNNN` or
  `SRC-NNNN` records; defaults to every non-excepted trace.
- **--refresh flag** (optional) — reconcile mappings while preserving stable target/test IDs.
- **Architecture decision IDs** (optional) — accepted project variations from the selected
  output profile; absence means use `{{architecture_style}}` from `{{output_profile}}`.

**Required state:** all artifacts and evidence checksums validate; state is `map` (or a
validated resume to it); every reachable public behavior has characterization evidence or
an approved exception.

**Context to read before starting:**

1. `config.json`, especially `output_profile`, strategy, roots, and project decisions.
2. `inventory.json`, every applicable `BEH-NNNN`, characterization `EVID-NNNN`, and
   `traceability.json`.
3. Characterization analysis, dependency map, risk matrix, and source public-surface view.
4. Generic boundary rules, selected target standards, pair mappings, selected output
   profile, and its target-specific profile document.
5. Existing decisions and exceptions, including intentional changes and unsupported scope.

## Procedure

### Step 1: Validate Mapping Readiness

1. Revalidate the full state graph and source revision. Stop if any referenced behavior,
   evidence, decision, or exception is missing, stale, or the wrong artifact kind.
2. Confirm each non-excepted trace has at least one evidence-backed behavioral contract.
   Mapping must not fill characterization gaps with assumptions.
3. Identify externally observable seams and dependency directions using callers, consumers,
   side effects, deployment/publication boundaries, data ownership, and change cadence.
   Source folders and classes are evidence, not automatic target modules.
4. Allocate stable `TGT-NNNN` IDs for logical target units and `TEST-NNNN` IDs for planned
   target contract tests. Preserve IDs through package/file renames; splitting or merging
   requires new IDs plus an explicit mapping record.

### Step 2: Select Architecture From the Output Profile

5. Apply only the selected profile's architecture.

{{#if output_profile == 'service'}}
   For this service, use the modular-hexagonal default: organize by business capability,
   then domain policy, application/use cases, inbound/outbound ports, adapters, and a visible
   composition root. A module communicates with another through a published application
   contract or event, never another module's persistence model or adapter.
{{/if}}
{{#if output_profile == 'library'}}
   For this library, map consumer-facing contracts to a deliberate API, implementation
   details to enforced internal modules/packages, and only genuine consumer-supplied
   extension points to SPI. Do not manufacture service ports, web adapters, or an
   application process.
{{/if}}
{{#if output_profile == 'sdk'}}
   For this SDK, apply API/internal/SPI boundaries and additionally map stability metadata,
   a compatibility facade, diagnostics, documentation, executable examples, upgrade
   guidance, and supported consumer/service matrices.
{{/if}}
{{#if output_profile == 'cli'}}
   For this CLI, map argument/config/stream/exit/process handling to command boundaries and
   keep core operations independent of process-global I/O. Add ports/adapters only where
   replaceable I/O, multiple front ends, or domain complexity justifies them; do not force
   the service layout.
{{/if}}

6. If project needs conflict with the selected profile, create an accepted `DEC-NNNN` with
   rationale, affected behavior IDs, consequences, enforcement, and approval. Do not encode
   the exception as an unexplained package name.

### Step 3: Map Contracts, Not Syntax Alone

7. For each behavioral contract, define target units responsible for policy, orchestration,
   boundary translation, persistence/I/O, composition, packaging, and tests as applicable.
   One source unit may map to several target units and several source units may merge when
   the behavior boundary supports it.
8. Map every public input, output, error, side effect, ordering guarantee, resource lifetime,
   concurrency constraint, numeric/serialization rule, and platform condition. Reference
   the `BEH`, `DEC`, `EXC`, and characterization `EVID` IDs that constrain each target unit.
9. Map ownership/RAII and native resources to explicit {{target_language}} lifecycles and
   cleanup tests. Map concurrency from characterized happens-before and progress semantics,
   not by replacing syntax token for token.
10. Map macros, templates, generated code, ABI/plugin boundaries, and binary/native
    dependencies using the pair profile. For unsupported dependencies/platforms, select a
    compatible substitution, retained boundary, compatibility process, or approved removal;
    otherwise transition to `blocked`.
11. Do not map undefined behavior as if it were a contract. Map the accepted stabilization,
    isolation, removal, or intentional-change decision and its exception. Approved dead code
    remains an excepted trace and gets no target unit unless decommission work needs one.

### Step 4: Define Coexistence and Release Seams

12. Identify seams at which legacy and target can coexist and be selected independently.
{{#if output_profile == 'service'}}
    For this service, prefer a protocol route, facade, message consumer, worker boundary, or
    another operationally observable selector.
{{/if}}
{{#if output_profile == 'library'}}
    For this library, prefer a compatibility facade, namespaced parallel version, consumer
    binding, or another consumer-controlled selector.
{{/if}}
{{#if output_profile == 'sdk'}}
    For this SDK, prefer a compatibility layer plus representative consumer adoption and a
    supported version-selection mechanism.
{{/if}}
{{#if output_profile == 'cli'}}
    For this CLI, prefer launcher/shim selection with isolated files, streams, and exit-code
    capture.
{{/if}}

13. For each seam, record state/data ownership, side-effect isolation, routing/selection,
    observability, synchronization/reconciliation needs, rollback direction, and the legacy
    decommission condition. Mirrored writes or shadow execution require explicit
    idempotency, ordering, and side-effect controls.
14. Construct a dependency DAG among proposed target units and seams. Cycles require a
    deliberate boundary decision; do not hide them by assigning arbitrary implementation
    waves.

### Step 5: Write the Mapping View and Traceability

15. Write `.migration/mapping.md` with stable IDs and at least these sections:

    ```markdown
    ## Contract Mapping
    | Behavior IDs | Source IDs | Target ID | Target path/surface | Responsibility | Decision/Exception IDs |

    ## Target Unit Catalog
    | Target ID | Planned path/module | Output-profile boundary | Depends on | Lifecycle/compatibility notes |

    ## Test Mapping
    | Test ID | Behavior IDs | Test level | Planned location/harness | Required variants |

    ## Coexistence Seams
    | Seam ID | Selection boundary | State/side effects | Rollback direction | Decommission condition |
    ```

16. Update `traceability.json` atomically:

    - preserve `source_unit`, behavior, decision, exception, and characterization evidence;
    - add stable target and planned test IDs for non-excepted links;
    - keep link status `unmapped` until an executable slice plan owns it; and
    - keep approved exclusions `excepted` with their exception references.

17. Verify every characterized observation is assigned to a target responsibility or an
    approved exception; every target unit has at least one source behavior or explicit new
    intentional-change decision; target dependencies obey the selected output profile; and
    no two mappings accidentally claim the same output path.
18. If architecture choice, unsupported scope, or coexistence safety is unresolved,
    transition `map -> blocked` with scoped exceptions and `resume_to: "map"`. A validator
    or mapping-generation failure transitions to `failed` with a scoped `quality-gate`
    exception, recovery diagnostics, and `resume_to: "map"`.
19. Stage mapping, traceability, decisions, exceptions, and state; validate the complete
    graph; then promote atomically. On success apply `map -> plan` and recommend migrate-plan.

## Outputs

- `.migration/mapping.md` — ID-bearing contract, target-unit, test, dependency, and
  coexistence mapping view.
- `.migration/traceability.json` — source/behavior/evidence to target/test mapping.
- `.migration/decisions/DEC-NNNN.json` — accepted architecture or boundary variations.
- `.migration/exceptions/EXC-NNNN.json` — unresolved or approved scoped mapping exceptions.
- `.migration/state.json` — validated transition to `plan`, `blocked`, or `failed`.

## Success Criteria

- Every non-excepted source behavior maps to stable target and planned test IDs; every
  approved omission remains traceable to an exception.
- Architecture follows the selected output profile: service, library, SDK, and CLI mappings
  do not leak incompatible structures into one another.
- Mapping preserves characterized lifetime, concurrency, error, numeric, serialization,
  platform, API, side-effect, and operational contracts.
- Dependency seams support independently releasable work, coexistence, route/selection
  reversal, rollback, and explicit legacy decommission conditions.
- Unsupported and unspecified behavior is decided, isolated, excepted, or blocking—never
  silently translated.
- All mappings use stable IDs and all JSON/cross-references validate atomically.
- No target implementation code was generated during mapping, and successful state ends in
  `plan`.
