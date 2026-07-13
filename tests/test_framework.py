"""High-value conformance tests for the compiler, lifecycle, and installer."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_PATH = REPOSITORY_ROOT / "agents" / "framework.py"
GOLDEN_MIGRATION = (
    REPOSITORY_ROOT
    / "fixtures"
    / "golden-multimodule"
    / "expected"
    / ".migration"
)

MODULE_NAME = "migration_framework_v3_under_test"
if MODULE_NAME in sys.modules:
    FRAMEWORK = sys.modules[MODULE_NAME]
else:
    SPEC = importlib.util.spec_from_file_location(MODULE_NAME, FRAMEWORK_PATH)
    assert SPEC is not None and SPEC.loader is not None
    FRAMEWORK = importlib.util.module_from_spec(SPEC)
    sys.modules[SPEC.name] = FRAMEWORK
    SPEC.loader.exec_module(FRAMEWORK)


def directory_bytes(root: Path) -> dict[str, bytes]:
    """Return a path-independent byte snapshot of every regular file under root."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def rewrite_bundle_manifest(bundle: Path, manifest: dict[str, object]) -> None:
    """Recompute the aggregate digest and persist a deliberately changed test manifest."""
    digest_input = {
        key: value for key, value in manifest.items() if key != "bundle_digest"
    }
    manifest["bundle_digest"] = FRAMEWORK.sha256_bytes(
        FRAMEWORK.canonical_json(digest_input).encode("utf-8")
    )
    (bundle / "manifest.json").write_text(
        FRAMEWORK.pretty_json(manifest), encoding="utf-8", newline="\n"
    )


class TemporaryDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="framework-v3-test-")
        self.addCleanup(self.temporary.cleanup)
        self.temp_path = Path(self.temporary.name)

        # framework.py invokes the hook compiler in subprocesses during installs.
        # Keep those subprocesses from writing bytecode into the checkout.
        environment = mock.patch.dict(
            os.environ, {"PYTHONDONTWRITEBYTECODE": "1"}
        )
        environment.start()
        self.addCleanup(environment.stop)

    def run_framework(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(FRAMEWORK_PATH), *arguments],
            cwd=REPOSITORY_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )


class CompilationConformanceTests(TemporaryDirectoryTestCase):
    def test_all_four_profile_compositions_compile_without_unresolved_tokens(self) -> None:
        for output_profile in ("service", "library", "sdk", "cli"):
            with self.subTest(output_profile=output_profile):
                composition = FRAMEWORK.compose_profiles(
                    "cpp-to-java-25", output_profile
                )
                bundle = self.temp_path / f"bundle-{output_profile}"
                manifest = FRAMEWORK.compile_bundle(composition, bundle)

                self.assertEqual(FRAMEWORK.verify_bundle(bundle), manifest)
                self.assertEqual(manifest["profiles"]["output"], output_profile)
                self.assertEqual(
                    manifest["variables"]["output_profile"], output_profile
                )

                selected = FRAMEWORK.selected_documents(composition)
                for destination, source in selected:
                    self.assertIn(destination, manifest["generated_files"])
                    self.assertIn(source, manifest["source_checksums"])

                for path in sorted(bundle.rglob("*")):
                    if path.suffix not in {".md", ".json"}:
                        continue
                    content = path.read_text(encoding="utf-8")
                    match = FRAMEWORK.TOKEN_RE.search(content)
                    self.assertIsNone(
                        match,
                        f"unresolved token in {path.relative_to(bundle)}: "
                        f"{match.group(0) if match else ''}",
                    )

    def test_repeated_compilation_is_byte_identical(self) -> None:
        composition = FRAMEWORK.compose_profiles("cpp-to-java-25", "service")
        first = self.temp_path / "first"
        second = self.temp_path / "second"

        FRAMEWORK.compile_bundle(composition, first, adapter="codex")
        FRAMEWORK.compile_bundle(composition, second, adapter="codex")

        self.assertEqual(directory_bytes(first), directory_bytes(second))

    def test_legacy_engine_cli_composes_v2_fields_from_valid_v1_pair_data(self) -> None:
        output = self.temp_path / "legacy-verify.md"
        environment = os.environ.copy()
        environment.update(
            {
                "TOOLKIT_DIR": str(REPOSITORY_ROOT),
                "PAIR_ID": "cpp-to-java-25",
                "MIGRATION_OUTPUT_PROFILE": "library",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        process = subprocess.run(
            [
                sys.executable,
                str(REPOSITORY_ROOT / "agents" / "compile-engine.py"),
                str(REPOSITORY_ROOT / "docs" / "skills" / "migrate-verify.md"),
                str(output),
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIsNone(FRAMEWORK.TOKEN_RE.search(output.read_text(encoding="utf-8")))

    def test_bundle_verification_detects_generated_file_and_manifest_tampering(self) -> None:
        composition = FRAMEWORK.compose_profiles("cpp-to-java-25", "service")
        bundle = self.temp_path / "bundle"
        manifest = FRAMEWORK.compile_bundle(composition, bundle)

        generated_path = next(iter(manifest["generated_files"]))
        with (bundle / generated_path).open("ab") as handle:
            handle.write(b"\ntampered\n")
        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError, "bundle file checksum mismatch"
        ):
            FRAMEWORK.verify_bundle(bundle)

        FRAMEWORK.compile_bundle(composition, bundle)
        manifest_path = bundle / "manifest.json"
        tampered_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        first_source = next(iter(tampered_manifest["source_checksums"]))
        tampered_manifest["source_checksums"][first_source] = "0" * 64
        manifest_path.write_text(
            FRAMEWORK.pretty_json(tampered_manifest),
            encoding="utf-8",
            newline="\n",
        )
        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError, "bundle manifest digest mismatch"
        ):
            FRAMEWORK.verify_bundle(bundle)

    def test_bundle_verification_uses_trusted_versioned_manifest_schemas(self) -> None:
        composition = FRAMEWORK.compose_profiles("cpp-to-java-25", "service")
        bundle = self.temp_path / "trusted-schema-bundle"
        manifest = FRAMEWORK.compile_bundle(composition, bundle)

        bundled_schema_path = bundle / "schemas" / "bundle-manifest.schema.json"
        bundled_schema = FRAMEWORK.read_json(bundled_schema_path)
        bundled_schema["properties"]["bundle_only_field"] = {"type": "string"}
        bundled_schema["required"].append("bundle_only_field")
        bundled_schema_path.write_text(
            FRAMEWORK.pretty_json(bundled_schema), encoding="utf-8", newline="\n"
        )
        manifest["generated_files"][
            "schemas/bundle-manifest.schema.json"
        ] = FRAMEWORK.sha256_file(bundled_schema_path)
        manifest["bundle_only_field"] = "accepted only by the bundle-supplied schema"
        rewrite_bundle_manifest(bundle, manifest)

        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError, "unexpected property 'bundle_only_field'"
        ):
            FRAMEWORK.verify_bundle(bundle)

        manifest = FRAMEWORK.compile_bundle(composition, bundle)
        legacy_manifest = {
            key: value
            for key, value in manifest.items()
            if key not in {"project_overrides", "inferred_overrides"}
        }
        legacy_manifest["schema_version"] = "2.0"
        legacy_manifest["bundle_format_version"] = "2.0"
        rewrite_bundle_manifest(bundle, legacy_manifest)
        self.assertEqual(FRAMEWORK.verify_bundle(bundle)["schema_version"], "2.0")

        legacy_manifest["schema_version"] = "99.0"
        legacy_manifest["bundle_format_version"] = "99.0"
        rewrite_bundle_manifest(bundle, legacy_manifest)
        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError, "unsupported bundle schema version '99.0'"
        ):
            FRAMEWORK.verify_bundle(bundle)

    def test_bundle_verification_requires_an_exact_safe_regular_file_inventory(self) -> None:
        composition = FRAMEWORK.compose_profiles("cpp-to-java-25", "service")

        bundle = self.temp_path / "unlisted-file-bundle"
        FRAMEWORK.compile_bundle(composition, bundle)
        unlisted = bundle / "workflows" / "unlisted.md"
        unlisted.write_text("unlisted workflow\n", encoding="utf-8")
        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError, "inventory mismatch.*unlisted"
        ):
            FRAMEWORK.verify_bundle(bundle)

        bundle = self.temp_path / "missing-file-bundle"
        manifest = FRAMEWORK.compile_bundle(composition, bundle)
        missing = next(iter(manifest["generated_files"]))
        (bundle / missing).unlink()
        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError, "inventory mismatch.*missing"
        ):
            FRAMEWORK.verify_bundle(bundle)

        bundle = self.temp_path / "symlink-bundle"
        FRAMEWORK.compile_bundle(composition, bundle)
        (bundle / "workflows" / "linked.md").symlink_to(bundle / "manifest.json")
        with self.assertRaisesRegex(FRAMEWORK.FrameworkError, "unsafe symlink"):
            FRAMEWORK.verify_bundle(bundle)

        bundle = self.temp_path / "non-regular-bundle"
        FRAMEWORK.compile_bundle(composition, bundle)
        os.mkfifo(bundle / "workflows" / "named-pipe")
        with self.assertRaisesRegex(FRAMEWORK.FrameworkError, "non-regular entry"):
            FRAMEWORK.verify_bundle(bundle)

    def test_v3_manifest_variables_must_match_the_declared_composition(self) -> None:
        composition = FRAMEWORK.compose_profiles("cpp-to-java-25", "service")
        bundle = self.temp_path / "inconsistent-variables-bundle"
        manifest = FRAMEWORK.compile_bundle(composition, bundle, adapter="codex")
        manifest["variables"]["compile_command"] = "./gradlew alternateCompile"
        rewrite_bundle_manifest(bundle, manifest)
        target = self.temp_path / "inconsistent-variables-target"
        target.mkdir()

        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError,
            "variables do not exactly match.*profiles and project_overrides",
        ):
            FRAMEWORK.install_compiled_bundle(
                mode="install",
                adapter="codex",
                target=target,
                bundle=bundle,
                dry_run=True,
                force=False,
                strict_hooks=False,
            )

    def test_invalid_schema_and_missing_composition_contracts_are_actionable(self) -> None:
        invalid = self.temp_path / "invalid-config.json"
        invalid.write_text(
            FRAMEWORK.pretty_json(
                {
                    "$schema": "schemas/migration-config.schema.json",
                    "schema_version": "1.0",
                }
            ),
            encoding="utf-8",
            newline="\n",
        )
        diagnostics = "\n".join(FRAMEWORK.validate_artifact(invalid))
        self.assertIn("expected constant '2.0'", diagnostics)
        self.assertIn("missing required property 'profiles'", diagnostics)
        self.assertIn("missing required property 'migration_strategy'", diagnostics)

        composition = FRAMEWORK.compose_profiles("cpp-to-java-25", "service")
        variables = dict(composition.variables)
        variables.pop("compile_command")
        missing_variable = replace(composition, variables=variables)
        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError,
            r"profile composition is missing variables: compile_command",
        ):
            FRAMEWORK.validate_composition(missing_variable)

        target = dict(composition.target)
        target["capabilities"] = [
            capability
            for capability in target["capabilities"]
            if capability != "dependency-integrity"
        ]
        missing_capability = replace(composition, target=target)
        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError,
            r"requires missing target capabilities: dependency-integrity",
        ):
            FRAMEWORK.validate_composition(missing_capability)

    def test_duplicate_json_and_unsafe_project_command_overrides_are_rejected(self) -> None:
        duplicate = self.temp_path / "duplicate.json"
        duplicate.write_text('{"schema_version":"2.0","schema_version":"1.0"}\n', encoding="utf-8")
        with self.assertRaisesRegex(FRAMEWORK.FrameworkError, "duplicate object key"):
            FRAMEWORK.read_json(duplicate)
        with self.assertRaisesRegex(FRAMEWORK.FrameworkError, "shell control syntax"):
            FRAMEWORK.parse_overrides(["compile_command=./build; touch unexpected"])
        with self.assertRaisesRegex(FRAMEWORK.FrameworkError, "typed variable contract"):
            FRAMEWORK.parse_overrides(["undeclared_value=1"])


class LifecycleConformanceTests(TemporaryDirectoryTestCase):
    def test_blocked_state_must_resume_to_the_interrupted_state(self) -> None:
        state_path = self.temp_path / "state.json"
        shutil.copyfile(
            REPOSITORY_ROOT / "docs" / "state" / "templates" / "state.json",
            state_path,
        )

        discovered = FRAMEWORK.transition_state(
            state_path, "discover", "Discovery started"
        )
        self.assertEqual(discovered["status"], "discover")
        self.assertEqual(discovered["revision"], 1)

        blocked = FRAMEWORK.transition_state(
            state_path, "blocked", "Awaiting build metadata"
        )
        self.assertEqual(blocked["resume_to"], "discover")

        with self.assertRaisesRegex(
            FRAMEWORK.FrameworkError,
            r"state must resume to 'discover', not 'plan'",
        ):
            FRAMEWORK.transition_state(state_path, "plan", "Skip ahead")
        self.assertEqual(FRAMEWORK.read_json(state_path)["status"], "blocked")

        resumed = FRAMEWORK.transition_state(
            state_path, "discover", "Build metadata supplied"
        )
        self.assertEqual(resumed["status"], "discover")
        self.assertIsNone(resumed["resume_to"])
        self.assertEqual(resumed["blocked_by"], [])
        self.assertEqual(resumed["revision"], 3)

    def test_migration_validation_detects_broken_cross_references_and_history(self) -> None:
        migration = self.temp_path / ".migration"
        shutil.copytree(GOLDEN_MIGRATION, migration)
        self.assertEqual(FRAMEWORK.validate_migration_directory(migration), [])

        traceability_path = migration / "traceability.json"
        traceability = FRAMEWORK.read_json(traceability_path)
        traceability["links"][0]["decisions"] = ["DEC-DOES-NOT-EXIST"]
        traceability_path.write_text(
            FRAMEWORK.pretty_json(traceability),
            encoding="utf-8",
            newline="\n",
        )

        state_path = migration / "state.json"
        state = FRAMEWORK.read_json(state_path)
        state["history"][5]["from"] = "discover"
        state_path.write_text(
            FRAMEWORK.pretty_json(state),
            encoding="utf-8",
            newline="\n",
        )

        diagnostics = "\n".join(
            FRAMEWORK.validate_migration_directory(migration)
        )
        self.assertIn("unknown decision 'DEC-DOES-NOT-EXIST'", diagnostics)
        self.assertIn("transition chain is discontinuous", diagnostics)
        self.assertIn("invalid transition 'discover'", diagnostics)

    def test_cutover_can_roll_back_to_approval_before_terminal_decommission(self) -> None:
        state_path = self.temp_path / "cutover-state.json"
        shutil.copyfile(GOLDEN_MIGRATION / "state.json", state_path)
        cut_over = FRAMEWORK.transition_state(
            state_path, "cut_over", "Approved cohort cutover started"
        )
        self.assertEqual(cut_over["status"], "cut_over")
        rolled_back = FRAMEWORK.transition_state(
            state_path, "approve", "Abort threshold triggered; route restored"
        )
        self.assertEqual(rolled_back["status"], "approve")
        self.assertIsNone(rolled_back["active_slice"])

        cut_over_again = FRAMEWORK.transition_state(
            state_path, "cut_over", "Cutover retried after corrective verification"
        )
        self.assertEqual(cut_over_again["status"], "cut_over")
        terminal = FRAMEWORK.transition_state(
            state_path, "decommissioned", "Retention and final approvals satisfied"
        )
        self.assertEqual(terminal["status"], "decommissioned")
        with self.assertRaisesRegex(FRAMEWORK.FrameworkError, "allowed: none"):
            FRAMEWORK.transition_state(state_path, "approve", "Cannot leave terminal state")


class InstallerConformanceTests(TemporaryDirectoryTestCase):
    def install_target(
        self,
        name: str,
        *,
        adapter: str = "codex",
        output_profile: str = "service",
        overrides: tuple[str, ...] = (),
    ) -> Path:
        target = self.temp_path / name
        target.mkdir()
        arguments = [
            "install",
            "--adapter",
            adapter,
            "--target",
            str(target),
            "--output-profile",
            output_profile,
        ]
        for override in overrides:
            arguments.extend(("--set", override))
        result = self.run_framework(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        return target

    def rewrite_ownership(self, target: Path, ownership: dict[str, object]) -> None:
        ownership_path = target / FRAMEWORK.OWNERSHIP_FILE
        ownership_path.write_text(
            FRAMEWORK.pretty_json(ownership), encoding="utf-8", newline="\n"
        )
        (target / FRAMEWORK.OWNERSHIP_CHECKSUM_FILE).write_text(
            FRAMEWORK.sha256_file(ownership_path) + "\n",
            encoding="ascii",
            newline="\n",
        )

    def make_v2_installation(self, target: Path) -> None:
        """Rewrite current metadata into the exact v2 wire shape."""
        manifest_path = target / FRAMEWORK.OWNERSHIP_DIR / "bundle-manifest.json"
        current_manifest = FRAMEWORK.read_json(manifest_path)
        legacy_manifest = {
            "$schema": "schemas/bundle-manifest.schema.json",
            "schema_version": "2.0",
            "framework_version": "2.0.0",
            "bundle_format_version": "2.0",
            "profiles": current_manifest["profiles"],
            "adapter": current_manifest["adapter"],
            "adapter_capabilities": current_manifest["adapter_capabilities"],
            "variables": current_manifest["variables"],
            "source_checksums": current_manifest["source_checksums"],
            "generated_files": current_manifest["generated_files"],
        }
        legacy_manifest["bundle_digest"] = FRAMEWORK.sha256_bytes(
            FRAMEWORK.canonical_json(legacy_manifest).encode("utf-8")
        )
        manifest_path.write_text(
            FRAMEWORK.pretty_json(legacy_manifest), encoding="utf-8", newline="\n"
        )

        current_ownership = FRAMEWORK.read_json(target / FRAMEWORK.OWNERSHIP_FILE)
        legacy_ownership = {
            "$schema": "schemas/installation-ownership.schema.json",
            "schema_version": "2.0",
            "framework_version": "2.0.0",
            "adapter": current_ownership["adapter"],
            "profiles": current_ownership["profiles"],
            "bundle_digest": legacy_manifest["bundle_digest"],
            "files": dict(current_ownership["files"]),
        }
        legacy_ownership["files"][
            f"{FRAMEWORK.OWNERSHIP_DIR}/bundle-manifest.json"
        ] = FRAMEWORK.sha256_file(manifest_path)
        self.rewrite_ownership(target, legacy_ownership)

    def test_bare_upgrade_preserves_every_adapter_and_output_profile(self) -> None:
        workflow_locations = {
            "kiro": ".kiro/skills/migrate-framework-update/SKILL.md",
            "claude": "CLAUDE.md",
            "codex": "docs/skills/migrate-framework-update.md",
        }
        containment_locations = {
            "kiro": ".kiro/steering/generic-workspace-containment.md",
            "claude": "CLAUDE.md",
            "codex": "docs/standards/generic/workspace-containment.md",
        }
        for adapter in ("kiro", "claude", "codex"):
            for output_profile in ("service", "library", "sdk", "cli"):
                with self.subTest(adapter=adapter, output_profile=output_profile):
                    target = self.install_target(
                        f"matrix-{adapter}-{output_profile}",
                        adapter=adapter,
                        output_profile=output_profile,
                    )
                    preview = self.run_framework(
                        "upgrade", "--target", str(target), "--dry-run"
                    )
                    self.assertEqual(preview.returncode, 0, preview.stderr)
                    report = json.loads(preview.stdout)
                    self.assertEqual(
                        report["next_configuration"]["adapter"], adapter
                    )
                    self.assertEqual(
                        report["next_configuration"]["profiles"]["output"],
                        output_profile,
                    )
                    self.assertEqual(report["configuration_changes"], [])
                    workflow = target / workflow_locations[adapter]
                    self.assertTrue(workflow.is_file(), workflow)
                    self.assertIn(
                        "migrate-framework-update",
                        workflow.read_text(encoding="utf-8"),
                    )
                    containment = target / containment_locations[adapter]
                    self.assertTrue(containment.is_file(), containment)
                    self.assertIn(
                        "Workspace and Target Containment",
                        containment.read_text(encoding="utf-8"),
                    )

    def test_bare_upgrade_preserves_installed_profile_and_explicit_overrides(self) -> None:
        override = "compile_command=./gradlew legacyCompile"
        target = self.install_target(
            "smart-upgrade",
            output_profile="library",
            overrides=(override,),
        )

        result = self.run_framework("upgrade", "--target", str(target))

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        expected_overrides = {"compile_command": "./gradlew legacyCompile"}
        self.assertEqual(report["current_configuration"]["adapter"], "codex")
        self.assertEqual(
            report["current_configuration"]["profiles"]["output"], "library"
        )
        self.assertEqual(
            report["current_configuration"]["project_overrides"],
            expected_overrides,
        )
        self.assertEqual(report["next_configuration"]["adapter"], "codex")
        self.assertEqual(
            report["next_configuration"]["profiles"]["output"], "library"
        )
        self.assertEqual(
            report["next_configuration"]["project_overrides"], expected_overrides
        )
        self.assertEqual(report["configuration_changes"], [])
        self.assertEqual(report["inferred_overrides"], {})
        self.assertEqual(
            report["migration_state"],
            {
                "present": False,
                "valid": True,
                "compatible": True,
                "recorded_framework_version": None,
                "diagnostics": [],
            },
        )

        ownership = FRAMEWORK.load_ownership(target)
        assert ownership is not None
        self.assertEqual(ownership["schema_version"], "3.0")
        self.assertEqual(ownership["profiles"]["output"], "library")
        self.assertEqual(ownership["project_overrides"], expected_overrides)

        stable = self.run_framework("upgrade", "--target", str(target), "--dry-run")
        self.assertEqual(stable.returncode, 0, stable.stderr)
        stable_report = json.loads(stable.stdout)
        self.assertEqual(stable_report["writes"], [])
        self.assertEqual(stable_report["deletes"], [])
        self.assertEqual(stable_report["configuration_changes"], [])

        repeated_override = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--set",
            override,
            "--dry-run",
        )
        self.assertEqual(repeated_override.returncode, 0, repeated_override.stderr)
        self.assertEqual(
            json.loads(repeated_override.stdout)["configuration_changes"], []
        )

    def test_configuration_changes_require_reconfigure_and_are_reported(self) -> None:
        target = self.install_target("reconfigure-guard", output_profile="library")

        guarded = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--output-profile",
            "service",
            "--dry-run",
        )
        self.assertNotEqual(guarded.returncode, 0)
        self.assertIn("--reconfigure", guarded.stderr)

        allowed = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--output-profile",
            "service",
            "--reconfigure",
            "--dry-run",
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        report = json.loads(allowed.stdout)
        self.assertEqual(report["current_configuration"]["profiles"]["output"], "library")
        self.assertEqual(report["next_configuration"]["profiles"]["output"], "service")
        self.assertIn(
            {
                "field": "profiles",
                "current": report["current_configuration"]["profiles"],
                "next": report["next_configuration"]["profiles"],
            },
            report["configuration_changes"],
        )
        ownership = FRAMEWORK.load_ownership(target)
        assert ownership is not None
        self.assertEqual(ownership["profiles"]["output"], "library")

        repeated = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--adapter",
            "codex",
            "--pair",
            "cpp-to-java-25",
            "--output-profile",
            "library",
            "--dry-run",
        )
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(json.loads(repeated.stdout)["configuration_changes"], [])

    def test_adapter_change_requires_reconfigure(self) -> None:
        target = self.install_target("adapter-reconfigure", adapter="codex")

        guarded = self.run_framework(
            "upgrade", "--target", str(target), "--adapter", "kiro", "--dry-run"
        )
        self.assertNotEqual(guarded.returncode, 0)
        self.assertIn("--reconfigure", guarded.stderr)

        allowed = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--adapter",
            "kiro",
            "--reconfigure",
            "--dry-run",
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        report = json.loads(allowed.stdout)
        self.assertIn(
            {"field": "adapter", "current": "codex", "next": "kiro"},
            report["configuration_changes"],
        )

    def test_unset_requires_reconfigure_and_removes_one_persisted_override(self) -> None:
        target = self.install_target(
            "unset-override",
            output_profile="library",
            overrides=(
                "compile_command=./gradlew legacyCompile",
                "test_command=./gradlew legacyTest",
            ),
        )

        guarded = self.run_framework(
            "upgrade", "--target", str(target), "--unset", "compile_command"
        )
        self.assertNotEqual(guarded.returncode, 0)
        self.assertIn("--reconfigure", guarded.stderr)

        allowed = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--unset",
            "compile_command",
            "--reconfigure",
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        report = json.loads(allowed.stdout)
        self.assertEqual(
            report["next_configuration"]["project_overrides"],
            {"test_command": "./gradlew legacyTest"},
        )
        self.assertIn(
            {
                "field": "project_overrides",
                "current": {
                    "compile_command": "./gradlew legacyCompile",
                    "test_command": "./gradlew legacyTest",
                },
                "next": {"test_command": "./gradlew legacyTest"},
            },
            report["configuration_changes"],
        )
        ownership = FRAMEWORK.load_ownership(target)
        assert ownership is not None
        self.assertEqual(
            ownership["project_overrides"],
            {"test_command": "./gradlew legacyTest"},
        )

    def test_set_adds_and_replaces_overrides_only_with_reconfigure(self) -> None:
        target = self.install_target(
            "set-overrides",
            overrides=("compile_command=./gradlew oldCompile",),
        )

        guarded = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--set",
            "compile_command=./gradlew newCompile",
            "--set",
            "test_command=./gradlew focusedTest",
            "--dry-run",
        )
        self.assertNotEqual(guarded.returncode, 0)
        self.assertIn("--reconfigure", guarded.stderr)

        allowed = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--set",
            "compile_command=./gradlew newCompile",
            "--set",
            "test_command=./gradlew focusedTest",
            "--reconfigure",
            "--dry-run",
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual(
            json.loads(allowed.stdout)["next_configuration"]["project_overrides"],
            {
                "compile_command": "./gradlew newCompile",
                "test_command": "./gradlew focusedTest",
            },
        )

    def test_precompiled_bundle_configuration_change_requires_reconfigure(self) -> None:
        target = self.install_target("bundle-reconfigure", output_profile="service")
        matching_bundle = self.temp_path / "matching-bundle"
        FRAMEWORK.compile_bundle(
            FRAMEWORK.compose_profiles("cpp-to-java-25", "service"),
            matching_bundle,
            adapter="codex",
        )
        matching = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--bundle",
            str(matching_bundle),
            "--dry-run",
        )
        self.assertEqual(matching.returncode, 0, matching.stderr)
        self.assertEqual(json.loads(matching.stdout)["configuration_changes"], [])

        changed_bundle = self.temp_path / "changed-bundle"
        FRAMEWORK.compile_bundle(
            FRAMEWORK.compose_profiles("cpp-to-java-25", "library"),
            changed_bundle,
            adapter="codex",
        )
        guarded = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--bundle",
            str(changed_bundle),
            "--dry-run",
        )
        self.assertNotEqual(guarded.returncode, 0)
        self.assertIn("--reconfigure", guarded.stderr)

        allowed = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--bundle",
            str(changed_bundle),
            "--reconfigure",
            "--dry-run",
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        report = json.loads(allowed.stdout)
        self.assertEqual(report["next_configuration"]["adapter"], "codex")
        self.assertEqual(report["next_configuration"]["profiles"]["output"], "library")
        self.assertIn(
            {
                "field": "profiles",
                "current": report["current_configuration"]["profiles"],
                "next": report["next_configuration"]["profiles"],
            },
            report["configuration_changes"],
        )

    def test_v2_upgrade_infers_and_persists_nondefault_variables_as_overrides(self) -> None:
        target = self.install_target(
            "legacy-v2",
            overrides=("compile_command=./gradlew legacyCompile",),
        )
        self.make_v2_installation(target)

        preview = self.run_framework("upgrade", "--target", str(target), "--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        preview_report = json.loads(preview.stdout)
        self.assertEqual(
            preview_report["inferred_overrides"],
            {"compile_command": "./gradlew legacyCompile"},
        )
        self.assertTrue(preview_report["warnings"])
        self.assertEqual(
            preview_report["next_configuration"]["project_overrides"],
            {"compile_command": "./gradlew legacyCompile"},
        )
        legacy_ownership = FRAMEWORK.load_ownership(target)
        assert legacy_ownership is not None
        self.assertEqual(legacy_ownership["schema_version"], "2.0")

        upgraded = self.run_framework("upgrade", "--target", str(target))
        self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
        ownership = FRAMEWORK.load_ownership(target)
        assert ownership is not None
        self.assertEqual(ownership["schema_version"], "3.0")
        self.assertEqual(
            ownership["project_overrides"],
            {"compile_command": "./gradlew legacyCompile"},
        )
        self.assertEqual(ownership["inferred_overrides"], ["compile_command"])

    def test_v2_inferred_override_warning_tracks_explicit_removal(self) -> None:
        target = self.install_target(
            "legacy-v2-remove-override",
            overrides=("compile_command=./gradlew legacyCompile",),
        )
        self.make_v2_installation(target)

        result = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--unset",
            "compile_command",
            "--reconfigure",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["next_configuration"]["project_overrides"], {})
        self.assertEqual(report["inferred_overrides"], {})
        self.assertIn(
            "removed legacy-inferred overrides: compile_command", report["warnings"]
        )
        self.assertNotIn(
            "preserved legacy-inferred overrides: compile_command", report["warnings"]
        )

    def test_invalid_migration_blocks_upgrade_without_mutating_state(self) -> None:
        target = self.install_target("invalid-migration")
        migration = target / ".migration"
        shutil.copytree(GOLDEN_MIGRATION, migration)
        traceability_path = migration / "traceability.json"
        traceability = FRAMEWORK.read_json(traceability_path)
        traceability["links"][0]["decisions"] = ["DEC-DOES-NOT-EXIST"]
        traceability_path.write_text(
            FRAMEWORK.pretty_json(traceability), encoding="utf-8", newline="\n"
        )
        before = directory_bytes(migration)

        result = self.run_framework("upgrade", "--target", str(target))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid", result.stderr.lower())
        self.assertIn("DEC-DOES-NOT-EXIST", result.stderr)
        self.assertEqual(directory_bytes(migration), before)

    def test_major_migration_compatibility_requires_approved_referenced_decision(self) -> None:
        target = self.install_target("major-migration")
        self.make_v2_installation(target)
        migration = target / ".migration"
        shutil.copytree(GOLDEN_MIGRATION, migration)
        decision_path = migration / "decisions" / "DEC-9000.json"
        decision = FRAMEWORK.read_json(migration / "decisions" / "DEC-0001.json")
        decision.update(
            {
                "id": "DEC-9000",
                "context": "The installed migration guidance is moving from framework v2 to v3.",
                "decision": "Adopt framework 3.0.0 guidance while preserving live migration state.",
                "consequences": [
                    "Managed guidance changes major version",
                    "The .migration record remains unchanged",
                ],
                "affected_contracts": [],
                "approvals": ["migration-owner"],
            }
        )
        decision_path.write_text(
            FRAMEWORK.pretty_json(decision), encoding="utf-8", newline="\n"
        )
        config_path = migration / "config.json"
        config = FRAMEWORK.read_json(config_path)
        config.setdefault("project_decisions", {})["framework_upgrade"] = "DEC-9000"
        config_path.write_text(
            FRAMEWORK.pretty_json(config), encoding="utf-8", newline="\n"
        )
        self.assertEqual(FRAMEWORK.validate_migration_directory(migration), [])
        before = directory_bytes(migration)

        preview = self.run_framework("upgrade", "--target", str(target), "--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        state = json.loads(preview.stdout)["migration_state"]
        self.assertEqual(state["recorded_framework_version"], "2.0.0")
        self.assertTrue(state["present"])
        self.assertTrue(state["valid"])
        self.assertFalse(state["compatible"])
        self.assertTrue(state["diagnostics"])
        self.assertEqual(directory_bytes(migration), before)

        unapproved = self.run_framework("upgrade", "--target", str(target))
        self.assertNotEqual(unapproved.returncode, 0)
        self.assertIn("--allow-major", unapproved.stderr)
        self.assertEqual(directory_bytes(migration), before)

        missing_decision = self.run_framework(
            "upgrade", "--target", str(target), "--allow-major"
        )
        self.assertNotEqual(missing_decision.returncode, 0)
        self.assertIn("--decision", missing_decision.stderr)
        self.assertEqual(directory_bytes(migration), before)

        unrelated_decision = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--allow-major",
            "--decision",
            "DEC-0001",
        )
        self.assertNotEqual(unrelated_decision.returncode, 0)
        self.assertIn("project_decisions.framework_upgrade", unrelated_decision.stderr)
        self.assertEqual(directory_bytes(migration), before)

        approved = self.run_framework(
            "upgrade",
            "--target",
            str(target),
            "--allow-major",
            "--decision",
            "DEC-9000",
        )
        self.assertEqual(approved.returncode, 0, approved.stderr)
        self.assertEqual(directory_bytes(migration), before)

        repeated = self.run_framework(
            "upgrade", "--target", str(target), "--dry-run"
        )
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        repeated_report = json.loads(repeated.stdout)
        self.assertTrue(repeated_report["migration_state"]["compatible"])
        self.assertEqual(repeated_report["writes"], [])
        self.assertEqual(repeated_report["deletes"], [])
        self.assertEqual(directory_bytes(migration), before)

    def test_terminal_migration_allows_major_guidance_update_without_approval(self) -> None:
        target = self.install_target("terminal-major-migration")
        self.make_v2_installation(target)
        migration = target / ".migration"
        shutil.copytree(GOLDEN_MIGRATION, migration)
        FRAMEWORK.transition_state(
            migration / "state.json", "cut_over", "Approved cutover completed"
        )
        FRAMEWORK.transition_state(
            migration / "state.json",
            "decommissioned",
            "Legacy retention and removal obligations completed",
        )
        self.assertEqual(FRAMEWORK.validate_migration_directory(migration), [])
        before = directory_bytes(migration)

        result = self.run_framework("upgrade", "--target", str(target))

        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout)["migration_state"]
        self.assertTrue(state["compatible"])
        self.assertIn("terminal", " ".join(state["diagnostics"]))
        self.assertEqual(directory_bytes(migration), before)

    def test_upgrade_wrappers_infer_configuration_without_prompting(self) -> None:
        root_target = self.install_target("root-wrapper", output_profile="library")
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        root_result = subprocess.run(
            [
                "bash",
                str(REPOSITORY_ROOT / "install.sh"),
                "--upgrade",
                "--target",
                str(root_target),
                "--dry-run",
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(root_result.returncode, 0, root_result.stderr)
        root_report = json.loads(root_result.stdout)
        self.assertEqual(root_report["next_configuration"]["adapter"], "codex")
        self.assertEqual(root_report["next_configuration"]["profiles"]["output"], "library")

        adapter_target = self.install_target(
            "adapter-wrapper",
            overrides=("compile_command=./gradlew legacyCompile",),
        )
        adapter_result = subprocess.run(
            [
                "bash",
                str(REPOSITORY_ROOT / "agents" / "codex" / "install.sh"),
                str(adapter_target),
                "--upgrade",
                "--reconfigure",
                "--unset",
                "compile_command",
                "--dry-run",
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(adapter_result.returncode, 0, adapter_result.stderr)
        adapter_report = json.loads(adapter_result.stdout)
        self.assertEqual(adapter_report["next_configuration"]["adapter"], "codex")
        self.assertEqual(adapter_report["next_configuration"]["project_overrides"], {})

    def test_root_wrapper_rejects_bundle_profile_options_instead_of_dropping_them(self) -> None:
        result = subprocess.run(
            [
                "bash",
                str(REPOSITORY_ROOT / "install.sh"),
                "--bundle",
                str(self.temp_path / "bundle"),
                "--pair",
                "cpp-to-java-25",
                "--target",
                str(self.temp_path),
                "--dry-run",
            ],
            cwd=REPOSITORY_ROOT,
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--bundle cannot be combined", result.stderr)

    def test_exact_precompiled_adapter_bundle_can_be_installed(self) -> None:
        bundle = self.temp_path / "codex-bundle"
        composition = FRAMEWORK.compose_profiles("cpp-to-java-25", "library")
        manifest = FRAMEWORK.compile_bundle(composition, bundle, adapter="codex")
        target = self.temp_path / "precompiled-target"
        target.mkdir()

        result = self.run_framework(
            "install",
            "--adapter",
            "codex",
            "--target",
            str(target),
            "--bundle",
            str(bundle),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ownership = FRAMEWORK.load_ownership(target)
        assert ownership is not None
        self.assertEqual(ownership["bundle_digest"], manifest["bundle_digest"])
        self.assertEqual(ownership["profiles"]["output"], "library")

        mismatch_target = self.temp_path / "mismatch-target"
        mismatch_target.mkdir()
        mismatch = self.run_framework(
            "install",
            "--adapter",
            "kiro",
            "--target",
            str(mismatch_target),
            "--bundle",
            str(bundle),
        )
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("bundle adapter is 'codex', not 'kiro'", mismatch.stderr)

    def test_dry_run_and_fresh_install_for_every_adapter(self) -> None:
        adapter_artifacts = {
            "kiro": ".kiro/hooks/migration-quality.json",
            "claude": ".claude/settings.json",
            "codex": ".codex/hooks.json",
        }
        for adapter, artifact in adapter_artifacts.items():
            with self.subTest(adapter=adapter):
                target = self.temp_path / f"target-{adapter}"
                target.mkdir()

                dry_run = self.run_framework(
                    "install",
                    "--adapter",
                    adapter,
                    "--target",
                    str(target),
                    "--output-profile",
                    "service",
                    "--dry-run",
                )
                self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
                dry_report = json.loads(dry_run.stdout)
                self.assertTrue(dry_report["dry_run"])
                self.assertTrue(dry_report["writes"])
                self.assertEqual(dry_report["conflicts"], [])
                self.assertEqual(list(target.iterdir()), [])

                installed = self.run_framework(
                    "install",
                    "--adapter",
                    adapter,
                    "--target",
                    str(target),
                    "--output-profile",
                    "service",
                )
                self.assertEqual(installed.returncode, 0, installed.stderr)
                install_report = json.loads(installed.stdout)
                self.assertFalse(install_report["dry_run"])
                self.assertEqual(install_report["conflicts"], [])
                self.assertTrue((target / artifact).is_file())

                ownership = FRAMEWORK.load_ownership(target)
                self.assertIsNotNone(ownership)
                assert ownership is not None
                self.assertEqual(ownership["adapter"], adapter)
                self.assertEqual(ownership["profiles"]["output"], "service")

                if adapter == "codex":
                    hooks = FRAMEWORK.read_json(target / artifact)
                    metadata = hooks["_migration_framework"]
                    self.assertTrue(metadata["instructions"])
                    self.assertTrue(metadata["activation_requirements"])
                    self.assertTrue(hooks["hooks"], "command hooks remain native")
                    self.assertTrue(
                        all(
                            instruction["type"] == "agent"
                            for instruction in metadata["instructions"]
                        )
                    )
                    guide = (target / "AGENTS.md").read_text(encoding="utf-8")
                    self.assertIn("Hook capability notice", guide)

    def test_unmanaged_collision_aborts_without_mutating_the_target(self) -> None:
        target = self.temp_path / "unmanaged-collision"
        target.mkdir()
        agents = target / "AGENTS.md"
        agents.write_text("user-owned instructions\n", encoding="utf-8")

        result = self.run_framework(
            "install", "--adapter", "codex", "--target", str(target)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unmanaged target collision", result.stderr)
        self.assertIn("AGENTS.md", result.stderr)
        self.assertEqual(
            agents.read_text(encoding="utf-8"), "user-owned instructions\n"
        )
        self.assertFalse((target / FRAMEWORK.OWNERSHIP_FILE).exists())
        self.assertEqual(
            [path.relative_to(target).as_posix() for path in target.rglob("*")],
            ["AGENTS.md"],
        )

    def test_every_adapter_detects_local_changes_on_upgrade_and_force_is_explicit(self) -> None:
        managed_paths = {
            "kiro": ".kiro/skills/migrate-init/SKILL.md",
            "claude": "CLAUDE.md",
            "codex": "AGENTS.md",
        }
        for adapter, relative in managed_paths.items():
            with self.subTest(adapter=adapter):
                target = self.temp_path / f"upgrade-{adapter}"
                target.mkdir()
                installed = self.run_framework(
                    "install", "--adapter", adapter, "--target", str(target)
                )
                self.assertEqual(installed.returncode, 0, installed.stderr)
                managed = target / relative
                managed.write_text("local framework-file edit\n", encoding="utf-8")

                conflicted = self.run_framework(
                    "upgrade", "--adapter", adapter, "--target", str(target)
                )
                self.assertNotEqual(conflicted.returncode, 0)
                self.assertIn("locally modified managed file", conflicted.stderr)
                self.assertEqual(managed.read_text(encoding="utf-8"), "local framework-file edit\n")

                forced = self.run_framework(
                    "upgrade", "--adapter", adapter, "--target", str(target), "--force"
                )
                self.assertEqual(forced.returncode, 0, forced.stderr)
                forced_report = json.loads(forced.stdout)
                self.assertTrue(forced_report["forced"])
                self.assertEqual(forced_report["forced_replacements"], [relative])
                self.assertNotEqual(managed.read_text(encoding="utf-8"), "local framework-file edit\n")

    def test_managed_upgrade_local_modification_conflict_and_explicit_force(self) -> None:
        target = self.temp_path / "managed-upgrade"
        target.mkdir()
        install = self.run_framework(
            "install", "--adapter", "codex", "--target", str(target)
        )
        self.assertEqual(install.returncode, 0, install.stderr)

        upgrade = self.run_framework(
            "upgrade", "--adapter", "codex", "--target", str(target)
        )
        self.assertEqual(upgrade.returncode, 0, upgrade.stderr)
        upgrade_report = json.loads(upgrade.stdout)
        self.assertEqual(upgrade_report["mode"], "upgrade")
        self.assertEqual(upgrade_report["conflicts"], [])
        self.assertTrue(upgrade_report["unchanged"])

        agents = target / "AGENTS.md"
        agents.write_text("local edit that must survive\n", encoding="utf-8")
        conflicted = self.run_framework(
            "upgrade", "--adapter", "codex", "--target", str(target)
        )
        self.assertNotEqual(conflicted.returncode, 0)
        self.assertIn("locally modified managed file", conflicted.stderr)
        self.assertEqual(
            agents.read_text(encoding="utf-8"), "local edit that must survive\n"
        )

        forced = self.run_framework(
            "upgrade",
            "--adapter",
            "codex",
            "--target",
            str(target),
            "--force",
        )
        self.assertEqual(forced.returncode, 0, forced.stderr)
        forced_report = json.loads(forced.stdout)
        self.assertTrue(forced_report["forced"])
        self.assertEqual(forced_report["forced_replacements"], ["AGENTS.md"])
        self.assertNotIn(
            "local edit that must survive", agents.read_text(encoding="utf-8")
        )
        ownership = FRAMEWORK.load_ownership(target)
        assert ownership is not None
        self.assertEqual(
            ownership["files"]["AGENTS.md"], FRAMEWORK.sha256_file(agents)
        )

    def test_modified_or_forged_ownership_metadata_is_rejected(self) -> None:
        target = self.temp_path / "ownership-tamper"
        target.mkdir()
        installed = self.run_framework(
            "install", "--adapter", "codex", "--target", str(target)
        )
        self.assertEqual(installed.returncode, 0, installed.stderr)

        ownership_path = target / FRAMEWORK.OWNERSHIP_FILE
        ownership = FRAMEWORK.read_json(ownership_path)
        ownership["files"]["important-user-file.txt"] = "0" * 64
        ownership_path.write_text(FRAMEWORK.pretty_json(ownership), encoding="utf-8")
        with self.assertRaisesRegex(FRAMEWORK.FrameworkError, "modified or corrupted"):
            FRAMEWORK.load_ownership(target)

        checksum_path = target / FRAMEWORK.OWNERSHIP_CHECKSUM_FILE
        checksum_path.write_text(FRAMEWORK.sha256_file(ownership_path) + "\n", encoding="ascii")
        with self.assertRaisesRegex(FRAMEWORK.FrameworkError, "outside the codex adapter surface"):
            FRAMEWORK.load_ownership(target)

    def test_promote_installation_rolls_back_a_mocked_mid_promotion_failure(self) -> None:
        target = self.temp_path / "rollback-target"
        target.mkdir()
        (target / "a.txt").write_bytes(b"old-a")
        (target / "obsolete.txt").write_bytes(b"old-obsolete")
        (target / "unrelated.txt").write_bytes(b"untouched")

        files = {"a.txt": b"new-a", "b.txt": b"new-b"}
        ownership = {
            "$schema": "schemas/installation-ownership.schema.json",
            "schema_version": "2.0",
            "framework_version": "2.0.0",
            "adapter": "codex",
            "profiles": {
                "source": "cpp",
                "target": "java-25",
                "pair": "cpp-to-java-25",
                "output": "service",
            },
            "bundle_digest": "0" * 64,
            "files": {
                relative: FRAMEWORK.sha256_bytes(content)
                for relative, content in files.items()
            },
        }
        preflight = {
            "writes": ["a.txt", "b.txt"],
            "deletes": ["obsolete.txt"],
        }

        real_replace = os.replace

        def fail_while_promoting_b(source: object, destination: object) -> None:
            source_path = Path(source)
            if source_path.name == "b.txt" and "stage" in source_path.parts:
                raise OSError("mocked promotion failure")
            real_replace(source, destination)

        with mock.patch.object(
            FRAMEWORK.os, "replace", side_effect=fail_while_promoting_b
        ):
            with self.assertRaisesRegex(OSError, "mocked promotion failure"):
                FRAMEWORK.promote_installation(
                    target, files, ownership, preflight
                )

        self.assertEqual((target / "a.txt").read_bytes(), b"old-a")
        self.assertFalse((target / "b.txt").exists())
        self.assertEqual(
            (target / "obsolete.txt").read_bytes(), b"old-obsolete"
        )
        self.assertEqual((target / "unrelated.txt").read_bytes(), b"untouched")
        self.assertFalse((target / FRAMEWORK.OWNERSHIP_FILE).exists())
        self.assertFalse(
            any(
                path.name.startswith(".migration-framework-transaction-")
                for path in self.temp_path.iterdir()
            )
        )


if __name__ == "__main__":
    unittest.main()
