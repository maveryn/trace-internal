"""Annotation projection helpers for Minesweeper board cells."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts, bbox_set_annotation_artifacts

from .state import Coord, coord_to_cell_id
from .rendering import RenderedMinesweeperScene


def _bbox_for_cell(rendered: RenderedMinesweeperScene, coord: Coord) -> list[float]:
    """Project one board coordinate to its inset cell bbox."""

    entity_id = coord_to_cell_id(coord)
    return [float(value) for value in rendered.render_map["cell_bboxes_px"][str(entity_id)]]


def minesweeper_bbox_set_annotation(
    *,
    rendered: RenderedMinesweeperScene,
    coords: Sequence[Coord],
) -> AnnotationArtifacts:
    """Project homogeneous cell witnesses to a public bbox-set annotation."""

    return bbox_set_annotation_artifacts([_bbox_for_cell(rendered, coord) for coord in coords])


def minesweeper_bbox_annotation(
    *,
    rendered: RenderedMinesweeperScene,
    coord: Coord,
) -> AnnotationArtifacts:
    """Project one guaranteed cell witness to a scalar bbox annotation."""

    value = [round(float(v), 3) for v in _bbox_for_cell(rendered, coord)]
    return AnnotationArtifacts(
        annotation_type="bbox",
        value=list(value),
        annotation_gt=TypedValue(type="bbox", value=list(value)),
        projected_annotation={
            "type": "bbox",
            "bbox": list(value),
            "pixel_bbox": list(value),
        },
    )


def minesweeper_keyed_bbox_sets_annotation(
    *,
    rendered: RenderedMinesweeperScene,
    coords_by_role: Mapping[str, Sequence[Coord]],
) -> AnnotationArtifacts:
    """Project role-bound cell witness groups to keyed bbox-set annotation."""

    value: dict[str, list[list[float]]] = {}
    for role, coords in sorted(coords_by_role.items()):
        value[str(role)] = [
            [round(float(v), 3) for v in _bbox_for_cell(rendered, coord)]
            for coord in coords
        ]
    return AnnotationArtifacts(
        annotation_type="keyed_bbox_set_map",
        value={str(role): [list(bbox) for bbox in bboxes] for role, bboxes in value.items()},
        annotation_gt=TypedValue(
            type="keyed_bbox_set_map",
            value={str(role): [list(bbox) for bbox in bboxes] for role, bboxes in value.items()},
        ),
        projected_annotation={
            "type": "keyed_bbox_set_map",
            "keyed_bbox_set_map": {str(role): [list(bbox) for bbox in bboxes] for role, bboxes in value.items()},
            "pixel_keyed_bbox_set_map": {str(role): [list(bbox) for bbox in bboxes] for role, bboxes in value.items()},
        },
    )


def cell_ids_for_coords(coords: Sequence[Coord]) -> tuple[str, ...]:
    """Return visible entity ids for board-coordinate witnesses."""

    return tuple(coord_to_cell_id(coord) for coord in coords)


def keyed_cell_ids_for_coords(coords_by_role: Mapping[str, Sequence[Coord]]) -> dict[str, list[str]]:
    """Return visible entity ids grouped by semantic annotation role."""

    return {str(role): [coord_to_cell_id(coord) for coord in coords] for role, coords in sorted(coords_by_role.items())}


__all__ = [
    "cell_ids_for_coords",
    "keyed_cell_ids_for_coords",
    "minesweeper_bbox_annotation",
    "minesweeper_bbox_set_annotation",
    "minesweeper_keyed_bbox_sets_annotation",
]
