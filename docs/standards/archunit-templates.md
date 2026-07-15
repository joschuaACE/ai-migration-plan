# ArchUnit Test Templates

These are the actual test files generated during `/migrate-init`. Copy the appropriate template based on output_type.

The package `com.company.app` is a placeholder — replace with the actual group/artifact during skeleton generation.

---

## Service: HexagonalArchitectureTest.java

Use for `output_type = "service"`. Enforces full hexagonal boundaries with Spring Boot conventions.

```java
package com.company.app;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noFields;

@AnalyzeClasses(packages = "com.company.app", importOptions = ImportOption.DoNotIncludeTests.class)
class HexagonalArchitectureTest {

    // === Rule 1: Domain has no Spring imports ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_spring =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("org.springframework..");

    // === Rule 2: Domain has no JPA imports ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_jpa =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("jakarta.persistence..");

    // === Rule 3: Domain ports are only interfaces ===
    @ArchTest
    static final ArchRule domain_ports_must_be_interfaces =
            classes()
                    .that().resideInAPackage("..domain.port..")
                    .should().beInterfaces();

    // === Rule 4: Dependencies point inward — domain depends on nothing outside ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_application =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..application..");

    @ArchTest
    static final ArchRule domain_must_not_depend_on_adapter =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..adapter..");

    @ArchTest
    static final ArchRule application_must_not_depend_on_adapter =
            noClasses()
                    .that().resideInAPackage("..application..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..adapter..");

    // === Rule 5: Adapter/in/ only depends on port.in, dto, and mapper ===
    @ArchTest
    static final ArchRule adapter_in_only_depends_on_allowed_packages =
            noClasses()
                    .that().resideInAPackage("..adapter.in..")
                    .should().dependOnClassesThat()
                    .resideInAnyPackage(
                            "..domain.service..",
                            "..domain.port.out..",
                            "..adapter.out.."
                    );

    // === Rule 6: Adapter/in/ never accesses driven ports or domain services ===
    @ArchTest
    static final ArchRule adapter_in_must_not_access_driven_ports =
            noClasses()
                    .that().resideInAPackage("..adapter.in..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..domain.port.out..");

    @ArchTest
    static final ArchRule adapter_in_must_not_access_domain_services =
            noClasses()
                    .that().resideInAPackage("..adapter.in..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..domain.service..");

    // === Rule 7: No field injection ===
    @ArchTest
    static final ArchRule no_field_injection =
            noFields()
                    .should().beAnnotatedWith("org.springframework.beans.factory.annotation.Autowired");

    // === Rule 8: Use case implementations are in application.usecase ===
    @ArchTest
    static final ArchRule use_case_implementations_in_correct_package =
            classes()
                    .that().implement(clazz ->
                            clazz.getPackageName().contains(".domain.port.in"))
                    .should().resideInAPackage("..application.usecase..");
}
```

---

## Library: HexagonalArchitectureTest.java

Use for `output_type = "library"`. Enforces hexagonal boundaries without Spring Boot assumptions.
For simple layered libraries (api/internal/spi), verifies that `internal/` is encapsulated.

```java
package com.company.app;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

@AnalyzeClasses(packages = "com.company.app", importOptions = ImportOption.DoNotIncludeTests.class)
class HexagonalArchitectureTest {

    // === Rule 1: Domain has no Spring imports ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_spring =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("org.springframework..");

    // === Rule 2: Domain has no JPA imports ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_jpa =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("jakarta.persistence..");

    // === Rule 3: Dependencies point inward ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_application =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..application..");

    @ArchTest
    static final ArchRule domain_must_not_depend_on_adapter =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..adapter..");

    @ArchTest
    static final ArchRule application_must_not_depend_on_adapter =
            noClasses()
                    .that().resideInAPackage("..application..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..adapter..");

    // === Rule 4: Public API has no framework annotations ===
    @ArchTest
    static final ArchRule api_must_not_depend_on_spring =
            noClasses()
                    .that().resideInAnyPackage("..api..", "..domain.port.in..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("org.springframework..");

    @ArchTest
    static final ArchRule api_must_not_depend_on_jakarta =
            noClasses()
                    .that().resideInAnyPackage("..api..", "..domain.port.in..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("jakarta..");

    // === Rule 5: Internal packages are not referenced by api/ ===
    @ArchTest
    static final ArchRule api_must_not_depend_on_internal =
            noClasses()
                    .that().resideInAPackage("..api..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..internal..");

    // === Rule 6: No Spring Boot starter classes exist ===
    @ArchTest
    static final ArchRule no_spring_boot_application =
            noClasses()
                    .should().beAnnotatedWith("org.springframework.boot.autoconfigure.SpringBootApplication");

    // === Rule 7: No REST controllers exist ===
    @ArchTest
    static final ArchRule no_rest_controllers =
            noClasses()
                    .should().beAnnotatedWith("org.springframework.web.bind.annotation.RestController");

    @ArchTest
    static final ArchRule no_request_mappings =
            noClasses()
                    .should().beAnnotatedWith("org.springframework.web.bind.annotation.RequestMapping");
}
```

---

## CLI: HexagonalArchitectureTest.java

Use for `output_type = "cli"`. Enforces hexagonal boundaries with picocli-specific rules.
No Spring web stack, no REST controllers, CLI commands only invoke use case ports.

```java
package com.company.app;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

@AnalyzeClasses(packages = "com.company.app", importOptions = ImportOption.DoNotIncludeTests.class)
class HexagonalArchitectureTest {

    // === Rule 1: Domain has no Spring imports ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_spring =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("org.springframework..");

    // === Rule 2: Domain has no picocli imports ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_picocli =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("picocli..");

    // === Rule 3: Dependencies point inward ===
    @ArchTest
    static final ArchRule domain_must_not_depend_on_application =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..application..");

    @ArchTest
    static final ArchRule domain_must_not_depend_on_adapter =
            noClasses()
                    .that().resideInAPackage("..domain..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..adapter..");

    @ArchTest
    static final ArchRule application_must_not_depend_on_adapter =
            noClasses()
                    .that().resideInAPackage("..application..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..adapter..");

    // === Rule 4: CLI adapter depends only on port.in and application.dto ===
    @ArchTest
    static final ArchRule cli_adapter_must_not_access_domain_services =
            noClasses()
                    .that().resideInAPackage("..adapter.in.cli..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..domain.service..");

    @ArchTest
    static final ArchRule cli_adapter_must_not_access_driven_ports =
            noClasses()
                    .that().resideInAPackage("..adapter.in.cli..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..domain.port.out..");

    @ArchTest
    static final ArchRule cli_adapter_must_not_access_outbound_adapters =
            noClasses()
                    .that().resideInAPackage("..adapter.in.cli..")
                    .should().dependOnClassesThat()
                    .resideInAPackage("..adapter.out..");

    // === Rule 5: No REST controllers exist ===
    @ArchTest
    static final ArchRule no_rest_controllers =
            noClasses()
                    .should().beAnnotatedWith("org.springframework.web.bind.annotation.RestController");

    @ArchTest
    static final ArchRule no_request_mappings =
            noClasses()
                    .should().beAnnotatedWith("org.springframework.web.bind.annotation.RequestMapping");

    // === Rule 6: No Spring Boot web configuration ===
    @ArchTest
    static final ArchRule no_spring_boot_application =
            noClasses()
                    .should().beAnnotatedWith("org.springframework.boot.autoconfigure.SpringBootApplication");
}
```
