# migrate-decommission

Retire the legacy path only after target cutover evidence, consumer adoption, observation,
retention, data, and recovery obligations are satisfied. Decommissioning is the terminal,
human-approved loss of the legacy fallback.

## When to Use

After a successful cutover has remained in `state.json.status: cut_over` for the required
observation and rollback-retention period. Do not use while any supported consumer, platform,
route, job, data owner, or recovery procedure still depends on the legacy path.

## Inputs

- **Decommission scope** (required) — stable source, behavior, dependency, platform, route,
  credential, data, artifact, and operational asset IDs.
- **Final approval references** (required) — named product, technical, operational, security,
  data, and compliance owners as applicable.
- **Retention/archive policy** (required) — what is deleted, archived, or retained and why.

Required evidence includes passing cutover records, consumer/traffic inventory, observation
window, incident/rollback history, reconciliation, legal/data retention, credential ownership,
and a forward-recovery plan after fallback removal.

## Procedure

1. Validate `.migration/` and prove all supported consumers use the target. “No recent traffic”
   alone is not reachability evidence.
2. Confirm every scoped trace is approved or excepted and links target verification plus
   cutover evidence. Resolve any dangling source, behavior, target, test, decision, exception,
   or evidence reference before removal.
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
   Record them as `EVID-NNNN` with `phase: decommission` and the relevant slice.
9. Update traceability and archival locations, validate all remaining references, then atomically
   transition `cut_over → decommissioned`. Preserve the audit record required by policy.

## Outputs

- Passing `.migration/evidence/EVID-NNNN.json` records with `phase: decommission`.
- Final asset disposition, consumer, data, credential, dependency, and recovery record.
- Updated traceability pointing to retained target and archival evidence.
- Terminal schema-valid `state.json` with `status: decommissioned`.

## Success Criteria

- No supported consumer or operational process depends on the retired path.
- Data, credentials, dependencies, platforms, licenses, routes, jobs, dashboards, and archives
  have explicit owners and validated dispositions.
- Final target and forward-recovery gates pass after removal.
- Named humans approved the irreversible loss of fallback.
- All evidence and traceability validate, and the lifecycle ends at `decommissioned` without
  a hidden legacy runtime or falsely completed exception.
