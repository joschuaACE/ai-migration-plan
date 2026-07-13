# migrate-cutover

Execute a separately approved, observable, and reversible cutover from legacy handling to
the verified target for the declared scope. Cutover is an operational gate, not a synonym
for merging code or finishing review.

## When to Use

After all source behaviors in the cutover scope are `approved` or `excepted`, every included
slice is in `state.json.completed_slices`, and the lifecycle is `approve`. Use only within the
approved change window and authority recorded by the project.

## Inputs

- **Cutover scope** (required) — stable behavior, consumer/cohort, route, artifact, command,
  or data-owner IDs that change authority.
- **Approval references** (required) — named human and operational/security approvals.
- **Observation window** (required) — duration, signals, thresholds, and owner.
- **--dry-run flag** (recommended first) — rehearse checks and commands without changing authority.

Required context includes approved plans/reviews, passing verification evidence, current
traceability, authoritative-path definition, synchronization/quiescence procedure, tested
rollback or forward-recovery procedure, abort thresholds, and communication plan.

## Procedure

1. Validate the complete `.migration/` graph and confirm the proposed scope has no `planned`,
   `implemented`, or merely `verified` trace links.
2. Confirm source and target revisions, configuration, dependency health, capacity, security,
   telemetry, on-call ownership, data consistency, and rollback window still match the approved
   evidence. Stale evidence blocks cutover.
3. Rehearse the exact route/binding/deployment/data commands with `--dry-run` or in a production-
   representative environment. Verify rollback does not duplicate or lose accepted work.
4. Create the cutover `EVID-NNNN` skeleton with `phase: cut_over`, the approved slice ID,
   commands, environment, linked behaviors, and expected artifacts. It is not passing yet.
5. At the approved start, transition `approve → cut_over`, then execute one bounded scope.
   Record exact results, operator identity, configuration revisions, and telemetry checkpoints.
6. Observe the declared signals for the full window. Do not expand the cohort while an abort
   signal, unexplained semantic delta, reconciliation gap, or dependency regression exists.
7. On success, mark cutover evidence passing and keep state at `cut_over` for the decommission
   observation/retention period.
8. On a safe rollback, execute the rehearsed procedure, record evidence, transition
   `cut_over → approve`, and return affected trace links to the last truthful status. On an
   uncertain or irreversible failure, transition to `failed` or `blocked` with explicit scope.
9. Validate and atomically promote evidence, traceability, and state changes. Never edit only
   the route and reconstruct evidence later.

## Outputs

- `.migration/evidence/EVID-NNNN.json` with `phase: cut_over` and pass/fail outcome.
- Updated traceability evidence links and authoritative-path notes.
- `state.json` at `cut_over`, `approve` after rollback, or explicit `blocked`/`failed`.
- Operational record of scope, commands, approvers, signals, observation window, and result.

## Success Criteria

- Scope and authority are explicit, approved, and limited to fully approved behaviors.
- Cutover and rollback commands were rehearsed and executed by authorized operators.
- Data, side effects, consumers, security, dependency health, and telemetry meet thresholds.
- Passing evidence is reproducible and linked; failures and rollbacks remain visible.
- Legacy fallback remains available until decommission retention criteria are met.
