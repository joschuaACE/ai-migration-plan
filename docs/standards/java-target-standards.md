# Target Application Standards

All generated Java code MUST conform to these standards. No exceptions.

## How to Read This Document

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Read PART 1 (Universal) — applies to ALL output types  │
│  Step 2: Read YOUR output_type profile file (auto-loaded)       │
│  Step 3: Check PART 3 anti-patterns before committing           │
└─────────────────────────────────────────────────────────────────┘
```

**Your output_type** is set in `.migration/config.json`. It determines which profile
file applies:

| output_type | What you're building | Profile File |
|-------------|---------------------|--------------|
| `service` | Spring Boot deployable (REST/gRPC/messaging) | `java-service-profile.md` |
| `library` | Plain JAR consumed by other projects | `java-library-profile.md` |
| `sdk` | Published library with docs + stability guarantees | `java-sdk-profile.md` |
| `cli` | Command-line tool with argument parsing | `java-cli-profile.md` |

---

# PART 1: Universal Standards (ALL Output Types)

Everything in Part 1 applies regardless of output_type.

## 1.1 Architecture: Hexagonal (Ports & Adapters)

### Core Principle

Dependencies point INWARD. Outer layers know about inner layers. Inner layers
know NOTHING about outer layers.

> **Note:** Hexagonal is mandatory for `service` and `cli` output types. For `library`
> and `sdk`, a simpler layered architecture (api/internal/spi) may be more appropriate —
> see `java-library-profile.md` for the decision criteria.

```
┌──────────────────────────────────────────────────┐
│  adapter/ (outermost — frameworks, I/O, infra)   │
│  ┌──────────────────────────────────────────┐    │
│  │  application/ (orchestration, use cases)  │    │
│  │  ┌──────────────────────────────────┐    │    │
│  │  │  domain/ (innermost — pure Java)  │    │    │
│  │  └──────────────────────────────────┘    │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

### Hexagonal Rules (Enforced by ArchUnit)

1. **domain/** has ZERO imports from: `org.springframework.*`, `jakarta.persistence.*`, `jakarta.transaction.*`
2. **domain/port/** contains ONLY interfaces (+ records for port method parameters)
3. **Dependencies point inward:** adapter → application → domain. NEVER reverse.
4. **Application layer owns transaction boundaries** — `@Transactional` on use cases, NEVER on domain services
5. **Every driven port (out/) has an adapter implementation AND a test fake**
6. **Adapters are replaceable** — switching from JPA to MongoDB changes ONLY `adapter/out/persistence/`

### Package Structure (Universal Layers)

```
src/main/java/com/{group}/{artifact}/
├── domain/                      # ZERO framework imports. Pure Java.
│   ├── model/                   # Entities, value objects (records), aggregates
│   ├── port/
│   │   ├── in/                  # Driving ports — use case interfaces
│   │   └── out/                 # Driven ports — repository/client/messaging interfaces
│   ├── service/                 # Domain services — business rules
│   └── exception/               # Domain-specific exception hierarchy
├── application/                 # Thin orchestration layer
│   ├── usecase/                 # Implements port/in/ interfaces
│   ├── mapper/                  # MapStruct mappers (domain ↔ DTO)
│   └── dto/                     # Records: commands, queries, responses
├── adapter/                     # ← varies by output_type (see profile file)
│   ├── in/                      # Driving adapters (inbound) — type-specific
│   └── out/                     # Driven adapters (outbound)
└── config/                      # Wiring — type-specific
```

### Adapter-In → Use Case Dependency Flow (MANDATORY)

**The single most important architectural rule:** Driving adapters (adapter/in/) MUST
invoke **use case port interfaces** (domain/port/in/). They NEVER directly inject
use case implementations, domain services, or repositories.

```
┌─────────────────┐       ┌──────────────────────┐       ┌──────────────┐
│  adapter/in/    │──────▶│  domain/port/in/      │◀──────│ application/ │
│  (entry point)  │ uses  │  (UseCase interface)  │ impl  │ (Service)    │
└─────────────────┘       └──────────────────────┘       └──────────────┘
```

Rules:
1. Entry points inject USE CASE PORTS (interfaces), never implementations
2. Entry points call use case methods, never domain services directly
3. Entry points never access repositories or driven ports
4. One entry point method = one use case invocation
5. The adapter/in/ layer does ONLY: parse input → validate → call use case → map response

## 1.2 Java 25 LTS Language Standards

**Target: Java 25 (LTS, released September 2025)** — All migrated code targets Java 25.

### Required Language Features

**Carried from Java 21 (stable):**
- **Records** for all DTOs, commands, queries, value objects, configuration properties
- **Sealed interfaces** for closed domain type hierarchies (e.g., Payment = Cash | Card | Crypto)
- **Pattern matching** in switch expressions for sealed type dispatch
- **Virtual threads** as default threading model
- **Text blocks** for multi-line strings (SQL, templates)
- **var** for local variables where type is obvious from RHS

**New in Java 22–24 (stable in 25):**
- **Unnamed variables (`_`)** — in lambdas, catches, and patterns where variable is unused
- **Stream Gatherers** (`stream.gather(...)`) — custom intermediate stream operations
- **Foreign Function & Memory API** — for native interop, replaces JNI
- **Markdown documentation comments** (`/// `) — preferred over HTML Javadoc
- **Flexible constructor bodies** — validate/compute before `super()` call

**New in Java 25 (stable):**
- **Scoped Values** (`ScopedValue<T>`) — preferred over `ThreadLocal` for virtual-thread workloads
- **Module import declarations** (`import module java.base`) — for compact utilities and tests
- **Compact source files** — for scripts, prototypes, CLI tools (not production services)

**Preview features (USE ONLY with decisions.md entry):**
- Structured Concurrency (5th preview) — allowed in non-critical paths
- Primitive Types in Patterns (3rd preview) — wait for stable
- Stable Values (preview) — wait for stable

### Scoped Values Pattern

```java
public final class RequestContext {
    public static final ScopedValue<TenantId> TENANT = ScopedValue.newInstance();
    public static final ScopedValue<UserId> CURRENT_USER = ScopedValue.newInstance();
}

// Bind at entry point
ScopedValue.where(RequestContext.TENANT, tenantId)
    .where(RequestContext.CURRENT_USER, userId)
    .run(() -> next.handle(request));

// Read downstream
TenantId tenant = RequestContext.TENANT.get();
```

## 1.3 Code Quality Constraints

| Metric | Maximum | Action if Violated |
|--------|---------|-------------------|
| Cyclomatic complexity per method | 10 | Extract helper methods or decompose |
| Lines per class (excl. imports) | 200 | Split into focused classes |
| Lines per method | 30 | Extract to private methods or new class |
| Dependencies per constructor | 4 | Split the use case / service |
| Package depth | 4 | Flatten or introduce module |

## 1.4 Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Driving port (in) | `VerbNounUseCase` | `ProcessOrderUseCase` |
| Driven port (out) | `NounPort` or `NounGateway` | `OrderRepository`, `PaymentGateway` |
| Use case impl | `VerbNounService` | `ProcessOrderService` |
| Domain entity | `Noun` | `Order`, `Customer` |
| Value object | `Noun` (record) | `Money`, `Address`, `OrderId` |
| DTO | `NounRequest` / `NounResponse` | `CreateOrderRequest` |
| Mapper | `NounMapper` | `OrderMapper` |
| Exception | `NounException` | `OrderNotFoundException` |
| Test | `NounTest` / `NounIntegrationTest` | `ProcessOrderServiceTest` |

Adapter naming varies by output_type — see your profile file.

## 1.5 Testing Principles (Universal)

**Rules that apply to ALL output types:**
- Domain tests: NO mocks. Test with real objects. Domain has no dependencies to mock.
- Application tests: Mock ports (interfaces). Verify orchestration logic.
- One test file per production class.
- Test naming: `should_[behavior]_when_[condition]()`
- No test without at least one assertion.
- Every public method has at least one test.

**Coverage Requirements:**
| Layer | Line | Branch | Mutation |
|-------|------|--------|----------|
| domain/ | 95% | 90% | 70% |
| application/ | 90% | 85% | 60% |
| adapter/in/ | 80% | 75% | — |
| adapter/out/ | 75% | 70% | — |

## 1.6 Dependency Management: Version Catalog (MANDATORY)

**Rule: ZERO hardcoded versions in `build.gradle.kts`.** All versions managed via
Gradle Version Catalog (`gradle/libs.versions.toml`).

| Rule | Rationale |
|------|-----------|
| All versions in `libs.versions.toml` ONLY | Single source of truth |
| Use `mavenBom()` for multi-artifact projects | Transitive alignment |
| Use `bundles` for related groups | Atomic upgrades |
| Pin annotation processors to same version as lib | MapStruct processor must match |
| No `+`, `latest.release`, or open ranges | Reproducible builds |
| Lock file in CI | Detect drift |

**Dependency choice rules (ALL types):**

| Need | Use | NOT |
|------|-----|-----|
| Object mapping | MapStruct | ModelMapper, manual |
| JSON | Jackson | Gson, org.json |
| Date/Time | java.time.* | java.util.Date, Joda-Time |
| Logging | SLF4J | System.out, Log4j direct |
| Testing | JUnit 5 + AssertJ + Mockito | JUnit 4, Hamcrest |
| Thread context | ScopedValue (Java 25) | ThreadLocal |
| Native interop | Foreign Function & Memory API | JNI |

---

# PART 3: Universal Anti-Patterns

These are red flags in ANY output type. Stop and fix immediately.

## Domain Layer Violations

- `import org.springframework.*` inside `domain/` → **ALWAYS WRONG**
- `import jakarta.persistence.*` inside `domain/` → **ALWAYS WRONG**
- Domain class with `@Service`, `@Component`, `@Entity` → move annotation to outer layer
- Domain service calling adapter directly → invert through port

## Architecture Violations

- Adapter/in/ injecting domain service directly → must use port/in interface
- Adapter/in/ accessing driven port (repository) → must go through use case
- Circular dependency between packages → break with interface extraction
- Application layer importing adapter types → wrong direction

## Code Smell Violations

- `@Autowired` on a field → constructor injection only
- `null` returned from public method → use `Optional<T>`
- `catch (Exception e)` → catch specific exception types
- `.get()` on Optional without guard → `orElseThrow()`
- `new` for a dependency inside a method → inject it
- `System.out.println()` → SLF4J logger
- Mutable DTO class → use `record`
- Static utility class → domain service or extension
- `ThreadLocal` for context → `ScopedValue` (Java 25)
- Hardcoded version in build.gradle.kts → version catalog

## Output-Type Cross-Contamination

- Library producing `adapter/in/web/` code → wrong output type
- CLI with `@RestController` → wrong output type
- Service without `application.yml` → incomplete
- SDK without Javadoc on public API → incomplete
- Library with `spring-boot-starter-*` in `implementation()` → use `compileOnly`

---

## Output Type Profiles

The output-type-specific standards (Part 2) are in separate steering files that
auto-load based on your migration context:

- `java-service-profile.md` — Spring Boot 4.x deployable (REST/gRPC/messaging)
- `java-library-profile.md` — Plain JAR consumed by other projects
- `java-sdk-profile.md` — Published library with docs + stability guarantees
- `java-cli-profile.md` — Command-line tool with argument parsing

These files use `inclusion: auto` and are loaded when relevant to your current task.
