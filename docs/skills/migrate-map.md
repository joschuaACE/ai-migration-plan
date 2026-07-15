# migrate-map

Map C++ codebase structure to target Java hexagonal package layout — produces mapping.md that defines the structural transformation for every source file, class, struct, enum, and free function.

## When to Use

- During migrate-init (called automatically as part of initialization)
- With --refresh when inventory.md is updated after discovering new files
- When the mapping needs adjustment before planning

## Inputs

- **--refresh flag** (optional) — update existing mapping.md with new inventory entries
- **--style flag** (optional) — architecture variant:
  - `hexagonal` (default): single module, package-by-layer
  - `modular-hexagonal`: multi-module Gradle project, hexagonal within each

**Required state:**
- `.migration/inventory.md` must exist
- `.migration/config.json` must exist (for group_id, artifact_id, output_type)

**Context to read before starting:**
1. inventory.md → know all source files
2. config.json → get target group/artifact IDs and output_type
3. C++ source tree → understand namespace and directory structure

## Procedure

### Step 1: Analyze C++ Structure

1. Parse C++ namespace hierarchy from source files
2. Map C++ directories to logical modules
3. Identify the dependency graph between namespaces/directories
4. Classify each C++ construct by its nature:

| C++ Construct | Classification Criteria | Target Layer |
|--------------|------------------------|-------------|
| Pure algorithm/computation | No I/O, no external deps | domain/service |
| Data structure (struct/class with mostly fields) | Primarily data holder | domain/model |
| Abstract base class | Virtual methods, no implementation | domain/port/in or out |
| Database/file I/O class | Reads/writes external state | domain/port/out (interface) + adapter/out (impl) |
| Network client | Makes HTTP/gRPC/socket calls | domain/port/out (interface) + adapter/out/client (impl) |
| Request handler / CLI entry | Receives external commands | adapter/in/web (service) or adapter/in/cli (cli) or N/A (library/sdk) |
| Configuration parser | Reads config files/env | config/ (@ConfigurationProperties) |
| Test file | gtest/catch2/etc | src/test/java (mirror structure) |
| Enum definition | enum/enum class | domain/model (Java enum) |
| Constants / defines | #define, constexpr | domain/model (constants class) or config |
| Free utility functions | Stateless helpers | domain/service or application/usecase |
| Thread/executor setup | Threading infrastructure | config/ (executor bean) |
| Event/callback system | Observer pattern | domain/port/in + adapter/in/messaging |

### Step 2: Generate Package Mapping

For each C++ namespace/directory, determine the Java package:

```markdown
## Namespace Mapping
| C++ Namespace | Java Package | Hexagonal Layer |
|--------------|-------------|-----------------|
| core:: | com.company.app.domain.service | domain |
| data:: | com.company.app.domain.model | domain |
| db:: | com.company.app.adapter.out.persistence | adapter/out |
| net:: | com.company.app.adapter.out.client | adapter/out |
| api:: | com.company.app.adapter.in.web | adapter/in |
| config:: | com.company.app.config | config |
| util:: | com.company.app.domain.service | domain (or remove if JDK covers it) |
```

**Output type adjustments to mapping:**
- **library/sdk:** No `adapter/in/web` or `adapter/in/messaging` targets. Classes that would be controllers in a service instead become part of the public API surface (port/in interfaces). Export headers map to domain/port/in.
- **cli:** `adapter/in/web` becomes `adapter/in/cli`. HTTP handlers become CLI command classes.
- **service:** All targets available (default behavior).

### Step 3: Generate File-Level Mapping

For each file in inventory.md:

```markdown
## File Mapping
| C++ File | Java Target | Package | Layer | Notes |
|----------|------------|---------|-------|-------|
| src/core/Engine.h | EnginePort.java | ...domain.port.in | domain/port | Interface (abstract methods) |
| src/core/Engine.cpp | EngineService.java | ...domain.service | domain/service | Implementation |
| src/db/Store.h | StorePort.java | ...domain.port.out | domain/port | Driven port interface |
| src/db/Store.cpp | StorePersistenceAdapter.java | ...adapter.out.persistence | adapter/out | JPA implementation |
| src/api/Handler.cpp | ItemController.java | ...adapter.in.web | adapter/in | REST controller |
```

### Step 4: Identify Port Boundaries

Scan for classes that:
- Are called by many other modules → likely a **driven port** (out)
- Call into this module from outside → likely a **driving port** (in)
- Define abstract/virtual interfaces → natural port interfaces

**For library/sdk output_type:** Driving ports (port/in) are especially important as they define the library's PUBLIC API that consumers will call directly. These must be carefully designed, well-documented, and stable.

```markdown
## Port Identification
| C++ Interface | Port Type | Java Port | Implementations |
|--------------|-----------|-----------|-----------------|
| IDataStore (virtual) | Driven (out) | DataStorePort | JpaDataStoreAdapter |
| IEventBus (virtual) | Driven (out) | EventPublisherPort | SpringEventAdapter |
| IRequestHandler | Driving (in) | ProcessRequestUseCase | (controller calls this) |
```

### Step 5: Write mapping.md

Produce complete document with:
- Namespace → package mapping
- File → class mapping (every file)
- Port identification (interfaces that cross boundaries)
- Gradle module structure (if modular-hexagonal)
- Test file mapping (C++ test → Java test location)

### Step 6: Validate Mapping

- Every inventory.md file has a mapping entry
- No two C++ files map to the same Java file (unless explicitly merged)
- Hexagonal rules satisfied (domain has no adapter targets, etc.)
- Port interfaces correctly identified for cross-boundary calls

## Outputs

- `.migration/mapping.md` — complete structural transformation map

## Success Criteria

- Every file in inventory.md has a mapping entry
- Namespace → package mapping is complete
- Port boundaries identified (driving and driven)
- Hexagonal layer assignment is consistent (no domain → adapter confusion)
- Test file mapping included
- mapping.md written and validated
