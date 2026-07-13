# Architecture Decision Rules

This document contains only principles that hold for every source language, target
language, delivery form, and framework. Concrete directory layouts, layering models,
dependency-injection rules, and framework conventions belong to the selected output
and target profiles.

## Select Architecture from Evidence

Do not infer an architecture from the target ecosystem's popular defaults. Select it
from the artifact's consumers, deployability, extension model, change boundaries, and
operational constraints.

Before mapping code, record:

- the externally observable interfaces and their consumers;
- independently deployable or releasable units;
- stable business capabilities and volatile infrastructure concerns;
- state ownership, side effects, failure boundaries, and trust boundaries;
- compatibility promises that constrain the public surface; and
- the selected output profile plus any justified deviations from it.

The output profile supplies the default architecture. Project decisions may refine that
default, but every deviation requires a decision record and evidence.

## Preserve Semantics, Not Accidental Structure

Source directories, files, inheritance trees, and build targets are evidence, not a
mandatory target layout. Preserve boundaries that carry observable behavior or a real
compatibility promise. Replace structures that exist only because of source-language,
build-system, or deployment limitations when the decision and its consequences are
recorded.

A structural change is acceptable only when all affected source behaviors remain linked
to target behaviors and verification evidence, or an intentional-divergence record
explicitly approves the change.

## Boundary Rules

1. Keep policy separate from mechanisms that perform external I/O or depend on a runtime.
2. Make every externally observable contract explicit: inputs, outputs, errors, ordering,
   side effects, timing assumptions, concurrency guarantees, and compatibility promises.
3. Direct dependencies according to the architecture selected by the output profile.
   Do not introduce a universal layer or interface merely for symmetry.
4. Introduce an interface at a real substitution, ownership, release, or test boundary.
   An interface with one implementation and no boundary rationale is not automatically useful.
5. Keep composition visible. Runtime wiring must be auditable without relying on hidden
   global state or undocumented discovery.
6. Prevent cycles across independently releasable units. When a legacy cycle cannot be
   removed in the current slice, record it as an exception with an owner and exit criterion.
7. Keep target-specific framework and serialization types out of stable consumer contracts
   unless those types are intentionally part of the compatibility promise.

## Slice Architecture

Plan around dependency seams and independently verifiable behavior, not around a fixed
sequence of technical layers. A useful migration slice:

- has a stable entry seam and observable outcome;
- can coexist with the legacy path;
- contains all code needed for one behavior, including error and side-effect paths;
- has characterization evidence before implementation;
- can be enabled, disabled, and rolled back independently where the runtime permits; and
- leaves the repository buildable and the migration state internally consistent.

Some slices are vertical user flows; others are protocol boundaries, library API clusters,
or shared data contracts. The plan must state why the selected seam is independently safe.

## Architecture Evidence

Architecture claims require reproducible evidence appropriate to the selected profiles.
Possible evidence includes dependency-graph checks, module-boundary checks, public-API
diffs, contract tests, packaging inspection, and a successful build. A diagram or prose
assertion alone is not enforcement.

Quality thresholds come from the composed profiles and project decisions. Do not apply
blanket file-size limits, one-test-per-method rules, or universal coverage percentages.
Behavioral contract coverage and changed-code risk are more useful than uniform quotas.

## Rule Provenance

Shared metadata: `source` is the framework v3 architecture/evidence policy;
`owner` is the generic framework profile. Row applicability is explicit below.

| Rule ID | Rationale | Applies when | Enforcement | Required evidence | Reviewed for |
|---|---|---|---|---|---|
| `GEN-ARCH-001` | Popular target conventions are not evidence about the artifact being migrated. | Every migration | Configuration and decision validation | Output-profile selection and decision references | Framework schema v2 |
| `GEN-ARCH-002` | Observable behavior can survive structural modernization only when mappings remain traceable. | Any structural change | Traceability validation and review | Source behavior, target unit, decision, and verification links | Framework schema v2 |
| `GEN-ARCH-003` | Smaller reversible slices reduce blast radius and permit coexistence. | Incremental strategy | Plan validation | Seam, enablement, rollback, and acceptance criteria | Framework schema v2 |
| `GEN-ARCH-004` | Architecture is credible only when a deterministic check can test the claimed boundary. | Any enforced architecture rule | Profile-declared validator | Validator output in the evidence index | Framework schema v2 |

The canonical metadata format and change policy are defined in
`docs/provenance/rule-metadata.md`.
