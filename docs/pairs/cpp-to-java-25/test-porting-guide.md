# C++ Test Suites to Java 25

Port the behavioral contract expressed by the source suite, including fixtures, parameter
generation, assertion continuation, process termination, timing, and environment. Do not
translate tests by macro count or require one Java test per C++ test/method.

Before changing a test, run the source suite in every supported build variant and store the
result as characterization evidence. Link each target test to behavior IDs and retain the
source test location.

## Google Test and Google Mock

### Assertions

| gtest/gmock | JUnit Jupiter / AssertJ candidate | Semantic note |
|---|---|---|
| `ASSERT_EQ`, `ASSERT_NE`, relational `ASSERT_*` | AssertJ equality/relational assertion | Fatal assertion stops the current C++ test; ordinary Java assertion stops the current test method. |
| `EXPECT_EQ` and other `EXPECT_*` | `SoftAssertions` or `assertAll` when continuation matters | Preserve evaluation order and the fact that later checks execute. |
| `ASSERT_TRUE/FALSE` | Boolean assertion | Prefer an assertion on the actual domain value when it gives better diagnostics. |
| `ASSERT_STREQ/STRNE` | String assertion | Characterize null pointers, embedded NUL, encoding, and case rules. |
| `ASSERT_NEAR`, float/double equality | AssertJ close-to or custom numeric comparator | Preserve absolute/relative/ULP tolerance, NaN, infinity, and signed-zero policy. |
| `ASSERT_THROW` / `EXPECT_THROW` | `assertThrows` or AssertJ throwable assertion | Check exact/assignable type, message/metadata, side effects, and cleanup as required. |
| `ASSERT_NO_THROW` | `assertDoesNotThrow` / AssertJ code assertion | Do not hide assertions inside a wrapper that changes failure diagnostics. |
| `EXPECT_THAT` | AssertJ or a custom assertion | Port custom matcher semantics and mismatch descriptions. |
| `GTEST_SKIP` | JUnit assumption/aborted test or conditional execution | Preserve reporting and reason; do not turn unsupported behavior into a pass. |
| `EXPECT_DEATH` / `ASSERT_DEATH` | Separate-JVM process harness | Java in-process exception assertions cannot prove exit status, signal, or stderr. |

### Fixtures and Parameterization

| gtest feature | Java candidate | Check |
|---|---|---|
| `TEST` | `@Test` | Name/tag/source-location traceability |
| `TEST_F`, `SetUp`, `TearDown` | `@BeforeEach`, `@AfterEach`, helper/extension | Construction and cleanup order, including failed setup |
| Suite setup/teardown | `@BeforeAll`, `@AfterAll`, extension | Static/instance lifecycle and parallel execution |
| `TEST_P`, instantiation | `@ParameterizedTest` plus source | Display names, Cartesian cases, invalid cases, lazy generation |
| Typed tests | Parameterized class/type token, interface contract suite, or generated tests | Generic erasure and per-type behavior |
| `SCOPED_TRACE` | Assertion description or extension context | Nested context must appear in failure output |

For gmock, preserve expectation cardinality, ordering (`InSequence`), defaults, actions,
argument capture, ownership, and verification timing. Mockito is a candidate, not a direct
equivalent. Prefer fakes or contract tests when interaction mocking would reproduce C++
implementation detail rather than observable behavior.

## Catch2

| Catch2 feature | Java candidate | Semantic note |
|---|---|---|
| `REQUIRE` | Ordinary fatal assertion | Stops only the current generated section/test path. |
| `CHECK` | Soft assertion / `assertAll` | Later assertions must still execute where observable. |
| `REQUIRE_THROWS*` / `CHECK_THROWS*` | Throwable assertion | Preserve continuation and exception matching. |
| `TEST_CASE` | Test method or nested test container | Preserve tags and reporter identity as needed. |
| `SECTION` | Separate/nested tests plus a fixture factory | Catch2 re-enters the test case from the beginning for each section path; do not share mutated state accidentally. |
| `GENERATE` | Method/argument source | Preserve generated values, combinations, and shrinking/seed behavior if used. |
| Template test cases | Contract test run over selected Java types/implementations | Preserve actual instantiated type set. |
| `INFO`, `CAPTURE` | Assertion descriptions/test reporter context | Preserve diagnostic values without logging secrets. |

## doctest

| doctest feature | Java candidate | Semantic note |
|---|---|---|
| `CHECK` / `REQUIRE` | Soft/fatal assertion as appropriate | Preserve continuation distinction. |
| `SUBCASE` | Separate/nested tests plus fixture factory | Like Catch2 sections, subcases re-enter enclosing code. |
| `TEST_CASE` / template case | Test or parameterized contract suite | Preserve registration and instantiated cases. |
| `CHECK_THROWS*` | Throwable assertion | Preserve exact matching and later execution. |
| doctest-in-production embedding | Separate target test source set or approved self-test entry point | Preserve consumer-visible self-test behavior if it is a real contract. |

## Behavioral Characterization Patterns

Use the strongest practical pattern for the boundary:

- **Golden master:** capture stdout, stderr, exit status, bytes, files, messages, or protocol
  output separately. Normalize only approved unstable fields.
- **Differential harness:** feed identical generated/boundary inputs to source and target and
  compare categorized outputs and side effects.
- **Contract suite:** run one behavior suite against legacy and target APIs/adapters.
- **Native fixture:** preserve known ABI/layout/protocol vectors when direct dual execution
  is not practical.
- **Property test:** express invariants and generate edge cases, retaining failing seeds.

Do not make the target test pass by updating a golden file before the difference has a
decision. Store source runtime, compiler, build variant, locale, zone, and platform with
environment-sensitive evidence.

## Test Doubles and External Systems

- Mock only a declared boundary; do not mock value objects or internal implementation calls.
- A fake must implement the same port/contract and pass shared contract tests where practical.
- Use a real compatible dependency in adapter integration tests for serialization, SQL,
  file, network, and transaction behavior.
- Record clock, randomness, scheduler, and identifier sources explicitly for deterministic tests.
- Preserve retry, timeout, cancellation, partial-write, cleanup, and concurrency failure cases.

## Java Test Design

- Use JUnit Jupiter as the baseline runner and an assertion library selected by the target profile.
- Choose test structure by behavior: one parameterized test may represent many source cases;
  one source test may require several Java tests to isolate contracts.
- Test names describe behavior and condition without requiring one naming grammar.
- Run tests under the output profile's packaging/runtime boundary where relevant, not only as unit tests.
- Keep source characterization results even after target tests pass; they are provenance for equivalence.

## Completion Criteria

A source suite is ported when:

- all behavior IDs it covers map to passing target evidence or an approved exception;
- skipped, disabled, flaky, death, timing, and platform-specific tests have explicit dispositions;
- fixture and assertion continuation semantics are preserved or intentionally changed;
- source-only gaps have new characterization where risk requires it; and
- deterministic verification can reproduce both source baseline and target results.

## Rule Provenance

Shared metadata: `applicability` is test migration under pair `cpp-to-java-25`; `source` is
the source-framework semantics, JUnit Jupiter behavior, and source characterization results;
`owner` is pair profile `cpp-to-java-25`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `PAIR-CPP-JAVA25-TEST-001` | Macro-to-method counts do not measure behavioral coverage. | Traceability validator | Behavior-to-source/target test links | gtest, Catch2, doctest to JUnit Jupiter |
| `PAIR-CPP-JAVA25-TEST-002` | Section/subcase re-entry changes fixture state and execution paths. | Pair review | Ported section-path tests | Catch2/doctest current profile |
| `PAIR-CPP-JAVA25-TEST-003` | In-process exception tests cannot prove process-death behavior. | Test gate | Separate-process exit/stderr evidence or approved disposition | JDK 25 |
