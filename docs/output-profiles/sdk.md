# SDK Output Profile

Use this profile for a published library whose primary product is a stable developer
experience for external consumers. The SDK profile extends every requirement in the
library output profile and adds compatibility, documentation, examples, diagnostics, and
support guarantees.

## Public Experience Contract

The API surface must make the common path obvious and the unsafe path difficult. Record:

- supported runtimes, platforms, transports, and service/API versions;
- stability level for every public API and SPI element;
- thread-safety, blocking, resource ownership, pagination, retry, and rate-limit semantics;
- authentication/credential handling without embedding secret values in diagnostics;
- error categories with actionable recovery guidance; and
- support and deprecation timelines.

Generated service models are not automatically a usable SDK. Place generated protocol
types behind a deliberate public surface when exposing them would couple consumers to an
unstable schema or generator.

## Documentation

Every stable public element requires reference documentation. Every primary user journey
requires a complete, executable example that includes setup, success handling, expected
errors, cleanup, and version assumptions.

Maintain at least:

- a minimal quick start;
- task-oriented guides for common journeys;
- API reference linked to stability and thread-safety contracts;
- an upgrade/deprecation guide;
- executable samples tested against the published artifact; and
- release notes that identify breaking, behavioral, and dependency changes.

Examples are consumer-contract fixtures, not unverified snippets. Redact or synthesize all
credentials, tokens, endpoints, and personal data.

## Compatibility and Release

- Use semantic versioning only with a written definition of what the SDK treats as public.
- Compare source and binary surfaces where the target ecosystem distinguishes them.
- Test serialization and generated-model compatibility when consumers persist SDK values.
- A deprecated element names its replacement, migration steps, and earliest removal release.
- Validate the SDK against every supported service/API version or state a narrower matrix.
- Test the installed/published package, not only the repository classes.

## Migration and Cutover

Provide a compatibility guide mapping legacy calls, errors, configuration, and lifecycle
to the target SDK. Run representative consumer applications against both artifacts. Track
adoption and unresolved consumer blockers before retiring the legacy SDK.

## Required Gates

- all library-profile gates;
- documentation coverage and broken-link checks;
- compile-and-run tests for every published example;
- public API/SPI stability classification and compatibility report;
- representative consumer fixture matrix; and
- packaged artifact, metadata, and dependency inspection.

## Rule Provenance

Shared metadata: `applicability` is any migration selecting the SDK output profile;
`source` is this portable SDK consumer/compatibility policy; `owner` is output profile `sdk`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `OUT-SDK-001` | SDK examples are executable compatibility promises. | Example test validator | Published-artifact example results | Output profile v2 |
| `OUT-SDK-002` | Unclassified public symbols create accidental support obligations. | API metadata validator | Stability report for every public symbol | Output profile v2 |
| `OUT-SDK-003` | Consumers need an actionable path through intentional API change. | Release review gate | Deprecation and upgrade guide | Output profile v2 |
