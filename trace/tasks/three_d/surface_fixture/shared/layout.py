"""Surface-fixture cell layout helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .state import SEMANTIC_COLOR_RGB
from .rendering import layout_surface_element_grid


def layout_cells(
    *,
    scene_variant: str,
    element_type: str,
    rows: int,
    cols: int,
    present_indices: Sequence[int],
    target_indices: Sequence[int],
    rng: Any,
    layout_style: str,
    color_by_index: Mapping[int, str] | None = None,
    state_by_index: Mapping[int, str] | None = None,
    reference_index: int | None = None,
    include_absent: bool = False,
) -> List[Dict[str, Any]]:
    """Create projected-cell records before pixel rendering."""

    color_by_index = color_by_index or {}
    state_by_index = state_by_index or {}
    present_set = {int(index) for index in present_indices}
    target_set = {int(index) for index in target_indices}
    u_pad = 0.065
    v_pad = 0.075
    gap = 0.016
    if str(layout_style) == "variable_grid":
        col_weights = [float(rng.uniform(0.78, 1.22)) for _ in range(int(cols))]
        row_weights = [float(rng.uniform(0.82, 1.18)) for _ in range(int(rows))]
    else:
        col_weights = [1.0 for _ in range(int(cols))]
        row_weights = [1.0 for _ in range(int(rows))]
    col_total = sum(col_weights) or 1.0
    row_total = sum(row_weights) or 1.0
    col_edges = [u_pad]
    for weight in col_weights:
        col_edges.append(float(col_edges[-1]) + (1.0 - 2.0 * u_pad) * float(weight) / float(col_total))
    row_edges = [v_pad]
    for weight in row_weights:
        row_edges.append(float(row_edges[-1]) + (1.0 - 2.0 * v_pad) * float(weight) / float(row_total))

    cells: List[Dict[str, Any]] = []
    for flat_index in range(int(rows) * int(cols)):
        row = int(flat_index // int(cols))
        col = int(flat_index % int(cols))
        u0 = float(col_edges[col])
        u1 = float(col_edges[col + 1])
        v0 = float(row_edges[row])
        v1 = float(row_edges[row + 1])
        if str(layout_style) == "brick_grid" and row % 2 == 1:
            shift = ((u1 - u0) * 0.22)
            u0 = max(u_pad, u0 + shift)
            u1 = min(1.0 - u_pad, u1 + shift)
        is_present = int(flat_index) in present_set
        if not is_present and not bool(include_absent):
            continue
        color_name = str(color_by_index.get(int(flat_index), ""))
        state = str(state_by_index.get(int(flat_index), "normal"))
        count_role = "target" if int(flat_index) in target_set else "distractor"
        if reference_index is not None and int(flat_index) == int(reference_index):
            count_role = "reference"
        element_id = f"{element_type}_{flat_index:02d}" if is_present else f"missing_{element_type}_{flat_index:02d}"
        cells.append(
            {
                "element_id": str(element_id),
                "cell_id": f"cell_{flat_index:02d}",
                "flat_index": int(flat_index),
                "element_type": str(element_type),
                "row": int(row),
                "column": int(col),
                "u0": float(u0 + gap),
                "u1": float(u1 - gap),
                "v0": float(v0 + gap),
                "v1": float(v1 - gap),
                "present": bool(is_present),
                "color_name": str(color_name),
                "fill_rgb": list(SEMANTIC_COLOR_RGB[color_name]) if color_name else None,
                "state": str(state),
                "count_role": str(count_role),
            }
        )
    return cells


def target_ids_from_indices(cells: Sequence[Mapping[str, Any]], target_indices: Sequence[int]) -> List[str]:
    """Return element ids for target flat indices."""

    target_set = {int(index) for index in target_indices}
    return [str(cell["element_id"]) for cell in cells if int(cell["flat_index"]) in target_set]


def grid_for_total(total_slots: int, *, min_cols: int = 3) -> Tuple[int, int]:
    """Return a stable rows/columns grid for a target slot count."""

    rows, cols = layout_surface_element_grid(int(total_slots))
    cols = max(int(min_cols), int(cols))
    rows = int((int(total_slots) + int(cols) - 1) // int(cols))
    return int(rows), int(cols)


def edge_neighbors(index: int, rows: int, cols: int) -> List[int]:
    """Return flat-index edge neighbors for one grid cell."""

    row = int(index // cols)
    col = int(index % cols)
    neighbors = []
    if row > 0:
        neighbors.append((row - 1) * cols + col)
    if row + 1 < rows:
        neighbors.append((row + 1) * cols + col)
    if col > 0:
        neighbors.append(row * cols + col - 1)
    if col + 1 < cols:
        neighbors.append(row * cols + col + 1)
    return neighbors


__all__ = [
    "edge_neighbors",
    "grid_for_total",
    "layout_cells",
    "target_ids_from_indices",
]
