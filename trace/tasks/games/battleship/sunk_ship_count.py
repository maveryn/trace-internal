"""Games Battleship-grid tasks over placed fleet ships and hit markers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

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
from ..shared.battleship_common import (
    BattleshipCandidateOption,
    FLEET_SHAPES,
    SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS,
    SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS,
    SUPPORTED_BATTLESHIP_QUERY_IDS,
    SUPPORTED_BATTLESHIP_SCENE_VARIANTS,
    SUPPORTED_BATTLESHIP_SHIP_STATUS_QUERY_IDS,
    SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS,
    BattleshipSample,
    BattleshipShipPlacement,
    Coord,
    all_coords,
    coord_to_cell_id,
    fleet_shape_by_id,
    matching_fleet_shape_ids,
    shape_orientations,
    sorted_coords,
    validate_battleship_sample,
)
from ..shared.battleship_scene import BattleshipRenderParams, render_battleship_grid_scene
from ..shared.complexity import build_games_battleship_grid_complexity
from ..shared.fixed_query_task import QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_BATTLESHIP_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_battleship_grid_base"
LAST_CELL_QUERY_ID = "last_ship_cell_label"
LAST_CELL_OPTION_LABELS = ("A", "B", "C", "D", "E", "F")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Battleship tracking-grid scenes."""

    sunk_ship_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    partial_ship_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    board_size_support: Tuple[int, ...] = (8, 9, 10)
    min_partial_ship_count: int = 2
    max_partial_ship_count: int = 4
    min_miss_count: int = 7
    max_miss_count: int = 16
    last_ship_cell_option_count_support: Tuple[int, ...] = (4, 5, 6)
    canvas_width: int = 1100
    canvas_height: int = 820
    panel_margin_px: int = 48
    max_board_size_px: int = 650
    board_border_width_px: int = 5
    grid_line_width_px: int = 2
    cell_padding_px: int = 7
    fleet_panel_width_px: int = 310
    board_panel_gap_px: int = 34
    fleet_icon_cell_px: int = 18
    label_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Battleship instance."""

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
    target_ship_id: str = ""
    target_ship_id_probabilities: Dict[str, float] | None = None
    last_ship_cell_option_count: int = 0
    last_ship_cell_option_count_support: Tuple[int, ...] = tuple()
    last_ship_cell_option_count_probabilities: Dict[str, float] | None = None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "battleship")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="battleship", apply_prob=0.0)


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one Battleship query."""

    return {
        "sunk_ship_count": "sunk_ship_count_support",
        "partial_ship_count": "partial_ship_count_support",
    }[str(query_id)]


def _ship_size_for_shape_id(shape_id: str) -> int:
    """Return the number of cells in one fleet shape."""

    shape = fleet_shape_by_id()[str(shape_id)]
    return len(tuple(shape.offsets))


def _cell_status_answer_support_for_ship(shape_id: str) -> Tuple[int, ...]:
    """Return feasible hit/unhit cell counts for one queried fleet shape."""

    return tuple(range(_ship_size_for_shape_id(str(shape_id)) + 1))


def _cell_status_pair_options() -> Tuple[Tuple[str, int], ...]:
    """Return feasible `(target_ship_id, answer)` options for cell-status queries."""

    pairs: list[Tuple[str, int]] = []
    for shape_id in SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS:
        for answer in _cell_status_answer_support_for_ship(str(shape_id)):
            pairs.append((str(shape_id), int(answer)))
    return tuple(pairs)


def _cell_status_pair_index_support() -> Tuple[int, ...]:
    """Return integer support over feasible cell-status pair options."""

    return tuple(range(len(_cell_status_pair_options())))


def _cell_status_target_ship_probabilities(
    pair_options: Sequence[Tuple[str, int]],
) -> Dict[str, float]:
    """Return marginal target-ship probabilities for feasible pair sampling."""

    total = max(1, len(tuple(pair_options)))
    return {
        str(shape_id): float(sum(1 for item, _answer in pair_options if str(item) == str(shape_id)) / total)
        for shape_id in SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS
    }


def _cell_status_answer_probabilities(pair_options: Sequence[Tuple[str, int]]) -> Dict[str, float]:
    """Return marginal answer probabilities for feasible pair sampling."""

    answers = sorted({int(answer) for _shape_id, answer in pair_options})
    total = max(1, len(tuple(pair_options)))
    return {
        str(answer): float(sum(1 for _shape_id, item in pair_options if int(item) == int(answer)) / total)
        for answer in answers
    }


def _cell_status_query_target_status(query_id: str) -> str:
    """Return the requested target-cell status for a named-ship cell query."""

    return {
        "named_ship_hit_cell_count": "hit",
        "named_ship_unhit_cell_count": "unhit",
    }[str(query_id)]


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Battleship query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_BATTLESHIP_QUERY_IDS,
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
    """Resolve one balanced named Battleship axis."""

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


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Battleship instance."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_BATTLESHIP_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_BATTLESHIP_STYLE_VARIANTS,
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
    target_ship_id = ""
    target_ship_id_probabilities: Dict[str, float] = {}
    last_ship_cell_option_count = 0
    last_ship_cell_option_count_support: Tuple[int, ...] = tuple()
    last_ship_cell_option_count_probabilities: Dict[str, float] = {}
    if str(query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS:
        explicit_target_ship_id = params.get("target_ship_id")
        explicit_target_answer = params.get("target_answer")
        pair_options = _cell_status_pair_options()
        if explicit_target_ship_id is None and explicit_target_answer is None:
            pair_index, _pair_probabilities = resolve_integer_choice(
                instance_seed=int(instance_seed),
                params=params,
                gen_defaults=_GEN_DEFAULTS,
                support_key="target_ship_answer_pair_index_support",
                explicit_key="target_ship_answer_pair_index",
                fallback_support=_cell_status_pair_index_support(),
                namespace=f"{TASK_ID}.target_ship_answer_pair.{str(query_id)}",
                balanced_flag_key="balanced_target_ship_answer_pair_sampling",
                namespace_support_permutation=True,
            )
            target_ship_id, target_answer = pair_options[int(pair_index)]
            target_ship_id_probabilities = _cell_status_target_ship_probabilities(pair_options)
            target_answer_probabilities = _cell_status_answer_probabilities(pair_options)
            target_answer_support = tuple(sorted({int(answer) for _shape_id, answer in pair_options}))
        else:
            if explicit_target_answer is None:
                compatible_target_ship_ids = SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS
            else:
                selected_answer = int(explicit_target_answer)
                compatible_target_ship_ids = tuple(
                    str(shape_id)
                    for shape_id in SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS
                    if int(selected_answer) in set(_cell_status_answer_support_for_ship(str(shape_id)))
                )
                if not compatible_target_ship_ids:
                    raise ValueError(f"unsupported target_answer for Battleship cell-status query: {selected_answer}")
            target_ship_id, target_ship_id_probabilities = _resolve_named_axis(
                instance_seed=int(instance_seed),
                params=params,
                namespace="target_ship_id",
                explicit_key="target_ship_id",
                weights_key="target_ship_id_weights",
                balance_flag_key="balanced_target_ship_id_sampling",
                supported=compatible_target_ship_ids,
            )
            cell_count_support = _cell_status_answer_support_for_ship(str(target_ship_id))
            target_answer, target_answer_probabilities = resolve_integer_choice(
                instance_seed=int(instance_seed),
                params=params,
                gen_defaults=_GEN_DEFAULTS,
                support_key=f"{str(target_ship_id)}_cell_count_support",
                explicit_key="target_answer",
                fallback_support=cell_count_support,
                namespace=f"{TASK_ID}.target_answer.{str(query_id)}.{str(target_ship_id)}",
                balanced_flag_key="balanced_target_answer_sampling",
                namespace_support_permutation=True,
            )
            target_answer_support = resolve_integer_support(
                params,
                gen_defaults=_GEN_DEFAULTS,
                key=f"{str(target_ship_id)}_cell_count_support",
                fallback=cell_count_support,
            )
    elif str(query_id) in SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS:
        target_ship_id, target_ship_id_probabilities = _resolve_named_axis(
            instance_seed=int(instance_seed),
            params=params,
            namespace="target_ship_id",
            explicit_key="target_ship_id",
            weights_key="target_ship_id_weights",
            balance_flag_key="balanced_target_ship_id_sampling",
            supported=SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS,
        )
        last_ship_cell_option_count, last_ship_cell_option_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="last_ship_cell_option_count_support",
            explicit_key="last_ship_cell_option_count",
            fallback_support=_DEFAULTS.last_ship_cell_option_count_support,
            namespace=f"{TASK_ID}.last_ship_cell_option_count",
            balanced_flag_key="balanced_last_ship_cell_option_count_sampling",
            namespace_support_permutation=True,
        )
        last_ship_cell_option_count_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="last_ship_cell_option_count_support",
            fallback=_DEFAULTS.last_ship_cell_option_count_support,
        )
        if int(last_ship_cell_option_count) < 2 or int(last_ship_cell_option_count) > len(LAST_CELL_OPTION_LABELS):
            raise ValueError("last_ship_cell_option_count must be between 2 and the label pool size")
        label_index_support = tuple(range(int(last_ship_cell_option_count)))
        label_index_params = dict(params)
        label_index_params["last_ship_cell_label_index_support"] = [int(value) for value in label_index_support]
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=label_index_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="last_ship_cell_label_index_support",
            explicit_key="target_answer",
            fallback_support=label_index_support,
            namespace=f"{TASK_ID}.target_answer.{LAST_CELL_QUERY_ID}",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
        target_answer_support = tuple(int(value) for value in label_index_support)
    else:
        support_key = _target_support_key(str(query_id))
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=str(support_key),
            explicit_key="target_answer",
            fallback_support=getattr(_DEFAULTS, support_key),
            namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key=str(support_key),
            fallback=getattr(_DEFAULTS, support_key),
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
        target_ship_id=str(target_ship_id),
        target_ship_id_probabilities=dict(target_ship_id_probabilities),
        last_ship_cell_option_count=int(last_ship_cell_option_count),
        last_ship_cell_option_count_support=tuple(int(value) for value in last_ship_cell_option_count_support),
        last_ship_cell_option_count_probabilities=dict(last_ship_cell_option_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> BattleshipRenderParams:
    """Resolve Battleship rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.battleship.text_font",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.battleship.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.battleship.layout",
        ),
        unit_scale_meta,
    )
    return BattleshipRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_size_px=scale_games_px(params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)), unit_scale, min_px=320),
        board_border_width_px=scale_games_px(params.get("board_border_width_px", group_default(_RENDER_DEFAULTS, "board_border_width_px", _DEFAULTS.board_border_width_px)), unit_scale, min_px=2),
        grid_line_width_px=scale_games_px(params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", _DEFAULTS.grid_line_width_px)), unit_scale, min_px=1),
        cell_padding_px=scale_games_px(params.get("cell_padding_px", group_default(_RENDER_DEFAULTS, "cell_padding_px", _DEFAULTS.cell_padding_px)), unit_scale, min_px=3),
        fleet_panel_width_px=int(params.get("fleet_panel_width_px", group_default(_RENDER_DEFAULTS, "fleet_panel_width_px", _DEFAULTS.fleet_panel_width_px))),
        board_panel_gap_px=int(params.get("board_panel_gap_px", group_default(_RENDER_DEFAULTS, "board_panel_gap_px", _DEFAULTS.board_panel_gap_px))),
        fleet_icon_cell_px=scale_games_px(params.get("fleet_icon_cell_px", group_default(_RENDER_DEFAULTS, "fleet_icon_cell_px", _DEFAULTS.fleet_icon_cell_px)), unit_scale, min_px=9),
        label_font_size_px=scale_games_px(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px)), unit_scale, min_px=12),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


def _inflated_cells(coords: Iterable[Coord], *, board_size: int) -> set[Coord]:
    """Return a one-cell Chebyshev margin around a ship."""

    inflated: set[Coord] = set()
    for row, col in coords:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr = int(row) + int(dr)
                nc = int(col) + int(dc)
                if 0 <= nr < int(board_size) and 0 <= nc < int(board_size):
                    inflated.add((nr, nc))
    return inflated


def _place_offsets(
    *,
    rng,
    board_size: int,
    offsets: Sequence[Coord],
    forbidden: set[Coord],
) -> Tuple[Coord, ...]:
    """Place one ship on the board without touching existing ships."""

    orientations = list(shape_orientations(offsets))
    rng.shuffle(orientations)
    for oriented in orientations:
        max_row = max(row for row, _col in oriented)
        max_col = max(col for _row, col in oriented)
        starts = [
            (row, col)
            for row in range(0, int(board_size) - int(max_row))
            for col in range(0, int(board_size) - int(max_col))
        ]
        rng.shuffle(starts)
        for start_row, start_col in starts:
            candidate = tuple((int(start_row) + int(row), int(start_col) + int(col)) for row, col in oriented)
            if not (set(candidate) & forbidden):
                return sorted_coords(candidate)
    raise ValueError("failed to place Battleship ship")


def _miss_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve miss-marker count bounds."""

    low = int(params.get("min_miss_count", group_default(_GEN_DEFAULTS, "min_miss_count", _DEFAULTS.min_miss_count)))
    high = int(params.get("max_miss_count", group_default(_GEN_DEFAULTS, "max_miss_count", _DEFAULTS.max_miss_count)))
    if low > high:
        raise ValueError("min_miss_count must be <= max_miss_count")
    return max(0, int(low)), max(0, int(high))


def _partial_ship_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve partially hit ship count bounds."""

    low = int(
        params.get(
            "min_partial_ship_count",
            group_default(_GEN_DEFAULTS, "min_partial_ship_count", _DEFAULTS.min_partial_ship_count),
        )
    )
    high = int(
        params.get(
            "max_partial_ship_count",
            group_default(_GEN_DEFAULTS, "max_partial_ship_count", _DEFAULTS.max_partial_ship_count),
        )
    )
    if low > high:
        raise ValueError("min_partial_ship_count must be <= max_partial_ship_count")
    return max(0, int(low)), max(0, int(high))


def _candidate_completes_target_shape(
    *,
    candidate: Coord,
    target_hit_coords: Sequence[Coord],
    target_shape_id: str,
) -> bool:
    """Return whether adding candidate to target hits completes the target ship shape."""

    completed = sorted_coords([*tuple(target_hit_coords), (int(candidate[0]), int(candidate[1]))])
    return str(target_shape_id) in matching_fleet_shape_ids(completed)


def _sample_last_cell_candidate_options(
    *,
    rng,
    board_size: int,
    target_ship: BattleshipShipPlacement,
    missing_coord: Coord,
    ship_cells: set[Coord],
    hit_coords: Sequence[Coord],
    answer_label_index: int,
    option_count: int,
) -> Tuple[BattleshipCandidateOption, ...]:
    """Return labeled candidate cells with exactly one valid missing-cell answer."""

    correct = (int(missing_coord[0]), int(missing_coord[1]))
    labels = tuple(str(label) for label in LAST_CELL_OPTION_LABELS[: int(option_count)])
    if len(labels) < 2:
        raise ValueError("Battleship last-cell option count must be at least 2")
    hit_set = {(int(row), int(col)) for row, col in hit_coords}
    target_hits = tuple((int(row), int(col)) for row, col in target_ship.hit_coords)
    invalid_pool: list[Coord] = []
    seen: set[Coord] = set()

    def _add_candidate(coord: Coord) -> None:
        row, col = int(coord[0]), int(coord[1])
        item = (row, col)
        if item in seen or item == correct or item in hit_set or item in ship_cells:
            return
        if not (0 <= row < int(board_size) and 0 <= col < int(board_size)):
            return
        if _candidate_completes_target_shape(
            candidate=item,
            target_hit_coords=target_hits,
            target_shape_id=str(target_ship.shape_id),
        ):
            return
        seen.add(item)
        invalid_pool.append(item)

    target_rows = [int(row) for row, _col in target_hits]
    target_cols = [int(col) for _row, col in target_hits]
    if target_rows and target_cols:
        for row in range(min(target_rows) - 2, max(target_rows) + 3):
            for col in range(min(target_cols) - 2, max(target_cols) + 3):
                _add_candidate((row, col))

    for row, col in target_hits:
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                if abs(int(dr)) + abs(int(dc)) <= 3:
                    _add_candidate((int(row) + int(dr), int(col) + int(dc)))

    all_water = [
        coord
        for coord in all_coords(int(board_size))
        if coord not in ship_cells and coord not in hit_set and coord != correct
    ]
    rng.shuffle(all_water)
    for coord in all_water:
        _add_candidate(coord)

    if len(invalid_pool) < len(labels) - 1:
        raise ValueError("failed to sample enough invalid Battleship last-cell candidates")

    rng.shuffle(invalid_pool)
    selected_label_index = int(answer_label_index) % len(labels)
    distractor_coords = list(invalid_pool[: len(labels) - 1])
    option_coords: list[Coord] = []
    distractor_index = 0
    for label_index in range(len(labels)):
        if int(label_index) == int(selected_label_index):
            option_coords.append(correct)
        else:
            option_coords.append(distractor_coords[distractor_index])
            distractor_index += 1
    options = tuple(
        BattleshipCandidateOption(
            label=str(label),
            coord=(int(coord[0]), int(coord[1])),
            is_answer=bool((int(coord[0]), int(coord[1])) == correct),
        )
        for label, coord in zip(labels, option_coords)
    )
    if sum(1 for option in options if bool(option.is_answer)) != 1:
        raise ValueError("failed to place exactly one Battleship answer option")
    return options


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> BattleshipSample:
    """Construct one Battleship tracking-grid scene for the requested axes."""

    if str(axes.query_id) not in SUPPORTED_BATTLESHIP_QUERY_IDS:
        raise ValueError(f"unsupported Battleship query_id: {axes.query_id}")

    board_size = int(axes.board_size)
    target_answer = 0 if axes.target_answer is None else int(axes.target_answer)
    if target_answer < 0 or target_answer > len(FLEET_SHAPES):
        raise ValueError(f"unsupported Battleship target_answer: {target_answer}")
    fleet_size = len(FLEET_SHAPES)
    is_cell_status_query = str(axes.query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS
    is_last_cell_query = str(axes.query_id) in SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS
    target_ship_id = str(axes.target_ship_id)
    target_cell_status = ""
    target_hit_count: int | None = None
    target_missing_coord: Coord | None = None
    candidate_options: Tuple[BattleshipCandidateOption, ...] = tuple()
    if bool(is_cell_status_query):
        if target_ship_id not in SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS:
            raise ValueError(f"unsupported Battleship target_ship_id: {target_ship_id}")
        target_cell_status = _cell_status_query_target_status(str(axes.query_id))
        target_ship_size = _ship_size_for_shape_id(str(target_ship_id))
        if int(target_answer) > int(target_ship_size):
            raise ValueError(f"target_answer {target_answer} exceeds target ship size {target_ship_size}")
        if str(axes.query_id) == "named_ship_hit_cell_count":
            target_hit_count = int(target_answer)
        else:
            target_hit_count = int(target_ship_size) - int(target_answer)
        sunk_count = 0
        partial_count = 0
    elif bool(is_last_cell_query):
        if target_ship_id not in SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS:
            raise ValueError(f"unsupported Battleship target_ship_id: {target_ship_id}")
        sunk_count = int(fleet_size) - 1
        partial_count = 1
    elif str(axes.query_id) == "sunk_ship_count":
        sunk_count = int(target_answer)
        partial_low, partial_high = _partial_ship_count_bounds(params)
        partial_count = min(
            int(fleet_size) - int(sunk_count),
            int(rng.randint(int(partial_low), int(partial_high))),
        )
    else:
        partial_count = int(target_answer)
        sunk_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="sunk_ship_count_support",
            fallback=_DEFAULTS.sunk_ship_count_support,
        )
        sunk_candidates = [
            int(value)
            for value in sunk_support
            if 0 < int(value) <= int(fleet_size) - int(partial_count)
        ]
        if not sunk_candidates:
            sunk_candidates = [0]
        sunk_count = int(rng.choice(sunk_candidates))

    forbidden: set[Coord] = set()
    ship_coords_by_shape_id: dict[str, Tuple[Coord, ...]] = {}
    for shape in FLEET_SHAPES:
        coords = _place_offsets(
            rng=rng,
            board_size=int(board_size),
            offsets=shape.offsets,
            forbidden=forbidden,
        )
        ship_coords_by_shape_id[str(shape.shape_id)] = tuple(coords)
        forbidden.update(_inflated_cells(coords, board_size=int(board_size)))

    fleet_shapes = list(FLEET_SHAPES)
    rng.shuffle(fleet_shapes)
    sunk_shape_ids = {str(shape.shape_id) for shape in fleet_shapes[:sunk_count]}
    remaining_shape_ids = [str(shape.shape_id) for shape in fleet_shapes[sunk_count:]]
    partial_shape_ids = set(remaining_shape_ids[:partial_count])

    placements: list[BattleshipShipPlacement] = []
    for shape in FLEET_SHAPES:
        coords = tuple(ship_coords_by_shape_id[str(shape.shape_id)])
        if bool(is_last_cell_query):
            if str(shape.shape_id) == str(target_ship_id):
                shuffled = list(coords)
                rng.shuffle(shuffled)
                target_missing_coord = (int(shuffled[0][0]), int(shuffled[0][1]))
                ship_hit_coords = sorted_coords(coord for coord in coords if coord != target_missing_coord)
                is_sunk = False
            else:
                ship_hit_coords = coords
                is_sunk = True
        elif bool(is_cell_status_query):
            shuffled = list(coords)
            rng.shuffle(shuffled)
            if str(shape.shape_id) == str(target_ship_id):
                hit_count = int(target_hit_count or 0)
            else:
                roll = float(rng.random())
                if roll < 0.30:
                    hit_count = 0
                elif roll < 0.55:
                    hit_count = len(coords)
                else:
                    hit_count = int(rng.randint(1, max(1, len(coords) - 1)))
            ship_hit_coords = sorted_coords(shuffled[:hit_count])
            is_sunk = int(hit_count) == len(coords)
        else:
            if str(shape.shape_id) in sunk_shape_ids:
                ship_hit_coords = coords
                is_sunk = True
            elif str(shape.shape_id) in partial_shape_ids:
                shuffled = list(coords)
                rng.shuffle(shuffled)
                hit_count = int(rng.randint(1, max(1, len(coords) - 1)))
                ship_hit_coords = sorted_coords(shuffled[:hit_count])
                is_sunk = False
            else:
                ship_hit_coords = tuple()
                is_sunk = False
        placements.append(
            BattleshipShipPlacement(
                ship_id=str(shape.shape_id),
                shape_id=str(shape.shape_id),
                display_name=str(shape.display_name),
                coords=coords,
                hit_coords=tuple(ship_hit_coords),
                is_sunk=bool(is_sunk),
            )
        )

    hit_coords = sorted_coords(coord for ship in placements for coord in ship.hit_coords)
    ship_cells = {coord for ship in placements for coord in ship.coords}
    if bool(is_last_cell_query):
        target_ships = [ship for ship in placements if str(ship.ship_id) == str(target_ship_id)]
        if len(target_ships) != 1 or target_missing_coord is None:
            raise ValueError("failed to resolve Battleship last-cell target")
        candidate_options = _sample_last_cell_candidate_options(
            rng=rng,
            board_size=int(board_size),
            target_ship=target_ships[0],
            missing_coord=target_missing_coord,
            ship_cells=set(ship_cells),
            hit_coords=hit_coords,
            answer_label_index=int(target_answer),
            option_count=int(axes.last_ship_cell_option_count),
        )
        answer_option = next(option for option in candidate_options if bool(option.is_answer))
        answer_label_index = LAST_CELL_OPTION_LABELS.index(str(answer_option.label))
        target_answer = int(answer_label_index)
    available_for_misses = [
        coord
        for coord in all_coords(int(board_size))
        if coord not in ship_cells
        and coord not in {(int(option.coord[0]), int(option.coord[1])) for option in candidate_options}
    ]
    rng.shuffle(available_for_misses)
    miss_low, miss_high = _miss_count_bounds(params)
    miss_count = min(len(available_for_misses), int(rng.randint(int(miss_low), int(miss_high))))
    miss_coords = sorted_coords(available_for_misses[:miss_count])
    sunk_count = len([ship for ship in placements if bool(ship.is_sunk)])
    partial_count = len([ship for ship in placements if bool(ship.hit_coords) and not bool(ship.is_sunk)])
    untouched_count = len([ship for ship in placements if not bool(ship.hit_coords)])
    if str(axes.query_id) == "sunk_ship_count":
        annotation_ships = [ship for ship in placements if bool(ship.is_sunk)]
        annotation_coords = sorted_coords(coord for ship in annotation_ships for coord in ship.hit_coords)
        annotation_ship_ids = tuple(str(ship.ship_id) for ship in annotation_ships)
        answer = int(sunk_count)
    elif str(axes.query_id) == "partial_ship_count":
        annotation_ships = [
            ship
            for ship in placements
            if bool(ship.hit_coords) and not bool(ship.is_sunk)
        ]
        annotation_coords = sorted_coords(
            coord
            for ship in annotation_ships
            for coord in ship.hit_coords
        )
        annotation_ship_ids = tuple(str(ship.ship_id) for ship in annotation_ships)
        answer = int(partial_count)
    elif bool(is_cell_status_query):
        annotation_ships = [ship for ship in placements if str(ship.ship_id) == str(target_ship_id)]
        if len(annotation_ships) != 1:
            raise ValueError("failed to resolve target ship")
        target_ship = annotation_ships[0]
        target_hit_coords = set(target_ship.hit_coords)
        if str(axes.query_id) == "named_ship_hit_cell_count":
            annotation_coords = sorted_coords(target_ship.hit_coords)
        else:
            annotation_coords = sorted_coords(coord for coord in target_ship.coords if coord not in target_hit_coords)
        annotation_ship_ids = (str(target_ship.ship_id),)
        answer = len(annotation_coords)
    elif bool(is_last_cell_query):
        annotation_ships = [ship for ship in placements if str(ship.ship_id) == str(target_ship_id)]
        if len(annotation_ships) != 1 or target_missing_coord is None:
            raise ValueError("failed to resolve target ship")
        answer_option = next(option for option in candidate_options if bool(option.is_answer))
        annotation_coords = sorted_coords([target_missing_coord])
        annotation_ship_ids = (str(annotation_ships[0].ship_id),)
        answer = str(answer_option.label)
    sample = BattleshipSample(
        board_size=int(board_size),
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        answer=str(answer) if bool(is_last_cell_query) else int(answer),
        ship_placements=tuple(placements),
        hit_coords=hit_coords,
        miss_coords=miss_coords,
        annotation_coords=annotation_coords,
        annotation_ship_ids=tuple(str(ship_id) for ship_id in annotation_ship_ids),
        target_answer=int(target_answer),
        sunk_ship_count=int(sunk_count),
        partial_ship_count=int(partial_count),
        untouched_ship_count=int(untouched_count),
        construction_mode="placed_fleet_with_full_partial_and_missed_shots",
        target_ship_id=str(target_ship_id),
        target_ship_display_name=(
            ""
            if not (bool(is_cell_status_query) or bool(is_last_cell_query))
            else str(fleet_shape_by_id()[str(target_ship_id)].display_name)
        ),
        target_ship_shape_id=str(target_ship_id) if (bool(is_cell_status_query) or bool(is_last_cell_query)) else "",
        target_cell_status=str(target_cell_status),
        target_missing_coord=target_missing_coord,
        candidate_options=tuple(candidate_options),
    )
    validate_battleship_sample(sample)
    return sample


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Battleship JSON output."""

    if str(query_id) in SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS:
        answer_value = "D"
        annotation_value = [[315, 405]]
        return (
            json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
            json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        )

    if str(query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS:
        answer_value = 3
        annotation_value = [[210, 220], [240, 220], [270, 220]]
        return (
            json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
            json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        )

    answer_value = 5
    annotation_value = {
        "Line 5": [[210, 220], [240, 220], [270, 220], [300, 220], [330, 220]],
        "Line 4": [[210, 280], [240, 280], [270, 280], [300, 280]],
        "Line 3": [[210, 340], [240, 340], [270, 340]],
        "Square 2x2": [[210, 400], [240, 400], [210, 430], [240, 430]],
        "L 3": [[210, 490], [210, 520], [240, 520]],
    }
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesBattleshipGridTask:
    """Return one grounded query over a visible Battleship tracking grid."""

    task_id = TASK_ID
    domain = "games"
    task_group = "battleship"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }

        sampled_scene: BattleshipSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

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
            namespace="games.battleship_grid.panel_scene_style",
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
        is_last_cell_query = str(axes.query_id) in SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS
        candidate_labels_by_coord = {
            (int(option.coord[0]), int(option.coord[1])): str(option.label)
            for option in sampled_scene.candidate_options
        }
        rendered_scene = render_battleship_grid_scene(
            board_size=int(sampled_scene.board_size),
            ship_cells_by_id={
                str(ship.ship_id): tuple(ship.coords)
                for ship in sampled_scene.ship_placements
            },
            sunk_ship_ids=[
                str(ship.ship_id)
                for ship in sampled_scene.ship_placements
                if bool(ship.is_sunk)
            ],
            hit_coords=sampled_scene.hit_coords,
            miss_coords=sampled_scene.miss_coords,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
            show_ship_bodies=not bool(is_last_cell_query),
            candidate_labels_by_coord=candidate_labels_by_coord,
        )
        annotation_ships_by_id = {str(ship.ship_id): ship for ship in sampled_scene.ship_placements}

        def _bbox_center(bbox: Sequence[float]) -> list[float]:
            return [
                round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
            ]

        annotation_keyed_point_sets: Dict[str, list[list[float]]] = {}
        annotation_key_to_ship_id: Dict[str, str] = {}
        annotation_hit_cell_ids_by_key: Dict[str, list[str]] = {}
        annotation_cell_ids = [
            coord_to_cell_id(coord)
            for coord in sorted_coords(sampled_scene.annotation_coords)
        ]
        annotation_points = [
            _bbox_center(rendered_scene.render_map["cell_bboxes_px"][str(cell_id)])
            for cell_id in annotation_cell_ids
        ]
        if str(axes.query_id) in SUPPORTED_BATTLESHIP_SHIP_STATUS_QUERY_IDS:
            for ship_id in sampled_scene.annotation_ship_ids:
                ship = annotation_ships_by_id[str(ship_id)]
                key = str(ship.display_name)
                hit_cell_ids = [
                    coord_to_cell_id((int(row), int(col)))
                    for row, col in sorted_coords(ship.hit_coords)
                ]
                if not hit_cell_ids:
                    raise ValueError("cannot build annotation points for ship with no hit cells")
                annotation_keyed_point_sets[str(key)] = [
                    _bbox_center(rendered_scene.render_map["cell_bboxes_px"][str(cell_id)])
                    for cell_id in hit_cell_ids
                ]
                annotation_key_to_ship_id[str(key)] = str(ship.ship_id)
                annotation_hit_cell_ids_by_key[str(key)] = [str(cell_id) for cell_id in hit_cell_ids]
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
                "object_description_standard_fleet",
                "object_description_hidden_fleet",
                "battleship_rule_text",
                "answer_hint_sunk_ship_count",
                "annotation_hint_sunk_ship_count",
                "answer_hint_partial_ship_count",
                "annotation_hint_partial_ship_count",
                "answer_hint_named_ship_hit_cell_count",
                "annotation_hint_named_ship_hit_cell_count",
                "answer_hint_named_ship_unhit_cell_count",
                "annotation_hint_named_ship_unhit_cell_count",
                "answer_hint_last_ship_cell_label",
                "annotation_hint_last_ship_cell_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        object_description_key = (
            "object_description_hidden_fleet"
            if bool(is_last_cell_query)
            else f"object_description_{str(axes.scene_variant)}"
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[object_description_key]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "battleship_rule_text": str(prompt_defaults["battleship_rule_text"]),
                "target_ship_name": str(sampled_scene.target_ship_display_name),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if bool(is_last_cell_query):
            answer_gt = TypedValue(type="string", value=str(sampled_scene.answer))
        else:
            answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        if str(axes.query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS or bool(is_last_cell_query):
            annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
            annotation_count = len(annotation_points)
        else:
            annotation_gt = TypedValue(type="keyed_point_set_map", value=dict(annotation_keyed_point_sets))
            annotation_count = len(annotation_keyed_point_sets)
        complexity = build_games_battleship_grid_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            board_size=int(sampled_scene.board_size),
            hit_count=len(sampled_scene.hit_coords),
            miss_count=len(sampled_scene.miss_coords),
            target_answer=int(sampled_scene.target_answer),
            annotation_count=int(annotation_count),
        )

        ship_trace = [
            {
                "ship_id": str(ship.ship_id),
                "shape_id": str(ship.shape_id),
                "display_name": str(ship.display_name),
                "coords": [[int(row), int(col)] for row, col in ship.coords],
                "hit_coords": [[int(row), int(col)] for row, col in ship.hit_coords],
                "is_sunk": bool(ship.is_sunk),
            }
            for ship in sampled_scene.ship_placements
        ]
        annotation_entity_ids = (
            [str(cell_id) for cell_id in annotation_cell_ids]
            if str(axes.query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS or bool(is_last_cell_query)
            else [str(ship_id) for ship_id in sampled_scene.annotation_ship_ids]
        )
        target_ship_cell_ids = []
        if sampled_scene.target_ship_id:
            target_ships = [
                ship
                for ship in sampled_scene.ship_placements
                if str(ship.ship_id) == str(sampled_scene.target_ship_id)
            ]
            if len(target_ships) == 1:
                target_ship_cell_ids = [
                    coord_to_cell_id(coord)
                    for coord in sorted_coords(target_ships[0].coords)
                ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_battleship_grid_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(sampled_scene.board_size),
                    "target_answer": int(sampled_scene.target_answer),
                    "target_ship_id": str(sampled_scene.target_ship_id),
                    "target_ship_display_name": str(sampled_scene.target_ship_display_name),
                    "target_ship_shape_id": str(sampled_scene.target_ship_shape_id),
                    "target_cell_status": str(sampled_scene.target_cell_status),
                    "target_missing_coord": (
                        None
                        if sampled_scene.target_missing_coord is None
                        else [int(sampled_scene.target_missing_coord[0]), int(sampled_scene.target_missing_coord[1])]
                    ),
                    "candidate_options": [
                        {
                            "label": str(option.label),
                            "coord": [int(option.coord[0]), int(option.coord[1])],
                            "cell_id": coord_to_cell_id((int(option.coord[0]), int(option.coord[1]))),
                            "is_answer": bool(option.is_answer),
                        }
                        for option in sampled_scene.candidate_options
                    ],
                    "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
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
                    "board_size": int(sampled_scene.board_size),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "board_size_probabilities": dict(axes.board_size_probabilities),
                    "target_answer": int(sampled_scene.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "target_ship_id": str(sampled_scene.target_ship_id),
                    "target_ship_display_name": str(sampled_scene.target_ship_display_name),
                    "target_ship_shape_id": str(sampled_scene.target_ship_shape_id),
                    "target_ship_id_probabilities": dict(axes.target_ship_id_probabilities or {}),
                    "target_cell_status": str(sampled_scene.target_cell_status),
                    "target_missing_coord": (
                        None
                        if sampled_scene.target_missing_coord is None
                        else [int(sampled_scene.target_missing_coord[0]), int(sampled_scene.target_missing_coord[1])]
                    ),
                    "candidate_labels": [str(option.label) for option in sampled_scene.candidate_options],
                    "last_ship_cell_option_count": int(axes.last_ship_cell_option_count),
                    "last_ship_cell_option_count_support": [int(value) for value in axes.last_ship_cell_option_count_support],
                    "last_ship_cell_option_count_probabilities": dict(axes.last_ship_cell_option_count_probabilities or {}),
                    "hit_count": len(sampled_scene.hit_coords),
                    "miss_count": len(sampled_scene.miss_coords),
                    "sunk_ship_count": int(sampled_scene.sunk_ship_count),
                    "partial_ship_count": int(sampled_scene.partial_ship_count),
                    "untouched_ship_count": int(sampled_scene.untouched_ship_count),
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
                "board_size": int(sampled_scene.board_size),
                "target_answer": int(sampled_scene.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "hit_coords": [[int(row), int(col)] for row, col in sampled_scene.hit_coords],
                "miss_coords": [[int(row), int(col)] for row, col in sampled_scene.miss_coords],
                "annotation_coords": [[int(row), int(col)] for row, col in sampled_scene.annotation_coords],
                "annotation_cell_ids": [str(cell_id) for cell_id in annotation_cell_ids],
                "annotation_ship_ids": [str(ship_id) for ship_id in sampled_scene.annotation_ship_ids],
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
                "annotation_ship_name_to_ship_id": dict(annotation_key_to_ship_id),
                "annotation_hit_cell_ids_by_ship_name": dict(annotation_hit_cell_ids_by_key),
                "target_ship_id": str(sampled_scene.target_ship_id),
                "target_ship_display_name": str(sampled_scene.target_ship_display_name),
                "target_ship_shape_id": str(sampled_scene.target_ship_shape_id),
                "target_ship_cell_ids": [str(cell_id) for cell_id in target_ship_cell_ids],
                "target_cell_status": str(sampled_scene.target_cell_status),
                "target_missing_coord": (
                    None
                    if sampled_scene.target_missing_coord is None
                    else [int(sampled_scene.target_missing_coord[0]), int(sampled_scene.target_missing_coord[1])]
                ),
                "candidate_options": [
                    {
                        "label": str(option.label),
                        "coord": [int(option.coord[0]), int(option.coord[1])],
                        "cell_id": coord_to_cell_id((int(option.coord[0]), int(option.coord[1]))),
                        "is_answer": bool(option.is_answer),
                    }
                    for option in sampled_scene.candidate_options
                ],
                "ship_placements": ship_trace,
                "fleet_shapes": [
                    {
                        "shape_id": str(shape.shape_id),
                        "display_name": str(shape.display_name),
                        "offsets": [[int(row), int(col)] for row, col in shape.offsets],
                    }
                    for shape in FLEET_SHAPES
                ],
                "sunk_ship_count": int(sampled_scene.sunk_ship_count),
                "partial_ship_count": int(sampled_scene.partial_ship_count),
                "untouched_ship_count": int(sampled_scene.untouched_ship_count),
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": (
                    "cell_set"
                    if str(axes.query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS or bool(is_last_cell_query)
                    else "object_map"
                ),
                "ids": (
                    [str(cell_id) for cell_id in annotation_cell_ids]
                    if str(axes.query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS or bool(is_last_cell_query)
                    else dict(annotation_key_to_ship_id)
                ),
            },
            "projected_annotation": {
                **(
                    {
                        "type": "point_set",
                        "point_set": [list(point) for point in annotation_points],
                        "pixel_point_set": [list(point) for point in annotation_points],
                    }
                    if str(axes.query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS or bool(is_last_cell_query)
                    else {
                        "type": "keyed_point_set_map",
                        "keyed_point_set_map": dict(annotation_keyed_point_sets),
                        "pixel_keyed_point_set_map": dict(annotation_keyed_point_sets),
                    }
                ),
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="battleship",
            query_id=str(axes.query_id),
        )


@register_task
class GamesBattleshipShipStatusCountTask(QuerySubsetTaskMixin, GamesBattleshipGridTask):
    """Count fleet ships matching one sampled hit-status condition."""

    task_id = "task_games__battleship__ship_status_count"
    supported_query_ids = (
        "sunk_ship_count",
        "partial_ship_count",
    )


@register_task
class GamesBattleshipShipCellStatusCountTask(QuerySubsetTaskMixin, GamesBattleshipGridTask):
    """Count hit or unhit cells inside one named fleet ship."""

    task_id = "task_games__battleship__ship_cell_status_count"
    supported_query_ids = (
        "named_ship_hit_cell_count",
        "named_ship_unhit_cell_count",
    )


@register_task
class GamesBattleshipLastShipCellLabelTask(QuerySubsetTaskMixin, GamesBattleshipGridTask):
    """Select the labeled cell that completes the only not-yet-sunk ship."""

    task_id = "task_games__battleship__last_ship_cell_label"
    supported_query_ids = (
        "last_ship_cell_label",
    )


__all__ = [
    "GamesBattleshipGridTask",
    "GamesBattleshipLastShipCellLabelTask",
    "GamesBattleshipShipCellStatusCountTask",
    "GamesBattleshipShipStatusCountTask",
]
