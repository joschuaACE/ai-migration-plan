#!/usr/bin/env python3
"""Installed, dependency-free runtime for migration state and completion claims.

The module deliberately has no dependency on ``agents.framework``.  A compiled bundle copies
this file to ``.migration-framework/bin/migrationctl.py``; in that layout schemas and
``runtime.json`` live one directory above ``bin``.  In a source checkout they live below the
repository root, which is also one directory above this file's parent.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence


CERTIFICATE_NAME = "completion-certificate.json"
CORE_ARTIFACTS = ("config.json", "state.json", "inventory.json", "traceability.json")
MANAGED_SOURCE_EXCLUSIONS = (
    ".git",
    ".migration",
    ".migration-framework",
    ".kiro",
    ".claude",
    ".codex",
)
TERMINAL_DISPOSITIONS = frozenset({"migrated", "replaced", "removed", "retained"})
MIGRATED_DISPOSITIONS = frozenset({"migrated", "replaced"})
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class MigrationRuntimeError(RuntimeError):
    """Raised for safe, user-actionable runtime failures."""


class DuplicateJsonKey(ValueError):
    """Raised when a JSON object repeats a key."""


@dataclass(frozen=True)
class RuntimeLayout:
    root: Path
    schemas: Path
    metadata: Path
    framework_version: str
    state_machine: dict[str, Any]


@dataclass
class MigrationContext:
    migration_dir: Path
    project_root: Path
    layout: RuntimeLayout
    artifacts: dict[str, dict[str, Any]]
    load_errors: list[str]

    def get(self, relative: str) -> dict[str, Any] | None:
        return self.artifacts.get(relative)

    @property
    def config(self) -> dict[str, Any]:
        return self.artifacts.get("config.json", {})

    @property
    def state(self) -> dict[str, Any]:
        return self.artifacts.get("state.json", {})

    @property
    def inventory(self) -> dict[str, Any]:
        return self.artifacts.get("inventory.json", {})

    @property
    def traceability(self) -> dict[str, Any]:
        return self.artifacts.get("traceability.json", {})

    @property
    def scope(self) -> dict[str, Any]:
        return self.artifacts.get("scope.json", {})

    @property
    def target_inventory(self) -> dict[str, Any]:
        return self.artifacts.get("target-inventory.json", {})


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs
        )
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateJsonKey) as exc:
        raise MigrationRuntimeError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise MigrationRuntimeError(f"{path}: top-level JSON value must be an object")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    """Durably replace one JSON file without exposing a partial artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(pretty_json(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def discover_runtime_layout(script_path: Path | None = None) -> RuntimeLayout:
    script = (script_path or Path(__file__)).expanduser().resolve()
    root = script.parent.parent
    schemas = root / "schemas"
    metadata_candidates = (root / "runtime.json", root / "framework.json")
    metadata = next((item for item in metadata_candidates if item.is_file()), None)
    if not schemas.is_dir():
        raise MigrationRuntimeError(f"runtime schema directory is missing: {schemas}")
    if metadata is None:
        raise MigrationRuntimeError(
            f"runtime metadata is missing; expected one of: "
            + ", ".join(str(item) for item in metadata_candidates)
        )
    manifest = read_json(metadata)
    state_machine = manifest.get("state_machine")
    if not isinstance(state_machine, dict) or not isinstance(
        state_machine.get("transitions"), dict
    ):
        raise MigrationRuntimeError(f"{metadata}: missing complete state_machine metadata")
    version = manifest.get("framework_version")
    if not isinstance(version, str):
        raise MigrationRuntimeError(f"{metadata}: missing framework_version")
    return RuntimeLayout(root, schemas, metadata, version, state_machine)


def resolve_migration_dir(path: Path) -> Path:
    expanded = path.expanduser()
    absolute = Path(os.path.abspath(expanded if expanded.is_absolute() else Path.cwd() / expanded))
    if (absolute / "state.json").is_file() or absolute.name == ".migration":
        return absolute
    candidate = absolute / ".migration"
    return candidate if candidate.is_dir() else absolute


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def safe_relative_path(value: Any, *, label: str, allow_dot: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise MigrationRuntimeError(f"{label}: path must be a non-empty string")
    normalized = value.replace("\\", "/")
    if allow_dot and normalized == ".":
        return normalized
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise MigrationRuntimeError(f"{label}: unsafe relative path {value!r}")
    return pure.as_posix()


def safe_project_path(
    project_root: Path, value: Any, *, label: str, allow_dot: bool = False
) -> Path:
    relative = safe_relative_path(value, label=label, allow_dot=allow_dot)
    root = project_root.resolve()
    parts = () if relative == "." else PurePosixPath(relative).parts
    candidate = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise MigrationRuntimeError(f"{label}: cannot inspect path {value!r}: {exc}") from exc
        if stat.S_ISLNK(mode):
            raise MigrationRuntimeError(f"{label}: symlink path component is forbidden: {value!r}")
    if not _is_relative_to(candidate, root):
        raise MigrationRuntimeError(f"{label}: path escapes project root: {value!r}")
    return candidate


def _resolve_ref(schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise MigrationRuntimeError(f"unsupported non-local schema reference {reference!r}")
    current: Any = schema
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise MigrationRuntimeError(f"invalid local schema reference {reference!r}")
        current = current[token]
    if not isinstance(current, dict):
        raise MigrationRuntimeError(f"schema reference does not name an object: {reference!r}")
    return current


def _json_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def schema_errors(
    value: Any,
    schema: dict[str, Any],
    *,
    root_schema: dict[str, Any] | None = None,
    location: str = "$",
) -> list[str]:
    """Validate the conservative JSON-Schema subset used by this framework."""
    root = root_schema or schema
    if "$ref" in schema:
        return schema_errors(
            value, _resolve_ref(root, schema["$ref"]), root_schema=root, location=location
        )
    errors: list[str] = []
    expected = schema.get("type")
    types = expected if isinstance(expected, list) else [expected] if expected else []
    if types and not any(_json_type(value, item) for item in types):
        return [f"{location}: expected type {expected!r}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{location}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: {value!r} is not one of {schema['enum']!r}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{location}: string is shorter than {schema['minLength']}")
        pattern = schema.get("pattern")
        if pattern and re.search(pattern, value) is None:
            errors.append(f"{location}: value does not match {pattern!r}")
        if schema.get("format") == "date-time" and parse_datetime(value) is None:
            errors.append(f"{location}: invalid date-time")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{location}: value is below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{location}: value is above {schema['maximum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{location}: needs at least {schema['minItems']} items")
        if schema.get("uniqueItems"):
            rendered = [canonical_json(item) for item in value]
            if len(rendered) != len(set(rendered)):
                errors.append(f"{location}: array items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    schema_errors(
                        item, item_schema, root_schema=root, location=f"{location}[{index}]"
                    )
                )
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{location}: missing required property {key!r}")
        properties = schema.get("properties", {})
        for key, child in properties.items():
            if key in value and isinstance(child, dict):
                errors.extend(
                    schema_errors(
                        value[key], child, root_schema=root, location=f"{location}.{key}"
                    )
                )
        additional = schema.get("additionalProperties", True)
        for key in value.keys() - properties.keys():
            if additional is False:
                errors.append(f"{location}: unexpected property {key!r}")
            elif isinstance(additional, dict):
                errors.extend(
                    schema_errors(
                        value[key], additional, root_schema=root, location=f"{location}.{key}"
                    )
                )
    for child in schema.get("allOf", []):
        errors.extend(schema_errors(value, child, root_schema=root, location=location))
    return errors


def load_context(
    migration_path: Path,
    *,
    project_root: Path | None = None,
    layout: RuntimeLayout | None = None,
    overrides: Mapping[str, dict[str, Any]] | None = None,
) -> MigrationContext:
    migration_dir = resolve_migration_dir(migration_path)
    root = (project_root or migration_dir.parent).expanduser().resolve()
    runtime_layout = layout or discover_runtime_layout()
    artifacts: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if migration_dir.is_symlink():
        return MigrationContext(
            migration_dir,
            root,
            runtime_layout,
            {},
            [f"{migration_dir}: migration directory must not be a symlink"],
        )
    if not migration_dir.is_dir():
        return MigrationContext(
            migration_dir, root, runtime_layout, {}, [f"{migration_dir}: directory is missing"]
        )
    json_paths: list[Path] = []
    for current, directories, names in os.walk(migration_dir, topdown=True, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(directories):
            path = current_path / name
            relative = path.relative_to(migration_dir).as_posix()
            if path.is_symlink():
                errors.append(f"{relative}: symlinks are forbidden inside .migration")
            else:
                kept.append(name)
        directories[:] = kept
        for name in sorted(names):
            path = current_path / name
            relative = path.relative_to(migration_dir).as_posix()
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                errors.append(f"{relative}: cannot inspect migration artifact: {exc}")
                continue
            if stat.S_ISLNK(mode):
                errors.append(f"{relative}: symlinks are forbidden inside .migration")
            elif not stat.S_ISREG(mode):
                errors.append(f"{relative}: migration artifact must be a regular file")
            elif path.suffix == ".json":
                json_paths.append(path)
    for path in sorted(json_paths):
        relative = path.relative_to(migration_dir).as_posix()
        try:
            artifacts[relative] = read_json(path)
        except MigrationRuntimeError as exc:
            errors.append(str(exc))
    artifacts.update(overrides or {})
    return MigrationContext(migration_dir, root, runtime_layout, artifacts, errors)


def _artifact_groups(ctx: MigrationContext) -> dict[str, dict[str, dict[str, Any]]]:
    prefixes = {
        "behaviors": "behaviors/",
        "decisions": "decisions/",
        "plans": "plans/",
        "evidence": "evidence/",
        "exceptions": "exceptions/",
    }
    return {
        name: {
            relative: artifact
            for relative, artifact in ctx.artifacts.items()
            if relative.startswith(prefix)
        }
        for name, prefix in prefixes.items()
    }


def _index_by_id(
    records: Mapping[str, dict[str, Any]], label: str, errors: list[str]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for relative, record in records.items():
        identifier = record.get("id")
        if not isinstance(identifier, str):
            continue
        if identifier in result:
            errors.append(f"{label}: duplicate id {identifier!r}")
        else:
            result[identifier] = record
    return result


def _validate_schema_artifacts(ctx: MigrationContext, errors: list[str]) -> None:
    for relative, artifact in sorted(ctx.artifacts.items()):
        reference = artifact.get("$schema")
        if not isinstance(reference, str):
            errors.append(f"{relative}: missing $schema")
            continue
        schema_path = ctx.layout.schemas / Path(reference).name
        if not schema_path.is_file():
            errors.append(f"{relative}: unknown runtime schema {Path(reference).name!r}")
            continue
        try:
            schema = read_json(schema_path)
            errors.extend(
                f"{relative}: {error}" for error in schema_errors(artifact, schema)
            )
        except MigrationRuntimeError as exc:
            errors.append(str(exc))


def _validate_state(ctx: MigrationContext, plan_ids: set[str], errors: list[str]) -> None:
    state = ctx.state
    if not state:
        return
    history = state.get("history", [])
    transitions = ctx.layout.state_machine.get("transitions", {})
    initial = ctx.layout.state_machine.get("initial")
    if isinstance(history, list):
        for index, transition in enumerate(history):
            if not isinstance(transition, dict):
                continue
            previous = transition.get("from")
            destination = transition.get("to")
            if previous is None:
                if index != 0 or destination != initial:
                    errors.append("state.json history[0]: must initialize from null")
            elif destination not in transitions.get(previous, []):
                errors.append(
                    f"state.json history[{index}]: invalid transition {previous!r} -> {destination!r}"
                )
            if index and transition.get("from") != history[index - 1].get("to"):
                errors.append(f"state.json history[{index}]: transition chain is discontinuous")
        if history:
            if state.get("last_transition") != history[-1]:
                errors.append("state.json: last_transition must equal final history entry")
            if state.get("status") != history[-1].get("to"):
                errors.append("state.json: status must equal final history destination")
            if state.get("revision") != len(history) - 1:
                errors.append("state.json: revision must equal completed transition count")
    for plan_id in state.get("completed_slices", []):
        if plan_id not in plan_ids:
            errors.append(f"state.json: completed_slices references unknown plan {plan_id!r}")
    if state.get("status") in {"blocked", "failed"}:
        if not state.get("resume_to") or not state.get("blocked_by"):
            errors.append("state.json: blocked/failed requires resume_to and blocked_by")
    elif state.get("resume_to") is not None or state.get("blocked_by"):
        errors.append("state.json: active state must clear resume_to and blocked_by")


def validate_context(
    ctx: MigrationContext, *, enforce_terminal_certificate: bool = True
) -> list[str]:
    """Return structural/schema/reference errors without making a completion claim."""
    errors = list(ctx.load_errors)
    for required in CORE_ARTIFACTS:
        if required not in ctx.artifacts:
            errors.append(f"missing core artifact {required}")
    v3_present = "scope.json" in ctx.artifacts or "target-inventory.json" in ctx.artifacts
    if v3_present:
        for required in ("scope.json", "target-inventory.json"):
            if required not in ctx.artifacts:
                errors.append(f"v3 migration graph is missing {required}")
    _validate_schema_artifacts(ctx, errors)
    groups = _artifact_groups(ctx)
    behaviors = _index_by_id(groups["behaviors"], "behaviors", errors)
    decisions = _index_by_id(groups["decisions"], "decisions", errors)
    plans = _index_by_id(groups["plans"], "plans", errors)
    evidence = _index_by_id(groups["evidence"], "evidence", errors)
    exceptions = _index_by_id(groups["exceptions"], "exceptions", errors)

    inventory_units = ctx.inventory.get("units", [])
    source: dict[str, dict[str, Any]] = {}
    source_paths: dict[str, str] = {}
    for index, unit in enumerate(inventory_units if isinstance(inventory_units, list) else []):
        if not isinstance(unit, dict):
            continue
        identifier = unit.get("id")
        path = unit.get("path")
        if isinstance(identifier, str):
            if identifier in source:
                errors.append(f"inventory.json: duplicate source id {identifier!r}")
            source[identifier] = unit
        if isinstance(path, str):
            if path in source_paths:
                errors.append(
                    f"inventory.json: duplicate path {path!r} for {source_paths[path]!r} and {identifier!r}"
                )
            source_paths[path] = str(identifier)

    target: dict[str, dict[str, Any]] = {}
    target_paths: dict[str, str] = {}
    for unit in ctx.target_inventory.get("units", []):
        if not isinstance(unit, dict):
            continue
        identifier, path = unit.get("id"), unit.get("path")
        if isinstance(identifier, str):
            if identifier in target:
                errors.append(f"target-inventory.json: duplicate id {identifier!r}")
            target[identifier] = unit
        if isinstance(path, str):
            if path in target_paths:
                errors.append(f"target-inventory.json: duplicate path {path!r}")
            target_paths[path] = str(identifier)
        if isinstance(identifier, str):
            try:
                _resolve_target_path(ctx, path, label=f"target {identifier} path")
            except MigrationRuntimeError as exc:
                errors.append(str(exc))

    migration_ids: dict[str, str] = {}
    for relative in ("state.json", "inventory.json", "traceability.json", "scope.json", "target-inventory.json"):
        artifact = ctx.artifacts.get(relative)
        if artifact and isinstance(artifact.get("migration_id"), str):
            migration_ids[relative] = artifact["migration_id"]
    if len(set(migration_ids.values())) > 1:
        errors.append(
            "migration_id mismatch: "
            + ", ".join(f"{name}={value!r}" for name, value in sorted(migration_ids.items()))
        )

    for behavior_id, behavior in behaviors.items():
        for source_id in behavior.get("source_units", []):
            if source_id not in source:
                errors.append(f"behavior {behavior_id}: unknown source unit {source_id!r}")
    for source_id, unit in source.items():
        for behavior_id in unit.get("behaviors", []):
            if behavior_id not in behaviors:
                errors.append(f"source {source_id}: unknown behavior {behavior_id!r}")
    for plan_id, plan in plans.items():
        for source_id in plan.get("source_units", []):
            if source_id not in source:
                errors.append(f"plan {plan_id}: unknown source unit {source_id!r}")
        for behavior_id in plan.get("behavioral_contracts", []):
            if behavior_id not in behaviors:
                errors.append(f"plan {plan_id}: unknown behavior {behavior_id!r}")
        if ctx.target_inventory:
            for target_id in plan.get("target_units", []):
                if target_id not in target:
                    errors.append(f"plan {plan_id}: unknown target unit {target_id!r}")
        for dependency in plan.get("dependencies", []):
            if dependency not in plans:
                errors.append(f"plan {plan_id}: unknown dependency {dependency!r}")
    for evidence_id, record in evidence.items():
        slice_id = record.get("slice_id")
        if slice_id is not None and slice_id not in plans:
            errors.append(f"evidence {evidence_id}: unknown slice {slice_id!r}")
        for behavior_id in record.get("contracts", []):
            if behavior_id not in behaviors:
                errors.append(f"evidence {evidence_id}: unknown behavior {behavior_id!r}")
    known_scope = (
        set(source)
        | set(behaviors)
        | set(plans)
        | set(target)
        | set(decisions)
        | set(evidence)
    )
    for exception_id, record in exceptions.items():
        for item in record.get("scope", []):
            if item not in known_scope:
                errors.append(f"exception {exception_id}: unknown scope id {item!r}")

    scope_seen: set[str] = set()
    for index, item in enumerate(ctx.scope.get("units", [])):
        if not isinstance(item, dict):
            continue
        source_id = item.get("source_unit")
        if source_id in scope_seen:
            errors.append(f"scope.json: duplicate disposition for {source_id!r}")
        if isinstance(source_id, str):
            scope_seen.add(source_id)
            if source_id not in source:
                errors.append(f"scope.json units[{index}]: unknown source unit {source_id!r}")
        for target_id in item.get("target_units", []):
            if target_id not in target:
                errors.append(f"scope.json units[{index}]: unknown target {target_id!r}")
        for decision_id in item.get("decisions", []):
            if decision_id not in decisions:
                errors.append(f"scope.json units[{index}]: unknown decision {decision_id!r}")
        for exception_id in item.get("exceptions", []):
            if exception_id not in exceptions:
                errors.append(f"scope.json units[{index}]: unknown exception {exception_id!r}")
    for decision_id in ctx.scope.get("policy", {}).get("boundary_decisions", []):
        if decision_id not in decisions:
            errors.append(f"scope.json policy: unknown boundary decision {decision_id!r}")

    traced_sources: set[str] = set()
    for index, link in enumerate(ctx.traceability.get("links", [])):
        if not isinstance(link, dict):
            continue
        source_id = link.get("source_unit")
        if source_id in traced_sources:
            errors.append(f"traceability.json: duplicate link for {source_id!r}")
        if isinstance(source_id, str):
            traced_sources.add(source_id)
        if source_id not in source:
            errors.append(f"traceability.json links[{index}]: unknown source {source_id!r}")
        reference_groups = [
            ("behavioral_contracts", behaviors),
            ("decisions", decisions),
            ("evidence", evidence),
            ("exceptions", exceptions),
        ]
        if ctx.target_inventory:
            reference_groups.extend((("target_units", target), ("tests", target)))
        for key, known in reference_groups:
            for identifier in link.get(key, []):
                if identifier not in known:
                    errors.append(f"traceability.json links[{index}]: unknown {key} id {identifier!r}")
    _validate_state(ctx, set(plans), errors)
    dependencies = {
        plan_id: list(plan.get("dependencies", [])) for plan_id, plan in plans.items()
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit_plan(plan_id: str, chain: list[str]) -> None:
        if plan_id in visiting:
            cycle_start = chain.index(plan_id)
            errors.append(
                "migration plans contain a dependency cycle: "
                + " -> ".join(chain[cycle_start:])
            )
            return
        if plan_id in visited:
            return
        visiting.add(plan_id)
        for dependency in dependencies.get(plan_id, []):
            visit_plan(dependency, chain + [dependency])
        visiting.remove(plan_id)
        visited.add(plan_id)

    for plan_id in sorted(dependencies):
        visit_plan(plan_id, [plan_id])
    if enforce_terminal_certificate:
        status = ctx.state.get("status")
        allowed_stages = {
            "cut_over": {"implementation", "decommission"},
            "decommissioned": {"decommission"},
        }.get(status)
        if allowed_stages:
            certificate = ctx.artifacts.get(CERTIFICATE_NAME)
            if not certificate:
                errors.append(f"state {status!r} requires a fresh completion certificate")
            else:
                if certificate.get("stage") not in allowed_stages:
                    errors.append(
                        f"state {status!r} requires certificate stage in {sorted(allowed_stages)!r}"
                    )
                fresh, freshness_errors = _certificate_fresh(ctx, certificate)
                errors.extend(f"terminal certificate: {item}" for item in freshness_errors)
    return sorted(set(errors))


def _git_revision(project_root: Path) -> str | None:
    git = project_root / ".git"
    if git.is_file():
        match = re.search(r"gitdir:\s*(.+)", git.read_text(encoding="utf-8", errors="replace"))
        if not match:
            return None
        git = (project_root / match.group(1).strip()).resolve()
    head = git / "HEAD"
    if not head.is_file():
        return None
    value = head.read_text(encoding="ascii", errors="replace").strip()
    if not value.startswith("ref: "):
        return value if re.fullmatch(r"[a-fA-F0-9]{40,64}", value) else None
    reference = value[5:]
    loose = git / reference
    if loose.is_file():
        return loose.read_text(encoding="ascii", errors="replace").strip()
    packed = git / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="ascii", errors="replace").splitlines():
            if line and not line.startswith(("#", "^")):
                digest, _, name = line.partition(" ")
                if name == reference:
                    return digest
    return None


def _normalized_config_root(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MigrationRuntimeError("config.json: source_root must be a non-empty path")
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/") or "."


def _source_root(ctx: MigrationContext) -> tuple[Path, str]:
    configured = _normalized_config_root(ctx.config.get("source_root"))
    if configured == ".":
        return ctx.project_root, configured
    path = safe_project_path(ctx.project_root, configured, label="config.json source_root")
    return path, configured


def _target_root_relative(ctx: MigrationContext) -> str | None:
    value = ctx.config.get("target_root")
    if not isinstance(value, str) or not value:
        return None
    normalized = _normalized_config_root(value)
    return None if normalized == "." else normalized


def _target_root(ctx: MigrationContext) -> Path:
    configured = _normalized_config_root(ctx.config.get("target_root"))
    if configured == ".":
        return ctx.project_root
    return safe_project_path(ctx.project_root, configured, label="config.json target_root")


def _resolve_target_path(ctx: MigrationContext, value: Any, *, label: str) -> Path:
    target_root = _target_root(ctx)
    path = safe_project_path(ctx.project_root, value, label=label)
    if not _is_relative_to(path, target_root):
        raise MigrationRuntimeError(
            f"{label}: path must resolve under config.target_root {ctx.config.get('target_root')!r}"
        )
    return path


def scan_source_tree(ctx: MigrationContext) -> tuple[list[dict[str, str]], list[str]]:
    root, configured = _source_root(ctx)
    if not root.is_dir():
        raise MigrationRuntimeError(f"configured source root is missing: {root}")
    ignored: list[str] = []
    ignored_roots: set[str] = set()
    if configured == ".":
        ignored_roots.update(MANAGED_SOURCE_EXCLUSIONS)
        target = _target_root_relative(ctx)
        if target:
            ignored_roots.add(target)
    files: list[dict[str, str]] = []
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_current = current_path.relative_to(root).as_posix()
        kept: list[str] = []
        for directory in sorted(directories):
            candidate = current_path / directory
            relative = candidate.relative_to(root).as_posix()
            if candidate.is_symlink():
                raise MigrationRuntimeError(f"source census rejects symlink directory: {relative}")
            if any(relative == item or relative.startswith(item + "/") for item in ignored_roots):
                ignored.append(relative)
            else:
                kept.append(directory)
        directories[:] = kept
        for name in sorted(names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if any(relative == item or relative.startswith(item + "/") for item in ignored_roots):
                ignored.append(relative)
                continue
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise MigrationRuntimeError(f"source census rejects symlink: {relative}")
            if not stat.S_ISREG(mode):
                raise MigrationRuntimeError(f"source census rejects non-regular entry: {relative}")
            files.append({"path": relative, "sha256": sha256_file(path)})
    return sorted(files, key=lambda item: item["path"]), sorted(set(ignored))


def source_snapshot_digest(
    source_root: str,
    revision: str | None,
    files: Sequence[Mapping[str, Any]],
    excluded_files: Sequence[Mapping[str, Any]],
) -> str:
    payload = {
        "source_root": source_root,
        "revision": revision,
        "files": sorted(files, key=lambda item: str(item.get("path"))),
        "excluded_files": sorted(excluded_files, key=lambda item: str(item.get("path"))),
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def snapshot_migration(
    migration_path: Path,
    *,
    project_root: Path | None = None,
    layout: RuntimeLayout | None = None,
) -> dict[str, Any]:
    ctx = load_context(migration_path, project_root=project_root, layout=layout)
    if not ctx.scope:
        raise MigrationRuntimeError(f"{ctx.migration_dir}: scope.json is required before snapshot")
    files, ignored = scan_source_tree(ctx)
    policy = ctx.scope.get("policy", {})
    existing_excluded = {
        item.get("path"): item
        for item in ctx.scope.get("source_snapshot", {}).get("excluded_files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if policy.get("mode") == "whole-source-root" and existing_excluded:
        raise MigrationRuntimeError("whole-source-root scope cannot contain excluded_files")
    excluded: list[dict[str, str]] = []
    included: list[dict[str, str]] = []
    for item in files:
        prior = existing_excluded.get(item["path"])
        if prior is None:
            included.append(item)
        else:
            excluded.append(
                {"path": item["path"], "sha256": item["sha256"], "exception": prior["exception"]}
            )
    missing_excluded = set(existing_excluded) - {item["path"] for item in files}
    if missing_excluded:
        raise MigrationRuntimeError(
            "excluded source paths are missing: " + ", ".join(sorted(missing_excluded))
        )
    source_root = _normalized_config_root(ctx.config.get("source_root"))
    revision = _git_revision(ctx.project_root)
    snapshot = {
        "source_root": source_root,
        "revision": revision,
        "captured_at": utc_now(),
        "digest": source_snapshot_digest(source_root, revision, included, excluded),
        "files": included,
        "excluded_files": excluded,
    }
    scope = dict(ctx.scope)
    scope["source_snapshot"] = snapshot
    schema = read_json(ctx.layout.schemas / "migration-scope.schema.json")
    errors = schema_errors(scope, schema)
    if errors:
        raise MigrationRuntimeError("snapshot would make scope.json invalid:\n  " + "\n  ".join(errors))
    write_json_atomic(ctx.migration_dir / "scope.json", scope)
    return {
        "command": "snapshot",
        "migration": str(ctx.migration_dir),
        "source_root": source_root,
        "source_files": len(included),
        "excluded_files": len(excluded),
        "ignored_managed_paths": ignored,
        "source_digest": snapshot["digest"],
        "written": "scope.json",
    }


def _current_source_errors(ctx: MigrationContext) -> list[str]:
    errors: list[str] = []
    snapshot = ctx.scope.get("source_snapshot", {})
    if not snapshot:
        return ["scope.json: missing source_snapshot"]
    try:
        actual, _ignored = scan_source_tree(ctx)
    except MigrationRuntimeError as exc:
        return [str(exc)]
    recorded = snapshot.get("files", [])
    excluded = snapshot.get("excluded_files", [])
    if snapshot.get("digest") == "0" * 64 or not recorded:
        errors.append("scope.json: placeholder or empty source snapshot is not certifiable")
    configured = _normalized_config_root(ctx.config.get("source_root"))
    if snapshot.get("source_root") != configured:
        errors.append("scope.json: source_snapshot.source_root differs from config.source_root")
    expected_digest = source_snapshot_digest(
        str(snapshot.get("source_root")), snapshot.get("revision"), recorded, excluded
    )
    if snapshot.get("digest") != expected_digest:
        errors.append("scope.json: source snapshot digest is invalid")
    recorded_entries = [
        item for item in list(recorded) + list(excluded) if isinstance(item, dict)
    ]
    recorded_path_list = [item.get("path") for item in recorded_entries]
    duplicate_paths = sorted(
        {
            path
            for path in recorded_path_list
            if isinstance(path, str) and recorded_path_list.count(path) > 1
        }
    )
    for path in duplicate_paths:
        errors.append(f"scope.json: source snapshot path is duplicated: {path}")
    actual_by_path = {item["path"]: item["sha256"] for item in actual}
    recorded_all = {
        item.get("path"): item.get("sha256")
        for item in recorded_entries
    }
    for path in sorted(set(recorded_all) - set(actual_by_path)):
        errors.append(f"source drift: recorded path is missing: {path}")
    for path in sorted(set(actual_by_path) - set(recorded_all)):
        errors.append(f"source drift: unrecorded path exists: {path}")
    for path in sorted(set(actual_by_path) & set(recorded_all)):
        if actual_by_path[path] != recorded_all[path]:
            errors.append(f"source drift: checksum changed: {path}")
    inventory_paths = {
        unit.get("path") for unit in ctx.inventory.get("units", []) if isinstance(unit, dict)
    }
    recorded_paths = {item.get("path") for item in recorded if isinstance(item, dict)}
    for path in sorted(recorded_paths - inventory_paths):
        errors.append(f"source census path has no inventory unit: {path}")
    for path in sorted(inventory_paths - recorded_paths):
        errors.append(f"inventory unit path is absent from source census: {path}")
    return errors


def _approved_exception(record: dict[str, Any], now: datetime) -> bool:
    if record.get("status") != "approved" or not record.get("approvals"):
        return False
    expiry = record.get("expires_at")
    if expiry is None:
        return True
    parsed = parse_datetime(expiry)
    return parsed is not None and parsed > now


def _accepted_decision(record: dict[str, Any]) -> bool:
    return record.get("status") == "accepted" and bool(record.get("approvals"))


def _resolve_artifact_path(ctx: MigrationContext, value: Any, *, working_directory: str | None = None) -> Path:
    relative = safe_relative_path(value, label="artifact path")
    direct = safe_project_path(ctx.project_root, relative, label="artifact path")
    if direct.exists() or not working_directory:
        return direct
    cwd_relative = safe_relative_path(
        working_directory,
        label="evidence working_directory",
        allow_dot=True,
    )
    nested_relative = relative if cwd_relative == "." else f"{cwd_relative}/{relative}"
    return safe_project_path(ctx.project_root, nested_relative, label="artifact path")


def _v3_evidence_errors(
    ctx: MigrationContext, evidence: Mapping[str, dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    for evidence_id, record in evidence.items():
        if record.get("schema_version") != "3.0":
            continue
        status_value, exit_code = record.get("status"), record.get("exit_code")
        if status_value == "pass" and exit_code != 0:
            errors.append(
                f"evidence {evidence_id}: pass status is dishonest with exit_code {exit_code!r}"
            )
        working_directory = record.get("working_directory")
        try:
            cwd = safe_project_path(
                ctx.project_root,
                working_directory,
                label=f"evidence {evidence_id} working_directory",
                allow_dot=True,
            )
            if not cwd.is_dir():
                errors.append(f"evidence {evidence_id}: working directory is missing")
        except MigrationRuntimeError as exc:
            errors.append(str(exc))
            cwd = None
        if status_value == "pass" and not record.get("artifacts"):
            errors.append(
                f"evidence {evidence_id}: passing evidence requires at least one checksummed artifact"
            )
        for artifact in record.get("artifacts", []):
            if not isinstance(artifact, dict):
                continue
            try:
                path = _resolve_artifact_path(
                    ctx,
                    artifact.get("path"),
                    working_directory=working_directory if cwd is not None else None,
                )
            except MigrationRuntimeError as exc:
                errors.append(f"evidence {evidence_id}: {exc}")
                continue
            if not path.is_file() or path.is_symlink():
                errors.append(f"evidence {evidence_id}: artifact is not a present regular file: {artifact.get('path')}")
            elif sha256_file(path) != artifact.get("sha256"):
                errors.append(f"evidence {evidence_id}: artifact checksum mismatch: {artifact.get('path')}")
        if record.get("phase") == "characterize" and record.get("slice_id") is not None:
            errors.append(f"evidence {evidence_id}: characterization evidence must not reference a slice")
        if record.get("phase") != "characterize" and record.get("slice_id") is None:
            errors.append(f"evidence {evidence_id}: {record.get('phase')!r} evidence requires a slice")
    return errors


def _current_target_errors(ctx: MigrationContext) -> list[str]:
    errors: list[str] = []
    for item in ctx.target_inventory.get("units", []):
        if not isinstance(item, dict):
            continue
        target_id = item.get("id")
        try:
            path = _resolve_target_path(ctx, item.get("path"), label=f"target {target_id} path")
        except MigrationRuntimeError as exc:
            errors.append(str(exc))
            continue
        if item.get("status") != "present":
            errors.append(f"target inventory unit is not present: {target_id}")
            continue
        checksum = item.get("sha256")
        if not isinstance(checksum, str) or not SHA256_RE.fullmatch(checksum):
            errors.append(f"present target has no concrete checksum: {target_id}")
            continue
        if isinstance(target_id, str) and target_id.startswith("TEST-") and item.get("kind") != "test":
            errors.append(f"test inventory id has non-test kind: {target_id}")
        if not path.is_file() or path.is_symlink():
            errors.append(f"target inventory path is not a present regular file: {target_id}")
        elif sha256_file(path) != checksum:
            errors.append(f"target inventory checksum drift: {target_id}")
    return errors


def target_inventory_digest(target_inventory: Mapping[str, Any]) -> str:
    payload = {
        "migration_id": target_inventory.get("migration_id"),
        "units": sorted(target_inventory.get("units", []), key=lambda item: str(item.get("id"))),
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def migration_graph_digest(
    source: MigrationContext | Mapping[str, dict[str, Any]],
    *,
    state_override: dict[str, Any] | None = None,
) -> str:
    """Digest all regular files in ``.migration`` except the certificate.

    The mapping fallback preserves the helper's original module-level API. Runtime trust
    decisions pass a context so markdown research and any other non-JSON records are bound too.
    """
    if not isinstance(source, MigrationContext):
        payload = {
            relative: artifact
            for relative, artifact in source.items()
            if relative != CERTIFICATE_NAME
        }
        if state_override is not None:
            payload["state.json"] = state_override
        return sha256_bytes(canonical_json(payload).encode("utf-8"))

    migration_dir = source.migration_dir
    if migration_dir.is_symlink():
        raise MigrationRuntimeError("migration graph digest rejects a symlink .migration directory")
    manifest: dict[str, str] = {}
    for current, directories, names in os.walk(migration_dir, topdown=True, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(directories):
            path = current_path / name
            relative = path.relative_to(migration_dir).as_posix()
            if path.is_symlink():
                raise MigrationRuntimeError(
                    f"migration graph digest rejects symlink directory: {relative}"
                )
            kept.append(name)
        directories[:] = kept
        for name in sorted(names):
            path = current_path / name
            relative = path.relative_to(migration_dir).as_posix()
            if relative == CERTIFICATE_NAME:
                continue
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise MigrationRuntimeError(f"migration graph digest rejects symlink: {relative}")
            if not stat.S_ISREG(mode):
                raise MigrationRuntimeError(
                    f"migration graph digest rejects non-regular artifact: {relative}"
                )
            if relative == "state.json" and state_override is not None:
                manifest[relative] = sha256_bytes(pretty_json(state_override).encode("utf-8"))
            else:
                manifest[relative] = sha256_file(path)
    return sha256_bytes(canonical_json(manifest).encode("utf-8"))


def _certificate_fresh(
    ctx: MigrationContext,
    certificate: Mapping[str, Any],
    *,
    stage: str | None = None,
    claim: str | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if certificate.get("generated") is not True or certificate.get("certified") is not True:
        errors.append("completion certificate is not runtime-generated and certified")
    if certificate.get("framework_version") != ctx.layout.framework_version:
        errors.append("completion certificate framework version is stale")
    if stage and certificate.get("stage") != stage:
        errors.append(f"completion certificate stage must be {stage!r}")
    if claim and certificate.get("claim") != claim:
        errors.append(f"completion certificate claim must be {claim!r}")
    expected_migration_id = ctx.scope.get("migration_id") or ctx.state.get("migration_id")
    if certificate.get("migration_id") != expected_migration_id:
        errors.append("completion certificate migration_id is stale")
    if certificate.get("state_revision") != ctx.state.get("revision"):
        errors.append("completion certificate state revision is stale")
    if certificate.get("source_digest") != ctx.scope.get("source_snapshot", {}).get("digest"):
        errors.append("completion certificate source digest is stale")
    if certificate.get("target_digest") != target_inventory_digest(ctx.target_inventory):
        errors.append("completion certificate target digest is stale")
    try:
        graph_digest = migration_graph_digest(ctx)
    except MigrationRuntimeError as exc:
        errors.append(str(exc))
    else:
        if certificate.get("migration_digest") != graph_digest:
            errors.append("completion certificate migration graph digest is stale")
    if ctx.scope:
        errors.extend(f"source freshness: {item}" for item in _current_source_errors(ctx))
    if ctx.target_inventory:
        errors.extend(f"target freshness: {item}" for item in _current_target_errors(ctx))
    groups = _artifact_groups(ctx)
    scratch: list[str] = []
    evidence = _index_by_id(groups["evidence"], "evidence", scratch)
    errors.extend(scratch)
    errors.extend(f"evidence freshness: {item}" for item in _v3_evidence_errors(ctx, evidence))
    return not errors, errors


def _audit(
    ctx: MigrationContext,
    claim: str,
    *,
    stage: str = "implementation",
) -> dict[str, Any]:
    # Audits are the recertification path. In terminal states, new evidence intentionally
    # stales the prior certificate before the replacement can be issued.
    structural = validate_context(ctx, enforce_terminal_certificate=False)
    findings = list(structural)
    warnings: list[str] = []
    groups = _artifact_groups(ctx)
    scratch: list[str] = []
    behaviors = _index_by_id(groups["behaviors"], "behaviors", scratch)
    decisions = _index_by_id(groups["decisions"], "decisions", scratch)
    plans = _index_by_id(groups["plans"], "plans", scratch)
    evidence = _index_by_id(groups["evidence"], "evidence", scratch)
    exceptions = _index_by_id(groups["exceptions"], "exceptions", scratch)
    findings.extend(scratch)
    source = {
        unit.get("id"): unit
        for unit in ctx.inventory.get("units", [])
        if isinstance(unit, dict) and isinstance(unit.get("id"), str)
    }
    scope_units_list = [item for item in ctx.scope.get("units", []) if isinstance(item, dict)]
    scope_units = {
        item.get("source_unit"): item
        for item in scope_units_list
        if isinstance(item.get("source_unit"), str)
    }
    target = {
        item.get("id"): item
        for item in ctx.target_inventory.get("units", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    traces = {
        item.get("source_unit"): item
        for item in ctx.traceability.get("links", [])
        if isinstance(item, dict) and isinstance(item.get("source_unit"), str)
    }
    now = datetime.now(timezone.utc)

    if not ctx.scope or not ctx.target_inventory:
        findings.append("legacy v2 migration graph is structurally readable but not certifiable without scope.json and target-inventory.json")
    if not any(item.get("schema_version") == "3.0" for item in evidence.values()):
        findings.append("legacy v2 evidence cannot certify completion; passing evidence-v3 records are required")
    findings.extend(_current_source_errors(ctx) if ctx.scope else [])
    findings.extend(_v3_evidence_errors(ctx, evidence))

    policy = ctx.scope.get("policy", {})
    if policy.get("required_claim") == "migrated" and claim != "migrated":
        findings.append("scope policy requires the strict migrated claim")
    boundary_ids = policy.get("boundary_decisions", [])
    if policy.get("mode") == "bounded":
        if not boundary_ids:
            findings.append("bounded scope requires at least one approved boundary decision")
        for decision_id in boundary_ids:
            if decision_id not in decisions or not _accepted_decision(decisions[decision_id]):
                findings.append(f"bounded scope decision is not accepted and approved: {decision_id}")
    elif boundary_ids:
        warnings.append("whole-source-root policy carries unnecessary boundary decisions")

    for exception_id, record in exceptions.items():
        if not _approved_exception(record, now):
            findings.append(f"exception is not approved and unexpired: {exception_id}")
    for decision_id, record in decisions.items():
        if record.get("status") == "accepted" and not record.get("approvals"):
            findings.append(f"accepted decision lacks approval: {decision_id}")

    for source_id in sorted(set(source) - set(scope_units)):
        findings.append(f"source unit has no scope disposition: {source_id}")
    for source_id in sorted(set(scope_units) - set(source)):
        findings.append(f"scope disposition has no inventory unit: {source_id}")

    dispositions: dict[str, list[str]] = {name: [] for name in ("pending", "migrated", "replaced", "removed", "retained")}
    unknown: list[str] = []
    for source_id, unit in source.items():
        scope_item = scope_units.get(source_id, {})
        disposition = scope_item.get("disposition")
        if disposition in dispositions:
            dispositions[disposition].append(source_id)
        if unit.get("reachability") == "unknown":
            unknown.append(source_id)
        if disposition == "pending":
            findings.append(f"source unit remains pending: {source_id}")
        if unit.get("reachability") == "unknown":
            findings.append(f"source unit reachability remains unknown: {source_id}")
        if disposition in MIGRATED_DISPOSITIONS:
            targets = scope_item.get("target_units", [])
            if not targets:
                findings.append(f"{disposition} source unit has no target units: {source_id}")
            if disposition == "replaced":
                decision_ids = scope_item.get("decisions", [])
                if not decision_ids:
                    findings.append(f"replaced source unit requires an accepted decision: {source_id}")
                for decision_id in decision_ids:
                    if decision_id not in decisions or not _accepted_decision(decisions[decision_id]):
                        findings.append(f"replacement decision is not accepted/approved: {source_id} -> {decision_id}")
            if unit.get("kind") == "production" and unit.get("reachability") == "reachable" and not unit.get("behaviors"):
                findings.append(f"reachable production source lacks behavioral contracts: {source_id}")
        if disposition == "removed":
            if not policy.get("allow_approved_removals"):
                findings.append(f"scope policy does not permit removal: {source_id}")
            refs = scope_item.get("exceptions", [])
            if not refs:
                findings.append(f"removed source requires an approved exception: {source_id}")
            for ref in refs:
                if ref not in exceptions or not _approved_exception(exceptions[ref], now):
                    findings.append(f"removed source exception is not approved/unexpired: {source_id} -> {ref}")
        if disposition == "retained" and not (scope_item.get("exceptions") or scope_item.get("decisions")):
            findings.append(f"retained source requires an approved decision or exception: {source_id}")
        if disposition == "retained":
            for ref in scope_item.get("exceptions", []):
                if ref not in exceptions or not _approved_exception(exceptions[ref], now):
                    findings.append(
                        f"retained source exception is not approved/unexpired: {source_id} -> {ref}"
                    )
            for ref in scope_item.get("decisions", []):
                if ref not in decisions or not _accepted_decision(decisions[ref]):
                    findings.append(
                        f"retained source decision is not accepted/approved: {source_id} -> {ref}"
                    )
        if claim == "migrated" and disposition in {"removed", "retained"}:
            findings.append(f"strict migrated claim forbids {disposition} source: {source_id}")

    excluded = ctx.scope.get("source_snapshot", {}).get("excluded_files", [])
    if excluded and (claim == "migrated" or not policy.get("allow_approved_removals")):
        findings.append("requested claim/policy forbids excluded source files")
    for item in excluded:
        ref = item.get("exception") if isinstance(item, dict) else None
        if ref not in exceptions or not _approved_exception(exceptions[ref], now):
            findings.append(f"source exclusion lacks approved/unexpired exception: {ref!r}")

    findings.extend(_current_target_errors(ctx) if ctx.target_inventory else [])

    approved_behaviors: set[str] = set()
    v3_pass = {
        evidence_id: record
        for evidence_id, record in evidence.items()
        if record.get("schema_version") == "3.0"
        and record.get("status") == "pass"
        and record.get("exit_code") == 0
    }
    for source_id, unit in source.items():
        source_behaviors = set(unit.get("behaviors", []))
        link = traces.get(source_id)
        disposition = scope_units.get(source_id, {}).get("disposition")
        if not source_behaviors and disposition not in MIGRATED_DISPOSITIONS:
            continue
        if link is None:
            findings.append(f"source behavior has no traceability link: {source_id}")
            continue
        trace_behaviors = set(link.get("behavioral_contracts", []))
        if trace_behaviors != source_behaviors:
            findings.append(f"inventory/trace behavior mismatch for {source_id}")
        for behavior_id in source_behaviors:
            contract_sources = set(behaviors.get(behavior_id, {}).get("source_units", []))
            if source_id not in contract_sources:
                findings.append(f"inventory/behavior back-reference mismatch: {source_id} -> {behavior_id}")
        if disposition in MIGRATED_DISPOSITIONS:
            if link.get("status") != "approved":
                findings.append(f"migrated/replaced source trace is not approved: {source_id}")
                continue
            targets_for_link = link.get("target_units", [])
            tests_for_link = link.get("tests", [])
            scoped_targets = set(scope_units.get(source_id, {}).get("target_units", []))
            if set(targets_for_link) != scoped_targets:
                findings.append(f"scope/trace target mapping mismatch for {source_id}")
            if not targets_for_link or not tests_for_link:
                findings.append(f"approved trace lacks target or test ids: {source_id}")
            for identifier in list(targets_for_link) + list(tests_for_link):
                if identifier not in target:
                    findings.append(f"approved trace references unresolved concrete target: {source_id} -> {identifier}")
            if unit.get("kind") == "production" and not any(
                target.get(identifier, {}).get("kind") == "production"
                for identifier in targets_for_link
            ):
                findings.append(
                    f"production source has no production target implementation: {source_id}"
                )
            refs = [v3_pass[item] for item in link.get("evidence", []) if item in v3_pass]
            characterized = set().union(
                *(set(item.get("contracts", [])) for item in refs if item.get("phase") == "characterize")
            ) if refs else set()
            verified = set().union(
                *(set(item.get("contracts", [])) for item in refs if item.get("phase") == "verify")
            ) if refs else set()
            missing_characterization = source_behaviors - characterized
            missing_verification = source_behaviors - verified
            if missing_characterization:
                findings.append(f"approved trace lacks passing v3 characterization evidence: {source_id} ({','.join(sorted(missing_characterization))})")
            if missing_verification:
                findings.append(f"approved trace lacks passing v3 verification evidence: {source_id} ({','.join(sorted(missing_verification))})")
            if not missing_characterization and not missing_verification:
                approved_behaviors.update(source_behaviors)

    for behavior_id, behavior in behaviors.items():
        if claim == "migrated" and behavior.get("known_gaps"):
            findings.append(
                f"strict migrated claim forbids known behavior gaps: {behavior_id}"
            )
        for source_id in behavior.get("source_units", []):
            unit = source.get(source_id, {})
            link = traces.get(source_id, {})
            if behavior_id not in unit.get("behaviors", []) or behavior_id not in link.get("behavioral_contracts", []):
                findings.append(f"behavior/inventory/trace back-reference mismatch: {behavior_id} -> {source_id}")

    required_sources = {
        source_id
        for source_id, item in scope_units.items()
        if item.get("disposition") in MIGRATED_DISPOSITIONS
    }
    required_behaviors = set().union(
        *(set(source[item].get("behaviors", [])) for item in required_sources if item in source)
    ) if required_sources else set()
    plan_sources = set().union(*(set(item.get("source_units", [])) for item in plans.values())) if plans else set()
    plan_behaviors = set().union(*(set(item.get("behavioral_contracts", [])) for item in plans.values())) if plans else set()
    plan_targets = set().union(*(set(item.get("target_units", [])) for item in plans.values())) if plans else set()
    required_targets = set().union(
        *(set(scope_units[item].get("target_units", [])) for item in required_sources)
    ) if required_sources else set()
    for source_id in sorted(required_sources - plan_sources):
        findings.append(f"migrated/replaced source is not owned by a plan: {source_id}")
    for behavior_id in sorted(required_behaviors - plan_behaviors):
        findings.append(f"required behavior is not owned by a plan: {behavior_id}")
    for target_id in sorted(required_targets - plan_targets):
        findings.append(f"required target is not owned by a plan: {target_id}")
    completed = set(ctx.state.get("completed_slices", []))
    for plan_id, plan in plans.items():
        if plan.get("status") != "approved":
            findings.append(f"plan is not approved: {plan_id}")
        if plan_id not in completed:
            findings.append(f"plan is not in completed_slices: {plan_id}")
    if ctx.state.get("active_slice") is not None:
        findings.append("state has an active slice")

    required_gates = set(ctx.config.get("quality_gates", {}).get("required_checks", []))
    for plan_id, plan in plans.items():
        missing_plan_gates = required_gates - set(plan.get("verification_gates", []))
        if missing_plan_gates:
            findings.append(
                f"plan {plan_id} omits configured gates: {','.join(sorted(missing_plan_gates))}"
            )
    for gate in sorted(required_gates):
        covered = set().union(
            *(
                set(record.get("contracts", []))
                for record in v3_pass.values()
                if record.get("phase") == "verify" and record.get("gate") == gate
            )
        ) if v3_pass else set()
        missing_gate_coverage = required_behaviors - covered
        if missing_gate_coverage:
            findings.append(
                f"configured gate {gate!r} lacks passing coverage for: "
                + ",".join(sorted(missing_gate_coverage))
            )

    if stage == "implementation" and ctx.state.get("status") != "approve":
        findings.append("implementation certification requires lifecycle state 'approve'")
    if stage == "decommission":
        if ctx.state.get("status") != "cut_over":
            findings.append("decommission certification requires lifecycle state 'cut_over'")
        for phase in ("cut_over", "decommission"):
            covered = set().union(
                *(set(record.get("contracts", [])) for record in v3_pass.values() if record.get("phase") == phase)
            ) if v3_pass else set()
            missing = required_behaviors - covered
            if missing:
                findings.append(f"decommission certification lacks passing {phase} evidence for: {','.join(sorted(missing))}")

    accounted_ids = {
        source_id
        for source_id, item in scope_units.items()
        if item.get("disposition") in TERMINAL_DISPOSITIONS
        and source.get(source_id, {}).get("reachability") != "unknown"
    }
    counts = {
        "source_files": len(ctx.scope.get("source_snapshot", {}).get("files", [])),
        "excluded_files": len(excluded),
        "source_units": len(source),
        "accounted_units": len(accounted_ids),
        "pending_units": len(dispositions["pending"]),
        "migrated_units": len(dispositions["migrated"]),
        "replaced_units": len(dispositions["replaced"]),
        "removed_units": len(dispositions["removed"]),
        "retained_units": len(dispositions["retained"]),
        "target_units": sum(1 for item in target if item.startswith("TGT-")),
        "test_units": sum(1 for item in target if item.startswith("TEST-")),
        "behaviors": len(behaviors),
        "approved_behaviors": len(approved_behaviors),
        "plans": len(plans),
        "approved_plans": sum(1 for item in plans.values() if item.get("status") == "approved"),
    }
    used_evidence = sorted(
        evidence_id
        for evidence_id, record in v3_pass.items()
        if record.get("phase") in ({"characterize", "verify"} if stage == "implementation" else {"characterize", "verify", "cut_over", "decommission"})
    )
    certifiable = not findings and bool(used_evidence)
    if not used_evidence:
        findings.append("no passing evidence-v3 records support the requested certificate stage")
        certifiable = False
    certificate = ctx.artifacts.get(CERTIFICATE_NAME)
    certificate_status: dict[str, Any] = {"present": bool(certificate)}
    if certificate:
        fresh, certificate_errors = _certificate_fresh(ctx, certificate)
        certificate_status.update({"fresh": fresh, "errors": certificate_errors})
        if not fresh:
            warnings.append("existing completion certificate is stale and must be reissued")
    try:
        graph_digest = migration_graph_digest(ctx)
    except MigrationRuntimeError as exc:
        findings.append(str(exc))
        graph_digest = None
        certifiable = False
    return {
        "command": "audit",
        "migration": str(ctx.migration_dir),
        "claim": claim,
        "stage": stage,
        "structurally_valid": not structural,
        "certifiable": certifiable,
        "counts": counts,
        "ids": {
            "pending": sorted(dispositions["pending"]),
            "migrated": sorted(dispositions["migrated"]),
            "replaced": sorted(dispositions["replaced"]),
            "removed": sorted(dispositions["removed"]),
            "retained": sorted(dispositions["retained"]),
            "unknown": sorted(unknown),
        },
        "evidence": used_evidence,
        "findings": sorted(set(findings)),
        "warnings": sorted(set(warnings)),
        "digests": {
            "source": ctx.scope.get("source_snapshot", {}).get("digest"),
            "target": target_inventory_digest(ctx.target_inventory) if ctx.target_inventory else None,
            "migration": graph_digest,
        },
        "certificate": certificate_status,
    }


def audit_migration(
    migration_path: Path,
    claim: str,
    *,
    stage: str = "implementation",
    project_root: Path | None = None,
    layout: RuntimeLayout | None = None,
) -> dict[str, Any]:
    return _audit(
        load_context(migration_path, project_root=project_root, layout=layout), claim, stage=stage
    )


def _build_certificate(
    ctx: MigrationContext,
    report: Mapping[str, Any],
    claim: str,
    stage: str,
    *,
    state_revision: int | None = None,
) -> dict[str, Any]:
    return {
        "$schema": "https://example.invalid/ai-migration-framework/schemas/completion-certificate.schema.json",
        "schema_version": "3.0",
        "generated": True,
        "migration_id": ctx.scope.get("migration_id") or ctx.state.get("migration_id"),
        "framework_version": ctx.layout.framework_version,
        "stage": stage,
        "claim": claim,
        "state_revision": ctx.state.get("revision") if state_revision is None else state_revision,
        "source_digest": report["digests"]["source"],
        "target_digest": report["digests"]["target"],
        "migration_digest": report["digests"]["migration"],
        "generated_at": utc_now(),
        "counts": report["counts"],
        "evidence": report["evidence"],
        "certified": True,
    }


def certify_migration(
    migration_path: Path,
    claim: str,
    stage: str,
    *,
    project_root: Path | None = None,
    layout: RuntimeLayout | None = None,
) -> dict[str, Any]:
    ctx = load_context(migration_path, project_root=project_root, layout=layout)
    report = _audit(ctx, claim, stage=stage)
    if not report["certifiable"]:
        raise MigrationRuntimeError(
            "migration is not certifiable:\n  " + "\n  ".join(report["findings"])
        )
    certificate = _build_certificate(ctx, report, claim, stage)
    schema = read_json(ctx.layout.schemas / "completion-certificate.schema.json")
    errors = schema_errors(certificate, schema)
    if errors:
        raise MigrationRuntimeError("generated certificate is invalid:\n  " + "\n  ".join(errors))
    write_json_atomic(ctx.migration_dir / CERTIFICATE_NAME, certificate)
    return certificate


def _prospective_state(ctx: MigrationContext, destination: str, reason: str) -> dict[str, Any]:
    state = json.loads(json.dumps(ctx.state))
    current = state.get("status")
    transitions = ctx.layout.state_machine.get("transitions", {})
    if destination not in transitions.get(current, []):
        allowed = ", ".join(transitions.get(current, [])) or "none"
        raise MigrationRuntimeError(
            f"invalid state transition {current!r} -> {destination!r}; allowed: {allowed}"
        )
    if current in {"blocked", "failed"} and state.get("resume_to") != destination:
        raise MigrationRuntimeError(f"state must resume to {state.get('resume_to')!r}")
    previous = current
    state["status"] = destination
    state["revision"] = state.get("revision", 0) + 1
    if destination in {"blocked", "failed"}:
        state["resume_to"] = previous
        state["blocked_by"] = [reason]
    elif previous in {"blocked", "failed"}:
        state["resume_to"] = None
        state["blocked_by"] = []
    if destination == "approve" and previous == "review":
        active = state.get("active_slice")
        if not active:
            raise MigrationRuntimeError("review -> approve requires active_slice")
        if active not in state.setdefault("completed_slices", []):
            state["completed_slices"].append(active)
        state["active_slice"] = None
    transition = {"from": previous, "to": destination, "at": utc_now(), "reason": reason}
    state["last_transition"] = transition
    state.setdefault("history", []).append(transition)
    state["validation_status"] = "valid"
    return state


def transition_migration(
    migration_path: Path,
    destination: str,
    reason: str,
    *,
    project_root: Path | None = None,
    layout: RuntimeLayout | None = None,
) -> dict[str, Any]:
    ctx = load_context(migration_path, project_root=project_root, layout=layout)
    current_errors = validate_context(ctx)
    if current_errors:
        raise MigrationRuntimeError("migration graph is invalid:\n  " + "\n  ".join(current_errors))
    certificate: dict[str, Any] | None = None
    certificate_path = ctx.migration_dir / CERTIFICATE_NAME
    required_stage = None
    if destination == "cut_over":
        required_stage = "implementation"
    elif destination == "decommissioned":
        required_stage = "decommission"
    if required_stage:
        current_certificate = ctx.artifacts.get(CERTIFICATE_NAME)
        if not current_certificate:
            raise MigrationRuntimeError(f"transition to {destination} requires a completion certificate")
        fresh, errors = _certificate_fresh(ctx, current_certificate, stage=required_stage)
        if not fresh:
            raise MigrationRuntimeError("completion certificate is not fresh:\n  " + "\n  ".join(errors))
        report = _audit(ctx, str(current_certificate.get("claim")), stage=required_stage)
        if not report["certifiable"]:
            raise MigrationRuntimeError(
                f"{required_stage} completion audit is incomplete:\n  "
                + "\n  ".join(report["findings"])
            )
        mismatches = [
            field
            for field in ("counts", "evidence")
            if current_certificate.get(field) != report.get(field)
        ]
        for field, digest_name in (
            ("source_digest", "source"),
            ("target_digest", "target"),
            ("migration_digest", "migration"),
        ):
            if current_certificate.get(field) != report.get("digests", {}).get(digest_name):
                mismatches.append(field)
        if mismatches:
            raise MigrationRuntimeError(
                "completion certificate does not match the current audit: "
                + ", ".join(sorted(mismatches))
            )
    prospective = _prospective_state(ctx, destination, reason)
    if required_stage:
        # Rebind the consumed certificate to the exact post-transition state and graph.
        certificate = dict(ctx.artifacts[CERTIFICATE_NAME])
        certificate["state_revision"] = prospective["revision"]
        certificate["migration_digest"] = migration_graph_digest(
            ctx, state_override=prospective
        )
        certificate["generated_at"] = utc_now()
        schema = read_json(ctx.layout.schemas / "completion-certificate.schema.json")
        certificate_errors = schema_errors(certificate, schema)
        if certificate_errors:
            raise MigrationRuntimeError(
                "prospective rebound certificate is invalid:\n  " + "\n  ".join(certificate_errors)
            )
    prospective_errors = validate_context(
        load_context(
            ctx.migration_dir,
            project_root=ctx.project_root,
            layout=ctx.layout,
            overrides={
                "state.json": prospective,
                **({CERTIFICATE_NAME: certificate} if certificate is not None else {}),
            },
        ),
        enforce_terminal_certificate=False,
    )
    if prospective_errors:
        raise MigrationRuntimeError(
            "prospective migration graph is invalid; state was not changed:\n  "
            + "\n  ".join(prospective_errors)
        )
    if required_stage:
        # Two files must move as one logical boundary. Write staged bytes, fsync, then replace
        # certificate first and state last: observers never see the new terminal state without
        # its rebound certificate. A failed state replace is recovered to the prior certificate.
        old_certificate = certificate_path.read_bytes()
        write_json_atomic(certificate_path, certificate)
        try:
            write_json_atomic(ctx.migration_dir / "state.json", prospective)
        except BaseException:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{CERTIFICATE_NAME}.rollback-", dir=ctx.migration_dir
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(old_certificate)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, certificate_path)
            finally:
                temporary.unlink(missing_ok=True)
            raise
    else:
        write_json_atomic(ctx.migration_dir / "state.json", prospective)
    result: dict[str, Any] = {"state": prospective}
    if certificate is not None:
        result["certificate"] = certificate
    return result


def _validation_report(ctx: MigrationContext) -> dict[str, Any]:
    errors = validate_context(ctx)
    certificate = ctx.artifacts.get(CERTIFICATE_NAME)
    certificate_status: dict[str, Any] = {"present": bool(certificate)}
    if certificate:
        fresh, certificate_errors = _certificate_fresh(ctx, certificate)
        certificate_status.update({"fresh": fresh, "errors": certificate_errors})
    return {
        "command": "validate",
        "migration": str(ctx.migration_dir),
        "valid": not errors,
        "errors": errors,
        "certificate": certificate_status,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and certify ai-migration-framework state"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate schemas and references")
    validate.add_argument("path", type=Path)
    snapshot = subparsers.add_parser("snapshot", help="refresh the deterministic source census")
    snapshot.add_argument("path", type=Path)
    snapshot.add_argument("--project-root", type=Path)
    audit = subparsers.add_parser("audit", help="audit a whole-scope completion claim")
    audit.add_argument("path", type=Path)
    audit.add_argument("--claim", choices=("accounted", "migrated"), required=True)
    audit.add_argument(
        "--stage",
        choices=("implementation", "decommission"),
        default="implementation",
    )
    certify = subparsers.add_parser("certify", help="write a certificate only after a passing audit")
    certify.add_argument("path", type=Path)
    certify.add_argument("--claim", choices=("accounted", "migrated"), required=True)
    certify.add_argument("--stage", choices=("implementation", "decommission"), required=True)
    transition = subparsers.add_parser("transition", help="apply a guarded lifecycle transition")
    transition.add_argument("--migration", type=Path, required=True)
    transition.add_argument("--to", required=True)
    transition.add_argument("--reason", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        layout = discover_runtime_layout()
        if args.command == "validate":
            report = _validation_report(load_context(args.path, layout=layout))
            print(pretty_json(report), end="")
            return 0 if report["valid"] else 1
        if args.command == "snapshot":
            print(
                pretty_json(
                    snapshot_migration(
                        args.path, project_root=args.project_root, layout=layout
                    )
                ),
                end="",
            )
            return 0
        if args.command == "audit":
            report = audit_migration(
                args.path, args.claim, stage=args.stage, layout=layout
            )
            print(pretty_json(report), end="")
            return 0 if report["certifiable"] else 1
        if args.command == "certify":
            certificate = certify_migration(args.path, args.claim, args.stage, layout=layout)
            print(pretty_json(certificate), end="")
            return 0
        if args.command == "transition":
            result = transition_migration(args.migration, args.to, args.reason, layout=layout)
            print(pretty_json(result), end="")
            return 0
    except MigrationRuntimeError as exc:
        print(pretty_json({"ok": False, "error": str(exc)}), end="")
        return 1
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
