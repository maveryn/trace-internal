"""Tents puzzle tasks over row/column clue grids and marked trees."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_puzzle_task_defaults,
    projected_puzzle_bbox_evidence,
    resolve_puzzle_axis_variant,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds
from ..shared.drawing import draw_centered_text, draw_rounded_rect
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


SCENE_ID = "tents"
MISSING_TENT_TASK_ID = "task_puzzles__tents__tents_missing_tent_cell_label"
VALID_CANDIDATE_COUNT_TASK_ID = "task_puzzles__tents__tents_valid_candidate_count"

SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "missing_tent_cell_label",
    "valid_candidate_count",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "tents_classic",
    "tents_card",
    "tents_blueprint",
)
SUPPORTED_PALETTE_VARIANTS: Tuple[str, ...] = (
    "garden",
    "autumn",
    "lake",
    "violet",
    "slate",
)
_SCENE_LOAD_BY_VARIANT = {
    "tents_classic": 0.18,
    "tents_card": 0.22,
    "tents_blueprint": 0.24,
}
_REASONING_LOAD_BY_QUERY = {
    "missing_tent_cell_label": 0.54,
    "valid_candidate_count": 0.62,
}
_STYLE_COLORS = {
    "tents_classic": {
        "panel_fill": (249, 248, 241),
        "grid_fill": (255, 253, 245),
        "cell_a": (253, 252, 245),
        "cell_b": (247, 250, 240),
        "grid_line": (158, 147, 120),
        "heavy_line": (92, 86, 72),
        "clue_fill": (238, 234, 217),
        "candidate_fill": (255, 240, 168),
        "candidate_outline": (140, 112, 38),
        "tree_fill": (55, 132, 83),
        "tree_outline": (33, 84, 54),
        "tent_fill": (202, 91, 75),
        "tent_shadow": (130, 62, 54),
        "accent": (50, 86, 150),
    },
    "tents_card": {
        "panel_fill": (244, 249, 251),
        "grid_fill": (250, 253, 255),
        "cell_a": (251, 253, 255),
        "cell_b": (242, 248, 252),
        "grid_line": (155, 178, 192),
        "heavy_line": (69, 91, 108),
        "clue_fill": (226, 238, 246),
        "candidate_fill": (255, 236, 164),
        "candidate_outline": (127, 99, 34),
        "tree_fill": (48, 139, 112),
        "tree_outline": (31, 86, 74),
        "tent_fill": (197, 93, 111),
        "tent_shadow": (122, 58, 72),
        "accent": (53, 103, 177),
    },
    "tents_blueprint": {
        "panel_fill": (239, 246, 252),
        "grid_fill": (247, 252, 255),
        "cell_a": (250, 253, 255),
        "cell_b": (240, 248, 253),
        "grid_line": (139, 171, 196),
        "heavy_line": (43, 82, 118),
        "clue_fill": (222, 237, 248),
        "candidate_fill": (255, 239, 150),
        "candidate_outline": (124, 96, 30),
        "tree_fill": (55, 128, 112),
        "tree_outline": (30, 78, 68),
        "tent_fill": (189, 87, 95),
        "tent_shadow": (115, 52, 60),
        "accent": (37, 90, 150),
    },
}
_PALETTE_COLORS = {
    "garden": {
        "clue_fill": (238, 234, 217),
        "candidate_fill": (255, 240, 168),
        "candidate_outline": (140, 112, 38),
        "candidate_label_fill": (255, 250, 215),
        "tree_fill": (55, 132, 83),
        "tree_outline": (33, 84, 54),
        "tent_fill": (202, 91, 75),
        "tent_shadow": (130, 62, 54),
        "tent_flap_fill": (245, 178, 142),
    },
    "autumn": {
        "clue_fill": (244, 228, 205),
        "candidate_fill": (255, 225, 153),
        "candidate_outline": (145, 91, 32),
        "candidate_label_fill": (255, 246, 212),
        "tree_fill": (136, 115, 48),
        "tree_outline": (83, 72, 34),
        "tent_fill": (183, 86, 47),
        "tent_shadow": (111, 55, 33),
        "tent_flap_fill": (244, 177, 116),
    },
    "lake": {
        "clue_fill": (222, 239, 242),
        "candidate_fill": (187, 231, 232),
        "candidate_outline": (39, 108, 125),
        "candidate_label_fill": (231, 249, 248),
        "tree_fill": (46, 130, 124),
        "tree_outline": (24, 78, 78),
        "tent_fill": (64, 107, 182),
        "tent_shadow": (39, 68, 119),
        "tent_flap_fill": (169, 207, 244),
    },
    "violet": {
        "clue_fill": (235, 229, 247),
        "candidate_fill": (226, 211, 250),
        "candidate_outline": (99, 76, 154),
        "candidate_label_fill": (246, 240, 255),
        "tree_fill": (64, 128, 101),
        "tree_outline": (34, 76, 62),
        "tent_fill": (131, 92, 183),
        "tent_shadow": (82, 57, 118),
        "tent_flap_fill": (212, 190, 240),
    },
    "slate": {
        "clue_fill": (229, 234, 238),
        "candidate_fill": (239, 219, 155),
        "candidate_outline": (93, 80, 51),
        "candidate_label_fill": (251, 246, 225),
        "tree_fill": (73, 118, 88),
        "tree_outline": (42, 70, 54),
        "tent_fill": (100, 115, 135),
        "tent_shadow": (57, 68, 83),
        "tent_flap_fill": (192, 202, 214),
    },
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "logic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="logic", apply_prob=0.5)


Cell = Tuple[int, int]


@dataclass(frozen=True)
class CandidateCellSpec:
    """One labeled candidate cell on a tents board."""

    label: str
    row: int
    col: int
    is_correct: bool
    is_legal: bool

    @property
    def cell(self) -> Cell:
        return (int(self.row), int(self.col))


@dataclass(frozen=True)
class TentsRenderParams:
    """Resolved rendering knobs for one tents-grid scene."""

    canvas_width: int
    canvas_height: int
    cell_size_px: int
    left_clue_width_px: int
    top_clue_height_px: int
    grid_line_width_px: int
    heavy_line_width_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    clue_font_size_px: int
    candidate_font_size_px: int
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    style_overrides: Dict[str, Tuple[int, int, int]]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class RenderedTentsScene:
    """Rendered tents-grid scene plus traceable geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    cell_bbox_map: Dict[str, List[float]]
    clue_bbox_map: Dict[str, List[float]]
    item_bbox_map: Dict[str, List[float]]


def _neighbors4(cell: Cell, rows: int, cols: int) -> List[Cell]:
    row, col = int(cell[0]), int(cell[1])
    candidates = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
    return [(int(r), int(c)) for r, c in candidates if 0 <= int(r) < int(rows) and 0 <= int(c) < int(cols)]


def _neighbors8(cell: Cell, rows: int, cols: int) -> List[Cell]:
    row, col = int(cell[0]), int(cell[1])
    out: List[Cell] = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr = int(row + dr)
            cc = int(col + dc)
            if 0 <= rr < int(rows) and 0 <= cc < int(cols):
                out.append((rr, cc))
    return out


def _touches_any_tent(cell: Cell, tents: Iterable[Cell], rows: int, cols: int) -> bool:
    near = set(_neighbors8(cell, int(rows), int(cols)))
    return any(tuple(tent) in near for tent in tents)


def _count_by_axis(cells: Iterable[Cell], size: int, axis: int) -> List[int]:
    counts = [0 for _ in range(int(size))]
    for row, col in cells:
        index = int(row if int(axis) == 0 else col)
        counts[int(index)] += 1
    return counts


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_palette_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PALETTE_VARIANTS,
        task_id=str(task_id),
        explicit_key="palette_variant",
        weights_key="palette_variant_weights",
        balance_flag_key="balanced_palette_variant_sampling",
        axis_namespace="palette_variant",
    )


def _resolve_grid_size(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    rng,
) -> Tuple[int, int, Tuple[int, int], Tuple[int, int]]:
    row_range = _get_range(
        params,
        gen_defaults,
        min_key="grid_rows_min",
        max_key="grid_rows_max",
        fallback_min=6,
        fallback_max=8,
    )
    col_range = _get_range(
        params,
        gen_defaults,
        min_key="grid_cols_min",
        max_key="grid_cols_max",
        fallback_min=6,
        fallback_max=8,
    )
    rows = int(params.get("grid_rows", rng.randint(int(row_range[0]), int(row_range[1]))))
    cols = int(params.get("grid_cols", rng.randint(int(col_range[0]), int(col_range[1]))))
    if not int(row_range[0]) <= int(rows) <= int(row_range[1]):
        raise ValueError("grid_rows falls outside configured range")
    if not int(col_range[0]) <= int(cols) <= int(col_range[1]):
        raise ValueError("grid_cols falls outside configured range")
    return int(rows), int(cols), tuple(row_range), tuple(col_range)


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> TentsRenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.tents.unit_size",
    )
    return TentsRenderParams(
        canvas_width=int(render_defaults.get("canvas_width", 1100)),
        canvas_height=int(render_defaults.get("canvas_height", 860)),
        cell_size_px=scale_puzzle_px(render_defaults.get("cell_size_px", 62), unit_scale, min_px=22),
        left_clue_width_px=scale_puzzle_px(render_defaults.get("left_clue_width_px", 78), unit_scale, min_px=38),
        top_clue_height_px=scale_puzzle_px(render_defaults.get("top_clue_height_px", 78), unit_scale, min_px=38),
        grid_line_width_px=scale_puzzle_px(render_defaults.get("grid_line_width_px", 2), unit_scale, min_px=1),
        heavy_line_width_px=scale_puzzle_px(render_defaults.get("heavy_line_width_px", 4), unit_scale, min_px=2),
        panel_padding_px=scale_puzzle_px(render_defaults.get("panel_padding_px", 26), unit_scale, min_px=12),
        panel_corner_radius_px=scale_puzzle_px(render_defaults.get("panel_corner_radius_px", 18), unit_scale, min_px=7),
        clue_font_size_px=scale_puzzle_px(render_defaults.get("clue_font_size_px", 28), unit_scale, min_px=14),
        candidate_font_size_px=scale_puzzle_px(render_defaults.get("candidate_font_size_px", 30), unit_scale, min_px=14),
        text_color_rgb=_rgb(render_defaults.get("text_color_rgb"), (28, 32, 38)),
        text_stroke_rgb=_rgb(render_defaults.get("text_stroke_rgb"), (255, 255, 255)),
        style_overrides={},
        unit_size_jitter=dict(unit_meta),
    )


def _option_labels(count: int) -> List[str]:
    return [option_label_for_index(index) for index in range(int(count))]


def _sample_marked_tree(rows: int, cols: int, *, rng) -> Cell:
    return (
        int(rng.randint(1, max(1, int(rows) - 2))),
        int(rng.randint(1, max(1, int(cols) - 2))),
    )


def _candidate_blocker_positions(
    *,
    candidate_cell: Cell,
    valid_cells: Sequence[Cell],
    protected_cells: Sequence[Cell],
    visible_tents: Sequence[Cell],
    rows: int,
    cols: int,
) -> List[Cell]:
    valid_set = {tuple(cell) for cell in valid_cells}
    protected = {tuple(cell) for cell in protected_cells}
    tent_set = {tuple(cell) for cell in visible_tents}
    options: List[Cell] = []
    for cell in _neighbors8(tuple(candidate_cell), int(rows), int(cols)):
        if tuple(cell) in protected or tuple(cell) in tent_set:
            continue
        if _touches_any_tent(tuple(cell), tent_set, int(rows), int(cols)):
            continue
        if any(tuple(valid_cell) in set(_neighbors8(tuple(cell), int(rows), int(cols))) for valid_cell in valid_set):
            continue
        options.append(tuple(cell))
    return options


def _place_tree_for_tent(
    *,
    tent_cell: Cell,
    rows: int,
    cols: int,
    occupied: Sequence[Cell],
    protected_cells: Sequence[Cell],
    rng,
) -> Cell | None:
    occupied_set = {tuple(cell) for cell in occupied}
    protected_set = {tuple(cell) for cell in protected_cells}
    choices = [
        tuple(cell)
        for cell in _neighbors4(tuple(tent_cell), int(rows), int(cols))
        if tuple(cell) not in occupied_set and tuple(cell) not in protected_set
    ]
    rng.shuffle(choices)
    return choices[0] if choices else None


def _place_extra_tents(
    *,
    rows: int,
    cols: int,
    visible_tents: List[Cell],
    protected_cells: Sequence[Cell],
    valid_cells: Sequence[Cell],
    count: int,
    rng,
) -> None:
    protected = {tuple(cell) for cell in protected_cells}
    valid_set = {tuple(cell) for cell in valid_cells}
    for _ in range(int(count)):
        candidates: List[Cell] = []
        for row in range(int(rows)):
            for col in range(int(cols)):
                cell = (int(row), int(col))
                if cell in protected or cell in visible_tents:
                    continue
                if _touches_any_tent(cell, visible_tents, int(rows), int(cols)):
                    continue
                if any(valid_cell in set(_neighbors8(cell, int(rows), int(cols))) for valid_cell in valid_set):
                    continue
                candidates.append(cell)
        if not candidates:
            return
        rng.shuffle(candidates)
        visible_tents.append(tuple(candidates[0]))


def _legal_candidate_cells(
    *,
    marked_tree: Cell,
    candidate_cells: Sequence[Cell],
    visible_tents: Sequence[Cell],
    tree_cells: Sequence[Cell],
    row_clues: Sequence[int],
    col_clues: Sequence[int],
    rows: int,
    cols: int,
) -> List[Cell]:
    visible_row_counts = _count_by_axis(visible_tents, int(rows), 0)
    visible_col_counts = _count_by_axis(visible_tents, int(cols), 1)
    occupied = {tuple(cell) for cell in visible_tents} | {tuple(cell) for cell in tree_cells}
    marked_neighbors = set(_neighbors4(tuple(marked_tree), int(rows), int(cols)))
    legal: List[Cell] = []
    for cell in [tuple(candidate) for candidate in candidate_cells]:
        row, col = int(cell[0]), int(cell[1])
        if cell not in marked_neighbors:
            continue
        if cell in occupied:
            continue
        if _touches_any_tent(cell, visible_tents, int(rows), int(cols)):
            continue
        if int(visible_row_counts[row]) + 1 > int(row_clues[row]):
            continue
        if int(visible_col_counts[col]) + 1 > int(col_clues[col]):
            continue
        legal.append(cell)
    return legal


def _build_partial_board(
    *,
    rows: int,
    cols: int,
    marked_tree: Cell,
    candidate_cells: Sequence[Cell],
    valid_cells: Sequence[Cell],
    gen_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    rng,
) -> Dict[str, Any]:
    valid_set = {tuple(cell) for cell in valid_cells}
    candidate_set = {tuple(cell) for cell in candidate_cells}
    row_extra = [0 for _ in range(int(rows))]
    col_extra = [0 for _ in range(int(cols))]
    for row, col in valid_set:
        row_extra[int(row)] = 1
        col_extra[int(col)] = 1

    visible_tents: List[Cell] = []
    protected_cells = list(candidate_set | {tuple(marked_tree)})
    for cell in candidate_cells:
        row, col = int(cell[0]), int(cell[1])
        if tuple(cell) in valid_set:
            continue
        if tuple(cell) not in set(_neighbors4(tuple(marked_tree), int(rows), int(cols))):
            continue
        if int(row_extra[row]) <= 0 or int(col_extra[col]) <= 0:
            continue
        if _touches_any_tent(tuple(cell), visible_tents, int(rows), int(cols)):
            continue
        blocker_options = _candidate_blocker_positions(
            candidate_cell=tuple(cell),
            valid_cells=list(valid_set),
            protected_cells=protected_cells,
            visible_tents=visible_tents,
            rows=int(rows),
            cols=int(cols),
        )
        if not blocker_options:
            raise RuntimeError("failed to block invalid tents candidate")
        rng.shuffle(blocker_options)
        visible_tents.append(tuple(blocker_options[0]))

    extra_low, extra_high = _get_range(
        params,
        gen_defaults,
        min_key="background_tent_count_min",
        max_key="background_tent_count_max",
        fallback_min=2,
        fallback_max=5,
    )
    _place_extra_tents(
        rows=int(rows),
        cols=int(cols),
        visible_tents=visible_tents,
        protected_cells=protected_cells,
        valid_cells=list(valid_set),
        count=int(rng.randint(int(extra_low), int(extra_high))),
        rng=rng,
    )

    tree_cells: List[Cell] = [tuple(marked_tree)]
    occupied_for_trees = list(protected_cells) + list(visible_tents)
    for tent_cell in visible_tents:
        paired_tree = _place_tree_for_tent(
            tent_cell=tuple(tent_cell),
            rows=int(rows),
            cols=int(cols),
            occupied=occupied_for_trees + tree_cells,
            protected_cells=protected_cells,
            rng=rng,
        )
        if paired_tree is not None:
            tree_cells.append(tuple(paired_tree))
            occupied_for_trees.append(tuple(paired_tree))

    visible_row_counts = _count_by_axis(visible_tents, int(rows), 0)
    visible_col_counts = _count_by_axis(visible_tents, int(cols), 1)
    row_clues = [int(visible_row_counts[index] + row_extra[index]) for index in range(int(rows))]
    col_clues = [int(visible_col_counts[index] + col_extra[index]) for index in range(int(cols))]
    legal = _legal_candidate_cells(
        marked_tree=tuple(marked_tree),
        candidate_cells=list(candidate_set),
        visible_tents=visible_tents,
        tree_cells=tree_cells,
        row_clues=row_clues,
        col_clues=col_clues,
        rows=int(rows),
        cols=int(cols),
    )
    if set(legal) != valid_set:
        raise RuntimeError("partial tents board does not expose the requested legal set")
    return {
        "visible_tents": [tuple(cell) for cell in visible_tents],
        "tree_cells": [tuple(cell) for cell in tree_cells],
        "row_clues": [int(value) for value in row_clues],
        "col_clues": [int(value) for value in col_clues],
        "legal_candidate_cells": [tuple(cell) for cell in legal],
    }


def _far_candidate_cells(
    *,
    rows: int,
    cols: int,
    marked_tree: Cell,
    excluded_cells: Sequence[Cell],
    count: int,
    rng,
) -> List[Cell]:
    excluded = {tuple(cell) for cell in excluded_cells}
    marked_adjacent = set(_neighbors4(tuple(marked_tree), int(rows), int(cols)))
    candidates: List[Cell] = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            cell = (int(row), int(col))
            if cell in excluded or cell in marked_adjacent or cell == tuple(marked_tree):
                continue
            candidates.append(cell)
    rng.shuffle(candidates)
    if len(candidates) < int(count):
        raise RuntimeError("failed to sample far tents candidates")
    return candidates[: int(count)]


def _build_missing_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{MISSING_TENT_TASK_ID}.dataset")
    rows, cols, row_range, col_range = _resolve_grid_size(params, gen_defaults=gen_defaults, rng=rng)
    option_count = int(params.get("option_count", group_default(gen_defaults, "option_count", 6)))
    option_count = max(4, min(6, int(option_count)))
    labels = _option_labels(int(option_count))
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{MISSING_TENT_TASK_ID}.answer_label",
        )
    )
    correct_index = int(selection % int(option_count))
    for _attempt in range(200):
        marked_tree = _sample_marked_tree(int(rows), int(cols), rng=rng)
        adjacent = _neighbors4(marked_tree, int(rows), int(cols))
        if len(adjacent) < 4:
            continue
        correct_cell = tuple(adjacent[int((selection // max(1, int(option_count))) % len(adjacent))])
        far_cells = _far_candidate_cells(
            rows=int(rows),
            cols=int(cols),
            marked_tree=marked_tree,
            excluded_cells=[marked_tree] + adjacent,
            count=max(0, int(option_count) - len(adjacent)),
            rng=rng,
        )
        distractor_cells = [tuple(cell) for cell in adjacent if tuple(cell) != tuple(correct_cell)] + list(far_cells)
        rng.shuffle(distractor_cells)
        ordered_cells: List[Cell] = []
        distractor_cursor = 0
        for label_index in range(int(option_count)):
            if int(label_index) == int(correct_index):
                ordered_cells.append(tuple(correct_cell))
            else:
                ordered_cells.append(tuple(distractor_cells[distractor_cursor]))
                distractor_cursor += 1
        board = _build_partial_board(
            rows=int(rows),
            cols=int(cols),
            marked_tree=tuple(marked_tree),
            candidate_cells=ordered_cells,
            valid_cells=[tuple(correct_cell)],
            gen_defaults=gen_defaults,
            params=params,
            rng=rng,
        )
        answer_value = str(labels[int(correct_index)])
        candidate_specs = [
            CandidateCellSpec(
                label=str(labels[index]),
                row=int(cell[0]),
                col=int(cell[1]),
                is_correct=bool(index == int(correct_index)),
                is_legal=bool(tuple(cell) == tuple(correct_cell)),
            )
            for index, cell in enumerate(ordered_cells)
        ]
        return {
            "rows": int(rows),
            "cols": int(cols),
            "grid_rows_range": list(row_range),
            "grid_cols_range": list(col_range),
            "marked_tree": tuple(marked_tree),
            "candidate_specs": candidate_specs,
            "visible_tents": list(board["visible_tents"]),
            "tree_cells": list(board["tree_cells"]),
            "row_clues": list(board["row_clues"]),
            "col_clues": list(board["col_clues"]),
            "legal_candidate_cells": list(board["legal_candidate_cells"]),
            "answer_value": str(answer_value),
            "answer_type": "option_letter",
            "supporting_item_ids": [
                f"candidate_{answer_value}",
                "marked_tree",
                f"row_clue_{int(correct_cell[0])}",
                f"col_clue_{int(correct_cell[1])}",
            ],
            "option_count": int(option_count),
            "correct_option_index": int(correct_index),
            "correct_cell": tuple(correct_cell),
            "target_answer_support": labels,
        }
    raise RuntimeError("failed to build missing tents dataset")


def _build_candidate_count_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{VALID_CANDIDATE_COUNT_TASK_ID}.dataset")
    rows, cols, row_range, col_range = _resolve_grid_size(params, gen_defaults=gen_defaults, rng=rng)
    support_min = int(params.get("target_count_min", group_default(gen_defaults, "target_count_min", 0)))
    support_max = int(params.get("target_count_max", group_default(gen_defaults, "target_count_max", 4)))
    support = [int(value) for value in range(int(support_min), int(support_max) + 1)]
    if not support or min(support) < 0 or max(support) > 4:
        raise ValueError("tents valid-candidate support must stay within 0..4")
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{VALID_CANDIDATE_COUNT_TASK_ID}.answer_count",
        )
    )
    target_count = int(support[int(selection % len(support))])
    labels = _option_labels(4)
    for _attempt in range(200):
        marked_tree = _sample_marked_tree(int(rows), int(cols), rng=rng)
        adjacent = _neighbors4(marked_tree, int(rows), int(cols))
        if len(adjacent) != 4:
            continue
        shuffled_adjacent = list(adjacent)
        rng.shuffle(shuffled_adjacent)
        valid_cells = [tuple(cell) for cell in shuffled_adjacent[: int(target_count)]]
        ordered_cells = list(adjacent)
        rng.shuffle(ordered_cells)
        board = _build_partial_board(
            rows=int(rows),
            cols=int(cols),
            marked_tree=tuple(marked_tree),
            candidate_cells=ordered_cells,
            valid_cells=valid_cells,
            gen_defaults=gen_defaults,
            params=params,
            rng=rng,
        )
        legal_set = {tuple(cell) for cell in board["legal_candidate_cells"]}
        candidate_specs = [
            CandidateCellSpec(
                label=str(labels[index]),
                row=int(cell[0]),
                col=int(cell[1]),
                is_correct=False,
                is_legal=bool(tuple(cell) in legal_set),
            )
            for index, cell in enumerate(ordered_cells)
        ]
        supporting_item_ids = ["marked_tree"] + [
            f"candidate_{spec.label}" for spec in candidate_specs if bool(spec.is_legal)
        ]
        return {
            "rows": int(rows),
            "cols": int(cols),
            "grid_rows_range": list(row_range),
            "grid_cols_range": list(col_range),
            "marked_tree": tuple(marked_tree),
            "candidate_specs": candidate_specs,
            "visible_tents": list(board["visible_tents"]),
            "tree_cells": list(board["tree_cells"]),
            "row_clues": list(board["row_clues"]),
            "col_clues": list(board["col_clues"]),
            "legal_candidate_cells": list(board["legal_candidate_cells"]),
            "answer_value": int(target_count),
            "answer_type": "integer",
            "supporting_item_ids": supporting_item_ids,
            "option_count": 4,
            "target_count_range": [int(support_min), int(support_max)],
            "target_answer_support": support,
        }
    raise RuntimeError("failed to build tents candidate-count dataset")


def _draw_tree_icon(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    trunk_fill: Tuple[int, int, int],
    trunk_outline: Tuple[int, int, int],
    ring_fill: Tuple[int, int, int],
    marked: bool,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    w = float(x1 - x0)
    h = float(y1 - y0)
    trunk = (
        x0 + (0.43 * w),
        y0 + (0.55 * h),
        x0 + (0.57 * w),
        y0 + (0.82 * h),
    )
    canopy = (
        x0 + (0.20 * w),
        y0 + (0.16 * h),
        x0 + (0.80 * w),
        y0 + (0.70 * h),
    )
    draw.rounded_rectangle(trunk, radius=max(2, int(w * 0.04)), fill=tuple(trunk_fill), outline=tuple(trunk_outline), width=1)
    draw.ellipse(canopy, fill=tuple(fill), outline=tuple(outline), width=2)
    if bool(marked):
        ring = (
            x0 + (0.08 * w),
            y0 + (0.07 * h),
            x0 + (0.92 * w),
            y0 + (0.91 * h),
        )
        draw.ellipse(ring, outline=tuple(ring_fill), width=max(3, int(w * 0.07)))


def _draw_tent_icon(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    fill: Tuple[int, int, int],
    shadow: Tuple[int, int, int],
    flap_fill: Tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    w = float(x1 - x0)
    h = float(y1 - y0)
    base_y = y0 + (0.78 * h)
    left = (x0 + (0.17 * w), base_y)
    peak = (x0 + (0.50 * w), y0 + (0.21 * h))
    right = (x0 + (0.83 * w), base_y)
    draw.polygon([left, peak, right], fill=tuple(fill), outline=tuple(shadow))
    draw.line([left, right], fill=tuple(shadow), width=max(2, int(w * 0.05)))
    draw.line([peak, (x0 + (0.50 * w), base_y)], fill=tuple(shadow), width=max(2, int(w * 0.035)))
    flap = [(x0 + (0.50 * w), base_y), (x0 + (0.61 * w), base_y), (x0 + (0.50 * w), y0 + (0.46 * h))]
    draw.polygon(flap, fill=tuple(flap_fill), outline=tuple(shadow))


def _render_tents_scene(
    image: Image.Image,
    *,
    scene_variant: str,
    palette_variant: str,
    rows: int,
    cols: int,
    row_clues: Sequence[int],
    col_clues: Sequence[int],
    marked_tree: Cell,
    tree_cells: Sequence[Cell],
    visible_tents: Sequence[Cell],
    candidate_specs: Sequence[CandidateCellSpec],
    render_params: TentsRenderParams,
) -> RenderedTentsScene:
    draw = ImageDraw.Draw(image)
    style = dict(_STYLE_COLORS[str(scene_variant)])
    style.update(_PALETTE_COLORS[str(palette_variant)])
    style.update(
        {
            str(key): tuple(int(component) for component in value[:3])
            for key, value in dict(render_params.style_overrides or {}).items()
        }
    )
    cell_size = int(render_params.cell_size_px)
    grid_w = int(cols) * int(cell_size)
    grid_h = int(rows) * int(cell_size)
    total_w = int(render_params.left_clue_width_px) + int(grid_w)
    total_h = int(render_params.top_clue_height_px) + int(grid_h)
    panel_x0 = int((int(render_params.canvas_width) - total_w) // 2) - int(render_params.panel_padding_px)
    panel_y0 = int((int(render_params.canvas_height) - total_h) // 2) - int(render_params.panel_padding_px)
    panel_x1 = int(panel_x0 + total_w + (2 * int(render_params.panel_padding_px)))
    panel_y1 = int(panel_y0 + total_h + (2 * int(render_params.panel_padding_px)))
    grid_x0 = int(panel_x0 + int(render_params.panel_padding_px) + int(render_params.left_clue_width_px))
    grid_y0 = int(panel_y0 + int(render_params.panel_padding_px) + int(render_params.top_clue_height_px))

    draw_rounded_rect(
        draw,
        (panel_x0, panel_y0, panel_x1, panel_y1),
        radius=int(render_params.panel_corner_radius_px),
        fill=style["panel_fill"],
        outline=style["heavy_line"],
        width=max(1, int(render_params.grid_line_width_px)),
    )

    clue_font = load_font(int(render_params.clue_font_size_px), bold=True)
    candidate_font = load_font(int(render_params.candidate_font_size_px), bold=True)
    cell_bbox_map: Dict[str, List[float]] = {}
    clue_bbox_map: Dict[str, List[float]] = {}
    item_bbox_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "tents_panel",
            "entity_type": "puzzle_tents_panel",
            "bbox_px": _round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
            "scene_variant": str(scene_variant),
            "palette_variant": str(palette_variant),
        }
    ]

    corner_bbox = (
        grid_x0 - int(render_params.left_clue_width_px),
        grid_y0 - int(render_params.top_clue_height_px),
        grid_x0,
        grid_y0,
    )
    draw.rectangle(corner_bbox, fill=style["clue_fill"], outline=style["grid_line"], width=int(render_params.grid_line_width_px))
    for row in range(int(rows)):
        y0 = int(grid_y0 + (row * cell_size))
        y1 = int(y0 + cell_size)
        bbox = (grid_x0 - int(render_params.left_clue_width_px), y0, grid_x0, y1)
        clue_bbox_map[f"row_clue_{row}"] = _round_bbox(bbox)
        item_bbox_map[f"row_clue_{row}"] = _round_bbox(bbox)
        draw.rectangle(bbox, fill=style["clue_fill"], outline=style["grid_line"], width=int(render_params.grid_line_width_px))
        draw_centered_text(
            draw,
            text=str(int(row_clues[row])),
            center=((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0),
            font=clue_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        entities.append({"entity_id": f"row_clue_{row}", "entity_type": "puzzle_tents_row_clue", "bbox_px": _round_bbox(bbox), "value": int(row_clues[row])})

    for col in range(int(cols)):
        x0 = int(grid_x0 + (col * cell_size))
        x1 = int(x0 + cell_size)
        bbox = (x0, grid_y0 - int(render_params.top_clue_height_px), x1, grid_y0)
        clue_bbox_map[f"col_clue_{col}"] = _round_bbox(bbox)
        item_bbox_map[f"col_clue_{col}"] = _round_bbox(bbox)
        draw.rectangle(bbox, fill=style["clue_fill"], outline=style["grid_line"], width=int(render_params.grid_line_width_px))
        draw_centered_text(
            draw,
            text=str(int(col_clues[col])),
            center=((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0),
            font=clue_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        entities.append({"entity_id": f"col_clue_{col}", "entity_type": "puzzle_tents_col_clue", "bbox_px": _round_bbox(bbox), "value": int(col_clues[col])})

    candidate_by_cell = {tuple(spec.cell): spec for spec in candidate_specs}
    for row in range(int(rows)):
        for col in range(int(cols)):
            x0 = int(grid_x0 + (col * cell_size))
            y0 = int(grid_y0 + (row * cell_size))
            x1 = int(x0 + cell_size)
            y1 = int(y0 + cell_size)
            bbox = (x0, y0, x1, y1)
            fill = style["cell_a"] if (row + col) % 2 == 0 else style["cell_b"]
            if (row, col) in candidate_by_cell:
                fill = style["candidate_fill"]
            draw.rectangle(bbox, fill=fill, outline=style["grid_line"], width=int(render_params.grid_line_width_px))
            cell_key = f"cell_{row}_{col}"
            cell_bbox_map[cell_key] = _round_bbox(bbox)
            item_bbox_map[cell_key] = _round_bbox(bbox)
            entities.append({"entity_id": cell_key, "entity_type": "puzzle_tents_cell", "bbox_px": _round_bbox(bbox), "row": int(row), "col": int(col)})

    draw.rectangle(
        (grid_x0, grid_y0, grid_x0 + grid_w, grid_y0 + grid_h),
        outline=style["heavy_line"],
        width=int(render_params.heavy_line_width_px),
    )

    tree_index = 0
    for tree_cell in tree_cells:
        row, col = int(tree_cell[0]), int(tree_cell[1])
        bbox = cell_bbox_map[f"cell_{row}_{col}"]
        entity_id = "marked_tree" if tuple(tree_cell) == tuple(marked_tree) else f"tree_{tree_index}"
        _draw_tree_icon(
            draw,
            bbox=bbox,
            fill=style["tree_fill"],
            outline=style["tree_outline"],
            trunk_fill=style.get("trunk_fill", (126, 88, 54)),
            trunk_outline=style.get("trunk_outline", (83, 58, 38)),
            ring_fill=style.get("marked_tree_ring", (24, 28, 34)),
            marked=bool(tuple(tree_cell) == tuple(marked_tree)),
        )
        item_bbox_map[entity_id] = list(bbox)
        entities.append({"entity_id": entity_id, "entity_type": "puzzle_tents_tree", "bbox_px": list(bbox), "row": int(row), "col": int(col), "marked": bool(tuple(tree_cell) == tuple(marked_tree))})
        tree_index += 1

    for tent_index, tent_cell in enumerate(visible_tents):
        row, col = int(tent_cell[0]), int(tent_cell[1])
        bbox = cell_bbox_map[f"cell_{row}_{col}"]
        entity_id = f"tent_{tent_index}"
        _draw_tent_icon(
            draw,
            bbox=bbox,
            fill=style["tent_fill"],
            shadow=style["tent_shadow"],
            flap_fill=style["tent_flap_fill"],
        )
        item_bbox_map[entity_id] = list(bbox)
        entities.append({"entity_id": entity_id, "entity_type": "puzzle_tents_tent", "bbox_px": list(bbox), "row": int(row), "col": int(col)})

    for spec in candidate_specs:
        row, col = int(spec.row), int(spec.col)
        bbox = cell_bbox_map[f"cell_{row}_{col}"]
        x0, y0, x1, y1 = [float(value) for value in bbox]
        label_w = float(cell_size) * 0.56
        label_h = float(cell_size) * 0.48
        label_bbox = (
            ((x0 + x1) / 2.0) - (label_w / 2.0),
            ((y0 + y1) / 2.0) - (label_h / 2.0),
            ((x0 + x1) / 2.0) + (label_w / 2.0),
            ((y0 + y1) / 2.0) + (label_h / 2.0),
        )
        draw.rounded_rectangle(
            label_bbox,
            radius=max(5, int(cell_size * 0.10)),
            fill=style["candidate_label_fill"],
            outline=style["candidate_outline"],
            width=max(2, int(cell_size * 0.04)),
        )
        draw_centered_text(
            draw,
            text=str(spec.label),
            center=((x0 + x1) / 2.0, (y0 + y1) / 2.0),
            font=candidate_font,
            fill=(26, 28, 32),
            stroke_fill=(255, 255, 255),
            stroke_width=1,
        )
        candidate_id = f"candidate_{spec.label}"
        item_bbox_map[candidate_id] = list(bbox)
        entities.append(
            {
                "entity_id": candidate_id,
                "entity_type": "puzzle_tents_candidate_cell",
                "bbox_px": list(bbox),
                "label": str(spec.label),
                "row": int(row),
                "col": int(col),
                "is_correct": bool(spec.is_correct),
                "is_legal": bool(spec.is_legal),
            }
        )

    return RenderedTentsScene(
        image=image,
        entities=entities,
        scene_bbox_px=_round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
        cell_bbox_map=cell_bbox_map,
        clue_bbox_map=clue_bbox_map,
        item_bbox_map=item_bbox_map,
    )


def _build_prompt(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        f"answer_hint_{query_id}",
        f"evidence_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(
        prompt_defaults,
        required_keys,
        context=f"prompt defaults for {task_id}",
    )
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "evidence_hint": str(prompt_values[f"evidence_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="logic",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


class _PuzzlesLogicTentsBaseTask:
    """Base implementation for one fixed public tents-grid task."""

    domain = "puzzles"
    task_group = "logic"
    default_dataset_enabled = True
    query_id: str

    def _build_dataset(
        self,
        *,
        params: Mapping[str, Any],
        instance_seed: int,
        gen_defaults: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if str(self.query_id) == "missing_tent_cell_label":
            return _build_missing_dataset(params=params, instance_seed=int(instance_seed), gen_defaults=gen_defaults)
        if str(self.query_id) == "valid_candidate_count":
            return _build_candidate_count_dataset(params=params, instance_seed=int(instance_seed), gen_defaults=gen_defaults)
        raise ValueError(f"unsupported tents query_id: {self.query_id}")

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id = str(self.query_id)
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        last_error: Exception | None = None
        dataset: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = self._build_dataset(
                    params=params,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    gen_defaults=gen_defaults,
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate tents puzzle instance") from last_error

        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        palette_variant, palette_variant_probabilities = _resolve_palette_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.tents_background",
        )
        render_params = replace(
            render_params,
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            style_overrides={
                "panel_fill": tuple(int(value) for value in scene_style.panel_fill_rgb),
                "grid_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
                "cell_a": tuple(int(value) for value in scene_style.option_fill_rgb),
                "cell_b": tuple(int(value) for value in scene_style.step_fill_rgb),
                "grid_line": tuple(int(value) for value in scene_style.grid_rgb),
                "heavy_line": tuple(int(value) for value in scene_style.panel_border_rgb),
                "clue_fill": tuple(int(value) for value in scene_style.panel_fill_rgb),
                "candidate_fill": tuple(int(value) for value in scene_style.step_fill_rgb),
                "candidate_outline": tuple(int(value) for value in scene_style.mark_rgb),
                "candidate_label_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
                "tree_fill": tuple(int(value) for value in scene_style.agent_rgb),
                "tree_outline": tuple(int(value) for value in scene_style.panel_border_rgb),
                "tent_fill": tuple(int(value) for value in scene_style.mark_rgb),
                "tent_shadow": tuple(int(value) for value in scene_style.panel_border_rgb),
                "tent_flap_fill": tuple(int(value) for value in scene_style.agent_inner_rgb),
                "accent": tuple(int(value) for value in scene_style.mark_rgb),
            },
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_tents_scene(
            background,
            scene_variant=str(scene_variant),
            palette_variant=str(palette_variant),
            rows=int(dataset["rows"]),
            cols=int(dataset["cols"]),
            row_clues=list(dataset["row_clues"]),
            col_clues=list(dataset["col_clues"]),
            marked_tree=tuple(dataset["marked_tree"]),
            tree_cells=list(dataset["tree_cells"]),
            visible_tents=list(dataset["visible_tents"]),
            candidate_specs=list(dataset["candidate_specs"]),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
        )
        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.item_bbox_map,
            [str(item_id) for item_id in dataset["supporting_item_ids"]],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_type = str(dataset["answer_type"])
        answer_value = dataset["answer_value"]
        answer_gt = TypedValue(type=answer_type, value=int(answer_value) if answer_type == "integer" else str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        rows = int(dataset["rows"])
        cols = int(dataset["cols"])
        grid_area_range = [
            int(dataset["grid_rows_range"][0]) * int(dataset["grid_cols_range"][0]),
            int(dataset["grid_rows_range"][1]) * int(dataset["grid_cols_range"][1]),
        ]
        candidate_specs = [
            {
                "label": str(spec.label),
                "row": int(spec.row),
                "col": int(spec.col),
                "is_correct": bool(spec.is_correct),
                "is_legal": bool(spec.is_legal),
            }
            for spec in dataset["candidate_specs"]
        ]
        query_params = {
            "query_variant": "default",
            "query_variant_probabilities": {"default": 1.0},
            "query_id": str(query_id),
            "query_variant": str(query_id),
            "query_variant_probabilities": {str(query_id): 1.0},
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "palette_variant": str(palette_variant),
            "palette_variant_probabilities": dict(palette_variant_probabilities),
            "grid_rows": int(rows),
            "grid_cols": int(cols),
            "grid_rows_range": list(dataset["grid_rows_range"]),
            "grid_cols_range": list(dataset["grid_cols_range"]),
            "option_count": int(dataset["option_count"]),
            "target_answer_support": list(dataset["target_answer_support"]),
        }
        if query_id == "valid_candidate_count":
            query_params["target_count_range"] = list(dataset["target_count_range"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": "default",
                    "query_id": str(query_id),
                    "query_variant": str(query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "palette_variant": str(palette_variant),
                    "answer_value": int(answer_value) if answer_type == "integer" else str(answer_value),
                },
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(query_id),
                "query_variant": str(query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "palette_variant": str(palette_variant),
                "scene_style": dict(scene_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "text_style": {
                    "clue_font_size_px": int(render_params.clue_font_size_px),
                    "candidate_font_size_px": int(render_params.candidate_font_size_px),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "clue_bboxes_px": {str(key): list(value) for key, value in rendered_scene.clue_bbox_map.items()},
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                "evidence_source": "item_bboxes_px",
            }, render_params.unit_size_jitter),
            "execution_trace": {
                **dict(query_params),
                "marked_tree": [int(value) for value in dataset["marked_tree"]],
                "row_clues": [int(value) for value in dataset["row_clues"]],
                "col_clues": [int(value) for value in dataset["col_clues"]],
                "visible_tents": [[int(r), int(c)] for r, c in dataset["visible_tents"]],
                "tree_cells": [[int(r), int(c)] for r, c in dataset["tree_cells"]],
                "candidate_specs": candidate_specs,
                "legal_candidate_cells": [[int(r), int(c)] for r, c in dataset["legal_candidate_cells"]],
                "answer_value": int(answer_value) if answer_type == "integer" else str(answer_value),
                "supporting_item_ids": [str(item_id) for item_id in dataset["supporting_item_ids"]],
                "question_format": str(query_id),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "value": list(evidence_bboxes),
            },
        }
        if query_id == "missing_tent_cell_label":
            trace_payload["execution_trace"].update(
                {
                    "correct_option_index": int(dataset["correct_option_index"]),
                    "correct_cell": [int(value) for value in dataset["correct_cell"]],
                }
            )

        visual_scan = normalize_int_with_bounds(int(rows * cols), grid_area_range)
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(_REASONING_LOAD_BY_QUERY[str(query_id)]),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class PuzzlesLogicTentsMissingTentCellLabelTask(_PuzzlesLogicTentsBaseTask):
    """Choose the candidate cell that can contain the missing tent for the marked tree."""

    task_id = MISSING_TENT_TASK_ID
    query_id = "missing_tent_cell_label"


@register_task
class PuzzlesLogicTentsValidCandidateCountTask(_PuzzlesLogicTentsBaseTask):
    """Count legal candidate cells for the marked tree in a partial tents grid."""

    task_id = VALID_CANDIDATE_COUNT_TASK_ID
    query_id = "valid_candidate_count"


__all__ = [
    "PuzzlesLogicTentsMissingTentCellLabelTask",
    "PuzzlesLogicTentsValidCandidateCountTask",
]
