# migrate-init

Initialize a versioned {{source_language}} to {{target_language}} migration record without
performing discovery, translation, or target implementation work.

## When to Use

- Once for a new migration before any other migration workflow.
- When adopting the framework for an existing project that does not yet have a valid
  `.migration/` directory.
- Do not use it to replace or repair an existing state directory; validate it and use
  migrate-resume or the framework upgrade procedure instead.

## Inputs

- **Source root** (required) — `{source_root}`, containing the legacy project.
- **Target root** (optional) — `{target_root}`, default `./app/`; it may not exist yet.
- **Migration ID** (required or generated) — a stable, project-specific identifier using
  letters, digits, `.`, `_`, or `-`.
- **Output profile** (optional confirmation) — must match the compiled bundle profile
  `{{output_profile}}`; selecting another profile requires compiling/installing that bundle
  so its documents, capabilities, architecture, and gates are present.
- **Migration strategy** (optional) — `incremental` by default; `big-bang` requires an
  accepted decision explaining why incremental seams are impractical.
- **Quality-gate policy** (required) — output-profile required checks plus a risk-approved
  coverage metric (`behavioral-contract`, `changed-code`, `public-api`, or `none`), threshold
  where applicable, and rationale. Automation must not invent the threshold.
- **--auto flag** (optional) — accept only profile defaults that require no project judgment.
  It must not invent architecture, compatibility, cutover, or risk decisions.

## Procedure

### Step 1: Preflight Without Mutation

1. Read the compiled bundle manifest and confirm the selected source, target, pair, and
   output profiles are compatible.
2. Resolve `{source_root}` and `{target_root}` without following a path outside the project.
   Verify `{source_root}` exists and contains evidence of {{source_language}} source or build
   metadata. The target may be absent.
3. If `.migration/` exists, stop before writing. Validate the existing directory and report
   whether the correct action is resume, managed upgrade, or explicit replacement. Never
   silently overwrite state, evidence, decisions, or locally edited reports.
4. Confirm the compiled `{{output_profile}}` profile matches build products and user intent.
   Build detection may suggest a profile, but mixed products or ambiguous consumers require
   a user decision and, if the choice changes, a correctly recompiled bundle.
5. Confirm incremental modernization as the default. For a requested big-bang migration,
   allocate the next `DEC-NNNN` ID and record the rationale, blast radius, rollback model,
   and required approval before accepting that strategy.
6. Start with the selected output profile's required checks. Record project additions and a
   risk-approved coverage metric, threshold, and rationale. `none` is allowed only with a
   specific rationale and does not waive behavioral-contract evidence; a metric other than
   `none` requires an explicit numeric threshold before configuration can be valid.

### Step 2: Allocate Stable Identity

7. Select one `migration_id` and retain it for the lifetime of the migration. Do not derive
   artifact identity from a mutable path, package, phase number, or timestamp.
8. Use monotonically allocated identifiers within each artifact class:
   `SRC-NNNN`, `BEH-NNNN`, `TGT-NNNN`, `TEST-NNNN`, `DEC-NNNN`, `SLICE-NNNN`,
   `EVID-NNNN`, and `EXC-NNNN`. An ID is never reused after rejection, removal, rename, or
   supersession.
9. Timestamps are UTC RFC 3339 values. They record events but never act as identity.

### Step 3: Stage the Authoritative State

10. Create a staging directory next to `.migration/` with these directories:

   ```text
   .migration/
   ├── analysis/
   ├── behaviors/
   ├── decisions/
   ├── evidence/
   ├── exceptions/
   ├── plans/
   ├── reports/
   ├── reviews/
   └── research/
   ```

11. Instantiate the bundle-owned JSON templates and preserve their `$schema` and
    `schema_version` fields. In an installed target, read them from
    `.migration-framework/state/templates/` and validate against
    `.migration-framework/schemas/`. In a portable bundle, the corresponding directories
    are `state/templates/` and `schemas/`. These are blank starting templates; the active
    records created from them belong under `.migration/`. Create:

    - `config.json` with `framework_version`, the source/target/pair profile IDs,
      `output_profile`, strategy, `{source_root}`, `{target_root}`, `quality_gates`, project
      decision references, and validation status;
    - `state.json` with `status: "initialize"`, revision `0`, no active slice, no completed
      slices, and its initial transition from `null`;
    - `inventory.json` with the migration ID and an empty `units` array; and
    - `traceability.json` with the migration ID and an empty `links` array.

12. Store project choices requiring judgment as individual schema-valid
    `.migration/decisions/DEC-NNNN.json` records. Profile selection is configuration;
    intentional behavior changes, exclusions, architecture variations, and strategy
    exceptions are decisions and must not be hidden in prose.
13. Do not create target source files, a build skeleton, mappings, plans, or behavioral
    equivalence claims during initialization. In particular, do not run
    `{{compile_command}}` until an output-profile-specific target structure exists. This
    preserves the required discovery and characterization gates before translation.

### Step 4: Validate and Promote Atomically

14. Validate each staged JSON artifact against its declared schema, then validate the
    complete staged cross-reference graph. A valid schema with a broken reference is still
    a failed initialization.
15. If validation fails, report every actionable diagnostic and delete only the staging
    directory. Leave any prior `.migration/` state untouched.
16. Atomically promote the staged directory to `.migration/` only after all validation
    succeeds. Set `config.json.validation_status` and `state.json.validation_status` to
    `valid` in the promoted, revalidated artifact set.

### Step 5: Enter Discovery

17. Apply the validated `initialize -> discover` transition. Increment the state revision,
    append the transition to `history`, and make it equal to `last_transition`. Do not edit
    only the status field.
18. Report the selected profiles, roots, strategy, quality-gate policy, migration ID,
    decision IDs, and validation result. The next action is migrate-detect.
19. Explain the remaining lifecycle explicitly:

    ```text
    discover -> characterize -> map -> plan -> execute -> verify -> review
             -> approve -> cut_over -> decommissioned
    ```

    Verification will produce reproducible evidence; review will separately evaluate
    semantic fidelity, idiomatic design, and justified modernization.

## Outputs

- `.migration/config.json` — schema-valid profile, strategy, root, and validation config.
- `.migration/state.json` — revisioned state transitioned from `initialize` to `discover`.
- `.migration/inventory.json` — empty schema-valid source inventory ready for discovery.
- `.migration/traceability.json` — empty schema-valid cross-reference graph.
- `.migration/decisions/DEC-NNNN.json` — any explicit initialization decisions.
- Empty artifact directories for later lifecycle stages; no target implementation files.

## Success Criteria

- Every created JSON file validates against its declared v2 schema.
- The complete `.migration/` graph validates before and after atomic promotion.
- The migration, profiles, output profile, strategy, and roots are explicit and stable.
- `quality_gates` contains the selected profile's required checks and an explicit risk-based
  coverage policy; no missing threshold was guessed.
- Existing migration state or unrelated project files were not overwritten.
- Big-bang strategy, if selected, has an accepted and approved decision record.
- `state.json` has a continuous history ending in `discover` with validation status `valid`.
- No discovery result, behavioral claim, target mapping, plan, or translated code was
  fabricated during initialization.
- The user knows migrate-detect is next and understands that verify and review are distinct
  gates before approval and cutover.
