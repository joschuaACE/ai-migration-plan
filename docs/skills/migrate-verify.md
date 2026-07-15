# migrate-verify

Verify translated Java code is semantically equivalent to C++ source — two-stage gate checking behavioral fidelity and architecture quality.

## When to Use

After migrate-execute N completes all waves. This is the fourth step in the phase cycle: Analyze → Plan → Execute → **Verify** → Review.

## Inputs

- **Phase number** (required) — which phase to verify
- **--deep flag** (optional) — method-by-method comparison (slower, more thorough)
- **--report-only flag** (optional) — produce report without blocking progression

**Required state:**
- Phase status: "executed"
- All plans in phase have summary.md
- Build passes, tests pass

**Context to read before starting:**
1. nn-analysis.md — the original C++ analysis
2. All nn-pp-plan.md files — what was intended
3. All nn-pp-summary.md files — what was actually done
4. The C++ source files
5. The generated Java files
6. config.json → check output_type (determines which quality checks apply)

## Procedure

### Stage 1: Semantic Equivalence Verification

Spawn a verifier agent with C++ source + Java target for each plan:

#### 1.1 Method-Level Comparison
For every public method in the C++ class:
- Corresponding Java method exists
- Same parameter semantics (types may differ, meaning must match)
- Same return semantics
- Same side effects
- Same error conditions produce equivalent exceptions

#### 1.2 Behavioral Path Tracing
For each critical execution path identified in nn-analysis.md:
- The path exists in Java code
- Same decision points (if/else, switch)
- Same loop behavior (iteration count, termination condition)
- Same ordering guarantees

#### 1.3 Edge Case Verification
- Null/nullptr handling: C++ nullptr checks → Java Optional or null guards
- Overflow handling: C++ integer overflow → Java behavior (document if different)
- Error propagation: C++ exceptions → Java exceptions (same escalation)
- Resource cleanup: C++ destructors → Java try-with-resources / @PreDestroy
- Thread safety: if C++ was thread-safe → Java must be too

#### 1.4 API Contract Check
- All public methods from C++ exist in Java (or explicitly removed via decisions.md)
- Method signatures are compatible (callers can migrate without surprises)
- Return types preserve the same information
- Exception types are documented and equivalent

#### Semantic Scoring
```
Score = (methods_verified_equivalent / total_public_methods) × 100
```
- 95-100%: PASS
- 85-94%: PASS with notes
- <85%: FAIL — gaps must be addressed

### Stage 2: Architecture Quality Verification

#### 2.1 Hexagonal Compliance
Run ArchUnit test suite:
```bash
cd app && ./gradlew test --tests '*HexagonalArchitectureTest'
```
- Domain has zero Spring imports
- Dependencies point inward
- Ports are interfaces
- No package cycles

#### 2.2 Spring Boot 4.x Standards (service and cli output_type ONLY)

Skip this section entirely for library/sdk output_type.

- Constructor injection only (no @Autowired fields)
- Records used for DTOs/value objects
- @ConfigurationProperties records (no @Value)
- ProblemDetail for error responses (service only)
- Virtual threads enabled (service only)
- Proper use of RestClient (not RestTemplate) (service only)

#### 2.2b Library/SDK Standards (library and sdk output_type ONLY)

- No @SpringBootApplication class exists
- No application.yml/properties exists
- No Spring Boot starter dependencies in runtime scope
- Public API consists of port/in interfaces + domain model records
- module-info.java exists and correctly exports public packages
- SPI interfaces (port/out) properly documented for consumers
- No framework-specific annotations on public API types
- Dependencies use `api()` vs `implementation()` correctly

#### 2.3 Code Quality
- No method > 30 lines
- No class > 200 lines (excl. imports)
- No constructor > 4 dependencies
- Cyclomatic complexity ≤ 10 per method
- No utility classes with static methods (should be services)
- No business logic in adapters

#### 2.4 Test Quality
- Every public method has at least one test
- Domain tests have NO Spring context (pure unit tests)
- No test relies on execution order
- Each test has meaningful assertions
- Coverage meets threshold for this layer

#### 2.5 Ponytail Audit (Over-engineering Detection)
- No abstractions that didn't exist in C++ (unless justified in decisions.md)
- No wrapper classes around things that work unwrapped
- No "just in case" interfaces (only ports are interfaces, and they're driven by need)
- Spring auto-configuration used where available (not manual wiring)
- No premature optimization patterns
- Output type respected — no Spring Boot infrastructure in library output, no controllers in CLI output

#### Quality Scoring
```
Score = (checks_passing / total_checks) × 100
```
- 90-100%: PASS
- 80-89%: PASS with advisory notes
- <80%: FAIL — fix before proceeding

### Output: nn-verification.md

Write the verification document with YAML frontmatter:
```yaml
---
phase: N
status: passed | gaps_found | failed
semantic_score: <0-100>
quality_score: <0-100>
test_coverage:
  line: <percent>
  branch: <percent>
archunit: passing | failing
gaps: <count of issues>
blocking_issues: <count>
advisory_issues: <count>
---
```

Followed by: Semantic Equivalence Results (verified methods table, gaps found table), Architecture Quality Results (passing checks, issues), Recommendations, and Verdict (PASS / PASS_WITH_NOTES / FAIL).

### Decision Gate

- If PASS: Update state.md → `status: verified`, suggest migrate-review N
- If PASS_WITH_NOTES: Show notes to user, ask to proceed or fix
- If FAIL: List blocking issues, suggest fixes, do NOT advance state

## Outputs

- `.migration/phases/NN-slug/nn-verification.md` — full verification results with scores and verdict

## Success Criteria

- Every public method compared (C++ vs Java)
- Semantic score calculated and meets threshold
- ArchUnit tests pass
- Code quality checks run
- Coverage verified against thresholds
- Ponytail audit completed (no over-engineering)
- nn-verification.md written with full results
- Blocking issues (if any) clearly listed with fix suggestions
- state.md updated appropriately
