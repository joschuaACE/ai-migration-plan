# Hooks

> **Note:** `{target_root}` refers to the Java project directory (default: `./app/`),
> configurable via `target_root` in `.migration/config.json`.

Automated quality checks that run on file events during migration.
All three supported agents have native hook systems. Each installer
reads this file and generates the agent-native format dynamically.

---

## compile-on-save

- trigger: file-save
- matcher: {target_root}/.*\.java$
- type: command
- command: cd {target_root} && ./gradlew compileJava -q
- timeout: 30
- description: Runs incremental Java compilation on every save to catch compile errors immediately

## domain-purity-check

- trigger: file-create
- matcher: {target_root}/src/main/java/.*/domain/.*\.java$
- type: agent
- prompt: Check the newly created file for imports of org.springframework.* or jakarta.persistence.*. The domain layer must be pure Java with ZERO framework imports. If any such imports are found, either: (1) remove the import and replace with a pure Java alternative, or (2) move the class to the appropriate outer layer (application/ or adapter/) where framework dependencies are allowed. Report which violation was found and what action to take.
- description: Ensures domain layer classes have zero framework imports

## architecture-direction-check

- trigger: file-save
- matcher: {target_root}/src/main/java/.*/adapter/in/.*\.java$
- type: agent
- prompt: Check the saved adapter/in/ file for hexagonal architecture violations. Allowed imports: domain.port.in.* (use case interfaces), application.dto.*, application.mapper.*, java.*, jakarta.validation.*, org.springframework.web.*, org.springframework.http.*. FORBIDDEN: domain.service.*, domain.port.out.*, application.usecase.*. If any forbidden import is found, flag it and explain that adapter/in/ must only invoke use case port interfaces, never implementations.
- description: Verifies adapter/in/ classes only depend on allowed packages

## test-companion-reminder

- trigger: file-create
- matcher: {target_root}/src/main/java/.*\.java$
- type: agent
- prompt: A new Java source file was created in src/main/java. Check if a corresponding test file exists in the matching src/test/java path (same package, class name with 'Test' suffix). If no test companion exists yet, remind the developer to create one.
- description: Reminds to create a corresponding test file when a new production Java class is created
