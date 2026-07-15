# migrate-execute

Execute migration plans — translate C++ to Java with wave-based parallel agents, build/test gates after each wave, and auto-fix capabilities.

## When to Use

After migrate-plan N is confirmed by the user. This is the third step in the phase cycle: Analyze → Plan → **Execute** → Verify → Review.

## Inputs

- **Phase number** (required) — which phase to execute
- **--wave N** (optional) — execute only wave N (for pacing, retry, or granular control)
- **--interactive** (optional) — one plan at a time, no parallel agents, user checkpoints between plans
- **--dry-run** (optional) — show what would be executed without writing files

**Required state:**
- Plans exist: `.migration/phases/NN-slug/nn-pp-plan.md`
- Phase status: "planned" or "executing"
- Target project compiles: `cd app && ./gradlew compileJava` passes

**Read config.json → check output_type** to determine which waves apply.

## Procedure

### Step 1: Discover and Order Plans

1. Read all nn-pp-plan.md files for this phase
2. Parse YAML frontmatter → extract wave assignments and dependencies
3. Group plans by wave number
4. Read config.json output_type — if library/sdk, wave 6 (adapter/in/web) does not apply; if cli, wave 6 becomes adapter/in/cli
5. Verify no dependency violations within wave grouping
6. If `--wave N` specified, filter to only that wave
7. Update state.md: `status: executing`

### Step 2: Execute Waves Sequentially

For each wave (1 through max):

#### 2a. Pre-Wave Check
- Verify all dependencies from prior waves are satisfied (summary.md exists for each dependency)
- If a dependency failed, STOP and report

#### 2b. Spawn Parallel Translator Agents

For each plan in this wave, spawn a translator agent with:

**Agent receives (via file references):**
- The nn-pp-plan.md file
- The C++ source files listed in the plan
- The C++ header files listed in the plan
- Java target standards reference
- mapping.md (for package/naming)
- decisions.md (for architectural context)
- The output_type from config.json

**Agent must follow these iron laws:**
1. Read ALL C++ source completely before writing ANY Java
2. Follow the plan's translation table EXACTLY — no freelancing
3. Place Java files in correct hexagonal package
4. Apply Java 25 / Spring Boot 4.x standards
5. Domain classes have ZERO Spring imports
6. Write test file(s) covering every public method (at minimum), same behavioral paths as C++, boundary values and null cases
7. Verify compilation: `./gradlew compileJava`
8. Run tests: `./gradlew test --tests 'TargetClassTest'`
9. Write nn-pp-summary.md with execution record
10. Commit: `migrate(phase-N/plan-PP): SourceClass → TargetClass`
11. Mark uncertain translations: `// MIGRATION-REVIEW: <reason>`
12. Respect output_type — libraries have NO Spring Boot annotations in production code; CLIs use picocli @Command not @RestController

#### 2c. Post-Wave Gates (BLOCKING)

After all agents in the wave complete, run gates:

**Gates for ALL output types:**
```bash
# Gate 1: Full project compiles
cd app && ./gradlew compileJava

# Gate 2: All tests pass
./gradlew test
```

**Gate 3: ArchUnit hexagonal rules pass**
```bash
./gradlew test --tests '*HexagonalArchitectureTest'
```
- For service: includes Spring-specific checks
- For library/sdk: checks domain purity and dependency direction only
- For cli: checks adapter/in/cli/ instead of adapter/in/web/

**Gate 4: Coverage threshold met (if configured)**
```bash
./gradlew jacocoTestReport jacocoTestCoverageVerification
```

**If ANY gate fails:**
1. Identify which plan's code caused the failure
2. Spawn a fixer agent with: error output, the failing Java file(s), the plan, C++ source for reference
3. Fixer produces corrected code + amended commit
4. Fixer rules: fix the SPECIFIC error, don't redesign, don't change public API, don't remove tests
5. Re-run gates (max 2 fix attempts per wave)
6. If still failing after 2 attempts: STOP, report to user, mark plan as blocked

#### 2d. Post-Wave Bookkeeping
- Record wave completion in state.md
- Update progress metrics (files_migrated, lines_java_generated)
- Log timing metrics

### Step 3: Phase Completion

After all waves complete successfully:

7. Write phase summary: `.migration/phases/NN-slug/nn-phase-summary.md`
   - Total plans executed: X
   - Total Java files generated: Y
   - Total test files: Z
   - Build status: passing
   - Test count: N passing
   - Time elapsed: T
   - Issues encountered: [list]

8. Run full project test suite one final time
9. Check coverage report against thresholds
10. Update state.md:
    - `status: executed`
    - Increment `phases_complete` if all plans succeeded
    - Update `files_migrated` count
11. Suggest next step: migrate-verify N

## Outputs

- Java source files in correct hexagonal packages under `{target_root}`
- Test files mirroring source structure under `{target_root}/src/test/java/`
- `.migration/phases/NN-slug/nn-pp-summary.md` per plan — execution record
- `.migration/phases/NN-slug/nn-phase-summary.md` — phase-level summary
- Git commits per plan: `migrate(phase-N/plan-PP): Source → Target`

## Success Criteria

- All plans in the phase executed (or explicitly blocked with reason)
- Every generated Java file compiles
- Every generated test passes
- ArchUnit hexagonal rules pass
- Coverage thresholds met (or gaps documented)
- Each plan has a summary.md recording what was done
- Commits follow format: `migrate(phase-N/plan-PP): Source → Target`
- Commit validation: no files in domain/ import org.springframework.* (block commit if violated)
- Commit validation: if Java source files changed, corresponding test files also changed (warn)
- state.md updated with accurate progress
- No `// MIGRATION-REVIEW:` comments left unrecorded
