# migrate-resume

Restore migration context from validated state, detect incomplete or unsafe work, and resume
through an allowed lifecycle transition without inferring progress from files or prose.

## When to Use

- At the start of a new session in a project containing `.migration/state.json`.
- After context compaction, interruption, pause, tool failure, or workspace recovery.
- When the user asks for status, continuation, or the exact next safe action.
- Before retrying work from `blocked` or `failed`.

## Inputs

- **No positional arguments** — reads `.migration/` from the current project.
- **--continue flag** (optional) — after reporting and validation, perform the recommended
  normal transition or dispatch the current workflow. Without it, migrate-resume is read-only.
- **--allow-source-change flag** (optional) — acknowledge source drift and return to the
  earliest affected lifecycle state through an explicit decision; never reuse stale evidence.

**Precondition:** `.migration/config.json` and `.migration/state.json` exist. Missing or
invalid state is reported; it is not reconstructed from target files, commits, or narrative
headings.

## Procedure

### Step 1: Validate Before Trusting State

1. Read `config.json`, `scope.json`, `state.json`, and `target-inventory.json`, then run:

   ```bash
   python3 .migration-framework/bin/migrationctl.py validate .migration
   ```

   Validate every JSON artifact, schema version, stable ID, cross-reference, evidence checksum,
   transition, and history chain in the current `.migration/` directory. This is structural
   current-state validation, not full-scope completion certification.
2. Confirm `state.status` equals the final `history` destination, `last_transition` equals
   the final history entry, and `revision` equals the number of completed transitions.
3. Confirm the framework/profile versions, output profile, migration strategy,
   `{source_root}`, `{target_root}`, and migration ID still match the workspace.
4. Compare the source revision and target/generated file ownership/checksums with the most
   recent valid artifacts. A timestamp alone neither proves activity nor indicates a stall.
5. If authoritative state is invalid or partially written, stop normal work. Locate the last
   complete valid snapshot/staging journal, retain diagnostics outside authoritative state,
   and restore atomically only through the framework recovery mechanism.

### Step 2: Restore State-Specific Context

6. Read only the context required by the current lifecycle state, plus config, scope policy and
   source dispositions, state, target inventory, active decisions/exceptions, traceability, and
   any completion certificate:

   | State | Required active context | Safe workflow |
   |---|---|---|
   | `initialize` | initialization templates and preflight | finish migrate-init |
   | `discover` | inventory and discovery research/checkpoint | migrate-detect |
   | `characterize` | uncovered source units, behaviors, source evidence, gaps | migrate-analyze |
   | `map` | behaviors/evidence, mapping, output-profile rules | migrate-map |
   | `plan` | unmapped/unplanned traces, slice DAG, mapping | migrate-plan |
   | `execute` | active plan, execution report, target ownership, prerequisites | migrate-execute, or migrate-verify after a valid handoff |
   | `verify` | active plan, configured gates, execution outputs, prior evidence | migrate-verify, or migrate-review when plan is verified |
   | `review` | deterministic evidence and unresolved judgment findings | migrate-review |
   | `approve` | review result, approvals, global audit, remaining slice DAG, certificate status | migrate-plan while work remains; otherwise migrate-audit before final cutover |
   | `cut_over` | final whole-scope record, telemetry, rollback, union coverage, and certificate status | monitor/rollback; audit before final decommission |
   | `decommissioned` | final evidence, decisions, retained archive | terminal; report only |
   | `blocked` | `resume_to`, `blocked_by` exceptions, owners, exit criteria | resolve then resume exactly |
   | `failed` | `resume_to`, failure diagnostics, rollback status, recovery action | recover then resume exactly |

7. For the active slice, summarize its stable source, behavior, target, test, decision,
   exception, and evidence IDs. Identify unresolved references instead of replacing them
   with path-based guesses.
8. Confirm prerequisites from the slice dependency DAG are approved as required. A present
   target file or commit is not proof that a dependency, gate, or slice completed.

### Step 3: Detect Incomplete Operations Safely

9. Compare the active plan tasks with the execution report, traceability, target-file
   checksums, staged writes, and last reversible checkpoint. Classify each task as recorded,
   safely retryable, externally uncertain, or complete with evidence.
10. Check for an interrupted dependency update, generator, state/data mutation, selector
    change, shadow/mirrored side effect, cutover, or decommission action. When external state
    is uncertain, stop and require reconciliation; do not rerun a potentially non-idempotent
    operation automatically.
11. If the lifecycle is `execute` or later and a target build exists, run
    `{{compile_command}}` from `{target_root}` as a diagnostic. Do not create authoritative
    gate evidence or advance state from this resume diagnostic; migrate-verify owns controlled
    deterministic verification.
12. Detect source drift by content revision/checksum, not elapsed time. If behavior-affecting
    source changed, identify impacted `SRC`, `BEH`, mapping, plan, and evidence IDs and return
    to the earliest affected state only with an explicit recovery decision. Stale evidence is
    marked superseded by a new append-only result, never rewritten.

### Step 4: Resolve Blocked or Failed State

13. For `blocked`, inspect every ID in `blocked_by`. Resume only after the named owner has met
    the exception's exit criterion, supplied the required dependency/decision/approval, or
    accepted a scoped policy exception with impact and mitigation.
14. For `failed`, confirm the failed operation stopped, target/external state is known, planned
    rollback or forward recovery completed, and the root cause has a concrete recovery action.
    Retain the failed diagnostic; a successful retry will append new evidence rather than
    overwrite history.
15. Validate all updated decisions, exceptions, recovery records, checksums, and references.
    The default recovery transition must return exactly to `state.resume_to`. Moving to an
    earlier safe lifecycle state requires an accepted recovery decision and a framework-
    validated state update; never jump ahead or clear `blocked_by` by hand.
16. With `--continue`, apply the validated `blocked|failed -> resume_to` transition, increment
    revision, append history, clear `resume_to` and resolved `blocked_by` references as one
    atomic state update, then dispatch the workflow for that state. Without `--continue`,
    report the required resolution and make no changes.

### Step 5: Determine the Next Safe Action

17. For a normal active state, continue its workflow at the first unrecorded safe checkpoint;
    do not re-run completed non-idempotent work. Key routing rules are:

    - `execute` with implemented trace and valid handoff -> run migrate-verify, which owns
      the validated `execute -> verify` transition;
    - `verify` with all required passing/waived deterministic evidence -> run migrate-review,
      which owns the validated `verify -> review` transition;
    - `review` with resolved findings and explicit human approval -> let migrate-review
      record plan approval and the `review -> approve` transition, then run a global audit;
    - `approve` -> run the installed audit command with `.migration` and the exact
      `accounted` or `migrated` policy claim before routing;
    - `approve` with any required work remaining -> mandatory `plan`; final cutover is forbidden;
    - `approve` with zero remaining work -> run migrate-audit certification; only a current
      passing implementation-stage certificate permits migrate-cutover to own
      `approve -> cut_over`;
    - partial cutover while state is `approve` -> record `phase: "cut_over"` observation
      evidence without entering global `cut_over`, then plan the remaining work;
    - `cut_over` with union cutover coverage complete -> run migrate-audit for a current
      decommission-stage certificate; and
    - `cut_over` with that certificate, post-cutover acceptance, asset dispositions, retention
      obligations, and final approval complete -> run migrate-decommission, which owns the
      whole-scope terminal transition.

18. A safely rolled-back final cutover returns `cut_over -> approve`; a partial rollback keeps
    state at `approve`. An uncertain or irreversible final-cutover failure enters `failed` with
    `resume_to: "cut_over"`. Execute the tested route/state
    recovery when trigger conditions require it, then record the outcome. Never describe
    approval as cutover or cutover as decommission.
19. Preserve the verification/review boundary: deterministic command results and checksums
    are `EVID` records; semantic fidelity, idiomatic design, architecture intent, and risk
    acceptance are judgment findings/approvals. Resume never converts one into the other.

### Step 6: Report a Traceable Status

20. Report at least:

    ```text
    Migration: <migration_id> (<source profile> -> <target profile>)
    Output profile / strategy: <profile> / <strategy>
    State / revision: <status> / <revision>
    Active slice: <SLICE ID or none>
    Scope: <accounted>/<declared>, <migrated>, <retained>, <removed>, <pending>, <unknown>
    Trace: <covered behaviors>/<required behaviors>, <implemented>, <verified>, <approved>, <cut over>
    Plans/targets/tests: <approved>/<required>, <verified>/<required>, <verified>/<required>
    Validation: <structural schema/reference/checksum result>
    Completion certificate: <missing|stale|failing|current, claim, stage>
    Blockers/failure: <EXC IDs, owners, exit criteria, rollback status>
    Last valid transition: <from -> to, reason, timestamp>
    Workspace diagnostic: <source drift, target build, incomplete/external operation>
    Next safe action: <workflow and stable IDs>
    ```

21. Do not report file-count similarity or an unqualified percentage as behavioral completion.
    Report accounted and migrated numerators separately. Completion claims require the global
    scope, source snapshot, target inventory, traceability, evidence, cutover union, and current
    certificate appropriate to the lifecycle stage; an approved exception alone is not migrated.
22. When the project configures `quality_gates.depth_policy`, run the depth analysis:

    ```bash
    python3 .migration-framework/bin/migrationctl.py continue .migration --project-root .
    ```

    Report the depth score, target/source ratio, and continuation status. If
    `continuation_needed` is true, include the top work items from the continuation plan in the
    status report and recommend targeted file-by-file translation before attempting
    re-certification. A migration whose lifecycle reached `cut_over` but whose depth score is
    below passing thresholds is a skeleton migration requiring substantial implementation work.
23. If `--continue` was supplied, show the exact transition/checkpoint performed and then
    continue with the selected workflow. Otherwise stop after the self-contained status and
    recommendation.

## Outputs

- By default, a read-only console report with validation, traceability, recovery, and next
  action; no files are created or changed.
- With `--continue`, one schema-valid atomic resume/normal transition and the selected
  workflow's own outputs.
- No fabricated state, overwritten evidence, implicit approval, cutover, or decommission.

## Success Criteria

- The current state graph, transition history, evidence checksums, profiles, and workspace
  ownership are structurally validated before any continuation, without presenting that result
  as full-scope completion.
- Context is restored by stable IDs and authoritative artifacts, not filenames, prose, or
  elapsed time.
- Interrupted and externally uncertain operations are detected and handled idempotently.
- Blocked/failed work resumes only after its scoped cause and recovery/rollback conditions
  are resolved, and only to the recorded safe state.
- The recommendation covers the full initialize-to-decommission lifecycle and distinguishes
  approval, cutover, rollback, and decommission.
- Approve-state routing uses global denominators: remaining work always returns to plan, while
  final cutover/decommission require current stage-specific completion certification.
- Deterministic verification evidence remains separate from judgment review.
- Default use is read-only; `--continue` performs only validated, traceable, atomic changes.
