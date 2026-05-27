"""Puzzle topology task for maze-exit reachability reasoning."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from ..shared.common import decouple_axis_sampling, projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import build_puzzle_complexity, clamp_unit_interval, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.fixed_query_task import rewrite_fixed_puzzle_query_output
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "puzzles_topology_maze_exit_internal"
MAZE_EXIT_REACHABILITY_LABEL_TASK_ID = "task_puzzles__maze__exit_reachability_label"
MAZE_REACHABLE_EXIT_COUNT_TASK_ID = "task_puzzles__maze__reachable_exit_count"
SCENE_ID = "maze"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "exit_reachability_label",
    "reachable_exit_count",
)
SUPPORTED_TARGET_REACHABILITY_VALUES: Tuple[str, ...] = ("reachable", "unreachable")
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "classic_wall_maze",
    "paper_labyrinth_maze",
    "block_wall_maze",
)
_SOURCE_QUERY_VARIANT_TARGET_REACHABILITY = {
    "reachable_exit_label": "reachable",
    "unreachable_exit_label": "unreachable",
}
_TARGET_REACHABILITY_DESCRIPTIONS = {
    "reachable": "reachable",
    "unreachable": "unreachable",
}
_REASONING_LOAD_BASE_BY_VARIANT = {
    "exit_reachability_label": 0.47,
    "reachable_exit_count": 0.52,
}
_TARGET_REACHABILITY_LOAD = {
    "reachable": 0.00,
    "unreachable": 0.02,
}
_SCENE_LOAD_BY_VARIANT = {
    "classic_wall_maze": 0.25,
    "paper_labyrinth_maze": 0.30,
    "block_wall_maze": 0.34,
}
_EXIT_LABEL_POOL: Tuple[str, ...] = tuple("ABCDEFGH")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "topology")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="topology")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="topology", apply_prob=0.0)

Color = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]
Cell = Tuple[int, int]
CellEdge = Tuple[Cell, Cell]


@dataclass(frozen=True)
class _MazeExitRenderParams:
    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    wall_stroke_width_px: int
    wall_stroke_width_min_px: int
    wall_stroke_width_max_px: int
    outer_wall_stroke_width_px: int
    outer_wall_stroke_width_min_px: int
    outer_wall_stroke_width_max_px: int
    exit_marker_radius_px: int
    exit_marker_shape: str
    exit_label_font_size_px: int
    start_font_size_px: int
    panel_fill_rgb: Color
    floor_fill_rgb: Color
    wall_color_rgb: Color
    border_color_rgb: Color
    text_color_rgb: Color
    text_stroke_rgb: Color
    start_fill_rgb: Color
    start_outline_rgb: Color
    exit_outline_rgb: Color
    exit_palette: Tuple[Color, ...]
    subtle_grid_rgb: Color
    unit_size_scale: float
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedMazeExitScene:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    scene_bbox_px: BBox
    item_bbox_map: Dict[str, BBox]
    cell_bbox_map: Dict[str, BBox]


def _to_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def _normalize_rgb(value: Any, fallback: Color) -> Color:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (
            max(0, min(255, _to_int(value[0], fallback[0]))),
            max(0, min(255, _to_int(value[1], fallback[1]))),
            max(0, min(255, _to_int(value[2], fallback[2]))),
        )
    return tuple(int(channel) for channel in fallback)


def _rgb_option(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: Color, *, seed: int) -> Color:
    raw = params.get(str(key), group_default(defaults, str(key), fallback))
    options = params.get(f"{key}_options", group_default(defaults, f"{key}_options", None))
    if isinstance(options, list) and options:
        rng = spawn_rng(int(seed), f"{TASK_ID}.render.{key}")
        return _normalize_rgb(options[int(rng.randrange(len(options)))], fallback)
    return _normalize_rgb(raw, fallback)


def _rgb_palette(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: Sequence[Color]) -> Tuple[Color, ...]:
    raw = params.get(str(key), group_default(defaults, str(key), list(fallback)))
    if not isinstance(raw, list) or not raw:
        raw = list(fallback)
    palette = tuple(_normalize_rgb(value, fallback[0]) for value in raw)
    return palette if palette else tuple(fallback)


def _string_option(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: str,
    *,
    seed: int,
    allowed: Sequence[str] | None = None,
) -> str:
    raw = str(params.get(str(key), group_default(defaults, str(key), str(fallback)))).strip() or str(fallback)
    options = params.get(f"{key}_options", group_default(defaults, f"{key}_options", None))
    if isinstance(options, list) and options:
        candidates = [str(value).strip() for value in options if str(value).strip()]
        if candidates:
            rng = spawn_rng(int(seed), f"{TASK_ID}.render.{key}")
            raw = str(candidates[int(rng.randrange(len(candidates)))])
    if allowed is not None and raw not in set(map(str, allowed)):
        return str(fallback)
    return str(raw)


def _resolve_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> _MazeExitRenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.maze.unit_size",
    )
    wall_default = _to_int(params.get("wall_stroke_width_px", group_default(render_defaults, "wall_stroke_width_px", 6)), 6)
    wall_min = _to_int(params.get("wall_stroke_width_min_px", group_default(render_defaults, "wall_stroke_width_min_px", wall_default)), wall_default)
    wall_max = _to_int(params.get("wall_stroke_width_max_px", group_default(render_defaults, "wall_stroke_width_max_px", wall_default)), wall_default)
    if int(wall_min) > int(wall_max):
        raise ValueError("wall_stroke_width_min_px must be <= wall_stroke_width_max_px")
    wall_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render.wall_width")
    wall_width = int(wall_rng.randint(max(2, int(wall_min)), max(2, int(wall_max))))
    outer_wall_default = _to_int(params.get("outer_wall_stroke_width_px", group_default(render_defaults, "outer_wall_stroke_width_px", 9)), 9)
    outer_wall_min = _to_int(
        params.get("outer_wall_stroke_width_min_px", group_default(render_defaults, "outer_wall_stroke_width_min_px", outer_wall_default)),
        outer_wall_default,
    )
    outer_wall_max = _to_int(
        params.get("outer_wall_stroke_width_max_px", group_default(render_defaults, "outer_wall_stroke_width_max_px", outer_wall_default)),
        outer_wall_default,
    )
    if int(outer_wall_min) > int(outer_wall_max):
        raise ValueError("outer_wall_stroke_width_min_px must be <= outer_wall_stroke_width_max_px")
    outer_wall_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render.outer_wall_width")
    outer_wall_width = int(outer_wall_rng.randint(max(3, int(outer_wall_min)), max(3, int(outer_wall_max))))
    return _MazeExitRenderParams(
        canvas_width=max(760, _to_int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 1200)), 1200)),
        canvas_height=max(620, _to_int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 900)), 900)),
        scene_margin_left_px=max(76, _to_int(params.get("scene_margin_left_px", group_default(render_defaults, "scene_margin_left_px", 104)), 104)),
        scene_margin_right_px=max(76, _to_int(params.get("scene_margin_right_px", group_default(render_defaults, "scene_margin_right_px", 104)), 104)),
        scene_margin_top_px=max(70, _to_int(params.get("scene_margin_top_px", group_default(render_defaults, "scene_margin_top_px", 90)), 90)),
        scene_margin_bottom_px=max(70, _to_int(params.get("scene_margin_bottom_px", group_default(render_defaults, "scene_margin_bottom_px", 90)), 90)),
        wall_stroke_width_px=max(2, scale_puzzle_px(wall_width, unit_scale, min_px=2)),
        wall_stroke_width_min_px=max(2, int(wall_min)),
        wall_stroke_width_max_px=max(2, int(wall_max)),
        outer_wall_stroke_width_px=max(3, scale_puzzle_px(outer_wall_width, unit_scale, min_px=3)),
        outer_wall_stroke_width_min_px=max(3, int(outer_wall_min)),
        outer_wall_stroke_width_max_px=max(3, int(outer_wall_max)),
        exit_marker_radius_px=max(13, scale_puzzle_px(_to_int(params.get("exit_marker_radius_px", group_default(render_defaults, "exit_marker_radius_px", 27)), 27), unit_scale, min_px=13)),
        exit_marker_shape=_string_option(
            params,
            render_defaults,
            "exit_marker_shape",
            "circle",
            seed=int(instance_seed),
            allowed=("circle", "square", "tab"),
        ),
        exit_label_font_size_px=max(14, scale_puzzle_px(_to_int(params.get("exit_label_font_size_px", group_default(render_defaults, "exit_label_font_size_px", 28)), 28), unit_scale, min_px=14)),
        start_font_size_px=max(11, scale_puzzle_px(_to_int(params.get("start_font_size_px", group_default(render_defaults, "start_font_size_px", 20)), 20), unit_scale, min_px=11)),
        panel_fill_rgb=_rgb_option(params, render_defaults, "panel_fill_rgb", (248, 249, 252), seed=int(instance_seed)),
        floor_fill_rgb=_rgb_option(params, render_defaults, "floor_fill_rgb", (255, 255, 255), seed=int(instance_seed)),
        wall_color_rgb=_rgb_option(params, render_defaults, "wall_color_rgb", (44, 52, 66), seed=int(instance_seed)),
        border_color_rgb=_rgb_option(params, render_defaults, "border_color_rgb", (96, 105, 118), seed=int(instance_seed)),
        text_color_rgb=_rgb_option(params, render_defaults, "text_color_rgb", (24, 29, 36), seed=int(instance_seed)),
        text_stroke_rgb=_rgb_option(params, render_defaults, "text_stroke_rgb", (255, 255, 255), seed=int(instance_seed)),
        start_fill_rgb=_rgb_option(params, render_defaults, "start_fill_rgb", (213, 239, 222), seed=int(instance_seed)),
        start_outline_rgb=_rgb_option(params, render_defaults, "start_outline_rgb", (44, 122, 84), seed=int(instance_seed)),
        exit_outline_rgb=_rgb_option(params, render_defaults, "exit_outline_rgb", (42, 48, 58), seed=int(instance_seed)),
        exit_palette=_rgb_palette(
            params,
            render_defaults,
            "exit_palette",
            ((242, 201, 80), (91, 158, 217), (224, 116, 92), (119, 184, 129), (165, 132, 211), (229, 151, 185), (95, 183, 178), (198, 145, 83)),
        ),
        subtle_grid_rgb=_rgb_option(params, render_defaults, "subtle_grid_rgb", (229, 232, 238), seed=int(instance_seed)),
        unit_size_scale=float(unit_scale),
        unit_size_jitter=dict(unit_meta),
    )


def _resolve_int_bounds(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    lower = _to_int(params.get(str(min_key), group_default(defaults, str(min_key), int(fallback_min))), int(fallback_min))
    upper = _to_int(params.get(str(max_key), group_default(defaults, str(max_key), int(fallback_max))), int(fallback_max))
    if int(lower) > int(upper):
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(lower), int(upper)


def _sample_int(
    *,
    rng,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    sampling_offset: int,
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = _resolve_int_bounds(
        params,
        defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
    )
    explicit = params.get(str(key))
    if explicit is not None:
        value = _to_int(explicit, int(lower))
        if not (int(lower) <= int(value) <= int(upper)):
            raise ValueError(f"{key} must be within [{lower}, {upper}]")
        return int(value), (int(lower), int(upper))
    support = list(range(int(lower), int(upper) + 1))
    _ = sampling_offset
    return int(rng.randint(int(lower), int(upper))), (int(lower), int(upper))


def _advance_sampling_after_axis(
    params: Mapping[str, Any],
    *,
    axis_size: int,
    explicit_keys: Sequence[str],
) -> Dict[str, Any]:
    """Return params unchanged for axis-advance call sites."""

    updated = dict(params)
    _ = int(axis_size), explicit_keys
    return updated


def _edge_key(a: Cell, b: Cell) -> CellEdge:
    return tuple(sorted((tuple(a), tuple(b))))  # type: ignore[return-value]


def _maze_cell_id(cell: Cell) -> str:
    return f"cell_c{int(cell[0])}_r{int(cell[1])}"


def _neighbors(cell: Cell, *, rows: int, cols: int) -> List[Cell]:
    col, row = int(cell[0]), int(cell[1])
    result: List[Cell] = []
    if col > 0:
        result.append((col - 1, row))
    if col + 1 < int(cols):
        result.append((col + 1, row))
    if row > 0:
        result.append((col, row - 1))
    if row + 1 < int(rows):
        result.append((col, row + 1))
    return result


def _generate_spanning_tree(
    *,
    rows: int,
    cols: int,
    start: Cell,
    rng,
    allowed_cells: set[Cell] | None = None,
) -> Tuple[CellEdge, ...]:
    if allowed_cells is None:
        allowed_cells = {
            (int(col), int(row))
            for row in range(int(rows))
            for col in range(int(cols))
        }
    if tuple(start) not in allowed_cells:
        raise ValueError("maze start cell must be inside the allowed cell set")
    visited = {tuple(start)}
    stack = [tuple(start)]
    edges: List[CellEdge] = []
    while stack:
        current = stack[-1]
        candidates = [
            cell
            for cell in _neighbors(current, rows=int(rows), cols=int(cols))
            if tuple(cell) in allowed_cells and tuple(cell) not in visited
        ]
        if not candidates:
            stack.pop()
            continue
        rng.shuffle(candidates)
        nxt = tuple(candidates[0])
        visited.add(nxt)
        stack.append(nxt)
        edges.append(_edge_key(current, nxt))
    if len(visited) != len(allowed_cells):
        raise ValueError("maze spanning tree failed to visit all cells")
    return tuple(edges)


def _boundary_sides(cell: Cell, *, rows: int, cols: int) -> Tuple[str, ...]:
    col, row = int(cell[0]), int(cell[1])
    sides: List[str] = []
    if row == 0:
        sides.append("top")
    if col == int(cols) - 1:
        sides.append("right")
    if row == int(rows) - 1:
        sides.append("bottom")
    if col == 0:
        sides.append("left")
    return tuple(sides)


def _reachable_cells_from_start(*, start: Cell, rows: int, cols: int, edges: Sequence[CellEdge]) -> Tuple[Cell, ...]:
    edge_set = {_edge_key(a, b) for a, b in edges}
    frontier = [tuple(start)]
    visited = {tuple(start)}
    while frontier:
        current = frontier.pop(0)
        for nxt in _neighbors(current, rows=int(rows), cols=int(cols)):
            if tuple(nxt) in visited:
                continue
            if _edge_key(current, tuple(nxt)) not in edge_set:
                continue
            visited.add(tuple(nxt))
            frontier.append(tuple(nxt))
    return tuple(sorted(visited, key=lambda item: (item[1], item[0])))


def _exit_clockwise_sort_key(exit_spec: Mapping[str, Any], *, rows: int, cols: int) -> Tuple[int, int]:
    col, row = (int(value) for value in exit_spec["cell"])
    side = str(exit_spec["side"])
    if side == "top":
        return (0, col)
    if side == "right":
        return (1, row)
    if side == "bottom":
        return (2, int(cols) - 1 - col)
    return (3, int(rows) - 1 - row)


def _sample_exit_target_index(*, params: Mapping[str, Any], rng, exit_count: int, offset: int) -> int:
    support = list(range(int(exit_count)))
    if "target_exit_index" in params:
        value = _to_int(params["target_exit_index"], 0)
        if int(value) not in support:
            raise ValueError("target_exit_index must be within the active exit support")
        return int(value)
    _ = offset
    return int(rng.choice(support))


def _sample_reachable_count(*, params: Mapping[str, Any], defaults: Mapping[str, Any], rng, exit_count: int) -> Tuple[int, Tuple[int, int]]:
    lower, upper = _resolve_int_bounds(
        params,
        defaults,
        min_key="reachable_exit_count_min",
        max_key="reachable_exit_count_max",
        fallback_min=1,
        fallback_max=5,
    )
    active_lower = max(1, min(int(lower), int(exit_count) - 1))
    active_upper = max(int(active_lower), min(int(upper), int(exit_count) - 1))
    support = list(range(int(active_lower), int(active_upper) + 1))
    if "reachable_exit_count" in params:
        value = _to_int(params["reachable_exit_count"], int(active_lower))
        if int(value) not in support:
            raise ValueError("reachable_exit_count must be within the active exit-count support")
        return int(value), (int(lower), int(upper))
    return int(rng.choice(support)), (int(lower), int(upper))


def _sample_reachable_count_for_exit_range(
    *,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
    exit_count_range: Tuple[int, int],
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = _resolve_int_bounds(
        params,
        defaults,
        min_key="reachable_exit_count_min",
        max_key="reachable_exit_count_max",
        fallback_min=1,
        fallback_max=5,
    )
    active_lower = max(1, min(int(lower), int(exit_count_range[1]) - 1))
    active_upper = max(int(active_lower), min(int(upper), int(exit_count_range[1]) - 1))
    support = list(range(int(active_lower), int(active_upper) + 1))
    if "reachable_exit_count" in params:
        value = _to_int(params["reachable_exit_count"], int(active_lower))
        if int(value) not in support:
            raise ValueError("reachable_exit_count must be within the active exit-count support")
        return int(value), (int(lower), int(upper))
    return int(rng.choice(support)), (int(lower), int(upper))


def _sample_exit_count_for_reachable_count(
    *,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
    reachable_count: int,
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = _resolve_int_bounds(
        params,
        defaults,
        min_key="exit_count_min",
        max_key="exit_count_max",
        fallback_min=5,
        fallback_max=8,
    )
    if int(upper) > len(_EXIT_LABEL_POOL):
        raise ValueError("exit_count cannot exceed the available exit-label pool")
    active_lower = max(int(lower), int(reachable_count) + 1)
    if int(active_lower) > int(upper):
        raise ValueError("reachable_exit_count requires more exits than exit_count_max allows")
    support = list(range(int(active_lower), int(upper) + 1))
    if "exit_count" in params:
        value = _to_int(params["exit_count"], int(active_lower))
        if not (int(lower) <= int(value) <= int(upper)):
            raise ValueError(f"exit_count must be within [{lower}, {upper}]")
        if int(value) <= int(reachable_count):
            raise ValueError("exit_count must be greater than reachable_exit_count")
        return int(value), (int(lower), int(upper))
    return int(rng.choice(support)), (int(lower), int(upper))


def _build_maze_exit_dataset(
    *,
    query_variant: str,
    target_reachability: str | None,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    max_attempts: int,
) -> Dict[str, Any]:
    is_label_variant = str(query_variant) == "exit_reachability_label"
    if bool(is_label_variant):
        if str(target_reachability) not in set(SUPPORTED_TARGET_REACHABILITY_VALUES):
            raise ValueError("target_reachability must be reachable or unreachable for exit_reachability_label")
        resolved_target_reachability = str(target_reachability)
    else:
        resolved_target_reachability = None
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    rows, row_range = _sample_int(
        rng=rng,
        params=params,
        defaults=gen_defaults,
        key="maze_rows",
        min_key="maze_rows_min",
        max_key="maze_rows_max",
        fallback_min=7,
        fallback_max=10,
        sampling_offset=0,
    )
    cols, col_range = _sample_int(
        rng=rng,
        params=params,
        defaults=gen_defaults,
        key="maze_cols",
        min_key="maze_cols_min",
        max_key="maze_cols_max",
        fallback_min=9,
        fallback_max=13,
        sampling_offset=3,
    )
    sampled_reachable_count: int | None = None
    reachable_count_range: Tuple[int, int] | None = None

    if str(query_variant) == "reachable_exit_count" and "exit_count" not in params:
        exit_count_bounds = _resolve_int_bounds(
            params,
            gen_defaults,
            min_key="exit_count_min",
            max_key="exit_count_max",
            fallback_min=5,
            fallback_max=8,
        )
        sampled_reachable_count, reachable_count_range = _sample_reachable_count_for_exit_range(
            params=params,
            defaults=gen_defaults,
            rng=rng,
            exit_count_range=exit_count_bounds,
        )
        exit_count, exit_count_range = _sample_exit_count_for_reachable_count(
            params=params,
            defaults=gen_defaults,
            rng=rng,
            reachable_count=int(sampled_reachable_count),
        )
    else:
        exit_count, exit_count_range = _sample_int(
            rng=rng,
            params=params,
            defaults=gen_defaults,
            key="exit_count",
            min_key="exit_count_min",
            max_key="exit_count_max",
            fallback_min=5,
            fallback_max=8,
            sampling_offset=11,
        )
    if int(exit_count) > len(_EXIT_LABEL_POOL):
        raise ValueError("exit_count cannot exceed the available exit-label pool")

    start_col_options = [max(1, int(cols) // 2 - 1), int(cols) // 2, min(int(cols) - 2, int(cols) // 2 + 1)]
    start_row_options = [max(1, int(rows) // 2 - 1), int(rows) // 2, min(int(rows) - 2, int(rows) // 2 + 1)]
    start = (int(rng.choice(start_col_options)), int(rng.choice(start_row_options)))
    if not (0 < start[0] < int(cols) - 1 and 0 < start[1] < int(rows) - 1):
        start = (max(1, min(int(cols) - 2, int(cols) // 2)), max(1, min(int(rows) - 2, int(rows) // 2)))

    all_boundary_cells = [
        (int(col), int(row))
        for row in range(int(rows))
        for col in range(int(cols))
        if bool(_boundary_sides((int(col), int(row)), rows=int(rows), cols=int(cols)))
    ]
    attempt_count = max(120, int(max_attempts) * 16)
    for attempt in range(int(attempt_count)):
        tree_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.maze_tree", index=int(attempt))
        candidate_cells = list(all_boundary_cells)
        tree_rng.shuffle(candidate_cells)
        if len(candidate_cells) < int(exit_count):
            continue
        exit_cells = [tuple(cell) for cell in candidate_cells[: int(exit_count)]]
        labels = list(_EXIT_LABEL_POOL)
        tree_rng.shuffle(labels)
        exits: List[Dict[str, Any]] = []
        for index, cell in enumerate(exit_cells):
            sides = list(_boundary_sides(cell, rows=int(rows), cols=int(cols)))
            side = str(tree_rng.choice(sides))
            exits.append(
                {
                    "item_id": f"exit_{index + 1}",
                    "label": str(labels[index]),
                    "cell": [int(cell[0]), int(cell[1])],
                    "side": str(side),
                }
            )
        exits = sorted(exits, key=lambda item: _exit_clockwise_sort_key(item, rows=int(rows), cols=int(cols)))

        target_index = _sample_exit_target_index(params=params, rng=tree_rng, exit_count=int(exit_count), offset=17)
        if bool(is_label_variant) and str(resolved_target_reachability) == "reachable":
            reachable_indices = {int(target_index)}
        elif bool(is_label_variant) and str(resolved_target_reachability) == "unreachable":
            reachable_indices = {index for index in range(int(exit_count)) if index != int(target_index)}
        else:
            if sampled_reachable_count is None:
                sampled_reachable_count, reachable_count_range = _sample_reachable_count(
                    params=params,
                    defaults=gen_defaults,
                    rng=tree_rng,
                    exit_count=int(exit_count),
                )
            shuffled_indices = list(range(int(exit_count)))
            tree_rng.shuffle(shuffled_indices)
            reachable_indices = set(shuffled_indices[: int(sampled_reachable_count)])

        blocked_exit_cells = {
            tuple(int(value) for value in exit_spec["cell"])
            for index, exit_spec in enumerate(exits)
            if int(index) not in reachable_indices
        }
        allowed_cells = {
            (int(col), int(row))
            for row in range(int(rows))
            for col in range(int(cols))
            if (int(col), int(row)) not in blocked_exit_cells
        }
        try:
            open_edges = set(
                _generate_spanning_tree(
                    rows=int(rows),
                    cols=int(cols),
                    start=tuple(start),
                    rng=tree_rng,
                    allowed_cells=allowed_cells,
                )
            )
        except ValueError:
            continue
        for index, exit_spec in enumerate(exits):
            cell = tuple(int(value) for value in exit_spec["cell"])
            if int(index) in reachable_indices and cell not in allowed_cells:
                raise ValueError("reachable exit cell was excluded from the maze")

        reachable_cells = set(_reachable_cells_from_start(start=tuple(start), rows=int(rows), cols=int(cols), edges=tuple(open_edges)))
        for index, exit_spec in enumerate(exits):
            cell = tuple(int(value) for value in exit_spec["cell"])
            exit_spec["reachable"] = bool(cell in reachable_cells)
        if {index for index, exit_spec in enumerate(exits) if bool(exit_spec["reachable"])} != set(reachable_indices):
            continue

        reachable_exits = [exit_spec for exit_spec in exits if bool(exit_spec["reachable"])]
        unreachable_exits = [exit_spec for exit_spec in exits if not bool(exit_spec["reachable"])]
        reachable_labels = [str(exit_spec["label"]) for exit_spec in reachable_exits]
        unreachable_labels = [str(exit_spec["label"]) for exit_spec in unreachable_exits]
        if bool(is_label_variant) and str(resolved_target_reachability) == "reachable":
            answer_exit = reachable_exits[0]
            answer_value: str | int = str(answer_exit["label"])
            supporting_item_ids = [str(answer_exit["item_id"])]
            evidence_policy = "single_reachable_exit_bbox"
            query_details: Dict[str, Any] = {"target_reachability": str(resolved_target_reachability)}
        elif bool(is_label_variant) and str(resolved_target_reachability) == "unreachable":
            answer_exit = unreachable_exits[0]
            answer_value = str(answer_exit["label"])
            supporting_item_ids = [str(answer_exit["item_id"])]
            evidence_policy = "single_unreachable_exit_bbox"
            query_details = {"target_reachability": str(resolved_target_reachability)}
        else:
            answer_value = int(len(reachable_exits))
            supporting_item_ids = [str(exit_spec["item_id"]) for exit_spec in sorted(reachable_exits, key=lambda item: str(item["label"]))]
            evidence_policy = "reachable_exit_bboxes_by_label"
            query_details = {"reachable_exit_count": int(answer_value)}
            reachable_count_range = locals().get("reachable_count_range", [1, 5])

        return {
            "query_variant": str(query_variant),
            "target_reachability": str(resolved_target_reachability) if resolved_target_reachability is not None else None,
            "scene_variant": str(scene_variant),
            "question_format": str(query_variant),
            "view_family": "topology_orthogonal_maze_exit_label",
            "topology_rule": "move_through_open_corridors_from_start_walls_block_motion",
            "maze_rows": int(rows),
            "maze_cols": int(cols),
            "maze_rows_range": [int(row_range[0]), int(row_range[1])],
            "maze_cols_range": [int(col_range[0]), int(col_range[1])],
            "start_cell": [int(start[0]), int(start[1])],
            "open_edges": [
                [[int(edge[0][0]), int(edge[0][1])], [int(edge[1][0]), int(edge[1][1])]]
                for edge in sorted(open_edges, key=lambda item: (item[0][1], item[0][0], item[1][1], item[1][0]))
            ],
            "exits": [dict(exit_spec) for exit_spec in exits],
            "exit_count": int(exit_count),
            "exit_count_range": [int(exit_count_range[0]), int(exit_count_range[1])],
            "reachable_exit_count": int(len(reachable_exits)),
            "reachable_exit_count_range": list(reachable_count_range) if str(query_variant) == "reachable_exit_count" else [1, max(1, int(exit_count) - 1)],
            "reachable_exit_labels": list(reachable_labels),
            "unreachable_exit_labels": list(unreachable_labels),
            "answer_value": answer_value,
            "supporting_item_ids": list(supporting_item_ids),
            "evidence_policy": str(evidence_policy),
            "query_details": dict(query_details),
            "solver_trace": {
                "start_cell": [int(start[0]), int(start[1])],
                "reachable_exit_labels": list(reachable_labels),
                "unreachable_exit_labels": list(unreachable_labels),
                "target_reachability": str(resolved_target_reachability) if resolved_target_reachability is not None else None,
                "answer_value": answer_value,
                "supporting_item_ids": list(supporting_item_ids),
                "evidence_policy": str(evidence_policy),
                **dict(query_details),
            },
        }

    raise ValueError("failed to build a maze with enough boundary leaf exits")


def _line_with_gap(
    draw: ImageDraw.ImageDraw,
    *,
    start: Tuple[float, float],
    end: Tuple[float, float],
    gap_center: Tuple[float, float] | None,
    gap_size: float,
    fill: Color,
    width: int,
) -> None:
    if gap_center is None:
        draw.line((float(start[0]), float(start[1]), float(end[0]), float(end[1])), fill=fill, width=int(width))
        return
    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    cx, cy = float(gap_center[0]), float(gap_center[1])
    if abs(y0 - y1) <= 1e-6:
        half = 0.5 * float(gap_size)
        draw.line((x0, y0, max(x0, cx - half), y0), fill=fill, width=int(width))
        draw.line((min(x1, cx + half), y0, x1, y0), fill=fill, width=int(width))
    else:
        half = 0.5 * float(gap_size)
        draw.line((x0, y0, x0, max(y0, cy - half)), fill=fill, width=int(width))
        draw.line((x0, min(y1, cy + half), x0, y1), fill=fill, width=int(width))


def _cell_center(*, left: float, top: float, cell_size: float, cell: Cell) -> Tuple[float, float]:
    return (
        float(left + ((float(cell[0]) + 0.5) * float(cell_size))),
        float(top + ((float(cell[1]) + 0.5) * float(cell_size))),
    )


def _text_bbox_for_center(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    pad: float,
    stroke_width: int,
) -> BBox:
    try:
        raw = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        width = float(raw[2] - raw[0])
        height = float(raw[3] - raw[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
    cx, cy = float(center[0]), float(center[1])
    return (float(cx - (0.5 * width) - pad), float(cy - (0.5 * height) - pad), float(cx + (0.5 * width) + pad), float(cy + (0.5 * height) + pad))


def _maze_exit_marker_bbox(
    *,
    center: Tuple[float, float],
    radius: float,
    side: str,
    shape: str,
) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    r = float(radius)
    if str(shape) == "tab":
        if str(side) in {"top", "bottom"}:
            return (float(cx - (1.18 * r)), float(cy - (0.78 * r)), float(cx + (1.18 * r)), float(cy + (0.78 * r)))
        return (float(cx - (0.78 * r)), float(cy - (1.18 * r)), float(cx + (0.78 * r)), float(cy + (1.18 * r)))
    return (float(cx - r), float(cy - r), float(cx + r), float(cy + r))


def _draw_maze_exit_marker(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    fill: Color,
    outline: Color,
    shape: str,
) -> None:
    if str(shape) == "square":
        radius = max(3, int(round((float(bbox[2]) - float(bbox[0])) * 0.10)))
        draw.rounded_rectangle(tuple(float(value) for value in bbox), radius=radius, fill=tuple(fill), outline=tuple(outline), width=3)
    elif str(shape) == "tab":
        radius = max(5, int(round(min(float(bbox[2]) - float(bbox[0]), float(bbox[3]) - float(bbox[1])) * 0.22)))
        draw.rounded_rectangle(tuple(float(value) for value in bbox), radius=radius, fill=tuple(fill), outline=tuple(outline), width=3)
    else:
        draw.ellipse(tuple(float(value) for value in bbox), fill=tuple(fill), outline=tuple(outline), width=3)


def _render_maze_exit_scene(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: _MazeExitRenderParams,
) -> _RenderedMazeExitScene:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    rows = int(dataset["maze_rows"])
    cols = int(dataset["maze_cols"])
    usable_width = float(render_params.canvas_width - render_params.scene_margin_left_px - render_params.scene_margin_right_px)
    usable_height = float(render_params.canvas_height - render_params.scene_margin_top_px - render_params.scene_margin_bottom_px)
    cell_size = float(min(usable_width / float(cols), usable_height / float(rows))) * float(render_params.unit_size_scale)
    grid_width = float(cell_size * float(cols))
    grid_height = float(cell_size * float(rows))
    left = float((render_params.canvas_width - grid_width) / 2.0)
    top = float((render_params.canvas_height - grid_height) / 2.0)
    right = float(left + grid_width)
    bottom = float(top + grid_height)
    pad = float(max(18, int(round(cell_size * 0.26))))

    scene_panel = (float(left - pad), float(top - pad), float(right + pad), float(bottom + pad))
    draw.rectangle(scene_panel, fill=tuple(render_params.panel_fill_rgb), outline=tuple(render_params.border_color_rgb), width=2)
    draw.rectangle((float(left), float(top), float(right), float(bottom)), fill=tuple(render_params.floor_fill_rgb))

    if str(scene_variant) in {"paper_labyrinth_maze", "block_wall_maze"}:
        grid_width_px = 1 if str(scene_variant) == "paper_labyrinth_maze" else 2
        for col in range(1, int(cols)):
            x = float(left + (col * cell_size))
            draw.line((x, top, x, bottom), fill=tuple(render_params.subtle_grid_rgb), width=int(grid_width_px))
        for row in range(1, int(rows)):
            y = float(top + (row * cell_size))
            draw.line((left, y, right, y), fill=tuple(render_params.subtle_grid_rgb), width=int(grid_width_px))

    exits = [dict(exit_spec) for exit_spec in dataset["exits"]]
    exit_by_wall: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for exit_spec in exits:
        col, row = (int(value) for value in exit_spec["cell"])
        side = str(exit_spec["side"])
        if side == "top":
            exit_by_wall[("top", col)] = exit_spec
        elif side == "bottom":
            exit_by_wall[("bottom", col)] = exit_spec
        elif side == "left":
            exit_by_wall[("left", row)] = exit_spec
        else:
            exit_by_wall[("right", row)] = exit_spec

    open_edges = {
        _edge_key(tuple(edge[0]), tuple(edge[1]))
        for edge in dataset["open_edges"]
    }
    cell_bbox_map: Dict[str, BBox] = {}
    wall_width = int(render_params.wall_stroke_width_px)
    outer_wall_width = int(render_params.outer_wall_stroke_width_px)
    gap_size = float(cell_size * 0.52)

    for row in range(int(rows)):
        y0 = float(top + (row * cell_size))
        y1 = float(top + ((row + 1) * cell_size))
        for col in range(int(cols)):
            x0 = float(left + (col * cell_size))
            x1 = float(left + ((col + 1) * cell_size))
            current = (int(col), int(row))
            cell_bbox_map[_maze_cell_id(current)] = (float(x0), float(y0), float(x1), float(y1))
            if row == 0:
                exit_spec = exit_by_wall.get(("top", int(col)))
                _line_with_gap(
                    draw,
                    start=(x0, y0),
                    end=(x1, y0),
                    gap_center=((x0 + x1) / 2.0, y0) if exit_spec is not None else None,
                    gap_size=gap_size,
                    fill=render_params.wall_color_rgb,
                    width=outer_wall_width,
                )
            if col == 0:
                exit_spec = exit_by_wall.get(("left", int(row)))
                _line_with_gap(
                    draw,
                    start=(x0, y0),
                    end=(x0, y1),
                    gap_center=(x0, (y0 + y1) / 2.0) if exit_spec is not None else None,
                    gap_size=gap_size,
                    fill=render_params.wall_color_rgb,
                    width=outer_wall_width,
                )
            if col == int(cols) - 1:
                exit_spec = exit_by_wall.get(("right", int(row)))
                _line_with_gap(
                    draw,
                    start=(x1, y0),
                    end=(x1, y1),
                    gap_center=(x1, (y0 + y1) / 2.0) if exit_spec is not None else None,
                    gap_size=gap_size,
                    fill=render_params.wall_color_rgb,
                    width=outer_wall_width,
                )
            else:
                neighbor = (int(col) + 1, int(row))
                if _edge_key(current, neighbor) not in open_edges:
                    draw.line((x1, y0, x1, y1), fill=tuple(render_params.wall_color_rgb), width=wall_width)
            if row == int(rows) - 1:
                exit_spec = exit_by_wall.get(("bottom", int(col)))
                _line_with_gap(
                    draw,
                    start=(x0, y1),
                    end=(x1, y1),
                    gap_center=((x0 + x1) / 2.0, y1) if exit_spec is not None else None,
                    gap_size=gap_size,
                    fill=render_params.wall_color_rgb,
                    width=outer_wall_width,
                )
            else:
                neighbor = (int(col), int(row) + 1)
                if _edge_key(current, neighbor) not in open_edges:
                    draw.line((x0, y1, x1, y1), fill=tuple(render_params.wall_color_rgb), width=wall_width)

    entities: List[Dict[str, Any]] = []
    item_bbox_map: Dict[str, BBox] = {}

    start_cell = tuple(int(value) for value in dataset["start_cell"])
    start_center = _cell_center(left=left, top=top, cell_size=cell_size, cell=start_cell)
    start_box_w = float(cell_size * 0.72)
    start_box_h = float(cell_size * 0.42)
    start_bbox = (
        float(start_center[0] - (0.5 * start_box_w)),
        float(start_center[1] - (0.5 * start_box_h)),
        float(start_center[0] + (0.5 * start_box_w)),
        float(start_center[1] + (0.5 * start_box_h)),
    )
    draw.rounded_rectangle(start_bbox, radius=max(4, int(round(cell_size * 0.08))), fill=tuple(render_params.start_fill_rgb), outline=tuple(render_params.start_outline_rgb), width=3)
    start_font = fit_font_to_box(
        draw,
        text="START",
        max_width=float(start_box_w),
        max_height=float(start_box_h),
        bold=True,
        min_size_px=10,
        max_size_px=int(render_params.start_font_size_px),
        fill_ratio=0.86,
    )
    draw_text_centered(
        draw,
        text="START",
        center=start_center,
        font=start_font,
        fill=tuple(render_params.text_color_rgb),
        stroke_fill=tuple(render_params.text_stroke_rgb),
        stroke_width=1,
    )
    entities.append({"entity_id": "start", "role": "start", "label": "START", "cell": [int(start_cell[0]), int(start_cell[1])], "bbox_px": list(start_bbox)})

    exit_font = load_font(int(render_params.exit_label_font_size_px), bold=True)
    marker_radius = float(render_params.exit_marker_radius_px)
    label_offset = float(marker_radius + max(14.0, cell_size * 0.22))
    door_color = tuple(render_params.floor_fill_rgb)
    for index, exit_spec in enumerate(exits):
        col, row = (int(value) for value in exit_spec["cell"])
        side = str(exit_spec["side"])
        cell_center = _cell_center(left=left, top=top, cell_size=cell_size, cell=(col, row))
        if side == "top":
            marker_center = (float(cell_center[0]), float(top - label_offset))
            door_bbox = (float(cell_center[0] - (gap_size * 0.35)), float(top - outer_wall_width * 0.6), float(cell_center[0] + (gap_size * 0.35)), float(top + outer_wall_width * 0.6))
        elif side == "bottom":
            marker_center = (float(cell_center[0]), float(bottom + label_offset))
            door_bbox = (float(cell_center[0] - (gap_size * 0.35)), float(bottom - outer_wall_width * 0.6), float(cell_center[0] + (gap_size * 0.35)), float(bottom + outer_wall_width * 0.6))
        elif side == "left":
            marker_center = (float(left - label_offset), float(cell_center[1]))
            door_bbox = (float(left - outer_wall_width * 0.6), float(cell_center[1] - (gap_size * 0.35)), float(left + outer_wall_width * 0.6), float(cell_center[1] + (gap_size * 0.35)))
        else:
            marker_center = (float(right + label_offset), float(cell_center[1]))
            door_bbox = (float(right - outer_wall_width * 0.6), float(cell_center[1] - (gap_size * 0.35)), float(right + outer_wall_width * 0.6), float(cell_center[1] + (gap_size * 0.35)))

        draw.rectangle(door_bbox, fill=door_color)
        marker_fill = tuple(render_params.exit_palette[int(index) % len(render_params.exit_palette)])
        marker_bbox = _maze_exit_marker_bbox(
            center=marker_center,
            radius=float(marker_radius),
            side=str(side),
            shape=str(render_params.exit_marker_shape),
        )
        _draw_maze_exit_marker(
            draw,
            bbox=marker_bbox,
            fill=marker_fill,
            outline=tuple(render_params.exit_outline_rgb),
            shape=str(render_params.exit_marker_shape),
        )
        draw_text_centered(
            draw,
            text=str(exit_spec["label"]),
            center=marker_center,
            font=exit_font,
            fill=tuple(render_params.text_color_rgb),
            stroke_fill=tuple(render_params.text_stroke_rgb),
            stroke_width=1,
        )
        text_bbox = _text_bbox_for_center(
            draw,
            text=str(exit_spec["label"]),
            center=marker_center,
            font=exit_font,
            pad=8.0,
            stroke_width=1,
        )
        item_bbox = (
            float(min(marker_bbox[0], text_bbox[0], door_bbox[0])),
            float(min(marker_bbox[1], text_bbox[1], door_bbox[1])),
            float(max(marker_bbox[2], text_bbox[2], door_bbox[2])),
            float(max(marker_bbox[3], text_bbox[3], door_bbox[3])),
        )
        item_bbox_map[str(exit_spec["item_id"])] = item_bbox
        entities.append(
            {
                "entity_id": str(exit_spec["item_id"]),
                "role": "reachable_exit" if bool(exit_spec["reachable"]) else "unreachable_exit",
                "label": str(exit_spec["label"]),
                "cell": [int(col), int(row)],
                "side": str(side),
                "reachable": bool(exit_spec["reachable"]),
                "bbox_px": list(item_bbox),
            }
        )

    scene_bbox = (
        float(max(0.0, min(scene_panel[0], *(bbox[0] for bbox in item_bbox_map.values())))),
        float(max(0.0, min(scene_panel[1], *(bbox[1] for bbox in item_bbox_map.values())))),
        float(min(float(render_params.canvas_width), max(scene_panel[2], *(bbox[2] for bbox in item_bbox_map.values())))),
        float(min(float(render_params.canvas_height), max(scene_panel[3], *(bbox[3] for bbox in item_bbox_map.values())))),
    )
    return _RenderedMazeExitScene(
        image=image,
        entities=tuple(entities),
        scene_bbox_px=scene_bbox,
        item_bbox_map=dict(item_bbox_map),
        cell_bbox_map=dict(cell_bbox_map),
    )


class _PuzzlesTopologyMazeExitBaseTask:
    """Answer reachability questions over a wall maze with labeled exits."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "topology"
    supported_query_variants: Tuple[str, ...] = SUPPORTED_QUERY_VARIANTS

    def _resolve_query_variant(
        self,
        params: Mapping[str, Any],
        *,
        instance_seed: int,
    ) -> Tuple[str, Dict[str, float], str | None]:
        explicit_variant = params.get("query_variant")
        source_target_reachability: str | None = None
        variant_params = dict(params)
        if explicit_variant is not None and str(explicit_variant) in _SOURCE_QUERY_VARIANT_TARGET_REACHABILITY:
            source_target_reachability = str(_SOURCE_QUERY_VARIANT_TARGET_REACHABILITY[str(explicit_variant)])
            variant_params["query_variant"] = "exit_reachability_label"
        query_variant, query_variant_probabilities = resolve_puzzle_axis_variant(
            params=variant_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=self.supported_query_variants,
            task_id=self.task_id,
            explicit_key="query_variant",
            weights_key="query_variant_weights",
            balance_flag_key="balanced_query_variant_sampling",
            axis_namespace="query_variant",
        )
        return str(query_variant), dict(query_variant_probabilities), source_target_reachability

    def _resolve_target_reachability(
        self,
        params: Mapping[str, Any],
        *,
        instance_seed: int,
        source_target_reachability: str | None,
    ) -> Tuple[str, Dict[str, float]]:
        if source_target_reachability is not None:
            selected = str(source_target_reachability)
            return selected, {
                value: (1.0 if str(value) == selected else 0.0)
                for value in SUPPORTED_TARGET_REACHABILITY_VALUES
            }
        target_reachability, target_reachability_probabilities = resolve_puzzle_axis_variant(
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_TARGET_REACHABILITY_VALUES,
            task_id=self.task_id,
            explicit_key="target_reachability",
            weights_key="target_reachability_weights",
            balance_flag_key="balanced_target_reachability_sampling",
            axis_namespace="target_reachability",
        )
        return str(target_reachability), dict(target_reachability_probabilities)

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_variant, query_variant_probabilities, source_target_reachability = self._resolve_query_variant(
            params,
            instance_seed=int(instance_seed),
        )
        after_task_params = _advance_sampling_after_axis(
            params,
            axis_size=len(self.supported_query_variants),
            explicit_keys=("query_variant",),
        )
        target_reachability: str | None = None
        target_reachability_probabilities: Dict[str, float] = {}
        after_target_params = dict(after_task_params)
        if str(query_variant) == "exit_reachability_label":
            target_reachability, target_reachability_probabilities = self._resolve_target_reachability(
                after_task_params,
                instance_seed=int(instance_seed),
                source_target_reachability=source_target_reachability,
            )
            after_target_params = _advance_sampling_after_axis(
                after_task_params,
                axis_size=len(SUPPORTED_TARGET_REACHABILITY_VALUES),
                explicit_keys=(
                    ("target_reachability", "query_variant")
                    if source_target_reachability is not None
                    else ("target_reachability",)
                ),
            )
        scene_params = after_target_params
        scene_variant, scene_variant_probabilities = resolve_puzzle_axis_variant(
            params=scene_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_SCENE_VARIANTS,
            task_id=self.task_id,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        dataset_params = decouple_axis_sampling(
            scene_params,
            preceding_axis_size=len(SUPPORTED_SCENE_VARIANTS),
            explicit_key="maze_rows",
        )
        dataset = _build_maze_exit_dataset(
            query_variant=str(query_variant),
            target_reachability=str(target_reachability) if target_reachability is not None else None,
            scene_variant=str(scene_variant),
            params=dataset_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            max_attempts=int(max_attempts),
        )
        render_params = _resolve_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.maze_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            floor_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            wall_color_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            subtle_grid_rgb=tuple(int(value) for value in scene_style.notebook_line_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_maze_exit_scene(
            background,
            dataset=dataset,
            scene_variant=str(scene_variant),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_classic_wall_maze",
                "object_description_paper_labyrinth_maze",
                "object_description_block_wall_maze",
                "answer_hint_exit_reachability_label",
                "answer_hint_reachable_exit_count",
                "evidence_hint_exit_reachability_label",
                "evidence_hint_reachable_exit_count",
                "json_example_exit_reachability_label",
                "json_example_reachable_exit_count",
                "json_example_answer_only_exit_reachability_label",
                "json_example_answer_only_reachable_exit_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        target_reachability_description = str(
            _TARGET_REACHABILITY_DESCRIPTIONS.get(str(target_reachability), "")
        )
        answer_hint = str(prompt_defaults[f"answer_hint_{str(query_variant)}"]).format(
            target_reachability_description=str(target_reachability_description),
        )
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(query_variant)}"]).format(
            target_reachability_description=str(target_reachability_description),
        )
        json_example = str(prompt_defaults[f"json_example_{str(query_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "target_reachability_description": str(target_reachability_description),
                "target_exit_label": str(dataset["query_details"].get("target_exit_label", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        supporting_item_ids = [str(value) for value in dataset["supporting_item_ids"]]
        rounded_item_bbox_map = {
            str(key): [round(float(value), 3) for value in bbox]
            for key, bbox in rendered_scene.item_bbox_map.items()
        }
        rounded_cell_bbox_map = {
            str(key): [round(float(value), 3) for value in bbox]
            for key, bbox in rendered_scene.cell_bbox_map.items()
        }
        evidence_projection = projected_puzzle_bbox_evidence(rounded_item_bbox_map, supporting_item_ids)
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        supporting_evidence_source = "item_bboxes_px"
        witness_type = "bbox_set"
        witness_value = list(evidence_bboxes)
        evidence_count = len(evidence_bboxes)
        if len(evidence_bboxes) != len(supporting_item_ids):
            raise ValueError("maze-exit evidence projection does not match supporting item ids")
        answer_value = dataset["answer_value"]
        if str(query_variant) == "reachable_exit_count":
            answer_gt = TypedValue(type="integer", value=int(answer_value))
        else:
            answer_gt = TypedValue(type="string", value=str(answer_value))

        exit_scan = normalize_int_with_bounds(int(dataset["exit_count"]), list(dataset["exit_count_range"]))
        row_scan = normalize_int_with_bounds(int(dataset["maze_rows"]), list(dataset["maze_rows_range"]))
        col_scan = normalize_int_with_bounds(int(dataset["maze_cols"]), list(dataset["maze_cols_range"]))
        evidence_denominator = max(1.0, float(dataset["exit_count_range"][1]))
        evidence_load = min(1.0, float(evidence_count) / float(evidence_denominator))
        reasoning_load = min(
            1.0,
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_variant)])
            + float(_TARGET_REACHABILITY_LOAD.get(str(target_reachability), 0.0))
            + (0.08 * float(exit_scan))
            + (0.10 * float(evidence_load)),
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": max(float(exit_scan), 0.5 * (float(row_scan) + float(col_scan))),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_topology_maze_exit_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "target_reachability": str(target_reachability) if target_reachability is not None else None,
                    "scene_variant": str(scene_variant),
                    "answer_value": answer_value,
                    "reachable_exit_labels": [str(value) for value in dataset["reachable_exit_labels"]],
                    "unreachable_exit_labels": [str(value) for value in dataset["unreachable_exit_labels"]],
                    "supporting_item_ids": list(supporting_item_ids),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "target_reachability": str(target_reachability) if target_reachability is not None else None,
                    "scene_variant": str(scene_variant),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "target_reachability_probabilities": dict(target_reachability_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "maze_rows": int(dataset["maze_rows"]),
                    "maze_cols": int(dataset["maze_cols"]),
                    "exit_count": int(dataset["exit_count"]),
                    "reachable_exit_count": int(dataset["reachable_exit_count"]),
                    **dict(dataset["query_details"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "layout": "orthogonal_wall_maze_with_boundary_exit_labels",
                "wall_stroke_width_px": int(render_params.wall_stroke_width_px),
                "outer_wall_stroke_width_px": int(render_params.outer_wall_stroke_width_px),
                "exit_marker_radius_px": int(render_params.exit_marker_radius_px),
                "exit_marker_shape": str(render_params.exit_marker_shape),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "item_bboxes_px": {str(key): list(value) for key, value in rounded_item_bbox_map.items()},
                "cell_bboxes_px": {str(key): list(value) for key, value in rounded_cell_bbox_map.items()},
                "evidence_source": str(supporting_evidence_source),
            }, render_params.unit_size_jitter),
            "execution_trace": {
                "query_variant": str(query_variant),
                "target_reachability": str(target_reachability) if target_reachability is not None else None,
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "topology_rule": str(dataset["topology_rule"]),
                "maze_rows": int(dataset["maze_rows"]),
                "maze_cols": int(dataset["maze_cols"]),
                "maze_rows_range": list(dataset["maze_rows_range"]),
                "maze_cols_range": list(dataset["maze_cols_range"]),
                "start_cell": list(dataset["start_cell"]),
                "open_edges": list(dataset["open_edges"]),
                "exits": [dict(exit_spec) for exit_spec in dataset["exits"]],
                "exit_count": int(dataset["exit_count"]),
                "exit_count_range": list(dataset["exit_count_range"]),
                "reachable_exit_count": int(dataset["reachable_exit_count"]),
                "reachable_exit_count_range": list(dataset["reachable_exit_count_range"]),
                "reachable_exit_labels": [str(value) for value in dataset["reachable_exit_labels"]],
                "unreachable_exit_labels": [str(value) for value in dataset["unreachable_exit_labels"]],
                "answer_value": answer_value,
                "supporting_item_ids": list(supporting_item_ids),
                "supporting_evidence_source": str(supporting_evidence_source),
                "evidence_policy": str(dataset["evidence_policy"]),
                "query_variant_probabilities": dict(query_variant_probabilities),
                "target_reachability_probabilities": dict(target_reachability_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "query_details": dict(dataset["query_details"]),
                "solver_trace": dict(dataset["solver_trace"]),
            },
            "witness_symbolic": {
                "type": str(witness_type),
                "value": list(witness_value),
                "ordered_item_ids": list(supporting_item_ids),
            },
            "projected_evidence": dict(evidence_projection),
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
            "complexity": complexity.to_dict(),
        }

        if str(query_variant) == "exit_reachability_label" and str(target_reachability) == "reachable" and str(answer_value) not in set(map(str, dataset["reachable_exit_labels"])):
            raise ValueError("reachable-exit label answer drifted from reachable exits")
        if str(query_variant) == "exit_reachability_label" and str(target_reachability) == "unreachable" and str(answer_value) not in set(map(str, dataset["unreachable_exit_labels"])):
            raise ValueError("unreachable-exit label answer drifted from unreachable exits")
        if str(query_variant) == "reachable_exit_count" and int(answer_value) != int(len(dataset["reachable_exit_labels"])):
            raise ValueError("reachable-exit count answer drifted from reachable exits")
        if not (0.0 <= float(complexity.complexity_score) <= 1.0):
            raise ValueError("maze-exit complexity score is outside [0, 1]")
        _ = clamp_unit_interval(float(complexity.complexity_score))

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesTopologyMazeExitReachabilityLabelTask(_PuzzlesTopologyMazeExitBaseTask):
    """Return a reachable or unreachable labeled exit in a wall maze."""

    task_id = MAZE_EXIT_REACHABILITY_LABEL_TASK_ID
    supported_query_variants = ("exit_reachability_label",)

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        output = super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts))
        return rewrite_fixed_puzzle_query_output(
            output,
            query_id=str(output.query_variant),
            scene_id=SCENE_ID,
        )


@register_task
class PuzzlesTopologyMazeReachableExitCountTask(_PuzzlesTopologyMazeExitBaseTask):
    """Count reachable exits in a wall maze."""

    task_id = MAZE_REACHABLE_EXIT_COUNT_TASK_ID
    supported_query_variants = ("reachable_exit_count",)

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        output = super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts))
        return rewrite_fixed_puzzle_query_output(
            output,
            query_id=str(output.query_variant),
            scene_id=SCENE_ID,
        )


__all__ = [
    "PuzzlesTopologyMazeExitReachabilityLabelTask",
    "PuzzlesTopologyMazeReachableExitCountTask",
]
