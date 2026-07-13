# Incremental Modernization Strategy

Incremental replacement is the default strategy. A big-bang replacement is permitted
only through an explicit decision that explains why safe coexistence is impossible or
more dangerous.

This guidance follows the gradual replacement model commonly called the
[Strangler Fig pattern](https://martinfowler.com/bliki/StranglerFigApplication.html),
but the seam may be an API, command, message, file format, library facade, data owner, or
process boundary rather than a network route.

## Choose the Seam

Select a seam that has observable behavior, bounded dependencies, and independent release
or enablement. For each candidate, record:

- callers and consumers;
- inputs, outputs, state, side effects, and error paths;
- shared data and consistency requirements;
- traffic or invocation routing mechanism;
- characterization evidence and known gaps;
- blast radius and security implications; and
- how to disable the target path without losing accepted work.

Prioritize a slice with high learning value and controlled blast radius. Do not begin
with a foundational component merely because it has few dependencies if its behavior
cannot be observed independently.

## Establish a Replacement Boundary

Introduce the smallest boundary capable of directing an invocation to the legacy or
target implementation. Preserve the consumer-facing contract while both paths coexist.
Possible mechanisms include a facade, compatibility adapter, feature flag, traffic router,
plugin selector, dual-read harness, or build-time binding.

The boundary must not conceal divergent semantics. It records which path handled each
verification case and exposes enough telemetry or test output to compare results.

## Coexistence Modes

| Mode | Use | Safety condition |
|---|---|---|
| Offline differential | Replay captured or generated cases through both paths. | Inputs are safe to replay; outputs can be normalized and compared. |
| Shadow | Legacy remains authoritative while target observes equivalent input. | Target side effects are disabled or isolated. |
| Dual read | Read both, return the authoritative result, compare in background. | Reads are side-effect free or controlled. |
| Mirrored write | Write both systems during transition. | Idempotency, ordering, reconciliation, and partial-failure policy are proven. |
| Routed cohort | Send a bounded consumer or traffic cohort to the target. | Cohort is identifiable, monitored, and reversible. |
| Build-time coexistence | Consumers choose legacy or target artifact at build/link time. | Compatibility suite runs against both choices. |

Never dual-write merely to increase confidence. Shared mutation is a data migration with
its own consistency, recovery, and ownership design.

## Cutover Contract

Before cutover, record:

- the exact scope and authoritative path before and after;
- readiness gates and who approves them;
- configuration, routing, packaging, or deployment changes;
- data synchronization or quiescence procedure;
- monitoring signals, observation window, and abort thresholds;
- operator responsibilities and communication needs; and
- the tested rollback procedure and maximum safe rollback window.

Cut over one independently reversible scope at a time. Preserve the legacy path until
the observation window passes unless retaining it would itself create unacceptable risk.

## Rollback

Rollback is an executable procedure, not “revert the commit.” It must account for data,
messages, caches, generated artifacts, consumer versions, and irreversible side effects.

Classify each change:

- **reversible:** route or bind back without data repair;
- **reconcilable:** route back after an explicit data/message reconciliation step; or
- **irreversible:** requires forward recovery and a higher approval gate.

Test rollback under representative failure conditions before production cutover. Record
the test as evidence and keep the procedure versioned with the slice.

## Decommissioning

Decommission only after:

- all supported consumers use the target path;
- the observation window and acceptance gates pass;
- rollback retention requirements expire or a forward-recovery plan replaces them;
- data ownership and archival obligations are resolved;
- old dependencies, credentials, routes, jobs, dashboards, and alerts are inventoried;
- licenses, binaries, and platform-specific deployment assets are removed deliberately; and
- a human approves the final loss of the legacy fallback.

Removal evidence links back to the source units and behaviors it retires. “No recent
traffic” alone is not proof that a public path is unreachable.

## Strategy Exceptions

If a big-bang strategy is selected, the decision must show:

- why no bounded seam supports coexistence;
- complete rehearsal and rollback or forward-recovery evidence;
- consumer coordination and downtime assumptions;
- data migration and reconciliation proof; and
- a named approval authority accepting the enlarged blast radius.

## Rule Provenance

Shared metadata: `source` is the framework v3 safety policy and the linked Strangler Fig
pattern description; `owner` is the generic framework profile. Row applicability is explicit below.

| Rule ID | Rationale | Applies when | Enforcement | Required evidence | Reviewed for |
|---|---|---|---|---|---|
| `GEN-STRAT-001` | Incremental routing limits blast radius and creates earlier evidence. | Strategy selection | Decision validation | Seam analysis or approved big-bang exception | Framework schema v2 |
| `GEN-STRAT-002` | Duplicate side effects can corrupt state while appearing equivalent. | Shadowing or dual writes | Plan and review checks | Side-effect isolation, idempotency, and reconciliation evidence | Framework schema v2 |
| `GEN-STRAT-003` | Source control rollback does not reverse external state. | Every cutover | Cutover preflight | Tested operational rollback or forward-recovery plan | Framework schema v2 |
| `GEN-STRAT-004` | Legacy removal destroys the final fallback and may strand unknown consumers. | Decommission | Human approval gate | Consumer, operations, data, and reachability evidence | Framework schema v2 |
