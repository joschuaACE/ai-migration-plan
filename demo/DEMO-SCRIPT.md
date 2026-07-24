# POC Presentation — Demo Script

**Format:** Hybrid — slides for narrative framing, live code for credibility.  
**Duration:** 45-60 min  
**Tools needed:** Browser (slides), IntelliJ/VS Code (code), Terminal (git + gradle)

---

## Flow: Slide → Code → Slide → Code

The key insight: **slides set the context, code proves it**. Never stay on slides for more than 2-3 minutes before switching to live.

---

## Act 1: The Hook (5 min)

### Slide 1: Title
> "Your Legacy. Modernized. Proven."

### Slide 2: The Challenge
> Brief — they know the problem. Don't dwell.

### Slide 3: The Proof (hero metrics)
> "These aren't projections. Let me show you."

**→ SWITCH TO TERMINAL:**

```bash
cd /home/josh/Desktop/dev/datev/ai-migration

# Show the git history — each phase is a commit
git log --oneline migrate-phase-1-complete..migration-complete

# Show the tags — clean migration milestones
git tag -l
```

> "Every phase is a tagged commit. You can check out any point in the journey. Let's start from the beginning."

---

## Act 2: The Journey (15 min)

### Show the source (1 min)

```bash
# Show what we started with
ls source/DvBilaAufbKern/
wc -l source/DvBilaAufbKern/*.cpp source/DvBilaAufbKern/*.CPP source/DvBilaAufbKern/*.h source/DvBilaAufbKern/*.H 2>/dev/null | tail -1

# "38,854 lines of C++98, Windows-specific, no tests, one flat directory"
```

### Show the analysis & planning (3 min)

```bash
# The AI's understanding of the codebase
cat .migration/inventory.md | head -60

# The phase plan — dependency ordered
cat .migration/roadmap.md | head -80

# Architectural decisions — all documented
cat .migration/decisions.md
```

> "The AI doesn't just translate line-by-line. It understands the architecture, maps dependencies, and plans a migration order that ensures every phase compiles on its own."

### Walk through one phase deeply (5 min)

```bash
# Phase 2 is the most impressive — god class decomposition
cat .migration/phases/02-base-framework/02-analysis.md | head -80

# Show what a wave plan looks like
cat .migration/phases/02-base-framework/02-01-plan.md
```

**→ SWITCH TO IDE:** Open the Java project structure.

Show the package layout:
```
app/src/main/java/com/datev/bilanz/dvbilaaufbkern/
├── api/          (4 files — the PUBLIC contract)
├── spi/          (10 interfaces — extension points)
└── internal/     (107 files — encapsulated)
```

> "This was a 4,079-line god class. The AI decomposed it into focused, testable components — each in its own package."

### Slide 4: Architecture Transformation
> Show briefly as summary of what they just saw live.

### Slide 5: Before/After Code
> "Let me show you this live."

**→ SWITCH TO IDE:** Open side-by-side:
- `source/DvBilaAufbKern/Alternativ.cpp`
- `app/src/main/java/.../internal/model/Alternativ.java`

Walk through:
- Global `KeineUmrechnung` → static `KEINE_UMRECHNUNG`
- `operator bool()` → `isActive()` method
- Raw pointers → null-safe delegation
- Manual destructor → GC handles it
- Same business semantics, modern idioms

---

## Act 3: Prove It Compiles & Passes (5 min)

**→ TERMINAL:**

```bash
cd app

# Compile — must be instant, no errors
./gradlew compileJava

# Run all tests
./gradlew test

# Show test report
open build/reports/tests/test/index.html
```

> "146 tests. All passing. This isn't a prototype — it's production-ready code."

### Show the ArchUnit test (IDE)

Open `HexagonalArchitectureTest.java`:

> "These rules run on every build. If anyone breaks the architecture — API depending on internal, Spring leaking into domain — the build fails."

### Show module-info.java (IDE)

> "The Java module system enforces the API boundary at the JVM level. Consumers can only see `api/` and `spi/`. Everything in `internal/` is encapsulated."

---

## Act 4: The Framework (10 min)

### Slide 6: The Framework
> Brief overview of the 6 steps.

### Slide 6b: We Learn From Your Code
> "This is key. Let me show you what I mean."

**→ SWITCH TO IDE:** Open their actual code side by side:
- Their `access-administration-service` (Template D)
- Our generated code

Point out identical patterns:
- `@RequiredArgsConstructor` + `@Slf4j`
- Layered architecture naming
- Exception handling style
- Constructor injection

### Slide 6c: Pattern Adoption
> Summary slide confirming what they just saw.

### Show the framework repo (2 min)

```bash
cd /home/josh/Desktop/dev/datev/ai-migration-plan

# Show the structure
tree docs/ -L 1

# Show a standards file
cat docs/standards/migration-philosophy.md | head -40

# Show how it gets installed
cat agents/kiro/install.sh | head -30
```

> "One source of truth. Multiple AI agents can use it. The knowledge is portable."

---

## Act 5: Quality & Methodology (5 min)

### Slide 7: Quality Gates
> Brief.

**→ TERMINAL:**

```bash
cd /home/josh/Desktop/dev/datev/ai-migration

# Show the hooks
cat .kiro/hooks/migration-quality.json | python3 -m json.tool

# Show a steering file
head -30 .kiro/steering/migration-philosophy.md
```

### Slide 8: God Class Decomposition
> "You saw this live. The 4,079-line CBaKAuswBasis became 5 focused classes + 27 model types."

### Slide 9: Migration Phases
> Show all 7 phases at a glance.

**→ TERMINAL:** Walk the git history interactively.

```bash
# Show the diff stats per phase
git diff --stat migrate-phase-1-complete migrate-phase-2-complete
git diff --stat migrate-phase-6-complete migration-complete
```

> "Each phase builds on the previous. Each produces compilable, tested code."

---

## Act 6: Scale & Close (10 min)

### Slide 10: The Advantage
### Slide 11: Multi-Source Capability

**→ TERMINAL:** Briefly show their own ZOT source if relevant:

```bash
ls /home/josh/Desktop/dev/datev/Template_A_to_D/C_CPP_ZOT_DvBilaAufbKern/DvBilaAufbKern/ | wc -l
# "200+ files. Same framework, same process. Ready to go."
```

### Slide 12: 3-Year Roadmap
### Slide 13: Why Us
### Slide 14: What We Delivered
### Slide 15: Call to Action

---

## Act 5b: The `.migration/` Folder — Your Migration Control Center (5-7 min)

> **When to show this:** After the quality gates discussion, or when someone asks "how do you track progress?" or "where is all this documented?"

**Setup line:**
> "I want to show you something that no other AI migration approach gives you. The AI doesn't just produce code — it produces a complete audit trail. Everything lives in one folder."

### The Walkthrough

**→ TERMINAL:**

```bash
cd /home/josh/Desktop/dev/datev/ai-migration

# Show the full structure
find .migration -type f | sort
```

**Explain the layers (point at terminal output):**

> "This is the `.migration/` directory. Think of it as a project management system that lives inside your git repo. Let me walk you through the layers."

---

### Layer 1: The Dashboard (30 sec)

```bash
cat .migration/state.md
```

> "This is your single-pane-of-glass. Status, active phase, files migrated, files remaining. At any moment, anyone on your team can run this one command and know exactly where the migration stands."

**Key things to point out:**
- `status: completed` / `active_phase: 7` / `total_phases: 7`
- `files_migrated: 51` / `files_remaining: 0`
- The last_updated timestamp

---

### Layer 2: Configuration & Decisions (1 min)

```bash
# What was configured
cat .migration/config.json

# What was DECIDED (by humans, not AI)
cat .migration/decisions.md
```

> "Config.json is the machine-readable settings — output type, Java version, architecture style. Decisions.md is the human-readable WHY — every architectural choice is numbered and justified. D-01 through D-08. If your architect disagrees with D-04, they change it here and the next phase respects it."

**Key things to point out:**
- `output_type: "library"` — because the C++ produced a .lib, not an executable
- `preserve_german_names: true` — deliberate domain decision
- `golden_master.deferred: true` — honest about what we CAN'T verify yet

---

### Layer 3: Research & Risk (1 min)

```bash
# What technologies were detected
cat .migration/research/legacy-stack.md | head -30

# What could go wrong — identified BEFORE writing code
cat .migration/research/risk-matrix.md | head -25

# How every C++ dependency maps to Java
cat .migration/research/dependency-map.md | head -30
```

> "Before writing a single line of Java, the framework does research. It identifies 12 risks, maps every dependency, and documents the legacy stack. This is how we avoid surprises in month 6."

---

### Layer 4: The Roadmap (1 min)

```bash
cat .migration/roadmap.md | head -50
```

> "The roadmap is dependency-ordered. Phase 1 has no dependencies. Phase 7 depends on ALL previous phases. You can't accidentally start Phase 4 before Phase 2 is done — the dependency graph prevents it."

**Draw attention to:**
- The phase dependency diagram at the bottom
- Files assigned to each phase
- Complexity ratings

---

### Layer 5: Per-Phase Deep Dive (2 min)

```bash
# Show what's inside one phase
ls .migration/phases/02-base-framework/

# The analysis — done BEFORE any code is written
cat .migration/phases/02-base-framework/02-analysis.md | head -40

# One wave plan — specific instructions for translation
cat .migration/phases/02-base-framework/02-01-plan.md | head -30

# The verification — done AFTER code is written
cat .migration/phases/02-base-framework/02-verification.md | head -25
```

> "Every phase goes through the same cycle: analysis → plan → execute → verify. Phase 2 had 6 wave plans because it was the god class decomposition — the hardest part. Each plan is reviewable by your senior devs BEFORE execution."

---

### Layer 6: Mapping & Traceability (30 sec)

```bash
cat .migration/mapping.md | head -50
```

> "Every C++ class maps to a specific Java package and class. If an auditor asks 'where did CBaKAuswKtoNachweis end up?' — the answer is right here. Complete traceability."

---

### Summary Slide / Verbal Recap

> "Let me summarize what `.migration/` gives you:"

| What | File | Why it matters |
|------|------|---------------|
| Progress dashboard | `state.md` | Anyone can check status in 5 seconds |
| Configuration | `config.json` | Machine-readable settings, version controlled |
| Architecture decisions | `decisions.md` | Auditable, overridable, human-authored |
| Risk management | `research/risk-matrix.md` | Risks identified before writing code |
| Dependency mapping | `research/dependency-map.md` | Every C++ lib → Java equivalent |
| Phase plans | `phases/nn-*/nn-pp-plan.md` | Reviewable before execution |
| Verification reports | `phases/nn-*/nn-verification.md` | Semantic equivalence scores |
| C++ → Java class map | `mapping.md` | Full audit traceability |
| Tech debt register | `tech-debt.md` | Honest about what needed redesign |

> "This entire folder is in your git repo. Version-controlled. Diffable. Auditable. No external tool, no proprietary platform, no SaaS dependency. Just markdown and JSON in git."

---

### The Killer Line

> "If we disappear tomorrow, your next team opens this folder and knows EXACTLY what was done, why, and what's left. That's what a professional migration looks like."

---

## Key Demo Commands (cheat sheet)

```bash
# In the migration repo
cd /home/josh/Desktop/dev/datev/ai-migration

# Git history (clean phase commits)
git log --oneline migrate-phase-1-complete..migration-complete

# Tags
git tag -l

# Checkout any phase to show intermediate state
git checkout migrate-phase-2-complete  # shows state after phase 2
git checkout main                      # back to final

# Show diff between phases
git diff --stat migrate-phase-1-complete migrate-phase-2-complete

# Source stats
wc -l source/DvBilaAufbKern/*.cpp source/DvBilaAufbKern/*.CPP 2>/dev/null | tail -1

# Java output stats  
find app/src/main/java -name "*.java" | wc -l   # 121 production files
find app/src/test/java -name "*.java" | wc -l   # test files

# Build & test
cd app && ./gradlew compileJava    # ~5 sec
cd app && ./gradlew test           # ~4 sec, 146 tests

# Framework repo
cd /home/josh/Desktop/dev/datev/ai-migration-plan
tree docs/ -L 2
```

---

## Talking Points (when they ask questions)

---

# Q&A PREPARATION GUIDE

## Strategy: Proactive Answering

**Don't wait for them to ask.** During the demo, naturally weave these answers into your flow. When you reach the relevant moment, say:

> "Now, the question you're probably thinking is..."

This shows you've thought deeper than they expected.

---

## PROACTIVE QUESTIONS — You Bring These Up First

These are the questions that, if you answer before they ask, create the "these people thought of everything" feeling.

---

### P-1: "What happens if the AI hallucinates?"

**When to bring up:** After showing the Build & Test slide / live demo.

**Answer:**
> "Great question that nobody usually asks until it's too late. We built the framework assuming AI WILL make mistakes. That's why every phase has 5 safety nets."

**Live proof:**

```bash
cd /home/josh/Desktop/dev/datev/ai-migration

# Show the verification file — semantic equivalence scores
cat .migration/phases/02-base-framework/02-verification.md | head -30

# Show ArchUnit catches structural mistakes automatically
cat app/src/test/java/com/datev/bilanz/dvbilaaufbkern/HexagonalArchitectureTest.java

# Show module-info prevents accidental exposure
cat app/src/main/java/module-info.java
```

**Key phrase:**
> "The AI proposes. The framework verifies. Compilation, ArchUnit, module boundaries, semantic comparison, two-pass review. A hallucination can't survive 5 gates."

---

### P-2: "How do you handle a 4,000-line god class?"

**When to bring up:** While showing the architecture transformation slide.

**Answer:**
> "This is the hardest problem in legacy migration. Let me show you exactly how we solved it — it's documented."

**Live proof:**

```bash
# Show the deliberate redesign decision
cat .migration/tech-debt.md | head -30

# Show the analysis that preceded the decomposition
cat .migration/phases/02-base-framework/02-analysis.md | head -60

# Show the result in IDE: 5 focused classes instead of 1 god class
ls app/src/main/java/com/datev/bilanz/dvbilaaufbkern/internal/basis/
```

**Key phrase:**
> "We don't just translate. We document the redesign decision, show the reasoning, decompose with purpose, and verify the result still behaves identically. Every decision is auditable."

---

### P-3: "What if we stop mid-migration? Is our investment lost?"

**When to bring up:** During the roadmap / scale discussion.

**Answer:**
> "Every single phase produces a standalone, compilable, tested artifact. Let me show you."

**Live proof:**

```bash
# Check out phase 2 — the project COMPILES at this intermediate state
git checkout migrate-phase-2-complete
cd app && ./gradlew compileJava
# BUILD SUCCESSFUL

# Come back to final
git checkout main
```

**Key phrase:**
> "At any tag, you have working software. You can pause after phase 3, ship what you have, and resume 6 months later. The framework has a `migrate-resume` command specifically for this."

---

### P-4: "How do we know the migration is actually complete and reliable?"

**When to bring up:** After showing the test suite passing.

**Answer:**
> "Three levels of confidence, each independently verifiable."

**Live proof:**

```bash
# Level 1: Structural completeness — all 51 files mapped
cat .migration/state.md | grep -A 5 "progress"

# Level 2: Semantic verification — score per phase
cat .migration/phases/01-foundation/01-verification.md | head -20
cat .migration/phases/02-base-framework/02-verification.md | head -20

# Level 3: Golden Master readiness (designed, waiting for your C++ access)
cat .migration/validation/test-variants.md
```

**Key phrase:**
> "100% file coverage is necessary but not sufficient. We also verify semantic equivalence method-by-method — there's a score per phase. And when you give us access to the C++ engine, we run Golden Master: same input, both engines, compare output byte-by-byte."

---

### P-5: "Can our developers steer the AI? Or is it a black box?"

**When to bring up:** After showing the framework methodology.

**Answer:**
> "Total control. Let me show you the steering mechanism."

**Live proof:**

```bash
# The config — your team controls all settings
cat .migration/config.json

# The decisions log — humans decide, AI executes
cat .migration/decisions.md

# The steering documents — rules the AI must follow
ls /home/josh/Desktop/dev/datev/ai-migration/.kiro/steering/
head -40 /home/josh/Desktop/dev/datev/ai-migration/.kiro/steering/migration-philosophy.md
```

**Key phrase:**
> "The AI doesn't decide the architecture. Your architects do — through steering documents. The AI follows the plan. If it deviates, the quality gates catch it. Your developers can override any decision in `decisions.md` and the next phase respects it."

---

### P-6: "How can I see the progress at any time?"

**When to bring up:** While showing git tags.

**Answer:**
> "Real-time visibility at three levels: state file, git history, and phase verification reports."

**Live proof:**

```bash
# High-level dashboard
cat .migration/state.md

# Per-phase progress  
ls .migration/phases/

# Git gives you exact diff of what changed per phase
git diff --stat migrate-phase-3-complete migrate-phase-4-complete

# Line-by-line — how many Java lines were produced per phase
git log --oneline --stat migrate-phase-1-complete..migration-complete | grep "files changed"
```

**Key phrase:**
> "At any moment you can run `cat .migration/state.md` and see: which phase we're on, how many files migrated, what's remaining, what's blocked. It's like a project dashboard — but in your git repo."

---

## THEIR QUESTIONS — What They'll Ask & How to Crush It

---

### Q-1: CTO — "How does this scale to 100 modules?"

**Answer:**
> "The framework gets BETTER with scale, not worse. Here's why."

**Live proof:**

```bash
# Show the framework is portable — one install command
cd /home/josh/Desktop/dev/datev/ai-migration-plan
cat install.sh

# Show the standards are centralized — one source of truth
ls docs/standards/
ls docs/skills/

# Every module gets the same quality
cat docs/hooks/migration-quality.md
```

**Key points:**
- Module 50 uses the same standards as module 1
- Patterns learned in DvBilaAufbKern (e.g., ZOT visitor, Bedingung handling) are now in the knowledge base
- Multiple AI agents can work on different modules in parallel
- Framework config is per-module — different output types (library, service, CLI) same process

---

### Q-2: Architect — "How do you ensure behavioral equivalence without running the original?"

**Answer:**
> "Three strategies, ranging from structural to runtime."

**Live proof:**

```bash
# Strategy 1: Method-by-method semantic mapping
cat .migration/phases/01-foundation/01-verification.md | grep -A 5 "Method-Level"

# Strategy 2: Risk matrix — we identified 12 risks before writing any code
cat .migration/research/risk-matrix.md | head -20

# Strategy 3: Golden Master plan (ready to activate)
cat .migration/validation/test-variants.md
cat .migration/validation/poc-config.json
```

**Key phrase:**
> "We verify in layers: structural mapping (every method accounted for), semantic analysis (does the Java method do what the C++ method did?), and finally Golden Master (same input → same output). Layers 1 and 2 are complete. Layer 3 activates when you give us C++ engine access."

---

### Q-3: Architect — "What about performance? Java is slower than C++."

**Answer:**
> "For a calculation library called from a service layer, the bottleneck is never CPU — it's I/O, database, and network. But let me address it directly."

**Key points:**
- Java 25 with virtual threads and JIT compilation performs comparably for business logic
- BigDecimal is slower than raw doubles — but it's CORRECT for financial calculations (C++ used doubles which have precision issues)
- The hexagonal architecture allows you to benchmark each port independently
- If profiling shows a hot path, you can optimize that specific method — the architecture isolates it

---

### Q-4: Lead Dev — "What if I disagree with an architectural decision the AI made?"

**Answer:**
> "You override it. Let me show you the mechanism."

**Live proof:**

```bash
# Every decision is in this file
cat .migration/decisions.md

# You add your own decision or change one:
# D-09: "Use records instead of Lombok for model classes"
# The next phase respects it.

# The steering docs are human-editable
cat /home/josh/Desktop/dev/datev/ai-migration/.kiro/steering/java-target-standards.md | head -30
```

**Key phrase:**
> "The AI is opinionated by default — but every opinion is overridable. Add a decision to `decisions.md`, edit the steering doc, or reject a phase in review. You have final say."

---

### Q-5: Lead Dev — "Can I see what the AI was 'thinking' for each translation?"

**Answer:**
> "Yes — every wave plan documents the reasoning."

**Live proof:**

```bash
# Each file has a translation plan with rationale
cat .migration/phases/01-foundation/01-01-plan.md

# Multi-file waves show dependencies and order
cat .migration/phases/02-base-framework/02-01-plan.md | head -40

# The analysis explains WHY things were decomposed
cat .migration/phases/02-base-framework/02-analysis.md | head -40
```

**Key phrase:**
> "There are 30+ wave plans in this repo. Each one says: this C++ construct becomes this Java pattern, for this reason, with these risks noted. Your senior devs can review these BEFORE we execute."

---

### Q-6: Lead Dev — "How do you handle platform-specific code (LPCTSTR, TCHAR, MFC)?"

**Answer:**
> "We identified this in the research phase. Let me show you."

**Live proof:**

```bash
# Legacy stack analysis  
cat .migration/research/legacy-stack.md | head -40

# The mapping decisions
cat .migration/mapping.md | head -40
```

**Key points:**
- `LPCTSTR` / `CString` → `String` (with UTF-8 awareness)
- `TCHAR` → removed (Java is always Unicode)
- `CBaKCurrency` → `BigDecimal` (precision-safe)
- `BIASSERT` → defensive null checks + test coverage (no runtime assertions)
- MFC containers → Java collections (`CTypedPtrList` → `List<T>`)
- Copy constructors → immutable value objects
- `operator bool()` → `isActive()` explicit methods

---

### Q-7: Finance — "What's the exit strategy if this doesn't work?"

**Answer:**
> "You already have it. Let me show you."

**Live proof:**

```bash
# Every phase is a git tag — you can stop anywhere
git tag -l

# The source code is YOURS — it's standard Java, standard Gradle
cat app/build.gradle.kts

# No proprietary runtime, no lock-in
cat app/src/main/java/module-info.java
# Only depends on slf4j — nothing else
```

**Key phrase:**
> "Three exit ramps: 1) Stop after any phase — you keep working software. 2) Your Java developers can take over and continue manually — it's standard code, standard build. 3) Switch AI provider — the framework works with Kiro, Claude, or Codex. No lock-in at any level."

---

### Q-8: Security — "Where does our code go? Who sees it?"

**Answer:**
> "Your code never leaves your infrastructure."

**Key points:**
- The framework is a set of markdown files + bash scripts — installs locally
- AI agents run on YOUR machine / YOUR CI — we don't host anything
- No cloud upload of source code (unless you choose to use a cloud AI provider)
- Compatible with on-premise AI models if required (local LLMs)
- All migration artifacts stay in YOUR git repo
- We can sign NDAs and work within your security perimeter

---

### Q-9: CTO — "Other companies offer AI migration. Why you?"

**Answer:**
> "Three things nobody else has in this room."

**Key points:**
1. **Proven on YOUR code** — not a synthetic demo. DvBilaAufbKern compiles and passes tests RIGHT NOW.
2. **Framework, not a service** — we leave you with a reusable asset. The framework stays after the engagement.
3. **Your patterns baked in** — we studied access-administration-service, user-management-service, refsys-aggregation-service. Our output looks like YOUR team wrote it.

**Live proof:**

```bash
# Show their patterns in our output
diff <(grep -r "@RequiredArgsConstructor\|@Slf4j" app/src/main/java/ | head -5) <(echo "Same as your RVO services")
```

---

### Q-10: Architect — "What about the ZOT subsystem? It's way bigger."

**Answer:**
> "It's the natural next step. And we're already designed to connect to it."

**Live proof:**

```bash
# Show the SPI interfaces — these ARE the ZOT connection points
ls app/src/main/java/com/datev/bilanz/dvbilaaufbkern/spi/
cat app/src/main/java/com/datev/bilanz/dvbilaaufbkern/spi/DruckTabCreator.java

# Show we already analyzed the ZOT source
ls /home/josh/Desktop/dev/datev/Template_A_to_D/C_CPP_ZOT_DvBilaAufbKern/DvBilaAufbKern/ | wc -l
# 200+ files — same framework, same process
```

**Key phrase:**
> "The SPI interfaces in this POC were DESIGNED as the integration point with ZOT. When we migrate ZOT, it implements these interfaces. The two libraries plug together through the ports."

---

## KILLER QUESTIONS — If They Ask These, You've Won

These are the questions that show they're already thinking about engagement terms:

### "When can you start the next module?"
> "Immediately. The framework is ready. Pick the module and we begin."

### "Can you train our team to use the framework?"
> "Absolutely. That's part of the value — you own the framework after the engagement."

### "What do you need from us to activate Golden Master?"
> "Access to build the C++ engine and run 4-6 representative ZOT variants. That's it."

### "How do we handle modules that depend on databases?"
> "The framework supports `output_type = service` — Spring Boot with hexagonal architecture, full observability. Different profile, same process."

---

## CONTINGENCY — If Something Goes Wrong During Demo

### Build fails:
```bash
# Quick recovery — reset and try again
cd app && ./gradlew clean compileJava
```

### Tests fail:
> "This is actually a feature — watch. The test tells us exactly what's wrong and where."
```bash
# Show the test report
cat app/build/reports/tests/test/index.html
```

### Terminal lag / IDE slow:
> Switch to slides and say: "Let me show you the result rather than waiting for the tooling."

### They want to see something you didn't prepare:
> "Let me show you in the repo. Everything is documented in `.migration/`."
```bash
find .migration/ -name "*.md" | head -20
```

---

## Files to Have Open in IDE Before Demo

1. `source/DvBilaAufbKern/Alternativ.cpp` — C++ source
2. `app/src/main/java/.../internal/model/Alternativ.java` — Java output
3. `app/src/main/java/.../internal/basis/AuswBasis.java` — decomposed god class
4. `app/src/main/java/.../api/AuswertungApi.java` — clean public API
5. `app/src/main/java/module-info.java` — module boundary
6. `app/src/test/.../HexagonalArchitectureTest.java` — ArchUnit rules
7. `.migration/roadmap.md` — phase plan
8. `.migration/decisions.md` — architecture decisions
9. `.migration/research/risk-matrix.md` — pre-identified risks
10. `.migration/tech-debt.md` — deliberate redesign decisions
11. `.migration/phases/02-base-framework/02-verification.md` — semantic scores

---

## Terminal Tabs to Have Ready

1. **Migration repo** — `cd /home/josh/Desktop/dev/datev/ai-migration`
2. **App build** — `cd /home/josh/Desktop/dev/datev/ai-migration/app`
3. **Framework repo** — `cd /home/josh/Desktop/dev/datev/ai-migration-plan`
4. **Template code** — `cd /home/josh/Desktop/dev/datev/Template_A_to_D`
