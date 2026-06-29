"""Annotation projection helpers for Sudoku cells."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.puzzles.shared.common import (
    projected_puzzle_bbox_annotation,
    projected_puzzle_keyed_bbox_set_annotation,
)

from .rules import coord_to_cell_id
from .state import Coord


def cell_ids_for_coords(coords: Sequence[Coord]) -> list[str]:
    """Return render-map cell ids for Sudoku coordinates."""

    return [coord_to_cell_id((int(row), int(col))) for row, col in coords]


def bbox_set_for_coords(
    bbox_map: Mapping[str, Sequence[float]],
    coords: Sequence[Coord],
) -> tuple[dict[str, Any], list[str]]:
    """Project homogeneous Sudoku cell witnesses into a bbox-set annotation."""

    entity_ids = cell_ids_for_coords(coords)
    projected = projected_puzzle_bbox_annotation(bbox_map, entity_ids)
    projected["type"] = "bbox_set"
    projected["pixel_bbox_set"] = [list(bbox) for bbox in projected["bbox_set"]]
    return projected, entity_ids


def bbox_set_map_for_marked_cell_context(
    bbox_map: Mapping[str, Sequence[float]],
    *,
    marked_cell: Coord,
    constraint_coords: Sequence[Coord],
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Project a marked cell and its constraint cells into a bbox-set map."""

    role_ids = {
        "marked_cell": cell_ids_for_coords([marked_cell]),
        "constraint_cells": cell_ids_for_coords(constraint_coords),
    }
    return projected_puzzle_keyed_bbox_set_annotation(bbox_map, role_ids), role_ids


__all__ = [
    "bbox_set_for_coords",
    "bbox_set_map_for_marked_cell_context",
    "cell_ids_for_coords",
]
