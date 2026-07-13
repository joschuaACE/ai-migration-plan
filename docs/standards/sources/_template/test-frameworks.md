# [LANGUAGE_NAME] Test Framework Semantics

Describe how to detect and run source tests and what their constructs mean. Target-framework
mappings belong to pair profiles.

## Framework Record

### [FRAMEWORK NAME]

**Detection:** Dependency/build declarations, imports/includes, registration, runners, and
file conventions.

**Execution:** Discovery command, filters/tags, sharding/parallelism, configuration variants,
environment, working directory, and exit/result formats.

**Assertions:** Fatal versus continuing behavior, equality/matchers, approximate numeric,
errors/exceptions, death/process, snapshots/golden files, and custom diagnostics.

**Lifecycle:** Suite/test fixtures, setup/cleanup failure, parameterization/generation,
nested sections/subcases, retries, skips/disabled/quarantine, timeouts, and async behavior.

**Doubles:** Mock/fake registration, expectation cardinality/order, ownership, verification
timing, and external-system fixtures.

**Evidence:** Machine-readable reports, coverage/profiling, seeds, captured artifacts, and
environment metadata.

## Characterization Requirements

- Discover all test targets/build variants, not only conventionally named files.
- Run the source baseline before target execution and retain exact command/result provenance.
- Record skipped, disabled, flaky, quarantined, platform-specific, and expected-failure tests.
- Separate stdout, stderr, exit status, files/messages, and other side effects in golden evidence.
- Preserve nondeterministic seeds and normalize only fields approved by a behavior decision.
- Treat missing tools/platforms and tests that cannot run as evidence gaps, not passes.

## Coverage

Record source coverage tools, configuration, exclusions, path remapping, branch/condition
semantics, and reports. Coverage is supporting evidence; it does not prove behavioral
equivalence or create a universal target percentage.

## Checklist

- [ ] Top supported frameworks and custom runners are detectable.
- [ ] Assertion continuation and fixture/parameter semantics are documented.
- [ ] Death/process, timing, concurrency, skip/flaky, and platform behavior is covered.
- [ ] Source baseline commands/results are reproducible.
- [ ] No target test framework or mechanical test-count mapping appears here.
