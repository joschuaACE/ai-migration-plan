# CLI Output Profile

Use this profile for a program invoked through a command shell, script, job runner, or
terminal. Commands, streams, exit status, signals, and the installed launcher are public
contracts.

## Command Architecture

Keep parsing and terminal adaptation at the command boundary. Commands translate arguments,
environment, configuration, and standard input into target-neutral operations; business
logic does not write directly to process-global streams or terminate the process.

Use a small core plus explicit I/O capabilities. Introduce full port/adapter layering only
when multiple front ends, replaceable infrastructure, or domain complexity justifies it.
The CLI profile does not force service architecture onto a single-process tool.

## Command Contract

Characterize and document:

- command and subcommand names, aliases, options, positional arguments, and defaults;
- validation order, help/version behavior, and unknown-option diagnostics;
- interactive prompts and a non-interactive equivalent;
- configuration precedence across flags, environment, project/user files, and defaults;
- current-directory, path, locale, time-zone, terminal, and encoding assumptions;
- signal, cancellation, timeout, partial-output, and cleanup behavior; and
- backward compatibility for scripts and automation.

Destructive operations require an explicit confirmation model. Non-interactive use must
fail safely instead of waiting forever for input.

## Stream and Exit-Code Contract

- `stdout` carries successful primary output intended for consumers or pipelines.
- `stderr` carries diagnostics, warnings, progress, and help associated with failure.
- Exit status `0` means the requested operation succeeded. Nonzero statuses are stable,
  documented categories; preserve legacy values when scripts rely on them or provide a
  compatibility decision.
- Machine-readable output has a versioned schema and is not mixed with progress or color.
- Interactive decoration is disabled when inappropriate and never changes semantic content.
- Partial output and broken-pipe behavior are explicit for streaming commands.

## Packaging Contract

Test the installed launcher and distribution, including executable permissions, runtime
discovery, working directory independence, path quoting, spaces, symlinks where supported,
completion files, and clean uninstallation. A repository-local invocation is not packaging
evidence.

If distributing a native executable or bundled runtime, record supported operating systems
and architectures, dynamic-library requirements, signing/notarization, and update behavior.

## Migration and Cutover

Run a golden command matrix against legacy and target binaries, capturing stdout, stderr,
exit status, produced files, and side effects separately. Normalize only approved unstable
fields such as timestamps. Coexist through distinct launcher names or a selectable shim;
rollback restores both invocation and any changed on-disk state.

## Required Gates

- golden command and error-path matrix;
- non-interactive, pipe, redirection, signal, and broken-pipe tests as applicable;
- machine-output schema validation;
- installed-package smoke test on each supported platform; and
- rollback/uninstall evidence for state-changing commands.

## Rule Provenance

Shared metadata: `applicability` is any migration selecting the CLI output profile;
`source` is this portable command/stream/package contract; `owner` is output profile `cli`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `OUT-CLI-001` | Scripts observe streams and exit status independently. | Command harness | Captured stdout, stderr, and exit status | Output profile v2 |
| `OUT-CLI-002` | Repository execution misses launcher and packaging failures. | Packaging validator | Installed-distribution smoke test | Output profile v2 |
| `OUT-CLI-003` | Terminal decoration must not corrupt pipelines or schemas. | Stream/TTY tests | Interactive and non-interactive results | Output profile v2 |
