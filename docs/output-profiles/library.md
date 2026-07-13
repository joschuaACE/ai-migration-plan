# Library Output Profile

Use this profile for a reusable artifact loaded directly by consumer code and released
independently from those consumers. A library has no mandatory process entry point or
runtime container.

## API / Internal / SPI Architecture

Separate the artifact into three conceptual surfaces:

| Surface | Audience | Compatibility promise |
|---|---|---|
| API | Code that calls the library | Public inputs, results, errors, lifecycle, and documented behavior |
| Internal | Library implementation only | No consumer access; may evolve within release policy |
| SPI | Consumer or third-party implementations | Provider contracts, discovery, lifecycle, and evolution rules |

Do not create an SPI merely to mirror an internal interface. Add one only when consumers
must supply a behavior or implementation. Keep API inputs and result types separate from
SPI lifecycle and provider context unless they genuinely share a compatibility contract.

The target profile must enforce exported/public packages or modules so internals are not
accidentally consumable. Reflection or naming conventions alone are insufficient when the
target offers a stronger boundary mechanism.

## Consumer Contract

Record and test:

- source and binary compatibility promised by the ecosystem;
- initialization, resource ownership, thread-safety, and shutdown behavior;
- error categories and recovery expectations;
- serialization or wire formats exposed to consumers;
- extension discovery, ordering, isolation, and failure behavior;
- optional versus required dependencies; and
- packaging metadata, supported runtimes, and published checksums/signatures.

Avoid runtime-framework types in the core public API unless framework integration is the
library's purpose. Put optional integrations in separate artifacts or explicitly optional
modules so consumers do not inherit unrelated runtime dependencies.

## Evolution Rules

- Minimize the public surface; every public symbol is a compatibility commitment.
- Prefer immutable values at boundaries when the target supports them without changing semantics.
- Document nullability/absence, ownership, blocking, concurrency, and error behavior.
- Adding a method to a consumer-implemented SPI may be breaking even when adding it to a
  library-implemented API interface is not; evaluate both source and binary impact.
- Deprecate with a replacement and migration path before removal, subject to the release policy.

## Migration and Coexistence

Run the same consumer-contract suite against legacy and target artifacts. Coexistence may
use a facade, compatibility module, build-time binding, or namespaced parallel versions.
Cutover is consumer adoption, so track supported consumers and do not decommission the
legacy artifact solely because the target package was published.

## Required Gates

- exported-surface and accidental-public-API check;
- consumer contract suite and representative integration fixture;
- source/binary compatibility check required by the target ecosystem;
- dependency exposure and packaged-artifact inspection; and
- license, provenance, integrity, and publication metadata checks.

## Rule Provenance

Shared metadata: `applicability` is any migration selecting the library output profile;
`source` is this portable library consumer-contract policy; `owner` is output profile `library`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `OUT-LIBRARY-001` | Internal freedom depends on an enforceable public boundary. | API-surface validator | Exported/public API report | Output profile v2 |
| `OUT-LIBRARY-002` | Consumer-implemented contracts evolve differently from caller-facing contracts. | Compatibility validator and review | API/SPI classification and compatibility result | Output profile v2 |
| `OUT-LIBRARY-003` | Publication is not consumer cutover. | Traceability and decommission gate | Supported-consumer adoption evidence | Output profile v2 |
