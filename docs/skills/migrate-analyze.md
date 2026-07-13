# migrate-analyze

Characterize observable {{source_language}} behavior and semantic risks, producing stable
behavioral contracts that must exist before target mapping or translation.

## When to Use

- After migrate-detect has completed and `state.json.status` is `characterize`.
- When source changes invalidate one or more characterized contracts.
- When a failed verification exposes a missing or incorrect source behavior and the
  lifecycle has intentionally returned to characterization.

## Inputs

- **Source-unit IDs** (optional) — one or more `SRC-NNNN` IDs; defaults to every reachable
  or unknown unit not yet covered by a valid behavioral contract.
- **--focus flag** (optional) — `ownership`, `concurrency`, `io`, `api`, `numeric`,
  `serialization`, `platform`, or `all` (default).
- **--refresh flag** (optional) — re-characterize affected contracts after a source revision
  change while preserving their stable `BEH-NNNN` IDs when the logical contract is the same.

**Required state:** all `.migration/` artifacts validate; state is `characterize` (or a
validated resume to it); discovery records the source revision, supported build variants,
public surfaces, dependencies, and characterization tasks; `scope.json.source_snapshot`
reconciles every declared source candidate with zero unresolved census items.

**Context to read before starting:**

1. `config.json` and `scope.json` for selected profiles, roots, output profile, strategy,
   completion policy, global denominators, source snapshot, and project choices.
2. `inventory.json` for stable source-unit IDs and reachability, plus
   `target-inventory.json` to confirm target implementation has not started prematurely.
3. `research/legacy-stack.md`, `dependency-map.md`, `risk-matrix.md`, and
   `characterization-plan.md` for discovered variants, boundaries, and hazards.
4. Source-profile idioms, semantic-hazard guidance, and pair equivalence policy.
5. Existing decisions, exceptions, behavioral contracts, and traceability links.

## Procedure

### Step 1: Define the Characterization Boundary

1. Validate state and confirm the recorded source revision still matches `{source_root}`.
   A changed source invalidates affected observations; do not reuse stale proof.
2. Group source units by observable boundary and dependency seam, not by directory size or
   a future target package. Candidate seams include a public API, command, protocol,
   message, file format, database interaction, native boundary, or independently runnable
   business capability.
3. List the supported build variants and environments for each boundary. Record which
   variants can be executed, which can only be analyzed, and why.
4. Allocate or reuse stable `BEH-NNNN` IDs. One contract describes one coherent stimulus
   and its externally observable results; changing its source path does not change its ID.

### Step 2: Collect Reproducible Source Evidence

5. Prefer existing source tests. Record the exact build/test `command`,
   `working_directory`, environment/toolchain, source revision, selected tests, `exit_code`,
   relevant output, and checksummed artifact path records. Do not store several commands or
   working directories in one evidence record.
6. Where source tests are absent or incomplete, add characterization at the narrowest safe
   seam using one or more of:

   - golden-master capture of outputs, errors, streams, files, messages, or side effects;
   - differential harnesses that can later exercise source and target with identical input;
   - representative consumer or protocol contract tests;
   - deterministic replay of recorded interactions with secrets and personal data removed;
   - static proof for unreachable/error states that cannot be executed safely; or
   - a documented, approved exception when reliable observation is impossible.

7. Normalize only explicitly unstable fields such as approved timestamps or random IDs.
   Record every normalization rule and its decision ID; never normalize a meaningful order,
   numeric difference, error, exit status, encoding, or side effect merely to make tests pass.
8. Store large raw results beneath `.migration/research/characterization/` with checksums.
   For every characterization run, create a schema-valid
   `.migration/evidence/EVID-NNNN.json` using the v3 evidence contract: `phase:
   "characterize"`, `slice_id: null`, one exact `command`, one project-root-relative
   `working_directory`, its integer `exit_code`, environment, `artifacts` containing path and
   SHA-256 pairs, affected `contracts`, status, and UTC `recorded_at`. Reference those `EVID`
   IDs from the behavioral contract and traceability link. The untouched evidence template is
   failing by design; only the recorded exit code and artifacts may justify `status: "pass"`.
   Characterization evidence precedes slices; do not invent a slice solely to give it identity.

### Step 3: Characterize Behavior Completely

9. For every contract, capture schema-required fields:

   - `id` and all contributing `source_units`;
   - preconditions and supported build/runtime variants;
   - one precise stimulus or event;
   - observable results, return values, errors, side effects, ordering, and timing bounds;
   - immutable evidence references; and
   - known gaps that evidence does not cover.

10. Characterize the selected output profile's public contract.

{{#if output_profile == 'service'}}
    For this service, cover protocols, authorization, transactions, idempotency, timeouts,
    retries, delivery/order, readiness, shutdown, backpressure, and relied-on telemetry.
{{/if}}
{{#if output_profile == 'library'}}
    For this library, cover API/SPI surface, source/binary expectations, initialization,
    ownership, thread safety, errors, serialization, optional dependencies, and consumer
    lifecycle.
{{/if}}
{{#if output_profile == 'sdk'}}
    For this SDK, cover the library contracts plus stability levels, supported matrix,
    diagnostics, documentation journeys, executable examples, pagination/rate limits, and
    deprecation behavior.
{{/if}}
{{#if output_profile == 'cli'}}
    For this CLI, cover arguments/config precedence, stdin, stdout, stderr, exit codes, TTY
    behavior, signals, partial output, generated files, launcher, and packaging behavior.
{{/if}}

11. Characterize ownership and lifetime: creator/owner/borrower relationships, aliasing,
    RAII cleanup order, exception and cancellation paths, static/global lifetime, callback
    retention, and native-resource shutdown. Garbage collection is not evidence of equivalent
    resource lifetime in {{target_language}}.
12. Characterize concurrency: thread-affinity, happens-before assumptions, locks and lock
    ordering, atomics and memory order, condition variables, cancellation, data races,
    lock-free progress expectations, scheduling sensitivity, and repeatability of failures.
13. Characterize language/runtime boundaries: numeric widths/overflow, floating point,
    locale/charset, binary layout, serialization, filesystem semantics, clock/time zone,
    exception/error translation, and platform/compiler conditional behavior.
14. Analyze macros, templates, code generation, ABI/plugin loading, binary-only/native
    dependencies, and reflection-like registration for semantics not visible in ordinary
    call graphs.

### Step 4: Apply Explicit Risk Policies

15. For undefined or implementation-defined {{source_language}} behavior, distinguish:

    - behavior guaranteed by the source language;
    - implementation-defined behavior with a recorded compiler/platform choice;
    - unspecified behavior where several outcomes are permitted; and
    - undefined behavior for which general equivalence cannot be promised.

    Observe relevant deployed environments, then either stabilize a chosen contract through
    an accepted `DEC-NNNN`, isolate/retain the legacy boundary, remove it with approved
    impact, or create `EXC-NNNN` category `unspecified-behavior` and block. Never translate
    an accidental observation into a universal guarantee.
16. An intentional behavior change requires an accepted decision naming affected `BEH` IDs,
    a replacement contract, consumer/operational impact, migration communication, tests,
    approval, and an `intentional-change` exception where compatibility policy is waived.
17. A dead/unreachable unit, unsupported dependency, or unsupported platform remains scoped
    by its corresponding exception. Confirm evidence, mitigation, owner, approval status,
    and exit/expiry criteria before treating its trace as excepted.
18. Escalate and transition to `blocked` when a high-risk behavior lacks trustworthy
    evidence, a required environment/dependency is unavailable, or human approval is
    required. A failed source harness or corrupted artifact transitions to `failed` with
    a failing characterization `EVID` record, a scoped `quality-gate` exception, diagnostics,
    and recovery action. Both states reference their exceptions in `blocked_by` and record
    `resume_to: "characterize"`.

### Step 5: Synthesize and Validate Contracts

19. Write one schema-valid `.migration/behaviors/BEH-NNNN.json` per observable contract.
    Update each inventory unit's `behaviors` array and add or update its traceability link:

    - ordinary links contain behavior IDs and start as `unmapped`;
    - intentionally excluded links use `status: "excepted"` and reference approved
      exception/decision IDs; and
    - characterization `EVID` IDs are present before mapping, while target units and tests
      remain empty until their lifecycle stages create them.

20. Write `.migration/analysis/characterization.md` as a human-readable, ID-bearing view
    covering seams, ownership, concurrency, hazards, gaps, evidence matrix, decisions,
    exceptions, and risk escalation. Markdown is not authoritative state.
21. Verify that every reachable source unit and every public/observable surface has at least
    one evidence-backed behavior contract. Unknown-reachability units need a contract or an
    explicit unresolved exception; approved dead-code links may be excepted.
22. Reconcile the global characterization denominators from `scope.json` and `inventory.json`.
    Report declared, accounted, reachable, unknown, retained, removed, behavior-required,
    characterized, evidence-passing, and remaining counts with stable IDs. `pending` or
    `unknown` is never hidden by a percentage; retained or removed source is accounted only
    when policy permits and is never counted as migrated.
23. Stage contracts, scope/inventory references, traceability, decisions, exceptions, analysis,
    and state together. Validate every schema, evidence checksum, and cross-reference before
    atomic promotion.
24. If the gate passes, apply `characterize -> map`. Report the global denominators, contract/
    evidence coverage, known gaps, undefined/implementation-defined findings, unresolved risks,
    selected completion claim, and the next action: migrate-map.

## Outputs

- `.migration/behaviors/BEH-NNNN.json` — schema-valid observable contracts.
- `.migration/inventory.json` — source units linked to their behavior IDs.
- `.migration/scope.json` — reconciled source dispositions and characterization denominators.
- `.migration/traceability.json` — source-to-behavior links or approved exceptions.
- `.migration/analysis/characterization.md` — ID-bearing human analysis and evidence view.
- `.migration/research/characterization/` — checksummed source observations and harness output.
- `.migration/evidence/EVID-NNNN.json` — schema-valid pre-slice characterization runs.
- `.migration/decisions/DEC-NNNN.json` and `.migration/exceptions/EXC-NNNN.json` as required.
- `.migration/state.json` — validated transition to `map`, `blocked`, or `failed`.

## Success Criteria

- Every reachable source unit and public behavior in the declared source census is covered by
  evidence-backed `BEH-NNNN` contracts; exclusions are explicit, scoped, approved, traceable,
  and reported outside the migrated numerator.
- Source tests are used where available, with golden-master, differential, consumer, or
  static evidence filling justified gaps.
- Ownership/RAII, concurrency, macros/templates, ABI/native dependencies, serialization,
  numeric behavior, variants, platform assumptions, and undefined/implementation-defined
  behavior are explicitly analyzed.
- Intentional changes and unpreservable behavior have decisions, replacement expectations,
  impact, approvals, and exceptions rather than false equivalence claims.
- Each characterization evidence record has `phase: "characterize"`, no slice reference, one
  exact `command`, one `working_directory`, its `exit_code`, reproducible environment data,
  path/SHA-256 artifacts, and visible known gaps.
- All artifacts and cross-references validate atomically, and successful state ends in `map`.
- No target mapping or translation began before characterization passed.
- Global declared, accounted, characterized, retained, removed, pending, unknown, and
  evidence-passing denominators are reported with stable IDs; no slice-local result is called
  whole-scope completion.
