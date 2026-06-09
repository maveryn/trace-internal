"""Games Connect Four task for grounded move-count queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

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
from ..shared.complexity import build_games_connect_four_move_complexity
from ..shared.connect_four_common import (
    Board,
    COLUMNS,
    Coord,
    RED,
    ROWS,
    YELLOW,
    board_dimensions,
    coord_to_cell_id,
    drop_disc,
    empty_board,
    has_connect_four,
    legal_drop_rows,
    occupied_cell_count,
    opponent,
    player_name,
    winning_drop_map,
)
from ..shared.connect_four_scene import ConnectFourRenderParams, render_connect_four_board_scene
from ..shared.fixed_query_task import QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_CONNECT_FOUR_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_connect_four_move_count_base"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "midgame_board",
    "crowded_board",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "winning_move_count",
    "safe_move_count",
)
SUPPORTED_BOARD_SIZE_VARIANTS: Tuple[str, ...] = (
    "standard_7x6",
    "small_6x5",
)
DEFAULT_SAFE_BOARD_SIZE_VARIANTS: Tuple[str, ...] = (
    "square_5x5",
    "square_6x6",
)
SUPPORTED_SAFE_BOARD_SIZE_VARIANTS: Tuple[str, ...] = (
    *DEFAULT_SAFE_BOARD_SIZE_VARIANTS,
    *SUPPORTED_BOARD_SIZE_VARIANTS,
)
SUPPORTED_WINNING_MOVE_LABEL_THREAT_KINDS: Tuple[str, ...] = (
    "vertical_threat",
    "horizontal_threat",
)
COLUMN_LABELS: Tuple[str, ...] = tuple("ABCDEFG")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Connect Four move-count scenes."""

    winning_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    safe_move_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    midgame_min_occupied_count: int = 8
    midgame_max_occupied_count: int = 16
    crowded_min_occupied_count: int = 16
    crowded_max_occupied_count: int = 24
    safe_midgame_min_occupied_count: int = 8
    safe_midgame_max_occupied_count: int = 16
    safe_crowded_min_occupied_count: int = 16
    safe_crowded_max_occupied_count: int = 24
    winning_move_label_threat_kind_weights: Dict[str, float] | None = None
    standard_board_rows: int = ROWS
    standard_board_columns: int = COLUMNS
    small_board_rows: int = 5
    small_board_columns: int = 6
    square_5_board_rows: int = 5
    square_5_board_columns: int = 5
    square_6_board_rows: int = 6
    square_6_board_columns: int = 6
    canvas_width: int = 980
    canvas_height: int = 900
    panel_margin_px: int = 48
    player_badge_height_px: int = 52
    player_badge_width_px: int = 220
    header_gap_px: int = 18
    max_board_width_px: int = 780
    board_corner_radius_px: int = 30
    board_frame_width_px: int = 16
    disc_inset_fraction: float = 0.14
    player_badge_font_size_px: int = 22
    marked_square_outline_width_px: int = 6
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 560
    canvas_min_height_px: int = 520
    canvas_side_padding_px: int = 132
    canvas_vertical_padding_px: int = 92


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Connect Four scene."""

    query_id: str
    scene_variant: str
    board_size_variant: str
    board_rows: int
    board_columns: int
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    board_size_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _QueryEvaluation:
    """Query-specific evaluation payload derived from one finalized board."""

    answer: int
    annotation_coords: Tuple[Coord, ...]
    annotation_entity_ids: Tuple[str, ...]
    winning_move_coords: Tuple[Coord, ...]
    safe_move_coords: Tuple[Coord, ...]


@dataclass(frozen=True)
class _SampledConnectFourScene:
    """One sampled Connect Four scene plus query-specific witness metadata."""

    board: Board
    current_player: int
    evaluation: _QueryEvaluation
    occupied_count: int
    construction_mode: str


@dataclass(frozen=True)
class _SampledConnectFourLabelScene:
    """One Connect Four scene for a single winning-column label query."""

    board: Board
    current_player: int
    evaluation: _QueryEvaluation
    occupied_count: int
    construction_mode: str
    threat_kind: str
    threat_kind_probabilities: Dict[str, float]
    column_labels: Tuple[str, ...]
    answer_label: str
    answer_column: int
    winning_line_coords: Tuple[Coord, ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "connect_four")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="connect_four", apply_prob=0.0)


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one query id."""

    return {
        "winning_move_count": "winning_move_count_support",
        "safe_move_count": "safe_move_count_support",
    }[str(query_id)]


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
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
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _target_answer_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced target-answer cycling."""

    target_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return target_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return target_params
    target_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return target_params


def _scene_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Decorrelate balanced scene cycling from balanced query cycling."""

    scene_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return scene_params
    if params.get("scene_variant") is not None:
        return scene_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return scene_params
    enabled = bool(
        params.get(
            "balanced_scene_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_scene_variant_sampling", True),
        )
    )
    if not enabled:
        return scene_params
    raw_weights = params.get(
        "scene_variant_weights",
        group_default(_GEN_DEFAULTS, "scene_variant_weights", {key: 1.0 for key in SUPPORTED_SCENE_VARIANTS}),
    )
    if not isinstance(raw_weights, Mapping):
        return scene_params
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_SCENE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_SCENE_VARIANTS):
        return scene_params
    if max(positives) - min(positives) > 1e-9:
        return scene_params
    scene_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return scene_params


def _board_size_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Cycle board sizes inside each query and scene pair for balanced reviews."""

    board_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return board_params
    if params.get("board_size_variant") is not None or params.get("board_size") is not None:
        return board_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return board_params
    enabled = bool(
        params.get(
            "balanced_board_size_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_board_size_variant_sampling", True),
        )
    )
    if not enabled:
        return board_params
    raw_weights = params.get(
        "board_size_variant_weights",
        group_default(_GEN_DEFAULTS, "board_size_variant_weights", {key: 1.0 for key in SUPPORTED_BOARD_SIZE_VARIANTS}),
    )
    if not isinstance(raw_weights, Mapping):
        return board_params
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_BOARD_SIZE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_BOARD_SIZE_VARIANTS):
        return board_params
    if max(positives) - min(positives) > 1e-9:
        return board_params

    raw_scene_weights = params.get(
        "scene_variant_weights",
        group_default(_GEN_DEFAULTS, "scene_variant_weights", {key: 1.0 for key in SUPPORTED_SCENE_VARIANTS}),
    )
    scene_count = 1
    if isinstance(raw_scene_weights, Mapping) and params.get("scene_variant") is None:
        scene_count = max(
            1,
            sum(
                1
                for value in SUPPORTED_SCENE_VARIANTS
                if float(raw_scene_weights.get(str(value), 0.0)) > 0.0
            ),
        )
    board_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS) * int(scene_count))
    return board_params


def _style_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Decorrelate balanced style cycling from balanced query cycling."""

    style_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return style_params
    if params.get("style_variant") is not None:
        return style_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return style_params
    enabled = bool(
        params.get(
            "balanced_style_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_style_variant_sampling", True),
        )
    )
    if not enabled:
        return style_params
    raw_weights = params.get(
        "style_variant_weights",
        group_default(
            _GEN_DEFAULTS,
            "style_variant_weights",
            {key: 1.0 for key in SUPPORTED_CONNECT_FOUR_STYLE_VARIANTS},
        ),
    )
    if not isinstance(raw_weights, Mapping):
        return style_params
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_CONNECT_FOUR_STYLE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_CONNECT_FOUR_STYLE_VARIANTS):
        return style_params
    if max(positives) - min(positives) > 1e-9:
        return style_params
    style_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return style_params


def _column_labels_for_columns(columns: int) -> Tuple[str, ...]:
    """Return visible column labels for a Connect Four board width."""

    if int(columns) > len(COLUMN_LABELS):
        raise ValueError(f"Connect Four column labels only support up to {len(COLUMN_LABELS)} columns")
    return tuple(str(label) for label in COLUMN_LABELS[: int(columns)])


def _board_size_variant_to_dimensions(board_size_variant: str) -> Tuple[int, int]:
    """Return `(rows, columns)` for one supported Connect Four board-size variant."""

    if str(board_size_variant) == "square_5x5":
        return int(_DEFAULTS.square_5_board_rows), int(_DEFAULTS.square_5_board_columns)
    if str(board_size_variant) == "square_6x6":
        return int(_DEFAULTS.square_6_board_rows), int(_DEFAULTS.square_6_board_columns)
    if str(board_size_variant) == "small_6x5":
        return int(_DEFAULTS.small_board_rows), int(_DEFAULTS.small_board_columns)
    if str(board_size_variant) == "standard_7x6":
        return int(_DEFAULTS.standard_board_rows), int(_DEFAULTS.standard_board_columns)
    raise ValueError(f"unsupported board_size_variant: {board_size_variant}")


def _normalize_board_size_variant(raw_value: Any) -> str:
    """Normalize explicit board-size aliases to the configured variant names."""

    text = str(raw_value).strip().lower().replace(" ", "")
    aliases = {
        "7x6": "standard_7x6",
        "standard": "standard_7x6",
        "standard_7x6": "standard_7x6",
        "6x5": "small_6x5",
        "small": "small_6x5",
        "small_6x5": "small_6x5",
        "5x5": "square_5x5",
        "square5x5": "square_5x5",
        "square_5x5": "square_5x5",
        "6x6": "square_6x6",
        "square6x6": "square_6x6",
        "square_6x6": "square_6x6",
    }
    if text not in aliases:
        raise ValueError(f"unsupported board_size: {raw_value}")
    return str(aliases[text])


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query id, honoring `query_id` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_id") is None and alias_params.get("query_variant") is not None:
        alias_params["query_id"] = alias_params["query_variant"]
    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_IDS,
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
    """Resolve one balanced named axis for the Connect Four task."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(item) for item in supported],
    )


def _resolve_board_size_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id_probabilities: Mapping[str, float],
) -> Tuple[str, int, int, Dict[str, float]]:
    """Resolve the Connect Four board-size axis."""

    alias_params = dict(params)
    if alias_params.get("board_size_variant") is None and alias_params.get("board_size") is not None:
        alias_params["board_size_variant"] = _normalize_board_size_variant(alias_params["board_size"])
    selected, probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_board_size_params_for_query_cycle(
            alias_params,
            query_id_probabilities=query_id_probabilities,
        ),
        namespace="board_size_variant",
        explicit_key="board_size_variant",
        weights_key="board_size_variant_weights",
        balance_flag_key="balanced_board_size_variant_sampling",
        supported=SUPPORTED_BOARD_SIZE_VARIANTS,
    )
    rows, columns = _board_size_variant_to_dimensions(str(selected))
    return str(selected), int(rows), int(columns), dict(probabilities)


def _resolve_safe_board_size_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id_probabilities: Mapping[str, float],
    target_answer: int,
) -> Tuple[str, int, int, Dict[str, float]]:
    """Resolve the safe-move board-size axis.

    Safe-count defaults use square 5x5 and 6x6 boards. Target answer 6 is only
    feasible on the 6-column board, so the default board axis is narrowed at the
    endpoint rather than deleting answer 6 from the configured support.
    """

    alias_params = dict(params)
    explicit_board_size = (
        alias_params.get("safe_board_size_variant")
        or alias_params.get("board_size_variant")
        or alias_params.get("board_size")
    )
    if alias_params.get("safe_board_size_variant") is None:
        if alias_params.get("board_size_variant") is not None:
            alias_params["safe_board_size_variant"] = alias_params["board_size_variant"]
        elif alias_params.get("board_size") is not None:
            alias_params["safe_board_size_variant"] = _normalize_board_size_variant(alias_params["board_size"])

    if alias_params.get("safe_board_size_variant_weights") is None:
        alias_params["safe_board_size_variant_weights"] = group_default(
            _GEN_DEFAULTS,
            "safe_board_size_variant_weights",
            {key: 1.0 for key in DEFAULT_SAFE_BOARD_SIZE_VARIANTS},
        )
    if alias_params.get("balanced_safe_board_size_variant_sampling") is None:
        alias_params["balanced_safe_board_size_variant_sampling"] = bool(
            group_default(_GEN_DEFAULTS, "balanced_safe_board_size_variant_sampling", True)
        )
    if explicit_board_size is None and int(target_answer) > int(_DEFAULTS.square_5_board_columns):
        alias_params["safe_board_size_variant_weights"] = {"square_6x6": 1.0}

    selected, probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_board_size_params_for_query_cycle(
            alias_params,
            query_id_probabilities=query_id_probabilities,
        ),
        namespace="safe_board_size_variant",
        explicit_key="safe_board_size_variant",
        weights_key="safe_board_size_variant_weights",
        balance_flag_key="balanced_safe_board_size_variant_sampling",
        supported=SUPPORTED_SAFE_BOARD_SIZE_VARIANTS,
    )
    rows, columns = _board_size_variant_to_dimensions(str(selected))
    if int(target_answer) > int(columns):
        raise ValueError(
            f"safe_move_count target_answer={int(target_answer)} is infeasible "
            f"for board_size_variant={str(selected)} with {int(columns)} columns"
        )
    return str(selected), int(rows), int(columns), dict(probabilities)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual sampling axes for one Connect Four instance."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_scene_variant_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        ),
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    target_support_key = _target_support_key(str(query_id))
    target_params = _target_answer_params_for_query_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, target_support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(target_support_key),
        fallback=getattr(_DEFAULTS, target_support_key),
    )
    if str(query_id) == "safe_move_count":
        board_size_variant, board_rows, board_columns, board_size_variant_probabilities = _resolve_safe_board_size_variant(
            instance_seed=int(instance_seed),
            params=params,
            query_id_probabilities=query_id_probabilities,
            target_answer=int(target_answer),
        )
    else:
        board_size_variant, board_rows, board_columns, board_size_variant_probabilities = _resolve_board_size_variant(
            instance_seed=int(instance_seed),
            params=params,
            query_id_probabilities=query_id_probabilities,
        )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_style_variant_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        ),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_CONNECT_FOUR_STYLE_VARIANTS,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        board_size_variant=str(board_size_variant),
        board_rows=int(board_rows),
        board_columns=int(board_columns),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        board_size_variant_probabilities=dict(board_size_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _resolve_winning_move_column_label_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve axes for the single winning-column label task."""

    query_id_probabilities = {"winning_move_column_label": 1.0}
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant.winning_move_column_label",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    board_size_variant, board_rows, board_columns, board_size_variant_probabilities = _resolve_board_size_variant(
        instance_seed=int(instance_seed),
        params=params,
        query_id_probabilities=query_id_probabilities,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant.winning_move_column_label",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_CONNECT_FOUR_STYLE_VARIANTS,
    )
    return _ResolvedAxes(
        query_id="winning_move_column_label",
        scene_variant=str(scene_variant),
        board_size_variant=str(board_size_variant),
        board_rows=int(board_rows),
        board_columns=int(board_columns),
        style_variant=str(style_variant),
        target_answer=1,
        target_answer_support=(1,),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        board_size_variant_probabilities=dict(board_size_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities={"1": 1.0},
    )


def _resolve_winning_move_label_threat_kind(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the constructed immediate-win pattern for the label task."""

    return _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="winning_move_column_label.threat_kind",
        explicit_key="winning_move_label_threat_kind",
        weights_key="winning_move_label_threat_kind_weights",
        balance_flag_key="balanced_winning_move_label_threat_kind_sampling",
        supported=SUPPORTED_WINNING_MOVE_LABEL_THREAT_KINDS,
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> ConnectFourRenderParams:
    """Resolve Connect Four rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.connect_four.text_font",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.connect_four.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.connect_four.layout",
        ),
        unit_scale_meta,
    )
    max_board_width_px = scale_games_px(
        params.get(
            "max_board_width_px",
            group_default(_RENDER_DEFAULTS, "max_board_width_px", _DEFAULTS.max_board_width_px),
        ),
        unit_scale,
        min_px=390,
    )
    player_badge_height_px = int(
        params.get(
            "player_badge_height_px",
            group_default(_RENDER_DEFAULTS, "player_badge_height_px", _DEFAULTS.player_badge_height_px),
        )
    )
    player_badge_width_px = int(
        params.get(
            "player_badge_width_px",
            group_default(_RENDER_DEFAULTS, "player_badge_width_px", _DEFAULTS.player_badge_width_px),
        )
    )
    header_gap_px = int(params.get("header_gap_px", group_default(_RENDER_DEFAULTS, "header_gap_px", _DEFAULTS.header_gap_px)))
    dynamic_canvas_enabled = bool(
        params.get(
            "dynamic_canvas_size_enabled",
            group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", _DEFAULTS.dynamic_canvas_size_enabled),
        )
    )
    base_canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    base_canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    canvas_width = int(base_canvas_width)
    canvas_height = int(base_canvas_height)
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        canvas_width = min(
            int(base_canvas_width),
            max(
                int(params.get("canvas_min_width_px", group_default(_RENDER_DEFAULTS, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px))),
                int(
                    round(
                        float(max_board_width_px)
                        + (
                            2.0
                            * float(
                                params.get(
                                    "canvas_side_padding_px",
                                    group_default(_RENDER_DEFAULTS, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px),
                                )
                            )
                        )
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
                        float(max_board_width_px)
                        + float(player_badge_height_px)
                        + float(header_gap_px)
                        + (
                            2.0
                            * float(
                                params.get(
                                    "canvas_vertical_padding_px",
                                    group_default(_RENDER_DEFAULTS, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px),
                                )
                            )
                        )
                    )
                ),
            ),
        )
    return ConnectFourRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        panel_margin_px=int(
            params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))
        ),
        player_badge_height_px=int(player_badge_height_px),
        player_badge_width_px=int(player_badge_width_px),
        header_gap_px=int(header_gap_px),
        max_board_width_px=int(max_board_width_px),
        board_corner_radius_px=scale_games_px(
            params.get(
                "board_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px),
            ),
            unit_scale,
            min_px=12,
        ),
        board_frame_width_px=scale_games_px(
            params.get(
                "board_frame_width_px",
                group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px),
            ),
            unit_scale,
            min_px=8,
        ),
        disc_inset_fraction=float(
            params.get(
                "disc_inset_fraction",
                group_default(_RENDER_DEFAULTS, "disc_inset_fraction", _DEFAULTS.disc_inset_fraction),
            )
        ),
        player_badge_font_size_px=int(
            params.get(
                "player_badge_font_size_px",
                group_default(_RENDER_DEFAULTS, "player_badge_font_size_px", _DEFAULTS.player_badge_font_size_px),
            )
        ),
        marked_square_outline_width_px=scale_games_px(
            params.get(
                "marked_square_outline_width_px",
                group_default(_RENDER_DEFAULTS, "marked_square_outline_width_px", _DEFAULTS.marked_square_outline_width_px),
            ),
            unit_scale,
            min_px=3,
        ),
        layout_jitter_meta=layout_jitter,
        font_family=str(font_family),
    )


def _mutable_board(
    board: Board | None = None,
    *,
    rows: int = ROWS,
    columns: int = COLUMNS,
) -> List[List[int]]:
    """Return one mutable board copy."""

    if board is None:
        board = empty_board(rows=int(rows), columns=int(columns))
    return [list(int(cell) for cell in row) for row in board]


def _freeze_board(board: Sequence[Sequence[int]]) -> Board:
    """Freeze one mutable board into the canonical tuple form."""

    return tuple(tuple(int(cell) for cell in row) for row in board)


def _resolve_current_player(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve the current player for one scene."""

    explicit = params.get("current_player")
    if explicit is None:
        return int(RED if int(rng.randrange(2)) == 0 else YELLOW)
    text = str(explicit).strip().lower()
    if text in {"red", "r", "1"}:
        return int(RED)
    if text in {"yellow", "y", "-1"}:
        return int(YELLOW)
    raise ValueError(f"unsupported current_player: {explicit}")


def _safe_move_coords(board: Board, *, current_player: int) -> Tuple[Coord, ...]:
    """Return every legal landing square that leaves the opponent without an immediate win."""

    coords: List[Coord] = []
    opposing_player = int(opponent(int(current_player)))
    for col in sorted(legal_drop_rows(board).keys()):
        next_board, landing_coord = drop_disc(board, int(current_player), int(col))
        if has_connect_four(next_board, int(current_player)):
            continue
        if not winning_drop_map(next_board, int(opposing_player)):
            coords.append(tuple(landing_coord))
    return tuple(sorted(tuple(coord) for coord in coords))


def _evaluate_query(
    *,
    board: Board,
    current_player: int,
    query_id: str,
) -> _QueryEvaluation | None:
    """Evaluate one query id on one visible board."""

    current_wins = winning_drop_map(board, int(current_player))
    winning_coords = tuple(sorted(tuple(coord) for coord, _ in current_wins.values()))
    safe_coords = _safe_move_coords(board, current_player=int(current_player))

    if str(query_id) == "winning_move_count":
        annotation_coords = winning_coords
    elif str(query_id) == "safe_move_count":
        annotation_coords = safe_coords
    else:
        return None

    return _QueryEvaluation(
        answer=int(len(annotation_coords)),
        annotation_coords=tuple(tuple(coord) for coord in annotation_coords),
        annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in annotation_coords),
        winning_move_coords=winning_coords,
        safe_move_coords=safe_coords,
    )


def _construct_vertical_threat_base(
    *,
    rng,
    current_player: int,
    target_answer: int,
    rows: int,
    columns: int,
) -> Tuple[Board, str]:
    """Construct one sparse vertical-threat base board for immediate-win counting."""

    if int(rows) < 4:
        raise ValueError("Connect Four immediate-win construction requires at least 4 rows")
    board = _mutable_board(rows=int(rows), columns=int(columns))
    if int(columns) == 6:
        candidate_columns = (0, 1, 4, 5)
    else:
        candidate_columns = tuple(range(0, int(columns), 2))
    if int(target_answer) > len(candidate_columns):
        raise ValueError("target answer exceeds the supported vertical-threat columns")
    selected_columns = [] if int(target_answer) == 0 else list(rng.sample(candidate_columns, k=int(target_answer)))
    for col in selected_columns:
        for row in range(int(rows) - 1, int(rows) - 4, -1):
            board[int(row)][int(col)] = int(current_player)
    return _freeze_board(board), "vertical_threats"


def _target_column_for_label_task(
    *,
    rng,
    params: Mapping[str, Any],
    columns: int,
) -> Tuple[int, str, Tuple[str, ...]]:
    """Resolve the intended answer column for a winning-column label scene."""

    column_labels = _column_labels_for_columns(int(columns))
    label_to_col = {str(label): int(index) for index, label in enumerate(column_labels)}
    explicit_label = params.get("target_column_label", params.get("answer_label"))
    if explicit_label is not None:
        label = str(explicit_label).strip().upper()
        if label not in label_to_col:
            raise ValueError(f"unsupported target_column_label={explicit_label!r} for {int(columns)} columns")
        return int(label_to_col[str(label)]), str(label), tuple(column_labels)

    explicit_column = params.get("target_column_index")
    if explicit_column is not None:
        column = int(explicit_column)
        if not 0 <= int(column) < int(columns):
            raise ValueError(f"target_column_index={int(column)} is outside a {int(columns)}-column board")
        return int(column), str(column_labels[int(column)]), tuple(column_labels)

    sampling_index = params.get("_sample_cursor")
    if sampling_index is not None:
        column = abs(int(sampling_index)) % int(columns)
    else:
        column = int(rng.randrange(int(columns)))
    return int(column), str(column_labels[int(column)]), tuple(column_labels)


def _horizontal_segment_for_target(*, rng, target_column: int, columns: int) -> Tuple[int, int]:
    """Return a length-four horizontal segment containing the target column."""

    start_min = max(0, int(target_column) - 3)
    start_max = min(int(target_column), int(columns) - 4)
    if int(start_min) > int(start_max):
        raise ValueError("failed to place a horizontal Connect Four threat segment")
    start = int(rng.randint(int(start_min), int(start_max)))
    return int(start), int(start + 3)


def _construct_winning_label_base(
    *,
    rng,
    current_player: int,
    target_column: int,
    rows: int,
    columns: int,
    threat_kind: str,
) -> Tuple[Board, str]:
    """Construct a sparse board with exactly one intended immediate-winning drop column."""

    if int(rows) < 4 or int(columns) < 4:
        raise ValueError("Connect Four winning-column labels require at least 4 rows and 4 columns")
    if not 0 <= int(target_column) < int(columns):
        raise ValueError("target_column is outside the board")

    board = _mutable_board(rows=int(rows), columns=int(columns))
    if str(threat_kind) == "vertical_threat":
        for row in range(int(rows) - 1, int(rows) - 4, -1):
            board[int(row)][int(target_column)] = int(current_player)
        return _freeze_board(board), "single_vertical_threat"

    if str(threat_kind) == "horizontal_threat":
        start, end = _horizontal_segment_for_target(
            rng=rng,
            target_column=int(target_column),
            columns=int(columns),
        )
        bottom_row = int(rows) - 1
        for col in range(int(start), int(end) + 1):
            if int(col) == int(target_column):
                continue
            board[int(bottom_row)][int(col)] = int(current_player)
        return _freeze_board(board), "single_horizontal_threat"

    raise ValueError(f"unsupported winning_move_label_threat_kind: {threat_kind}")


def _occupancy_bounds(scene_variant: str, *, rows: int, columns: int) -> Tuple[int, int]:
    """Return occupied-cell lower and upper bounds for one scene variant."""

    if str(scene_variant) == "crowded_board":
        minimum = int(_DEFAULTS.crowded_min_occupied_count)
        maximum = int(_DEFAULTS.crowded_max_occupied_count)
    else:
        minimum = int(_DEFAULTS.midgame_min_occupied_count)
        maximum = int(_DEFAULTS.midgame_max_occupied_count)
    capacity = int(rows) * int(columns)
    return min(int(minimum), int(capacity) - 1), min(int(maximum), int(capacity) - 1)


def _safe_occupancy_bounds(scene_variant: str, *, rows: int, columns: int) -> Tuple[int, int]:
    """Return denser occupied-cell bounds for safe-move counting scenes."""

    if str(scene_variant) == "crowded_board":
        minimum = int(
            group_default(
                _GEN_DEFAULTS,
                "safe_crowded_min_occupied_count",
                _DEFAULTS.safe_crowded_min_occupied_count,
            )
        )
        maximum = int(
            group_default(
                _GEN_DEFAULTS,
                "safe_crowded_max_occupied_count",
                _DEFAULTS.safe_crowded_max_occupied_count,
            )
        )
    else:
        minimum = int(
            group_default(
                _GEN_DEFAULTS,
                "safe_midgame_min_occupied_count",
                _DEFAULTS.safe_midgame_min_occupied_count,
            )
        )
        maximum = int(
            group_default(
                _GEN_DEFAULTS,
                "safe_midgame_max_occupied_count",
                _DEFAULTS.safe_midgame_max_occupied_count,
            )
        )
    capacity = int(rows) * int(columns)
    return min(int(minimum), int(capacity) - 1), min(int(maximum), int(capacity) - 1)


def _augment_board_density(
    *,
    rng,
    board: Board,
    current_player: int,
    query_id: str,
    target_answer: int,
    scene_variant: str,
) -> Board:
    """Densify one valid board while preserving the query answer."""

    rows, columns = board_dimensions(board)
    minimum_occupied, maximum_occupied = _occupancy_bounds(str(scene_variant), rows=int(rows), columns=int(columns))
    current_board = board
    if int(occupied_cell_count(current_board)) > int(maximum_occupied):
        raise ValueError("base board already exceeds the requested scene occupancy bound")
    if int(occupied_cell_count(current_board)) >= int(minimum_occupied):
        return current_board

    opposing_player = int(opponent(int(current_player)))
    for _ in range(320):
        if int(occupied_cell_count(current_board)) >= int(minimum_occupied):
            break
        landing_rows = legal_drop_rows(current_board)
        candidate_columns = [int(col) for col in sorted(landing_rows.keys())]
        if not candidate_columns:
            break
        success = False
        for _ in range(96):
            candidate_column = int(candidate_columns[int(rng.randrange(len(candidate_columns)))])
            filler_player = int(current_player) if float(rng.random()) < 0.35 else int(opposing_player)
            next_board, _ = drop_disc(current_board, int(filler_player), int(candidate_column))
            if int(occupied_cell_count(next_board)) > int(maximum_occupied):
                continue
            if has_connect_four(next_board, int(current_player)) or has_connect_four(next_board, int(opposing_player)):
                continue
            evaluation = _evaluate_query(
                board=next_board,
                current_player=int(current_player),
                query_id=str(query_id),
            )
            if evaluation is None or int(evaluation.answer) != int(target_answer):
                continue
            current_board = next_board
            success = True
            break
        if not success:
            break
    if int(occupied_cell_count(current_board)) < int(minimum_occupied):
        raise ValueError("failed to densify Connect Four board into the requested scene variant range")
    return current_board


def _sample_column_heights(*, rng, occupied: int, rows: int, columns: int) -> List[int]:
    """Sample one gravity-consistent column-height composition for the requested occupancy."""

    heights = [0] * int(columns)
    column_indices = list(range(int(columns)))
    rng.shuffle(column_indices)
    remaining = int(occupied)
    for index, col in enumerate(column_indices):
        remaining_columns = int(columns - index - 1)
        min_height = max(0, int(remaining - (remaining_columns * int(rows))))
        max_height = min(int(rows), int(remaining))
        height = int(rng.randint(min_height, max_height))
        heights[int(col)] = int(height)
        remaining -= int(height)
    return heights


def _random_gravity_board(
    *,
    rng,
    minimum_occupied: int,
    maximum_occupied: int,
    current_player: int,
    rows: int,
    columns: int,
    search_attempts: int = 1024,
) -> Board:
    """Return one random gravity-consistent non-terminal board."""

    feasible_occupied = []
    for occupied in range(int(minimum_occupied), int(maximum_occupied) + 1):
        if occupied >= int(rows * columns):
            continue
        if int(current_player) == int(RED) and int(occupied) % 2 == 0:
            feasible_occupied.append(int(occupied))
        if int(current_player) == int(YELLOW) and int(occupied) % 2 == 1:
            feasible_occupied.append(int(occupied))
    if not feasible_occupied:
        raise ValueError("no feasible occupied counts match the requested current-player parity")

    for _ in range(max(1, int(search_attempts))):
        occupied = int(feasible_occupied[int(rng.randrange(len(feasible_occupied)))])
        heights = _sample_column_heights(
            rng=rng,
            occupied=int(occupied),
            rows=int(rows),
            columns=int(columns),
        )
        if max(heights) == 0:
            continue
        if int(current_player) == int(RED):
            red_count = yellow_count = int(occupied // 2)
        else:
            red_count = int((occupied + 1) // 2)
            yellow_count = int((occupied - 1) // 2)
        colors = [int(RED)] * int(red_count) + [int(YELLOW)] * int(yellow_count)
        rng.shuffle(colors)
        board = _mutable_board(rows=int(rows), columns=int(columns))
        color_index = 0
        for col in range(int(columns)):
            for offset in range(int(heights[col])):
                row = int(rows - 1 - offset)
                board[row][col] = int(colors[color_index])
                color_index += 1
        frozen = _freeze_board(board)
        if has_connect_four(frozen, int(RED)) or has_connect_four(frozen, int(YELLOW)):
            continue
        return frozen
    raise ValueError("failed to sample one gravity-consistent Connect Four board")


def _construct_safe_move_board(
    *,
    rng,
    current_player: int,
    target_answer: int,
    scene_variant: str,
    rows: int,
    columns: int,
) -> Tuple[Board, str]:
    """Construct one board whose safe-move count matches the requested answer."""

    minimum_occupied, maximum_occupied = _safe_occupancy_bounds(str(scene_variant), rows=int(rows), columns=int(columns))
    for _ in range(72):
        board = _random_gravity_board(
            rng=rng,
            minimum_occupied=int(minimum_occupied),
            maximum_occupied=int(maximum_occupied),
            current_player=int(current_player),
            rows=int(rows),
            columns=int(columns),
            search_attempts=48,
        )
        if winning_drop_map(board, int(current_player)):
            continue
        evaluation = _evaluate_query(
            board=board,
            current_player=int(current_player),
            query_id="safe_move_count",
        )
        if evaluation is None or int(evaluation.answer) != int(target_answer):
            continue
        return board, "safe_move_search"
    raise ValueError("failed to construct one safe-move Connect Four board")


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SampledConnectFourScene:
    """Construct one Connect Four scene consistent with the requested axes."""

    current_player = _resolve_current_player(rng, params=params)
    if str(axes.query_id) == "winning_move_count":
        base_board, construction_mode = _construct_vertical_threat_base(
            rng=rng,
            current_player=int(current_player),
            target_answer=int(axes.target_answer),
            rows=int(axes.board_rows),
            columns=int(axes.board_columns),
        )
        board = _augment_board_density(
            rng=rng,
            board=base_board,
            current_player=int(current_player),
            query_id=str(axes.query_id),
            target_answer=int(axes.target_answer),
            scene_variant=str(axes.scene_variant),
        )
    else:
        board, construction_mode = _construct_safe_move_board(
            rng=rng,
            current_player=int(current_player),
            target_answer=int(axes.target_answer),
            scene_variant=str(axes.scene_variant),
            rows=int(axes.board_rows),
            columns=int(axes.board_columns),
        )

    evaluation = _evaluate_query(
        board=board,
        current_player=int(current_player),
        query_id=str(axes.query_id),
    )
    if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
        raise ValueError("final Connect Four board does not match the requested target answer")
    return _SampledConnectFourScene(
        board=board,
        current_player=int(current_player),
        evaluation=evaluation,
        occupied_count=int(occupied_cell_count(board)),
        construction_mode=str(construction_mode),
    )


def _sample_winning_column_label_scene(
    *,
    rng,
    axes: _ResolvedAxes,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _SampledConnectFourLabelScene:
    """Construct one Connect Four scene with exactly one immediate winning column."""

    current_player = _resolve_current_player(rng, params=params)
    threat_kind, threat_kind_probabilities = _resolve_winning_move_label_threat_kind(
        instance_seed=int(instance_seed),
        params=params,
    )
    target_column, answer_label, column_labels = _target_column_for_label_task(
        rng=rng,
        params=params,
        columns=int(axes.board_columns),
    )
    base_board, construction_mode = _construct_winning_label_base(
        rng=rng,
        current_player=int(current_player),
        target_column=int(target_column),
        rows=int(axes.board_rows),
        columns=int(axes.board_columns),
        threat_kind=str(threat_kind),
    )
    board = _augment_board_density(
        rng=rng,
        board=base_board,
        current_player=int(current_player),
        query_id="winning_move_count",
        target_answer=1,
        scene_variant=str(axes.scene_variant),
    )
    evaluation = _evaluate_query(
        board=board,
        current_player=int(current_player),
        query_id="winning_move_count",
    )
    if evaluation is None or int(evaluation.answer) != 1:
        raise ValueError("final Connect Four board does not have exactly one winning move")
    winning_map = winning_drop_map(board, int(current_player))
    if set(winning_map.keys()) != {int(target_column)}:
        raise ValueError("final Connect Four board did not preserve the target winning column")
    _landing_coord, completed_lines = winning_map[int(target_column)]
    if not completed_lines:
        raise ValueError("target winning column has no completed line")
    return _SampledConnectFourLabelScene(
        board=board,
        current_player=int(current_player),
        evaluation=evaluation,
        occupied_count=int(occupied_cell_count(board)),
        construction_mode=str(construction_mode),
        threat_kind=str(threat_kind),
        threat_kind_probabilities=dict(threat_kind_probabilities),
        column_labels=tuple(str(label) for label in column_labels),
        answer_label=str(answer_label),
        answer_column=int(target_column),
        winning_line_coords=tuple(tuple(coord) for coord in completed_lines[0]),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return deterministic prompt examples for Connect Four JSON output."""

    answer_value = 2
    annotation_value = [[210, 340, 300, 430], [390, 340, 480, 430]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _build_winning_column_label_prompt_json_examples() -> Tuple[str, str]:
    """Return deterministic prompt examples for a winning-column label JSON output."""

    answer_value = "D"
    annotation_value = [[390, 340, 480, 430]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _object_description(
    *,
    prompt_defaults: Mapping[str, Any],
    scene_variant: str,
    board_size_variant: str,
) -> str:
    """Return a prompt-facing scene description that includes board dimensions."""

    base_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
    if str(board_size_variant) == "square_5x5":
        return str(base_description).replace("a Connect Four board", "a 5-column by 5-row Connect Four board")
    if str(board_size_variant) == "square_6x6":
        return str(base_description).replace("a Connect Four board", "a 6-column by 6-row Connect Four board")
    if str(board_size_variant) == "small_6x5":
        return str(base_description).replace("a Connect Four board", "a 6-column by 5-row Connect Four board")
    return str(base_description).replace("a Connect Four board", "a standard 7-column by 6-row Connect Four board")


class GamesConnectFourMoveCountTask:
    """Return one grounded counting query over a visible Connect Four board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "connect_four"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: _SampledConnectFourScene | None = None
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
            namespace="games.connect_four_board.panel_scene_style",
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
        rendered_scene = render_connect_four_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            current_player=int(sampled_scene.current_player),
            params=render_params,
            marked_square=None,
            panel_style=panel_style,
        )
        annotation_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evaluation.annotation_entity_ids
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
                "object_description_midgame_board",
                "object_description_crowded_board",
                "legal_drop_rule_text",
                "winning_rule_text",
                "safety_rule_text",
                "answer_hint_winning_move_count",
                "answer_hint_safe_move_count",
                "annotation_hint_winning_move_count",
                "annotation_hint_safe_move_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples()
        current_player_name = player_name(int(sampled_scene.current_player))
        opponent_player_name = player_name(int(opponent(int(sampled_scene.current_player))))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": _object_description(
                    prompt_defaults=prompt_defaults,
                    scene_variant=str(axes.scene_variant),
                    board_size_variant=str(axes.board_size_variant),
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "current_player_name": str(current_player_name),
                "opponent_player_name": str(opponent_player_name),
                "legal_drop_rule_text": str(prompt_defaults["legal_drop_rule_text"]),
                "winning_rule_text": str(prompt_defaults["winning_rule_text"]),
                "safety_rule_text": str(prompt_defaults["safety_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.evaluation.answer))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        complexity = build_games_connect_four_move_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            occupied_count=int(sampled_scene.occupied_count),
            target_answer=int(axes.target_answer),
            annotation_count=len(sampled_scene.evaluation.annotation_entity_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_connect_four_board_{str(axes.scene_variant)}_{str(axes.board_size_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "board_size_variant": str(axes.board_size_variant),
                    "board_row_count": int(axes.board_rows),
                    "board_column_count": int(axes.board_columns),
                    "style_variant": str(axes.style_variant),
                    "current_player": str(current_player_name),
                    "target_answer": int(sampled_scene.evaluation.answer),
                    "occupied_count": int(sampled_scene.occupied_count),
                    "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.annotation_entity_ids],
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
                    "board_size_variant": str(axes.board_size_variant),
                    "board_row_count": int(axes.board_rows),
                    "board_column_count": int(axes.board_columns),
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "board_size_variant_probabilities": dict(axes.board_size_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "current_player": str(current_player_name),
                    "opponent_player": str(opponent_player_name),
                    "target_answer": int(sampled_scene.evaluation.answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "occupied_count": int(sampled_scene.occupied_count),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "board_size_variant": str(axes.board_size_variant),
                "board_row_count": int(axes.board_rows),
                "board_column_count": int(axes.board_columns),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
                "effective_cell_size_px": rendered_scene.render_map.get("effective_cell_size_px"),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "board_size_variant": str(axes.board_size_variant),
                "board_row_count": int(axes.board_rows),
                "board_column_count": int(axes.board_columns),
                "style_variant": str(axes.style_variant),
                "current_player": str(current_player_name),
                "opponent_player": str(opponent_player_name),
                "target_answer": int(sampled_scene.evaluation.answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "occupied_count": int(sampled_scene.occupied_count),
                "construction_mode": str(sampled_scene.construction_mode),
                "board_rows": [[int(cell) for cell in row] for row in sampled_scene.board],
                "winning_move_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.winning_move_coords],
                "safe_move_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.safe_move_coords],
                "annotation_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.annotation_coords],
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.annotation_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evaluation.annotation_entity_ids],
            },
            "projected_annotation": {
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
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
            query_id=str(axes.query_id),
            scene_id="connect_four",
        )


@register_task
class GamesConnectFourWinningMoveColumnLabelTask:
    """Select the labeled Connect Four column that wins immediately."""

    task_id = "task_games__connect_four__winning_move_column_label"
    domain = "games"
    task_group = "connect_four"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_winning_move_column_label_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: _SampledConnectFourLabelScene | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{self.task_id}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_winning_column_label_scene(
                    rng=attempt_rng,
                    axes=axes,
                    params=params,
                    instance_seed=int(instance_seed),
                )
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
            namespace="games.connect_four_board.panel_scene_style",
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
        rendered_scene = render_connect_four_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            current_player=int(sampled_scene.current_player),
            params=render_params,
            marked_square=None,
            panel_style=panel_style,
            column_labels=sampled_scene.column_labels,
        )
        if len(sampled_scene.evaluation.annotation_entity_ids) != 1:
            raise RuntimeError("winning-column label task expects exactly one landing-cell witness")
        annotation_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evaluation.annotation_entity_ids
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
                "object_description_midgame_board",
                "object_description_crowded_board",
                "legal_drop_rule_text",
                "winning_rule_text",
                "answer_hint_winning_move_column_label",
                "annotation_hint_winning_move_column_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_winning_column_label_prompt_json_examples()
        current_player_name = player_name(int(sampled_scene.current_player))
        opponent_player_name = player_name(int(opponent(int(sampled_scene.current_player))))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": _object_description(
                    prompt_defaults=prompt_defaults,
                    scene_variant=str(axes.scene_variant),
                    board_size_variant=str(axes.board_size_variant),
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint_winning_move_column_label"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_winning_move_column_label"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "current_player_name": str(current_player_name),
                "opponent_player_name": str(opponent_player_name),
                "legal_drop_rule_text": str(prompt_defaults["legal_drop_rule_text"]),
                "winning_rule_text": str(prompt_defaults["winning_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="string", value=str(sampled_scene.answer_label))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        complexity = build_games_connect_four_move_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            occupied_count=int(sampled_scene.occupied_count),
            target_answer=1,
            annotation_count=1,
        )

        winning_coord = sampled_scene.evaluation.annotation_coords[0]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_connect_four_board_{str(axes.scene_variant)}_{str(axes.board_size_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "board_size_variant": str(axes.board_size_variant),
                    "board_row_count": int(axes.board_rows),
                    "board_column_count": int(axes.board_columns),
                    "style_variant": str(axes.style_variant),
                    "current_player": str(current_player_name),
                    "answer_label": str(sampled_scene.answer_label),
                    "answer_column": int(sampled_scene.answer_column),
                    "winning_move_coord": [int(winning_coord[0]), int(winning_coord[1])],
                    "winning_move_entity_id": str(sampled_scene.evaluation.annotation_entity_ids[0]),
                    "column_labels": [str(label) for label in sampled_scene.column_labels],
                    "occupied_count": int(sampled_scene.occupied_count),
                    "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.annotation_entity_ids],
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
                    "board_size_variant": str(axes.board_size_variant),
                    "board_row_count": int(axes.board_rows),
                    "board_column_count": int(axes.board_columns),
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "board_size_variant_probabilities": dict(axes.board_size_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "threat_kind": str(sampled_scene.threat_kind),
                    "threat_kind_probabilities": dict(sampled_scene.threat_kind_probabilities),
                    "current_player": str(current_player_name),
                    "opponent_player": str(opponent_player_name),
                    "answer_label": str(sampled_scene.answer_label),
                    "answer_column": int(sampled_scene.answer_column),
                    "column_labels": [str(label) for label in sampled_scene.column_labels],
                    "occupied_count": int(sampled_scene.occupied_count),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "board_size_variant": str(axes.board_size_variant),
                "board_row_count": int(axes.board_rows),
                "board_column_count": int(axes.board_columns),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
                "effective_cell_size_px": rendered_scene.render_map.get("effective_cell_size_px"),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "board_size_variant": str(axes.board_size_variant),
                "board_row_count": int(axes.board_rows),
                "board_column_count": int(axes.board_columns),
                "style_variant": str(axes.style_variant),
                "threat_kind": str(sampled_scene.threat_kind),
                "current_player": str(current_player_name),
                "opponent_player": str(opponent_player_name),
                "answer_label": str(sampled_scene.answer_label),
                "answer_column": int(sampled_scene.answer_column),
                "column_labels": [str(label) for label in sampled_scene.column_labels],
                "occupied_count": int(sampled_scene.occupied_count),
                "construction_mode": str(sampled_scene.construction_mode),
                "board_rows": [[int(cell) for cell in row] for row in sampled_scene.board],
                "winning_move_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.winning_move_coords],
                "winning_line_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.winning_line_coords],
                "annotation_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.annotation_coords],
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.annotation_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evaluation.annotation_entity_ids],
            },
            "projected_annotation": {
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
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
            query_id=str(axes.query_id),
            scene_id="connect_four",
        )


@register_task
class GamesConnectFourWinningMoveCountTask(QuerySubsetTaskMixin, GamesConnectFourMoveCountTask):
    """Count Connect Four drop columns that win immediately."""

    task_id = "task_games__connect_four__winning_move_count"
    supported_query_ids = ("winning_move_count",)


@register_task
class GamesConnectFourSafeMoveCountTask(QuerySubsetTaskMixin, GamesConnectFourMoveCountTask):
    """Count Connect Four drop columns that avoid an immediate reply win."""

    task_id = "task_games__connect_four__safe_move_count"
    supported_query_ids = ("safe_move_count",)


__all__ = [
    "GamesConnectFourSafeMoveCountTask",
    "GamesConnectFourWinningMoveColumnLabelTask",
    "GamesConnectFourWinningMoveCountTask",
]
