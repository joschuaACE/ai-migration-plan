# Java 25 CLI Specialization

This document specializes `docs/output-profiles/cli.md` for a Java 25 command-line
distribution. Picocli is the default candidate parser, but parser selection follows the
pair dependency decision and legacy command contract.

## Package Shape

```text
{target_root}/src/main/java/<base-package>/
├── command/       # Parser annotations/adapters, option validation, stream mapping
├── core/          # Target-neutral operations and values
├── io/            # Filesystem, network, process, and clock implementations
├── output/        # Human and machine renderers
└── CliLauncher.java
```

Commands stay thin: parse, validate boundary syntax, invoke one coherent operation, render,
and map errors to exit status. Business logic does not call `System.exit`, read process-global
streams directly, or depend on parser types. Inject `PrintWriter`/streams and I/O capabilities
so tests can capture output without mutating global process state.

Adopt additional ports/use-case interfaces when there are multiple entry points, replaceable
infrastructure, or meaningful domain complexity. A single focused CLI does not need service
package ceremony.

## Launcher and Command Pattern

Keep process termination at the outermost launcher:

```java
public final class CliLauncher {
    private CliLauncher() {}

    public static void main(String[] args) {
        var command = CommandComposition.create(System.in, System.out, System.err);
        int exitCode = new picocli.CommandLine(command).execute(args);
        System.exit(exitCode);
    }
}
```

Subcommands normally implement `Callable<Integer>` (or the selected parser's equivalent)
and return a documented exit status. Tests invoke command objects/parser execution directly;
separate process tests verify the installed launcher and real process exit.

## Arguments, Configuration, and Help

- Preserve command/subcommand names, aliases, short/long flags, positional arity, defaults,
  repeated options, option terminator behavior, and error/help text relied on by scripts.
- Define precedence explicitly, commonly flags over environment over project/user config over
  defaults, but preserve legacy precedence unless a decision changes it.
- Distinguish missing from empty values and redact secret option/environment values.
- Provide non-interactive equivalents for prompts and fail safely when input is unavailable.
- Destructive operations require confirmation or an explicit automation flag; confirmation
  itself must not make scripted execution hang.
- Help and version commands avoid unnecessary network/config initialization.

## stdout, stderr, and Exit Status

- Successful primary results go to stdout.
- Diagnostics, warnings, progress, and failure-associated help go to stderr.
- Status `0` means success. Give nonzero statuses stable symbolic meanings and preserve legacy
  values used by automation or document an approved compatibility mapping.
- Do not log through a backend that writes to stdout and corrupts primary output.
- A machine-readable mode emits only its versioned schema on stdout; progress/color stay on stderr.
- Disable decoration when streams are redirected or the environment requests no color.
- Define partial-output and broken-pipe policy for streaming commands. A closed downstream pipe
  should not produce an unrelated stack trace or silently report the wrong status.

Illustrative exit categories (projects choose and document actual numbers): usage/configuration,
input/not-found, permission/authentication, conflict, transient external failure, and internal
error. Avoid passing arbitrary exception or HTTP status values through as process exit codes.

## Charset, Locale, Paths, and Signals

- Specify charset for stdin/stdout machine formats, files, and subprocess protocols. Console
  encoding may differ from Java's default charset.
- Use an explicit locale for machine output and retain user locale only for intentionally
  localized human text.
- Test spaces, quoting, Unicode, relative/absolute paths, symlinks, case, permissions, and
  working-directory independence on supported platforms.
- Define interruption, signal, shutdown-hook, timeout, temp-file, and partial-write behavior.
- Use atomic replacement and fsync/durability only where the characterized contract requires it.

## Packaging

The selected distribution may be a launcher plus JVM, a bundled runtime image, or a native
executable. Record supported platforms/architectures and startup/size constraints before
selecting native compilation.

For every distributed form, test:

- launcher quoting and runtime discovery from outside the project directory;
- executable permissions, spaces/symlinks, and environment forwarding;
- generated completion/man/help assets if shipped;
- dependency/native-library inclusion, integrity, signing/notarization, and licenses;
- `--help`, `--version`, success, usage error, runtime error, and signal handling; and
- upgrade/uninstall/rollback for on-disk state.

Native-image compatibility requires explicit reflection/resource/proxy metadata and tests of
the actual native binary. It is not a mandatory property of a CLI.

## Gradle Shape

Use the `application` plugin or selected packaging plugin with a Java 25 toolchain. Declare
the parser and optional logging/backend dependencies through the catalog, then apply
alignment, locks, and dependency verification from `gradle-version-catalog.md`. Do not add
the Spring Boot web stack to obtain lifecycle/configuration features for a CLI.

## Verification

- golden matrix capturing stdout, stderr, exit status, files, and side effects separately;
- parser tests for valid/invalid combinations, defaults, help/version, and configuration precedence;
- non-interactive, redirection, pipe/broken-pipe, timeout, cancellation, and signal tests as applicable;
- machine-output schema and backward-compatibility tests;
- filesystem/charset/locale/platform fixtures; and
- installed distribution smoke tests on every supported packaging/platform combination.

Use separate-JVM tests where process exit, environment, signals, launcher quoting, classpath,
or module/native packaging is part of the contract.

## Anti-Patterns

- business logic in parser-annotated command classes;
- calls to `System.exit` below the outer launcher;
- primary output mixed with logs/progress on stdout;
- prompts with no safe non-interactive behavior;
- stack traces for ordinary usage errors or status `0` on failure;
- machine output that changes with terminal color, locale, or log configuration;
- only testing repository-local `java` execution instead of the installed distribution; and
- requiring native image without measured startup/package need and compatibility evidence.

## Rule Provenance

Shared metadata: `applicability` is Java 25 plus CLI output; `source` is the portable CLI
contract and Java 25 target/runtime policy; `owner` is the Java 25 CLI specialization.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `TGT-JAVA25-CLI-001` | Only the launcher should terminate the JVM; inner termination prevents composability and tests. | Architecture validator | Call/dependency report and command tests | JDK 25 / CLI profile v2 |
| `TGT-JAVA25-CLI-002` | Process-global defaults differ across terminals and platforms. | CLI contract tests | Explicit charset/locale/path matrix | JDK 25 / CLI profile v2 |
| `TGT-JAVA25-CLI-003` | Native and launcher packaging failures do not appear in in-process tests. | Distribution validator | Installed-package process results | JDK 25 / CLI profile v2 |
