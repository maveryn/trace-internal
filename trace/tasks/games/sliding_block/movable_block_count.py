"""Sliding-block game tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from string import ascii_uppercase
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.annotation_artifacts import bbox_set_annotation_artifacts
from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.option_layout import balanced_option_grid_spec, option_grid_position, option_grid_size
from ..shared.sampling import get_games_int_param as _get_int, get_games_int_range as _get_range, resolve_games_named_axis
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_scene_noise_defaults


INTERNAL_TASK_ID = "games_sliding_block_internal"
SLIDING_BLOCKER_COUNT_TASK_ID = "task_games__sliding_block__sliding_block_blocker_count"
SLIDING_MOVABLE_BLOCK_COUNT_TASK_ID = "task_games__sliding_block__movable_block_count"
SLIDING_MOVE_RESULT_TASK_ID = "task_games__sliding_block__sliding_block_move_result_label"
SCENE_ID = "sliding_block"

SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "blocker_count",
    "movable_block_count",
    "move_result_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "wooden_tray",
    "cool_grid",
    "paper_board",
)
SUPPORTED_EXIT_SIDES: Tuple[str, ...] = ("right", "left", "top", "bottom")
_ANSWER_TYPES = {
    "blocker_count": "integer",
    "movable_block_count": "integer",
    "move_result_label": "option_letter",
}
_SCENE_LOAD = {
    "wooden_tray": 0.18,
    "cool_grid": 0.22,
    "paper_board": 0.20,
}
_REASONING_LOAD = {
    "blocker_count": 0.38,
    "movable_block_count": 0.42,
    "move_result_label": 0.58,
}
_BLOCK_FILLS: Tuple[Tuple[int, int, int], ...] = (
    (72, 118, 178),
    (72, 151, 120),
    (208, 136, 76),
    (132, 103, 184),
    (214, 179, 76),
    (69, 152, 166),
    (190, 89, 108),
    (141, 119, 82),
    (96, 133, 155),
    (175, 112, 72),
    (90, 160, 130),
    (118, 114, 190),
)
_TARGET_FILL = (218, 75, 66)
_STYLE_COLORS = {
    "wooden_tray": {
        "panel_fill": (246, 238, 222),
        "board_fill": (251, 244, 230),
        "grid": (169, 135, 94),
        "border": (105, 76, 50),
        "path": (255, 236, 165),
        "exit": (74, 86, 99),
    },
    "cool_grid": {
        "panel_fill": (243, 248, 252),
        "board_fill": (250, 253, 255),
        "grid": (177, 193, 208),
        "border": (72, 91, 112),
        "path": (218, 235, 255),
        "exit": (47, 93, 155),
    },
    "paper_board": {
        "panel_fill": (250, 248, 241),
        "board_fill": (255, 253, 246),
        "grid": (198, 187, 164),
        "border": (99, 91, 75),
        "path": (244, 238, 180),
        "exit": (76, 91, 88),
    },
}

_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=INTERNAL_TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id="sliding_block", apply_prob=0.0)


@dataclass(frozen=True)
class BlockSpec:
    """One rectangular sliding block in grid coordinates."""

    block_id: str
    label: str
    row: int
    col: int
    height: int
    width: int
    role: str
    fill_rgb: Tuple[int, int, int]

    @property
    def cells(self) -> Tuple[Tuple[int, int], ...]:
        return tuple(
            (int(self.row + dr), int(self.col + dc))
            for dr in range(int(self.height))
            for dc in range(int(self.width))
        )


@dataclass(frozen=True)
class BlockMoveSpec:
    """One slide in grid-cell units."""

    block_id: str
    direction: str
    distance: int


@dataclass(frozen=True)
class SlidingBlockRenderParams:
    """Resolved visual parameters for one sliding-block board."""

    canvas_width: int
    canvas_height: int
    board_size_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    block_corner_radius_px: int
    board_border_width_px: int
    grid_width_px: int
    block_gap_px: int
    target_outline_width_px: int
    label_font_size_px: int
    target_label_font_size_px: int
    arrow_width_px: int
    arrow_head_length_px: int
    arrow_head_width_px: int
    panel_fill_rgb: Tuple[int, int, int] | None
    board_fill_rgb: Tuple[int, int, int] | None
    grid_rgb: Tuple[int, int, int] | None
    border_rgb: Tuple[int, int, int] | None
    path_rgb: Tuple[int, int, int] | None
    exit_rgb: Tuple[int, int, int] | None
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class RenderedSlidingBlockScene:
    """Rendered sliding-block board with traceable geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    board_bbox_px: List[float]
    path_bbox_px: List[float]
    exit_arrow_bbox_px: List[float]
    block_bbox_map: Dict[str, List[float]]
    option_panel_bbox_map: Dict[str, List[float]]


def _int_value(mapping: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(mapping.get(str(key), int(fallback)))


def _cells_for(row: int, col: int, height: int, width: int) -> Tuple[Tuple[int, int], ...]:
    return tuple((int(row + dr), int(col + dc)) for dr in range(int(height)) for dc in range(int(width)))


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> SlidingBlockRenderParams:
    merged = dict(render_defaults)
    merged.update(dict(params))
    unit_scale, unit_meta = resolve_games_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="games.sliding_block.unit_size",
    )
    return SlidingBlockRenderParams(
        canvas_width=_int_value(merged, "canvas_width", 980),
        canvas_height=_int_value(merged, "canvas_height", 900),
        board_size_px=scale_games_px(_int_value(merged, "board_size_px", 660), unit_scale, min_px=320),
        panel_padding_px=scale_games_px(_int_value(merged, "panel_padding_px", 44), unit_scale, min_px=18),
        panel_corner_radius_px=scale_games_px(_int_value(merged, "panel_corner_radius_px", 28), unit_scale, min_px=10),
        block_corner_radius_px=scale_games_px(_int_value(merged, "block_corner_radius_px", 16), unit_scale, min_px=6),
        board_border_width_px=scale_games_px(_int_value(merged, "board_border_width_px", 5), unit_scale, min_px=2),
        grid_width_px=scale_games_px(_int_value(merged, "grid_width_px", 2), unit_scale, min_px=1),
        block_gap_px=scale_games_px(_int_value(merged, "block_gap_px", 7), unit_scale, min_px=3),
        target_outline_width_px=scale_games_px(_int_value(merged, "target_outline_width_px", 6), unit_scale, min_px=2),
        label_font_size_px=scale_games_px(_int_value(merged, "label_font_size_px", 30), unit_scale, min_px=14),
        target_label_font_size_px=scale_games_px(_int_value(merged, "target_label_font_size_px", 34), unit_scale, min_px=16),
        arrow_width_px=scale_games_px(_int_value(merged, "arrow_width_px", 8), unit_scale, min_px=3),
        arrow_head_length_px=scale_games_px(_int_value(merged, "arrow_head_length_px", 28), unit_scale, min_px=12),
        arrow_head_width_px=scale_games_px(_int_value(merged, "arrow_head_width_px", 28), unit_scale, min_px=12),
        panel_fill_rgb=None,
        board_fill_rgb=None,
        grid_rgb=None,
        border_rgb=None,
        path_rgb=None,
        exit_rgb=None,
        text_color_rgb=_rgb(merged.get("text_color_rgb"), (28, 32, 38)),
        text_stroke_rgb=_rgb(merged.get("text_stroke_rgb"), (255, 255, 255)),
        unit_size_jitter=dict(unit_meta),
    )


def _style_colors(scene_variant: str, render_params: SlidingBlockRenderParams) -> Dict[str, Tuple[int, int, int]]:
    colors = dict(_STYLE_COLORS[str(scene_variant)])
    overrides = {
        "panel_fill": render_params.panel_fill_rgb,
        "board_fill": render_params.board_fill_rgb,
        "grid": render_params.grid_rgb,
        "border": render_params.border_rgb,
        "path": render_params.path_rgb,
        "exit": render_params.exit_rgb,
    }
    for key, value in overrides.items():
        if value is not None:
            colors[str(key)] = tuple(int(component) for component in value)
    return colors


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=INTERNAL_TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported_variants=SUPPORTED_SCENE_VARIANTS,
    )


def _resolve_exit_side(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=INTERNAL_TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="exit_side",
        explicit_key="exit_side",
        weights_key="exit_side_weights",
        balance_flag_key="balanced_exit_side_sampling",
        supported_variants=SUPPORTED_EXIT_SIDES,
    )


def _move_result_option_count(params: Mapping[str, Any], *, instance_seed: int) -> int:
    raw_support = params.get(
        "move_result_option_count_support",
        group_default(_GEN_DEFAULTS, "move_result_option_count_support", [4, 6]),
    )
    support = [int(value) for value in raw_support]
    if not support:
        raise ValueError("move_result_option_count_support must not be empty")
    explicit = params.get("option_count", params.get("move_result_option_count"))
    if explicit is not None:
        count = int(explicit)
        if count not in set(support):
            raise ValueError(f"unsupported sliding-block move-result option_count: {count}")
        return int(count)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{INTERNAL_TASK_ID}.move_result_label.option_count",
    )
    return int(support[int(index) % len(support)])


def _answer_support(params: Mapping[str, Any], *, query_id: str, instance_seed: int = 0) -> List[int | str]:
    if str(query_id) == "blocker_count":
        low = _get_int(params, _GEN_DEFAULTS, "blocker_count_min", 1)
        high = _get_int(params, _GEN_DEFAULTS, "blocker_count_max", 5)
        return [int(value) for value in range(int(low), int(high) + 1)]
    if str(query_id) == "movable_block_count":
        low = _get_int(params, _GEN_DEFAULTS, "movable_block_count_min", 4)
        high = _get_int(params, _GEN_DEFAULTS, "movable_block_count_max", 9)
        return [int(value) for value in range(int(low), int(high) + 1)]
    raw = params.get("move_result_answer_labels")
    if raw is not None:
        return [str(item) for item in raw]
    count = _move_result_option_count(params, instance_seed=int(instance_seed))
    raw = list(ascii_uppercase[: int(count)])
    return [str(item) for item in raw]


def _choose_balanced_answer_target(
    *,
    params: Mapping[str, Any],
    query_id: str,
    instance_seed: int,
) -> int | str:
    support = _answer_support(params, query_id=str(query_id), instance_seed=int(instance_seed))
    if not support:
        raise ValueError(f"empty answer support for {query_id}")
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{INTERNAL_TASK_ID}.{query_id}.answer",
    )
    return support[int(index) % len(support)]


def _target_layout(
    *,
    exit_side: str,
    rows: int,
    cols: int,
    path_support_count: int,
    rng,
) -> Tuple[BlockSpec, List[Tuple[int, int]]]:
    target_length = 2
    if str(exit_side) in {"right", "left"}:
        row = int(rng.randint(1, max(1, int(rows) - 2)))
        if str(exit_side) == "right":
            max_col = max(0, int(cols) - target_length - int(path_support_count))
            col = int(rng.randint(0, int(max_col)))
            path_cells = [(row, c) for c in range(int(col + target_length), int(cols))]
        else:
            min_col = int(path_support_count)
            max_col = max(min_col, int(cols) - target_length)
            col = int(rng.randint(int(min_col), int(max_col)))
            path_cells = [(row, c) for c in range(0, int(col))]
        target = BlockSpec("target", "T", row, col, 1, target_length, "target", _TARGET_FILL)
    else:
        col = int(rng.randint(1, max(1, int(cols) - 2)))
        if str(exit_side) == "bottom":
            max_row = max(0, int(rows) - target_length - int(path_support_count))
            row = int(rng.randint(0, int(max_row)))
            path_cells = [(r, col) for r in range(int(row + target_length), int(rows))]
        else:
            min_row = int(path_support_count)
            max_row = max(min_row, int(rows) - target_length)
            row = int(rng.randint(int(min_row), int(max_row)))
            path_cells = [(r, col) for r in range(0, int(row))]
        target = BlockSpec("target", "T", row, col, target_length, 1, "target", _TARGET_FILL)
    return target, list(path_cells)


def _perpendicular_block_for_path_cell(
    *,
    path_cell: Tuple[int, int],
    exit_side: str,
    rows: int,
    cols: int,
    rng,
    block_id: str,
    role: str,
    fill_rgb: Tuple[int, int, int],
) -> BlockSpec:
    row, col = int(path_cell[0]), int(path_cell[1])
    if str(exit_side) in {"right", "left"}:
        length_candidates = [3, 2] if int(rows) >= 6 else [2]
        for height in length_candidates:
            top_candidates = [top for top in range(int(row) - int(height) + 1, int(row) + 1) if 0 <= top and top + int(height) <= int(rows)]
            if top_candidates:
                top = int(top_candidates[int(rng.randrange(len(top_candidates)))])
                return BlockSpec(str(block_id), "", top, col, int(height), 1, str(role), tuple(fill_rgb))
    else:
        length_candidates = [3, 2] if int(cols) >= 6 else [2]
        for width in length_candidates:
            left_candidates = [left for left in range(int(col) - int(width) + 1, int(col) + 1) if 0 <= left and left + int(width) <= int(cols)]
            if left_candidates:
                left = int(left_candidates[int(rng.randrange(len(left_candidates)))])
                return BlockSpec(str(block_id), "", row, left, 1, int(width), str(role), tuple(fill_rgb))
    raise RuntimeError("failed to place path-blocking sliding block")


def _candidate_distractor(
    *,
    block_id: str,
    rows: int,
    cols: int,
    rng,
    role: str,
    fill_rgb: Tuple[int, int, int],
) -> BlockSpec:
    horizontal = bool(rng.randrange(2))
    length = 3 if int(rng.randrange(4)) == 0 else 2
    if horizontal:
        width, height = int(length), 1
    else:
        width, height = 1, int(length)
    row = int(rng.randint(0, int(rows) - int(height)))
    col = int(rng.randint(0, int(cols) - int(width)))
    return BlockSpec(str(block_id), "", row, col, int(height), int(width), str(role), tuple(fill_rgb))


def _assign_labels(blocks: Sequence[BlockSpec], *, correct_block_id: str | None, correct_label: str | None) -> List[BlockSpec]:
    non_target = [block for block in blocks if str(block.block_id) != "target"]
    labels = list(ascii_uppercase)
    assigned: Dict[str, str] = {}
    if correct_block_id and correct_label:
        assigned[str(correct_block_id)] = str(correct_label)
    cursor = 0
    for block in non_target:
        if str(block.block_id) in assigned:
            continue
        while cursor < len(labels) and labels[cursor] in set(assigned.values()):
            cursor += 1
        assigned[str(block.block_id)] = labels[cursor]
        cursor += 1
    out: List[BlockSpec] = []
    for block in blocks:
        if str(block.block_id) == "target":
            out.append(block)
        else:
            out.append(
                BlockSpec(
                    block.block_id,
                    assigned[str(block.block_id)],
                    block.row,
                    block.col,
                    block.height,
                    block.width,
                    block.role,
                    block.fill_rgb,
                )
            )
    return out


def _block_by_id(blocks: Sequence[BlockSpec]) -> Dict[str, BlockSpec]:
    return {str(block.block_id): block for block in blocks}


def _state_signature(blocks: Sequence[BlockSpec]) -> Tuple[Tuple[str, int, int], ...]:
    return tuple(sorted((str(block.block_id), int(block.row), int(block.col)) for block in blocks))


def _replace_block(blocks: Sequence[BlockSpec], moved: BlockSpec) -> List[BlockSpec]:
    return [moved if str(block.block_id) == str(moved.block_id) else block for block in blocks]


def _shift_block(block: BlockSpec, *, direction: str, distance: int) -> BlockSpec:
    dr, dc = {
        "up": (-1, 0),
        "down": (1, 0),
        "left": (0, -1),
        "right": (0, 1),
    }[str(direction)]
    return BlockSpec(
        block.block_id,
        block.label,
        int(block.row) + (int(dr) * int(distance)),
        int(block.col) + (int(dc) * int(distance)),
        block.height,
        block.width,
        block.role,
        block.fill_rgb,
    )


def _inside_board(block: BlockSpec, *, rows: int, cols: int) -> bool:
    return 0 <= int(block.row) and 0 <= int(block.col) and int(block.row) + int(block.height) <= int(rows) and int(block.col) + int(block.width) <= int(cols)


def _can_apply_move(blocks: Sequence[BlockSpec], *, block_id: str, direction: str, distance: int, rows: int, cols: int) -> bool:
    block_map = _block_by_id(blocks)
    block = block_map[str(block_id)]
    occupied_without_block = {
        cell
        for other in blocks
        if str(other.block_id) != str(block_id)
        for cell in other.cells
    }
    for step in range(1, int(distance) + 1):
        shifted = _shift_block(block, direction=str(direction), distance=int(step))
        if not _inside_board(shifted, rows=int(rows), cols=int(cols)):
            return False
        if any(cell in occupied_without_block for cell in shifted.cells):
            return False
    return True


def _apply_move(blocks: Sequence[BlockSpec], *, move: BlockMoveSpec) -> List[BlockSpec]:
    block = _block_by_id(blocks)[str(move.block_id)]
    return _replace_block(
        blocks,
        _shift_block(block, direction=str(move.direction), distance=int(move.distance)),
    )


def _legal_moves(
    blocks: Sequence[BlockSpec],
    *,
    rows: int,
    cols: int,
    max_distance: int,
    exclude_block_ids: Iterable[str] = (),
) -> List[BlockMoveSpec]:
    excluded = {str(block_id) for block_id in exclude_block_ids}
    moves: List[BlockMoveSpec] = []
    for block in blocks:
        if str(block.block_id) == "target" or str(block.block_id) in excluded:
            continue
        directions = ("left", "right") if int(block.width) > int(block.height) else ("up", "down")
        for direction in directions:
            for distance in range(1, int(max_distance) + 1):
                if _can_apply_move(
                    blocks,
                    block_id=str(block.block_id),
                    direction=str(direction),
                    distance=int(distance),
                    rows=int(rows),
                    cols=int(cols),
                ):
                    moves.append(BlockMoveSpec(str(block.block_id), str(direction), int(distance)))
                else:
                    break
    return moves


def _sample_move_sequence(
    *,
    blocks: Sequence[BlockSpec],
    rows: int,
    cols: int,
    move_count: int,
    max_distance: int,
    rng,
) -> Tuple[List[BlockMoveSpec], List[List[BlockSpec]]]:
    """Sample an ordered sequence and return the board state after each move."""

    for _attempt in range(160):
        current = list(blocks)
        sequence: List[BlockMoveSpec] = []
        states: List[List[BlockSpec]] = [list(current)]
        moved_ids: List[str] = []
        for _step in range(int(move_count)):
            legal = _legal_moves(
                current,
                rows=int(rows),
                cols=int(cols),
                max_distance=int(max_distance),
                exclude_block_ids=(),
            )
            fresh = [move for move in legal if str(move.block_id) not in set(moved_ids)]
            choices = fresh or legal
            if not choices:
                break
            move = choices[int(rng.randrange(len(choices)))]
            current = _apply_move(current, move=move)
            sequence.append(move)
            states.append(list(current))
            if str(move.block_id) not in moved_ids:
                moved_ids.append(str(move.block_id))
        if len(sequence) == int(move_count):
            return sequence, states
    raise RuntimeError("failed to sample a valid sliding-block move sequence")


def _move_sequence_text(sequence: Sequence[BlockMoveSpec], *, blocks: Sequence[BlockSpec]) -> str:
    labels = {str(block.block_id): str(block.label) for block in blocks}
    parts = []
    for index, move in enumerate(sequence, start=1):
        noun = "cell" if int(move.distance) == 1 else "cells"
        parts.append(f"{index}. block {labels[str(move.block_id)]} slides {int(move.distance)} {noun} {move.direction}")
    return "; ".join(parts)


def _build_move_result_options(
    *,
    initial_blocks: Sequence[BlockSpec],
    states: Sequence[Sequence[BlockSpec]],
    rows: int,
    cols: int,
    option_labels: Sequence[str],
    correct_label: str,
    max_distance: int,
    rng,
) -> List[Dict[str, Any]]:
    correct_index = [str(label) for label in option_labels].index(str(correct_label))
    correct_blocks = list(states[-1])
    correct_signature = _state_signature(correct_blocks)
    candidates: List[List[BlockSpec]] = []
    seen = {correct_signature}
    for state in list(states[:-1]):
        signature = _state_signature(state)
        if signature not in seen:
            candidates.append(list(state))
            seen.add(signature)

    bases = [list(state) for state in states]
    for _attempt in range(260):
        base = list(bases[int(rng.randrange(len(bases)))])
        legal = _legal_moves(
            base,
            rows=int(rows),
            cols=int(cols),
            max_distance=int(max_distance),
            exclude_block_ids=(),
        )
        if not legal:
            continue
        move = legal[int(rng.randrange(len(legal)))]
        candidate = _apply_move(base, move=move)
        signature = _state_signature(candidate)
        if signature in seen:
            continue
        candidates.append(list(candidate))
        seen.add(signature)
        if len(candidates) >= len(option_labels) - 1:
            break
    if len(candidates) < len(option_labels) - 1:
        for _attempt in range(260):
            base = list(initial_blocks)
            legal = _legal_moves(
                base,
                rows=int(rows),
                cols=int(cols),
                max_distance=1,
                exclude_block_ids=(),
            )
            if not legal:
                continue
            move = legal[int(rng.randrange(len(legal)))]
            candidate = _apply_move(base, move=move)
            signature = _state_signature(candidate)
            if signature in seen:
                continue
            candidates.append(list(candidate))
            seen.add(signature)
            if len(candidates) >= len(option_labels) - 1:
                break
    if len(candidates) < len(option_labels) - 1:
        raise RuntimeError("failed to build enough unique sliding-block result options")

    options: List[Dict[str, Any]] = []
    distractor_cursor = 0
    for index, label in enumerate(option_labels):
        is_correct = int(index) == int(correct_index)
        option_blocks = correct_blocks if is_correct else candidates[distractor_cursor]
        if not is_correct:
            distractor_cursor += 1
        options.append(
            {
                "option_id": f"option_{label}",
                "label": str(label),
                "is_correct": bool(is_correct),
                "blocks": [
                    {
                        "block_id": str(block.block_id),
                        "label": str(block.label),
                        "row": int(block.row),
                        "col": int(block.col),
                        "height": int(block.height),
                        "width": int(block.width),
                        "role": str(block.role),
                        "fill_rgb": [int(value) for value in block.fill_rgb],
                        "cells": [[int(r), int(c)] for r, c in block.cells],
                    }
                    for block in option_blocks
                ],
            }
        )
    return options


def _dataset_blocks_to_specs(blocks: Sequence[Mapping[str, Any]]) -> List[BlockSpec]:
    return [
        BlockSpec(
            str(block["block_id"]),
            str(block["label"]),
            int(block["row"]),
            int(block["col"]),
            int(block["height"]),
            int(block["width"]),
            str(block["role"]),
            tuple(int(value) for value in block["fill_rgb"]),
        )
        for block in blocks
    ]


def _movable_block_ids(blocks: Sequence[BlockSpec], *, rows: int, cols: int) -> List[str]:
    moves = _legal_moves(
        blocks,
        rows=int(rows),
        cols=int(cols),
        max_distance=1,
        exclude_block_ids=(),
    )
    movable = {str(move.block_id) for move in moves}
    return [
        str(block.block_id)
        for block in blocks
        if str(block.block_id) != "target" and str(block.block_id) in movable
    ]


def _build_movable_block_count_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    exit_side: str,
) -> Dict[str, Any]:
    target = int(
        _choose_balanced_answer_target(
            params=params,
            query_id="movable_block_count",
            instance_seed=int(instance_seed),
        )
    )
    max_attempts = _get_int(params, _GEN_DEFAULTS, "movable_block_count_generation_attempts", 512)
    observed_counts: List[int] = []
    for attempt in range(int(max_attempts)):
        candidate_seed = int(instance_seed) + (7919 * (int(attempt) + 1))
        candidate = _build_sliding_dataset(
            query_id="blocker_count",
            params=params,
            instance_seed=int(candidate_seed),
            exit_side=str(exit_side),
        )
        blocks = _dataset_blocks_to_specs(candidate["blocks"])
        movable_ids = _movable_block_ids(
            blocks,
            rows=int(candidate["rows"]),
            cols=int(candidate["cols"]),
        )
        movable_count = int(len(movable_ids))
        observed_counts.append(int(movable_count))
        if int(movable_count) != int(target):
            continue
        out = dict(candidate)
        out.update(
            {
                "query_id": "movable_block_count",
                "answer_value": int(movable_count),
                "answer_block_ids": [str(block_id) for block_id in movable_ids],
                "movable_block_ids": [str(block_id) for block_id in movable_ids],
                "movable_block_count": int(movable_count),
                "answer_support": [
                    int(item)
                    for item in _answer_support(params, query_id="movable_block_count", instance_seed=int(instance_seed))
                ],
                "movable_generation_attempt": int(attempt) + 1,
            }
        )
        return out
    raise RuntimeError(
        "failed to sample sliding-block movable_block_count "
        f"target={target}; observed_counts={sorted(set(observed_counts))}"
    )


def _build_sliding_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    exit_side: str,
) -> Dict[str, Any]:
    if str(query_id) == "movable_block_count":
        return _build_movable_block_count_dataset(
            params=params,
            instance_seed=int(instance_seed),
            exit_side=str(exit_side),
        )

    rng = spawn_rng(int(instance_seed), f"{INTERNAL_TASK_ID}.{query_id}.dataset")
    rows_min, rows_max = _get_range(
        params,
        _GEN_DEFAULTS,
        min_key="board_rows_min",
        max_key="board_rows_max",
        fallback_min=6,
        fallback_max=7,
    )
    cols_min, cols_max = _get_range(
        params,
        _GEN_DEFAULTS,
        min_key="board_cols_min",
        max_key="board_cols_max",
        fallback_min=6,
        fallback_max=7,
    )
    target = _choose_balanced_answer_target(params=params, query_id=str(query_id), instance_seed=int(instance_seed))
    if str(query_id) == "blocker_count":
        blocker_count = int(target)
        correct_option_label = None
    else:
        blocker_count = int(rng.randint(1, min(3, _get_int(params, _GEN_DEFAULTS, "blocker_count_max", 6))))
        correct_option_label = str(target)
    rows = int(rng.randint(int(rows_min), int(rows_max)))
    cols = int(rng.randint(int(cols_min), int(cols_max)))
    if str(exit_side) in {"right", "left"}:
        cols = max(int(cols), int(blocker_count) + 2)
    else:
        rows = max(int(rows), int(blocker_count) + 2)
    rows = min(max(int(rows), int(rows_min)), int(rows_max))
    cols = min(max(int(cols), int(cols_min)), int(cols_max))

    target_block, path_cells = _target_layout(
        exit_side=str(exit_side),
        rows=int(rows),
        cols=int(cols),
        path_support_count=int(blocker_count),
        rng=rng,
    )
    if len(path_cells) < int(blocker_count):
        raise RuntimeError("not enough path cells for requested blocker count")
    selected_path_cells = list(path_cells)
    rng.shuffle(selected_path_cells)
    selected_path_cells = selected_path_cells[: int(blocker_count)]

    blocks: List[BlockSpec] = [target_block]
    occupied = set(target_block.cells)
    blocker_ids: List[str] = []
    for index, cell in enumerate(selected_path_cells):
        block_id = f"blocker_{index}"
        block = _perpendicular_block_for_path_cell(
            path_cell=cell,
            exit_side=str(exit_side),
            rows=int(rows),
            cols=int(cols),
            rng=rng,
            block_id=block_id,
            role="path_blocker",
            fill_rgb=_BLOCK_FILLS[index % len(_BLOCK_FILLS)],
        )
        if any(cell in occupied for cell in block.cells):
            raise RuntimeError("path blocker overlap during sliding-block generation")
        occupied.update(block.cells)
        blocks.append(block)
        blocker_ids.append(str(block_id))

    non_target_min = _get_int(params, _GEN_DEFAULTS, "non_target_block_count_min", 6)
    non_target_max = _get_int(params, _GEN_DEFAULTS, "non_target_block_count_max", 10)
    desired_non_target = int(rng.randint(int(non_target_min), int(non_target_max)))
    desired_non_target = max(int(desired_non_target), int(blocker_count))

    path_cell_set = set(path_cells)
    attempts = 0
    while len(blocks) - 1 < int(desired_non_target) and attempts < 900:
        attempts += 1
        idx = len(blocks) - 1
        block = _candidate_distractor(
            block_id=f"distractor_{idx}",
            rows=int(rows),
            cols=int(cols),
            rng=rng,
            role="distractor",
            fill_rgb=_BLOCK_FILLS[idx % len(_BLOCK_FILLS)],
        )
        if any(cell in occupied for cell in block.cells):
            continue
        if any(cell in path_cell_set for cell in block.cells):
            continue
        occupied.update(block.cells)
        blocks.append(block)

    labeled_blocks = _assign_labels(blocks, correct_block_id=None, correct_label=None)
    option_boards: List[Dict[str, Any]] = []
    moved_block_ids: List[str] = []
    move_sequence_trace: List[Dict[str, Any]] = []
    move_sequence_description = ""
    correct_option_id = ""
    correct_answer: int | str
    if str(query_id) == "blocker_count":
        correct_answer = int(blocker_count)
        answer_block_ids = list(blocker_ids)
    else:
        option_labels = [str(item) for item in _answer_support(params, query_id=str(query_id), instance_seed=int(instance_seed))]
        move_min = _get_int(params, _GEN_DEFAULTS, "move_result_move_count_min", 1)
        move_max = _get_int(params, _GEN_DEFAULTS, "move_result_move_count_max", 3)
        move_count_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{INTERNAL_TASK_ID}.{query_id}.move_count",
        )
        move_count = int(move_min) + (int(move_count_index) % (int(move_max) - int(move_min) + 1))
        max_distance = _get_int(params, _GEN_DEFAULTS, "move_result_slide_distance_max", 3)
        sequence, states = _sample_move_sequence(
            blocks=labeled_blocks,
            rows=int(rows),
            cols=int(cols),
            move_count=int(move_count),
            max_distance=int(max_distance),
            rng=rng,
        )
        for move in sequence:
            if str(move.block_id) not in moved_block_ids:
                moved_block_ids.append(str(move.block_id))
            label = _block_by_id(labeled_blocks)[str(move.block_id)].label
            move_sequence_trace.append(
                {
                    "block_id": str(move.block_id),
                    "label": str(label),
                    "direction": str(move.direction),
                    "distance": int(move.distance),
                }
            )
        move_sequence_description = _move_sequence_text(sequence, blocks=labeled_blocks)
        option_boards = _build_move_result_options(
            initial_blocks=labeled_blocks,
            states=states,
            rows=int(rows),
            cols=int(cols),
            option_labels=option_labels,
            correct_label=str(correct_option_label),
            max_distance=int(max_distance),
            rng=rng,
        )
        correct_answer = str(correct_option_label)
        correct_option_id = f"option_{correct_option_label}"
        answer_block_ids = list(moved_block_ids)
    movable_block_ids = _movable_block_ids(labeled_blocks, rows=int(rows), cols=int(cols))
    target_path_cells = list(path_cells)
    return {
        "query_id": str(query_id),
        "rows": int(rows),
        "cols": int(cols),
        "exit_side": str(exit_side),
        "blocks": [
            {
                "block_id": str(block.block_id),
                "label": str(block.label),
                "row": int(block.row),
                "col": int(block.col),
                "height": int(block.height),
                "width": int(block.width),
                "role": str(block.role),
                "fill_rgb": [int(value) for value in block.fill_rgb],
                "cells": [[int(r), int(c)] for r, c in block.cells],
            }
            for block in labeled_blocks
        ],
        "target_block_id": "target",
        "blocking_block_ids": [str(block_id) for block_id in blocker_ids],
        "answer_block_ids": [str(block_id) for block_id in answer_block_ids],
        "target_path_cells": [[int(r), int(c)] for r, c in target_path_cells],
        "move_sequence": [dict(item) for item in move_sequence_trace],
        "move_sequence_description": str(move_sequence_description),
        "moved_block_ids": [str(block_id) for block_id in moved_block_ids],
        "movable_block_ids": [str(block_id) for block_id in movable_block_ids],
        "movable_block_count": int(len(movable_block_ids)),
        "option_boards": [dict(option) for option in option_boards],
        "correct_option_id": str(correct_option_id),
        "answer_value": correct_answer,
        "blocker_count": int(blocker_count),
        "answer_support": [
            str(item) if isinstance(item, str) else int(item)
            for item in _answer_support(params, query_id=str(query_id), instance_seed=int(instance_seed))
        ],
        "non_target_block_count": int(len(labeled_blocks) - 1),
    }


def _cell_bbox(
    *,
    board_left: float,
    board_top: float,
    cell_size: float,
    row: int,
    col: int,
    row_span: int = 1,
    col_span: int = 1,
    inset: float = 0.0,
) -> List[float]:
    return [
        round(float(board_left + (int(col) * float(cell_size)) + float(inset)), 3),
        round(float(board_top + (int(row) * float(cell_size)) + float(inset)), 3),
        round(float(board_left + ((int(col) + int(col_span)) * float(cell_size)) - float(inset)), 3),
        round(float(board_top + ((int(row) + int(row_span)) * float(cell_size)) - float(inset)), 3),
    ]


def _exit_arrow_points(
    *,
    exit_side: str,
    board_bbox: Sequence[float],
    target_block: Mapping[str, Any],
    cell_size: float,
) -> Tuple[Tuple[float, float], Tuple[float, float], List[float]]:
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    row = int(target_block["row"])
    col = int(target_block["col"])
    height = int(target_block["height"])
    width = int(target_block["width"])
    if str(exit_side) == "right":
        cy = y0 + (float(row) + (0.5 * float(height))) * float(cell_size)
        start, end = (x1 - 8.0, cy), (x1 + 72.0, cy)
    elif str(exit_side) == "left":
        cy = y0 + (float(row) + (0.5 * float(height))) * float(cell_size)
        start, end = (x0 + 8.0, cy), (x0 - 72.0, cy)
    elif str(exit_side) == "bottom":
        cx = x0 + (float(col) + (0.5 * float(width))) * float(cell_size)
        start, end = (cx, y1 - 8.0), (cx, y1 + 72.0)
    else:
        cx = x0 + (float(col) + (0.5 * float(width))) * float(cell_size)
        start, end = (cx, y0 + 8.0), (cx, y0 - 72.0)
    arrow_bbox = _bbox_union([[start[0], start[1], end[0], end[1]]])
    return start, end, arrow_bbox


def _draw_board_at(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    blocks: Sequence[Mapping[str, Any]],
    board_bbox: Sequence[float],
    scene_variant: str,
    render_params: SlidingBlockRenderParams,
    show_path: bool,
    show_arrow: bool,
    label_font_size: int,
    target_label_font_size: int,
    block_gap_px: float,
    entity_prefix: str,
) -> Tuple[Dict[str, List[float]], List[Dict[str, Any]], List[float], List[float]]:
    rows = int(dataset["rows"])
    cols = int(dataset["cols"])
    x0, y0, x1, y1 = [float(value) for value in board_bbox]
    cell_size = min((x1 - x0) / float(cols), (y1 - y0) / float(rows))
    board_width = float(cell_size * int(cols))
    board_height = float(cell_size * int(rows))
    board_left = x0 + ((x1 - x0) - board_width) / 2.0
    board_top = y0 + ((y1 - y0) - board_height) / 2.0
    board_rect = [
        round(board_left, 3),
        round(board_top, 3),
        round(board_left + board_width, 3),
        round(board_top + board_height, 3),
    ]
    colors = _style_colors(str(scene_variant), render_params)
    draw_rounded_rect(
        draw,
        tuple(board_rect),
        radius=max(6, int(18 * (float(cell_size) / 80.0))),
        fill=colors["board_fill"],
        outline=colors["border"],
        width=max(1, int(render_params.board_border_width_px)),
    )
    path_cell_boxes = [
        _cell_bbox(
            board_left=board_left,
            board_top=board_top,
            cell_size=cell_size,
            row=int(cell[0]),
            col=int(cell[1]),
            inset=max(1.0, float(cell_size) * 0.04),
        )
        for cell in dataset["target_path_cells"]
    ]
    if bool(show_path):
        for bbox in path_cell_boxes:
            draw.rounded_rectangle(tuple(bbox), radius=max(2, int(cell_size * 0.10)), fill=tuple(colors["path"]))

    for r in range(1, int(rows)):
        y = board_top + (float(r) * cell_size)
        draw.line([(board_left, y), (board_left + board_width, y)], fill=tuple(colors["grid"]), width=max(1, int(render_params.grid_width_px)))
    for c in range(1, int(cols)):
        x = board_left + (float(c) * cell_size)
        draw.line([(x, board_top), (x, board_top + board_height)], fill=tuple(colors["grid"]), width=max(1, int(render_params.grid_width_px)))

    block_bbox_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": f"{entity_prefix}board",
            "entity_type": "sliding_block",
            "bbox_px": list(board_rect),
            "rows": int(rows),
            "cols": int(cols),
        }
    ]
    label_font = load_font(max(10, int(label_font_size)), bold=True)
    target_font = load_font(max(10, int(target_label_font_size)), bold=True)
    for block in blocks:
        bbox = _cell_bbox(
            board_left=board_left,
            board_top=board_top,
            cell_size=cell_size,
            row=int(block["row"]),
            col=int(block["col"]),
            row_span=int(block["height"]),
            col_span=int(block["width"]),
            inset=float(block_gap_px),
        )
        fill = tuple(int(value) for value in block["fill_rgb"])
        outline = (30, 35, 42) if str(block["role"]) == "target" else colors["border"]
        width = max(1, int(render_params.target_outline_width_px if str(block["role"]) == "target" else 2))
        draw_rounded_rect(
            draw,
            tuple(bbox),
            radius=max(4, min(int(render_params.block_corner_radius_px), int(cell_size * 0.18))),
            fill=fill,
            outline=outline,
            width=int(width),
        )
        font = target_font if str(block["role"]) == "target" else label_font
        draw_centered_text(
            draw,
            text=str(block["label"]),
            center=((float(bbox[0]) + float(bbox[2])) / 2.0, (float(bbox[1]) + float(bbox[3])) / 2.0),
            font=font,
            fill=tuple(render_params.text_color_rgb),
            stroke_fill=tuple(render_params.text_stroke_rgb),
            stroke_width=2 if int(label_font_size) >= 18 else 1,
        )
        block_bbox_map[str(block["block_id"])] = list(bbox)
        entities.append(
            {
                "entity_id": f"{entity_prefix}{block['block_id']}",
                "entity_type": "sliding_block",
                "label": str(block["label"]),
                "role": str(block["role"]),
                "bbox_px": list(bbox),
                "row": int(block["row"]),
                "col": int(block["col"]),
                "height": int(block["height"]),
                "width": int(block["width"]),
            }
        )

    exit_arrow_bbox: List[float] = [0.0, 0.0, 0.0, 0.0]
    if bool(show_arrow):
        target_block = next(block for block in blocks if str(block["block_id"]) == "target")
        arrow_start, arrow_end, _arrow_bbox = _exit_arrow_points(
            exit_side=str(dataset["exit_side"]),
            board_bbox=board_rect,
            target_block=target_block,
            cell_size=cell_size,
        )
        draw_arrow(
            draw,
            start=arrow_start,
            end=arrow_end,
            fill=colors["exit"],
            width=max(2, int(render_params.arrow_width_px)),
            head_length_px=float(render_params.arrow_head_length_px),
            head_width_px=float(render_params.arrow_head_width_px),
        )
        exit_arrow_bbox = [
            round(min(float(arrow_start[0]), float(arrow_end[0])) - 18.0, 3),
            round(min(float(arrow_start[1]), float(arrow_end[1])) - 18.0, 3),
            round(max(float(arrow_start[0]), float(arrow_end[0])) + 18.0, 3),
            round(max(float(arrow_start[1]), float(arrow_end[1])) + 18.0, 3),
        ]
        entities.append(
            {
                "entity_id": f"{entity_prefix}exit_arrow",
                "entity_type": "sliding_block_exit_arrow",
                "exit_side": str(dataset["exit_side"]),
                "bbox_px": list(exit_arrow_bbox),
            }
        )
    path_bbox = _bbox_union(path_cell_boxes) if bool(show_path) else [0.0, 0.0, 0.0, 0.0]
    return block_bbox_map, entities, path_bbox, exit_arrow_bbox


def _render_sliding_block_move_result_scene(
    image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: SlidingBlockRenderParams,
) -> RenderedSlidingBlockScene:
    draw = ImageDraw.Draw(image)
    colors = _style_colors(str(scene_variant), render_params)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    option_boards = [dict(option) for option in dataset.get("option_boards", [])]
    option_grid = balanced_option_grid_spec(len(option_boards))
    grid_cols = int(option_grid.columns)
    grid_rows = int(option_grid.rows) + 1
    margin_x = 48.0
    margin_y = 54.0
    gap_x = 24.0
    gap_y = 26.0
    panel_w = (float(width) - (2.0 * margin_x) - (float(grid_cols - 1) * gap_x)) / float(grid_cols)
    panel_h = (float(height) - (2.0 * margin_y) - (float(grid_rows - 1) * gap_y)) / float(grid_rows)
    board_size = min(panel_w - 44.0, panel_h - 76.0)
    option_area_width, _option_area_height = option_grid_size(
        len(option_boards),
        item_width=panel_w,
        item_height=panel_h,
        gap_x=gap_x,
        gap_y=gap_y,
        columns=grid_cols,
    )
    block_bbox_map: Dict[str, List[float]] = {}
    option_panel_bbox_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    panel_bboxes: List[List[float]] = []
    source_board_bbox = [0.0, 0.0, 0.0, 0.0]
    title_font = load_font(18, bold=True)
    source_item = {
        "option_id": "source",
        "label": "Original",
        "is_source": True,
        "blocks": list(dataset["blocks"]),
    }
    panel_items = [source_item] + option_boards
    for index, option in enumerate(panel_items):
        if bool(option.get("is_source", False)):
            panel_left = margin_x + ((option_area_width - panel_w) / 2.0)
            panel_top = margin_y
        else:
            option_index = int(index) - 1
            _row, _col, panel_left, panel_top = option_grid_position(
                option_index,
                len(option_boards),
                left=margin_x,
                top=margin_y + panel_h + gap_y,
                item_width=panel_w,
                item_height=panel_h,
                gap_x=gap_x,
                gap_y=gap_y,
                columns=grid_cols,
            )
        panel_bbox = [
            round(panel_left, 3),
            round(panel_top, 3),
            round(panel_left + panel_w, 3),
            round(panel_top + panel_h, 3),
        ]
        option_id = str(option["option_id"])
        draw_rounded_rect(
            draw,
            tuple(panel_bbox),
            radius=18,
            fill=colors["panel_fill"],
            outline=colors["border"],
            width=2,
        )
        draw_centered_text(
            draw,
            text=str(option["label"]),
            center=(panel_left + (70.0 if bool(option.get("is_source", False)) else 42.0), panel_top + 25.0),
            font=title_font,
            fill=tuple(render_params.text_color_rgb),
            stroke_fill=tuple(render_params.text_stroke_rgb),
            stroke_width=1,
        )
        board_left = panel_left + ((panel_w - board_size) / 2.0)
        board_top = panel_top + 58.0
        rendered_blocks, rendered_entities, _hidden_path_bbox, _hidden_exit_bbox = _draw_board_at(
            draw,
            dataset=dataset,
            blocks=option["blocks"],
            board_bbox=[board_left, board_top, board_left + board_size, board_top + board_size],
            scene_variant=str(scene_variant),
            render_params=render_params,
            show_path=False,
            show_arrow=False,
            label_font_size=14,
            target_label_font_size=15,
            block_gap_px=max(2.0, float(render_params.block_gap_px) * 0.35),
            entity_prefix=f"{option_id}_",
        )
        entities.extend(rendered_entities)
        panel_bboxes.append(list(panel_bbox))
        if bool(option.get("is_source", False)):
            block_bbox_map = dict(rendered_blocks)
            source_board_bbox = [
                round(float(board_left), 3),
                round(float(board_top), 3),
                round(float(board_left + board_size), 3),
                round(float(board_top + board_size), 3),
            ]
            entities.append(
                {
                    "entity_id": "source_panel",
                    "entity_type": "sliding_block_source_panel",
                    "bbox_px": list(panel_bbox),
                }
            )
        else:
            option_id = str(option["option_id"])
            option_panel_bbox_map[option_id] = list(panel_bbox)
            entities.append(
                {
                    "entity_id": option_id,
                    "entity_type": "sliding_block_result_option",
                    "label": str(option["label"]),
                    "is_correct": bool(option.get("is_correct", False)),
                    "bbox_px": list(panel_bbox),
                }
            )

    scene_bbox = _bbox_union(panel_bboxes)
    return RenderedSlidingBlockScene(
        image=image,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        board_bbox_px=list(source_board_bbox),
        path_bbox_px=[0.0, 0.0, 0.0, 0.0],
        exit_arrow_bbox_px=[0.0, 0.0, 0.0, 0.0],
        block_bbox_map=block_bbox_map,
        option_panel_bbox_map=option_panel_bbox_map,
    )


def render_sliding_block_scene(
    image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: SlidingBlockRenderParams,
) -> RenderedSlidingBlockScene:
    """Render one sliding-block board and return projected geometry."""

    if str(dataset.get("query_id", "")) == "move_result_label":
        return _render_sliding_block_move_result_scene(
            image,
            dataset=dataset,
            scene_variant=str(scene_variant),
            render_params=render_params,
        )

    draw = ImageDraw.Draw(image)
    show_exit_path = str(dataset.get("query_id", "")) == "blocker_count"
    rows = int(dataset["rows"])
    cols = int(dataset["cols"])
    max_dim = max(int(rows), int(cols))
    cell_size = float(render_params.board_size_px) / float(max_dim)
    board_width = float(cell_size * int(cols))
    board_height = float(cell_size * int(rows))
    board_left = float((int(render_params.canvas_width) - board_width) / 2.0)
    board_top = float((int(render_params.canvas_height) - board_height) / 2.0 + 16.0)
    board_bbox = [
        round(board_left, 3),
        round(board_top, 3),
        round(board_left + board_width, 3),
        round(board_top + board_height, 3),
    ]
    panel_bbox = [
        round(board_bbox[0] - int(render_params.panel_padding_px), 3),
        round(board_bbox[1] - int(render_params.panel_padding_px), 3),
        round(board_bbox[2] + int(render_params.panel_padding_px), 3),
        round(board_bbox[3] + int(render_params.panel_padding_px), 3),
    ]
    colors = _style_colors(str(scene_variant), render_params)
    draw_rounded_rect(
        draw,
        tuple(panel_bbox),
        radius=int(render_params.panel_corner_radius_px),
        fill=colors["panel_fill"],
        outline=colors["border"],
        width=max(1, int(render_params.board_border_width_px) - 1),
    )
    draw_rounded_rect(
        draw,
        tuple(board_bbox),
        radius=18,
        fill=colors["board_fill"],
        outline=colors["border"],
        width=int(render_params.board_border_width_px),
    )
    path_cell_boxes = [
        _cell_bbox(
            board_left=board_left,
            board_top=board_top,
            cell_size=cell_size,
            row=int(cell[0]),
            col=int(cell[1]),
            inset=3.0,
        )
        for cell in dataset["target_path_cells"]
    ]
    if bool(show_exit_path):
        for bbox in path_cell_boxes:
            draw.rounded_rectangle(tuple(bbox), radius=10, fill=tuple(colors["path"]))

    for r in range(1, int(rows)):
        y = board_top + (float(r) * cell_size)
        draw.line([(board_left, y), (board_left + board_width, y)], fill=tuple(colors["grid"]), width=int(render_params.grid_width_px))
    for c in range(1, int(cols)):
        x = board_left + (float(c) * cell_size)
        draw.line([(x, board_top), (x, board_top + board_height)], fill=tuple(colors["grid"]), width=int(render_params.grid_width_px))

    block_bbox_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "board",
            "entity_type": "sliding_block",
            "bbox_px": list(board_bbox),
            "rows": int(rows),
            "cols": int(cols),
        }
    ]
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    target_font = load_font(int(render_params.target_label_font_size_px), bold=True)
    for block in dataset["blocks"]:
        bbox = _cell_bbox(
            board_left=board_left,
            board_top=board_top,
            cell_size=cell_size,
            row=int(block["row"]),
            col=int(block["col"]),
            row_span=int(block["height"]),
            col_span=int(block["width"]),
            inset=float(render_params.block_gap_px),
        )
        fill = tuple(int(value) for value in block["fill_rgb"])
        outline = (30, 35, 42) if str(block["role"]) == "target" else colors["border"]
        width = int(render_params.target_outline_width_px) if str(block["role"]) == "target" else 3
        draw_rounded_rect(
            draw,
            tuple(bbox),
            radius=int(render_params.block_corner_radius_px),
            fill=fill,
            outline=outline,
            width=int(width),
        )
        font = target_font if str(block["role"]) == "target" else label_font
        draw_centered_text(
            draw,
            text=str(block["label"]),
            center=((float(bbox[0]) + float(bbox[2])) / 2.0, (float(bbox[1]) + float(bbox[3])) / 2.0),
            font=font,
            fill=tuple(render_params.text_color_rgb),
            stroke_fill=tuple(render_params.text_stroke_rgb),
            stroke_width=2,
        )
        block_bbox_map[str(block["block_id"])] = list(bbox)
        entities.append(
            {
                "entity_id": str(block["block_id"]),
                "entity_type": "sliding_block",
                "label": str(block["label"]),
                "role": str(block["role"]),
                "bbox_px": list(bbox),
                "row": int(block["row"]),
                "col": int(block["col"]),
                "height": int(block["height"]),
                "width": int(block["width"]),
            }
        )

    exit_arrow_bbox: List[float] = [0.0, 0.0, 0.0, 0.0]
    if bool(show_exit_path):
        target_block = next(block for block in dataset["blocks"] if str(block["block_id"]) == "target")
        arrow_start, arrow_end, _arrow_bbox = _exit_arrow_points(
            exit_side=str(dataset["exit_side"]),
            board_bbox=board_bbox,
            target_block=target_block,
            cell_size=cell_size,
        )
        draw_arrow(
            draw,
            start=arrow_start,
            end=arrow_end,
            fill=colors["exit"],
            width=int(render_params.arrow_width_px),
            head_length_px=float(render_params.arrow_head_length_px),
            head_width_px=float(render_params.arrow_head_width_px),
        )
        exit_arrow_bbox = [
            round(min(float(arrow_start[0]), float(arrow_end[0])) - 18.0, 3),
            round(min(float(arrow_start[1]), float(arrow_end[1])) - 18.0, 3),
            round(max(float(arrow_start[0]), float(arrow_end[0])) + 18.0, 3),
            round(max(float(arrow_start[1]), float(arrow_end[1])) + 18.0, 3),
        ]
        entities.append(
            {
                "entity_id": "exit_arrow",
                "entity_type": "sliding_block_exit_arrow",
                "exit_side": str(dataset["exit_side"]),
                "bbox_px": list(exit_arrow_bbox),
            }
        )
    path_bbox = _bbox_union(path_cell_boxes) if bool(show_exit_path) else [0.0, 0.0, 0.0, 0.0]
    scene_bbox = _bbox_union([panel_bbox, exit_arrow_bbox]) if bool(show_exit_path) else list(panel_bbox)
    return RenderedSlidingBlockScene(
        image=image,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        board_bbox_px=list(board_bbox),
        path_bbox_px=list(path_bbox),
        exit_arrow_bbox_px=list(exit_arrow_bbox),
        block_bbox_map=block_bbox_map,
        option_panel_bbox_map={},
    )


class _SlidingBlockBaseTask:
    """Base generator for public sliding-block scene tasks."""

    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    fixed_query_id: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id = str(self.fixed_query_id)
        if query_id not in SUPPORTED_QUERY_IDS:
            raise ValueError(f"unsupported sliding-block query_id: {query_id}")
        scene_variant, scene_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        exit_side, exit_probabilities = _resolve_exit_side(params, instance_seed=int(instance_seed))
        dataset = _build_sliding_dataset(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
            exit_side=str(exit_side),
        )
        render_params = _resolve_render_params(params, _RENDER_DEFAULTS, instance_seed=int(instance_seed))
        scene_style, scene_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.sliding_block_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            board_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            grid_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            border_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            path_rgb=tuple(int(value) for value in scene_style.step_fill_rgb),
            exit_rgb=tuple(int(value) for value in scene_style.mark_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_sliding_block_scene(
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
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "answer_hint_option_letter",
                "annotation_hint_blocker_count",
                "annotation_hint_movable_block_count",
                "annotation_hint_move_result_label",
                "json_example_blocker_count",
                "json_example_movable_block_count",
                "json_example_move_result_label",
                "json_example_answer_only_blocker_count",
                "json_example_answer_only_movable_block_count",
                "json_example_answer_only_move_result_label",
            ),
            context=f"prompt defaults for {INTERNAL_TASK_ID}",
        )
        answer_type = str(_ANSWER_TYPES[str(query_id)])
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{query_id}"]),
                "answer_hint": str(prompt_defaults["answer_hint_integer" if answer_type == "integer" else "answer_hint_option_letter"]),
                "json_example": str(prompt_defaults[f"json_example_{query_id}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{query_id}"]),
                "move_sequence_description": str(dataset.get("move_sequence_description", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_block_ids = [str(item) for item in dataset["answer_block_ids"]]
        if str(query_id) == "move_result_label":
            annotation_bboxes = [
                [round(float(value), 3) for value in rendered_scene.block_bbox_map[str(block_id)]]
                for block_id in answer_block_ids
            ]
            correct_option_id = str(dataset["correct_option_id"])
            annotation_bboxes.append(
                [round(float(value), 3) for value in rendered_scene.option_panel_bbox_map[correct_option_id]]
            )
        else:
            annotation_bboxes = [
                [round(float(value), 3) for value in rendered_scene.block_bbox_map[str(block_id)]]
                for block_id in answer_block_ids
            ]
        annotation_artifacts = bbox_set_annotation_artifacts(annotation_bboxes)
        annotation_bboxes = list(annotation_artifacts.value)
        answer_value = int(dataset["answer_value"]) if answer_type == "integer" else str(dataset["answer_value"])
        answer_gt = TypedValue(type=answer_type, value=answer_value)
        annotation_gt = annotation_artifacts.annotation_gt

        count_load_value = int(dataset.get("movable_block_count", dataset["blocker_count"]))
        visual_scan = clamp_unit_interval(
            0.42 * normalize_int_with_bounds(int(dataset["non_target_block_count"]), [6, 10])
            + 0.28 * normalize_int_with_bounds(max(int(dataset["rows"]), int(dataset["cols"])), [6, 8])
            + 0.30 * normalize_int_with_bounds(int(count_load_value), [1, 10])
        )
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD[str(query_id)])
            + 0.10 * normalize_int_with_bounds(int(count_load_value), [1, 10])
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "game_sliding_block",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "exit_side": str(exit_side),
                    "target_block_id": str(dataset["target_block_id"]),
                    "blocking_block_ids": [str(item) for item in dataset["blocking_block_ids"]],
                    "movable_block_ids": [str(item) for item in dataset.get("movable_block_ids", [])],
                    "answer_value": answer_value,
                    "view_family": SCENE_ID,
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probabilities),
                    "exit_side": str(exit_side),
                    "exit_side_probabilities": dict(exit_probabilities),
                    "rows": int(dataset["rows"]),
                    "cols": int(dataset["cols"]),
                    "blocker_count": int(dataset["blocker_count"]),
                    "movable_block_count": int(dataset.get("movable_block_count", 0)),
                    "answer_support": list(dataset["answer_support"]),
                    "non_target_block_count": int(dataset["non_target_block_count"]),
                    "move_count": int(len(dataset.get("move_sequence", []))),
                    "option_count": int(len(dataset.get("option_boards", []))),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "exit_side": str(exit_side),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "board_bbox_px": list(rendered_scene.board_bbox_px),
                "path_bbox_px": list(rendered_scene.path_bbox_px),
                "exit_arrow_bbox_px": list(rendered_scene.exit_arrow_bbox_px),
                "option_panel_bboxes_px": {str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()},
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "target_label_font_size_px": int(render_params.target_label_font_size_px),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": attach_games_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "board_bbox_px": list(rendered_scene.board_bbox_px),
                "path_bbox_px": list(rendered_scene.path_bbox_px),
                "exit_arrow_bbox_px": list(rendered_scene.exit_arrow_bbox_px),
                "block_bboxes_px": {str(key): list(value) for key, value in rendered_scene.block_bbox_map.items()},
                "option_panel_bboxes_px": {str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()},
                "annotation_source": "block_bboxes_px+option_panel_bboxes_px" if str(query_id) == "move_result_label" else "block_bboxes_px",
            }, render_params.unit_size_jitter),
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "exit_side": str(exit_side),
                "rows": int(dataset["rows"]),
                "cols": int(dataset["cols"]),
                "blocks": [dict(block) for block in dataset["blocks"]],
                "target_block_id": str(dataset["target_block_id"]),
                "blocking_block_ids": [str(item) for item in dataset["blocking_block_ids"]],
                "movable_block_ids": [str(item) for item in dataset.get("movable_block_ids", [])],
                "movable_block_count": int(dataset.get("movable_block_count", 0)),
                "answer_block_ids": [str(item) for item in answer_block_ids],
                "target_path_cells": [list(item) for item in dataset["target_path_cells"]],
                "move_sequence": [dict(item) for item in dataset.get("move_sequence", [])],
                "move_sequence_description": str(dataset.get("move_sequence_description", "")),
                "moved_block_ids": [str(item) for item in dataset.get("moved_block_ids", [])],
                "option_boards": [dict(item) for item in dataset.get("option_boards", [])],
                "correct_option_id": str(dataset.get("correct_option_id", "")),
                "answer_value": answer_value,
                "question_format": str(query_id),
                "view_family": SCENE_ID,
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": dict(annotation_artifacts.projected_annotation),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class GamesSlidingBlockBlockerCountTask(_SlidingBlockBaseTask):
    """Count rectangular blocks currently occupying the target block's exit path."""

    task_id = SLIDING_BLOCKER_COUNT_TASK_ID
    fixed_query_id = "blocker_count"


@register_task
class GamesSlidingBlockMovableBlockCountTask(_SlidingBlockBaseTask):
    """Count non-target blocks that can legally slide at least one cell."""

    task_id = SLIDING_MOVABLE_BLOCK_COUNT_TASK_ID
    fixed_query_id = "movable_block_count"


class GamesSlidingBlockMoveResultLabelTask(_SlidingBlockBaseTask):
    """Choose the final board after applying a short ordered slide sequence."""

    task_id = SLIDING_MOVE_RESULT_TASK_ID
    fixed_query_id = "move_result_label"


__all__ = [
    "GamesSlidingBlockBlockerCountTask",
    "GamesSlidingBlockMovableBlockCountTask",
    "GamesSlidingBlockMoveResultLabelTask",
]
