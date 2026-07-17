# migrate-review

Review migrated code with two passes — semantic fidelity checking plus ponytail minimalism audit — then ship or request fixes.

## When to Use

After migrate-verify N passes. This is the final step in the phase cycle: Analyze → Plan → Execute → Verify → **Review**. After this passes, the phase is complete.

## Inputs

- **Phase number** (required) — which phase to review
- **--scope flag** (optional):
  - `diff` — review only the git diff for this phase (faster)
  - `full` — review all generated files regardless of diff
- **--fix flag** (optional) — auto-fix advisory issues (OVER_ENGINEERED, UNNECESSARY) without asking

**Required state:**
- Phase status: "verified"
- nn-verification.md exists with passing status
- config.json output_type determines which checks apply

## Procedure

### Step 1: Gather Review Context

1. Get git diff for this phase: `git diff migrate-phase-N-start..HEAD`
2. Read all Java files generated in this phase
3. Read corresponding C++ source files
4. Read decisions.md for justified divergences

### Step 2: Pass 1 — Semantic Fidelity Review

Spawn a reviewer agent focused on semantic fidelity:

**Checks:**
- Are there behavior changes NOT recorded in decisions.md?
- Are there silently dropped methods or functionality?
- Are error paths handled equivalently?
- Is thread-safety preserved where C++ was thread-safe?
- Are return values semantically equivalent (not just typed similarly)?
- Are side effects preserved (writes, events, state changes)?

**Verdict per file:** `FAITHFUL` | `DRIFT_MINOR` | `DRIFT_MAJOR`
- `DRIFT_MINOR`: Acceptable if justified (log it)
- `DRIFT_MAJOR`: Unacceptable — must fix or record decision

### Step 3: Pass 2 — Ponytail Minimalism Audit

Spawn a reviewer agent focused on minimalism:

**Checks against the migration ladder:**

1. **Is there code that doesn't need to exist?**
   - Dead code carried over from C++ that was dead there too
   - Defensive code beyond what the C++ had (unless at trust boundary)

2. **Does the framework already provide this?** (Skip for library/sdk output_type — Spring is not a dependency)
   - Hand-rolled connection pooling (use HikariCP default)
   - Manual retry logic (use Resilience4j)
   - Custom serialization (use Jackson auto-config)

3. **Are there unnecessary abstractions?**
   - Wrapper classes that add nothing
   - Interfaces with only one implementation (unless it's a port)
   - Builder patterns where a constructor/record works

4. **Could it be simpler?**
   - Multi-step code that a single annotation handles
   - Manual bean wiring that auto-configuration covers
   - Verbose null checks that Optional handles

5. **Is the output type respected?**
   - Library producing adapter/in/web/ code → VIOLATION
   - Library with Spring Boot starters in dependencies → OVER_ENGINEERED (use compileOnly)
   - CLI with REST controllers → WRONG_TYPE
   - Service missing application.yml → INCOMPLETE

**Verdict per finding:** `OVER_ENGINEERED` | `UNNECESSARY` | `SIMPLIFIABLE` | `APPROVED`

### Step 4: Consolidated Verdict

Combine both passes into a review document:

```markdown
## Migration Review: Phase N

### Semantic Fidelity
| File | Status | Notes |
|------|--------|-------|

### Minimalism Audit
| File | Finding | Severity | Action |
|------|---------|----------|--------|

### Verdict: APPROVED | NEEDS_FIXES | BLOCKED
```

### Step 5: Resolution

**If APPROVED (no blocking issues):**
1. Tag commit: `git tag migrate-phase-N-complete`
2. Update state.md: `status: completed` for this phase
3. Update progress metrics
4. Report: phase done, suggest migrate-analyze N+1 for next phase
5. **If this is the LAST phase** (all phases in roadmap.md are now `completed`):
   - Run final full target graph build:
     ```bash
     graphify {target_root}/src --mode deep
     ```
   - Run source↔target comparison:
     ```bash
     graphify query "compare overall architecture coverage between source and target"
     ```
   - Generate ARC42 documentation (graphify `arc42` mode — see graphify-integration.md):
     - Read ALL migration artifacts (graphs, decisions, mapping, tech-debt, phase analyses)
     - Generate all 12 ARC42 sections to `.migration/arc42/`
     - Use `arc42-generation-template.md` as the structural guide
     - Write in German (DATEV convention)
   - Copy ARC42 docs into target project:
     ```bash
     cp -r .migration/arc42/ {target_root}/docs/arc42/
     ```
   - Copy final graph visualization into target project:
     ```bash
     mkdir -p {target_root}/docs/architecture
     cp .migration/graphs/target/graph.html {target_root}/docs/architecture/
     cp .migration/graphs/target/GRAPH_REPORT.md {target_root}/docs/architecture/
     ```
   - Commit: `docs(arc42): generate architecture documentation from migration`
   - Report: "Migration complete. ARC42 documentation generated. Open {target_root}/docs/arc42/arc42-documentation.md"

**If NEEDS_FIXES:**
1. If `--fix` flag: auto-apply non-risky fixes (OVER_ENGINEERED, UNNECESSARY)
2. Otherwise: present fix list to user, ask which to apply
3. After fixes: re-run verification gates
4. Re-review fixed code (abbreviated)

**If BLOCKED (semantic drift detected):**
1. List all DRIFT_MAJOR items
2. For each: suggest fix OR ask user to record as intentional in decisions.md
3. Do NOT advance until all drift is resolved or justified

## Outputs

- Review verdict in console output
- Git tag: `migrate-phase-N-complete` (if approved)
- state.md updated with completion status and progress metrics
- If final phase:
  - `.migration/arc42/` — Full ARC42 documentation (12 sections)
  - `.migration/graphs/target/` — Final target architecture graph
  - `{target_root}/docs/arc42/` — ARC42 docs in target project
  - `{target_root}/docs/architecture/graph.html` — Interactive architecture visualization

## Success Criteria

- All generated Java files reviewed for semantic fidelity
- Ponytail audit completed — no unjustified over-engineering
- All DRIFT_MAJOR items resolved (fixed or justified in decisions.md)
- Phase tagged in git: `migrate-phase-N-complete`
- state.md updated with completion status
- Progress metrics accurate
