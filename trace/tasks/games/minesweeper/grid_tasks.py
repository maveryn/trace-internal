"""Games Minesweeper-grid tasks for local deduction and clue satisfaction."""

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
from ..shared.complexity import build_games_minesweeper_grid_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.fixed_query_task import rewrite_public_query_output
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.minesweeper_common import (
    SUPPORTED_MINESWEEPER_QUERY_IDS,
    SUPPORTED_MINESWEEPER_SCENE_VARIANTS,
    Coord,
    MinesweeperSample,
    adjacent_flag_count,
    all_coords,
    clue_context_flags,
    clue_number,
    coord_to_cell_id,
    forced_mine_supports,
    forced_safe_supports,
    neighbor_coords,
    satisfied_clue_coords,
    sorted_coords,
    unsatisfied_clue_coords,
    validate_board_contract,
)
from ..shared.minesweeper_scene import MinesweeperRenderParams, render_minesweeper_grid_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_MINESWEEPER_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_minesweeper_grid_base"
REVEAL_OUTCOME_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
REVEAL_OUTCOME_VOCAB: Tuple[str, ...] = ("mine", "empty", "1", "2", "3", "4", "5", "6", "7", "8")
REVEAL_OUTCOME_BY_CODE: Dict[int, str] = {
    0: "mine",
    1: "empty",
    2: "1",
    3: "2",
    4: "3",
    5: "4",
    6: "5",
    7: "6",
    8: "7",
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Minesweeper scenes."""

    forced_mine_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    forced_safe_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    remaining_mine_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    reveal_outcome_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8)
    reveal_outcome_option_count_support: Tuple[int, ...] = (4, 6)
    satisfied_clue_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    board_size_support: Tuple[int, ...] = (4, 5, 6, 7, 8)
    forced_cell_board_size_support: Tuple[int, ...] = (4, 5)
    reveal_outcome_board_size_support: Tuple[int, ...] = (5, 6, 7, 8)
    open_min_distractor_hidden_count: int = 2
    open_max_distractor_hidden_count: int = 4
    mixed_min_distractor_hidden_count: int = 4
    mixed_max_distractor_hidden_count: int = 8
    canvas_width: int = 900
    canvas_height: int = 900
    panel_margin_px: int = 56
    max_board_size_px: int = 720
    board_border_width_px: int = 5
    grid_line_width_px: int = 2
    cell_padding_px: int = 6
    number_font_size_px: int = 48


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Minesweeper instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    board_size: int
    target_answer: int | None
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    board_size_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    reveal_outcome_option_count: int = 0
    reveal_outcome_option_count_support: Tuple[int, ...] = tuple()
    reveal_outcome_option_count_probabilities: Dict[str, float] | None = None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "minesweeper")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="minesweeper", apply_prob=0.5)


def _target_support_key(query_id: str) -> str | None:
    """Return the configured answer-support key for one Minesweeper query."""

    return {
        "forced_mine_count": "forced_mine_count_support",
        "forced_safe_count": "forced_safe_count_support",
        "remaining_mine_count": "remaining_mine_count_support",
        "reveal_outcome_label": "reveal_outcome_support",
        "satisfied_clue_count": "satisfied_clue_count_support",
    }[str(query_id)]


def _board_size_support_key(supported_query_ids: Sequence[str]) -> str:
    """Return the board-size support key for the active Minesweeper task."""

    supported = tuple(str(value) for value in supported_query_ids)
    if set(supported) == {"forced_mine_count", "forced_safe_count"}:
        return "forced_cell_board_size_support"
    if set(supported) == {"reveal_outcome_label"}:
        return "reveal_outcome_board_size_support"
    return "board_size_support"


def _uses_uniform_query_cycle(
    params: Mapping[str, Any],
    probabilities: Mapping[str, float],
    *,
    supported_query_ids: Sequence[str] = SUPPORTED_MINESWEEPER_QUERY_IDS,
) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_variant") is not None:
        return False
    enabled = bool(
        params.get(
            "balanced_query_id_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True),
        )
    )
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
    supported_query_ids: Sequence[str] = SUPPORTED_MINESWEEPER_QUERY_IDS,
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner axes."""

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


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str] = SUPPORTED_MINESWEEPER_QUERY_IDS,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Minesweeper query id."""

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
    supported: Tuple[str, ...],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named Minesweeper axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=supported,
    )


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str] = SUPPORTED_MINESWEEPER_QUERY_IDS,
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Minesweeper instance."""

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
        params=cycle_params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_MINESWEEPER_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_MINESWEEPER_STYLE_VARIANTS,
    )
    board_size_support_key = _board_size_support_key(supported_query_ids)
    board_size, board_size_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(board_size_support_key),
        explicit_key="board_size",
        fallback_support=getattr(_DEFAULTS, str(board_size_support_key)),
        namespace=f"{TASK_ID}.board_size.{str(board_size_support_key)}",
        balanced_flag_key="balanced_board_size_sampling",
        namespace_support_permutation=True,
    )
    support_key = _target_support_key(str(query_id))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=getattr(_DEFAULTS, support_key),
    )
    reveal_outcome_option_count = 0
    reveal_outcome_option_count_support: Tuple[int, ...] = tuple()
    reveal_outcome_option_count_probabilities: Dict[str, float] = {}
    if str(query_id) == "reveal_outcome_label":
        reveal_outcome_option_count, reveal_outcome_option_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="reveal_outcome_option_count_support",
            explicit_key="option_count",
            fallback_support=_DEFAULTS.reveal_outcome_option_count_support,
            namespace=f"{TASK_ID}.reveal_outcome_option_count",
            balanced_flag_key="balanced_reveal_outcome_option_count_sampling",
            namespace_support_permutation=True,
        )
        reveal_outcome_option_count_support = resolve_integer_support(
            cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            key="reveal_outcome_option_count_support",
            fallback=_DEFAULTS.reveal_outcome_option_count_support,
        )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        board_size=int(board_size),
        target_answer=None if target_answer is None else int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        board_size_probabilities=dict(board_size_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        reveal_outcome_option_count=int(reveal_outcome_option_count),
        reveal_outcome_option_count_support=tuple(int(value) for value in reveal_outcome_option_count_support),
        reveal_outcome_option_count_probabilities=dict(reveal_outcome_option_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> MinesweeperRenderParams:
    """Resolve Minesweeper rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.minesweeper.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.minesweeper.layout",
        ),
        unit_scale_meta,
    )
    max_board_size_px = scale_games_px(
        params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)),
        unit_scale,
        min_px=360,
    )
    default_canvas_width = int(group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))
    default_canvas_height = int(group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))
    canvas_size = int(max(500, min(max(default_canvas_width, default_canvas_height), int(max_board_size_px) + 160)))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.minesweeper.font_family",
        params=params,
    )
    return MinesweeperRenderParams(
        canvas_width=int(params.get("canvas_width", canvas_size)),
        canvas_height=int(params.get("canvas_height", canvas_size)),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_size_px=int(max_board_size_px),
        board_border_width_px=scale_games_px(params.get("board_border_width_px", group_default(_RENDER_DEFAULTS, "board_border_width_px", _DEFAULTS.board_border_width_px)), unit_scale, min_px=2),
        grid_line_width_px=scale_games_px(params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", _DEFAULTS.grid_line_width_px)), unit_scale, min_px=1),
        cell_padding_px=scale_games_px(params.get("cell_padding_px", group_default(_RENDER_DEFAULTS, "cell_padding_px", _DEFAULTS.cell_padding_px)), unit_scale, min_px=3),
        number_font_size_px=scale_games_px(params.get("number_font_size_px", group_default(_RENDER_DEFAULTS, "number_font_size_px", _DEFAULTS.number_font_size_px)), unit_scale, min_px=18),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
        instance_seed=int(instance_seed),
    )


def _distractor_bounds(scene_variant: str) -> Tuple[int, int]:
    """Return hidden-distractor count bounds for one scene variant."""

    if str(scene_variant) == "mixed_grid":
        return int(_DEFAULTS.mixed_min_distractor_hidden_count), int(_DEFAULTS.mixed_max_distractor_hidden_count)
    return int(_DEFAULTS.open_min_distractor_hidden_count), int(_DEFAULTS.open_max_distractor_hidden_count)


def _choose_distractors(
    *,
    rng,
    size: int,
    clue_cell: Coord,
    occupied: set[Coord],
    scene_variant: str,
) -> Tuple[Coord, ...]:
    """Choose non-local hidden distractor cells away from the forcing clue."""

    local = set(neighbor_coords(clue_cell, size=int(size)))
    local.add(clue_cell)
    candidates = [coord for coord in all_coords(size=int(size)) if coord not in occupied and coord not in local]
    rng.shuffle(candidates)
    low, high = _distractor_bounds(str(scene_variant))
    count = int(rng.randint(min(int(low), len(candidates)), min(int(high), len(candidates)))) if candidates else 0
    return tuple(sorted(candidates[:count]))


def _chebyshev_distance(a: Coord, b: Coord) -> int:
    """Return grid Chebyshev distance between two coordinates."""

    return max(abs(int(a[0]) - int(b[0])), abs(int(a[1]) - int(b[1])))


def _build_state(
    *,
    size: int,
    mine_coords: set[Coord],
    flagged_coords: set[Coord],
    hidden_coords: set[Coord],
) -> Tuple[Tuple[Coord, ...], Tuple[Coord, ...], Tuple[Coord, ...], Tuple[Coord, ...]]:
    """Return canonical mine/revealed/flagged/hidden partitions."""

    revealed_coords = set(all_coords(size=int(size))) - set(hidden_coords) - set(flagged_coords)
    validate_board_contract(
        size=int(size),
        mine_coords=tuple(mine_coords),
        revealed_coords=tuple(revealed_coords),
        flagged_coords=tuple(flagged_coords),
        hidden_coords=tuple(hidden_coords),
    )
    return (
        sorted_coords(mine_coords),
        sorted_coords(revealed_coords),
        sorted_coords(flagged_coords),
        sorted_coords(hidden_coords),
    )


def _supporting_annotation(
    *,
    size: int,
    forced_cells: Tuple[Coord, ...],
    support_map: Mapping[Coord, Tuple[Coord, ...]],
    flagged_coords: Tuple[Coord, ...],
) -> Tuple[Tuple[Coord, ...], Tuple[Coord, ...]]:
    """Return clue witnesses and full annotation coordinates for forced cells."""

    clue_coords: set[Coord] = set()
    for coord in forced_cells:
        clue_coords.update(support_map.get(coord, ()))
    context_flags = set(clue_context_flags(clue_coords=clue_coords, flagged_coords=flagged_coords, size=int(size)))
    annotation = set(forced_cells)
    annotation.update(clue_coords)
    annotation.update(context_flags)
    return sorted_coords(clue_coords), sorted_coords(annotation)


def _make_local_rule_sample(
    *,
    rng,
    axes: _ResolvedAxes,
    force_kind: str,
    target_count: int,
) -> MinesweeperSample:
    """Construct one board around a local forced-mine or forced-safe clue."""

    size = int(axes.board_size)
    interior = [(row, col) for row in range(1, size - 1) for col in range(1, size - 1)]
    clue_cell = tuple(rng.choice(interior))
    neighbors = list(neighbor_coords(clue_cell, size=int(size)))
    rng.shuffle(neighbors)
    hidden_targets = set(tuple(coord) for coord in neighbors[: int(target_count)])
    remaining_neighbors = [coord for coord in neighbors if coord not in hidden_targets]
    if str(force_kind) == "safe":
        flag_count = int(rng.randint(1, max(1, min(3, len(remaining_neighbors)))))
    else:
        max_flags = min(2, len(remaining_neighbors))
        flag_count = int(rng.randint(0, max_flags)) if max_flags > 0 else 0
    flagged_coords = set(tuple(coord) for coord in remaining_neighbors[: int(flag_count)])
    occupied = set(hidden_targets) | set(flagged_coords) | {clue_cell}
    distractors = set(_choose_distractors(
        rng=rng,
        size=int(size),
        clue_cell=clue_cell,
        occupied=occupied,
        scene_variant=str(axes.scene_variant),
    ))
    hidden_coords = set(hidden_targets) | set(distractors)
    if str(force_kind) == "mine":
        mine_coords = set(hidden_targets) | set(flagged_coords)
    elif str(force_kind) == "safe":
        mine_coords = set(distractors) | set(flagged_coords)
    else:
        raise ValueError(f"unsupported Minesweeper force_kind: {force_kind}")
    mine_coords, revealed_coords, flagged_coords_tuple, hidden_coords_tuple = _build_state(
        size=int(size),
        mine_coords=mine_coords,
        flagged_coords=set(flagged_coords),
        hidden_coords=hidden_coords,
    )
    mine_support = forced_mine_supports(
        size=int(size),
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords_tuple,
        hidden_coords=hidden_coords_tuple,
    )
    safe_support = forced_safe_supports(
        size=int(size),
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords_tuple,
        hidden_coords=hidden_coords_tuple,
    )
    if str(force_kind) == "mine":
        forced = sorted_coords(mine_support.keys())
        support_map = mine_support
        answer: int | str = int(len(forced))
        query_id = "forced_mine_count"
    else:
        forced = sorted_coords(safe_support.keys())
        support_map = safe_support
        answer = int(len(forced))
        query_id = "forced_safe_count"
    target_set = set(hidden_targets)
    if set(forced) != target_set:
        raise ValueError("constructed Minesweeper forced-cell count does not match target")
    clue_coords, _ = _supporting_annotation(
        size=int(size),
        forced_cells=tuple(forced),
        support_map=support_map,
        flagged_coords=flagged_coords_tuple,
    )
    satisfied = satisfied_clue_coords(
        size=int(size),
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords_tuple,
    )
    unsatisfied = unsatisfied_clue_coords(
        size=int(size),
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords_tuple,
    )
    return MinesweeperSample(
        size=int(size),
        query_id=str(query_id),
        answer=answer,
        mine_coords=tuple(mine_coords),
        revealed_coords=tuple(revealed_coords),
        flagged_coords=tuple(flagged_coords_tuple),
        hidden_coords=tuple(hidden_coords_tuple),
        forced_mine_coords=sorted_coords(mine_support.keys()),
        forced_safe_coords=sorted_coords(safe_support.keys()),
        satisfied_clue_coords=tuple(satisfied),
        unsatisfied_clue_coords=tuple(unsatisfied),
        forcing_clue_coords=tuple(clue_coords),
        annotation_coords=tuple(forced),
        target_answer=int(target_count),
        distractor_hidden_count=len(distractors),
        construction_mode=f"local_forced_{str(force_kind)}",
    )


def _make_remaining_mine_count_sample(
    *,
    rng,
    axes: _ResolvedAxes,
    target_count: int,
) -> MinesweeperSample:
    """Construct one board asking for remaining adjacent mines around one clue."""

    size = int(axes.board_size)
    target = int(target_count)
    if target < 0 or target > 5:
        raise ValueError(f"unsupported remaining mine target count: {target}")

    interior = [(row, col) for row in range(1, size - 1) for col in range(1, size - 1)]
    if not interior:
        raise ValueError("remaining mine count requires an interior clue cell")

    for _attempt in range(256):
        clue_cell = tuple(rng.choice(interior))
        neighbors = list(neighbor_coords(clue_cell, size=int(size)))
        rng.shuffle(neighbors)
        if int(target) == 0:
            max_flags = min(4, len(neighbors) - 1)
            if max_flags < 1:
                continue
            flag_count = int(rng.randint(1, max_flags))
            max_hidden_safe = min(4, len(neighbors) - int(flag_count))
            if max_hidden_safe < 1:
                continue
            hidden_safe_count = int(rng.randint(1, max_hidden_safe))
        else:
            max_flags = min(3, len(neighbors) - int(target) - 1)
            if max_flags < 0:
                continue
            flag_count = int(rng.randint(0, max_flags))
            max_extra_safe = min(3, len(neighbors) - int(flag_count) - int(target))
            if max_extra_safe < 1:
                continue
            hidden_safe_count = int(rng.randint(1, max_extra_safe))

        flagged_coords = set(tuple(coord) for coord in neighbors[:flag_count])
        hidden_mines = set(tuple(coord) for coord in neighbors[flag_count : flag_count + int(target)])
        hidden_safe_start = int(flag_count) + int(target)
        hidden_safe = set(tuple(coord) for coord in neighbors[hidden_safe_start : hidden_safe_start + int(hidden_safe_count)])
        occupied = set(flagged_coords) | set(hidden_mines) | set(hidden_safe) | {clue_cell}
        distractors = set(
            _choose_distractors(
                rng=rng,
                size=int(size),
                clue_cell=clue_cell,
                occupied=occupied,
                scene_variant=str(axes.scene_variant),
            )
        )
        mine_coords, revealed_coords, flagged_coords_tuple, hidden_coords_tuple = _build_state(
            size=int(size),
            mine_coords=set(flagged_coords) | set(hidden_mines),
            flagged_coords=set(flagged_coords),
            hidden_coords=set(hidden_mines) | set(hidden_safe) | set(distractors),
        )
        clue = clue_number(clue_cell, mine_coords=mine_coords, size=int(size))
        flags = adjacent_flag_count(clue_cell, flagged_coords=flagged_coords_tuple, size=int(size))
        if int(clue) <= 0 or int(clue) - int(flags) != int(target):
            continue

        mine_support = forced_mine_supports(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
            hidden_coords=hidden_coords_tuple,
        )
        safe_support = forced_safe_supports(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
            hidden_coords=hidden_coords_tuple,
        )
        satisfied = satisfied_clue_coords(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
        )
        unsatisfied = unsatisfied_clue_coords(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
        )
        return MinesweeperSample(
            size=int(size),
            query_id="remaining_mine_count",
            answer=int(target),
            mine_coords=tuple(mine_coords),
            revealed_coords=tuple(revealed_coords),
            flagged_coords=tuple(flagged_coords_tuple),
            hidden_coords=tuple(hidden_coords_tuple),
            forced_mine_coords=sorted_coords(mine_support.keys()),
            forced_safe_coords=sorted_coords(safe_support.keys()),
            satisfied_clue_coords=tuple(satisfied),
            unsatisfied_clue_coords=tuple(unsatisfied),
            forcing_clue_coords=(clue_cell,),
            annotation_coords=(clue_cell,),
            target_answer=int(target),
            distractor_hidden_count=len(distractors),
            construction_mode="marked_clue_remaining_mine_count",
        )
    raise ValueError("failed to construct Minesweeper remaining-mine-count board")


def _make_satisfied_clue_sample(
    *,
    rng,
    axes: _ResolvedAxes,
    target_count: int,
) -> MinesweeperSample:
    """Construct a board with satisfied and unsatisfied opened number cells."""

    size = int(axes.board_size)
    target = int(target_count)
    if target < 1 or target > 8:
        raise ValueError(f"unsupported satisfied clue target count: {target}")
    for _attempt in range(512):
        all_cells = list(all_coords(size=int(size)))
        if target >= 3 and rng.random() < 0.65:
            first = tuple(rng.choice(all_cells))
            pair_candidates = [
                coord
                for coord in neighbor_coords(first, size=int(size))
                if abs(int(coord[0]) - int(first[0])) + abs(int(coord[1]) - int(first[1])) == 1
            ]
            if not pair_candidates:
                continue
            flagged_seed = {first, tuple(rng.choice(pair_candidates))}
        else:
            flagged_seed = {tuple(rng.choice(all_cells))}

        target_pool: set[Coord] = set()
        for flag_cell in flagged_seed:
            target_pool.update(neighbor_coords(flag_cell, size=int(size)))
        target_pool -= set(flagged_seed)
        if len(target_pool) < target:
            continue

        shuffled_target_pool = list(sorted_coords(target_pool))
        rng.shuffle(shuffled_target_pool)
        visible_satisfied = set(shuffled_target_pool[:target])
        hidden_local_safe = set(shuffled_target_pool[target:])
        blocked = set(flagged_seed) | set(target_pool)
        unflagged_region_candidates = [
            coord
            for coord in all_cells
            if coord not in blocked
            and all(_chebyshev_distance(coord, flag_cell) >= 3 for flag_cell in flagged_seed)
        ]
        unflagged_pair_candidates = [
            (a, b)
            for index, a in enumerate(unflagged_region_candidates)
            for b in unflagged_region_candidates[index + 1:]
            if _chebyshev_distance(a, b) == 1
        ]
        if not unflagged_pair_candidates:
            continue
        unflagged_mines = set(rng.choice(unflagged_pair_candidates))
        occupied = set(blocked) | set(unflagged_mines)
        distractor_candidates = [
            coord
            for coord in all_cells
            if coord not in occupied
            and all(_chebyshev_distance(coord, mine_cell) >= 2 for mine_cell in unflagged_mines)
        ]
        rng.shuffle(distractor_candidates)
        low, high = _distractor_bounds(str(axes.scene_variant))
        remote_count = (
            int(rng.randint(min(int(low), len(distractor_candidates)), min(int(high), len(distractor_candidates))))
            if distractor_candidates
            else 0
        )
        remote_hidden_safe = set(distractor_candidates[:remote_count])

        mine_coords, revealed_coords, flagged_coords_tuple, hidden_coords_tuple = _build_state(
            size=int(size),
            mine_coords=set(flagged_seed) | set(unflagged_mines),
            flagged_coords=set(flagged_seed),
            hidden_coords=set(hidden_local_safe) | set(remote_hidden_safe) | set(unflagged_mines),
        )
        mine_support = forced_mine_supports(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
            hidden_coords=hidden_coords_tuple,
        )
        safe_support = forced_safe_supports(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
            hidden_coords=hidden_coords_tuple,
        )
        satisfied = satisfied_clue_coords(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
        )
        unsatisfied = unsatisfied_clue_coords(
            size=int(size),
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords_tuple,
        )
        if set(satisfied) != set(visible_satisfied):
            continue
        if len(unsatisfied) < max(2, min(4, int(target))):
            continue
        if not any(
            clue_number(coord, mine_coords=mine_coords, size=int(size)) >= 2
            and adjacent_flag_count(coord, flagged_coords=flagged_coords_tuple, size=int(size)) == 0
            for coord in unsatisfied
        ):
            continue
        return MinesweeperSample(
            size=int(size),
            query_id="satisfied_clue_count",
            answer=int(len(satisfied)),
            mine_coords=tuple(mine_coords),
            revealed_coords=tuple(revealed_coords),
            flagged_coords=tuple(flagged_coords_tuple),
            hidden_coords=tuple(hidden_coords_tuple),
            forced_mine_coords=sorted_coords(mine_support.keys()),
            forced_safe_coords=sorted_coords(safe_support.keys()),
            satisfied_clue_coords=tuple(satisfied),
            unsatisfied_clue_coords=tuple(unsatisfied),
            forcing_clue_coords=tuple(satisfied),
            annotation_coords=tuple(satisfied),
            target_answer=int(target),
            distractor_hidden_count=len(remote_hidden_safe),
            construction_mode="exact_satisfied_clue_count_with_unsatisfied_clues",
        )
    raise ValueError("failed to construct Minesweeper satisfied-clue board with unsatisfied clue distractors")


def _reveal_outcome_for_code(code: int) -> str:
    """Return the visible reveal-outcome label for one balanced outcome code."""

    try:
        return str(REVEAL_OUTCOME_BY_CODE[int(code)])
    except KeyError as exc:
        raise ValueError(f"unsupported reveal outcome code: {code}") from exc


def _sample_reveal_outcome_options(*, rng, outcome: str, option_count: int) -> Tuple[Tuple[str, str], ...]:
    """Return labeled image options containing the correct reveal outcome."""

    labels = tuple(str(label) for label in REVEAL_OUTCOME_LABELS[: int(option_count)])
    if len(labels) < 2:
        raise ValueError("Minesweeper reveal-outcome option count must be at least 2")
    distractors = [str(value) for value in REVEAL_OUTCOME_VOCAB if str(value) != str(outcome)]
    rng.shuffle(distractors)
    option_values = [str(outcome), *distractors[: max(0, len(labels) - 1)]]
    rng.shuffle(option_values)
    return tuple((str(label), str(value)) for label, value in zip(labels, option_values))


def _remote_hidden_distractors(
    *,
    rng,
    size: int,
    target_cell: Coord,
    support_clue: Coord,
    occupied: set[Coord],
    scene_variant: str,
) -> set[Coord]:
    """Choose hidden distractors away from the target and its supporting clue."""

    support_neighbors = set(neighbor_coords(support_clue, size=int(size)))
    target_neighbors = set(neighbor_coords(target_cell, size=int(size)))
    candidates = [
        coord
        for coord in all_coords(size=int(size))
        if coord not in occupied
        and coord != support_clue
        and coord not in support_neighbors
        and coord not in target_neighbors
        and _chebyshev_distance(coord, target_cell) >= 2
    ]
    rng.shuffle(candidates)
    low, high = _distractor_bounds(str(scene_variant))
    if not candidates:
        return set()
    count = int(rng.randint(min(int(low), len(candidates)), min(int(high), len(candidates))))
    return set(tuple(coord) for coord in candidates[:count])


def _make_reveal_outcome_sample(
    *,
    rng,
    axes: _ResolvedAxes,
    target_code: int,
    option_count: int,
) -> MinesweeperSample:
    """Construct one board asking for the outcome of revealing one marked hidden cell."""

    size = int(axes.board_size)
    outcome = _reveal_outcome_for_code(int(target_code))
    target_cells = list(all_coords(size=int(size)))
    rng.shuffle(target_cells)
    for target_cell in target_cells:
        target_neighbors = list(neighbor_coords(target_cell, size=int(size)))
        if str(outcome).isdigit() and len(target_neighbors) < int(outcome) + 1:
            continue
        for _attempt in range(96):
            rng.shuffle(target_neighbors)
            flagged_coords: set[Coord] = set()
            mine_coords: set[Coord] = set()
            if str(outcome) == "mine":
                support_clue = tuple(rng.choice(target_neighbors))
                support_candidates = [coord for coord in neighbor_coords(support_clue, size=int(size)) if coord != target_cell]
                rng.shuffle(support_candidates)
                support_flag_count = int(rng.randint(0, min(2, len(support_candidates)))) if support_candidates else 0
                flagged_coords = set(tuple(coord) for coord in support_candidates[:support_flag_count])
                mine_coords = {target_cell} | set(flagged_coords)
            else:
                reveal_count = 0 if str(outcome) == "empty" else int(outcome)
                if reveal_count == 0:
                    possible_supports = list(target_neighbors)
                    rng.shuffle(possible_supports)
                    support_clue = None
                    support_only_flag = None
                    for candidate in possible_supports:
                        support_only_flags = [
                            coord
                            for coord in neighbor_coords(candidate, size=int(size))
                            if coord != target_cell and coord not in set(target_neighbors)
                        ]
                        rng.shuffle(support_only_flags)
                        if support_only_flags:
                            support_clue = tuple(candidate)
                            support_only_flag = tuple(support_only_flags[0])
                            break
                    if support_clue is None or support_only_flag is None:
                        continue
                    flagged_coords = {support_only_flag}
                else:
                    if len(target_neighbors) < reveal_count + 1:
                        continue
                    support_clue = tuple(rng.choice(target_neighbors))
                    flag_candidates = [coord for coord in target_neighbors if coord != support_clue]
                    rng.shuffle(flag_candidates)
                    flagged_coords = set(tuple(coord) for coord in flag_candidates[:reveal_count])
                    if len(flagged_coords) != reveal_count:
                        continue
                    support_adjacent_flags = set(neighbor_coords(support_clue, size=int(size))) & set(flagged_coords)
                    if not support_adjacent_flags:
                        continue
                mine_coords = set(flagged_coords)

            occupied = {target_cell, support_clue} | set(flagged_coords) | set(mine_coords)
            distractors = _remote_hidden_distractors(
                rng=rng,
                size=int(size),
                target_cell=target_cell,
                support_clue=support_clue,
                occupied=occupied,
                scene_variant=str(axes.scene_variant),
            )
            hidden_coords = {target_cell} | set(distractors)
            mine_coords_tuple, revealed_coords, flagged_coords_tuple, hidden_coords_tuple = _build_state(
                size=int(size),
                mine_coords=set(mine_coords),
                flagged_coords=set(flagged_coords),
                hidden_coords=set(hidden_coords),
            )
            mine_support = forced_mine_supports(
                size=int(size),
                mine_coords=mine_coords_tuple,
                revealed_coords=revealed_coords,
                flagged_coords=flagged_coords_tuple,
                hidden_coords=hidden_coords_tuple,
            )
            safe_support = forced_safe_supports(
                size=int(size),
                mine_coords=mine_coords_tuple,
                revealed_coords=revealed_coords,
                flagged_coords=flagged_coords_tuple,
                hidden_coords=hidden_coords_tuple,
            )
            if str(outcome) == "mine":
                if target_cell not in mine_support:
                    continue
                supporting_clues = tuple(mine_support[target_cell])
            else:
                if target_cell not in safe_support:
                    continue
                actual_count = clue_number(target_cell, mine_coords=mine_coords_tuple, size=int(size))
                expected_count = 0 if str(outcome) == "empty" else int(outcome)
                if int(actual_count) != int(expected_count):
                    continue
                supporting_clues = tuple(safe_support[target_cell])

            target_neighbor_flags = set(neighbor_coords(target_cell, size=int(size))) & set(flagged_coords_tuple)
            context_flags = set(
                clue_context_flags(
                    clue_coords=supporting_clues,
                    flagged_coords=flagged_coords_tuple,
                    size=int(size),
                )
            )
            supporting_flags = sorted_coords(set(context_flags) | set(target_neighbor_flags))
            satisfied = satisfied_clue_coords(
                size=int(size),
                mine_coords=mine_coords_tuple,
                revealed_coords=revealed_coords,
                flagged_coords=flagged_coords_tuple,
            )
            unsatisfied = unsatisfied_clue_coords(
                size=int(size),
                mine_coords=mine_coords_tuple,
                revealed_coords=revealed_coords,
                flagged_coords=flagged_coords_tuple,
            )
            options = _sample_reveal_outcome_options(rng=rng, outcome=str(outcome), option_count=int(option_count))
            answer_label = next(label for label, value in options if str(value) == str(outcome))
            annotation_coords = sorted_coords((target_cell, *supporting_clues, *supporting_flags))
            return MinesweeperSample(
                size=int(size),
                query_id="reveal_outcome_label",
                answer=str(answer_label),
                mine_coords=tuple(mine_coords_tuple),
                revealed_coords=tuple(revealed_coords),
                flagged_coords=tuple(flagged_coords_tuple),
                hidden_coords=tuple(hidden_coords_tuple),
                forced_mine_coords=sorted_coords(mine_support.keys()),
                forced_safe_coords=sorted_coords(safe_support.keys()),
                satisfied_clue_coords=tuple(satisfied),
                unsatisfied_clue_coords=tuple(unsatisfied),
                forcing_clue_coords=tuple(supporting_clues),
                annotation_coords=tuple(annotation_coords),
                target_answer=int(target_code),
                distractor_hidden_count=len(distractors),
                construction_mode=f"marked_hidden_cell_reveal_{str(outcome)}",
                target_cell_coord=target_cell,
                supporting_clue_coords=tuple(supporting_clues),
                supporting_flag_coords=tuple(supporting_flags),
                reveal_outcome=str(outcome),
                answer_options=tuple(options),
            )
    raise ValueError("failed to construct Minesweeper reveal-outcome board")


def _sample_scene(*, rng, axes: _ResolvedAxes) -> MinesweeperSample:
    """Construct one Minesweeper scene for the requested axes."""

    if str(axes.query_id) == "forced_mine_count":
        return _make_local_rule_sample(
            rng=rng,
            axes=axes,
            force_kind="mine",
            target_count=int(axes.target_answer or 1),
        )
    if str(axes.query_id) == "forced_safe_count":
        return _make_local_rule_sample(
            rng=rng,
            axes=axes,
            force_kind="safe",
            target_count=int(axes.target_answer or 1),
        )
    if str(axes.query_id) == "remaining_mine_count":
        return _make_remaining_mine_count_sample(
            rng=rng,
            axes=axes,
            target_count=int(axes.target_answer or 0),
        )
    if str(axes.query_id) == "satisfied_clue_count":
        return _make_satisfied_clue_sample(
            rng=rng,
            axes=axes,
            target_count=int(axes.target_answer or 1),
        )
    if str(axes.query_id) == "reveal_outcome_label":
        return _make_reveal_outcome_sample(
            rng=rng,
            axes=axes,
            target_code=int(axes.target_answer or 0),
            option_count=int(axes.reveal_outcome_option_count),
        )
    raise ValueError(f"unsupported Minesweeper query_id: {axes.query_id}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Minesweeper JSON output."""

    if str(query_id) == "remaining_mine_count":
        answer_value = 2
        annotation_value = [[210, 220, 280, 290]]
    elif str(query_id) == "reveal_outcome_label":
        answer_value = "C"
        annotation_value = {
            "target_cell": [[210, 220, 280, 290]],
            "supporting_clues": [[140, 220, 210, 290]],
            "supporting_flags": [[140, 150, 210, 220]],
        }
    else:
        answer_value = 3
        annotation_value = [[140, 220, 210, 290], [210, 220, 280, 290], [280, 220, 350, 290]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesMinesweeperGridTask:
    """Return one grounded query over a visible Minesweeper grid."""

    task_id = TASK_ID
    domain = "games"
    task_group = "minesweeper"
    supported_query_ids: Tuple[str, ...] = SUPPORTED_MINESWEEPER_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(
            int(instance_seed),
            params=params,
            supported_query_ids=tuple(self.supported_query_ids),
        )
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: MinesweeperSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.minesweeper.panel_scene",
            treatment_weights=group_default(_GEN_DEFAULTS, "panel_treatment_weights", {}),
            palette_weights=group_default(_GEN_DEFAULTS, "panel_palette_weights", {}),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_minesweeper_grid_scene(
            size=int(sampled_scene.size),
            mine_coords=sampled_scene.mine_coords,
            revealed_coords=sampled_scene.revealed_coords,
            flagged_coords=sampled_scene.flagged_coords,
            hidden_coords=sampled_scene.hidden_coords,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            highlighted_clue_coords=(
                sampled_scene.forcing_clue_coords
                if str(axes.query_id) in {"forced_mine_count", "forced_safe_count", "remaining_mine_count", "reveal_outcome_label"}
                else ()
            ),
            highlighted_target_coords=(
                (sampled_scene.target_cell_coord,)
                if str(axes.query_id) == "reveal_outcome_label" and sampled_scene.target_cell_coord is not None
                else ()
            ),
            reveal_outcome_options=(
                sampled_scene.answer_options
                if str(axes.query_id) == "reveal_outcome_label"
                else ()
            ),
        )
        annotation_entity_ids = [coord_to_cell_id(coord) for coord in sampled_scene.annotation_coords]
        annotation_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
            for entity_id in annotation_entity_ids
        ]
        keyed_annotation_entity_ids: Dict[str, list[str]] = {}
        keyed_annotation_bboxes: Dict[str, list[list[float]]] = {}
        if str(axes.query_id) == "reveal_outcome_label":
            keyed_annotation_coords: Dict[str, Tuple[Coord, ...]] = {
                "target_cell": ((sampled_scene.target_cell_coord,) if sampled_scene.target_cell_coord is not None else ()),
                "supporting_clues": tuple(sampled_scene.supporting_clue_coords),
                "supporting_flags": tuple(sampled_scene.supporting_flag_coords),
            }
            for role, coords in keyed_annotation_coords.items():
                role_ids = [coord_to_cell_id(coord) for coord in coords]
                keyed_annotation_entity_ids[str(role)] = [str(entity_id) for entity_id in role_ids]
                keyed_annotation_bboxes[str(role)] = [
                    list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
                    for entity_id in role_ids
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
                "object_description_open_grid",
                "object_description_mixed_grid",
                "minesweeper_rule_text",
                "answer_hint_forced_mine_count",
                "answer_hint_forced_safe_count",
                "answer_hint_remaining_mine_count",
                "answer_hint_reveal_outcome_label",
                "answer_hint_satisfied_clue_count",
                "annotation_hint_forced_mine_count",
                "annotation_hint_forced_safe_count",
                "annotation_hint_remaining_mine_count",
                "annotation_hint_reveal_outcome_label",
                "annotation_hint_satisfied_clue_count",
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
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "minesweeper_rule_text": str(prompt_defaults["minesweeper_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if str(axes.query_id) == "reveal_outcome_label":
            answer_gt = TypedValue(type="option_letter", value=str(sampled_scene.answer))
            annotation_gt = TypedValue(
                type="keyed_bbox_set_map",
                value={str(key): [list(bbox) for bbox in value] for key, value in keyed_annotation_bboxes.items()},
            )
        else:
            answer_gt = TypedValue(type="integer", value=sampled_scene.answer)
            annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        target_for_complexity = int(sampled_scene.target_answer or 0)
        complexity = build_games_minesweeper_grid_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            board_size=int(sampled_scene.size),
            hidden_count=len(sampled_scene.hidden_coords),
            target_answer=int(target_for_complexity),
            annotation_count=len(annotation_entity_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_minesweeper_grid_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(sampled_scene.size),
                    "target_answer": sampled_scene.target_answer,
                    "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
                    "keyed_annotation_entity_ids": dict(keyed_annotation_entity_ids),
                    "reveal_outcome": str(sampled_scene.reveal_outcome),
                    "reveal_outcome_option_count": int(len(sampled_scene.answer_options)),
                    "answer_options": [
                        {"label": str(label), "outcome": str(outcome)}
                        for label, outcome in sampled_scene.answer_options
                    ],
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
                    "board_size": int(sampled_scene.size),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "board_size_probabilities": dict(axes.board_size_probabilities),
                    "target_answer": sampled_scene.target_answer,
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "reveal_outcome": str(sampled_scene.reveal_outcome),
                    "reveal_outcome_option_count": int(len(sampled_scene.answer_options)),
                    "reveal_outcome_option_count_support": [int(value) for value in axes.reveal_outcome_option_count_support],
                    "reveal_outcome_option_count_probabilities": dict(axes.reveal_outcome_option_count_probabilities or {}),
                    "answer_options": [
                        {"label": str(label), "outcome": str(outcome)}
                        for label, outcome in sampled_scene.answer_options
                    ],
                    "hidden_count": len(sampled_scene.hidden_coords),
                    "flagged_count": len(sampled_scene.flagged_coords),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(rendered_scene.render_map.get("text_style", {})),
                "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "board_size": int(sampled_scene.size),
                "target_answer": sampled_scene.target_answer,
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "mine_coords": [[int(row), int(col)] for row, col in sampled_scene.mine_coords],
                "revealed_coords": [[int(row), int(col)] for row, col in sampled_scene.revealed_coords],
                "flagged_coords": [[int(row), int(col)] for row, col in sampled_scene.flagged_coords],
                "hidden_coords": [[int(row), int(col)] for row, col in sampled_scene.hidden_coords],
                "forced_mine_coords": [[int(row), int(col)] for row, col in sampled_scene.forced_mine_coords],
                "forced_safe_coords": [[int(row), int(col)] for row, col in sampled_scene.forced_safe_coords],
                "satisfied_clue_coords": [[int(row), int(col)] for row, col in sampled_scene.satisfied_clue_coords],
                "unsatisfied_clue_coords": [[int(row), int(col)] for row, col in sampled_scene.unsatisfied_clue_coords],
                "forcing_clue_coords": [[int(row), int(col)] for row, col in sampled_scene.forcing_clue_coords],
                "annotation_coords": [[int(row), int(col)] for row, col in sampled_scene.annotation_coords],
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
                "keyed_annotation_entity_ids": dict(keyed_annotation_entity_ids),
                "target_cell_coord": (
                    [int(sampled_scene.target_cell_coord[0]), int(sampled_scene.target_cell_coord[1])]
                    if sampled_scene.target_cell_coord is not None
                    else None
                ),
                "supporting_clue_coords": [
                    [int(row), int(col)] for row, col in sampled_scene.supporting_clue_coords
                ],
                "supporting_flag_coords": [
                    [int(row), int(col)] for row, col in sampled_scene.supporting_flag_coords
                ],
                "reveal_outcome": str(sampled_scene.reveal_outcome),
                "reveal_outcome_option_count": int(len(sampled_scene.answer_options)),
                "answer_options": [
                    {"label": str(label), "outcome": str(outcome)}
                    for label, outcome in sampled_scene.answer_options
                ],
                "answer_option_letter": str(sampled_scene.answer) if str(axes.query_id) == "reveal_outcome_label" else "",
                "distractor_hidden_count": int(sampled_scene.distractor_hidden_count),
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "keyed_object_set_map" if str(axes.query_id) == "reveal_outcome_label" else "object_set",
                **(
                    {"ids_by_role": dict(keyed_annotation_entity_ids)}
                    if str(axes.query_id) == "reveal_outcome_label"
                    else {"ids": [str(entity_id) for entity_id in annotation_entity_ids]}
                ),
            },
            "projected_annotation": {
                **(
                    {
                        "type": "keyed_bbox_set_map",
                        "keyed_bbox_set_map": {
                            str(key): [list(bbox) for bbox in value]
                            for key, value in keyed_annotation_bboxes.items()
                        },
                        "pixel_keyed_bbox_set_map": {
                            str(key): [list(bbox) for bbox in value]
                            for key, value in keyed_annotation_bboxes.items()
                        },
                    }
                    if str(axes.query_id) == "reveal_outcome_label"
                    else {"bbox_set": [list(bbox) for bbox in annotation_bboxes]}
                ),
            },
            "background": background_meta,
            "panel_scene_style": dict(panel_style_meta),
            "post_image_noise": post_noise_meta,
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="minesweeper",
            query_id=str(axes.query_id),
        )
        return rewrite_public_query_output(
            output,
            query_id=str(axes.query_id),
            query_id_probabilities=axes.query_id_probabilities,
        )


@register_task
class GamesMinesweeperForcedCellCountTask(GamesMinesweeperGridTask):
    """Count hidden cells forced to be mines or safe by visible clues."""

    task_id = "task_games__minesweeper__forced_cell_count"
    supported_query_ids = ("forced_mine_count", "forced_safe_count")


@register_task
class GamesMinesweeperSatisfiedClueCountTask(FixedQueryVariantTaskMixin, GamesMinesweeperGridTask):
    """Count opened number cells exactly satisfied by adjacent flags."""

    task_id = "task_games__minesweeper__satisfied_clue_count"
    fixed_query_id = "satisfied_clue_count"
    supported_query_ids = ("satisfied_clue_count",)


@register_task
class GamesMinesweeperRemainingMineCountValueTask(FixedQueryVariantTaskMixin, GamesMinesweeperGridTask):
    """Compute how many adjacent mines remain around one marked clue."""

    task_id = "task_games__minesweeper__remaining_mine_count_value"
    fixed_query_id = "remaining_mine_count"
    supported_query_ids = ("remaining_mine_count",)


@register_task
class GamesMinesweeperRevealOutcomeLabelTask(FixedQueryVariantTaskMixin, GamesMinesweeperGridTask):
    """Choose the on-image result option for revealing one marked hidden cell."""

    task_id = "task_games__minesweeper__reveal_outcome_label"
    fixed_query_id = "reveal_outcome_label"
    supported_query_ids = ("reveal_outcome_label",)


__all__ = [
    "GamesMinesweeperForcedCellCountTask",
    "GamesMinesweeperGridTask",
    "GamesMinesweeperRemainingMineCountValueTask",
    "GamesMinesweeperRevealOutcomeLabelTask",
    "GamesMinesweeperSatisfiedClueCountTask",
]
