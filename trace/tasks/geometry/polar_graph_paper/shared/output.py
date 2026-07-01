"""Output helpers for polar graph paper tasks."""

from __future__ import annotations

from typing import Any


def point_annotation_from_render(render_map: dict[str, Any]) -> list[float]:
    point = render_map["point_p"]
    return [float(point[0]), float(point[1])]


def point_map_annotation_from_render(render_map: dict[str, Any], labels: tuple[str, ...]) -> dict[str, list[float]]:
    annotation: dict[str, list[float]] = {}
    for label in labels:
        point = render_map[f"point_{label.lower()}"]
        annotation[str(label)] = [float(point[0]), float(point[1])]
    return annotation


def projected_point_annotation(annotation: list[float]) -> dict[str, Any]:
    return {"type": "point", "value": list(annotation)}


def projected_point_map_annotation(annotation: dict[str, list[float]]) -> dict[str, Any]:
    point_map = {str(key): list(value) for key, value in annotation.items()}
    return {
        "type": "point_map",
        "value": point_map,
        "point_map": point_map,
        "pixel_point_map": point_map,
    }
