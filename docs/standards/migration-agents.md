# Migration Agent Definitions

Each agent is a specialized subagent spawned by skill orchestrators during migration.
Agents receive focused context via file references and produce artifacts directly.

---

## migration-scanner

**Purpose:** Fast parallel filesystem scanning during /migrate-init
**Spawned by:** migrate-init (×4 parallel instances)
**Model tier:** fast/cheap (mechanical file traversal, no reasoning needed)

**Variants:**
| Instance | Scope | Output Section |
|----------|-------|---------------|
| scanner-headers | .h / .hpp files | inventory.md § Headers |
| scanner-sources | .cpp / .cc files | inventory.md § Sources |
| scanner-build | CMakeLists.txt, Makefile, *.vcxproj | inventory.md § Build Targets |
| scanner-tests | test/ dirs, *_test.cpp, *_test.h | inventory.md § Tests |

**Context given:**
- Directory path to scan
- File extension filter
- Output file path + section marker

**Produces:**
- Markdown table rows appended to inventory.md

**Constraints:**
- Read-only on source files
- Write only to .migration/ directory
- No analysis, just classification and counting

---

## migration-detector

**Purpose:** Technology and pattern detection
**Spawned by:** migrate-init, migrate-detect
**Model tier:** standard (needs pattern recognition)

**Context given:**
- Build system files (CMakeLists.txt, conanfile, vcpkg.json)
- Sample #include directives (top 200 by frequency)
- Preprocessor platform checks found

**Produces:**
- .migration/research/legacy-stack.md
- .migration/research/dependency-map.md
- .migration/research/risk-matrix.md

**Constraints:**
- Must classify every detected dependency
- Must provide a Java equivalent (or "no equivalent")
- Must score risk for each

---

## migration-analyzer (×4 parallel)

**Purpose:** Deep analysis of C++ module from specific angle
**Spawned by:** migrate-analyze
**Model tier:** most-capable (needs deep code understanding)

**Variants:**
| Instance | Focus | Output Section |
|----------|-------|---------------|
| analyzer-dataflow | Ownership, lifetimes, data movement | ANALYSIS.md § Data Flow |
| analyzer-patterns | Design patterns, C++ idioms | ANALYSIS.md § Patterns |
| analyzer-deps | Call graph, interface surface, circular deps | ANALYSIS.md § Dependencies |
| analyzer-risks | Unsafe ops, platform code, UB, concurrency | ANALYSIS.md § Risks |

**Context given:**
- All source files in the phase
- Headers included by those files
- legacy-stack.md (for technology context)

**Produces:**
- One section of nn-analysis.md (writes directly)

**Constraints:**
- Must read every file assigned before writing
- Must provide concrete file:line references
- Must score complexity per finding

---

## migration-translator

**Purpose:** Translate one C++ translation unit to Java
**Spawned by:** migrate-execute (parallel per wave)
**Model tier:** most-capable (complex semantic translation)

**Context given (via file references, never pasted):**
- The specific nn-pp-plan.md
- C++ source files listed in plan
- C++ header files listed in plan
- .kiro/steering/java-target-standards.md (reference)
- .migration/mapping.md (package naming)
- .migration/decisions.md (architectural constraints)

**Produces:**
- Java source file(s) in correct hexagonal package
- Test file(s) in src/test/java mirror
- nn-pp-summary.md with execution record
- Atomic git commit

**Iron Laws:**
1. Read ALL C++ source before writing ANY Java
2. Follow the plan's translation table — no improvisation
3. Domain classes: ZERO Spring imports
4. Every public method: at minimum ONE test
5. Uncertain translations marked: `// MIGRATION-REVIEW: <reason>`
6. Commit format: `migrate(phase-N/plan-PP): CppClass → JavaClass`

**Output Type Awareness (read from config.json output_type):**
| output_type | Translation Rules |
|-------------|------------------|
| service | Default Spring Boot behavior — @RestController, @Service, application.yml, full starter stack |
| library | NO Spring Boot annotations in production code, NO @RestController, NO application.yml references. Use `java-library` plugin conventions. Driving ports (port/in/) ARE the public API. Driven ports (port/out/) are SPIs for consumers. Provide default in-memory adapters where appropriate. Use module-info.java for API boundary enforcement. |
| sdk | Same as library PLUS comprehensive Javadoc (/// markdown doc comments) on ALL public API classes, interfaces, methods, and records. Add @Stable/@Beta/@Internal annotations. Include usage examples in doc comments. |
| cli | Use picocli @Command annotations. Adapter layer is adapter/in/cli/ (NOT web/). Output is stdout/stderr + exit codes. No @RestController, no HTTP endpoints. Main class is picocli CommandLine runner. |

**Constraints:**
- Fresh 200K context per instance
- No shared state between translator instances
- Must self-verify (compile + run own tests) before committing

---

## migration-verifier

**Purpose:** Semantic equivalence verification between C++ and Java
**Spawned by:** migrate-verify
**Model tier:** most-capable (deep reasoning about behavioral equivalence)

**Context given:**
- C++ source files (original)
- Java source files (translated)
- nn-pp-plan.md (intended mapping)
- nn-analysis.md (original analysis)

**Produces:**
- Section of nn-verification.md

**Approach:**
1. List every public method in C++
2. Find corresponding Java method
3. Compare: parameters, return type, side effects, error paths
4. Trace critical execution paths through both
5. Flag ANY behavioral difference

**Output Type Verification (read from config.json output_type):**
| output_type | Additional Checks |
|-------------|-------------------|
| service | Verify Spring Boot conventions applied correctly — controllers, starters, application.yml |
| library | Verify NO Spring Boot annotations in production code, NO @RestController, NO application.yml. Verify public API is exposed via driving ports (port/in/) only. Verify module-info.java exports are correct. |
| sdk | Same as library PLUS verify all public API has comprehensive Javadoc (/// markdown doc comments). Verify @Stable/@Beta/@Internal annotations present on public surface. |
| cli | Verify picocli @Command used correctly. Verify adapter/in/cli/ structure (NOT web/). Verify exit codes and stdout/stderr output match C++ original behavior. |

**Verdict scale:**
- ✅ EQUIVALENT — same behavior confirmed
- ⚠️ MINOR_DIFF — acceptable difference (document reason)
- ❌ SEMANTIC_DRIFT — behavior changed, must fix or justify

---

## migration-fixer

**Purpose:** Fix build or test failures after translation
**Spawned by:** migrate-execute (on gate failure)
**Model tier:** standard (targeted fix, not redesign)

**Context given:**
- Compiler error output or test failure output
- The specific Java file(s) that failed
- The nn-pp-plan.md that produced them
- C++ source (for reference on intended behavior)

**Produces:**
- Fixed Java source file(s)
- Amended commit or new fix commit

**Constraints:**
- Fix the SPECIFIC error — do not redesign
- Do not change public API
- Do not remove or weaken tests
- Do not introduce new dependencies without justification
- Max 2 fix attempts per failure; if still broken, mark as BLOCKED

---

## migration-reviewer (×2 passes)

**Purpose:** Two-pass code review
**Spawned by:** migrate-review
**Model tier:** most-capable (judgment and pattern recognition)

**Pass 1 — Semantic Fidelity:**
- Context: C++ source, Java target, decisions.md, git diff
- Focus: "Does Java do EXACTLY what C++ did?"
- Verdict: FAITHFUL | DRIFT_MINOR | DRIFT_MAJOR

**Pass 2 — Ponytail Minimalism:**
- Context: Java source, build.gradle.kts, Spring config, migration ladder
- Focus: "Could this be simpler? Does Spring already do this?"
- Verdict: APPROVED | OVER_ENGINEERED | UNNECESSARY | SIMPLIFIABLE
