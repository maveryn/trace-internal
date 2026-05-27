"""Shared centered-grid layout helpers for tile task rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from trace.tasks.shared.bbox_projection import BBox
from .grid_graph import cell_id


@dataclass(frozen=True)
class _CenteredGridLayout:
    """Resolved centered grid layout in pixel space."""

    canvas_size: int
    rows: int
    cols: int
    cell_size: int
    origin_x: int
    origin_y: int
    board_width: int
    board_height: int


def resolve_centered_grid_layout(
    *,
    rows: int,
    cols: int,
    canvas_size: int,
    margin: int,
    min_cell_size: int = 8,
) -> _CenteredGridLayout:
    """Resolve one centered square-cell grid layout inside a canvas."""
    usable_w = max(int(min_cell_size), int(canvas_size) - 2 * int(margin))
    usable_h = max(int(min_cell_size), int(canvas_size) - 2 * int(margin))
    cell_size = max(int(min_cell_size), min(usable_w // int(cols), usable_h // int(rows)))
    board_w = int(cell_size) * int(cols)
    board_h = int(cell_size) * int(rows)
    origin_x = (int(canvas_size) - board_w) // 2
    origin_y = (int(canvas_size) - board_h) // 2
    return _CenteredGridLayout(
        canvas_size=int(canvas_size),
        rows=int(rows),
        cols=int(cols),
        cell_size=int(cell_size),
        origin_x=int(origin_x),
        origin_y=int(origin_y),
        board_width=int(board_w),
        board_height=int(board_h),
    )


def build_cell_bbox_map(layout: _CenteredGridLayout) -> Dict[str, BBox]:
    """Build deterministic per-cell pixel bounding boxes for one grid layout."""
    bbox_map: Dict[str, BBox] = {}
    for row in range(int(layout.rows)):
        for col in range(int(layout.cols)):
            x0 = int(layout.origin_x) + int(col) * int(layout.cell_size)
            y0 = int(layout.origin_y) + int(row) * int(layout.cell_size)
            x1 = x0 + int(layout.cell_size)
            y1 = y0 + int(layout.cell_size)
            bbox_map[cell_id((row, col))] = (float(x0), float(y0), float(x1), float(y1))
    return bbox_map
