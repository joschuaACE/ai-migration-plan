# Migration State Artifacts

The `.migration/` directory is a versioned, machine-validated record of discovery,
decisions, execution, and evidence. Markdown may explain a decision or finding, but
workflow state and cross-references live in schema-valid structured artifacts.

## Required Artifact Classes

| Artifact | Responsibility | Stable identifiers |
|---|---|---|
| `config.json` | Framework/schema versions, selected profiles, roots, strategy, strictness, and project decisions | Profile and decision references |
| `state.json` | Current lifecycle state, active slice, transition history, blockers, and validation status | Transition and slice IDs |
| `inventory.json` | Source units, build variants, public surfaces, dependencies, platforms, and reachability | Source-unit and build-variant IDs |
| `behaviors/*.json` | Characterized inputs, outputs, errors, side effects, concurrency, and known evidence gaps | Behavior and contract IDs |
| `decisions/*.json` | Architecture, compatibility, divergence, dependency, and strategy decisions | `DEC-0001` style IDs |
| `plans/*.json` | Dependency-seamed slices, prerequisites, acceptance gates, coexistence, rollback, and decommission tasks | `SLICE-0001` style IDs and gate IDs |
| `traceability.json` | Links among source units, behaviors, target units, tests, decisions, exceptions, and evidence | Trace-link IDs plus referenced IDs |
| `exceptions/*.json` | Waivers, unsupported behavior/platforms, blockers, owners, approvals, and expiry/exit criteria | `EXC-0001` style IDs |
| `evidence/*.json` | Immutable validator runs and review records | `EVID-0001` style IDs and review IDs |

Profiles may require additional artifacts, but they may not overload these meanings. Large
command outputs belong under `evidence/` and are referenced by checksum; they do not belong
inline in state history.

Every structured artifact includes at least `schema_version`. Configuration also records
`framework_version`, source and target profile IDs, pair ID, output-profile ID, migration
strategy, `{source_root}`, `{target_root}`, and its last validation result.

## Identity and Cross-Reference Rules

- IDs are stable after creation and unique within their artifact class.
- Renaming a file or target unit does not change its ID.
- A reference to a missing or wrong-kind ID is a validation failure.
- Removing a record that is still referenced is forbidden; supersede it instead.
- Every completion claim links at least one source behavior to a target unit and passing
  evidence, or to an approved intentional-divergence/removal decision.
- Evidence records are append-only. A later run supersedes an earlier result without
  rewriting the historical result.
- Timestamps are UTC RFC 3339 values and are never used as identity.

## Lifecycle State Machine

The normal lifecycle is:

```text
initialize
    -> discover
    -> characterize
    -> map
    -> plan
    -> execute
    -> verify
    -> review
    -> approve
    -> cut_over
    -> decommissioned
```

`approve` means the slice is eligible for its recorded cutover; it does not mean traffic,
consumers, or data have already moved. `decommissioned` requires post-cutover evidence and
completion of the slice's decommission action. The final slice also requires approval that
the legacy path may be removed.

### Exceptional Transitions

Any active state may enter `blocked` or `failed`:

- `blocked` means progress requires a named decision, dependency, approval, or external
  condition. State records `resume_to` and `blocked_by` exception IDs; the referenced
  exception records owner, cause, attempted mitigations, and exit criterion.
- `failed` means a validator, execution, or cutover operation failed. State records
  `resume_to` and references the failure exception/evidence; those records hold rollback
  status and recovery action.
- Resume is a transition event, not a lifecycle state or a shortcut to the next stage. It
  first validates all state, resolves or supersedes the blocker/failure, and returns to
  `resume_to` or an explicitly earlier safe state.

Skipping a normal state requires a profile-authorized transition plus a decision record.
File presence, a commit, or a prior review comment is never enough to infer a transition.

## Transition Record

`state.json` increments `revision` and stores the transition in both `last_transition` and
append-only `history`:

```json
{
  "from": "verify",
  "to": "review",
  "at": "2026-01-15T14:30:00Z",
  "reason": "Required deterministic gates passed for SLICE-0003"
}
```

Gate, decision, exception, review, and actor details remain in their typed artifacts and
`traceability.json`; validate those references before applying the transition. The applicable
state schema remains authoritative.

## Slice Completion Conditions

A slice cannot transition to:

- `execute` until required characterization and mapping references exist;
- `verify` until execution output and deviations are recorded;
- `review` until all deterministic gates have evidence or approved exceptions;
- `approve` until judgment findings are resolved or explicitly accepted;
- `cut_over` until the cutover and rollback procedures pass preflight; or
- `decommissioned` until post-cutover acceptance passes and decommission obligations are met.

## Validation and Recovery

Validate every artifact before and after a transition. A writer stages all related
changes, validates the complete state set, and promotes them atomically. On failure, retain
the prior valid state and store diagnostics outside the authoritative artifact set.

On resume:

1. validate schema versions and profile compatibility;
2. validate all references and evidence checksums;
3. compare the workspace with the last recorded generated and target artifacts;
4. identify the last valid transition and any incomplete operation;
5. record recovery or rollback evidence; and
6. resume only through a valid state transition.

## Narrative Files

Human-readable research, rationale, and reports may be stored alongside structured state.
They must carry the stable IDs they discuss. Narrative checkboxes or headings are views;
they are not authoritative status.

## Rule Provenance

Shared metadata: `source` is `framework.json` plus the repository-owned migration-state
schemas; `owner` is the generic framework profile. Row applicability is explicit below.

| Rule ID | Rationale | Applies when | Enforcement | Required evidence | Reviewed for |
|---|---|---|---|---|---|
| `GEN-STATE-001` | Stable identifiers keep traceability intact across file and package changes. | Every state artifact | Schema and reference validation | Valid cross-reference graph | Framework schema v2 |
| `GEN-STATE-002` | Approval and cutover are distinct risk events. | Every releasable slice | State-machine validation | Review approval, cutover preflight, and post-cutover result | Framework schema v2 |
| `GEN-STATE-003` | Partial state writes can falsely advance a migration. | Every state mutation | Staging and atomic promotion | Previous valid state or complete validated update | Framework schema v2 |
| `GEN-STATE-004` | Presence of output does not prove successful execution. | Resume and completion checks | Evidence-reference validation | Validator result with checksum and environment | Framework schema v2 |
