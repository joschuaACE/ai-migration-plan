# migrate-plan

Create schema-valid, dependency-seamed migration slices that can be implemented, verified,
released, rolled back, and decommissioned independently.

## When to Use

- After migrate-map completes and `state.json.status` is `plan`.
- After an approved slice when more mapped behavior remains (`approve -> plan`).
- When verification or review returns to planning because the slice boundary, dependency,
  or acceptance contract—not just its implementation—must change.

## Inputs

- **Scope IDs** (optional) — mapped `BEH-NNNN`, `TGT-NNNN`, or candidate seam IDs;
  defaults to the smallest unplanned, dependency-ready behavior set.
- **--strategy flag** (optional) — `conservative`, `modern`, or `hybrid` implementation
  guidance inside the configured migration strategy. It never authorizes behavioral drift.
- **--all-ready flag** (optional) — plan every currently dependency-ready slice, while still
  selecting only one active slice for execution.

**Required state:** state is `plan` (or a validated resume to it); all source inventory,
behavioral contracts, characterization evidence, mapping, decisions, exceptions, and
traceability validate; every planned behavior has at least one target/test mapping.

**Context to read before starting:**

1. `config.json`, `state.json`, `inventory.json`, and `traceability.json`.
2. Every in-scope behavioral contract and characterization evidence record.
3. `mapping.md` target units, dependency DAG, output-profile boundary, and coexistence seams.
4. Selected generic, source, target, pair, and output-profile standards in merge precedence.
5. Dependency substitutions, accepted decisions, approved exceptions, and unresolved risks.

## Procedure

### Step 1: Select an Independently Releasable Slice

1. Validate the complete migration graph and confirm mapping still matches the source
   revision and characterized contracts.
2. Select behavior at a real dependency seam: protocol route, consumer-facing API/facade,
   message or job boundary, command/shim, native process boundary, or another selector that
   lets legacy and target coexist. Do not group work merely because files share a directory,
   package, phase number, or architectural layer.
3. Make the slice as small as possible while still independently buildable, testable,
   observable, selectable, and reversible. If it cannot be released without unrelated
   unfinished work, split it or explain the coupling in an accepted decision.
4. Allocate the next stable `SLICE-NNNN` ID. Slice identity survives plan-file renames and
   retries; a materially different release boundary gets a new ID and supersedes the old plan.
5. Build the slice dependency DAG using other `SLICE` IDs. Every dependency must already be
   approved or appear as an explicit earlier plan; cycles require a boundary decision.

### Step 2: Prove Planning Readiness

6. For every included `SRC` and `BEH` ID, verify characterization `EVID` records are present,
   reproducible, and cover supported variants. Translation is forbidden if required behavior
   is represented only by prose or an unapproved gap.
7. Resolve each dependency from the pair dependency map. Record the exact selected
   replacement, retained interoperability boundary, version/alignment/integrity policy,
   license/security constraints, and confidence. An unsupported dependency or platform must
   be isolated with an approved `EXC` or block planning.
8. Resolve language-semantic risks explicitly: ownership/RAII, concurrency/memory order,
   numeric/serialization behavior, macros/templates, ABI/native code, and undefined or
   implementation-defined behavior. Reference the `DEC`/`EXC` that authorizes stabilization,
   intentional change, legacy retention, or removal.
9. Exclude confirmed dead code only through its approved `dead-code` exception and preserve
   its decommission trace. Intentional changes need an accepted decision, replacement
   behavior, consumer impact, communication, tests, approval, and compatibility exception.
10. Apply the architecture from `{{output_profile}}` and `{{architecture_style}}`.
{{#if output_profile == 'service'}}
    Preserve modular policy/application, port, adapter, and composition-root boundaries.
{{/if}}
{{#if output_profile == 'library'}}
    Preserve API/internal/SPI, module export, and consumer compatibility boundaries without
    an application process.
{{/if}}
{{#if output_profile == 'sdk'}}
    Preserve API/internal/SPI and consumer compatibility boundaries, and deliver stability
    metadata, documentation, executable examples, and consumer migration guidance.
{{/if}}
{{#if output_profile == 'cli'}}
    Preserve command/config/stream/exit/package contracts with only justified internal ports.
{{/if}}
    Target annotations, frameworks, and package conventions may not leak into profile-neutral
    policy or public contracts unless the selected profile explicitly makes them part of the
    product.

    Before continuing, enumerate every persistent target path the slice may create or change,
    including sources, tests, build definitions and launchers, dependency metadata, generated
    sources, project-local caches, reports, and packaged output. Resolve each path from the
    project root and require it to remain beneath `{target_root}`. Any alternate build root
    requires an accepted orchestration decision that lists the outside-target paths,
    ownership, command working directory, and rollback; an existing directory alone is not
    authorization.

### Step 3: Define Delivery, Coexistence, and Recovery

11. Describe the slice's independently releasable boundary in concrete terms: artifact or
    deployable unit, selector/routing mechanism, consumer cohort, state ownership, and
    observable success/failure signals.
12. Define coexistence before implementation: how legacy remains available, how the selected
    boundary chooses legacy or target, how shadow execution isolates side effects, how any
    mirrored state is ordered/idempotent/reconciled/recovered, and which evidence
    distinguishes paths and cohorts.
{{#if output_profile == 'service'}}
    Use a route, protocol facade, message/worker selector, or similarly observable service
    boundary and record target-versus-legacy telemetry.
{{/if}}
{{#if output_profile == 'library'}}
    Use a compatibility facade, parallel namespace/version, or consumer binding and track
    consumer adoption separately from publication.
{{/if}}
{{#if output_profile == 'sdk'}}
    Use a compatibility layer/version selector and representative consumer applications;
    track documentation and supported-consumer adoption separately from publication.
{{/if}}
{{#if output_profile == 'cli'}}
    Use a launcher or shim selector and isolate/capture files, stdout, stderr, and exit status.
{{/if}}

13. Define a rollback procedure with trigger thresholds, operator/owner, maximum safe window,
    state/data reconciliation, exact selector reversal, and a verification command. “Revert
    the commit” is insufficient when consumers, traffic, schemas, or state have changed.
14. Define cutover preflight and human approval: required deterministic evidence, judgment
    findings, risk owner, approvers, change window, communication, and go/no-go criteria.
15. Define decommission obligations: adoption/traffic proof, retention window, data/archive
    needs, dependency removal, launcher/route cleanup, consumer notification, operational
    runbook updates, and post-removal verification. Cutover and decommission are separate.

### Step 4: Select Profile-Configured Gates

16. Start with the selected output profile's required quality gates and add behavior-specific
    gates. At minimum, each slice includes `behavioral-contracts`, `build`, and the applicable
    target tests; use the exact canonical compile command `{{compile_command}}` and configured
    test command `{{test_command}}`, both with the default project-root invocation
    `cd {target_root} && <command>`. Confirm the working directory, launcher, build definition,
    and expected report paths agree before approving the plan. An accepted orchestration
    decision must replace that invocation consistently in every affected gate and hook.
17. Add only applicable architecture, public/binary API, static analysis, dependency graph
    and integrity, security, changed-code coverage, documentation/examples, packaging,
    concurrency, performance, platform, or integration gates. Record exact commands,
    environment, expected artifacts, and pass conditions.
18. Coverage is one risk signal, not a universal completion claim. Use a project/profile
    approved changed-code or contract-coverage threshold where configured; never impose a
    blanket percentage or one-test-per-method rule. Every `BEH` must instead have a target
    test/evidence path or an approved exception.
19. Separate gate types explicitly:

    - migrate-verify will execute deterministic commands and append reproducible
      `EVID-NNNN` records; and
    - migrate-review will judge semantic fidelity, idiomatic {{target_language}} design,
      architecture intent, risk, and whether modernization is justified.

    A review opinion cannot replace a failed deterministic gate, and repeated command output
    is not a substitute for judgment review.

### Step 5: Write Plans and Traceability

20. Write `.migration/plans/SLICE-NNNN.json` using exactly the plan schema fields:

    ```json
    {
      "$schema": "schemas/plan.schema.json",
      "schema_version": "2.0",
      "id": "SLICE-NNNN",
      "status": "planned",
      "source_units": ["SRC-NNNN"],
      "behavioral_contracts": ["BEH-NNNN"],
      "target_units": ["TGT-NNNN"],
      "dependencies": [],
      "release_boundary": "Independently selectable delivery boundary",
      "rollback": "Tested selector and state recovery procedure",
      "verification_gates": ["behavioral-contracts", "build", "tests"],
      "approval_refs": []
    }
    ```

21. Write `.migration/plans/SLICE-NNNN.md` as the ID-bearing executable detail view with:

    - objective and behavior/evidence/source/target/test trace matrix;
    - exact project-root-relative target files, build/tooling files, generated outputs, and
      output-profile boundary constraints;
    - dependency selections and prerequisites;
    - ordered implementation tasks small enough to audit and retry;
    - target test strategy derived from behavior contracts and supported variants;
    - deterministic gate commands and expected artifacts;
    - coexistence, cutover preflight, rollback rehearsal, and decommission tasks;
    - accepted decisions/exceptions and forbidden scope; and
    - risk owner, approval gate, and block/failure escalation criteria.

22. Update each covered trace to `planned`, preserving characterization evidence and adding
    the slice's target/test/decision/exception references. Do not mark implementation or
    verification complete in advance.
23. Check that all plan source, behavior, target, dependency, decision, exception, and
    evidence IDs resolve; no target file is written by two concurrently executable slices;
    and no slice depends on a later or nonexistent plan.
24. Present the slice boundary, risk, gates, coexistence, rollback, and exclusions for human
    planning approval. If approval or a dependency is missing, transition to `blocked` with
    a scoped exception and `resume_to: "plan"`; planning/validator failure transitions to
    `failed` with a scoped `quality-gate` exception, recovery action, and the same resume state.
25. Stage plan JSON/Markdown, traceability, and state together; validate and promote
    atomically. Set `active_slice` to the human-confirmed ready slice (whose plan status is
    still `planned`), apply `plan -> execute`, and recommend migrate-execute with that ID.

## Outputs

- `.migration/plans/SLICE-NNNN.json` — schema-valid dependency-seam slice plan.
- `.migration/plans/SLICE-NNNN.md` — executable implementation, gate, release, and recovery view.
- `.migration/traceability.json` — in-scope links advanced to `planned`.
- `.migration/decisions/DEC-NNNN.json` and `.migration/exceptions/EXC-NNNN.json` as required.
- `.migration/state.json` — active slice and validated transition to `execute`, `blocked`, or
  `failed`.

## Success Criteria

- Every slice is independently buildable, testable, observable, selectable/releasable, and
  reversible at a real dependency seam; grouping is not based on file/package waves.
- Every planned source/behavior has characterization evidence and stable source, target,
  test, decision, exception, and evidence traceability as applicable.
- Architecture and gates come from the selected output profile without universal service or
  hexagonal assumptions.
- Unsupported scope, dead code, intentional change, and undefined/implementation-defined
  behavior have explicit policy records, owners, approvals, and mitigation.
- Coexistence, cutover preflight, rollback, and decommission obligations are executable and
  risk-owned.
- Planned target and build/tooling paths remain beneath `{target_root}`, or an accepted
  orchestration decision explicitly owns every exception and alternate command directory.
- Verification commands and judgment review criteria are separate and explicit.
- Plan JSON, dependency DAG, traceability, and state validate atomically; successful state
  ends in `execute` with exactly one active slice.
