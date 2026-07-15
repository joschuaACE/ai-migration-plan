# migrate-plan

Generate executable translation plans from analysis — dependency-ordered PLAN.md files for each translation unit with exact instructions a translator agent can follow mechanically.

## When to Use

After migrate-analyze N completes successfully. Plans MUST be generated before execution. This is the second step in the phase cycle: Analyze → **Plan** → Execute → Verify → Review.

## Inputs

- **Phase number** (required) — which phase to plan
- **--strategy flag** (optional) — override default translation strategy:
  - `conservative`: 1:1 structural mapping, minimize redesign
  - `modern`: leverage Spring Boot 4.x idioms fully, accept structural divergence
  - `hybrid` (default): conservative for core logic, modern for infrastructure

**Required state:**
- `.migration/phases/NN-slug/nn-analysis.md` must exist
- Phase status must be "Analyzing" complete or "Planning"

**Context to read before starting:**
1. nn-analysis.md → understand the module deeply
2. mapping.md → know where each class lands in hexagonal structure
3. decisions.md → respect all recorded decisions
4. Java target standards → enforce architecture rules
5. config.json → check output_type (determines which waves apply)
6. .migration/research/dependency-map.md → map each C++ dependency to its Java equivalent for translation

## Procedure

### Step 1: Decompose into Translation Units

1. Read nn-analysis.md completely
2. Identify translation units (one plan per):
   - Each C++ class that becomes a domain entity/service → 1 plan
   - Each C++ class that becomes a port interface + adapter → 1 plan
   - Each C++ class that becomes a use case → 1 plan
   - Groups of tightly-coupled small classes → 1 plan (if <100 LOC total)
3. For each unit, determine target hexagonal layer from mapping.md

### Step 2: Dependency Order into Waves

Assign each plan to a wave following hexagonal layer order. Wave availability depends on `output_type` from config.json:

```
Wave 1: domain/model/     — entities, value objects, records, enums (ALL types)
Wave 2: domain/port/      — interfaces for in/ and out/ (ALL types)
Wave 3: domain/service/   — business rules (ALL types)
Wave 4: application/      — use cases, DTOs, mappers (ALL types)
Wave 5: adapter/out/      — persistence, clients, messaging (ALL types)
Wave 6: adapter/in/       — controllers (service), CLI commands (cli), SKIP for library/sdk
Wave 7: config/           — Spring config (service/cli), auto-config (library/sdk if Spring support)
```

**Output type adjustments:**
- **library/sdk:** Skip Wave 6 entirely. Wave 7 is optional (only if providing Spring auto-configuration for consumers). Add a Wave 5b: `spi/` — default SPI implementations.
- **cli:** Wave 6 becomes adapter/in/cli/ (Picocli @Command classes instead of @RestController)
- **service:** All waves apply as shown (default behavior)

Within each wave, order by internal dependency (if A uses B, B comes first).

### Step 3: Generate Plan Files

For each translation unit, create nn-pp-plan.md with YAML frontmatter:

```yaml
---
phase: <N>
plan: <PP>
wave: <1-7>
title: "<descriptive name>"
source_files:
  - "<path to C++ source>"
  - "<path to C++ header>"
target_files:
  - "<target Java file path>"
  - "<target test file path>"
target_layer: "domain/service"
depends_on: [<plan-ids this depends on>]
dependency_map_applied: true
complexity: <1-5>
strategy: <conservative|modern|hybrid>
must_haves:
  truths:
    - "<behavioral truth that must hold after translation>"
  artifacts:
    - "<file that must exist after execution>"
  tests:
    - "<test that must pass>"
---
```

Then the plan body with these sections:

- **Objective** — what this plan accomplishes in one sentence
- **Source Analysis Summary** — key findings from ANALYSIS.md relevant to this unit
- **Translation Table** — C++ Element → Java Target → Layer → Notes (every public method mapped)
- **Dependency Mapping** — from dependency-map.md: C++ Dependency → Java Replacement → Confidence → Notes. Translators MUST use the Java replacements listed. Do NOT introduce alternatives.
- **Target Structure** — skeleton of the Java class with package, constructor, and method signatures
- **Spring Annotations** — which annotations to apply where (none in domain/)
- **Test Strategy** — port existing C++ tests, add boundary value tests, test naming convention: should_\<behavior\>_when_\<condition\>
- **Dependencies Required** — any new Gradle dependencies needed
- **Verification Criteria** — compile, tests pass, behavioral equivalence checks, ArchUnit passes

### Step 4: Plan Verification

4. After all plans generated, verify:
   - Every source file from ANALYSIS.md is covered by at least one plan
   - No target file appears in two plans (no conflicts)
   - Wave ordering respects dependencies (no plan depends on a later wave)
   - Every public method in C++ has a mapping entry
   - Every C++ dependency used in this phase's source files has a mapping entry in the plan
   - Every plan has at least one `must_haves.truths` entry
   - Every plan produces at least one test file

5. If verification fails:
   - Identify gaps
   - Generate additional plans or adjust existing ones
   - Re-verify (max 3 iterations)

### Step 5: Gate & Update

6. Present plan summary to user:
   - Plans generated: N
   - Waves: M
   - Total source files covered: X
   - Estimated complexity distribution
7. Ask user to confirm plans (unless auto mode in STATE)
8. Update state.md: `status: planned`, record plan count
9. Suggest next step: migrate-execute N

## Outputs

- One or more `.migration/phases/NN-slug/nn-pp-plan.md` files (one per translation unit)

## Success Criteria

- Every source file in the phase maps to at least one plan
- Plans are dependency-ordered into waves (no forward references)
- Each plan has YAML frontmatter with complete metadata
- Each plan has a translation table (C++ → Java mapping)
- Each plan specifies test strategy
- Each plan has verification criteria
- Wave ordering matches hexagonal layers
- User confirmed the plans
- state.md updated
