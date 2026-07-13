# migrate-framework-update

Safely update the framework-managed guidance, workflows, hooks, schemas, and installation
metadata in a migration project without changing its live `.migration/` record.

## When to Use

- When a project already has a valid managed installation under `.migration-framework/`.
- When adopting a newer framework release or a reviewed, precompiled adapter bundle.
- When deliberately changing the installed adapter, migration pair, output profile, or
  project overrides.
- Do not use this workflow for a fresh installation or to repair invalid migration state.

## Inputs

- **Target project** (required) — the project containing `.migration-framework/`.
- **Upgrade source** (required) — either a trusted local framework checkout or a verified
  precompiled bundle plus a compatible framework CLI. Do not fetch or execute an unreviewed
  update source during this workflow.
- **Configuration changes** (optional) — adapter, pair, output profile, `--set KEY=VALUE`,
  or `--unset KEY` values that the user explicitly intends to change.
- **Major-version decision** (conditional) — an accepted `DEC-NNNN` record referenced by
  `.migration/config.json` as `project_decisions.framework_upgrade` and containing a recorded
  human approval reference when an active migration adopts a new installed framework major.
  The workflow verifies the approval's human provenance; the CLI verifies that a nonblank
  approval reference exists.
- **Conflict policy** (optional) — `--force` only for individually reviewed generated-file
  conflicts that the user explicitly authorizes replacing.

## Procedure

### Step 1: Establish a Trusted, Valid Source

1. Resolve the target project and upgrade source to local paths. Confirm the target contains
   `.migration-framework/ownership.json` and its recorded checksum. Do not use a plain copy
   of generated skills as an upgrade source.
2. For a framework checkout, run `python3 agents/framework.py check` from that checkout and
   stop if validation or conformance fails. For a precompiled bundle, confirm it came from a
   trusted source; the upgrade preflight must then verify its manifest, generated-file
   checksums, aggregate digest, and adapter compatibility.
3. Treat corrupted, missing, or unsafe ownership metadata as a blocker. Do not reconstruct
   ownership by guessing from files in the target.

### Step 2: Validate the Target Before Planning Changes

4. If `.migration/` exists, run the installed structural validator against the current state:

   ```bash
   python3 .migration-framework/bin/migrationctl.py validate .migration
   ```

   A pre-runtime installation will not contain that file. In that one compatibility case, run
   the trusted framework checkout's legacy structural command instead:

   ```text
   python3 <framework-checkout>/agents/framework.py validate-migration <target-project>/.migration
   ```

   Stop on an invalid schema, transition history, decision reference, or cross-artifact link.
   A pass is not whole-scope completion, and a framework update is not a repair mechanism for
   project state.
5. Record a recursive checksum snapshot of `.migration/` after any separately approved
   decision work and immediately before the installer runs. The installer owns
   `.migration-framework/`; it must never write, delete, or normalize files in `.migration/`.
6. Run an upgrade dry-run from the trusted framework CLI using only the intended inputs:

   ```text
   python3 agents/framework.py upgrade --target <target-project> --dry-run
   ```

   Add `--bundle <compiled-bundle>` when updating from an exact bundle. Omitted adapter,
   pair, output profile, and project overrides must be inferred from verified installation
   metadata rather than from current framework defaults. If the intended inputs or bundle
   change installed configuration, include `--reconfigure` before requesting the detailed
   dry-run. Without it, the configuration guard stops before emitting the full report.

### Step 3: Review Configuration and Compatibility

7. Review the dry-run's current and proposed framework versions, adapter, profiles,
   overrides, bundle digests, compatibility status, writes, deletions, unchanged paths,
   conflicts, and explicit `forced_replacements` paths. Explain every effective configuration
   change before proceeding.
8. If the guard reports that configuration would change because `--reconfigure` was omitted,
   treat that result as a guard failure rather than a reviewed preview. Confirm the intended
   change, add `--reconfigure`, and repeat the dry-run to obtain the complete before/after
   report. Without `--bundle`, use `--set KEY=VALUE` to add or replace an override and
   `--unset KEY` to remove one. A bundle already contains its exact profiles and overrides, so
   do not combine `--bundle` with `--pair`, `--output-profile`, `--set`, or `--unset`. Never use
   `--reconfigure` merely to bypass an unexplained mismatch.
9. For legacy installation metadata, review every `legacy-inferred` override and warning.
   Preserve inferred values unless the user explicitly reconfigures them. Stop if an old
   value no longer exists, has an incompatible type, or attempts to change protected profile
   identity.
10. If the dry-run reports a cross-major update while `.migration/` exists, confirm the
    referenced `DEC-NNNN` record is accepted, equals
    `.migration/config.json`'s `project_decisions.framework_upgrade` value, and its `approvals`
    array contains a recorded reference to human review. The CLI checks acceptance, that exact
    configuration reference, and the presence of a nonblank approval reference; this workflow
    must verify the reference's human provenance. If it is missing, pause this workflow and
    obtain the decision; do not invent or self-approve it. Repeat the dry-run with
    `--allow-major` and `--decision DEC-NNNN`. This gate applies once when an active migration
    adopts a new installed major. It is unnecessary for later same-major updates or a terminal
    migration, though the migration graph must still validate.
11. Inspect every collision or locally modified generated file. Prefer moving a useful local
    edit back into the framework's curated source. Add `--force` only when the user explicitly
    approves replacement after seeing the affected paths and consequences, then repeat the
    dry-run and confirm `forced_replacements` contains exactly those approved paths.

### Step 4: Approve and Apply the Exact Plan

12. Present the final dry-run report and the exact upgrade command. Obtain explicit user
    confirmation before any managed file is changed.
13. Run the same command with only `--dry-run` removed. Do not add configuration, major-version,
    bundle, strict-hook, or force flags that were absent from the approved preflight.
14. If staging, checksum verification, or promotion fails, report the rollback result and
    stop. Do not manually finish a partial installation.

### Step 5: Verify the Result and State Boundary

15. Validate the new ownership record and its checksum, then repeat the upgrade as a dry-run.
    After a successful major adoption, omit the now-unnecessary one-time `--allow-major` and
    `--decision` flags. Keep every ordinary configuration and bundle input unchanged. The
    dry-run must report no pending writes, deletions, conflicts, or configuration changes.
16. If `.migration/` exists, run the newly installed
    `python3 .migration-framework/bin/migrationctl.py validate .migration` again and compare the
    current artifact graph with the pre-upgrade checksum snapshot. Any installer-caused
    difference is a failed update even if the installed guidance appears correct. Structural
    validation still does not certify whole-scope migration.
17. Report the installed framework version, adapter, profiles, preserved or changed
    overrides, bundle digest, legacy-inference warnings, the explicit `forced_replacements`
    paths, and the migration compatibility result.

## Outputs

- Captured pre-upgrade and post-upgrade dry-run reports.
- Updated framework-owned guidance and support files in the target project.
- Updated `.migration-framework/ownership.json`, manifest, schemas, templates, and
  provenance for the verified bundle.
- An unchanged `.migration/` tree, except for any separately approved decision work completed
  before the installer snapshot.

## Success Criteria

- The source checkout passes framework validation or the supplied bundle passes every digest
  and compatibility check.
- The effective configuration is preserved unless the user explicitly approved
  `--reconfigure` inputs.
- Legacy inferred overrides are visible, reviewed, and persisted without silent defaulting.
- An active migration is valid and a cross-major update has an accepted,
  configuration-referenced decision whose recorded human approval reference was verified by
  this workflow.
- The applied command exactly matches the approved dry-run except for removal of `--dry-run`.
- Ownership verification passes and a subsequent dry-run is empty.
- The installer made no change anywhere under `.migration/`.
