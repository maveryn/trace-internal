"""Annotation and answer helpers for the graph node-link scene."""

from __future__ import annotations

from typing import Any

from trace.core.types import TypedValue
from trace.tasks.graph.shared.graph_scene import (
    projected_edge_label_bbox_annotation,
    projected_edge_pair_annotation,
    projected_node_point_annotation,
)

def labels_from_sample(sample: Any, field_name: str) -> tuple[str, ...]:
    """Read one label sequence from a graph sample field."""

    raw = getattr(sample, str(field_name))
    if isinstance(raw, str):
        return (str(raw),)
    return tuple(str(item) for item in raw)


def edges_from_sample(sample: Any, field_name: str) -> tuple[tuple[str, str], ...]:
    """Read one edge-label sequence from a graph sample field."""

    raw = getattr(sample, str(field_name))
    if raw and isinstance(raw[0], str):
        return (tuple(str(item) for item in raw[:2]),)
    return tuple(tuple(str(item) for item in edge[:2]) for edge in raw)


def answer_value(sample: Any, *, answer_field: str, answer_type: str) -> Any:
    """Resolve one typed answer value from a sampled graph field."""

    if hasattr(sample, str(answer_field)):
        value = getattr(sample, str(answer_field))
    elif hasattr(sample, "target_labels"):
        value = len(getattr(sample, "target_labels"))
    elif hasattr(sample, "target_edges"):
        value = len(getattr(sample, "target_edges"))
    else:
        raise AttributeError(f"sample has no answer field {answer_field!r}")
    if str(answer_type) == "integer":
        return int(value)
    return str(value)


def annotation_value(
    sample: Any,
    rendered_scene: Any,
    *,
    annotation_kind: str,
    annotation_field: str,
) -> tuple[TypedValue, dict[str, Any], dict[str, Any]]:
    """Project task-selected minimal witnesses into pixel annotation space."""

    kind = str(annotation_kind)
    if kind in {"node_point_set", "node_point_sequence"}:
        labels = labels_from_sample(sample, str(annotation_field))
        projection = projected_node_point_annotation(rendered_scene, labels)
        points = [list(point) for point in projection["pixel_point_set"]]
        annotation_type = "point_sequence" if kind == "node_point_sequence" else "point_set"
        return (
            TypedValue(type=annotation_type, value=list(points)),
            {"type": annotation_type, annotation_type: list(points), **dict(projection)},
            {"type": "object_sequence" if kind == "node_point_sequence" else "object_set", "labels": list(labels)},
        )
    if kind == "edge_point_pair_set":
        edges = edges_from_sample(sample, str(annotation_field))
        projection = projected_edge_pair_annotation(rendered_scene, edges)
        pairs = [[list(pair[0]), list(pair[1])] for pair in projection["point_pair_set"]]
        return (
            TypedValue(type="point_pair_set", value=list(pairs)),
            {"type": "point_pair_set", "point_pair_set": list(pairs), **dict(projection)},
            {"type": "edge_set", "edge_labels": [list(edge) for edge in edges]},
        )
    if kind == "edge_label_bbox_set":
        edges = edges_from_sample(sample, str(annotation_field))
        boxes: list[list[float]] = []
        projections: list[dict[str, Any]] = []
        for edge in edges:
            projection = projected_edge_label_bbox_annotation(rendered_scene, edge)
            boxes.extend([list(box) for box in projection["pixel_bbox_set"]])
            projections.append(dict(projection))
        return (
            TypedValue(type="bbox_set", value=list(boxes)),
            {"type": "bbox_set", "bbox_set": list(boxes), "edge_label_projections": projections},
            {"type": "edge_label_set", "edge_labels": [list(edge) for edge in edges]},
        )
    raise ValueError(f"unsupported node-link annotation kind: {kind}")


__all__ = [
    "annotation_value",
    "answer_value",
    "edges_from_sample",
    "labels_from_sample",
]
