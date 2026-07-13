"""Focused conformance tests for the installed migration completion runtime."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = REPOSITORY_ROOT / "agents" / "migration_runtime.py"
SCHEMAS = REPOSITORY_ROOT / "schemas"

SPEC = importlib.util.spec_from_file_location("migration_runtime_under_test", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


def schema(name: str) -> str:
    return f"https://example.invalid/ai-migration-framework/schemas/{name}"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class MigrationRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="migration-runtime-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.migration = self.root / ".migration"
        self.layout = RUNTIME.discover_runtime_layout(RUNTIME_PATH)
        self._create_strict_project()

    def _state_history(self) -> list[dict[str, object]]:
        states = [
            "initialize",
            "discover",
            "characterize",
            "map",
            "plan",
            "execute",
            "verify",
            "review",
            "approve",
        ]
        result: list[dict[str, object]] = []
        previous: str | None = None
        for index, destination in enumerate(states):
            result.append(
                {
                    "from": previous,
                    "to": destination,
                    "at": f"2026-01-01T00:00:{index:02d}Z",
                    "reason": destination,
                }
            )
            previous = destination
        return result

    def _create_strict_project(self) -> None:
        source = self.root / "legacy" / "main.cpp"
        target = self.root / "app" / "src" / "Main.java"
        test = self.root / "app" / "test" / "MainTest.java"
        source.parent.mkdir(parents=True)
        target.parent.mkdir(parents=True)
        test.parent.mkdir(parents=True)
        source.write_text("int answer() { return 42; }\n", encoding="utf-8")
        target.write_text("final class Main { static int answer() { return 42; } }\n", encoding="utf-8")
        test.write_text("final class MainTest {}\n", encoding="utf-8")

        write_json(
            self.migration / "config.json",
            {
                "$schema": schema("migration-config.schema.json"),
                "schema_version": "2.0",
                "framework_version": "3.1.0",
                "profiles": {
                    "source": "cpp",
                    "target": "java-25",
                    "pair": "cpp-to-java-25",
                },
                "output_profile": "library",
                "migration_strategy": "incremental",
                "source_root": "legacy",
                "target_root": "app",
                "quality_gates": {
                    "required_checks": ["build"],
                    "coverage": {
                        "metric": "behavioral-contract",
                        "threshold_percent": 100,
                        "rationale": "The one observable contract must pass.",
                    },
                },
                "project_decisions": {},
                "validation_status": "valid",
            },
        )
        history = self._state_history()
        write_json(
            self.migration / "state.json",
            {
                "$schema": schema("migration-state.schema.json"),
                "schema_version": "2.0",
                "migration_id": "runtime-test",
                "revision": len(history) - 1,
                "status": "approve",
                "resume_to": None,
                "active_slice": None,
                "completed_slices": ["SLICE-0001"],
                "blocked_by": [],
                "last_transition": history[-1],
                "history": history,
                "validation_status": "valid",
            },
        )
        write_json(
            self.migration / "inventory.json",
            {
                "$schema": schema("inventory.schema.json"),
                "schema_version": "2.0",
                "migration_id": "runtime-test",
                "units": [
                    {
                        "id": "SRC-0001",
                        "path": "main.cpp",
                        "kind": "production",
                        "reachability": "reachable",
                        "behaviors": ["BEH-0001"],
                        "dependencies": [],
                        "risks": [],
                    }
                ],
            },
        )
        write_json(
            self.migration / "scope.json",
            {
                "$schema": schema("migration-scope.schema.json"),
                "schema_version": "3.0",
                "migration_id": "runtime-test",
                "policy": {
                    "mode": "whole-source-root",
                    "required_claim": "migrated",
                    "allow_approved_removals": False,
                    "boundary_decisions": [],
                },
                "source_snapshot": {
                    "source_root": "legacy",
                    "revision": None,
                    "captured_at": "1970-01-01T00:00:00Z",
                    "digest": "0" * 64,
                    "files": [],
                    "excluded_files": [],
                },
                "units": [
                    {
                        "source_unit": "SRC-0001",
                        "disposition": "migrated",
                        "target_units": ["TGT-0001"],
                        "decisions": [],
                        "exceptions": [],
                        "rationale": "The observable implementation moved to Java.",
                    }
                ],
            },
        )
        write_json(
            self.migration / "target-inventory.json",
            {
                "$schema": schema("target-inventory.schema.json"),
                "schema_version": "3.0",
                "migration_id": "runtime-test",
                "units": [
                    {
                        "id": "TGT-0001",
                        "path": "app/src/Main.java",
                        "kind": "production",
                        "status": "present",
                        "sha256": RUNTIME.sha256_file(target),
                    },
                    {
                        "id": "TEST-0001",
                        "path": "app/test/MainTest.java",
                        "kind": "test",
                        "status": "present",
                        "sha256": RUNTIME.sha256_file(test),
                    },
                ],
            },
        )
        write_json(
            self.migration / "behaviors" / "BEH-0001.json",
            {
                "$schema": schema("behavioral-contract.schema.json"),
                "schema_version": "2.0",
                "id": "BEH-0001",
                "source_units": ["SRC-0001"],
                "preconditions": [],
                "stimulus": "Call answer",
                "observations": ["Returns 42"],
                "evidence": ["EVID-0001"],
                "known_gaps": [],
            },
        )
        write_json(
            self.migration / "plans" / "SLICE-0001.json",
            {
                "$schema": schema("plan.schema.json"),
                "schema_version": "2.0",
                "id": "SLICE-0001",
                "status": "approved",
                "source_units": ["SRC-0001"],
                "behavioral_contracts": ["BEH-0001"],
                "target_units": ["TGT-0001"],
                "dependencies": [],
                "release_boundary": "One pure function",
                "rollback": "Use the source implementation",
                "verification_gates": ["build"],
                "approval_refs": ["owner@example.invalid"],
            },
        )
        for identifier, phase, slice_id, gate in (
            ("EVID-0001", "characterize", None, "characterization"),
            ("EVID-0002", "verify", "SLICE-0001", "build"),
        ):
            artifact_path = source if phase == "characterize" else target
            write_json(
                self.migration / "evidence" / f"{identifier}.json",
                {
                    "$schema": schema("evidence-v3.schema.json"),
                    "schema_version": "3.0",
                    "id": identifier,
                    "phase": phase,
                    "slice_id": slice_id,
                    "gate": gate,
                    "status": "pass",
                    "command": "verified-command",
                    "working_directory": ".",
                    "exit_code": 0,
                    "environment": {"runner": "test"},
                    "artifacts": [
                        {
                            "path": artifact_path.relative_to(self.root).as_posix(),
                            "sha256": RUNTIME.sha256_file(artifact_path),
                        }
                    ],
                    "contracts": ["BEH-0001"],
                    "recorded_at": "2026-01-01T00:01:00Z",
                },
            )
        write_json(
            self.migration / "traceability.json",
            {
                "$schema": schema("traceability.schema.json"),
                "schema_version": "2.0",
                "migration_id": "runtime-test",
                "links": [
                    {
                        "source_unit": "SRC-0001",
                        "behavioral_contracts": ["BEH-0001"],
                        "target_units": ["TGT-0001"],
                        "tests": ["TEST-0001"],
                        "decisions": [],
                        "evidence": ["EVID-0001", "EVID-0002"],
                        "exceptions": [],
                        "status": "approved",
                    }
                ],
            },
        )
        RUNTIME.snapshot_migration(
            self.migration, project_root=self.root, layout=self.layout
        )

    def audit(self, claim: str = "migrated") -> dict[str, object]:
        return RUNTIME.audit_migration(
            self.migration,
            claim,
            project_root=self.root,
            layout=self.layout,
        )

    def test_strict_audit_and_certificate_succeed_for_closed_scope(self) -> None:
        report = self.audit()
        self.assertTrue(report["structurally_valid"], report["findings"])
        self.assertTrue(report["certifiable"], report["findings"])
        self.assertEqual(report["counts"]["source_units"], 1)
        self.assertEqual(report["counts"]["approved_behaviors"], 1)

        certificate = RUNTIME.certify_migration(
            self.migration,
            "migrated",
            "implementation",
            project_root=self.root,
            layout=self.layout,
        )
        self.assertTrue(certificate["certified"])
        self.assertEqual(certificate["claim"], "migrated")
        self.assertEqual(
            json.loads((self.migration / "completion-certificate.json").read_text()),
            certificate,
        )

    def test_missing_source_file_blocks_certification(self) -> None:
        (self.root / "legacy" / "main.cpp").unlink()
        report = self.audit()
        self.assertFalse(report["certifiable"])
        self.assertTrue(any("recorded path is missing" in item for item in report["findings"]))

    def test_pending_unit_blocks_both_claims(self) -> None:
        scope_path = self.migration / "scope.json"
        scope = json.loads(scope_path.read_text())
        scope["policy"]["required_claim"] = "accounted"
        scope["units"][0]["disposition"] = "pending"
        scope["units"][0]["target_units"] = []
        write_json(scope_path, scope)
        for claim in ("accounted", "migrated"):
            with self.subTest(claim=claim):
                report = self.audit(claim)
                self.assertFalse(report["certifiable"])
                self.assertIn("SRC-0001", report["ids"]["pending"])

    def test_unresolved_or_unchecksummed_target_blocks_certification(self) -> None:
        target_path = self.migration / "target-inventory.json"
        inventory = json.loads(target_path.read_text())
        inventory["units"][0]["sha256"] = None
        write_json(target_path, inventory)
        report = self.audit()
        self.assertFalse(report["certifiable"])
        self.assertTrue(
            any("present target has no concrete checksum" in item for item in report["findings"])
        )

    def test_target_inventory_cannot_point_outside_configured_target_root(self) -> None:
        target_path = self.migration / "target-inventory.json"
        inventory = json.loads(target_path.read_text())
        source = self.root / "legacy" / "main.cpp"
        inventory["units"][0]["path"] = "legacy/main.cpp"
        inventory["units"][0]["sha256"] = RUNTIME.sha256_file(source)
        write_json(target_path, inventory)
        report = self.audit()
        self.assertFalse(report["certifiable"])
        self.assertTrue(
            any("must resolve under config.target_root" in item for item in report["findings"])
        )

    def test_symlinked_target_path_cannot_supply_completion_evidence(self) -> None:
        real_target = self.root / "app" / "src" / "Main.java"
        linked_target = self.root / "app" / "src" / "LinkedMain.java"
        linked_target.symlink_to(real_target)
        target_path = self.migration / "target-inventory.json"
        inventory = json.loads(target_path.read_text())
        inventory["units"][0]["path"] = "app/src/LinkedMain.java"
        inventory["units"][0]["sha256"] = RUNTIME.sha256_file(real_target)
        write_json(target_path, inventory)

        report = self.audit()

        self.assertFalse(report["certifiable"])
        self.assertTrue(
            any("symlink path component is forbidden" in item for item in report["findings"])
        )

    def test_dishonest_passing_evidence_blocks_certification(self) -> None:
        evidence_path = self.migration / "evidence" / "EVID-0002.json"
        evidence = json.loads(evidence_path.read_text())
        evidence["exit_code"] = 7
        write_json(evidence_path, evidence)

        report = self.audit()

        self.assertFalse(report["certifiable"])
        self.assertTrue(
            any("pass status is dishonest" in item for item in report["findings"])
        )

    def test_known_behavior_gap_blocks_strict_migrated_claim(self) -> None:
        behavior_path = self.migration / "behaviors" / "BEH-0001.json"
        behavior = json.loads(behavior_path.read_text())
        behavior["known_gaps"] = ["Only the happy path was characterized"]
        write_json(behavior_path, behavior)

        report = self.audit()

        self.assertFalse(report["certifiable"])
        self.assertTrue(
            any("forbids known behavior gaps" in item for item in report["findings"])
        )

    def test_bounded_scope_requires_an_approved_boundary_decision(self) -> None:
        scope_path = self.migration / "scope.json"
        scope = json.loads(scope_path.read_text())
        scope["policy"]["mode"] = "bounded"
        write_json(scope_path, scope)

        report = self.audit()

        self.assertFalse(report["certifiable"])
        self.assertTrue(
            any("bounded scope requires" in item for item in report["findings"])
        )

    def test_legacy_v2_opaque_target_references_remain_structurally_readable(self) -> None:
        (self.migration / "scope.json").unlink()
        (self.migration / "target-inventory.json").unlink()
        context = RUNTIME.load_context(
            self.migration, project_root=self.root, layout=self.layout
        )
        self.assertEqual(RUNTIME.validate_context(context), [])

    def test_non_json_migration_record_drift_stales_certificate(self) -> None:
        notes = self.migration / "research.md"
        notes.write_text("initial\n", encoding="utf-8")
        certificate = RUNTIME.certify_migration(
            self.migration,
            "migrated",
            "implementation",
            project_root=self.root,
            layout=self.layout,
        )
        notes.write_text("changed\n", encoding="utf-8")
        context = RUNTIME.load_context(
            self.migration, project_root=self.root, layout=self.layout
        )
        fresh, errors = RUNTIME._certificate_fresh(context, certificate)
        self.assertFalse(fresh)
        self.assertIn("completion certificate migration graph digest is stale", errors)

    def test_cutover_reaudits_certificate_counts_before_mutating_state(self) -> None:
        RUNTIME.certify_migration(
            self.migration,
            "migrated",
            "implementation",
            project_root=self.root,
            layout=self.layout,
        )
        certificate_path = self.migration / "completion-certificate.json"
        certificate = json.loads(certificate_path.read_text())
        certificate["counts"]["migrated_units"] = 999
        write_json(certificate_path, certificate)
        before = (self.migration / "state.json").read_bytes()
        with self.assertRaisesRegex(
            RUNTIME.MigrationRuntimeError, "does not match the current audit"
        ):
            RUNTIME.transition_migration(
                self.migration,
                "cut_over",
                "forged count",
                project_root=self.root,
                layout=self.layout,
            )
        self.assertEqual((self.migration / "state.json").read_bytes(), before)

    def test_direct_terminal_state_without_certificate_is_invalid(self) -> None:
        state_path = self.migration / "state.json"
        state = json.loads(state_path.read_text())
        transition = {
            "from": "approve",
            "to": "cut_over",
            "at": "2026-01-01T00:02:00Z",
            "reason": "direct edit",
        }
        state["status"] = "cut_over"
        state["revision"] += 1
        state["last_transition"] = transition
        state["history"].append(transition)
        write_json(state_path, state)
        context = RUNTIME.load_context(
            self.migration, project_root=self.root, layout=self.layout
        )
        errors = RUNTIME.validate_context(context)
        self.assertTrue(any("requires a fresh completion certificate" in item for item in errors))

    def test_failed_transition_does_not_mutate_state(self) -> None:
        before = (self.migration / "state.json").read_bytes()
        with self.assertRaisesRegex(RUNTIME.MigrationRuntimeError, "completion certificate"):
            RUNTIME.transition_migration(
                self.migration,
                "cut_over",
                "not certified",
                project_root=self.root,
                layout=self.layout,
            )
        self.assertEqual((self.migration / "state.json").read_bytes(), before)

    def test_cutover_transition_rebinds_certificate_to_new_revision(self) -> None:
        certificate = RUNTIME.certify_migration(
            self.migration,
            "migrated",
            "implementation",
            project_root=self.root,
            layout=self.layout,
        )
        result = RUNTIME.transition_migration(
            self.migration,
            "cut_over",
            "global implementation certificate passed",
            project_root=self.root,
            layout=self.layout,
        )
        self.assertEqual(result["state"]["status"], "cut_over")
        rebound = json.loads((self.migration / "completion-certificate.json").read_text())
        self.assertEqual(rebound["state_revision"], certificate["state_revision"] + 1)
        context = RUNTIME.load_context(
            self.migration, project_root=self.root, layout=self.layout
        )
        self.assertTrue(RUNTIME._certificate_fresh(context, rebound)[0])

    def test_decommission_recertification_replaces_stale_cutover_certificate(self) -> None:
        RUNTIME.certify_migration(
            self.migration,
            "migrated",
            "implementation",
            project_root=self.root,
            layout=self.layout,
        )
        RUNTIME.transition_migration(
            self.migration,
            "cut_over",
            "global implementation certificate passed",
            project_root=self.root,
            layout=self.layout,
        )
        target = self.root / "app" / "src" / "Main.java"
        for identifier, phase in (
            ("EVID-0003", "cut_over"),
            ("EVID-0004", "decommission"),
        ):
            write_json(
                self.migration / "evidence" / f"{identifier}.json",
                {
                    "$schema": schema("evidence-v3.schema.json"),
                    "schema_version": "3.0",
                    "id": identifier,
                    "phase": phase,
                    "slice_id": "SLICE-0001",
                    "gate": phase,
                    "status": "pass",
                    "command": f"verified-{phase}",
                    "working_directory": ".",
                    "exit_code": 0,
                    "environment": {"runner": "test"},
                    "artifacts": [
                        {
                            "path": "app/src/Main.java",
                            "sha256": RUNTIME.sha256_file(target),
                        }
                    ],
                    "contracts": ["BEH-0001"],
                    "recorded_at": "2026-01-01T00:02:00Z",
                },
            )
        trace_path = self.migration / "traceability.json"
        trace = json.loads(trace_path.read_text())
        trace["links"][0]["evidence"].extend(["EVID-0003", "EVID-0004"])
        write_json(trace_path, trace)

        stale_context = RUNTIME.load_context(
            self.migration, project_root=self.root, layout=self.layout
        )
        self.assertTrue(
            any(
                "terminal certificate" in item
                for item in RUNTIME.validate_context(stale_context)
            )
        )
        terminal_authorization = RUNTIME.certify_migration(
            self.migration,
            "migrated",
            "decommission",
            project_root=self.root,
            layout=self.layout,
        )
        result = RUNTIME.transition_migration(
            self.migration,
            "decommissioned",
            "whole declared scope passed terminal certification",
            project_root=self.root,
            layout=self.layout,
        )

        self.assertEqual(result["state"]["status"], "decommissioned")
        rebound = json.loads((self.migration / "completion-certificate.json").read_text())
        self.assertEqual(rebound["stage"], "decommission")
        self.assertEqual(
            rebound["state_revision"], terminal_authorization["state_revision"] + 1
        )
        terminal_context = RUNTIME.load_context(
            self.migration, project_root=self.root, layout=self.layout
        )
        self.assertEqual(RUNTIME.validate_context(terminal_context), [])
        self.assertTrue(RUNTIME._certificate_fresh(terminal_context, rebound)[0])

    def test_copied_installed_layout_discovers_schemas_and_runtime_metadata(self) -> None:
        installed = self.root / ".migration-framework"
        (installed / "bin").mkdir(parents=True)
        shutil.copyfile(RUNTIME_PATH, installed / "bin" / "migrationctl.py")
        shutil.copytree(SCHEMAS, installed / "schemas")
        framework = json.loads((REPOSITORY_ROOT / "framework.json").read_text())
        write_json(
            installed / "runtime.json",
            {
                "schema_version": "1.0",
                "framework_version": framework["framework_version"],
                "state_machine": framework["state_machine"],
            },
        )
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        process = subprocess.run(
            [
                sys.executable,
                str(installed / "bin" / "migrationctl.py"),
                "validate",
                ".migration",
            ],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertTrue(json.loads(process.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
