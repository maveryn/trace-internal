"""Shared helpers for annotated measurement values in geometry tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


def _coerce_value_for_json(value: Any) -> Any:
    """Normalize one measurement value into JSON-safe primitive form."""
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        rounded = round(float(value))
        if abs(float(value) - float(rounded)) <= 1e-9:
            return int(rounded)
        return float(value)
    return str(value)


def build_role_value_evidence(
    *,
    roles: Sequence[str],
    role_to_annotation: Mapping[str, str],
    role_to_value: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build annotation->value evidence payload from role-bound values.

    Duplicate annotation tokens are permitted only when they map to the same value.
    """
    evidence: Dict[str, Any] = {}
    for role in [str(item) for item in roles]:
        if str(role) not in role_to_annotation:
            raise ValueError(f"missing annotation token for role: {role}")
        if str(role) not in role_to_value:
            raise ValueError(f"missing measurement value for role: {role}")
        annotation = str(role_to_annotation[str(role)]).strip()
        if not annotation:
            raise ValueError(f"empty annotation token for role: {role}")
        coerced_value = _coerce_value_for_json(role_to_value[str(role)])
        if annotation in evidence:
            if evidence[annotation] != coerced_value:
                raise ValueError(f"conflicting values for annotation token in evidence map: {annotation}")
            continue
        evidence[annotation] = coerced_value
    return {str(key): value for key, value in evidence.items()}


def format_annotation_value(value: Any) -> str:
    """Format one measurement value for on-image numeric annotation text."""
    coerced = _coerce_value_for_json(value)
    return str(coerced)
