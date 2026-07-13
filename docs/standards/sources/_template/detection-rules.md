# [LANGUAGE_NAME] Detection Rules

Define deterministic signals for identifying [LANGUAGE_NAME] source, build variants,
generated inputs, releasable artifacts, dependencies, tests, and platform behavior.

Apply these signals to every path in the deterministic `scope.json.source_snapshot`. Reconcile
each path with stable source inventory or an exception-backed excluded-file record. Unknown or
unclassified paths block discovery; familiar extensions and successful builds must not define a
smaller denominator implicitly.

## Language and Version Detection

| Signal | Meaning | Confidence/conflict policy |
|---|---|---|
| <!-- extension/shebang/manifest/compiler --> | <!-- version or language --> | <!-- policy --> |

Prefer build/compiler metadata over extensions. Record unknown or conflicting versions and
feature-inferred minimum versions separately.

## Build and Package Systems

| Sentinel/command | System | Extract |
|---|---|---|
| <!-- file/command --> | <!-- build tool --> | Targets, sources, flags, definitions, generated inputs, dependencies |

Do not impose a universal priority among build files. Identify the CI/release entry point
and preserve every supported configuration/platform/architecture/feature variant.

## Artifact Classification

| Build signal | Artifact evidence |
|---|---|
| <!-- declaration/output --> | Service-like process, CLI, library, SDK/public package, plugin, or mixed product |

Detection supplies evidence; the composed output-profile decision remains explicit. Mixed
products may require several migration outputs.

## Source and Generated Inputs

List source extensions, module/package declarations, interface/public-surface syntax,
generator definitions/inputs/outputs, resources/assets, FFI/native declarations, and code
excluded by supported variants.

## Dependency and Test Detection

Define manifest/import/link/runtime signals for dependencies and runner/fixture/assertion/
skip/parameterization signals for tests. Include coverage, benchmark, integration, and
platform-specific test configurations.

## Platform and Environment

Detect conditional compilation, runtime OS/architecture checks, environment/configuration,
locale/charset/time defaults, filesystem assumptions, native loading, device APIs, and
deployment scripts.

## Semantic Hazard Signals

| Hazard class | Detection examples | Required follow-up |
|---|---|---|
| Ownership/lifetime | <!-- syntax/APIs --> | Ownership graph and cleanup evidence |
| Errors/control flow | <!-- syntax/APIs --> | Failure categories and side effects |
| Concurrency/memory model | <!-- syntax/APIs --> | Ordering, visibility, cancellation analysis |
| Numeric/encoding/serialization | <!-- syntax/APIs --> | Boundary and byte-level characterization |
| Metaprogramming/generation | <!-- syntax/APIs --> | Instantiated/generated surface inventory |
| Undefined/implementation-dependent | <!-- language categories --> | Environment evidence and disposition |
| ABI/native/platform | <!-- declarations/loading --> | ABI/package/platform support record |

## Negative and Ambiguous Fixtures

Include non-project files that resemble [LANGUAGE_NAME], projects with conflicting versions,
several build systems, generated-only sources, unsupported variants, missing manifests, and
unsafe/pathological input. Detection must report ambiguity rather than silently default.
