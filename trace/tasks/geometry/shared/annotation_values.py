"""Shared helpers for annotated measurement values in geometry tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence


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


def build_role_value_annotation(
    *,
    roles: Sequence[str],
    role_to_annotation: Mapping[str, str],
    role_to_value: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build annotation->value annotation payload from role-bound values.

    Duplicate annotation tokens are permitted only when they map to the same value.
    """
    annotation: Dict[str, Any] = {}
    for role in [str(item) for item in roles]:
        if str(role) not in role_to_annotation:
            raise ValueError(f"missing annotation token for role: {role}")
        if str(role) not in role_to_value:
            raise ValueError(f"missing measurement value for role: {role}")
        annotation = str(role_to_annotation[str(role)]).strip()
        if not annotation:
            raise ValueError(f"empty annotation token for role: {role}")
        coerced_value = _coerce_value_for_json(role_to_value[str(role)])
        if annotation in annotation:
            if annotation[annotation] != coerced_value:
                raise ValueError(f"conflicting values for annotation token in annotation map: {annotation}")
            continue
        annotation[annotation] = coerced_value
    return {str(key): value for key, value in annotation.items()}


def build_annotation_value_tokens(annotation_map: Mapping[str, Any]) -> List[str]:
    """Build one deterministic unordered symbolic annotation set from annotation values."""
    tokens: List[str] = []
    for annotation, value in sorted(((str(key), item) for key, item in annotation_map.items()), key=lambda item: item[0]):
        token = f"{annotation}={format_annotation_value(value)}"
        tokens.append(str(token))
    return list(tokens)


def build_annotation_value_point_map(
    *,
    annotation_map: Mapping[str, Any],
    annotation_centers: Mapping[str, Sequence[float]],
) -> Dict[str, List[float]]:
    """Project annotation=value annotation tokens back to annotation center points."""
    point_map: Dict[str, List[float]] = {}
    for annotation, value in sorted(((str(key), item) for key, item in annotation_map.items()), key=lambda item: item[0]):
        if annotation not in annotation_centers:
            continue
        center = annotation_centers[annotation]
        if not isinstance(center, Sequence) or len(center) != 2:
            continue
        token = f"{annotation}={format_annotation_value(value)}"
        point_map[str(token)] = [float(center[0]), float(center[1])]
    return dict(point_map)


def format_annotation_value(value: Any) -> str:
    """Format one measurement value for on-image numeric annotation text."""
    coerced = _coerce_value_for_json(value)
    return str(coerced)
