"""Shared helpers for graph-point evidence payloads."""

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
    """Build unlabeled graph-point-set evidence while preserving labeled projections.

    The primary `evidence_value` is an unordered list of integer graph-paper points.
    Labeled map projections are still emitted in `projected_evidence` so task traces
    can retain the semantic correspondence between rendered labels and sampled points.
    """

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
    """Build one empty graph-point-set evidence payload.

    Some count-style geometry tasks legitimately have zero witnesses. In those
    cases the contract still wants `graph_point_set` evidence, but with empty
    symbolic/projection payloads instead of inventing placeholder points.
    """

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
