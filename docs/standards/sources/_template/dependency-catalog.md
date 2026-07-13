# [LANGUAGE_NAME] Dependency Detection Catalog

Catalog source dependencies and the capabilities they provide. Target replacements belong
to a language-pair profile because a valid choice depends on both target and output profile.

## Entry Format

| Field | Content |
|---|---|
| Dependency | Canonical project/package/module name and common aliases |
| Detection | Manifest/build/import/link/runtime signals |
| Capability | Actual behavior supplied to the source product |
| Version evidence | Lockfile, manifest, binary metadata, generator, or unknown |
| Platforms/native assets | Supported systems, architectures, ABI and packaged binaries |
| Observable contracts | Protocols, files, schemas, ordering, errors, security, performance |
| Ownership | Maintenance, license, security, update source |

## Standard Capabilities

Record source standard-library/runtime capabilities that may appear as dependencies or
implicit runtime requirements:

| Source feature | Detection signals | Observable concerns |
|---|---|---|
| Collections/data structures | <!-- imports/types --> | Ordering, equality, mutation, concurrency |
| File/stream I/O | <!-- imports/calls --> | Encoding, paths, permissions, buffering, errors |
| Networking | <!-- imports/calls --> | Protocol, TLS, timeout, cancellation, streaming |
| Concurrency | <!-- imports/calls --> | Scheduling, memory model, cancellation, shutdown |
| Serialization | <!-- imports/calls --> | Schema, compatibility, deterministic bytes |

## Third-Party Categories

Create entries for the ecosystem's relevant categories, such as networking/RPC,
serialization/schema, databases, logging/telemetry, tests/benchmarks, security/crypto,
compression/archive, math/media/native compute, CLI/GUI, IPC, and configuration.

| Dependency | Detection | Capability | Version/platform/native evidence | Observable contracts |
|---|---|---|---|---|
| <!-- name --> | <!-- signals --> | <!-- used behavior --> | <!-- evidence --> | <!-- contracts --> |

## Missing or Ambiguous Evidence

Record vendored/forked code, undeclared transitive use, system libraries, dynamic loading,
plugins, generated clients, and runtime downloads. Conflicting names or manifests remain
ambiguous findings until build/release evidence resolves them.

## Checklist

- [ ] Entries describe used capabilities rather than popularity.
- [ ] Version/license/native/platform evidence is recorded.
- [ ] Protocol and persisted-format contracts are identified.
- [ ] Dynamic, vendored, generated, and system dependencies are covered.
- [ ] No target dependency or architecture is selected here.
