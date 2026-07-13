# Java 25 Architecture Check Templates

Architecture checks are generated from the composed target/output profile. These snippets
illustrate enforceable rules; replace the example base package with the project decision and
include the selected rules in the normal test task. A copied test that is never executed is
not enforcement.

Pin the selected ArchUnit version through the project catalog/decision. Store the test report
as verification evidence.

## Service: Modular Hexagonal Dependencies

```java
package com.example.migrated.architecture;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;

import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

@AnalyzeClasses(packages = "com.example.migrated")
final class ModularHexagonalArchitectureTest {

    @ArchTest
    static final ArchRule domain_has_no_framework_or_outer_dependencies =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "org.springframework..",
                "jakarta.persistence..",
                "..application..",
                "..adapter..",
                "..config..");

    @ArchTest
    static final ArchRule application_does_not_depend_on_adapters =
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().resideInAPackage("..adapter..");

    @ArchTest
    static final ArchRule inbound_adapters_do_not_call_outbound_adapters =
        noClasses().that().resideInAPackage("..adapter.in..")
            .should().dependOnClassesThat().resideInAPackage("..adapter.out..");

    @ArchTest
    static final ArchRule business_modules_are_acyclic =
        slices().matching("com.example.migrated.(*)..")
            .should().beFreeOfCycles();
}
```

The cycle rule does not stop one module from importing another module's internal package.
Generate module-specific allow-list rules from the selected module manifest, or run Spring
Modulith's module verification when selected. Test-framework/configuration packages may need
explicit exclusions, but every exclusion is narrow and documented.

## Library and SDK: API / Internal / SPI

```java
package com.example.library.architecture;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

@AnalyzeClasses(packages = "com.example.library")
final class LibraryBoundaryTest {

    @ArchTest
    static final ArchRule api_does_not_depend_on_internal =
        noClasses().that().resideInAPackage("..api..")
            .should().dependOnClassesThat().resideInAPackage("..internal..");

    @ArchTest
    static final ArchRule spi_does_not_depend_on_internal =
        noClasses().that().resideInAPackage("..spi..")
            .should().dependOnClassesThat().resideInAPackage("..internal..");

    @ArchTest
    static final ArchRule public_contract_does_not_depend_on_framework_integration =
        noClasses().that().resideInAnyPackage("..api..", "..spi..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "org.springframework..",
                "..integration..");
}
```

ArchUnit sees bytecode dependencies but does not decide the published API by itself. Also
validate `module-info.java`/`jar --describe-module`, exported packages, public signatures,
generated POM/module metadata, and a source/binary API diff. A public implementation in an
unexported internal package may be legitimate (for example a service provider), so do not
apply a blanket “all public classes live in api” rule.

SDK validation adds stability-classification and documentation checks for exported symbols;
those are API metadata validators, not architecture-import rules.

## CLI: Command Boundary

```java
package com.example.tool.architecture;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

@AnalyzeClasses(packages = "com.example.tool")
final class CliArchitectureTest {

    @ArchTest
    static final ArchRule only_the_launcher_exits_the_process =
        classes().that().doNotHaveFullyQualifiedName("com.example.tool.CliLauncher")
            .should().notCallMethod(System.class, "exit", int.class);

    @ArchTest
    static final ArchRule core_does_not_depend_on_parser =
        noClasses().that().resideInAPackage("..core..")
            .should().dependOnClassesThat().resideInAPackage("picocli..");

    @ArchTest
    static final ArchRule core_does_not_depend_on_commands =
        noClasses().that().resideInAPackage("..core..")
            .should().dependOnClassesThat().resideInAPackage("..command..");
}
```

Generate the exact launcher class predicate from configuration. Use runtime
command tests—not ArchUnit—to enforce stdout/stderr, exit-code, TTY/color, signal, and
installed-package contracts.

## Validation Rules

- Compile every generated architecture test as part of repository conformance fixtures.
- Fail when a required package/module from the composed profile is absent, unless the profile
  marks it conditional and the project did not select that capability.
- Fail on zero imported production classes; an empty architecture test must not pass vacuously.
- Keep exclusions in project decisions with owner and removal criterion.
- Record the exact rule set, imported artifact checksum, command, result, and report as evidence.
- Do not label review-only guidance as an ArchUnit-enforced rule.

## Rule Provenance

Shared metadata: `applicability` is Java 25 compositions selecting the corresponding
architecture rule; `source` is the composed output/target architecture contract and selected
ArchUnit documentation; `owner` is target profile `java-25`.

| Rule ID | Rationale | Enforcement | Evidence | Reviewed for |
|---|---|---|---|---|
| `TGT-JAVA25-ARCH-001` | A rule that imports no production classes passes without protecting a boundary. | Architecture harness validator | Import count and ArchUnit report | Java 25 profile v2 |
| `TGT-JAVA25-ARCH-002` | Library exports require module/API inspection beyond bytecode dependency direction. | Publication validator | Module/export/API report | JDK 25 |
| `TGT-JAVA25-ARCH-003` | CLI stream/exit semantics are runtime contracts, not static dependencies. | CLI command harness | Process stdout/stderr/status results | JDK 25 |
