# Migration Completeness

Migration completeness is a whole-scope claim. It is different from installing the framework,
initializing state, creating a target foundation, validating the current artifact graph, or
approving one migration slice. Those milestones may be necessary, but none proves that the
declared legacy product has been fully migrated.

## Completion Vocabulary

Use the narrowest truthful claim:

| Claim | Meaning | What it does not mean |
|---|---|---|
| Framework installed | Agent guidance, schemas, templates, hooks, and the installed CLI are available. | Discovery or migration has run. |
| Migration initialized | The roots, profiles, scope contract, empty inventories, and lifecycle state are structurally valid. | Any source behavior is characterized or implemented. |
| Target foundation present | Target build or architecture scaffolding exists. | The legacy scope is represented in the target. |
| Slice implemented | One approved slice has target code and tests. | Its gates passed or other slices are migrated. |
| Slice verified | Deterministic gates passed for one slice. | Judgment approval, cutover, or whole-scope closure. |
| Slice approved | One slice passed verification, review, and human approval. | Remaining work is zero. |
| Scope accounted | Every declared source-census item has a stable inventory identity and an explicit disposition. | Every item was migrated. |
| Scope implementation migrated | Every declared item that must be preserved has an approved target implementation with passing characterization and verification evidence, and the selected completion policy permits no remaining non-target disposition. | Final traffic authority, legacy retirement, or absolute proof of every unknowable runtime behavior. |
| Migration complete | The latest completion audit is passing, all declared scope is cut over, legacy decommission obligations are closed, and terminal state is justified by whole-scope evidence. | Merely a clean build, valid graph, approved exception, or human assertion. |

Do not use unqualified words such as “complete,” “done,” “fully migrated,” “100%,” or
“foundation complete.” Name the milestone, scope, numerator, denominator, and non-migrated
dispositions instead.

## Authoritative Denominators

`.migration/scope.json` defines the completion policy and authoritative source-file denominator.
Its policy records the mode, required claim, whether approved removals are allowed, and boundary
decision IDs. `whole-source-root` normally has no boundary decisions. `bounded` requires one or
more accepted `DEC-NNNN` records with durable human approvals; automation may not infer or
self-approve a narrower boundary. Its one
source snapshot records the source root, revision, capture time, digest, path/SHA-256 file list,
and exception-backed excluded-file list. Its per-`SRC` units record disposition, target IDs,
decisions, exceptions, and rationale. Product, supported-variant, platform, public/operational-
surface, and consumer evidence remains in inventory, discovery research, and accepted decisions;
the audit consumes those artifacts rather than inventing undeclared `scope.json` fields.
Changing any boundary requires an accepted, approved decision and a new source-census snapshot;
it is never an incidental result of what a scanner happened to find.

`.migration/inventory.json` records stable source-unit identities. Its source-census snapshot
must reconcile every deterministic candidate found beneath the declared roots as inventoried,
excluded by the scope contract, or unresolved. Generated inputs, build metadata, tests,
resources, schemas, deployment assets, and supported variant-only inputs are part of the census
when they influence product behavior or delivery.

`.migration/target-inventory.json` records actual target units, tests, build and packaging
assets, runtime/deployment assets, and retained interoperability boundaries. Each entry contains
only its stable ID, project-root-relative path, kind, truthful status, and SHA-256. Planned paths
are not actual target inventory. Source/behavior, decision, exception, slice, and evidence
cross-links remain in scope, traceability, and plans.

Structural validation proves that the currently populated artifacts conform to schemas and
cross-reference rules. It does not prove that the source census is exhaustive, that every item
has target evidence, or that the migration is complete.

## Accounted and Migrated Are Separate Metrics

Report both metrics using stable IDs, never file-count similarity:

```text
accounted = (migrated + replaced + retained + approved_removed) / declared_scope
migrated  = (migrated + replaced) / declared_scope
```

An item is **accounted** only when it has a stable source identity and one explicit, evidence-
backed disposition. Schema-defined source dispositions are `pending`, `migrated`, `replaced`,
`removed`, and `retained`; `unknown` is an audit finding for census/inventory/behavior gaps, not
a stored disposition. Pending and unknown items are not accounted. Retained source/native
boundaries and approved removals may close accounting under the declared policy, but they do
not increase the migrated numerator.

At the implementation stage, an item is **migrated** or **replaced** only when every required
observable behavior is linked to actual target units and tests, passing characterization and
target verification evidence, and approval. At the decommission stage it additionally requires
successful cutover evidence and target authority. `replaced` denotes an approved replacement
whose intentional semantic change remains explicit, and is included in the migrated numerator.
Many source units may map to one target unit, and one source unit may map to several target
units; no one-file-per-file rule follows from the metric.

Strict “100% migrated” requires all of these counts to be zero:

- pending or unowned source units, behaviors, target units, tests, and slices;
- unknown reachability, behavior, source-census, consumer, platform, or variant items;
- retained legacy, native, compatibility-process, or fallback boundaries;
- removed or excluded source scope, including approved dead-code removal;
- unverified, merely verified, or unapproved trace links; at the decommission stage, any
  not-yet-cut-over link also blocks;
- unresolved, temporary, expired, blocking, failed, or quality-gate exceptions.

If any count is nonzero, report the exact category and IDs. A project may truthfully be “100%
accounted with approved removals” or “100% of required preserved behavior migrated with a
retained native boundary,” but neither is strict 100% migration of the declared legacy scope.

## Global Closure Invariant

Before final cutover or decommission, a fresh completion audit must prove the common conditions
below. Conditions marked decommission-stage are not prerequisites for the implementation-stage
certificate that authorizes final cutover; making them prerequisites there would be circular.

1. The scope contract is approved and still matches the products and consumers being retired.
   A bounded policy has nonempty accepted, human-approved boundary decisions; a whole-source-
   root policy has no unexplained narrowing decision.
2. A deterministic source refresh matches the recorded source revision and reconciles the
   complete census with zero unresolved candidates.
3. Every declared source unit and observable surface has a terminal disposition; every required
   preserved behavior has characterization evidence.
4. Every required behavior is owned by exactly one approved slice or an explicitly shared,
   fully approved mapping; no trace remains `unmapped`, `planned`, `implemented`, or merely
   `verified`.
5. Actual target inventory, target tests, and passing verification evidence cover every
   migrated behavior and supported variant.
6. **Decommission stage:** the union of successful cutover scopes covers every required
   behavior, consumer, route, data owner, platform, and product boundary.
7. Exceptions and retained/removed items satisfy the declared completion policy; strict mode
   rejects every retained or removed item even when approved.
8. There is no active slice, every required plan is approved, target ownership is current, and
   source or target drift has not invalidated evidence.
9. **Decommission stage:** legacy assets have a complete remove, transfer, archive, or
   policy-approved retention disposition, and no supported runtime or operational process
   depends on the retired path.

Failure of any condition blocks a full-scope completion certificate. It does not invalidate
truthful evidence for already completed slices.

## Completion Audit and Certification

Run migrate-audit after each approved slice for progress and immediately before final cutover
and decommission for certification. A progress audit may pass structural checks while reporting
remaining work. A certification audit passes only when the requested completion policy and the
global closure invariant pass at the exact recorded source and target revisions.

The audit report includes at least:

- declared-scope, census, inventory, behavior, target, test, slice, and consumer denominators;
- counts and stable IDs for migrated, replaced, retained, removed, pending, unknown, and
  unverified items;
- trace statuses, exception categories/statuses, source and target drift, and active work;
- the exact policy evaluated and whether the result is progress-only or certifying; and
- evidence references for the source refresh, target verification, cutover union, and asset
  disposition.

The machine certificate stores only its schema-defined binding fields: generated flag,
migration/framework identity, stage, claim, state revision, source/target/migration digests,
generation time, counts, evidence IDs, and certified result. Detailed product and consumer
evidence stays in its authoritative artifacts and is bound through those digests/evidence IDs.

A certificate's stage is part of the claim. `implementation` means every declared item is
implemented, verified, and approved and may authorize the final cutover; it does not assert that
cutover already happened. `decommission` additionally proves complete cutover authority and
legacy-asset closure.

A certificate becomes stale when the scope, source revision, supported matrix, target revision,
traceability, decisions, exceptions, cutover authority, or consumer inventory changes. Final
cutover and decommission must reject a stale or progress-only result.

## Rule Provenance

Shared metadata: `source` is the framework v3 scope, inventory, traceability, evidence, and
lifecycle policy; `owner` is the generic framework profile.

| Rule ID | Rationale | Applies when | Enforcement | Required evidence | Reviewed for |
|---|---|---|---|---|---|
| `GEN-COMP-001` | Structural validity and scope completion answer different questions. | Every validation or completion claim | Claim and lifecycle review | Named milestone plus global audit result | Framework schema v3 |
| `GEN-COMP-002` | Missing work is invisible unless discovery has a reconciled denominator. | Discovery and source refresh | Source-census reconciliation | Scope contract, census snapshot, and inventory dispositions | Framework schema v3 |
| `GEN-COMP-003` | Approved retention or removal is accounted but not migrated. | Progress and completion reporting | Completion-policy evaluation | Separate accounted/migrated numerators and disposition IDs | Framework schema v3 |
| `GEN-COMP-004` | Slice approval cannot substantiate whole-product completion. | Approval, cutover, and decommission | Global completion audit | Passing current certification over all declared scope | Framework schema v3 |

## Behavioral Depth Enforcement

Structural certification (BEH-NNNN coverage, trace links, passing gates) proves that the
migration graph is connected and evidence exists. It does NOT prove that the target
implementation is semantically faithful to the source. A skeleton that compiles, defines the
right interfaces, and passes trivial tests satisfies structural certification while
implementing near-zero actual business logic.

### Depth Policy

The `quality_gates.depth_policy` in `config.json` controls behavioral depth enforcement:

```json
{
  "quality_gates": {
    "depth_policy": {
      "enforcement": "blocking",
      "min_observation_coverage_percent": 50,
      "min_target_source_ratio": 0.1,
      "min_assertions_per_behavior": 3
    }
  }
}
```

| Field | Default | Meaning |
|---|---|---|
| `enforcement` | `advisory` | `off` = no checks, `advisory` = warnings only, `blocking` = prevents certification |
| `min_observation_coverage_percent` | 50 | Percent of declared BEH observations that must have individual `verified_by` links |
| `min_target_source_ratio` | 0.1 | Minimum (target non-blank lines) / (source non-blank lines). A 155K-line source with 2K target lines (ratio 0.013) would fail. |
| `min_assertions_per_behavior` | 3 | Minimum test assertions per behavioral contract (from `depth_metrics` in evidence records) |

### Depth Metrics in Evidence

When depth policy is `advisory` or `blocking`, evidence records SHOULD include the optional
`depth_metrics` field:

```json
{
  "id": "EVID-0005",
  "gate": "tests",
  "status": "pass",
  "depth_metrics": {
    "observations_exercised": 7,
    "total_observations": 10,
    "assertions": 42,
    "source_lines": 2973,
    "target_lines": 450
  }
}
```

Without `depth_metrics`, the audit still computes source/target ratios from the file system
and observation coverage from structured `verified_by` links in behavioral contracts.

### Structured Observations

Behavioral contracts MAY use structured observations (schema version 2.1) that link each
observation to specific verification evidence:

```json
{
  "schema_version": "2.1",
  "id": "BEH-0002",
  "observations": [
    {
      "id": "OBS-001",
      "description": "FS codes 1-8 determine which account value components are retrieved",
      "verified_by": ["TEST-0005", "EVID-0004"],
      "complexity": "complex"
    },
    {
      "id": "OBS-002",
      "description": "Invalidate(konto) cascades to affected rows",
      "verified_by": ["TEST-0006"],
      "complexity": "moderate"
    }
  ]
}
```

Plain string observations remain valid (schema version 2.0) but score 0% on observation
coverage — they cannot be individually verified.

### Continuation Plan

When depth analysis identifies incomplete work, the `continue` command produces a prioritized
file-by-file translation plan:

```bash
python3 .migration-framework/bin/migrationctl.py continue .migration --project-root .
```

This outputs:
- Which source units have skeleton-only targets (target/source ratio below 0.15)
- Prioritized order (largest implementation gaps first)
- Estimated sessions remaining
- Which behavioral contracts need deeper test coverage

### What Depth Enforcement Prevents

Without depth enforcement, an agent can satisfy certification by:
1. Declaring all source units as "migrated"
2. Writing target files that define correct interfaces but implement no logic
3. Running `{{compile_command}}` and test commands on trivial tests that pass against skeletons
4. Recording evidence with `exit_code: 0`

With `enforcement: blocking`, the audit would report:
- `depth: target/source ratio 0.013 is below threshold 0.1 (2K target / 155K source)`
- `depth: 0 behavior(s) have fewer than 3 test assertions`
- `certifiable: false`

This does not substitute for expert semantic judgment — a 10:1 compression ratio may be
legitimate (e.g., replacing verbose legacy idioms with modern equivalents). But a 100:1
ratio is never legitimate for a faithful port, and the framework now surfaces this signal
rather than silently certifying it.
