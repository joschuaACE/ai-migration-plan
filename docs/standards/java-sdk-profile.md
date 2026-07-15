# SDK Profile (output_type = "sdk")

Everything from the Library profile applies. SDK adds documentation, stability,
publishing, and developer experience requirements on top.

**Key difference from library:** Every public API element must have comprehensive
documentation, stability annotations, and binary compatibility guarantees. An SDK
is a PRODUCT — it's judged by how quickly a developer can go from zero to working code.

---

## SDK Design Principles

These principles guide EVERY decision when building an SDK (in addition to Library principles):

1. **Consumer empathy** — The person using your SDK is not you. They don't know your
   domain. Error messages guide them to the fix. Doc comments show complete working
   examples. The API reads like a story, not a puzzle.

2. **Progressive disclosure** — Simple things are simple. Common use cases need 1-3 lines.
   Advanced configuration is available but not required. Sensible defaults everywhere.
   A developer should get to "Hello World" in under 5 minutes.

3. **Backward compatibility is sacred** — Once published, a public method signature is a
   contract. Deprecate before removing. Provide migration paths. Never break consumers
   silently. 100% backward compatible — always.

4. **Documentation IS the product** — If it's not documented, it doesn't exist. If the
   docs are wrong, the code is wrong. Doc comments are tested (compilable examples).
   Preempt developers' questions — document into silence.

5. **Stability is communicated** — Every public type is annotated: `@Stable` (safe to
   depend on), `@Beta` (may change in minor versions), `@Internal` (hands off). No
   guessing. No surprise breaking changes.

6. **Versioning tells the truth** — MAJOR = breaking, MINOR = new features, PATCH = bugfix.
   No exceptions. Binary compatibility checked automatically on every release.

7. **Examples are tests** — The `samples/` directory compiles and runs against the published
   artifact. If the sample breaks, the release is blocked. Sample code is often the first
   interaction a developer has with your SDK — it must be exemplary.

8. **Idiomatic above all** — The SDK must feel native to Java developers. Follow Java
   conventions, use modern Java features, respect the ecosystem. A non-idiomatic API
   requires higher cognitive load and creates unnecessary friction.

9. **Dependable** — Great logging, tracing, and error messages. Predictable support
   lifecycle. Feature coverage is documented. Quality is measurable.

---

## SDK Architecture

SDKs use the same `api/internal/spi` architecture as libraries (see Library Profile).
The key addition is the `annotation/`, `samples/`, and `docs/` layers.

```
project-root/
├── {target_root}/              ← Migrated Java project (default: app/)
│   └── src/
│       ├── main/java/com/{group}/{artifact}/
│       │   ├── api/                     # PUBLIC: interfaces, records, exceptions
│       │   │   ├── DataProcessorApi.java
│       │   │   ├── ProcessResult.java
│       │   │   ├── ProcessConfig.java
│       │   │   └── ProcessException.java
│       │   ├── internal/                # PRIVATE: all implementation
│       │   │   └── DefaultProcessor.java
│       │   ├── spi/                     # OPTIONAL: extension points
│       │   │   └── OutputFormatter.java
│       │   └── annotation/              # PUBLIC: stability markers
│       │       ├── Stable.java
│       │       ├── Beta.java
│       │       └── Internal.java
│       ├── main/resources/
│       └── test/java/...
├── samples/                             # Runnable usage examples
│   ├── basic-usage/
│   │   ├── build.gradle.kts            # Depends on SDK as published artifact
│   │   └── src/main/java/.../BasicUsageSample.java
│   ├── advanced-config/
│   └── spring-integration/             # Optional: for Spring consumers
├── docs/
│   ├── api-overview.md                 # Architecture and concepts
│   ├── getting-started.md              # Zero to working code in 5 minutes
│   ├── migration-from-cpp.md           # For users of the original C++ API
│   └── compatibility.md                # Version history and breaking changes
└── gradle/
    └── libs.versions.toml
```

---

## Stability Annotations

Every public type MUST carry exactly one stability annotation:

```java
package com.company.sdk.annotation;

import java.lang.annotation.*;

/// Indicates this API is stable and will not change incompatibly in minor versions.
/// Safe to depend on in production code.
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD})
public @interface Stable {}
```

```java
/// Indicates this API may change in minor versions.
/// Use in production with awareness that migration may be needed.
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD})
public @interface Beta {
    String since() default "";
}
```

```java
/// Indicates this API is internal and may change without notice.
/// Not for external use. Will not appear in public Javadoc.
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD, ElementType.PACKAGE})
public @interface Internal {}
```

**Rules:**
- `@Stable` types may never have methods removed or signatures changed
- `@Beta` types must become `@Stable` or be removed within 2 minor versions
- `@Internal` types must NEVER appear in public method signatures
- Adding `@Stable` is a one-way door — you cannot downgrade to `@Beta`

---

## SDK Documentation Standards

### Doc Comment Pattern

Every public interface, class, record, and method gets a `///` markdown doc comment:

```java
/// Processes raw data from the input source into structured output.
///
/// ## Quick Start
/// ```java
/// var processor = DataProcessorApi.of(ProcessorConfig.defaults());
/// var result = processor.process("alice,bob,charlie");
/// System.out.println(result.recordCount()); // 3
/// ```
///
/// ## Thread Safety
/// Instances are thread-safe. Multiple threads may call [#process] concurrently.
///
/// ## Error Handling
/// Throws [ProcessingException] if the input is unreadable or malformed.
/// The exception message includes the input snippet and the underlying cause.
///
/// @since 1.0
/// @see ProcessorConfig
@Stable
public interface DataProcessorApi {

    /// Parse the given input string into individual fields.
    ///
    /// @param input the delimited text to parse (must not be null or blank)
    /// @return result containing parsed fields and metadata
    /// @throws ProcessingException if parsing fails due to malformed input
    /// @throws IllegalArgumentException if input is null or blank
    ParseResult process(String input);

    /// Create a processor with default comma delimiter and UTF-8 charset.
    ///
    /// This is the simplest way to get started:
    /// ```java
    /// var result = DataProcessorApi.ofDefaults().process("a,b,c");
    /// ```
    static DataProcessorApi ofDefaults() {
        return new com.company.sdk.internal.DefaultDataProcessor(
            ProcessorConfig.defaults());
    }

    /// Create a processor with custom configuration.
    ///
    /// @param config processing configuration (non-null)
    /// @see ProcessorConfig#builder()
    static DataProcessorApi of(ProcessorConfig config) {
        return new com.company.sdk.internal.DefaultDataProcessor(config);
    }
}
```

### Documentation Checklist

Every public element must have:
- [ ] One-line summary (what it does)
- [ ] Longer description if behavior is non-obvious
- [ ] Usage example (compilable code snippet)
- [ ] Thread-safety statement (on types)
- [ ] Error handling description (what throws, when, and how to handle)
- [ ] `@since` tag indicating version introduced
- [ ] `@see` links to related types
- [ ] `@param` and `@return` on every method

---

## SDK Error Message Standards

Error messages are documentation. They are often the FIRST thing a developer reads
when integrating your SDK. Make them actionable.

```java
// ❌ BAD — cryptic, unhelpful, no guidance
throw new ProcessingException("Invalid input");

// ❌ BAD — technical but no fix guidance
throw new ProcessingException("Parse error at offset 42");

// ✅ GOOD — what's wrong, what was expected, how to fix
throw new ProcessingException(
    "Cannot parse input: found empty field at position 3. "
    + "Ensure all fields contain non-empty values, or use "
    + "ProcessorConfig.builder().allowEmpty(true) to permit empty fields.");
```

**Error message structure:**
1. **What went wrong** — clear statement of the problem
2. **Context** — relevant data (file path, position, value)
3. **How to fix** — actionable guidance pointing to the right API

---

## SDK Builder Pattern

SDKs MUST use builders for any configuration with more than 2 parameters. Builders
are the primary creation mechanism — no public constructors.

```java
/// Configuration for the data processor.
///
/// ## Quick Start
/// ```java
/// // Minimal — all defaults
/// var config = ProcessorConfig.defaults();
///
/// // Custom delimiter
/// var config = ProcessorConfig.builder()
///     .delimiter('|')
///     .build();
/// ```
///
/// @since 1.0
@Stable
public record ProcessorConfig(
    char delimiter,
    int maxFieldCount,
    boolean trimWhitespace,
    boolean allowEmpty,
    Charset charset
) {
    /// Create configuration with sensible defaults (comma delimiter, UTF-8).
    public static ProcessorConfig defaults() {
        return builder().build();
    }

    /// Start building a custom configuration.
    public static Builder builder() {
        return new Builder();
    }

    /// Builder for [ProcessorConfig].
    ///
    /// All settings are optional — unset values use sensible defaults.
    @Stable
    public static final class Builder {
        private char delimiter = ',';
        private int maxFieldCount = 10_000;
        private boolean trimWhitespace = true;
        private boolean allowEmpty = false;
        private Charset charset = StandardCharsets.UTF_8;

        /// Set the field delimiter character. Default: `,`
        public Builder delimiter(char delimiter) {
            this.delimiter = delimiter;
            return this;
        }

        /// Set maximum number of fields per record. Default: 10,000.
        /// @throws IllegalArgumentException if maxFieldCount ≤ 0
        public Builder maxFieldCount(int maxFieldCount) {
            if (maxFieldCount <= 0) {
                throw new IllegalArgumentException(
                    "maxFieldCount must be positive, got: " + maxFieldCount);
            }
            this.maxFieldCount = maxFieldCount;
            return this;
        }

        /// Whether to trim whitespace from field values. Default: true.
        public Builder trimWhitespace(boolean trimWhitespace) {
            this.trimWhitespace = trimWhitespace;
            return this;
        }

        /// Whether to allow empty fields. Default: false.
        public Builder allowEmpty(boolean allowEmpty) {
            this.allowEmpty = allowEmpty;
            return this;
        }

        /// Set the character encoding. Default: UTF-8.
        public Builder charset(Charset charset) {
            this.charset = Objects.requireNonNull(charset, "charset must not be null");
            return this;
        }

        /// Build the configuration. Validates all settings.
        public ProcessorConfig build() {
            return new ProcessorConfig(
                delimiter, maxFieldCount, trimWhitespace, allowEmpty, charset);
        }
    }
}
```

**Builder rules:**
- Builders are `final` classes — cannot be subclassed
- Every setter returns `this` (fluent API)
- `build()` validates and returns an immutable object
- Required parameters go in builder constructor; optional use setters
- Builders are reusable — calling `build()` multiple times is safe

---

## SDK Versioning & Compatibility

### Service Version Pattern

If the SDK wraps a versioned service or protocol, expose version selection:

```java
/// Supported versions of the data processing format.
@Stable
public enum ProcessorVersion {
    V1_0("1.0"),
    V2_0("2.0");

    private final String version;

    ProcessorVersion(String version) {
        this.version = version;
    }

    public String getVersion() { return version; }

    /// Get the latest supported version.
    public static ProcessorVersion getLatest() {
        return V2_0;
    }
}
```

### Binary Compatibility Rules

- **Run japicmp on every release** against the previous published version
- **NEVER remove** a `@Stable` public method — deprecate first
- **NEVER change** a `@Stable` method signature (parameters or return type)
- **Adding methods to interfaces** — only with `default` implementation
- **Adding methods to SPI interfaces** — always with `default` implementation
- **New classes/methods** — allowed in minor versions (additive change)
- **Package accretion** — packages grow by adding, never by removing

### Deprecation Process

```java
/// @deprecated Since 2.1. Use [#processAsync(ProcessCommand)] instead.
///   Will be removed in 3.0.
/// @see #processAsync(ProcessCommand)
@Deprecated(since = "2.1", forRemoval = true)
@Stable
ProcessResult processSync(ProcessCommand command);
```

**Timeline:** Deprecated in version X → removed no earlier than version X+1.0.0 (next major)

---

## Samples

Samples are the SDK's first impression. They must be:
- **Minimal** — only the essentials to demonstrate one concept
- **Functional** — compile and run without errors
- **Commented** — brief comments explaining each meaningful line
- **Self-contained** — no dependency on other samples
- **Tested** — built by CI on every commit

### Sample Structure

```
samples/
├── basic-usage/
│   ├── build.gradle.kts           # depends on published SDK artifact
│   └── src/main/java/
│       └── BasicUsageSample.java  # public static void main
├── custom-config/
│   └── ...
├── error-handling/
│   └── ...
└── spring-integration/            # Optional: for Spring consumers
    └── ...
```

### Sample Rules

1. **Each sample has `public static void main`** — immediately runnable
2. **Depend on published artifact** — not source dependency
3. **One concept per sample** — don't combine multiple operations
4. **Include error handling** — show how to handle exceptions idiomatically
5. **Run on all platforms** — Windows, macOS, Linux
6. **CI builds samples** — if a sample breaks, the release is blocked

---

## SDK-Specific Rules (in addition to Library rules)

1. **Every public class/interface/method/record** has `///` markdown doc comment
2. **Every public type** has a stability annotation (`@Stable`, `@Beta`, or `@Internal`)
3. **Doc comments include usage examples** — show the consumer how to call it
4. **Binary compatibility checked** — japicmp on every release
5. **Semantic versioning strict** — breaking changes = major bump, new API = minor
6. **Samples compile against published artifact** — not source dependency
7. **Migration guide** from C++ API if replacing existing SDK
8. **Deprecation process** — mark `@Deprecated(since="X", forRemoval=true)` one major
   version before removal. Include `@see` pointing to the replacement
9. **Getting-started guide** — zero to working code in 5 minutes or less
10. **Error messages are actionable** — what went wrong, context, how to fix
11. **Thread-safety documented on every public type** — stated explicitly
12. **Immutable client instances** — once built, a client is immutable and thread-safe

---

## SDK Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Public API interface | `NounApi` | `DataProcessorApi` |
| Configuration | `NounConfig` (record + builder) | `ProcessorConfig` |
| Result type | `NounResult` (record/sealed) | `ProcessResult` |
| SPI interface | `NounSpi` or `NounProvider` | `StorageProvider` |
| Exception | `NounException` (unchecked) | `ProcessingException` |
| Stability annotation | `@Stable`, `@Beta`, `@Internal` | `@Stable` |
| Version enum | `NounVersion` | `ProcessorVersion` |
| Sample class | `NounSample` | `BasicUsageSample` |

---

## SDK Testing

Same as Library testing, PLUS:

| Category | What it verifies | How |
|----------|-----------------|-----|
| **Sample compilation** | Samples compile against published artifact | Gradle composite build or dependency |
| **Doc example validation** | Code in doc comments compiles | Extract and compile during build |
| **Binary compatibility** | No accidental breaking changes | japicmp on CI |
| **Deprecation audit** | Deprecated items have replacement docs | Custom lint or ArchUnit rule |
| **Thread-safety stress** | Concurrent client usage is safe | Virtual thread stress tests |

---

## SDK Anti-Patterns (in addition to Library anti-patterns)

### Documentation Violations
- Public method without `///` doc comment → **VIOLATION**
- Public type without `@Stable`/`@Beta`/`@Internal` → **VIOLATION**
- Doc comment without usage example on public interface → **incomplete**
- Error message that doesn't guide the user to a fix → **rewrite it**

### Compatibility Violations
- Breaking change without major version bump → **VIOLATION**
- Removing public method without deprecation cycle → **VIOLATION**
- `@Internal` type exposed in public method signature → **API design error**
- Sample that depends on internal packages → **VIOLATION**

### Developer Experience Violations
- More than 3 lines to get started with common case → **over-complicated**
- Requiring domain knowledge to use basic features → **not progressive disclosure**
- Cryptic error without guidance → **hostile to consumers**
- No getting-started guide → **incomplete SDK**
- Builder without sensible defaults → **forcing unnecessary decisions**
