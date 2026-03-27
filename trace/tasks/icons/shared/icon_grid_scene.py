"""Shared compact grid-layout helpers for labeled icon cell scenes."""

from __future__ import annotations

from typing import List, Tuple


BBox = Tuple[int, int, int, int]


def resolve_compact_grid_shape(cell_count: int) -> Tuple[int, int]:
    """Return a compact `(rows, cols)` grid for a requested labeled cell count."""

    n = int(cell_count)
    if n <= 4:
        return 2, 2
    if n <= 6:
        return 2, 3
    if n <= 8:
        return 2, 4
    return 3, 4


def resolve_grid_cell_slots(content_bbox: BBox, *, cell_count: int, cell_padding_px: int) -> List[BBox]:
    """Return row-major grid slots inside one content rectangle."""

    rows, cols = resolve_compact_grid_shape(int(cell_count))
    x0, y0, x1, y1 = content_bbox
    width = max(1, int(x1 - x0))
    height = max(1, int(y1 - y0))
    cell_w = width / float(cols)
    cell_h = height / float(rows)
    pad = max(0, int(cell_padding_px))
    slots: List[BBox] = []
    for row in range(rows):
        for col in range(cols):
            if len(slots) >= int(cell_count):
                return slots
            slot_x0 = int(round(float(x0) + (float(col) * cell_w))) + pad
            slot_y0 = int(round(float(y0) + (float(row) * cell_h))) + pad
            slot_x1 = int(round(float(x0) + (float(col + 1) * cell_w))) - pad
            slot_y1 = int(round(float(y0) + (float(row + 1) * cell_h))) - pad
            slots.append((slot_x0, slot_y0, slot_x1, slot_y1))
    return slots


__all__ = ["resolve_compact_grid_shape", "resolve_grid_cell_slots"]
