# migrate-audit

Audit whole-scope migration progress and, only when every applicable global closure condition
passes, create the completion certificate required by final cutover or terminal decommission.
This workflow distinguishes structural state validity, 100% accounted scope, and strict 100%
migrated scope. It does not implement, approve, cut over, or decommission work.

## When to Use

- After discovery establishes or refreshes the authoritative source census.
- After every approved slice, before deciding between another plan and final cutover.
- Immediately before final cutover, using an implementation-stage certificate.
- Immediately before terminal decommission, using a decommission-stage certificate.
- Whenever a user or agent asks whether the whole declared legacy product is complete.

## Inputs

- **Claim** (required) — `accounted` or `migrated`.
  - `accounted` allows evidence-backed retained and approved-removed dispositions permitted by
    the scope policy, but reports them outside the migrated numerator.
  - `migrated` is strict: pending, unknown, retained, removed, and unverified counts must all be
    zero.
- **Stage** (optional for progress, required for certification) — `implementation` before final
  cutover or `decommission` before the terminal transition.
- **Certification request** (optional) — run the separate `certify` command to create
  `.migration/completion-certificate.json` only when the selected claim and stage pass. Without
  that explicit request, run `audit` and report progress without writing a certificate.

**Required state:** `.migration/config.json`, `.migration/scope.json`, `state.json`,
`inventory.json`, `target-inventory.json`, `traceability.json`, all referenced contracts,
plans, decisions, exceptions, and evidence exist and structurally validate. The source and
target roots resolve within the project or through accepted orchestration decisions.

## Procedure

### Step 1: Validate Structure Without Inferring Completion

1. Run the installed validator from the project root:

   ```bash
   python3 .migration-framework/bin/migrationctl.py validate .migration
   ```

2. Treat this result only as proof that the currently populated artifact set is schema-valid,
   internally consistent, and lifecycle-valid. A passing structural validation does not prove
   that discovery found the whole source product or that any behavior migrated.
3. Read completion policy, source snapshot, and per-source dispositions from `scope.json`;
   read product, variant, platform, consumer, behavior, plan, and evidence denominators from
   their authoritative inventory, research, decision, traceability, plan, and evidence
   artifacts. Confirm the requested claim matches the user's intent. Never substitute
   `accounted` when strict `migrated` was requested.
   For `whole-source-root`, reject unexplained narrowing. For `bounded`, require a nonempty
   `boundary_decisions` list whose referenced decisions are accepted and durably human-approved;
   certification refuses an unapproved or self-inferred boundary.

### Step 2: Refresh the Authoritative Census and Workspace Snapshots

4. Confirm the configured source and target roots, supported products, variants, platforms,
   consumers, generated roots, and approved scan exclusions still match the workspace.
5. Refresh the deterministic source census and target snapshot from the project root:

   ```bash
   python3 .migration-framework/bin/migrationctl.py snapshot .migration --project-root .
   ```

6. Reconcile every source candidate as inventoried, scope-excluded, or unresolved. Reconcile
   every actual target source, test, build, package, deployment, and retained-boundary asset
   with `target-inventory.json`. A path present on disk without a stable identity and trace is
   unresolved; a planned target path is not evidence that an actual target unit exists.
7. Rerun structural validation after the snapshot. Source, target, scope, supported-matrix, or
   consumer drift invalidates prior completion certification and returns affected work to the
   earliest truthful lifecycle state.

### Step 3: Calculate Global Denominators

8. Run the installed whole-scope audit:

   ```bash
   python3 .migration-framework/bin/migrationctl.py audit .migration --claim <accounted|migrated>
   ```

9. Report, with stable IDs, at least:

   - declared source-census total and accounted total;
   - migrated, replaced, retained, approved-removed, pending, and unknown source counts;
   - required, characterized, mapped, implemented, verified, approved, and cut-over behaviors;
   - planned, active, verified, approved, and remaining slices;
   - actual target units/tests and unverified or orphan target entries;
   - supported products, variants, platforms, consumers, routes, and data owners still using
     legacy authority; and
   - proposed, approved, expired, blocking, failed, and policy-incompatible exceptions.

10. Calculate the claims separately:

    ```text
    accounted = (migrated + replaced + retained + approved_removed) / declared_scope
    migrated  = (migrated + replaced) / declared_scope
    ```

    Do not count `pending` or audit-derived `unknown` gaps as accounted. Count an approved,
    target-authoritative `replaced` disposition in the migrated claim; do not count retained or
    removed scope as migrated. Do not use target/source file-count similarity as either
    denominator.
11. For strict `migrated`, fail when any pending, unknown, retained, removed, or unverified item
    exists, even when a removal or retained boundary has human approval. List every blocking ID.

### Step 4: Route Remaining Work

12. If implementation-stage work remains, do not recommend cutover. From `approve`, the only
    forward migration route is `approve -> plan`; select the smallest dependency-ready remaining
    behavior set and retain the global denominators in the next plan.
13. If discovery or characterization denominators are incomplete, return to `discover` or
    `characterize` through an accepted recovery decision. If target inventory or evidence is
    incomplete, return to the owning map, plan, execute, verify, or review workflow.
14. An approved exception may change a disposition or the `accounted` result. It cannot turn a
    retained or removed item into a strict migrated item.

### Step 5: Certify Final-Cutover Readiness

15. Only after the implementation audit passes for the requested claim, create the mandatory
    implementation-stage certificate:

    ```bash
    python3 .migration-framework/bin/migrationctl.py certify .migration --claim <accounted|migrated> --stage implementation
    ```

16. Confirm `.migration/completion-certificate.json` records the generated flag,
    migration/framework identity, exact stage and claim, state revision, source/target/migration
    digests, generation time, schema-defined counts, evidence IDs, and certified result. Those
    digests bind the detailed scope, inventory, traceability, plan, decision, exception, and
    evidence artifacts. Final cutover must reject a missing, failing, progress-only,
    wrong-claim, wrong-stage, or stale certificate.

### Step 6: Certify Terminal-Decommission Readiness

17. After all required cutover scopes pass their observation windows, rerun Steps 1 through 3.
    Confirm the union of passing cutover evidence covers every required behavior, consumer,
    route, artifact, platform, data owner, and product boundary.
18. Reconcile the full legacy-asset inventory and prove every asset is removed, transferred,
    archived, or retained only when the requested claim explicitly permits it. Strict migrated
    certification permits no retained legacy/native runtime or removed declared source scope.
19. Create the mandatory decommission-stage certificate only after every terminal condition
    passes:

    ```bash
    python3 .migration-framework/bin/migrationctl.py certify .migration --claim <accounted|migrated> --stage decommission
    ```

20. Decommission may transition to terminal state only while this exact certificate remains
    current. Any subsequent scope, source, target, traceability, decision, exception, evidence,
    cutover, consumer, or asset-disposition change invalidates it and requires a new audit.

## Outputs

- A whole-scope progress report with explicit numerators, denominators, dispositions, and IDs.
- `.migration/completion-certificate.json` only when the separate certification command is
  explicitly requested and every selected claim/stage condition passes.
- A precise route to discovery, characterization, mapping, planning, execution, verification,
  review, cutover completion, or asset closure when certification fails.
- No target implementation, approval, traffic movement, legacy removal, or unsupported
  completion claim.

## Success Criteria

- Structural validity is reported separately from scope accounting and migration completion.
- The source census and target inventory are fresh, deterministic, and fully reconciled.
- Accounted and migrated numerators are reported separately with exact non-migrated IDs.
- Strict 100% migrated has zero pending, unknown, retained, removed, and unverified items.
- Remaining implementation work forces another plan instead of permitting final cutover.
- Final cutover and terminal decommission each require a passing, current certificate for the
  exact claim and stage.
- No certificate is created from stale snapshots, partial slice evidence, approved prose, a
  clean build, file counts, or structural validation alone.
