# C++ to Java 25 Dependency Candidates

This catalog supplies investigation candidates, not automatic replacements. Dependency
selection is project- and output-profile-specific. Preserve protocols, data, failure modes,
security properties, licensing, deployment support, and performance constraints before
preferring an ecosystem convention.

For every detected dependency, record its version, linked targets, used API subset, license,
platforms, native assets, observable formats/protocols, security ownership, and disposition:
replace, retain behind a native boundary, isolate in a compatibility process, remove as dead,
or block pending a decision.

## Networking and RPC

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| Boost.Asio / libevent / libuv | `java.nio`, virtual-thread blocking I/O, Netty | Completion ordering, event-loop affinity, cancellation, backpressure, timers, UDP, native transports |
| Boost.Beast / cpp-httplib / cpp-netlib | JDK HTTP/WebSocket APIs, framework client/server adapter, Netty | Client vs server surface, streaming, HTTP versions, TLS, proxy, compression, timeout behavior |
| libcurl | `java.net.http.HttpClient`, Apache HttpComponents, selected framework client | Every enabled curl feature: redirects, cookies, proxy, auth, TLS, multipart, callbacks, streaming |
| gRPC C++ | grpc-java plus the same protobuf contracts | Code-generation/plugin versions, status metadata, deadlines, streaming/backpressure, interceptors |
| ZeroMQ/cppzmq | JeroMQ, native binding, or protocol redesign | Socket pattern, high-water marks, multipart frames, identity, native interoperability, performance |
| POCO Net | JDK APIs or selected service adapter | Used subset rather than library brand |

Virtual threads are an execution choice, not a network-library equivalent. Benchmark and
test scheduling/cancellation semantics before changing an event-driven design.

## Serialization and Schemas

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| Protocol Buffers | protobuf-java / grpc-java code generation | Exact schema, unknown fields, presence/defaults, generated-version compatibility, deterministic encoding |
| FlatBuffers | Official Java runtime/code generation | Schema/compiler alignment, unsigned values, buffer ownership, byte order |
| Cap'n Proto | Maintained Java implementation or compatibility service | Ecosystem maturity, schema support, zero-copy assumptions, interoperability fixtures |
| nlohmann/json / RapidJSON / simdjson | Jackson, JSON-P, Gson, or a focused parser | Duplicate keys, number precision, ordering, comments, invalid UTF, unknown fields, canonical output |
| cereal / Boost.Serialization | Explicit schema plus selected codec | Type/version metadata, object identity, polymorphism, archives, backward compatibility |
| pugixml / TinyXML-2 | JAXP/StAX, JAXB implementation, Jackson XML | Entity/DTD policy, namespaces, whitespace, ordering, security hardening |
| yaml-cpp | SnakeYAML Engine or Jackson YAML | YAML version/schema, duplicate keys, tags, anchors, unsafe construction |
| MessagePack | msgpack-java or explicit compatibility adapter | Integer widths, extension types, map order, canonical bytes |

Run byte-level golden and cross-runtime compatibility tests. “Both produce JSON/XML” is not
evidence of the same contract.

## Data Stores

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| SQLite C API | SQLite JDBC/native bridge | Existing file compatibility, locking, pragmas, extensions, transactions; do not substitute H2 silently |
| libpq / MySQL client | JDBC driver, selected data adapter, or reactive driver if required | SQL dialect, types, encoding, transaction/isolation, prepared statements, cancellation, pooling |
| ODBC | Vendor JDBC driver or retained ODBC bridge | Driver feature set, DSN/auth, type conversion, stored procedures, supported platform |
| mongocxx | MongoDB Java driver | Codec behavior, sessions, read/write concerns, retry semantics, change streams |
| hiredis / cpp-redis | Lettuce, Jedis, or selected service adapter | Cluster/sentinel, pipelines, scripts, binary keys, pub/sub ordering, timeout/reconnect |
| RocksDB / LevelDB / LMDB | Maintained Java binding or storage redesign | On-disk compatibility, native packaging, iterators/snapshots, transactions, compaction, backup |

An ORM is an architecture decision, not a direct client-library replacement. Preserve query,
transaction, locking, and data compatibility before introducing one.

## Logging and Observability

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| spdlog / glog / Boost.Log / log4cxx | SLF4J API with an output-profile-selected backend | Severity mapping, structured fields, async loss policy, file rotation, formatting, audit guarantees |
| Metrics/tracing library | Output-profile-selected OpenTelemetry/Micrometer or direct API | Metric type/unit/cardinality, trace propagation, sampling, exporter failure behavior |

Libraries and SDKs should normally expose at most a logging API and allow consumers to choose
the backend. Services and CLIs select packaging-specific backends.

## Tests and Benchmarks

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| gtest/gmock | JUnit Jupiter, AssertJ, Mockito where interaction mocking is useful | Fatal/nonfatal assertions, fixtures, death tests, custom matchers, typed/parameterized suites |
| Catch2 / doctest | JUnit Jupiter plus assertion library | Section/subcase re-entry semantics, generators, tags, reporters |
| Boost.Test / CppUnit | JUnit Jupiter plus assertion library | Registration, fixtures, data suites, result reporting |
| Google Benchmark / Celero | JMH | Warmup, forks, dead-code elimination, parameters, native comparison methodology |

Port behavioral intent, not test count or one-to-one method layout. Preserve source test
results as characterization evidence.

## Cryptography and Security

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| OpenSSL / mbedTLS | JCA/JCE/JSSE provider APIs, Bouncy Castle when required, or retained native boundary | Algorithm/provider, key formats, TLS versions/ciphers, verification, FIPS requirements, error behavior |
| libsodium | Maintained binding, Tink for an approved redesign, or JCA primitive | Exact construction/protocol compatibility; high-level APIs are not interchangeable |
| Botan / Crypto++ | JCA/JCE plus approved provider | Algorithm/mode/padding, RNG, constant-time and provider compliance |

Never replace a cryptographic construction by name similarity. Require a security review and
known-answer/interoperability tests; record provider and policy requirements.

## Concurrency and Parallelism

| C++ dependency/construct | Java 25 candidates | Selection checks |
|---|---|---|
| `std::thread` / pthread / Boost.Thread | Platform or virtual thread, executor | Blocking vs CPU work, affinity, priority, cancellation, identity, shutdown |
| mutex / condition variable | Monitor, `Lock`/`Condition`, queue or higher-level synchronizer | Reentrancy, fairness, interruptibility, predicate, time source, lock order |
| C++ atomics | Atomic classes, `VarHandle`, lock, or confinement | Width, memory order, fences, CAS behavior, lock-free assumption |
| `std::async` / futures | `CompletableFuture`, executor task, preview-approved structured concurrency | Launch policy, aggregation, cancellation, exception propagation |
| OpenMP / oneTBB | Fork/join, parallel stream, executor, vector/native implementation | Scheduling, determinism, reductions, locality, nested parallelism, performance |

## Compression, Files, and Native Memory

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| zlib | `java.util.zip` | Wrapper format, level, dictionary, checksums, concatenated members, error behavior |
| LZ4 / Zstandard / Snappy | Maintained Java/native binding | Frame vs block format, native packaging, dictionary/version compatibility |
| bzip2 / archive formats | Apache Commons Compress or selected codec | Metadata, permissions, symlinks, path traversal, streaming |
| `std::filesystem` / Boost.Filesystem | `java.nio.file` | Symlinks, case, permissions, atomic moves, locks, error categories, path encoding |
| `mmap` / shared memory | `FileChannel` mapping, FFM, compatibility process, or redesign | Visibility, durability, unmapping/lifetime, layout, cross-process synchronization |

## Math, Media, and Native Compute

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| Eigen / Armadillo | ojAlgo, Commons Math, ND4J, or native binding | Supported operations, precision, layout, vectorization, sparse behavior, performance |
| BLAS/LAPACK / FFTW | Java library or approved native binding | ABI/provider, strides/layout, thread count, rounding, reproducibility |
| OpenCV | OpenCV Java bindings or selected Java imaging library | Native packaging, module coverage, matrix ownership, codec/platform support |

Performance-sensitive replacements require representative benchmarks and numeric tolerances,
not ecosystem popularity.

## CLI, GUI, IPC, and Platform APIs

| C++ dependency | Java 25 candidates | Selection checks |
|---|---|---|
| CLI11 / cxxopts / Program_options / getopt | Picocli or explicit parser | Exact command, defaults, errors, help, streams, exit codes, shell behavior |
| Qt / wxWidgets / GTK / ImGui | Java UI toolkit, retained native UI, or separately approved product redesign | Interaction/accessibility, rendering, platform integration, packaging; web replacement is not automatic |
| D-Bus | Maintained D-Bus binding or compatibility process | Type/signature mapping, bus policy, activation, signals, platform support |
| Win32 / POSIX APIs | JDK API, FFM/native adapter, or platform-specific target module | Used capability, security model, missing semantics, deployment platform |
| Dynamic libraries/plugins | ServiceLoader, explicit registry, native loader, or compatibility process | Discovery order, isolation, ABI/API compatibility, lifecycle, trust/signing |

## Configuration

| C++ dependency/format | Java 25 candidates | Selection checks |
|---|---|---|
| INI/libconfig | Focused parser or output-profile configuration adapter | Duplicate keys, ordering, comments, interpolation, encoding, write-back fidelity |
| TOML | Maintained TOML parser | TOML version, date/time and integer semantics, dotted keys |
| YAML | SnakeYAML Engine or Jackson YAML | Schema/tags, anchors, duplicate keys, safe construction |
| Environment/flags | Output-profile configuration boundary | Precedence, empty vs missing, secret redaction, reload behavior |

## Selection Record

For each project dependency, produce a decision with:

- source dependency/version/license and stable inventory IDs;
- used capabilities and observable contracts;
- candidate evaluation and rejected alternatives;
- selected Java coordinates or retained native artifact, with owner/version policy;
- output-profile placement and exposed/transitive dependency impact;
- security, integrity, platform, and packaging checks;
- compatibility fixtures and performance evidence where applicable; and
- rollback, upgrade, and unsupported-platform policy.

## Rule Provenance

Shared metadata: `applicability` is dependency selection under pair `cpp-to-java-25`;
`source` is the C++ dependency inventory plus authoritative candidate-library/protocol
documentation reviewed by the project; `owner` is pair profile `cpp-to-java-25`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `PAIR-CPP-JAVA25-DEP-001` | Library names do not describe the used semantic subset. | Dependency-decision validator | Used-capability inventory and candidate evaluation | C++ to JDK 25 profile v2 |
| `PAIR-CPP-JAVA25-DEP-002` | Format/protocol compatibility needs byte-level evidence. | Compatibility gate | Cross-runtime golden/interoperability results | C++ to JDK 25 profile v2 |
| `PAIR-CPP-JAVA25-DEP-003` | A native binding retains ABI, supply-chain, and deployment risk. | Native-boundary review | ABI/platform/package evidence and owner | C++ to JDK 25 profile v2 |
