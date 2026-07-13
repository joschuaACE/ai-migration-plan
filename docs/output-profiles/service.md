# Service Output Profile

Use this profile for a continuously running, independently deployable process that owns
network, message, scheduler, or worker entry points. The default architecture is modular
hexagonal: business capabilities form modules, and each module protects its policy from
delivery and infrastructure mechanisms through explicit ports.

## Modular Hexagonal Default

Within each business module:

- the domain holds business rules and invariants without framework or infrastructure types;
- application use cases orchestrate domain behavior and define transaction intent;
- inbound ports describe supported operations without transport-specific request types;
- outbound ports describe capabilities the use cases require, not vendor technologies;
- inbound adapters translate protocols, messages, jobs, or schedules into use-case inputs;
- outbound adapters implement persistence, messaging, clock, identity, and remote-system
  capabilities; and
- a visible composition root binds adapters to use cases.

Dependencies point from adapters toward application and domain policy. Outbound adapter
implementations depend on the port they implement; policy never imports the implementation.
Transport validation and error mapping stay at inbound boundaries. Infrastructure errors
are translated before they cross into application or domain contracts.

## Module Boundaries

Organize first by business capability, then by architectural role within the capability.
One module may use another only through a published application contract or event. It must
not import the other module's persistence model, private domain objects, or adapters.

Module boundaries must be checkable with the target profile's dependency validator. Split
deployment units only when release cadence, scaling, isolation, ownership, or trust evidence
justifies distributed-system cost; modular hexagonal does not imply microservices.

## Service Contracts

Characterize and preserve:

- protocol schemas and compatibility policy;
- authentication, authorization, and trust boundaries;
- timeout, cancellation, retry, and idempotency semantics;
- transaction, ordering, delivery, and partial-failure behavior;
- health, readiness, graceful shutdown, and backpressure behavior; and
- logs, metrics, traces, audit records, and service-level objectives that consumers rely on.

Every outbound call has an explicit timeout. Retries and circuit breakers are conditional:
apply them only when the operation is safe, the failure mode warrants them, and retry
amplification is controlled. Do not retry non-idempotent work by default.

## Coexistence and Cutover

Prefer routing at an existing protocol, consumer, or message boundary. Shadow execution
must isolate target side effects. Mirrored writes require proven idempotency, ordering,
reconciliation, and partial-failure policy. A routed cohort needs path-specific telemetry
and an immediate route-back procedure.

Cutover evidence includes contract comparisons, dependency health, load or capacity checks
where relevant, observability readiness, and a tested rollback or forward-recovery plan.

## Required Gates

- module dependency and policy-purity check;
- contract and adapter integration tests for changed boundaries;
- build, packaging, configuration, and startup checks;
- security and dependency analysis declared by the target profile;
- behavior-specific concurrency, data, and failure-path evidence; and
- cutover/rollback rehearsal appropriate to the slice risk.

## Rule Provenance

Shared metadata: `applicability` is any migration selecting the service output profile;
`source` is this portable service contract and Ports-and-Adapters boundary guidance;
`owner` is output profile `service`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `OUT-SERVICE-001` | Modular ports isolate business change from delivery and infrastructure churn. | Architecture validator and review | Module dependency report | Output profile v2 |
| `OUT-SERVICE-002` | Unconditional retries can duplicate work and amplify outages. | Review and resilience tests | Per-call timeout/retry/idempotency decision | Output profile v2 |
| `OUT-SERVICE-003` | A deployable replacement needs operational as well as functional equivalence. | Service gate validator | Startup, health, shutdown, telemetry, and rollback evidence | Output profile v2 |
