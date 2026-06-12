"""Annotation projection helpers for candlestick body and wick witnesses."""

from __future__ import annotations

from trace.tasks.charts.candlestick.shared.rendering import bbox_center
from trace.tasks.charts.candlestick.shared.state import BBox, Point, Rendered, Selection


def annotation_boxes_and_points(
    *,
    rendered: Rendered,
    selection: Selection,
) -> tuple[list[BBox], list[Point]]:
    """Project selected candle roles to body or wick boxes and their centers."""

    annotation_boxes: list[BBox] = []
    annotation_points: list[Point] = []
    for role, candle_id in zip(selection.annotation_roles, selection.annotation_candle_ids):
        if str(role).endswith("_wick"):
            annotation_box = list(rendered.wick_bboxes_px[str(candle_id)])
        else:
            annotation_box = list(rendered.body_bboxes_px[str(candle_id)])
        annotation_boxes.append(list(annotation_box))
        annotation_points.append(bbox_center(annotation_box))
    return annotation_boxes, annotation_points


__all__ = ["annotation_boxes_and_points"]
