"""Lightweight JSON-Schema-style validator (stdlib only).

Implements the subset of JSON Schema needed to validate agent/tool I/O at
runtime without pulling a third-party dependency:

  - type, required, properties, enum, items, minimum, maximum,
    minLength, maxLength, minItems, additionalProperties, oneOf.

It is intentionally small but correct for the schemas shipped under
``assets/schemas``. Unknown keywords are ignored (forward-compatible).
"""
from __future__ import annotations

from typing import Any

from .errors import SchemaValidationError

_SIMPLE_TYPES = {"string", "integer", "number", "boolean", "object", "array", "null"}


def _type_matches(value: Any, type_name: str) -> bool:
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "null":
        return value is None
    return True  # unknown type -> permissive


def _validate_node(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        return

    typ = schema.get("type")
    if typ is not None:
        if isinstance(typ, list):
            if not any(_type_matches(value, t) for t in typ):
                errors.append(f"{path}: expected one of {typ}, got {type(value).__name__}")
                return
        elif isinstance(typ, str):
            if not _type_matches(value, typ):
                errors.append(f"{path}: expected {typ}, got {type(value).__name__}")
                return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string longer than maxLength {schema['maxLength']}")
        if "pattern" in schema:
            import re

            if not re.search(schema["pattern"], value):
                errors.append(f"{path}: string does not match pattern {schema['pattern']!r}")

    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required property '{req}'")
        for key, sub in props.items():
            if key in value:
                _validate_node(value[key], sub, f"{path}.{key}", errors)
        if schema.get("additionalProperties") is False:
            extras = set(value) - set(props)
            if extras:
                errors.append(f"{path}: additionalProperties not allowed: {sorted(extras)}")

    if isinstance(value, list):
        items = schema.get("items")
        if items is not None:
            for i, item in enumerate(value):
                _validate_node(item, items, f"{path}[{i}]", errors)
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than maxItems {schema['maxItems']}")

    if "oneOf" in schema:
        matched = 0
        for sub in schema["oneOf"]:
            sub_errors: list[str] = []
            _validate_node(value, sub, path, sub_errors)
            if not sub_errors:
                matched += 1
        if matched != 1:
            errors.append(f"{path}: matched {matched} of oneOf branches (expected exactly 1)")


def validate(instance: Any, schema: dict[str, Any], *, label: str = "instance") -> None:
    """Validate ``instance`` against ``schema``; raise SchemaValidationError on failure."""
    errors: list[str] = []
    _validate_node(instance, schema, label, errors)
    if errors:
        raise SchemaValidationError(
            f"{label} failed schema validation ({len(errors)} error(s))",
            errors=errors,
        )


def is_valid(instance: Any, schema: dict[str, Any]) -> bool:
    try:
        validate(instance, schema)
    except SchemaValidationError:
        return False
    return True


def load_schema(path) -> dict[str, Any]:
    """Load a JSON schema file from disk."""
    import json
    from pathlib import Path

    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


__all__ = ["validate", "is_valid", "load_schema"]