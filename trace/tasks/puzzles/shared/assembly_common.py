"""Shared dataset builders and render defaults for spatial assembly puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from .common import resolve_puzzle_axis_variant


Cells = Tuple[Tuple[int, int], ...]

SUPPORTED_PUZZLE_ASSEMBLY_SCENE_VARIANTS: Tuple[str, ...] = (
    "assembly_strip",
    "assembly_card",
    "assembly_outline",
)
SUPPORTED_PUZZLE_ASSEMBLY_TASK_VARIANTS: Tuple[str, ...] = ("can_be_built",)


@dataclass(frozen=True)
class PuzzleAssemblyDefaults:
    """Stable fallback defaults shared by spatial assembly puzzles."""

    piece_count_min: int = 3
    piece_count_max: int = 4
    option_count_min: int = 5
    option_count_max: int = 7
    target_cell_count_min: int = 8
    target_cell_count_max: int = 11
    target_bbox_max_dim: int = 5

    canvas_width: int = 1200
    canvas_height: int = 980
    scene_margin_left_px: int = 64
    scene_margin_right_px: int = 64
    scene_margin_top_px: int = 56
    scene_margin_bottom_px: int = 56
    piece_card_size_px: int = 144
    piece_gap_px: int = 24
    piece_panel_padding_px: int = 24
    piece_to_options_gap_px: int = 56
    option_panel_width_px: int = 176
    option_panel_height_px: int = 204
    option_gap_px: int = 22
    option_row_gap_px: int = 22
    option_shape_box_size_px: int = 126
    option_label_gap_px: int = 16
    panel_corner_radius_px: int = 28
    cell_corner_radius_px: int = 8
    border_width_px: int = 3
    option_label_font_size_px: int = 30


@dataclass(frozen=True)
class PuzzleAssemblyRenderParams:
    """Resolved rendering knobs for spatial assembly scenes."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    piece_card_size_px: int
    piece_gap_px: int
    piece_panel_padding_px: int
    piece_to_options_gap_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_row_gap_px: int
    option_shape_box_size_px: int
    option_label_gap_px: int
    panel_corner_radius_px: int
    cell_corner_radius_px: int
    border_width_px: int
    option_label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    piece_card_fill_rgb: Tuple[int, int, int]
    option_panel_fill_rgb: Tuple[int, int, int]
    option_shape_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    piece_palette_rgb: Tuple[Tuple[int, int, int], ...]


_PIECE_LIBRARY: Tuple[Cells, ...] = (
    ((0, 0), (1, 0)),
    ((0, 0), (1, 0), (2, 0)),
    ((0, 0), (0, 1), (1, 1)),
    ((0, 0), (1, 0), (2, 0), (3, 0)),
    ((0, 0), (1, 0), (0, 1), (1, 1)),
    ((0, 0), (1, 0), (2, 0), (1, 1)),
    ((0, 0), (0, 1), (0, 2), (1, 2)),
    ((1, 0), (2, 0), (0, 1), (1, 1)),
)


def _resolve_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer generation or rendering parameter."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def resolve_assembly_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active assembly scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_ASSEMBLY_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_assembly_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic assembly variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_ASSEMBLY_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_assembly_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: PuzzleAssemblyDefaults,
) -> PuzzleAssemblyRenderParams:
    """Resolve rendering params for spatial assembly scenes."""

    palette = render_defaults.get(
        "piece_palette_rgb",
        [
            [221, 109, 95],
            [87, 160, 133],
            [105, 127, 214],
            [232, 179, 76],
        ],
    )
    if not isinstance(palette, Sequence) or len(palette) < 3:
        raise ValueError("piece_palette_rgb must contain at least three RGB colors")

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        raw = params.get(str(key), group_default(render_defaults, str(key), list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must be a length-3 RGB sequence")
        return tuple(int(value) for value in raw)

    return PuzzleAssemblyRenderParams(
        canvas_width=int(_resolve_int_param(params, render_defaults, "canvas_width", defaults.canvas_width)),
        canvas_height=int(_resolve_int_param(params, render_defaults, "canvas_height", defaults.canvas_height)),
        scene_margin_left_px=int(_resolve_int_param(params, render_defaults, "scene_margin_left_px", defaults.scene_margin_left_px)),
        scene_margin_right_px=int(_resolve_int_param(params, render_defaults, "scene_margin_right_px", defaults.scene_margin_right_px)),
        scene_margin_top_px=int(_resolve_int_param(params, render_defaults, "scene_margin_top_px", defaults.scene_margin_top_px)),
        scene_margin_bottom_px=int(_resolve_int_param(params, render_defaults, "scene_margin_bottom_px", defaults.scene_margin_bottom_px)),
        piece_card_size_px=int(_resolve_int_param(params, render_defaults, "piece_card_size_px", defaults.piece_card_size_px)),
        piece_gap_px=int(_resolve_int_param(params, render_defaults, "piece_gap_px", defaults.piece_gap_px)),
        piece_panel_padding_px=int(_resolve_int_param(params, render_defaults, "piece_panel_padding_px", defaults.piece_panel_padding_px)),
        piece_to_options_gap_px=int(_resolve_int_param(params, render_defaults, "piece_to_options_gap_px", defaults.piece_to_options_gap_px)),
        option_panel_width_px=int(_resolve_int_param(params, render_defaults, "option_panel_width_px", defaults.option_panel_width_px)),
        option_panel_height_px=int(_resolve_int_param(params, render_defaults, "option_panel_height_px", defaults.option_panel_height_px)),
        option_gap_px=int(_resolve_int_param(params, render_defaults, "option_gap_px", defaults.option_gap_px)),
        option_row_gap_px=int(_resolve_int_param(params, render_defaults, "option_row_gap_px", defaults.option_row_gap_px)),
        option_shape_box_size_px=int(_resolve_int_param(params, render_defaults, "option_shape_box_size_px", defaults.option_shape_box_size_px)),
        option_label_gap_px=int(_resolve_int_param(params, render_defaults, "option_label_gap_px", defaults.option_label_gap_px)),
        panel_corner_radius_px=int(_resolve_int_param(params, render_defaults, "panel_corner_radius_px", defaults.panel_corner_radius_px)),
        cell_corner_radius_px=int(_resolve_int_param(params, render_defaults, "cell_corner_radius_px", defaults.cell_corner_radius_px)),
        border_width_px=int(_resolve_int_param(params, render_defaults, "border_width_px", defaults.border_width_px)),
        option_label_font_size_px=int(_resolve_int_param(params, render_defaults, "option_label_font_size_px", defaults.option_label_font_size_px)),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        piece_card_fill_rgb=_triple("piece_card_fill_rgb", (252, 252, 255)),
        option_panel_fill_rgb=_triple("option_panel_fill_rgb", (251, 251, 255)),
        option_shape_fill_rgb=_triple("option_shape_fill_rgb", (252, 252, 255)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        piece_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
    )


def _canonicalize_cells(cells: Iterable[Tuple[int, int]]) -> Cells:
    """Shift one cell set so its minimum x/y is `(0, 0)`."""

    sorted_cells = sorted((int(x), int(y)) for x, y in cells)
    if not sorted_cells:
        raise ValueError("polyomino cells cannot be empty")
    min_x = min(x for x, _ in sorted_cells)
    min_y = min(y for _, y in sorted_cells)
    return tuple(sorted((int(x - min_x), int(y - min_y)) for x, y in sorted_cells))


def _rotate_cells_90(cells: Cells) -> Cells:
    """Rotate one polyomino 90 degrees clockwise around the origin and canonicalize it."""

    return _canonicalize_cells((int(y), int(-x)) for x, y in cells)


def unique_rotations(cells: Cells) -> Tuple[Cells, ...]:
    """Return the unique rotation set for one polyomino without reflection."""

    current = _canonicalize_cells(cells)
    rotations: List[Cells] = []
    seen = set()
    for _ in range(4):
        if current not in seen:
            rotations.append(current)
            seen.add(current)
        current = _rotate_cells_90(current)
    return tuple(rotations)


def _translate_cells(cells: Cells, dx: int, dy: int) -> Cells:
    """Translate one canonical polyomino by integer offsets."""

    return tuple(sorted((int(x + dx), int(y + dy)) for x, y in cells))


def _cell_count(cells: Cells) -> int:
    """Return the number of occupied cells in one polyomino."""

    return int(len(cells))


def polyomino_bbox_dims(cells: Cells) -> Tuple[int, int]:
    """Return `(width, height)` for one canonical polyomino."""

    max_x = max(int(x) for x, _ in cells)
    max_y = max(int(y) for _, y in cells)
    return int(max_x + 1), int(max_y + 1)


def _are_adjacent(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    """Return whether two cells share one edge."""

    return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1])) == 1


def _sample_piece_shapes(
    *,
    piece_count: int,
    target_cell_count_min: int,
    target_cell_count_max: int,
    rng,
) -> Tuple[Cells, ...]:
    """Sample one distinct piece set whose total area fits the target support."""

    for _ in range(500):
        shapes = tuple(_canonicalize_cells(rng.choice(_PIECE_LIBRARY)) for _ in range(int(piece_count)))
        area = sum(_cell_count(shape) for shape in shapes)
        distinct_shape_count = len({shape for shape in shapes})
        if int(target_cell_count_min) <= int(area) <= int(target_cell_count_max) and int(distinct_shape_count) >= 2:
            return shapes
    raise RuntimeError("failed to sample assembly pieces within the target area support")


def _place_piece_shapes(
    piece_shapes: Sequence[Cells],
    *,
    target_bbox_max_dim: int,
    rng,
) -> Cells:
    """Place rotated pieces into one connected target silhouette."""

    placed_shapes: List[Cells] = []
    union_cells: set[Tuple[int, int]] = set()
    first_shape = rng.choice(list(unique_rotations(piece_shapes[0])))
    placed_shapes.append(first_shape)
    union_cells.update(first_shape)

    for piece_shape in piece_shapes[1:]:
        rotations = list(unique_rotations(piece_shape))
        rng.shuffle(rotations)
        success = False
        for rotation in rotations:
            union_list = list(union_cells)
            rng.shuffle(union_list)
            piece_cells = list(rotation)
            rng.shuffle(piece_cells)
            for union_cell in union_list:
                directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                rng.shuffle(directions)
                for dir_x, dir_y in directions:
                    target_anchor = (int(union_cell[0] + dir_x), int(union_cell[1] + dir_y))
                    if target_anchor in union_cells:
                        continue
                    for piece_cell in piece_cells:
                        dx = int(target_anchor[0] - piece_cell[0])
                        dy = int(target_anchor[1] - piece_cell[1])
                        translated = set(_translate_cells(rotation, dx, dy))
                        if translated & union_cells:
                            continue
                        combined = set(union_cells) | set(translated)
                        canonical_combined = _canonicalize_cells(combined)
                        width, height = polyomino_bbox_dims(canonical_combined)
                        if max(int(width), int(height)) > int(target_bbox_max_dim):
                            continue
                        union_cells = combined
                        placed_shapes.append(_canonicalize_cells(translated))
                        success = True
                        break
                    if success:
                        break
                if success:
                    break
            if success:
                break
        if not success:
            raise RuntimeError("failed to place one assembly piece into a connected target silhouette")

    return _canonicalize_cells(union_cells)


def _sample_connected_shape(
    *,
    area: int,
    target_bbox_max_dim: int,
    preferred_bbox: Tuple[int, int],
    rng,
) -> Cells:
    """Sample one connected polyomino with approximately matching footprint."""

    for _ in range(600):
        cells = {(0, 0)}
        while len(cells) < int(area):
            frontier: set[Tuple[int, int]] = set()
            for cell_x, cell_y in cells:
                for delta_x, delta_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    candidate = (int(cell_x + delta_x), int(cell_y + delta_y))
                    if candidate not in cells:
                        frontier.add(candidate)
            frontier_list = list(frontier)
            rng.shuffle(frontier_list)
            chosen = frontier_list[0]
            cells.add((int(chosen[0]), int(chosen[1])))
        canonical = _canonicalize_cells(cells)
        width, height = polyomino_bbox_dims(canonical)
        if max(int(width), int(height)) > int(target_bbox_max_dim):
            continue
        if abs(int(width) - int(preferred_bbox[0])) > 1 or abs(int(height) - int(preferred_bbox[1])) > 1:
            continue
        return canonical
    raise RuntimeError("failed to sample one connected assembly distractor shape")


def can_tile_polyomino_with_pieces(target_cells: Cells, piece_shapes: Sequence[Cells]) -> bool:
    """Return whether the target silhouette is tileable by the pieces under rotation only."""

    target = frozenset((int(x), int(y)) for x, y in target_cells)
    rotations_by_piece = [unique_rotations(_canonicalize_cells(shape)) for shape in piece_shapes]
    initial_indices = tuple(range(len(rotations_by_piece)))
    cache: Dict[Tuple[frozenset[Tuple[int, int]], Tuple[int, ...]], bool] = {}

    def _search(remaining_cells: frozenset[Tuple[int, int]], remaining_piece_indices: Tuple[int, ...]) -> bool:
        if not remaining_cells:
            return True
        key = (remaining_cells, remaining_piece_indices)
        if key in cache:
            return bool(cache[key])
        anchor_cell = min(remaining_cells)
        for position, piece_index in enumerate(remaining_piece_indices):
            for rotation in rotations_by_piece[int(piece_index)]:
                for piece_cell in rotation:
                    translated = frozenset(
                        (int(cell_x + anchor_cell[0] - piece_cell[0]), int(cell_y + anchor_cell[1] - piece_cell[1]))
                        for cell_x, cell_y in rotation
                    )
                    if not translated <= remaining_cells:
                        continue
                    next_indices = remaining_piece_indices[:position] + remaining_piece_indices[position + 1 :]
                    next_remaining = frozenset(cell for cell in remaining_cells if cell not in translated)
                    if _search(next_remaining, next_indices):
                        cache[key] = True
                        return True
        cache[key] = False
        return False

    return bool(_search(target, initial_indices))


def _resolve_piece_count(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleAssemblyDefaults,
    task_id: str,
) -> Tuple[int, Tuple[int, int]]:
    """Resolve one deterministic piece count within the configured support."""

    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="piece_count_min",
        max_key="piece_count_max",
        fallback_min=int(defaults.piece_count_min),
        fallback_max=int(defaults.piece_count_max),
        context=f"{task_id} piece-count bounds",
    )
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:piece_count",
        )
    )
    chosen = int(lower + (selection % (upper - lower + 1)))
    return int(chosen), (int(lower), int(upper))


def _resolve_option_count(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleAssemblyDefaults,
    task_id: str,
) -> Tuple[int, Tuple[int, int]]:
    """Resolve one deterministic option count within the configured support."""

    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=int(defaults.option_count_min),
        fallback_max=int(defaults.option_count_max),
        context=f"{task_id} option-count bounds",
    )
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:option_count",
        )
    )
    chosen = int(lower + (selection % (upper - lower + 1)))
    return int(chosen), (int(lower), int(upper))


def build_assembly_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleAssemblyDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic assembly puzzle dataset."""

    if str(task_variant) not in set(SUPPORTED_PUZZLE_ASSEMBLY_TASK_VARIANTS):
        raise ValueError(f"unsupported spatial assembly variant: {task_variant}")
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    piece_count, piece_count_range = _resolve_piece_count(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    option_count, option_count_range = _resolve_option_count(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    target_cell_count_min, target_cell_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="target_cell_count_min",
        max_key="target_cell_count_max",
        fallback_min=int(defaults.target_cell_count_min),
        fallback_max=int(defaults.target_cell_count_max),
        context=f"{task_id} target-cell-count bounds",
    )
    target_bbox_max_dim = int(
        params.get(
            "target_bbox_max_dim",
            group_default(gen_defaults, "target_bbox_max_dim", int(defaults.target_bbox_max_dim)),
        )
    )

    piece_shapes: Tuple[Cells, ...]
    target_cells: Cells
    distractor_shapes: List[Cells]
    target_cell_count = 0
    target_bbox = (0, 0)
    for _ in range(120):
        piece_shapes = _sample_piece_shapes(
            piece_count=int(piece_count),
            target_cell_count_min=int(target_cell_count_min),
            target_cell_count_max=int(target_cell_count_max),
            rng=rng,
        )
        try:
            target_cells = _place_piece_shapes(
                piece_shapes,
                target_bbox_max_dim=int(target_bbox_max_dim),
                rng=rng,
            )
        except RuntimeError:
            continue
        target_cell_count = int(_cell_count(target_cells))
        target_bbox = polyomino_bbox_dims(target_cells)

        distractor_shapes = []
        seen_shapes = {target_cells}
        distractor_attempts = 0
        while len(distractor_shapes) < int(option_count - 1) and int(distractor_attempts) < 2200:
            distractor_attempts += 1
            try:
                candidate = _sample_connected_shape(
                    area=int(target_cell_count),
                    target_bbox_max_dim=int(target_bbox_max_dim),
                    preferred_bbox=target_bbox,
                    rng=rng,
                )
            except RuntimeError:
                break
            if candidate in seen_shapes:
                continue
            seen_shapes.add(candidate)
            if can_tile_polyomino_with_pieces(candidate, piece_shapes):
                continue
            distractor_shapes.append(candidate)
        if len(distractor_shapes) == int(option_count - 1):
            break
    else:
        raise RuntimeError("failed to construct a complete assembly option set")

    correct_option_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:correct_option_index",
        )
    ) % int(option_count)
    answer_option_label = option_label_for_index(int(correct_option_index))
    correct_option_panel_id = f"option_panel_{int(correct_option_index + 1)}"

    option_shapes = list(distractor_shapes)
    option_shapes.insert(int(correct_option_index), target_cells)
    option_specs: List[Dict[str, Any]] = []
    for option_index, option_cells in enumerate(option_shapes):
        panel_id = f"option_panel_{int(option_index + 1)}"
        option_specs.append(
            {
                "option_panel_id": str(panel_id),
                "option_label": str(option_label_for_index(int(option_index))),
                "cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in option_cells],
                "cell_count": int(_cell_count(option_cells)),
                "bbox_dims": list(polyomino_bbox_dims(option_cells)),
                "is_correct": bool(option_index == int(correct_option_index)),
                "is_tileable": bool(option_cells == target_cells),
            }
        )

    piece_specs = [
        {
            "piece_id": f"piece_{int(index + 1)}",
            "cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in piece_shape],
            "cell_count": int(_cell_count(piece_shape)),
            "bbox_dims": list(polyomino_bbox_dims(piece_shape)),
            "rotation_count": int(len(unique_rotations(piece_shape))),
        }
        for index, piece_shape in enumerate(piece_shapes)
    ]

    return {
        "task_variant": str(task_variant),
        "piece_specs": list(piece_specs),
        "piece_shapes": [tuple(shape) for shape in piece_shapes],
        "piece_count": int(piece_count),
        "piece_count_range": [int(piece_count_range[0]), int(piece_count_range[1])],
        "option_specs": list(option_specs),
        "option_count": int(option_count),
        "option_count_range": [int(option_count_range[0]), int(option_count_range[1])],
        "target_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in target_cells],
        "target_bbox_dims": [int(target_bbox[0]), int(target_bbox[1])],
        "target_cell_count": int(target_cell_count),
        "target_cell_count_range": [int(target_cell_count_min), int(target_cell_count_max)],
        "answer_option_label": str(answer_option_label),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(correct_option_panel_id),
        "valid_option_panel_ids": [str(correct_option_panel_id)],
        "solver_trace": {
            "task_variant": str(task_variant),
            "piece_shapes": [
                [[int(cell_x), int(cell_y)] for cell_x, cell_y in shape]
                for shape in piece_shapes
            ],
            "target_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in target_cells],
            "target_cell_count": int(target_cell_count),
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(answer_option_label),
            "correct_option_panel_id": str(correct_option_panel_id),
            "option_tileability": {
                str(spec["option_panel_id"]): bool(spec["is_tileable"])
                for spec in option_specs
            },
            "piece_count": int(piece_count),
            "option_count": int(option_count),
            "target_bbox_dims": [int(target_bbox[0]), int(target_bbox[1])],
        },
    }


__all__ = [
    "PuzzleAssemblyDefaults",
    "PuzzleAssemblyRenderParams",
    "SUPPORTED_PUZZLE_ASSEMBLY_SCENE_VARIANTS",
    "SUPPORTED_PUZZLE_ASSEMBLY_TASK_VARIANTS",
    "build_assembly_dataset_for_variant",
    "can_tile_polyomino_with_pieces",
    "polyomino_bbox_dims",
    "resolve_assembly_render_params",
    "resolve_assembly_scene_variant",
    "resolve_assembly_task_variant",
    "unique_rotations",
]
