"""Pure polyomino rules and shape transforms for missing-piece puzzles."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from .state import Cell, Cells


PUZZLE_POLYOMINO_PIECE_LIBRARY: Tuple[Cells, ...] = (
    ((0, 0), (1, 0)),
    ((0, 0), (1, 0), (2, 0)),
    ((0, 0), (0, 1), (1, 1)),
    ((0, 0), (1, 0), (2, 0), (3, 0)),
    ((0, 0), (1, 0), (0, 1), (1, 1)),
    ((0, 0), (1, 0), (2, 0), (1, 1)),
    ((0, 0), (0, 1), (0, 2), (1, 2)),
    ((1, 0), (2, 0), (0, 1), (1, 1)),
)

D4_TRANSFORMS: Tuple[str, ...] = (
    "identity",
    "rotate_90",
    "rotate_180",
    "rotate_270",
    "flip_horizontal",
    "flip_vertical",
    "flip_main_diagonal",
    "flip_anti_diagonal",
)


def _canonicalize_cells(cells: Iterable[Cell]) -> Cells:
    """Shift one cell set so its minimum x/y is `(0, 0)`."""

    sorted_cells = sorted((int(x), int(y)) for x, y in cells)
    if not sorted_cells:
        raise ValueError("polyomino cells cannot be empty")
    min_x = min(x for x, _ in sorted_cells)
    min_y = min(y for _, y in sorted_cells)
    return tuple(
        sorted(
            (int(x - min_x), int(y - min_y))
            for x, y in sorted_cells
        )
    )


def canonicalize_polyomino_cells(cells: Iterable[Cell]) -> Cells:
    """Return a canonical polyomino cell tuple."""

    return _canonicalize_cells(cells)


def _rotate_cells_90(cells: Cells) -> Cells:
    """Rotate one polyomino 90 degrees clockwise and canonicalize it."""

    return _canonicalize_cells((int(y), int(-x)) for x, y in cells)


def unique_rotations(cells: Cells) -> Tuple[Cells, ...]:
    """Return the unique rotation set for one polyomino without reflection."""

    current = _canonicalize_cells(cells)
    rotations: List[Cells] = []
    seen = set()
    for _index in range(4):
        if current not in seen:
            rotations.append(current)
            seen.add(current)
        current = _rotate_cells_90(current)
    return tuple(rotations)


def translate_polyomino_cells(cells: Cells, dx: int, dy: int) -> Cells:
    """Translate one canonical polyomino by integer offsets."""

    return tuple(
        sorted(
            (int(x + dx), int(y + dy))
            for x, y in cells
        )
    )


def polyomino_cell_count(cells: Cells) -> int:
    """Return the number of occupied cells in one polyomino."""

    return int(len(cells))


def polyomino_bbox_dims(cells: Cells) -> Tuple[int, int]:
    """Return `(width, height)` for one canonical polyomino."""

    max_x = max(int(x) for x, _ in cells)
    max_y = max(int(y) for _, y in cells)
    return int(max_x + 1), int(max_y + 1)


def canonical_rotation_signature(cells: Cells) -> Cells:
    """Return a rotation-invariant signature for one polyomino."""

    rotations = tuple(unique_rotations(canonicalize_polyomino_cells(cells)))
    return min(rotations)


def shape_bbox_dims(cells: Iterable[Cell]) -> Tuple[int, int]:
    """Return width and height of one canonical cell set."""

    canonical = canonicalize_polyomino_cells(cells)
    max_x = max(int(x) for x, _ in canonical)
    max_y = max(int(y) for _, y in canonical)
    return int(max_x + 1), int(max_y + 1)


def is_connected_cells(cells: Iterable[Cell]) -> bool:
    """Return whether a non-empty cell set is 4-connected."""

    cell_set = {(int(x), int(y)) for x, y in cells}
    if not cell_set:
        return False
    stack = [next(iter(cell_set))]
    seen: set[Cell] = set()
    while stack:
        cell_x, cell_y = stack.pop()
        if (cell_x, cell_y) in seen:
            continue
        seen.add((cell_x, cell_y))
        for delta_x, delta_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            candidate = (int(cell_x + delta_x), int(cell_y + delta_y))
            if candidate in cell_set and candidate not in seen:
                stack.append(candidate)
    return len(seen) == len(cell_set)


def missing_region_is_interior(
    *,
    target_cells: set[Cell],
    missing_cells: set[Cell],
) -> bool:
    """Return true when every missing cell is surrounded by target cells."""

    if not target_cells or not missing_cells:
        return False
    if not missing_cells <= target_cells:
        return False
    min_x = min(x for x, _ in target_cells)
    max_x = max(x for x, _ in target_cells)
    min_y = min(y for _, y in target_cells)
    max_y = max(y for _, y in target_cells)
    for cell_x, cell_y in missing_cells:
        if int(cell_x) in {int(min_x), int(max_x)}:
            return False
        if int(cell_y) in {int(min_y), int(max_y)}:
            return False
        for delta_x, delta_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (int(cell_x + delta_x), int(cell_y + delta_y)) not in target_cells:
                return False
    return True


def neighbors(cell: Cell) -> Tuple[Cell, ...]:
    """Return edge-neighbor coordinates for one cell."""

    x, y = int(cell[0]), int(cell[1])
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def apply_d4_transform(cells: Cells, transform_name: str) -> Cells:
    """Apply one square-grid rotation/reflection transform and canonicalize it."""

    selected = str(transform_name)

    def _map_cell(cell_x: int, cell_y: int) -> Cell:
        x, y = int(cell_x), int(cell_y)
        if selected == "identity":
            return x, y
        if selected == "rotate_90":
            return y, -x
        if selected == "rotate_180":
            return -x, -y
        if selected == "rotate_270":
            return -y, x
        if selected == "flip_horizontal":
            return -x, y
        if selected == "flip_vertical":
            return x, -y
        if selected == "flip_main_diagonal":
            return y, x
        if selected == "flip_anti_diagonal":
            return -y, -x
        raise ValueError(f"unsupported transform: {transform_name}")

    return canonicalize_polyomino_cells(
        _map_cell(int(cell_x), int(cell_y)) for cell_x, cell_y in cells
    )


def unique_d4_transforms(cells: Cells) -> Tuple[Dict[str, Any], ...]:
    """Return unique rotation/reflection transforms for one cell shape."""

    canonical = canonicalize_polyomino_cells(cells)
    seen: set[Cells] = set()
    transforms: List[Dict[str, Any]] = []
    for transform_name in D4_TRANSFORMS:
        transformed = apply_d4_transform(canonical, str(transform_name))
        if transformed in seen:
            continue
        seen.add(transformed)
        transforms.append({"transform": str(transform_name), "cells": transformed})
    return tuple(transforms)


def d4_signature(cells: Iterable[Cell]) -> Cells:
    """Return a canonical equivalence signature under rotation and reflection."""

    canonical = canonicalize_polyomino_cells(cells)
    return min(tuple(payload["cells"]) for payload in unique_d4_transforms(canonical))


__all__ = [
    "D4_TRANSFORMS",
    "PUZZLE_POLYOMINO_PIECE_LIBRARY",
    "apply_d4_transform",
    "canonical_rotation_signature",
    "canonicalize_polyomino_cells",
    "d4_signature",
    "is_connected_cells",
    "missing_region_is_interior",
    "neighbors",
    "polyomino_bbox_dims",
    "polyomino_cell_count",
    "shape_bbox_dims",
    "translate_polyomino_cells",
    "unique_d4_transforms",
    "unique_rotations",
]
