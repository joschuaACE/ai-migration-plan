# Migration State Files

Reference for the `.migration/` directory — the persistent state layer that tracks
progress, decisions, and artifacts throughout a C++ → Java migration.

---

## Directory Layout

```
.migration/
├── state.md                    ← Central state tracker (status, progress, active phase)
├── config.json                 ← Migration configuration (output type, versions, decisions)
├── roadmap.md                  ← Ordered phases covering all source files
├── inventory.md                ← Classified file inventory (every .cpp/.h/.hpp)
├── decisions.md                ← Architecture decision log (D-NN numbering)
├── mapping.md                  ← C++ → Java structural transformation map
├── tech-debt.md                ← Patterns requiring redesign (not 1:1 ports)
├── research/
│   ├── legacy-stack.md         ← Detected C++ technologies with migration paths
│   ├── target-stack.md         ← Target Java architecture description
│   ├── risk-matrix.md          ← Risks ranked by impact × likelihood
│   └── dependency-map.md       ← Per-dependency C++ → Java migration strategy
├── phases/
│   └── nn-slug/                ← Per-phase working directory (e.g., 01-core-engine/)
│       ├── nn-analysis.md      ← Deep analysis (data flow, patterns, deps, risks)
│       ├── nn-pp-plan.md       ← Translation plan per unit (pp = plan number)
│       ├── nn-pp-summary.md    ← Execution record per plan
│       ├── nn-phase-summary.md ← Phase-level completion summary
│       └── nn-verification.md  ← Semantic equivalence + quality verification
└── validation/                 ← PoC mode only
    ├── poc-config.json         ← Golden master comparison configuration
    └── test-variants.md        ← Selected test data variants
```

---

## state.md — The Central State Tracker

`state.md` is the single source of truth for migration progress. Every skill reads it
to understand context, and every skill writes it to record progress. It uses YAML
frontmatter for machine-parseable state.

### Schema

```yaml
---
migration_version: "1.0"
source: "<C++ standard> / <build system>"      # e.g., "C++17 / CMake 3.21"
target: "Spring Boot 4.0 / Java 25 / Hexagonal"
output_type: "<service|library|sdk|cli>"
architecture: hexagonal
mode: "full"                                    # "full" or "poc"
status: initialized                             # see lifecycle below
active_phase: 0                                 # currently active phase number
total_phases: 0                                 # total from roadmap.md
progress:
  phases_complete: 0
  files_migrated: 0
  files_remaining: 0                            # total from inventory.md
stopped_at: ""                                  # what was happening when work paused
last_updated: "2025-01-15T14:30:00Z"
---
```

### Status Lifecycle

Status transitions follow the phase cycle. Each phase moves through these states
sequentially — there is no skipping.

```
initialized → analyzing → planning → executing → verified → completed
     │                                                           │
     │              (per-phase cycle repeats)                    │
     └──────────────────────────────────────────────────────────┘
```

| Status | Meaning | Set by | Next step |
|--------|---------|--------|-----------|
| `initialized` | Project scanned, skeleton created, no phase work started | migrate-init | migrate-analyze 1 |
| `analyzing` | Active phase is being deep-analyzed | migrate-analyze | migrate-plan N |
| `planning` | Translation plans being generated for active phase | migrate-plan | migrate-execute N |
| `executing` | Plans being translated to Java code | migrate-execute | migrate-verify N |
| `verified` | Semantic equivalence and quality checks passed | migrate-verify | migrate-review N |
| `completed` | Phase reviewed and approved, git tagged | migrate-review | migrate-analyze N+1 |

### Who Reads / Writes state.md

| Skill | Reads | Writes |
|-------|-------|--------|
| migrate-init | — | Creates it |
| migrate-analyze | status, active_phase | status → `analyzing`, active_phase |
| migrate-plan | status, active_phase | status → `planning` |
| migrate-execute | status, active_phase, progress | status → `executing`, progress metrics |
| migrate-verify | status | status → `verified` |
| migrate-review | status, progress | status → `completed`, progress, phases_complete++ |
| migrate-resume | ALL fields | stopped_at, last_updated |

### Stall Detection

`last_updated` enables stall detection. If more than 10 minutes have elapsed since
last progress, migrate-resume alerts that work may have been interrupted and recommends
resumption strategy.

---

## config.json — Migration Configuration

Stores user decisions and detected settings as structured data. Read by all planning
and execution skills.

```json
{
  "output_type": "service",
  "java_version": "25",
  "spring_boot_version": "4.0",
  "architecture": "hexagonal",
  "group_id": "com.company.app",
  "artifact_id": "my-app",
  "source_root": "./src",
  "target_root": "./app",
  "database": "postgresql",
  "api_style": "rest",
  "auth": "spring-security-oauth2",
  "messaging": "none",
  "deployment": "container"
}
```

Fields vary by output type — library/sdk omit service-specific fields like `database`,
`api_style`, `auth`, `messaging`, `deployment`.

---

## roadmap.md — Phase Ordering

Dependency-ordered list of migration phases. Each phase is a logical module or
tightly-coupled cluster of files.

| Field | Purpose |
|-------|---------|
| Phase number | Execution order |
| Name | Human-readable phase identifier |
| Goal | What this phase accomplishes |
| Files | C++ source files included |
| Dependencies | Which prior phases must complete first |
| Complexity | 1-5 rating |
| Status | Not Started / In Progress / Complete |

---

## inventory.md — File Classification

Every `.cpp`, `.h`, and `.hpp` file in the source tree, classified by:

- Type (source/core, source/utility, header/interface, test, config)
- LOC count
- Complexity score
- Dependencies (what it includes)
- Assigned phase

---

## decisions.md — Architecture Decision Log

Numbered decisions (D-01, D-02, ...) recording every architectural choice. Decisions
are permanent — they are never silently overridden.

Format:
```markdown
## D-01: Output type is service
- **Context:** Build produces executable with socket listeners
- **Decision:** Migrate as Spring Boot 4.x service with hexagonal architecture
- **Consequences:** Full adapter layer needed, Spring Security required
```

---

## mapping.md — Structural Transformation Map

Maps every C++ namespace, directory, class, and function to its Java target:
- Namespace → Java package
- File → Java class + hexagonal layer
- Port boundaries (driving and driven interfaces)

---

## tech-debt.md — Redesign Candidates

Patterns from C++ that cannot be ported 1:1 and require intentional redesign:
- Template metaprogramming → generics + strategy pattern
- Manual memory management → standard Java patterns
- Macro-generated code → code generation or reflection

---

## research/ — Technology Intelligence

| File | Content |
|------|---------|
| `legacy-stack.md` | Every detected C++ technology with version, usage count, and migration difficulty |
| `target-stack.md` | The target Java architecture and framework choices |
| `risk-matrix.md` | Risks scored by impact × likelihood with mitigations |
| `dependency-map.md` | Each C++ library → recommended Java equivalent |

---

## phases/nn-slug/ — Per-Phase Working Directory

Each phase gets its own directory (e.g., `phases/01-core-engine/`) containing:

| File | Created by | Purpose |
|------|-----------|---------|
| `nn-analysis.md` | migrate-analyze | Deep analysis: data flow, patterns, dependencies, risks |
| `nn-pp-plan.md` | migrate-plan | Translation plan per unit (wave-ordered) |
| `nn-pp-summary.md` | migrate-execute | Execution record per plan (what was done) |
| `nn-phase-summary.md` | migrate-execute | Phase-level completion metrics |
| `nn-verification.md` | migrate-verify | Semantic equivalence scores + quality audit |

The `nn` prefix is the zero-padded phase number. The `pp` prefix is the plan number
within the phase.

---

## validation/ — PoC Mode Only

Created when `--poc` flag is used during migrate-init. Contains golden master
comparison configuration:

- `poc-config.json` — paths to C++ engine, Java engine, test data, comparison tolerance
- `test-variants.md` — selected ZOT test data variants for equivalence validation

---

## File Naming Convention

All files in `.migration/` follow **lowercase-kebab-case**:
- Words separated by hyphens: `tech-debt.md`, `legacy-stack.md`
- Numeric prefixes for ordering: `01-core-engine/`, `nn-pp-plan.md`
- No UPPERCASE file names
- Extensions: `.md` for documents, `.json` for structured data
