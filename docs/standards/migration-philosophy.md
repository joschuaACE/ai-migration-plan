# Migration Philosophy

You are performing a C++ to Java Spring Boot migration. Every interaction in this project
is governed by these non-negotiable principles.

## Iron Laws

1. **NO TRANSLATION WITHOUT SOURCE ANALYSIS FIRST** — Read the ENTIRE C++ source file before writing a single line of Java. Trace the real flow end to end.
2. **NO MODULE MARKED COMPLETE WITHOUT SEMANTIC EQUIVALENCE VERIFICATION** — Same inputs must produce same outputs. Every public method's behavior must be preserved or the change explicitly recorded.
3. **NO NEW DEPENDENCY WITHOUT CHECKING IF SPRING/JDK ALREADY PROVIDES IT** — Climb the migration ladder before reaching for third-party code.
4. **NO ARCHITECTURAL DECISIONS WITHOUT RECORDING IN decisions.md** — Silent redesigns are bugs. Every divergence from 1:1 translation gets a decision record.
5. **NO CODE WITHOUT TESTS** — Every translated class ships with tests that exercise the same paths as the C++ original (or better).

## The Migration Ladder

Before writing target code, stop at the first rung that holds:

1. **Does this C++ code need to exist in Java?** → YAGNI: skip dead code, mark in inventory.md
2. **Does Spring Boot already provide this?** → Use the starter/auto-configuration
3. **Does the JDK standard library cover it?** → java.util, java.time, java.nio, java.net.http
4. **Does an already-chosen dependency handle it?** → Reuse what's in build.gradle.kts
5. **Can a Spring annotation do it?** → @Transactional, @Cacheable, @Scheduled, @Async
6. **Can it be one line?** → Write one line
7. **Only then:** Write the minimum implementation that passes the test

The ladder runs AFTER you understand the problem. Read first, climb second.

## Behavioral Equivalence

The migrated Java code must produce **identical observable behavior** to the C++ original:
- Same inputs → same outputs (within type-system differences)
- Same error conditions → equivalent exceptions
- Same ordering guarantees (if the C++ code was ordered, Java must be too)
- Same thread-safety properties (if C++ was thread-safe, Java must be too)

**Acceptable divergences (must be recorded in decisions.md):**
- Memory management differences (RAII → Spring lifecycle, expected)
- Platform-specific code replaced with portable Java (expected)
- Performance characteristics (Java GC vs C++ manual allocation, expected)
- Null handling improvements (raw pointers → Optional<T>, improvement)

**Unacceptable divergences (these are bugs):**
- Silently dropping functionality
- Changing business logic without decision record
- Swallowing exceptions that C++ propagated
- Breaking API contracts that other code depends on
- Removing thread-safety without analysis

## Output Type Awareness

Not every C++ codebase migrates to a Spring Boot microservice. The `output_type` in config.json
determines what the target artifact is:

| output_type | C++ was... | Java becomes... |
|-------------|-----------|-----------------|
| `service` | Executable with network listeners | Spring Boot deployable |
| `library` | .dll / .so / .a / static lib | Plain JAR (no main, no Spring Boot plugin) |
| `sdk` | Library with versioned public API | Library + docs + samples + stability markers |
| `cli` | Command-line tool | Picocli/Spring Shell app with native-image option |

**What this changes:**
- **Library/SDK:** No `@SpringBootApplication`, no application.yml, no REST controllers.
  The public API is the driving ports (port/in/ interfaces), not endpoints.
  SPIs replace adapters — consumers provide their own implementations.
- **CLI:** Adapter layer is cli/ (command parsers), not web/.
  Output is stdout/stderr + exit codes, not HTTP responses.
- **All types:** Domain layer stays pure Java. Hexagonal direction stays inward.
  Behavioral equivalence still applies — same inputs → same outputs regardless of packaging.

**The Migration Ladder still applies** regardless of output type. The question "Does Spring Boot
already provide this?" is simply irrelevant for libraries — skip to "Does the JDK standard
library cover it?" when output_type is `library` or `sdk`.

## Translation Patterns

| C++ Pattern | Java/Spring Equivalent | Notes |
|-------------|----------------------|-------|
| RAII / destructor | try-with-resources / @PreDestroy / @DisposableBean | Lifecycle managed by Spring |
| new/delete | Spring bean lifecycle (no manual allocation) | Let the container manage it |
| shared_ptr | @Scope("singleton") bean (default) | Spring singleton = shared ownership |
| unique_ptr | @Scope("prototype") or local variable | Exclusive ownership |
| std::vector | List<T> (ArrayList) | Prefer immutable: List.of() |
| std::map | Map<K,V> (HashMap/LinkedHashMap) | Prefer Map.of() for constants |
| std::optional | Optional<T> | Never return null |
| Templates | Generics (if semantically equivalent) | Otherwise use strategy pattern |
| Multiple inheritance | Interface composition + delegation | Java has no MI |
| Operator overloading | Named methods (add, multiply, compareTo) | Implement Comparable for ordering |
| Friend functions | Package-private access | Same package = friend |
| #define constants | static final / enum / @ConfigurationProperties | Context-dependent |
| #ifdef platform | @Profile / Spring profiles | Runtime switchable |
| Function pointers | @FunctionalInterface / Consumer / Function | Type-safe callbacks |
| Global state | @Component @Scope("singleton") | Spring-managed, testable |
| volatile/atomic | java.util.concurrent.atomic / synchronized | Match original guarantees |
| std::thread | Virtual threads / @Async | Modern concurrency |
| ThreadLocal | ScopedValue (Java 25) | Preferred for virtual-thread workloads |
| Exceptions (throw) | Unchecked exceptions (RuntimeException hierarchy) | Domain exception classes |

## Red Flags — STOP and Investigate

If you find yourself doing any of these, STOP:

- Writing Java without having read the C++ source → **Read it first**
- Adding an abstraction that doesn't exist in C++ → **Justify it or remove it**
- Skipping a test because "it's obvious" → **Write the test**
- Translating dead code → **Mark dead in inventory.md, skip translation**
- Generating a utility class → **It probably belongs as a domain service or port**
- Putting Spring annotations in domain/ package → **VIOLATION: domain is pure Java**
- Using @Autowired on a field → **Constructor injection only**
- Returning null from a public method → **Use Optional<T>**
- Catching Exception broadly → **Catch specific exceptions**

## Anti-Rationalization

| Excuse | Response |
|--------|----------|
| "This file is too simple to need analysis" | Every file gets analysis. Simple files have non-obvious edge cases in their callers. |
| "I'll improve the architecture while migrating" | NO. Migration preserves behavior. Architecture improvements are SEPARATE phases with SEPARATE decisions. |
| "The test is trivial, I'll skip it" | No. Every public method gets a test. Period. |
| "I'll add a helper class to make it cleaner" | Did the C++ need it? If not, you're adding complexity. YAGNI. |
| "The Spring way is better here" | Record the decision in decisions.md FIRST. Then implement. Never silently redesign. |
| "This code is obviously dead" | Prove it. Grep all callers. Mark in inventory.md with evidence. |
| "I'll handle error cases later" | No. Error handling migrates WITH the happy path. Same commit. |
| "The C++ tests are too coupled to port" | Write NEW tests that verify the same behavior. Don't skip coverage. |

## Progress Discipline

- Update `.migration/state.md` after every completed plan
- Never mark a phase complete without running ALL tests
- If stuck for > 10 minutes, record the blocker in state.md and move to next unit
- Every commit message follows: `migrate(phase-N/plan-P): SourceClass → TargetClass`
- Tag phase completion: `git tag migrate-phase-N-complete`
