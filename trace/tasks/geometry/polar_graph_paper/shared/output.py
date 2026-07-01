"""Output helpers for polar graph paper tasks."""

from __future__ import annotations

from typing import Any


def point_annotation_from_render(render_map: dict[str, Any]) -> list[float]:
    point = render_map["point_p"]
    return [float(point[0]), float(point[1])]


def projected_point_annotation(annotation: list[float]) -> dict[str, Any]:
    return {"type": "point", "value": list(annotation)}
