# Graphify Integration Reference

Internal reference for Graphify knowledge graph extraction during migration. This is NOT
a user-invoked command — it runs automatically at defined points in the migration workflow.

Other skills call into Graphify modes implicitly; this document defines what happens
at each integration point.

## Prerequisites

**Graphify** (https://github.com/Graphify-Labs/graphify) must be installed:

```bash
pip install graphifyy    # PyPI package (CLI command is still `graphify`)
# or
pipx install graphifyy   # isolated install
# or
uv tool install graphifyy
```

Requires Python 3.10+. The `graphify` CLI must be on PATH.

**Key capabilities used:**
- Tree-sitter AST extraction for code (C++, Java) — no LLM needed for structural analysis
- `--mode deep` for semantic extraction (uses Gemini if `GEMINI_API_KEY` set, otherwise host LLM)
- `--update` for incremental re-extraction (only changed files)
- `graphify query` for graph traversal (BFS/DFS)
- `graphify path` for shortest-path between concepts
- Community detection (Leiden algorithm) for module boundary identification
- God node analysis for coupling hotspots
- Surprising connections for hidden dependencies

**Output format:** `graphify-out/` directory with `graph.json`, `graph.html`, `GRAPH_REPORT.md`

---

## When This Runs Automatically

| Mode | Triggered By | When |
|------|-------------|------|
| `source` | **migrate-init** Phase 1 (Scan + Understand) | Automatically after source scanning completes |
| `target` | **migrate-execute** | Automatically at end of execution (after all waves pass) |
| `compare` | **migrate-verify** | Automatically at end of verification |
| `arc42` | **migrate-review** (final phase only) | Automatically after final review completes |
| `query` | Any skill (inline) | Available as an inline capability during any skill — not a separate command |

---

## Outputs Location

```
.migration/
├── graphs/
│   ├── source/                    ← C++ source architecture graph
│   │   ├── graph.json
│   │   ├── graph.html
│   │   └── GRAPH_REPORT.md
│   ├── target/                    ← Java target architecture graph (cumulative)
│   │   ├── graph.json
│   │   ├── graph.html
│   │   └── GRAPH_REPORT.md
│   ├── target-phase-NN/           ← Per-phase snapshots
│   │   ├── graph.json
│   │   └── GRAPH_REPORT.md
│   └── comparison/                ← Source↔Target delta
│       └── architecture-drift.md
└── arc42/
    ├── arc42-documentation.md     ← Full ARC42 document
    ├── 01-introduction-goals.md
    ├── 02-constraints.md
    ├── 03-context-scope.md
    ├── 04-solution-strategy.md
    ├── 05-building-block-view.md
    ├── 06-runtime-view.md
    ├── 07-deployment-view.md
    ├── 08-crosscutting-concepts.md
    ├── 09-architecture-decisions.md
    ├── 10-quality-requirements.md
    ├── 11-risks-technical-debt.md
    └── 12-glossary.md
```

---

## Procedure

---

### Mode: `source` — Graphify the C++ Source

**Trigger:** migrate-init Phase 1 (Scan + Understand) — runs automatically after source scanning completes.

1. Read `.migration/config.json` → get `source_root`
2. Run Graphify on the C++ source directory:
   ```bash
   graphify {source_root} --mode deep
   ```
   - Deep mode to capture INFERRED relationships (important for C++ includes/macros)
   - Tree-sitter AST extraction handles .cpp/.h/.hpp natively
3. Move outputs to migration-managed location:
   ```bash
   mkdir -p .migration/graphs/source
   cp graphify-out/graph.json .migration/graphs/source/
   cp graphify-out/GRAPH_REPORT.md .migration/graphs/source/
   cp graphify-out/graph.html .migration/graphs/source/ 2>/dev/null || true
   ```
4. Extract architecture insights for migrate-analyze:
   - **God Nodes** → these are the most coupled C++ components, migrate them carefully
   - **Communities** → natural module boundaries, validate against roadmap phase grouping
   - **Surprising Connections** → hidden coupling that could break during migration
5. Write `.migration/graphs/source/architecture-insights.md`:
   ```markdown
   # Source Architecture Insights (from Graphify)

   ## God Nodes (High Coupling Risk)
   <!-- List god nodes with edge counts — these need extra attention during migration -->

   ## Natural Module Boundaries (Communities)
   <!-- List communities with member nodes — compare against roadmap phases -->

   ## Surprising Connections
   <!-- Hidden dependencies that cross module boundaries -->

   ## Suggested Migration Order Validation
   <!-- Does the dependency graph agree with roadmap ordering? -->
   ```
6. Cross-reference communities against `.migration/roadmap.md`:
   - If a graphify community spans multiple phases → WARN: tight coupling across phase boundary
   - If a roadmap phase spans multiple communities → WARN: phase may be too large
   - Write warnings to `.migration/graphs/source/phase-alignment.md`

---

### Mode: `target` — Graphify the Java Target

**Trigger:** migrate-execute — runs automatically after all waves pass gates.

1. Read `.migration/config.json` → get `target_root` (default `app/`)
2. Read `.migration/state.md` → get `active_phase`
3. Run Graphify on the Java target:
   ```bash
   graphify {target_root}/src --update
   ```
   - Uses `--update` for incremental extraction (only new/changed files)
   - First run after init does full extraction
4. Move/copy outputs:
   ```bash
   mkdir -p .migration/graphs/target
   cp graphify-out/graph.json .migration/graphs/target/
   cp graphify-out/GRAPH_REPORT.md .migration/graphs/target/
   cp graphify-out/graph.html .migration/graphs/target/ 2>/dev/null || true

   # Snapshot for this phase
   mkdir -p .migration/graphs/target-phase-$(printf '%02d' $PHASE)
   cp graphify-out/graph.json .migration/graphs/target-phase-$(printf '%02d' $PHASE)/
   cp graphify-out/GRAPH_REPORT.md .migration/graphs/target-phase-$(printf '%02d' $PHASE)/
   ```
5. Validate architecture:
   - **Community count growing?** → architecture may be fragmenting
   - **New god nodes appearing in Java?** → service is getting too coupled
   - **Hexagonal layers respected?** Query: "Does domain depend on adapter?" → should be NO
6. Write `.migration/graphs/target/evolution-phase-NN.md`:
   ```markdown
   # Architecture Evolution — Phase NN

   ## Graph Statistics
   - Nodes: X (delta: +Y from previous phase)
   - Edges: X (delta: +Y)
   - Communities: X

   ## New God Nodes (Coupling Risk)
   <!-- Any new high-degree nodes in the Java target -->

   ## Architecture Violations
   <!-- Domain → adapter dependencies, circular deps, etc. -->

   ## Community Health
   <!-- Are Java communities aligning with hexagonal layers? -->
   ```

---

### Mode: `compare` — Source ↔ Target Architecture Comparison

**Trigger:** migrate-verify — runs automatically at end of verification.

1. Load `.migration/graphs/source/graph.json`
2. Load `.migration/graphs/target/graph.json`
3. Load `.migration/mapping.md` (C++ → Java structure map)
4. Compare:
   - **Coverage**: What % of source nodes have a corresponding target node?
   - **Structure preservation**: Do source communities map cleanly to target communities?
   - **Complexity change**: Has total edge count grown (more coupling) or shrunk (better separation)?
   - **Lost connections**: Source edges that have no target equivalent (functionality gap?)
   - **New connections**: Target edges with no source equivalent (added coupling?)
5. Write `.migration/graphs/comparison/architecture-drift.md`:
   ```markdown
   # Architecture Drift Report

   ## Coverage
   - Source nodes: X
   - Target nodes mapped: Y (Z%)
   - Unmapped source concepts: [list]

   ## Structural Comparison
   | Metric | Source (C++) | Target (Java) | Delta |
   |--------|-------------|---------------|-------|
   | Total nodes | | | |
   | Total edges | | | |
   | Communities | | | |
   | Max degree (god node) | | | |
   | Avg clustering coefficient | | | |

   ## Coupling Changes
   - Reduced coupling: [list source connections that were correctly decoupled]
   - Increased coupling: [list new target connections that may violate architecture]

   ## Unmigrated Functionality
   - Source nodes with no target equivalent (may be intentional — check decisions.md)
   ```

---

### Mode: `arc42` — Generate ARC42 Documentation

**Trigger:** migrate-review (final phase only) — runs automatically after final review completes.

#### Prerequisites
- `.migration/graphs/source/graph.json` exists
- `.migration/graphs/target/graph.json` exists
- `.migration/decisions.md` exists
- `.migration/mapping.md` exists
- `.migration/roadmap.md` exists
- `.migration/config.json` exists
- `.migration/tech-debt.md` exists

#### Procedure

1. Read ALL migration artifacts:
   - Source graph + report
   - Target graph + report
   - decisions.md
   - mapping.md
   - roadmap.md (with phase completion status)
   - config.json
   - tech-debt.md
   - All phase analysis files (nn-analysis.md)
   - Architecture drift report (if exists)

2. Generate each ARC42 section from specific data sources:

| ARC42 Section | Primary Data Source |
|---|---|
| 01 Introduction & Goals | config.json (purpose), decisions.md (D-01..D-05) |
| 02 Constraints | decisions.md (tech constraints), config.json (Java 25, Spring Boot 4) |
| 03 Context & Scope | Source graph communities (system boundary), external dependencies |
| 04 Solution Strategy | decisions.md, mapping.md (C++ → Java strategy), tech-debt.md |
| 05 Building Block View | Target graph communities + god nodes, package structure |
| 06 Runtime View | Phase analyses (data flow sections), sequence from source graph paths |
| 07 Deployment View | config.json (deployment target), if service: Cloud Foundry/K8s |
| 08 Crosscutting Concepts | Target graph surprising connections, shared infrastructure |
| 09 Architecture Decisions | decisions.md (full list, formatted as ADRs) |
| 10 Quality Requirements | migrate-verify reports, ArchUnit rules, test coverage |
| 11 Risks & Technical Debt | tech-debt.md, source graph god nodes still unresolved |
| 12 Glossary | Source graph node labels (German domain terms), mapping.md |

3. Write individual section files to `.migration/arc42/`
4. Write combined `.migration/arc42/arc42-documentation.md`
5. Generate in German if source domain terms are German (DATEV convention)

---

### Mode: `query <question>` — Query Architecture Graph

**Availability:** Inline capability during any skill — not a separate command.

1. Determine which graph to query:
   - If question mentions C++/source/original → use `.migration/graphs/source/graph.json`
   - If question mentions Java/target/new → use `.migration/graphs/target/graph.json`
   - If ambiguous → query both and compare
2. Run:
   ```bash
   graphify query "<question>"
   ```
   with `graphify-out/` symlinked or copied from the appropriate migration graph
3. Return answer with source citations

---

## Expected Outcomes

- Source graph captures ALL C++ modules as nodes with relationships
- Target graph grows incrementally with each phase
- Per-phase snapshots enable architecture evolution tracking
- Architecture drift report flags unexpected coupling changes
- ARC42 document is generated with all 12 sections populated
- ARC42 sections reference concrete graph data (node counts, communities, etc.)
- God node warnings surface BEFORE they become entrenched
- Community alignment validates roadmap phase boundaries
- Query mode allows ad-hoc architecture questions during any skill execution
