# migrate-execute

Implement one planning-approved dependency-seam slice from characterized behavior and a
validated `planned` plan, while keeping the legacy path available for later verification
and cutover.

## When to Use

- After migrate-plan selects an active slice and `state.json.status` is `execute`.
- To continue an interrupted active slice after migrate-resume validates recovery.
- To rework implementation after deterministic verification or judgment review returns the
  lifecycle to `execute`.

## Inputs

- **Slice ID** (optional) — defaults to `state.json.active_slice`; an explicit ID must match it.
- **--task ID** (optional) — execute one ordered task from the slice detail plan.
- **--interactive flag** (optional) — require confirmation between reversible task checkpoints.
- **--dry-run flag** (optional) — report files, commands, dependencies, side effects, and
  checkpoints without writing target or migration state.

**Required state:** the active `SLICE-NNNN` JSON and Markdown plans, all referenced source
units, behavioral contracts, characterization evidence, target/test mappings, decisions,
exceptions, dependencies, `scope.json`, and `target-inventory.json` validate; state is
`execute` (or a validated resume to it).

## Procedure

### Step 1: Revalidate the Execution Contract

1. Validate the current `.migration/` artifact graph and confirm the source revision, plan checksum,
   selected profiles, `{source_root}`, and `{target_root}` have not drifted. Resolve the target
   root from the project root without following a symlink outside the project. Structural graph
   validity is not a claim that the declared scope is fully implemented.
2. Read the active plan completely with every referenced {{source_language}} source unit,
   `BEH`, characterization `EVID`, mapping, target/pair/output standards, decision, and
   exception. Do not translate from the plan summary alone.
3. Refuse execution if any required behavior lacks characterization evidence, an exception
   is unapproved/expired, a prerequisite slice is not approved, or a target file is owned by
   another concurrently active slice. Resolve every planned target/build path and anticipated
   persistent tool output before mutation. Refuse an outside-`{target_root}` path unless an
   accepted orchestration decision explicitly owns that path and its command topology.
4. Confirm the slice remains independently releasable and reversible. If implementation
   reveals a false seam, missing contract, new public behavior, or unsafe rollback, stop and
   return to the appropriate earlier lifecycle state instead of silently expanding scope.
5. In dry-run mode, report the ordered tasks, exact resolved target and build/tooling paths,
   command working directories, anticipated persistent outputs, dependency changes,
   coexistence controls, and rollback checkpoint, then exit without mutation.

### Step 2: Establish a Reversible Workspace

6. Use the project's existing version-control/reversible-change mechanism. Create a
   slice-scoped branch or checkpoint only when project policy permits; never modify unrelated
   user work, rewrite history, or assume permission to publish changes.
7. Ensure the legacy implementation remains runnable and the planned selector/routing shim
   defaults to the legacy path. Execution must not move consumers, production traffic, or
   durable state; those actions belong to approved cutover.
8. Stage dependency/build changes first and use only the plan-approved substitutions,
   versions, alignment constraints/platforms, integrity metadata, and license/security
   decisions. Keep the build launcher, definitions, metadata, project-local caches, and output
   beneath `{target_root}` unless the plan cites its accepted orchestration decision. A
   coordinate catalog alone is not resolved-version enforcement.
9. Mark the plan `in-progress` and preserve state `execute`. Do not advance traceability or
   state based on file presence alone.

### Step 3: Implement in Dependency Order

10. Execute the plan's ordered tasks. Tasks may run concurrently only when their dependency
    prerequisites are complete, their owned target files do not overlap, and they cannot
    mutate the same build metadata, generated output, state, fixture, or external resource.
    Architectural layer waves are not a substitute for this dependency check.
11. For every target unit:

    - implement only behavior referenced by its `BEH`/`DEC`/`EXC` trace;
    - preserve public inputs, outputs, errors, side effects, ordering, resource lifetime,
      concurrency, numeric/serialization, and platform contracts;
    - use idiomatic {{target_language}} only where equivalence and accepted modernization
      permit it;
    - keep framework/infrastructure types out of profile-neutral policy and public contracts
      unless the selected output profile requires them; and
    - retain stable `TGT-NNNN` identity in the execution report even if files are renamed.

12. Apply the selected architecture, not a universal structure.
{{#if output_profile == 'service'}}
    For this service, implement business-capability modules with policy/application ports and
    adapters, a visible composition root, boundary validation/error translation, and a
    framework-free domain.
{{/if}}
{{#if output_profile == 'library'}}
    For this library, enforce API/internal/SPI surfaces, create no mandatory application
    process, and keep runtime-framework types out of the core consumer API.
{{/if}}
{{#if output_profile == 'sdk'}}
    For this SDK, enforce API/internal/SPI surfaces plus stability metadata, diagnostics,
    compatibility guidance, documentation, and executable consumer examples.
{{/if}}
{{#if output_profile == 'cli'}}
    For this CLI, keep command parsing and process I/O at the boundary, core operations
    independent of global streams/process exit, exit/stream behavior stable, and packaging
    testable through the installed launcher.
{{/if}}

13. Translate ownership and RAII into explicit resource ownership and deterministic cleanup
    where required. Test success, error, cancellation, shutdown, and partial-construction
    paths; automatic memory reclamation is not equivalent cleanup evidence.
14. Implement concurrency from characterized happens-before, affinity, atomicity, ordering,
    cancellation, and progress requirements. Do not mechanically replace primitives whose
    memory or scheduling semantics differ.
15. Implement undefined/implementation-defined, intentional-change, dead-code, native,
    unsupported dependency, and platform policies exactly as their decisions/exceptions
    specify. Any new uncertainty gets a stable decision/exception and blocks affected work;
    do not leave an untracked review comment or guessed behavior.

### Step 4: Implement Contract-Derived Tests and Coexistence

16. Create or update each planned `TEST-NNNN` harness from its behavioral contracts and
    characterization fixtures. Cover observable paths, boundaries, supported variants, and
    relevant failure/concurrency/resource cases; do not use a blanket one-test-per-method
    rule or tests that merely mirror implementation internals.
17. Preserve differential capability so source and target can receive equivalent inputs
    during verification. Keep normalization rules linked to their accepted decisions.
18. Implement the planned coexistence selector/facade/route/shim with the legacy path as the
    safe default. Shadow work must suppress or isolate side effects; mirrored writes require
    the plan's idempotency, ordering, reconciliation, and partial-failure controls.
19. Implement observability needed to distinguish legacy and target paths without changing
    public behavior or exposing secrets. Add the planned rollback mechanism, but do not
    invoke cutover or decommission actions during execution.

### Step 5: Use Fast Feedback Without Claiming Verification

20. At each reversible checkpoint, run the narrowest relevant target tests and compile the
    full target from the configured target root using the exact canonical commands:

    ```bash
    cd {target_root} && {{test_single_command}}
    cd {target_root} && {{compile_command}}
    ```

    These are the default invocations. Use an alternate working directory only when the plan
    cites the accepted orchestration decision and gives the exact replacement commands.

21. Before handing off, run the configured target test command from `{target_root}`:

    ```bash
    cd {target_root} && {{test_command}}
    ```

    These runs are execution feedback. migrate-verify must rerun all profile-configured
    deterministic gates in a controlled environment and append authoritative `EVID` records.
22. Fix only defects within the approved behavior and target boundary. A fix that changes a
    public contract, dependency choice, architecture boundary, coexistence model, or rollback
    plan requires returning to characterize, map, or plan with an explicit transition.
23. If progress requires an unavailable dependency, environment, decision, or approval,
    create/update the scoped exception, mark the plan `blocked`, and transition
    `execute -> blocked` with `resume_to: "execute"`. If compilation, tests, generation, or
    workspace promotion fails, preserve diagnostics and rollback status, create a scoped
    `quality-gate` exception describing recovery/exit criteria, reference it from
    `blocked_by`, mark the plan `failed`, and transition `execute -> failed` with
    `resume_to: "execute"`.

### Step 6: Record an Atomic Execution Handoff

24. Write `.migration/plans/SLICE-NNNN-execution.md` containing target/test IDs and exact
    project-root-relative paths, source/behavior trace, dependency changes, coexistence
    mechanism, exact command working directories and commands, feedback, generated artifacts,
    deviations, unresolved risks, and rollback checkpoint. Every uncertainty must reference
    a `DEC` or `EXC` ID.
25. Reconcile every created or changed target source, test, build, packaging, generated,
    deployment, and retained-boundary asset into `.migration/target-inventory.json` with its
    stable target identity, project-root-relative path, kind, truthful lifecycle status, and
    SHA-256 checksum. A path on disk that is absent from target inventory is unresolved; a
    planned target ID without an actual target-inventory entry is not implementation evidence.
26. Update `traceability.json` links to `implemented`, add actual target/test IDs, and preserve
    characterization evidence, decisions, and exceptions. Do not add verification evidence
    that has not been produced.
27. Keep the plan status `in-progress` until deterministic verification changes it. Do not
    add the slice to `completed_slices`, approve it, select target traffic, or remove legacy.
28. Report global declared, accounted, implemented, verified, approved, retained, removed,
    pending, unknown, unverified, and remaining-slice denominators. The active slice may be
    fully implemented while global migration remains incomplete.
29. Stage execution report, target inventory, plan, traceability, and state changes; validate all references
    and target-file ownership; promote atomically. Keep lifecycle state at `execute` and
    recommend migrate-verify with the active slice ID; migrate-verify revalidates the handoff
    and owns the `execute -> verify` transition before running authoritative gates.

## Outputs

- {{target_language}} implementation, tests, build/tooling files, and project-local build
  outputs under `{target_root}` in output-profile-specific boundaries.
- Slice-scoped coexistence, observability, and rollback mechanisms with legacy still active.
- `.migration/plans/SLICE-NNNN-execution.md` — ID-bearing execution and deviation record.
- `.migration/traceability.json` — implemented target/test links.
- `.migration/target-inventory.json` — actual target assets, statuses, and checksums.
- Updated plan, decision, exception, and state artifacts as required.
- `.migration/state.json` — remains valid at `execute` for a successful handoff, or records a
  validated transition to `blocked` or `failed`.

## Success Criteria

- Only the active, planning-approved dependency-seam slice was implemented; unrelated user
  work and other slices were preserved.
- Every target unit and test traces to source behavior, characterization evidence, and any
  governing decision/exception.
- Structure matches the selected output profile without universal service/hexagonal leakage.
- Ownership, concurrency, numeric/serialization, error, platform, and native-boundary
  semantics follow characterized contracts or explicit approved divergence.
- Target-owned paths and project-local outputs remain beneath `{target_root}`, or exactly
  match the outside paths owned by an accepted orchestration decision.
- The target compiles with `{{compile_command}}` from its approved working directory and
  configured execution-feedback tests pass, or failure/blocking state accurately records
  diagnostics and recovery.
- Legacy remains selectable; coexistence and rollback controls exist; no cutover or
  decommission occurred.
- No untracked uncertainty or false completion claim remains.
- Actual target inventory reconciles every slice-owned target asset, and global remaining-work
  counts are explicit; file presence or successful execution feedback is not full-scope proof.
- Successful execution hands off from valid state `execute`; migrate-verify performs the
  `execute -> verify` transition, and deterministic verification and judgment review remain
  separate subsequent gates.
