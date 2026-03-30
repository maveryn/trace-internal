"""Cross-domain helpers for graph-point evidence payloads."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


def pixel_point_to_graph_units(
    point: Sequence[float],
    *,
    origin: Sequence[float],
    spacing: int,
    tol: float = 1e-6,
) -> list[int]:
    """Project one pixel-space point to integer graph-paper coordinates."""

    spacing_px = max(1, int(spacing))
    gx_raw = (float(point[0]) - float(origin[0])) / float(spacing_px)
    gy_raw = (float(origin[1]) - float(point[1])) / float(spacing_px)
    gx = int(round(gx_raw))
    gy = int(round(gy_raw))
    if abs(gx_raw - float(gx)) > float(tol) or abs(gy_raw - float(gy)) > float(tol):
        raise ValueError("point is not aligned to graph-paper lattice for graph-unit evidence")
    return [int(gx), int(gy)]


def labeled_grid_point_evidence_artifacts(
    *,
    points_by_label: Mapping[str, Sequence[float]],
    graph_origin: Sequence[float],
    graph_spacing: int,
    witness_type: str,
    ordered_labels: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """Build evidence/witness/projection payloads for labeled graph points."""

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
            pixel_point,
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
            "pixel_point_map": dict(pixel_map),
            "grid_point_map": dict(grid_map),
            "pixel_point_set": list(pixel_set),
            "pixel_point_path": list(pixel_set),
            "grid_point_set": list(grid_set),
            "grid_point_path": list(grid_set),
        },
    }


def graph_point_set_evidence_artifacts(
    *,
    points_by_label: Mapping[str, Sequence[float]],
    graph_origin: Sequence[float],
    graph_spacing: int,
    witness_type: str,
    ordered_labels: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """Build unlabeled graph-point-set evidence while preserving projections."""

    labeled = labeled_grid_point_evidence_artifacts(
        points_by_label=points_by_label,
        graph_origin=graph_origin,
        graph_spacing=graph_spacing,
        witness_type=witness_type,
        ordered_labels=ordered_labels,
    )
    projected = dict(labeled["projected_evidence"])
    grid_set = projected.get("grid_point_set", [])
    if not isinstance(grid_set, list) or not grid_set:
        raise ValueError("graph_point_set evidence requires at least one graph point")
    return {
        "evidence_type": "graph_point_set",
        "evidence_value": list(grid_set),
        "required_labels": list(labeled.get("required_labels", [])),
        "witness_symbolic": dict(labeled["witness_symbolic"]),
        "projected_evidence": projected,
    }


def empty_graph_point_set_evidence_artifacts(*, witness_type: str) -> Dict[str, Any]:
    """Build one empty graph-point-set evidence payload."""

    return {
        "evidence_type": "graph_point_set",
        "evidence_value": [],
        "required_labels": [],
        "witness_symbolic": {
            "type": str(witness_type),
            "labels": [],
        },
        "projected_evidence": {
            "type": "graph_point_set",
            "pixel_point_set": [],
            "grid_point_set": [],
        },
    }


def graph_point_evidence_artifacts(
    *,
    points_by_label: Mapping[str, Sequence[float]],
    graph_origin: Sequence[float],
    graph_spacing: int,
    witness_type: str,
    ordered_labels: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """Build single graph-point evidence while preserving labeled projections."""

    labeled = labeled_grid_point_evidence_artifacts(
        points_by_label=points_by_label,
        graph_origin=graph_origin,
        graph_spacing=graph_spacing,
        witness_type=witness_type,
        ordered_labels=ordered_labels,
    )
    projected = dict(labeled["projected_evidence"])
    grid_set = projected.get("grid_point_set", [])
    if not isinstance(grid_set, list) or len(grid_set) != 1:
        raise ValueError("graph_point evidence requires exactly one graph point")
    point = grid_set[0]
    if not isinstance(point, list) or len(point) != 2:
        raise ValueError("graph_point evidence must be one [x, y] integer pair")
    return {
        "evidence_type": "graph_point",
        "evidence_value": list(point),
        "required_labels": list(labeled.get("required_labels", [])),
        "witness_symbolic": dict(labeled["witness_symbolic"]),
        "projected_evidence": projected,
    }


__all__ = [
    "empty_graph_point_set_evidence_artifacts",
    "graph_point_evidence_artifacts",
    "graph_point_set_evidence_artifacts",
    "labeled_grid_point_evidence_artifacts",
    "pixel_point_to_graph_units",
]
