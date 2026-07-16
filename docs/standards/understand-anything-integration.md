# Understand-Anything + Graphify Integration Plan

> How the two tools complement each other in the C++ → Java migration workflow,
> and how to instrument them so users understand what they're migrating BEFORE
> they start translating code.

---

## The Problem

Most legacy C++ projects have zero documentation. Developers inheriting these
codebases have no idea:
- What the system does at a business level
- How components relate to each other
- Which parts are critical vs dead code
- What the intended architecture was

The migration framework currently jumps straight into scanning + translating.
Users need to **understand** before they **migrate**.

---

## Tool Comparison

| Dimension | Graphify | Understand-Anything |
|-----------|---------|---------------------|
| **What it builds** | Knowledge graph (NetworkX JSON) | Knowledge graph (interactive dashboard) |
| **Extraction** | Tree-sitter AST + LLM semantic | Tree-sitter AST + LLM semantic |
| **Output** | `graphify-out/` (graph.json, graph.html, GRAPH_REPORT.md) | `.ua/` (knowledge-graph.json, dashboard) |
| **Visualization** | vis.js force-directed graph | Interactive dashboard with layers, tours, search |
| **Unique strength** | God nodes, community detection (Leiden), surprising connections, edge confidence tiers, graph queries (BFS/DFS) | Architectural layer grouping, guided tours, business domain extraction, diff impact, onboarding guides, persona-adaptive UI |
| **Query model** | `graphify query/path/explain` — graph traversal | `/understand-chat` — conversational Q&A over graph |
| **Domain knowledge** | Communities + edges | `/understand-domain` — explicit domains, flows, steps |
| **Incremental** | `--update` (changed files only) | Incremental by default (fingerprint-based) |
| **Installation** | `pip install graphifyy` (Python) | Plugin install or `install.sh` (Node.js/TypeScript) |
| **Multi-platform** | CLI, any agent | Claude Code, Codex, Cursor, Copilot, Gemini CLI, Kiro, etc. |
| **Graph format** | Nodes + edges + hyperedges + communities | Nodes + edges + layers + tours + domain flows |

---

## Complementary Strengths (Why Use Both)

### Graphify excels at:
1. **Structural analysis** — community detection reveals natural module boundaries
2. **Coupling metrics** — god nodes quantify migration risk
3. **Migration validation** — source↔target graph comparison tracks architectural drift
4. **Surprising connections** — hidden dependencies that would break during migration
5. **Edge confidence** — EXTRACTED vs INFERRED vs AMBIGUOUS tells you what's certain

### Understand-Anything excels at:
1. **Human comprehension** — guided tours teach the codebase in dependency order
2. **Business domain extraction** — maps code to business processes (domains, flows, steps)
3. **Interactive exploration** — click any node, see plain-English explanation
4. **Onboarding** — `/understand-onboard` generates a new-team-member guide
5. **Layer visualization** — automatic grouping by architectural role (API/Service/Data/UI/Utility)
6. **Diff impact** — shows ripple effects before committing changes

### Together they provide:
- **Graphify**: The analytical backbone — metrics, community detection, migration tracking
- **Understand-Anything**: The human interface — dashboards, tours, explanations, domain mapping

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Migration Workflow                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PHASE 0: UNDERSTAND (before migration starts)              │
│  ┌───────────────────┐    ┌────────────────────────┐       │
│  │ Understand-Anything│    │ Graphify               │       │
│  │                   │    │                        │       │
│  │ /understand       │    │ graphify . --mode deep │       │
│  │ /understand-domain│    │                        │       │
│  │ /understand-onboard│   │                        │       │
│  └────────┬──────────┘    └────────────┬───────────┘       │
│           │                            │                    │
│           ▼                            ▼                    │
│  .ua/knowledge-graph.json    graphify-out/graph.json        │
│  .ua/domain-graph.json       graphify-out/GRAPH_REPORT.md   │
│           │                            │                    │
│           └──────────┬─────────────────┘                    │
│                      ▼                                      │
│         .migration/understanding/                           │
│         ├── dashboard.html  (UA interactive dashboard)      │
│         ├── graph.json      (Graphify knowledge graph)      │
│         ├── domain-map.md   (UA domain extraction)          │
│         ├── onboarding.md   (UA onboarding guide)           │
│         ├── architecture-insights.md (Graphify analysis)    │
│         └── tours/          (UA guided tours)               │
│                      │                                      │
│                      ▼                                      │
│  PHASE 1+: MIGRATE (existing workflow)                      │
│  migrate-init → analyze → plan → execute → verify → review │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Proposed New Skill: `migrate-understand`

**Position in workflow:** BEFORE `migrate-init`. This is Phase 0.

```
migrate-understand → migrate-init → migrate-analyze → ... → migrate-review
```

### What it does:

1. **Run Understand-Anything** on the C++ source:
   - `/understand` — builds the structural knowledge graph + interactive dashboard
   - `/understand-domain` — extracts business domains, flows, process steps
   - `/understand-onboard` — generates a human-readable onboarding guide

2. **Run Graphify** on the same source:
   - `graphify {source} --mode deep` — builds community graph with confidence tiers
   - God nodes, surprising connections, community detection

3. **Cross-reference the outputs:**
   - UA architectural layers ↔ Graphify communities (do they agree?)
   - UA domain flows ↔ Graphify edge paths (same execution chains?)
   - UA guided tours ↔ Graphify suggested questions (complementary learning paths?)

4. **Produce unified understanding artifacts:**
   - Combined architecture overview (layers from UA + coupling from Graphify)
   - Domain glossary (business terms from UA domain extraction → feeds ARC42 §12 Glossary)
   - Migration complexity heatmap (god nodes from Graphify + layer assignments from UA)
   - Interactive dashboard (UA) + analytical report (Graphify) — both accessible

5. **Feed into migrate-init:**
   - UA domain extraction informs roadmap phase naming (business-meaningful names)
   - Graphify communities inform roadmap phase grouping (dependency-based)
   - UA onboarding guide becomes part of the migration documentation
   - UA layer classification helps auto-assign C++ files to hexagonal layers

---

## How They Share Data

### Tree-sitter overlap

Both tools use tree-sitter for structural extraction. This means:
- **Same AST facts** extracted (imports, functions, classes, call sites)
- **No conflict** — they can run on the same source directory independently
- **Potential optimization**: Run UA first (it caches in `.ua/`), then Graphify. In the future, a bridge could share the tree-sitter parse results to avoid double-parsing.

### Graph format interop

| Format | Graphify | Understand-Anything |
|--------|---------|---------------------|
| Nodes | `{id, label, type, source_file, confidence}` | `{id, name, type, file, summary, layer, tags}` |
| Edges | `{source, target, relationship, confidence: EXTRACTED/INFERRED/AMBIGUOUS}` | `{source, target, type, description}` |
| Communities | Leiden algorithm clusters | Architectural layers (API/Service/Data/UI/Utility) |
| Extras | Hyperedges, god_nodes, surprising_connections | Tours, domain_flows, language_concepts |

**Key insight**: Graphify's communities are algorithmically detected (data-driven), while UA's layers are semantically assigned (LLM-driven). They measure different things and complement each other:
- If a Graphify community maps cleanly to one UA layer → strong architectural signal
- If a Graphify community spans multiple UA layers → potential architectural concern
- If a UA layer spans many Graphify communities → that layer may have hidden internal modularity

---

## Data Flow Into Existing Skills

### → migrate-init

| Understanding artifact | How it's used in migrate-init |
|----------------------|------------------------------|
| UA domain flows | Name roadmap phases by business domain (not just "Phase 1") |
| Graphify communities | Group files into phases by natural module boundary |
| UA layer assignments | Pre-classify C++ files into target hexagonal layers |
| UA onboarding guide | Include as `.migration/onboarding.md` for human context |
| Graphify god nodes | Flag high-risk files that need extra analysis time |

### → migrate-analyze

| Understanding artifact | How it's used in migrate-analyze |
|----------------------|----------------------------------|
| UA domain flows | Agent 1 (Data Flow) gets pre-mapped business flows |
| Graphify communities + edges | Agent 3 (Dependency Mapper) gets validated dependency data |
| UA summaries per file | All agents get plain-English context without re-reading full source |
| Graphify confidence tiers | Agent 4 (Risk Assessor) knows which dependencies are certain vs guessed |

### → migrate-verify

| Understanding artifact | How it's used in migrate-verify |
|----------------------|----------------------------------|
| UA domain flows (source) vs UA domain flows (target) | Verify business logic preserved |
| Graphify source graph vs target graph | Quantitative architecture drift |

### → ARC42 Generation

| ARC42 Section | Understand-Anything contribution | Graphify contribution |
|---|---|---|
| §1 Introduction | UA onboarding guide (purpose/scope) | — |
| §3 Context & Scope | UA external dependencies from graph | Graphify external boundary nodes |
| §5 Building Block View | UA layer groupings + summaries | Graphify communities + god nodes |
| §6 Runtime View | UA domain flows (process steps) | Graphify path queries |
| §8 Cross-cutting Concepts | UA language concepts detected | Graphify surprising connections |
| §12 Glossary | UA domain extraction (business terms) | Graphify node labels |

---

## Installation Requirements

### For the migration framework to use both:

```bash
# Graphify (Python)
pip install graphifyy   # or: pipx install graphifyy

# Understand-Anything (Node.js)
curl -fsSL https://raw.githubusercontent.com/Egonex-AI/Understand-Anything/main/install.sh | bash -s kiro
# This installs skills to ~/.kiro/skills/ and makes /understand available
```

### Verify both are available:

```bash
graphify --version          # Should print version
# Understand-Anything is invoked as a skill — no standalone CLI needed
# It's available as /understand in the agent session
```

---

## Proposed Workflow (User Perspective)

```
# Step 0: Understand what you're migrating
migrate-understand ./source/cpp-project

# This runs both tools and produces:
# - Interactive dashboard (open in browser)
# - Domain map (business processes in the code)
# - Onboarding guide (human-readable "what is this?")
# - Architecture insights (coupling, risks, module boundaries)
# - Guided tours (dependency-ordered learning paths)

# Step 1: Now that you understand, start the migration
migrate-init ./source/cpp-project

# The init skill READS the understanding artifacts to:
# - Name phases by business domain
# - Group files by community boundaries
# - Pre-assign hexagonal layers
# - Flag god nodes for extra analysis
```

---

## Open Questions / Future Work

1. **Graph format bridge**: Could we convert between UA's knowledge-graph.json and Graphify's graph.json to avoid maintaining two parallel graphs? Or is the overhead acceptable given they measure different things?

2. **Shared tree-sitter cache**: Both tools parse the same source with tree-sitter. A shared cache could save ~30-50% of initial extraction time on large projects.

3. **Dashboard unification**: UA has the better interactive dashboard. Could we overlay Graphify's community detection + confidence tiers onto UA's visualization? (UA nodes colored by Graphify community, edges styled by confidence tier.)

4. **Incremental sync**: When `migrate-execute` produces new Java code, both tools need to update. Could we trigger both from a single git hook (`/understand --auto-update` + `graphify --update`) to stay in sync?

5. **Token budget**: Running both on a 200K LOC codebase consumes significant tokens for the LLM semantic pass. Strategy:
   - Run UA first (it has good incremental caching)
   - Run Graphify with `--mode deep` only on the first pass; subsequent passes use `--update`
   - For code-only extraction (no docs/papers), Graphify's tree-sitter pass needs zero LLM tokens
   - UA's file-analyzer runs up to 5 concurrent agents — monitor token usage

6. **Language support**: Both tools support C++ via tree-sitter. Verify edge cases:
   - Template-heavy code (CRTP, SFINAE)
   - Preprocessor macro expansion
   - Header-only libraries
   - Platform-specific #ifdef blocks
