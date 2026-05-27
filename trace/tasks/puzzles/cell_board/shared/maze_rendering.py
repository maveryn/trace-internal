"""Shared maze rendering helpers for tile/path tasks."""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from PIL import ImageDraw

from trace.tasks.shared.bbox_projection import BBox, bbox_center
from .grid_layout import build_cell_bbox_map, resolve_centered_grid_layout
from .grid_graph import cell_id


Coord = Tuple[int, int]


def render_path_maze_scene(
    rows: int,
    cols: int,
    blocked: Sequence[Sequence[bool]],
    start: Coord,
    goal: Coord,
    path: Sequence[Coord],
    *,
    draw: ImageDraw.ImageDraw,
    canvas_size: int,
    margin: int,
) -> Dict[str, BBox]:
    """Render one tile maze with highlighted path and start/goal markers."""
    layout = resolve_centered_grid_layout(
        rows=rows,
        cols=cols,
        canvas_size=canvas_size,
        margin=margin,
    )
    path_set = set(path)
    bbox_map = build_cell_bbox_map(layout)

    for row in range(rows):
        for col in range(cols):
            cell = (row, col)
            x0, y0, x1, y1 = bbox_map[cell_id(cell)]
            fill = (255, 255, 255)
            if blocked[row][col]:
                fill = (20, 20, 20)
            elif cell in path_set:
                fill = (164, 211, 255)
            draw.rectangle([x0, y0, x1, y1], fill=fill, outline=(110, 110, 110), width=1)

    for rc, color in ((start, (36, 149, 59)), (goal, (190, 44, 44))):
        cx, cy = bbox_center(bbox_map[cell_id(rc)])
        radius = max(4, int(round(float(layout.cell_size) * 0.22)))
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=color,
            outline=(12, 12, 12),
            width=1,
        )
    return bbox_map
