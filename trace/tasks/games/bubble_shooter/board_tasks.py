"""Games Bubble-shooter tasks over close-packed bubble grids."""

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
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.bubble_shooter_common import (
    BUBBLE_COLOR_KEYS,
    BUBBLE_OPTION_LABELS,
    SUPPORTED_BUBBLE_SHOOTER_QUERY_IDS,
    SUPPORTED_BUBBLE_SHOOTER_SCENE_VARIANTS,
    SUPPORTED_BUBBLE_SHOOTER_STYLE_VARIANTS,
    Board,
    BubbleShooterOption,
    BubbleShooterSample,
    Coord,
    all_bubble_coords,
    board_from_mapping,
    bubble_entity_id,
    bubble_neighbors,
    compute_shot_outcome,
    landing_slot_entity_id,
    occupied_coords,
    option_entity_id,
    shooter_bubble_entity_id,
    sorted_coords,
    top_connected_occupied,
    validate_bubble_shooter_sample,
)
from ..shared.bubble_shooter_scene import BubbleShooterRenderParams, render_bubble_shooter_scene
from ..shared.complexity import build_games_bubble_shooter_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_bubble_shooter_board_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Bubble-shooter scenes."""

    row_count_support: Tuple[int, ...] = (7, 8, 9)
    col_count_support: Tuple[int, ...] = (8, 9, 10)
    pop_count_support: Tuple[int, ...] = (0, 2, 3, 4, 5)
    drop_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    count_query_max_row_count: int = 7
    option_count_support: Tuple[int, ...] = (4, 5, 6)
    pop_color_label_support: Tuple[str, ...] = BUBBLE_OPTION_LABELS
    canvas_width: int = 980
    canvas_height: int = 820
    panel_margin_px: int = 42
    playfield_width_px: int = 860
    playfield_height_px: int = 720
    playfield_border_width_px: int = 5
    board_top_px: int = 38
    board_height_px: int = 500
    bubble_gap_px: int = 2
    path_width_px: int = 5
    shooter_radius_px: int = 22
    option_radius_px: int = 17
    option_label_font_size_px: int = 22
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 560
    canvas_min_height_px: int = 500
    canvas_side_padding_px: int = 120
    canvas_vertical_padding_px: int = 86


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Bubble-shooter instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    row_count: int
    col_count: int
    target_answer: int | None
    target_label: str | None
    option_count: int
    target_answer_support: Tuple[int, ...]
    target_label_support: Tuple[str, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    row_count_probabilities: Dict[str, float]
    col_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    target_label_probabilities: Dict[str, float]
    option_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "bubble_shooter")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="bubble_shooter", apply_prob=0.5)


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Bubble-shooter query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_BUBBLE_SHOOTER_QUERY_IDS,
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
    """Resolve one balanced named Bubble-shooter axis."""

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


def _string_support(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[str],
) -> Tuple[str, ...]:
    """Resolve a string support list from params/defaults."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    if raw is None:
        raw = tuple(fallback)
    if isinstance(raw, str):
        values = (raw,)
    else:
        values = tuple(str(value) for value in raw)
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


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_BUBBLE_SHOOTER_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner answer axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_BUBBLE_SHOOTER_QUERY_IDS))
    return cycle_params


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Bubble-shooter instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    answer_cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_BUBBLE_SHOOTER_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_BUBBLE_SHOOTER_STYLE_VARIANTS,
    )
    row_count, row_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="row_count_support",
        explicit_key="row_count",
        fallback_support=_DEFAULTS.row_count_support,
        namespace=f"{TASK_ID}.row_count",
        balanced_flag_key="balanced_row_count_sampling",
        namespace_support_permutation=True,
    )
    col_count, col_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="col_count_support",
        explicit_key="col_count",
        fallback_support=_DEFAULTS.col_count_support,
        namespace=f"{TASK_ID}.col_count",
        balanced_flag_key="balanced_col_count_sampling",
        namespace_support_permutation=True,
    )

    target_answer = None
    target_answer_probabilities: Dict[str, float] = {}
    if str(query_id) == "pop_count":
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="pop_count_support",
            fallback=_DEFAULTS.pop_count_support,
        )
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="pop_count_support",
            explicit_key="target_answer",
            fallback_support=_DEFAULTS.pop_count_support,
            namespace=f"{TASK_ID}.target_answer.pop_count",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
    elif str(query_id) == "drop_count":
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="drop_count_support",
            fallback=_DEFAULTS.drop_count_support,
        )
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="drop_count_support",
            explicit_key="target_answer",
            fallback_support=_DEFAULTS.drop_count_support,
            namespace=f"{TASK_ID}.target_answer.drop_count",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
    else:
        target_answer_support = tuple(_DEFAULTS.pop_count_support)

    if str(query_id) in {"pop_count", "drop_count"} and params.get("row_count") is None:
        row_count = min(
            int(row_count),
            int(group_default(_GEN_DEFAULTS, "count_query_max_row_count", _DEFAULTS.count_query_max_row_count)),
        )

    target_label = None
    target_label_probabilities: Dict[str, float] = {}
    target_label_support = _string_support(
        params,
        key="pop_color_label_support",
        fallback=_DEFAULTS.pop_color_label_support,
    )
    option_count = 0
    option_count_probabilities: Dict[str, float] = {}
    if str(query_id) == "pop_color_label":
        option_count, option_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="option_count_support",
            explicit_key="option_count",
            fallback_support=_DEFAULTS.option_count_support,
            namespace=f"{TASK_ID}.option_count",
            balanced_flag_key="balanced_option_count_sampling",
            namespace_support_permutation=True,
        )
        target_label, target_label_probabilities = _resolve_label_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            support_key="pop_color_label_support",
            explicit_key="target_label",
            fallback_support=_DEFAULTS.pop_color_label_support,
            namespace=f"{TASK_ID}.target_label.pop_color_label",
            balanced_flag_key="balanced_target_label_sampling",
        )
        target_index = BUBBLE_OPTION_LABELS.index(str(target_label))
        option_count = max(int(option_count), int(target_index) + 1)

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        row_count=int(row_count),
        col_count=int(col_count),
        target_answer=None if target_answer is None else int(target_answer),
        target_label=None if target_label is None else str(target_label),
        option_count=int(option_count),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        target_label_support=tuple(str(value) for value in target_label_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        row_count_probabilities=dict(row_count_probabilities),
        col_count_probabilities=dict(col_count_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        target_label_probabilities=dict(target_label_probabilities),
        option_count_probabilities=dict(option_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> BubbleShooterRenderParams:
    """Resolve Bubble-shooter rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.bubble_shooter.text_font",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.bubble_shooter.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.bubble_shooter.layout",
        ),
        unit_scale_meta,
    )
    base_canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    base_canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    playfield_width_px = scale_games_px(
        params.get("playfield_width_px", group_default(_RENDER_DEFAULTS, "playfield_width_px", _DEFAULTS.playfield_width_px)),
        unit_scale,
        min_px=430,
    )
    playfield_height_px = scale_games_px(
        params.get("playfield_height_px", group_default(_RENDER_DEFAULTS, "playfield_height_px", _DEFAULTS.playfield_height_px)),
        unit_scale,
        min_px=360,
    )
    dynamic_canvas_enabled = bool(
        params.get(
            "dynamic_canvas_size_enabled",
            group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", _DEFAULTS.dynamic_canvas_size_enabled),
        )
    )
    canvas_width = base_canvas_width
    canvas_height = base_canvas_height
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        canvas_width = min(
            int(base_canvas_width),
            max(
                int(params.get("canvas_min_width_px", group_default(_RENDER_DEFAULTS, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px))),
                int(
                    round(
                        float(playfield_width_px)
                        + (2.0 * float(params.get("canvas_side_padding_px", group_default(_RENDER_DEFAULTS, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px))))
                    )
                ),
            ),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        canvas_height = min(
            int(base_canvas_height),
            max(
                int(params.get("canvas_min_height_px", group_default(_RENDER_DEFAULTS, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px))),
                int(
                    round(
                        float(playfield_height_px)
                        + (2.0 * float(params.get("canvas_vertical_padding_px", group_default(_RENDER_DEFAULTS, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px))))
                    )
                ),
            ),
        )
    return BubbleShooterRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        playfield_width_px=int(playfield_width_px),
        playfield_height_px=int(playfield_height_px),
        playfield_border_width_px=scale_games_px(params.get("playfield_border_width_px", group_default(_RENDER_DEFAULTS, "playfield_border_width_px", _DEFAULTS.playfield_border_width_px)), unit_scale, min_px=2),
        board_top_px=scale_games_px(params.get("board_top_px", group_default(_RENDER_DEFAULTS, "board_top_px", _DEFAULTS.board_top_px)), unit_scale, min_px=19),
        board_height_px=scale_games_px(params.get("board_height_px", group_default(_RENDER_DEFAULTS, "board_height_px", _DEFAULTS.board_height_px)), unit_scale, min_px=250),
        bubble_gap_px=scale_games_px(params.get("bubble_gap_px", group_default(_RENDER_DEFAULTS, "bubble_gap_px", _DEFAULTS.bubble_gap_px)), unit_scale, min_px=1),
        path_width_px=scale_games_px(params.get("path_width_px", group_default(_RENDER_DEFAULTS, "path_width_px", _DEFAULTS.path_width_px)), unit_scale, min_px=2),
        shooter_radius_px=scale_games_px(params.get("shooter_radius_px", group_default(_RENDER_DEFAULTS, "shooter_radius_px", _DEFAULTS.shooter_radius_px)), unit_scale, min_px=11),
        option_radius_px=scale_games_px(params.get("option_radius_px", group_default(_RENDER_DEFAULTS, "option_radius_px", _DEFAULTS.option_radius_px)), unit_scale, min_px=8),
        option_label_font_size_px=scale_games_px(params.get("option_label_font_size_px", group_default(_RENDER_DEFAULTS, "option_label_font_size_px", _DEFAULTS.option_label_font_size_px)), unit_scale, min_px=11),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


def _colors_except(excluded: Sequence[str]) -> Tuple[str, ...]:
    """Return available colors excluding a small set."""

    excluded_set = {str(value) for value in excluded}
    values = tuple(color for color in BUBBLE_COLOR_KEYS if color not in excluded_set)
    return values or tuple(BUBBLE_COLOR_KEYS)


def _make_connected_shape(
    *,
    rng,
    rows: int,
    cols: int,
    start: Coord,
    count: int,
    blocked: set[Coord],
    min_row: int = 1,
    max_row: int | None = None,
) -> Tuple[Coord, ...]:
    """Sample a connected set of grid cells."""

    limit_row = int(rows) - 1 if max_row is None else int(max_row)
    shape: list[Coord] = [tuple(start)]
    seen = {tuple(start)}
    frontier = [tuple(start)]
    while len(shape) < int(count) and frontier:
        rng.shuffle(frontier)
        source = frontier[0]
        candidates = [
            neighbor
            for neighbor in bubble_neighbors(source, rows=rows, cols=cols)
            if neighbor not in seen
            and neighbor not in blocked
            and int(min_row) <= int(neighbor[0]) <= int(limit_row)
        ]
        if not candidates:
            frontier.pop(0)
            continue
        rng.shuffle(candidates)
        coord = tuple(candidates[0])
        seen.add(coord)
        shape.append(coord)
        frontier.append(coord)
    if len(shape) != int(count):
        raise ValueError("failed to construct connected bubble shape")
    return sorted_coords(shape)


def _landing_candidates_for_shape(*, rows: int, cols: int, shape: Sequence[Coord], blocked: set[Coord]) -> Tuple[Coord, ...]:
    """Return empty landing slots adjacent to a shape."""

    shape_set = {tuple(coord) for coord in shape}
    candidates: set[Coord] = set()
    for coord in shape_set:
        for neighbor in bubble_neighbors(coord, rows=rows, cols=cols):
            if neighbor in shape_set or neighbor in blocked:
                continue
            if 1 <= int(neighbor[0]) <= int(rows) - 2:
                candidates.add(neighbor)
    return sorted_coords(candidates)


def _support_path_to_top(*, rng, rows: int, cols: int, start: Coord, blocked: set[Coord]) -> Tuple[Coord, ...]:
    """Return a short occupied support path from a component to the top row."""

    current = tuple(start)
    path: list[Coord] = []
    guard = 0
    while int(current[0]) > 0 and guard < int(rows) * 3:
        guard += 1
        candidates = [
            neighbor
            for neighbor in bubble_neighbors(current, rows=rows, cols=cols)
            if int(neighbor[0]) == int(current[0]) - 1 and neighbor not in blocked
        ]
        if not candidates:
            raise ValueError("failed to construct support path to top")
        rng.shuffle(candidates)
        current = tuple(candidates[0])
        path.append(current)
        blocked.add(current)
    if not path or int(path[-1][0]) != 0:
        raise ValueError("support path did not reach top row")
    return tuple(path)


def _add_top_clutter(
    *,
    rng,
    rows: int,
    cols: int,
    values: Dict[Coord, str],
    protected: set[Coord],
    excluded_colors: Sequence[str],
    scene_variant: str,
) -> None:
    """Add visually dense top-connected clutter without touching protected cells."""

    colors = _colors_except(excluded_colors)
    fill_rows = 3 if str(scene_variant) == "dense_pack" else 2
    for row in range(min(int(rows), int(fill_rows))):
        base_probability = 0.92 if row == 0 else 0.72 if str(scene_variant) == "dense_pack" else 0.52
        for col in range(int(cols)):
            coord = (int(row), int(col))
            if coord in protected or coord in values:
                continue
            if row == 0 or rng.random() < float(base_probability):
                values[coord] = str(rng.choice(colors))


def _assert_top_supported(board: Board) -> None:
    """Reject boards with pre-existing floating bubbles."""

    if set(occupied_coords(board)) != set(top_connected_occupied(board)):
        raise ValueError("bubble shooter board contains unsupported bubbles before the shot")


def _make_no_pop_board(*, rng, axes: _ResolvedAxes, color_key: str) -> Tuple[Board, Coord]:
    """Construct a board where the shown shot attaches but does not pop bubbles."""

    rows, cols = int(axes.row_count), int(axes.col_count)
    values: Dict[Coord, str] = {}
    _add_top_clutter(
        rng=rng,
        rows=rows,
        cols=cols,
        values=values,
        protected=set(),
        excluded_colors=(str(color_key),),
        scene_variant=str(axes.scene_variant),
    )
    occupied = set(values)
    candidates = [
        coord
        for coord in all_bubble_coords(rows, cols)
        if coord not in occupied
        and 1 <= int(coord[0]) <= int(rows) - 2
        and any(neighbor in occupied for neighbor in bubble_neighbors(coord, rows=rows, cols=cols))
    ]
    if not candidates:
        raise ValueError("no landing candidate for no-pop construction")
    rng.shuffle(candidates)
    landing = tuple(candidates[0])
    board = board_from_mapping(rows=rows, cols=cols, values=values)
    _assert_top_supported(board)
    outcome = compute_shot_outcome(board, landing_coord=landing, color_key=str(color_key))
    if outcome.popped_coords or outcome.dropped_coords:
        raise ValueError("constructed no-pop board unexpectedly changed state")
    return board, landing


def _make_pop_board(*, rng, axes: _ResolvedAxes, target: int, color_key: str) -> Tuple[Board, Coord]:
    """Construct a board where one shot pops exactly `target` existing bubbles."""

    if int(target) == 0:
        return _make_no_pop_board(rng=rng, axes=axes, color_key=str(color_key))

    rows, cols = int(axes.row_count), int(axes.col_count)
    start = (int(rng.randint(2, max(2, rows - 3))), int(rng.randint(2, max(2, cols - 3))))
    component = _make_connected_shape(
        rng=rng,
        rows=rows,
        cols=cols,
        start=start,
        count=int(target),
        blocked=set(),
        min_row=1,
        max_row=max(2, rows - 2),
    )
    landing_candidates = list(_landing_candidates_for_shape(rows=rows, cols=cols, shape=component, blocked=set(component)))
    if not landing_candidates:
        raise ValueError("no landing candidate for pop component")
    rng.shuffle(landing_candidates)
    landing = tuple(landing_candidates[0])
    protected = set(component) | {landing}
    values: Dict[Coord, str] = {coord: str(color_key) for coord in component}
    support_blocked = set(protected)
    support = _support_path_to_top(rng=rng, rows=rows, cols=cols, start=component[0], blocked=support_blocked)
    support_colors = _colors_except((str(color_key),))
    for index, coord in enumerate(support):
        values[coord] = str(support_colors[index % len(support_colors)])
    protected.update(support)
    _add_top_clutter(
        rng=rng,
        rows=rows,
        cols=cols,
        values=values,
        protected=protected,
        excluded_colors=(str(color_key),),
        scene_variant=str(axes.scene_variant),
    )
    board = board_from_mapping(rows=rows, cols=cols, values=values)
    _assert_top_supported(board)
    outcome = compute_shot_outcome(board, landing_coord=landing, color_key=str(color_key))
    if len(outcome.popped_coords) != int(target):
        raise ValueError("constructed pop board did not hit target pop count")
    return board, landing


def _make_drop_board(*, rng, axes: _ResolvedAxes, target: int, color_key: str) -> Tuple[Board, Coord]:
    """Construct a board where one shot drops exactly `target` bubbles."""

    rows, cols = int(axes.row_count), int(axes.col_count)
    if int(target) > max(1, (rows - 4) * 2):
        raise ValueError("drop target is too large for this board")
    start = (int(rng.randint(2, max(2, rows - 4))), int(rng.randint(2, max(2, cols - 3))))
    pop_component = _make_connected_shape(
        rng=rng,
        rows=rows,
        cols=cols,
        start=start,
        count=2,
        blocked=set(),
        min_row=1,
        max_row=max(2, rows - 3),
    )
    landing_candidates = list(_landing_candidates_for_shape(rows=rows, cols=cols, shape=pop_component, blocked=set(pop_component)))
    below_candidates = [
        neighbor
        for coord in pop_component
        for neighbor in bubble_neighbors(coord, rows=rows, cols=cols)
        if int(neighbor[0]) > max(int(item[0]) for item in pop_component)
        and neighbor not in set(pop_component)
    ]
    if not landing_candidates or not below_candidates:
        raise ValueError("drop construction needs landing and tail candidates")
    rng.shuffle(landing_candidates)
    rng.shuffle(below_candidates)
    landing = tuple(landing_candidates[0])
    blocked = set(pop_component) | {landing}
    if int(target) > 0:
        tail_seed = next((coord for coord in below_candidates if coord != landing), None)
        if tail_seed is None:
            raise ValueError("drop construction has no tail seed")
        tail = _make_connected_shape(
            rng=rng,
            rows=rows,
            cols=cols,
            start=tail_seed,
            count=int(target),
            blocked=blocked,
            min_row=int(tail_seed[0]),
            max_row=int(rows) - 1,
        )
    else:
        tail = tuple()
    protected = set(pop_component) | set(tail) | {landing}
    support_blocked = set(protected)
    support = _support_path_to_top(rng=rng, rows=rows, cols=cols, start=pop_component[0], blocked=support_blocked)
    protected.update(support)
    values: Dict[Coord, str] = {coord: str(color_key) for coord in pop_component}
    non_shot_colors = _colors_except((str(color_key),))
    tail_color = str(non_shot_colors[1 % len(non_shot_colors)])
    for coord in tail:
        values[coord] = tail_color
    for index, coord in enumerate(support):
        values[coord] = str(non_shot_colors[index % len(non_shot_colors)])
    _add_top_clutter(
        rng=rng,
        rows=rows,
        cols=cols,
        values=values,
        protected=protected,
        excluded_colors=(str(color_key),),
        scene_variant=str(axes.scene_variant),
    )
    board = board_from_mapping(rows=rows, cols=cols, values=values)
    _assert_top_supported(board)
    outcome = compute_shot_outcome(board, landing_coord=landing, color_key=str(color_key))
    if len(outcome.popped_coords) != 2 or len(outcome.dropped_coords) != int(target):
        raise ValueError("constructed drop board did not hit target drop count")
    return board, landing


def _sample_pop_count_scene(*, rng, axes: _ResolvedAxes) -> BubbleShooterSample:
    """Construct a pop-count scene."""

    target = 2 if axes.target_answer is None else int(axes.target_answer)
    color = str(rng.choice(BUBBLE_COLOR_KEYS))
    board, landing = _make_pop_board(rng=rng, axes=axes, target=target, color_key=color)
    outcome = compute_shot_outcome(board, landing_coord=landing, color_key=color)
    sample = BubbleShooterSample(
        row_count=int(axes.row_count),
        col_count=int(axes.col_count),
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        board=board,
        landing_coord=landing,
        shooter_color_key=color,
        answer=int(target),
        target_answer=int(target),
        option_specs=tuple(),
        outcome=outcome,
        evidence_entity_ids=tuple(bubble_entity_id(coord) for coord in outcome.popped_coords),
        construction_mode="single_shot_pop_component",
    )
    validate_bubble_shooter_sample(sample)
    return sample


def _sample_drop_count_scene(*, rng, axes: _ResolvedAxes) -> BubbleShooterSample:
    """Construct a drop-count scene."""

    target = 1 if axes.target_answer is None else int(axes.target_answer)
    color = str(rng.choice(BUBBLE_COLOR_KEYS))
    board, landing = _make_drop_board(rng=rng, axes=axes, target=target, color_key=color)
    outcome = compute_shot_outcome(board, landing_coord=landing, color_key=color)
    sample = BubbleShooterSample(
        row_count=int(axes.row_count),
        col_count=int(axes.col_count),
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        board=board,
        landing_coord=landing,
        shooter_color_key=color,
        answer=int(target),
        target_answer=int(target),
        option_specs=tuple(),
        outcome=outcome,
        evidence_entity_ids=tuple(bubble_entity_id(coord) for coord in outcome.dropped_coords),
        construction_mode="pop_bridge_then_drop_floating_tail",
    )
    validate_bubble_shooter_sample(sample)
    return sample


def _sample_pop_color_scene(*, rng, axes: _ResolvedAxes) -> BubbleShooterSample:
    """Construct a color-option scene with exactly one popping displayed color."""

    target_label = str(axes.target_label or "A")
    option_count = int(axes.option_count or 4)
    target_index = BUBBLE_OPTION_LABELS.index(target_label)
    option_count = max(option_count, target_index + 1)
    colors = list(BUBBLE_COLOR_KEYS)
    rng.shuffle(colors)
    target_color = str(colors[0])
    negative_colors = [color for color in colors[1:] if color != target_color]
    if len(negative_colors) < option_count - 1:
        raise ValueError("not enough distinct option colors")
    target_pop_count = int(rng.randint(2, 5))
    board, landing = _make_pop_board(rng=rng, axes=axes, target=target_pop_count, color_key=target_color)
    option_colors = list(negative_colors[: option_count - 1])
    option_colors.insert(target_index, target_color)
    option_specs = tuple(
        BubbleShooterOption(
            label=str(BUBBLE_OPTION_LABELS[index]),
            color_key=str(color),
            is_answer=bool(index == target_index),
        )
        for index, color in enumerate(option_colors)
    )
    positive = [
        option
        for option in option_specs
        if len(compute_shot_outcome(board, landing_coord=landing, color_key=str(option.color_key)).popped_coords) > 0
    ]
    if len(positive) != 1 or str(positive[0].label) != target_label:
        raise ValueError("constructed color-option board has ambiguous popping option")
    outcome = compute_shot_outcome(board, landing_coord=landing, color_key=target_color)
    evidence_ids = tuple(bubble_entity_id(coord) for coord in outcome.popped_coords)
    sample = BubbleShooterSample(
        row_count=int(axes.row_count),
        col_count=int(axes.col_count),
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        board=board,
        landing_coord=landing,
        shooter_color_key=None,
        answer=str(target_label),
        target_answer=str(target_label),
        option_specs=option_specs,
        outcome=outcome,
        evidence_entity_ids=tuple(evidence_ids),
        construction_mode="one_displayed_color_reaches_pop_threshold",
    )
    validate_bubble_shooter_sample(sample)
    return sample


def _sample_scene(*, rng, axes: _ResolvedAxes) -> BubbleShooterSample:
    """Construct one Bubble-shooter scene for the requested query."""

    query = str(axes.query_id)
    if query == "pop_count":
        return _sample_pop_count_scene(rng=rng, axes=axes)
    if query == "drop_count":
        return _sample_drop_count_scene(rng=rng, axes=axes)
    if query == "pop_color_label":
        return _sample_pop_color_scene(rng=rng, axes=axes)
    raise ValueError(f"unsupported Bubble-shooter query_id: {query}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Bubble-shooter JSON output."""

    if str(query_id) == "pop_color_label":
        answer_value: str | int = "C"
        evidence_value = [[403, 279], [449, 279]]
    elif str(query_id) == "drop_count":
        answer_value = 4
        evidence_value = [[483, 373], [529, 373], [506, 413], [552, 413]]
    else:
        answer_value = 5
        evidence_value = [[373, 237], [419, 237], [396, 277], [442, 277], [488, 277]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesBubbleShooterBoardTask:
    """Return one grounded query over a visible Bubble-shooter board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "bubble_shooter"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: BubbleShooterSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Bubble-shooter scene after {max_attempts} attempts")

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
            namespace="games.bubble_shooter.panel_scene_style",
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
        rendered_scene = render_bubble_shooter_scene(
            board=sampled_scene.board,
            landing_coord=sampled_scene.landing_coord,
            shooter_color_key=sampled_scene.shooter_color_key,
            option_specs=sampled_scene.option_specs,
            query_id=str(axes.query_id),
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
        )
        evidence_points = [
            list(rendered_scene.render_map["entity_centers_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_entity_ids
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
                "object_description_open_pack",
                "object_description_dense_pack",
                "bubble_shooter_rule_text",
                "answer_hint_pop_count",
                "evidence_hint_pop_count",
                "answer_hint_drop_count",
                "evidence_hint_drop_count",
                "answer_hint_pop_color_label",
                "evidence_hint_pop_color_label",
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
                "bubble_shooter_rule_text": str(prompt_defaults["bubble_shooter_rule_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
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
            if str(axes.query_id) == "pop_color_label"
            else TypedValue(type="integer", value=int(sampled_scene.answer))
        )
        evidence_gt = TypedValue(type="point_set", value=[list(point) for point in evidence_points])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        complexity = build_games_bubble_shooter_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            bubble_count=len(occupied_coords(sampled_scene.board)),
            row_count=int(sampled_scene.row_count),
            col_count=int(sampled_scene.col_count),
            target_answer=sampled_scene.answer,
            option_count=len(sampled_scene.option_specs),
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )
        board_trace = [
            {
                "coord": [int(coord[0]), int(coord[1])],
                "bubble_id": bubble_entity_id(coord),
                "color_key": str(sampled_scene.board[coord[0]][coord[1]]),
            }
            for coord in occupied_coords(sampled_scene.board)
        ]
        option_trace = [
            {
                "label": str(option.label),
                "color_key": str(option.color_key),
                "is_answer": bool(option.is_answer),
                "entity_id": option_entity_id(str(option.label)),
            }
            for option in sampled_scene.option_specs
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_bubble_shooter_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "row_count": int(sampled_scene.row_count),
                    "col_count": int(sampled_scene.col_count),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
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
                    "row_count": int(sampled_scene.row_count),
                    "col_count": int(sampled_scene.col_count),
                    "bubble_count": len(occupied_coords(sampled_scene.board)),
                    "option_count": len(sampled_scene.option_specs),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "row_count_probabilities": dict(axes.row_count_probabilities),
                    "col_count_probabilities": dict(axes.col_count_probabilities),
                    "target_answer": sampled_scene.target_answer,
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "target_label": axes.target_label,
                    "target_label_support": [str(value) for value in axes.target_label_support],
                    "target_label_probabilities": dict(axes.target_label_probabilities),
                    "option_count_probabilities": dict(axes.option_count_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "row_count": int(sampled_scene.row_count),
                "col_count": int(sampled_scene.col_count),
                "board_bubbles": board_trace,
                "landing_coord": [int(sampled_scene.landing_coord[0]), int(sampled_scene.landing_coord[1])],
                "shooter_color_key": sampled_scene.shooter_color_key,
                "option_specs": option_trace,
                "outcome": {
                    "color_key": str(sampled_scene.outcome.color_key),
                    "connected_same_color_coords": [[int(row), int(col)] for row, col in sampled_scene.outcome.connected_same_color_coords],
                    "popped_coords": [[int(row), int(col)] for row, col in sampled_scene.outcome.popped_coords],
                    "dropped_coords": [[int(row), int(col)] for row, col in sampled_scene.outcome.dropped_coords],
                },
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
            },
            "projected_evidence": {
                "point_set": [list(point) for point in evidence_points],
                "pixel_point_set": [list(point) for point in evidence_points],
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
            scene_id="bubble_shooter",
            query_id=str(axes.query_id),
        )


@register_task
class GamesBubbleShooterShotEffectCountTask(QuerySubsetTaskMixin, GamesBubbleShooterBoardTask):
    """Count bubbles matching a sampled immediate shot-effect condition."""

    task_id = "task_games__bubble_shooter__shot_effect_count"
    supported_query_ids = (
        "pop_count",
        "drop_count",
    )


@register_task
class GamesBubbleShooterPopColorLabelTask(FixedQueryVariantTaskMixin, GamesBubbleShooterBoardTask):
    """Choose the labeled next-bubble color that would make bubbles pop."""

    task_id = "task_games__bubble_shooter__pop_color_label"
    fixed_query_id = "pop_color_label"


__all__ = [
    "GamesBubbleShooterBoardTask",
    "GamesBubbleShooterPopColorLabelTask",
    "GamesBubbleShooterShotEffectCountTask",
]
