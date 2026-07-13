# Migration Workflow Responsibilities

These responsibilities describe what the migration workflows must accomplish. An agent
adapter may assign them to one worker, several isolated workers, or a human-assisted
process. The knowledge layer does not assume a particular model, command syntax, degree
of parallelism, or ability to enforce hooks.

## Discovery

Inventory the complete source product rather than only files with familiar extensions.
Include build variants, generated inputs, public interfaces, tests, assets, schemas,
runtime entry points, deployment files, and external dependencies.

Required properties:

- source files are read-only;
- every inventory item has a stable identifier and provenance;
- exclusions include a reason and evidence;
- conflicting build metadata is reported, not resolved by guesswork; and
- platform and configuration variants remain distinct until their behavior is compared.

## Characterization

Turn observations into behavioral contracts before target implementation begins. Use
source tests, golden masters, differential harnesses, protocol examples, public API
inventories, and recorded side effects as appropriate.

Characterization must distinguish:

- observed behavior from specified behavior;
- absent evidence from a passing result;
- deterministic output from environment-sensitive output; and
- behavior to preserve from approved behavior to normalize or remove.

## Analysis

Analyze ownership, data flow, control flow, errors, concurrency, external effects,
compatibility promises, build variants, and source-language hazards. Findings cite source
locations or generated-input provenance and carry severity, confidence, and an owner.

When analysis is parallelized, partition by a declared scope and merge through stable
identifiers. Workers must not append concurrently to the same artifact.

## Mapping and Planning

Map source behaviors and units to target contracts, modules, and delivery artifacts.
Plan independently verifiable slices around seams, not merely files or packages.

Each slice declares:

- dependencies and entry seam;
- source behaviors and target units;
- coexistence and routing approach;
- implementation, characterization, and verification work;
- acceptance gates and human approvals;
- rollback trigger and procedure; and
- exceptions, blockers, and decommission prerequisites.

## Execution

Implement only an approved slice. Read all source and decision references in that slice
before writing target artifacts. Preserve uncertain findings explicitly rather than
inventing behavior.

Execution records actual files changed, commands run, results, new dependencies,
assumptions, and deviations from the plan. It may not mark its own work verified or
approved.

## Deterministic Verification

Verification produces reproducible evidence. It runs the selected profile's build, tests,
contract comparisons, static checks, dependency checks, architecture checks, and artifact
inspection. Each evidence record includes the exact command or validator, environment,
input checksum, output location, result, and timestamp.

Verification does not decide whether a semantic difference is desirable or whether a
modernization is idiomatic. A non-deterministic or unavailable check is recorded as a gap,
not silently treated as passing.

## Judgment Review

Review evaluates questions that deterministic tools cannot settle:

- Does the implementation faithfully express the characterized behavior?
- Are intentional changes justified and approved?
- Is the target design idiomatic for its selected profiles without unnecessary complexity?
- Are unknowns, weak evidence, and operational risk represented honestly?
- Is the slice safe to approve, cut over, defer, or send back?

Review references verification evidence but does not rewrite it. Review produces a
verdict, findings with stable identifiers, required actions, and approval identities.

## Recovery and Resume

On interruption, preserve the last valid state and staged evidence. Resumption validates
state and cross-references, identifies incomplete operations, and continues from the last
successful transition. It must not infer success from files merely being present.

## Adapter Capability Boundary

An adapter declares which operations it can package and which hooks it can actually
enforce. If it cannot enforce a required event or validator, compilation or installation
must follow the configured strictness policy: fail, or emit a visible warning and install
the requirement as instructions. The framework must never describe advisory text as an
equivalent enforcing hook.

## Rule Provenance

Shared metadata: `source` is the framework v3 workflow and adapter-capability contract;
`owner` is the generic framework profile. Row applicability is explicit below.

| Rule ID | Rationale | Applies when | Enforcement | Required evidence | Reviewed for |
|---|---|---|---|---|---|
| `GEN-WRK-001` | Adapter mechanics must not leak into portable migration knowledge. | Every adapter | Document and capability validation | Adapter capability declaration | Framework schema v2 |
| `GEN-WRK-002` | Concurrent writes create nondeterministic and corrupt state. | Parallel work | Artifact ownership validation | Declared scope and deterministic merge result | Framework schema v2 |
| `GEN-WRK-003` | An executor cannot independently substantiate its own completion claim. | Every executed slice | State-machine validation | Separate execution, verification, and review records | Framework schema v2 |
| `GEN-WRK-004` | Unsupported hooks are weaker controls, even if their prose is identical. | Adapter lacks an event or enforcement primitive | Capability/strictness validation | Failure or explicit installation warning | Framework schema v2 |
