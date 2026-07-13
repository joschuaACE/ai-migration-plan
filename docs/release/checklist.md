# Framework release checklist

## Contract review

- [ ] Classify the release as major, minor, or patch using `semantic-versioning.md`.
- [ ] Update `framework_version` and every affected schema, profile, adapter, or bundle version.
- [ ] Document upgrade diagnostics for every intentional incompatibility.
- [ ] Review rule provenance and version-sensitive source links.
- [ ] Confirm generic guidance contains no source, target, framework, or output-profile rules.

## Automated evidence

- [ ] Run `python3 agents/framework.py check` from a clean checkout.
- [ ] Compile every pair/output composition twice and confirm byte-identical bundles.
- [ ] Exercise Kiro, Claude, and Codex fresh install, dry-run, managed upgrade, local-change conflict, and forced replacement.
- [ ] Confirm required unsupported hook semantics fail and advisory semantics become explicit instructions.
- [ ] Validate all fixture descriptors and the multi-module golden lifecycle state.
- [ ] Inspect the CI result for schema, shell, Python, template, hook, installer, fixture, and documentation checks.

## Production-pilot gate

- [ ] Zero critical validator findings remain.
- [ ] All source/test/build/output fixture categories are represented.
- [ ] The realistic scenario covers blocked resume, failure recovery, intentional divergence, incremental cutover, rollback, and decommission planning.
- [ ] A human reviewer has recorded the remaining LLM-dependent fidelity and design judgments.
- [ ] The release artifact contains its manifest, source checksums, generated-file checksums, adapter capabilities, and profile identifiers.
