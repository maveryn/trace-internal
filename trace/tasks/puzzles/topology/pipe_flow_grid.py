"""Pipe-flow repair puzzle on an oriented tile grid."""

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
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import load_font
from ..shared.common import projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import build_puzzle_complexity, clamp_unit_interval, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


TASK_ID = "task_puzzles__pipe_flow__pipe_flow_repair_tile_label"
SCENE_ID = "pipe_flow"
QUERY_ID = "flow_repair_tile_label"

_GRID_SIZE_VARIANTS: Tuple[str, ...] = ("6x6", "7x7", "8x8", "9x9", "10x10")
_SCENE_VARIANTS: Tuple[str, ...] = ("water_pipe", "circuit_trace", "industrial_conduit")
_LABEL_POOL = tuple("ABCDEF")
_DIRECTIONS: Tuple[str, ...] = ("N", "E", "S", "W")
_DELTAS = {
    "N": (-1, 0),
    "E": (0, 1),
    "S": (1, 0),
    "W": (0, -1),
}
_OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
_ROTATE_CW = {"N": "E", "E": "S", "S": "W", "W": "N"}
_SCENE_LOAD = {
    "water_pipe": 0.20,
    "circuit_trace": 0.28,
    "industrial_conduit": 0.32,
}

Cell = Tuple[int, int]
Openings = Tuple[str, ...]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderParams:
    """Resolved pipe-grid render parameters."""

    canvas_width: int
    canvas_height: int
    scene_margin_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    cell_gap_px: int
    cell_border_width_px: int
    pipe_width_px: int
    source_dest_font_size_px: int
    tile_label_font_size_px: int
    panel_fill_rgb: Color
    cell_fill_rgb: Color
    grid_line_rgb: Color
    pipe_rgb: Color
    pipe_shadow_rgb: Color
    source_fill_rgb: Color
    source_outline_rgb: Color
    dest_fill_rgb: Color
    dest_outline_rgb: Color
    label_fill_rgb: Color
    label_text_rgb: Color
    text_stroke_rgb: Color
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class _TileSpec:
    """One pipe-grid tile."""

    tile_id: str
    row: int
    col: int
    required_openings: Openings
    current_openings: Openings
    is_path: bool
    is_branch: bool
    label: str


@dataclass(frozen=True)
class _OptionSpec:
    """One labeled 2x2 replacement piece option."""

    option_id: str
    label: str
    local_openings: Tuple[Tuple[int, int, Openings], ...]
    is_correct: bool
    connects_after_rotation_turns: Tuple[int, ...]
    display_rotation_turns: int


@dataclass(frozen=True)
class _Dataset:
    """One sampled pipe-flow repair puzzle."""

    rows: int
    cols: int
    grid_size_variant: str
    scene_variant: str
    path_cells: Tuple[Cell, ...]
    branch_cells: Tuple[Cell, ...]
    branch_terminal_cells: Tuple[Cell, ...]
    start_cell: Cell
    destination_cell: Cell
    missing_origin: Cell
    missing_cells: Tuple[Cell, ...]
    missing_region_id: str
    correct_option_panel_id: str
    answer_label: str
    candidate_count: int
    tiles: Tuple[_TileSpec, ...]
    options: Tuple[_OptionSpec, ...]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered pipe-grid scene plus projection maps."""

    image: Image.Image
    scene_bbox_px: BBox
    tile_bbox_map: Dict[str, BBox]
    item_bbox_map: Dict[str, BBox]
    entities: Tuple[Dict[str, Any], ...]


@dataclass(frozen=True)
class _Defaults:
    """Fallback defaults for the pipe-flow scene."""

    grid_size_min: int = 6
    grid_size_max: int = 10
    path_length_min: int = 10
    path_length_max: int = 24
    candidate_count_min: int = 6
    candidate_count_max: int = 6
    branch_count_min: int = 2
    branch_count_max: int = 5
    branch_length_min: int = 2
    branch_length_max: int = 4
    canvas_width: int = 1120
    canvas_height: int = 900
    scene_margin_px: int = 72
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 22
    panel_border_width_px: int = 3
    cell_gap_px: int = 3
    cell_border_width_px: int = 2
    pipe_width_px: int = 12
    source_dest_font_size_px: int = 15
    tile_label_font_size_px: int = 18
    panel_fill_rgb: Color = (248, 250, 252)
    cell_fill_rgb: Color = (255, 255, 255)
    grid_line_rgb: Color = (196, 203, 215)
    pipe_rgb: Color = (57, 143, 205)
    pipe_shadow_rgb: Color = (224, 232, 242)
    source_fill_rgb: Color = (203, 238, 224)
    source_outline_rgb: Color = (41, 120, 83)
    dest_fill_rgb: Color = (251, 229, 177)
    dest_outline_rgb: Color = (164, 107, 28)
    label_fill_rgb: Color = (35, 42, 54)
    label_text_rgb: Color = (255, 255, 255)
    text_stroke_rgb: Color = (255, 255, 255)


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "topology")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="topology", apply_prob=0.0)


def _to_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def _rgb(value: Any, fallback: Color) -> Color:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (
            max(0, min(255, _to_int(value[0], fallback[0]))),
            max(0, min(255, _to_int(value[1], fallback[1]))),
            max(0, min(255, _to_int(value[2], fallback[2]))),
        )
    return tuple(int(channel) for channel in fallback)


def _rgb_option(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: Color,
    *,
    seed: int,
) -> Color:
    options = params.get(f"{key}_options", group_default(defaults, f"{key}_options", None))
    if isinstance(options, list) and options:
        rng = spawn_rng(int(seed), f"{TASK_ID}.render.{key}")
        return _rgb(options[int(rng.randrange(len(options)))], fallback)
    return _rgb(params.get(str(key), group_default(defaults, str(key), fallback)), fallback)


def _resolve_render_params(params: Mapping[str, Any], render_defaults: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.pipe_flow.unit_size",
    )
    return _RenderParams(
        canvas_width=max(760, _to_int(params.get("canvas_width", group_default(render_defaults, "canvas_width", _DEFAULTS.canvas_width)), _DEFAULTS.canvas_width)),
        canvas_height=max(640, _to_int(params.get("canvas_height", group_default(render_defaults, "canvas_height", _DEFAULTS.canvas_height)), _DEFAULTS.canvas_height)),
        scene_margin_px=max(48, scale_puzzle_px(_to_int(params.get("scene_margin_px", group_default(render_defaults, "scene_margin_px", _DEFAULTS.scene_margin_px)), _DEFAULTS.scene_margin_px), unit_scale, min_px=36)),
        panel_padding_px=max(12, scale_puzzle_px(_to_int(params.get("panel_padding_px", group_default(render_defaults, "panel_padding_px", _DEFAULTS.panel_padding_px)), _DEFAULTS.panel_padding_px), unit_scale, min_px=12)),
        panel_corner_radius_px=max(0, scale_puzzle_px(_to_int(params.get("panel_corner_radius_px", group_default(render_defaults, "panel_corner_radius_px", _DEFAULTS.panel_corner_radius_px)), _DEFAULTS.panel_corner_radius_px), unit_scale, min_px=8)),
        panel_border_width_px=max(1, scale_puzzle_px(_to_int(params.get("panel_border_width_px", group_default(render_defaults, "panel_border_width_px", _DEFAULTS.panel_border_width_px)), _DEFAULTS.panel_border_width_px), unit_scale, min_px=1)),
        cell_gap_px=max(0, scale_puzzle_px(_to_int(params.get("cell_gap_px", group_default(render_defaults, "cell_gap_px", _DEFAULTS.cell_gap_px)), _DEFAULTS.cell_gap_px), unit_scale, min_px=2)),
        cell_border_width_px=max(1, scale_puzzle_px(_to_int(params.get("cell_border_width_px", group_default(render_defaults, "cell_border_width_px", _DEFAULTS.cell_border_width_px)), _DEFAULTS.cell_border_width_px), unit_scale, min_px=1)),
        pipe_width_px=max(8, scale_puzzle_px(_to_int(params.get("pipe_width_px", group_default(render_defaults, "pipe_width_px", _DEFAULTS.pipe_width_px)), _DEFAULTS.pipe_width_px), unit_scale, min_px=8)),
        source_dest_font_size_px=max(12, scale_puzzle_px(_to_int(params.get("source_dest_font_size_px", group_default(render_defaults, "source_dest_font_size_px", _DEFAULTS.source_dest_font_size_px)), _DEFAULTS.source_dest_font_size_px), unit_scale, min_px=12)),
        tile_label_font_size_px=max(12, scale_puzzle_px(_to_int(params.get("tile_label_font_size_px", group_default(render_defaults, "tile_label_font_size_px", _DEFAULTS.tile_label_font_size_px)), _DEFAULTS.tile_label_font_size_px), unit_scale, min_px=12)),
        panel_fill_rgb=_rgb_option(params, render_defaults, "panel_fill_rgb", _DEFAULTS.panel_fill_rgb, seed=int(instance_seed)),
        cell_fill_rgb=_rgb_option(params, render_defaults, "cell_fill_rgb", _DEFAULTS.cell_fill_rgb, seed=int(instance_seed)),
        grid_line_rgb=_rgb_option(params, render_defaults, "grid_line_rgb", _DEFAULTS.grid_line_rgb, seed=int(instance_seed)),
        pipe_rgb=_rgb_option(params, render_defaults, "pipe_rgb", _DEFAULTS.pipe_rgb, seed=int(instance_seed)),
        pipe_shadow_rgb=_rgb_option(params, render_defaults, "pipe_shadow_rgb", _DEFAULTS.pipe_shadow_rgb, seed=int(instance_seed)),
        source_fill_rgb=_rgb_option(params, render_defaults, "source_fill_rgb", _DEFAULTS.source_fill_rgb, seed=int(instance_seed)),
        source_outline_rgb=_rgb_option(params, render_defaults, "source_outline_rgb", _DEFAULTS.source_outline_rgb, seed=int(instance_seed)),
        dest_fill_rgb=_rgb_option(params, render_defaults, "dest_fill_rgb", _DEFAULTS.dest_fill_rgb, seed=int(instance_seed)),
        dest_outline_rgb=_rgb_option(params, render_defaults, "dest_outline_rgb", _DEFAULTS.dest_outline_rgb, seed=int(instance_seed)),
        label_fill_rgb=_rgb_option(params, render_defaults, "label_fill_rgb", _DEFAULTS.label_fill_rgb, seed=int(instance_seed)),
        label_text_rgb=_rgb_option(params, render_defaults, "label_text_rgb", _DEFAULTS.label_text_rgb, seed=int(instance_seed)),
        text_stroke_rgb=_rgb_option(params, render_defaults, "text_stroke_rgb", _DEFAULTS.text_stroke_rgb, seed=int(instance_seed)),
        unit_size_jitter=dict(unit_meta),
    )


def _parse_grid_size_variant(value: str) -> Tuple[int, int]:
    if str(value) not in _GRID_SIZE_VARIANTS:
        raise ValueError(f"unsupported grid_size_variant: {value}")
    raw_rows, raw_cols = str(value).split("x", maxsplit=1)
    return int(raw_rows), int(raw_cols)


def _normalize_openings(openings: Iterable[str]) -> Openings:
    present = {str(direction) for direction in openings if str(direction) in set(_DIRECTIONS)}
    return tuple(direction for direction in _DIRECTIONS if direction in present)


def _rotate_openings(openings: Iterable[str], turns: int = 1) -> Openings:
    result = [str(direction) for direction in openings]
    for _ in range(int(turns) % 4):
        result = [_ROTATE_CW[direction] for direction in result]
    return _normalize_openings(result)


def _cell_add(cell: Cell, direction: str) -> Cell:
    dr, dc = _DELTAS[str(direction)]
    return (int(cell[0] + dr), int(cell[1] + dc))


def _direction_between(left: Cell, right: Cell) -> str:
    dr = int(right[0] - left[0])
    dc = int(right[1] - left[1])
    for direction, delta in _DELTAS.items():
        if tuple(delta) == (dr, dc):
            return str(direction)
    raise ValueError(f"cells are not orthogonal neighbors: {left} -> {right}")


def _path_openings(path: Sequence[Cell]) -> Dict[Cell, Openings]:
    openings: Dict[Cell, set[str]] = {tuple(cell): set() for cell in path}
    for index, cell in enumerate(path):
        cell = tuple(cell)
        if index > 0:
            direction = _direction_between(cell, tuple(path[index - 1]))
            openings[cell].add(direction)
        if index < len(path) - 1:
            direction = _direction_between(cell, tuple(path[index + 1]))
            openings[cell].add(direction)
    return {cell: _normalize_openings(value) for cell, value in openings.items()}


def _find_path(rng, *, rows: int, cols: int, min_length: int, max_length: int) -> Tuple[Cell, ...]:
    """Sample a simple start-marker-to-finish-flag path across the grid."""

    for _ in range(260):
        start = (int(rng.randrange(int(rows))), 0)
        goal = (int(rng.randrange(int(rows))), int(cols - 1))
        stack: List[Tuple[Cell, List[Cell], set[Cell]]] = [(start, [start], {start})]
        step_limit = max(1, int(rows * cols * 8))
        while stack and step_limit > 0:
            step_limit -= 1
            cell, path, visited = stack.pop()
            if cell == goal and int(min_length) <= len(path) <= int(max_length):
                return tuple(path)
            if len(path) >= int(max_length):
                continue
            directions = list(_DIRECTIONS)
            rng.shuffle(directions)
            directions.sort(key=lambda d: 0 if (d == "E" and cell[1] < goal[1]) else (1 if d in {"N", "S"} else 2))
            for direction in directions:
                nxt = _cell_add(cell, direction)
                if not (0 <= nxt[0] < int(rows) and 0 <= nxt[1] < int(cols)):
                    continue
                if nxt in visited:
                    continue
                if nxt[1] < cell[1] - 1:
                    continue
                new_path = [*path, nxt]
                remaining_min = abs(int(goal[0] - nxt[0])) + abs(int(goal[1] - nxt[1]))
                if len(new_path) + remaining_min > int(max_length):
                    continue
                stack.append((nxt, new_path, {*visited, nxt}))
    raise RuntimeError("failed to sample pipe-flow path")


def _connected_to_destination(tile_map: Mapping[Cell, Openings], *, rows: int, cols: int, start_cell: Cell, destination_cell: Cell) -> bool:
    """Return whether the start marker reaches the finish flag through matching tile openings."""

    seen = {tuple(start_cell)}
    frontier = [tuple(start_cell)]
    while frontier:
        cell = frontier.pop()
        if cell == tuple(destination_cell):
            return True
        for direction in tile_map.get(cell, ()):
            nxt = _cell_add(cell, direction)
            if not (0 <= nxt[0] < int(rows) and 0 <= nxt[1] < int(cols)):
                continue
            if _OPPOSITE[direction] not in set(tile_map.get(nxt, ())):
                continue
            if nxt in seen:
                continue
            seen.add(nxt)
            frontier.append(nxt)
    return False


def _block_cells(origin: Cell) -> Tuple[Cell, ...]:
    """Return the four global cells covered by a 2x2 missing piece."""

    row, col = int(origin[0]), int(origin[1])
    return ((row, col), (row, col + 1), (row + 1, col), (row + 1, col + 1))


def _local_cells() -> Tuple[Cell, ...]:
    return ((0, 0), (0, 1), (1, 0), (1, 1))


def _select_missing_origin(path: Sequence[Cell], *, rows: int, cols: int, rng) -> Cell:
    """Choose an interior 2x2 block that a contiguous path segment passes through."""

    candidates: List[Tuple[int, Cell]] = []
    indexed_path = {tuple(cell): index for index, cell in enumerate(path)}
    for row in range(1, max(1, int(rows) - 2)):
        for col in range(1, max(1, int(cols) - 2)):
            origin = (int(row), int(col))
            block = set(_block_cells(origin))
            inside_indices = sorted(indexed_path[cell] for cell in block if cell in indexed_path)
            if len(inside_indices) < 2:
                continue
            if inside_indices[-1] - inside_indices[0] + 1 != len(inside_indices):
                continue
            if inside_indices[0] <= 0 or inside_indices[-1] >= len(path) - 1:
                continue
            if tuple(path[inside_indices[0] - 1]) in block or tuple(path[inside_indices[-1] + 1]) in block:
                continue
            candidates.append((len(inside_indices), origin))
    if not candidates:
        raise RuntimeError("failed to choose a 2x2 pipe-flow missing block")
    max_inside = max(score for score, _origin in candidates)
    preferred = [origin for score, origin in candidates if int(score) == int(max_inside)]
    return tuple(preferred[int(rng.randrange(len(preferred)))])


def _add_opening(openings_by_cell: Dict[Cell, set[str]], left: Cell, right: Cell) -> None:
    """Add a bidirectional pipe connection between adjacent cells."""

    direction = _direction_between(tuple(left), tuple(right))
    openings_by_cell.setdefault(tuple(left), set()).add(direction)
    openings_by_cell.setdefault(tuple(right), set()).add(_OPPOSITE[direction])


def _is_boundary_cell(cell: Cell, *, rows: int, cols: int) -> bool:
    row, col = int(cell[0]), int(cell[1])
    return row == 0 or row == int(rows) - 1 or col == 0 or col == int(cols) - 1


def _boundary_distance(cell: Cell, *, rows: int, cols: int) -> int:
    row, col = int(cell[0]), int(cell[1])
    return min(row, int(rows) - 1 - row, col, int(cols) - 1 - col)


def _find_branch_path_to_side(
    *,
    anchor: Cell,
    occupied: set[Cell],
    rows: int,
    cols: int,
    min_length: int,
    max_length: int,
    rng,
) -> Tuple[Cell, ...] | None:
    """Find an offshoot path from a main-path anchor to any grid side."""

    anchor = tuple(anchor)
    stack: List[Tuple[Cell, List[Cell], set[Cell]]] = [(anchor, [], {anchor})]
    step_limit = max(1, int(rows * cols * 10))
    while stack and step_limit > 0:
        step_limit -= 1
        cell, branch_path, visited = stack.pop()
        if branch_path and len(branch_path) >= int(min_length) and _is_boundary_cell(branch_path[-1], rows=int(rows), cols=int(cols)):
            return tuple(branch_path)
        if len(branch_path) >= int(max_length):
            continue
        directions = list(_DIRECTIONS)
        rng.shuffle(directions)
        directions.sort(key=lambda direction: _boundary_distance(_cell_add(cell, direction), rows=int(rows), cols=int(cols)))
        for direction in directions:
            nxt = _cell_add(cell, direction)
            if not (0 <= nxt[0] < int(rows) and 0 <= nxt[1] < int(cols)):
                continue
            if nxt in occupied or nxt in visited:
                continue
            stack.append((nxt, [*branch_path, nxt], {*visited, nxt}))
    return None


def _add_branch_paths(
    openings_by_cell: Dict[Cell, set[str]],
    *,
    path: Sequence[Cell],
    missing_cells: set[Cell],
    rows: int,
    cols: int,
    branch_count: int,
    branch_length_min: int,
    branch_length_max: int,
    rng,
) -> Tuple[Tuple[Cell, ...], Tuple[Cell, ...]]:
    """Attach visible offshoots to the main path, each terminating on a grid side."""

    occupied = {tuple(cell) for cell in path} | set(missing_cells)
    branch_cells: set[Cell] = set()
    branch_terminals: List[Cell] = []
    anchors = [tuple(cell) for cell in path[1:-1] if tuple(cell) not in missing_cells]
    for _ in range(max(0, int(branch_count))):
        rng.shuffle(anchors)
        started = False
        for anchor in anchors:
            max_length = max(int(branch_length_max), int(min(rows, cols) - 1))
            branch_path = _find_branch_path_to_side(
                anchor=anchor,
                occupied=set(occupied),
                rows=int(rows),
                cols=int(cols),
                min_length=max(1, int(branch_length_min)),
                max_length=max(1, int(max_length)),
                rng=rng,
            )
            if not branch_path:
                continue
            prev = anchor
            for current in branch_path:
                current = tuple(current)
                if current in occupied:
                    break
                _add_opening(openings_by_cell, tuple(prev), current)
                occupied.add(current)
                branch_cells.add(current)
                prev = current
            else:
                branch_terminals.append(tuple(branch_path[-1]))
                started = True
            break
        if not started:
            break
    return tuple(sorted(branch_cells)), tuple(branch_terminals)


def _localize_block(global_openings: Mapping[Cell, Openings], *, origin: Cell) -> Dict[Cell, Openings]:
    """Convert global 2x2 block openings into local 0/1 cell coordinates."""

    origin_row, origin_col = int(origin[0]), int(origin[1])
    localized: Dict[Cell, Openings] = {}
    for row, col in _local_cells():
        global_cell = (int(origin_row + row), int(origin_col + col))
        localized[(int(row), int(col))] = _normalize_openings(global_openings.get(global_cell, ()))
    return localized


def _globalize_block(local_openings: Mapping[Cell, Openings], *, origin: Cell) -> Dict[Cell, Openings]:
    """Convert a local 2x2 option piece into global grid-cell openings."""

    origin_row, origin_col = int(origin[0]), int(origin[1])
    return {
        (int(origin_row + row), int(origin_col + col)): _normalize_openings(local_openings.get((row, col), ()))
        for row, col in _local_cells()
    }


def _option_signature(local_openings: Mapping[Cell, Openings]) -> Tuple[Tuple[int, int, Openings], ...]:
    return tuple(
        (int(row), int(col), _normalize_openings(local_openings.get((row, col), ())))
        for row, col in _local_cells()
    )


def _rotation_canonical_option_signature(local_openings: Mapping[Cell, Openings]) -> Tuple[Tuple[int, int, Openings], ...]:
    """Return a canonical signature treating quarter-turn rotations as equivalent."""

    return min(
        _option_signature(_rotate_local_option(local_openings, turns=turns))
        for turns in range(4)
    )


def _rotate_local_option(local_openings: Mapping[Cell, Openings], *, turns: int) -> Dict[Cell, Openings]:
    """Rotate a 2x2 option piece clockwise by the requested number of quarter-turns."""

    result = {cell: _normalize_openings(local_openings.get(cell, ())) for cell in _local_cells()}
    for _ in range(int(turns) % 4):
        rotated: Dict[Cell, Openings] = {cell: tuple() for cell in _local_cells()}
        for (row, col), openings in result.items():
            next_cell = (int(col), int(1 - row))
            rotated[next_cell] = _rotate_openings(openings, 1)
        result = rotated
    return result


def _random_local_option(rng) -> Dict[Cell, Openings]:
    """Build one internally consistent random 2x2 pipe option."""

    openings: Dict[Cell, set[str]] = {cell: set() for cell in _local_cells()}
    internal_edges = (
        ((0, 0), "E", (0, 1), "W"),
        ((1, 0), "E", (1, 1), "W"),
        ((0, 0), "S", (1, 0), "N"),
        ((0, 1), "S", (1, 1), "N"),
    )
    for left, left_dir, right, right_dir in internal_edges:
        if rng.random() < 0.46:
            openings[left].add(left_dir)
            openings[right].add(right_dir)
    boundary_stubs = (
        ((0, 0), "N"), ((0, 1), "N"),
        ((1, 0), "S"), ((1, 1), "S"),
        ((0, 0), "W"), ((1, 0), "W"),
        ((0, 1), "E"), ((1, 1), "E"),
    )
    stubs = list(boundary_stubs)
    rng.shuffle(stubs)
    for cell, direction in stubs[: int(rng.randint(2, 5))]:
        openings[cell].add(direction)
    if sum(1 for value in openings.values() if value) < 2:
        cell, direction = stubs[-1]
        openings[cell].add(direction)
    return {cell: _normalize_openings(value) for cell, value in openings.items()}


def _option_connects(
    *,
    visible_map: Mapping[Cell, Openings],
    local_openings: Mapping[Cell, Openings],
    origin: Cell,
    rows: int,
    cols: int,
    start_cell: Cell,
    destination_cell: Cell,
) -> bool:
    test_map = {tuple(cell): _normalize_openings(openings) for cell, openings in visible_map.items()}
    test_map.update(_globalize_block(local_openings, origin=origin))
    return _connected_to_destination(
        test_map,
        rows=int(rows),
        cols=int(cols),
        start_cell=tuple(start_cell),
        destination_cell=tuple(destination_cell),
    )


def _option_connecting_rotation_turns(
    *,
    visible_map: Mapping[Cell, Openings],
    local_openings: Mapping[Cell, Openings],
    origin: Cell,
    rows: int,
    cols: int,
    start_cell: Cell,
    destination_cell: Cell,
) -> Tuple[int, ...]:
    """Return all clockwise rotations that make a displayed option solve the path."""

    turns: List[int] = []
    for turn_count in range(4):
        rotated = _rotate_local_option(local_openings, turns=int(turn_count))
        if _option_connects(
            visible_map=visible_map,
            local_openings=rotated,
            origin=origin,
            rows=int(rows),
            cols=int(cols),
            start_cell=start_cell,
            destination_cell=destination_cell,
        ):
            turns.append(int(turn_count))
    return tuple(turns)


def _build_option_specs(
    *,
    correct_local_openings: Mapping[Cell, Openings],
    visible_map: Mapping[Cell, Openings],
    origin: Cell,
    rows: int,
    cols: int,
    start_cell: Cell,
    destination_cell: Cell,
    answer_label_index: int,
    rng,
) -> Tuple[_OptionSpec, ...]:
    """Create one rotatable correct 2x2 option and five genuinely distinct distractors."""

    labels = tuple(_LABEL_POOL)
    correct_display_turns = int(rng.randrange(4))
    correct_display_openings = _rotate_local_option(correct_local_openings, turns=correct_display_turns)
    correct_signature = _rotation_canonical_option_signature(correct_display_openings)
    correct_connecting_turns = _option_connecting_rotation_turns(
        visible_map=visible_map,
        local_openings=correct_display_openings,
        origin=origin,
        rows=int(rows),
        cols=int(cols),
        start_cell=start_cell,
        destination_cell=destination_cell,
    )
    if not correct_connecting_turns:
        raise RuntimeError("displayed correct pipe-flow option is not solvable under rotation")
    distractors: List[Dict[Cell, Openings]] = []
    seen = {correct_signature}

    def maybe_add(candidate: Mapping[Cell, Openings]) -> None:
        normalized = {cell: _normalize_openings(candidate.get(cell, ())) for cell in _local_cells()}
        signature = _rotation_canonical_option_signature(normalized)
        if signature in seen:
            return
        if _option_connecting_rotation_turns(
            visible_map=visible_map,
            local_openings=normalized,
            origin=origin,
            rows=int(rows),
            cols=int(cols),
            start_cell=start_cell,
            destination_cell=destination_cell,
        ):
            return
        seen.add(signature)
        distractors.append(normalized)

    for _ in range(1200):
        if len(distractors) >= len(labels) - 1:
            break
        maybe_add(_random_local_option(rng))
    if len(distractors) < len(labels) - 1:
        raise RuntimeError("failed to build enough pipe-flow option distractors")

    options: List[_OptionSpec] = []
    distractor_iter = iter(distractors)
    for option_index, label in enumerate(labels):
        is_correct = bool(option_index == int(answer_label_index))
        local_openings = (
            {cell: _normalize_openings(correct_display_openings.get(cell, ())) for cell in _local_cells()}
            if is_correct
            else next(distractor_iter)
        )
        connecting_turns = (
            correct_connecting_turns
            if is_correct
            else _option_connecting_rotation_turns(
                visible_map=visible_map,
                local_openings=local_openings,
                origin=origin,
                rows=int(rows),
                cols=int(cols),
                start_cell=start_cell,
                destination_cell=destination_cell,
            )
        )
        if bool(is_correct) != bool(connecting_turns):
            raise RuntimeError("pipe-flow option uniqueness check failed")
        options.append(
            _OptionSpec(
                option_id=f"option_panel_{int(option_index + 1)}",
                label=str(label),
                local_openings=_option_signature(local_openings),
                is_correct=is_correct,
                connects_after_rotation_turns=tuple(int(value) for value in connecting_turns),
                display_rotation_turns=int(correct_display_turns if is_correct else 0),
            )
        )
    return tuple(options)


def _resolve_axis_variant(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    supported_variants: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=tuple(str(value) for value in supported_variants),
        task_id=TASK_ID,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        axis_namespace=str(axis_namespace),
    )


def _build_dataset(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any], instance_seed: int) -> _Dataset:
    grid_size_variant, _grid_probs = _resolve_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=_GRID_SIZE_VARIANTS,
        explicit_key="grid_size_variant",
        weights_key="grid_size_variant_weights",
        balance_flag_key="balanced_grid_size_variant_sampling",
        axis_namespace="grid_size_variant",
    )
    scene_variant, _scene_probs = _resolve_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )
    rows, cols = _parse_grid_size_variant(str(grid_size_variant))
    path_min, path_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="path_length_min",
        max_key="path_length_max",
        fallback_min=_DEFAULTS.path_length_min,
        fallback_max=_DEFAULTS.path_length_max,
        context=f"{TASK_ID} path length",
    )
    candidate_min, candidate_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="candidate_count_min",
        max_key="candidate_count_max",
        fallback_min=_DEFAULTS.candidate_count_min,
        fallback_max=_DEFAULTS.candidate_count_max,
        context=f"{TASK_ID} candidate count",
    )
    branch_min, branch_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="branch_count_min",
        max_key="branch_count_max",
        fallback_min=_DEFAULTS.branch_count_min,
        fallback_max=_DEFAULTS.branch_count_max,
        context=f"{TASK_ID} branch count",
    )
    branch_length_min, branch_length_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="branch_length_min",
        max_key="branch_length_max",
        fallback_min=_DEFAULTS.branch_length_min,
        fallback_max=_DEFAULTS.branch_length_max,
        context=f"{TASK_ID} branch length",
    )
    candidate_min = max(6, min(len(_LABEL_POOL), int(candidate_min)))
    candidate_max = max(candidate_min, min(len(_LABEL_POOL), int(candidate_max)))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")

    for _ in range(180):
        candidate_count = int(rng.randint(int(candidate_min), int(candidate_max)))
        candidate_labels = tuple(_LABEL_POOL[index] for index in range(candidate_count))
        explicit_label = str(params.get("answer_label", "") or "").strip().upper()
        if explicit_label:
            if explicit_label not in candidate_labels:
                raise ValueError(f"answer_label {explicit_label!r} outside candidate labels for candidate_count={candidate_count}")
            answer_label_index = int(candidate_labels.index(explicit_label))
        else:
            answer_label_index = int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}:answer_label:{candidate_count}",
                )
                % candidate_count
            )
        answer_label = str(candidate_labels[int(answer_label_index)])
        path = _find_path(
            rng,
            rows=int(rows),
            cols=int(cols),
            min_length=max(8, int(path_min)),
            max_length=min(int(rows * cols), int(path_max)),
        )
        if len(path) < 8:
            continue
        try:
            missing_origin = _select_missing_origin(path, rows=int(rows), cols=int(cols), rng=rng)
        except RuntimeError:
            continue
        missing_cells = set(_block_cells(missing_origin))
        path_openings = _path_openings(path)
        full_openings: Dict[Cell, set[str]] = {
            tuple(cell): set(openings)
            for cell, openings in path_openings.items()
        }
        branch_count = int(rng.randint(int(branch_min), int(branch_max)))
        branch_cells, branch_terminal_cells = _add_branch_paths(
            full_openings,
            path=path,
            missing_cells=set(missing_cells),
            rows=int(rows),
            cols=int(cols),
            branch_count=int(branch_count),
            branch_length_min=int(branch_length_min),
            branch_length_max=int(branch_length_max),
            rng=rng,
        )
        if len(branch_terminal_cells) < max(1, min(int(branch_count), int(branch_min))):
            continue
        full_map: Dict[Cell, Openings] = {
            tuple(cell): _normalize_openings(openings)
            for cell, openings in full_openings.items()
            if openings
        }
        visible_map = {
            tuple(cell): tuple(openings)
            for cell, openings in full_map.items()
            if tuple(cell) not in missing_cells
        }
        if _connected_to_destination(visible_map, rows=rows, cols=cols, start_cell=path[0], destination_cell=path[-1]):
            continue
        correct_local_openings = _localize_block(full_map, origin=missing_origin)
        if not _option_connects(
            visible_map=visible_map,
            local_openings=correct_local_openings,
            origin=missing_origin,
            rows=int(rows),
            cols=int(cols),
            start_cell=path[0],
            destination_cell=path[-1],
        ):
            continue
        try:
            options = _build_option_specs(
                correct_local_openings=correct_local_openings,
                visible_map=visible_map,
                origin=missing_origin,
                rows=int(rows),
                cols=int(cols),
                start_cell=path[0],
                destination_cell=path[-1],
                answer_label_index=int(answer_label_index),
                rng=rng,
            )
        except RuntimeError:
            continue

        tiles: List[_TileSpec] = []
        path_set = set(path)
        branch_set = set(branch_cells)
        for cell in sorted(visible_map):
            required = path_openings.get(cell, tuple())
            current = visible_map[cell]
            tiles.append(
                _TileSpec(
                    tile_id=f"tile_r{cell[0]}c{cell[1]}",
                    row=int(cell[0]),
                    col=int(cell[1]),
                    required_openings=tuple(required),
                    current_openings=tuple(current),
                    is_path=bool(cell in path_set),
                    is_branch=bool(cell in branch_set),
                    label="",
                )
            )
        correct_option = next(option for option in options if option.is_correct)
        return _Dataset(
            rows=int(rows),
            cols=int(cols),
            grid_size_variant=str(grid_size_variant),
            scene_variant=str(scene_variant),
            path_cells=tuple(path),
            branch_cells=tuple(branch_cells),
            branch_terminal_cells=tuple(branch_terminal_cells),
            start_cell=tuple(path[0]),
            destination_cell=tuple(path[-1]),
            missing_origin=tuple(missing_origin),
            missing_cells=tuple(sorted(missing_cells)),
            missing_region_id="missing_region",
            correct_option_panel_id=str(correct_option.option_id),
            answer_label=str(answer_label),
            candidate_count=int(candidate_count),
            tiles=tuple(tiles),
            options=tuple(options),
        )
    raise RuntimeError("failed to construct unique pipe-flow option puzzle")


def _tile_bbox(*, row: int, col: int, grid_left: int, grid_top: int, cell_size: int, gap: int) -> Tuple[int, int, int, int]:
    x0 = int(grid_left + (int(col) * (int(cell_size) + int(gap))))
    y0 = int(grid_top + (int(row) * (int(cell_size) + int(gap))))
    return (x0, y0, int(x0 + cell_size), int(y0 + cell_size))


def _draw_pipe(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    openings: Openings,
    pipe_rgb: Color,
    shadow_rgb: Color,
    pipe_width: int,
    scene_variant: str,
) -> None:
    if not openings:
        return
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    edge_points = {
        "N": (cx, bbox[1]),
        "E": (bbox[2], cy),
        "S": (cx, bbox[3]),
        "W": (bbox[0], cy),
    }
    shadow_width = max(1, int(pipe_width) + 6)
    for direction in openings:
        draw.line([(cx, cy), edge_points[str(direction)]], fill=tuple(shadow_rgb), width=shadow_width)
    for direction in openings:
        draw.line([(cx, cy), edge_points[str(direction)]], fill=tuple(pipe_rgb), width=int(pipe_width))
    radius = max(5, int(pipe_width // 2))
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=tuple(pipe_rgb), outline=tuple(shadow_rgb), width=2)
    if str(scene_variant) == "circuit_trace":
        dot_radius = max(3, int(pipe_width // 4))
        draw.ellipse((cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius), fill=(255, 255, 255))


def _draw_label_chip(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    bbox: Tuple[int, int, int, int],
    render_params: _RenderParams,
) -> None:
    if not label:
        return
    chip = max(26, int(render_params.tile_label_font_size_px) + 12)
    chip_bbox = (int(bbox[0] + 7), int(bbox[1] + 7), int(bbox[0] + 7 + chip), int(bbox[1] + 7 + chip))
    draw.rounded_rectangle(chip_bbox, radius=8, fill=tuple(render_params.label_fill_rgb), outline=tuple(render_params.text_stroke_rgb), width=1)
    font = load_font(int(render_params.tile_label_font_size_px), bold=True)
    draw_centered_text(
        draw,
        text=str(label),
        center=((chip_bbox[0] + chip_bbox[2]) / 2.0, (chip_bbox[1] + chip_bbox[3]) / 2.0),
        font=font,
        fill=tuple(render_params.label_text_rgb),
        stroke_fill=tuple(render_params.label_fill_rgb),
        stroke_width=0,
    )


def _draw_start_marker(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    render_params: _RenderParams,
) -> Tuple[int, int, int, int]:
    """Draw a compact visual start marker without text."""

    cx = int((bbox[0] + bbox[2]) / 2)
    cy = int((bbox[1] + bbox[3]) / 2)
    cell_size = int(min(bbox[2] - bbox[0], bbox[3] - bbox[1]))
    radius = max(11, int(cell_size * 0.32))
    marker_bbox = (int(cx - radius), int(cy - radius), int(cx + radius), int(cy + radius))
    draw.ellipse(
        marker_bbox,
        fill=tuple(render_params.source_fill_rgb),
        outline=tuple(render_params.source_outline_rgb),
        width=max(2, int(render_params.cell_border_width_px + 1)),
    )
    triangle = [
        (int(cx - radius * 0.30), int(cy - radius * 0.54)),
        (int(cx - radius * 0.30), int(cy + radius * 0.54)),
        (int(cx + radius * 0.58), int(cy)),
    ]
    draw.polygon(triangle, fill=tuple(render_params.source_outline_rgb))
    return marker_bbox


def _draw_finish_flag(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    render_params: _RenderParams,
) -> Tuple[int, int, int, int]:
    """Draw a compact red triangular destination flag without text."""

    cell_size = int(min(bbox[2] - bbox[0], bbox[3] - bbox[1]))
    cx = int((bbox[0] + bbox[2]) / 2)
    cy = int((bbox[1] + bbox[3]) / 2)
    pole_h = max(26, int(cell_size * 0.74))
    pole_x = int(cx - cell_size * 0.22)
    pole_top = int(cy - pole_h * 0.50)
    pole_bottom = int(cy + pole_h * 0.50)
    flag_w = max(20, int(cell_size * 0.58))
    flag_h = max(16, int(cell_size * 0.42))
    marker_bbox = (
        int(pole_x - 4),
        int(pole_top - 4),
        int(pole_x + flag_w + 5),
        int(pole_bottom + 4),
    )
    flag_fill = (220, 57, 57)
    flag_outline = (132, 32, 32)
    draw.line([(pole_x, pole_top), (pole_x, pole_bottom)], fill=flag_outline, width=max(3, int(cell_size * 0.08)))
    triangle = [
        (int(pole_x), int(pole_top + 2)),
        (int(pole_x + flag_w), int(pole_top + flag_h * 0.48)),
        (int(pole_x), int(pole_top + flag_h)),
    ]
    draw.polygon(triangle, fill=flag_fill)
    draw.line([triangle[0], triangle[1], triangle[2], triangle[0]], fill=flag_outline, width=2)
    draw.ellipse(
        (pole_x - 4, pole_bottom - 4, pole_x + 4, pole_bottom + 4),
        fill=flag_outline,
    )
    return marker_bbox


def _option_opening_map(option: _OptionSpec) -> Dict[Cell, Openings]:
    return {
        (int(row), int(col)): _normalize_openings(openings)
        for row, col, openings in option.local_openings
    }


def _draw_option_panel(
    draw: ImageDraw.ImageDraw,
    *,
    option: _OptionSpec,
    panel_bbox: Tuple[int, int, int, int],
    render_params: _RenderParams,
    scene_variant: str,
) -> Tuple[Dict[str, Any], Dict[str, BBox]]:
    """Draw one 2x2 replacement-piece option panel."""

    draw_rounded_rect(
        draw,
        panel_bbox,
        radius=max(10, int(render_params.panel_corner_radius_px * 0.55)),
        fill=tuple(render_params.panel_fill_rgb),
        outline=tuple(render_params.grid_line_rgb),
        width=max(1, int(render_params.panel_border_width_px)),
    )
    _draw_label_chip(draw, label=str(option.label), bbox=panel_bbox, render_params=render_params)
    inner_left = int(panel_bbox[0] + 24)
    inner_top = int(panel_bbox[1] + 34)
    inner_right = int(panel_bbox[2] - 18)
    inner_bottom = int(panel_bbox[3] - 14)
    cell_gap = max(2, int(render_params.cell_gap_px))
    cell_size = int(min((inner_right - inner_left - cell_gap) / 2, (inner_bottom - inner_top - cell_gap) / 2))
    grid_left = int((panel_bbox[0] + panel_bbox[2] - (2 * cell_size + cell_gap)) / 2)
    grid_top = int(inner_top + max(0, (inner_bottom - inner_top - (2 * cell_size + cell_gap)) / 2))
    option_map = _option_opening_map(option)
    cell_bboxes: Dict[str, BBox] = {}
    for row, col in _local_cells():
        bbox = _tile_bbox(row=row, col=col, grid_left=grid_left, grid_top=grid_top, cell_size=cell_size, gap=cell_gap)
        draw.rounded_rectangle(
            bbox,
            radius=max(5, int(cell_size * 0.16)),
            fill=tuple(render_params.cell_fill_rgb),
            outline=tuple(render_params.grid_line_rgb),
            width=max(1, int(render_params.cell_border_width_px)),
        )
        _draw_pipe(
            draw,
            bbox=bbox,
            openings=option_map.get((row, col), tuple()),
            pipe_rgb=tuple(render_params.pipe_rgb),
            shadow_rgb=tuple(render_params.pipe_shadow_rgb),
            pipe_width=max(5, min(int(render_params.pipe_width_px), int(cell_size * 0.36))),
            scene_variant=str(scene_variant),
        )
        cell_bboxes[f"{option.option_id}_cell_{row}_{col}"] = tuple(float(value) for value in bbox)
    return (
        {
            "id": str(option.option_id),
            "type": "pipe_flow_option_panel",
            "label": str(option.label),
            "bbox_px": [int(value) for value in panel_bbox],
            "is_correct": bool(option.is_correct),
            "local_openings": [
                {"row": int(row), "col": int(col), "openings": list(openings)}
                for row, col, openings in option.local_openings
            ],
        },
        {str(option.option_id): tuple(float(value) for value in panel_bbox), **cell_bboxes},
    )


def _render_scene(
    *,
    background: Image.Image,
    dataset: _Dataset,
    render_params: _RenderParams,
) -> _RenderedScene:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    option_panel_width = 128
    option_panel_height = 128
    option_gap = 16
    option_cols = 2
    option_rows = 3
    option_width = int(option_cols * option_panel_width + (option_cols - 1) * option_gap)
    option_height = int(option_rows * option_panel_height + (option_rows - 1) * option_gap)
    board_option_gap = 38
    usable_width = int(render_params.canvas_width - (2 * render_params.scene_margin_px) - option_width - board_option_gap)
    usable_height = int(render_params.canvas_height - (2 * render_params.scene_margin_px) - 34)
    cell_size = int(min((usable_width - ((dataset.cols - 1) * render_params.cell_gap_px)) / dataset.cols, (usable_height - ((dataset.rows - 1) * render_params.cell_gap_px)) / dataset.rows))
    cell_size = max(28, min(42, cell_size))
    grid_width = int(dataset.cols * cell_size + (dataset.cols - 1) * render_params.cell_gap_px)
    grid_height = int(dataset.rows * cell_size + (dataset.rows - 1) * render_params.cell_gap_px)
    content_width = int(grid_width + board_option_gap + option_width)
    content_height = int(max(grid_height, option_height))
    content_left = int((render_params.canvas_width - content_width) / 2)
    grid_left = int(content_left)
    options_left = int(grid_left + grid_width + board_option_gap)
    content_top = int((render_params.canvas_height - content_height) / 2)
    grid_top = int(content_top + max(0, (content_height - grid_height) / 2))
    options_top = int(content_top + max(0, (content_height - option_height) / 2))
    panel_top = int(content_top - render_params.panel_padding_px)
    panel_bottom = int(content_top + content_height + render_params.panel_padding_px)
    panel_bbox = (
        int(grid_left - render_params.panel_padding_px),
        int(panel_top),
        int(grid_left + grid_width + render_params.panel_padding_px),
        int(panel_bottom),
    )
    options_panel_bbox = (
        int(options_left - render_params.panel_padding_px),
        int(panel_top),
        int(options_left + option_width + render_params.panel_padding_px),
        int(panel_bottom),
    )
    draw_rounded_rect(
        draw,
        panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=tuple(render_params.panel_fill_rgb),
        outline=tuple(render_params.grid_line_rgb),
        width=int(render_params.panel_border_width_px),
    )
    draw_rounded_rect(
        draw,
        options_panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=tuple(render_params.panel_fill_rgb),
        outline=tuple(render_params.grid_line_rgb),
        width=int(render_params.panel_border_width_px),
    )
    tile_bbox_map: Dict[str, BBox] = {}
    item_bbox_map: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = [
        {
            "id": "pipe_flow_panel",
            "type": "pipe_flow_panel",
            "bbox_px": [int(value) for value in panel_bbox],
            "rows": int(dataset.rows),
            "cols": int(dataset.cols),
            "scene_variant": str(dataset.scene_variant),
            "missing_region_id": str(dataset.missing_region_id),
        }
    ]
    by_cell = {(tile.row, tile.col): tile for tile in dataset.tiles}
    pipe_rgb = tuple(render_params.pipe_rgb)
    pipe_shadow_rgb = tuple(render_params.pipe_shadow_rgb)
    missing_cells = set(dataset.missing_cells)
    missing_bboxes: List[Tuple[int, int, int, int]] = []
    for row in range(dataset.rows):
        for col in range(dataset.cols):
            bbox = _tile_bbox(row=row, col=col, grid_left=grid_left, grid_top=grid_top, cell_size=cell_size, gap=int(render_params.cell_gap_px))
            if (row, col) in missing_cells:
                missing_bboxes.append(tuple(bbox))
                draw.rounded_rectangle(
                    bbox,
                    radius=max(4, int(cell_size * 0.14)),
                    fill=(18, 20, 24),
                    outline=(18, 20, 24),
                    width=1,
                )
                continue
            draw.rounded_rectangle(
                bbox,
                radius=max(4, int(cell_size * 0.14)),
                fill=tuple(render_params.cell_fill_rgb),
                outline=tuple(render_params.grid_line_rgb),
                width=int(render_params.cell_border_width_px),
            )
            tile = by_cell.get((row, col))
            if tile is None:
                continue
            _draw_pipe(
                draw,
                bbox=bbox,
                openings=tuple(tile.current_openings),
                pipe_rgb=tuple(pipe_rgb),
                shadow_rgb=tuple(pipe_shadow_rgb),
                pipe_width=max(5, min(int(render_params.pipe_width_px if dataset.scene_variant != "circuit_trace" else max(7, render_params.pipe_width_px - 4)), int(cell_size * 0.38))),
                scene_variant=str(dataset.scene_variant),
            )
            tile_bbox_map[str(tile.tile_id)] = tuple(float(value) for value in bbox)
            item_bbox_map[str(tile.tile_id)] = tuple(float(value) for value in bbox)
            entities.append(
                {
                    "id": str(tile.tile_id),
                    "type": "pipe_flow_tile",
                    "label": str(tile.label),
                    "row_index": int(tile.row),
                    "col_index": int(tile.col),
                    "bbox_px": [int(value) for value in bbox],
                    "current_openings": list(tile.current_openings),
                    "required_openings": list(tile.required_openings),
                    "is_path": bool(tile.is_path),
                    "is_branch": bool(tile.is_branch),
                }
            )

    start_bbox = _tile_bbox(row=dataset.start_cell[0], col=dataset.start_cell[1], grid_left=grid_left, grid_top=grid_top, cell_size=cell_size, gap=int(render_params.cell_gap_px))
    dest_bbox = _tile_bbox(row=dataset.destination_cell[0], col=dataset.destination_cell[1], grid_left=grid_left, grid_top=grid_top, cell_size=cell_size, gap=int(render_params.cell_gap_px))
    start_marker_bbox = _draw_start_marker(draw, bbox=start_bbox, render_params=render_params)
    finish_marker_bbox = _draw_finish_flag(draw, bbox=dest_bbox, render_params=render_params)
    item_bbox_map["start_marker"] = tuple(float(value) for value in start_marker_bbox)
    item_bbox_map["finish_flag"] = tuple(float(value) for value in finish_marker_bbox)
    entities.extend(
        [
            {
                "id": "start_marker",
                "type": "pipe_flow_start_marker",
                "bbox_px": [int(value) for value in start_marker_bbox],
                "cell": [int(dataset.start_cell[0]), int(dataset.start_cell[1])],
            },
            {
                "id": "finish_flag",
                "type": "pipe_flow_finish_flag",
                "bbox_px": [int(value) for value in finish_marker_bbox],
                "cell": [int(dataset.destination_cell[0]), int(dataset.destination_cell[1])],
            },
        ]
    )

    if missing_bboxes:
        missing_region_bbox = (
            min(box[0] for box in missing_bboxes),
            min(box[1] for box in missing_bboxes),
            max(box[2] for box in missing_bboxes),
            max(box[3] for box in missing_bboxes),
        )
        draw.rounded_rectangle(
            missing_region_bbox,
            radius=max(7, int(cell_size * 0.20)),
            fill=(18, 20, 24),
            outline=(245, 247, 250),
            width=max(2, int(render_params.cell_border_width_px + 1)),
        )
        item_bbox_map[str(dataset.missing_region_id)] = tuple(float(value) for value in missing_region_bbox)
        entities.append(
            {
                "id": str(dataset.missing_region_id),
                "type": "pipe_flow_missing_2x2_region",
                "bbox_px": [int(value) for value in missing_region_bbox],
                "origin_row": int(dataset.missing_origin[0]),
                "origin_col": int(dataset.missing_origin[1]),
                "cells": [[int(row), int(col)] for row, col in dataset.missing_cells],
            }
        )

    for option_index, option in enumerate(dataset.options):
        row = int(option_index // option_cols)
        col = int(option_index % option_cols)
        panel = (
            int(options_left + col * (option_panel_width + option_gap)),
            int(options_top + row * (option_panel_height + option_gap)),
            int(options_left + col * (option_panel_width + option_gap) + option_panel_width),
            int(options_top + row * (option_panel_height + option_gap) + option_panel_height),
        )
        entity, option_bboxes = _draw_option_panel(
            draw,
            option=option,
            panel_bbox=panel,
            render_params=render_params,
            scene_variant=str(dataset.scene_variant),
        )
        entities.append(dict(entity))
        for key, value in option_bboxes.items():
            if key == str(option.option_id):
                item_bbox_map[str(key)] = tuple(float(v) for v in value)
            else:
                tile_bbox_map[str(key)] = tuple(float(v) for v in value)

    scene_bbox = (
        float(min(panel_bbox[0], options_panel_bbox[0])),
        float(min(panel_bbox[1], options_panel_bbox[1])),
        float(max(panel_bbox[2], options_panel_bbox[2])),
        float(max(panel_bbox[3], options_panel_bbox[3])),
    )

    return _RenderedScene(
        image=image,
        scene_bbox_px=tuple(float(value) for value in scene_bbox),
        tile_bbox_map=dict(tile_bbox_map),
        item_bbox_map=dict(item_bbox_map),
        entities=tuple(entities),
    )


def _build_prompt(prompt_defaults: Mapping[str, Any], *, scene_variant: str, instance_seed: int) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        f"object_description_{scene_variant}",
        "json_output_contract",
        "json_output_contract_answer_only",
        "answer_hint",
        "evidence_hint",
        "json_example",
        "json_example_answer_only",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {TASK_ID}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_values["answer_hint"]),
        "evidence_hint": str(prompt_values["evidence_hint"]),
        "json_example": str(prompt_values["json_example"]),
        "json_example_answer_only": str(prompt_values["json_example_answer_only"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="topology",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=QUERY_ID,
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_values["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }


@register_task
class PuzzlesTopologyPipeFlowRepairTileLabelTask:
    """Choose the 2x2 pipe piece that repairs start-marker-to-finish-flag flow."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "topology"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        group_defaults = get_task_group_defaults("puzzles", "topology")
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(group_defaults, task_id=TASK_ID)
        complexity_weights = resolve_puzzle_complexity_weights(group_defaults, task_id=TASK_ID)
        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed) + int(attempt_index))
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate pipe-flow repair puzzle") from last_error

        scene_variant_probabilities = _resolve_axis_variant(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            supported_variants=_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )[1]
        grid_size_variant_probabilities = _resolve_axis_variant(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            supported_variants=_GRID_SIZE_VARIANTS,
            explicit_key="grid_size_variant",
            weights_key="grid_size_variant_weights",
            balance_flag_key="balanced_grid_size_variant_sampling",
            axis_namespace="grid_size_variant",
        )[1]
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.pipe_flow_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            cell_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            grid_line_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            pipe_rgb=tuple(int(value) for value in scene_style.mark_rgb),
            pipe_shadow_rgb=tuple(int(value) for value in scene_style.notebook_line_rgb),
            label_fill_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            label_text_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_scene(background=background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(prompt_defaults, scene_variant=str(dataset.scene_variant), instance_seed=int(instance_seed))
        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.item_bbox_map,
            [str(dataset.correct_option_panel_id), str(dataset.missing_region_id)],
        )
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        query_params = {
            "query_id": QUERY_ID,
            "query_id_probabilities": {QUERY_ID: 1.0},
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "scene_variant_probabilities": {str(key): float(value) for key, value in scene_variant_probabilities.items()},
            "grid_size_variant": str(dataset.grid_size_variant),
            "grid_size_variant_probabilities": {str(key): float(value) for key, value in grid_size_variant_probabilities.items()},
            "rows": int(dataset.rows),
            "cols": int(dataset.cols),
            "path_length": int(len(dataset.path_cells)),
            "branch_cell_count": int(len(dataset.branch_cells)),
            "branch_terminal_count": int(len(dataset.branch_terminal_cells)),
            "candidate_count": int(dataset.candidate_count),
            "rotation_allowed": True,
            "answer_label": str(dataset.answer_label),
        }
        tile_trace = [
            {
                "tile_id": str(tile.tile_id),
                "label": str(tile.label),
                "row_index": int(tile.row),
                "col_index": int(tile.col),
                "current_openings": list(tile.current_openings),
                "required_openings": list(tile.required_openings),
                "is_path": bool(tile.is_path),
                "is_branch": bool(tile.is_branch),
            }
            for tile in dataset.tiles
        ]
        option_trace = [
            {
                "option_id": str(option.option_id),
                "label": str(option.label),
                "is_correct": bool(option.is_correct),
                "rotation_allowed": True,
                "display_rotation_turns": int(option.display_rotation_turns),
                "connects_after_rotation_turns": [int(value) for value in option.connects_after_rotation_turns],
                "local_openings": [
                    {"row": int(row), "col": int(col), "openings": list(openings)}
                    for row, col, openings in option.local_openings
                ],
            }
            for option in dataset.options
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": QUERY_ID,
                    "scene_id": SCENE_ID,
                    "scene_variant": str(dataset.scene_variant),
                    "answer_label": str(dataset.answer_label),
                    "correct_option_panel_id": str(dataset.correct_option_panel_id),
                    "missing_region_id": str(dataset.missing_region_id),
                },
            },
            "query_spec": {
                "query_id": QUERY_ID,
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
                "scene_variant": str(dataset.scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "tile_bboxes_px": {str(key): [round(float(v), 3) for v in value] for key, value in rendered_scene.tile_bbox_map.items()},
                "item_bboxes_px": {str(key): [round(float(v), 3) for v in value] for key, value in rendered_scene.item_bbox_map.items()},
                "evidence_source": "item_bboxes_px",
            }, render_params.unit_size_jitter),
            "execution_trace": {
                **dict(query_params),
                "question_format": QUERY_ID,
                "tiles": tile_trace,
                "option_specs": option_trace,
                "path_cells": [[int(r), int(c)] for r, c in dataset.path_cells],
                "branch_cells": [[int(r), int(c)] for r, c in dataset.branch_cells],
                "branch_terminal_cells": [[int(r), int(c)] for r, c in dataset.branch_terminal_cells],
                "start_cell": [int(dataset.start_cell[0]), int(dataset.start_cell[1])],
                "destination_cell": [int(dataset.destination_cell[0]), int(dataset.destination_cell[1])],
                "missing_origin": [int(dataset.missing_origin[0]), int(dataset.missing_origin[1])],
                "missing_cells": [[int(r), int(c)] for r, c in dataset.missing_cells],
                "missing_region_id": str(dataset.missing_region_id),
                "correct_option_panel_id": str(dataset.correct_option_panel_id),
                "supporting_item_ids": [str(dataset.correct_option_panel_id), str(dataset.missing_region_id)],
                "answer_value": str(dataset.answer_label),
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
        visual_scan = clamp_unit_interval(
            0.45 * normalize_int_with_bounds(int(dataset.rows * dataset.cols), [36, 100])
            + 0.35 * normalize_int_with_bounds(int(len(dataset.tiles)), [14, 46])
            + 0.20 * normalize_int_with_bounds(int(dataset.candidate_count), [6, 6])
        )
        reasoning_load = clamp_unit_interval(0.38 + (0.32 * normalize_int_with_bounds(int(len(dataset.path_cells)), [10, 24])))
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD[str(dataset.scene_variant)]),
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
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
            prompt_variants=dict(prompt_variants),
        )


__all__ = ["PuzzlesTopologyPipeFlowRepairTileLabelTask"]
