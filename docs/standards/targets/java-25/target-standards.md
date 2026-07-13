# Java 25 Target Standards

These rules apply to Java 25 target artifacts. Architecture and delivery contracts come
from the selected output profile; Java package names and framework conventions do not
belong in the generic layer.

## Composition

Read the composed knowledge in this order:

1. generic migration and evidence principles;
2. source profile;
3. this Java 25 target profile;
4. selected language-pair guidance;
5. selected output profile (`service`, `library`, `sdk`, or `cli`);
6. the corresponding Java output specialization; and
7. approved project decisions.

Later layers may specialize a default, but they cannot silently weaken generic evidence,
traceability, or lifecycle requirements.

## Java 25 Baseline

- Use a Java 25 toolchain and compile with `--release 25` or the build-tool equivalent.
- Keep preview features disabled unless a version-specific decision satisfies every rule
  in `runtime-compatibility.md`.
- Prefer permanent language features when they improve clarity or safety; feature novelty
  is not a migration requirement.
- Verify the packaged artifact on every supported production JDK/platform combination.
- Treat JDK distribution and support lifetime as project decisions; LTS support terms are
  supplied by vendors, not by Java syntax.

`runtime-compatibility.md` is authoritative for permanent versus preview/incubator status,
module checks, charset/runtime differences, removed APIs, and native interoperability.

## Type and Value Semantics

- Use records for transparent immutable data carriers when record equality, construction,
  and serialization semantics match the contract. Do not turn entities with identity or
  lifecycle into records by default.
- Use sealed hierarchies when the set of variants is intentionally closed and compatible
  with consumer evolution.
- Make absence explicit at public boundaries. `Optional` is suitable for many return values,
  but is not a universal replacement for nullable fields, parameters, or serialization states.
- Define numeric range, overflow, rounding, scale, NaN/infinity, and conversion behavior
  from pair-specific analysis. `BigDecimal` is not automatically correct for every source
  floating-point value, and Java integer overflow may not match the source contract.
- Do not expose mutable collections directly. State whether returned collections are snapshots,
  immutable views, or live views.
- Specify charset, locale, time zone, clock, line endings, and path behavior at observable boundaries.

## Errors and Resources

- Model error categories and recoverability from characterized source behavior; do not
  collapse every failure into one unchecked exception.
- Preserve cause chains and sanitize sensitive content in messages and logs.
- Use checked or unchecked exceptions according to the public compatibility contract, not
  a blanket style rule.
- Use try-with-resources for deterministic lifetime of files, sockets, streams, native
  segments/arenas, locks represented as resources, and other closeable handles.
- Never depend on garbage collection, finalization, or cleaners for timely externally
  observable cleanup.
- Test partial construction, exceptions, cancellation, and shutdown paths.

## Concurrency

Virtual threads are appropriate for high-concurrency blocking workloads; they are not a
drop-in requirement for CPU-bound parallelism, affinity-sensitive native work, or existing
event-loop contracts. Select an executor and scheduling model from measured behavior.

- Reconstruct happens-before, atomicity, ordering, and cancellation guarantees explicitly.
- Avoid blocking while holding monitors or locks without analyzing contention and pinning/native behavior.
- Use scoped values for bounded immutable context propagation when lexical scope matches the
  contract; they are not a universal state store.
- Structured concurrency is preview in Java 25 and follows the preview policy.
- Test shutdown, interruption, timeout clocks, backpressure, and rejected work.

## Modules and Packages

- Let the output profile define business/module boundaries.
- Export only intentional library/SDK API and SPI packages.
- Keep implementation packages encapsulated and prevent dependency cycles.
- Run dependency and internal-API analysis on compiled artifacts.
- Treat `--add-opens` and `--add-exports` as time-bounded exceptions with owners.
- Keep framework, persistence, transport, and generated protocol types out of stable policy
  and consumer contracts unless exposure is intentional.

## Build and Dependency Discipline

- Treat `{target_root}` as the Gradle build root by default. Keep `settings.gradle` or
  `settings.gradle.kts`, the root `build.gradle` or `build.gradle.kts`, `gradlew`,
  `gradlew.bat`, `gradle/wrapper/`, version catalogs, verification metadata, locks,
  project-local `.gradle/`, `build/`, reports, and packaged output beneath it.
- When `{target_root}` is `app`, create a standalone build in `app/`; do not create a
  repository-root settings file with `include("app")`, a repository-root wrapper, or a
  repository-root `gradle/` directory.
- Reusing an existing repository-root multi-project build requires an accepted orchestration
  decision that lists every outside-target path, changes the canonical command working
  directory, assigns ownership, and defines rollback. Do not introduce such a topology only
  to bootstrap the target build.
- Commit the build wrapper and pin its distribution checksum.
- Pin plugins and dependency requests; prohibit dynamic versions, open ranges, and unreviewed snapshots.
- Centralize coordinates with a version catalog when appropriate, while recognizing that
  catalogs do not enforce the resolved dependency graph.
- Use platforms or dependency constraints when related artifacts require alignment.
- Commit and review dependency locking and integrity-verification metadata according to the
  project's reproducibility and supply-chain policy.
- Keep repositories explicit and content-filtered; do not add repositories from subprojects
  or generated scripts without a decision.
- Inspect the resolved runtime graph and packaged artifact, not only declared dependencies.

See `gradle-version-catalog.md` for Gradle-specific templates and enforcement detail.

## Verification Gates

The composed profiles select gates and thresholds based on behavior and risk. A Java target
typically supplies:

- clean compile, test, package, and packaged-artifact smoke results;
- behavioral contract/differential tests;
- changed-code coverage or mutation evidence where it reduces uncertainty;
- static analysis and architecture/module checks;
- dependency resolution, vulnerability/license policy, locking, and integrity checks;
- public API/binary checks for libraries and SDKs; and
- output-specific integration and operational checks.

Do not require one test per method, one test file per production class, or universal line
coverage percentages. Tests protect behavior and boundaries; thresholds are profile- and
risk-configured.

## Output Specializations

| Output | Portable architecture contract | Java specialization |
|---|---|---|
| Service | `docs/output-profiles/service.md` | `service-profile.md` |
| Library | `docs/output-profiles/library.md` | `library-profile.md` |
| SDK | `docs/output-profiles/sdk.md` | `sdk-profile.md` |
| CLI | `docs/output-profiles/cli.md` | `cli-profile.md` |

Only the service specialization defaults to Spring and modular hexagonal packaging.
Library and SDK targets use API/internal/SPI boundaries. A CLI uses command, stream,
exit-code, and packaging contracts and adopts additional ports only when justified.

## Java Anti-Patterns

- Using internal JDK APIs or permanent `--add-opens` workarounds without an exception.
- Relying on default charset, locale, zone, or filesystem behavior for a protocol.
- Translating ownership-sensitive RAII into GC-only cleanup.
- Assuming virtual threads preserve source scheduling, affinity, or memory-order semantics.
- Enabling preview features in only compilation or tests but not every runtime entry point.
- Exposing implementation/framework types through a stable library or SDK API accidentally.
- Treating a version catalog as dependency resolution enforcement.
- Declaring completion from coverage alone without behavioral evidence.

## Rule Provenance

Shared metadata: `applicability` is every Java 25 target composition; `source` is the Java
25 runtime guidance, official JDK 25 migration documentation, official Gradle guidance, and
the selected output contract; `owner` is target profile `java-25`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `TGT-JAVA25-BASE-001` | Source syntax and production runtime compatibility are different claims. | Java compatibility gate | Toolchain compile and packaged-runtime matrix | JDK 25 GA |
| `TGT-JAVA25-BASE-002` | Value-type convenience must not change identity, equality, or wire semantics. | Pair review and contract tests | Type-mapping decision and behavior results | JDK 25 GA |
| `TGT-JAVA25-BUILD-001` | Declared dependency requests do not prove a stable resolved graph. | Dependency validator | Resolution, lock, and integrity reports | Gradle 9.6.1 guidance |
| `TGT-JAVA25-BUILD-002` | A wrapper or settings file outside the target build root changes repository topology and invalidates target-root commands. | Workspace path and command preflight | Resolved build paths and exact command working directory | Framework schema v2 |
| `TGT-JAVA25-TEST-001` | Uniform method/file coverage rules are weak proxies for migration fidelity. | Profile gate validation | Behavior-linked, risk-configured quality gates | Framework schema v2 |
