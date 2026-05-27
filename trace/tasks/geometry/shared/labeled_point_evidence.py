"""Geometry wrappers for graph-derived pixel-point evidence helpers."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.graph_point_evidence import (
    empty_graph_point_set_evidence_artifacts as _base_empty_graph_point_set_evidence_artifacts,
    graph_point_evidence_artifacts as _base_graph_point_evidence_artifacts,
    graph_point_set_evidence_artifacts as _base_graph_point_set_evidence_artifacts,
    labeled_grid_point_evidence_artifacts,
)


def _as_pixel_point_set_artifacts(artifacts: Dict[str, Any]) -> Dict[str, Any]:
    """Expose graph-derived Geometry evidence as public pixel point sets."""

    projected = dict(artifacts.get("projected_evidence") or {})
    pixel_points = projected.get("pixel_point_set")
    if pixel_points is None:
        pixel_path = projected.get("pixel_point_sequence")
        pixel_points = list(pixel_path) if isinstance(pixel_path, list) else []
    point_set = [[float(point[0]), float(point[1])] for point in pixel_points if isinstance(point, (list, tuple)) and len(point) == 2]

    witness_symbolic = dict(artifacts.get("witness_symbolic") or {})

    pixel_projected: Dict[str, Any] = {
        "type": "point_set",
        "point_set": [list(point) for point in point_set],
        "pixel_point_set": [list(point) for point in point_set],
    }
    if "pixel_point_map" in projected:
        pixel_projected["pixel_point_map"] = dict(projected["pixel_point_map"])
    if "pixel_point_sequence" in projected:
        pixel_projected["pixel_point_sequence"] = [list(point) for point in projected["pixel_point_sequence"]]

    return {
        "evidence_type": "point_set",
        "evidence_value": [list(point) for point in point_set],
        "required_labels": list(artifacts.get("required_labels", [])),
        "witness_symbolic": witness_symbolic,
        "projected_evidence": pixel_projected,
    }


def graph_point_set_evidence_artifacts(**kwargs: Any) -> Dict[str, Any]:
    """Build Geometry public evidence as pixel points for a graph-point set witness."""

    return _as_pixel_point_set_artifacts(_base_graph_point_set_evidence_artifacts(**kwargs))


def empty_graph_point_set_evidence_artifacts(*, witness_type: str) -> Dict[str, Any]:
    """Build an empty Geometry pixel point-set evidence payload."""

    return _as_pixel_point_set_artifacts(
        _base_empty_graph_point_set_evidence_artifacts(witness_type=str(witness_type))
    )


def graph_point_evidence_artifacts(**kwargs: Any) -> Dict[str, Any]:
    """Build Geometry public evidence as a singleton pixel point set."""

    return _as_pixel_point_set_artifacts(_base_graph_point_evidence_artifacts(**kwargs))


__all__ = [
    "empty_graph_point_set_evidence_artifacts",
    "graph_point_evidence_artifacts",
    "graph_point_set_evidence_artifacts",
    "labeled_grid_point_evidence_artifacts",
]
