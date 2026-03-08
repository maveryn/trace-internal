"""Shared helpers for labeled graph-point evidence payloads."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from .graph_rendering import pixel_point_to_graph_units


def labeled_grid_point_evidence_artifacts(
    *,
    points_by_label: Mapping[str, Sequence[float]],
    graph_origin: Sequence[float],
    graph_spacing: int,
    witness_type: str,
    ordered_labels: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """Build evidence/witness/projection payloads for one labeled point map."""
    if ordered_labels is None:
        labels = [str(label) for label in points_by_label.keys()]
    else:
        labels = [str(label) for label in ordered_labels]
    if not labels:
        raise ValueError("labeled evidence requires at least one label")

    pixel_map: Dict[str, list[float]] = {}
    grid_map: Dict[str, list[int]] = {}
    pixel_set: list[list[float]] = []
    grid_set: list[list[int]] = []
    for label in labels:
        if str(label) not in points_by_label:
            raise ValueError(f"missing point for evidence label: {label}")
        point = points_by_label[str(label)]
        if not isinstance(point, Sequence) or len(point) != 2:
            raise ValueError(f"invalid point for evidence label: {label}")
        pixel_point = [float(point[0]), float(point[1])]
        grid_point = pixel_point_to_graph_units(
            (float(point[0]), float(point[1])),
            origin=(float(graph_origin[0]), float(graph_origin[1])),
            spacing=int(graph_spacing),
        )
        pixel_map[str(label)] = list(pixel_point)
        grid_map[str(label)] = list(grid_point)
        pixel_set.append(list(pixel_point))
        grid_set.append(list(grid_point))

    return {
        "evidence_type": "grid_point_map",
        "evidence_value": dict(grid_map),
        "required_labels": list(labels),
        "witness_symbolic": {
            "type": str(witness_type),
            "labels": list(labels),
        },
        "projected_evidence": {
            "point_map": dict(pixel_map),
            "grid_point_map": dict(grid_map),
            "point_set": list(pixel_set),
            "point_path": list(pixel_set),
            "grid_point_set": list(grid_set),
            "grid_point_path": list(grid_set),
        },
    }

