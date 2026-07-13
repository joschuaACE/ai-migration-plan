# C++ Semantic Hazard Analysis

C++ behavior depends on the language standard, compiler, ABI, flags, platform, linked
libraries, build configuration, and runtime inputs. Analyze every supported build variant
before claiming a portable contract. A successful run on one toolchain is evidence for that
environment only.

## Classification Policy

Classify each hazard as:

| Class | Meaning | Migration policy |
|---|---|---|
| Specified | The applicable standard and program define the outcome. | Preserve the observable contract. |
| Implementation-defined | The implementation chooses and documents an outcome. | Record compiler/ABI/platform and decide whether to preserve or normalize. |
| Unspecified | Several outcomes are allowed without documentation. | Do not depend on one observed ordering/value without an approved normalization. |
| Undefined | The standard imposes no requirements after the operation. | Never claim general equivalence; isolate, characterize observed environments, then normalize, remove, or block. |
| Environment-dependent | External locale, clock, filesystem, network, configuration, or dependency changes the outcome. | Capture the environment and make the target dependency explicit. |

Every finding includes source location, reachable callers, build variants, current evidence,
consumer impact, selected disposition, and traceability IDs.

## Build Variants and Translation Units

Inspect the actual compile database or equivalent per supported configuration. Record:

- compiler family/version, language standard, target triple, ABI, and standard library;
- optimization, sanitizers, exception/RTTI settings, floating-point mode, and warning policy;
- preprocessor definitions, forced includes, include ordering, generated headers, and PCH/modules;
- architecture, endianness, word size, alignment/packing flags, and calling conventions;
- static/shared linkage, link order, symbol visibility, weak symbols, and LTO; and
- debug/release, feature, customer, platform, and test-only variants.

A source file compiled under two macro sets is two semantic variants. Do not merge them in
the inventory until their observable behavior is proven equivalent.

## Numeric and Data-Model Hazards

Check:

- width and signedness of fundamental types, especially plain `char`, `long`, enums, and `size_t`;
- signed overflow, invalid shifts, division edge cases, narrowing, and implicit conversions;
- unsigned wraparound and mixed signed/unsigned comparison;
- floating-point precision, evaluation order, contraction/FMA, rounding mode, NaN payloads,
  signed zero, infinities, denormals, and tolerance policy;
- integral promotions in variadic calls and format-string/type mismatches;
- endianness, alignment, padding, bit fields, unions, packed structures, and raw object bytes; and
- assumptions in hashes, binary formats, checksums, random generation, and pointer-to-integer casts.

Do not map a numeric type by spelling alone. Derive required range, overflow behavior,
serialization width, and performance constraints from callers and protocols.

## Ownership, Lifetime, and RAII

Inventory every owned and borrowed resource: heap memory, file descriptors/handles, locks,
sockets, mappings, transactions, callbacks, native buffers, and library contexts.

Look for:

- raw pointers/references whose ownership is implicit;
- `unique_ptr`, `shared_ptr`, `weak_ptr`, aliasing constructors, custom deleters, and cycles;
- views (`string_view`, `span`, iterators, references) that may outlive storage;
- move-from assumptions, self-move, copy elision, and destructor side effects;
- iterator/reference invalidation after container mutation;
- exception paths between acquisition and release;
- order of local, member, base, static, and thread-local destruction;
- static initialization order across translation units; and
- placement `new`, manual lifetime management, pools, arenas, and intrusive containers.

Garbage collection does not replace deterministic release. Translate timing-sensitive RAII
to an explicit scoped-lifecycle construct and test success, exception, cancellation, and
partial-construction paths. Preserve ownership semantics even when memory reclamation differs.

## Object Model, Templates, and Macros

Analyze:

- virtual dispatch, RTTI, covariant returns, slicing, multiple/virtual inheritance, and downcasts;
- layout-dependent casts, strict aliasing, provenance, `memcpy` object construction, and unions;
- templates instantiated by supported builds, specializations, SFINAE, concepts, CRTP,
  expression templates, and compile-time generated tables;
- `constexpr`, `consteval`, static assertions, and build-time validation that must move to a
  target compile, generation, or startup check;
- macros with repeated evaluation, token pasting/stringification, statement-like control
  flow, conditional declarations, and generated identifiers; and
- generated sources whose generator, inputs, and version are part of the real source of truth.

Translate instantiated behavior, not an imagined generic equivalent. Preserve macro argument
evaluation count and conditional surfaces or approve a normalization.

## Errors and Control Flow

Record the complete error model:

- exceptions, exception specifications, `noexcept`, and terminate behavior;
- status codes, sentinels, `errno`, thread-local error APIs, and out parameters;
- assertion/abort behavior and differences between debug and release;
- cleanup during stack unwinding and exceptions crossing module/ABI boundaries;
- `setjmp`/`longjmp`, signals, callbacks, coroutine suspension, and cancellation; and
- partially written output or committed state before failure.

Do not translate every nonzero result to one exception type. Preserve category, recoverability,
side effects, and caller control flow at the public boundary.

## Concurrency and Memory Model

Identify thread entry points, executors, affinity, thread-local state, locks, atomics, signals,
and shared mutable objects. For each shared access, record synchronization and happens-before
assumptions.

Pay special attention to:

- data races (undefined behavior), benign-race claims, and double-checked initialization;
- atomic width, lock-freedom assumptions, memory order, fences, and compare/exchange loops;
- condition-variable predicates, spurious wakeups, lost notifications, and timeout clocks;
- lock ordering, recursive locks, upgrade/downgrade behavior, and reentrancy;
- callback execution context, thread affinity, and destructor-driven join/detach;
- concurrent container and iterator guarantees;
- cancellation, interruption, shutdown, and work accepted during drain; and
- fork/signal safety and synchronization performed from signal handlers.

Matching final outputs is insufficient if visibility, atomicity, ordering, deadlock, or
cancellation guarantees changed. Use stress/model tests where ordinary examples cannot
exercise the contract.

## ABI, Native, and Dependency Boundaries

Treat these as high-risk until proven otherwise:

- exported symbols, name mangling, `extern "C"`, calling conventions, visibility, and version scripts;
- public struct/class layout, vtables, inline functions, allocator ownership across modules,
  and exceptions crossing shared-library boundaries;
- callbacks/function pointers, userdata lifetime, dynamically loaded plugins, and symbol lookup;
- JNI or other foreign runtimes already embedded in the source;
- native dependencies without a target replacement, licensing constraints, or platform gaps; and
- protocols implemented through raw memory, vendor headers, or undocumented device behavior.

Choose deliberately among replacement, a compatibility process, a maintained native bridge,
or an unsupported-platform decision. A native bridge retains ABI, memory-safety, packaging,
and deployment risks; it is not a zero-cost direct mapping.

## Serialization, Text, Filesystem, and Platform Behavior

Characterize byte-level output and parsing rules:

- charset, invalid-byte handling, BOM, embedded NUL, normalization, case mapping, and locale;
- line endings, path separators, path encoding, case sensitivity, symlinks, permissions,
  atomic rename, file locking, sparse files, and memory mapping;
- field width/order, padding, delimiters, escaping, schema/default evolution, unknown fields,
  and deterministic map iteration;
- timestamp units, clock source, time zone, daylight-saving behavior, and precision;
- network framing, timeout, DNS, proxy, TLS, retry, partial reads/writes, and backpressure; and
- platform conditional branches with no portable fallback.

Golden files must state the platform and normalization rules. Never normalize a difference
that consumers can observe without an approved decision.

## Required Evidence

For reachable high-risk findings, gather the strongest practical combination of:

- source test results across supported build variants;
- compiler warnings and static analysis;
- address, undefined-behavior, thread, and memory sanitizer results where supported;
- golden-master or differential cases including failure and boundary values;
- ABI/symbol/layout reports for exported native surfaces;
- representative platform and architecture runs; and
- an approved decision when behavior cannot be safely preserved.

Absence of a tool or supported runtime is an evidence gap or exception, not a pass.

## Rule Provenance

Shared metadata: `applicability` is every migration selecting the C++ source profile;
`source` is the applicable ISO C++ standard plus supported compiler/ABI documentation;
`owner` is source profile `cpp`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `SRC-CPP-HAZ-001` | C++ semantics can vary across translation-unit configuration and ABI. | Source-profile analyzer | Per-variant compile metadata | C++11 through C++23 profile |
| `SRC-CPP-HAZ-002` | Undefined behavior cannot support a portable equivalence claim. | Finding/disposition validator | Reachability, environment observations, and approved disposition | C++11 through C++23 profile |
| `SRC-CPP-HAZ-003` | Automatic memory reclamation does not preserve deterministic resource lifetime. | Review and lifecycle tests | Ownership map and cleanup-path results | C++11 through C++23 profile |
| `SRC-CPP-HAZ-004` | Concurrency equivalence includes ordering and visibility, not just outputs. | Concurrency gate | Memory-order analysis and stress/model evidence | C++11 through C++23 profile |
