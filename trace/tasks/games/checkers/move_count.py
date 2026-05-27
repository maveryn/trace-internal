"""Games Checkers task for grounded move-count queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

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
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.checkers_common import (
    BLACK,
    BOARD_SIZE,
    RED,
    Board,
    CheckersCaptureChain,
    CheckersMove,
    Coord,
    allowed_non_king_row,
    coord_to_cell_id,
    empty_board,
    enumerate_king_capture_chains,
    enumerate_legal_moves,
    freeze_board,
    occupied_piece_count,
    opponent,
    playable_coords,
    piece_to_entity_id,
    player_name,
)
from ..shared.checkers_scene import CheckersRenderParams, render_checkers_board_scene
from ..shared.complexity import build_games_checkers_move_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.style import SUPPORTED_CHECKERS_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_checkers_move_count_base"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "midgame_board",
    "crowded_board",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "legal_move_count",
    "capture_move_count",
    "max_capture_chain_length",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Checkers move-count scenes."""

    legal_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    capture_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    max_capture_chain_length_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    midgame_min_occupied_count: int = 8
    midgame_max_occupied_count: int = 12
    crowded_min_occupied_count: int = 13
    crowded_max_occupied_count: int = 17
    canvas_width: int = 980
    canvas_height: int = 920
    panel_margin_px: int = 48
    player_badge_height_px: int = 52
    player_badge_width_px: int = 230
    header_gap_px: int = 18
    max_board_size_px: int = 780
    board_corner_radius_px: int = 26
    board_frame_width_px: int = 10
    piece_inset_fraction: float = 0.17
    player_badge_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Checkers scene."""

    query_id: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SceneEvaluation:
    """Query-specific evaluation payload derived from one finalized board."""

    answer: int
    legal_moves: Tuple[CheckersMove, ...]
    capture_moves: Tuple[CheckersMove, ...]
    evidence_coords: Tuple[Coord, ...]
    evidence_entity_ids: Tuple[str, ...]
    evidence_kind: str = "cell"
    marked_coord: Coord | None = None
    max_capture_chains: Tuple[CheckersCaptureChain, ...] = ()
    selected_capture_chain: CheckersCaptureChain | None = None


@dataclass(frozen=True)
class _SampledCheckersScene:
    """One sampled Checkers scene plus query-specific witness metadata."""

    board: Board
    current_player: int
    evaluation: _SceneEvaluation
    occupied_count: int
    construction_mode: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "checkers")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="checkers")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="checkers", apply_prob=0.0)


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one query id."""

    return {
        "legal_move_count": "legal_move_count_support",
        "capture_move_count": "capture_move_count_support",
        "max_capture_chain_length": "max_capture_chain_length_support",
    }[str(query_id)]


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
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
        group_default(_GEN_DEFAULTS, "style_variant_weights", {key: 1.0 for key in SUPPORTED_CHECKERS_STYLE_VARIANTS}),
    )
    if not isinstance(raw_weights, Mapping):
        return style_params
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_CHECKERS_STYLE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_CHECKERS_STYLE_VARIANTS):
        return style_params
    if max(positives) - min(positives) > 1e-9:
        return style_params
    style_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return style_params


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query id, honoring `query_id` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_id") is None and alias_params.get("query_id") is not None:
        alias_params["query_id"] = alias_params["query_id"]
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
    """Resolve one balanced named axis for the Checkers task."""

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


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual sampling axes for one Checkers instance."""

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
        supported=SUPPORTED_CHECKERS_STYLE_VARIANTS,
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
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> CheckersRenderParams:
    """Resolve Checkers rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.checkers.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.checkers.layout",
        ),
        unit_scale_meta,
    )
    return CheckersRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        player_badge_height_px=int(
            params.get(
                "player_badge_height_px",
                group_default(_RENDER_DEFAULTS, "player_badge_height_px", _DEFAULTS.player_badge_height_px),
            )
        ),
        player_badge_width_px=int(
            params.get(
                "player_badge_width_px",
                group_default(_RENDER_DEFAULTS, "player_badge_width_px", _DEFAULTS.player_badge_width_px),
            )
        ),
        header_gap_px=int(params.get("header_gap_px", group_default(_RENDER_DEFAULTS, "header_gap_px", _DEFAULTS.header_gap_px))),
        max_board_size_px=scale_games_px(
            params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)),
            unit_scale,
            min_px=390,
        ),
        board_corner_radius_px=scale_games_px(
            params.get(
                "board_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px),
            ),
            unit_scale,
            min_px=10,
        ),
        board_frame_width_px=scale_games_px(
            params.get(
                "board_frame_width_px",
                group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px),
            ),
            unit_scale,
            min_px=5,
        ),
        piece_inset_fraction=float(
            params.get(
                "piece_inset_fraction",
                group_default(_RENDER_DEFAULTS, "piece_inset_fraction", _DEFAULTS.piece_inset_fraction),
            )
        ),
        player_badge_font_size_px=int(
            params.get(
                "player_badge_font_size_px",
                group_default(_RENDER_DEFAULTS, "player_badge_font_size_px", _DEFAULTS.player_badge_font_size_px),
            )
        ),
        layout_jitter_meta=layout_jitter,
    )


def _resolve_current_player(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve the current player for one scene."""

    explicit = params.get("current_player")
    if explicit is None:
        return int(RED if int(rng.randrange(2)) == 0 else BLACK)
    text = str(explicit).strip().lower()
    if text in {"red", "r", "1"}:
        return int(RED)
    if text in {"black", "b", "-1"}:
        return int(BLACK)
    raise ValueError(f"unsupported current_player: {explicit}")


def _scene_occupied_range(scene_variant: str) -> Tuple[int, int]:
    """Return the target occupied-piece range for one scene family."""

    if str(scene_variant) == "crowded_board":
        return (int(_DEFAULTS.crowded_min_occupied_count), int(_DEFAULTS.crowded_max_occupied_count))
    return (int(_DEFAULTS.midgame_min_occupied_count), int(_DEFAULTS.midgame_max_occupied_count))


def _quiet_slots(player: int) -> Tuple[Tuple[Coord, Coord], ...]:
    """Return non-overlapping one-step edge move templates for one player."""

    if int(player) == int(RED):
        return (
            ((1, 0), (0, 1)),
            ((1, 6), (0, 7)),
            ((3, 0), (2, 1)),
            ((3, 6), (2, 7)),
            ((5, 0), (4, 1)),
            ((5, 6), (4, 7)),
        )
    return (
        ((0, 7), (1, 6)),
        ((1, 0), (2, 1)),
        ((2, 7), (3, 6)),
        ((3, 0), (4, 1)),
        ((4, 7), (5, 6)),
        ((5, 0), (6, 1)),
    )


def _capture_slots(player: int) -> Tuple[Tuple[Coord, Coord, Coord], ...]:
    """Return non-overlapping single-jump edge capture templates for one player."""

    if int(player) == int(RED):
        return (
            ((3, 0), (2, 1), (1, 2)),
            ((5, 0), (4, 1), (3, 2)),
            ((7, 0), (6, 1), (5, 2)),
            ((2, 7), (1, 6), (0, 5)),
            ((4, 7), (3, 6), (2, 5)),
            ((6, 7), (5, 6), (4, 5)),
        )
    return (
        ((0, 7), (1, 6), (2, 5)),
        ((1, 0), (2, 1), (3, 2)),
        ((2, 7), (3, 6), (4, 5)),
        ((3, 0), (4, 1), (5, 2)),
        ((4, 7), (5, 6), (6, 5)),
        ((5, 0), (6, 1), (7, 2)),
    )


_KING_CHAIN_TEMPLATE: Tuple[Coord, ...] = (
    (0, 1),
    (2, 3),
    (4, 1),
    (6, 3),
    (4, 5),
    (6, 7),
)


def _transform_king_chain_template(rng) -> Tuple[Coord, ...]:
    """Return one reflected king-capture template with five possible jumps."""

    flip_rows = bool(rng.randrange(2))
    flip_cols = bool(rng.randrange(2))
    coords: list[Coord] = []
    for row, col in _KING_CHAIN_TEMPLATE:
        out_row = BOARD_SIZE - 1 - int(row) if flip_rows else int(row)
        out_col = BOARD_SIZE - 1 - int(col) if flip_cols else int(col)
        coords.append((int(out_row), int(out_col)))
    return tuple(coords)


def _base_king_chain_board(*, rng, current_player: int, target_answer: int) -> Tuple[Board, Coord]:
    """Construct a board with one unique marked-king capture chain prefix."""

    if not (1 <= int(target_answer) <= 5):
        raise ValueError("max_capture_chain_length target must be in 1..5")
    landing_path = _transform_king_chain_template(rng)[: int(target_answer) + 1]
    mutable = [list(int(cell) for cell in row) for row in empty_board()]
    marked_coord = landing_path[0]
    mutable[int(marked_coord[0])][int(marked_coord[1])] = int(current_player)
    for origin, landing in zip(landing_path, landing_path[1:]):
        captured = ((int(origin[0]) + int(landing[0])) // 2, (int(origin[1]) + int(landing[1])) // 2)
        mutable[int(captured[0])][int(captured[1])] = int(opponent(int(current_player)))
    return freeze_board(mutable), marked_coord


def _evaluate_board(
    *,
    board: Board,
    current_player: int,
    query_id: str,
    marked_coord: Coord | None = None,
) -> _SceneEvaluation | None:
    """Evaluate one finalized board under the active query semantics."""

    legal_moves = tuple(enumerate_legal_moves(board, int(current_player)))
    capture_moves = tuple(move for move in legal_moves if move.captured is not None)
    if str(query_id) == "max_capture_chain_length":
        if marked_coord is None:
            return None
        marked = (int(marked_coord[0]), int(marked_coord[1]))
        if int(board[marked[0]][marked[1]]) != int(current_player):
            return None
        chains = tuple(enumerate_king_capture_chains(board, player=int(current_player), origin=marked))
        if not chains:
            return None
        max_length = max(len(chain.captured) for chain in chains)
        max_chains = tuple(chain for chain in chains if len(chain.captured) == int(max_length))
        if len(max_chains) != 1:
            return None
        selected = max_chains[0]
        evidence_coords = tuple(selected.captured)
        return _SceneEvaluation(
            answer=int(max_length),
            legal_moves=legal_moves,
            capture_moves=capture_moves,
            evidence_coords=evidence_coords,
            evidence_entity_ids=tuple(
                piece_to_entity_id(coord, player=opponent(int(current_player))) for coord in evidence_coords
            ),
            evidence_kind="piece",
            marked_coord=marked,
            max_capture_chains=max_chains,
            selected_capture_chain=selected,
        )
    relevant_moves = legal_moves if str(query_id) == "legal_move_count" else capture_moves
    destinations = tuple((int(move.landing[0]), int(move.landing[1])) for move in relevant_moves)
    if len(set(destinations)) != len(destinations):
        return None
    evidence_coords = tuple(sorted(set(destinations)))
    return _SceneEvaluation(
        answer=int(len(relevant_moves)),
        legal_moves=legal_moves,
        capture_moves=capture_moves,
        evidence_coords=evidence_coords,
        evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in evidence_coords),
    )


def _base_board_for_axes(*, rng, current_player: int, query_id: str, target_answer: int) -> Tuple[Board, str, Coord | None]:
    """Construct one sparse base board that already meets the requested answer."""

    mutable = [list(int(cell) for cell in row) for row in empty_board()]
    if str(query_id) == "max_capture_chain_length":
        board, marked_coord = _base_king_chain_board(
            rng=rng,
            current_player=int(current_player),
            target_answer=int(target_answer),
        )
        return board, "marked_king_capture_chain", marked_coord

    if str(query_id) == "legal_move_count":
        if int(target_answer) > 0:
            selected_slots = list(rng.sample(_quiet_slots(int(current_player)), k=int(target_answer)))
            for origin, _landing in selected_slots:
                mutable[int(origin[0])][int(origin[1])] = int(current_player)
            return freeze_board(mutable), "quiet_edge_templates", None
        return freeze_board(mutable), "empty_zero_legal", None

    if int(target_answer) > 0:
        selected_slots = list(rng.sample(_capture_slots(int(current_player)), k=int(target_answer)))
        for origin, captured, _landing in selected_slots:
            mutable[int(origin[0])][int(origin[1])] = int(current_player)
            mutable[int(captured[0])][int(captured[1])] = int(opponent(int(current_player)))
        return freeze_board(mutable), "capture_edge_templates", None

    quiet_slots = _quiet_slots(int(current_player))
    quiet_count = min(len(quiet_slots), max(1, int(rng.randint(2, 4))))
    selected_slots = list(rng.sample(quiet_slots, k=int(quiet_count)))
    for origin, _landing in selected_slots:
        mutable[int(origin[0])][int(origin[1])] = int(current_player)
    return freeze_board(mutable), "quiet_zero_capture", None


def _try_add_fillers(
    *,
    rng,
    board: Board,
    current_player: int,
    query_id: str,
    target_answer: int,
    scene_variant: str,
    marked_coord: Coord | None = None,
) -> Tuple[Board, _SceneEvaluation, int]:
    """Add non-semantic filler pieces while preserving the requested answer."""

    min_occupied, max_occupied = _scene_occupied_range(str(scene_variant))
    desired_occupied = int(rng.randint(int(min_occupied), int(max_occupied)))
    mutable = [list(int(cell) for cell in row) for row in board]
    current_occupied = int(occupied_piece_count(mutable))
    evaluation = _evaluate_board(
        board=freeze_board(mutable),
        current_player=int(current_player),
        query_id=str(query_id),
        marked_coord=marked_coord,
    )
    if evaluation is None or int(evaluation.answer) != int(target_answer):
        raise ValueError("base board did not satisfy the requested checkers answer")

    playable = list(playable_coords())
    attempts = 0
    while int(current_occupied) < int(desired_occupied) and attempts < 640:
        attempts += 1
        row, col = playable[int(rng.randrange(len(playable)))]
        if int(mutable[row][col]) != 0:
            continue
        piece_player = int(current_player if float(rng.random()) < 0.36 else opponent(int(current_player)))
        if not allowed_non_king_row(int(piece_player), int(row)):
            continue
        mutable[row][col] = int(piece_player)
        frozen = freeze_board(mutable)
        candidate = _evaluate_board(
            board=frozen,
            current_player=int(current_player),
            query_id=str(query_id),
            marked_coord=marked_coord,
        )
        if candidate is None or int(candidate.answer) != int(target_answer):
            mutable[row][col] = 0
            continue
        evaluation = candidate
        current_occupied = int(occupied_piece_count(mutable))

    frozen = freeze_board(mutable)
    evaluation = _evaluate_board(
        board=frozen,
        current_player=int(current_player),
        query_id=str(query_id),
        marked_coord=marked_coord,
    )
    final_occupied = int(occupied_piece_count(frozen))
    if evaluation is None or int(evaluation.answer) != int(target_answer):
        raise ValueError("failed to preserve the requested checkers answer after filler placement")
    if not (int(min_occupied) <= int(final_occupied) <= int(max_occupied)):
        raise ValueError("failed to reach the requested scene-density range for checkers")
    return frozen, evaluation, final_occupied


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SampledCheckersScene:
    """Construct one Checkers scene consistent with the requested axes."""

    current_player = _resolve_current_player(rng, params=params)
    base_board, base_mode, marked_coord = _base_board_for_axes(
        rng=rng,
        current_player=int(current_player),
        query_id=str(axes.query_id),
        target_answer=int(axes.target_answer),
    )
    board, evaluation, occupied_count = _try_add_fillers(
        rng=rng,
        board=base_board,
        current_player=int(current_player),
        query_id=str(axes.query_id),
        target_answer=int(axes.target_answer),
        scene_variant=str(axes.scene_variant),
        marked_coord=marked_coord,
    )
    return _SampledCheckersScene(
        board=board,
        current_player=int(current_player),
        evaluation=evaluation,
        occupied_count=int(occupied_count),
        construction_mode=str(base_mode),
    )


def _build_prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for the active Checkers query id."""

    answer_value = 4 if str(query_id) == "max_capture_chain_length" else 2 if str(query_id) == "capture_move_count" else 3
    evidence_value = [[132, 188, 196, 252], [204, 188, 268, 252]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _movement_rule_text(current_player: int) -> str:
    """Return the prompt-facing forward-movement rule text."""

    if int(current_player) == int(RED):
        return "Only dark squares are playable; Red moves upward and Black moves downward."
    return "Only dark squares are playable; Black moves downward and Red moves upward."


class GamesCheckersMoveCountTask:
    """Return one grounded counting query over a visible Checkers board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "checkers"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: _SampledCheckersScene | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
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
        rendered_scene = render_checkers_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            current_player=int(sampled_scene.current_player),
            params=render_params,
            marked_coord=sampled_scene.evaluation.marked_coord,
            king_coords=() if sampled_scene.evaluation.marked_coord is None else (sampled_scene.evaluation.marked_coord,),
        )
        if str(sampled_scene.evaluation.evidence_kind) == "piece":
            evidence_bboxes = [
                list(rendered_scene.render_map["piece_bboxes_px"][str(entity_id)])
                for entity_id in sampled_scene.evaluation.evidence_entity_ids
            ]
        else:
            evidence_bboxes = [
                list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
                for entity_id in sampled_scene.evaluation.evidence_entity_ids
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
                "capture_rule_text",
                "single_jump_rule_text",
                "legal_move_rule_text",
                "king_chain_rule_text",
                "answer_hint_legal_move_count",
                "answer_hint_capture_move_count",
                "answer_hint_max_capture_chain_length",
                "evidence_hint_legal_move_count",
                "evidence_hint_capture_move_count",
                "evidence_hint_max_capture_chain_length",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_id=str(axes.query_id))
        current_player_name = player_name(int(sampled_scene.current_player))
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
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "current_player_name": str(current_player_name),
                "movement_rule_text": str(_movement_rule_text(int(sampled_scene.current_player))),
                "capture_rule_text": str(prompt_defaults["capture_rule_text"]),
                "single_jump_rule_text": str(prompt_defaults["single_jump_rule_text"]),
                "legal_move_rule_text": str(prompt_defaults["legal_move_rule_text"]),
                "king_chain_rule_text": str(prompt_defaults["king_chain_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_checkers_move_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            occupied_count=int(sampled_scene.occupied_count),
            target_answer=int(axes.target_answer),
            evidence_count=len(sampled_scene.evaluation.evidence_entity_ids),
        )

        legal_move_specs = [
            {
                "origin": [int(move.origin[0]), int(move.origin[1])],
                "landing": [int(move.landing[0]), int(move.landing[1])],
                "captured": None if move.captured is None else [int(move.captured[0]), int(move.captured[1])],
                "landing_cell_id": str(coord_to_cell_id(move.landing)),
            }
            for move in sorted(
                sampled_scene.evaluation.legal_moves,
                key=lambda move: (move.origin[0], move.origin[1], move.landing[0], move.landing[1]),
            )
        ]
        board_rows = [[int(cell) for cell in row] for row in sampled_scene.board]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_checkers_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(BOARD_SIZE),
                    "current_player": str(current_player_name),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
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
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "board_size": int(BOARD_SIZE),
                    "current_player": str(current_player_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "board_size": int(BOARD_SIZE),
                "current_player": str(current_player_name),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "board_rows": board_rows,
                "construction_mode": str(sampled_scene.construction_mode),
                "occupied_count": int(sampled_scene.occupied_count),
                "legal_move_count": int(len(sampled_scene.evaluation.legal_moves)),
                "capture_move_count": int(len(sampled_scene.evaluation.capture_moves)),
                "legal_move_specs": legal_move_specs,
                "marked_coord": None
                if sampled_scene.evaluation.marked_coord is None
                else [int(sampled_scene.evaluation.marked_coord[0]), int(sampled_scene.evaluation.marked_coord[1])],
                "marked_piece_kind": "king" if sampled_scene.evaluation.marked_coord is not None else None,
                "max_capture_chain_length": None
                if sampled_scene.evaluation.selected_capture_chain is None
                else int(len(sampled_scene.evaluation.selected_capture_chain.captured)),
                "max_capture_chain_specs": [
                    {
                        "origin": [int(chain.origin[0]), int(chain.origin[1])],
                        "landings": [[int(row), int(col)] for row, col in chain.landings],
                        "captured": [[int(row), int(col)] for row, col in chain.captured],
                    }
                    for chain in sampled_scene.evaluation.max_capture_chains
                ],
                "evidence_kind": str(sampled_scene.evaluation.evidence_kind),
                "evidence_coords": [
                    [int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.evidence_coords
                ],
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
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
            scene_id="checkers",
            query_id=str(axes.query_id),
        )


@register_task
class GamesCheckersMoveCountPublicTask(QuerySubsetTaskMixin, GamesCheckersMoveCountTask):
    """Count Checkers landing squares matching one sampled move condition."""

    task_id = "task_games__checkers__move_count"
    supported_query_ids = (
        "legal_move_count",
        "capture_move_count",
    )


@register_task
class GamesCheckersMaxCaptureChainLengthTask(FixedQueryVariantTaskMixin, GamesCheckersMoveCountTask):
    """Find the maximum capture-chain length for the marked king checker."""

    task_id = "task_games__checkers__max_capture_chain_length"
    fixed_query_id = "max_capture_chain_length"


__all__ = [
    "GamesCheckersMaxCaptureChainLengthTask",
    "GamesCheckersMoveCountPublicTask",
]
