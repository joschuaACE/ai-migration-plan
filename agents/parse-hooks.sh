#!/bin/bash
# Compile portable Markdown hook definitions into adapter-native JSON.
#
# Compatibility usage:
#   bash agents/parse-hooks.sh <kiro|claude|codex> <hooks-dir> [target_root]
#
# Strict capability enforcement can be enabled with --strict (in any position)
# or MIGRATION_HOOK_STRICT=1. In strict mode, approximate trigger mappings and
# unsupported hook types are fatal instead of becoming explicit metadata.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 - "$SCRIPT_DIR" "$@" <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, NoReturn


PORTABLE_TRIGGERS = {
    "file-save",
    "file-create",
    "file-delete",
    "pre-tool",
    "post-tool",
    "stop",
    "session-start",
}
PORTABLE_TYPES = {"command", "agent"}
REQUIRED_FIELDS = {
    "trigger",
    "matcher",
    "type",
    "description",
    "required",
    "enforcement",
}
BASE_FIELDS = REQUIRED_FIELDS | {"command", "prompt", "timeout"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELD_RE = re.compile(r"^-[ \t]+([A-Za-z][A-Za-z0-9_.-]*):[ \t]*(.*)$")
TARGET_ROOT_RE = re.compile(
    r"^(?:\./)?[A-Za-z0-9.][A-Za-z0-9._-]*(?:/[A-Za-z0-9.][A-Za-z0-9._-]*)*$"
)
UNRESOLVED_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
UNRESOLVED_MARKER_RE = re.compile(r"\{\{|\}\}|\{%|%\}")
TRUTHY = {"1", "true", "yes", "on"}
FALSEY = {"0", "false", "no", "off", ""}


class HookError(Exception):
    """Actionable input or capability error."""


def die(message: str, *, usage: bool = False) -> NoReturn:
    print(f"parse-hooks: error: {message}", file=sys.stderr)
    if usage:
        print(
            "usage: parse-hooks.sh [--strict] <kiro|claude|codex> "
            "<hooks-dir> [target_root]",
            file=sys.stderr,
        )
    raise SystemExit(2)


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HookError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HookError(f"cannot read capability declaration {path}: {exc}") from exc
    try:
        value = json.loads(text, object_pairs_hook=reject_duplicate_json_keys)
    except (json.JSONDecodeError, HookError) as exc:
        raise HookError(f"invalid capability declaration {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HookError(f"capability declaration {path} must be a JSON object")
    return value


def parse_strict_env() -> bool:
    raw = os.environ.get(
        "MIGRATION_HOOK_STRICT", os.environ.get("HOOK_STRICT", "")
    ).strip().lower()
    if raw in TRUTHY:
        return True
    if raw in FALSEY:
        return False
    raise HookError(
        "MIGRATION_HOOK_STRICT/HOOK_STRICT must be one of "
        "1, 0, true, false, yes, no, on, or off"
    )


def parse_args(argv: list[str]) -> tuple[str, Path, str, bool]:
    strict = parse_strict_env()
    positional: list[str] = []
    for arg in argv:
        if arg == "--strict":
            strict = True
        elif arg in {"-h", "--help"}:
            print(
                "usage: parse-hooks.sh [--strict] <kiro|claude|codex> "
                "<hooks-dir> [target_root]"
            )
            raise SystemExit(0)
        elif arg.startswith("--"):
            die(f"unknown option {arg!r}", usage=True)
        else:
            positional.append(arg)

    if len(positional) not in {2, 3}:
        die("expected an adapter and hooks directory", usage=True)

    agent, hooks_dir_raw = positional[:2]
    if agent not in {"kiro", "claude", "codex"}:
        die(f"unknown adapter {agent!r}; expected kiro, claude, or codex")

    target_root = positional[2] if len(positional) == 3 else "app"
    validate_target_root(target_root)

    hooks_dir = Path(hooks_dir_raw)
    if not hooks_dir.is_dir():
        die(f"hooks directory does not exist or is not a directory: {hooks_dir}")

    return agent, hooks_dir, target_root, strict


def validate_target_root(target_root: str) -> None:
    if not target_root or "\x00" in target_root or "\n" in target_root or "\r" in target_root:
        raise HookError("target_root must be a non-empty single-line relative path")
    if not TARGET_ROOT_RE.fullmatch(target_root):
        raise HookError(
            f"unsafe target_root {target_root!r}; use a relative path containing only "
            "letters, numbers, '.', '_', '-', and '/'"
        )
    segments = target_root[2:].split("/") if target_root.startswith("./") else target_root.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise HookError(f"unsafe target_root {target_root!r}; traversal is not allowed")


def require_mapping(parent: dict[str, Any], key: str, source: Path) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise HookError(f"{source}: capability field {key!r} must be an object")
    return value


def validate_capabilities(cap: dict[str, Any], agent: str, source: Path) -> None:
    required_top = {
        "schema_version",
        "adapter",
        "adapter_version",
        "packaging",
        "surfaces",
        "output_format",
        "hook_types",
        "triggers",
        "activation",
        "evidence",
    }
    missing = sorted(required_top - cap.keys())
    if missing:
        raise HookError(f"{source}: missing capability fields: {', '.join(missing)}")
    if cap["schema_version"] != "2.0":
        raise HookError(f"{source}: unsupported schema_version {cap['schema_version']!r}")
    if cap["adapter"] != agent:
        raise HookError(
            f"{source}: adapter is {cap['adapter']!r}, expected {agent!r}"
        )
    if not isinstance(cap["adapter_version"], str) or not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+", cap["adapter_version"]
    ):
        raise HookError(f"{source}: adapter_version must be semantic version text")
    for field in ("packaging", "surfaces"):
        value = cap[field]
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item.strip() for item in value)
            or len(value) != len(set(value))
        ):
            raise HookError(
                f"{source}: {field} must be a non-empty, duplicate-free array of strings"
            )
    expected_format = "kiro-v1" if agent == "kiro" else "matcher-groups-v1"
    if cap["output_format"] != expected_format:
        raise HookError(
            f"{source}: output_format must be {expected_format!r} for {agent}"
        )

    hook_types = require_mapping(cap, "hook_types", source)
    if set(hook_types) != PORTABLE_TYPES:
        raise HookError(
            f"{source}: hook_types must declare exactly {sorted(PORTABLE_TYPES)}"
        )
    for portable_type, declaration in hook_types.items():
        if not isinstance(declaration, dict):
            raise HookError(f"{source}: hook_types.{portable_type} must be an object")
        support = declaration.get("support")
        if support not in {"native", "instruction"}:
            raise HookError(
                f"{source}: hook_types.{portable_type}.support must be native or instruction"
            )
        if not isinstance(declaration.get("timeout"), bool):
            raise HookError(
                f"{source}: hook_types.{portable_type}.timeout must be a boolean"
            )
        stability = declaration.get("stability")
        if stability not in {"stable", "experimental", "unsupported"}:
            raise HookError(
                f"{source}: hook_types.{portable_type}.stability must be stable, "
                "experimental, or unsupported"
            )
        native_type = declaration.get("native_type")
        if support == "native" and native_type not in {"command", "prompt", "agent"}:
            raise HookError(
                f"{source}: hook_types.{portable_type}.native_type is invalid"
            )
        if support == "instruction" and native_type is not None:
            raise HookError(
                f"{source}: instruction-only type {portable_type!r} cannot declare native_type"
            )
        if support == "native" and stability == "unsupported":
            raise HookError(
                f"{source}: native type {portable_type!r} cannot have unsupported stability"
            )
        if support == "instruction" and stability != "unsupported":
            raise HookError(
                f"{source}: instruction-only type {portable_type!r} must have unsupported stability"
            )
        if support == "instruction" and not isinstance(declaration.get("reason"), str):
            raise HookError(
                f"{source}: instruction-only type {portable_type!r} requires a reason"
            )

    triggers = require_mapping(cap, "triggers", source)
    if set(triggers) != PORTABLE_TRIGGERS:
        missing_triggers = sorted(PORTABLE_TRIGGERS - triggers.keys())
        extra_triggers = sorted(triggers.keys() - PORTABLE_TRIGGERS)
        details = []
        if missing_triggers:
            details.append(f"missing {missing_triggers}")
        if extra_triggers:
            details.append(f"unknown {extra_triggers}")
        raise HookError(f"{source}: invalid trigger declarations ({'; '.join(details)})")
    for trigger, declaration in triggers.items():
        if not isinstance(declaration, dict):
            raise HookError(f"{source}: triggers.{trigger} must be an object")
        support = declaration.get("support")
        if support not in {"native", "approximate", "unsupported"}:
            raise HookError(
                f"{source}: triggers.{trigger}.support must be native, approximate, or unsupported"
            )
        event = declaration.get("event")
        if support != "unsupported" and (not isinstance(event, str) or not event):
            raise HookError(f"{source}: triggers.{trigger}.event must be a non-empty string")
        strategy = declaration.get("matcher_strategy")
        if strategy not in {"portable", "fixed", "none"}:
            raise HookError(
                f"{source}: triggers.{trigger}.matcher_strategy is invalid"
            )
        if strategy == "fixed" and not isinstance(declaration.get("native_matcher"), str):
            raise HookError(
                f"{source}: triggers.{trigger}.native_matcher must be a string"
            )
        native_types = declaration.get("native_types")
        if (
            not isinstance(native_types, list)
            or not all(
                isinstance(item, str) and item in PORTABLE_TYPES
                for item in native_types
            )
            or len(native_types) != len(set(native_types))
            or (support != "unsupported" and not native_types)
            or (support == "unsupported" and native_types)
        ):
            raise HookError(
                f"{source}: triggers.{trigger}.native_types must be a duplicate-free "
                "command/agent array, non-empty exactly when the trigger is supported"
            )
        if support != "native" and not isinstance(declaration.get("reason"), str):
            raise HookError(
                f"{source}: non-native trigger {trigger!r} requires a reason"
            )

    activation = require_mapping(cap, "activation", source)
    if not isinstance(activation.get("requirements", []), list) or not all(
        isinstance(item, str) and item.strip()
        for item in activation.get("requirements", [])
    ):
        raise HookError(f"{source}: activation.requirements must be an array of strings")
    evidence = require_mapping(cap, "evidence", source)
    reviewed = evidence.get("last_reviewed")
    try:
        if not isinstance(reviewed, str):
            raise ValueError
        date.fromisoformat(reviewed)
    except ValueError:
        raise HookError(f"{source}: evidence.last_reviewed must use YYYY-MM-DD")
    if not isinstance(evidence.get("url"), str) or not evidence["url"].startswith(
        "https://"
    ):
        raise HookError(f"{source}: evidence.url must be an HTTPS URL")


@dataclass(frozen=True)
class HookDefinition:
    name: str
    source: Path
    line: int
    trigger: str
    matcher: str
    hook_type: str
    description: str
    required: bool
    enforcement: str
    command: str | None
    prompt: str | None
    timeout: int | None
    context: tuple[tuple[str, str], ...]


def location(path: Path, line: int) -> str:
    return f"{path}:{line}"


def validate_unresolved(value: str, where: str) -> None:
    match = UNRESOLVED_RE.search(value) or UNRESOLVED_MARKER_RE.search(value)
    if match:
        token = match.group(0).splitlines()[0]
        raise HookError(f"{where}: unresolved template token {token!r}")
    if "{target_root}" in value:
        raise HookError(f"{where}: unresolved {{target_root}} placeholder")


def build_hook(
    name: str,
    source: Path,
    line: int,
    fields: dict[str, tuple[str, int]],
    target_root: str,
) -> HookDefinition:
    where = location(source, line)
    if not NAME_RE.fullmatch(name):
        raise HookError(
            f"{where}: invalid hook name {name!r}; use lower-case kebab-case"
        )

    missing = sorted(REQUIRED_FIELDS - fields.keys())
    if missing:
        raise HookError(f"{where}: missing required fields: {', '.join(missing)}")

    values: dict[str, str] = {}
    for key, (raw_value, field_line) in fields.items():
        if not raw_value.strip():
            raise HookError(f"{location(source, field_line)}: field {key!r} cannot be empty")
        value = raw_value.strip().replace("{target_root}", target_root)
        validate_unresolved(value, f"{location(source, field_line)} field {key!r}")
        if "\x00" in value or "\r" in value or "\n" in value:
            raise HookError(
                f"{location(source, field_line)}: field {key!r} must be a single line"
            )
        values[key] = value

    trigger = values["trigger"]
    if trigger not in PORTABLE_TRIGGERS:
        raise HookError(
            f"{where}: unsupported trigger {trigger!r}; expected one of "
            f"{', '.join(sorted(PORTABLE_TRIGGERS))}"
        )

    hook_type = values["type"]
    if hook_type not in PORTABLE_TYPES:
        raise HookError(
            f"{where}: unsupported hook type {hook_type!r}; expected command or agent"
        )

    required_raw = values["required"]
    if required_raw not in {"true", "false"}:
        raise HookError(f"{where}: required must be the boolean true or false")
    required = required_raw == "true"

    expected_enforcement = "deterministic" if hook_type == "command" else "judgment"
    enforcement = values["enforcement"]
    if enforcement not in {"deterministic", "judgment"}:
        raise HookError(
            f"{where}: enforcement must be deterministic or judgment"
        )
    if enforcement != expected_enforcement:
        raise HookError(
            f"{where}: {hook_type} hooks require enforcement: {expected_enforcement}"
        )

    command = values.get("command")
    prompt = values.get("prompt")
    if hook_type == "command":
        if command is None:
            raise HookError(f"{where}: command hook requires a command field")
        if prompt is not None:
            raise HookError(f"{where}: command hook cannot contain a prompt field")
    else:
        if prompt is None:
            raise HookError(f"{where}: agent hook requires a prompt field")
        if command is not None:
            raise HookError(f"{where}: agent hook cannot contain a command field")

    extra_fields = sorted(set(values) - BASE_FIELDS)
    if hook_type == "command" and extra_fields:
        raise HookError(
            f"{where}: command hook has unknown fields: {', '.join(extra_fields)}"
        )
    context = tuple((key, values[key]) for key in extra_fields)

    timeout: int | None = None
    if "timeout" in values:
        timeout_raw = values["timeout"]
        if not re.fullmatch(r"[0-9]+", timeout_raw):
            raise HookError(f"{where}: timeout must be an integer number of seconds")
        timeout = int(timeout_raw)
        if not 1 <= timeout <= 3600:
            raise HookError(f"{where}: timeout must be between 1 and 3600 seconds")

    matcher = values["matcher"]
    try:
        re.compile(matcher)
    except re.error as exc:
        raise HookError(f"{where}: matcher is not a valid regular expression: {exc}") from exc

    return HookDefinition(
        name=name,
        source=source,
        line=line,
        trigger=trigger,
        matcher=matcher,
        hook_type=hook_type,
        description=values["description"],
        required=required,
        enforcement=enforcement,
        command=command,
        prompt=prompt,
        timeout=timeout,
        context=context,
    )


def parse_hook_file(path: Path, target_root: str) -> list[HookDefinition]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HookError(f"{path}: hook definitions must be UTF-8") from exc
    except OSError as exc:
        raise HookError(f"cannot read hook definition {path}: {exc}") from exc

    unresolved = UNRESOLVED_RE.search(text) or UNRESOLVED_MARKER_RE.search(text)
    if unresolved:
        line = text.count("\n", 0, unresolved.start()) + 1
        token = unresolved.group(0).splitlines()[0]
        raise HookError(f"{path}:{line}: unresolved template token {token!r}")

    hooks: list[HookDefinition] = []
    current_name: str | None = None
    current_line = 0
    fields: dict[str, tuple[str, int]] = {}

    def finish_current() -> None:
        nonlocal current_name, current_line, fields
        if current_name is not None:
            hooks.append(build_hook(current_name, path, current_line, fields, target_root))

    for line_no, line in enumerate(text.splitlines(), start=1):
        heading = re.fullmatch(r"##[ \t]+(.+?)[ \t]*", line)
        if heading:
            finish_current()
            current_name = heading.group(1).strip()
            current_line = line_no
            fields = {}
            continue

        if current_name is None:
            continue

        if line.startswith("-"):
            field_match = FIELD_RE.fullmatch(line)
            if not field_match:
                raise HookError(
                    f"{path}:{line_no}: malformed field; expected '- key: value'"
                )
            key, value = field_match.groups()
            if key in fields:
                previous_line = fields[key][1]
                raise HookError(
                    f"{path}:{line_no}: duplicate field {key!r} "
                    f"(first declared on line {previous_line})"
                )
            fields[key] = (value, line_no)
        elif line.strip() and line.strip() != "---":
            raise HookError(
                f"{path}:{line_no}: unexpected content in hook section; "
                "expected '- key: value'"
            )

    finish_current()
    return hooks


def load_hooks(hooks_dir: Path, target_root: str) -> list[HookDefinition]:
    try:
        files = sorted(
            (
                path
                for path in hooks_dir.iterdir()
                if path.is_file() and path.suffix == ".md"
            ),
            key=lambda path: path.name,
        )
    except OSError as exc:
        raise HookError(f"cannot enumerate hooks directory {hooks_dir}: {exc}") from exc
    if not files:
        raise HookError(f"no .md hook definition files found in {hooks_dir}")
    symlinks = [path for path in files if path.is_symlink()]
    if symlinks:
        raise HookError(
            f"hook definition symlinks are not allowed: {', '.join(path.name for path in symlinks)}"
        )

    hooks: list[HookDefinition] = []
    names: dict[str, HookDefinition] = {}
    for path in files:
        for hook in parse_hook_file(path, target_root):
            if hook.name in names:
                first = names[hook.name]
                raise HookError(
                    f"{location(hook.source, hook.line)}: duplicate hook name {hook.name!r}; "
                    f"first declared at {location(first.source, first.line)}"
                )
            names[hook.name] = hook
            hooks.append(hook)
    if not hooks:
        raise HookError(f"no level-two hook sections found in {hooks_dir}")
    return hooks


def warning(
    code: str,
    hook: HookDefinition,
    message: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "hook": hook.name,
        "message": message,
        "required": hook.required,
        # Generated artifacts must not depend on the absolute staging directory.
        "source": f"{hook.source.name}:{hook.line}",
    }


def prompt_with_context(hook: HookDefinition, *, include_event_filter: bool) -> str:
    assert hook.prompt is not None
    pieces: list[str] = []
    if include_event_filter:
        pieces.append(
            f"This portable hook represents `{hook.trigger}` for paths matching the regular "
            f"expression `{hook.matcher}`. Inspect the hook input first. If the event or path "
            "does not match, return JSON {\"ok\": true} without performing the review."
        )
    pieces.append(hook.prompt)
    if hook.context:
        pieces.append(
            "Portable hook context:\n"
            + "\n".join(f"- {key}: {value}" for key, value in hook.context)
        )
    return "\n\n".join(pieces)


def native_matcher(trigger_cap: dict[str, Any], hook: HookDefinition) -> str | None:
    strategy = trigger_cap["matcher_strategy"]
    if strategy == "portable":
        return hook.matcher
    if strategy == "fixed":
        return trigger_cap["native_matcher"]
    return None


def compile_hooks(
    agent: str,
    hooks: list[HookDefinition],
    cap: dict[str, Any],
    strict: bool,
) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    instructions: list[dict[str, Any]] = []
    native_hooks: list[tuple[HookDefinition, str, str | None, str, str | None]] = []

    for hook in hooks:
        trigger_cap = cap["triggers"][hook.trigger]
        type_cap = cap["hook_types"][hook.hook_type]
        problems: list[dict[str, str]] = []

        if trigger_cap["support"] != "native":
            problems.append(
                warning(
                    "approximate-trigger"
                    if trigger_cap["support"] == "approximate"
                    else "unsupported-trigger",
                    hook,
                    trigger_cap["reason"],
                )
            )
        if type_cap["support"] != "native":
            problems.append(
                warning("unsupported-hook-type", hook, type_cap["reason"])
            )
        elif (
            trigger_cap["support"] != "unsupported"
            and hook.hook_type not in trigger_cap["native_types"]
        ):
            problems.append(
                warning(
                    "unsupported-type-for-trigger",
                    hook,
                    f"{agent} does not support {hook.hook_type} handlers for "
                    f"the native {trigger_cap['event']} event",
                )
            )
        elif (
            trigger_cap["support"] != "unsupported"
            and type_cap["stability"] == "experimental"
        ):
            problems.append(
                warning(
                    "experimental-hook-type",
                    hook,
                    f"{agent} {hook.hook_type} hook handlers are experimental",
                )
            )
        if hook.timeout is not None and not type_cap["timeout"]:
            problems.append(
                warning(
                    "unsupported-timeout",
                    hook,
                    f"{agent} ignores timeout for {hook.hook_type} hooks",
                )
            )

        if strict and problems:
            rendered = "; ".join(problem["message"] for problem in problems)
            raise HookError(
                f"{location(hook.source, hook.line)}: strict capability check failed for "
                f"{hook.name!r}: {rendered}"
            )
        warnings.extend(problems)

        if (
            type_cap["support"] != "native"
            or trigger_cap["support"] == "unsupported"
            or hook.hook_type not in trigger_cap["native_types"]
        ):
            instructions.append(
                {
                    "description": hook.description,
                    "hook": hook.name,
                    "matcher": hook.matcher,
                    "prompt": prompt_with_context(hook, include_event_filter=False)
                    if hook.prompt
                    else None,
                    "reason": "; ".join(
                        problem["message"].rstrip(".") for problem in problems
                    )
                    + ".",
                    "required": hook.required,
                    "enforcement": hook.enforcement,
                    "trigger": hook.trigger,
                    "type": hook.hook_type,
                }
            )
            continue

        native_prompt = (
            prompt_with_context(
                hook,
                include_event_filter=trigger_cap["support"] == "approximate",
            )
            if hook.prompt
            else None
        )
        if agent == "claude" and native_prompt is not None:
            native_prompt = (
                f"{native_prompt}\n\nHook input: $ARGUMENTS\n\n"
                "Return JSON {\"ok\": true} when the check passes or does not apply, "
                "or {\"ok\": false, \"reason\": \"...\"} when it fails."
            )

        native_hooks.append(
            (
                hook,
                trigger_cap["event"],
                native_matcher(trigger_cap, hook),
                type_cap["native_type"],
                native_prompt,
            )
        )

    warnings.sort(key=lambda item: (item["hook"], item["code"], item["message"]))
    instructions.sort(key=lambda item: item["hook"])

    if agent == "kiro":
        result = emit_kiro(native_hooks)
    else:
        result = emit_matcher_groups(agent, native_hooks)

    activation_requirements = cap.get("activation", {}).get("requirements", [])
    if warnings or instructions or activation_requirements:
        result["_migration_framework"] = {
            "activation_requirements": activation_requirements,
            "adapter": agent,
            "instructions": instructions,
            "schema_version": "2.0",
            "strict": strict,
            "warnings": warnings,
        }
    return result


def emit_kiro(
    native_hooks: list[tuple[HookDefinition, str, str | None, str, str | None]],
) -> dict[str, Any]:
    emitted: list[dict[str, Any]] = []
    for hook, event, matcher, native_type, prompt in native_hooks:
        action: dict[str, Any] = {"type": native_type}
        if native_type == "command":
            action["command"] = hook.command
        else:
            action["prompt"] = prompt
        item: dict[str, Any] = {
            "action": action,
            "description": hook.description,
            "enabled": True,
            "name": hook.name,
            "trigger": event,
        }
        if matcher is not None:
            item["matcher"] = matcher
        if hook.timeout is not None and native_type == "command":
            item["timeout"] = hook.timeout
        emitted.append(item)
    return {"hooks": emitted, "version": "v1"}


def emit_matcher_groups(
    agent: str,
    native_hooks: list[tuple[HookDefinition, str, str | None, str, str | None]],
) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for hook, event, matcher, native_type, prompt in native_hooks:
        handler: dict[str, Any] = {"type": native_type}
        if native_type == "command":
            handler["command"] = hook.command
        else:
            handler["prompt"] = prompt
        if hook.timeout is not None:
            handler["timeout"] = hook.timeout
        if agent == "codex":
            handler["statusMessage"] = hook.description

        group: dict[str, Any] = {"hooks": [handler]}
        if matcher is not None:
            group["matcher"] = matcher
        events[event].append(group)

    return {"hooks": {event: events[event] for event in sorted(events)}}


def main() -> int:
    script_dir = Path(sys.argv[1]).resolve()
    agent, hooks_dir, target_root, strict = parse_args(sys.argv[2:])
    cap_path = script_dir / agent / "capabilities.json"
    cap = load_json(cap_path)
    validate_capabilities(cap, agent, cap_path)
    hooks = load_hooks(hooks_dir, target_root)
    result = compile_hooks(agent, hooks, cap, strict)

    metadata = result.get("_migration_framework", {})
    for item in metadata.get("warnings", []):
        print(
            f"parse-hooks: warning: {item['source']}: {item['hook']}: {item['message']}",
            file=sys.stderr,
        )
    json.dump(result, sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


try:
    raise SystemExit(main())
except HookError as exc:
    die(str(exc))
PY
