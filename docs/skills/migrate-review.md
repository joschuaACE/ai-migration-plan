# migrate-review

Perform LLM-assisted judgment review of one verified migration slice: semantic fidelity,
minimalism, target idiom quality, and justified modernization. Every check here requires
reasoning that cannot be reduced to a command or numeric threshold.

## When to Use

After `migrate-verify SLICE-NNNN` has produced passing evidence for every required automated
gate. The lifecycle position is Verify → **Review** → Approve. Review does not repeat the
build, test, coverage, architecture, static-analysis, or dependency-integrity commands and
does not itself cut over production traffic.

## Inputs

- **Slice ID** (required) — the `SLICE-NNNN` plan to review.
- **--scope flag** (optional):
  - `diff` — review target changes and traceability affected by this slice;
  - `full` — review all target units and contracts in the slice.
- **--fix flag** (optional) — apply low-risk advisory simplifications, then require verification again.

**Required state:**

- `.migration/state.json` has `status: verify` and names the slice.
- The plan has `status: verified`.
- All required `EVID-NNNN` verification records pass and traceability links them.
- `config.json` selects the output profile whose idioms and boundaries apply.

Trust deterministic verification only for what it proved: commands ran in the recorded
environment, required gates passed, and references exist. This review judges whether the
implementation preserves meaning and whether any modernization is appropriate.

## Procedure

### Step 1: Enter review and gather context

1. Validate `.migration/`, then transition `state.json` from `verify` to `review`.
2. Read the slice plan, source units, `BEH-NNNN` contracts, known gaps, target units and tests.
3. Read traceability, deterministic evidence, accepted decisions, approved exceptions, and
   the selected source/target/pair/output standards.
4. Read the slice diff and any coexistence, rollback, and consumer/deployment constraints.

### Step 2: Semantic fidelity review

Judge behavior by contract and observable path rather than by file shape:

- Do target results, error categories, ordering, numeric behavior, side effects, and resource
  lifecycles preserve each characterized observation?
- Are concurrency visibility, atomicity, cancellation, shutdown, and thread-safety properties
  preserved where the source relied on them?
- Are implicit charset, locale, time, filesystem, serialization, platform, ABI, and dependency
  assumptions preserved or deliberately normalized?
- Is every difference linked to an accepted `DEC-NNNN` and, when policy requires it, an
  approved `EXC-NNNN` with consumer impact and mitigation?
- Does coexistence keep the legacy and target paths from duplicating or corrupting side effects?

Undefined, unspecified, or environment-dependent source behavior cannot receive a blanket
equivalence claim. Review its observed scope and approved disposition explicitly.

**Verdict per behavior:** `FAITHFUL` | `DRIFT_MINOR` | `DRIFT_MAJOR`

- `FAITHFUL` — the available contracts, evidence, and reasoning support the compatibility claim.
- `DRIFT_MINOR` — a bounded difference is accepted and traceable.
- `DRIFT_MAJOR` — an unapproved or unsafe behavior change must be fixed or explicitly decided.

### Step 3: Minimalism audit

Assess whether the target is direct and maintainable without carrying accidental source or
AI-generated complexity:

1. Is dead/unreachable source code omitted only through an approved exception?
2. Is defensive code limited to real trust, compatibility, or recovery boundaries?
3. Are wrappers, builders, strategies, configuration layers, and extension points justified
   by a behavior, selected output architecture, or actual second implementation?
4. Could the same behavior be clearer with a smaller target-idiomatic construct?
5. Does the design avoid speculative portability, premature distribution, and premature optimization?

An interface with one implementation is not automatically unnecessary when it is a required
service port or a consumer-facing SPI; judge it against the selected output profile.

{{#if output_profile == 'service'}}
{{#if target_language_id == 'java-25'}}
For a Java service, question hand-built pooling, serialization, retry, or wiring only when the
selected framework safely provides the required behavior. Auto-configuration is not a reason
to erase an explicit domain/application boundary or a behavior-specific resilience decision.
{{/if}}
{{/if}}

**Verdict per finding:** `OVER_ENGINEERED` | `UNNECESSARY` | `SIMPLIFIABLE` | `APPROVED`

### Step 4: Target idiom and output-profile review

Judge whether the code reads naturally in {{target_language}} without forcing fashionable
features or line-by-line transliteration:

- Are names, types, absence/error models, resource scopes, collections, concurrency, and module
  boundaries idiomatic for the target?
- Does the service/library/SDK/CLI structure match its selected profile without cross-contamination?
- Are public API/SPI and compatibility commitments deliberately small and documented?
- Are unsupported, preview, incubating, or experimental target features backed by an accepted
  decision, complete build/runtime flags, compatibility scope, and exit plan?

{{#if target_language_id == 'java-25'}}
Consider records, sealed hierarchies, pattern matching, streams, and modern concurrency only
where they clarify the mapped contract. Do not force streams over clearer loops, expose preview
features through stable APIs accidentally, or mistake garbage collection for deterministic
resource cleanup.
{{/if}}

**Verdict:** `IDIOMATIC` | `TRANSLITERATED` | `ACCEPTABLE`

### Step 5: Consolidate the judgment

Write `.migration/reviews/SLICE-NNNN-review.md` with:

```markdown
## Migration Review: SLICE-NNNN

### Behavioral Fidelity
| Behavior ID | Verdict | Evidence/Decision/Exception | Reasoning |
|---|---|---|---|

### Minimalism
| Target unit | Finding | Severity | Action |
|---|---|---|---|

### Idiom and Output Profile
| Target unit | Verdict | Notes |
|---|---|---|

### Overall Verdict: RECOMMEND_APPROVAL | NEEDS_FIXES | BLOCKED
```

Do not convert uncertain reasoning into a fabricated deterministic score.

### Step 6: Resolve and request approval

**If RECOMMEND_APPROVAL:**

1. Present the review, remaining known gaps, rollback scope, and cutover implications to the
   named human approver.
2. After explicit approval is recorded, set the plan to `approved` and transition
   every fully covered trace link to `approved`, append the slice ID to
   `state.json.completed_slices`, clear `active_slice`, and transition state from `review`
   to `approve`. Add the durable human approval reference to the plan's `approval_refs`.
   Stage and validate these mutations as one atomic update.
3. Approval permits the next slice or a separately planned cutover; it does not merge, deploy,
   route traffic, or decommission the legacy path automatically.

**If NEEDS_FIXES:**

1. Apply `--fix` only to low-risk minimalism/idiom findings within the authorized slice.
2. Transition `review → execute`, update target units and traceability, rerun every affected
   deterministic verification gate, then repeat review on the changed scope.

**If BLOCKED:**

1. List every `DRIFT_MAJOR`, unsupported dependency/platform, unresolved source behavior, or
   missing approval.
2. Fix it, or propose a decision/exception with explicit impact and approvers; never treat an
   unapproved note as justification.
3. Transition to `blocked` when external input is required, recording `resume_to: review`; after
   resolution, resume review or return to execution as appropriate.

## Outputs

- `.migration/reviews/SLICE-NNNN-review.md` — evidence-linked judgment and recommendation.
- New or updated `DEC-NNNN` / `EXC-NNNN` proposals for every intentional difference.
- Updated plan, traceability, and `state.json` only after explicit human approval or a valid corrective transition.
- No automatic cutover, merge, deployment, or decommission operation.

## Success Criteria

- Every slice behavior receives an evidence-linked fidelity judgment.
- Minimalism and idiom quality are assessed against the selected output profile.
- Every major drift is fixed or covered by an accepted decision and required approval.
- Deterministic verification is not duplicated or misrepresented as semantic judgment.
- Human approval, remaining risk, coexistence, and rollback implications are explicit.
- Plan, traceability, decisions/exceptions, review report, and lifecycle state agree.
