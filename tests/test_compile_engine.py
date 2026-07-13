"""Unit tests for the strict migration-framework template compiler."""

from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = REPOSITORY_ROOT / "agents" / "compile-engine.py"
SPEC = importlib.util.spec_from_file_location("migration_compile_engine", ENGINE_PATH)
assert SPEC is not None and SPEC.loader is not None
ENGINE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ENGINE
SPEC.loader.exec_module(ENGINE)

TemplateEngine = ENGINE.TemplateEngine
TemplateError = ENGINE.TemplateError


class EngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "docs"
        self.root.mkdir()

    def engine(self, variables=None, **kwargs):
        return TemplateEngine(variables or {}, self.root, **kwargs)

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
        return path


class VariableTests(EngineTestCase):
    def test_substitutes_supported_scalar_values_deterministically(self) -> None:
        engine = self.engine(
            {
                "text": "Grüße",
                "integer": 25,
                "decimal": 2.5,
                "enabled": True,
                "disabled": False,
                "nothing": None,
            }
        )
        rendered = engine.render(
            "{{text}}|{{integer}}|{{decimal}}|{{enabled}}|{{disabled}}|{{nothing}}"
        )
        self.assertEqual(rendered, "Grüße|25|2.5|true|false|null")

    def test_unknown_variable_is_fatal_with_location(self) -> None:
        with self.assertRaisesRegex(
            TemplateError, r"example\.md:2:8: unknown template variable 'missing'"
        ):
            self.engine().render("first\nvalue: {{missing}}", source_path="example.md")

    def test_unknown_variable_in_inactive_branch_is_fatal(self) -> None:
        template = (
            "{{#if selected == 'yes'}}ok"
            "{{#else}}{{misspelled}}{{/if}}"
        )
        with self.assertRaisesRegex(TemplateError, "misspelled"):
            self.engine({"selected": "yes"}).render(template)

    def test_non_scalar_substitution_is_fatal(self) -> None:
        for value in (["one"], {"nested": "value"}, ("tuple",)):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TemplateError, "must be a scalar"):
                    self.engine({"value": value}).render("{{value}}")

    def test_non_finite_float_is_fatal(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TemplateError, "not a finite scalar"):
                    self.engine({"value": value}).render("{{value}}")

    def test_variable_cannot_inject_an_unresolved_directive(self) -> None:
        with self.assertRaisesRegex(TemplateError, "unresolved template token"):
            self.engine({"value": "{{other}}"}).render("{{value}}")

    def test_rejects_a_non_mapping_variable_container(self) -> None:
        with self.assertRaisesRegex(TypeError, "variables must be a mapping"):
            TemplateEngine([("name", "value")], self.root)


class ConditionalTests(EngineTestCase):
    def test_nested_conditionals_and_else_render_the_selected_branches(self) -> None:
        template = (
            "before\n"
            "{{#if language == 'java'}}"
            "java-"
            "{{#if profile != \"service\"}}library{{#else}}service{{/if}}"
            "{{#else}}other{{/if}}"
            "\nafter"
        )
        engine = self.engine({"language": "java", "profile": "library"})
        self.assertEqual(engine.render(template), "before\njava-library\nafter")

    def test_false_branch_without_else_is_empty(self) -> None:
        engine = self.engine({"language": "cpp"})
        self.assertEqual(
            engine.render("a{{#if language == 'java'}}x{{/if}}b"), "ab"
        )

    def test_escaped_conditional_literal_is_supported(self) -> None:
        engine = self.engine({"answer": "it's ready"})
        self.assertEqual(
            engine.render(r"{{#if answer == 'it\'s ready'}}yes{{/if}}"), "yes"
        )

    def test_malformed_conditional_is_fatal(self) -> None:
        malformed = (
            "{{#if language}}x{{/if}}",
            "{{#if language = 'java'}}x{{/if}}",
            "{{#if 12bad == 'java'}}x{{/if}}",
            "{{#unless language == 'java'}}x{{/if}}",
        )
        for template in malformed:
            with self.subTest(template=template):
                with self.assertRaises(TemplateError):
                    self.engine({"language": "java"}).render(template)

    def test_missing_close_is_fatal(self) -> None:
        with self.assertRaisesRegex(TemplateError, "missing.*if"):
            self.engine({"x": "y"}).render("{{#if x == 'y'}}yes")

    def test_unmatched_else_and_close_are_fatal(self) -> None:
        for template in ("{{#else}}", "{{/if}}"):
            with self.subTest(template=template):
                with self.assertRaisesRegex(TemplateError, "without a matching"):
                    self.engine().render(template)

    def test_duplicate_else_is_fatal(self) -> None:
        template = (
            "{{#if x == 'y'}}one{{#else}}two{{#else}}three{{/if}}"
        )
        with self.assertRaisesRegex(TemplateError, "more than one"):
            self.engine({"x": "y"}).render(template)

    def test_conditional_nesting_depth_is_bounded(self) -> None:
        count = 129
        template = "{{#if x == 'y'}}" * count + "yes" + "{{/if}}" * count
        with self.assertRaisesRegex(TemplateError, "conditional nesting depth"):
            self.engine({"x": "y"}).render(template)

    def test_unterminated_and_empty_directives_are_fatal(self) -> None:
        for template, message in (
            ("prefix {{value", "unterminated"),
            ("prefix {{}}", "empty"),
            ("prefix {{{{value}}", "nested"),
            ("prefix {{value\n}}", "one line"),
        ):
            with self.subTest(template=template):
                with self.assertRaisesRegex(TemplateError, message):
                    self.engine({"value": "ok"}).render(template)


class IncludeTests(EngineTestCase):
    def test_resolves_include_variables_and_prefers_standards_directory(self) -> None:
        self.write("partials/item.md", "root")
        self.write("standards/partials/item.md", "standard {{value}}")
        engine = self.engine({"folder": "partials", "value": "result"})
        rendered = engine.render("A {{> {{folder}}/item.md}} B")
        self.assertEqual(rendered, "A standard result B")

    def test_nested_includes_are_rendered_recursively(self) -> None:
        self.write("one.md", "one({{> two.md}})")
        self.write("two.md", "two({{name}})")
        self.assertEqual(
            self.engine({"name": "three"}).render("{{> one.md}}"),
            "one(two(three))",
        )

    def test_inactive_include_does_not_have_to_exist(self) -> None:
        template = "{{#if enabled == 'true'}}{{> missing.md}}{{#else}}ok{{/if}}"
        self.assertEqual(self.engine({"enabled": False}).render(template), "ok")

    def test_unknown_variable_in_inactive_include_path_is_fatal(self) -> None:
        template = (
            "{{#if enabled == 'true'}}"
            "{{> {{unknown}}/missing.md}}"
            "{{#else}}ok{{/if}}"
        )
        with self.assertRaisesRegex(TemplateError, "unknown"):
            self.engine({"enabled": False}).render(template)

    def test_unsafe_or_malformed_inactive_include_is_still_fatal(self) -> None:
        references = ("../secret.md", "/etc/passwd", "file.md#one#two")
        for reference in references:
            template = (
                "{{#if enabled == 'true'}}{{> "
                + reference
                + "}}{{#else}}ok{{/if}}"
            )
            with self.subTest(reference=reference):
                with self.assertRaises(TemplateError):
                    self.engine({"enabled": False}).render(template)

    def test_missing_file_is_fatal(self) -> None:
        with self.assertRaisesRegex(TemplateError, "included file not found"):
            self.engine().render("{{> no-such-file.md}}")

    def test_absolute_and_traversal_paths_are_fatal(self) -> None:
        paths = (
            "/etc/passwd",
            "../secret.md",
            "directory/../secret.md",
            "C:\\Windows\\system.ini",
        )
        for path in paths:
            with self.subTest(path=path):
                with self.assertRaises(TemplateError):
                    self.engine().render("{{> " + path + "}}")

    def test_variable_cannot_inject_path_traversal(self) -> None:
        with self.assertRaisesRegex(TemplateError, "traversal"):
            self.engine({"directory": ".."}).render(
                "{{> {{directory}}/secret.md}}"
            )

    def test_symlink_escape_is_fatal(self) -> None:
        outside = Path(self.temporary.name) / "secret.md"
        outside.write_text("secret", encoding="utf-8")
        link = self.root / "escape.md"
        try:
            link.symlink_to(outside)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"symlinks unavailable: {error}")
        with self.assertRaisesRegex(TemplateError, "escapes docs root"):
            self.engine().render("{{> escape.md}}")

    def test_include_cycle_reports_the_chain(self) -> None:
        self.write("a.md", "{{> b.md}}")
        self.write("b.md", "{{> a.md}}")
        with self.assertRaisesRegex(TemplateError, r"cycle.*a\.md.*b\.md.*a\.md"):
            self.engine().render_file(self.root / "a.md")

    def test_include_depth_is_bounded(self) -> None:
        self.write("a.md", "{{> b.md}}")
        self.write("b.md", "{{> c.md}}")
        self.write("c.md", "done")
        with self.assertRaisesRegex(TemplateError, r"maximum include depth \(1\)"):
            self.engine(max_include_depth=1).render("{{> a.md}}")

    def test_invalid_depth_is_rejected(self) -> None:
        for depth in (0, -1, False, 1.5, "2"):
            with self.subTest(depth=depth):
                with self.assertRaises(ValueError):
                    self.engine(max_include_depth=depth)

    def test_malformed_include_directives_are_fatal(self) -> None:
        malformed = (
            "{{> }}",
            "{{> file.md#one#two}}",
            "{{> file.md# }}",
            "{{> {{#if x == 'y'}}/file.md}}",
        )
        for template in malformed:
            with self.subTest(template=template):
                with self.assertRaises(TemplateError):
                    self.engine({"x": "y"}).render(template)


class SectionTests(EngineTestCase):
    def test_extracts_only_an_exact_section_without_its_heading(self) -> None:
        self.write(
            "guide.md",
            "# Guide\nintro\n\n## Build System Detection\n"
            "body {{value}}\n### Detail\nmore\n## Next\nlater\n",
        )
        rendered = self.engine({"value": "compiled"}).render(
            "{{> guide.md#build-system-detection}}"
        )
        self.assertEqual(rendered, "body compiled\n### Detail\nmore")

    def test_section_anchor_is_not_a_substring_or_case_insensitive_match(self) -> None:
        self.write("guide.md", "## Build System Detection\nbody\n")
        for anchor in ("system-detection", "Build-System-Detection"):
            with self.subTest(anchor=anchor):
                with self.assertRaisesRegex(TemplateError, "section.*not found"):
                    self.engine().render("{{> guide.md#" + anchor + "}}")

    def test_missing_and_ambiguous_sections_are_fatal(self) -> None:
        self.write("guide.md", "## Same\none\n## Same\ntwo\n")
        with self.assertRaisesRegex(TemplateError, "not found"):
            self.engine().render("{{> guide.md#missing}}")
        with self.assertRaisesRegex(TemplateError, "ambiguous"):
            self.engine().render("{{> guide.md#same}}")

    def test_headings_inside_code_fences_are_not_sections(self) -> None:
        self.write("guide.md", "```markdown\n## Fake\ntext\n```\n")
        with self.assertRaisesRegex(TemplateError, "not found"):
            self.engine().render("{{> guide.md#fake}}")


class FileAndCompatibilityTests(EngineTestCase):
    def test_compile_file_normalizes_newlines_and_writes_utf8(self) -> None:
        source = Path(self.temporary.name) / "input.md"
        destination = Path(self.temporary.name) / "nested" / "output.md"
        second_destination = Path(self.temporary.name) / "other" / "output.md"
        source.write_bytes("héllo\r\n{{name}}\rline\n".encode("utf-8"))
        engine = self.engine({"name": "世界"})
        engine.compile_file(source, destination)
        engine.compile_file(source, second_destination)
        self.assertEqual(destination.read_bytes(), "héllo\n世界\nline\n".encode("utf-8"))
        self.assertEqual(destination.read_bytes(), second_destination.read_bytes())
        self.assertEqual(list(destination.parent.glob(".output.md.*.tmp")), [])

    def test_failed_compilation_does_not_replace_destination(self) -> None:
        source = Path(self.temporary.name) / "input.md"
        destination = Path(self.temporary.name) / "output.md"
        source.write_text("{{missing}}", encoding="utf-8")
        destination.write_text("keep me", encoding="utf-8")
        with self.assertRaises(TemplateError):
            self.engine().compile_file(source, destination)
        self.assertEqual(destination.read_text(encoding="utf-8"), "keep me")

    def test_missing_docs_root_is_fatal(self) -> None:
        with self.assertRaisesRegex(TemplateError, "docs root cannot be resolved"):
            TemplateEngine({}, self.root / "missing")

    def test_legacy_two_argument_cli_uses_environment_pair(self) -> None:
        toolkit = Path(self.temporary.name) / "toolkit"
        docs = toolkit / "docs"
        (docs / "templates").mkdir(parents=True)
        variables = {"pairs": {"cpp-to-java": {"language": "Java 25"}}}
        (docs / "templates" / "variables.json").write_text(
            json.dumps(variables), encoding="utf-8"
        )
        source = toolkit / "source.md"
        destination = toolkit / "generated" / "output.md"
        source.write_bytes(b"Target: {{language}}\r\n")
        environment = os.environ.copy()
        environment.update(
            {"TOOLKIT_DIR": str(toolkit), "PAIR_ID": "cpp-to-java"}
        )

        result = subprocess.run(
            [sys.executable, str(ENGINE_PATH), str(source), str(destination)],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(destination.read_bytes(), b"Target: Java 25\n")

    def test_legacy_cli_reports_unknown_pair_without_traceback(self) -> None:
        toolkit = Path(self.temporary.name) / "toolkit"
        variables_file = toolkit / "docs" / "templates" / "variables.json"
        variables_file.parent.mkdir(parents=True)
        variables_file.write_text('{"pairs": {}}', encoding="utf-8")
        source = toolkit / "source.md"
        source.write_text("plain", encoding="utf-8")
        destination = toolkit / "output.md"
        environment = os.environ.copy()
        environment.update({"TOOLKIT_DIR": str(toolkit), "PAIR_ID": "missing"})

        result = subprocess.run(
            [sys.executable, str(ENGINE_PATH), str(source), str(destination)],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("pair_id 'missing' not found", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
