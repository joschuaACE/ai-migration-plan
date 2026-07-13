# Java 25 Library Specialization

This document specializes `docs/output-profiles/library.md` for a Java 25 artifact consumed
directly from another Java program. The default boundary is API/internal/SPI; do not impose
service controllers, application configuration, or dependency-injection runtime on consumers.

## Package and Module Boundary

```text
{target_root}/src/main/java/<base-package>/
├── api/            # Caller-facing contracts and values
├── spi/            # Optional consumer/provider implementations
└── internal/       # Non-exported implementation
```

Use additional feature subpackages when the public surface is large. Do not create `spi`
until consumers actually implement a contract.

When the supported ecosystem permits JPMS, use `module-info.java` to export only `api` and
intentional `spi` packages. Otherwise enforce the same surface with packaging/API analysis
and a documented automatic-module name where applicable.

Illustrative descriptor:

```java
module com.example.library {
    exports com.example.library.api;
    exports com.example.library.spi;

    uses com.example.library.spi.FormatterProvider;
    provides com.example.library.spi.FormatterProvider
        with com.example.library.internal.DefaultFormatterProvider;
}
```

Do not export or open `internal`. Add qualified `opens` only for a selected integration that
requires reflection, and test it on the module path. Avoid blanket `open module` declarations.

## API and SPI Design

- Keep the public surface minimal and intentional. A public class in an exported package is
  a compatibility promise even if documentation calls it internal.
- Records are appropriate for immutable transparent values only when their constructor,
  equality, component names, and serialization behavior are stable API.
- Expose interfaces when consumers need substitution or the implementation must vary. Do
  not add an interface for every class.
- Use factories/builders when they create evolution room or protect invariants; a public
  constructor is fine for a complete stable value.
- Document nullability/absence, ownership, thread safety, blocking, exceptions, complexity,
  and lifecycle for every public contract.
- Use `AutoCloseable` when a consumer must release external resources, and test idempotent
  close/use-after-close behavior.
- Public signatures may use an approved dependency type when it is intentionally part of the
  contract. Record the compatibility/transitive cost; do not require “JDK types only” blindly.
- Keep optional framework integrations in separate artifacts/modules or narrowly qualified
  packages so ordinary consumers do not inherit their runtime.

SPI implementors are downstream producers. Adding an abstract method, tightening inputs, or
changing discovery/lifecycle may break them even if ordinary API callers still compile.
Prefer capability/version negotiation or default methods only when a safe default exists.

## Errors and Compatibility

- Preserve source and binary compatibility according to the published release policy.
- Define public exception/result categories and whether implementations may add subtypes.
- Avoid leaking internal dependency exceptions; translate with the cause retained and
  sensitive values redacted.
- Treat record component changes, sealed permits changes, generic bounds, default methods,
  checked exceptions, annotations, and serialization identifiers as compatibility inputs.
- Deprecations name a replacement and migration path; removal requires the configured release gate.

Use japicmp, Revapi, or an equivalent selected validator against the last supported published
artifact. Compile representative consumer fixtures as well; a binary diff alone does not
prove behavioral compatibility.

## Gradle and Publication

Use `java-library` and the dependency controls in `gradle-version-catalog.md`.

- Declare `api` only when a dependency's types intentionally occur in the public contract;
  otherwise use `implementation`.
- Validate generated POM and Gradle module metadata, variants/capabilities, JPMS descriptor,
  automatic-module name, sources/docs artifacts, signatures, and checksums.
- Test from the repository-published artifact in an isolated consumer build.
- Reproducibly build the same coordinates; never republish different bytes under one version.
- Keep local lock files as producer-build evidence and publish constraints intentionally;
  consumers do not inherit producer locks automatically.

## Verification

- public API/SPI and accidental-export report;
- source/binary compatibility check against the configured baseline;
- behavior contract tests run against legacy and target implementations where possible;
- SPI provider contract tests and service-discovery/module-path tests when an SPI exists;
- resource, concurrency, serialization, and error compatibility tests where promised;
- published-artifact consumer fixtures on classpath/module path as supported; and
- dependency exposure, metadata, integrity, license, and package-content checks.

Coverage and mutation thresholds are risk-configured. Do not require one test per public
method or one test class per production class.

## Anti-Patterns

- exposing implementation packages because a consumer fixture imported them;
- making every internal interface an SPI;
- forcing a service framework or logging backend transitively on consumers;
- returning mutable internal collections or dependency-specific mutable state accidentally;
- relying on package naming without an API/export validator;
- changing consumer-implemented SPI contracts as though they were library-implemented API; and
- declaring publication successful without testing the published artifact from a consumer.

## Rule Provenance

Shared metadata: `applicability` is Java 25 plus library output; `source` is the portable
library contract and Java 25 module/API policy; `owner` is the Java 25 library specialization.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `TGT-JAVA25-LIB-001` | Java public/exported symbols become consumer compatibility commitments. | API/module validator | Exported surface report | JDK 25 / output profile v2 |
| `TGT-JAVA25-LIB-002` | SPI changes can break downstream implementations differently from callers. | Compatibility review | API/SPI classification and consumer fixtures | JDK 25 / output profile v2 |
| `TGT-JAVA25-LIB-003` | Producer locks do not constrain a consumer's resolved graph. | Publication validator | Published constraints/metadata and consumer resolution | Gradle 9.6.1 guidance |
