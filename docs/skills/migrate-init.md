# migrate-init

Initialize a C++ to Java migration project — understand the source codebase (structure, domains, architecture), detect tech, determine output type (service/library/sdk/cli), build inventory, gather decisions, generate roadmap, and create the target project skeleton.

## Prerequisites

**Understand-Anything** (https://github.com/Egonex-AI/Understand-Anything) must be installed:

```bash
# Kiro CLI
curl -fsSL https://raw.githubusercontent.com/Egonex-AI/Understand-Anything/main/install.sh | bash -s kiro
```

Requires Node.js >= 18. Makes `/understand`, `/understand-domain`, `/understand-onboard`, `/understand-chat` available as skills.

**Graphify** (https://github.com/Graphify-Labs/graphify) must be installed:

```bash
pip install graphifyy   # or: pipx install graphifyy
```

Requires Python 3.10+. The `graphify` CLI must be on PATH.

## When to Use

Once, at the very start of a migration. This is the first command in the workflow. It must be run before any other migration skill.

## Inputs

- **Path to C++ source root** (required) — the directory containing .cpp/.h/.hpp files
- **--auto flag** (optional) — skip interactive questions, infer output type from build system, use defaults
- **--poc flag** (optional) — PoC mode. Scopes migration to calculation engine replacement only. Enables golden master validation. Skips full architecture questions.
- **--language** (optional) — output language for UA-generated documents (default: auto-detect, typically `de` for DATEV)
- **--skip-dashboard** (optional) — skip launching the interactive UA dashboard at the end of Phase 1

## Procedure

### Phase 1: Scan + Understand

This phase combines source scanning with deep codebase understanding. It runs the Understand-Anything (UA) pipeline and Graphify analysis to produce a comprehensive understanding baseline before any migration decisions are made.

#### Step 1.1: Validate & Initialize

1. Verify source path exists and contains C++ files (.cpp, .h, .hpp, .cc, .hh)
2. If `.migration/` already exists, ask user to confirm overwrite
3. Count total files and LOC — report to user
4. If > 500 files, suggest scoping to a subdirectory for first pass
5. Create `.migration/` directory structure
6. Create `.migration/understanding/` directory

#### Step 1.2: Source Scanning (Parallel Agents)

7. Spawn 4 parallel scanner agents:
   - **Agent 1 (headers):** Scan all .h/.hpp files → classify by purpose (interface, implementation, config, types)
   - **Agent 2 (sources):** Scan all .cpp/.cc files → classify by purpose (entry point, library, test, utility)
   - **Agent 3 (build):** Analyze CMakeLists.txt/Makefile/vcxproj → extract targets, dependencies, compiler flags
   - **Agent 4 (tests):** Scan test directories → catalog test coverage, frameworks used
8. Each agent writes its section directly to `.migration/inventory.md`
9. Verify inventory.md has all files accounted for

Inventory entry format per file:
```markdown
| File | Type | LOC | Complexity | Dependencies | Phase |
|------|------|-----|-----------|--------------|-------|
| src/core/DataProcessor.cpp | source/core | 342 | 3 | DataStore.h, Logger.h | 3 |
```

#### Step 1.3: Run Understand-Anything Pipeline

10. Run the full UA pipeline on the source:
    ```
    /understand {source_path} --language de
    ```
    This invokes UA's multi-agent pipeline:
    - `project-scanner` → discovers files, languages, frameworks
    - `file-analyzer` → extracts functions, classes, imports, produces graph nodes
    - `architecture-analyzer` → assigns architectural layers
    - `tour-builder` → generates dependency-ordered learning tours
    - `graph-reviewer` → validates graph completeness

11. Run domain extraction:
    ```
    /understand-domain
    ```
    This produces the business domain mapping: domains, flows, process steps.
    Critical for legacy code where business logic is buried in implementation.

12. Run onboarding guide generation:
    ```
    /understand-onboard
    ```
    Produces a structured guide for new team members.

13. Copy UA outputs to migration directory:
    ```bash
    mkdir -p .migration/understanding/dashboard
    mkdir -p .migration/understanding/tours
    cp .ua/knowledge-graph.json .migration/understanding/
    cp .ua/domain-graph.json .migration/understanding/ 2>/dev/null || true
    cp .ua/domain-map.md .migration/understanding/ 2>/dev/null || true
    cp .ua/onboarding.md .migration/understanding/ 2>/dev/null || true
    cp -r .ua/tours/* .migration/understanding/tours/ 2>/dev/null || true
    ```

14. Extract layer assignments from UA knowledge graph:
    - Parse `knowledge-graph.json` → for each node, extract `layer` field
    - Write `.migration/understanding/layer-assignments.json`:
      ```json
      {
        "src/core/DataProcessor.cpp": "Service",
        "src/api/Handler.h": "API",
        "src/db/Storage.cpp": "Data",
        "src/util/Logger.cpp": "Utility"
      }
      ```

#### Step 1.4: Run Graphify Deep Analysis

15. Run Graphify deep analysis on the source:
    ```bash
    graphify {source_path} --mode deep
    ```
    Deep mode captures INFERRED relationships (critical for C++ #include chains and macros).
    Tree-sitter AST extraction handles .cpp/.h/.hpp natively.
    This produces:
    - Community detection (Leiden algorithm) → natural module boundaries
    - God nodes → highest coupling (migration risk indicators)
    - Surprising connections → hidden cross-module dependencies
    - Edge confidence tiers (EXTRACTED/INFERRED/AMBIGUOUS)

16. Copy Graphify outputs:
    ```bash
    mkdir -p .migration/graphs/source
    cp graphify-out/graph.json .migration/understanding/
    cp graphify-out/graph.html .migration/understanding/
    cp graphify-out/GRAPH_REPORT.md .migration/understanding/
    cp graphify-out/graph.json .migration/graphs/source/
    cp graphify-out/GRAPH_REPORT.md .migration/graphs/source/
    cp graphify-out/graph.html .migration/graphs/source/ 2>/dev/null || true
    ```

#### Step 1.5: Cross-Reference Analysis

17. Load both graphs and compare:
    - **Layer↔Community alignment**: Do Graphify communities map to UA layers?
      - Community mostly "Service" layer → cohesive service module
      - Community spanning "API" + "Service" + "Data" → vertical slice (may be one phase)
      - Community spanning unrelated layers → possible architectural smell
    - **Domain↔Community alignment**: Do business domains map to communities?
      - One domain = one community → clean domain separation
      - One domain spans many communities → domain logic is scattered
    - **God nodes by layer**: Are coupling hotspots in expected places?
      - God node in "Utility" → normal (shared helpers)
      - God node in "Service" → potential design issue, needs careful migration
      - God node in "Data" → data access bottleneck

18. Write `.migration/understanding/architecture-insights.md`:
    ```markdown
    # Architecture Insights (Combined Analysis)

    ## System Overview
    - Total files: X
    - Total LOC: Y
    - Languages: C++ ({standard})
    - Architectural layers detected: {from UA}
    - Natural communities detected: {from Graphify}

    ## Module Boundaries
    | Graphify Community | UA Layer(s) | Files | Coupling (edges) | Assessment |
    |---|---|---|---|---|
    | Community 0: "{label}" | Service, Data | 15 | 23 internal, 8 external | Clean module |
    | Community 1: "{label}" | API, Service | 12 | 18 internal, 15 external | Vertical slice |

    ## Coupling Hotspots (God Nodes)
    | File | Degree | Layer | Community | Risk |
    |------|--------|-------|-----------|------|
    | {from Graphify god nodes + UA layer} | | | | |

    ## Business Domains Detected
    | Domain | UA Flow Steps | Graphify Community | Files |
    |--------|--------------|-------------------|-------|
    | {from UA domain extraction cross-referenced with Graphify} | | | |

    ## Hidden Dependencies (Surprising Connections)
    | From | To | Confidence | Risk to Migration |
    |------|-----|-----------|-------------------|
    | {from Graphify surprising connections} | | | |

    ## Recommended Migration Approach
    - Phase grouping suggestion: {based on community boundaries}
    - Start with: {lowest-coupling community / leaf modules}
    - High-risk areas: {god nodes that need extra analysis}
    - Domain alignment: {which business domains to keep together}
    ```

19. Write `.migration/graphs/source/phase-alignment.md` — initial alignment assessment (will be refined in Phase 5 after roadmap generation)

#### Step 1.6: Generate Executive Summary

20. Write `.migration/understanding/understanding-summary.md`:
    ```markdown
    # Understanding: {project_name}

    ## What This System Does
    {From UA onboarding guide — 2-3 paragraph business-level summary}

    ## Architecture at a Glance
    - {N} modules (communities) with {M} cross-module connections
    - Layers: {from UA — API/Service/Data/Utility distribution}
    - Business domains: {from UA domain extraction}

    ## Migration Complexity Assessment
    - Coupling density: {total edges / total nodes — low/medium/high}
    - God nodes (high-risk): {count} files with >10 connections
    - Hidden dependencies: {count} surprising cross-module connections
    - Dead code candidates: {nodes with 0 incoming edges and non-API layer}

    ## Explore Interactively
    - Open UA dashboard: `npx understand-anything-viewer .`
    - Open Graphify visualization: open `.migration/understanding/graph.html` in browser
    - Ask questions: `/understand-chat "How does X work?"`
    - Trace paths: `graphify query "connection between A and B"`
    ```

#### Step 1.7: Interactive Dashboard (Optional)

21. Unless `--skip-dashboard` flag is set, offer to launch the UA interactive dashboard:
    ```
    "Understanding complete. Open the interactive dashboard? (recommended)"
    ```
    If yes:
    ```bash
    npx understand-anything-viewer {source_path}
    ```
    This opens the browser with the full interactive knowledge graph.

22. Display the executive summary in the terminal.

### Phase 2: Technology Detection

23. Run the migrate-detect workflow (inline or as sub-task):
    - Scan #include directives for known libraries
    - Analyze build files for package manager dependencies
    - Detect C++ standard version from compiler flags
    - Identify platform-specific code (#ifdef blocks)
    - Write `.migration/research/legacy-stack.md`
    - Write `.migration/research/dependency-map.md` (each C++ dep → Java equivalent)
    - Write `.migration/research/risk-matrix.md` (risks ranked by migration difficulty)

Note: This phase can leverage UA's `project-scanner` output from Phase 1 to avoid re-scanning files.

### Phase 3: Architecture Decisions (Interactive unless --auto)

24. Ask user the following (one question at a time):
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
25. Record all decisions in `.migration/decisions.md` with D-NN numbering
26. Write `.migration/research/target-stack.md`

### Phase 4: Structure Mapping

27. Run the migrate-map workflow, informed by Phase 1 understanding artifacts:
    - Map C++ namespaces → Java packages
    - Map C++ directories → hexagonal layers — **use `.migration/understanding/layer-assignments.json` as the primary input** (UA has already classified each file's architectural role)
    - Map C++ classes → Java class targets (service/entity/port/adapter) — **use Graphify communities to identify natural module boundaries**
    - Where UA layer assignments and Graphify communities disagree, flag for manual review
    - Write `.migration/mapping.md`

### Phase 5: Roadmap Generation

28. Analyze dependency graph between C++ modules (who includes whom)
29. Order modules by dependency depth (leaf modules first)
30. Group into phases (one phase = one logical module or tightly-coupled cluster)
    - **Use Graphify community boundaries as the primary grouping signal** — files in the same community belong in the same phase
    - **Use UA domain names for phase naming** instead of generic "Phase 1, 2, 3"
    - Validate that no phase splits a Graphify community unless there is a compelling dependency-order reason
    - If a community spans multiple dependency depths, split into sub-phases but keep them adjacent in the roadmap
31. Cross-reference roadmap phases against Graphify communities:
    - If a community spans multiple phases → WARN: tight coupling across phase boundary
    - If a phase spans multiple communities → INFO: phase may be larger than needed
    - Write alignment report to `.migration/graphs/source/phase-alignment.md` (update from Phase 1 preliminary)
    - If significant misalignment, suggest roadmap adjustments to user
32. Write `.migration/roadmap.md` with:
    - Phase number, name (from UA domains), goal
    - Files included
    - Graphify community alignment
    - Dependencies on other phases
    - Estimated complexity (1-5)
    - God nodes in this phase (from Graphify — flagged as "needs extra analysis")
    - Status: Not Started
33. Write `.migration/tech-debt.md` (patterns that need redesign, not 1:1 port)

### Phase 6: State & Config

34. Write `.migration/config.json` with user decisions (output_type, java_version, spring_boot_version, architecture style, etc.)
35. Write `.migration/state.md` with YAML frontmatter:
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
    understanding:
      ua_complete: true
      graphify_complete: true
      communities_detected: <count>
      god_nodes_detected: <count>
      domains_detected: <count>
    last_updated: "<now>"
    ---
    ```

    **If --poc mode:**
    - Create `.migration/validation/` directory
    - Create `.migration/validation/test-variants.md` with selected ZOT variants
    - Create `.migration/validation/poc-config.json` with cpp_engine_path, cpp_engine_command, java_engine_command, test_data_path, comparison_format, tolerance
    - Add to state.md: `mode: poc`

### Phase 7: Project Skeleton

36. Initialize project skeleton in target_root (default: `./app/`) based on `output_type`:

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

37. Commit: `migrate(init): initialize migration project from <source_path>`

### Phase 8: Report & Next Steps

38. Display summary:
    - Total files: X (.cpp) + Y (.h/.hpp)
    - Total lines: N
    - Detected technologies: [list]
    - Architectural layers: [from UA]
    - Natural communities: [count from Graphify]
    - God nodes (high-risk): [count]
    - Business domains: [from UA domain extraction]
    - Phases generated: Z
    - Estimated complexity: [distribution]

39. Suggest next step: "Run `migrate-analyze 1` to begin analyzing the first phase"
    - If --poc mode: also suggest "Run `migrate-golden-master` to validate functional equivalence"

40. Commit: `migrate(init): complete initialization with understanding baseline`

## Outputs

### Understanding Artifacts
- `.migration/understanding/knowledge-graph.json` — UA structural knowledge graph
- `.migration/understanding/domain-graph.json` — UA business domain extraction
- `.migration/understanding/domain-map.md` — Human-readable domain→code mapping
- `.migration/understanding/onboarding.md` — Generated onboarding guide
- `.migration/understanding/tours/` — UA guided architecture tours
- `.migration/understanding/layer-assignments.json` — UA architectural layer per file
- `.migration/understanding/graph.json` — Graphify knowledge graph
- `.migration/understanding/graph.html` — Graphify interactive visualization
- `.migration/understanding/GRAPH_REPORT.md` — Graphify analysis (god nodes, communities, surprises)
- `.migration/understanding/architecture-insights.md` — Combined analysis (UA + Graphify)
- `.migration/understanding/understanding-summary.md` — Executive summary for stakeholders
- `.migration/understanding/dashboard/` — UA interactive dashboard assets

### Migration Planning Artifacts
- `.migration/state.md` — migration state tracker
- `.migration/roadmap.md` — ordered phases (named by domain, grouped by community)
- `.migration/inventory.md` — classified file inventory
- `.migration/decisions.md` — architecture decision log
- `.migration/mapping.md` — C++ → Java structure map
- `.migration/tech-debt.md` — patterns requiring redesign
- `.migration/config.json` — migration configuration
- `.migration/research/legacy-stack.md` — detected technologies
- `.migration/research/target-stack.md` — target architecture
- `.migration/research/risk-matrix.md` — migration risks
- `.migration/research/dependency-map.md` — library migration paths

### Architecture Graph Artifacts
- `.migration/graphs/source/graph.json` — Graphify knowledge graph of C++ source
- `.migration/graphs/source/graph.html` — Interactive graph visualization
- `.migration/graphs/source/GRAPH_REPORT.md` — God nodes, communities, surprising connections
- `.migration/graphs/source/phase-alignment.md` — Graphify communities vs roadmap phase alignment

### Target Project
- `{target_root}` — target project skeleton (build.gradle.kts, Gradle wrapper, hexagonal package structure, ArchUnit test)

### PoC Mode (if --poc)
- `.migration/validation/poc-config.json` — PoC validation configuration
- `.migration/validation/test-variants.md` — Selected ZOT test variants

## Success Criteria

- .migration/ directory created with all required files
- UA knowledge graph generated with all source files as nodes
- UA domain extraction produced at least 1 business domain with flows
- UA onboarding guide generated (human-readable)
- Graphify graph generated with communities detected
- Graphify GRAPH_REPORT.md contains god nodes and surprising connections
- Cross-reference analysis produced (layer↔community alignment)
- Executive summary generated with complexity assessment
- All outputs saved to `.migration/understanding/`
- inventory.md has EVERY .cpp/.h/.hpp file classified
- legacy-stack.md has all detected technologies with migration paths
- decisions.md has numbered architecture decisions (including output_type decision)
- mapping.md maps C++ structure to hexagonal Java packages (informed by UA layer assignments)
- roadmap.md has dependency-ordered phases covering all source files (validated against Graphify communities)
- state.md initialized with correct counts, output_type, and understanding metadata
- config.json has valid configuration with output_type set
- Project skeleton matches output_type (service→Spring Boot app, library→java-library JAR, sdk→library+docs, cli→application plugin)
- Skeleton project compiles (`cd app && ./gradlew compileJava` succeeds)
- ArchUnit hexagonal test exists and passes (trivially, empty project)
- User knows the next step (migrate-analyze 1)
- If --poc: validation directory created with poc-config.json and test-variants.md
