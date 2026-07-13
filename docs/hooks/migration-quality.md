# Hooks

> **Note:** `{target_root}` refers to the target project directory (default: `./app/`),
> configurable via `target_root` in `.migration/config.json`.

Portable quality checks that may run on file events during migration. Adapter capability
manifests decide whether each check is native, approximate, or an explicit review instruction.
Unsupported judgment hooks are never represented as command enforcement.

---

## compile-on-save

- trigger: file-save
- matcher: {target_root}/{{target_source_dir}}/.*
- type: command
- command: cd {target_root} && {{compile_command}} -q
- required: true
- enforcement: deterministic
- timeout: 30
- description: Runs incremental compilation on every save to catch errors immediately

{{#if output_profile == 'service'}}
## service-domain-purity-review

- trigger: file-create
- matcher: {target_root}/{{target_source_dir}}/.*/domain/.*
- type: agent
- prompt: Check the newly created file for imports of framework packages. The domain layer must be pure {{target_language}} with ZERO framework imports. If any framework imports are found, either: (1) remove the import and replace with a pure {{target_language}} alternative, or (2) move the class to the appropriate outer layer (application/ or adapter/) where framework dependencies are allowed. Report which violation was found and what action to take.
{{#if target_language_id == 'java-25'}}
- framework_imports: org.springframework.*, jakarta.persistence.*, jakarta.inject.*
{{/if}}
- required: false
- enforcement: judgment
- description: Reviews service domain policy for framework and infrastructure leakage

## architecture-direction-check

- trigger: file-save
- matcher: {target_root}/{{target_source_dir}}/.*/adapter/in/.*
- type: agent
- prompt: Check the saved adapter/in/ file for hexagonal architecture violations. Adapter/in/ classes must only invoke use case port interfaces (domain.port.in.*), never implementations directly. Check for forbidden imports that bypass the port interfaces and depend directly on domain internals or adapter/out/ implementations.
{{#if target_language_id == 'java-25'}}
- allowed_imports: domain.port.in.*, application.dto.*, application.mapper.*, java.*, jakarta.validation.*, org.springframework.web.*, org.springframework.http.*
- forbidden_imports: domain.service.*, domain.port.out.*, application.usecase.*
{{/if}}
- required: false
- enforcement: judgment
- description: Verifies adapter/in/ classes only depend on allowed packages
{{/if}}

## behavior-traceability-review

- trigger: file-create
- matcher: {target_root}/{{target_source_dir}}/.*
- type: agent
- prompt: A new {{target_language}} source unit was created. Review whether its observable behavior is linked in traceability.json to a characterized BEH identifier and to appropriate target tests or an approved exception. Do not require one test file per production file; judge the evidence at the behavioral contract and selected output-profile boundary.
- required: false
- enforcement: judgment
- description: Reviews behavioral-contract and test traceability without imposing file-count rules

## migration-state-structural-validation

- trigger: file-save
- matcher: \.migration/(config|scope|state|inventory|target-inventory|traceability|completion-certificate)\.json|\.migration/(behaviors|decisions|plans|evidence|exceptions)/.*\.json
- type: command
- command: python3 .migration-framework/bin/migrationctl.py validate .migration
- required: true
- enforcement: deterministic
- timeout: 30
- description: Validates the current migration artifact structure and references after authoritative state saves; a pass is not a full-scope completion certificate

## completion-claim-review

- trigger: stop
- matcher: .*
- type: agent
- prompt: Before ending, inspect the response for claims such as complete, done, fully migrated, 100%, foundation complete, ready for final cutover, or decommissioned. Require the narrowest truthful milestone and exact declared/accounted/migrated denominators. Structural validation, installation, initialization, a target foundation, a passing build, or one approved slice is not whole-scope completion. Accounted and migrated are separate; retained and approved-removed items never increase the migrated numerator. Strict 100% migrated requires pending, unknown, retained, removed, and unverified counts all equal zero. A final-cutover claim requires a current passing implementation-stage completion certificate, and terminal decommission requires a current passing decommission-stage certificate. If evidence is absent or stale, replace the unsupported claim with the remaining IDs and the next safe workflow.
- required: false
- enforcement: judgment
- description: Prevents unsupported whole-project completion claims at the end of an agent turn
