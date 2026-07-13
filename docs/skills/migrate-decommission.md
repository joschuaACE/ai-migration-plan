# migrate-decommission

Retire the legacy path only after target cutover evidence, consumer adoption, observation,
retention, data, and recovery obligations are satisfied. Decommissioning is the terminal,
human-approved loss of the legacy fallback.

## When to Use

After the union of successful cutovers covers the whole declared scope and final cutover has
remained in `state.json.status: cut_over` for the required observation and rollback-retention
period. Do not use while any declared source item, supported consumer, platform, route, job,
data owner, or recovery procedure still depends on the legacy path. Bounded-slice legacy
removal is not terminal decommission.

## Inputs

- **Whole declared decommission scope** (required) — every stable source, behavior, dependency,
  platform, consumer, route, credential, data, artifact, and operational asset ID in the
  migration denominator. A subset cannot transition global state to `decommissioned`.
- **Final approval references** (required) — named product, technical, operational, security,
  data, and compliance owners as applicable.
- **Retention/archive policy** (required) — what is deleted, archived, or retained and why.

Required evidence includes passing cutover records, consumer/traffic inventory, observation
window, incident/rollback history, reconciliation, legal/data retention, credential ownership,
and a forward-recovery plan after fallback removal.

## Procedure

1. Structurally validate the current artifacts and run a whole-scope audit:

   ```bash
   python3 .migration-framework/bin/migrationctl.py validate .migration
   python3 .migration-framework/bin/migrationctl.py audit .migration --claim <accounted|migrated>
   ```

   Prove all supported consumers use the target. “No recent traffic” alone is not reachability
   evidence. Structural validation or an implementation-stage certificate alone cannot
   authorize terminal state.
2. Confirm every declared trace is approved or policy-compatible excepted and links target
   verification plus successful cutover evidence. The union of cutover evidence must cover all
   required behaviors, consumers, routes, data owners, platforms, and products. Resolve any
   dangling or remaining source, behavior, target, test, plan, decision, exception, evidence,
   pending, unknown, retained, removed, or unverified item according to the exact completion
   policy before removal. Strict migrated mode requires every such non-migrated count to be zero.
3. Inventory legacy executables/libraries, source/build targets, routes, DNS/service discovery,
   queues/jobs, databases/files, schemas, feature flags, credentials/secrets, licenses, native
   dependencies, dashboards, alerts, runbooks, deployment assets, and support documentation.
4. Classify each asset as remove, archive, transfer, or retain. Record data migration,
   reconciliation, retention, deletion, audit, and ownership evidence.
5. Rehearse decommission and forward recovery in a safe environment. Verify target restoration,
   backup, incident response, and consumer communication no longer assume the legacy fallback.
6. Obtain explicit final approval acknowledging that route-back will no longer be available.
7. Execute removal in bounded, observable steps. Stop on unexpected consumers, integrity gaps,
   security regressions, or failed target health signals; transition to `blocked`/`failed` and
   do not claim decommission completion.
8. Run final target behavioral, packaging, dependency, security, and operational smoke gates.
   Record one v3 `EVID-NNNN` per reproducible gate with `phase: "decommission"`, one exact
   `command`, one `working_directory`, integer `exit_code`, environment, linked contracts, and
   artifact path/SHA-256 pairs.
9. Update traceability, target inventory, source dispositions, consumer/asset dispositions, and
   archival locations. Refresh workspace snapshots, then structurally validate and rerun the
   whole-scope audit.
10. Create the mandatory terminal certificate only after all removals and final gates are
    represented in the current digests:

    ```bash
    python3 .migration-framework/bin/migrationctl.py snapshot .migration --project-root .
    python3 .migration-framework/bin/migrationctl.py certify .migration --claim <accounted|migrated> --stage decommission
    ```

    Reject a missing, failing, stale, wrong-claim, or wrong-stage certificate. A certificate
    created before subsequent removal or state mutation is stale.
11. While the decommission-stage certificate remains current, atomically transition the whole
    migration to terminal state:

    ```bash
    python3 .migration-framework/bin/migrationctl.py transition --migration .migration --to decommissioned --reason "Whole declared scope passed decommission certification"
    ```

    The guarded command validates the pre-transition authorization and atomically reissues the
    certificate against the terminal state revision and digest, so the transition cannot make
    its own proof stale. Preserve the audit and certificate records required by policy.

## Outputs

- Passing `.migration/evidence/EVID-NNNN.json` records with `phase: decommission`.
- Final asset disposition, consumer, data, credential, dependency, and recovery record.
- Updated traceability pointing to retained target and archival evidence.
- Current `.migration/completion-certificate.json` for the selected claim and
  `stage: "decommission"`.
- Terminal schema-valid `state.json` with `status: decommissioned`.

## Success Criteria

- No supported consumer or operational process depends on the retired path.
- Every declared source, behavior, target, test, plan, cutover scope, consumer, and legacy asset
  is included in the terminal audit; a subset cannot produce terminal state.
- Data, credentials, dependencies, platforms, licenses, routes, jobs, dashboards, and archives
  have explicit owners and validated dispositions.
- Final target and forward-recovery gates pass after removal.
- Named humans approved the irreversible loss of fallback.
- All evidence and traceability validate, and the lifecycle ends at `decommissioned` without
  a hidden legacy runtime or falsely completed exception.
- The terminal transition is backed by a passing current decommission-stage certificate. Strict
  migrated mode has zero pending, unknown, retained, removed, and unverified items.
