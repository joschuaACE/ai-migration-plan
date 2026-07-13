# Workspace and Target Containment

This standard separates migration records and installed framework material from the product
being created. The project root owns `.migration/`, `.migration-framework/`, and installed
integration surfaces. `{source_root}` identifies the legacy input. `{target_root}` is the
default ownership and execution boundary for the new target product.

## Default Target Boundary

Unless an accepted project decision defines another topology, every persistent target-owned
path must resolve beneath `{target_root}`. This includes implementation and test sources,
build definitions and launchers, dependency and integrity metadata, generated sources,
project-local caches, reports, packaged artifacts, and other build output.

Do not turn the project root into a target build root merely because `{target_root}` is a
child directory. From the project root, invoke every configured target command in this form:

```bash
cd {target_root} && <configured-target-command>
```

The command, its launcher, and its project-local outputs must remain inside the resolved
target boundary. Relative traversal, absolute output paths, and symlinks must not bypass it.

## Explicit Orchestration Exceptions

An existing repository may intentionally orchestrate several products from a shared build
root. Reusing that topology requires an accepted decision before planning or writing files.
The decision records the alternate working directory, every project-root path to be changed,
ownership, affected commands and outputs, compatibility impact, and rollback procedure.
Update the canonical commands and plans to match the decision; never infer an exception from
an existing directory or silently create a new repository-root orchestrator.

## Planning and Evidence

Before execution, resolve and report every planned target path and anticipated persistent
tool output relative to the project root. Stop on an unapproved path outside `{target_root}`
or on unrelated user work at a planned destination.

Verification runs the exact recorded command from the exact recorded working directory. A
successful equivalent command from another directory is not evidence for the configured
command. Evidence records the working directory, command, exit status, and target-contained
artifacts or reports needed to reproduce the result.

## Rule Provenance

Shared metadata: `source` is the framework v3 workspace-ownership policy; `owner` is the
generic framework profile. These rules apply to every migration.

| Rule ID | Rationale | Enforcement | Required evidence | Reviewed for |
|---|---|---|---|---|
| `GEN-WORKSPACE-001` | A declared target boundary is ineffective when build or product files spill into the project root. | Plan and execution path preflight | Resolved target path inventory | Framework schema v2 |
| `GEN-WORKSPACE-002` | A command proven from a different directory may exercise a different build. | Verification gate | Exact working directory, command, exit status, and artifacts | Framework schema v2 |
| `GEN-WORKSPACE-003` | Shared orchestration changes repository-wide ownership and rollback scope. | Decision validation | Accepted topology decision and affected-path list | Framework schema v2 |

The canonical metadata format and change policy are defined in
`docs/provenance/rule-metadata.md`.
