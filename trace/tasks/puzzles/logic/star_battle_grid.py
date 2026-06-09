"""Star Battle region-grid logic puzzle tasks."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, replace
from string import ascii_uppercase
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_raw as _bbox_union, round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_puzzle_task_defaults,
    projected_puzzle_bbox_annotation,
    resolve_puzzle_axis_variant,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds
from ..shared.drawing import draw_centered_text, draw_rounded_rect
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


SCENE_ID = "star_battle"
VALID_CELL_ANYWHERE_TASK_ID = "task_puzzles__star_battle__valid_cell_anywhere_label"
SCOPED_VALID_CELL_TASK_ID = "task_puzzles__star_battle__scoped_valid_cell_label"
REMAINING_COUNT_TASK_ID = "task_puzzles__star_battle__star_battle_remaining_count"

VALID_CELL_QUERY_IDS: Tuple[str, ...] = (
    "valid_cell_anywhere_label",
    "valid_cell_in_marked_region_label",
    "valid_cell_for_marked_row_label",
)
VALID_CELL_ANYWHERE_QUERY_IDS: Tuple[str, ...] = ("valid_cell_anywhere_label",)
SCOPED_VALID_CELL_QUERY_IDS: Tuple[str, ...] = (
    "valid_cell_in_marked_region_label",
    "valid_cell_for_marked_row_label",
)
REMAINING_COUNT_QUERY_IDS: Tuple[str, ...] = (
    "remaining_valid_cells_in_marked_region_count",
    "remaining_valid_cells_in_marked_row_count",
    "remaining_valid_cells_in_marked_column_count",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (*VALID_CELL_QUERY_IDS, *REMAINING_COUNT_QUERY_IDS)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "star_battle_classic",
    "star_battle_pastel",
    "star_battle_blueprint",
)

_SCENE_LOAD_BY_VARIANT = {
    "star_battle_classic": 0.20,
    "star_battle_pastel": 0.22,
    "star_battle_blueprint": 0.24,
}
_REASONING_LOAD_BY_QUERY = {
    "valid_cell_anywhere_label": 0.56,
    "valid_cell_in_marked_region_label": 0.58,
    "valid_cell_for_marked_row_label": 0.54,
    "remaining_valid_cells_in_marked_region_count": 0.64,
    "remaining_valid_cells_in_marked_row_count": 0.60,
    "remaining_valid_cells_in_marked_column_count": 0.60,
}
_REGION_PALETTES = {
    "star_battle_classic": (
        (246, 217, 215),
        (219, 234, 249),
        (224, 241, 217),
        (250, 235, 190),
        (235, 222, 246),
        (221, 241, 239),
        (248, 224, 202),
        (229, 232, 240),
        (240, 224, 212),
    ),
    "star_battle_pastel": (
        (248, 226, 232),
        (223, 238, 255),
        (230, 246, 225),
        (255, 243, 206),
        (239, 229, 252),
        (220, 245, 241),
        (255, 231, 210),
        (231, 235, 246),
        (243, 231, 220),
    ),
    "star_battle_blueprint": (
        (219, 233, 246),
        (229, 241, 250),
        (220, 239, 238),
        (236, 241, 221),
        (229, 230, 246),
        (218, 229, 239),
        (242, 236, 218),
        (226, 236, 244),
        (236, 225, 235),
    ),
}

Cell = Tuple[int, int]
BBox = List[float]

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "logic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="logic", apply_prob=0.5)


@dataclass(frozen=True)
class StarBattleRenderParams:
    """Resolved rendering knobs for one Star Battle grid."""

    canvas_width: int
    canvas_height: int
    cell_size_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    grid_line_width_px: int
    heavy_line_width_px: int
    clue_size_px: int
    candidate_font_size_px: int
    clue_font_size_px: int
    title_font_size_px: int
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    style_overrides: Dict[str, Any]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class CandidateCellSpec:
    """One labeled Star Battle candidate cell."""

    label: str
    row: int
    col: int
    is_correct: bool
    is_legal: bool

    @property
    def cell(self) -> Cell:
        return (int(self.row), int(self.col))


@dataclass(frozen=True)
class RenderedStarBattleScene:
    """Rendered Star Battle scene plus traceable geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: BBox
    cell_bbox_map: Dict[str, BBox]
    row_bbox_map: Dict[str, BBox]
    col_bbox_map: Dict[str, BBox]
    region_bbox_map: Dict[str, BBox]
    item_bbox_map: Dict[str, BBox]


def _blend_rgb(base: Tuple[int, int, int], overlay: Tuple[int, int, int], alpha: float) -> Tuple[int, int, int]:
    weight = max(0.0, min(1.0, float(alpha)))
    return tuple(
        max(0, min(255, int(round((float(base[index]) * (1.0 - weight)) + (float(overlay[index]) * weight)))))
        for index in range(3)
    )


def _cell_key(cell: Cell) -> str:
    return f"cell_{int(cell[0])}_{int(cell[1])}"


def _candidate_key(label: str) -> str:
    return f"candidate_{str(label)}"


def _region_key(region_index: int) -> str:
    return f"region_{int(region_index)}"


def _neighbors4(cell: Cell, size: int) -> List[Cell]:
    row, col = int(cell[0]), int(cell[1])
    out: List[Cell] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rr = row + dr
        cc = col + dc
        if 0 <= rr < int(size) and 0 <= cc < int(size):
            out.append((int(rr), int(cc)))
    return out


def _neighbors8(cell: Cell, size: int) -> List[Cell]:
    row, col = int(cell[0]), int(cell[1])
    out: List[Cell] = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr = row + dr
            cc = col + dc
            if 0 <= rr < int(size) and 0 <= cc < int(size):
                out.append((int(rr), int(cc)))
    return out


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_queries: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None and effective_params.get("query_variant") is not None:
        effective_params["query_id"] = str(effective_params["query_variant"])
    return resolve_puzzle_axis_variant(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(query) for query in supported_queries],
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


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


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> StarBattleRenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.star_battle.unit_size",
    )
    return StarBattleRenderParams(
        canvas_width=int(render_defaults.get("canvas_width", 1080)),
        canvas_height=int(render_defaults.get("canvas_height", 900)),
        cell_size_px=scale_puzzle_px(render_defaults.get("cell_size_px", 64), unit_scale, min_px=24),
        panel_padding_px=scale_puzzle_px(render_defaults.get("panel_padding_px", 28), unit_scale, min_px=12),
        panel_corner_radius_px=scale_puzzle_px(render_defaults.get("panel_corner_radius_px", 18), unit_scale, min_px=7),
        grid_line_width_px=scale_puzzle_px(render_defaults.get("grid_line_width_px", 2), unit_scale, min_px=1),
        heavy_line_width_px=scale_puzzle_px(render_defaults.get("heavy_line_width_px", 4), unit_scale, min_px=2),
        clue_size_px=scale_puzzle_px(render_defaults.get("clue_size_px", 54), unit_scale, min_px=26),
        candidate_font_size_px=scale_puzzle_px(render_defaults.get("candidate_font_size_px", 28), unit_scale, min_px=14),
        clue_font_size_px=scale_puzzle_px(render_defaults.get("clue_font_size_px", 24), unit_scale, min_px=12),
        title_font_size_px=scale_puzzle_px(render_defaults.get("title_font_size_px", 20), unit_scale, min_px=11),
        text_color_rgb=_rgb(render_defaults.get("text_color_rgb"), (28, 32, 38)),
        text_stroke_rgb=_rgb(render_defaults.get("text_stroke_rgb"), (255, 255, 255)),
        style_overrides={},
        unit_size_jitter=dict(unit_meta),
    )


def _sample_solution(size: int, *, rng) -> List[Cell]:
    """Sample one non-touching permutation: one star in each row and column."""

    cols = list(range(int(size)))
    for _ in range(512):
        rng.shuffle(cols)
        stars = [(row, int(cols[row])) for row in range(int(size))]
        if all(abs(stars[row][1] - stars[row - 1][1]) > 1 for row in range(1, int(size))):
            return stars
    raise RuntimeError("failed to sample Star Battle solution")


def _grow_regions(size: int, stars: Sequence[Cell], *, rng) -> List[List[int]]:
    """Grow connected colored regions from solution-star seed cells."""

    region_grid = [[-1 for _ in range(int(size))] for _ in range(int(size))]
    regions = {index: {tuple(cell)} for index, cell in enumerate(stars)}
    frontiers: Dict[int, List[Cell]] = {}
    for index, cell in enumerate(stars):
        row, col = int(cell[0]), int(cell[1])
        region_grid[row][col] = int(index)
        frontiers[int(index)] = [nbr for nbr in _neighbors4((row, col), int(size)) if region_grid[nbr[0]][nbr[1]] < 0]

    unassigned = int(size * size - len(stars))
    while unassigned > 0:
        expandable = [idx for idx, frontier in frontiers.items() if frontier]
        if not expandable:
            raise RuntimeError("region growth became disconnected")
        region_index = int(expandable[int(rng.randrange(len(expandable)))])
        rng.shuffle(frontiers[region_index])
        cell = tuple(frontiers[region_index].pop())
        if region_grid[int(cell[0])][int(cell[1])] >= 0:
            continue
        region_grid[int(cell[0])][int(cell[1])] = int(region_index)
        regions[int(region_index)].add(cell)
        unassigned -= 1
        for nbr in _neighbors4(cell, int(size)):
            if region_grid[int(nbr[0])][int(nbr[1])] < 0:
                frontiers[int(region_index)].append(tuple(nbr))

    return region_grid


def _region_cells(region_grid: Sequence[Sequence[int]]) -> Dict[int, List[Cell]]:
    regions: Dict[int, List[Cell]] = {}
    for row, values in enumerate(region_grid):
        for col, value in enumerate(values):
            regions.setdefault(int(value), []).append((int(row), int(col)))
    return regions


def _connected_region(region_grid: Sequence[Sequence[int]], region_index: int) -> bool:
    cells = set(_region_cells(region_grid).get(int(region_index), []))
    if not cells:
        return False
    start = next(iter(cells))
    seen = {start}
    queue: deque[Cell] = deque([start])
    size = len(region_grid)
    while queue:
        cur = queue.popleft()
        for nbr in _neighbors4(cur, int(size)):
            if nbr in cells and nbr not in seen:
                seen.add(nbr)
                queue.append(nbr)
    return seen == cells


def _star_counts_by_region(stars: Iterable[Cell], region_grid: Sequence[Sequence[int]], size: int) -> List[int]:
    counts = [0 for _ in range(int(size))]
    for row, col in stars:
        counts[int(region_grid[int(row)][int(col)])] += 1
    return counts


def _legal_cells(
    *,
    size: int,
    region_grid: Sequence[Sequence[int]],
    visible_stars: Sequence[Cell],
) -> List[Cell]:
    star_set = {tuple(cell) for cell in visible_stars}
    filled_rows = {int(row) for row, _col in star_set}
    filled_cols = {int(col) for _row, col in star_set}
    filled_regions = {int(region_grid[int(row)][int(col)]) for row, col in star_set}
    legal: List[Cell] = []
    for row in range(int(size)):
        if row in filled_rows:
            continue
        for col in range(int(size)):
            cell = (int(row), int(col))
            if col in filled_cols:
                continue
            if int(region_grid[row][col]) in filled_regions:
                continue
            if any(tuple(star) in set(_neighbors8(cell, int(size))) for star in star_set):
                continue
            legal.append(cell)
    return legal


def _scope_cells(query_id: str, dataset: Mapping[str, Any]) -> List[Cell]:
    size = int(dataset["size"])
    if str(query_id).endswith("_in_marked_region_count") or str(query_id) == "valid_cell_in_marked_region_label":
        region_index = int(dataset["marked_region_index"])
        return [tuple(cell) for cell in dataset["regions"][str(region_index)]]
    if str(query_id).endswith("_for_marked_row_label") or str(query_id).endswith("_in_marked_row_count"):
        row = int(dataset["marked_row_index"])
        return [(row, col) for col in range(size)]
    if str(query_id).endswith("_in_marked_column_count"):
        col = int(dataset["marked_col_index"])
        return [(row, col) for row in range(size)]
    return [(row, col) for row in range(size) for col in range(size)]


def _scope_item_ids(query_id: str, dataset: Mapping[str, Any]) -> List[str]:
    if str(query_id).endswith("_in_marked_region_count") or str(query_id) == "valid_cell_in_marked_region_label":
        return [_region_key(int(dataset["marked_region_index"]))]
    if str(query_id).endswith("_for_marked_row_label") or str(query_id).endswith("_in_marked_row_count"):
        return [f"row_{int(dataset['marked_row_index'])}"]
    if str(query_id).endswith("_in_marked_column_count"):
        return [f"col_{int(dataset['marked_col_index'])}"]
    return []


def _base_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.star_battle.base")
    size_min, size_max = _get_range(
        params,
        gen_defaults,
        min_key="grid_size_min",
        max_key="grid_size_max",
        fallback_min=6,
        fallback_max=9,
    )
    explicit_size = params.get("grid_size")
    if explicit_size is None:
        selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.grid_size"))
        size = int(size_min + (selection % (size_max - size_min + 1)))
    else:
        size = int(explicit_size)
    if not int(size_min) <= int(size) <= int(size_max):
        raise ValueError("grid_size outside configured range")

    stars = _sample_solution(int(size), rng=rng)
    region_grid = _grow_regions(int(size), stars, rng=rng)
    for region_index in range(int(size)):
        if not _connected_region(region_grid, int(region_index)):
            raise RuntimeError("Star Battle region is not connected")
    region_star_counts = _star_counts_by_region(stars, region_grid, int(size))
    if any(count != 1 for count in region_star_counts):
        raise RuntimeError("Star Battle generated region without exactly one solution star")

    reveal_min_frac = float(params.get("visible_star_fraction_min", group_default(gen_defaults, "visible_star_fraction_min", 0.30)))
    reveal_max_frac = float(params.get("visible_star_fraction_max", group_default(gen_defaults, "visible_star_fraction_max", 0.55)))
    reveal_min = max(1, int(round(float(size) * float(reveal_min_frac))))
    reveal_max = max(reveal_min, min(int(size) - 1, int(round(float(size) * float(reveal_max_frac)))))
    reveal_count = int(rng.randint(reveal_min, reveal_max))
    shuffled_stars = list(stars)
    rng.shuffle(shuffled_stars)
    visible_stars = sorted([tuple(cell) for cell in shuffled_stars[:reveal_count]])
    legal = _legal_cells(size=int(size), region_grid=region_grid, visible_stars=visible_stars)
    if not legal:
        raise RuntimeError("Star Battle partial board has no legal cells")

    regions = {
        str(region_index): [tuple(cell) for cell in cells]
        for region_index, cells in _region_cells(region_grid).items()
    }
    return {
        "size": int(size),
        "grid_size_range": [int(size_min), int(size_max)],
        "solution_stars": [tuple(cell) for cell in stars],
        "visible_stars": [tuple(cell) for cell in visible_stars],
        "region_grid": [[int(value) for value in row] for row in region_grid],
        "regions": regions,
        "legal_cells": [tuple(cell) for cell in legal],
    }


def _choose_scope(
    *,
    query_id: str,
    base: Dict[str, Any],
    target_min: int,
    target_max: int,
    rng,
) -> Tuple[Dict[str, Any], List[Cell], List[Cell]]:
    size = int(base["size"])
    legal_set = {tuple(cell) for cell in base["legal_cells"]}
    candidates: List[Tuple[Dict[str, Any], List[Cell], List[Cell]]] = []
    if str(query_id) in {"valid_cell_in_marked_region_label", "remaining_valid_cells_in_marked_region_count"}:
        for region_index, cells in dict(base["regions"]).items():
            scope = [tuple(cell) for cell in cells]
            scoped_legal = sorted([cell for cell in scope if cell in legal_set])
            if int(target_min) <= len(scoped_legal) <= int(target_max):
                candidates.append(({"marked_region_index": int(region_index)}, scope, scoped_legal))
    elif str(query_id) in {"valid_cell_for_marked_row_label", "remaining_valid_cells_in_marked_row_count"}:
        for row in range(size):
            scope = [(row, col) for col in range(size)]
            scoped_legal = sorted([cell for cell in scope if cell in legal_set])
            if int(target_min) <= len(scoped_legal) <= int(target_max):
                candidates.append(({"marked_row_index": int(row)}, scope, scoped_legal))
    elif str(query_id) == "remaining_valid_cells_in_marked_column_count":
        for col in range(size):
            scope = [(row, col) for row in range(size)]
            scoped_legal = sorted([cell for cell in scope if cell in legal_set])
            if int(target_min) <= len(scoped_legal) <= int(target_max):
                candidates.append(({"marked_col_index": int(col)}, scope, scoped_legal))
    else:
        scope = [(row, col) for row in range(size) for col in range(size)]
        scoped_legal = sorted([cell for cell in scope if cell in legal_set])
        if int(target_min) <= len(scoped_legal) <= int(target_max):
            candidates.append(({}, scope, scoped_legal))
    if not candidates:
        raise RuntimeError(f"could not find Star Battle scope for {query_id}")
    return candidates[int(rng.randrange(len(candidates)))]


def _build_valid_cell_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.{query_id}.valid")
    option_min, option_max = _get_range(
        params,
        gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=5,
        fallback_max=8,
    )
    option_count = int(params.get("option_count", rng.randint(int(option_min), int(option_max))))
    option_count = max(4, min(8, int(option_count)))
    labels = list(ascii_uppercase[:option_count])
    for attempt in range(300):
        base = _base_dataset(params=params, instance_seed=int(instance_seed) + attempt, gen_defaults=gen_defaults, task_id=task_id)
        scope_info, scope, scoped_legal = _choose_scope(
            query_id=str(query_id),
            base=base,
            target_min=1,
            target_max=int(base["size"]) * int(base["size"]),
            rng=rng,
        )
        legal_set = {tuple(cell) for cell in scoped_legal}
        invalid_scope = [tuple(cell) for cell in scope if tuple(cell) not in legal_set and tuple(cell) not in set(base["visible_stars"])]
        if len(scoped_legal) < 1 or len(invalid_scope) < int(option_count) - 1:
            continue
        correct_cell = tuple(scoped_legal[int(rng.randrange(len(scoped_legal)))])
        rng.shuffle(invalid_scope)
        distractors = list(invalid_scope[: int(option_count) - 1])
        selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.{query_id}.answer_label"))
        correct_index = int(selection % int(option_count))
        ordered: List[Cell] = []
        cursor = 0
        for index in range(int(option_count)):
            if index == correct_index:
                ordered.append(correct_cell)
            else:
                ordered.append(tuple(distractors[cursor]))
                cursor += 1
        candidate_specs = [
            CandidateCellSpec(
                label=str(labels[index]),
                row=int(cell[0]),
                col=int(cell[1]),
                is_correct=bool(index == correct_index),
                is_legal=bool(tuple(cell) in legal_set),
            )
            for index, cell in enumerate(ordered)
        ]
        if sum(1 for spec in candidate_specs if spec.is_legal) != 1:
            continue
        answer_value = str(labels[correct_index])
        dataset = dict(base)
        dataset.update(scope_info)
        dataset.update(
            {
                "query_id": str(query_id),
                "objective_contract": "valid_cell_label",
                "candidate_specs": candidate_specs,
                "scope_cells": [tuple(cell) for cell in scope],
                "scoped_legal_cells": [tuple(cell) for cell in scoped_legal],
                "answer_value": str(answer_value),
                "answer_type": "option_letter",
                "option_count": int(option_count),
                "correct_option_index": int(correct_index),
                "correct_cell": tuple(correct_cell),
                "supporting_item_ids": [_candidate_key(str(answer_value)), *_scope_item_ids(str(query_id), {**base, **scope_info})],
                "target_answer_support": labels,
            }
        )
        return dataset
    raise RuntimeError(f"failed to build Star Battle valid-cell dataset for {query_id}")


def _build_remaining_count_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.{query_id}.count")
    count_min, count_max = _get_range(
        params,
        gen_defaults,
        min_key="target_count_min",
        max_key="target_count_max",
        fallback_min=1,
        fallback_max=6,
    )
    support = [int(value) for value in range(int(count_min), int(count_max) + 1)]
    if not support or min(support) < 1:
        raise ValueError("Star Battle remaining-count support must be positive")
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query_id}.answer_count",
        )
    )
    target_count = int(support[int(selection % len(support))])
    for attempt in range(300):
        base = _base_dataset(params=params, instance_seed=int(instance_seed) + attempt, gen_defaults=gen_defaults, task_id=task_id)
        scope_info, scope, scoped_legal = _choose_scope(
            query_id=str(query_id),
            base=base,
            target_min=int(target_count),
            target_max=int(target_count),
            rng=rng,
        )
        answer_value = int(len(scoped_legal))
        dataset = dict(base)
        dataset.update(scope_info)
        scope_ids = _scope_item_ids(str(query_id), {**base, **scope_info})
        supporting_ids = [*_scope_item_ids(str(query_id), {**base, **scope_info})]
        supporting_ids.extend([_cell_key(cell) for cell in scoped_legal])
        dataset.update(
            {
                "query_id": str(query_id),
                "objective_contract": "remaining_count",
                "candidate_specs": [],
                "scope_cells": [tuple(cell) for cell in scope],
                "scoped_legal_cells": [tuple(cell) for cell in scoped_legal],
                "answer_value": int(answer_value),
                "answer_type": "integer",
                "option_count": 0,
                "supporting_item_ids": supporting_ids if supporting_ids else scope_ids,
                "target_count_range": [int(count_min), int(count_max)],
                "target_answer_support": support,
            }
        )
        return dataset
    raise RuntimeError(f"failed to build Star Battle remaining-count dataset for {query_id}")


def _draw_star(draw: ImageDraw.ImageDraw, bbox: Sequence[float], *, fill: Tuple[int, int, int], outline: Tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    r_outer = min(x1 - x0, y1 - y0) * 0.34
    r_inner = r_outer * 0.43
    points = []
    for idx in range(10):
        radius = r_outer if idx % 2 == 0 else r_inner
        angle = -1.5708 + idx * 0.628318
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(points, fill=fill, outline=outline)


def _render_scene(
    image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: StarBattleRenderParams,
) -> RenderedStarBattleScene:
    draw = ImageDraw.Draw(image)
    size = int(dataset["size"])
    style_overrides = dict(render_params.style_overrides or {})
    palette = [
        tuple(int(channel) for channel in color)
        for color in style_overrides.get("region_palette", _REGION_PALETTES[str(scene_variant)])
    ]
    cell_size = int(render_params.cell_size_px)
    clue = int(render_params.clue_size_px)
    grid_w = int(size * cell_size)
    total_w = int(clue + grid_w)
    total_h = int(clue + grid_w)
    panel_x0 = int((int(render_params.canvas_width) - total_w) // 2) - int(render_params.panel_padding_px)
    panel_y0 = int((int(render_params.canvas_height) - total_h) // 2) - int(render_params.panel_padding_px)
    grid_x0 = int(panel_x0 + int(render_params.panel_padding_px) + clue)
    grid_y0 = int(panel_y0 + int(render_params.panel_padding_px) + clue)
    panel_x1 = int(panel_x0 + total_w + (2 * int(render_params.panel_padding_px)))
    panel_y1 = int(panel_y0 + total_h + (2 * int(render_params.panel_padding_px)))
    border = tuple(style_overrides.get("border", (74, 82, 96) if scene_variant != "star_battle_blueprint" else (49, 88, 123)))
    grid_line = tuple(style_overrides.get("grid_line", (126, 132, 144) if scene_variant != "star_battle_blueprint" else (112, 151, 181)))
    clue_fill = tuple(style_overrides.get("clue_fill", (245, 247, 250) if scene_variant != "star_battle_blueprint" else (225, 238, 248)))
    accent = tuple(style_overrides.get("accent", (45, 91, 176) if scene_variant != "star_battle_blueprint" else (31, 93, 150)))
    accent_backdrop = tuple(style_overrides.get("accent_backdrop", (255, 255, 255)))
    highlight_fill = tuple(style_overrides.get("highlight_fill", (255, 241, 142) if scene_variant != "star_battle_blueprint" else (255, 236, 120)))
    candidate_fill = tuple(style_overrides.get("candidate_fill", (255, 250, 218)))
    panel_fill = tuple(style_overrides.get("panel_fill", (250, 250, 247) if scene_variant != "star_battle_blueprint" else (241, 248, 252)))
    region_grid = list(dataset["region_grid"])
    marked_region = dataset.get("marked_region_index")
    marked_row = dataset.get("marked_row_index")
    marked_col = dataset.get("marked_col_index")

    draw_rounded_rect(
        draw,
        (panel_x0, panel_y0, panel_x1, panel_y1),
        radius=int(render_params.panel_corner_radius_px),
        fill=panel_fill,
        outline=border,
        width=max(1, int(render_params.grid_line_width_px)),
    )
    clue_font = load_font(int(render_params.clue_font_size_px), bold=True)
    candidate_font = load_font(int(render_params.candidate_font_size_px), bold=True)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)

    cell_bbox_map: Dict[str, BBox] = {}
    row_bbox_map: Dict[str, BBox] = {}
    col_bbox_map: Dict[str, BBox] = {}
    item_bbox_map: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "star_battle_panel",
            "entity_type": "puzzle_star_battle_panel",
            "bbox_px": _round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
            "scene_variant": str(scene_variant),
        }
    ]

    draw_text_traced(draw,(panel_x0 + 18, panel_y0 + 14), "Star Battle", fill=render_params.text_color_rgb, font=title_font, role="readout", required=False)
    for row in range(size):
        bbox = (grid_x0 - clue, grid_y0 + row * cell_size, grid_x0, grid_y0 + (row + 1) * cell_size)
        row_bbox_map[f"row_{row}"] = _round_bbox(bbox)
        item_bbox_map[f"row_{row}"] = _round_bbox(bbox)
        is_marked = bool(marked_row is not None and int(marked_row) == int(row))
        draw.rectangle(
            bbox,
            fill=highlight_fill if is_marked else clue_fill,
            outline=accent if is_marked else grid_line,
            width=max(3 if is_marked else 1, int(render_params.grid_line_width_px)),
        )
        draw_centered_text(draw, text="1", center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2), font=clue_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1)
        entities.append({"entity_id": f"row_{row}", "entity_type": "puzzle_star_battle_row_clue", "bbox_px": _round_bbox(bbox), "value": 1, "row": int(row)})
    for col in range(size):
        bbox = (grid_x0 + col * cell_size, grid_y0 - clue, grid_x0 + (col + 1) * cell_size, grid_y0)
        col_bbox_map[f"col_{col}"] = _round_bbox(bbox)
        item_bbox_map[f"col_{col}"] = _round_bbox(bbox)
        is_marked = bool(marked_col is not None and int(marked_col) == int(col))
        draw.rectangle(
            bbox,
            fill=highlight_fill if is_marked else clue_fill,
            outline=accent if is_marked else grid_line,
            width=max(3 if is_marked else 1, int(render_params.grid_line_width_px)),
        )
        draw_centered_text(draw, text="1", center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2), font=clue_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1)
        entities.append({"entity_id": f"col_{col}", "entity_type": "puzzle_star_battle_col_clue", "bbox_px": _round_bbox(bbox), "value": 1, "col": int(col)})

    for row in range(size):
        for col in range(size):
            region_index = int(region_grid[row][col])
            bbox = (grid_x0 + col * cell_size, grid_y0 + row * cell_size, grid_x0 + (col + 1) * cell_size, grid_y0 + (row + 1) * cell_size)
            fill = palette[region_index % len(palette)]
            if marked_region is not None and int(marked_region) == int(region_index):
                fill = _blend_rgb(fill, highlight_fill, 0.44)
            if marked_row is not None and int(marked_row) == int(row):
                fill = _blend_rgb(fill, highlight_fill, 0.52)
            if marked_col is not None and int(marked_col) == int(col):
                fill = _blend_rgb(fill, highlight_fill, 0.52)
            draw.rectangle(bbox, fill=fill, outline=grid_line, width=max(1, int(render_params.grid_line_width_px)))
            key = _cell_key((row, col))
            cell_bbox_map[key] = _round_bbox(bbox)
            item_bbox_map[key] = _round_bbox(bbox)
            entities.append({"entity_id": key, "entity_type": "puzzle_star_battle_cell", "bbox_px": _round_bbox(bbox), "row": int(row), "col": int(col), "region_index": int(region_index)})

    for row in range(size):
        for col in range(size):
            region_index = int(region_grid[row][col])
            x0 = grid_x0 + col * cell_size
            y0 = grid_y0 + row * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            width = max(2, int(render_params.heavy_line_width_px))
            if row == 0 or int(region_grid[row - 1][col]) != region_index:
                draw.line((x0, y0, x1, y0), fill=border, width=width)
            if row == size - 1 or int(region_grid[row + 1][col]) != region_index:
                draw.line((x0, y1, x1, y1), fill=border, width=width)
            if col == 0 or int(region_grid[row][col - 1]) != region_index:
                draw.line((x0, y0, x0, y1), fill=border, width=width)
            if col == size - 1 or int(region_grid[row][col + 1]) != region_index:
                draw.line((x1, y0, x1, y1), fill=border, width=width)

    draw.rectangle((grid_x0, grid_y0, grid_x0 + grid_w, grid_y0 + grid_w), outline=border, width=max(3, int(render_params.heavy_line_width_px)))
    if marked_row is not None:
        bbox = (grid_x0, grid_y0 + int(marked_row) * cell_size, grid_x0 + grid_w, grid_y0 + (int(marked_row) + 1) * cell_size)
        draw.rectangle(bbox, outline=accent_backdrop, width=max(8, int(render_params.heavy_line_width_px) + 5))
        draw.rectangle(bbox, outline=accent, width=max(5, int(render_params.heavy_line_width_px) + 2))
    if marked_col is not None:
        bbox = (grid_x0 + int(marked_col) * cell_size, grid_y0, grid_x0 + (int(marked_col) + 1) * cell_size, grid_y0 + grid_w)
        draw.rectangle(bbox, outline=accent_backdrop, width=max(8, int(render_params.heavy_line_width_px) + 5))
        draw.rectangle(bbox, outline=accent, width=max(5, int(render_params.heavy_line_width_px) + 2))

    region_bbox_map: Dict[str, BBox] = {}
    for region_index, cells in dict(dataset["regions"]).items():
        boxes = [cell_bbox_map[_cell_key(tuple(cell))] for cell in cells]
        region_bbox_map[_region_key(int(region_index))] = _bbox_union(boxes)
        item_bbox_map[_region_key(int(region_index))] = list(region_bbox_map[_region_key(int(region_index))])
        entities.append({"entity_id": _region_key(int(region_index)), "entity_type": "puzzle_star_battle_region", "bbox_px": list(region_bbox_map[_region_key(int(region_index))]), "region_index": int(region_index), "cell_count": len(cells)})
    if marked_region is not None:
        for cell in dataset["regions"][str(int(marked_region))]:
            bbox = cell_bbox_map[_cell_key(tuple(cell))]
            inset = max(3, int(cell_size * 0.08))
            inner = (bbox[0] + inset, bbox[1] + inset, bbox[2] - inset, bbox[3] - inset)
            draw.rectangle(inner, outline=accent_backdrop, width=max(5, int(render_params.grid_line_width_px) + 3))
            draw.rectangle(inner, outline=accent, width=max(3, int(render_params.grid_line_width_px) + 1))

    for index, star in enumerate(dataset["visible_stars"]):
        bbox = cell_bbox_map[_cell_key(tuple(star))]
        _draw_star(draw, bbox, fill=(35, 39, 46), outline=(255, 255, 255))
        entity_id = f"star_{index}"
        item_bbox_map[entity_id] = list(bbox)
        entities.append({"entity_id": entity_id, "entity_type": "puzzle_star_battle_star", "bbox_px": list(bbox), "row": int(star[0]), "col": int(star[1])})

    for spec in dataset.get("candidate_specs", []):
        bbox = cell_bbox_map[_cell_key(spec.cell)]
        x0, y0, x1, y1 = [float(v) for v in bbox]
        label_bbox = (x0 + cell_size * 0.22, y0 + cell_size * 0.22, x1 - cell_size * 0.22, y1 - cell_size * 0.22)
        draw.rounded_rectangle(label_bbox, radius=max(5, int(cell_size * 0.10)), fill=candidate_fill, outline=accent, width=max(2, int(cell_size * 0.04)))
        draw_centered_text(draw, text=str(spec.label), center=((x0 + x1) / 2, (y0 + y1) / 2), font=candidate_font, fill=(26, 28, 32), stroke_fill=(255, 255, 255), stroke_width=1)
        item_bbox_map[_candidate_key(spec.label)] = list(bbox)
        entities.append({"entity_id": _candidate_key(spec.label), "entity_type": "puzzle_star_battle_candidate_cell", "bbox_px": list(bbox), "label": str(spec.label), "row": int(spec.row), "col": int(spec.col), "is_correct": bool(spec.is_correct), "is_legal": bool(spec.is_legal)})

    return RenderedStarBattleScene(
        image=image,
        entities=entities,
        scene_bbox_px=_round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
        cell_bbox_map=cell_bbox_map,
        row_bbox_map=row_bbox_map,
        col_bbox_map=col_bbox_map,
        region_bbox_map=region_bbox_map,
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
        f"annotation_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {task_id}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
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
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
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


class _PuzzlesLogicStarBattleBaseTask:
    """Base implementation for public Star Battle tasks."""

    domain = "puzzles"
    task_group = "logic"
    default_dataset_enabled = True
    supported_query_ids: Tuple[str, ...]

    def _build_dataset(
        self,
        *,
        query_id: str,
        params: Mapping[str, Any],
        instance_seed: int,
        gen_defaults: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if str(query_id) in VALID_CELL_QUERY_IDS:
            return _build_valid_cell_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed), gen_defaults=gen_defaults, task_id=str(self.task_id))
        if str(query_id) in REMAINING_COUNT_QUERY_IDS:
            return _build_remaining_count_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed), gen_defaults=gen_defaults, task_id=str(self.task_id))
        raise ValueError(f"unsupported Star Battle query_id: {query_id}")

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        query_id, query_id_probabilities = _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_queries=tuple(self.supported_query_ids),
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        last_error: Exception | None = None
        dataset: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = self._build_dataset(
                    query_id=str(query_id),
                    params=params,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    gen_defaults=gen_defaults,
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate Star Battle puzzle instance") from last_error

        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.star_battle_background",
        )
        render_params = replace(
            render_params,
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            style_overrides={
                "region_palette": tuple(tuple(int(channel) for channel in color) for color in scene_style.state_colors),
                "border": tuple(int(value) for value in scene_style.panel_border_rgb),
                "grid_line": tuple(int(value) for value in scene_style.grid_rgb),
                "clue_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
                "accent": tuple(int(value) for value in scene_style.mark_rgb),
                "accent_backdrop": tuple(int(value) for value in scene_style.text_stroke_rgb),
                "highlight_fill": tuple(int(value) for value in scene_style.step_fill_rgb),
                "candidate_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
                "panel_fill": tuple(int(value) for value in scene_style.panel_fill_rgb),
            },
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_scene(background, dataset=dataset, scene_variant=str(scene_variant), render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
        )
        annotation_projection = projected_puzzle_bbox_annotation(
            rendered_scene.item_bbox_map,
            [str(item_id) for item_id in dataset["supporting_item_ids"]],
        )
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_set"]]
        answer_type = str(dataset["answer_type"])
        answer_value = dataset["answer_value"]
        answer_gt = TypedValue(type=answer_type, value=int(answer_value) if answer_type == "integer" else str(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        size = int(dataset["size"])
        candidate_specs = [
            {
                "label": str(spec.label),
                "row": int(spec.row),
                "col": int(spec.col),
                "is_correct": bool(spec.is_correct),
                "is_legal": bool(spec.is_legal),
            }
            for spec in dataset.get("candidate_specs", [])
        ]
        query_params = {
            "query_id": str(query_id),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "grid_size": int(size),
            "grid_size_range": list(dataset["grid_size_range"]),
            "option_count": int(dataset["option_count"]),
            "target_answer_support": list(dataset["target_answer_support"]),
        }
        for key in ("marked_region_index", "marked_row_index", "marked_col_index", "target_count_range", "correct_option_index"):
            if key in dataset:
                query_params[key] = dataset[key]
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value) if answer_type == "integer" else str(answer_value),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
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
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "row_bboxes_px": {str(key): list(value) for key, value in rendered_scene.row_bbox_map.items()},
                "col_bboxes_px": {str(key): list(value) for key, value in rendered_scene.col_bbox_map.items()},
                "region_bboxes_px": {str(key): list(value) for key, value in rendered_scene.region_bbox_map.items()},
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                "annotation_source": "item_bboxes_px",
            }, render_params.unit_size_jitter),
            "execution_trace": {
                **dict(query_params),
                "solution_stars": [[int(r), int(c)] for r, c in dataset["solution_stars"]],
                "visible_stars": [[int(r), int(c)] for r, c in dataset["visible_stars"]],
                "region_grid": [[int(value) for value in row] for row in dataset["region_grid"]],
                "regions": {str(key): [[int(r), int(c)] for r, c in cells] for key, cells in dict(dataset["regions"]).items()},
                "candidate_specs": candidate_specs,
                "legal_cells": [[int(r), int(c)] for r, c in dataset["legal_cells"]],
                "scope_cells": [[int(r), int(c)] for r, c in dataset["scope_cells"]],
                "scoped_legal_cells": [[int(r), int(c)] for r, c in dataset["scoped_legal_cells"]],
                "answer_value": int(answer_value) if answer_type == "integer" else str(answer_value),
                "supporting_item_ids": [str(item_id) for item_id in dataset["supporting_item_ids"]],
                "question_format": str(query_id),
            },
            "witness_symbolic": {"type": "bbox_set", "value": list(annotation_bboxes)},
            "projected_annotation": {"type": "bbox_set", "bbox_set": list(annotation_bboxes), "value": list(annotation_bboxes)},
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        if "correct_cell" in dataset:
            trace_payload["execution_trace"]["correct_cell"] = [int(value) for value in dataset["correct_cell"]]

        visual_scan = normalize_int_with_bounds(int(size * size), [int(dataset["grid_size_range"][0]) ** 2, int(dataset["grid_size_range"][1]) ** 2])
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(_REASONING_LOAD_BY_QUERY[str(query_id)]),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        trace_payload["complexity"] = complexity.to_dict()
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class PuzzlesLogicStarBattleValidCellAnywhereLabelTask(_PuzzlesLogicStarBattleBaseTask):
    """Choose a labeled cell where a Star Battle star can be legally placed anywhere."""

    task_id = VALID_CELL_ANYWHERE_TASK_ID
    supported_query_ids = VALID_CELL_ANYWHERE_QUERY_IDS


@register_task
class PuzzlesLogicStarBattleScopedValidCellLabelTask(_PuzzlesLogicStarBattleBaseTask):
    """Choose a labeled cell where a Star Battle star can be legally placed in a marked scope."""

    task_id = SCOPED_VALID_CELL_TASK_ID
    supported_query_ids = SCOPED_VALID_CELL_QUERY_IDS


@register_task
class PuzzlesLogicStarBattleRemainingCountTask(_PuzzlesLogicStarBattleBaseTask):
    """Count legal remaining Star Battle placements in a marked row, column, or region."""

    task_id = REMAINING_COUNT_TASK_ID
    supported_query_ids = REMAINING_COUNT_QUERY_IDS


__all__ = [
    "PuzzlesLogicStarBattleRemainingCountTask",
    "PuzzlesLogicStarBattleScopedValidCellLabelTask",
    "PuzzlesLogicStarBattleValidCellAnywhereLabelTask",
]
