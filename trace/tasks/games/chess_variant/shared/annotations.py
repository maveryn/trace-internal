"""Annotation projection helpers for chess-variant games tasks."""

from __future__ import annotations

from typing import Any, Mapping

from .state import ChessVariantEvaluation


def annotation_from_evaluation(
    *,
    evaluation: ChessVariantEvaluation,
    render_map: Mapping[str, Any],
) -> tuple[str, list[list[float]], dict[str, Any]]:
    """Project semantic annotation ids to the public annotation payload."""

    if evaluation.annotation_kind == "piece_point":
        points: list[list[float]] = []
        for entity_id in evaluation.annotation_entity_ids:
            bbox = render_map["piece_bboxes_px"][str(entity_id)]
            points.append([
                round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
            ])
        return "point_set", points, {
            "type": "point_set",
            "point_set": [list(point) for point in points],
            "pixel_point_set": [list(point) for point in points],
        }

    if evaluation.annotation_kind == "cell":
        bboxes = [list(render_map["cell_bboxes_px"][entity_id]) for entity_id in evaluation.annotation_entity_ids]
    else:
        bboxes = [list(render_map["piece_bboxes_px"][entity_id]) for entity_id in evaluation.annotation_entity_ids]
    return "bbox_set", [list(bbox) for bbox in bboxes], {"bbox_set": [list(bbox) for bbox in bboxes]}


__all__ = ["annotation_from_evaluation"]
