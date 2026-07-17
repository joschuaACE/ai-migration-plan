# ARC42 Generation Template

> Maps migration artifacts + Graphify knowledge graphs → ARC42 v9.0 sections.
> Used by the `arc42` mode (see graphify-integration.md).
---

## How This Works

The migration workflow accumulates artifacts throughout its lifecycle. When all phases
are complete (or on-demand), the `arc42` mode of Graphify integration reads these artifacts and populates
the ARC42 template below. Each section documents WHERE to source the content from.

**Output:** `.migration/arc42/arc42-documentation.md` (single file, matching official template structure)

**Language:** German for DATEV projects (section headings stay English per official template for anchor compatibility, content is German).

---

## Template Structure (aligned to arc42 v9.0-EN)

### 1. Introduction and Goals {#section-introduction-and-goals}

**Data Sources:**
- `config.json` → `purpose`, `output_type`, `source_root`
- `decisions.md` → D-01 through D-05 (foundational decisions)
- `roadmap.md` → overall migration goal statement

**Subheadings to generate:**

#### 1.1 Requirements Overview {#_requirements_overview}

Populate from:
- `config.json.purpose` — what the system does
- `roadmap.md` first paragraph — migration objective
- Source `GRAPH_REPORT.md` → system scope (what the source graph covers)

#### 1.2 Quality Goals {#_quality_goals}

Fixed quality goals for migrated systems (customize if decisions.md overrides):

| Priority | Quality Goal | Motivation |
|----------|-------------|-----------|
| 1 | Behavioral equivalence | Migrated code produces identical outputs for identical inputs |
| 2 | Architectural conformance | Hexagonal/4-layer structure enforced by ArchUnit |
| 3 | Testability | >80% coverage, all public methods tested |
| 4 | Maintainability | Clear layer separation, no god nodes exceeding source |
| 5 | Performance parity | No regression vs C++ implementation |

#### 1.3 Stakeholders {#_stakeholders}

| Role/Name | Contact | Expectations |
|-----------|---------|-------------|
| Development Team | — | Idiomatic, understandable Java codebase |
| Business (Fachbereich) | — | Functional equivalence to existing solution |
| Operations (Betrieb) | — | Standard deployment (CF/K8s), observability |
| QA | — | Automated test suite, regression capability |

---

### 2. Architecture Constraints {#section-architecture-constraints}

**Data Sources:**
- `config.json` → `java_version`, `spring_boot_version`, `output_type`, `architecture`
- `decisions.md` → technology constraint decisions
- `java-target-standards.md` → mandatory architectural and organizational patterns

**Generate table:**

| Constraint | Description | Source |
|-----------|-------------|--------|
| Java {version} | Target language version | config.json |
| {Framework} | Spring Boot 4.x / plain library / picocli | config.json output_type |
| {Architecture} | Hexagonal / 4-layer DATEV | config.json |
| Gradle Kotlin DSL | Build system | Framework standard |
| DATEV conventions | Package structure, DbAdapter, MapStruct, etc. | java-target-standards.md |
| CI/CD | Jenkins + DATEV-CI | Organizational |
| Security | rrmo-security-component | DATEV standard |
| Logging | Splunk-compatible, VK3 masking | DATEV standard |

Also list organizational constraints from `decisions.md` (team size, timeline, etc.).

---

### 3. Context and Scope {#section-context-and-scope}

**Data Sources:**
- Source graph → nodes typed as "external" or with edges crossing system boundary
- Target graph → adapter/out implementations (each represents a technical interface)
- `research/dependency-map.md` → external system list
- `mapping.md` → interface mapping

#### 3.1 Business Context {#_business_context}

Generate a **context diagram** (Mermaid) from the source graph:
- Center: The system being migrated
- Surrounding: External actors/systems identified as graph nodes with cross-boundary edges
- Each connection labeled with business purpose

| External System/Actor | Input | Output | Description |
|----------------------|-------|--------|-------------|
| {From source graph external nodes and dependency-map.md} | | | |

#### 3.2 Technical Context {#_technical_context}

Generate from the target graph adapter/out nodes:
- Each adapter/out implementation = one technical channel
- Include protocol, format, authentication

| Channel | Protocol/Technology | Description |
|---------|-------------------|-------------|
| {For each adapter/out in target: REST/Feign/Kafka/DB/etc.} | | |

---

### 4. Solution Strategy {#section-solution-strategy}

**Data Sources:**
- `decisions.md` → all architecture decisions
- `mapping.md` → C++ to Java translation strategy
- `tech-debt.md` → intentional redesign decisions (not 1:1 ports)
- `java-target-standards.md` → pattern choices

**Generate:**
- Technology decisions table (from decisions.md)
- Architecture approach (hexagonal for libraries, 4-layer for DATEV services)
- Migration strategy summary:
  - Wave-based execution (domain first, then ports, then adapters)
  - Behavioral equivalence enforced through golden-master tests
  - Graphify-tracked architecture evolution
  - Patterns that were redesigned vs 1:1 ported (from tech-debt.md)
- Quality approach: ArchUnit, compile-on-save, domain purity hooks, Cucumber BDD

---

### 5. Building Block View {#section-building-block-view}

**Data Sources:**
- Target graph → communities = Level 1 building blocks
- Target graph → nodes within communities = Level 2
- Target graph → god nodes = cross-cutting components
- `GRAPH_REPORT.md` → community labels
- `mapping.md` → what each block corresponds to in C++

#### 5.1 Whitebox Overall System {#_whitebox_overall_system}

**Overview Diagram:** Generate Mermaid diagram from target graph communities:
- Each community = one black box
- Edges between communities = interfaces between blocks
- God nodes shown as cross-cutting (they connect multiple communities)

**Motivation:** Derived from migration goal + architecture decisions.

**Contained Building Blocks:**

| Building Block | Description | Source (C++) |
|---------------|-------------|-------------|
| {Community 1 label} | {From GRAPH_REPORT.md} | {From mapping.md} |
| {Community 2 label} | | |
| ... | | |

**Important Interfaces:** List edges between communities (from graph), labeled with purpose.

#### Per-block detail (Black Box Template):

For each top-level building block (community), generate:

```markdown
### {Community Label} {#_building_block_N}

**Purpose/Responsibility:** {From community's dominant node types and GRAPH_REPORT description}

**Interface(s):** {Edges connecting this community to others — list source→target with relationship label}

**Quality/Performance:** {Any god nodes in this community indicate coupling hotspots}

**Directory/File Location:** {Package path from target graph node source_location fields}

**Fulfilled Requirements:** {Trace back to roadmap.md phases that produced this block}

**Open Issues/Risks:** {From tech-debt.md items relating to this community's nodes}
```

#### Level 2 {#_level_2}

For each major community, expand into its constituent nodes:
- Group by hexagonal layer (domain / application / adapter)
- Show internal relationships

#### Level 3 {#_level_3}

Only generate for complex building blocks (communities with >15 nodes or god nodes with degree >10).

---

### 6. Runtime View {#section-runtime-view}

**Data Sources:**
- Phase analysis files → "Data Flow & Ownership" sections
- Source graph → `graphify path` queries between key nodes
- Target graph → call sequences through layers

**Generate runtime scenarios for key business flows:**

Use `graphify path` to trace the primary data flows:
```bash
graphify path "{entry_point_node}" "{output_node}"
```

For each major use case identified in the source analysis:

```markdown
## {Use Case Name} {#_runtime_scenario_N}

{Mermaid sequence diagram generated from graph path traversal}

```mermaid
sequenceDiagram
    participant {Layer1}
    participant {Layer2}
    participant {Layer3}
    {Steps derived from graph path, one arrow per edge}
```

{Description of notable aspects: which community boundaries are crossed,
which god nodes are involved, which surprising connections activate}
```

Minimum: generate scenarios for the top 3 data flows (highest-traffic paths in graph).

---

### 7. Deployment View {#section-deployment-view}

**Data Sources:**
- `config.json` → `deployment_target`
- `decisions.md` → infrastructure decisions
- Target project manifest files (if exist: `manifest.yml`, `Jenkinsfile`, `deployment/`)
- `application-*.yml` files in target (reveal environment profiles)

#### 7.1 Infrastructure Level 1 {#_infrastructure_level_1}

**Overview Diagram:** Mermaid deployment diagram showing:
- Runtime environment (Cloud Foundry / Kubernetes / standalone JVM)
- External services the system connects to (from graph adapter/out nodes)
- Data stores

| Environment | Profile | Config File | Notes |
|------------|---------|-------------|-------|
| Local/Dev | `default` | `application.yml` | H2/embedded Mongo |
| QS | `qs` / `test-it` | `application-qs.yml` | Dedicated test DB |
| Production | `cloud` / `cloudfoundry` | `application-cloudfoundry.yml` | Full HA |

**Mapping of Building Blocks to Infrastructure:**
- Map target graph communities to deployment units
- If single deployable (monolith): all communities in one JAR
- If library: shipped as artifact to Maven/GitHub Packages

#### 7.2 Infrastructure Level 2 {#_infrastructure_level_2}

Only generate if multi-service deployment or complex infrastructure:
- Per-service details (memory, instances, scaling)
- From Cloud Foundry manifests or K8s YAMLs in target project

---

### 8. Cross-cutting Concepts {#section-concepts}

**Data Sources:**
- Target graph → surprising connections (cross-community edges indicate shared concepts)
- `java-target-standards.md` → standard patterns applied
- Phase analysis files → shared patterns identified across phases
- Source graph → infrastructure nodes shared by multiple communities

**Generate one subsection per cross-cutting concern:**

| Concept | Data Source | Content |
|---------|-------------|---------|
| Security | java-target-standards §4 + decisions.md | @RvoSecurity, FKT users, OAuth2/Basic Auth |
| Logging & Monitoring | java-target-standards §9 | @Slf4j, Splunk markers, VK3 masking, MDC |
| Error Handling | java-target-standards §7 | Rvo*Exception hierarchy, ErrorDto, @ControllerAdvice |
| Persistence | java-target-standards §5 | DbAdapter pattern, JPA conventions, MongoDB patterns |
| Object Mapping | java-target-standards §6 | MapStruct, unmappedTargetPolicy=ERROR, 3-layer chain |
| Testing Strategy | java-target-standards §10 | JUnit 5 + Cucumber(DE) + ArchUnit + WireMock |
| External Communication | java-target-standards §8 | Feign clients, adapter pattern, request-scoped cache |
| Configuration | java-target-standards §9 | Profile strategy, VCAP services, @ConfigurationProperties |

---

### 9. Architecture Decisions {#section-design-decisions}

**Data Sources:**
- `decisions.md` → direct reformatting as ADR entries
- `tech-debt.md` → decisions about intentional divergence from C++ source

**Format each decision as:**

```markdown
## ADR-{NN}: {Title}

**Status:** Accepted
**Date:** {From decisions.md timestamp or migration start date}
**Context:** {The situation that required a decision}
**Decision:** {What was decided}
**Consequences:** {Impact — derived from graph: which communities/nodes are affected}
```

Include ALL decisions from decisions.md. Add supplementary decisions from tech-debt.md
(these represent "decided NOT to port 1:1" choices).

---

### 10. Quality Requirements {#section-quality-scenarios}

**Data Sources:**
- Verification reports (nn-verification.md) → quality metrics achieved
- ArchUnit rules → architecture quality enforcement
- Test coverage reports
- Graphify graph statistics → coupling metrics

#### 10.1 Quality Requirements Overview {#_quality_requirements_overview}

| Quality Goal | Scenario | Metric | Achieved |
|-------------|----------|--------|----------|
| Behavioral equivalence | All golden-master tests pass | 100% | {from verify reports} |
| Architecture conformance | ArchUnit rules without violation | 0 violations | {from verify reports} |
| Test coverage | All public methods tested | >80% line coverage | {from verify reports} |
| Coupling control | No god node exceeds source max | Max degree ≤ {source max} | {from target graph} |
| Layer isolation | No domain→adapter dependencies | 0 cross-layer paths | {from graphify path checks} |

#### 10.2 Quality Scenarios {#_quality_scenarios}

Generate testable scenarios from verification findings:
- "When a new developer reads the domain module, they find zero framework imports"
- "When running ArchUnit tests, all hexagonal rules pass"
- "When comparing source and target graphs, coverage exceeds 90%"

---

### 11. Risks and Technical Debts {#section-technical-risks}

**Data Sources:**
- `tech-debt.md` → known debt items with priority
- Source graph → god nodes (complexity risk — high coupling in source may propagate)
- Architecture drift report → uncovered source concepts
- `research/risk-matrix.md` → original risk assessment from init
- Verification reports → any PASS_WITH_NOTES items

**Generate:**

| Risk/Debt | Source | Impact | Mitigation | Status |
|-----------|--------|--------|-----------|--------|
| {God node X with degree Y} | Source graph | High coupling may propagate | Monitor target graph degree | {Resolved/Open} |
| {Pattern Z not portable} | tech-debt.md | Required redesign | {Decision D-NN} | {Resolved/Open} |
| {Unmapped source concept} | Drift report | Possible functionality gap | Verify intentional | {Open} |
| {From risk-matrix.md} | Init assessment | {Impact} | {Mitigation} | {Resolved/Open} |

---

### 12. Glossary {#section-glossary}

**Data Sources:**
- Source graph → all node labels (especially German domain terms)
- `mapping.md` → C++ term → Java term mapping
- Model class field names → German business vocabulary
- Target project domain classes → current naming

**Generate:**

| Term | Definition | Java Equivalent |
|------|-----------|-----------------|
| {German domain term from source graph} | {Meaning in business context} | {Java class/package name from mapping.md} |

Focus on:
1. German business terms preserved in code (Auswertung, Mandant, Berater, Kennziffer, etc.)
2. C++ technical terms that were renamed in Java
3. Abbreviations used in the codebase (VK3, GuV, BWA, etc.)
4. DATEV-specific terminology (FKT user, Personengruppe, Anlagespiegel, etc.)

---

## Generation Rules

1. **Structure:** Match the official arc42 v9.0-EN template structure exactly (section numbers, heading anchors)
2. **Language:** Content in German for DATEV projects; section headings remain English (anchor compatibility)
3. **Diagrams:** Mermaid syntax for all diagrams (renderable in GitLab, GitHub, IntelliJ)
4. **Graph References:** Every section MUST cite specific Graphify data (node counts, community names, path results)
5. **Traceability:** Link each statement to its source artifact (`decisions.md D-NN`, `graph node X`, etc.)
6. **Incremental:** Can be regenerated at any time — reads current state, not cached
7. **Honesty:** If data for a section is unavailable, state explicitly what's missing — never invent
8. **Black Box Template:** Follow the official arc42 black box template format for Building Block View entries
9. **Anchor IDs:** Preserve `{#section-*}` anchors from official template for cross-reference compatibility
10. **No placeholder content:** If a section would only contain template placeholders, omit it with a note explaining what data is needed to populate it
