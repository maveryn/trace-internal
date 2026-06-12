"""Annotation projection helpers for Connect Four games scenes."""

from __future__ import annotations

from typing import Sequence

from .common import Coord, coord_to_cell_id
from .rendering import RenderedConnectFourScene


def cell_bboxes_for_coords(
    rendered_scene: RenderedConnectFourScene,
    coords: Sequence[Coord],
) -> list[list[float]]:
    """Return rendered cell bboxes for board coordinates."""

    cell_bboxes = rendered_scene.render_map.get("cell_bboxes_px", {})
    bboxes: list[list[float]] = []
    for coord in coords:
        cell_id = coord_to_cell_id((int(coord[0]), int(coord[1])))
        bbox = cell_bboxes.get(str(cell_id))
        if bbox is None:
            raise ValueError(f"missing rendered Connect Four cell bbox for {cell_id}")
        bboxes.append([round(float(value), 3) for value in bbox])
    return bboxes


__all__ = ["cell_bboxes_for_coords"]
