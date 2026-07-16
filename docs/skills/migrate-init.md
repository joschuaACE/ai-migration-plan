# migrate-init

Initialize a C++ to Java migration project — scan source, detect tech, determine output type (service/library/sdk/cli), build inventory, gather decisions, generate roadmap, and create the target project skeleton.

## When to Use

Once, at the very start of a migration. This is the first command in the workflow. It must be run before any other migration skill.

## Inputs

- **Path to C++ source root** (required) — the directory containing .cpp/.h/.hpp files
- **--auto flag** (optional) — skip interactive questions, infer output type from build system, use defaults
- **--poc flag** (optional) — PoC mode. Scopes migration to calculation engine replacement only. Enables golden master validation. Skips full architecture questions.

## Procedure

### Phase 1: Source Scanning (Parallel Agents)

1. Verify source path exists and contains C++ files
2. If `.migration/` already exists, ask user to confirm overwrite
3. Create `.migration/` directory structure
4. Spawn 4 parallel scanner agents:
   - **Agent 1 (headers):** Scan all .h/.hpp files → classify by purpose (interface, implementation, config, types)
   - **Agent 2 (sources):** Scan all .cpp/.cc files → classify by purpose (entry point, library, test, utility)
   - **Agent 3 (build):** Analyze CMakeLists.txt/Makefile/vcxproj → extract targets, dependencies, compiler flags
   - **Agent 4 (tests):** Scan test directories → catalog test coverage, frameworks used
5. Each agent writes its section directly to `.migration/inventory.md`
6. Verify inventory.md has all files accounted for

Inventory entry format per file:
```markdown
| File | Type | LOC | Complexity | Dependencies | Phase |
|------|------|-----|-----------|--------------|-------|
| src/core/DataProcessor.cpp | source/core | 342 | 3 | DataStore.h, Logger.h | 3 |
```

### Phase 2: Technology Detection

7. Run the migrate-detect workflow (inline or as sub-task):
   - Scan #include directives for known libraries
   - Analyze build files for package manager dependencies
   - Detect C++ standard version from compiler flags
   - Identify platform-specific code (#ifdef blocks)
   - Write `.migration/research/legacy-stack.md`
   - Write `.migration/research/dependency-map.md` (each C++ dep → Java equivalent)
   - Write `.migration/research/risk-matrix.md` (risks ranked by migration difficulty)

### Phase 3: Architecture Decisions (Interactive unless --auto)

8. Ask user the following (one question at a time):
   - **If --poc flag is set:**
     - Skip database, API style, authentication, messaging, deployment questions
     - Set output_type = "library" (calculation engine is a library)
     - Ask only: purpose, group/artifact ID, and which C++ files constitute the calculation engine
     - Ask: where is the test data (ZOT variants) for golden master validation?
     - Ask: how to build and run the C++ engine to produce reference output?
     - Record decision D-01: "PoC mode — scope limited to calculation engine replacement"
   - What is the application's primary purpose?
   - **What does the C++ build produce?** (executable with network listeners → `service`, command-line tool → `cli`, .dll/.so/.a/static lib → `library`, library with public headers + versioned API → `sdk`). Record as `output_type`.
   - Group ID and Artifact ID for Gradle? (e.g., com.company.app)
   - **If output_type = service:**
     - Database technology target? (PostgreSQL/MySQL/MongoDB/none)
     - Does the app expose REST APIs? gRPC? Both?
     - Authentication mechanism? (Spring Security + OAuth2 / JWT / Basic / none)
     - Message broker needed? (Kafka/RabbitMQ/none)
     - Deployment target? (Container/K8s/bare metal/serverless)
   - **If output_type = library or sdk:**
     - Will consumers use Spring? (determines whether to include optional auto-configuration)
     - Should the library publish to Maven Central, GitHub Packages, or internal repo?
     - Any SPIs consumers must implement? (driven ports with no default adapter)
   - **If output_type = sdk (additionally):**
     - Versioning strategy? (semver strict / semver relaxed)
     - API stability level for initial release? (beta / stable)
   - **If output_type = cli:**
     - Argument parsing framework preference? (picocli / Spring Shell / plain args)
     - Target native image (GraalVM) or JVM JAR?
   - Any C++ components that should NOT be migrated? (FFI boundary?)
9. Record all decisions in `.migration/decisions.md` with D-NN numbering
10. Write `.migration/research/target-stack.md`

### Phase 4: Structure Mapping

11. Run the migrate-map workflow:
    - Map C++ namespaces → Java packages
    - Map C++ directories → hexagonal layers
    - Map C++ classes → Java class targets (service/entity/port/adapter)
    - Write `.migration/mapping.md`

### Phase 5: Roadmap Generation

12. Analyze dependency graph between C++ modules (who includes whom)
13. Order modules by dependency depth (leaf modules first)
14. Group into phases (one phase = one logical module or tightly-coupled cluster)
15. Write `.migration/roadmap.md` with:
    - Phase number, name, goal
    - Files included
    - Dependencies on other phases
    - Estimated complexity (1-5)
    - Status: Not Started
16. Write `.migration/tech-debt.md` (patterns that need redesign, not 1:1 port)

### Phase 6: Initialize State & Config

17. Write `.migration/config.json` with user decisions (output_type, java_version, spring_boot_version, architecture style, etc.)
18. Write `.migration/state.md` with YAML frontmatter:
    ```yaml
    ---
    migration_version: "1.0"
    source: "<detected C++ standard> / <detected build system>"
    target: "Spring Boot 4.0 / Java 25 / Hexagonal"
    output_type: "<service|library|sdk|cli>"
    architecture: hexagonal
    status: initialized
    active_phase: 0
    total_phases: <count from ROADMAP>
    progress:
      phases_complete: 0
      files_migrated: 0
      files_remaining: <total from INVENTORY>
    last_updated: "<now>"
    ---
    ```
19. Initialize project skeleton in target_root (default: `./app/`) based on `output_type`:

    **If --poc mode:**
    - Create `.migration/validation/` directory
    - Create `.migration/validation/test-variants.md` with selected ZOT variants
    - Create `.migration/validation/poc-config.json` with cpp_engine_path, cpp_engine_command, java_engine_command, test_data_path, comparison_format, tolerance
    - Add to state.md: `mode: poc`

    **If output_type = `service` (default):**
    - Create `{target_root}` directory
    - Generate build.gradle.kts with Spring Boot 4.x plugin + detected dependencies
    - Generate settings.gradle.kts with project name
    - Create Gradle wrapper (gradlew) — Gradle 9.3+
    - Create hexagonal package structure (domain/, application/, adapter/in/web/, adapter/out/, config/)
    - Create Application.java main class (`@SpringBootApplication`)
    - Create application.yml with basic config
    - Create ArchUnit test for hexagonal rules

    **If output_type = `library` or `sdk`:**
    - Create `{target_root}` directory
    - Generate build.gradle.kts with `java-library` + `maven-publish` plugins (NO Spring Boot plugin)
    - Generate settings.gradle.kts
    - Create Gradle wrapper (gradlew) — Gradle 9.3+
    - Create hexagonal package structure WITHOUT adapter/in/web/, adapter/in/messaging/, adapter/in/scheduler/
    - Create adapter/out/defaults/ for optional default SPI implementations
    - Create spi/ package for extension points
    - Do NOT create Application.java or application.yml
    - Create module-info.java with exports for public API packages
    - Create ArchUnit test (adapted: no adapter/in checks)
    - For `sdk` additionally: create samples/ directory, docs/ directory, annotation/ package with @Stable/@Beta/@Internal
    - Configure `withJavadocJar()` and `withSourcesJar()` in build.gradle.kts

    **If output_type = `cli`:**
    - Create `{target_root}` directory
    - Generate build.gradle.kts with `application` plugin + picocli dependency
    - Generate settings.gradle.kts
    - Create Gradle wrapper (gradlew) — Gradle 9.3+
    - Create hexagonal package structure with adapter/in/cli/ (no web/, no messaging/)
    - Create main class with picocli `@Command` entry point
    - Do NOT create application.yml (unless using Spring Shell)
    - Create ArchUnit test for hexagonal rules (adapted for CLI adapter)
    - Configure GraalVM native-image support if user opted in

20. Commit: `migrate(init): initialize migration project from <source_path>`

### Phase 7: Report & Next Steps

21. Display summary:
    - Total files: X (.cpp) + Y (.h/.hpp)
    - Total lines: N
    - Detected technologies: [list]
    - Phases generated: Z
    - Estimated complexity: [distribution]

### Phase 8: Source Architecture Graph (Graphify)

22. Run Graphify on the C++ source to capture baseline architecture:
    ```bash
    graphify {source_root} --mode deep
    ```
    - Deep mode captures INFERRED relationships (critical for C++ #include chains and macros)
    - Tree-sitter AST extraction handles .cpp/.h/.hpp natively
23. Move graph outputs to migration-managed location:
    ```bash
    mkdir -p .migration/graphs/source
    cp graphify-out/graph.json .migration/graphs/source/
    cp graphify-out/GRAPH_REPORT.md .migration/graphs/source/
    cp graphify-out/graph.html .migration/graphs/source/ 2>/dev/null || true
    ```
24. Extract architecture insights from GRAPH_REPORT.md:
    - **God Nodes** → highest-coupled C++ components, these need careful migration
    - **Communities** → natural module boundaries, validate against roadmap phase grouping
    - **Surprising Connections** → hidden coupling that could break during migration
25. Cross-reference graphify communities against roadmap.md phases:
    - If a community spans multiple phases → WARN: tight coupling across phase boundary
    - If a phase spans multiple communities → INFO: phase may be larger than needed
    - Write alignment report to `.migration/graphs/source/phase-alignment.md`
    - If significant misalignment, suggest roadmap adjustments to user
26. Write `.migration/graphs/source/architecture-insights.md` summarizing god nodes, communities, and surprising connections
27. Commit: `migrate(init): add source architecture graph`
28. Suggest next step: "Run migrate-analyze 1 to begin analyzing the first phase"
    - If --poc mode: also suggest "Run migrate-golden-master to validate functional equivalence"

## Outputs

- `.migration/state.md` — migration state tracker
- `.migration/roadmap.md` — ordered phases
- `.migration/inventory.md` — classified file inventory
- `.migration/decisions.md` — architecture decision log
- `.migration/mapping.md` — C++ → Java structure map
- `.migration/tech-debt.md` — patterns requiring redesign
- `.migration/config.json` — migration configuration
- `.migration/research/legacy-stack.md` — detected technologies
- `.migration/research/target-stack.md` — target architecture
- `.migration/research/risk-matrix.md` — migration risks
- `.migration/research/dependency-map.md` — library migration paths
- `{target_root}` — target project skeleton (build.gradle.kts, Gradle wrapper, hexagonal package structure, ArchUnit test)
- `.migration/graphs/source/graph.json` — Graphify knowledge graph of C++ source
- `.migration/graphs/source/graph.html` — Interactive graph visualization
- `.migration/graphs/source/GRAPH_REPORT.md` — God nodes, communities, surprising connections
- `.migration/graphs/source/architecture-insights.md` — Migration-relevant architecture insights
- `.migration/graphs/source/phase-alignment.md` — Graphify communities vs roadmap phase alignment
- If --poc: `.migration/validation/poc-config.json` and `.migration/validation/test-variants.md`

## Success Criteria

- .migration/ directory created with all required files
- inventory.md has EVERY .cpp/.h/.hpp file classified
- legacy-stack.md has all detected technologies with migration paths
- decisions.md has numbered architecture decisions (including output_type decision)
- mapping.md maps C++ structure to hexagonal Java packages
- roadmap.md has dependency-ordered phases covering all source files
- state.md initialized with correct counts and output_type
- config.json has valid configuration with output_type set
- Project skeleton matches output_type (service→Spring Boot app, library→java-library JAR, sdk→library+docs, cli→application plugin)
- Skeleton project compiles (`cd app && ./gradlew compileJava` succeeds)
- ArchUnit hexagonal test exists and passes (trivially, empty project)
- User knows the next step
- If --poc: validation directory created with poc-config.json and test-variants.md
