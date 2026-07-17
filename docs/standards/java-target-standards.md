# Target Application Standards

All generated Java code MUST conform to these standards. No exceptions.

## How to Read This Document

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Read ALL PARTS — they apply to ALL output types        │
│  Step 2: Read YOUR output_type profile file (auto-loaded)       │
│  Step 3: Check PART 12 anti-patterns before committing          │
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

# PART 1: Architecture & Package Structure

## 1.1 Conceptual Model: Hexagonal (Ports & Adapters)

The conceptual architecture is hexagonal — dependencies point INWARD. Outer layers
know about inner layers. Inner layers know NOTHING about outer layers. This principle
is absolute regardless of how the packages are named.

```
┌──────────────────────────────────────────────────────────────┐
│  presentation/external (outermost — frameworks, I/O, infra)  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  business/ (orchestration, domain logic)              │    │
│  │  ┌──────────────────────────────────────────────┐    │    │
│  │  │  persistence/ (data access via DbAdapters)    │    │    │
│  │  └──────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## 1.2 Services — Four-Layer Package Structure

All Spring Boot services use a consistent 4-layer package layout:

```
de.datev.{org}.{service-name}/
├── presentation/
│   ├── rest/
│   │   ├── {domain}/          ← Controllers grouped by business domain
│   │   ├── exception/         ← @ControllerAdvice ExceptionMapper
│   │   ├── handler/           ← Generic request handlers (if needed)
│   │   ├── model/             ← DTOs (sub-packaged by domain)
│   │   │   ├── base/
│   │   │   ├── {domain1}/
│   │   │   └── {domain2}/
│   │   └── mapper/            ← MapStruct mappers (DTO ↔ Model)
│   ├── event/                 ← Kafka event handlers (inbound)
│   │   └── model/             ← Event DTOs
│   └── security/              ← Security adapters, AOP aspects
├── business/
│   ├── {domain}/              ← Service classes + domain models
│   │   ├── model/             ← Business-layer value objects
│   │   ├── mapper/            ← Business-level mappers
│   │   └── (validators, checks, resolvers)
│   ├── commands/              ← Command objects (complex services)
│   │   └── {domain}/
│   ├── exception/             ← Business exceptions
│   └── util/                  ← Business utilities
├── persistence/
│   ├── entity/                ← JPA entities
│   ├── repository/            ← Spring Data JPA repositories
│   ├── mapper/                ← Entity ↔ Model mappers
│   ├── {Domain}DbAdapter.java ← Adapter wrapping repos (THE key pattern)
│   └── Interceptor/           ← Hibernate interceptors
├── external/
│   ├── feign/                 ← @FeignClient interfaces
│   ├── model/                 ← External service DTOs
│   ├── mapper/                ← External ↔ Model mappers
│   ├── caching/               ← Request-scoped caches
│   ├── kafka/                 ← Kafka producers (outbound)
│   └── {Service}Adapter.java  ← Adapter wrapping Feign clients
└── infrastructure/
    └── configuration/         ← Spring @Configuration classes
        ├── web/
        ├── mongo/
        ├── jpa/
        └── shedlock/
```

## 1.3 Reactive Services (WebFlux) — Flat Package Variant

WebFlux services use a slightly flatter structure with "boundry" (sic) instead of "presentation":

```
de.datev.{org}.{service-name}/
├── boundry/
│   ├── controller/            ← @RestController implementing generated API interfaces
│   └── event/
│       ├── config/
│       └── model/
├── client/                    ← WebClient-based API clients
├── config/
│   ├── filter/                ← WebFlux WebFilters
│   ├── mongo/
│   └── security/
├── constant/                  ← Static constant classes
├── document/codec/            ← MongoDB codecs
├── exception/                 ← Exception hierarchy + @RestControllerAdvice
├── functions/                 ← Business logic functions
├── logging/                   ← Custom log layouts (VK3 masking)
├── mapper/                    ← MapStruct interfaces
├── model/
│   └── enums/
├── repository/                ← Raw MongoCollection-based repos
├── service/                   ← Interface + Impl pattern
└── util/                      ← Utility classes
```

## 1.4 Library JARs — API/Internal/SPI Layering

```
de.datev.{org}.{library-name}/
├── api/                       ← Public API (exported via module-info.java)
├── spi/                       ← Extension points consumers implement (exported)
└── internal/                  ← Hidden implementation (NOT exported)
    ├── model/
    ├── basis/
    └── {domain-specific packages}
```

## 1.5 Layer Dependency Rules (Enforced by ArchUnit)

| Rule | Enforcement |
|---|---|
| Layer dependencies flow: presentation → business → persistence/external | ArchUnit |
| Persistence layer accessed ONLY through `*DbAdapter` classes | ArchUnit |
| Controllers reside in `presentation/rest/` | ArchUnit |
| Controller names end with `Controller` | ArchUnit |
| Database entities/repos only in `persistence/` | ArchUnit |
| MapStruct mappers use Spring injection | ArchUnit |
| MapStruct mappers use `unmappedTargetPolicy = ERROR` | ArchUnit |
| Business layer has ZERO imports from `jakarta.persistence.*` | ArchUnit |
| Business layer has ZERO imports from `org.springframework.web.*` | ArchUnit |

## 1.6 Adapter-In → Service Dependency Flow (MANDATORY)

**The single most important architectural rule:** Presentation layer components (controllers)
MUST invoke **business service classes**. They NEVER directly inject repositories or DbAdapters.

```
┌─────────────────┐       ┌──────────────────────┐       ┌──────────────────┐
│  presentation/  │──────▶│  business/            │──────▶│  persistence/    │
│  (Controller)   │ calls │  (Service)            │ calls │  (DbAdapter)     │
└─────────────────┘       └──────────────────────┘       └──────────────────┘
```

Rules:
1. Controllers inject Services, never DbAdapters or Repositories
2. Services inject DbAdapters and external Adapters, never Repositories directly
3. DbAdapters inject Repositories and Mappers
4. One controller method = one service method invocation (ideally)
5. The presentation layer does ONLY: parse input → validate → call service → map response

---

# PART 2: Java 25 Language Standards

**Target: Java 25 (LTS, released September 2025)** — All migrated code targets Java 25.

## 2.1 Required Language Features

**Carried from Java 21 (stable):**
- **Records** for library value objects, configuration properties, and simple DTOs where mutability is not needed
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

## 2.2 Scoped Values Pattern

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

## 2.3 Records vs Lombok Classes

| Context | Use Records | Use Lombok Classes |
|---------|-------------|-------------------|
| Library value objects | ✓ | — |
| Configuration properties | ✓ | — |
| Simple immutable DTOs | ✓ | — |
| Service-layer models (mutable) | — | ✓ (`@Getter @Setter @Builder` etc.) |
| Service DTOs (mutable, inheritance) | — | ✓ (`@Data @SuperBuilder`) |
| JPA entities | — | ✓ (`@Data @Builder @NoArgsConstructor @AllArgsConstructor`) |
| Event DTOs needing builder pattern | — | ✓ (`@Builder(toBuilder = true)`) |

**Rule:** In service projects, prefer Lombok classes for models/DTOs (matches existing DATEV patterns).
Records are appropriate for library value objects and sealed interface members.

---

# PART 3: Code Patterns (Lombok, DI, Models, DTOs)

## 3.1 Lombok Usage — Standard Service Class

```java
@Slf4j
@Service
@RequiredArgsConstructor
public class GroupService {
    private final GroupDbAdapter groupDbAdapter;
    private final OmAdapter omAdapter;
}
```

## 3.2 Lombok Usage — Standard Controller

```java
@Slf4j
@RestController
@RequestMapping(value = {"v1", "v1/privileged"})
@Tag(name = "Group")
@RequiredArgsConstructor
public class GroupController {
    private final GroupService groupService;
}
```

## 3.3 Model/DTO Classes (Service Projects)

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@SuperBuilder
public class GroupDto {
    @JsonProperty("display_name")
    private String displayName;
}
```

## 3.4 Model Classes (Library Projects) — THE Standard Combo

**Always use this exact 7-annotation combination. Never use `@Data` in library models.**

```java
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode
@ToString
public class MasterData {
    private Integer consultant;
    private Integer client;
    private Integer fiscalYear;
}
```

## 3.5 Constants/Utility Classes

```java
@UtilityClass
public class MetricConstants {
    public static final String METRIC_MONGO = "mongodb.operation";
}
```

## 3.6 Lombok Rules

| Rule | Applies To |
|---|---|
| `@Slf4j` on every class that logs (nearly all) | All |
| `@RequiredArgsConstructor` for constructor injection | Controllers, Services, Adapters |
| Never use `@Data` in library model projects | Libraries |
| `@Builder(toBuilder = true)` when copies with modification needed | DTOs/Events |
| `@ToString(callSuper = true)` + `@EqualsAndHashCode(callSuper = true)` for subclasses | Inheritance |
| `lombok.addLombokGeneratedAnnotation = true` in `lombok.config` | All projects |

## 3.7 lombok.config (MANDATORY in every project)

```properties
config.stopBubbling = true
lombok.addLombokGeneratedAnnotation = true
```

## 3.8 Dependency Injection Pattern

**Always constructor injection via `@RequiredArgsConstructor`:**

```java
@Service
@RequiredArgsConstructor
public class ImportService {
    private final GroupDbAdapter groupDbAdapter;      // persistence adapter
    private final OmAdapter omAdapter;                // external adapter
    private final GroupDtoMapper groupDtoMapper;      // mapper
}
```

Rules:
- **NEVER** use `@Autowired` field injection
- **NEVER** use setter injection
- All injected fields are `private final`
- Maximum 4 dependencies per constructor — split the class if exceeded

## 3.9 Model/DTO Field Type Rules

### Wrapper Types Only (Never Primitives in Domain Models)

| Use | Don't Use | Reason |
|---|---|---|
| `Integer` | `int` | Nullable fields common in domain |
| `Long` | `long` | Monetary amounts, IDs |
| `Boolean` | `boolean` | Tri-state possible (null = unknown) |

Exception: DTOs with `@JsonProperty("is_global") private boolean global` — simple flags can use primitives in DTOs.

### Monetary/Amount Values

- **Library models**: `Long` (minor units — cents/Pfennig)
- **API/calculations**: `BigDecimal` (when precision required)
- **Never `float` or `double`** for financial data

### Identifiers

| Type | Usage |
|---|---|
| `Long` | Internal database IDs |
| `UUID` | Service organization IDs, external IDs |
| `Integer` | Domain-specific codes (consultant number, client number, fiscal year) |
| `String` | External string identifiers |

### Collections

```java
private List<CollectiveAccount> collectiveAccounts;           // Lists of nested objects
private Map<String, AccountValue> values = new LinkedHashMap<>();  // Order-preserving maps
private List<Integer> accountNumbers;                          // Lists of primitives
```

- Initialize Maps with `new LinkedHashMap<>()` (preserves insertion order)
- Lists default to `null` (not empty list)

### Date/Time

| Type | Usage |
|---|---|
| `OffsetDateTime` | Timestamps with timezone (state changes) |
| `LocalDate` | Date-only values (fiscal year dates) |
| `Integer` | Year as integer when only year needed |

### Enums

```java
@Getter
public enum LegalFormEnum {
    UNBEKANNT(0),
    EU(1),
    KAP(2);

    private final Integer value;

    LegalFormEnum(Integer value) {
        this.value = value;
    }

    @Override
    public String toString() {
        return String.valueOf(value);
    }
}
```

Rules:
- Enum suffix: `*Enum` (e.g., `LegalFormEnum`, `CompanySizeClassEnum`)
- Numeric `Integer value` field
- Override `toString()` to return the value
- German business terms for enum constants (`UNBEKANNT`, `KLEIN`, `GROSS`)

## 3.10 Value Objects & Type Safety

### Custom Value Object for REST Binding

```java
@Data
@RequiredArgsConstructor
public class PersonContextId {
    private final Long value;

    public static PersonContextId valueOf(String value) {
        return new PersonContextId(Long.parseLong(value));
    }
}
```

Spring MVC automatically calls `valueOf(String)` for request parameter binding:
```java
@GetMapping("/profiles")
public PersonProfileResponse getProfile(
    @RequestParam("person-context-id") PersonContextId personContextId) { ... }
```

### Command Objects with Validation Guards

```java
public class AddClassifierCommand implements ProfileIdCommandInterface {
    private final Long profileId;
    private final Classifier classifier;

    public AddClassifierCommand(Long profileId, Classifier classifier) {
        if (profileId == null)
            throw new IllegalArgumentException("ProfileId must not be null!");
        guardClassifierElements(classifier.getClassifierElements());
        this.profileId = profileId;
        this.classifier = classifier;
    }
}
```

---

# PART 4: REST & Security

## 4.1 Dual-Path Mapping (Standard Pattern)

Every controller serves both end-user and privileged/FKT routes:

```java
@RestController
@RequestMapping(value = {"v1", "v1/privileged"})
```

Or with domain-specific paths:
```java
@RequestMapping(path = {"v1/administrative-profiles", "v1/privileged/administrative-profiles"})
```

## 4.2 Path Conventions

- **Kebab-case** for all URL segments: `/person-contexts/{person-context-id}`
- **API versioning** in path: `/v1/`, `/api/v1/`
- **Path variables** use kebab-case: `{person-context-id}`, `{group-id}`
- **No trailing slashes**

## 4.3 Method Annotations Stack

```java
@RvoSecurity(permission = {RvoSecurityType.OWNER, RvoSecurityType.ADMIN})
@GetMapping(value = "/person-contexts/{person-context-id}", produces = MediaType.APPLICATION_JSON_VALUE)
@Operation(summary = "Get person context by ID")
@ApiResponses(value = {
    @ApiResponse(responseCode = "200", description = "Success"),
    @ApiResponse(responseCode = "403", description = "Forbidden"),
    @ApiResponse(responseCode = "404", description = "Not found")
})
@HistoryUseCase(useCase = "GETPC")
public ResponseEntity<PersonContextDto> getPersonContextById(
    @PathVariable("person-context-id") Long personContextId,
    @Parameter(hidden = true) Administrator administrator) {
    // ...
}
```

## 4.4 Response Patterns

| Style | When | Example |
|---|---|---|
| `ResponseEntity<T>` | MVC controllers | `ResponseEntity.ok(dto)` |
| `Mono<Void>` / `Mono<T>` | WebFlux controllers | Implements generated API interface |
| `ResponseEntity<Void>` | Mutations with no body | `ResponseEntity.status(HttpStatus.CREATED).build()` |

## 4.5 OpenAPI Code-Gen (WebFlux Services)

Server-side generation from `openapi.yaml`:
- Generator: `spring`, `interfaceOnly=true`
- Controllers implement the generated interface
- `reactive=true`, `responseWrapper=reactor.core.CorePublisher`
- `useResponseEntity=false`
- `useTags=true`

Client-side generation for upstream APIs:
- Generator: `java`, library: `webclient`
- Additional model annotations: `@lombok.Builder @lombok.AllArgsConstructor`

## 4.6 @RvoSecurity — Method-Level Authorization

```java
// Custom annotation — resolves Administrator from security context
@RvoSecurity
@RvoSecurity(permission = {RvoSecurityType.OWNER, RvoSecurityType.ADMIN, RvoSecurityType.ORG_UNIT_ADMIN})
```

`Administrator` object is injected into controller methods via the security framework:
```java
public ResponseEntity<Dto> getResource(
    @PathVariable("id") Long id,
    @Parameter(hidden = true) Administrator administrator) { ... }
```

## 4.7 Authentication Methods

| Method | Where |
|---|---|
| HTTP Basic Auth | All MVC services |
| OAuth2 JWT (Resource Server) | WebFlux services |
| LDAP-backed Basic Auth | User-management, access-admin |

## 4.8 FKT (Functional/Technical) Users

- Identified by `@fkt.datev.de` email suffix
- Access privileged endpoints (`/v1/privileged/`)
- Matched by patterns: `WSRVIN(1|2|3)@fkt.datev.de`

## 4.9 Custom AOP Authorization

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ValidateUser {}

@Aspect
@Component
public class ValidateUserAspect {
    @Before("@annotation(ValidateUser)")
    public void validateUser(JoinPoint joinPoint) {
        for (Object arg : joinPoint.getArgs()) {
            if (arg instanceof ProfileId profileId) {
                authorizationService.validateUser(profileId.getValue());
                return;
            }
        }
    }
}
```

## 4.10 Security Configuration (WebFlux)

```java
.pathMatchers(HttpMethod.POST, "/api/**").authenticated()
.pathMatchers(HttpMethod.DELETE, pattern).hasRole("INTERNAL_ADMIN")
.pathMatchers(AUTH_WHITELIST).permitAll()
.anyExchange().denyAll()
```

Security headers:
```java
.headers(headers -> {
    headers.contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'self'"));
    headers.hsts(hsts -> hsts.maxAgeInSeconds(31536000));
    headers.frameOptions(fo -> fo.mode(DENY));
})
```

CORS:
```java
.allowedOriginPatterns("*.datev.de", "http://localhost:*")
.allowCredentials(true)
```

## 4.11 Security Ant-Pattern Configuration

```yaml
rvo:
  security:
    ant-patterns:
      whitelist-role-anonymous: /actuator/health,/actuator/info
      whitelist-role-end-user: /v1/**
      whitelist-role-fkt-user: /v1/privileged/**
```

## 4.12 History/Audit Annotation

```java
@HistoryUseCase(useCase = "DELGRP")  // on mutating controller methods
@HistoryUseCase(useCase = "CopyP")
```

---

# PART 5: Persistence (DbAdapter, JPA, MongoDB)

## 5.1 The DbAdapter Pattern (MANDATORY)

**Services NEVER inject repositories directly.** Always wrap in a `*DbAdapter`:

```java
@Service
@Slf4j
@RequiredArgsConstructor
public class GroupDbAdapter {
    private final GroupRepository groupRepository;
    private final GroupMapper groupMapper;

    public List<GroupModel> getGroupsByServiceOrgId(UUID serviceOrgId) {
        return groupRepository
            .findGroupsByServiceOrgIdAndOrgUnitIdNotNull(serviceOrgId, PageRequest.of(0, MAX))
            .stream()
            .map(groupMapper::mapToModel)
            .collect(Collectors.toList());
    }
}
```

**Why:** The DbAdapter encapsulates repository access AND entity-to-model mapping.
Business services work with Models, never with Entities directly.

## 5.2 JPA Entity Conventions

```java
@Entity
@Table(name = "AZRGRUPPE", schema = "AVADMIN")
@SequenceGenerator(name = "group_generator", sequenceName = "SZRGRUPPE",
    schema = "SQ_NUK2", allocationSize = 1)
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Group implements Serializable {
    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "group_generator")
    @Column(name = "GRUPPENID", nullable = false, updatable = false)
    private Long id;

    @Column(name = "SERVICE_ORG_ID")
    private UUID serviceOrgId;

    @Column(name = "BESCHREIBUNG")
    private String description;
}
```

Rules:
- German column/table names (from mainframe heritage)
- Schema separation: `AVADMIN` for tables, `SQ_NUK2` for sequences
- `allocationSize = 1` always
- Custom converters for types: `UUIDConverter`, `BooleanConverter`
- Hibernate `Interceptor` for lifecycle events + history

## 5.3 Spring Data JPA Repositories

```java
@Transactional
@Repository
public interface GroupRepository extends JpaRepository<Group, Long> {
    Page<Group> findGroupsByServiceOrgIdAndOrgUnitIdNotNull(UUID serviceOrgId, PageRequest page);

    @Query("select new ...Projection(...) FROM Entity e WHERE ...")
    Optional<ProjectionDto> getByField(Long value);

    @Modifying
    @Query("update Entity e set e.field = :value WHERE e.id = :id")
    int updateField(@Param("id") Long id, @Param("value") String value);
}
```

## 5.4 MongoDB Patterns (Raw Driver — WebFlux)

**NOT Spring Data reactive repos.** Raw `MongoCollection<T>`:

```java
@Repository
@Slf4j
public class MasterDataRepository {
    private final MongoCollection<MasterData> masterDataCollection;

    public MasterDataRepository(MongoClient insertMongoClient,
                                @Value("${spring.data.mongodb.database}") String databaseName) {
        this.masterDataCollection = insertMongoClient
            .getDatabase(databaseName)
            .getCollection(MASTER_DATA, MasterData.class);
    }

    public Mono<DeleteResult> deleteOne(Integer consultant, Integer client, Integer fiscalYear) {
        return Mono.from(masterDataCollection.deleteOne(QueryUtil.getByBusinessKey(consultant, client, fiscalYear)))
                   .elapsed().map(LoggingUtil.logDebugWithDuration("Deleted masterData"));
    }
}
```

Rules:
- Two MongoClient beans: `insertMongoClient` (retryWrites=true) and `updateMongoClient` (retryWrites=false)
- Profile-based: `@Profile("cloud")` vs `@Profile("local")`
- Custom codecs (e.g., `OffsetDateTimeCodec`)
- Snake_case field naming strategy at driver level

## 5.5 MongoDB Document Models

```java
@Document(MASTER_DATA)   // constant from CollectionConstants
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor @EqualsAndHashCode @ToString
public class MasterData {
    private Integer consultant;
    private Integer client;
    private Integer fiscalYear;
    private MasterDataContext context;
    private List<CollectiveAccount> collectiveAccounts;
}
```

Collection name constants:
```java
@UtilityClass
public class CollectionConstants {
    public static final String MASTER_DATA = "masterData";
    public static final String STATE_DOC = "stateDoc";
    public static final String MOVEMENT_DATA_DAYS = "movementDataDays";
}
```

## 5.6 Three-Layer Data Flow

```
Entity (persistence/) ←→ Model (business/) ←→ DTO (presentation/)
  ↑ persistence/mapper        ↑ presentation/rest/mapper
```

Each layer has its own mapper interfaces. Models are the intermediate representation.
Business logic operates ONLY on Models, never on Entities or DTOs.

---

# PART 6: Object Mapping (MapStruct)

## 6.1 Standard MapStruct Interface

```java
@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.ERROR)
public interface GroupDtoMapper {
    GroupDto map(GroupModel source);

    @Mapping(target = "org.id", source = "orgId")
    @Mapping(target = "org.displayName", source = "workplaceName")
    GroupWithOrgDto mapToGroupWithDto(GroupModel source);
}
```

## 6.2 Rules

| Rule | Enforcement |
|---|---|
| `componentModel = "spring"` always | ArchUnit |
| `unmappedTargetPolicy = ReportingPolicy.ERROR` always | ArchUnit |
| Separate mapper per layer transition | Convention |
| Presentation mappers in `presentation/rest/mapper/` | Convention |
| Persistence mappers in `persistence/mapper/` | Convention |
| External mappers in `external/mapper/` | Convention |

## 6.3 Three-Layer Mapping Chain

```
Entity ←→ Model ←→ DTO
  ↑ persistence/mapper   ↑ presentation/rest/mapper
```

Each transition has its own mapper interface:
- `persistence/mapper/GroupMapper` — maps `GroupEntity` ↔ `GroupModel`
- `presentation/rest/mapper/GroupDtoMapper` — maps `GroupModel` ↔ `GroupDto`
- `external/mapper/OmUserModelMapper` — maps external DTOs ↔ internal Models

## 6.4 MapStruct in Version Catalog

```toml
[versions]
mapstruct = "1.6.3"

[libraries]
mapstruct = { module = "org.mapstruct:mapstruct", version.ref = "mapstruct" }
mapstruct-processor = { module = "org.mapstruct:mapstruct-processor", version.ref = "mapstruct" }
```

**Rule:** Pin annotation processor to the same version as the library.

---

# PART 7: Exception Handling (Rvo* Hierarchy)

## 7.1 Exception Hierarchy (MVC Services)

```
RuntimeException
└── RvoMainException (from base-component, has errorCode field)
    ├── RvoAccessException        → 403
    ├── RvoNotFoundException      → 404
    ├── RvoBadRequestException    → 400
    ├── RvoUnprocessableEntityException → 422
    ├── RvoConflictException      → 409
    └── RvoServerErrorException   → 500
```

**Rule:** All business exceptions extend from `RvoMainException`. Never throw raw `RuntimeException`.

## 7.2 Exception Hierarchy (WebFlux/Reactive Services)

```
RuntimeException
└── AggregationProcessingBaseException (abstract, has httpStatusCode)
    ├── AggregationProcessingBusinessException
    ├── HttpCallException (abstract)
    │   ├── HttpCallBusinessException
    │   ├── HttpCallTechnicalException
    │   └── HttpCallNoContentException
    └── InitialLoadFailedException
```

## 7.3 Global Exception Handler (MVC)

```java
@ControllerAdvice
@Slf4j
public class ExceptionMapper extends ResponseEntityExceptionHandler {

    @ExceptionHandler({RvoAccessException.class, RvoNotFoundException.class})
    public ResponseEntity<Void> mapForbiddenException(Throwable cause, HttpServletRequest req) {
        log.error("ExceptionMapper: ErrorCode: {}", extractErrorCode(cause), cause);
        return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
    }

    @ExceptionHandler({RvoBadRequestException.class, MethodArgumentTypeMismatchException.class})
    public ResponseEntity<ErrorDto> mapBadRequestException(Throwable cause, HttpServletRequest req) {
        String errorCode = "#RVOUMS" + HttpStatus.BAD_REQUEST.value();
        return ResponseEntity.badRequest().body(
            new ErrorDto(errorCode, cause.getMessage(), "", getRequestId(req)));
    }

    @ExceptionHandler({RvoConflictException.class})
    public ResponseEntity<ErrorDto> mapConflictExceptions(Throwable cause, HttpServletRequest req) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(
            new ErrorDto("#RVOUMS409", cause.getMessage(), "", getRequestId(req)));
    }
}
```

## 7.4 ErrorDto Pattern

```java
public class ErrorDto {
    private String error;            // "#RVOUMS400"
    private String errorDescription; // Human-readable message
    private String errorUri;         // Reference documentation (usually empty)
    private String requestId;        // From DATEV_REQUEST_ID header
}
```

## 7.5 WebFlux Exception Handler (RFC 7807)

```java
@RestControllerAdvice
@Slf4j
public class RestExceptionHandler {
    @ExceptionHandler(AggregationProcessingBusinessException.class)
    public ResponseEntity<Problem> handleBusinessException(AggregationProcessingBusinessException e) {
        return ResponseEntity.status(e.getHttpStatusCode())
            .body(Problem.create()
                .withTitle("Business Error")
                .withDetail(Vk3MaskingUtil.maskMessage(e.getMessage(), WHITELIST)));
    }
}
```

## 7.6 VK3 Data Masking in Errors

Sensitive financial data (Verarbeitungskennzeichen 3) must be masked before appearing in error responses or logs:
```java
Vk3MaskingUtil.maskMessage(e.getMessage(), ExceptionUtil.JAVA_FIELDS_WHITELIST)
```

## 7.7 Rules

- All exceptions are **unchecked** (extend `RuntimeException`)
- Never use checked exceptions
- Every `@ControllerAdvice` must handle ALL `Rvo*Exception` subtypes
- Error responses include `requestId` from `DATEV_REQUEST_ID` header
- Log the full stack trace at ERROR level in the exception handler
- Mask VK3 fields before including in error response bodies

---

# PART 8: External Communication (Feign, WebClient, Kafka)

## 8.1 Spring Cloud OpenFeign (MVC Services)

```java
@FeignClient(name = "om-backend-service",
    url = "${rvo.external.url-om-backend}",
    configuration = PropagationConfiguration.class)
public interface OmBackendService {
    @GetMapping(value = "/v1/users/{user-id}", produces = MediaType.APPLICATION_JSON_VALUE)
    OmUserDto getUserById(@PathVariable("user-id") Long userId,
                          @RequestHeader("x-rvo-service-user-id") String serviceUserId);
}
```

## 8.2 Adapter Wrapping Feign Clients

```java
@Component
@RequiredArgsConstructor
@Slf4j
public class OmAdapter {
    private final OmBackendService omBackendService;
    private final OmBackendRequestScopedCache cache;
    private final OmUserModelMapper mapper;

    @Memorize  // request-scoped caching
    public OmUserModel getUserById(Long userId, String serviceUserId) {
        OmUserDto dto = omBackendService.getUserById(userId, serviceUserId);
        return mapper.mapToModel(dto);
    }
}
```

**Rule:** External Adapters always map external DTOs to internal Models before returning.

## 8.3 Request-Scoped Caching

```java
@Component
@RequestScope
public class OmBackendRequestScopedCache {
    private final Map<Long, OmUserDto> userCache = new HashMap<>();

    public OmUserDto getOrFetch(Long userId, Supplier<OmUserDto> fetcher) {
        return userCache.computeIfAbsent(userId, id -> fetcher.get());
    }
}
```

## 8.4 WebClient-Based Clients (WebFlux)

```java
@Component
@Slf4j
public class MasterDataClient {
    private final MasterdataContextApi masterdataContextApi;

    public Mono<MasterdataContext> getMasterdataContext(Integer consultant, Integer client, Integer fiscalYear) {
        return Mono.deferContextual(ctx ->
            masterdataContextApi.getMasterdataContext(consultant, client, fiscalYear,
                ctx.get(LoggingUtil.CORRELATION_ID_KEY)));
    }
}
```

## 8.5 Kafka Event Producer (WebFlux — ReactiveKafkaProducerTemplate)

```java
public interface ChangeEventProducer {
    Mono<Void> publishChangedEvent(ChangedEventDto eventDto);
}

@Component
@Slf4j
@RequiredArgsConstructor
@ConditionalOnProperty(value = "kafka-config.enabled", havingValue = "true")
public class ChangeEventProducerImpl implements ChangeEventProducer {
    private final ReactiveKafkaProducerTemplate<String, String> producerTemplate;
    private final ObjectMapper objectMapper;

    @Override
    public Mono<Void> publishChangedEvent(ChangedEventDto eventDto) {
        String json = objectMapper.writeValueAsString(eventDto);
        return producerTemplate.send(topicName, key, json)
            .doOnSuccess(r -> log.info("Event published: {}", key))
            .onErrorResume(e -> { log.error("Failed to publish", e); return Mono.empty(); })
            .then();
    }
}
```

## 8.6 Mock Producer for Non-Kafka Environments

```java
@Component
@Slf4j
@ConditionalOnProperty(value = "kafka-config.enabled", havingValue = "false", matchIfMissing = true)
public class ChangeEventProducerMock implements ChangeEventProducer {
    @Override
    public Mono<Void> publishChangedEvent(ChangedEventDto eventDto) {
        log.info("Mock: would publish event {}", eventDto);
        return Mono.empty();
    }
}
```

## 8.7 Event-Driven Process Orchestration (MVC)

```java
// Custom DATEV event-client framework
@EventMethod(process = 1107, state = 1)
public void handleR4cEvent(Event event) {
    // Process event, then trigger next state:
    eventProducer.createNextEvent(event, nextState, payload);
}
```

## 8.8 Event Retry (MongoDB-backed)

- Failed events stored in `R4cRetryEventEntity` (MongoDB)
- `@Scheduled` with `@SchedulerLock` (ShedLock) polls for retries
- Configurable delay: `rvo-r4c-retry.fixedDelay: 10000`

## 8.9 Spring ApplicationEvents (Internal Pub/Sub)

```java
// Publishing
applicationEventPublisher.publishEvent(new CopyProductPermissionEvent(this, event));

// Handling
@Async
@EventListener
public void handleLifecycleEvent(InternalLifeCycleEvent event) {
    kafkaSender.send(event.toKafkaMessage());
}
```

## 8.10 Resilience4j Configuration

```yaml
resilience4j:
  circuitbreaker:
    instances:
      masterDataCircuitBreaker:
        slidingWindowSize: 10
        failureRateThreshold: 50
        waitDurationInOpenState: 30s
  retry:
    instances:
      http-client-retry:
        maxAttempts: 3
        waitDuration: 500ms
        exponentialBackoffMultiplier: 2
      mongodb-retry:
        maxAttempts: 3
        waitDuration: 100ms
```

## 8.11 Circuit Breaker + Retry (Order Matters)

```java
return webClientCall
    .transformDeferred(RetryOperator.of(retryInstance))         // retry FIRST
    .transformDeferred(CircuitBreakerOperator.of(circuitBreaker)); // CB wraps retry
```

---

# PART 9: Configuration & Infrastructure

## 9.1 Application Properties Namespace

```yaml
# Custom namespace per service
ref-sys:
  client:
    acds:
      base-path: ${vcap.services.refsys-acds.credentials.uri}
      client-id: ${vcap.services.refsys-acds.credentials.clientId}
  circuitbreaker-enabled: false
  mongodb:
    max-idle-time-in-ms: 10000
    min-pool-size: 5
    max-pool-size: 50

rvo:
  external:
    url-user-management: ${vcap.services.rvo-url-provider.credentials.url-user-management-service}
  security:
    ant-patterns:
      whitelist-role-anonymous: /actuator/health,/actuator/info
      whitelist-role-end-user: /v1/**
      whitelist-role-fkt-user: /v1/privileged/**
```

## 9.2 Cloud Foundry VCAP Services

External service credentials come from VCAP:
```yaml
${vcap.services.{service-name}.credentials.{key}}
```

**Rule:** Never hardcode URLs or credentials. Always resolve from VCAP or environment variables.

## 9.3 Profile Strategy

| Profile | Purpose |
|---|---|
| `default` | Local development (H2/embedded Mongo) |
| `cloud` / `cloudfoundry` | Cloud Foundry deployment |
| `test` | Unit/integration tests |
| `test-it` | Full integration test environment |
| `h2_inmemory` | In-memory database |
| `postgres` | PostgreSQL |
| `db2_cloud` | DB2 production |
| `eventclient` | Enable Kafka |
| `swagger` | Enable Swagger UI |
| `local` | Local MongoDB |
| `security-test` | Enable security in tests |

## 9.4 @ConfigurationProperties Pattern

```java
@Setter
@Getter
@Component
@ConfigurationProperties(prefix = "refsys.initial-load")
public class InitialLoadConfiguration {
    private Integer maxImportDurationInMs;
    private Integer parkingTimeInMs;
    private Integer inventoriesBufferSize;
    private Integer accountSumDaysBufferSize;
}
```

## 9.5 Conditional Activation

```java
@ConditionalOnProperty(value = "kafka-config.enabled", havingValue = "true")
@Profile(ProfileConstants.CLOUD_PROFILE)
```

## 9.6 Logging — Standard Setup

- SLF4J + Logback everywhere
- `@Slf4j` (Lombok) on every class that logs
- logback-spring.xml with profile-specific appenders

## 9.7 Structured Logging Context

WebFlux — Reactor Context propagation:
```java
@Component
public class LoggingContextFilter implements WebFilter {
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        // Extract: consultant, client, fiscalYear, correlationId, requestId
        return chain.filter(exchange)
            .contextWrite(ctx -> ctx.put("correlationId", correlationId));
    }
}
```

MVC — MDC via headers:
```java
MDC.put("requestId", request.getHeader("DATEV_REQUEST_ID"));
```

## 9.8 Splunk-Optimized Markers

```java
private static final Marker MARKER = MarkerFactory.getMarker("REFSYS_SPLUNK_MARKER");
log.info(MARKER, "Initial load completed for consultant={}", consultant);
```

## 9.9 Timed Operations (Reactive)

```java
return mongoOperation
    .elapsed()
    .map(LoggingUtil.logDebugWithDuration("MongoDB upsert masterData"));
```

## 9.10 VK3 Masking in Logs

Custom Logback `PatternLayout` masks sensitive accounting fields:
```java
public class MaskingPatternLayout extends PatternLayout {
    // Masks patterns matching VK3 fields (account numbers, amounts, tax IDs)
}
```

## 9.11 Constant-Based Log Messages

```java
public static final String INITIAL_LOAD_START_LOG = "Starting initial load for consultant={}";
public static final String INITIAL_LOAD_RESPONSE_LOG = "Initial load completed in {}ms";
```

## 9.12 Error Logging with Error Codes

```java
log.error("ExceptionMapper: ErrorCode: {}", errorCode, cause);
log.warn("user has no admin permission for serviceOrg={}", serviceOrgId, ex);
```

## 9.13 Cloud Foundry Manifest

```yaml
applications:
  - name: service-name
    memory: 1G
    instances: 2
    buildpack: java_buildpack_offline
    path: target/service-name.jar
    env:
      JBP_CONFIG_OPEN_JDK_JRE: '{ jre: { version: 25.+ } }'
      JAVA_OPTS: '-Dfile.encoding=UTF-8'
      SPRING_PROFILES_ACTIVE: cloud,eventclient
    services:
      - rvo-url-provider
      - rvo-db2-credentials
      - access-administration-fkt-credhub
```

## 9.14 Health & Observability

- Spring Boot Actuator (`/actuator/health`, `/actuator/info`)
- OpenTelemetry OTLP exporter for distributed tracing
- Custom Micrometer metrics (`.tap(Micrometer.metrics(...))`)
- Splunk-compatible log format

Micrometer metrics tap (reactive):
```java
return operation
    .name(MetricConstants.METRIC_MONGO)
    .tag(MetricConstants.REPOSITORY, "masterData")
    .tag(MetricConstants.METHOD, "upsertOne")
    .tag(MetricConstants.METRIC_TYPE, MetricConstants.METRIC_WRITE)
    .tap(Micrometer.metrics(meterRegistry));
```

## 9.15 Distributed Scheduling (ShedLock)

```java
@Scheduled(fixedDelayString = "${rvo-r4c-retry.fixedDelay:10000}")
@SchedulerLock(name = "Scheduler_lock_Retry",
    lockAtLeastFor = "${rvo-r4c-retry.lockAtLeast:PT5S}",
    lockAtMostFor = "${rvo-r4c-retry.lockAtMost:PT30S}")
void retry() { ... }
```

## 9.16 Build Tool

| Context | Use |
|---|---|
| New migration output | Gradle (`build.gradle.kts`) with version catalog |
| Existing DATEV services staying on Maven | Keep Maven — don't migrate build tool |

## 9.17 CI/CD

- Jenkins (`Jenkinsfile`, `Jenkinsfile-ReleaseDeploy`)
- DATEV CI (`.datev-ci.yaml`)
- GitLab (`.gitlab/issue_templates/`)
- Renovate (`renovate.json`) for dependency updates
- Gitleaks (`gitleaks.toml`) for secret scanning

---

# PART 10: Testing (JUnit 5 + AssertJ + German Cucumber + ArchUnit + WireMock)

## 10.1 Test Classification

| Suffix | Type | Framework |
|---|---|---|
| `*Test.java` | Unit test | JUnit 5 + Mockito |
| `*IT.java` | Integration test | Spring Boot Test |
| `*SecurityIT.java` | Security integration | Spring Security Test |
| `*Spec.groovy` | Unit test (alt) | Groovy Spock |
| `RunCucumberTest.java` | BDD runner | Cucumber |
| `ArchitectureTest.java` | Architecture | ArchUnit |

## 10.2 Unit Test Pattern

```java
@ExtendWith(MockitoExtension.class)
class GroupServiceTest {
    @InjectMocks GroupService groupService;
    @Mock GroupDbAdapter groupDbAdapter;
    @Mock OmAdapter omAdapter;

    @Test
    @DisplayName("should return groups from serviceOrg for admin")
    void shouldReturnGroupsFromServiceOrgIdForAdmin() {
        // given
        when(groupDbAdapter.getGroupsByServiceOrgId(serviceOrgId)).thenReturn(groupList);

        // when
        var result = groupService.getGroupsByAdmin(adminModel);

        // then
        assertThat(result).containsExactlyInAnyOrder(groupModel1, groupModel2);
    }
}
```

## 10.3 Test Method Naming

```java
// Pattern: should_<expected>_when_<condition>
void should_return_500_when_unexpected_exception_is_thrown()
void should_return_groups_from_serviceOrg_for_admin()

// Or camelCase with @DisplayName:
@DisplayName("should return groups from serviceOrg for admin")
void shouldReturnGroupsFromServiceOrgIdForAdmin()
```

Both styles are acceptable. Be consistent within a file.

## 10.4 WebFlux Controller Tests

```java
@WebFluxTest(InitialLoadController.class)
@ContextConfiguration(classes = {TestResilienceConfiguration.class})
@ActiveProfiles("test")
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class InitialLoadControllerTest {
    private WebTestClient webTestClient;
    @Autowired private ApplicationContext context;
    @MockitoBean private CommonImportService commonImportService;

    @BeforeEach
    void setUp() {
        webTestClient = WebTestClient.bindToApplicationContext(context)
            .configureClient().baseUrl("/api/v1").build();
    }
}
```

## 10.5 Integration Tests (Spring Boot)

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfiguration.class)
@ContextConfiguration(initializers = TestApplicationInitializer.class,
    classes = {WireMockTestConfiguration.class})
@ClearDatabaseAnCreateIndexesBeforeEachTest  // Custom annotation
@AutoConfigureWebTestClient
@ActiveProfiles("test")
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class InitialLoadControllerIT { ... }
```

## 10.6 German-Language Cucumber BDD

```gherkin
#language:de
Funktionalität: Gruppen verwalten

  Szenario: Gruppe erfolgreich erstellen
    Gegeben seien die Testdaten der Mongo-DB aus dem Ordner "groups_create"
    Angenommen der angemeldete Benutzer ist ein Admin
    Wenn ich eine neue Gruppe mit dem Namen "Testgruppe" erstelle
    Dann erhalte ich den Statuscode 201
    Und die Gruppe existiert in der Datenbank
```

Cucumber configuration:
```java
@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
@ConfigurationParameters({
    @ConfigurationParameter(key = GLUE_PROPERTY_NAME,
        value = "de.datev.rvo.usermanagementservice.cucumber"),
    @ConfigurationParameter(key = FILTER_TAGS_PROPERTY_NAME, value = "not @Disabled")
})
public class CucumberTest {}
```

## 10.7 ArchUnit Enforcement

```java
@AnalyzeClasses(packages = "de.datev.rvo.usermanagementservice",
    importOptions = {ImportOption.DoNotIncludeTests.class})
class ArchitectureTest {
    @ArchTest
    ArchTests allArchTests = ArchTests.in(AllRules.class);
}
```

Standard rules enforced:
1. Persistence layer only accessed through adapter classes
2. Controllers named with `Controller` suffix
3. Database classes only in persistence layer
4. Layer dependencies respected (presentation → business → persistence/external)
5. MapStruct mappers use Spring injection
6. MapStruct reports unmapped targets as errors
7. Controllers reside in `presentation.rest` package

## 10.8 Model toString Tests (Library Pattern)

```java
@Slf4j
class MasterDataTest {
    private EasyRandom easyRandom;

    @BeforeEach
    void setUp() {
        easyRandom = new EasyRandom();
    }

    @Test
    @DisplayName("toString should include all attributes")
    void should_log_all_attributes_when_to_string_is_called() {
        MasterData testObject = easyRandom.nextObject(MasterData.class);
        log.info(testObject.toString());
        assertToString(memoryAppender, testObject); // reflection-based assertion
    }
}
```

## 10.9 WireMock Stubs Organization

```
src/test/resources/wiremock-mappings/
├── feature-file-exclusive/
│   ├── groups_create/          ← stubs for specific Cucumber feature
│   └── person_context_get/
└── fallback/                    ← default stubs (130+ files)
    ├── om_business_mapping/
    ├── personality/
    └── media-administration/
```

## 10.10 Coverage Requirements

| Layer | Line | Branch | Mutation |
|-------|------|--------|----------|
| business/ | 95% | 90% | 70% |
| presentation/ | 90% | 85% | 60% |
| persistence/ (DbAdapters) | 80% | 75% | — |
| external/ (Adapters) | 75% | 70% | — |

## 10.11 Testing Rules

- Business-layer tests: Mock DbAdapters and external Adapters. Verify business logic.
- Persistence tests: Use Testcontainers. Verify actual queries against real database.
- One test file per production class.
- Every public method has at least one test.
- No test without at least one assertion.

---

# PART 11: Naming & Domain Language

## 11.1 Class Naming Conventions

| Suffix | Layer | Purpose | Example |
|---|---|---|---|
| `Controller` | presentation | REST endpoints | `GroupController`, `InitialLoadController` |
| `Service` | business | Business logic (concrete or interface) | `GroupService`, `ImportService` |
| `ServiceImpl` | business | Implementation of service interface | `ImportServiceImpl` |
| `DbAdapter` | persistence | Wraps repository + entity mapping | `GroupDbAdapter`, `PersonContextDbAdapter` |
| `Adapter` | external | Wraps Feign/WebClient calls | `OmAdapter`, `GatewayAdapter` |
| `Repository` | persistence | Spring Data JPA/Mongo interface | `GroupRepository`, `MasterDataRepository` |
| `Entity` | persistence | JPA entity (optional suffix) | `PersonProfileEntity` |
| `Mapper` | any | MapStruct interface | `GroupDtoMapper`, `PersonContextMapper` |
| `Configuration` | infrastructure | Spring `@Configuration` | `WebSecurityConfiguration` |
| `Constants` | any | Static final constants class | `MetricConstants`, `ProfileConstants` |
| `Dto` | presentation/external | Data transfer object | `GroupDto`, `ChangedEventDto` |
| `Model` | business | Business layer value object | `AdminModel`, `GroupModel` |
| `Exception` | any | Custom exception | `RvoConflictException` |
| `Util` | any | Stateless utility | `LoggingUtil`, `QueryUtil` |
| `Filter` | presentation | WebFilter / Servlet filter | `LoggingContextFilter` |
| `Validator` | business | Validation logic | `GroupValidator` |
| `Check` | business | Authorization check | `GroupAdminCheck` |
| `Client` | external | HTTP client (WebFlux) | `MasterDataClient` |
| `Predicate` | any | Conditional logic (Resilience4j) | `HttpCallRetryExceptionPredicate` |
| `Command` | business | Command pattern object | `AddClassifierCommand` |
| `EventHandlerAdapter` | presentation | Kafka event handler | `R4CEventHandlerAdapter` |

## 11.2 German Domain Terminology (Preserved in Code)

German business domain terms are preserved — never anglicize them:

| German | Context |
|---|---|
| `Berater` / `consultant` | Tax consultant (Steuerberater) |
| `Mandant` / `client` | Client of the consultant |
| `Wirtschaftsjahr` / `fiscalYear` | Fiscal year |
| `Personengruppe` | Person group |
| `Auswertung` | Evaluation/Report |
| `Kennziffer` | Key figure/indicator |
| `Gesellschafter` | Shareholder |
| `Buchungssatz` | Booking entry |
| `Bilanz` | Balance sheet |
| `GuV` | Profit & Loss (Gewinn- und Verlustrechnung) |
| `Anlagespiegel` | Asset schedule |
| `Kontennachweis` | Account proof |
| `Stammdaten` | Master data |
| `Bewegungsdaten` | Movement/transaction data |

## 11.3 Field Naming by Context

| Context | Convention | Example |
|---|---|---|
| Package names | English | `presentation`, `business`, `persistence`, `external` |
| Class names | Mix — German for domain concepts, English for technical | `Auswertung`, `Controller`, `Service` |
| Java field names | camelCase (English with German domain terms where no clear English equivalent exists) | `fiscalYear`, `consultant`, `personContextId` |
| Database columns | German uppercase (mainframe heritage) | `BESCHREIBUNG`, `GRUPPENID`, `PERSONCONTEXT_ID` |
| REST paths | English kebab-case | `/person-contexts/`, `/groups/` |
| JSON fields | snake_case via `@JsonProperty` | `display_name`, `service_org_id` |
| MongoDB fields | snake_case (naming strategy) | `fiscal_year`, `consultant` |
| Cucumber features | German | `Funktionalität`, `Szenario`, `Gegeben`, `Wenn`, `Dann` |
| Log messages | English | `"Initial load completed for consultant={}"` |
| Comments | Prefer English for new code | — |

---

# PART 12: Code Quality & Anti-Patterns

## 12.1 Code Quality Constraints

| Metric | Maximum | Action if Violated |
|--------|---------|-------------------|
| Cyclomatic complexity per method | 10 | Extract helper methods or decompose |
| Lines per class (excl. imports) | 200 | Split into focused classes |
| Lines per method | 30 | Extract to private methods or new class |
| Dependencies per constructor | 4 | Split the use case / service |
| Package depth | 4 | Flatten or introduce module |

## 12.2 Architecture Anti-Patterns

- Controller injecting DbAdapter or Repository directly → **ALWAYS WRONG** (must go through Service)
- Service injecting Repository directly → **ALWAYS WRONG** (must go through DbAdapter)
- Circular dependency between packages → break with interface extraction
- Business layer importing presentation types → wrong direction
- Persistence layer importing presentation types → wrong direction

## 12.3 Domain/Layer Violations

- `import org.springframework.web.*` inside `business/` → **ALWAYS WRONG**
- `import jakarta.persistence.*` inside `business/` → **ALWAYS WRONG** (persistence annotations stay in persistence layer)
- Business class with `@RestController`, `@GetMapping` → move to presentation
- Business class with `@Entity`, `@Table` → move to persistence

## 12.4 Code Smell Violations

- `@Autowired` on a field → constructor injection only (`@RequiredArgsConstructor`)
- `null` returned from public method → use `Optional<T>`
- `catch (Exception e)` → catch specific exception types
- `.get()` on Optional without guard → `orElseThrow()`
- `new` for a dependency inside a method → inject it
- `System.out.println()` → `@Slf4j` logger
- Mutable DTO class without Lombok → use Lombok annotations
- Static utility class without `@UtilityClass` → add `@UtilityClass`
- `ThreadLocal` for context → `ScopedValue` (Java 25)
- Hardcoded version in build.gradle.kts → version catalog
- `@Data` in a library model project → use the 7-annotation combo
- Checked exceptions → use unchecked (`Rvo*Exception` hierarchy)
- Primitive types (`int`, `long`, `boolean`) in domain models → use wrapper types

## 12.5 What NOT to Include (Banned Patterns)

| Banned | Use Instead |
|---|---|
| `@Data` in library model projects | `@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor @EqualsAndHashCode @ToString` |
| Bean Validation annotations in shared model JARs | Validate in the service layer |
| Jackson annotations in shared model JARs | Keep transport concerns in service DTOs |
| Direct repository injection into services | `*DbAdapter` pattern |
| Primitive types in domain models | Wrapper types (`Integer`, `Long`, `Boolean`) |
| English-only domain naming | Preserve German business terms |
| `@Autowired` field injection | `@RequiredArgsConstructor` + `private final` |
| Checked exceptions | Unchecked `Rvo*Exception` hierarchy |
| `float` / `double` for financial data | `Long` (minor units) or `BigDecimal` |
| `java.util.Date` / Joda-Time | `java.time.*` (`OffsetDateTime`, `LocalDate`) |
| `ThreadLocal` | `ScopedValue` (Java 25) |
| ModelMapper | MapStruct |
| Gson / org.json | Jackson |
| JUnit 4 / Hamcrest | JUnit 5 + AssertJ |
| Log4j direct | SLF4J |
| JNI | Foreign Function & Memory API |
| Open version ranges (`+`, `latest.release`) | Pinned versions in catalog |

## 12.6 Output-Type Cross-Contamination

- Library producing `presentation/rest/` code → wrong output type
- CLI with `@RestController` → wrong output type
- Service without `application.yml` → incomplete
- SDK without Javadoc on public API → incomplete
- Library with `spring-boot-starter-*` in `implementation()` → use `compileOnly`

---

# PART 13: Reactive Patterns (WebFlux Services)

> This section applies ONLY to WebFlux-based services. MVC services use standard
> synchronous patterns with virtual threads.

## 13.1 Interface + Impl for All Services

```java
public interface ImportService {
    Mono<Void> doFullImport(Integer consultant, Integer client, Integer fiscalYear);
}

@Service
@Slf4j
public class ImportServiceImpl extends CommonService implements ImportService {
    @Override
    public Mono<Void> doFullImport(Integer consultant, Integer client, Integer fiscalYear) {
        return // ...
    }
}
```

## 13.2 Timed Operations with .elapsed()

```java
return mongoOperation
    .elapsed()
    .map(LoggingUtil.logInfoWithDuration("Operation completed"));
```

## 13.3 Context Propagation for Logging

```java
return chain.filter(exchange)
    .contextWrite(LoggingUtil.createInitialContext(loggingContext, correlationId));

// Accessing context downstream:
return Mono.deferContextual(ctx -> {
    String corrId = ctx.get(LoggingUtil.CORRELATION_ID_KEY);
    return apiClient.call(corrId);
});
```

## 13.4 Buffering + Controlled Concurrency

```java
return flux
    .buffer(configuration.getBufferSize())
    .flatMap(batch -> bulkUpsert(batch), MAX_CONCURRENCY, MAX_PREFETCH);
```

## 13.5 Parallel Independent Operations

```java
return Flux.merge(
    insertMovementDataDays(dayData),
    insertMovementDataMonths(monthData),
    importMasterData(masterDataContext),
    importMasterDataAccounts(accounts)
);
```

## 13.6 Fire-and-Forget Pattern

```java
return service.doFireAndForgetFullImport(params)
    .thenReturn(true)
    .elapsed().map(LoggingUtil.logInfoWithDuration("Full import"))
    .then();
```

---

# Appendix A: Dependency Management

## A.1 Version Catalog (MANDATORY)

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

## A.2 Service Dependencies

| Category | Artifact |
|---|---|
| Web | `spring-boot-starter-web` OR `spring-boot-starter-webflux` |
| Persistence | `spring-boot-starter-data-jpa` and/or `spring-boot-starter-data-mongodb` |
| External calls | `spring-cloud-starter-openfeign` (MVC) or OpenAPI-generated WebClient (WebFlux) |
| Messaging | Custom `event-client` (Kafka) |
| Security | `rrmo-security-component`, `spring-security-datev-claims-starter` |
| Mapping | `mapstruct`, `lombok` |
| Resilience | `resilience4j-spring-boot3` (WebFlux) |
| Scheduling | `shedlock-spring` + `shedlock-provider-mongo` |
| API Docs | `springdoc-openapi-starter-webmvc-ui` |
| Observability | `spring-boot-starter-actuator`, OpenTelemetry |
| History | `history-component` (DATEV internal) |
| JSON | Jackson (via Spring Boot starter) |
| Date/Time | `java.time.*` (built-in) |
| Logging | SLF4J (via Spring Boot starter) |

## A.3 Library Dependencies

| Category | Artifact |
|---|---|
| Code gen | `lombok` |
| MongoDB mapping | `spring-data-mongodb` (for `@Document` only) |
| Testing | `junit-jupiter`, `assertj-core`, `easy-random-core`, `reflections` |

## A.4 Test Dependencies

| Category | Artifact |
|---|---|
| Unit | `junit-jupiter`, `mockito-core`, `assertj-core` |
| BDD | `cucumber-java`, `cucumber-spring`, `cucumber-junit-platform-engine` |
| Integration | `spring-boot-starter-test`, `testcontainers` |
| Mocking | `spring-cloud-contract-wiremock` |
| Architecture | `archunit-junit5`, `datev.rvo:archunit-rules` |
| Kafka | `spring-kafka-test` (`@EmbeddedKafka`) |
| Async | `awaitility` |
| Data gen | `easy-random-core`, `instancio-junit` |
| Contracts | `pact-jvm-consumer-junit5` |
| Alternative | `spock-core`, `spock-spring` (Groovy) |

## A.5 Dependency Choice Rules

| Need | Use | NOT |
|------|-----|-----|
| Object mapping | MapStruct | ModelMapper, manual |
| JSON | Jackson | Gson, org.json |
| Date/Time | java.time.* | java.util.Date, Joda-Time |
| Logging | SLF4J | System.out, Log4j direct |
| Testing | JUnit 5 + AssertJ + Mockito | JUnit 4, Hamcrest |
| Thread context | ScopedValue (Java 25) | ThreadLocal |
| Native interop | Foreign Function & Memory API | JNI |
| HTTP clients (MVC) | Spring Cloud OpenFeign | RestTemplate, manual HttpClient |
| HTTP clients (WebFlux) | WebClient (generated) | RestTemplate, Feign |
| Resilience | Resilience4j | Hystrix, manual retry |
| Scheduling | ShedLock | Quartz (unless complex scheduling needed) |

---

# Appendix B: ArchUnit Rules Template

```java
@AnalyzeClasses(packages = "de.datev.rvo.{service}",
    importOptions = {ImportOption.DoNotIncludeTests.class})
class ArchitectureTest {

    @ArchTest
    static final ArchRule persistence_accessed_only_through_adapters =
        noClasses().that().resideInAPackage("..business..")
            .should().dependOnClassesThat().resideInAPackage("..persistence.repository..");

    @ArchTest
    static final ArchRule controllers_in_presentation =
        classes().that().haveSimpleNameEndingWith("Controller")
            .should().resideInAPackage("..presentation.rest..");

    @ArchTest
    static final ArchRule database_classes_in_persistence =
        classes().that().areAnnotatedWith(Entity.class)
            .should().resideInAPackage("..persistence.entity..");

    @ArchTest
    static final ArchRule layer_dependencies =
        layeredArchitecture().consideringOnlyDependenciesInLayers()
            .layer("Presentation").definedBy("..presentation..")
            .layer("Business").definedBy("..business..")
            .layer("Persistence").definedBy("..persistence..")
            .layer("External").definedBy("..external..")
            .whereLayer("Presentation").mayNotBeAccessedByAnyLayer()
            .whereLayer("Business").mayOnlyBeAccessedByLayers("Presentation")
            .whereLayer("Persistence").mayOnlyBeAccessedByLayers("Business")
            .whereLayer("External").mayOnlyBeAccessedByLayers("Business");

    @ArchTest
    static final ArchRule mappers_use_spring_injection =
        classes().that().haveSimpleNameEndingWith("Mapper")
            .and().areInterfaces()
            .should().beAnnotatedWith(Mapper.class);

    @ArchTest
    static final ArchRule mappers_report_unmapped_errors =
        classes().that().areAnnotatedWith(Mapper.class)
            .should().beAnnotatedWith(
                Mapper.class); // verified via unmappedTargetPolicy=ERROR in annotation
}
```

---

# Appendix C: Quick Reference Card

| Decision | Standard |
|---|---|
| Package layout (service) | `presentation/business/persistence/external` |
| Package layout (reactive service) | `boundry/service/repository/client/config` |
| Package layout (library) | `api/internal/spi` with `module-info.java` |
| Repo access | Through `*DbAdapter` only — never direct |
| DI style | `@RequiredArgsConstructor` + `private final` fields |
| Model annotations (library) | `@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor @EqualsAndHashCode @ToString` |
| Model annotations (service DTO) | `@Data @NoArgsConstructor @AllArgsConstructor @SuperBuilder` |
| Mapping | MapStruct, `componentModel="spring"`, `unmappedTargetPolicy=ERROR` |
| Exceptions | `Rvo*Exception` hierarchy → `@ControllerAdvice` ExceptionMapper |
| REST paths | Kebab-case, dual-mapping (`v1` + `v1/privileged`) |
| Security | `@RvoSecurity` on methods, `Administrator` injected |
| Tests | JUnit 5 + AssertJ + German Cucumber + ArchUnit + WireMock |
| Logging | `@Slf4j`, structured MDC, VK3 masking, Splunk markers |
| Nullability | Wrapper types, no annotations, null-safe arithmetic |
| German terms | Preserved in domain model — never anglicize |
| Field naming (DB) | German uppercase (`BESCHREIBUNG`, `GRUPPENID`) |
| Field naming (Java) | camelCase |
| Field naming (JSON) | snake_case via `@JsonProperty` |
| Field naming (MongoDB) | snake_case (naming strategy) |
| Service pattern (MVC) | Concrete service classes |
| Service pattern (WebFlux) | Interface + Impl |
| Build tool (new projects) | Gradle + version catalog |
| Deployment | Cloud Foundry |
| CI | Jenkins / DATEV CI / GitLab |

---

## Output Type Profiles

The output-type-specific standards are in separate steering files that auto-load
based on your migration context:

- `java-service-profile.md` — Spring Boot 4.x deployable (REST/gRPC/messaging)
- `java-library-profile.md` — Plain JAR consumed by other projects
- `java-sdk-profile.md` — Published library with docs + stability guarantees
- `java-cli-profile.md` — Command-line tool with argument parsing

These files use `inclusion: auto` and are loaded when relevant to your current task.
