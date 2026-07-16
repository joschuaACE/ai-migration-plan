# migrate-understand

Understand a legacy codebase BEFORE migrating it — run Understand-Anything for human-readable comprehension (dashboard, tours, domain mapping, onboarding) and Graphify for analytical architecture intelligence (communities, coupling, risk). Produces a unified understanding baseline that feeds all subsequent migration skills.

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

- **FIRST** — before migrate-init. This is Phase 0 of the migration.
- When you inherit an undocumented C++ codebase and need to understand it
- When stakeholders ask "what does this system even do?" before approving migration
- When onboarding new team members to the legacy code
- Anytime during migration to re-orient ("what was this module supposed to do?")

## Inputs

- **Path to C++ source** (required) — directory containing .cpp/.h/.hpp files
- **--language** (optional) — output language for UA (default: auto-detect, typically `de` for DATEV)
- **--skip-graphify** (optional) — skip Graphify if already run (e.g., graph exists)
- **--skip-ua** (optional) — skip Understand-Anything if already run

## Outputs

```
.migration/understanding/
├── dashboard/                  ← UA interactive dashboard (open in browser)
│   └── (served by UA viewer)
├── knowledge-graph.json        ← UA structural knowledge graph
├── domain-graph.json           ← UA business domain extraction
├── domain-map.md               ← Human-readable domain→code mapping
├── onboarding.md               ← Generated onboarding guide
├── tours/                      ← UA guided architecture tours
├── layer-assignments.json      ← UA architectural layer per file
├── graph.json                  ← Graphify knowledge graph
├── graph.html                  ← Graphify interactive visualization
├── GRAPH_REPORT.md             ← Graphify analysis (god nodes, communities, surprises)
├── architecture-insights.md    ← Combined analysis (both tools)
└── understanding-summary.md    ← Executive summary for stakeholders
```

## Procedure

### Step 1: Validate Source

1. Verify source path exists and contains C++ files (.cpp, .h, .hpp, .cc, .hh)
2. Count total files and LOC — report to user
3. If > 500 files, suggest scoping to a subdirectory for first pass
4. Create `.migration/understanding/` directory

### Step 2: Run Understand-Anything

5. Run the full UA pipeline on the source:
   ```
   /understand {source_path} --language de
   ```
   This invokes UA's multi-agent pipeline:
   - `project-scanner` → discovers files, languages, frameworks
   - `file-analyzer` → extracts functions, classes, imports, produces graph nodes
   - `architecture-analyzer` → assigns architectural layers
   - `tour-builder` → generates dependency-ordered learning tours
   - `graph-reviewer` → validates graph completeness

6. Run domain extraction:
   ```
   /understand-domain
   ```
   This produces the business domain mapping: domains, flows, process steps.
   Critical for legacy code where business logic is buried in implementation.

7. Run onboarding guide generation:
   ```
   /understand-onboard
   ```
   Produces a structured guide for new team members.

8. Copy UA outputs to migration directory:
   ```bash
   mkdir -p .migration/understanding/dashboard
   cp .ua/knowledge-graph.json .migration/understanding/
   cp .ua/domain-graph.json .migration/understanding/ 2>/dev/null || true
   ```

9. Extract layer assignments from UA knowledge graph:
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

### Step 3: Run Graphify

10. Run Graphify deep analysis on the same source:
    ```bash
    graphify {source_path} --mode deep
    ```
    This produces:
    - Community detection (Leiden algorithm) → natural module boundaries
    - God nodes → highest coupling (migration risk indicators)
    - Surprising connections → hidden cross-module dependencies
    - Edge confidence tiers (EXTRACTED/INFERRED/AMBIGUOUS)

11. Copy Graphify outputs:
    ```bash
    cp graphify-out/graph.json .migration/understanding/
    cp graphify-out/graph.html .migration/understanding/
    cp graphify-out/GRAPH_REPORT.md .migration/understanding/
    ```

### Step 4: Cross-Reference Analysis

12. Load both graphs and compare:
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

13. Write `.migration/understanding/architecture-insights.md`:
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

### Step 5: Generate Executive Summary

14. Write `.migration/understanding/understanding-summary.md`:
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

    ## Recommended Next Step
    Run `migrate-init {source_path}` to begin the migration.
    The init skill will use these understanding artifacts to:
    - Name phases by business domain
    - Group files by community boundaries
    - Pre-classify files into hexagonal layers
    - Flag god nodes for extra analysis time

    ## Explore Interactively
    - Open UA dashboard: `npx understand-anything-viewer .`
    - Open Graphify visualization: open `.migration/understanding/graph.html` in browser
    - Ask questions: `/understand-chat "How does X work?"`
    - Trace paths: `graphify query "connection between A and B"`
    ```

### Step 6: Launch Dashboard

15. Offer to launch the UA interactive dashboard:
    ```
    "Understanding complete. Open the interactive dashboard? (recommended)"
    ```
    If yes:
    ```bash
    npx understand-anything-viewer {source_path}
    ```
    This opens the browser with the full interactive knowledge graph.

16. Display the executive summary in the terminal.

17. Suggest next step: "Run `migrate-init {source_path}` to begin the migration."

## Integration with migrate-init

When `migrate-init` runs and detects `.migration/understanding/` exists:

1. **Phase naming**: Use UA domain names instead of generic "Phase 1, 2, 3"
2. **File grouping**: Use Graphify communities as the primary grouping (validated by UA layers)
3. **Layer pre-assignment**: Use UA `layer-assignments.json` to pre-populate mapping.md
4. **Risk flagging**: God nodes from Graphify get marked as "needs extra analysis" in roadmap.md
5. **Skip redundant work**: migrate-init Phase 2 (tech detection) can read from UA's project-scanner output instead of re-scanning

## Success Criteria

- UA knowledge graph generated with all source files as nodes
- UA domain extraction produced at least 1 business domain with flows
- UA onboarding guide generated (human-readable)
- UA dashboard launchable in browser
- Graphify graph generated with communities detected
- Graphify GRAPH_REPORT.md contains god nodes and surprising connections
- Cross-reference analysis produced (layer↔community alignment)
- Executive summary generated with complexity assessment
- All outputs saved to `.migration/understanding/`
- User can explore the codebase interactively before committing to migration
