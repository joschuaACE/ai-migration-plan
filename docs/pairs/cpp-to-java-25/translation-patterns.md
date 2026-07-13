# C++ to Java 25 Translation Patterns

These are candidate mappings, not mechanical substitutions. Apply the C++ semantic-hazard
analysis, Java 25 target rules, and selected output profile before choosing a pattern. Record
observable differences in a decision or exception and link the verification evidence.

## Mapping Procedure

For each construct:

1. identify the source intent, reachable callers, build variants, and observable behavior;
2. classify ownership, errors, concurrency, numeric, encoding, ABI, and side-effect semantics;
3. select the smallest Java mechanism that preserves that contract;
4. choose architecture and framework placement from the output profile, not from the C++ spelling;
5. test boundary values and failure paths against the source; and
6. record any normalization, unsupported platform, or retained native dependency.

## Ownership and Lifetime

| C++ construct | Java 25 candidate | Required check |
|---|---|---|
| Stack/automatic object | Local object/reference | Destructor timing and escape/lifetime behavior |
| `unique_ptr<T>` | Exclusively owned reference, often a private final field | Transfer/move semantics and deterministic cleanup |
| `shared_ptr<T>` | Ordinary shared reference only when lifetime is memory-only | Custom deleter, aliasing, cycles, identity, and final-release side effects |
| `weak_ptr<T>` | Explicit registry/handle policy; `WeakReference` only for cache-like GC semantics | Whether source lock/expiry behavior is observable |
| Raw pointer/reference | Reference, optional value, index/handle, or native segment | Ownership, nullability, bounds, aliasing, and borrowed lifetime |
| RAII resource wrapper | `AutoCloseable` plus try-with-resources or explicit owner lifecycle | Cleanup order on success, exception, cancellation, and shutdown |
| Arena/pool/placement `new` | Ordinary allocation, bounded pool, or Foreign Function & Memory arena | Address stability, layout, performance evidence, and close lifetime |

Never map smart-pointer category to dependency-injection scope. Ownership and container
lifecycle are different contracts.

## Values, Containers, and Numeric Behavior

| C++ construct | Java 25 candidate | Required check |
|---|---|---|
| Plain value struct | Record or immutable class | Equality, identity, serialization, validation, and construction semantics |
| `optional<T>` | `Optional<T>` return or explicit domain sum type | Distinguish absent, null, unknown, and serialization states |
| `variant<...>` | Sealed hierarchy/record variants | Unknown alternatives and compatibility evolution |
| `vector`/`deque`/`list` | `List` or a specialized queue/deque | Mutation, iterator invalidation, complexity, thread safety, and snapshot/live view |
| `map`/`unordered_map` | Ordered/sorted/hash `Map` implementation | Iteration order, key equality/hash, null policy, and deterministic serialization |
| Fixed-width integer | Java primitive plus explicit range/unsigned operations when needed | Overflow, narrowing, shifts, wire width, and unsigned comparison/division |
| Floating point | `float`/`double`, or a deliberate decimal type for decimal contracts | NaN, infinities, signed zero, precision, rounding, tolerance, and serialized form |
| `string`/byte buffer | `String`, `byte[]`, buffer, or memory segment | Charset, embedded NUL, unsigned bytes, normalization, mutation, and ownership |

Use explicit `Charset`, `Locale`, `ZoneId`, and byte order at boundaries. Do not infer a
protocol from Java defaults.

## Polymorphism, Templates, and Macros

| C++ construct | Java 25 candidate | Required check |
|---|---|---|
| Virtual interface | Interface or abstract class | Destruction/lifecycle, default behavior, covariance, RTTI, and ABI/plugin use |
| Multiple inheritance | Interface composition plus delegation | Shared base state, virtual inheritance, dispatch ambiguity, and identity |
| CRTP/static polymorphism | Generic strategy, sealed hierarchy, or generated specialized code | Compile-time constraints and performance rationale |
| Template | Generic only when type erasure and numeric operations preserve behavior | Actual instantiations, specialization, layout, overload resolution, and boxing |
| SFINAE/concepts | Bounded generics, explicit overloads, factories, or generation | Rejected-program behavior and consumer diagnostics |
| `constexpr`/`consteval` | Constant, generated artifact, static validation, or startup calculation | Compile-time failure guarantee and build reproducibility |
| Macro constant | `static final`, enum, configuration, or generated value | Type, scope, conditional definition, and build-variant value |
| Function-like macro | Method/lambda/generator | Argument evaluation count, control flow, token operations, and source locations |
| Pimpl | Internal implementation boundary | Consumer/API stability intent; do not preserve pointer indirection automatically |

Translate the supported instantiated surface. A generic Java abstraction that compiles but
changes specialization or dispatch behavior is semantic drift.

## Errors and Control Flow

| C++ construct | Java 25 candidate | Required check |
|---|---|---|
| Exception | Typed checked/unchecked exception or result type | Catch boundaries, category, recovery, cause, and cleanup |
| Error/status code | Result type, exception, or preserved status at process/protocol boundary | Exact caller branching, partial output, and retry behavior |
| `errno`/last-error API | Immediate typed capture at adapter/native boundary | Thread-local timing and operation-specific meaning |
| `noexcept`/termination | Explicit fatal boundary or impossible-failure invariant | Whether termination is part of the observable contract |
| Assertion | Validation, invariant check, test assertion, or retained fatal check | Debug/release differences and external input handling |
| Coroutine/callback | Synchronous method, future, publisher, or callback | Suspension, cancellation, execution context, ordering, and backpressure |

Do not convert every C++ exception to an unchecked exception by style preference. The Java
API contract and the selected output profile determine error representation.

## Concurrency

| C++ construct | Java 25 candidate | Required check |
|---|---|---|
| `std::thread`/pthread | Platform or virtual thread, task executor, or retained native thread | CPU vs blocking work, affinity, priority, shutdown, and thread identity |
| `std::async`/future | `CompletableFuture`, executor task, or preview-approved structured concurrency | Launch policy, eager/lazy behavior, cancellation, and exception aggregation |
| Mutex/lock guard | `synchronized`, `Lock`, semaphore, or confinement | Reentrancy, fairness, interruptibility, condition usage, and lock order |
| Condition variable | `Condition`, monitor protocol, queue, latch, or higher-level primitive | Predicate loop, spurious wakeups, clock, notification semantics |
| Atomic/fence | `VarHandle`, atomic class, lock, or confinement | Width, compare/exchange, memory ordering, lock-freedom, and overflow |
| `thread_local` | Explicit task context, scoped value, or `ThreadLocal` with lifecycle | Inheritance, pooling, mutation, and cleanup; scoped values require lexical immutable context |

Virtual threads simplify some blocking workloads but do not preserve scheduling, affinity,
lock-freedom, or source memory-order guarantees automatically. Structured concurrency is a
Java 25 preview feature and requires the preview decision gate.

## Native and Platform Boundaries

- Prefer a supported Java implementation only after protocol, security, performance, and
  compatibility comparison.
- Use the Foreign Function & Memory API for an approved native bridge when ABI/layout and
  lifecycle can be tested; it does not make the dependency portable.
- A sidecar/compatibility process may provide safer isolation for unstable or unsafe native code.
- Replace preprocessor platform branches with separate adapters, packaging variants, or
  explicit runtime selection only when their behavior is characterized.
- Record unsupported operating systems, architectures, devices, and native dependencies as
  decisions/exceptions rather than silently dropping them.

## Output-Profile Placement

- **Service:** place Java framework code in service adapters/composition; keep module policy
  independent and follow the modular hexagonal service profile.
- **Library:** expose deliberate API and optional SPI; keep implementation internal and avoid
  forcing a runtime framework on consumers.
- **SDK:** apply library boundaries plus stability, consumer contracts, executable examples,
  and compatibility documentation.
- **CLI:** preserve command, stdout, stderr, exit-code, signal, and installed-package contracts;
  do not translate the CLI into a web service unless an approved product decision changes it.

## Rule Provenance

Shared metadata: `applicability` is semantic mapping under pair `cpp-to-java-25`; `source`
is the C++ semantic-hazard profile, Java 25 target policy, and characterized project behavior;
`owner` is pair profile `cpp-to-java-25`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `PAIR-CPP-JAVA25-001` | Source constructs encode intent beyond their syntax. | Pair review and traceability validation | Hazard finding, mapping decision, and behavior evidence | C++11-23 to JDK 25 |
| `PAIR-CPP-JAVA25-002` | DI scope does not model smart-pointer ownership or final-release side effects. | Pair review | Ownership map and cleanup tests | C++11-23 to JDK 25 |
| `PAIR-CPP-JAVA25-003` | Virtual threads and Java atomics do not automatically preserve the C++ memory model. | Concurrency gate | Happens-before analysis and stress/model tests | C++11-23 to JDK 25 |
