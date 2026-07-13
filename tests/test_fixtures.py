"""Conformance tests for the C++ fixture matrix and golden migration."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPOSITORY_ROOT / "fixtures"
GOLDEN_ROOT = FIXTURES_ROOT / "golden-multimodule"
GOLDEN_MIGRATION = GOLDEN_ROOT / "expected" / ".migration"

MODULE_NAME = "migration_framework_v3_fixture_test"
if MODULE_NAME in sys.modules:
    FRAMEWORK = sys.modules[MODULE_NAME]
else:
    framework_path = REPOSITORY_ROOT / "agents" / "framework.py"
    spec = importlib.util.spec_from_file_location(MODULE_NAME, framework_path)
    assert spec is not None and spec.loader is not None
    FRAMEWORK = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = FRAMEWORK
    spec.loader.exec_module(FRAMEWORK)


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


class FixtureMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_paths = sorted(FIXTURES_ROOT.glob("*/fixture.json"))
        cls.fixtures = [load_json(path) for path in cls.fixture_paths]

    def test_every_fixture_conforms_to_the_versioned_schema(self) -> None:
        schema = REPOSITORY_ROOT / "schemas" / "fixture.schema.json"
        self.assertGreaterEqual(len(self.fixture_paths), 5)
        for path in self.fixture_paths:
            with self.subTest(fixture=path.parent.name):
                self.assertEqual(FRAMEWORK.validate_json_file(path, schema), [])

    def test_matrix_covers_profiles_builds_tests_and_cpp_migration_hazards(self) -> None:
        outputs = {fixture["output_profile"] for fixture in self.fixtures}
        builds = {fixture["build_system"] for fixture in self.fixtures}
        tests = {fixture["test_framework"] for fixture in self.fixtures}
        features = {
            item
            for fixture in self.fixtures
            for field in ("source_units", "hazards", "interfaces")
            for item in fixture[field]
        }

        self.assertEqual(outputs, {"service", "library", "sdk", "cli"})
        self.assertTrue({"cmake", "make", "meson"}.issubset(builds))
        self.assertTrue({"googletest", "catch2", "doctest"}.issubset(tests))

        required_feature_groups = {
            "ownership and RAII": {
                "raii-ownership",
                "raii-transaction",
                "ownership-transfer",
            },
            "concurrency": {
                "shared-mutex-concurrency",
                "thread-pool-ordering",
            },
            "templates": {"templates", "template-algorithms"},
            "macros": {"macro-configuration", "macro-feature-flag"},
            "error models": {"error-model", "exception-contract"},
            "binary or native dependencies": {
                "binary-compatibility",
                "native-abi",
                "native-library",
                "native-sqlite",
            },
            "serialization": {"serialization", "serialization-layout"},
            "numeric behavior": {"numeric-width", "floating-point-rounding"},
            "filesystem I/O": {"filesystem"},
            "network I/O": {"network", "http"},
            "platform behavior": {"platform-conditionals"},
        }
        for label, candidates in required_feature_groups.items():
            with self.subTest(feature=label):
                self.assertTrue(
                    candidates & features,
                    f"fixture matrix has no representative for {label}",
                )

    def test_fixture_profile_selections_are_composable_without_core_changes(self) -> None:
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["id"]):
                composition = FRAMEWORK.compose_profiles(
                    "cpp-to-java-25", fixture["output_profile"]
                )
                self.assertEqual(
                    composition.source["id"], fixture["source_profile"]
                )
                self.assertEqual(
                    composition.target["id"], fixture["target_profile"]
                )
                self.assertEqual(
                    composition.output["id"], fixture["output_profile"]
                )

    def test_scaffolded_second_language_pair_composes_without_core_changes(self) -> None:
        scaffold = FIXTURES_ROOT / "profile-scaffold"
        schema = REPOSITORY_ROOT / "schemas" / "profile.schema.json"
        profiles = {
            path.stem.removesuffix("-profile"): load_json(path)
            for path in sorted(scaffold.glob("*-profile.json"))
        }
        self.assertEqual(set(profiles), {"source", "target", "pair", "output"})
        for path in sorted(scaffold.glob("*-profile.json")):
            with self.subTest(profile=path.name):
                self.assertEqual(FRAMEWORK.validate_json_file(path, schema), [])

        variables = {}
        for kind in ("source", "target", "pair", "output"):
            variables.update(profiles[kind]["variables"])
        composition = FRAMEWORK.Composition(
            FRAMEWORK.read_json(REPOSITORY_ROOT / "framework.json"),
            profiles["source"],
            profiles["target"],
            profiles["pair"],
            profiles["output"],
            variables,
        )
        FRAMEWORK.validate_composition(composition)
        self.assertEqual(composition.profile_ids["target"], "sample-target")


class GoldenScenarioTests(unittest.TestCase):
    def test_golden_migration_is_schema_valid_and_cross_reference_complete(self) -> None:
        self.assertEqual(
            FRAMEWORK.validate_migration_directory(GOLDEN_MIGRATION), []
        )

        inventory = load_json(GOLDEN_MIGRATION / "inventory.json")
        traceability = load_json(GOLDEN_MIGRATION / "traceability.json")
        source_ids = {unit["id"] for unit in inventory["units"]}
        traced_ids = {link["source_unit"] for link in traceability["links"]}
        self.assertEqual(traced_ids, source_ids)

        excepted = [
            link for link in traceability["links"] if link["status"] == "excepted"
        ]
        self.assertEqual(len(excepted), 1)
        self.assertEqual(excepted[0]["source_unit"], "SRC-0005")
        self.assertEqual(excepted[0]["exceptions"], ["EXC-0001"])

    def test_golden_scenario_exercises_slices_resume_divergence_and_recovery(self) -> None:
        fixture = load_json(GOLDEN_ROOT / "fixture.json")
        config = load_json(GOLDEN_MIGRATION / "config.json")
        state = load_json(GOLDEN_MIGRATION / "state.json")
        traceability = load_json(GOLDEN_MIGRATION / "traceability.json")
        decision = load_json(
            GOLDEN_MIGRATION / "decisions" / "DEC-0001.json"
        )
        evidence = [
            load_json(path)
            for path in sorted((GOLDEN_MIGRATION / "evidence").glob("*.json"))
        ]
        plans = [
            load_json(path)
            for path in sorted((GOLDEN_MIGRATION / "plans").glob("*.json"))
        ]

        self.assertEqual(config["migration_strategy"], "incremental")
        self.assertEqual(config["output_profile"], "service")
        self.assertEqual(
            config["project_decisions"]["cutover_mechanism"],
            "route-by-capability",
        )

        self.assertEqual({plan["id"] for plan in plans}, {"SLICE-0001", "SLICE-0002"})
        self.assertTrue(all(plan["release_boundary"] for plan in plans))
        self.assertTrue(all(plan["rollback"] for plan in plans))
        self.assertEqual(set(state["completed_slices"]), {plan["id"] for plan in plans})

        transition_pairs = {
            (transition["from"], transition["to"])
            for transition in state["history"]
        }
        self.assertIn(("characterize", "blocked"), transition_pairs)
        self.assertIn(("blocked", "characterize"), transition_pairs)
        self.assertIn(("execute", "failed"), transition_pairs)
        self.assertIn(("failed", "execute"), transition_pairs)
        self.assertEqual(state["revision"], len(state["history"]) - 1)

        self.assertEqual(decision["affected_contracts"], ["BEH-0002"])
        divergence_link = next(
            link
            for link in traceability["links"]
            if link["source_unit"] == "SRC-0002"
        )
        self.assertIn("DEC-0001", divergence_link["decisions"])

        recovery = [
            item
            for item in evidence
            if item["slice_id"] == "SLICE-0002"
            and item["gate"] == "differential-ordering"
        ]
        self.assertEqual({item["status"] for item in recovery}, {"fail", "pass"})
        self.assertEqual(
            {item["id"] for item in recovery},
            set(divergence_link["evidence"]),
        )

        acceptance = set(fixture["acceptance"])
        self.assertTrue(
            {
                "two-independent-slices",
                "blocked-and-resumed-state",
                "intentional-divergence-record",
                "failure-recovery-evidence",
                "cutover-and-decommission-plan",
            }.issubset(acceptance)
        )


if __name__ == "__main__":
    unittest.main()
