"""Games Snake tasks over visible grid states."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
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
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import load_font
from ..shared.complexity import build_games_snake_grid_complexity
from ..shared.fixed_query_task import rewrite_public_query_output
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.snake_common import (
    DIRECTION_NAMES,
    PLANNED_MOVE_OUTCOMES,
    SUPPORTED_SNAKE_MOVE_SAFETY_QUERY_IDS,
    SUPPORTED_SNAKE_PATH_OUTCOME_QUERY_IDS,
    SUPPORTED_SNAKE_SCENE_VARIANTS,
    SUPPORTED_SNAKE_STYLE_VARIANTS,
    Coord,
    SnakeSample,
    SnakeSimulation,
    SnakeState,
    all_coords,
    candidate_move_sequences,
    coord_to_cell_id,
    move_sequence_text,
    neighbor_coords,
    safe_next_directions,
    simulate_snake_moves,
    step_coord,
    validate_snake_sample,
    visible_snake_trace,
)
from ..shared.snake_scene import SnakeRenderParams, render_snake_grid_scene
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_snake_grid_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Snake scenes."""

    board_size_support: Tuple[int, ...] = (7, 8, 9, 10)
    body_length_support: Tuple[int, ...] = (5, 6, 7, 8, 9, 10, 11)
    safe_direction_count_support: Tuple[int, ...] = (0, 1, 2, 3)
    planned_move_count_support: Tuple[int, ...] = (3, 4, 5)
    obstacle_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    planned_move_outcome_support: Tuple[str, ...] = PLANNED_MOVE_OUTCOMES
    canvas_width: int = 900
    canvas_height: int = 900
    panel_margin_px: int = 54
    max_board_size_px: int = 720
    board_border_width_px: int = 6
    grid_line_width_px: int = 2
    cell_padding_px: int = 8
    food_radius_px: int = 28
    eye_radius_px: int = 4


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Snake instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    board_size: int
    body_length: int
    planned_move_count: int
    obstacle_count: int
    target_safe_direction_count: int | None
    target_planned_outcome: str | None
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    board_size_probabilities: Dict[str, float]
    body_length_probabilities: Dict[str, float]
    planned_move_count_probabilities: Dict[str, float]
    obstacle_count_probabilities: Dict[str, float]
    target_safe_direction_count_probabilities: Dict[str, float]
    target_planned_outcome_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "snake")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="snake")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="snake", apply_prob=0.5)


def _public_answer_for_query(query_id: str, raw_answer: str | int) -> str | int:
    """Return the public answer value for one Snake query."""

    query = str(query_id)
    if query == "path_result_option_label":
        return str(raw_answer)
    return int(raw_answer)


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Snake query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=tuple(str(value) for value in supported_query_ids),
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
    """Resolve one balanced named Snake axis."""

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
    """Resolve one string-valued support from params/defaults."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    values = (str(raw),) if isinstance(raw, str) else tuple(str(value) for value in raw)
    values = tuple(value for value in values if value)
    if not values:
        raise ValueError(f"{key} must contain at least one value")
    return values


def _resolve_string_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one string-valued support choice."""

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


def _resolve_path_result_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve point-vs-game-over outcomes with roughly 25% game-over targets."""

    support = _string_support(
        params,
        key="planned_move_outcome_support",
        fallback=_DEFAULTS.planned_move_outcome_support,
    )
    explicit = params.get("target_planned_outcome", params.get("target_path_result"))
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"target_planned_outcome={value!r} is not in planned_move_outcome_support")
        return value, {str(item): (1.0 if str(item) == value else 0.0) for item in support}

    if "point" in support and "game_over" in support:
        probabilities = {"point": 0.75, "game_over": 0.25}
        sampling_index = params.get("_sample_cursor")
        balanced = bool(
            params.get(
                "balanced_planned_move_outcome_sampling",
                group_default(_GEN_DEFAULTS, "balanced_planned_move_outcome_sampling", True),
            )
        )
        if balanced and sampling_index is not None:
            return ("game_over" if abs(int(sampling_index)) % 4 == 0 else "point"), probabilities
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.path_result")
        return ("game_over" if float(rng.random()) < 0.25 else "point"), probabilities

    probabilities = {str(item): 1.0 / float(len(support)) for item in support}
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.path_result")
    return str(rng.choice(tuple(support))), probabilities


def _uses_uniform_query_cycle(
    params: Mapping[str, Any],
    probabilities: Mapping[str, float],
    *,
    supported_query_ids: Sequence[str],
) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
        return False
    if not bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True))):
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
    """Cycle answer targets within each query rather than across all queries."""

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


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Snake instance."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported_query_ids,
    )
    cycle_params = _params_for_query_occurrence_cycle(
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
        supported=SUPPORTED_SNAKE_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_SNAKE_STYLE_VARIANTS,
    )
    board_size, board_size_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="board_size_support",
        explicit_key="board_size",
        fallback_support=_DEFAULTS.board_size_support,
        namespace=f"{TASK_ID}.board_size",
        balanced_flag_key="balanced_board_size_sampling",
        namespace_support_permutation=True,
    )
    body_length, body_length_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="body_length_support",
        explicit_key="body_length",
        fallback_support=_DEFAULTS.body_length_support,
        namespace=f"{TASK_ID}.body_length",
        balanced_flag_key="balanced_body_length_sampling",
        namespace_support_permutation=True,
    )
    planned_move_count, planned_move_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="planned_move_count_support",
        explicit_key="planned_move_count",
        fallback_support=_DEFAULTS.planned_move_count_support,
        namespace=f"{TASK_ID}.planned_move_count",
        balanced_flag_key="balanced_planned_move_count_sampling",
        namespace_support_permutation=True,
    )
    obstacle_count, obstacle_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="obstacle_count_support",
        explicit_key="obstacle_count",
        fallback_support=_DEFAULTS.obstacle_count_support,
        namespace=f"{TASK_ID}.obstacle_count",
        balanced_flag_key="balanced_obstacle_count_sampling",
        namespace_support_permutation=True,
    )

    target_safe_direction_count: int | None = None
    target_safe_direction_count_probabilities: Dict[str, float] = {}
    target_planned_outcome: str | None = None
    target_planned_outcome_probabilities: Dict[str, float] = {}

    if str(query_id) == "safe_direction_count":
        target_safe_direction_count, target_safe_direction_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="safe_direction_count_support",
            explicit_key="target_safe_direction_count",
            fallback_support=_DEFAULTS.safe_direction_count_support,
            namespace=f"{TASK_ID}.safe_direction_count",
            balanced_flag_key="balanced_safe_direction_count_sampling",
            namespace_support_permutation=True,
        )
    elif str(query_id) == "path_result_option_label":
        target_planned_outcome, target_planned_outcome_probabilities = _resolve_path_result_choice(
            instance_seed=int(instance_seed),
            params=cycle_params,
        )

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        board_size=int(board_size),
        body_length=int(body_length),
        planned_move_count=int(planned_move_count),
        obstacle_count=int(obstacle_count),
        target_safe_direction_count=None if target_safe_direction_count is None else int(target_safe_direction_count),
        target_planned_outcome=None if target_planned_outcome is None else str(target_planned_outcome),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        board_size_probabilities=dict(board_size_probabilities),
        body_length_probabilities=dict(body_length_probabilities),
        planned_move_count_probabilities=dict(planned_move_count_probabilities),
        obstacle_count_probabilities=dict(obstacle_count_probabilities),
        target_safe_direction_count_probabilities=dict(target_safe_direction_count_probabilities),
        target_planned_outcome_probabilities=dict(target_planned_outcome_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> SnakeRenderParams:
    """Resolve Snake rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.snake.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.snake.layout",
        ),
        unit_scale_meta,
    )
    return SnakeRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_size_px=scale_games_px(params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)), unit_scale, min_px=360),
        board_border_width_px=scale_games_px(params.get("board_border_width_px", group_default(_RENDER_DEFAULTS, "board_border_width_px", _DEFAULTS.board_border_width_px)), unit_scale, min_px=2),
        grid_line_width_px=scale_games_px(params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", _DEFAULTS.grid_line_width_px)), unit_scale, min_px=1),
        cell_padding_px=scale_games_px(params.get("cell_padding_px", group_default(_RENDER_DEFAULTS, "cell_padding_px", _DEFAULTS.cell_padding_px)), unit_scale, min_px=3),
        food_radius_px=scale_games_px(params.get("food_radius_px", group_default(_RENDER_DEFAULTS, "food_radius_px", _DEFAULTS.food_radius_px)), unit_scale, min_px=8),
        eye_radius_px=scale_games_px(params.get("eye_radius_px", group_default(_RENDER_DEFAULTS, "eye_radius_px", _DEFAULTS.eye_radius_px)), unit_scale, min_px=2),
        layout_jitter_meta=layout_jitter,
    )


def _random_snake_state(
    *,
    rng: Any,
    board_size: int,
    body_length: int,
    prefer_edge_head: bool = False,
) -> SnakeState:
    """Construct a random connected visible snake with food on an open cell."""

    size = int(board_size)
    length = max(2, int(body_length) + 1)
    for _attempt in range(260):
        if bool(prefer_edge_head):
            edge = int(rng.randrange(4))
            if edge == 0:
                head = (0, int(rng.randrange(size)))
            elif edge == 1:
                head = (size - 1, int(rng.randrange(size)))
            elif edge == 2:
                head = (int(rng.randrange(size)), 0)
            else:
                head = (int(rng.randrange(size)), size - 1)
        else:
            head = (int(rng.randrange(size)), int(rng.randrange(size)))
        path = [head]
        while len(path) < length:
            candidates = [coord for coord in neighbor_coords(path[-1], size=size) if coord not in set(path)]
            if not candidates:
                break
            candidates = list(candidates)
            rng.shuffle(candidates)
            path.append(candidates[0])
        if len(path) != length:
            continue
        open_cells = [coord for coord in all_coords(size) if coord not in set(path)]
        if not open_cells:
            continue
        food = rng.choice(open_cells)
        return SnakeState(board_size=size, head=head, body=tuple(path[1:]), food=food, obstacles=tuple())
    raise ValueError("failed to construct random Snake state")


def _with_food(state: SnakeState, food: Coord) -> SnakeState:
    """Return `state` with a different food coordinate."""

    return SnakeState(
        board_size=int(state.board_size),
        head=state.head,
        body=tuple(state.body),
        food=(int(food[0]), int(food[1])),
        obstacles=tuple(state.obstacles),
    )


def _with_obstacles(state: SnakeState, obstacles: Sequence[Coord]) -> SnakeState:
    """Return `state` with visible blocked wall cells."""

    return SnakeState(
        board_size=int(state.board_size),
        head=state.head,
        body=tuple(state.body),
        food=state.food,
        obstacles=tuple((int(row), int(col)) for row, col in obstacles),
    )


def _open_cells(state: SnakeState, *, exclude: Iterable[Coord] = ()) -> Tuple[Coord, ...]:
    """Return open board cells not occupied by snake and optional exclusions."""

    excluded = set((int(row), int(col)) for row, col in exclude)
    occupied = {state.head} | set(state.body) | set(state.obstacles) | excluded
    return tuple(coord for coord in all_coords(state.board_size) if coord not in occupied)


def _safe_step_options(state: SnakeState) -> Tuple[Tuple[str, Coord], ...]:
    """Return immediate safe direction and destination pairs."""

    pairs: list[Tuple[str, Coord]] = []
    for direction in DIRECTION_NAMES:
        simulation = simulate_snake_moves(state, (direction,))
        if simulation.outcome in {"safe", "food"} and simulation.traversed_coords:
            pairs.append((str(direction), simulation.traversed_coords[-1]))
    return tuple(pairs)


def _sample_obstacles(
    *,
    rng: Any,
    state: SnakeState,
    count: int,
    exclude: Iterable[Coord] = (),
) -> Tuple[Coord, ...]:
    """Sample blocked wall cells away from the snake, food, and optional cells."""

    excluded = set((int(row), int(col)) for row, col in exclude)
    excluded.add((int(state.food[0]), int(state.food[1])))
    candidates = list(_open_cells(state, exclude=excluded))
    if len(candidates) < int(count):
        raise ValueError("not enough open cells for Snake wall obstacles")
    rng.shuffle(candidates)
    return tuple((int(row), int(col)) for row, col in candidates[: int(count)])


def _planned_evidence_ids(state: SnakeState, simulation: SnakeSimulation) -> Tuple[str, ...]:
    """Return public evidence cell ids for one planned move sequence."""

    coords = tuple(dict.fromkeys(simulation.traversed_coords))
    if coords:
        return tuple(coord_to_cell_id(coord) for coord in coords)
    return (coord_to_cell_id(state.head),)


def _sample_safe_direction_count(*, rng: Any, axes: _ResolvedAxes) -> SnakeSample:
    """Construct a safe-next-direction count sample."""

    target = 2 if axes.target_safe_direction_count is None else int(axes.target_safe_direction_count)
    for _attempt in range(900):
        state = _random_snake_state(
            rng=rng,
            board_size=int(axes.board_size),
            body_length=int(axes.body_length),
            prefer_edge_head=(target <= 2),
        )
        try:
            obstacles = _sample_obstacles(rng=rng, state=state, count=int(axes.obstacle_count))
        except ValueError:
            continue
        state = _with_obstacles(state, obstacles)
        safe_directions = safe_next_directions(state)
        if len(safe_directions) != target:
            continue
        sample = SnakeSample(
            query_id=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=int(len(safe_directions)),
            state=state,
            single_move=None,
            planned_moves=tuple(),
            safe_directions=tuple(safe_directions),
            evidence_cell_ids=tuple(coord_to_cell_id(step_coord(state.head, direction)) for direction in safe_directions),
            target_outcome=None,
            observed_event_step=None,
            construction_mode=f"safe_direction_count_{target}",
        )
        validate_snake_sample(sample)
        return sample
    raise ValueError("failed to construct Snake safe-direction count sample")


def _dummy_food_state(state: SnakeState) -> SnakeState:
    """Place food on a deterministic open cell away from sampled movement paths."""

    open_cells = _open_cells(state)
    if not open_cells:
        raise ValueError("no open cell for dummy food")
    return _with_food(state, open_cells[-1])


def _find_sequence_for_path_result(
    *,
    rng: Any,
    state: SnakeState,
    length: int,
    target_result: str,
) -> Tuple[SnakeState, Tuple[str, ...], SnakeSimulation] | None:
    """Search move sequences for either a final point or a game-over event."""

    search_state = _dummy_food_state(state)
    sequences = list(candidate_move_sequences(int(length)))
    rng.shuffle(sequences)
    for sequence in sequences:
        simulation = simulate_snake_moves(search_state, sequence)
        if simulation.outcome == "food":
            continue
        is_game_over = str(simulation.outcome) in {"body", "wall"}
        is_point = (not is_game_over) and len(simulation.traversed_coords) == int(length)
        if str(target_result) == "game_over" and not is_game_over:
            continue
        if str(target_result) == "point" and not is_point:
            continue

        traversed = set(simulation.traversed_coords)
        open_food = [coord for coord in _open_cells(state) if coord not in traversed]
        if not open_food:
            continue
        final_state = _with_food(state, rng.choice(open_food))
        final_simulation = simulate_snake_moves(final_state, sequence)
        if final_simulation.outcome == "food":
            continue
        final_game_over = str(final_simulation.outcome) in {"body", "wall"}
        final_point = (not final_game_over) and len(final_simulation.traversed_coords) == int(length)
        if str(target_result) == "game_over" and final_game_over:
            return final_state, tuple(sequence), final_simulation
        if str(target_result) == "point" and final_point:
            return final_state, tuple(sequence), final_simulation
    return None


def _point_option_coords(
    *,
    rng: Any,
    state: SnakeState,
    count: int,
    exclude: Iterable[Coord] = (),
) -> Tuple[Coord, ...]:
    """Sample visible in-board cells for path-result point options."""

    excluded = set((int(row), int(col)) for row, col in exclude)
    candidates = [coord for coord in _open_cells(state) if coord not in excluded]
    if len(candidates) < int(count):
        raise ValueError("not enough open cells for Snake point options")
    rng.shuffle(candidates)
    return tuple(candidates[: int(count)])


def _build_path_result_options(
    *,
    rng: Any,
    state: SnakeState,
    target_result: str,
    final_head: Coord,
) -> Tuple[str, Tuple[Mapping[str, object], ...]]:
    """Build four image-visible result options with one game-over card."""

    labels = ["A", "B", "C", "D"]
    answer_label = str(rng.choice(labels))
    game_over_label = answer_label if str(target_result) == "game_over" else str(rng.choice([label for label in labels if label != answer_label]))
    options_by_label: Dict[str, Dict[str, object]] = {
        str(game_over_label): {
            "label": str(game_over_label),
            "kind": "game_over",
            "text": "GAME OVER",
            "is_answer": str(target_result) == "game_over",
        }
    }

    point_labels = [label for label in labels if label != game_over_label]
    point_coords: Dict[str, Coord] = {}
    excluded: set[Coord] = set()
    if str(target_result) == "point":
        point_coords[answer_label] = (int(final_head[0]), int(final_head[1]))
        excluded.add((int(final_head[0]), int(final_head[1])))
    distractor_labels = [label for label in point_labels if label not in point_coords]
    for label, coord in zip(
        distractor_labels,
        _point_option_coords(rng=rng, state=state, count=len(distractor_labels), exclude=excluded),
    ):
        point_coords[str(label)] = (int(coord[0]), int(coord[1]))

    for label in point_labels:
        coord = point_coords[str(label)]
        options_by_label[str(label)] = {
            "label": str(label),
            "kind": "point",
            "coord": [int(coord[0]), int(coord[1])],
            "cell_id": coord_to_cell_id(coord),
            "is_answer": str(target_result) == "point" and str(label) == answer_label,
        }
    return answer_label, tuple(options_by_label[str(label)] for label in labels)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    text: str,
    font: Any,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int] | None = None,
    stroke_width: int = 0,
) -> None:
    """Draw centered text with a robust Pillow text-box fallback."""

    try:
        bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        width = float(bbox[2] - bbox[0])
        height = float(bbox[3] - bbox[1])
        x = float(center[0]) - (width / 2.0) - float(bbox[0])
        y = float(center[1]) - (height / 2.0) - float(bbox[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        x = float(center[0]) - (float(width) / 2.0)
        y = float(center[1]) - (float(height) / 2.0)
    draw.text(
        (x, y),
        str(text),
        font=font,
        fill=fill,
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=stroke_fill,
    )


def _draw_path_result_options(
    *,
    image: Any,
    render_map: Mapping[str, Any],
    sample: SnakeSample,
) -> Tuple[Any, Dict[str, list[float]]]:
    """Draw image-visible A-D result options for the path-result task."""

    out = image.convert("RGBA")
    draw = ImageDraw.Draw(out, "RGBA")
    cell_bboxes = render_map.get("cell_bboxes_px", {})
    board_bbox = tuple(float(v) for v in render_map.get("board_bbox_px", (54, 54, 846, 846)))
    option_bboxes: Dict[str, list[float]] = {}
    cell_width = (float(board_bbox[2]) - float(board_bbox[0])) / max(1.0, float(sample.state.board_size))
    point_font = load_font(max(18, int(round(cell_width * 0.34))), bold=True)
    card_font = load_font(max(18, int(round(cell_width * 0.24))), bold=True)
    label_fill = (17, 24, 39)
    option_fill = (255, 255, 255, 235)
    option_outline = (16, 24, 40, 255)

    game_over_option: Mapping[str, object] | None = None
    for option in sample.result_options:
        label = str(option.get("label", ""))
        if str(option.get("kind")) != "point":
            game_over_option = option
            continue
        cell_id = str(option.get("cell_id", ""))
        if cell_id not in cell_bboxes:
            continue
        bbox = tuple(float(v) for v in cell_bboxes[cell_id])
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        radius = max(15.0, min(float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])) * 0.33)
        marker_bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
        draw.ellipse(marker_bbox, fill=option_fill, outline=option_outline, width=max(3, int(round(radius * 0.16))))
        _draw_centered_text(
            draw,
            center=(cx, cy),
            text=label,
            font=point_font,
            fill=label_fill,
            stroke_fill=(255, 255, 255),
            stroke_width=1,
        )
        option_bboxes[label] = [round(float(value), 3) for value in marker_bbox]

    if game_over_option is not None:
        label = str(game_over_option.get("label", ""))
        canvas_w, canvas_h = out.size
        card_w = min(260.0, max(170.0, (float(board_bbox[2]) - float(board_bbox[0])) * 0.34))
        card_h = max(48.0, min(68.0, float(canvas_h) - float(board_bbox[3]) - 18.0))
        if card_h < 44.0:
            card_h = 52.0
            top = max(10.0, float(board_bbox[1]) - card_h - 16.0)
        else:
            top = float(board_bbox[3]) + 12.0
        left = min(max(14.0, (float(canvas_w) - card_w) / 2.0), float(canvas_w) - card_w - 14.0)
        card_bbox = (left, top, left + card_w, top + card_h)
        draw.rounded_rectangle(card_bbox, radius=12, fill=(250, 250, 250, 238), outline=option_outline, width=3)
        _draw_centered_text(
            draw,
            center=((card_bbox[0] + card_bbox[2]) / 2.0, (card_bbox[1] + card_bbox[3]) / 2.0),
            text=f"{label}: GAME OVER",
            font=card_font,
            fill=label_fill,
            stroke_fill=(255, 255, 255),
            stroke_width=1,
        )
        option_bboxes[label] = [round(float(value), 3) for value in card_bbox]
    return out.convert("RGB"), option_bboxes


def _sample_path_result_option(*, rng: Any, axes: _ResolvedAxes) -> SnakeSample:
    """Construct a planned path-result option sample."""

    target = str(axes.target_planned_outcome or "point")
    for _attempt in range(900):
        state = _random_snake_state(rng=rng, board_size=int(axes.board_size), body_length=int(axes.body_length))
        try:
            obstacles = _sample_obstacles(rng=rng, state=state, count=int(axes.obstacle_count))
        except ValueError:
            continue
        state = _with_obstacles(state, obstacles)
        result = _find_sequence_for_path_result(
            rng=rng,
            state=state,
            length=int(axes.planned_move_count),
            target_result=target,
        )
        if result is None:
            continue
        final_state, sequence, simulation = result
        try:
            answer_label, options = _build_path_result_options(
                rng=rng,
                state=final_state,
                target_result=target,
                final_head=simulation.final_head,
            )
        except ValueError:
            continue
        sample = SnakeSample(
            query_id=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=str(answer_label),
            state=final_state,
            single_move=None,
            planned_moves=tuple(sequence),
            safe_directions=tuple(),
            evidence_cell_ids=_planned_evidence_ids(final_state, simulation),
            target_outcome=str(target),
            observed_event_step=int(simulation.event_step),
            construction_mode=f"path_result_option_{target}",
            result_options=tuple(options),
        )
        validate_snake_sample(sample)
        return sample
    raise ValueError("failed to construct Snake path-result option sample")


def _sample_scene(*, rng: Any, axes: _ResolvedAxes) -> SnakeSample:
    """Construct one Snake sample for the active query."""

    query = str(axes.query_id)
    if query == "safe_direction_count":
        return _sample_safe_direction_count(rng=rng, axes=axes)
    if query == "path_result_option_label":
        return _sample_path_result_option(rng=rng, axes=axes)
    raise ValueError(f"unsupported Snake query_id: {query}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Snake JSON output."""

    if str(query_id) == "safe_direction_count":
        answer: str | int = 2
        evidence = [[338, 332, 410, 404], [482, 332, 554, 404]]
    elif str(query_id) == "path_result_option_label":
        answer = "B"
        evidence = [[410, 332, 482, 404], [482, 332, 554, 404], [554, 332, 626, 404]]
    else:
        answer = 2
        evidence = [[338, 332, 410, 404], [482, 332, 554, 404]]
    return (
        json.dumps({"evidence": evidence, "answer": answer}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesSnakeGridTask:
    """Return one grounded query over a visible Snake grid."""

    task_id = TASK_ID
    domain = "games"
    task_group = "snake"
    supported_query_ids: Tuple[str, ...] = SUPPORTED_SNAKE_MOVE_SAFETY_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params, supported_query_ids=self.supported_query_ids)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: SnakeSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_snake_grid_scene(
            state=sampled_scene.state,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
        )
        render_map = dict(rendered_scene.render_map)
        base_image = rendered_scene.image
        if str(axes.query_id) == "path_result_option_label":
            base_image, option_bboxes = _draw_path_result_options(
                image=base_image,
                render_map=render_map,
                sample=sampled_scene,
            )
            render_map["result_option_bboxes_px"] = dict(option_bboxes)
        evidence_bboxes = [
            list(render_map["cell_bboxes_px"][str(cell_id)])
            for cell_id in sampled_scene.evidence_cell_ids
        ]
        image, post_noise_meta = apply_post_image_noise(
            base_image,
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
                "object_description_square_grid",
                "snake_rule_text",
                "planned_move_wall_evidence_rule_text",
                "answer_hint_safe_direction_count",
                "evidence_hint_safe_direction_count",
                "answer_hint_path_result_option_label",
                "evidence_hint_path_result_option_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        planned_moves_text = move_sequence_text(sampled_scene.planned_moves)
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
                "snake_rule_text": str(prompt_defaults["snake_rule_text"]),
                "planned_move_wall_evidence_rule_text": str(prompt_defaults["planned_move_wall_evidence_rule_text"]),
                "planned_moves": str(planned_moves_text),
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

        public_answer = _public_answer_for_query(str(axes.query_id), sampled_scene.answer)
        if str(axes.query_id) == "path_result_option_label":
            answer_gt = TypedValue(type="option_letter", value=str(public_answer))
        else:
            answer_gt = TypedValue(type="integer", value=int(public_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_snake_grid_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            board_size=int(sampled_scene.state.board_size),
            body_length=len(sampled_scene.state.body),
            planned_move_count=len(sampled_scene.planned_moves),
            evidence_count=len(sampled_scene.evidence_cell_ids),
            target_answer=public_answer,
        )
        simulation_trace = None
        if sampled_scene.planned_moves:
            simulation = simulate_snake_moves(sampled_scene.state, sampled_scene.planned_moves)
            simulation_trace = {
                "outcome": str(simulation.outcome),
                "event_step": int(simulation.event_step),
                "traversed_coords": [[int(row), int(col)] for row, col in simulation.traversed_coords],
                "collision_coord": None if simulation.collision_coord is None else [int(simulation.collision_coord[0]), int(simulation.collision_coord[1])],
                "final_head": [int(simulation.final_head[0]), int(simulation.final_head[1])],
            }
        result_options = [dict(option) for option in sampled_scene.result_options]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_snake_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(sampled_scene.state.board_size),
                    "obstacle_count": len(tuple(sampled_scene.state.obstacles)),
                    "obstacle_cell_ids": [coord_to_cell_id(coord) for coord in sampled_scene.state.obstacles],
                    "evidence_cell_ids": [str(cell_id) for cell_id in sampled_scene.evidence_cell_ids],
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
                    "board_size": int(sampled_scene.state.board_size),
                    "body_length": len(sampled_scene.state.body),
                    "obstacle_count": len(tuple(sampled_scene.state.obstacles)),
                    "obstacle_cell_ids": [coord_to_cell_id(coord) for coord in sampled_scene.state.obstacles],
                    "planned_move_count": len(sampled_scene.planned_moves) if sampled_scene.planned_moves else None,
                    "single_move": sampled_scene.single_move,
                    "planned_moves": [str(move) for move in sampled_scene.planned_moves],
                    "safe_directions": [str(direction) for direction in sampled_scene.safe_directions],
                    "answer_value": public_answer,
                    "result_options": list(result_options),
                    "target_safe_direction_count": axes.target_safe_direction_count,
                    "target_planned_outcome": axes.target_planned_outcome,
                    "target_outcome": sampled_scene.target_outcome,
                    "observed_event_step": sampled_scene.observed_event_step,
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "board_size_probabilities": dict(axes.board_size_probabilities),
                    "body_length_probabilities": dict(axes.body_length_probabilities),
                    "planned_move_count_probabilities": dict(axes.planned_move_count_probabilities),
                    "obstacle_count_probabilities": dict(axes.obstacle_count_probabilities),
                    "target_safe_direction_count_probabilities": dict(axes.target_safe_direction_count_probabilities),
                    "target_planned_outcome_probabilities": dict(axes.target_planned_outcome_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(render_map.get("layout_jitter", {})),
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "state": dict(visible_snake_trace(sampled_scene.state)),
                "single_move": sampled_scene.single_move,
                "planned_moves": [str(move) for move in sampled_scene.planned_moves],
                "planned_move_count": len(sampled_scene.planned_moves) if sampled_scene.planned_moves else None,
                "safe_directions": [str(direction) for direction in sampled_scene.safe_directions],
                "answer_value": public_answer,
                "result_options": list(result_options),
                "target_safe_direction_count": axes.target_safe_direction_count,
                "target_planned_outcome": axes.target_planned_outcome,
                "observed_event_step": sampled_scene.observed_event_step,
                "simulation": simulation_trace,
                "evidence_cell_ids": [str(cell_id) for cell_id in sampled_scene.evidence_cell_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "cell_set",
                "ids": [str(cell_id) for cell_id in sampled_scene.evidence_cell_ids],
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
            scene_id="snake",
            query_id=str(axes.query_id),
        )


def _rewrite_generated_output(output: TaskOutput) -> TaskOutput:
    """Rewrite public Snake query fields to the active query-id contract."""

    query_id = str(output.query_id)
    probabilities = None
    payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
    query_spec = payload.get("query_spec") if isinstance(payload, Mapping) else None
    if isinstance(query_spec, Mapping):
        spec_params = query_spec.get("params")
        if isinstance(spec_params, Mapping):
            raw_probabilities = spec_params.get("query_id_probabilities")
            if isinstance(raw_probabilities, Mapping):
                probabilities = {str(key): float(value) for key, value in raw_probabilities.items()}
    return rewrite_public_query_output(output, query_id=query_id, query_id_probabilities=probabilities)


@register_task
class GamesSnakeMoveSafetyTask(GamesSnakeGridTask):
    """Evaluate immediate Snake move safety from the visible head position."""

    task_id = "task_games__snake__safe_direction_count"
    supported_query_ids = SUPPORTED_SNAKE_MOVE_SAFETY_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _rewrite_generated_output(super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts)))


@register_task
class GamesSnakePathOutcomeTask(GamesSnakeGridTask):
    """Evaluate a listed Snake movement sequence."""

    task_id = "task_games__snake__path_outcome_option_label"
    supported_query_ids = SUPPORTED_SNAKE_PATH_OUTCOME_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _rewrite_generated_output(super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts)))


__all__ = [
    "GamesSnakeGridTask",
    "GamesSnakeMoveSafetyTask",
    "GamesSnakePathOutcomeTask",
]
