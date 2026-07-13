# Java 25 Service Specialization

This document specializes `docs/output-profiles/service.md` for the Java 25 service stack.
The selected target manifest supplies the reviewed framework and dependency versions. The
default architecture is a modular hexagonal service; it is not a top-level collection of
global `domain`, `application`, and `adapter` packages.

## Feature-First Modules

```text
{target_root}/src/main/java/<base-package>/
├── orders/
│   ├── domain/                         # Business policy; no Spring/infrastructure imports
│   ├── application/
│   │   ├── port/in/                    # Supported use-case contracts
│   │   ├── port/out/                   # Capabilities required by use cases
│   │   └── usecase/                    # Orchestration and transaction intent
│   ├── adapter/
│   │   ├── in/http/                    # Transport mapping and validation
│   │   ├── in/messaging/
│   │   ├── out/persistence/
│   │   └── out/client/
│   └── config/                         # Module composition
├── billing/
│   └── ...
└── ServiceApplication.java             # Process composition root
```

Adapters depend inward on application contracts. Application use cases depend on domain and
outbound port interfaces. Domain policy depends on neither Spring nor adapters. A module
uses another module through a published application contract or event, never through its
adapter or persistence model.

Use Spring Modulith and/or ArchUnit when selected to validate module and dependency rules;
the repository validator must run the chosen check and retain its report. Modular design
does not require splitting modules into network services.

## Spring Boundary Rules

- Use constructor injection. Bind dependencies in configuration/composition; do not use
  field injection or a service locator.
- Keep `@RestController`, persistence annotations/entities, messaging annotations, HTTP
  clients, and Spring configuration types in adapters/configuration.
- Put transaction boundaries around application operations that own a business transaction;
  do not annotate domain entities/services.
- Bind configuration through validated, typed configuration properties. Separate secrets
  from ordinary configuration and redact them from errors/telemetry.
- For blocking HTTP calls, consider `RestClient` or an `@HttpExchange` client behind an
  outbound port. Use a reactive client only when the selected execution model requires it;
  do not mix reactive and blocking styles accidentally.
- Map HTTP errors to `ProblemDetail` or the approved protocol contract at the inbound adapter.
  Domain/application contracts do not return HTTP response types.
- Keep reflection/proxy/native-image requirements visible and test the packaged mode actually shipped.

## Concurrency and Resilience

Enable virtual threads only after classifying workload, dependencies, pinning/native calls,
thread-local assumptions, and capacity limits. Preserve explicit executors for CPU-bound or
affinity-sensitive work. Scoped values are suitable for lexically scoped immutable request
context; they are not a replacement for durable state.

Every outbound operation declares a timeout and cancellation behavior. Add retries only for
classified transient failures when idempotency or deduplication makes them safe. Bound retry
count/backoff and test timeout/retry interaction. Circuit breakers, bulkheads, and caches are
risk-driven adapters, not dependencies installed in every service.

## API, Data, and Lifecycle

- Generate or validate OpenAPI/protobuf/message schemas where those contracts exist.
- Preserve status/error mapping, headers/metadata, ordering, streaming, pagination, and
  compatibility policy through contract tests.
- Keep persistence entities and transport DTOs out of domain and cross-module contracts.
- Validate startup configuration before accepting work, but distinguish required from
  temporarily unavailable dependencies in readiness policy.
- Implement graceful shutdown: stop acceptance, drain bounded in-flight work, commit or
  cancel safely, flush required telemetry, and release resources.
- Make liveness independent of downstream availability; use readiness and dependency-specific
  health for inability to serve.

## Security

- Authenticate and authorize at declared trust boundaries; do not infer that every endpoint
  requires the same mechanism.
- Validate untrusted transport input before application invocation and enforce business
  authorization within the relevant use case/policy.
- Use parameterized data access and approved output encoding.
- Keep credentials out of source, generated manifests, logs, traces, and exception messages.
- Preserve TLS/client-certificate, token, audit, and privilege behavior with security fixtures.

## Observability

Use OpenTelemetry/Micrometer or the selected equivalent through adapter/configuration or
application decorators so core policy is not tied to instrumentation annotations.

Required signals are contract- and risk-driven:

- trace/context propagation across changed boundaries;
- structured logs with correlation and redaction;
- request/work rates, latency, failures, saturation, and business outcomes;
- dependency and queue/backpressure signals; and
- audit evidence where the source contract or regulation requires it.

Sampling, label/cardinality, retention, and exporter-failure behavior are deployment
decisions. A trace annotation on every method is not an observability strategy.

## Gradle Shape

Use the Java 25 toolchain and the dependency rules in `gradle-version-catalog.md`. Declare
only adapters/features selected for the project. A typical service may apply the Spring Boot
plugin and depend on selected starters through catalog aliases, but the framework does not
install persistence, security, native image, messaging, or observability libraries merely
because the output type is `service`.

Validate the resolved graph, locks, integrity metadata, layered/package artifact, startup,
and production launch command.

## Verification

- domain and use-case tests without a Spring context where practical;
- adapter slice/contract tests for HTTP, messaging, persistence, and clients actually changed;
- module/architecture dependency checks;
- packaged integration tests with real compatible infrastructure;
- security, configuration, startup, readiness/liveness, and graceful-shutdown tests;
- concurrency/resilience evidence for changed guarantees; and
- routed-cohort/shadow/cutover/rollback evidence required by the service output profile.

## Anti-Patterns

- global layer packages that allow unrelated business modules to couple freely;
- Spring, persistence, or transport types inside domain policy;
- controllers/listeners calling repositories or coordinating several application operations directly;
- unconditional retry of non-idempotent work;
- health endpoints returning success while required readiness conditions fail, or liveness
  failing solely because a downstream dependency is unavailable;
- enabling virtual threads without testing thread-local/native/blocking assumptions; and
- claiming architecture enforcement when no deterministic dependency check runs.

## Rule Provenance

Shared metadata: `applicability` is Java 25 plus service output; `source` is the portable
service contract, Java 25 target policy, and selected Spring reference documentation;
`owner` is the Java 25 service specialization.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `TGT-JAVA25-SERVICE-001` | Feature-first modules prevent a global layered monolith from bypassing capability boundaries. | ArchUnit/Modulith validator | Module dependency report | Java 25 service profile v2 |
| `TGT-JAVA25-SERVICE-002` | Framework types at the policy boundary couple business behavior to delivery/infrastructure. | Architecture validator | Import/dependency result | Java 25 service profile v2 |
| `TGT-JAVA25-SERVICE-003` | Resilience mechanisms can change side effects and amplify failures. | Review and failure-path tests | Timeout/retry/idempotency decision and results | Java 25 service profile v2 |
