# DATEV Java Conventions

> Extracted from DATEV reference codebases (Templates A–D) and calibrated against
> our migration framework output. These conventions override generic framework defaults
> when generating Java code for DATEV projects.

---

## Applicability

| Project Type | Applies |
|---|---|
| Spring Boot Service (MVC or WebFlux) | ✓ Full |
| Library JAR (no Spring) | ✓ Sections marked "Library" |
| Migration output (C++ → Java) | ✓ Complement framework defaults |

---

## 1. Package Structure & Layering

### 1.1 Services — Four-Layer Architecture

All DATEV Spring Boot services use a consistent 4-layer package layout:

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

### 1.2 Reactive Services (WebFlux) — Flat Package Variant

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

### 1.3 Library JARs — API/Internal/SPI Layering

```
de.datev.{org}.{library-name}/
├── api/                       ← Public API (exported via module-info.java)
├── spi/                       ← Extension points consumers implement (exported)
└── internal/                  ← Hidden implementation (NOT exported)
    ├── model/
    ├── basis/
    └── {domain-specific packages}
```

### 1.4 Rules

| Rule | Enforcement |
|---|---|
| Persistence layer accessed ONLY through `*DbAdapter` classes | ArchUnit |
| Controllers reside in `presentation/rest/` | ArchUnit |
| Controller names end with `Controller` | ArchUnit |
| Database entities/repos only in `persistence/` | ArchUnit |
| MapStruct mappers use Spring injection | ArchUnit |
| MapStruct mappers use `unmappedTargetPolicy = ERROR` | ArchUnit |
| Layer dependencies flow: presentation → business → persistence/external | ArchUnit |

---

## 2. Class Naming Conventions

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

---

## 3. Lombok Usage

### 3.1 Standard Service Class

```java
@Slf4j
@Service
@RequiredArgsConstructor
public class GroupService {
    private final GroupDbAdapter groupDbAdapter;
    private final OmAdapter omAdapter;
}
```

### 3.2 Standard Controller

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

### 3.3 Model/DTO Classes (Service Projects)

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

### 3.4 Model Classes (Library Projects) — THE Standard Combo

**Always use this exact 7-annotation combination. Never use `@Data`.**

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

### 3.5 Constants/Utility Classes

```java
@UtilityClass
public class MetricConstants {
    public static final String METRIC_MONGO = "mongodb.operation";
}
```

### 3.6 Rules

| Rule | Applies To |
|---|---|
| `@Slf4j` on every class that logs (nearly all) | All |
| `@RequiredArgsConstructor` for constructor injection | Controllers, Services, Adapters |
| Never use `@Data` in library model projects | Libraries |
| `@Builder(toBuilder = true)` when copies with modification needed | DTOs/Events |
| `@ToString(callSuper = true)` + `@EqualsAndHashCode(callSuper = true)` for subclasses | Inheritance |
| `lombok.addLombokGeneratedAnnotation = true` in `lombok.config` | All projects |

### 3.7 lombok.config

```properties
config.stopBubbling = true
lombok.addLombokGeneratedAnnotation = true
```

---

## 4. REST Controller Patterns

### 4.1 Dual-Path Mapping (Standard DATEV Pattern)

Every controller serves both end-user and privileged/FKT routes:

```java
@RestController
@RequestMapping(value = {"v1", "v1/privileged"})
```

Or with domain-specific paths:
```java
@RequestMapping(path = {"v1/administrative-profiles", "v1/privileged/administrative-profiles"})
```

### 4.2 Path Conventions

- **Kebab-case** for all URL segments: `/person-contexts/{person-context-id}`
- **API versioning** in path: `/v1/`, `/api/v1/`
- **Path variables** use kebab-case: `{person-context-id}`, `{group-id}`
- **No trailing slashes**

### 4.3 Method Annotations Stack

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

### 4.4 Response Patterns

| Style | When | Example |
|---|---|---|
| `ResponseEntity<T>` | MVC controllers | `ResponseEntity.ok(dto)` |
| `Mono<Void>` / `Mono<T>` | WebFlux controllers | Implements generated API interface |
| `ResponseEntity<Void>` | Mutations with no body | `ResponseEntity.status(HttpStatus.CREATED).build()` |

### 4.5 OpenAPI Code-Gen (WebFlux services)

Server-side generation from `openapi.yaml`:
- Generator: `spring`, `interfaceOnly=true`
- Controllers implement the generated interface
- `reactive=true`, `responseWrapper=reactor.core.CorePublisher`
- `useResponseEntity=false`
- `useTags=true`

Client-side generation for upstream APIs:
- Generator: `java`, library: `webclient`
- Additional model annotations: `@lombok.Builder @lombok.AllArgsConstructor`

### 4.6 Security on Endpoints

```java
// Custom DATEV annotation — resolves Administrator from security context
@RvoSecurity
@RvoSecurity(permission = {RvoSecurityType.OWNER, RvoSecurityType.ADMIN, RvoSecurityType.ORG_UNIT_ADMIN})
```

WebFlux security via `ServerHttpSecurity`:
```java
.pathMatchers(HttpMethod.POST, "/api/**").authenticated()
.pathMatchers(HttpMethod.DELETE, pattern).hasRole("INTERNAL_ADMIN")
.pathMatchers(AUTH_WHITELIST).permitAll()
.anyExchange().denyAll()
```

---

## 5. Persistence Patterns

### 5.1 The DbAdapter Pattern (MANDATORY)

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

### 5.2 JPA Entity Conventions

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

- German column/table names (from mainframe heritage)
- Schema separation: `AVADMIN` for tables, `SQ_NUK2` for sequences
- `allocationSize = 1` always
- Custom converters for types: `UUIDConverter`, `BooleanConverter`
- Hibernate `Interceptor` for lifecycle events + history

### 5.3 Spring Data JPA Repositories

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

### 5.4 MongoDB Patterns (Raw Driver — WebFlux)

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

- Two MongoClient beans: `insertMongoClient` (retryWrites=true) and `updateMongoClient` (retryWrites=false)
- Profile-based: `@Profile("cloud")` vs `@Profile("local")`
- Custom codecs (e.g., `OffsetDateTimeCodec`)
- Snake_case field naming strategy at driver level

### 5.5 MongoDB Document Models

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

---

## 6. Object Mapping (MapStruct)

### 6.1 Standard MapStruct Interface

```java
@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.ERROR)
public interface GroupDtoMapper {
    GroupDto map(GroupModel source);

    @Mapping(target = "org.id", source = "orgId")
    @Mapping(target = "org.displayName", source = "workplaceName")
    GroupWithOrgDto mapToGroupWithDto(GroupModel source);
}
```

### 6.2 Rules

| Rule | Enforcement |
|---|---|
| `componentModel = "spring"` always | ArchUnit |
| `unmappedTargetPolicy = ReportingPolicy.ERROR` always | ArchUnit |
| Separate mapper per layer transition | Convention |
| Presentation mappers in `presentation/rest/mapper/` | Convention |
| Persistence mappers in `persistence/mapper/` | Convention |
| External mappers in `external/mapper/` | Convention |

### 6.3 Three-Layer Mapping Chain

```
Entity ←→ Model ←→ DTO
  ↑ persistence/mapper   ↑ presentation/rest/mapper
```

Each layer has its own mapper interfaces. Models are the intermediate representation.

---

## 7. Exception Handling

### 7.1 Exception Hierarchy

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

For reactive services:
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

### 7.2 Global Exception Handler

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

### 7.3 ErrorDto Pattern

```java
public class ErrorDto {
    private String error;            // "#RVOUMS400"
    private String errorDescription; // Human-readable message
    private String errorUri;         // Reference documentation (usually empty)
    private String requestId;        // From DATEV_REQUEST_ID header
}
```

### 7.4 WebFlux Exception Handler (RFC 7807)

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

### 7.5 VK3 Data Masking in Errors

Sensitive financial data (Verarbeitungskennzeichen 3) must be masked:
```java
Vk3MaskingUtil.maskMessage(e.getMessage(), ExceptionUtil.JAVA_FIELDS_WHITELIST)
```

---

## 8. Configuration Patterns

### 8.1 Application Properties Namespace

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

### 8.2 Cloud Foundry VCAP Services

External service credentials come from VCAP:
```yaml
${vcap.services.{service-name}.credentials.{key}}
```

### 8.3 Profile Strategy

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

### 8.4 @ConfigurationProperties Pattern

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

### 8.5 Conditional Activation

```java
@ConditionalOnProperty(value = "kafka-config.enabled", havingValue = "true")
@Profile(ProfileConstants.CLOUD_PROFILE)
```

---

## 9. Logging Patterns

### 9.1 Standard Setup

- SLF4J + Logback everywhere
- `@Slf4j` (Lombok) on every class that logs
- logback-spring.xml with profile-specific appenders

### 9.2 Structured Logging Context

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

### 9.3 Splunk-Optimized Markers

```java
private static final Marker MARKER = MarkerFactory.getMarker("REFSYS_SPLUNK_MARKER");
log.info(MARKER, "Initial load completed for consultant={}", consultant);
```

### 9.4 Timed Operations (Reactive)

```java
return mongoOperation
    .elapsed()
    .map(LoggingUtil.logDebugWithDuration("MongoDB upsert masterData"));
```

### 9.5 VK3 Masking in Logs

Custom Logback `PatternLayout` masks sensitive accounting fields:
```java
public class MaskingPatternLayout extends PatternLayout {
    // Masks patterns matching VK3 fields (account numbers, amounts, tax IDs)
}
```

### 9.6 Constant-Based Log Messages

```java
public static final String INITIAL_LOAD_START_LOG = "Starting initial load for consultant={}";
public static final String INITIAL_LOAD_RESPONSE_LOG = "Initial load completed in {}ms";
```

### 9.7 Error Logging with Error Codes

```java
log.error("ExceptionMapper: ErrorCode: {}", errorCode, cause);
log.warn("user has no admin permission for serviceOrg={}", serviceOrgId, ex);
```

---

## 10. Testing Patterns

### 10.1 Test Classification

| Suffix | Type | Framework |
|---|---|---|
| `*Test.java` | Unit test | JUnit 5 + Mockito |
| `*IT.java` | Integration test | Spring Boot Test |
| `*SecurityIT.java` | Security integration | Spring Security Test |
| `*Spec.groovy` | Unit test (alt) | Groovy Spock |
| `RunCucumberTest.java` | BDD runner | Cucumber |
| `ArchitectureTest.java` | Architecture | ArchUnit |

### 10.2 Unit Test Pattern

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

### 10.3 Test Method Naming

```java
// Pattern: should_<expected>_when_<condition>
void should_return_500_when_unexpected_exception_is_thrown()
void should_return_groups_from_serviceOrg_for_admin()

// Or camelCase with @DisplayName:
@DisplayName("should return groups from serviceOrg for admin")
void shouldReturnGroupsFromServiceOrgIdForAdmin()
```

### 10.4 WebFlux Controller Tests

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

### 10.5 Integration Tests (Spring Boot)

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

### 10.6 German-Language Cucumber BDD

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

### 10.7 ArchUnit Enforcement

```java
@AnalyzeClasses(packages = "de.datev.rvo.usermanagementservice",
    importOptions = {ImportOption.DoNotIncludeTests.class})
class ArchitectureTest {
    @ArchTest
    ArchTests allArchTests = ArchTests.in(AllRules.class);
}
```

Standard rules:
1. Persistence layer only accessed through adapter classes
2. Controllers named with `Controller` suffix
3. Database classes only in persistence layer
4. Layer dependencies respected (presentation → business → persistence/external)
5. MapStruct mappers use Spring injection
6. MapStruct reports unmapped targets as errors
7. Controllers reside in `presentation.rest` package

### 10.8 Model toString Tests (Library Pattern)

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

### 10.9 WireMock Stubs Organization

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

### 10.10 Test Dependencies Summary

| Dependency | Purpose |
|---|---|
| JUnit 5 (Jupiter) | Test framework |
| Mockito | Mocking |
| AssertJ | Fluent assertions |
| Cucumber (Java + Spring) | German BDD features |
| WireMock | External service simulation |
| Testcontainers | MongoDB in Docker |
| @EmbeddedKafka | Kafka in tests |
| Awaitility | Async assertion |
| EasyRandom | Random object generation |
| Instancio | Test data generation |
| Pact | Consumer-driven contracts |
| ArchUnit | Architecture enforcement |
| REST Assured | API testing |
| Groovy Spock | Alternative unit testing |

---

## 11. Security Patterns

### 11.1 Authentication

| Method | Where |
|---|---|
| HTTP Basic Auth | All MVC services |
| OAuth2 JWT (Resource Server) | WebFlux services |
| LDAP-backed Basic Auth | User-management, access-admin |

### 11.2 DATEV Security Framework

```java
// Method-level security (from rrmo-security-component)
@RvoSecurity
@RvoSecurity(permission = {RvoSecurityType.OWNER, RvoSecurityType.ADMIN, RvoSecurityType.ORG_UNIT_ADMIN})
```

`Administrator` object is injected into controller methods via framework:
```java
public ResponseEntity<Dto> getResource(
    @PathVariable("id") Long id,
    @Parameter(hidden = true) Administrator administrator) { ... }
```

### 11.3 Custom AOP Authorization

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

### 11.4 FKT (Functional/Technical) Users

- Identified by `@fkt.datev.de` email suffix
- Access privileged endpoints (`/v1/privileged/`)
- Matched by patterns: `WSRVIN(1|2|3)@fkt.datev.de`

### 11.5 Security Headers (WebFlux)

```java
.headers(headers -> {
    headers.contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'self'"));
    headers.hsts(hsts -> hsts.maxAgeInSeconds(31536000));
    headers.frameOptions(fo -> fo.mode(DENY));
})
```

### 11.6 CORS

```java
.allowedOriginPatterns("*.datev.de", "http://localhost:*")
.allowCredentials(true)
```

---

## 12. Reactive Patterns (WebFlux Services)

### 12.1 Interface + Impl for All Services

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

### 12.2 Timed Operations with .elapsed()

```java
return mongoOperation
    .elapsed()
    .map(LoggingUtil.logInfoWithDuration("Operation completed"));
```

### 12.3 Circuit Breaker + Retry (order matters)

```java
return webClientCall
    .transformDeferred(RetryOperator.of(retryInstance))         // retry FIRST
    .transformDeferred(CircuitBreakerOperator.of(circuitBreaker)); // CB wraps retry
```

### 12.4 Micrometer Metrics Tap

```java
return operation
    .name(MetricConstants.METRIC_MONGO)
    .tag(MetricConstants.REPOSITORY, "masterData")
    .tag(MetricConstants.METHOD, "upsertOne")
    .tag(MetricConstants.METRIC_TYPE, MetricConstants.METRIC_WRITE)
    .tap(Micrometer.metrics(meterRegistry));
```

### 12.5 Context Propagation for Logging

```java
return chain.filter(exchange)
    .contextWrite(LoggingUtil.createInitialContext(loggingContext, correlationId));

// Accessing context downstream:
return Mono.deferContextual(ctx -> {
    String corrId = ctx.get(LoggingUtil.CORRELATION_ID_KEY);
    return apiClient.call(corrId);
});
```

### 12.6 Buffering + Controlled Concurrency

```java
return flux
    .buffer(configuration.getBufferSize())
    .flatMap(batch -> bulkUpsert(batch), MAX_CONCURRENCY, MAX_PREFETCH);
```

### 12.7 Parallel Independent Operations

```java
return Flux.merge(
    insertMovementDataDays(dayData),
    insertMovementDataMonths(monthData),
    importMasterData(masterDataContext),
    importMasterDataAccounts(accounts)
);
```

### 12.8 Fire-and-Forget Pattern

```java
return service.doFireAndForgetFullImport(params)
    .thenReturn(true)
    .elapsed().map(LoggingUtil.logInfoWithDuration("Full import"))
    .then();
```

### 12.9 Resilience4j Configuration

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

---

## 13. External Service Communication

### 13.1 Spring Cloud OpenFeign (MVC Services)

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

### 13.2 Adapter Wrapping Feign Clients

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

### 13.3 Request-Scoped Caching

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

### 13.4 WebClient-Based Clients (WebFlux)

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

---

## 14. Kafka/Messaging Patterns

### 14.1 Event Producer (WebFlux — ReactiveKafkaProducerTemplate)

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

### 14.2 Mock Producer for Non-Kafka Environments

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

### 14.3 Event-Driven Process Orchestration (MVC)

```java
// Custom DATEV event-client framework
@EventMethod(process = 1107, state = 1)
public void handleR4cEvent(Event event) {
    // Process event, then trigger next state:
    eventProducer.createNextEvent(event, nextState, payload);
}
```

### 14.4 Event Retry (MongoDB-backed)

- Failed events stored in `R4cRetryEventEntity` (MongoDB)
- `@Scheduled` with `@SchedulerLock` (ShedLock) polls for retries
- Configurable delay: `rvo-r4c-retry.fixedDelay: 10000`

### 14.5 Spring ApplicationEvents (Internal Pub/Sub)

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

---

## 15. Model/DTO Field Type Rules

### 15.1 Wrapper Types Only (Never Primitives)

| Use | Don't Use | Reason |
|---|---|---|
| `Integer` | `int` | Nullable fields common in DATEV domain |
| `Long` | `long` | Monetary amounts, IDs |
| `Boolean` | `boolean` | Tri-state possible (null = unknown) |

Exception: DTOs with `@JsonProperty("is_global") private boolean global` — simple flags can use primitives in DTOs.

### 15.2 Monetary/Amount Values

- **Library models**: `Long` (minor units — cents/Pfennig)
- **API/calculations**: `BigDecimal` (when precision required)
- **Never `float` or `double`** for financial data

### 15.3 Identifiers

| Type | Usage |
|---|---|
| `Long` | Internal database IDs |
| `UUID` | Service organization IDs, external IDs |
| `Integer` | Domain-specific codes (consultant number, client number, fiscal year) |
| `String` | External string identifiers |

### 15.4 Collections

```java
private List<CollectiveAccount> collectiveAccounts;           // Lists of nested objects
private Map<String, AccountValue> values = new LinkedHashMap<>();  // Order-preserving maps
private List<Integer> accountNumbers;                          // Lists of primitives
```

- Initialize Maps with `new LinkedHashMap<>()` (preserves insertion order)
- Lists default to `null` (not empty list)

### 15.5 Date/Time

| Type | Usage |
|---|---|
| `OffsetDateTime` | Timestamps with timezone (state changes) |
| `LocalDate` | Date-only values (fiscal year dates) |
| `Integer` | Year as integer when only year needed |

### 15.6 Enums

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

---

## 16. Domain Language

### 16.1 German Domain Terminology Preserved

DATEV preserves German business domain terms in code:

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

### 16.2 Naming Rules

- **Package names**: English (`presentation`, `business`, `persistence`, `external`)
- **Class names**: Mix — German for domain concepts (`Auswertung`), English for technical (`Controller`, `Service`)
- **Field names**: English with German domain terms where no clear English equivalent exists
- **Database columns**: German (mainframe heritage): `BESCHREIBUNG`, `GRUPPENID`, `PERSONCONTEXT_ID`
- **REST paths**: English kebab-case (`/person-contexts/`, `/groups/`)
- **Cucumber features**: German (`Funktionalität`, `Szenario`, `Gegeben`, `Wenn`, `Dann`)
- **Log messages**: English
- **Comments**: German or English (inconsistent — prefer English for new code)

---

## 17. Value Objects & Type Safety

### 17.1 Custom Value Object for REST Binding

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

### 17.2 Command Objects with Validation Guards

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

### 17.3 History/Audit Annotation

```java
@HistoryUseCase(useCase = "DELGRP")  // on mutating controller methods
@HistoryUseCase(useCase = "CopyP")
```

---

## 18. Infrastructure & Deployment

### 18.1 Cloud Foundry Manifest

```yaml
applications:
  - name: service-name
    memory: 1G
    instances: 2
    buildpack: java_buildpack_offline
    path: target/service-name.jar
    env:
      JBP_CONFIG_OPEN_JDK_JRE: '{ jre: { version: 17.+ } }'
      JAVA_OPTS: '-Dfile.encoding=UTF-8'
      SPRING_PROFILES_ACTIVE: cloud,eventclient
    services:
      - rvo-url-provider
      - rvo-db2-credentials
      - access-administration-fkt-credhub
```

### 18.2 Health & Observability

- Spring Boot Actuator (`/actuator/health`, `/actuator/info`)
- OpenTelemetry OTLP exporter for distributed tracing
- Custom Micrometer metrics (`.tap(Micrometer.metrics(...))`)
- Splunk-compatible log format

### 18.3 Distributed Scheduling (ShedLock)

```java
@Scheduled(fixedDelayString = "${rvo-r4c-retry.fixedDelay:10000}")
@SchedulerLock(name = "Scheduler_lock_Retry",
    lockAtLeastFor = "${rvo-r4c-retry.lockAtLeast:PT5S}",
    lockAtMostFor = "${rvo-r4c-retry.lockAtMost:PT30S}")
void retry() { ... }
```

### 18.4 Build Tool

| Existing DATEV projects | Migration output |
|---|---|
| Maven (pom.xml) | Gradle (build.gradle.kts) |
| Spring Boot parent POM | Version catalog (libs.versions.toml) |
| DATEV parent POM (`administration-parent`) | Standalone |

When migrating: Use Gradle with version catalog. Existing services stay on Maven.

### 18.5 CI/CD

- Jenkins (`Jenkinsfile`, `Jenkinsfile-ReleaseDeploy`)
- DATEV CI (`.datev-ci.yaml`)
- GitLab (`.gitlab/issue_templates/`)
- Renovate (`renovate.json`) for dependency updates
- Gitleaks (`gitleaks.toml`) for secret scanning

---

## 19. Migration Framework Calibration

### 19.1 When Framework Defaults Differ from DATEV Patterns

| Aspect | Framework Default | DATEV Convention | Resolution |
|---|---|---|---|
| Architecture | Hexagonal (ports/adapters) | 4-layer (presentation/business/persistence/external) | Use DATEV 4-layer for services; keep hexagonal for libraries |
| Models | Records (immutable) | Lombok classes (mutable, @Getter/@Setter/@Builder) | Use Lombok for service models; records OK for library value objects |
| Field types | Primitives where non-null | Wrapper types always (Integer/Long/Boolean) | Use wrapper types |
| DI | Constructor records | @RequiredArgsConstructor on classes | Use Lombok RequiredArgsConstructor |
| Persistence | Repository directly | DbAdapter wrapping repository | Always use DbAdapter pattern |
| Service pattern | Concrete classes | Interface + Impl (reactive); concrete (MVC) | Match service type |
| Mapping | Manual or records | MapStruct with ERROR policy | Use MapStruct |
| Tests | JUnit 5 + AssertJ | JUnit 5 + AssertJ + Cucumber (German) + ArchUnit | Add Cucumber + ArchUnit |
| Error handling | Domain exceptions | Rvo*Exception hierarchy + ErrorDto | Use Rvo pattern |
| Naming | English throughout | German domain terms preserved | Preserve German terms |

### 19.2 What to Always Include in Generated Code

1. **`@Slf4j`** on every class
2. **`lombok.config`** with `addLombokGeneratedAnnotation = true`
3. **ArchUnit test** enforcing layer boundaries
4. **DbAdapter** between services and repositories
5. **MapStruct mappers** with `unmappedTargetPolicy = ERROR`
6. **ExceptionMapper** (`@ControllerAdvice`) with ErrorDto response
7. **Dual path mapping** (`v1` + `v1/privileged`)
8. **@RvoSecurity** on endpoint methods
9. **Profile-based configuration** (test, default, cloud)
10. **Wrapper types** for all model fields

### 19.3 What NOT to Include (DATEV Doesn't Use)

- `@Data` in library model projects (use the 7-annotation combo)
- Bean Validation annotations in shared model JARs
- Jackson annotations in shared model JARs
- Direct repository injection into services
- Primitive types in domain models
- English-only domain naming (preserve German business terms)
- `@Autowired` field injection (always constructor injection)
- Checked exceptions (use unchecked hierarchy)

---

## Appendix A: Dependency Matrix

### A.1 Service Dependencies (Maven)

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

### A.2 Library Dependencies (Maven)

| Category | Artifact |
|---|---|
| Code gen | `lombok` |
| MongoDB mapping | `spring-data-mongodb` (for `@Document` only) |
| Testing | `junit-jupiter`, `assertj-core`, `easy-random-core`, `reflections` |

### A.3 Test Dependencies

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

---

## Appendix B: ArchUnit Rules Template

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

## Appendix C: Quick Reference Card

| Decision | DATEV Standard |
|---|---|
| Package layout (service) | `presentation/business/persistence/external` |
| Package layout (library) | `api/internal/spi` with `module-info.java` |
| Repo access | Through `*DbAdapter` only — never direct |
| DI style | `@RequiredArgsConstructor` + `private final` fields |
| Model annotations (library) | `@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor @EqualsAndHashCode @ToString` |
| Model annotations (service DTO) | `@Data @NoArgsConstructor @AllArgsConstructor @SuperBuilder` |
| Mapping | MapStruct, `componentModel="spring"`, `unmappedTargetPolicy=ERROR` |
| Exceptions | `Rvo*Exception` hierarchy → `@ControllerAdvice` ExceptionMapper |
| REST paths | Kebab-case, dual-mapping (`v1` + `v1/privileged`) |
| Security | `@RvoSecurity` on methods, `Administrator` injected |
| Tests | JUnit 5 + AssertJ + German Cucumber + ArchUnit |
| Logging | `@Slf4j`, structured MDC, VK3 masking |
| Nullability | Wrapper types, no annotations, null-safe arithmetic |
| German terms | Preserved in domain model — never anglicize |
| Field naming (DB) | German uppercase (`BESCHREIBUNG`, `GRUPPENID`) |
| Field naming (Java) | camelCase |
| Field naming (JSON) | snake_case via `@JsonProperty` |
| Field naming (MongoDB) | snake_case (naming strategy) |
