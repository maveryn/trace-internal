"""Annotation projection helpers for Chess games scenes."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from trace.tasks.games.shared.piece_board_rules import Coord, coord_to_cell_id
from trace.tasks.games.shared.piece_board_renderer import RenderedChessScene


def bbox_set_for_entities(rendered_scene: RenderedChessScene, *, entity_ids: Tuple[str, ...], annotation_kind: str) -> list[list[float]]:
    """Project cell or piece entity ids into bbox-set annotation."""

    key = "cell_bboxes_px" if str(annotation_kind) == "cell" else "piece_bboxes_px"
    mapping = rendered_scene.render_map[str(key)]
    return [list(mapping[str(entity_id)]) for entity_id in entity_ids]


def keyed_move_bboxes(
    rendered_scene: RenderedChessScene,
    *,
    source: Coord,
    destination: Coord,
    king: Coord,
) -> dict[str, list[float]]:
    """Project checkmate source, destination, and king cells to keyed bboxes."""

    cells = rendered_scene.render_map["cell_bboxes_px"]
    return {
        "from": list(cells[coord_to_cell_id(source)]),
        "to": list(cells[coord_to_cell_id(destination)]),
        "king": list(cells[coord_to_cell_id(king)]),
    }


def projected_bbox_payload(annotation_bboxes: list[list[float]]) -> dict[str, Any]:
    """Return projected bbox-set trace payload."""

    return {"bbox_set": [list(bbox) for bbox in annotation_bboxes]}


def projected_keyed_bbox_payload(annotation_map: Mapping[str, list[float]]) -> dict[str, Any]:
    """Return projected keyed-bbox trace payload."""

    value = {str(key): list(bbox) for key, bbox in annotation_map.items()}
    return {"type": "keyed_bbox_map", "keyed_bbox_map": value, "pixel_keyed_bbox_map": value}

__all__ = ["bbox_set_for_entities", "keyed_move_bboxes", "projected_bbox_payload", "projected_keyed_bbox_payload"]
