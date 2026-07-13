# Creating a Target-Language Profile

A target profile defines one target language/toolchain's capabilities, runtime compatibility,
build and dependency controls, quality tooling, and architecture-enforcement mechanisms. It
does not select a service/library/SDK/CLI architecture; output profiles own those contracts.

## Paths and Manifest

Use a stable lowercase, hyphenated versioned ID where the language version changes the
contract, and create:

```text
docs/profiles/targets/<target-id>/profile.json
docs/standards/targets/<target-id>/
```

The manifest conforms to `schemas/profile.schema.json` and declares version/kind/ID,
capabilities, all common target documents, canonical typed variables/commands, and
provenance. Output-specific target documents are selected from each output profile's
`target_documents` map rather than placed in every compiled bundle.

Use `docs/profiles/targets/java-25/profile.json` as the structural example. A new target
must compose without a generic compiler or workflow change.

## Common Target Knowledge

Cover:

- exact supported language/runtime/toolchain baseline and support matrix;
- permanent versus preview/incubator/experimental features and opt-in policy;
- runtime, standard-library, charset/locale/time/filesystem, removed-API, and platform compatibility;
- modules/packages, public API inspection, and available dependency-direction validators;
- build wrapper/toolchain, compile/test/lint/package commands, deterministic output, and metadata validation;
- dependency declarations, graph alignment, locking, integrity, vulnerability/license, and repository policy;
- static analysis, formatting, testing, coverage/mutation capabilities, and artifact inspection; and
- primary sources plus last-reviewed runtime/build-tool versions.

Do not mandate every modern feature. Select features when they preserve semantics or improve
safety without violating compatibility. Do not freeze unrelated ecosystem point releases in
knowledge prose; project dependency decisions own reviewed coordinates.

## Output Specializations

For each supported output profile, add only target-specific implementation guidance:

- service framework/module/adapter validation;
- library API/internal/SPI export and publication checks;
- SDK documentation, examples, stability, and compatibility tooling; or
- CLI parser, stream/exit, launcher, and packaging tooling.

The portable output documents remain under `docs/output-profiles/`. If a target cannot
satisfy an output's required capability, composition fails instead of installing incomplete guidance.

## Enforcement and Provenance

Each important rule states rationale, applicability, enforcement, required evidence, source,
and reviewed version according to `docs/provenance/rule-metadata.md`. Review gates are labeled
as judgment; they are not described as deterministic validators.

## Validation

- Manifest/documents/provenance conform to schemas and compile without unresolved references.
- Commands are present and executable in a minimal fixture.
- Permanent/preview status and removed/runtime claims match primary documentation.
- Architecture examples compile and fail on representative violations.
- Dependency resolution, lock, and integrity controls are tested separately.
- Every declared output specialization composes and passes its fixture.
- Repeated compilation is byte-identical.
- Adding the target required no generic compiler/workflow modification.

## Review Checklist

- [ ] Target ID/version and support matrix are explicit.
- [ ] Runtime compatibility goes beyond source syntax.
- [ ] Preview/incubator features are opt-in and version-gated.
- [ ] Output architecture is not mislabeled as universal target guidance.
- [ ] Dependency catalog, alignment, locking, and integrity have distinct controls.
- [ ] Quality thresholds are profile/risk-configured, not blanket percentages.
- [ ] Target-specific output documents exist only for supported compositions.
- [ ] Version-sensitive rules cite primary sources and reviewed versions.
