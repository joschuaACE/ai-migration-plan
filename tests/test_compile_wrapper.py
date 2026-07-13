"""Compatibility and safety tests for agents/compile-templates.sh."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPOSITORY_ROOT / "agents" / "compile-templates.sh"


FAKE_FRAMEWORK = textwrap.dedent(
    """\
    import json
    import os
    from pathlib import Path
    import sys

    arguments = sys.argv[1:]
    log_path = os.environ.get("FAKE_ARGUMENT_LOG")
    if log_path:
        Path(log_path).write_text(json.dumps(arguments), encoding="utf-8")

    print("framework-status")
    if os.environ.get("FAKE_FAIL"):
        print("fake compilation failure", file=sys.stderr)
        raise SystemExit(7)

    output_argument = next(
        (argument for argument in arguments if argument.startswith("--output=")),
        None,
    )
    if output_argument is None:
        print("missing --output", file=sys.stderr)
        raise SystemExit(8)
    output = Path(output_argument.split("=", 1)[1])

    if not os.environ.get("FAKE_SKIP_DOCUMENT"):
        workflow = output / "workflows" / os.environ.get(
            "FAKE_WORKFLOW_NAME", "migrate-init.md"
        )
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_bytes(
            os.environ.get("FAKE_DOCUMENT", "compiled workflow\\n").encode("utf-8")
        )
    """
)


class CompileWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.checkout = Path(self.temporary.name) / "checkout with spaces"
        self.agents = self.checkout / "agents"
        self.agents.mkdir(parents=True)
        self.wrapper = self.agents / "compile-templates.sh"
        shutil.copyfile(WRAPPER, self.wrapper)
        (self.agents / "framework.py").write_text(
            FAKE_FRAMEWORK, encoding="utf-8", newline="\n"
        )
        self.argument_log = Path(self.temporary.name) / "arguments.json"
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "FAKE_ARGUMENT_LOG": str(self.argument_log),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )

    def run_wrapper(self, *arguments: str, **environment: str) -> subprocess.CompletedProcess[str]:
        process_environment = self.environment.copy()
        process_environment.update(environment)
        return subprocess.run(
            ["bash", str(self.wrapper), *arguments],
            cwd=self.checkout,
            env=process_environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def logged_arguments(self) -> list[str]:
        return json.loads(self.argument_log.read_text(encoding="utf-8"))

    def logged_option(self, name: str) -> str:
        prefix = f"--{name}="
        match = next(
            argument
            for argument in self.logged_arguments()
            if argument.startswith(prefix)
        )
        return match.split("=", 1)[1]

    def test_bundle_form_delegates_to_framework_with_default_output(self) -> None:
        result = self.run_wrapper("cpp-to-java-25")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "framework-status\n")
        self.assertEqual(
            self.logged_arguments(),
            [
                "compile",
                "--pair=cpp-to-java-25",
                f"--output={self.checkout / 'compiled'}",
            ],
        )

    def test_bundle_form_preserves_quoted_output_and_accepts_options_anywhere(self) -> None:
        output = Path(self.temporary.name) / "bundle output [one]"
        result = self.run_wrapper(
            "--adapter",
            "codex",
            "cpp-to-java-25",
            str(output),
            "--output-profile=library",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.logged_arguments(),
            [
                "compile",
                "--pair=cpp-to-java-25",
                f"--output={output}",
                "--output-profile=library",
                "--adapter=codex",
            ],
        )

    def test_bundle_pair_aliases_are_normalized(self) -> None:
        aliases = {
            "cpp-java25": "cpp-to-java-25",
            "cpp-to-java25": "cpp-to-java-25",
            "example-to-java25": "example-to-java-25",
        }
        for alias, expected in aliases.items():
            with self.subTest(alias=alias):
                result = self.run_wrapper(alias, str(self.checkout / alias))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.logged_option("pair"), expected)

    def test_shell_metacharacters_are_passed_literally_and_never_evaluated(self) -> None:
        marker = Path(self.temporary.name) / "must-not-exist"
        pair = f"$(touch {marker})"
        result = self.run_wrapper(pair, str(self.checkout / "output"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.logged_option("pair"), pair)
        self.assertFalse(marker.exists())

    def test_legacy_form_normalizes_target_and_prints_only_selected_document(self) -> None:
        content = "# Compiled\n\nGrüße — exact bytes"
        result = self.run_wrapper(
            "cpp",
            "java25",
            "docs/skills/migrate-init.md",
            FAKE_DOCUMENT=content,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, content)
        arguments = self.logged_arguments()
        self.assertEqual(arguments[0:2], ["compile", "--pair=cpp-to-java-25"])
        temporary_bundle = Path(self.logged_option("output"))
        self.assertFalse(temporary_bundle.exists(), "legacy staging directory was not cleaned")

    def test_legacy_form_forwards_profile_and_adapter(self) -> None:
        result = self.run_wrapper(
            "--output-profile",
            "cli",
            "cpp",
            "java-25",
            "docs/skills/migrate-init.md",
            "--adapter=kiro",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = self.logged_arguments()
        self.assertEqual(self.logged_option("pair"), "cpp-to-java-25")
        self.assertEqual(arguments[-2:], ["--output-profile=cli", "--adapter=kiro"])

    def test_legacy_failure_never_leaks_framework_status_or_document(self) -> None:
        result = self.run_wrapper(
            "cpp",
            "java25",
            "docs/skills/migrate-init.md",
            FAKE_FAIL="1",
            FAKE_DOCUMENT="must not be printed",
        )

        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout, "")
        self.assertIn("fake compilation failure", result.stderr)
        temporary_bundle = Path(self.logged_option("output"))
        self.assertFalse(temporary_bundle.exists())

    def test_legacy_missing_selected_document_is_an_error_without_partial_stdout(self) -> None:
        result = self.run_wrapper(
            "cpp",
            "java25",
            "docs/skills/migrate-init.md",
            FAKE_SKIP_DOCUMENT="1",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("selected workflow was not generated", result.stderr)

    def test_legacy_document_must_be_a_safe_direct_workflow_path(self) -> None:
        invalid_paths = (
            "/docs/skills/migrate-init.md",
            "docs/skills/../hooks/migration-quality.md",
            "docs/hooks/migration-quality.md",
            "docs/skills/nested/migrate-init.md",
        )
        for document in invalid_paths:
            with self.subTest(document=document):
                self.argument_log.unlink(missing_ok=True)
                result = self.run_wrapper("cpp", "java25", document)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertFalse(self.argument_log.exists())

    def test_invalid_arity_and_unknown_options_fail_before_framework(self) -> None:
        invocations = (
            (),
            ("one", "two", "three", "four"),
            ("--unknown",),
            ("--adapter",),
            ("--output-profile=", "cpp-to-java-25"),
        )
        for arguments in invocations:
            with self.subTest(arguments=arguments):
                self.argument_log.unlink(missing_ok=True)
                result = self.run_wrapper(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Usage:", result.stderr)
                self.assertFalse(self.argument_log.exists())

    def test_duplicate_options_are_rejected(self) -> None:
        result = self.run_wrapper(
            "cpp-to-java-25",
            "--adapter",
            "codex",
            "--adapter=kiro",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("only once", result.stderr)
        self.assertFalse(self.argument_log.exists())

    def test_double_dash_allows_an_output_path_that_starts_with_dash(self) -> None:
        result = self.run_wrapper("--", "cpp-to-java-25", "-bundle")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.logged_option("output"), "-bundle")

    def test_help_does_not_invoke_framework(self) -> None:
        result = self.run_wrapper("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("compile-templates.sh PAIR_ID", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertFalse(self.argument_log.exists())


if __name__ == "__main__":
    unittest.main()
