# Service Profile (output_type = "service")

A Spring Boot 4.x deployable — REST/gRPC/messaging endpoints, database access,
full observability stack. This is the default when the C++ source is an executable
with network listeners.

---

## Service Design Principles

These principles guide EVERY decision when building a service:

1. **Health-first** — The service reports its own health accurately. If a dependency is
   down, the health endpoint reflects it. No silent failures hiding behind 200 OK.

2. **Resilience by default** — Every outbound call has a timeout, a retry policy, and a
   circuit breaker. Assume the network will fail; code for it from day one.

3. **Graceful shutdown** — In-flight requests complete before the process exits. Connections
   drain. No data loss on SIGTERM. Virtual threads + Spring lifecycle handle this.

4. **Idempotent where possible** — POST operations that create resources should be safely
   retriable. Use idempotency keys for operations that can't naturally be idempotent.

5. **Observable from the outside** — If you can't see it in metrics, traces, or logs, it
   doesn't exist. Every use case is `@Observed`. Every error is logged with context.

6. **Fail-fast startup** — If config is missing or a required dependency is unreachable,
   fail at startup, not at first request. Use `@ConfigurationProperties` validation.

7. **Secure by default** — Authentication is not optional. Input validation is not optional.
   SQL injection is impossible (parameterized queries). Secrets never touch code.

8. **Contract-first APIs** — Define the API contract (OpenAPI/protobuf) before implementation.
   The contract is the truth; the code implements it, not the other way around.

---

## Service Package Structure

```
src/main/java/com/{group}/{artifact}/
├── domain/                      # (universal — see Part 1)
├── application/                 # (universal — see Part 1)
├── adapter/
│   ├── in/                      # Driving adapters (inbound)
│   │   ├── web/                 # @RestController — REST endpoints
│   │   ├── grpc/                # gRPC service implementations
│   │   ├── messaging/           # @EventListener, @KafkaListener
│   │   └── scheduler/           # @Scheduled tasks
│   └── out/                     # Driven adapters (outbound)
│       ├── persistence/         # @Repository, JPA entities
│       ├── messaging/           # Event/message publishers
│       ├── client/              # RestClient / @HttpExchange
│       └── cache/               # Cache implementations
└── config/                      # @Configuration, @Bean definitions
    ├── security/
    ├── persistence/
    └── observability/
```

## Service Gradle Build

```kotlin
plugins {
    java
    alias(libs.plugins.spring.boot)
    alias(libs.plugins.spring.dependency.management)
    alias(libs.plugins.graalvm.native)
}

java {
    toolchain { languageVersion = JavaLanguageVersion.of(25) }
}

dependencies {
    implementation(libs.spring.boot.starter.web)
    implementation(libs.spring.boot.starter.data.jpa)
    implementation(libs.spring.boot.starter.validation)
    implementation(libs.spring.boot.starter.actuator)
    implementation(libs.spring.boot.starter.security)
    implementation(libs.bundles.observability)
    implementation(libs.mapstruct)
    annotationProcessor(libs.mapstruct.processor)
    testImplementation(libs.spring.boot.starter.test)
    testImplementation(libs.bundles.testing)
}
```

## Service-Specific Spring Boot 4.x Rules

- **Constructor injection only** — no `@Autowired` on fields
- **@ConfigurationProperties records** — type-safe config, not `@Value`
- **RestClient** for HTTP calls (not RestTemplate, not WebClient for blocking)
- **@HttpExchange** for declarative HTTP service interfaces
- **ProblemDetail (RFC 9457)** for all error responses
- **Micrometer Observation API** — `@Observed` on every use case
- **Spring Modulith** for module boundaries
- **Spring AOT** compatible code — minimize runtime reflection
- **Virtual threads enabled** (`spring.threads.virtual.enabled=true`)

## Service Adapter Naming

| Element | Pattern | Example |
|---------|---------|---------|
| REST controller | `NounController` | `OrderController` |
| gRPC service | `NounGrpcService` | `OrderGrpcService` |
| Message listener | `NounListener` | `OrderEventListener` |
| Persistence adapter | `NounPersistenceAdapter` | `OrderPersistenceAdapter` |
| HTTP client adapter | `NounClientAdapter` | `PaymentClientAdapter` |

## Service Controller Pattern (CORRECT)

```java
@RestController
@RequestMapping("/api/orders")
class OrderController {

    private final ProcessOrderUseCase processOrder;  // ← port interface
    private final OrderMapper mapper;

    OrderController(ProcessOrderUseCase processOrder, OrderMapper mapper) {
        this.processOrder = processOrder;
        this.mapper = mapper;
    }

    @PostMapping
    ResponseEntity<OrderResponse> create(@Valid @RequestBody CreateOrderRequest request) {
        var command = mapper.toCommand(request);
        var result = processOrder.execute(command);
        return ResponseEntity.status(CREATED).body(mapper.toResponse(result));
    }
}
```

## Service Observability (Required)

**Stack:** OTel Java Agent + Micrometer Observation + OTLP exporter + structured JSON logging

**Rules:**
- EVERY use case: `@Observed`
- EVERY adapter/out/: auto-traced by OTel agent
- Trace ID on every log line
- Health indicator per external dependency (`/actuator/health`)
- Custom business metrics for domain events

**application.yml:**
```yaml
management:
  endpoints:
    web.exposure.include: health,info,metrics,prometheus
  tracing:
    sampling.probability: 1.0
  observations:
    annotations.enabled: true
  otlp:
    tracing.endpoint: http://localhost:4318/v1/traces
    metrics.endpoint: http://localhost:4318/v1/metrics

logging:
  pattern:
    level: "%5p [${spring.application.name},%X{traceId:-},%X{spanId:-}]"
```

## Service Security

- Input validation at adapter boundary (Jakarta Bean Validation)
- Spring Security method-level authorization on use cases
- CSRF for browser endpoints
- Secrets via environment / Spring Vault — never hardcoded

## Service Testing

```
Unit tests:         domain/ + application/ — no Spring context
Slice tests:        @WebMvcTest (web), @DataJpaTest (persistence)
Integration tests:  @SpringBootTest + Testcontainers
Architecture tests: ArchUnit hexagonal + Spring conventions
Contract tests:     Spring Cloud Contract for API consumers
```

## Service Anti-Patterns

- `import org.springframework.*` inside `domain/` → **VIOLATION**
- Business logic in `@RestController` → extract to use case
- Controller injecting domain service or repository → **inject use case port**
- Controller orchestrating multiple calls → **single use case invocation**
- Domain entity returned from controller → map to DTO
- `@Transactional` on domain service → move to use case
- `Thread.sleep()` → virtual threads / scheduled task
- `System.out.println()` → SLF4J logger
- Hardcoded URL/credentials → `@ConfigurationProperties`
- Missing `@Observed` on use case → add it
