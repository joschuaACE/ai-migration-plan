#!/usr/bin/env python3
"""Strict, deterministic template compiler for migration framework documents.

Supported directives are deliberately small:

* ``{{variable_name}}``
* ``{{#if variable_name == 'value'}} ... {{#else}} ... {{/if}}``
* ``{{> relative/path.md#optional-section-anchor}}``

Includes are resolved below a configured ``docs_root``.  For compatibility with
the original templates, ``standards/`` is searched before the root itself.

The module API is :class:`TemplateEngine` and :class:`TemplateError`.  The
two-positional-argument command line interface remains compatible with the
legacy shell compiler and loads its variables from ``TOOLKIT_DIR``, ``PAIR_ID``
and ``docs/templates/variables.json``.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
import tempfile
from typing import TypeAlias


__all__ = ("TemplateEngine", "TemplateError", "compile_file", "load_pair_variables")


_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_.-]*"
_IDENTIFIER_RE = re.compile(rf"^{_IDENTIFIER}$")
_CONDITION_RE = re.compile(
    rf"^#if\s+({_IDENTIFIER})\s*(==|!=)\s*"
    r"('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")$"
)
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_MAX_CONDITIONAL_DEPTH = 128


class TemplateError(ValueError):
    """Raised when a template cannot be compiled safely and completely."""

    def __init__(
        self,
        message: str,
        *,
        source: str | os.PathLike[str] | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        self.message = message
        self.source = str(source) if source is not None else None
        self.line = line
        self.column = column
        super().__init__(self.__str__())

    def __str__(self) -> str:
        location = self.source or "<template>"
        if self.line is not None:
            location += f":{self.line}"
            if self.column is not None:
                location += f":{self.column}"
        return f"{location}: {self.message}"


@dataclass(frozen=True)
class _Directive:
    content: str
    offset: int
    line: int
    column: int


@dataclass(frozen=True)
class _Text:
    value: str


@dataclass(frozen=True)
class _Variable:
    name: str
    directive: _Directive


@dataclass(frozen=True)
class _Include:
    reference: str
    directive: _Directive


@dataclass(frozen=True)
class _Conditional:
    name: str
    operator: str
    expected: str
    when_true: tuple["_Node", ...]
    when_false: tuple["_Node", ...]
    directive: _Directive


_Node: TypeAlias = _Text | _Variable | _Include | _Conditional
_Lexeme: TypeAlias = _Text | _Directive


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _line_and_column(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    previous_newline = text.rfind("\n", 0, offset)
    column = offset + 1 if previous_newline < 0 else offset - previous_newline
    return line, column


def _directive_error(
    message: str, directive: _Directive, source: str | os.PathLike[str] | None
) -> TemplateError:
    return TemplateError(
        message,
        source=source,
        line=directive.line,
        column=directive.column,
    )


def _find_include_end(
    text: str, start: int, source: str | os.PathLike[str] | None
) -> int:
    """Find an include's outer ``}}``, skipping nested variable tokens."""

    position = start + 3
    while position < len(text):
        nested_start = text.find("{{", position)
        close = text.find("}}", position)
        if close < 0:
            line, column = _line_and_column(text, start)
            raise TemplateError(
                "unterminated include directive",
                source=source,
                line=line,
                column=column,
            )
        if 0 <= nested_start < close:
            nested_close = text.find("}}", nested_start + 2)
            if nested_close < 0:
                line, column = _line_and_column(text, nested_start)
                raise TemplateError(
                    "unterminated variable in include path",
                    source=source,
                    line=line,
                    column=column,
                )
            nested_content = text[nested_start + 2 : nested_close].strip()
            if not _IDENTIFIER_RE.fullmatch(nested_content):
                line, column = _line_and_column(text, nested_start)
                raise TemplateError(
                    "include paths may contain only simple variable directives",
                    source=source,
                    line=line,
                    column=column,
                )
            position = nested_close + 2
            continue
        return close

    line, column = _line_and_column(text, start)
    raise TemplateError(
        "unterminated include directive",
        source=source,
        line=line,
        column=column,
    )


def _lex(
    text: str, source: str | os.PathLike[str] | None
) -> tuple[_Lexeme, ...]:
    lexemes: list[_Lexeme] = []
    position = 0

    while position < len(text):
        start = text.find("{{", position)
        if start < 0:
            lexemes.append(_Text(text[position:]))
            break
        if start > position:
            lexemes.append(_Text(text[position:start]))

        if text.startswith("{{>", start):
            close = _find_include_end(text, start, source)
        else:
            close = text.find("}}", start + 2)
            nested = text.find("{{", start + 2, close if close >= 0 else None)
            if nested >= 0:
                line, column = _line_and_column(text, nested)
                raise TemplateError(
                    "nested template directive is not allowed here",
                    source=source,
                    line=line,
                    column=column,
                )
            if close < 0:
                line, column = _line_and_column(text, start)
                raise TemplateError(
                    "unterminated template directive",
                    source=source,
                    line=line,
                    column=column,
                )

        line, column = _line_and_column(text, start)
        raw_content = text[start + 2 : close]
        content = raw_content.strip()
        if not content:
            raise TemplateError(
                "empty template directive",
                source=source,
                line=line,
                column=column,
            )
        if "\n" in raw_content:
            raise TemplateError(
                "template directives must fit on one line",
                source=source,
                line=line,
                column=column,
            )
        lexemes.append(_Directive(content, start, line, column))
        position = close + 2
    return tuple(lexemes)


class _Parser:
    def __init__(
        self,
        lexemes: tuple[_Lexeme, ...],
        source: str | os.PathLike[str] | None,
    ) -> None:
        self.lexemes = lexemes
        self.source = source
        self.position = 0

    def parse(self) -> tuple[_Node, ...]:
        nodes, terminator = self._parse_sequence(depth=0)
        if terminator is not None:
            if terminator.content == "#else":
                message = "{{#else}} without a matching {{#if}}"
            else:
                message = "{{/if}} without a matching {{#if}}"
            raise _directive_error(message, terminator, self.source)
        return nodes

    def _parse_sequence(
        self, *, depth: int
    ) -> tuple[tuple[_Node, ...], _Directive | None]:
        nodes: list[_Node] = []
        while self.position < len(self.lexemes):
            lexeme = self.lexemes[self.position]
            self.position += 1
            if isinstance(lexeme, _Text):
                nodes.append(lexeme)
                continue

            content = lexeme.content
            if content in {"#else", "/if"}:
                return tuple(nodes), lexeme

            condition_match = _CONDITION_RE.fullmatch(content)
            if condition_match:
                if depth >= _MAX_CONDITIONAL_DEPTH:
                    raise _directive_error(
                        f"maximum conditional nesting depth "
                        f"({_MAX_CONDITIONAL_DEPTH}) exceeded",
                        lexeme,
                        self.source,
                    )
                name, operator, literal = condition_match.groups()
                try:
                    expected = ast.literal_eval(literal)
                except (SyntaxError, ValueError) as error:
                    raise _directive_error(
                        f"invalid conditional string literal: {error}",
                        lexeme,
                        self.source,
                    ) from error
                if not isinstance(expected, str):
                    raise _directive_error(
                        "conditional comparison value must be a string",
                        lexeme,
                        self.source,
                    )

                when_true, terminator = self._parse_sequence(depth=depth + 1)
                if terminator is None:
                    raise _directive_error(
                        "conditional is missing {{/if}}", lexeme, self.source
                    )
                when_false: tuple[_Node, ...] = ()
                if terminator.content == "#else":
                    when_false, terminator = self._parse_sequence(depth=depth + 1)
                    if terminator is None:
                        raise _directive_error(
                            "conditional {{#else}} branch is missing {{/if}}",
                            lexeme,
                            self.source,
                        )
                    if terminator.content == "#else":
                        raise _directive_error(
                            "conditional contains more than one {{#else}}",
                            terminator,
                            self.source,
                        )
                if terminator.content != "/if":
                    raise _directive_error(
                        "conditional is missing {{/if}}", lexeme, self.source
                    )

                nodes.append(
                    _Conditional(
                        name,
                        operator,
                        expected,
                        when_true,
                        when_false,
                        lexeme,
                    )
                )
                continue

            if content.startswith("#if"):
                raise _directive_error(
                    "malformed conditional; expected "
                    "{{#if variable == 'value'}}",
                    lexeme,
                    self.source,
                )
            if content.startswith("#") or content.startswith("/"):
                raise _directive_error(
                    f"unsupported control directive '{{{{{content}}}}}'",
                    lexeme,
                    self.source,
                )
            if content.startswith(">"):
                reference = content[1:].strip()
                if not reference:
                    raise _directive_error(
                        "include directive requires a path", lexeme, self.source
                    )
                nodes.append(_Include(reference, lexeme))
                continue
            if not _IDENTIFIER_RE.fullmatch(content):
                raise _directive_error(
                    f"malformed or unsupported template directive '{{{{{content}}}}}'",
                    lexeme,
                    self.source,
                )
            nodes.append(_Variable(content, lexeme))

        return tuple(nodes), None


class TemplateEngine:
    """Compile templates with strict references and sandboxed includes.

    Args:
        variables: Mapping of template variable names to JSON-scalar values.
        docs_root: Directory that owns every file an include may read.
        max_include_depth: Maximum number of nested include edges.  A value of
            one allows a root template to include a file, but that file may not
            include another one.
    """

    def __init__(
        self,
        variables: Mapping[str, object],
        docs_root: str | os.PathLike[str],
        *,
        max_include_depth: int = 32,
    ) -> None:
        if not isinstance(variables, Mapping):
            raise TypeError("variables must be a mapping")
        if (
            isinstance(max_include_depth, bool)
            or not isinstance(max_include_depth, int)
            or max_include_depth < 1
        ):
            raise ValueError("max_include_depth must be a positive integer")

        root = Path(docs_root)
        try:
            resolved_root = root.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise TemplateError(
                f"docs root cannot be resolved: {error}", source=root
            ) from error
        if not resolved_root.is_dir():
            raise TemplateError("docs root is not a directory", source=root)

        self.variables = dict(variables)
        self.docs_root = resolved_root
        self.max_include_depth = max_include_depth

    def render(
        self,
        template: str,
        *,
        source_path: str | os.PathLike[str] | None = None,
    ) -> str:
        """Render template text, returning normalized LF-only text."""

        if not isinstance(template, str):
            raise TypeError("template must be a string")
        normalized = _normalize_newlines(template)
        stack: tuple[Path, ...] = ()
        if source_path is not None:
            candidate = Path(source_path)
            try:
                if candidate.exists():
                    stack = (candidate.resolve(strict=True),)
            except (OSError, RuntimeError) as error:
                raise TemplateError(
                    f"source path cannot be resolved: {error}", source=source_path
                ) from error

        rendered = self._render_document(
            normalized,
            source_path=source_path,
            include_stack=stack,
            include_depth=0,
        )
        unresolved = rendered.find("{{")
        if unresolved >= 0:
            line, column = _line_and_column(rendered, unresolved)
            raise TemplateError(
                "rendered output contains an unresolved template token",
                source=source_path,
                line=line,
                column=column,
            )
        return rendered

    def compile(self, template: str, *, source_path: str | os.PathLike[str] | None = None) -> str:
        """Alias for :meth:`render` for callers that use compiler terminology."""

        return self.render(template, source_path=source_path)

    def render_file(self, source_path: str | os.PathLike[str]) -> str:
        """Read and render a UTF-8 template file."""

        source = Path(source_path)
        try:
            with source.open("r", encoding="utf-8", errors="strict", newline="") as file:
                content = file.read()
        except (OSError, UnicodeError) as error:
            raise TemplateError(
                f"cannot read UTF-8 template: {error}", source=source
            ) from error
        return self.render(content, source_path=source)

    def compile_file(
        self,
        source_path: str | os.PathLike[str],
        destination_path: str | os.PathLike[str],
    ) -> None:
        """Render a file and atomically write deterministic UTF-8/LF output."""

        output = self.render_file(source_path)
        destination = Path(destination_path)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise TemplateError(
                f"cannot create destination directory: {error}", source=destination
            ) from error

        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                errors="strict",
                newline="\n",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_name = file.name
                file.write(output)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_name, destination)
            temporary_name = None
        except (OSError, UnicodeError) as error:
            raise TemplateError(
                f"cannot write compiled template: {error}", source=destination
            ) from error
        finally:
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name)
                except FileNotFoundError:
                    pass

    def _render_document(
        self,
        template: str,
        *,
        source_path: str | os.PathLike[str] | None,
        include_stack: tuple[Path, ...],
        include_depth: int,
    ) -> str:
        lexemes = _lex(template, source_path)
        nodes = _Parser(lexemes, source_path).parse()
        # Validate both sides of every conditional so typos cannot hide in a
        # currently inactive branch.  Includes themselves remain lazy: an
        # inactive optional include need not exist for the selected profile.
        self._validate_references(nodes, source_path)
        return self._render_nodes(
            nodes,
            source_path=source_path,
            include_stack=include_stack,
            include_depth=include_depth,
        )

    def _validate_references(
        self,
        nodes: tuple[_Node, ...],
        source_path: str | os.PathLike[str] | None,
    ) -> None:
        for node in nodes:
            if isinstance(node, _Text):
                continue
            if isinstance(node, _Variable):
                self._variable_text(node.name, node.directive, source_path)
                continue
            if isinstance(node, _Include):
                reference = self._interpolate_include_reference(
                    node.reference, node.directive, source_path
                )
                include_path, _ = self._split_include_reference(
                    reference, node.directive, source_path
                )
                # Optional includes remain lazy with respect to existence and
                # section lookup, but malformed, absolute, traversing, and
                # escaping paths are invalid in every conditional branch.
                self._resolve_include_path(
                    include_path,
                    node.directive,
                    source_path,
                    must_exist=False,
                )
                continue
            self._variable_text(node.name, node.directive, source_path)
            self._validate_references(node.when_true, source_path)
            self._validate_references(node.when_false, source_path)

    def _render_nodes(
        self,
        nodes: tuple[_Node, ...],
        *,
        source_path: str | os.PathLike[str] | None,
        include_stack: tuple[Path, ...],
        include_depth: int,
    ) -> str:
        chunks: list[str] = []
        for node in nodes:
            if isinstance(node, _Text):
                chunks.append(node.value)
            elif isinstance(node, _Variable):
                chunks.append(
                    self._variable_text(node.name, node.directive, source_path)
                )
            elif isinstance(node, _Include):
                chunks.append(
                    self._render_include(
                        node,
                        source_path=source_path,
                        include_stack=include_stack,
                        include_depth=include_depth,
                    )
                )
            else:
                actual = self._variable_text(
                    node.name, node.directive, source_path
                )
                matches = actual == node.expected
                if node.operator == "!=":
                    matches = not matches
                selected = node.when_true if matches else node.when_false
                chunks.append(
                    self._render_nodes(
                        selected,
                        source_path=source_path,
                        include_stack=include_stack,
                        include_depth=include_depth,
                    )
                )
        return "".join(chunks)

    def _variable_text(
        self,
        name: str,
        directive: _Directive,
        source_path: str | os.PathLike[str] | None,
    ) -> str:
        if name not in self.variables:
            raise _directive_error(
                f"unknown template variable '{name}'", directive, source_path
            )
        value = self.variables[name]
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return value
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if not math.isfinite(value):
                raise _directive_error(
                    f"template variable '{name}' is not a finite scalar",
                    directive,
                    source_path,
                )
            return json.dumps(value, allow_nan=False, ensure_ascii=False)
        raise _directive_error(
            f"template variable '{name}' must be a scalar, not "
            f"{type(value).__name__}",
            directive,
            source_path,
        )

    def _interpolate_include_reference(
        self,
        reference: str,
        directive: _Directive,
        source_path: str | os.PathLike[str] | None,
    ) -> str:
        result: list[str] = []
        position = 0
        while position < len(reference):
            start = reference.find("{{", position)
            if start < 0:
                result.append(reference[position:])
                break
            result.append(reference[position:start])
            close = reference.find("}}", start + 2)
            if close < 0:
                raise _directive_error(
                    "unterminated variable in include path", directive, source_path
                )
            name = reference[start + 2 : close].strip()
            if not _IDENTIFIER_RE.fullmatch(name):
                raise _directive_error(
                    "include paths may contain only simple variable directives",
                    directive,
                    source_path,
                )
            result.append(self._variable_text(name, directive, source_path))
            position = close + 2

        interpolated = "".join(result).strip()
        if "{{" in interpolated or "}}" in interpolated:
            raise _directive_error(
                "include path contains an unresolved or injected template token",
                directive,
                source_path,
            )
        return interpolated

    def _render_include(
        self,
        node: _Include,
        *,
        source_path: str | os.PathLike[str] | None,
        include_stack: tuple[Path, ...],
        include_depth: int,
    ) -> str:
        reference = self._interpolate_include_reference(
            node.reference, node.directive, source_path
        )
        include_path, anchor = self._split_include_reference(
            reference, node.directive, source_path
        )
        resolved = self._resolve_include_path(
            include_path, node.directive, source_path
        )
        assert resolved is not None  # must_exist=True is the default

        if resolved in include_stack:
            cycle_start = include_stack.index(resolved)
            cycle = include_stack[cycle_start:] + (resolved,)
            display = " -> ".join(self._display_path(path) for path in cycle)
            raise _directive_error(
                f"include cycle detected: {display}", node.directive, source_path
            )
        if include_depth >= self.max_include_depth:
            raise _directive_error(
                f"maximum include depth ({self.max_include_depth}) exceeded",
                node.directive,
                source_path,
            )

        try:
            with resolved.open(
                "r", encoding="utf-8", errors="strict", newline=""
            ) as file:
                included = _normalize_newlines(file.read())
        except (OSError, UnicodeError) as error:
            raise _directive_error(
                f"cannot read included UTF-8 file '{include_path}': {error}",
                node.directive,
                source_path,
            ) from error

        if anchor is not None:
            included = self._extract_section(
                included, anchor, resolved, node.directive, source_path
            )

        rendered = self._render_document(
            included,
            source_path=resolved,
            include_stack=include_stack + (resolved,),
            include_depth=include_depth + 1,
        )
        return rendered.strip("\n")

    def _split_include_reference(
        self,
        reference: str,
        directive: _Directive,
        source_path: str | os.PathLike[str] | None,
    ) -> tuple[str, str | None]:
        if reference.count("#") > 1:
            raise _directive_error(
                "include reference contains more than one section separator",
                directive,
                source_path,
            )
        if "#" in reference:
            path_text, anchor = reference.split("#", 1)
            if not anchor or anchor.strip() != anchor:
                raise _directive_error(
                    "include section anchor is empty or has surrounding whitespace",
                    directive,
                    source_path,
                )
            if any(ord(character) < 32 for character in anchor):
                raise _directive_error(
                    "include section anchor contains a control character",
                    directive,
                    source_path,
                )
        else:
            path_text, anchor = reference, None

        path_text = path_text.strip()
        if not path_text:
            raise _directive_error(
                "include directive requires a file path", directive, source_path
            )
        return path_text, anchor

    def _resolve_include_path(
        self,
        path_text: str,
        directive: _Directive,
        source_path: str | os.PathLike[str] | None,
        *,
        must_exist: bool = True,
    ) -> Path | None:
        if "\x00" in path_text or any(
            ord(character) < 32 for character in path_text
        ):
            raise _directive_error(
                "include path contains a control character", directive, source_path
            )
        if "\\" in path_text:
            raise _directive_error(
                "include paths must use forward slashes", directive, source_path
            )

        posix_path = PurePosixPath(path_text)
        windows_path = PureWindowsPath(path_text)
        if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
            raise _directive_error(
                f"absolute include path is forbidden: '{path_text}'",
                directive,
                source_path,
            )
        if any(part in {".", ".."} for part in posix_path.parts):
            raise _directive_error(
                f"include path traversal is forbidden: '{path_text}'",
                directive,
                source_path,
            )

        relative = Path(*posix_path.parts)
        candidates = (self.docs_root / "standards" / relative, self.docs_root / relative)
        escaped_candidate = False
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
            except FileNotFoundError:
                continue
            except (OSError, RuntimeError) as error:
                raise _directive_error(
                    f"include path cannot be resolved safely: {error}",
                    directive,
                    source_path,
                ) from error
            try:
                resolved.relative_to(self.docs_root)
            except ValueError:
                escaped_candidate = True
                continue
            if not resolved.is_file():
                continue
            return resolved

        if escaped_candidate:
            raise _directive_error(
                f"include path escapes docs root through a symlink: '{path_text}'",
                directive,
                source_path,
            )
        if not must_exist:
            return None
        raise _directive_error(
            f"included file not found: '{path_text}'", directive, source_path
        )

    def _extract_section(
        self,
        text: str,
        anchor: str,
        included_path: Path,
        directive: _Directive,
        source_path: str | os.PathLike[str] | None,
    ) -> str:
        lines = text.split("\n")
        headings: list[tuple[int, int, str]] = []
        fence_character: str | None = None
        fence_length = 0

        for index, line in enumerate(lines):
            fence_match = _FENCE_RE.match(line)
            if fence_match:
                marker = fence_match.group(1)
                if fence_character is None:
                    fence_character = marker[0]
                    fence_length = len(marker)
                elif marker[0] == fence_character and len(marker) >= fence_length:
                    fence_character = None
                    fence_length = 0
                continue
            if fence_character is not None:
                continue

            heading_match = _HEADING_RE.match(line)
            if not heading_match:
                continue
            heading_text = re.sub(
                r"[ \t]+#+[ \t]*$", "", heading_match.group(2)
            )
            headings.append(
                (
                    index,
                    len(heading_match.group(1)),
                    self._heading_anchor(heading_text),
                )
            )

        matches = [heading for heading in headings if heading[2] == anchor]
        if not matches:
            raise _directive_error(
                f"section '#{anchor}' not found in '{self._display_path(included_path)}'",
                directive,
                source_path,
            )
        if len(matches) > 1:
            raise _directive_error(
                f"section '#{anchor}' is ambiguous in "
                f"'{self._display_path(included_path)}'",
                directive,
                source_path,
            )

        start_index, level, _ = matches[0]
        end_index = len(lines)
        for heading_index, heading_level, _ in headings:
            if heading_index > start_index and heading_level <= level:
                end_index = heading_index
                break
        return "\n".join(lines[start_index + 1 : end_index]).strip("\n")

    @staticmethod
    def _heading_anchor(heading: str) -> str:
        # This intentionally implements one documented, stable slugging rule
        # instead of fuzzy/substring matching.  It covers the Markdown ATX
        # headings used by framework documents and preserves Unicode letters.
        without_tags = re.sub(r"<[^>]*>", "", heading)
        lowered = without_tags.strip().lower()
        lowered = re.sub(r"[^\w\- ]", "", lowered, flags=re.UNICODE)
        return re.sub(r"[ \t\n\r\f\v]+", "-", lowered)

    def _display_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.docs_root).as_posix()
        except ValueError:
            return str(path)


def load_pair_variables() -> tuple[dict[str, object], str]:
    """Load the active legacy pair from ``docs/templates/variables.json``."""

    toolkit_dir = Path(os.environ.get("TOOLKIT_DIR", "."))
    pair_id = os.environ.get("PAIR_ID", "")
    variables_file = toolkit_dir / "docs" / "templates" / "variables.json"
    try:
        with variables_file.open("r", encoding="utf-8", errors="strict") as file:
            data = json.load(file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TemplateError(
            f"cannot load legacy variables: {error}", source=variables_file
        ) from error

    pairs = data.get("pairs") if isinstance(data, dict) else None
    if not isinstance(pairs, dict) or pair_id not in pairs:
        raise TemplateError(
            f"pair_id '{pair_id}' not found in variables.json", source=variables_file
        )
    pair = pairs[pair_id]
    if not isinstance(pair, dict):
        raise TemplateError(
            f"pair_id '{pair_id}' must contain an object", source=variables_file
        )
    # Valid v1 flat data remains accepted, but current documents use the v2
    # canonical contract (notably compile_command and output_profile).  When a
    # v2 checkout is available, compose its profile variables around the legacy
    # pair instead of requiring old clients to fabricate new fields.
    variables: dict[str, object] = dict(pair)
    if "build_command" in variables and "compile_command" not in variables:
        variables["compile_command"] = variables["build_command"]

    framework_path = toolkit_dir / "framework.json"
    if framework_path.is_file():
        try:
            framework = json.loads(framework_path.read_text(encoding="utf-8"))
            aliases = framework.get("compatibility", {}).get("accepted_pair_aliases", {})
            canonical_pair = aliases.get(pair_id, pair_id)
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", canonical_pair):
                raise ValueError(f"unsafe pair profile id {canonical_pair!r}")
            pair_profile_path = (
                toolkit_dir / "docs" / "profiles" / "pairs" / canonical_pair / "profile.json"
            )
            pair_profile = json.loads(pair_profile_path.read_text(encoding="utf-8"))
            source_id = pair_profile["source"]
            target_id = pair_profile["target"]
            output_id = os.environ.get(
                "MIGRATION_OUTPUT_PROFILE", framework.get("default_output_profile", "service")
            )
            for kind, profile_id in (
                ("source", source_id), ("target", target_id), ("output", output_id)
            ):
                if not isinstance(profile_id, str) or not re.fullmatch(
                    r"[a-z0-9]+(?:-[a-z0-9]+)*", profile_id
                ):
                    raise ValueError(f"unsafe {kind} profile id {profile_id!r}")
            profile_paths = (
                toolkit_dir / "docs" / "profiles" / "sources" / source_id / "profile.json",
                toolkit_dir / "docs" / "profiles" / "targets" / target_id / "profile.json",
                pair_profile_path,
                toolkit_dir / "docs" / "profiles" / "outputs" / output_id / "profile.json",
            )
            composed: dict[str, object] = {}
            for profile_path in profile_paths:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
                profile_variables = profile.get("variables", {})
                if not isinstance(profile_variables, dict):
                    raise ValueError(f"{profile_path} variables must be an object")
                composed.update(profile_variables)
            # Preserve explicitly supplied valid v1 values, then let the output
            # profile own output-specific framework/architecture selections.
            output_variables = json.loads(profile_paths[-1].read_text(encoding="utf-8")).get(
                "variables", {}
            )
            composed.update(variables)
            composed.update(output_variables)
            composed["pair_id"] = canonical_pair
            variables = composed
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise TemplateError(
                f"cannot compose v2 compatibility profiles: {error}", source=framework_path
            ) from error
    return variables, str(toolkit_dir)


def compile_file(
    source_path: str | os.PathLike[str],
    destination_path: str | os.PathLike[str],
) -> None:
    """Legacy environment-backed module entry point."""

    variables, toolkit_dir = load_pair_variables()
    engine = TemplateEngine(variables, Path(toolkit_dir) / "docs")
    engine.compile_file(source_path, destination_path)


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <source_file> <dest_file>", file=sys.stderr)
        return 2
    try:
        compile_file(argv[1], argv[2])
    except TemplateError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
