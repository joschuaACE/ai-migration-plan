# Creating a Language-Pair Profile

A pair profile contains knowledge that exists only at the intersection of one registered
source and target: semantic mappings, dependency substitutions, interoperability hazards,
test-porting guidance, and equivalence policy. It must not duplicate source detection,
target toolchain rules, output architecture, workflow logic, or adapter packaging.

## Identifier and Paths

Use the canonical identifier `<source-id>-to-<target-id>`, including version separators in
the registered IDs. For example, the reference pair is `cpp-to-java-25`.

Create:

```text
docs/profiles/pairs/<pair-id>/profile.json
docs/pairs/<pair-id>/
```

Document paths in the manifest are repository-relative, normalized paths under
`docs/pairs/<pair-id>/`. Traversal, absolute paths, symlink escapes, and duplicate documents
are invalid.

## Pair Manifest

Conform to `schemas/profile.schema.json` with:

- `schema_version`, `profile_version`, `kind: "pair"`, stable `id`, and display name;
- registered `source` and `target` IDs;
- source/target capability requirements;
- capabilities the pair supplies;
- the complete ordered document list;
- pair-only variables, if any;
- equivalence policy for uncertain, implementation-dependent, and intentional changes; and
- provenance with reviewed framework/toolchain versions and evidence sources.

Use `docs/profiles/pairs/cpp-to-java-25/profile.json` as the structural reference. Do not add
pair aliases or compatibility shims unless the framework compatibility policy requires them.

## Required Knowledge

The exact filenames are declared by the manifest. A production pair normally covers:

- semantic mapping patterns with preconditions and observable differences;
- dependency candidates with selection criteria rather than automatic replacements;
- test-framework semantics and characterization strategy;
- numeric, ownership/lifetime, error, concurrency, encoding, serialization, ABI/native, and
  platform interoperability hazards;
- worked examples for each supported output profile, clearly marked illustrative; and
- rule provenance and version-sensitive primary sources.

Keep source examples and target examples small enough to review, but include error and edge
paths. Do not present framework placement as a property of a language construct.

## Capability Requirements

Require every source/target capability the pair depends on. Compilation must fail when a
selected profile does not provide a required capability. Do not make the core compiler know
the new pair: a structurally valid pair must compose through manifests alone.

If the pair supports only a subset of output profiles, declare that limitation and make
unsupported composition fail with an actionable diagnostic.

## Validation

Run the repository validation command, then compile the pair with every supported output
profile and adapter. Verify:

- manifests and provenance conform to schemas;
- every declared document exists, is compiled, and has a unique safe path;
- every template reference is known and every required variable is supplied;
- no unresolved template delimiter reaches output;
- generated bundles are byte-identical across repeated compilation;
- capability failures identify the missing profile/capability; and
- adding the pair required no generic workflow or compiler source change.

## Review Checklist

- [ ] Canonical pair ID matches registered source and target IDs.
- [ ] Pair manifest validates and declares all documents/capabilities.
- [ ] Knowledge is genuinely pair-specific.
- [ ] Mappings include semantic preconditions and failure/edge behavior.
- [ ] Native, numeric, ownership, concurrency, encoding, and protocol gaps have policies.
- [ ] Output-profile examples do not leak into universal pair rules.
- [ ] Version-sensitive claims cite primary sources and reviewed versions.
- [ ] All supported compositions compile deterministically.
- [ ] No core workflow/compiler change was required.
