"""Annotation projection helpers for density-curve chart scenes."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.charts.density_curve.shared.state import DensityCurveDataset, DensityCurveRendered


def density_curve_annotation_payload(
    *,
    dataset: DensityCurveDataset,
    rendered: DensityCurveRendered,
) -> tuple[str, Dict[str, list[float]], Dict[str, Any]]:
    """Return annotation payloads for the answer curve witness."""

    answer_label = str(dataset.query.answer_label)
    annotation_map_source = {
        "answer_mean_marker": rendered.mean_marker_bboxes_px,
        "answer_mode_marker": rendered.mode_marker_bboxes_px,
        "answer_interval_mass": rendered.interval_mass_bboxes_px,
        "answer_density_at_x": rendered.density_at_x_points_px,
    }[str(dataset.query.annotation_key)]
    annotation_value = list(annotation_map_source[str(answer_label)])
    annotation_type = (
        "keyed_point_map"
        if str(dataset.query.annotation_key) == "answer_density_at_x"
        else "keyed_bbox_map"
    )
    annotation = {str(dataset.query.annotation_key): list(annotation_value)}
    projected: dict[str, Any] = {
        "type": str(annotation_type),
        "answer_label": str(answer_label),
    }
    if str(annotation_type) == "keyed_point_map":
        projected["keyed_point_map"] = dict(annotation)
        projected["pixel_keyed_point_map"] = dict(annotation)
    else:
        projected["keyed_bbox_map"] = dict(annotation)
        projected["pixel_keyed_bbox_map"] = dict(annotation)
    return str(annotation_type), dict(annotation), dict(projected)
