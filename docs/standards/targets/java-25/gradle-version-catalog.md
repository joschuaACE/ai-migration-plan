# Gradle Dependency Management for Java 25

This framework does not freeze ecosystem point releases in prose. Each project selects
supported coordinates through reviewed dependency decisions and records the owner, source,
compatibility evidence, and update policy. Generated builds centralize those selected
coordinates and validate the resolved graph.

Primary references:

- [Gradle version catalogs](https://docs.gradle.org/current/userguide/version_catalogs.html)
- [Platforms and dependency constraints](https://docs.gradle.org/current/userguide/platforms.html)
- [Dependency locking](https://docs.gradle.org/current/userguide/dependency_locking.html)
- [Dependency verification](https://docs.gradle.org/current/userguide/dependency_verification.html)

## Four Distinct Controls

| Control | What it does | What it does not do |
|---|---|---|
| Version catalog | Centralizes aliases, requested coordinates, and plugin declarations; creates type-safe accessors | Does not enforce the version selected during conflict resolution |
| Platform / constraints | Recommends or strictly constrains versions in the resolved dependency graph | Does not pin every future resolution by itself |
| Dependency locking | Records resolved versions for lock-enabled configurations | Does not prove artifact integrity or publisher identity |
| Dependency verification | Checks artifact/metadata checksums and, where configured, signatures | Does not find vulnerabilities, license problems, or semantic incompatibility |

A production build commonly needs all four. Bundles in a version catalog group declarations;
they do not make upgrades atomic and do not align transitive versions.

## Version Catalog Contract

Use `gradle/libs.versions.toml` (or an explicitly registered catalog) as the central name
and coordinate registry. The chosen point versions come from project decisions, not this
document.

Illustrative shape:

```toml
[versions]
framework = "<reviewed-framework-version>"
mapping = "<reviewed-mapping-version>"
testing = "<reviewed-testing-version>"

[libraries]
framework-platform = { module = "example.framework:framework-bom", version.ref = "framework" }
framework-core = { module = "example.framework:framework-core" }
mapping-api = { module = "example.mapping:mapping-api", version.ref = "mapping" }
mapping-processor = { module = "example.mapping:mapping-processor", version.ref = "mapping" }
testing-runner = { module = "example.testing:testing-runner", version.ref = "testing" }

[bundles]
testing = ["testing-runner"]

[plugins]
quality = { id = "example.quality", version = "<reviewed-plugin-version>" }
```

Rules:

- no dynamic versions (`+`, `latest.*`), open ranges, or unreviewed snapshots;
- one alias names one semantic role; avoid aliases that obscure the actual dependency;
- processors/code generators use versions proven compatible with their runtime/API library;
- repositories are declared centrally and content-filtered where multiple repositories are required;
- plugin coordinates and repositories receive the same provenance and integrity review as libraries;
- `api` versus `implementation`, optionality, capabilities, classifiers, and exclusions remain at
  the dependency declaration site because a catalog does not model the full dependency semantics; and
- catalog changes reference the dependency decision that approved them.

## Alignment with Platforms and Constraints

Use a platform when a vendor publishes a compatible BOM or when a multi-module build needs a
shared set of constraints:

```kotlin
dependencies {
    implementation(platform(libs.framework.platform))
    implementation(libs.framework.core)
}
```

For repository-owned alignment, define constraints in a `java-platform` project:

```kotlin
plugins {
    `java-platform`
}

dependencies {
    constraints {
        api("example.mapping:mapping-api:<reviewed-mapping-version>")
        api("example.mapping:mapping-processor:<reviewed-mapping-version>")
    }
}
```

Choose deliberately among preferred, strict, rejected, and enforced versions. Use
`enforcedPlatform` only when overriding all consumers is an intentional compatibility
decision. Published libraries and SDKs should avoid leaking an enforced platform that may
override a consumer's graph unexpectedly.

Validate alignment using resolved dependency reports or a machine-readable resolution
validator. Reading `libs.versions.toml` cannot prove which versions the build selected.

## Dependency Locking

Enable locking for the configurations whose reproducibility matters, commonly through:

```kotlin
dependencyLocking {
    lockAllConfigurations()
}
```

Generate/update locks only as part of a reviewed dependency change:

```bash
./gradlew dependencies --write-locks
```

Commit lock state, ensure CI fails on unapproved drift, and inspect the diff. Resolve every
relevant configuration at lock generation time; an unresolved configuration may remain
unlocked. Decide separately whether a published library exposes strict constraints or keeps
locks as build-only reproducibility evidence for its own tests.

## Dependency Integrity Verification

Use strict dependency verification for release and CI builds. Generate a candidate baseline
from a trusted resolution context, then review it before committing:

```bash
./gradlew --write-verification-metadata sha256,pgp help
./gradlew --dependency-verification strict check
```

The generated `gradle/verification-metadata.xml` is not self-authenticating: bootstrapping
trusts the artifacts currently downloaded. Compare critical checksums/signing keys with an
independent trusted source, constrain trusted keys, and review additions/removals.

Prefer SHA-256 or SHA-512 checksums. Use signatures when trustworthy signatures and keys are
available; signatures and secure checksums are complementary. Verification must cover
plugins and metadata as well as libraries. Keep in mind that changing modules such as
snapshots are unsuitable for reproducible verified releases.

Dependency verification checks integrity/provenance, not known vulnerabilities. Run a
separate profile-declared vulnerability, license, and policy analysis.

## Output-Profile Rules

### Service

- Import vendor BOMs/platforms for aligned framework families.
- Lock runtime, test, build-plugin, and migration-tool configurations used in CI/release.
- Inspect the packaged runtime graph and container/runtime image, not only compile classpaths.
- Select observability, resilience, persistence, and security dependencies from actual requirements;
  do not install the full catalog by default.

### Library

- Use `java-library`; expose a dependency with `api` only when its types intentionally occur
  in the public API/SPI contract.
- Keep framework integrations optional and isolated in separate artifacts/modules where practical.
- Validate the published POM/module metadata and consumer resolution, because local locks are
  not automatically a consumer constraint.
- Prefer compatible constraints/platform guidance over forcing consumer versions.

### SDK

- Apply all library rules.
- Test the published artifact against the supported consumer matrix and service/API versions.
- Treat any public dependency-type or constraint change as an API compatibility input.
- Run source/binary API comparison independently of dependency locking.

### CLI

- Lock and verify the complete packaged runtime, including native-image or bundled-runtime inputs.
- Smoke-test the installed distribution from a clean environment.
- Inspect licenses, native libraries, launch scripts, and platform classifiers in the package.

## Wrapper and Repository Reproducibility

- Commit the Gradle wrapper files and pin/verify the wrapper distribution checksum.
- Record the Gradle version supported by Java 25 and every selected plugin.
- Prohibit project-level repository injection when central repository policy is enabled.
- Fail on repository or dependency declarations that bypass the generated ownership manifest.
- Check deterministic generated metadata and packaged artifacts where the toolchain permits it.

## Dependency Change Record

Every addition or update records:

- decision ID, owner, purpose, and output-profile placement;
- selected coordinate/version and authoritative source;
- supported Java/Gradle/framework matrix;
- license, vulnerability, maintenance, and transitive graph review;
- alignment constraint/platform impact;
- lock and integrity-metadata diffs;
- compatibility and packaged-artifact test results; and
- rollback or downgrade constraints.

## Rule Provenance

Shared metadata: `applicability` is Java 25 targets using Gradle; `source` is the linked
official Gradle catalog/platform/locking/verification documentation; `owner` is target
profile `java-25`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `TGT-JAVA25-GRADLE-001` | Catalog versions are requested declarations, not resolution enforcement. | Resolved-graph validator | Dependency resolution report and alignment declaration | Gradle 9.6.1 documentation |
| `TGT-JAVA25-GRADLE-002` | Locking pins resolution but cannot establish artifact integrity. | Build validator | Lock state plus verification metadata/result | Gradle 9.6.1 documentation |
| `TGT-JAVA25-GRADLE-003` | Bootstrapped checksums inherit the trust of the current download source. | Dependency review gate | Independently reviewed checksum/key additions | Gradle 9.6.1 documentation |
| `TGT-JAVA25-GRADLE-004` | Library consumers do not automatically inherit the producer's local locks. | Publication validator | Published metadata and consumer fixture resolution | Gradle 9.6.1 documentation |
