"""Annotation projection helpers for curve-panel charts."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .state import CurvePanelDataset, RenderedCurvePanels


def bbox_center(bbox: Sequence[float]) -> List[float]:
    """Return the center point for one rendered bbox."""

    if len(bbox) < 4:
        raise ValueError("bbox must have at least four coordinates")
    x0, y0, x1, y1 = [float(value) for value in bbox[:4]]
    return [round((x0 + x1) * 0.5, 3), round((y0 + y1) * 0.5, 3)]


def point_set_from_ids(
    *,
    rendered: RenderedCurvePanels,
    point_ids: Sequence[str] = (),
    intersection_ids: Sequence[str] = (),
    crossing_ids: Sequence[str] = (),
) -> List[List[float]]:
    """Project rendered marker/intersection/crossing ids to a point set."""

    points: List[List[float]] = []
    for point_id in point_ids:
        point_box = rendered.point_bboxes.get(str(point_id))
        if point_box is not None:
            points.append(bbox_center(point_box))
    for intersection_id in intersection_ids:
        intersection_box = rendered.intersection_bboxes.get(str(intersection_id))
        if intersection_box is not None:
            points.append(bbox_center(intersection_box))
    for crossing_id in crossing_ids:
        crossing_box = rendered.threshold_crossing_bboxes.get(str(crossing_id))
        if crossing_box is not None:
            points.append(bbox_center(crossing_box))
    return points


def keyed_start_end_points(
    *,
    dataset: CurvePanelDataset,
    rendered: RenderedCurvePanels,
) -> Dict[str, List[float]]:
    """Project each panel's start/end marker into a keyed point map."""

    annotation: Dict[str, List[float]] = {}
    for point_id in dataset.query.annotation_point_ids:
        point_box = rendered.point_bboxes.get(str(point_id))
        if point_box is None:
            continue
        parts = str(point_id).split("|")
        if len(parts) != 3:
            continue
        panel_label, _method_label, x_value = parts
        role = "start" if int(x_value) == int(dataset.query.start_x_value) else "end"
        annotation[f"{str(panel_label)}_{role}"] = bbox_center(point_box)
    expected_key_count = int(len(dataset.panels)) * 2
    if len(annotation) != int(expected_key_count):
        raise RuntimeError("start/end annotation map is incomplete")
    return annotation


def projected_annotation_payload(
    *,
    dataset: CurvePanelDataset,
    annotation_type: str,
    annotation: Sequence[Sequence[float]] | Mapping[str, Sequence[float]],
) -> Dict[str, Any]:
    """Build the projected annotation trace payload for one public task."""

    if str(annotation_type) == "keyed_point_map":
        keyed_point_map = {
            str(key): list(point) for key, point in dict(annotation).items()
        }
        return {
            "type": "keyed_point_map",
            "keyed_point_map": dict(keyed_point_map),
            "pixel_keyed_point_map": dict(keyed_point_map),
            "panel_labels": list(dataset.query.annotation_panel_labels),
            "point_ids": list(dataset.query.annotation_point_ids),
            "intersection_ids": list(dataset.query.annotation_intersection_ids),
            "threshold_crossing_ids": list(
                dataset.query.annotation_threshold_crossing_ids
            ),
        }
    point_set = [list(point) for point in list(annotation)]
    return {
        "type": "point_set",
        "point_set": list(point_set),
        "pixel_point_set": list(point_set),
        "panel_labels": list(dataset.query.annotation_panel_labels),
        "point_ids": list(dataset.query.annotation_point_ids),
        "intersection_ids": list(dataset.query.annotation_intersection_ids),
        "threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
    }


__all__ = [
    "bbox_center",
    "keyed_start_end_points",
    "point_set_from_ids",
    "projected_annotation_payload",
]
