# migrate-cutover

Execute a separately approved, observable, and reversible cutover from legacy handling to
the verified target for the declared scope. Cutover is an operational gate, not a synonym
for merging code or finishing review.

## When to Use

After all source behaviors in the bounded cutover scope are `approved` or policy-compatible
`excepted`, every included slice is in `state.json.completed_slices`, and the lifecycle is
`approve`. Use only within the approved change window and authority recorded by the project.
Final cutover additionally requires a current passing implementation-stage completion
certificate for the exact claim. A partial cutover never authorizes terminal decommission.

## Inputs

- **Cutover scope** (required) — stable behavior, consumer/cohort, route, artifact, command,
  or data-owner IDs that change authority.
- **Approval references** (required) — named human and operational/security approvals.
- **Observation window** (required) — duration, signals, thresholds, and owner.
- **Cutover kind** (required) — `partial` when declared implementation work or legacy authority
  remains, or `final` when this scope closes the complete declared cutover union.
- **--dry-run flag** (recommended first) — rehearse checks and commands without changing authority.

Required context includes approved plans/reviews, passing verification evidence, current
traceability, authoritative-path definition, synchronization/quiescence procedure, tested
rollback or forward-recovery procedure, abort thresholds, and communication plan.

## Procedure

1. Structurally validate the current `.migration/` artifact graph:

   ```bash
   python3 .migration-framework/bin/migrationctl.py validate .migration
   ```

   Confirm the proposed bounded scope has no `planned`, `implemented`, or merely `verified`
   trace links. This scope-local and structural result is not whole-scope completion.
2. Run the whole-scope progress audit and report exact remaining IDs:

   ```bash
   python3 .migration-framework/bin/migrationctl.py audit .migration --claim <accounted|migrated>
   ```

   If this is a final cutover, require zero remaining implementation work and a current passing
   `.migration/completion-certificate.json` with the exact claim and
   `stage: "implementation"`. Reject missing, stale, failing, wrong-claim, or progress-only
   certification. If work remains, label this cutover `partial` and preserve the return-to-plan
   path.
3. Confirm source and target revisions, configuration, dependency health, capacity, security,
   telemetry, on-call ownership, data consistency, and rollback window still match the approved
   evidence. Stale evidence blocks cutover.
4. Rehearse the exact route/binding/deployment/data commands with `--dry-run` or in a production-
   representative environment. Verify rollback does not duplicate or lose accepted work.
5. Create one cutover `EVID-NNNN` v3 skeleton per reproducible operation with `phase:
   "cut_over"`, the approved slice ID, one exact `command`, one `working_directory`, initial
   failing `exit_code`/status, environment, linked contracts, and expected artifact paths. Each
   successful artifact record later includes its SHA-256. The untouched skeleton is not passing.
6. At the approved start, route by kind:

   - **partial:** keep global lifecycle state at `approve` while executing the bounded cohort/
     route operation and recording `phase: "cut_over"` evidence;
   - **final:** only with the current passing implementation-stage certificate, transition
     `approve -> cut_over`, then execute the final bounded authority change.

   Apply the final transition through the guarded runtime, never by editing `state.json`:

   ```bash
   python3 .migration-framework/bin/migrationctl.py transition --migration .migration --to cut_over --reason "Whole declared implementation scope is certified for final cutover"
   ```

   The command validates the pre-transition certificate and atomically reissues it against the
   incremented state revision. Later cutover evidence changes make that implementation
   certificate stale, as expected; decommission requires a fresh certificate for its own stage.

   Record exact results, operator identity, configuration revisions, and telemetry checkpoints.
7. Observe the declared signals for the full window. Do not expand the cohort while an abort
   signal, unexplained semantic delta, reconciliation gap, or dependency regression exists.
8. On success, set each evidence record's exact `exit_code`, status, and checksummed artifacts;
   update traceability authority and the accumulated union of successful cutover scopes.
   Then route by kind:

   - **partial:** after its observation requirements pass, keep state at `approve`, run the
     global audit, and transition `approve -> plan` whenever declared work remains;
   - **final:** keep state at `cut_over` for the final decommission observation/retention period.

   A successful partial cutover is not described as decommissioned or complete.
9. On a safe rollback, execute the rehearsed procedure, record evidence, and return affected
   trace links to the last truthful status. A partial rollback leaves global state at `approve`;
   a final rollback transitions `cut_over -> approve`. On an uncertain or irreversible failure,
   transition to `failed` or `blocked` with explicit scope.
10. Validate and atomically promote evidence, traceability, and state changes. Never edit only
   the route and reconstruct evidence later.

## Outputs

- `.migration/evidence/EVID-NNNN.json` with `phase: cut_over` and pass/fail outcome.
- Updated traceability evidence links and authoritative-path notes.
- `state.json` remaining at `approve` through successful partial cutover, at `approve` after
  final rollback, `cut_over` after
  successful final cutover, or explicit `blocked`/`failed`.
- Operational record of scope, commands, approvers, signals, observation window, and result.

## Success Criteria

- Scope and authority are explicit, approved, and limited to fully approved behaviors.
- Final cutover has a current passing implementation-stage certificate and is the only cutover
  that enters global `cut_over`; partial cutover is explicitly labeled, keeps state at
  `approve`, and returns workflow control to remaining planning.
- Cutover and rollback commands were rehearsed and executed by authorized operators.
- Data, side effects, consumers, security, dependency health, and telemetry meet thresholds.
- Passing evidence is reproducible and linked; failures and rollbacks remain visible.
- Legacy fallback remains available until decommission retention criteria are met.
- The union of successful cutover scopes and all remaining consumers/routes is reported, so a
  bounded success cannot masquerade as whole-scope completion.
