"""Annotation helpers for combo-mark chart tasks."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.charts.combo_mark.shared.state import ComboScene
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts


def points_for_indices(
    indices: Iterable[int],
    scene: ComboScene,
    *,
    include_primary: bool,
    include_line: bool,
) -> tuple[dict[str, list[float]], list[str]]:
    """Return keyed mark-center points for task-selected category indices."""

    points: dict[str, list[float]] = {}
    labels: list[str] = []
    for idx in indices:
        category_label = str(scene.labels[int(idx)])
        if include_primary:
            points[f"{category_label}.primary"] = [
                float(scene.primary_points[int(idx)][0]),
                float(scene.primary_points[int(idx)][1]),
            ]
            labels.append(f"{scene.primary_name}:{scene.labels[int(idx)]}")
        if include_line:
            points[f"{category_label}.line"] = [
                float(scene.line_points[int(idx)][0]),
                float(scene.line_points[int(idx)][1]),
            ]
            labels.append(f"{scene.line_name}:{scene.labels[int(idx)]}")
    return points, labels


def keyed_point_artifacts(points: Mapping[str, Sequence[float]]) -> AnnotationArtifacts:
    value = {
        str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
        for key, point in points.items()
    }
    projected = {
        "type": "keyed_point_map",
        "keyed_point_map": dict(value),
        "pixel_keyed_point_map": dict(value),
    }
    return AnnotationArtifacts(
        annotation_type="keyed_point_map",
        value=dict(value),
        annotation_gt=TypedValue(type="keyed_point_map", value=dict(value)),
        projected_annotation=projected,
    )


__all__ = ["keyed_point_artifacts", "points_for_indices"]
