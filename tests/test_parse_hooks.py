#!/usr/bin/env python3
"""Conformance and security tests for the portable hook compiler."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PARSER = REPO_ROOT / "agents" / "parse-hooks.sh"


VALID_HOOKS = """
# Hooks

## compile-on-save

- trigger: file-save
- matcher: {target_root}/src/.*
- type: command
- command: cd {target_root} && ./gradlew compileJava
- timeout: 30
- required: true
- enforcement: deterministic
- description: Compile changed target code

## domain-review

- trigger: file-create
- matcher: {target_root}/src/.*/domain/.*
- type: agent
- prompt: Check the new domain file for framework imports.
- forbidden_imports: org.springframework.*, jakarta.persistence.*
- required: false
- enforcement: judgment
- description: Review domain purity
"""


EXACT_HOOKS = """
# Hooks

## preflight

- trigger: pre-tool
- matcher: Bash
- type: command
- command: ./scripts/preflight
- timeout: 1
- required: true
- enforcement: deterministic
- description: Validate a tool call

## completion-review

- trigger: stop
- matcher: .*
- type: agent
- prompt: Confirm that the migration slice is complete.
- required: false
- enforcement: judgment
- description: Review completion
"""


class ParseHooksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="parse-hooks-test-")
        self.hooks_dir = Path(self.temp_dir.name) / "hooks"
        self.hooks_dir.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write(self, content: str, name: str = "hooks.md") -> Path:
        path = self.hooks_dir / name
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
        return path

    def run_parser(
        self,
        agent: str,
        *extra: str,
        target_root: str = "app",
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            "bash",
            str(PARSER),
            agent,
            str(self.hooks_dir),
            target_root,
            *extra,
        ]
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=merged_env,
            check=False,
            capture_output=True,
            text=True,
        )

    def assert_error(self, result: subprocess.CompletedProcess[str], text: str) -> None:
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn(text, result.stderr)

    def test_kiro_emits_both_native_hook_types(self) -> None:
        self.write(VALID_HOOKS)
        result = self.run_parser("kiro")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)

        self.assertEqual(output["version"], "v1")
        self.assertNotIn("_migration_framework", output)
        self.assertEqual([hook["name"] for hook in output["hooks"]], [
            "compile-on-save",
            "domain-review",
        ])
        self.assertEqual(output["hooks"][0]["matcher"], "app/src/.*")
        self.assertEqual(output["hooks"][0]["action"]["type"], "command")
        self.assertEqual(output["hooks"][1]["action"]["type"], "agent")
        self.assertIn("forbidden_imports", output["hooks"][1]["action"]["prompt"])

    def test_claude_marks_file_events_as_approximate_and_uses_agent_handler(self) -> None:
        self.write(VALID_HOOKS)
        result = self.run_parser("claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)

        groups = output["hooks"]["PostToolUse"]
        self.assertEqual([group["matcher"] for group in groups], [
            "Write|Edit",
            "Write|Edit",
        ])
        self.assertEqual(groups[0]["hooks"][0]["type"], "command")
        self.assertEqual(groups[1]["hooks"][0]["type"], "agent")
        self.assertIn("$ARGUMENTS", groups[1]["hooks"][0]["prompt"])
        warnings = output["_migration_framework"]["warnings"]
        self.assertEqual(len(warnings), 3)
        self.assertEqual(
            {item["code"] for item in warnings},
            {"approximate-trigger", "experimental-hook-type"},
        )
        self.assertTrue(
            all(item["source"] in {"hooks.md:3", "hooks.md:14"} for item in warnings)
        )

    def test_codex_omits_agent_hook_instead_of_faking_command_enforcement(self) -> None:
        self.write(VALID_HOOKS)
        result = self.run_parser("codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)

        groups = output["hooks"]["PostToolUse"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["hooks"][0]["type"], "command")
        self.assertNotIn("echo", groups[0]["hooks"][0]["command"])
        instructions = output["_migration_framework"]["instructions"]
        self.assertEqual([item["hook"] for item in instructions], ["domain-review"])
        self.assertIn("only command handlers execute", instructions[0]["reason"])
        self.assertTrue(output["_migration_framework"]["activation_requirements"])

    def test_output_is_byte_deterministic(self) -> None:
        self.write(VALID_HOOKS)
        first = self.run_parser("codex")
        second = self.run_parser("codex")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertNotIn(self.temp_dir.name, first.stdout)

    def test_strict_mode_accepts_exact_kiro_capabilities(self) -> None:
        self.write(EXACT_HOOKS)
        result = self.run_parser("kiro", "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["hooks"][0]["timeout"], 1)

    def test_strict_mode_rejects_approximate_and_unsupported_capabilities(self) -> None:
        self.write(VALID_HOOKS)
        self.assert_error(self.run_parser("claude", "--strict"), "strict capability check failed")

        self.hooks_dir.joinpath("hooks.md").write_text(
            textwrap.dedent(EXACT_HOOKS).lstrip(), encoding="utf-8"
        )
        self.assert_error(self.run_parser("codex", "--strict"), "only command handlers execute")

    def test_strict_mode_environment_variable_is_supported(self) -> None:
        self.write(VALID_HOOKS)
        result = self.run_parser("claude", env={"MIGRATION_HOOK_STRICT": "true"})
        self.assert_error(result, "strict capability check failed")

    def test_event_specific_type_capability_becomes_an_instruction(self) -> None:
        self.write(
            """
            ## startup-review
            - trigger: session-start
            - matcher: .*
            - type: agent
            - prompt: Review migration state before work begins.
            - required: false
            - enforcement: judgment
            - description: Review startup state
            """
        )
        result = self.run_parser("claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["hooks"], {})
        instructions = output["_migration_framework"]["instructions"]
        self.assertEqual(instructions[0]["hook"], "startup-review")
        self.assertIn("does not support agent handlers", instructions[0]["reason"])

    def test_rejects_missing_fields_invalid_values_and_malformed_lines(self) -> None:
        cases = {
            "missing required fields": """
                ## broken
                - trigger: stop
                - matcher: .*
                - type: command
                - command: true
                - required: true
                - enforcement: deterministic
            """,
            "unsupported trigger": """
                ## broken
                - trigger: sometimes
                - matcher: .*
                - type: command
                - command: true
                - required: true
                - enforcement: deterministic
                - description: Broken
            """,
            "unsupported hook type": """
                ## broken
                - trigger: stop
                - matcher: .*
                - type: shell
                - command: true
                - required: true
                - enforcement: deterministic
                - description: Broken
            """,
            "timeout must be an integer": """
                ## broken
                - trigger: stop
                - matcher: .*
                - type: command
                - command: true
                - timeout: fast
                - required: true
                - enforcement: deterministic
                - description: Broken
            """,
            "malformed field": """
                ## broken
                - trigger: stop
                - matcher: .*
                - type: command
                - command: true
                - required: true
                - enforcement: deterministic
                - description Broken
            """,
            "valid regular expression": """
                ## broken
                - trigger: stop
                - matcher: [
                - type: command
                - command: true
                - required: true
                - enforcement: deterministic
                - description: Broken
            """,
        }
        for index, (expected, content) in enumerate(cases.items()):
            with self.subTest(expected=expected):
                for path in self.hooks_dir.glob("*.md"):
                    path.unlink()
                self.write(content, f"case-{index}.md")
                self.assert_error(self.run_parser("kiro"), expected)

    def test_rejects_duplicate_names_and_fields(self) -> None:
        self.write(EXACT_HOOKS, "one.md")
        self.write(EXACT_HOOKS, "two.md")
        self.assert_error(self.run_parser("kiro"), "duplicate hook name")

        for path in self.hooks_dir.glob("*.md"):
            path.unlink()
        self.write(
            """
            ## duplicate-field
            - trigger: stop
            - trigger: pre-tool
            - matcher: .*
            - type: command
            - command: true
            - required: true
            - enforcement: deterministic
            - description: Broken
            """
        )
        self.assert_error(self.run_parser("kiro"), "duplicate field 'trigger'")

    def test_rejects_hook_definition_symlinks(self) -> None:
        outside = Path(self.temp_dir.name) / "outside.md"
        outside.write_text(textwrap.dedent(EXACT_HOOKS).lstrip(), encoding="utf-8")
        self.hooks_dir.joinpath("linked.md").symlink_to(outside)
        self.assert_error(self.run_parser("kiro"), "symlinks are not allowed")

    def test_rejects_unresolved_tokens(self) -> None:
        self.write(
            """
            ## unresolved
            - trigger: stop
            - matcher: .*
            - type: command
            - command: {{compile_command}}
            - required: true
            - enforcement: deterministic
            - description: Broken
            """
        )
        self.assert_error(self.run_parser("kiro"), "unresolved template token")

        self.hooks_dir.joinpath("hooks.md").write_text(
            textwrap.dedent(EXACT_HOOKS).replace(
                "./scripts/preflight", "{{compile_command"
            ).lstrip(),
            encoding="utf-8",
        )
        self.assert_error(self.run_parser("kiro"), "unresolved template token")

    def test_rejects_out_of_range_timeouts_and_invalid_policy_fields(self) -> None:
        for timeout in ("0", "3601"):
            with self.subTest(timeout=timeout):
                self.write(EXACT_HOOKS.replace("- timeout: 1", f"- timeout: {timeout}"))
                self.assert_error(self.run_parser("kiro"), "between 1 and 3600")

        invalid_fields = {
            "required must be the boolean": EXACT_HOOKS.replace(
                "- required: true", "- required: yes"
            ),
            "require enforcement: deterministic": EXACT_HOOKS.replace(
                "- enforcement: deterministic", "- enforcement: judgment"
            ),
        }
        for expected, content in invalid_fields.items():
            with self.subTest(expected=expected):
                self.write(content)
                self.assert_error(self.run_parser("kiro"), expected)

    def test_commands_are_escaped_as_data_and_never_executed_by_the_parser(self) -> None:
        self.write(
            """
            ## quoted-command
            - trigger: pre-tool
            - matcher: Bash
            - type: command
            - command: printf '\"$PARSE_HOOK_SENTINEL\"' && cd {target_root}
            - required: true
            - enforcement: deterministic
            - description: Preserve shell syntax
            """
        )
        result = self.run_parser("kiro", target_root="safe/nested")
        self.assertEqual(result.returncode, 0, result.stderr)
        command = json.loads(result.stdout)["hooks"][0]["action"]["command"]
        self.assertEqual(
            command,
            "printf '\"$PARSE_HOOK_SENTINEL\"' && cd safe/nested",
        )

    def test_rejects_unsafe_target_roots(self) -> None:
        self.write(EXACT_HOOKS)
        for target_root in (
            "../app",
            "/tmp/app",
            "app; touch bad",
            "app/$HOME",
            "-P",
        ):
            with self.subTest(target_root=target_root):
                self.assert_error(
                    self.run_parser("kiro", target_root=target_root),
                    "unsafe target_root",
                )


if __name__ == "__main__":
    unittest.main()
