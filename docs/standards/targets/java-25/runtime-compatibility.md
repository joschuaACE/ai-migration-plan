# Java 25 Runtime and Compatibility Guidance

Target Java 25 as a tested runtime and toolchain, not merely a source-syntax level. Record
the JDK distribution, supported operating systems/architectures, and support policy in the
project decisions. Long-term-support terms are vendor-specific.

Primary references:

- [Oracle JDK 25 Migration Guide](https://docs.oracle.com/en/java/javase/25/migrate/getting-started.html)
- [Significant Changes in JDK 25](https://docs.oracle.com/en/java/javase/25/migrate/significant-changes-jdk-25.html)
- [Removed Tools and Components](https://docs.oracle.com/en/java/javase/25/migrate/removed-tools-and-components.html)
- [Java 25 language changes](https://docs.oracle.com/en/java/javase/25/language/java-language-changes-summary.html)
- [OpenJDK JDK 25 feature list](https://openjdk.org/projects/jdk/25/)

## Supported, Preview, Incubator, and Experimental Features

Use permanent Java 25 features when they simplify the mapped behavior and the supported
runtime matrix accepts them. Do not require a new feature merely because it exists.

Representative permanent features available in Java 25 include records, sealed classes,
pattern matching used by earlier releases, virtual threads, the Foreign Function & Memory
API, Stream Gatherers, unnamed variables/patterns, Markdown documentation comments, scoped
values, module import declarations, compact source files and instance `main` methods,
flexible constructor bodies, and the key derivation function API.

The following Java 25 features are not ordinary permanent APIs:

| Feature | Java 25 status | Default policy |
|---|---|---|
| Structured Concurrency | Fifth preview | Disabled unless a decision approves preview use |
| Primitive Types in Patterns | Third preview | Disabled |
| Stable Values | Preview | Disabled |
| PEM Encodings of Cryptographic Objects | Preview | Disabled for compatibility-critical code |
| Vector API | Incubator | Disabled unless performance evidence and module/runtime support justify it |
| JFR CPU-Time Profiling | Experimental | Tooling decision only; never a product dependency by accident |

Preview use requires all of the following:

- a decision naming the JEP, exact JDK release, affected source sets, and replacement plan;
- `--enable-preview` at compile, test, packaging, and every runtime entry point;
- no preview types leaking into a published stable API/SPI unless explicitly supported;
- CI and packaged-runtime tests using the selected Java 25 distribution; and
- an upgrade gate because preview APIs and syntax may change or disappear.

## Compilation and Runtime Baseline

- Compile with a Java 25 toolchain and `--release 25` (or the build tool's equivalent) to
  constrain the documented Java SE API surface.
- Run tests and packaged-artifact smoke tests on the production JDK distribution; `--release`
  does not test vendor, filesystem, TLS provider, native library, or runtime behavior.
- Treat compiler warnings, deprecated-for-removal APIs, and illegal-access workarounds as
  migration findings with owners.
- Do not use internal `sun.*`, `com.sun.*`, or other encapsulated JDK APIs without a narrow,
  approved exception and removal plan.

## Module Boundaries and Encapsulation

Select module boundaries according to the output profile:

- libraries and SDKs should export only intentional API/SPI packages and declare required
  modules precisely;
- services may use explicit application modules even when the final runtime is not a fully
  modular image; and
- CLIs should not introduce modules solely for ceremony, but packaged runtime images need
  explicit dependency analysis.

Run `jdeps --jdk-internals` on produced classes/artifacts and inspect transitive dependencies.
Use `jdeps`/`jlink` analysis for custom runtime images. `--add-opens`, `--add-exports`, and
automatic-module-name workarounds are temporary compatibility exceptions, not the default
architecture. Test service loading, reflection, serialization, annotation processing, and
resource lookup across the selected module boundary.

## Charset, Locale, Time, and Platform Defaults

Java SE APIs use UTF-8 as the default charset from JDK 18 onward, but that does not make
implicit decoding safe for migration. Console encoding, native encoding, legacy files,
protocols, subprocesses, and dependent libraries may use different encodings.

- Specify `Charset` at every persisted, protocol, and subprocess boundary.
- Characterize malformed/unmappable input policy and BOM handling.
- Preserve or deliberately normalize Unicode normalization and locale-sensitive case mapping.
- Pass an explicit `Locale` for machine formats and a `ZoneId`/clock for time-sensitive logic.
- Test line endings, path case/normalization, permissions, symlinks, and atomic file operations
  on every supported platform.
- Never use the current default locale, zone, or charset as a hidden protocol definition.

## Removed and Changed APIs

For migrated code and every upgraded dependency:

1. Compile from a clean dependency cache with the Java 25 toolchain.
2. Run `jdeprscan --release 25` against the produced artifact and review deprecated-for-removal APIs.
3. Run `jdeps --jdk-internals` and eliminate or approve internal API use.
4. Review the official removed-tools/components lists for every JDK release between the
   previous supported runtime and 25.
5. Run behavioral tests for strong encapsulation, security-provider/TLS, locale data,
   garbage collection, finalization/cleaner usage, process launching, and native access
   where the source or dependencies rely on them.
6. Test startup scripts and operational flags; removed command-line options can break a
   deployment even when application bytecode compiles.

Static analysis cannot see every reflective lookup or dynamically loaded provider. A clean
`jdeps` result is one piece of evidence, not a complete compatibility claim.

## Native Interoperability

The Foreign Function & Memory API is permanent in Java 25, but selecting it does not remove
native risk. Preserve ABI, layout, lifetime, thread, callback, error, and packaging contracts.
Pin native library versions, generate or verify layouts against supported platforms, and run
failure-path tests. Keep native access behind a target boundary so it can be replaced.

## Rule Provenance

Shared metadata: `applicability` is every Java 25 target composition; `source` is the linked
Oracle JDK 25 migration/language documentation and OpenJDK 25 feature list; `owner` is target
profile `java-25`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `TGT-JAVA25-001` | Preview features bind source and runtime to one release and may change incompatibly. | Build/profile validator | Decision plus compile/test/runtime preview flags | JDK 25 GA |
| `TGT-JAVA25-002` | `--release` constrains APIs but cannot prove runtime compatibility. | Java compatibility gate | Toolchain compile plus packaged-runtime matrix | JDK 25 GA |
| `TGT-JAVA25-003` | UTF-8 defaults do not describe legacy files, console, native, or protocol encodings. | Boundary review and tests | Explicit charset and compatibility fixtures | JDK 25 GA |
| `TGT-JAVA25-004` | Static analysis misses reflective and dynamic linkage. | Compatibility gate | `jdeps`, `jdeprscan`, and runtime smoke results | JDK 25 GA |
