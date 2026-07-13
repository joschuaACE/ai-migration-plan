# Framework semantic versioning

The framework uses semantic versioning for the contract that profile authors,
adapter authors, generated bundles, installers, and migration-state tooling consume.

## Major version

Increment the major version for an incompatible change to any of these surfaces:

- a JSON Schema or required state-artifact field;
- profile composition, precedence, required capabilities, or variable types;
- compiled bundle layout or checksum semantics;
- ownership metadata, safe-upgrade behavior, or adapter packaging;
- portable hook meaning or the interpretation of required enforcement;
- lifecycle states or allowed transitions.

A major release must include an actionable upgrade diagnostic. Generated files are
never rewritten merely because a new major version exists; ownership and local-change
checks still apply.

## Minor version

Increment the minor version for backward-compatible additions such as a new profile,
optional capability, optional artifact field, validator, fixture, rule, or adapter
surface. Existing valid profile compositions and managed installations must remain valid.

## Patch version

Increment the patch version for corrections that do not alter the public contract:
clarified guidance, provenance refreshes, deterministic-output fixes, security hardening
that rejects inputs already outside the documented contract, and test improvements.

## Versioned surfaces

`framework_version` versions the release. Each schema and generated artifact also has
`schema_version`; profiles have `profile_version`; adapters have `adapter_version`; and
compiled bundles have `bundle_format_version`. Change the narrowest applicable version,
then apply the framework semantic-version rule above to the aggregate release.
