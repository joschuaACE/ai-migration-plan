# Creating a Source-Language Profile

A source profile teaches the framework how to discover and characterize one language and
its ecosystem. It must not choose a target architecture or dependency replacement; those
belong to output and pair profiles.

## Paths and Manifest

Use a stable lowercase, hyphenated ID and create:

```text
docs/profiles/sources/<source-id>/profile.json
docs/standards/sources/<source-id>/
```

The manifest conforms to `schemas/profile.schema.json` and declares version/kind/ID,
capabilities, every source document, typed variables needed by workflows, and provenance.
Document paths are repository-relative, normalized, and confined to the source directory.

Use `docs/profiles/sources/cpp/profile.json` as the structural example. A new profile must
compose through its manifest without compiler or generic workflow changes.

## Knowledge Responsibilities

A production source profile covers:

- language/build/package-manager detection with conflicting-signal policy;
- every supported build/configuration/platform variant and generated input;
- output-artifact and public-surface detection without forcing an output decision;
- dependency and native/ABI boundary inventory;
- ownership/lifetime, error, concurrency, numeric, type-system, metaprogramming, and code-generation idioms;
- specified, unspecified, undefined, implementation-defined, and environment-dependent hazards;
- serialization, encoding, filesystem, time, locale, and platform behavior;
- test-framework structure, discovery, fixtures, assertions, skipping, and coverage evidence; and
- authoritative sources plus reviewed compiler/language versions.

Dependency catalogs identify source capabilities and detection signals. They do not name a
universal target replacement.

## Detection Quality

Prefer actual build metadata such as compile databases, lockfiles, module graphs, and CI/release
commands over extension heuristics. Preserve multiple variants until analysis proves them
equivalent. Record confidence and provenance for inferred findings.

Unknown language versions, generated sources, conditional code, or unsupported build variants
produce findings/exceptions; they do not silently receive defaults.

## Capabilities

Declare only capabilities the documents and validators genuinely provide. Typical source
capabilities include source detection, build-variant discovery, behavior characterization,
ownership analysis, or native-boundary analysis. Pair manifests fail composition if they
require an absent capability.

## Validation

- Manifest and provenance conform to schemas.
- Every declared document exists, is unique, path-safe, and compiled.
- Required variables are typed and fully resolved.
- Representative positive, negative, ambiguous, and multi-variant fixtures pass.
- Malformed/generated/path traversal inputs fail safely.
- Adding the source required no generic compiler/workflow modification.
- At least one independently registered pair composes successfully.

## Review Checklist

- [ ] Canonical ID and directory names match.
- [ ] Build variants and generated inputs are first-class.
- [ ] Hazards cover behavior categories, lifetime, errors, concurrency, numeric/encoding, ABI/native, and platforms.
- [ ] Test discovery includes disabled/flaky/platform-specific behavior.
- [ ] Source docs contain no target architecture or automatic dependency choices.
- [ ] Claims cite reviewed specifications/toolchain documentation.
- [ ] Conformance fixtures include ambiguous and failure cases.
