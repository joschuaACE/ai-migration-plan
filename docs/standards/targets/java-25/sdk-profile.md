# Java 25 SDK Specialization

This document specializes `docs/output-profiles/sdk.md`. Apply every Java library rule first,
then add the SDK's external-consumer, documentation, examples, diagnostics, and compatibility
requirements.

## Artifact Shape

Keep the core API/internal/SPI boundary from the library profile. Separate optional concerns
when they would otherwise burden all consumers:

```text
sdk-core/                 # Stable public API and implementation
sdk-integration-<name>/   # Optional framework/transport integration
sdk-samples/              # Executable consumer projects
sdk-bom-or-platform/      # Optional alignment contract for a multi-artifact SDK
```

Generated protocol clients/models belong in an internal or explicitly generated artifact
unless their types are intentionally part of the stable SDK API. Generation inputs, plugin
versions, and checksums are provenance inputs.

## Stability Classification

Classify every exported public type/member as the project's equivalent of:

- **stable:** normal compatibility and deprecation policy applies;
- **preview/beta:** consumer opt-in with a documented weaker evolution promise;
- **deprecated:** supported temporarily with replacement and removal horizon; or
- **internal:** not exported and not consumer accessible.

Use a repository-owned annotation or a selected well-supported annotation package, and
generate a machine-readable stability report. An “internal” annotation on an exported public
type is weaker than not exporting it.

## Java API Experience

- Offer a minimal creation path without requiring a DI container.
- Use immutable configuration/value types when their equality and serialization contracts
  are suitable; builders should validate coherently at `build()` and avoid ambiguous precedence.
- Define sync/async variants deliberately. Document executor use, blocking, cancellation,
  thread safety, callbacks, and context propagation.
- Model service/API errors into stable SDK categories while preserving status/code, request
  identifiers, retryability, and cause without leaking credentials or payload secrets.
- Document resource ownership and implement `AutoCloseable` for clients/transports that need
  deterministic shutdown.
- Keep telemetry hooks and logging backend-neutral for consumers.
- Do not expose Java 25 preview APIs from stable SDK surface by default.

## Documentation and Examples

Use Javadoc or Java 25 Markdown documentation comments consistently with the selected
documentation toolchain. Every stable public element documents purpose, parameters/type
constraints, return/absence, thrown errors, thread safety/blocking, resource lifecycle,
compatibility/stability, and a useful cross-reference.

Publish and test:

- a minimal quick start from an empty consumer project;
- authentication/configuration guidance with synthetic secrets;
- examples for primary workflows, pagination/streaming where applicable, errors/retries,
  cancellation, and cleanup;
- an upgrade/deprecation guide mapping legacy SDK calls to target calls;
- API reference and supported runtime/service compatibility matrix; and
- release notes that separate source, binary, behavioral, dependency, and security changes.

Compile and run examples against the locally published artifact in CI. Avoid snippets that
compile only because they can see repository internals or undeclared test dependencies.

## Compatibility

Use a selected API compatibility tool plus consumer fixtures. Review at least:

- binary and source surface;
- generic signatures, annotations, nullability, checked errors, and sealed hierarchies;
- record components and serialization shape;
- SPI provider compatibility and discovery;
- transitive/public dependency types and platform constraints;
- persisted SDK values/caches if consumers may store them; and
- supported Java/runtime and remote service/API version matrix.

Semantic versioning follows the repository's published definition of public API. Preview
classification is not permission for arbitrary silent breakage; document changes and migration.

## Diagnostics and Security

- Error messages state the failed operation and a safe next action where possible.
- Redact tokens, credentials, authorization headers, personally identifying data, and
  sensitive bodies from exceptions, logs, traces, examples, and `toString()` output.
- Expose request/correlation IDs and stable error codes when the remote contract supplies them.
- Make retryability explicit; do not tell consumers to retry unsafe operations blindly.
- Test dependency integrity, signature/checksum publication, provenance, and vulnerability/license policy.

## Verification

- every Java library gate;
- stability classification coverage for exported symbols;
- documentation lint/link/reference checks;
- clean compile and execution of published examples;
- representative consumer fixtures against supported Java and service/API versions;
- binary/source API comparison against the configured release baseline;
- error/redaction/resource/concurrency contract tests; and
- installed artifact metadata, dependency exposure, signatures, and checksums.

## Anti-Patterns

- exposing raw generated or transport types unintentionally;
- examples that use repository classes not present in the published artifact;
- a custom stability annotation with no validator or release-policy meaning;
- logging credentials or response bodies in “helpful” diagnostics;
- promising universal backward compatibility while changing public dependency types or SPI;
- treating documentation coverage percentage as proof that guidance is correct; and
- decommissioning the legacy SDK before supported consumers have an adoption disposition.

## Rule Provenance

Shared metadata: `applicability` is Java 25 plus SDK output; `source` is the portable SDK and
Java 25 library/compatibility policies; `owner` is the Java 25 SDK specialization.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `TGT-JAVA25-SDK-001` | Export boundaries are stronger than “internal” labels on public symbols. | Module/API validator | Export and stability report | JDK 25 / output profile v2 |
| `TGT-JAVA25-SDK-002` | Examples must reflect the artifact consumers actually receive. | Example fixture validator | Locally published artifact example results | JDK 25 / output profile v2 |
| `TGT-JAVA25-SDK-003` | Remote and Java compatibility both constrain an SDK. | Compatibility matrix validator | API diff plus consumer/service matrix results | JDK 25 / output profile v2 |
