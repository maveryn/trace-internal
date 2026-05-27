"""Games 2048-board tasks over one visible board state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_2048_board_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, rewrite_public_query_output
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.twenty_forty_eight_common import (
    Board,
    Coord,
    EMPTY,
    MOVE_RESULT_QUERY_IDS,
    SIZE,
    SUPPORTED_2048_DIRECTIONS,
    SUPPORTED_2048_GOAL_CELLS,
    SUPPORTED_2048_LABELS,
    SUPPORTED_2048_QUERY_IDS,
    SUPPORTED_2048_SCENE_VARIANTS,
    SUPPORTED_2048_STYLE_VARIANTS,
    Move2048Result,
    Sample2048,
    board_max_tile,
    coord_to_cell_id,
    goal_cell_name_to_coord,
    simulate_2048_move,
    validate_2048_sample,
)
from ..shared.twenty_forty_eight_scene import TwentyFortyEightRenderParams, render_2048_board_scene
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_2048_board_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible 2048-board scenes."""

    merge_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    score_value_support: Tuple[int, ...] = (0, 4, 8, 12, 16, 24, 32, 40)
    max_tile_value_support: Tuple[int, ...] = (16, 32, 64, 128, 256)
    best_move_label_support: Tuple[str, ...] = SUPPORTED_2048_LABELS
    canvas_width: int = 900
    canvas_height: int = 900
    panel_margin_px: int = 64
    board_size_px: int = 560
    board_radius_px: int = 18
    cell_gap_px: int = 14
    cell_radius_px: int = 10
    tile_font_size_px: int = 46
    arrow_width_px: int = 9
    label_font_size_px: int = 24
    goal_outline_width_px: int = 7


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one 2048 instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    move_direction: str
    goal_cell_name: str
    target_answer: int | None
    target_label: str | None
    target_answer_support: Tuple[int, ...]
    target_label_support: Tuple[str, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    move_direction_probabilities: Dict[str, float]
    goal_cell_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    target_label_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "2048")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="2048", apply_prob=0.5)


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced 2048 query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported_query_ids,
    )


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named 2048 axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(value) for value in supported],
    )


def _string_support(params: Mapping[str, Any], *, key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
    """Resolve a string support list from params/defaults."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    if raw is None:
        raw = tuple(fallback)
    values = (str(raw),) if isinstance(raw, str) else tuple(str(value) for value in raw)
    values = tuple(value for value in values if value)
    if not values:
        raise ValueError(f"{key} must contain at least one label")
    return values


def _resolve_label_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one label-valued support choice."""

    support = _string_support(params, key=str(support_key), fallback=fallback_support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"{explicit_key}={value!r} is not in {support_key}")
        return value, {str(item): (1.0 if str(item) == value else 0.0) for item in support}
    probabilities = {str(item): 1.0 / float(len(support)) for item in support}
    sampling_index = params.get("_sample_cursor")
    balanced = bool(params.get(str(balanced_flag_key), group_default(_GEN_DEFAULTS, str(balanced_flag_key), True)))
    if balanced and sampling_index is not None:
        return str(support[abs(int(sampling_index)) % len(support)]), probabilities
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(rng.choice(tuple(support))), probabilities


def _uses_uniform_query_cycle(
    params: Mapping[str, Any],
    probabilities: Mapping[str, float],
    *,
    supported_query_ids: Sequence[str],
) -> bool:
    """Return true when the query axis uses the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(tuple(supported_query_ids)):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner answer axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(
        params,
        query_id_probabilities,
        supported_query_ids=supported_query_ids,
    ):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(tuple(supported_query_ids)))
    return cycle_params


def _target_support_key(query_id: str) -> str:
    """Return the integer support key used by one 2048 value query."""

    if str(query_id) == "merge_count":
        return "merge_count_support"
    if str(query_id) == "score_value":
        return "score_value_support"
    if str(query_id) == "max_tile_value":
        return "max_tile_value_support"
    raise ValueError(f"query id {query_id!r} does not use integer target support")


def _target_fallback(query_id: str) -> Tuple[int, ...]:
    """Return fallback answer support for one 2048 value query."""

    if str(query_id) == "merge_count":
        return _DEFAULTS.merge_count_support
    if str(query_id) == "score_value":
        return _DEFAULTS.score_value_support
    if str(query_id) == "max_tile_value":
        return _DEFAULTS.max_tile_value_support
    raise ValueError(f"query id {query_id!r} does not use integer target support")


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one 2048 instance."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported_query_ids,
    )
    answer_cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
        supported_query_ids=supported_query_ids,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_2048_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_2048_STYLE_VARIANTS,
    )
    move_direction, move_direction_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="move_direction",
        explicit_key="move_direction",
        weights_key="move_direction_weights",
        balance_flag_key="balanced_move_direction_sampling",
        supported=SUPPORTED_2048_DIRECTIONS,
    )
    goal_cell_name, goal_cell_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="goal_cell",
        explicit_key="goal_cell",
        weights_key="goal_cell_weights",
        balance_flag_key="balanced_goal_cell_sampling",
        supported=SUPPORTED_2048_GOAL_CELLS,
    )

    target_answer = None
    target_answer_support: Tuple[int, ...] = tuple()
    target_answer_probabilities: Dict[str, float] = {}
    target_label = None
    target_label_probabilities: Dict[str, float] = {}
    target_label_support = _string_support(
        params,
        key="best_move_label_support",
        fallback=_DEFAULTS.best_move_label_support,
    )
    if str(query_id) in MOVE_RESULT_QUERY_IDS:
        support_key = _target_support_key(str(query_id))
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key=support_key,
            fallback=_target_fallback(str(query_id)),
        )
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=support_key,
            explicit_key="target_answer",
            fallback_support=_target_fallback(str(query_id)),
            namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
    elif str(query_id) == "best_move_label":
        target_label, target_label_probabilities = _resolve_label_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            support_key="best_move_label_support",
            explicit_key="target_label",
            fallback_support=_DEFAULTS.best_move_label_support,
            namespace=f"{TASK_ID}.target_label.best_move_label",
            balanced_flag_key="balanced_target_label_sampling",
        )
    else:
        raise ValueError(f"unsupported 2048 query_id: {query_id}")

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        move_direction=str(move_direction),
        goal_cell_name=str(goal_cell_name),
        target_answer=None if target_answer is None else int(target_answer),
        target_label=None if target_label is None else str(target_label),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        target_label_support=tuple(str(value) for value in target_label_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        move_direction_probabilities=dict(move_direction_probabilities),
        goal_cell_probabilities=dict(goal_cell_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        target_label_probabilities=dict(target_label_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> TwentyFortyEightRenderParams:
    """Resolve 2048 rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.2048.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.2048.layout",
        ),
        unit_scale_meta,
    )
    return TwentyFortyEightRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        board_size_px=scale_games_px(params.get("board_size_px", group_default(_RENDER_DEFAULTS, "board_size_px", _DEFAULTS.board_size_px)), unit_scale, min_px=280),
        board_radius_px=scale_games_px(params.get("board_radius_px", group_default(_RENDER_DEFAULTS, "board_radius_px", _DEFAULTS.board_radius_px)), unit_scale, min_px=8),
        cell_gap_px=scale_games_px(params.get("cell_gap_px", group_default(_RENDER_DEFAULTS, "cell_gap_px", _DEFAULTS.cell_gap_px)), unit_scale, min_px=6),
        cell_radius_px=scale_games_px(params.get("cell_radius_px", group_default(_RENDER_DEFAULTS, "cell_radius_px", _DEFAULTS.cell_radius_px)), unit_scale, min_px=5),
        tile_font_size_px=scale_games_px(params.get("tile_font_size_px", group_default(_RENDER_DEFAULTS, "tile_font_size_px", _DEFAULTS.tile_font_size_px)), unit_scale, min_px=22),
        arrow_width_px=scale_games_px(params.get("arrow_width_px", group_default(_RENDER_DEFAULTS, "arrow_width_px", _DEFAULTS.arrow_width_px)), unit_scale, min_px=4),
        label_font_size_px=scale_games_px(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px)), unit_scale, min_px=13),
        goal_outline_width_px=scale_games_px(params.get("goal_outline_width_px", group_default(_RENDER_DEFAULTS, "goal_outline_width_px", _DEFAULTS.goal_outline_width_px)), unit_scale, min_px=3),
        layout_jitter_meta=layout_jitter,
    )


def _line_coords(index: int, direction: str) -> Tuple[Coord, ...]:
    """Return 2048 line coordinates in move-compression order."""

    if str(direction) == "left":
        return tuple((int(index), col) for col in range(SIZE))
    if str(direction) == "right":
        return tuple((int(index), col) for col in range(SIZE - 1, -1, -1))
    if str(direction) == "up":
        return tuple((row, int(index)) for row in range(SIZE))
    if str(direction) == "down":
        return tuple((row, int(index)) for row in range(SIZE - 1, -1, -1))
    raise ValueError(f"unsupported direction: {direction!r}")


def _board_from_move_order(lines: Sequence[Sequence[int]], *, direction: str) -> Board:
    """Build a board from rows/columns expressed in movement order."""

    if len(lines) != SIZE or any(len(line) != SIZE for line in lines):
        raise ValueError("2048 move-order lines must be 4 x 4")
    rows = [[EMPTY for _col in range(SIZE)] for _row in range(SIZE)]
    for line_index, line in enumerate(lines):
        for slot_index, value in enumerate(line):
            row, col = _line_coords(int(line_index), str(direction))[int(slot_index)]
            rows[int(row)][int(col)] = int(value)
    return tuple(tuple(int(value) for value in row) for row in rows)


def _score_decomposition(score: int) -> Tuple[int, ...]:
    """Return merged tile values that sum to a supported score."""

    target = int(score)
    if target == 0:
        return tuple()
    values: list[int] = []
    remaining = int(target)
    for value in (32, 16, 8, 4):
        while remaining >= int(value) and len(values) < 4:
            values.append(int(value))
            remaining -= int(value)
    if remaining != 0 or len(values) > 4:
        raise ValueError(f"unsupported 2048 score target: {score}")
    return tuple(values)


def _non_merging_line(rng, *, force_slide: bool = False, max_value: int = 64) -> Tuple[int, ...]:
    """Return one sparse line that slides without creating a merge."""

    values = [2, 4, 8, 16, 32, 64, 128]
    values = [value for value in values if int(value) <= int(max_value)]
    start_offset = int(rng.randrange(len(values)))
    filled = [int(values[(start_offset + index) % len(values)]) for index in range(int(rng.randint(2, 5)))]
    if bool(force_slide):
        return (EMPTY,) + tuple(filled[:3])
    line = list(filled[:SIZE])
    while len(line) < SIZE:
        line.append(EMPTY)
    if rng.random() < 0.45:
        rng.shuffle(line)
    return tuple(int(value) for value in line)


def _board_for_merge_values(
    *,
    rng,
    direction: str,
    merge_values: Sequence[int],
    max_clutter_value: int = 64,
    force_slide_when_no_merge: bool = False,
) -> Board:
    """Construct a board whose shown move creates the requested merge values."""

    line_values: list[list[int]] = [[] for _ in range(SIZE)]
    line_order = list(range(SIZE))
    rng.shuffle(line_order)
    for index, merged_value in enumerate(merge_values):
        line = line_values[line_order[int(index) % SIZE]]
        if len(line) > SIZE - 2:
            line = line_values[line_order[(int(index) + 1) % SIZE]]
        line.extend([int(merged_value) // 2, int(merged_value) // 2])

    lines: list[Tuple[int, ...]] = []
    used_slide_line = False
    for line in line_values:
        if line:
            padded = list(line[:SIZE])
            while len(padded) < SIZE:
                padded.append(EMPTY)
            if rng.random() < 0.40 and padded.count(EMPTY) > 0:
                zero_indices = [idx for idx, value in enumerate(padded) if int(value) == EMPTY]
                if zero_indices:
                    first_zero = int(zero_indices[0])
                    padded.insert(0, padded.pop(first_zero))
            lines.append(tuple(int(value) for value in padded[:SIZE]))
            continue
        force_slide = bool(force_slide_when_no_merge and not used_slide_line)
        lines.append(_non_merging_line(rng, force_slide=force_slide, max_value=int(max_clutter_value)))
        used_slide_line = bool(used_slide_line or force_slide)
    return _board_from_move_order(lines, direction=str(direction))


def _merge_metric(result: Move2048Result, *, query_id: str) -> int:
    """Return the answer metric for one value query."""

    if str(query_id) == "merge_count":
        return int(len(result.merge_pairs))
    if str(query_id) == "score_value":
        return int(result.score)
    if str(query_id) == "max_tile_value":
        return int(board_max_tile(result.after))
    raise ValueError(f"unsupported 2048 value query: {query_id}")


def _evidence_coords_for_query(result: Move2048Result, *, query_id: str) -> Tuple[Coord, ...]:
    """Return source-cell evidence coordinates for one value query."""

    if str(query_id) in {"merge_count", "score_value"}:
        return tuple(coord for pair in result.merge_pairs for coord in pair)
    if str(query_id) == "max_tile_value":
        max_value = int(board_max_tile(result.after))
        max_cells = [
            tuple(coord)
            for coord, sources in result.result_sources.items()
            if int(result.after[int(coord[0])][int(coord[1])]) == int(max_value) and sources
        ]
        return tuple(coord for cell in max_cells for coord in result.result_sources[cell])
    raise ValueError(f"unsupported 2048 value query: {query_id}")


def _unique_max_result(result: Move2048Result) -> bool:
    """Return true when the post-move board has exactly one max-valued tile."""

    max_value = int(board_max_tile(result.after))
    return sum(1 for row in result.after for value in row if int(value) == int(max_value)) == 1


def _sample_move_result_scene(*, rng, axes: _ResolvedAxes) -> Sample2048:
    """Construct a single-arrow 2048 value query."""

    query = str(axes.query_id)
    target = int(axes.target_answer if axes.target_answer is not None else 0)
    for _attempt in range(160):
        if query == "merge_count":
            merge_values = tuple(int(rng.choice((4, 8, 16, 32))) for _idx in range(target))
            board = _board_for_merge_values(
                rng=rng,
                direction=str(axes.move_direction),
                merge_values=merge_values,
                force_slide_when_no_merge=(target == 0),
            )
        elif query == "score_value":
            board = _board_for_merge_values(
                rng=rng,
                direction=str(axes.move_direction),
                merge_values=_score_decomposition(target),
                force_slide_when_no_merge=(target == 0),
            )
        elif query == "max_tile_value":
            if target < 4 or (target & (target - 1)) != 0:
                raise ValueError(f"max_tile_value target must be a power of two >= 4: {target}")
            board = _board_for_merge_values(
                rng=rng,
                direction=str(axes.move_direction),
                merge_values=(target,),
                max_clutter_value=max(2, int(target) // 2),
            )
        else:
            raise ValueError(f"unsupported 2048 value query: {query}")

        result = simulate_2048_move(board, str(axes.move_direction))
        if not result.moved:
            continue
        if _merge_metric(result, query_id=query) != target:
            continue
        if query == "max_tile_value" and not _unique_max_result(result):
            continue
        all_results = {
            str(direction): simulate_2048_move(board, str(direction))
            for direction in SUPPORTED_2048_DIRECTIONS
        }
        evidence_ids = tuple(coord_to_cell_id(coord) for coord in _evidence_coords_for_query(result, query_id=query))
        sample = Sample2048(
            query_id=query,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=int(target),
            board=board,
            move_direction=str(axes.move_direction),
            move_label_by_direction={},
            goal_cell=None,
            move_result=result,
            all_move_results=all_results,
            evidence_cell_ids=evidence_ids,
            construction_mode=f"single_move_{query}",
        )
        validate_2048_sample(sample)
        return sample
    raise ValueError(f"failed to sample 2048 {query} scene")


def _compatible_goal_directions(goal_cell: Coord) -> Tuple[str, ...]:
    """Return directions that can move a tile directly into the goal corner."""

    row, col = int(goal_cell[0]), int(goal_cell[1])
    directions: list[str] = []
    if int(col) == 0:
        directions.append("left")
    if int(col) == SIZE - 1:
        directions.append("right")
    if int(row) == 0:
        directions.append("up")
    if int(row) == SIZE - 1:
        directions.append("down")
    return tuple(directions)


def _assign_move_labels(*, rng, target_direction: str, target_label: str) -> Dict[str, str]:
    """Assign four visible labels while forcing one target direction label."""

    remaining_labels = [label for label in SUPPORTED_2048_LABELS if str(label) != str(target_label)]
    rng.shuffle(remaining_labels)
    other_directions = [direction for direction in SUPPORTED_2048_DIRECTIONS if str(direction) != str(target_direction)]
    rng.shuffle(other_directions)
    labels = {str(target_direction): str(target_label)}
    for direction, label in zip(other_directions, remaining_labels[: len(other_directions)]):
        labels[str(direction)] = str(label)
    return labels


def _sample_best_move_scene(*, rng, axes: _ResolvedAxes) -> Sample2048:
    """Construct a candidate-arrow query with one best move for the outlined goal cell."""

    target_label = str(axes.target_label or "A")
    goal_cell = goal_cell_name_to_coord(str(axes.goal_cell_name))
    compatible = _compatible_goal_directions(goal_cell)
    target_direction = str(axes.move_direction) if str(axes.move_direction) in compatible else str(rng.choice(compatible))
    line_index = int(goal_cell[0]) if target_direction in {"left", "right"} else int(goal_cell[1])

    for _attempt in range(96):
        lines = [_non_merging_line(rng, max_value=32) for _idx in range(SIZE)]
        lines[line_index] = (64, 64, EMPTY, EMPTY)
        board = _board_from_move_order(lines, direction=target_direction)
        results = {
            str(direction): simulate_2048_move(board, str(direction))
            for direction in SUPPORTED_2048_DIRECTIONS
        }
        values = {
            str(direction): int(result.after[int(goal_cell[0])][int(goal_cell[1])])
            for direction, result in results.items()
        }
        best_value = max(values.values())
        best_dirs = [direction for direction, value in values.items() if int(value) == int(best_value)]
        if best_dirs != [target_direction] or int(best_value) <= 0:
            continue
        sources = tuple(results[target_direction].result_sources.get(goal_cell, tuple()))
        if not sources:
            continue
        move_labels = _assign_move_labels(rng=rng, target_direction=target_direction, target_label=target_label)
        evidence_ids = tuple(coord_to_cell_id(coord) for coord in sources)
        sample = Sample2048(
            query_id="best_move_label",
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=str(target_label),
            board=board,
            move_direction=str(target_direction),
            move_label_by_direction=move_labels,
            goal_cell=goal_cell,
            move_result=results[target_direction],
            all_move_results=results,
            evidence_cell_ids=evidence_ids,
            construction_mode="candidate_move_maximizes_goal_cell_value",
        )
        validate_2048_sample(sample)
        return sample
    raise ValueError("failed to sample 2048 best-move scene")


def _sample_scene(*, rng, axes: _ResolvedAxes) -> Sample2048:
    """Construct one 2048 scene for the requested query."""

    if str(axes.query_id) in MOVE_RESULT_QUERY_IDS:
        return _sample_move_result_scene(rng=rng, axes=axes)
    if str(axes.query_id) == "best_move_label":
        return _sample_best_move_scene(rng=rng, axes=axes)
    raise ValueError(f"unsupported 2048 query_id: {axes.query_id}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for 2048 JSON output."""

    if str(query_id) == "best_move_label":
        answer_value: str | int = "D"
        evidence_value = [[224, 224, 344, 344], [358, 224, 478, 344]]
    elif str(query_id) == "merge_count":
        answer_value = 2
        evidence_value = [[224, 224, 344, 344], [358, 224, 478, 344]]
    elif str(query_id) == "score_value":
        answer_value = 24
        evidence_value = [[224, 224, 344, 344], [358, 224, 478, 344]]
    else:
        answer_value = 128
        evidence_value = [[224, 224, 344, 344], [358, 224, 478, 344]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _move_result_trace(result: Move2048Result) -> Dict[str, Any]:
    """Serialize one 2048 move result into JSON-compatible trace data."""

    return {
        "direction": str(result.direction),
        "after": [[int(value) for value in row] for row in result.after],
        "merge_pairs": [
            [[int(a[0]), int(a[1])], [int(b[0]), int(b[1])]]
            for a, b in result.merge_pairs
        ],
        "score": int(result.score),
        "moved": bool(result.moved),
        "result_sources": [
            {
                "dest": [int(dest[0]), int(dest[1])],
                "sources": [[int(source[0]), int(source[1])] for source in sources],
            }
            for dest, sources in sorted(result.result_sources.items())
        ],
    }


class Games2048BoardTask:
    """Return one grounded query over a visible 2048 board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "2048"
    supported_query_ids: Tuple[str, ...] = SUPPORTED_2048_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(
            int(instance_seed),
            params=params,
            supported_query_ids=tuple(self.supported_query_ids),
        )
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: Sample2048 | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid 2048 board after {max_attempts} attempts")

        allowed_panel_treatments_raw = params.get(
            "panel_scene_treatments",
            group_default(_RENDER_DEFAULTS, "panel_scene_treatments", None),
        )
        if isinstance(allowed_panel_treatments_raw, str):
            allowed_panel_treatments = (str(allowed_panel_treatments_raw),)
        elif allowed_panel_treatments_raw is None:
            allowed_panel_treatments = None
        else:
            allowed_panel_treatments = tuple(str(item) for item in allowed_panel_treatments_raw)
        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.2048_board.panel_scene_style",
            treatments=allowed_panel_treatments,
            treatment_weights=params.get(
                "panel_scene_treatment_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_treatment_weights", None),
            ),
            palette_weights=params.get(
                "panel_scene_palette_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_palette_weights", None),
            ),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_2048_board_scene(
            board=sampled_scene.board,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
            move_direction=None if str(axes.query_id) == "best_move_label" else str(sampled_scene.move_direction),
            move_label_by_direction=sampled_scene.move_label_by_direction if str(axes.query_id) == "best_move_label" else None,
            goal_cell=sampled_scene.goal_cell,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_cell_ids
        ]
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
                "object_description_standard_board",
                "move_rule_text",
                "score_rule_text",
                "goal_rule_text",
                "answer_hint_merge_count",
                "evidence_hint_merge_count",
                "answer_hint_score_value",
                "evidence_hint_score_value",
                "answer_hint_max_tile_value",
                "evidence_hint_max_tile_value",
                "answer_hint_best_move_label",
                "evidence_hint_best_move_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "move_rule_text": str(prompt_defaults["move_rule_text"]),
                "score_rule_text": str(prompt_defaults["score_rule_text"]),
                "goal_rule_text": str(prompt_defaults["goal_rule_text"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = (
            TypedValue(type="string", value=str(sampled_scene.answer))
            if str(axes.query_id) == "best_move_label"
            else TypedValue(type="integer", value=int(sampled_scene.answer))
        )
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        filled_count = sum(1 for row in sampled_scene.board for value in row if int(value) != EMPTY)
        complexity = build_games_2048_board_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            filled_count=int(filled_count),
            merge_count=int(len(sampled_scene.move_result.merge_pairs)),
            target_answer=sampled_scene.answer,
            evidence_count=len(sampled_scene.evidence_cell_ids),
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_2048_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "move_direction": str(sampled_scene.move_direction),
                    "goal_cell": None if sampled_scene.goal_cell is None else [int(sampled_scene.goal_cell[0]), int(sampled_scene.goal_cell[1])],
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_cell_ids],
                },
            },
            "query_spec": {
                "query_id": str(axes.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "move_direction": str(sampled_scene.move_direction),
                    "goal_cell": str(axes.goal_cell_name),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "move_direction_probabilities": dict(axes.move_direction_probabilities),
                    "goal_cell_probabilities": dict(axes.goal_cell_probabilities),
                    "target_answer": axes.target_answer,
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "target_label": axes.target_label,
                    "target_label_support": [str(value) for value in axes.target_label_support],
                    "target_label_probabilities": dict(axes.target_label_probabilities),
                    "filled_count": int(filled_count),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "effective_cell_size_px": rendered_scene.render_map.get("effective_cell_size_px"),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "board_before": [[int(value) for value in row] for row in sampled_scene.board],
                "move_direction": str(sampled_scene.move_direction),
                "move_label_by_direction": dict(sampled_scene.move_label_by_direction),
                "goal_cell": None if sampled_scene.goal_cell is None else [int(sampled_scene.goal_cell[0]), int(sampled_scene.goal_cell[1])],
                "move_result": _move_result_trace(sampled_scene.move_result),
                "all_move_results": {
                    str(direction): _move_result_trace(result)
                    for direction, result in sampled_scene.all_move_results.items()
                },
                "answer": sampled_scene.answer,
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_cell_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_cell_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="2048",
            query_id=str(axes.query_id),
        )


@register_task
class Games2048MoveResultValueTask(Games2048BoardTask):
    """Answer integer questions about one shown 2048 move."""

    task_id = "task_games__2048__move_result_value"
    supported_query_ids = MOVE_RESULT_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        output = super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts))
        query_id = str(output.query_id)
        payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
        probabilities = None
        query_spec = payload.get("query_spec") if isinstance(payload, Mapping) else None
        if isinstance(query_spec, Mapping):
            spec_params = query_spec.get("params")
            if isinstance(spec_params, Mapping):
                raw_probabilities = spec_params.get("query_id_probabilities")
                if isinstance(raw_probabilities, Mapping):
                    probabilities = {str(key): float(value) for key, value in raw_probabilities.items()}
        return rewrite_public_query_output(output, query_id=query_id, query_id_probabilities=probabilities)


@register_task
class Games2048BestMoveLabelTask(FixedQueryVariantTaskMixin, Games2048BoardTask):
    """Choose the labeled 2048 move that maximizes the outlined goal-cell value."""

    task_id = "task_games__2048__best_move_label"
    fixed_query_id = "best_move_label"
    supported_query_ids = ("best_move_label",)


__all__ = [
    "Games2048BestMoveLabelTask",
    "Games2048BoardTask",
    "Games2048MoveResultValueTask",
]
