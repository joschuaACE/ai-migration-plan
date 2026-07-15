# migrate-analyze

Deep-analyze a C++ module for migration — traces data flow, detects patterns, identifies risks, and produces a comprehensive ANALYSIS.md that the planning skill consumes.

## When to Use

- Before migrate-plan N — analysis MUST precede planning
- When a phase's source has changed and analysis needs refresh
- This is the first step for each phase in the migration cycle: Analyze → Plan → Execute → Verify → Review

## Inputs

- **Phase number** (required) — which phase from roadmap.md to analyze
- **--focus flag** (optional) — limit analysis to specific concern: `memory`, `concurrency`, `io`, `api`, or `all` (default: all)

**Required state:**
- `.migration/roadmap.md` must exist (from migrate-init)
- `.migration/inventory.md` must exist
- `.migration/mapping.md` must exist
- Phase N must have status "Not Started" or "Analyzing"

**Context to read before starting:**
1. roadmap.md → get file list for this phase
2. inventory.md → get file metadata
3. mapping.md → know target Java structure
4. decisions.md → respect existing architectural decisions
5. config.json → check output_type (library analysis focuses on API surface; service focuses on endpoints)

## Procedure

### Step 1: Phase Setup

1. Read roadmap.md → extract phase N metadata (files, goal, dependencies)
2. Create `.migration/phases/NN-slug/` directory if not exists
3. Verify all source files listed in the phase actually exist
4. Update state.md: `status: analyzing`, `active_phase: N`

### Step 2: Parallel Deep Analysis (4 agents)

Spawn 4 parallel analysis agents, each writing a section of nn-analysis.md:

**Agent 1: Data Flow Tracer**
- Context: All source files in this phase + their direct includes
- Analyzes:
  - Class/struct definitions — fields, relationships, inheritance
  - Ownership semantics — who creates, who owns, who destroys
  - Data flow through public methods — inputs → transformations → outputs
  - Shared state — global variables, singletons, static members
  - Lifetime patterns — stack vs heap, RAII scopes
- Output section: `## Data Flow & Ownership`

**Agent 2: Pattern Detector**
- Context: All source files in this phase
- Analyzes:
  - Design patterns used: Singleton, Observer, Factory, Builder, Strategy, Command, etc.
  - C++-specific patterns: RAII, CRTP, Pimpl, Copy-and-Swap, Rule of Five
  - Idioms: SFINAE, tag dispatch, expression templates
  - Code generation patterns: macros generating code, template instantiations
  - Error handling pattern: exceptions, error codes, errno, std::expected
- Output section: `## Design Patterns & Idioms`
- For each pattern found, note: Location, Pattern name, How it maps to Java, Risk level (1-5)

**Agent 3: Dependency Mapper**
- Context: All source files + build files referencing this phase's targets
- Analyzes:
  - Internal dependencies — what other project modules this phase calls
  - External dependencies — which third-party libraries are used
  - Callers — what other code calls INTO this phase (defines the port interfaces)
  - Interface surface — public API that must be preserved
  - Circular dependencies — if any exist, flag for resolution
  - For library/sdk: Identify PUBLIC API surface — these become the exported port/in interfaces
  - For library/sdk: Identify SPI surface — extension points where consumers provide implementations (port/out)
- Output section: `## Dependencies & Interface Surface`

**Agent 4: Risk Assessor**
- Context: All source files + legacy-stack.md + risk-matrix.md
- Analyzes:
  - Unsafe operations: raw pointer arithmetic, void* casts, unions, reinterpret_cast
  - Platform-specific code: #ifdef blocks, system calls
  - Undefined behavior risks: signed overflow, dangling pointers, data races
  - Concurrency patterns: mutexes, atomics, lock-free structures
  - Performance-critical sections: tight loops, cache-sensitive code, SIMD
  - Macro-heavy code: complex preprocessor logic that needs manual translation
- Output section: `## Risks & Migration Challenges`

### Step 3: Synthesis

5. After all agents complete, read the full nn-analysis.md
6. Add a summary section at top:
   ```markdown
   ## Migration Summary
   - Files: N source + M headers
   - Total LOC: X
   - Complexity Score: Y/5
   - Key challenges: [list top 3]
   - Recommended strategy: conservative|modern|hybrid
   - Estimated translation effort: [small|medium|large|very-large]
   - Output type consideration: <what's notable for this output type>
   ```
7. Add per-file complexity scores:
   ```markdown
   ## File Complexity Scores
   | File | LOC | Cyclomatic | Patterns | Risk | Score (1-5) |
   |------|-----|-----------|----------|------|:-----------:|
   ```

### Step 4: Gate & Update

8. Verify all 4 sections written with substantive content (not empty)
9. If any section is empty → re-spawn that agent with broader context
10. Update state.md: increment analysis count
11. Report to user:
    - Phase complexity score
    - Top risks identified
    - Recommended next step: migrate-plan N

## Outputs

- `.migration/phases/NN-slug/nn-analysis.md` — comprehensive analysis with all 4 sections plus summary

## Success Criteria

- All source files in the phase were read and analyzed
- nn-analysis.md has all 4 sections populated (Data Flow, Patterns, Dependencies, Risks)
- Every class/struct in the phase is documented with its purpose
- Public API surface identified (these become port interfaces)
- Ownership/lifetime patterns documented (critical for Java translation)
- Risks flagged with severity (these become plan constraints)
- Complexity score assigned to each file
- state.md updated
