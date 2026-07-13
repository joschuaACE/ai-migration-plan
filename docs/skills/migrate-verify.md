# migrate-verify

Run deterministic quality gates for one migrated slice. Verification produces reproducible
evidence for build, tests, behavioral contracts, profile rules, coverage, static analysis,
dependency integrity, and traceability. It does not make semantic or design judgments.

## When to Use

After `migrate-execute` completes a `SLICE-NNNN` plan. The lifecycle position is
Execute → **Verify** → Review. Failed gates return the slice to execution or mark the
migration failed; they never become an optimistic “pass with judgment.”

## Inputs

- **Slice ID** (required) — the `SLICE-NNNN` plan to verify.
- **--report-only flag** (optional) — write evidence without changing lifecycle or plan status.

**Required state:**

- `.migration/state.json` is schema-valid with `status: execute` and this active slice.
- `.migration/plans/SLICE-NNNN.json` exists with execution target units recorded.
- `.migration/scope.json` and `.migration/target-inventory.json` are current and every actual
  slice-owned target path has a truthful inventory entry and checksum.
- Every referenced `BEH-NNNN` contract has passing characterization evidence created before
  the plan, or an approved `EXC-NNNN` that explicitly limits the claim.
- `config.json` is valid and contains risk-approved quality gates for the selected output profile.

Read the plan, behavioral contracts, inventory, traceability links, decisions, exceptions,
execution summary, and selected source/target/output standards before running gates.

## Procedure

### Step 1: Validate inputs and enter verification

1. Run the installed structural validator:

   ```bash
   python3 .migration-framework/bin/migrationctl.py validate .migration
   ```

   A pass validates the current artifacts and references; it does not prove whole-scope
   completion.
2. Confirm every plan source unit and behavior has a traceability link.
3. Confirm characterization `EVID-NNNN` records are passing and have `phase: characterize`
   with no slice ID, proving that the contract preceded planning.
4. Resolve `{target_root}`, every execution-report target/build path, and every configured
   report path from the project root. Confirm target-owned paths remain beneath the target
   root and that the working directory, launcher, and build definition needed by each
   canonical command exist there. An outside-target path is valid only when an accepted
   orchestration decision explicitly lists it and supplies the matching working directory,
   ownership, and rollback.
5. Unless `--report-only` is set, transition `state.json` from `execute` to `verify`:

   ```bash
   python3 .migration-framework/bin/migrationctl.py transition --migration .migration --to verify --reason "Begin deterministic verification for SLICE-NNNN"
   ```

If any prerequisite is missing, stop before target verification and record the configuration
or characterization gap. Do not invent evidence or silently narrow the slice.

The commands below show the default `{target_root}` topology. An accepted orchestration
decision replaces the working directory and commands consistently; verification must use
those exact approved replacements rather than mixing topologies.

### Gate 1: Build and packaging

```bash
cd {target_root} && {{compile_command}}
```

Run any output-profile packaging or startup smoke command declared in `config.json`. Record
the exact project-root-relative `working_directory`, one exact `command`, toolchain and runtime
identifiers, integer `exit_code`, and every required log/report artifact as a path/SHA-256 pair
in an `EVID-NNNN` v3 record with `phase: verify` and this slice ID. Do not put several commands
or directories into one evidence record. Do not record a normalized or equivalent command from
a different directory; rerun the recorded command itself before assigning `status: pass`.

### Gate 2: Target and differential tests

```bash
cd {target_root} && {{test_command}}
```

Run the target suite plus the plan's behavioral, golden-master, differential, contract,
concurrency, failure-path, and platform cases. A passing unit suite is not a substitute for
the `BEH-NNNN` observations. Link each behavior to the test and evidence that exercises it.

### Gate 3: Profile architecture and boundary rules

```bash
cd {target_root} && {{architecture_test_command}}
```

Apply only the selected output profile's machine-checkable boundaries:

- **service:** module direction, domain/application policy purity, ports, adapters, and
  composition-root rules;
- **library:** API/internal/SPI exports, consumer surface, and runtime dependency exposure;
- **SDK:** library boundaries plus compatibility, documentation, example, and consumer gates;
- **CLI:** command boundary, stream ownership, exit-code, non-interactive, and packaging rules.

Do not apply service hexagonal rules to a library, SDK, or CLI merely because the target
profile can run an architecture tool.

{{#if target_language_id == 'java-25'}}
For Java 25, also run the selected profile's module/package checks, `jdeps`/`jdeprscan` gates
where applicable, preview-feature flag consistency, and packaged-runtime compatibility checks.
{{/if}}

### Gate 4: Output-profile presence and absence checks

Automate objective surface checks from the selected output profile. Examples include service
startup/configuration artifacts, library module exports and absence of application runtime
frameworks, SDK public documentation/examples, or CLI help, streams, exit codes, and distribution
contents. Report facts here; leave whether an abstraction is elegant to review.

### Gate 5: Configured coverage policy

Read `.migration/config.json` and the selected output manifest. Use its configured
behavioral-contract, changed-code, or public-API metric and project-approved threshold. The
framework defines no universal percentage and does not require one test per method or file.

Resolve `{{coverage_report_path}}` beneath `{target_root}` and read it there; if it is absent,
run:

```bash
cd {target_root} && {{coverage_command}}
```

Fail configuration validation if a required threshold or risk rationale is missing. Record
actual metric, configured threshold, command, and report checksum in evidence.

### Gate 6: Slice traceability completeness

For every source unit and `BEH-NNNN` in the slice, verify `traceability.json` links:

- target units or an approved exception;
- tests that exercise the behavioral observation;
- intentional divergence decisions and policy exceptions;
- passing characterization and target verification evidence; and
- current status consistent with the plan.

This is a slice-local presence and cross-reference gate, not a semantic comparison or a global
completion audit. Do not score method counts or declare meaning equivalent because names/
signatures exist.

### Gate 7: Static, dependency, and integrity analysis

```bash
cd {target_root} && {{lint_command}}
```

Run configured static analysis, dependency graph/policy checks, vulnerability/license policy,
and dependency integrity verification. For Gradle targets, confirm requested version alignment
where needed and review dependency verification metadata changes rather than treating a version
catalog as resolved-version enforcement.

### Gate 8: Coexistence and recovery checks

When the plan changes a live seam, run its shadow/dual-read/routed-cohort isolation checks,
rollback or forward-recovery rehearsal, reconciliation checks, and abort-signal validation.
Do not perform a production cutover during verification.

### Step 9: Record result and transition

Create one immutable v3 `.migration/evidence/EVID-NNNN.json` per independently reproducible
gate. Each record has one `command`, one `working_directory`, its integer `exit_code`, and
`artifacts` whose entries each contain a project-root-relative `path` and SHA-256. Before
promotion, rerun or mechanically check that those singular fields name the command actually
executed, the exit code supports the declared result, and every checksummed artifact exists at
the recorded target-contained path. Then update traceability with those IDs and refresh affected
`target-inventory.json` entries to their schema-defined `planned`, `present`, or `removed`
status and current checksum. Verification status remains in traceability/evidence. A narrative report may be written to
`.migration/reports/SLICE-NNNN-verification.md`, but it never replaces the JSON evidence.

- **All required gates pass:** set the plan to `verified`; advance each fully covered
  traceability link to `verified` (leave a shared/partially covered link at its earlier status);
  keep state at `verify`; recommend `migrate-review SLICE-NNNN`.
- **Remediable gate fails:** retain failing evidence, transition `verify → execute`, fix the
  slice, then rerun all affected gates.
- **Execution cannot continue:** transition `verify → failed` with a blocker/failure reference.
- **Report only:** do not mutate state or plan status.

After any result, report the global declared, accounted, implemented, verified, approved,
retained, removed, pending, unknown, unverified, and remaining-slice denominators. Passing every
gate for this slice advances only this slice; it does not certify whole-scope migration.

Warnings advance only when the selected profile permits them and the evidence records the
policy. A failed required gate cannot be waived except through an approved `EXC-NNNN` whose
scope, impact, mitigation, and approvers are traceable.

## Outputs

- `.migration/evidence/EVID-NNNN.json` — exact deterministic gate evidence.
- Updated `.migration/traceability.json` evidence links and fully covered link statuses.
- Updated `.migration/target-inventory.json` statuses and checksums for verified target assets.
- Updated `.migration/plans/SLICE-NNNN.json` status when not report-only.
- Optional `.migration/reports/SLICE-NNNN-verification.md` summary.
- Validated `.migration/state.json` transition or explicit failure/blocker.

## Success Criteria

- Every required profile/project gate has reproducible passing evidence.
- Every passing command can be rerun exactly from its recorded working directory, and its
  recorded artifacts resolve beneath `{target_root}` unless an accepted orchestration
  decision says otherwise.
- Every slice behavior has passing characterization and target test evidence.
- Build, tests, applicable architecture/output rules, configured coverage, static analysis,
  dependency analysis/integrity, and recovery checks pass.
- Traceability has no dangling or falsely completed links.
- No semantic-fidelity, minimalism, or idiom judgment is presented as deterministic proof.
- Plan and lifecycle state are schema-valid and ready for `migrate-review`.
- Slice verification and global completion are reported separately with exact remaining IDs;
  only migrate-audit may certify the whole declared scope.
