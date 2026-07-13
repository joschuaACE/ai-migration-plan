#!/usr/bin/env python3
"""Validated compiler and safe installer for ai-migration-framework v3.

The implementation intentionally uses only the Python standard library so a clean
checkout can validate, compile, and install without bootstrapping dependencies.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK_MANIFEST = ROOT / "framework.json"
OWNERSHIP_DIR = ".migration-framework"
OWNERSHIP_FILE = f"{OWNERSHIP_DIR}/ownership.json"
OWNERSHIP_CHECKSUM_FILE = f"{OWNERSHIP_DIR}/ownership.sha256"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"\{\{(?:[#/>!]?)[^{}]+\}\}")
SAFE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class FrameworkError(RuntimeError):
    """Actionable validation, compilation, or installation failure."""


class DuplicateJsonKey(ValueError):
    """Raised when JSON input would otherwise silently replace a key."""


@dataclass(frozen=True)
class Composition:
    framework: dict[str, Any]
    source: dict[str, Any]
    target: dict[str, Any]
    pair: dict[str, Any]
    output: dict[str, Any]
    variables: dict[str, str | int | float | bool]
    legacy: bool = False
    project_overrides: dict[str, str | int | float | bool] = field(default_factory=dict)
    inferred_overrides: tuple[str, ...] = ()

    @property
    def profile_ids(self) -> dict[str, str]:
        return {
            "source": self.source["id"],
            "target": self.target["id"],
            "pair": self.pair["id"],
            "output": self.output["id"],
        }


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateJsonKey(f"duplicate object key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    except FileNotFoundError as exc:
        raise FrameworkError(f"required JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FrameworkError(f"invalid JSON in {path}:{exc.lineno}:{exc.colno}: {exc.msg}") from exc
    except DuplicateJsonKey as exc:
        raise FrameworkError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FrameworkError(f"expected a JSON object in {path}")
    return value


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        temp.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def repo_path(relative: str, *, must_exist: bool = True) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise FrameworkError(f"unsafe repository path: {relative!r}")
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise FrameworkError(f"repository path escapes the checkout: {relative!r}") from exc
    if must_exist and not resolved.is_file():
        raise FrameworkError(f"manifest references missing file: {relative}")
    return resolved


def relative_repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise FrameworkError(f"path is outside the framework checkout: {path}") from exc


def load_template_module() -> Any:
    path = ROOT / "agents" / "compile-engine.py"
    spec = importlib.util.spec_from_file_location("migration_compile_engine", path)
    if spec is None or spec.loader is None:
        raise FrameworkError(f"cannot load template engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    if not hasattr(module, "TemplateEngine") or not hasattr(module, "TemplateError"):
        raise FrameworkError("compile-engine.py must export TemplateEngine and TemplateError")
    return module


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def _resolve_local_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise FrameworkError(f"validator only supports local schema references, got {reference!r}")
    current: Any = root_schema
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise FrameworkError(f"invalid local schema reference: {reference}")
        current = current[part]
    if not isinstance(current, dict):
        raise FrameworkError(f"schema reference does not point to an object: {reference}")
    return current


def schema_errors(
    value: Any,
    schema: dict[str, Any],
    *,
    root_schema: dict[str, Any] | None = None,
    location: str = "$",
) -> list[str]:
    """Validate the JSON-Schema subset used by this repository."""
    root_schema = root_schema or schema
    if "$ref" in schema:
        return schema_errors(value, _resolve_local_ref(root_schema, schema["$ref"]), root_schema=root_schema, location=location)

    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(_json_type_matches(value, item) for item in expected_types):
            return [f"{location}: expected {' or '.join(expected_types)}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{location}: expected constant {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: {value!r} is not one of {schema['enum']!r}")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{location}: string is shorter than {schema['minLength']}")
        pattern = schema.get("pattern")
        if pattern and re.search(pattern, value) is None:
            errors.append(f"{location}: {value!r} does not match /{pattern}/")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{location}: {value!r} is not an ISO 8601 date-time")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{location}: {value} is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{location}: {value} is above maximum {schema['maximum']}")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{location}: needs at least {schema['minItems']} items")
        if schema.get("uniqueItems"):
            seen: set[str] = set()
            for index, item in enumerate(value):
                key = canonical_json(item)
                if key in seen:
                    errors.append(f"{location}[{index}]: duplicate array item")
                seen.add(key)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(schema_errors(item, item_schema, root_schema=root_schema, location=f"{location}[{index}]"))

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{location}: missing required property {key!r}")
        properties = schema.get("properties", {})
        for key, child in properties.items():
            if key in value and isinstance(child, dict):
                errors.extend(schema_errors(value[key], child, root_schema=root_schema, location=f"{location}.{key}"))
        property_names = schema.get("propertyNames")
        if isinstance(property_names, dict):
            for key in value:
                errors.extend(schema_errors(key, property_names, root_schema=root_schema, location=f"{location}.<property>"))
        additional = schema.get("additionalProperties", True)
        for key in value:
            if key in properties:
                continue
            if additional is False:
                errors.append(f"{location}: unexpected property {key!r}")
            elif isinstance(additional, dict):
                errors.extend(schema_errors(value[key], additional, root_schema=root_schema, location=f"{location}.{key}"))

    for subschema in schema.get("allOf", []):
        errors.extend(schema_errors(value, subschema, root_schema=root_schema, location=location))
    condition = schema.get("if")
    if isinstance(condition, dict) and not schema_errors(value, condition, root_schema=root_schema, location=location):
        then = schema.get("then")
        if isinstance(then, dict):
            errors.extend(schema_errors(value, then, root_schema=root_schema, location=location))
    return errors


def validate_json_file(instance_path: Path, schema_path: Path) -> list[str]:
    instance = read_json(instance_path)
    schema = read_json(schema_path)
    return [f"{relative_repo_path(instance_path)}: {error}" for error in schema_errors(instance, schema)]


def schema_definition_errors(schema: dict[str, Any], *, label: str) -> list[str]:
    """Reject misspelled/unsupported schema keywords in the repository-owned subset."""
    allowed = {
        "$schema", "$id", "$ref", "$defs", "title", "description", "type",
        "additionalProperties", "required", "properties", "const", "enum", "pattern",
        "minLength", "minItems", "uniqueItems", "minimum", "maximum", "items",
        "propertyNames", "allOf", "if", "then", "format",
    }
    valid_types = {"null", "boolean", "integer", "number", "string", "array", "object"}
    errors: list[str] = []

    def walk(node: Any, location: str) -> None:
        if not isinstance(node, dict):
            errors.append(f"{label} {location}: schema node must be an object")
            return
        for keyword in node:
            if keyword not in allowed:
                errors.append(f"{label} {location}: unsupported or misspelled schema keyword {keyword!r}")
        declared_type = node.get("type")
        if declared_type is not None:
            types = declared_type if isinstance(declared_type, list) else [declared_type]
            if not types or any(item not in valid_types for item in types) or len(types) != len(set(types)):
                errors.append(f"{label} {location}.type: invalid or duplicate JSON types")
        pattern = node.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                errors.append(f"{label} {location}.pattern: must be a string")
            else:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(f"{label} {location}.pattern: invalid regular expression: {exc}")
        required = node.get("required")
        if required is not None and (
            not isinstance(required, list)
            or not all(isinstance(item, str) for item in required)
            or len(required) != len(set(required))
        ):
            errors.append(f"{label} {location}.required: must be a duplicate-free string array")
        reference = node.get("$ref")
        if reference is not None:
            if not isinstance(reference, str) or not reference.startswith("#/"):
                errors.append(f"{label} {location}.$ref: only local references are supported")
            else:
                try:
                    _resolve_local_ref(schema, reference)
                except FrameworkError as exc:
                    errors.append(f"{label} {location}.$ref: {exc}")
        properties = node.get("properties", {})
        if not isinstance(properties, dict):
            errors.append(f"{label} {location}.properties: must be an object")
        else:
            for name, child in properties.items():
                walk(child, f"{location}.properties.{name}")
        definitions = node.get("$defs", {})
        if not isinstance(definitions, dict):
            errors.append(f"{label} {location}.$defs: must be an object")
        else:
            for name, child in definitions.items():
                walk(child, f"{location}.$defs.{name}")
        for keyword in ("items", "propertyNames", "if", "then"):
            if keyword in node:
                walk(node[keyword], f"{location}.{keyword}")
        additional = node.get("additionalProperties")
        if additional is not None and not isinstance(additional, bool):
            walk(additional, f"{location}.additionalProperties")
        all_of = node.get("allOf", [])
        if not isinstance(all_of, list):
            errors.append(f"{label} {location}.allOf: must be an array")
        else:
            for index, child in enumerate(all_of):
                walk(child, f"{location}.allOf[{index}]")

    walk(schema, "$")
    return errors


def find_profile(kind: str, profile_id: str) -> dict[str, Any]:
    plural = {"source": "sources", "target": "targets", "pair": "pairs", "output": "outputs"}[kind]
    path = ROOT / "docs" / "profiles" / plural / profile_id / "profile.json"
    profile = read_json(path)
    if profile.get("kind") != kind:
        raise FrameworkError(f"{relative_repo_path(path)} declares kind {profile.get('kind')!r}, expected {kind!r}")
    if profile.get("id") != profile_id:
        raise FrameworkError(f"{relative_repo_path(path)} declares id {profile.get('id')!r}, expected {profile_id!r}")
    return profile


def load_v1_pair(
    pair_id: str,
    output_id: str,
    overrides: Mapping[str, str | int | float | bool] | None = None,
) -> Composition:
    """Compatibility loader for structurally valid v1 flat pair data."""
    framework = read_json(FRAMEWORK_MANIFEST)
    legacy_path = repo_path(framework["compatibility"]["v1_variables"])
    legacy = read_json(legacy_path)
    pair_data = legacy.get("pairs", {}).get(pair_id)
    declared = legacy.get("variables", {})
    if not isinstance(pair_data, dict) or not pair_data:
        raise FrameworkError(f"unknown migration pair: {pair_id}")
    if not isinstance(declared, dict):
        raise FrameworkError("v1 variables.json has no variable contract")
    unknown = sorted(set(pair_data) - set(declared))
    if unknown:
        raise FrameworkError(f"v1 pair {pair_id!r} contains undeclared variables: {', '.join(unknown)}")
    variables = dict(pair_data)
    aliases = framework["compatibility"]["deprecated_variable_aliases"]
    for old, new in aliases.items():
        if old in variables:
            variables.setdefault(new, variables[old])
            variables.pop(old, None)
    source_id = str(variables.get("source_language_id", ""))
    target_id = str(variables.get("target_language_id", ""))
    source = find_profile("source", source_id)
    target = find_profile("target", target_id)
    output = find_profile("output", output_id)
    legacy_values = dict(variables)
    variables = {}
    variables.update(source.get("variables", {}))
    variables.update(target.get("variables", {}))
    variables.update(legacy_values)
    variables.update(output.get("variables", {}))
    variables["pair_id"] = pair_id
    variables.update(overrides or {})
    pair = {
        "kind": "pair", "id": pair_id, "source": source_id, "target": target_id,
        "documents": sorted(
            relative_repo_path(path) for path in (ROOT / "docs" / "pairs" / pair_id).glob("*.md")
        ),
        "variables": {"pair_id": pair_id}, "capabilities": [], "requires": {},
    }
    composition = Composition(
        framework,
        source,
        target,
        pair,
        output,
        variables,
        legacy=True,
        project_overrides=dict(overrides or {}),
    )
    validate_composition(composition)
    return composition


def parse_overrides(items: Sequence[str]) -> dict[str, str | int | float | bool]:
    result: dict[str, str | int | float | bool] = {}
    for item in items:
        if "=" not in item:
            raise FrameworkError(f"project override must be KEY=VALUE, got {item!r}")
        key, raw = item.split("=", 1)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise FrameworkError(f"invalid project override key: {key!r}")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        result[key] = parsed
    validate_project_overrides(result)
    return result


def validate_project_overrides(
    overrides: Mapping[str, str | int | float | bool],
) -> None:
    protected = {"source_language_id", "target_language_id", "pair_id", "output_profile"}
    contract = read_json(FRAMEWORK_MANIFEST).get("variable_contract", {})
    for key, value in overrides.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise FrameworkError(f"invalid project override key: {key!r}")
        if key not in contract:
            raise FrameworkError(
                f"project override {key!r} is not declared by the typed variable contract"
            )
        if key in protected:
            raise FrameworkError(f"profile identity variable cannot be overridden: {key}")
        if not isinstance(value, (str, int, float, bool)) or value is None:
            raise FrameworkError(f"project override {key!r} must be a scalar value")
        if not _json_type_matches(value, contract[key]["type"]):
            raise FrameworkError(
                f"project override {key!r} must be {contract[key]['type']}, "
                f"got {type(value).__name__}"
            )
        if isinstance(value, str):
            if any(marker in value for marker in ("\x00", "\n", "\r", "{{", "}}")):
                raise FrameworkError(
                    f"project override {key!r} contains unsafe control or template syntax"
                )
            if key.endswith("_command") and (re.search(r"[;&|`<>]", value) or "$(" in value):
                raise FrameworkError(
                    f"project command override {key!r} contains unsupported shell control syntax"
                )


def parse_unsets(items: Sequence[str]) -> tuple[str, ...]:
    protected = {"source_language_id", "target_language_id", "pair_id", "output_profile"}
    contract = read_json(FRAMEWORK_MANIFEST).get("variable_contract", {})
    result: list[str] = []
    for key in items:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise FrameworkError(f"invalid project override key to unset: {key!r}")
        if key not in contract:
            raise FrameworkError(f"cannot unset undeclared project override {key!r}")
        if key in protected:
            raise FrameworkError(f"profile identity variable cannot be unset: {key}")
        if key in result:
            raise FrameworkError(f"project override may be unset only once: {key}")
        result.append(key)
    return tuple(result)


def compose_profiles(
    pair_id: str | None,
    output_id: str | None,
    overrides: Mapping[str, str | int | float | bool] | None = None,
) -> Composition:
    framework = read_json(FRAMEWORK_MANIFEST)
    validate_project_overrides(overrides or {})
    pair_id = pair_id or framework["default_pair"]
    pair_id = framework.get("compatibility", {}).get("accepted_pair_aliases", {}).get(pair_id, pair_id)
    output_id = output_id or framework["default_output_profile"]
    if not SAFE_ID_RE.fullmatch(pair_id) or not SAFE_ID_RE.fullmatch(output_id):
        raise FrameworkError("profile identifiers must be lowercase kebab-case")
    try:
        pair = find_profile("pair", pair_id)
    except FrameworkError as exc:
        if "does not exist" not in str(exc):
            raise
        return load_v1_pair(pair_id, output_id, overrides)
    source = find_profile("source", pair["source"])
    target = find_profile("target", pair["target"])
    output = find_profile("output", output_id)

    variables: dict[str, str | int | float | bool] = {}
    for layer_name, layer in (("source", source), ("target", target), ("pair", pair), ("output", output)):
        layer_variables = layer.get("variables", {})
        if not isinstance(layer_variables, dict):
            raise FrameworkError(f"{layer_name} profile variables must be an object")
        for key, value in layer_variables.items():
            if not isinstance(value, (str, int, float, bool)) or value is None:
                raise FrameworkError(f"profile variable {key!r} must be a scalar")
            variables[key] = value
    variables.update(overrides or {})
    composition = Composition(
        framework,
        source,
        target,
        pair,
        output,
        variables,
        project_overrides=dict(overrides or {}),
    )
    validate_composition(composition)
    return composition


def validate_composition(composition: Composition) -> None:
    profiles = {
        "source": composition.source,
        "target": composition.target,
        "pair": composition.pair,
        "output": composition.output,
    }
    missing_variables = sorted(set(composition.framework["required_variables"]) - set(composition.variables))
    if missing_variables:
        raise FrameworkError(f"profile composition is missing variables: {', '.join(missing_variables)}")
    contract = composition.framework.get("variable_contract", {})
    if set(contract) != set(composition.framework["required_variables"]):
        raise FrameworkError("framework variable_contract must declare exactly every required variable")
    for name, definition in contract.items():
        if not _json_type_matches(composition.variables[name], definition["type"]):
            raise FrameworkError(
                f"profile variable {name!r} must be {definition['type']}, got {type(composition.variables[name]).__name__}"
            )
    for layer_name, profile in profiles.items():
        for name in profile.get("variables", {}):
            if name not in contract:
                raise FrameworkError(f"{layer_name} profile declares unknown variable {name!r}")
            expected_owner = contract[name]["owner"]
            if expected_owner != layer_name:
                raise FrameworkError(
                    f"{layer_name} profile cannot own variable {name!r}; typed contract owner is {expected_owner}"
                )
    for owner_name in ("pair", "output"):
        owner = profiles[owner_name]
        for required_kind, required_caps in owner.get("requires", {}).items():
            provider = profiles.get(required_kind)
            if provider is None:
                raise FrameworkError(f"{owner_name} profile requires unknown provider kind {required_kind!r}")
            missing = sorted(set(required_caps) - set(provider.get("capabilities", [])))
            if missing:
                raise FrameworkError(
                    f"{owner_name} profile {owner['id']!r} requires missing {required_kind} capabilities: {', '.join(missing)}"
                )
    for profile in profiles.values():
        for document in profile.get("documents", []):
            repo_path(document)
    target_documents = composition.output.get("target_documents", {}).get(composition.target["id"])
    if not target_documents:
        raise FrameworkError(
            f"output profile {composition.output['id']!r} has no documents for target {composition.target['id']!r}"
        )
    for document in target_documents:
        repo_path(document)


def selected_documents(composition: Composition) -> list[tuple[str, str]]:
    """Return (output-relative-path, source-relative-path) in stable order."""
    groups: list[tuple[str, Iterable[str]]] = [
        ("standards/generic", composition.framework["generic_documents"]),
        ("standards/source", composition.source["documents"]),
        ("standards/target", composition.target["documents"]),
        ("standards/pair", composition.pair["documents"]),
        ("standards/output", composition.output["documents"]),
        ("standards/output-target", composition.output["target_documents"][composition.target["id"]]),
        ("provenance", composition.framework.get("provenance_documents", [])),
        ("workflows", composition.framework["workflow_documents"]),
        ("hooks", composition.framework["hook_documents"]),
    ]
    result: list[tuple[str, str]] = []
    destinations: set[str] = set()
    for destination_dir, documents in groups:
        for source in sorted(documents):
            destination = f"{destination_dir}/{Path(source).name}"
            if destination in destinations:
                raise FrameworkError(f"two selected documents map to the same bundle path: {destination}")
            destinations.add(destination)
            result.append((destination, source))
    return result


def load_adapter_capabilities(adapter: str) -> dict[str, Any]:
    if adapter == "portable":
        return {
            "schema_version": "2.0",
            "adapter": "portable",
            "adapter_version": "2.0.0",
            "packaging": ["standards", "workflows", "hooks", "schemas", "provenance"],
            "hook_capabilities": {"command": False, "agent_judgment": False, "events": [], "unsupported_policy": "warn-and-instruct"},
        }
    if adapter not in {"kiro", "claude", "codex"}:
        raise FrameworkError(f"unknown adapter: {adapter}")
    path = ROOT / "agents" / adapter / "capabilities.json"
    capabilities = read_json(path)
    if capabilities.get("adapter") != adapter:
        raise FrameworkError(f"adapter capability manifest has wrong adapter id: {path}")
    return capabilities


def compile_bundle(
    composition: Composition,
    output_dir: Path,
    *,
    adapter: str = "portable",
) -> dict[str, Any]:
    """Compile a complete bundle in staging and atomically promote it."""
    output_dir = output_dir.expanduser().resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.stage-", dir=output_dir.parent))
    backup: Path | None = None
    module = load_template_module()
    engine = module.TemplateEngine(composition.variables, docs_root=ROOT / "docs")
    source_checksums: dict[str, str] = {}
    generated: dict[str, str] = {}
    try:
        composition_sources = [
            FRAMEWORK_MANIFEST,
            ROOT / "agents" / "compile-engine.py",
            ROOT / "agents" / "framework.py",
            ROOT / "docs" / "profiles" / "sources" / composition.source["id"] / "profile.json",
            ROOT / "docs" / "profiles" / "targets" / composition.target["id"] / "profile.json",
            ROOT / "docs" / "profiles" / "pairs" / composition.pair["id"] / "profile.json",
            ROOT / "docs" / "profiles" / "outputs" / composition.output["id"] / "profile.json",
        ]
        if adapter != "portable":
            composition_sources.append(ROOT / "agents" / adapter / "capabilities.json")
        for source in composition_sources:
            if source.is_file():
                source_checksums[relative_repo_path(source)] = sha256_file(source)
        for destination, source_relative in selected_documents(composition):
            source = repo_path(source_relative)
            source_checksums[source_relative] = sha256_file(source)
            destination_path = stage / destination
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                rendered = engine.render(source.read_text(encoding="utf-8"), source_path=source)
            except module.TemplateError as exc:
                raise FrameworkError(f"template compilation failed for {source_relative}: {exc}") from exc
            if TOKEN_RE.search(rendered):
                token = TOKEN_RE.search(rendered)
                raise FrameworkError(f"unresolved template token in {source_relative}: {token.group(0) if token else ''}")
            if not rendered.endswith("\n"):
                rendered += "\n"
            destination_path.write_text(rendered, encoding="utf-8", newline="\n")

        for schema_relative in sorted(composition.framework["schemas"]):
            source = repo_path(schema_relative)
            source_checksums[schema_relative] = sha256_file(source)
            destination = stage / "schemas" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        for source in sorted((ROOT / "docs" / "state" / "templates").glob("*.json")):
            source_relative = relative_repo_path(source)
            source_checksums[source_relative] = sha256_file(source)
            destination = stage / "state" / "templates" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

        for path in sorted(stage.rglob("*")):
            if path.is_file():
                generated[path.relative_to(stage).as_posix()] = sha256_file(path)
        adapter_capabilities = load_adapter_capabilities(adapter)
        manifest_without_digest = {
            "$schema": "schemas/bundle-manifest.schema.json",
            "schema_version": "3.0",
            "framework_version": composition.framework["framework_version"],
            "bundle_format_version": "3.0",
            "profiles": composition.profile_ids,
            "adapter": adapter,
            "adapter_capabilities": adapter_capabilities,
            "variables": dict(sorted(composition.variables.items())),
            "project_overrides": dict(sorted(composition.project_overrides.items())),
            "inferred_overrides": sorted(composition.inferred_overrides),
            "source_checksums": dict(sorted(source_checksums.items())),
            "generated_files": dict(sorted(generated.items())),
        }
        manifest = dict(manifest_without_digest)
        manifest["bundle_digest"] = sha256_bytes(canonical_json(manifest_without_digest).encode("utf-8"))
        (stage / "manifest.json").write_text(pretty_json(manifest), encoding="utf-8", newline="\n")

        if output_dir.exists():
            backup = output_dir.with_name(f".{output_dir.name}.backup-{uuid.uuid4().hex}")
            os.replace(output_dir, backup)
        os.replace(stage, output_dir)
        if backup:
            shutil.rmtree(backup)
        return manifest
    except Exception:
        if output_dir.exists() and backup is not None:
            shutil.rmtree(output_dir, ignore_errors=True)
        if backup is not None and backup.exists():
            os.replace(backup, output_dir)
        shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    bundle_dir = bundle_dir.resolve()
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise FrameworkError(f"bundle manifest is missing or unsafe: {manifest_path}")
    manifest = read_json(manifest_path)
    schema_version = manifest.get("schema_version")
    schema_name = {
        "2.0": "bundle-manifest-v2.schema.json",
        "3.0": "bundle-manifest.schema.json",
    }.get(schema_version)
    if schema_name is None:
        raise FrameworkError(f"unsupported bundle schema version {schema_version!r}")
    schema = read_json(ROOT / "schemas" / schema_name)
    errors = schema_errors(manifest, schema)
    if errors:
        raise FrameworkError("invalid bundle manifest:\n  " + "\n  ".join(errors))

    actual_files: set[str] = set()
    for path in sorted(bundle_dir.rglob("*")):
        relative = path.relative_to(bundle_dir).as_posix()
        if path.is_symlink():
            raise FrameworkError(f"bundle contains an unsafe symlink: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise FrameworkError(f"bundle contains a non-regular entry: {relative}")
        actual_files.add(relative)
    expected_files = set(manifest["generated_files"]) | {"manifest.json"}
    missing = sorted(expected_files - actual_files)
    unlisted = sorted(actual_files - expected_files)
    if missing or unlisted:
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unlisted:
            details.append("unlisted: " + ", ".join(unlisted))
        raise FrameworkError("bundle file inventory mismatch (" + "; ".join(details) + ")")

    for relative, expected in manifest["generated_files"].items():
        path = safe_join(bundle_dir, relative)
        actual = sha256_file(path)
        if actual != expected:
            raise FrameworkError(f"bundle file checksum mismatch: {relative}")
    digest_input = {key: value for key, value in manifest.items() if key != "bundle_digest"}
    actual_digest = sha256_bytes(canonical_json(digest_input).encode("utf-8"))
    if actual_digest != manifest["bundle_digest"]:
        raise FrameworkError("bundle manifest digest mismatch")
    return manifest


def safe_join(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or relative in {"", "."}:
        raise FrameworkError(f"unsafe relative path: {relative!r}")
    result = root.joinpath(rel)
    resolved_parent = result.parent.resolve(strict=False)
    try:
        resolved_parent.relative_to(root.resolve())
    except ValueError as exc:
        raise FrameworkError(f"path escapes target root through a symlink: {relative}") from exc
    return result


def _bundle_files(bundle: Path, prefix: str) -> list[Path]:
    directory = bundle / prefix
    if not directory.exists():
        return []
    return sorted(path for path in directory.rglob("*") if path.is_file())


def _first_description(path: Path) -> str:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            return line[:200].replace('"', "'")
    return "Migration framework guidance"


def run_hook_parser(adapter: str, hooks_dir: Path, *, strict: bool = False) -> tuple[bytes, str]:
    command = [
        "bash",
        str(ROOT / "agents" / "parse-hooks.sh"),
        adapter,
        str(hooks_dir),
        "app",
    ]
    if strict:
        command.append("--strict")
    process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if process.returncode:
        detail = process.stderr.strip() or process.stdout.strip() or f"exit {process.returncode}"
        raise FrameworkError(f"{adapter} hook generation failed: {detail}")
    try:
        parsed = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise FrameworkError(f"{adapter} hook generator returned invalid JSON: {exc.msg}") from exc
    return pretty_json(parsed).encode("utf-8"), process.stderr.strip()


def _common_install_files(bundle: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {
        f"{OWNERSHIP_DIR}/bundle-manifest.json": (bundle / "manifest.json").read_bytes(),
    }
    for prefix in ("schemas", "state/templates", "provenance"):
        for source in _bundle_files(bundle, prefix):
            relative = source.relative_to(bundle).as_posix()
            files[f"{OWNERSHIP_DIR}/{relative}"] = source.read_bytes()
    return files


def _codex_guide(manifest: Mapping[str, Any], hook_warning: str) -> str:
    warning = ""
    if hook_warning:
        warning = (
            "\n## Hook capability notice\n\n"
            "Some portable judgment hooks are instructions rather than enforceable Codex hooks. "
            "See `.codex/hooks.json` metadata and apply those checks during review.\n"
        )
    return f"""# Migration Framework

This project is managed by ai-migration-framework {manifest['framework_version']}.
The selected migration is {manifest['profiles']['source']} → {manifest['profiles']['target']}
with the `{manifest['profiles']['output']}` output profile.

## Knowledge base

- `docs/standards/` contains generic, source, target, pair, and output-profile rules.
- `docs/skills/` contains portable lifecycle workflows.
- `.migration-framework/schemas/` defines all machine-validated state artifacts.

Read the relevant standards and workflow before changing migration code. Verification
must create reproducible evidence; semantic fidelity and design judgment belong to review.
{warning}"""


def render_codex_install(bundle: Path, manifest: Mapping[str, Any], strict_hooks: bool) -> dict[str, bytes]:
    files = _common_install_files(bundle)
    for source in _bundle_files(bundle, "standards"):
        relative = source.relative_to(bundle / "standards").as_posix()
        files[f"docs/standards/{relative}"] = source.read_bytes()
    for source in _bundle_files(bundle, "workflows"):
        files[f"docs/skills/{source.name}"] = source.read_bytes()
    hook_json, warning = run_hook_parser("codex", bundle / "hooks", strict=strict_hooks)
    files[".codex/hooks.json"] = hook_json
    files["AGENTS.md"] = _codex_guide(manifest, warning).encode("utf-8")
    return files


def render_claude_install(bundle: Path, manifest: Mapping[str, Any], strict_hooks: bool) -> dict[str, bytes]:
    files = _common_install_files(bundle)
    sections = [
        "# Migration Framework\n\n",
        f"Managed by ai-migration-framework {manifest['framework_version']} for "
        f"{manifest['profiles']['source']} → {manifest['profiles']['target']} "
        f"({manifest['profiles']['output']}).\n\n",
        "## Standards\n\n",
    ]
    for source in _bundle_files(bundle, "standards"):
        sections.append(source.read_text(encoding="utf-8").rstrip() + "\n\n---\n\n")
    sections.append("## Workflows\n\n")
    for source in _bundle_files(bundle, "workflows"):
        sections.append(source.read_text(encoding="utf-8").rstrip() + "\n\n")
    files["CLAUDE.md"] = "".join(sections).encode("utf-8")
    hook_json, _warning = run_hook_parser("claude", bundle / "hooks", strict=strict_hooks)
    files[".claude/settings.json"] = hook_json
    return files


def render_kiro_install(bundle: Path, manifest: Mapping[str, Any], strict_hooks: bool) -> dict[str, bytes]:
    del manifest
    files = _common_install_files(bundle)
    for source in _bundle_files(bundle, "standards"):
        relative = source.relative_to(bundle / "standards")
        flattened = "-".join(relative.with_suffix("").parts) + ".md"
        inclusion = "always" if relative.parts[0] == "generic" else "auto"
        title = source.stem.replace("-", " ")
        header = (
            "---\n"
            f"inclusion: {inclusion}\n"
            f"name: {json.dumps(title, ensure_ascii=False)}\n"
            f"description: {json.dumps(_first_description(source), ensure_ascii=False)}\n"
            "---\n\n"
        )
        files[f".kiro/steering/{flattened}"] = (header + source.read_text(encoding="utf-8")).encode("utf-8")
    for source in _bundle_files(bundle, "workflows"):
        skill_name = source.stem
        header = (
            "---\n"
            f"name: {skill_name}\n"
            f"description: {json.dumps(_first_description(source), ensure_ascii=False)}\n"
            "---\n\n"
        )
        files[f".kiro/skills/{skill_name}/SKILL.md"] = (header + source.read_text(encoding="utf-8")).encode("utf-8")
    hook_json, _warning = run_hook_parser("kiro", bundle / "hooks", strict=strict_hooks)
    files[".kiro/hooks/migration-quality.json"] = hook_json
    return files


def render_install_files(
    adapter: str,
    bundle: Path,
    manifest: Mapping[str, Any],
    *,
    strict_hooks: bool,
) -> dict[str, bytes]:
    renderers = {
        "codex": render_codex_install,
        "claude": render_claude_install,
        "kiro": render_kiro_install,
    }
    try:
        files = renderers[adapter](bundle, manifest, strict_hooks)
    except KeyError as exc:
        raise FrameworkError(f"unsupported installation adapter: {adapter}") from exc
    for relative in files:
        safe_join(Path("/tmp/migration-framework-safety-root"), relative)
        if relative == OWNERSHIP_FILE:
            raise FrameworkError("renderer must not generate ownership metadata directly")
    validate_rendered_install(files, adapter)
    return dict(sorted(files.items()))


def validate_rendered_install(files: Mapping[str, bytes], adapter: str) -> None:
    for relative, data in files.items():
        try:
            text_value = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FrameworkError(f"generated adapter file is not UTF-8: {relative}: {exc}") from exc
        token = TOKEN_RE.search(text_value)
        if token:
            raise FrameworkError(f"generated adapter file contains unresolved token {token.group(0)!r}: {relative}")
        if relative.endswith(".json"):
            try:
                parsed = json.loads(text_value)
            except json.JSONDecodeError as exc:
                raise FrameworkError(f"generated adapter JSON is invalid: {relative}: {exc.msg}") from exc
            if not isinstance(parsed, dict):
                raise FrameworkError(f"generated adapter JSON must contain an object: {relative}")
        if adapter == "kiro" and (
            relative.startswith(".kiro/steering/") or relative.startswith(".kiro/skills/")
        ):
            lines = text_value.splitlines()
            try:
                closing = lines.index("---", 1)
            except ValueError as exc:
                raise FrameworkError(f"generated Kiro Markdown has no closing frontmatter: {relative}") from exc
            if not lines or lines[0] != "---" or closing < 2:
                raise FrameworkError(f"generated Kiro Markdown has malformed frontmatter: {relative}")
            frontmatter = lines[1:closing]
            required = {"name", "description"}
            if relative.startswith(".kiro/steering/"):
                required.add("inclusion")
            present = {line.split(":", 1)[0] for line in frontmatter if ":" in line}
            missing = required - present
            if missing:
                raise FrameworkError(f"generated Kiro frontmatter is missing {sorted(missing)}: {relative}")


def _file_checksum_or_none(path: Path) -> str | None:
    if not path.exists() and not path.is_symlink():
        return None
    if not path.is_file() or path.is_symlink():
        return "<not-a-regular-file>"
    return sha256_file(path)


def load_ownership(target: Path) -> dict[str, Any] | None:
    path = target / OWNERSHIP_FILE
    if not path.exists():
        if (target / OWNERSHIP_CHECKSUM_FILE).exists():
            raise FrameworkError(f"orphaned managed ownership checksum: {target / OWNERSHIP_CHECKSUM_FILE}")
        return None
    checksum_path = target / OWNERSHIP_CHECKSUM_FILE
    if not checksum_path.is_file() or checksum_path.is_symlink():
        raise FrameworkError(f"managed ownership checksum is missing or unsafe: {checksum_path}")
    expected_checksum = checksum_path.read_text(encoding="ascii").strip()
    if not SHA256_RE.fullmatch(expected_checksum) or sha256_file(path) != expected_checksum:
        raise FrameworkError(f"managed ownership metadata was modified or corrupted: {path}")
    ownership = read_json(path)
    schema_version = ownership.get("schema_version")
    schema_name = {
        "2.0": "installation-ownership-v2.schema.json",
        "3.0": "installation-ownership.schema.json",
    }.get(schema_version)
    if schema_name is None:
        raise FrameworkError(
            f"unsupported managed ownership schema version {schema_version!r}: {path}"
        )
    schema = read_json(ROOT / "schemas" / schema_name)
    errors = schema_errors(ownership, schema)
    if errors:
        raise FrameworkError(f"invalid framework ownership metadata {path}: {'; '.join(errors)}")
    adapter = ownership["adapter"]
    allowed_prefixes = {
        "kiro": (".kiro/steering/", ".kiro/skills/", ".kiro/hooks/", f"{OWNERSHIP_DIR}/"),
        "claude": ("CLAUDE.md", ".claude/settings.json", f"{OWNERSHIP_DIR}/"),
        "codex": ("AGENTS.md", ".codex/hooks.json", "docs/standards/", "docs/skills/", f"{OWNERSHIP_DIR}/"),
    }[adapter]
    for relative, checksum in ownership["files"].items():
        if not isinstance(relative, str) or not isinstance(checksum, str) or not SHA256_RE.fullmatch(checksum):
            raise FrameworkError(f"invalid owned file entry in {path}: {relative!r}")
        if not any(
            relative.startswith(prefix) if prefix.endswith("/") else relative == prefix
            for prefix in allowed_prefixes
        ):
            raise FrameworkError(f"ownership metadata contains a path outside the {adapter} adapter surface: {relative}")
        safe_join(target, relative)
    return ownership


def load_installed_bundle_manifest(
    target: Path, ownership: Mapping[str, Any]
) -> dict[str, Any]:
    relative = f"{OWNERSHIP_DIR}/bundle-manifest.json"
    path = safe_join(target, relative)
    expected = ownership.get("files", {}).get(relative)
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        raise FrameworkError(f"managed ownership metadata has no valid checksum for {relative}")
    if not path.is_file() or path.is_symlink() or sha256_file(path) != expected:
        raise FrameworkError(f"installed bundle manifest was modified, removed, or corrupted: {path}")
    manifest = read_json(path)
    schema_version = manifest.get("schema_version")
    schema_name = {
        "2.0": "bundle-manifest-v2.schema.json",
        "3.0": "bundle-manifest.schema.json",
    }.get(schema_version)
    if schema_name is None:
        raise FrameworkError(
            f"unsupported installed bundle schema version {schema_version!r}: {path}"
        )
    errors = schema_errors(manifest, read_json(ROOT / "schemas" / schema_name))
    if errors:
        raise FrameworkError(f"invalid installed bundle manifest {path}: {'; '.join(errors)}")
    digest_input = {key: value for key, value in manifest.items() if key != "bundle_digest"}
    actual_digest = sha256_bytes(canonical_json(digest_input).encode("utf-8"))
    if actual_digest != manifest["bundle_digest"]:
        raise FrameworkError(f"installed bundle manifest digest mismatch: {path}")
    for field in ("adapter", "profiles", "bundle_digest", "framework_version"):
        if ownership.get(field) != manifest.get(field):
            raise FrameworkError(
                f"managed ownership {field} does not match the installed bundle manifest"
            )
    if ownership.get("schema_version") == "3.0" and manifest.get("schema_version") == "3.0":
        for field in ("project_overrides", "inferred_overrides"):
            ownership_value = ownership.get(field, [] if field == "inferred_overrides" else {})
            manifest_value = manifest.get(field, [] if field == "inferred_overrides" else {})
            if ownership_value != manifest_value:
                raise FrameworkError(
                    f"managed ownership {field} does not match the installed bundle manifest"
                )
    return manifest


def manifest_project_overrides(
    manifest: Mapping[str, Any],
) -> tuple[dict[str, str | int | float | bool], tuple[str, ...]]:
    """Return explicit/inferred overrides, normalizing a verified v2 manifest."""
    if manifest.get("schema_version") == "3.0":
        overrides = dict(manifest.get("project_overrides", {}))
        inferred = tuple(sorted(manifest.get("inferred_overrides", [])))
        missing = sorted(set(inferred) - set(overrides))
        if missing:
            raise FrameworkError(
                "bundle inferred_overrides are not present in project_overrides: "
                + ", ".join(missing)
            )
        composition = compose_profiles(
            manifest["profiles"]["pair"], manifest["profiles"]["output"], overrides
        )
        for kind in ("source", "target", "pair", "output"):
            if manifest["profiles"].get(kind) != composition.profile_ids[kind]:
                raise FrameworkError(
                    f"bundle {kind} profile {manifest['profiles'].get(kind)!r} is incompatible "
                    f"with the current catalog value {composition.profile_ids[kind]!r}"
                )
        if canonical_json(manifest["variables"]) != canonical_json(composition.variables):
            raise FrameworkError(
                "bundle variables do not exactly match the composition derived from "
                "profiles and project_overrides"
            )
        return overrides, inferred

    profiles = manifest["profiles"]
    baseline = compose_profiles(profiles["pair"], profiles["output"])
    for kind in ("source", "target", "pair", "output"):
        if profiles.get(kind) != baseline.profile_ids[kind]:
            raise FrameworkError(
                f"legacy bundle {kind} profile {profiles.get(kind)!r} is incompatible with "
                f"the current catalog value {baseline.profile_ids[kind]!r}"
            )
    installed_variables = manifest.get("variables", {})
    contract = baseline.framework.get("variable_contract", {})
    unknown = sorted(set(installed_variables) - set(contract))
    missing = sorted(set(contract) - set(installed_variables))
    if unknown or missing:
        details: list[str] = []
        if unknown:
            details.append("unknown: " + ", ".join(unknown))
        if missing:
            details.append("missing: " + ", ".join(missing))
        raise FrameworkError(
            "legacy bundle variables cannot be normalized against the current contract ("
            + "; ".join(details)
            + ")"
        )
    protected = {"source_language_id", "target_language_id", "pair_id", "output_profile"}
    overrides: dict[str, str | int | float | bool] = {}
    for name, installed_value in installed_variables.items():
        expected_type = contract[name]["type"]
        if not _json_type_matches(installed_value, expected_type):
            raise FrameworkError(
                f"legacy bundle variable {name!r} must be {expected_type}, "
                f"got {type(installed_value).__name__}"
            )
        baseline_value = baseline.variables[name]
        if name in protected:
            if installed_value != baseline_value:
                raise FrameworkError(
                    f"legacy bundle protected identity variable {name!r} does not match "
                    "the installed profiles; use an explicit reconfiguration"
                )
            continue
        if installed_value != baseline_value:
            overrides[name] = installed_value
    # Re-run normal composition validation with the inferred values before trusting them.
    compose_profiles(profiles["pair"], profiles["output"], overrides)
    inferred = tuple(sorted(overrides))
    return overrides, inferred


def installed_project_overrides(
    ownership: Mapping[str, Any], manifest: Mapping[str, Any]
) -> tuple[dict[str, str | int | float | bool], tuple[str, ...]]:
    if ownership.get("schema_version") != "3.0":
        return manifest_project_overrides(manifest)
    overrides = dict(ownership.get("project_overrides", {}))
    inferred = tuple(sorted(ownership.get("inferred_overrides", [])))
    missing = sorted(set(inferred) - set(overrides))
    if missing:
        raise FrameworkError(
            "ownership inferred_overrides are not present in project_overrides: "
            + ", ".join(missing)
        )
    compose_profiles(manifest["profiles"]["pair"], manifest["profiles"]["output"], overrides)
    return overrides, inferred


def configuration_snapshot(
    manifest: Mapping[str, Any],
    overrides: Mapping[str, str | int | float | bool],
) -> dict[str, Any]:
    return {
        "framework_version": manifest["framework_version"],
        "adapter": manifest["adapter"],
        "profiles": dict(manifest["profiles"]),
        "project_overrides": dict(sorted(overrides.items())),
        "bundle_digest": manifest["bundle_digest"],
    }


def configuration_changes(
    current: Mapping[str, Any], next_configuration: Mapping[str, Any]
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field_name in ("adapter", "profiles", "project_overrides"):
        before = current.get(field_name)
        after = next_configuration.get(field_name)
        if before != after:
            changes.append({"field": field_name, "current": before, "next": after})
    return changes


def _major_version(value: str) -> int:
    match = re.fullmatch(r"([0-9]+)\.[0-9]+\.[0-9]+", value)
    if not match:
        raise FrameworkError(f"invalid semantic framework version: {value!r}")
    return int(match.group(1))


def _major_upgrade_decision_errors(
    migration_dir: Path, decision_id: str | None
) -> list[str]:
    if not decision_id:
        return ["a cross-major framework update requires --decision DEC-NNNN"]
    if not re.fullmatch(r"DEC-[0-9]{4,}", decision_id):
        return [f"invalid framework update decision id: {decision_id!r}"]
    config = read_json(migration_dir / "config.json")
    configured_decision = config.get("project_decisions", {}).get("framework_upgrade")
    if configured_decision != decision_id:
        return [
            f"framework update decision {decision_id} is not referenced by "
            "config.json project_decisions.framework_upgrade"
        ]
    matching: dict[str, Any] | None = None
    for path in sorted((migration_dir / "decisions").glob("*.json")):
        candidate = read_json(path)
        if candidate.get("id") == decision_id:
            matching = candidate
            break
    if matching is None:
        return [f"framework update decision {decision_id} does not exist"]
    errors: list[str] = []
    if matching.get("status") != "accepted":
        errors.append(f"framework update decision {decision_id} is not accepted")
    approvals = matching.get("approvals", [])
    if not approvals or any(
        not isinstance(approval, str) or not approval.strip() for approval in approvals
    ):
        errors.append(
            f"framework update decision {decision_id} has no valid approval references"
        )
    return errors


def inspect_migration_state_for_upgrade(
    target: Path,
    current_framework_version: str,
    next_framework_version: str,
    *,
    dry_run: bool,
    allow_major: bool,
    decision_id: str | None,
) -> dict[str, Any]:
    migration_dir = target / ".migration"
    if not migration_dir.exists():
        if allow_major or decision_id:
            raise FrameworkError(
                "--allow-major and --decision apply only when the target has .migration state"
            )
        return {
            "present": False,
            "valid": True,
            "compatible": True,
            "recorded_framework_version": None,
            "diagnostics": [],
        }
    if migration_dir.is_symlink() or not migration_dir.is_dir():
        raise FrameworkError(
            f"target migration state path is not a safe directory: {migration_dir}"
        )
    diagnostics = validate_migration_directory(migration_dir)
    if diagnostics:
        raise FrameworkError(
            "target migration state is invalid; upgrade made no changes:\n  "
            + "\n  ".join(diagnostics)
        )
    config = read_json(migration_dir / "config.json")
    recorded = config["framework_version"]
    lifecycle_state = read_json(migration_dir / "state.json")["status"]
    terminal_states = set(read_json(FRAMEWORK_MANIFEST)["state_machine"]["terminal"])
    if lifecycle_state in terminal_states:
        if allow_major or decision_id:
            raise FrameworkError(
                "--allow-major/--decision were supplied, but the migration lifecycle is "
                f"already terminal ({lifecycle_state})"
            )
        return {
            "present": True,
            "valid": True,
            "compatible": True,
            "recorded_framework_version": recorded,
            "diagnostics": [
                f"migration lifecycle is terminal ({lifecycle_state}); "
                "cross-major approval is not required"
            ],
        }
    # The live state deliberately keeps the framework version it was created with. Once an
    # approved major adoption has succeeded, the managed installation is the durable record
    # of that adoption; comparing the live-state version forever would make every later v3
    # maintenance update require the same approval again.
    compatible = _major_version(current_framework_version) == _major_version(
        next_framework_version
    )
    if compatible:
        if allow_major or decision_id:
            raise FrameworkError(
                "--allow-major/--decision were supplied, but the migration state is already "
                "major-version compatible"
            )
        return {
            "present": True,
            "valid": True,
            "compatible": True,
            "recorded_framework_version": recorded,
            "diagnostics": [],
        }
    approval_errors = _major_upgrade_decision_errors(migration_dir, decision_id)
    diagnostics = [
        f"managed installation moves from framework {current_framework_version} to "
        f"{next_framework_version}; migration state records {recorded}"
    ]
    if not allow_major:
        diagnostics.append("execution requires --allow-major and an approved --decision")
    diagnostics.extend(approval_errors)
    if not dry_run and (not allow_major or approval_errors):
        raise FrameworkError(
            "cross-major framework update is not approved; upgrade made no changes:\n  "
            + "\n  ".join(diagnostics)
        )
    return {
        "present": True,
        "valid": True,
        "compatible": False,
        "recorded_framework_version": recorded,
        "diagnostics": diagnostics,
    }


def resolve_upgrade_composition(
    target: Path,
    *,
    pair_id: str | None,
    output_id: str | None,
    adapter: str | None,
    requested_overrides: Mapping[str, str | int | float | bool],
    unset_overrides: Sequence[str],
) -> tuple[Composition, str]:
    target = target.expanduser().resolve()
    if not target.is_dir():
        raise FrameworkError(f"target directory does not exist: {target}")
    ownership = load_ownership(target)
    if ownership is None:
        raise FrameworkError("target has no managed installation; use install")
    installed_manifest = load_installed_bundle_manifest(target, ownership)
    current_overrides, inferred_keys = installed_project_overrides(ownership, installed_manifest)
    overlap = sorted(set(requested_overrides) & set(unset_overrides))
    if overlap:
        raise FrameworkError(
            "project overrides cannot be set and unset together: " + ", ".join(overlap)
        )
    merged_overrides = dict(current_overrides)
    inferred = set(inferred_keys)
    for key in unset_overrides:
        if key not in merged_overrides:
            raise FrameworkError(f"project override {key!r} is not currently set")
        merged_overrides.pop(key)
        inferred.discard(key)
    for key, value in requested_overrides.items():
        merged_overrides[key] = value
        inferred.discard(key)
    installed_profiles = installed_manifest["profiles"]
    composition = compose_profiles(
        pair_id or installed_profiles["pair"],
        output_id or installed_profiles["output"],
        merged_overrides,
    )
    composition = replace(composition, inferred_overrides=tuple(sorted(inferred)))
    selected_adapter = adapter or installed_manifest["adapter"]
    return composition, selected_adapter


def installation_preflight(
    target: Path,
    new_files: Mapping[str, bytes],
    ownership: Mapping[str, Any] | None,
    *,
    mode: str,
) -> dict[str, Any]:
    if mode == "install" and ownership is not None:
        raise FrameworkError("target already has a managed installation; use upgrade")
    if mode == "upgrade" and ownership is None:
        raise FrameworkError("target has no managed installation; use install")
    old_files: dict[str, str] = dict(ownership.get("files", {})) if ownership else {}
    new_checksums = {relative: sha256_bytes(content) for relative, content in new_files.items()}
    conflicts: list[dict[str, str]] = []
    writes: list[str] = []
    unchanged: list[str] = []
    for relative, expected in sorted(new_checksums.items()):
        destination = safe_join(target, relative)
        current = _file_checksum_or_none(destination)
        if current == expected:
            unchanged.append(relative)
            continue
        writes.append(relative)
        if relative in old_files:
            if current not in {None, old_files[relative]}:
                conflicts.append({"path": relative, "reason": "locally modified managed file"})
        elif current is not None:
            conflicts.append({"path": relative, "reason": "unmanaged target collision"})
        parent = destination.parent
        while parent != target and parent != target.parent:
            if parent.exists() and (not parent.is_dir() or parent.is_symlink()):
                conflicts.append({"path": relative, "reason": f"unsafe parent path {parent.relative_to(target)}"})
                break
            parent = parent.parent
    deletes: list[str] = []
    for relative, old_checksum in sorted(old_files.items()):
        if relative in new_files:
            continue
        destination = safe_join(target, relative)
        current = _file_checksum_or_none(destination)
        if current is None:
            continue
        deletes.append(relative)
        if current != old_checksum:
            conflicts.append({"path": relative, "reason": "locally modified obsolete managed file"})
    conflicts = [dict(item) for item in {canonical_json(item): item for item in conflicts}.values()]
    conflicts.sort(key=lambda item: (item["path"], item["reason"]))
    return {
        "mode": mode,
        "target": str(target),
        "writes": writes,
        "deletes": deletes,
        "unchanged": unchanged,
        "conflicts": conflicts,
    }


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def promote_installation(
    target: Path,
    files: Mapping[str, bytes],
    ownership: Mapping[str, Any],
    preflight: Mapping[str, Any],
) -> None:
    transaction_root = Path(tempfile.mkdtemp(prefix=".migration-framework-transaction-", dir=target.parent))
    stage = transaction_root / "stage"
    backup = transaction_root / "backup"
    promoted: list[str] = []
    backed_up: list[str] = []
    ownership_bytes = pretty_json(ownership).encode("utf-8")
    ownership_checksum_bytes = (sha256_bytes(ownership_bytes) + "\n").encode("ascii")
    all_files = dict(files)
    all_files[OWNERSHIP_FILE] = ownership_bytes
    all_files[OWNERSHIP_CHECKSUM_FILE] = ownership_checksum_bytes
    try:
        for relative, content in all_files.items():
            staged = safe_join(stage, relative)
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(content)
            if sha256_file(staged) != sha256_bytes(content):
                raise FrameworkError(f"staged file failed checksum verification: {relative}")

        changed = list(preflight["writes"]) + list(preflight["deletes"])
        for relative in sorted(set(changed)):
            destination = safe_join(target, relative)
            if destination.exists() or destination.is_symlink():
                saved = safe_join(backup, relative)
                saved.parent.mkdir(parents=True, exist_ok=True)
                os.replace(destination, saved)
                backed_up.append(relative)

        for relative in preflight["writes"]:
            staged = safe_join(stage, relative)
            destination = safe_join(target, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, destination)
            promoted.append(relative)
    except Exception:
        for relative in reversed(promoted):
            _remove_path(safe_join(target, relative))
        for relative in reversed(backed_up):
            saved = safe_join(backup, relative)
            destination = safe_join(target, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if saved.exists() or saved.is_symlink():
                os.replace(saved, destination)
        raise
    finally:
        shutil.rmtree(transaction_root, ignore_errors=True)


def install_compiled_bundle(
    *,
    mode: str,
    adapter: str | None,
    target: Path,
    bundle: Path,
    dry_run: bool,
    force: bool,
    strict_hooks: bool,
    reconfigure: bool = False,
    allow_major: bool = False,
    decision_id: str | None = None,
) -> dict[str, Any]:
    target = target.expanduser().resolve()
    if not target.is_dir():
        raise FrameworkError(f"target directory does not exist: {target}")
    bundle = bundle.expanduser().resolve()
    manifest = verify_bundle(bundle)
    adapter = adapter or manifest["adapter"]
    if adapter not in {"kiro", "claude", "codex"}:
        raise FrameworkError(f"bundle adapter {adapter!r} cannot be installed into a target")
    if manifest["adapter"] != adapter:
        raise FrameworkError(
            f"bundle adapter is {manifest['adapter']!r}, not {adapter!r}; recompile the bundle for the selected adapter"
        )
    current_capabilities = load_adapter_capabilities(adapter)
    if manifest["adapter_capabilities"] != current_capabilities:
        raise FrameworkError(
            f"bundle adapter capabilities no longer match agents/{adapter}/capabilities.json; recompile before installation"
        )
    current_ownership = load_ownership(target)
    next_overrides, next_inferred_keys = manifest_project_overrides(manifest)
    next_configuration = configuration_snapshot(manifest, next_overrides)
    current_configuration: dict[str, Any] | None = None
    changes: list[dict[str, Any]] = []
    warnings: list[str] = []
    migration_state = {
        "present": False,
        "valid": True,
        "compatible": True,
        "recorded_framework_version": None,
        "diagnostics": [],
    }
    if mode == "upgrade":
        if current_ownership is None:
            raise FrameworkError("target has no managed installation; use install")
        installed_manifest = load_installed_bundle_manifest(target, current_ownership)
        current_overrides, current_inferred_keys = installed_project_overrides(
            current_ownership, installed_manifest
        )
        if current_ownership.get("schema_version") == "2.0" and current_overrides:
            preserved_inferred = sorted(
                key
                for key in current_inferred_keys
                if key in next_inferred_keys
                and next_overrides.get(key) == current_overrides[key]
            )
            changed_inferred = sorted(
                key
                for key in current_inferred_keys
                if key in next_overrides
                and next_overrides.get(key) != current_overrides[key]
            )
            explicit_inferred = sorted(
                key
                for key in current_inferred_keys
                if key in next_overrides
                and next_overrides.get(key) == current_overrides[key]
                and key not in next_inferred_keys
            )
            removed_inferred = sorted(
                key for key in current_inferred_keys if key not in next_overrides
            )
            if preserved_inferred:
                warnings.append(
                    "preserved legacy-inferred overrides: "
                    + ", ".join(preserved_inferred)
                )
            if changed_inferred:
                warnings.append(
                    "changed legacy-inferred overrides: "
                    + ", ".join(changed_inferred)
                )
            if explicit_inferred:
                warnings.append(
                    "preserved values and recorded legacy-inferred overrides as explicit: "
                    + ", ".join(explicit_inferred)
                )
            if removed_inferred:
                warnings.append(
                    "removed legacy-inferred overrides: "
                    + ", ".join(removed_inferred)
                )
        current_configuration = configuration_snapshot(installed_manifest, current_overrides)
        changes = configuration_changes(current_configuration, next_configuration)
        if changes and not reconfigure:
            summary = ", ".join(item["field"] for item in changes)
            raise FrameworkError(
                "upgrade would change installed configuration "
                f"({summary}); rerun with --reconfigure after reviewing a dry-run"
            )
        migration_state = inspect_migration_state_for_upgrade(
            target,
            installed_manifest["framework_version"],
            manifest["framework_version"],
            dry_run=dry_run,
            allow_major=allow_major,
            decision_id=decision_id,
        )
    elif reconfigure or allow_major or decision_id:
        raise FrameworkError(
            "--reconfigure, --allow-major, and --decision are valid only for upgrade"
        )

    files = render_install_files(adapter, bundle, manifest, strict_hooks=strict_hooks)
    preflight = installation_preflight(target, files, current_ownership, mode=mode)
    if preflight["conflicts"] and not force and not dry_run:
        details = "\n".join(f"  - {item['path']}: {item['reason']}" for item in preflight["conflicts"])
        raise FrameworkError(f"installation conflicts detected; no files changed:\n{details}\nUse --force only to replace these paths explicitly.")
    ownership = {
        "$schema": "schemas/installation-ownership.schema.json",
        "schema_version": "3.0",
        "framework_version": manifest["framework_version"],
        "adapter": adapter,
        "profiles": manifest["profiles"],
        "project_overrides": dict(sorted(next_overrides.items())),
        "inferred_overrides": sorted(next_inferred_keys),
        "bundle_digest": manifest["bundle_digest"],
        "files": {relative: sha256_bytes(content) for relative, content in sorted(files.items())},
    }
    ownership_bytes = pretty_json(ownership).encode("utf-8")
    metadata_contents = {
        OWNERSHIP_FILE: ownership_bytes,
        OWNERSHIP_CHECKSUM_FILE: (sha256_bytes(ownership_bytes) + "\n").encode("ascii"),
    }
    metadata_writes = [
        relative
        for relative, content in metadata_contents.items()
        if _file_checksum_or_none(target / relative) != sha256_bytes(content)
    ]
    preflight["writes"] = sorted(set(preflight["writes"]) | set(metadata_writes))
    preflight["current_configuration"] = current_configuration
    preflight["next_configuration"] = next_configuration
    preflight["configuration_changes"] = changes
    preflight["inferred_overrides"] = {
        key: next_overrides[key] for key in sorted(next_inferred_keys)
    }
    preflight["migration_state"] = migration_state
    preflight["warnings"] = warnings
    preflight["forced"] = bool(force and preflight["conflicts"])
    preflight["forced_replacements"] = (
        sorted({item["path"] for item in preflight["conflicts"]})
        if force
        else []
    )
    preflight["dry_run"] = dry_run
    if not dry_run:
        promote_installation(target, files, ownership, preflight)
    return preflight


def install_or_upgrade(
    *,
    mode: str,
    composition: Composition,
    adapter: str,
    target: Path,
    dry_run: bool,
    force: bool,
    strict_hooks: bool,
    reconfigure: bool = False,
    allow_major: bool = False,
    decision_id: str | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="migration-framework-bundle-") as temp:
        bundle = Path(temp) / "bundle"
        compile_bundle(composition, bundle, adapter=adapter)
        return install_compiled_bundle(
            mode=mode,
            adapter=adapter,
            target=target,
            bundle=bundle,
            dry_run=dry_run,
            force=force,
            strict_hooks=strict_hooks,
            reconfigure=reconfigure,
            allow_major=allow_major,
            decision_id=decision_id,
        )


def _all_profile_paths() -> list[Path]:
    return sorted((ROOT / "docs" / "profiles").glob("*/*/profile.json"))


def _validate_manifest_documents(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    document_fields = ("generic_documents", "workflow_documents", "hook_documents", "provenance_documents", "release_documents", "documentation", "schemas")
    for field in document_fields:
        for relative in manifest.get(field, []):
            try:
                repo_path(relative)
            except FrameworkError as exc:
                errors.append(str(exc))
    return errors


def _validate_state_machine_manifest(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    machine = manifest.get("state_machine", {})
    states = set(machine.get("states", []))
    transitions = machine.get("transitions", {})
    if set(transitions) != states:
        errors.append("framework.json state_machine.transitions must declare exactly every state")
    if machine.get("initial") not in states:
        errors.append("framework.json state_machine.initial is not a declared state")
    for terminal in machine.get("terminal", []):
        if terminal not in states:
            errors.append(f"framework.json terminal state is undeclared: {terminal!r}")
    for source, destinations in transitions.items():
        for destination in destinations:
            if destination not in states:
                errors.append(f"framework.json transition {source!r} points to unknown state {destination!r}")
    for terminal in machine.get("terminal", []):
        if transitions.get(terminal):
            errors.append(f"framework.json terminal state {terminal!r} must not have outgoing transitions")
    return errors


def _validate_markdown_contracts() -> list[str]:
    errors: list[str] = []
    required_skill_sections = ("## When to Use", "## Inputs", "## Procedure", "## Outputs", "## Success Criteria")
    for path in sorted((ROOT / "docs" / "skills").glob("*.md")):
        content = path.read_text(encoding="utf-8")
        if not content.startswith(f"# {path.stem}\n"):
            errors.append(f"{relative_repo_path(path)}: first heading must be '# {path.stem}'")
        for section in required_skill_sections:
            if section not in content:
                errors.append(f"{relative_repo_path(path)}: missing required section {section}")
    for path in sorted((ROOT / "docs" / "hooks").glob("*.md")):
        content = path.read_text(encoding="utf-8")
        names: set[str] = set()
        current: str | None = None
        fields: dict[str, str] = {}

        def finish_hook() -> None:
            if current is None or current.lower() == "hooks":
                return
            required = {"trigger", "matcher", "type", "description", "required", "enforcement"}
            missing = sorted(required - fields.keys())
            if missing:
                errors.append(f"{relative_repo_path(path)} hook {current!r}: missing fields {', '.join(missing)}")
            if fields.get("type") == "command" and "command" not in fields:
                errors.append(f"{relative_repo_path(path)} hook {current!r}: command hook has no command")
            if fields.get("type") == "agent" and "prompt" not in fields:
                errors.append(f"{relative_repo_path(path)} hook {current!r}: agent hook has no prompt")
            if fields.get("required") not in {"true", "false"}:
                errors.append(f"{relative_repo_path(path)} hook {current!r}: required must be true or false")
            expected_enforcement = "deterministic" if fields.get("type") == "command" else "judgment"
            if fields.get("enforcement") != expected_enforcement:
                errors.append(f"{relative_repo_path(path)} hook {current!r}: enforcement must be {expected_enforcement}")

        for line in content.splitlines():
            heading = re.fullmatch(r"##\s+(.+?)\s*", line)
            if heading:
                finish_hook()
                current = heading.group(1)
                fields = {}
                if current in names:
                    errors.append(f"{relative_repo_path(path)}: duplicate hook name {current!r}")
                names.add(current)
                continue
            field = re.fullmatch(r"-\s+([a-z][a-z0-9_-]*):\s*(.*)", line)
            if field and current:
                fields[field.group(1)] = field.group(2).strip()
        finish_hook()
    return errors


def _validate_generic_neutrality() -> list[str]:
    errors: list[str] = []
    forbidden = re.compile(r"\b(?:Java|Spring|Gradle|JUnit|ArchUnit)\b|C\+\+|\bhexagonal\b", re.IGNORECASE)
    for path in sorted((ROOT / "docs" / "standards" / "generic").glob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if forbidden.search(line):
                errors.append(f"{relative_repo_path(path)}:{number}: language/output-specific term in generic standard")
    return errors


def _validate_state_templates() -> list[str]:
    errors: list[str] = []
    for path in sorted((ROOT / "docs" / "state" / "templates").glob("*.json")):
        try:
            instance = read_json(path)
            schema_reference = instance.get("$schema")
            if not isinstance(schema_reference, str):
                errors.append(f"{relative_repo_path(path)}: missing $schema")
                continue
            schema_path = ROOT / "schemas" / schema_reference.rsplit("/", 1)[-1]
            if not schema_path.is_file():
                errors.append(f"{relative_repo_path(path)}: unknown schema {schema_reference!r}")
                continue
            errors.extend(validate_json_file(path, schema_path))
        except FrameworkError as exc:
            errors.append(str(exc))
    return errors


def _validate_fixtures() -> list[str]:
    errors: list[str] = []
    fixture_schema = ROOT / "schemas" / "fixture.schema.json"
    fixture_paths = sorted((ROOT / "fixtures").glob("*/fixture.json"))
    identifiers: set[str] = set()
    outputs: set[str] = set()
    build_systems: set[str] = set()
    test_frameworks: set[str] = set()
    for path in fixture_paths:
        try:
            errors.extend(validate_json_file(path, fixture_schema))
            fixture = read_json(path)
            identifier = fixture.get("id")
            if identifier in identifiers:
                errors.append(f"{relative_repo_path(path)}: duplicate fixture id {identifier!r}")
            identifiers.add(identifier)
            outputs.add(fixture.get("output_profile"))
            build_systems.add(fixture.get("build_system"))
            test_frameworks.add(fixture.get("test_framework"))
        except FrameworkError as exc:
            errors.append(str(exc))
    missing_outputs = {"service", "library", "sdk", "cli"} - outputs
    if missing_outputs:
        errors.append(f"fixture matrix is missing output profiles: {', '.join(sorted(missing_outputs))}")
    missing_builds = {"cmake", "make", "meson"} - build_systems
    if missing_builds:
        errors.append(f"fixture matrix is missing representative build systems: {', '.join(sorted(missing_builds))}")
    missing_tests = {"googletest", "catch2", "doctest"} - test_frameworks
    if missing_tests:
        errors.append(f"fixture matrix is missing source test frameworks: {', '.join(sorted(missing_tests))}")
    profile_schema = ROOT / "schemas" / "profile.schema.json"
    scaffold_paths = sorted((ROOT / "fixtures" / "profile-scaffold").glob("*-profile.json"))
    if len(scaffold_paths) != 4:
        errors.append("profile scaffold must contain source, target, pair, and output manifests")
    for path in scaffold_paths:
        errors.extend(validate_json_file(path, profile_schema))
    golden = ROOT / "fixtures" / "golden-multimodule" / "expected" / ".migration"
    if golden.is_dir():
        errors.extend(validate_migration_directory(golden))
    else:
        errors.append("golden multi-module fixture has no expected .migration state")
    return errors


def _validate_schema_catalog(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    declared = set(manifest.get("schemas", []))
    actual = {relative_repo_path(path) for path in (ROOT / "schemas").glob("*.schema.json")}
    for relative in sorted(actual - declared):
        errors.append(f"schema is not declared by framework.json: {relative}")
    for relative in sorted(declared - actual):
        errors.append(f"declared schema does not exist: {relative}")
    identifiers: dict[str, str] = {}
    for relative in sorted(actual):
        try:
            schema = read_json(repo_path(relative))
        except FrameworkError as exc:
            errors.append(str(exc))
            continue
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{relative}: must declare JSON Schema draft 2020-12")
        errors.extend(schema_definition_errors(schema, label=relative))
        identifier = schema.get("$id")
        if not isinstance(identifier, str):
            errors.append(f"{relative}: missing $id")
        elif identifier in identifiers:
            errors.append(f"{relative}: duplicate $id also used by {identifiers[identifier]}")
        else:
            identifiers[identifier] = relative
    return errors


def _validate_profiles(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    profile_schema = ROOT / "schemas" / "profile.schema.json"
    for path in _all_profile_paths():
        try:
            errors.extend(validate_json_file(path, profile_schema))
            profile = read_json(path)
            plural = path.parent.parent.name
            expected_kind = {"sources": "source", "targets": "target", "pairs": "pair", "outputs": "output"}.get(plural)
            if expected_kind != profile.get("kind"):
                errors.append(f"{relative_repo_path(path)}: path kind {expected_kind!r} differs from manifest kind {profile.get('kind')!r}")
            if path.parent.name != profile.get("id"):
                errors.append(f"{relative_repo_path(path)}: directory and profile id differ")
            for relative in profile.get("documents", []):
                repo_path(relative)
            for documents in profile.get("target_documents", {}).values():
                for relative in documents:
                    repo_path(relative)
        except FrameworkError as exc:
            errors.append(str(exc))
    pairs = sorted(path.parent.name for path in (ROOT / "docs" / "profiles" / "pairs").glob("*/profile.json"))
    outputs = sorted(path.parent.name for path in (ROOT / "docs" / "profiles" / "outputs").glob("*/profile.json"))
    if manifest.get("default_pair") not in pairs:
        errors.append("framework default_pair does not name an installed pair profile")
    if manifest.get("default_output_profile") not in outputs:
        errors.append("framework default_output_profile does not name an installed output profile")
    return errors


def _validate_adapter_manifests() -> list[str]:
    errors: list[str] = []
    schema_path = ROOT / "schemas" / "adapter-capabilities.schema.json"
    for adapter in ("kiro", "claude", "codex"):
        path = ROOT / "agents" / adapter / "capabilities.json"
        try:
            errors.extend(validate_json_file(path, schema_path))
            capabilities = read_json(path)
            if capabilities.get("adapter") != adapter:
                errors.append(f"{relative_repo_path(path)}: adapter id must be {adapter!r}")
        except FrameworkError as exc:
            errors.append(str(exc))
    return errors


def _validate_v1_compatibility(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        legacy = read_json(repo_path(manifest["compatibility"]["v1_variables"]))
    except FrameworkError as exc:
        return [str(exc)]
    declared = legacy.get("variables")
    pairs = legacy.get("pairs")
    if not isinstance(declared, dict) or not isinstance(pairs, dict):
        return ["v1 variables.json must contain object-valued variables and pairs"]
    for pair_id, variables in pairs.items():
        if not SAFE_ID_RE.fullmatch(pair_id) or not isinstance(variables, dict):
            errors.append(f"invalid v1 pair entry: {pair_id!r}")
            continue
        unknown = sorted(set(variables) - set(declared))
        if unknown:
            errors.append(f"v1 pair {pair_id!r} has undeclared variables: {', '.join(unknown)}")
        for key, definition in declared.items():
            if key in variables and isinstance(definition, dict):
                expected = definition.get("type")
                if expected and not _json_type_matches(variables[key], expected):
                    errors.append(f"v1 pair {pair_id!r} variable {key!r} violates declared type {expected}")
    return errors


def _validate_documentation_consistency(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    readme_path = ROOT / "README.md"
    try:
        readme = readme_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"README.md: {exc}"]
    expected_literals = {
        manifest["framework_version"],
        manifest["default_pair"],
        manifest["default_output_profile"],
        "python3 agents/framework.py check",
        "python3 agents/framework.py compile",
        "python3 agents/framework.py install",
        "python3 agents/framework.py upgrade",
    }
    expected_literals.update(path.parent.name for path in (ROOT / "docs" / "profiles" / "outputs").glob("*/profile.json"))
    expected_literals.update(("kiro", "claude", "codex"))
    for literal in sorted(expected_literals):
        if literal not in readme:
            errors.append(f"README.md: missing manifest-backed value or executable example {literal!r}")
    if "cpp-to-java25" in readme:
        errors.append("README.md: stale pair id 'cpp-to-java25'; use 'cpp-to-java-25'")
    return errors


def _directory_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _validate_compositions(*, determinism: bool) -> list[str]:
    errors: list[str] = []
    pair_ids = sorted(path.parent.name for path in (ROOT / "docs" / "profiles" / "pairs").glob("*/profile.json"))
    output_ids = sorted(path.parent.name for path in (ROOT / "docs" / "profiles" / "outputs").glob("*/profile.json"))
    with tempfile.TemporaryDirectory(prefix="migration-framework-validation-") as temporary:
        temp = Path(temporary)
        for pair_id in pair_ids:
            for output_id in output_ids:
                label = f"{pair_id}/{output_id}"
                try:
                    composition = compose_profiles(pair_id, output_id)
                    first = temp / f"{pair_id}-{output_id}-a"
                    compile_bundle(composition, first)
                    verify_bundle(first)
                    for adapter in ("kiro", "claude", "codex"):
                        first_json, _ = run_hook_parser(adapter, first / "hooks")
                        second_json, _ = run_hook_parser(adapter, first / "hooks")
                        if first_json != second_json:
                            errors.append(f"{label}: {adapter} hook output is nondeterministic")
                    if determinism:
                        second = temp / f"{pair_id}-{output_id}-b"
                        compile_bundle(composition, second)
                        if _directory_hashes(first) != _directory_hashes(second):
                            errors.append(f"{label}: repeated compilation is not byte-identical")
                except (FrameworkError, OSError, subprocess.SubprocessError) as exc:
                    errors.append(f"{label}: {exc}")
    return errors


def validate_repository(*, determinism: bool = False) -> list[str]:
    errors: list[str] = []
    try:
        manifest = read_json(FRAMEWORK_MANIFEST)
        errors.extend(validate_json_file(FRAMEWORK_MANIFEST, ROOT / "schemas" / "framework.schema.json"))
    except FrameworkError as exc:
        return [str(exc)]
    errors.extend(_validate_manifest_documents(manifest))
    errors.extend(_validate_state_machine_manifest(manifest))
    errors.extend(_validate_schema_catalog(manifest))
    errors.extend(_validate_profiles(manifest))
    errors.extend(_validate_adapter_manifests())
    errors.extend(_validate_v1_compatibility(manifest))
    errors.extend(_validate_documentation_consistency(manifest))
    errors.extend(_validate_state_templates())
    errors.extend(_validate_fixtures())
    errors.extend(_validate_markdown_contracts())
    errors.extend(_validate_generic_neutrality())
    for path in sorted((ROOT / "docs").rglob("*.md")):
        if "_template" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        if "{{build_command}}" in content:
            errors.append(f"{relative_repo_path(path)}: deprecated template variable {{{{build_command}}}}")
    if not errors:
        errors.extend(_validate_compositions(determinism=determinism))
    return sorted(set(errors))


def validate_artifact(path: Path) -> list[str]:
    path = path.expanduser().resolve()
    instance = read_json(path)
    reference = instance.get("$schema")
    if not isinstance(reference, str):
        return [f"{path}: missing $schema"]
    schema_name = Path(reference).name
    schema_path = ROOT / "schemas" / schema_name
    if not schema_path.is_file():
        return [f"{path}: unknown framework schema {reference!r}"]
    errors = schema_errors(instance, read_json(schema_path))
    return [f"{path}: {error}" for error in errors]


def validate_migration_directory(directory: Path) -> list[str]:
    directory = directory.expanduser().resolve()
    errors: list[str] = []
    json_files = sorted(directory.rglob("*.json"))
    if not json_files:
        return [f"{directory}: no JSON state artifacts found"]
    artifacts: dict[str, dict[str, Any]] = {}
    for path in json_files:
        try:
            artifact = read_json(path)
            artifacts[path.relative_to(directory).as_posix()] = artifact
            errors.extend(validate_artifact(path))
        except FrameworkError as exc:
            errors.append(str(exc))
    inventory = artifacts.get("inventory.json", {})
    source_ids = {item.get("id") for item in inventory.get("units", []) if isinstance(item, dict)}
    behavior_ids: set[str] = set()
    decision_ids: set[str] = set()
    plan_ids: set[str] = set()
    evidence_ids: set[str] = set()
    exception_ids: set[str] = set()
    config = artifacts.get("config.json")
    if config and config.get("validation_status") == "valid":
        coverage = config.get("quality_gates", {}).get("coverage", {})
        if coverage.get("metric") != "none" and coverage.get("threshold_percent") is None:
            errors.append("config.json: valid configuration requires a project-approved coverage threshold")
    for relative, artifact in artifacts.items():
        if relative.startswith("behaviors/"):
            behavior_ids.add(artifact.get("id"))
            for source_id in artifact.get("source_units", []):
                if source_id not in source_ids:
                    errors.append(f"{relative}: references unknown source unit {source_id!r}")
        elif relative.startswith("decisions/"):
            decision_ids.add(artifact.get("id"))
        elif relative.startswith("plans/"):
            plan_ids.add(artifact.get("id"))
        elif relative.startswith("evidence/"):
            evidence_ids.add(artifact.get("id"))
        elif relative.startswith("exceptions/"):
            exception_ids.add(artifact.get("id"))

    if config:
        try:
            configured = compose_profiles(
                config.get("profiles", {}).get("pair"), config.get("output_profile")
            )
            for kind in ("source", "target", "pair"):
                actual = config.get("profiles", {}).get(kind)
                expected = configured.profile_ids[kind]
                if actual != expected:
                    errors.append(
                        f"config.json: {kind} profile {actual!r} is incompatible with selected pair; expected {expected!r}"
                    )
        except FrameworkError as exc:
            errors.append(f"config.json: profile composition failed: {exc}")
        referenced_decisions = {
            value
            for value in config.get("project_decisions", {}).values()
            if isinstance(value, str) and re.fullmatch(r"DEC-[0-9]{4,}", value)
        }
        for decision_id in referenced_decisions - decision_ids:
            errors.append(f"config.json: project_decisions references unknown decision {decision_id!r}")
        if config.get("migration_strategy") == "big-bang":
            accepted = {
                artifact.get("id")
                for relative, artifact in artifacts.items()
                if relative.startswith("decisions/")
                and artifact.get("status") == "accepted"
                and artifact.get("approvals")
            }
            if not (referenced_decisions & accepted):
                errors.append("config.json: big-bang strategy requires an accepted, approved decision reference")

    for unit in inventory.get("units", []):
        for behavior_id in unit.get("behaviors", []):
            if behavior_id not in behavior_ids:
                errors.append(f"inventory.json source unit {unit.get('id')!r}: unknown behavior {behavior_id!r}")
    for relative, artifact in artifacts.items():
        if relative.startswith("decisions/"):
            for behavior_id in artifact.get("affected_contracts", []):
                if behavior_id not in behavior_ids:
                    errors.append(f"{relative}: references unknown behavior {behavior_id!r}")
            if artifact.get("status") == "accepted" and not artifact.get("approvals"):
                errors.append(f"{relative}: accepted decision requires an approval reference")
        elif relative.startswith("plans/"):
            for source_id in artifact.get("source_units", []):
                if source_id not in source_ids:
                    errors.append(f"{relative}: references unknown source unit {source_id!r}")
            for behavior_id in artifact.get("behavioral_contracts", []):
                if behavior_id not in behavior_ids:
                    errors.append(f"{relative}: references unknown behavior {behavior_id!r}")
            for dependency in artifact.get("dependencies", []):
                if dependency not in plan_ids:
                    errors.append(f"{relative}: references unknown plan dependency {dependency!r}")
            if artifact.get("status") == "approved" and not artifact.get("approval_refs"):
                errors.append(f"{relative}: approved plan requires at least one human approval reference")
        elif relative.startswith("evidence/"):
            if artifact.get("slice_id") is not None and artifact.get("slice_id") not in plan_ids:
                errors.append(f"{relative}: references unknown slice {artifact.get('slice_id')!r}")
            if artifact.get("phase") == "characterize" and artifact.get("slice_id") is not None:
                errors.append(f"{relative}: characterization evidence must precede and therefore not reference a slice")
            if artifact.get("phase") != "characterize" and artifact.get("slice_id") is None:
                errors.append(f"{relative}: {artifact.get('phase')!r} evidence requires a slice")
            for behavior_id in artifact.get("contracts", []):
                if behavior_id not in behavior_ids:
                    errors.append(f"{relative}: references unknown behavior {behavior_id!r}")
        elif relative.startswith("exceptions/"):
            known_scope = source_ids | plan_ids | behavior_ids
            for scope_id in artifact.get("scope", []):
                if scope_id not in known_scope:
                    errors.append(f"{relative}: references unknown scope id {scope_id!r}")
            if artifact.get("status") == "approved" and not artifact.get("approvals"):
                errors.append(f"{relative}: approved exception requires an approval reference")
    traceability = artifacts.get("traceability.json", {})
    traced_source_ids: set[str] = set()
    for index, link in enumerate(traceability.get("links", [])):
        traced_source_ids.add(link.get("source_unit"))
        if link.get("source_unit") not in source_ids:
            errors.append(f"traceability.json links[{index}]: unknown source unit {link.get('source_unit')!r}")
        for behavior_id in link.get("behavioral_contracts", []):
            if behavior_id not in behavior_ids:
                errors.append(f"traceability.json links[{index}]: unknown behavior {behavior_id!r}")
        for decision_id in link.get("decisions", []):
            if decision_id not in decision_ids:
                errors.append(f"traceability.json links[{index}]: unknown decision {decision_id!r}")
        for evidence_id in link.get("evidence", []):
            if evidence_id not in evidence_ids:
                errors.append(f"traceability.json links[{index}]: unknown evidence {evidence_id!r}")
        for exception_id in link.get("exceptions", []):
            if exception_id not in exception_ids:
                errors.append(f"traceability.json links[{index}]: unknown exception {exception_id!r}")
        if link.get("status") == "excepted" and not link.get("exceptions"):
            errors.append(f"traceability.json links[{index}]: excepted link requires an exception")
        if link.get("status") != "excepted" and not link.get("behavioral_contracts"):
            errors.append(f"traceability.json links[{index}]: non-excepted link requires a behavioral contract")
    state = artifacts.get("state.json")
    if state:
        if state.get("status") not in {"initialize", "discover", "characterize"}:
            missing_traces = source_ids - traced_source_ids
            if missing_traces:
                errors.append(
                    "traceability.json: lifecycle state requires links for source units "
                    + ", ".join(sorted(missing_traces))
                )
        history = state.get("history", [])
        transitions = read_json(FRAMEWORK_MANIFEST)["state_machine"]["transitions"]
        for index, transition in enumerate(history):
            previous = transition.get("from")
            destination = transition.get("to")
            if previous is None:
                if index != 0 or destination != read_json(FRAMEWORK_MANIFEST)["state_machine"]["initial"]:
                    errors.append("state.json history[0]: must initialize from null")
            elif destination not in transitions.get(previous, []):
                errors.append(f"state.json history[{index}]: invalid transition {previous!r} → {destination!r}")
            if index and transition.get("from") != history[index - 1].get("to"):
                errors.append(f"state.json history[{index}]: transition chain is discontinuous")
        if history:
            if state.get("last_transition") != history[-1]:
                errors.append("state.json: last_transition must equal the final history entry")
            if state.get("status") != history[-1].get("to"):
                errors.append("state.json: status must equal the final history destination")
            if state.get("revision") != len(history) - 1:
                errors.append("state.json: revision must equal completed transition count")
        for slice_id in state.get("completed_slices", []):
            if slice_id not in plan_ids:
                errors.append(f"state.json: completed_slices references unknown plan {slice_id!r}")
            else:
                matching_plan = next(
                    (
                        artifact
                        for relative, artifact in artifacts.items()
                        if relative.startswith("plans/") and artifact.get("id") == slice_id
                    ),
                    None,
                )
                if matching_plan and matching_plan.get("status") != "approved":
                    errors.append(f"state.json: completed slice {slice_id!r} must have an approved plan")
        if state.get("status") in {"blocked", "failed"}:
            if not state.get("resume_to") or not state.get("blocked_by"):
                errors.append("state.json: blocked/failed state requires resume_to and blocked_by")
        elif state.get("resume_to") is not None or state.get("blocked_by"):
            errors.append("state.json: active state must clear resume_to and blocked_by")
        if state.get("status") == "approve" and state.get("active_slice") is not None:
            errors.append("state.json: approved state must clear active_slice after completing the slice")
    plan_dependencies = {
        artifact.get("id"): list(artifact.get("dependencies", []))
        for relative, artifact in artifacts.items()
        if relative.startswith("plans/")
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit_plan(plan_id: str, chain: list[str]) -> None:
        if plan_id in visiting:
            cycle = chain[chain.index(plan_id):]
            errors.append("migration plans contain a dependency cycle: " + " -> ".join(cycle))
            return
        if plan_id in visited:
            return
        visiting.add(plan_id)
        for dependency in plan_dependencies.get(plan_id, []):
            visit_plan(dependency, chain + [dependency])
        visiting.remove(plan_id)
        visited.add(plan_id)

    for plan_id in sorted(plan_dependencies):
        visit_plan(plan_id, [plan_id])
    return sorted(set(errors))


def transition_state(
    path: Path,
    destination: str,
    reason: str,
    blockers: Sequence[str] = (),
) -> dict[str, Any]:
    path = path.expanduser().resolve()
    errors = validate_artifact(path)
    if errors:
        raise FrameworkError("state artifact is invalid:\n  " + "\n  ".join(errors))
    state = read_json(path)
    manifest = read_json(FRAMEWORK_MANIFEST)
    transitions = manifest["state_machine"]["transitions"]
    current = state["status"]
    if destination not in transitions.get(current, []):
        allowed = ", ".join(transitions.get(current, [])) or "none"
        raise FrameworkError(f"invalid state transition {current!r} → {destination!r}; allowed: {allowed}")
    if current in {"blocked", "failed"} and state.get("resume_to") and destination != state["resume_to"]:
        raise FrameworkError(f"state must resume to {state['resume_to']!r}, not {destination!r}")
    previous = current
    state["status"] = destination
    state["revision"] += 1
    if destination in {"blocked", "failed"}:
        state["resume_to"] = previous
        state["blocked_by"] = list(blockers) or [reason]
    elif current in {"blocked", "failed"}:
        state["resume_to"] = None
        state["blocked_by"] = []
    if destination == "approve" and previous == "review":
        active_slice = state.get("active_slice")
        if not active_slice:
            raise FrameworkError("review → approve requires an active_slice to complete")
        if active_slice not in state["completed_slices"]:
            state["completed_slices"].append(active_slice)
        state["active_slice"] = None
    transition = {
        "from": previous,
        "to": destination,
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "reason": reason,
    }
    state["last_transition"] = transition
    state.setdefault("history", []).append(transition)
    state["validation_status"] = "valid"
    schema = read_json(ROOT / "schemas" / "migration-state.schema.json")
    errors = schema_errors(state, schema)
    if errors:
        raise FrameworkError("transition produced invalid state:\n  " + "\n  ".join(errors))
    write_text_atomic(path, pretty_json(state))
    return state


def syntax_errors() -> list[str]:
    errors: list[str] = []
    for path in sorted((ROOT / "agents").rglob("*.py")) + sorted((ROOT / "tests").rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f"{relative_repo_path(path)}: {exc}")
    for path in sorted(ROOT.glob("*.sh")) + sorted((ROOT / "agents").rglob("*.sh")):
        process = subprocess.run(["bash", "-n", str(path)], cwd=ROOT, text=True, capture_output=True, check=False)
        if process.returncode:
            errors.append(f"{relative_repo_path(path)}: {process.stderr.strip()}")
    for path in sorted(ROOT.rglob("*.json")):
        if any(part in {".git", ".compiled"} for part in path.parts):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeError) as exc:
            errors.append(f"{relative_repo_path(path)}: {exc}")
    return errors


def run_unit_tests() -> tuple[bool, str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )
    output = (process.stdout + process.stderr).strip()
    return process.returncode == 0, output


def print_validation(errors: Sequence[str], *, label: str) -> int:
    if errors:
        print(f"{label} failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"{label} passed")
    return 0


def add_composition_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--pair",
        default=None,
        help="pair profile id (upgrade preserves the installed value; other commands use framework.json)",
    )
    parser.add_argument(
        "--output-profile",
        default=None,
        choices=("service", "library", "sdk", "cli"),
        help="output profile (upgrade preserves the installed value when omitted)",
    )
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="project-level scalar variable override; repeatable",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile, validate, and safely install ai-migration-framework v3"
    )
    framework_version = read_json(FRAMEWORK_MANIFEST)["framework_version"]
    parser.add_argument("--version", action="version", version=f"%(prog)s {framework_version}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate repository contracts and all profile compositions")
    validate.add_argument("--determinism", action="store_true", help="compile every composition twice and compare bytes")

    check = subparsers.add_parser("check", help="run full repository validation, determinism, syntax, and unit tests")
    check.add_argument("--skip-tests", action="store_true", help="skip unit tests (validation and syntax still run)")

    compile_parser = subparsers.add_parser("compile", help="compile a deterministic portable or adapter bundle")
    add_composition_arguments(compile_parser)
    compile_parser.add_argument("--adapter", default="portable", choices=("portable", "kiro", "claude", "codex"))
    compile_parser.add_argument("--output", required=True, type=Path)

    install = subparsers.add_parser("install", help="safely install an adapter package")
    add_composition_arguments(install)
    install.add_argument("--adapter", required=True, choices=("kiro", "claude", "codex"))
    install.add_argument("--target", required=True, type=Path)
    install.add_argument("--bundle", type=Path, help="install this already compiled, checksum-verified adapter bundle")
    install.add_argument("--dry-run", action="store_true", help="show exact writes, deletes, and conflicts without mutation")
    install.add_argument("--force", action="store_true", help="explicitly replace reported conflicting paths")
    install.add_argument("--strict-hooks", action="store_true", help="fail if any portable hook lacks exact native semantics")

    upgrade = subparsers.add_parser(
        "upgrade", help="safely upgrade an existing managed installation"
    )
    add_composition_arguments(upgrade)
    upgrade.add_argument("--adapter", choices=("kiro", "claude", "codex"), help="override the installed adapter")
    upgrade.add_argument("--target", required=True, type=Path)
    upgrade.add_argument("--bundle", type=Path, help="upgrade to this checksum-verified adapter bundle")
    upgrade.add_argument("--dry-run", action="store_true", help="show configuration and file changes without mutation")
    upgrade.add_argument("--force", action="store_true", help="explicitly replace reported conflicting paths")
    upgrade.add_argument("--strict-hooks", action="store_true", help="fail if any portable hook lacks exact native semantics")
    upgrade.add_argument(
        "--reconfigure",
        action="store_true",
        help="authorize an adapter, profile, or project-override change",
    )
    upgrade.add_argument(
        "--unset",
        dest="unsets",
        action="append",
        default=[],
        metavar="KEY",
        help="remove one recorded project override; repeatable and requires --reconfigure",
    )
    upgrade.add_argument(
        "--allow-major",
        action="store_true",
        help="authorize a cross-major guidance update for an active migration",
    )
    upgrade.add_argument(
        "--decision",
        metavar="DEC-NNNN",
        help="accepted, approved migration decision authorizing a cross-major update",
    )

    artifact = subparsers.add_parser("validate-artifact", help="validate one JSON artifact from its $schema")
    artifact.add_argument("path", type=Path)

    migration = subparsers.add_parser("validate-migration", help="validate a .migration directory and cross-references")
    migration.add_argument("path", type=Path)

    transition = subparsers.add_parser("transition", help="apply one validated lifecycle transition to state.json")
    transition.add_argument("--state", required=True, type=Path)
    transition.add_argument("--to", required=True)
    transition.add_argument("--reason", required=True)
    transition.add_argument("--blocker", action="append", default=[], help="stable blocker/failure reference; repeatable")

    listing = subparsers.add_parser("list", help="list installed profile and adapter ids")
    listing.add_argument("kind", choices=("pairs", "outputs", "adapters", "all"), nargs="?", default="all")
    return parser


def _list_values(kind: str) -> dict[str, list[str]]:
    result = {
        "pairs": sorted(path.parent.name for path in (ROOT / "docs" / "profiles" / "pairs").glob("*/profile.json")),
        "outputs": sorted(path.parent.name for path in (ROOT / "docs" / "profiles" / "outputs").glob("*/profile.json")),
        "adapters": ["claude", "codex", "kiro"],
    }
    return result if kind == "all" else {kind: result[kind]}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return print_validation(validate_repository(determinism=args.determinism), label="Framework validation")
        if args.command == "check":
            errors = syntax_errors()
            errors.extend(validate_repository(determinism=True))
            status = print_validation(sorted(set(errors)), label="Framework check")
            if status or args.skip_tests:
                return status
            passed, output = run_unit_tests()
            if output:
                print(output, file=sys.stderr if not passed else sys.stdout)
            if not passed:
                print("Unit tests failed", file=sys.stderr)
                return 1
            print("Unit tests passed")
            return 0
        if args.command == "compile":
            composition = compose_profiles(args.pair, args.output_profile, parse_overrides(args.overrides))
            manifest = compile_bundle(composition, args.output, adapter=args.adapter)
            verify_bundle(args.output)
            print(pretty_json({"output": str(args.output.resolve()), "bundle_digest": manifest["bundle_digest"], "profiles": manifest["profiles"]}), end="")
            return 0
        if args.command == "install":
            if args.bundle:
                if args.pair is not None or args.output_profile is not None or args.overrides:
                    raise FrameworkError("--bundle cannot be combined with --pair, --output-profile, or --set")
                report = install_compiled_bundle(
                    mode="install",
                    adapter=args.adapter,
                    target=args.target,
                    bundle=args.bundle,
                    dry_run=args.dry_run,
                    force=args.force,
                    strict_hooks=args.strict_hooks,
                )
            else:
                composition = compose_profiles(args.pair, args.output_profile, parse_overrides(args.overrides))
                report = install_or_upgrade(
                    mode="install",
                    composition=composition,
                    adapter=args.adapter,
                    target=args.target,
                    dry_run=args.dry_run,
                    force=args.force,
                    strict_hooks=args.strict_hooks,
                )
            print(pretty_json(report), end="")
            return 0
        if args.command == "upgrade":
            requested_overrides = parse_overrides(args.overrides)
            unset_overrides = parse_unsets(args.unsets)
            if args.bundle:
                if args.pair is not None or args.output_profile is not None or requested_overrides or unset_overrides:
                    raise FrameworkError(
                        "--bundle cannot be combined with --pair, --output-profile, --set, or --unset"
                    )
                report = install_compiled_bundle(
                    mode="upgrade",
                    adapter=args.adapter,
                    target=args.target,
                    bundle=args.bundle,
                    dry_run=args.dry_run,
                    force=args.force,
                    strict_hooks=args.strict_hooks,
                    reconfigure=args.reconfigure,
                    allow_major=args.allow_major,
                    decision_id=args.decision,
                )
            else:
                composition, adapter = resolve_upgrade_composition(
                    args.target,
                    pair_id=args.pair,
                    output_id=args.output_profile,
                    adapter=args.adapter,
                    requested_overrides=requested_overrides,
                    unset_overrides=unset_overrides,
                )
                report = install_or_upgrade(
                    mode="upgrade",
                    composition=composition,
                    adapter=adapter,
                    target=args.target,
                    dry_run=args.dry_run,
                    force=args.force,
                    strict_hooks=args.strict_hooks,
                    reconfigure=args.reconfigure,
                    allow_major=args.allow_major,
                    decision_id=args.decision,
                )
            print(pretty_json(report), end="")
            return 0
        if args.command == "validate-artifact":
            return print_validation(validate_artifact(args.path), label="Artifact validation")
        if args.command == "validate-migration":
            return print_validation(validate_migration_directory(args.path), label="Migration state validation")
        if args.command == "transition":
            print(pretty_json(transition_state(args.state, args.to, args.reason, args.blocker)), end="")
            return 0
        if args.command == "list":
            print(pretty_json(_list_values(args.kind)), end="")
            return 0
        raise FrameworkError(f"unknown command: {args.command}")
    except FrameworkError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
