# CLI Profile (output_type = "cli")

A command-line tool with argument parsing, console I/O, and exit codes.
Use when the C++ source is a command-line application (not a daemon/server).

**Key difference from service:** No HTTP endpoints, no Spring Boot web stack.
Input comes from arguments/stdin. Output goes to stdout/stderr. Success/failure
communicated via exit codes.

---

## CLI Design Principles

These principles guide EVERY decision when building a CLI tool. They are distilled
from the Command Line Interface Guidelines (clig.dev), Unix philosophy, and modern
CLI UX research.

### Philosophy

1. **Human-first design** — CLI programs are used by humans. Design for humans first,
   machines second. Output should be readable, errors should be helpful, and the tool
   should feel like it's on the user's side.

2. **Simple parts that work together** — Do one thing well. stdout output should be
   machine-parseable (or offer `--json`). Other tools should be able to pipe your output
   without scraping human-readable text.

3. **Fast startup, fast failure** — CLI tools must respond instantly. If arguments are wrong,
   fail in <100ms with a clear message. Never make the user wait for validation.

4. **Exit codes are a contract** — 0 = success. Non-zero = failure. Different non-zero values
   communicate different failure types. Document them. Never return 0 on failure.

5. **Help text is documentation** — `--help` is the first thing users try. It should be
   complete, show examples, and describe the most common usage. Lead with examples.

6. **Predictable behavior** — Same inputs always produce same outputs. No hidden state
   between runs. No "it works on my machine" from environment leakage.

7. **Progressive verbosity** — Default: quiet (just results). `-v`: progress info.
   `--debug`: diagnostic detail. Never dump debug output by default.

8. **Respect the terminal** — Detect if stdout is a TTY. Colors and progress bars for
   interactive use. Plain text for piped output. Respect `NO_COLOR` and `TERM=dumb`.

### Operational Principles

9. **Conversation as the norm** — Running a CLI is a conversation. Suggest next steps
   after errors. Suggest corrections for typos. Guide the user toward success.

10. **Robustness** — Make it crash-only: no cleanup needed, idempotent where possible.
    Make it recoverable: `<up>` + `<enter>` should pick up where it left off.

11. **Confirm destructive actions** — Anything irreversible should require confirmation
    interactively, or `--force`/`--yes` in scripts. Never silently destroy data.

12. **Configuration cascades** — Flags override environment variables, which override
    project config (`.env`), which override user config, which override system defaults.

---

## CLI Architecture

CLIs use a clean layered architecture. The entry point (commands) delegates to
business logic, which delegates to I/O through interfaces.

```
src/main/java/com/{group}/{artifact}/
├── command/                     # ENTRY POINT: picocli @Command classes
│   ├── App.java                 # Main class — launches picocli
│   ├── RootCommand.java         # Root command, routes to subcommands
│   ├── ProcessCommand.java      # Subcommand implementations
│   └── mixin/                   # Shared option mixins (OutputOptions, etc.)
├── core/                        # BUSINESS LOGIC: pure computation
│   ├── ProcessingEngine.java    # Core algorithms, no I/O
│   ├── Validator.java           # Input validation
│   └── model/                   # Domain types (records, sealed interfaces)
├── io/                          # I/O BOUNDARY: file, network, system
│   ├── FileReader.java          # File system operations
│   ├── FileWriter.java          # Output writers
│   └── HttpClient.java          # Network operations (if needed)
└── output/                      # OUTPUT FORMATTING
    ├── TableFormatter.java      # Human-readable table output
    ├── JsonFormatter.java       # Machine-readable JSON output
    └── ProgressReporter.java    # Progress indicators (writes to stderr)
```

### Why This Structure

- **`command/`** — Thin layer. Parses arguments, validates input, calls core logic,
  formats output. No business logic here.
- **`core/`** — Pure Java. No I/O, no framework dependencies. Testable with `new`.
  This is where all computation and business rules live.
- **`io/`** — All external interactions isolated here. Mockable for testing.
- **`output/`** — Formatting separated from computation. Supports multiple output
  formats without changing core logic.

---

## CLI Gradle Build

```kotlin
plugins {
    application
    alias(libs.plugins.graalvm.native)
}

java {
    toolchain { languageVersion = JavaLanguageVersion.of(25) }
}

application {
    mainClass = "com.company.tool.command.App"
}

dependencies {
    implementation(libs.picocli)
    annotationProcessor(libs.picocli.codegen)
    implementation(libs.slf4j.api)
    implementation(libs.logback.classic)

    testImplementation(libs.bundles.testing)
}

graalvmNative {
    binaries {
        named("main") {
            mainClass = application.mainClass
            buildArgs.addAll("--no-fallback", "-O2")
        }
    }
}
```

---

## CLI Entry Point Pattern

```java
package com.company.tool.command;

import picocli.CommandLine;

/// Application entry point. Minimal — just launches picocli.
public class App {
    public static void main(String[] args) {
        int exitCode = new CommandLine(new RootCommand())
            .execute(args);
        System.exit(exitCode);
    }
}
```

```java
package com.company.tool.command;

import picocli.CommandLine.Command;
import java.util.concurrent.Callable;

/// Root command — provides help, version, and routes to subcommands.
@Command(name = "mytool",
         mixinStandardHelpOptions = true,
         version = "1.0.0",
         description = "One-line description of what the tool does.",
         subcommands = {
             ProcessCommand.class,
             ValidateCommand.class
         },
         footer = {
             "",
             "Examples:",
             "  mytool process input.csv -o output.json",
             "  mytool validate config.yml",
             "  cat data.csv | mytool process --format json"
         })
class RootCommand implements Callable<Integer> {

    @Override
    public Integer call() {
        CommandLine.usage(this, System.out);
        return 0;
    }
}
```

---

## CLI Command Pattern

```java
package com.company.tool.command;

import com.company.tool.core.ProcessingEngine;
import com.company.tool.core.model.ProcessResult;
import com.company.tool.io.FileReader;
import com.company.tool.output.JsonFormatter;
import com.company.tool.output.TableFormatter;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

import java.nio.file.Path;
import java.util.concurrent.Callable;

@Command(name = "process",
         description = "Process input files into structured output.",
         footer = {
             "",
             "Examples:",
             "  mytool process data.csv",
             "  mytool process data.csv -o result.json --format json",
             "  cat data.csv | mytool process -"
         })
class ProcessCommand implements Callable<Integer> {

    @Parameters(index = "0", description = "Input file (use '-' for stdin)")
    private Path inputFile;

    @Option(names = {"-o", "--output"}, description = "Output file (default: stdout)")
    private Path output;

    @Option(names = {"-f", "--format"}, description = "Output format: table, json, csv",
            defaultValue = "table")
    private String format;

    @Option(names = {"-v", "--verbose"}, description = "Show progress and details")
    private boolean verbose;

    @Option(names = {"-q", "--quiet"}, description = "Suppress all status messages")
    private boolean quiet;

    @Option(names = {"--force"}, description = "Overwrite output without confirmation")
    private boolean force;

    @Override
    public Integer call() {
        try {
            // Validate early, fail fast
            var input = resolveInput(inputFile);

            // Status to stderr (visible in terminal, not in pipes)
            if (verbose) {
                System.err.printf("Processing %s...%n", inputFile);
            }

            // Core logic — no I/O concerns here
            var engine = new ProcessingEngine();
            var result = engine.process(input);

            // Format and output — data goes to stdout
            var formatted = switch (format) {
                case "json" -> JsonFormatter.format(result);
                case "csv" -> CsvFormatter.format(result);
                default -> TableFormatter.format(result);
            };

            if (output != null) {
                writeToFile(output, formatted, force);
            } else {
                System.out.print(formatted);
            }

            // Summary to stderr
            if (!quiet) {
                System.err.printf("Processed %d records%n", result.recordCount());
            }
            return 0;

        } catch (IllegalArgumentException e) {
            // User error — bad input
            System.err.println("Error: " + e.getMessage());
            System.err.println("Run 'mytool process --help' for usage.");
            return 2;

        } catch (Exception e) {
            // Runtime error — something unexpected
            System.err.println("Error: " + e.getMessage());
            if (verbose) {
                e.printStackTrace(System.err);
            }
            return 1;
        }
    }
}
```

---

## Exit Code Contract

| Code | Meaning | When |
|------|---------|------|
| 0 | Success | Operation completed. Output on stdout. |
| 1 | Runtime error | Network failure, file unreadable, processing error. Retrying might help. |
| 2 | Usage error | Bad arguments, missing required input, invalid format. Fix the command. |

**Rules:**
- Never return 0 on failure
- User declining a confirmation prompt → exit 0 (deliberate choice, not error)
- Empty output on success → exit 0 (operation succeeded, nothing to report)
- Unknown subcommand → exit 2 (picocli handles this automatically)

---

## stdout / stderr Contract

| Stream | What goes there | Why |
|--------|----------------|-----|
| **stdout** | Data output. The "result" of the command. | This is what pipes and redirects capture. Must be clean, parseable. |
| **stderr** | Status messages, progress, errors, prompts | Visible to user in terminal, invisible in pipes and redirects. |

**The single most important rule:** If someone runs `mytool process input.csv > output.json`,
the output.json file must contain ONLY the formatted result. No "Processing..." messages,
no progress bars, no warnings mixed in.

---

## Output Formatting

### Default: Human-Readable

When stdout is a TTY (interactive terminal), default to human-readable output.

### Machine-Readable: `--json`

When `--json` is passed, or stdout is NOT a TTY (piped), output structured JSON:

```java
// Smart default: detect context
private String resolveFormat(String explicitFormat) {
    if (explicitFormat != null) return explicitFormat;
    // If piped to another program, default to JSON
    if (System.console() == null) return "json";
    // Interactive terminal: human-readable
    return "table";
}
```

### Color & Formatting

```java
// Respect NO_COLOR standard and terminal capabilities
private boolean useColor() {
    if (System.getenv("NO_COLOR") != null) return false;
    if ("dumb".equals(System.getenv("TERM"))) return false;
    if (System.console() == null) return false;  // not a TTY
    return true;
}
```

---

## Configuration Precedence

From highest to lowest priority:

1. **Flags** — `--timeout 30`
2. **Environment variables** — `MYTOOL_TIMEOUT=30`
3. **Project config** — `.mytool.yml` in current directory
4. **User config** — `~/.config/mytool/config.yml` (XDG Base Directory)
5. **System config** — `/etc/mytool/config.yml`
6. **Hardcoded defaults** — sensible values baked into the code

**Rules:**
- Environment variable names: `MYTOOL_` prefix + UPPER_SNAKE_CASE flag name
- Never require a config file for basic operation — sensible defaults always
- Support `-` as filename to mean stdin/stdout
- Never read secrets from flags (visible in `ps`) — use `--password-file` or stdin

---

## GraalVM Native Image

CLIs must start fast. GraalVM native image gives <50ms startup.

**Rules for native-image compatibility:**
- Minimize reflection (picocli codegen handles its own reflection config)
- No dynamic class loading at runtime
- Register any reflection usage in `reflect-config.json`
- Test the native binary in CI, not just the JVM version
- Use `--no-fallback` to ensure pure native (no bundled JVM)

---

## CLI-Specific Rules

1. **Exit codes are the API** — 0/1/2 as documented above
2. **stdout for data, stderr for humans** — never mix them
3. **No Spring Boot** — no controllers, no application.yml, no web starters
4. **GraalVM native-image friendly** — minimize reflection, fast startup
5. **Prefer flags to args** — except for the primary positional input
6. **Have full-length versions of all flags** — `-v` AND `--verbose`
7. **Support `--help` and `--version` everywhere** — including subcommands
8. **Lead help text with examples** — users learn by pattern matching
9. **Show progress for long operations** — spinners to stderr, not stdout
10. **Support stdin piping** — when no file argument given and stdin is not a TTY
11. **Respect `NO_COLOR`** — disable color when environment says so
12. **Confirm destructive actions** — prompt interactively, `--force` for scripts

---

## CLI Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Root command | `RootCommand` | `RootCommand` |
| Subcommand | `VerbNounCommand` | `ProcessDataCommand` |
| Shared options mixin | `NounMixin` | `OutputMixin` |
| Output formatter | `NounFormatter` | `TableFormatter` |
| Core engine | `NounEngine` or `NounProcessor` | `ProcessingEngine` |
| I/O adapter | `NounReader` / `NounWriter` | `FileReader` |

---

## CLI Testing

### Test Categories

| Category | What it verifies | How |
|----------|-----------------|-----|
| **Core unit tests** | Business logic correctness | JUnit 5 + AssertJ, test `core/` with `new` |
| **Command tests** | Exit codes + stdout/stderr content | Instantiate command, call `call()`, capture output |
| **Integration tests** | Full CLI as subprocess | Run binary, verify stdout + exit code |
| **Piping tests** | stdin/stdout composition works | Feed input via stdin, verify output |
| **Error tests** | Bad input produces correct exit code + helpful message | Pass invalid args, assert exit 2 |

### Command Test Pattern

```java
@Test
void should_return_0_and_output_json_on_success() {
    var cmd = new CommandLine(new ProcessCommand());
    var sw = new StringWriter();
    cmd.setOut(new PrintWriter(sw));

    int exitCode = cmd.execute("input.csv", "--format", "json");

    assertThat(exitCode).isZero();
    assertThat(sw.toString()).contains("\"recordCount\":");
}

@Test
void should_return_2_when_input_file_missing() {
    var cmd = new CommandLine(new ProcessCommand());
    var err = new StringWriter();
    cmd.setErr(new PrintWriter(err));

    int exitCode = cmd.execute();

    assertThat(exitCode).isEqualTo(2);
    assertThat(err.toString()).contains("Missing required parameter");
}
```

### Testing Rules

- **No @SpringBootTest** — CLIs have no Spring context
- **Test exit codes explicitly** — they are your API contract
- **Test stderr separately from stdout** — they serve different purposes
- **Test with both TTY and pipe modes** — output format may differ
- **Test native image in CI** — verify it starts and produces correct output

---

## CLI Anti-Patterns

### Architecture Violations
- `@RestController` anywhere → **WRONG TYPE** (CLIs don't serve HTTP)
- `application.yml` with server config → **WRONG TYPE** (no server)
- `spring-boot-starter-web` in dependencies → **WRONG TYPE**
- Business logic inside `@Command` method → extract to `core/`

### Output Violations
- Status/progress messages on stdout → **breaks pipes** (use stderr)
- Exit code 0 on failure → **violates contract**
- ANSI color codes when stdout is not a TTY → **breaks piped output**
- Debug output by default → **noisy** (verbose mode only)
- Long output without a pager → **unfriendly** (pipe to `less` when TTY)

### UX Violations
- Hanging with no output on long operations → **feels broken** (show progress)
- Cryptic error without guidance → **hostile** (tell user how to fix)
- Hard-coding file paths → **fragile** (accept as arguments/options)
- Requiring config file for basic operation → **friction** (sensible defaults)
- Destroying data without confirmation → **dangerous** (confirm or `--force`)
- Silent success when state changes → **confusing** (tell user what happened)
- Different behavior on different runs with same input → **unpredictable**
