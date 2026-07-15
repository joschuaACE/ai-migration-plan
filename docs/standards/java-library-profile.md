# Library Profile (output_type = "library")

A plain JAR with no main class, no Spring Boot plugin. Use when the C++ source is
a DLL, static library (.a/.lib), or shared library (.so/.dylib).

**Key difference from service:** There are NO controllers, NO application.yml, NO Spring
Boot starters in runtime. The public API IS the exported interfaces. Consumers call your
library directly via Java method invocations, not HTTP.

---

## Library Design Principles

These principles guide EVERY decision when building a library. They are distilled from
Joshua Bloch's API design principles, the Java Module System philosophy, and modern
Java language features (sealed types, records, pattern matching).

### The Golden Rules

1. **When in doubt, leave it out** — Every public type is a permanent commitment.
   You can always add later; you can never take away. Minimize conceptual weight over
   class-count.

2. **Easy to use, hard to misuse** — It should be easy to do simple things, possible
   to do complex things, and impossible (or at least difficult) to do wrong things.
   Compile-time safety beats runtime errors.

3. **Self-documenting APIs** — It should rarely require documentation to read code written
   against a good API. Names, types, and structure should make intent obvious.

4. **Don't make the client do anything the library could do** — Reduce boilerplate.
   Sensible defaults. One-liner for the common case, configuration for the advanced case.

5. **Minimize accessibility** — When in doubt, make it package-private. If not
   package-private, make it internal (unexported module package). Only expose what
   consumers genuinely need.

### Structural Principles

6. **Immutability by default** — All public types should be records or immutable classes.
   Mutable state creates thread-safety contracts that are hard to document and easy to
   break. Immutable objects are simple, thread-safe, and freely sharable.

7. **Interfaces over classes** — The public API surface should be interfaces. This
   decouples consumers from providers, allows multiple implementations, and enables
   testing with fakes/mocks without framework magic.

8. **Fail-fast on bad input** — Validate at API boundary immediately. Throw clear
   exceptions with messages that tell the caller exactly what's wrong and how to fix it.
   The sooner you report a bug, the less damage it will do.

9. **Zero surprise dependencies** — Consumers should never be forced to pull in libraries
   they didn't ask for. Use `api()` sparingly, `implementation()` aggressively. A good
   library is a lightweight library.

10. **No framework lock-in** — The public API uses ONLY JDK types. No Spring, no Jakarta,
    no framework annotations on anything a consumer imports. Framework support lives in
    an optional auto-configuration package.

11. **Thread-safety documented** — Every public class states its thread-safety guarantee:
    thread-safe, not-thread-safe, or conditionally-thread-safe. No guessing.

12. **Testable in isolation** — Consumers must be able to instantiate and test your library
    with `new`, a factory method, or a builder. No container required. No classpath magic.

---

## Architecture: API / Internal / SPI

A library has ONE architecture. It is simple, layered, and enforced by `module-info.java`:

```
src/main/java/com/{group}/{artifact}/
├── api/                         # PUBLIC — the consumer-facing contract
│   ├── DataProcessorApi.java    # Main entry point (interface + factory methods)
│   ├── ProcessResult.java       # Return types (records)
│   ├── ProcessConfig.java       # Configuration (record or builder)
│   └── ProcessException.java    # Exception hierarchy (unchecked)
├── internal/                    # PRIVATE — all implementation lives here
│   ├── DefaultProcessor.java    # Implements api/ interfaces
│   ├── Parser.java              # Internal helpers
│   └── Validator.java           # Internal validation
└── spi/                         # OPTIONAL — extension points for consumers
    └── OutputFormatter.java     # Interface consumers can implement
```

### The Three Layers

| Layer | Visibility | Purpose | Who writes implementations? |
|-------|-----------|---------|---------------------------|
| `api/` | Exported (public) | Consumer-facing contract: interfaces, records, exceptions, factory methods | The library (default impls live in `internal/`) |
| `internal/` | Not exported (encapsulated) | All implementation detail. Free to change between releases | The library only |
| `spi/` | Exported (public) | Extension points — interfaces consumers MAY implement | The consumer |

### Why This Works

- **Clear boundary** — `module-info.java` enforces which packages are visible. No
  discipline required; the compiler rejects illegal access.
- **Safe evolution** — Everything in `internal/` can change freely. The public surface
  (`api/` + `spi/`) is your only compatibility commitment.
- **Consumer vs Provider types** — Types in `api/` are "provider types" (library implements
  them; adding methods is safe). Types in `spi/` are "consumer types" (consumers implement
  them; adding methods requires a default to avoid breaking).

### When to Add `spi/`

Add `spi/` ONLY when the library has genuine extension points — when consumers must
provide implementations for storage, transport, formatting, or other pluggable behavior.

**Indicators you need `spi/`:**
- C++ source had virtual base classes / callback interfaces / plugin mechanisms
- The library talks to external systems that consumers control (file system, network, DB)
- Multiple deployment environments need different backend implementations

**If the library is self-contained** (computation, parsing, transformation, encoding) —
skip `spi/` entirely. Just `api/` and `internal/`.

---

## API Design Patterns

### Factory Methods Over Constructors

Factory methods give evolution room without breaking backward compatibility. They also
make the API self-documenting through descriptive names.

```java
package com.company.parser.api;

/// Parses delimited text input into structured fields.
///
/// Thread-safe: instances are safe to use from multiple threads concurrently.
public interface DataParserApi {

    ParseResult parse(String input);

    /// Create a parser with the default comma delimiter.
    static DataParserApi ofComma() {
        return new com.company.parser.internal.DefaultDataParser(',');
    }

    /// Create a parser with a custom delimiter.
    static DataParserApi of(char delimiter) {
        return new com.company.parser.internal.DefaultDataParser(delimiter);
    }
}
```

**Why factory methods win:**
- Can return different internal implementations without exposing them
- Can cache/pool instances
- Can evolve parameters (add overloads) without breaking existing code
- Descriptive names make intent clear (`ofComma()` vs `new DataParser(',')`)

### Sealed Types for Controlled Hierarchies

Use sealed interfaces to define closed type hierarchies in your API. This gives consumers
exhaustive pattern matching while preventing unauthorized extension.

```java
/// Result of a processing operation.
public sealed interface ProcessResult permits ProcessResult.Success, ProcessResult.Failure {

    record Success(List<String> fields, int recordCount) implements ProcessResult {}
    record Failure(String errorMessage) implements ProcessResult {}
}
```

**Why:** Consumers get compile-time exhaustiveness checking in switch expressions.
The library controls the hierarchy — no surprise subtypes.

### Builder Pattern for Complex Configuration

When configuration exceeds 3 parameters, use a builder. Builders validate at `build()`
time, catching misconfiguration early.

```java
/// Configuration for the data processor.
public record ProcessorConfig(
    char delimiter,
    int maxFieldCount,
    boolean trimWhitespace,
    Charset charset
) {
    public static Builder builder() { return new Builder(); }

    public static final class Builder {
        private char delimiter = ',';
        private int maxFieldCount = 1000;
        private boolean trimWhitespace = true;
        private Charset charset = StandardCharsets.UTF_8;

        public Builder delimiter(char d) { this.delimiter = d; return this; }
        public Builder maxFieldCount(int n) { this.maxFieldCount = n; return this; }
        public Builder trimWhitespace(boolean t) { this.trimWhitespace = t; return this; }
        public Builder charset(Charset c) { this.charset = c; return this; }

        public ProcessorConfig build() {
            if (maxFieldCount <= 0) throw new IllegalArgumentException("maxFieldCount must be positive");
            return new ProcessorConfig(delimiter, maxFieldCount, trimWhitespace, charset);
        }
    }
}
```

### Policy / Process Separation

Separate WHAT from HOW. Configuration and policy are declared once and reused.
Processing happens per-invocation.

```java
// Policy — immutable, reusable, describes WHAT to do
var config = ProcessorConfig.builder()
    .delimiter('|')
    .trimWhitespace(true)
    .build();

// API instance — created once, thread-safe
var processor = DataProcessorApi.of(config);

// Process — per-invocation, uses the policy
var result = processor.process(inputData);
```

The consumer never participates in the internal process. They declare policy, supply
input, and receive output. No subclassing. No callback spaghetti.

---

## Package Cohesion Rules

From IBM's API design practices and JPMS best practices:

1. **A package is a cohesive unit** — All types in a package must be related to the same
   purpose. No grab-bag packages.

2. **Packages evolve by accretion** — Add new types/methods in compatible ways. Never
   remove or change existing public signatures. If you must break compatibility, create
   a new package (e.g., `api.v2/`).

3. **Minimize package coupling** — Types in `api/` should avoid referencing types from
   third-party packages in their signatures. This reduces `uses` constraints and
   dependency fan-out for consumers.

4. **One module delivers the whole package** — A package must not be split across multiple
   JARs. The consumer must know the entire API is present.

---

## module-info.java (REQUIRED)

This is your hard API boundary. No discipline required — the compiler enforces it.

```java
module com.company.mylib {
    // Public API — what consumers see
    exports com.company.mylib.api;

    // Extension points — only if spi/ exists
    exports com.company.mylib.spi;

    // internal/ is NOT exported — encapsulated by default
    // Nothing else needs to be said about it.

    // Dependencies
    requires org.slf4j;

    // Optional Spring support — qualified export
    exports com.company.mylib.autoconfigure to spring.beans, spring.context;
    requires static spring.context;
    requires static spring.boot.autoconfigure;
}
```

**Rules:**
- `api/` and `spi/` are exported. Period.
- `internal/` is never exported. The module system hides it.
- Use `requires static` for optional dependencies (Spring, etc.)
- Use qualified `exports ... to` for optional framework integration packages.

---

## Library Gradle Build

```kotlin
plugins {
    `java-library`
    `maven-publish`
}

java {
    toolchain { languageVersion = JavaLanguageVersion.of(25) }
    withJavadocJar()
    withSourcesJar()
}

dependencies {
    // API — exposed to consumers transitively (KEEP MINIMAL)
    api(libs.slf4j.api)

    // Implementation — hidden from consumers
    implementation(libs.mapstruct)
    annotationProcessor(libs.mapstruct.processor)

    // Optional Spring support — consumers opt-in, not forced
    compileOnly(libs.spring.context)
    compileOnly(libs.spring.boot.autoconfigure)

    // Testing
    testImplementation(libs.bundles.testing)
}

publishing {
    publications {
        create<MavenPublication>("mavenJava") { from(components["java"]) }
    }
}
```

**Dependency rules:**
- `api()` — ONLY for types that appear in YOUR public method signatures
- `implementation()` — everything else (hidden from consumers' compile classpath)
- `compileOnly()` — optional integrations that consumers may or may not have
- Never use `spring-boot-starter-*` in `implementation()` — libraries don't own starters

---

## Library-Specific Rules

1. **module-info.java is mandatory** — It defines your API contract at the compiler level.
2. **`api()` only for types in YOUR public signatures** — If consumers see a type in your
   method signatures, it goes in `api()`. Everything else: `implementation()`.
3. **ZERO Spring imports in production code** (except optional auto-config package).
4. **No application.yml** — Libraries have no runtime config of their own.
5. **No main class** — No `@SpringBootApplication`, no `public static void main`.
6. **All public types are records or interfaces** — Records for data, interfaces for behavior.
7. **Factory methods over constructors** — Evolution room without breaking backward compat.
8. **Builder pattern for complex config** — When >3 parameters.
9. **Unchecked exceptions** — Throw `RuntimeException` subclasses. Checked exceptions
   pollute consumer code with catch blocks for non-recoverable conditions.
10. **SPI interfaces use default methods** — So adding a method doesn't break existing
    consumer implementations.
11. **Sealed types for closed hierarchies** — Prevent unauthorized extension of your
    return types and result types.
12. **Avoid statics beyond factory methods** — No static singletons, no global state.
    Instance creation through factories/builders; singletons via DI or ServiceLoader.

---

## Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Public API interface | `NounApi` or `VerbNounApi` | `DataProcessorApi` |
| Configuration | `NounConfig` (record) | `ProcessorConfig` |
| Result type | `NounResult` (record/sealed) | `ProcessResult` |
| SPI interface | `NounSpi` or `NounProvider` | `StorageProvider` |
| Default impl | `DefaultNoun` or `InMemoryNoun` | `DefaultStorage` |
| Exception | `NounException` (unchecked) | `ProcessingException` |
| Builder | `NounConfig.Builder` (nested) | `ProcessorConfig.Builder` |
| Auto-config | `NounAutoConfiguration` | `MyLibAutoConfiguration` |

**Name quality test (Bloch):** If it's hard to find good names, go back to the drawing
board. Don't be afraid to split or merge an API. If names start falling into place,
you're on the right track.

---

## Testing

Libraries are tested WITHOUT frameworks. Pure Java. Fast. Deterministic.

### Test Categories

| Category | What it verifies | How |
|----------|-----------------|-----|
| **Unit tests** | Every public method behaves correctly | JUnit 5 + AssertJ, instantiate with `new`/factory |
| **Consumer integration tests** | Library works exactly as a consumer would use it | Instantiate via public API only, no internal access |
| **SPI contract tests** | Default implementations satisfy the SPI contract | Implement SPI interface, verify behavior |
| **Thread-safety tests** | Concurrent calls don't corrupt state | Parallel streams / virtual threads hammering public API |
| **Edge case tests** | Null inputs, empty collections, boundary values | Parameterized tests with `@ValueSource` / `@NullSource` |
| **API compatibility tests** | No accidental breaking changes between releases | japicmp on CI |

### Testing Rules

- **No @SpringBootTest** — Libraries have no Spring context.
- **No mocks for your own code** — Test with real objects. Mock only true external
  boundaries (filesystem, network) and only when needed.
- **Test naming:** `should_[behavior]_when_[condition]()`
- **One test file per production class** in mirrored package structure.
- **Every public method gets at least one test.**
- **Test the contract, not the implementation** — Tests should not break when
  `internal/` is refactored.

### Coverage Requirements

| Layer | Line | Branch |
|-------|------|--------|
| api/ (validation logic in records) | 95% | 90% |
| internal/ | 90% | 85% |
| spi/ (default method impls) | 90% | 85% |

---

## Anti-Patterns

### Architecture Violations

- `@RestController` anywhere → **WRONG OUTPUT TYPE** (libraries don't serve HTTP)
- `application.yml` exists → **WRONG OUTPUT TYPE** (libraries don't own config)
- `spring-boot-starter-*` in `implementation()` → use `compileOnly` only
- Spring annotations on public API types → **framework lock-in**
- No `module-info.java` → **missing API boundary** (this is non-negotiable)

### API Design Violations

- `implementation()` for types in public signatures → must use `api()`
- Returning framework-specific types from public API → pure JDK types only
- Mutable public class → use record or immutable builder pattern
- `throws Exception` on public method → specific unchecked exception types
- Internal class in exported package → move to `internal/` package
- Constructor with >3 params without builder → hard to evolve
- Requiring subclassing to use the library → use interfaces + composition
- Static `getInstance()` singletons → factory method or ServiceLoader

### Consumer-Hostile Patterns

- Forcing consumers to call methods in a specific order → redesign as builder/config
- Silently accepting invalid input → fail-fast with clear message
- Returning null from public method → use `Optional<T>` or throw
- Long parameter lists with same types → consumers WILL get the order wrong
- Requiring consumers to handle lifecycle (init/destroy) → handle internally or
  document with `AutoCloseable`

---

## Versioning & Compatibility

- **Semantic versioning** — MAJOR.MINOR.PATCH strictly honored
- **Package accretion** — Packages evolve by adding, never removing
- **Binary compatibility** — Run japicmp on CI against the last published version
- **Deprecation before removal** — Mark `@Deprecated(since="X", forRemoval=true)` one
  major version before removing. Include `@see` pointing to the replacement.
- **SPI evolution** — Always add `default` implementations to new SPI methods so
  existing consumer implementations don't break
