# Migration Philosophy

Migration is an evidence-driven change to a running contract, not a syntax-conversion
exercise. These principles apply to every language pair and output profile.

## Non-Negotiable Principles

1. **Discover before deciding.** Inventory all build variants, public surfaces,
   dependencies, platforms, tests, data formats, side effects, and runtime entry points.
2. **Characterize before translating.** Capture existing behavior with source tests,
   golden-master or differential tests where practical, API inventories, and explicit
   known gaps. Existing tests are evidence, not proof of complete behavior.
3. **Translate in reversible slices.** Select a dependency seam with an enablement and
   rollback path. Keep both implementations able to coexist until acceptance evidence is
   sufficient for the slice's risk.
4. **Make every difference explicit.** Preserve observable behavior by default. Record
   intentional changes, unpreservable behavior, and accepted risk before declaring a
   slice complete.
5. **Trace every completion claim.** A source unit and behavior must link to its target
   unit, tests, decisions, exceptions, and verification evidence.
6. **Separate verification from review.** Verification runs reproducible checks and
   records their outputs. Review applies judgment to semantic fidelity, idiomatic design,
   and justified modernization. Neither substitutes for the other.
7. **Prefer the smallest sufficient mechanism.** Reuse a selected platform capability or
   dependency when it satisfies the contract. Add new code or dependencies only after the
   behavioral and operational need is demonstrated.
8. **Close the declared denominator.** Structural validity and slice approval are not project
   completion. Report accounted and migrated scope separately, force another plan while work
   remains, and require current global certification before final cutover or decommission.

## Observable Compatibility

Compatibility is evaluated at observable boundaries, including:

- accepted and rejected inputs;
- returned values, emitted events, files, messages, and other side effects;
- error categories, partial-failure behavior, and retry visibility;
- ordering, atomicity, idempotency, and concurrency guarantees;
- numeric, encoding, locale, time-zone, and serialization behavior;
- resource and performance constraints that are part of a documented service level; and
- public source, binary, or protocol compatibility promised to consumers.

Representation may change when it is not observable. A difference is not acceptable
merely because the target runtime makes it convenient.

## Required Dispositions for Difficult Source Behavior

Every discovered behavior receives one of these dispositions:

| Disposition | Meaning | Required record |
|---|---|---|
| `preserve` | The target must reproduce the observed contract. | Behavior mapping and verification evidence |
| `normalize` | Multiple legacy outcomes become one intentional target outcome. | Approved divergence and consumer-impact analysis |
| `remove` | Proven dead or unreachable behavior will not migrate. | Reachability evidence and approval |
| `defer` | The behavior remains on the legacy path for a later slice. | Owner, dependency, and exit criterion |
| `block` | No safe implementation or coexistence path is known. | Blocker, attempted mitigations, and escalation owner |

`remove` and retained/deferred legacy behavior may be accounted under an approved scope policy,
but they are not migrated. Strict 100% migrated scope permits no removal, retention, deferral,
stored pending disposition, audit-derived unknown gap, or unverified item.

Undefined, unspecified, implementation-defined, or environment-dependent source behavior
must not be labeled equivalent without evidence. Capture the actually observed behavior
and environments, then choose `preserve`, `normalize`, or `block`. A test that happens to
pass on one machine does not make an undefined contract portable.

## Decision Ladder

After the behavior is understood, stop at the first option that fully meets the contract:

1. Prove the code is unreachable or no longer required, then remove it through the
   dead-code policy.
2. Use a capability supplied by the selected target or output profile.
3. Use the target platform's standard capabilities.
4. Reuse an already approved dependency.
5. Add a compatible dependency with ownership, security, licensing, and lifecycle evidence.
6. Implement the minimum custom mechanism that satisfies the characterized behavior.

The ladder is not permission to redesign silently. Record any option that changes an
observable behavior or public compatibility promise.

## Evidence Gates

A slice may advance only when the evidence required by its risk and profiles exists.
Typical gates combine:

- behavioral-contract and differential test results;
- changed-code coverage or mutation evidence where useful;
- compilation, packaging, static analysis, and architecture checks;
- dependency and supply-chain checks;
- operational or performance evidence for affected service levels; and
- unresolved exception and decision approvals.

Do not use universal coverage percentages or require a test for every method. Configure
thresholds by profile and project risk, and explain what behavior each gate protects.
Passing slice gates advances that slice only. Final cutover and decommission additionally
require migrate-audit to reconcile the complete declared source census, actual target inventory,
traceability, slice approvals, cutover union, consumers, and asset dispositions.

## Human Approval Gates

Human approval is mandatory before:

- accepting an intentional behavioral divergence;
- normalizing uncertain or implementation-dependent behavior;
- dropping a supported dependency, platform, or public API;
- crossing a high-risk data, security, or irreversible cutover boundary;
- waiving a required validator; or
- decommissioning the final legacy path.

Human approval cannot turn missing evidence, unknown scope, retained source, or an approved
removal into migrated scope. Approval selects a documented policy disposition; the completion
report must still show its category and exclude it from the migrated numerator.

## Rule Provenance

Shared metadata: `source` is the framework v3 migration/evidence policy;
`owner` is the generic framework profile. Row applicability is explicit below.

| Rule ID | Rationale | Applies when | Enforcement | Required evidence | Reviewed for |
|---|---|---|---|---|---|
| `GEN-MIG-001` | Translation without characterization hides semantic drift. | Before execution | Lifecycle validator | Behavior inventory and characterization evidence | Framework schema v2 |
| `GEN-MIG-002` | Difficult source behavior needs an explicit policy rather than a false equivalence claim. | Behavior is uncertain, dead, changed, or deferred | Disposition and cross-reference validation | Decision, exception, or reachability evidence | Framework schema v2 |
| `GEN-MIG-003` | Deterministic checks and human judgment answer different questions. | Verification and review | State-transition validation | Separate verification and review records | Framework schema v2 |
| `GEN-MIG-004` | Uniform coverage quotas are poor proxies for behavioral confidence. | Quality-gate selection | Profile composition validation | Configured gates with rationale | Framework schema v2 |
| `GEN-MIG-005` | Slice completion and structural validity do not close a whole-product denominator. | Approval, final cutover, and decommission | Global completion audit | Current implementation/decommission certificate and exact counts | Framework schema v3 |
