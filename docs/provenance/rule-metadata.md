# Rule Provenance Metadata

Important normative rules must be traceable to a rationale, scope, enforcement mechanism,
and review basis. Provenance makes it possible to tell a universal invariant from a
profile default, distinguish enforced controls from advisory guidance, and review
version-sensitive recommendations without rewriting unrelated knowledge.

## Normative Rule Record

Use the following fields in a manifest record or an adjacent Markdown table:

| Field | Required | Meaning |
|---|---|---|
| `rule_id` | Yes | Stable namespaced identifier, for example `GEN-<AREA>-<NNN>` |
| `statement` | Yes | One testable requirement; avoid combining independent obligations |
| `rationale` | Yes | Risk or invariant protected by the rule |
| `applicability` | Yes | Profiles, lifecycle states, conditions, and explicit exclusions |
| `enforcement` | Yes | Validator, schema constraint, hook, review gate, or `advisory` |
| `evidence` | Yes | Artifact or result that demonstrates compliance |
| `source` | Yes | Maintainer rationale, standard, specification, or authoritative documentation |
| `last_reviewed_version` | Yes | Framework or external version against which the rule was checked |
| `owner` | Yes | Profile or framework area responsible for review |
| `supersedes` | No | Prior rule IDs replaced by this rule |

An adjacent table may declare a field once as shared metadata only when every row has the
same value. State the inherited `applicability`, `source`, and `owner` immediately before the
table; do not rely on directory context or reader inference.

Example:

```yaml
rule_id: JAVA-BUILD-003
statement: Resolved dependency alignment must use constraints or a platform when a family of artifacts must share compatible versions.
rationale: A version catalog centralizes requested coordinates but does not enforce the resolved graph.
applicability: Java target projects that consume an aligned artifact family.
enforcement: dependency-resolution validator
evidence: resolved dependency report and platform/constraint declaration
source: https://docs.gradle.org/current/userguide/version_catalogs.html
last_reviewed_version: Gradle 9.6.1
owner: target/java-25
```

## Identifier Namespaces

| Prefix | Owner |
|---|---|
| `GEN-` | Generic framework principles |
| `SRC-<ID>-` | Source-language profile |
| `TGT-<ID>-` | Target-language profile |
| `PAIR-<ID>-` | Language-pair profile |
| `OUT-<ID>-` | Output profile |
| `ADAPTER-<ID>-` | Agent packaging/capability adapter |

IDs do not encode a document line number or semantic version. A wording clarification
keeps the ID; a material change in obligation creates a new ID and uses `supersedes`.

## Enforcement Vocabulary

- **Schema:** rejects invalid structure or values deterministically.
- **Validator:** inspects composed inputs or generated artifacts deterministically.
- **Hook:** invokes a validator at an adapter-supported event. A hook is enforcing only
  when the adapter can block or fail that event.
- **Review gate:** requires recorded human or LLM judgment; it is not deterministic.
- **Advisory:** instruction only. It must not be reported as enforced.

When enforcement differs by adapter, the rule points to a validator and the adapter
capability declaration states whether it can invoke that validator automatically. The
knowledge document must not claim equivalent enforcement across adapters.

## Source Quality

Prefer primary sources: language specifications, official migration guides, build-tool
documentation, standards, and repository-owned test evidence. Practitioner articles may
explain a pattern but do not override specifications or measured project behavior.

External sources are links, not copied text. Version-sensitive rules record the exact
version reviewed and must be rechecked when the target/toolchain profile advances.

## Review Policy

Review provenance when:

- a schema or profile has a breaking version change;
- a target runtime, compiler, build tool, framework, or adapter capability changes;
- a validator changes what it considers passing;
- fixture evidence contradicts the rationale; or
- the source link is removed, superseded, or no longer authoritative.

A stale review version produces a validation warning or failure according to profile
strictness. It does not silently disable the rule.
