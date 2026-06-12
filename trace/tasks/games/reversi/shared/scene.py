"""Games Reversi task for grounded move-count and flip-count queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults, required_group_defaults
from trace.tasks.shared.font_assets import get_font_family_record, sample_font_family
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_query_spec,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from .common import (
    BLACK,
    WHITE,
    Board,
    Coord,
    coord_to_cell_id,
    corner_coords,
    frontier_disc_coords,
    legal_moves_with_flips,
    player_name,
    simulate_random_state,
)
from trace.tasks.games.shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from .rendering import ReversiRenderParams, render_reversi_board_scene
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.style import SUPPORTED_REVERSI_STYLE_VARIANTS
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "reversi"
SCENE_NAMESPACE = "games.reversi"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "compact_board",
    "classic_board",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "legal_move_count",
    "corner_move_count",
    "flip_count_for_marked_move",
)
FRONTIER_QUERY_IDS: Tuple[str, ...] = (
    "black_frontier_disc_count",
    "white_frontier_disc_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Reversi move-count scenes."""

    legal_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    corner_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    flip_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    frontier_disc_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    canvas_width: int = 900
    canvas_height: int = 900
    panel_margin_px: int = 48
    player_badge_height_px: int = 52
    player_badge_width_px: int = 190
    header_gap_px: int = 18
    max_board_size_px: int = 720
    board_corner_radius_px: int = 24
    board_frame_width_px: int = 14
    cell_line_width_px: int = 3
    marked_square_outline_width_px: int = 6
    disc_inset_fraction: float = 0.14
    player_badge_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Reversi scene."""

    query_id: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    board_size: int
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SampledReversiScene:
    """One sampled Reversi scene plus query-specific witness metadata."""

    board: Board
    current_player: int
    legal_moves: Dict[Coord, Tuple[Coord, ...]]
    annotation_coords: Tuple[Coord, ...]
    annotation_entity_ids: Tuple[str, ...]
    marked_move: Coord | None
    marked_move_flips: Tuple[Coord, ...]
    construction_mode: str


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id="reversi", apply_prob=0.0)


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str] = SUPPORTED_QUERY_IDS,
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
    """Resolve one balanced named axis for the Reversi task."""

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


def _uses_uniform_query_cycle(
    params: Mapping[str, Any],
    probabilities: Mapping[str, float],
    *,
    supported_query_ids: Sequence[str] = SUPPORTED_QUERY_IDS,
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
    supported_query_ids: Sequence[str] = SUPPORTED_QUERY_IDS,
) -> Dict[str, Any]:
    """Use a per-query occurrence index for axes balanced under the query cycle."""

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


def _scene_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str] = SUPPORTED_QUERY_IDS,
) -> Dict[str, Any]:
    """Decorrelate balanced scene cycling from balanced query cycling."""

    if params.get("scene_variant") is not None:
        return dict(params)
    enabled = bool(
        params.get(
            "balanced_scene_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_scene_variant_sampling", True),
        )
    )
    if not enabled:
        return dict(params)
    raw_weights = params.get(
        "scene_variant_weights",
        group_default(_GEN_DEFAULTS, "scene_variant_weights", {key: 1.0 for key in SUPPORTED_SCENE_VARIANTS}),
    )
    if not isinstance(raw_weights, Mapping):
        return dict(params)
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_SCENE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_SCENE_VARIANTS):
        return dict(params)
    if max(positives) - min(positives) > 1e-9:
        return dict(params)
    return _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
        supported_query_ids=supported_query_ids,
    )


def _style_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str] = SUPPORTED_QUERY_IDS,
) -> Dict[str, Any]:
    """Decorrelate balanced style cycling from balanced query cycling."""

    if params.get("style_variant") is not None:
        return dict(params)
    enabled = bool(
        params.get(
            "balanced_style_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_style_variant_sampling", True),
        )
    )
    if not enabled:
        return dict(params)
    raw_weights = params.get(
        "style_variant_weights",
        group_default(_GEN_DEFAULTS, "style_variant_weights", {key: 1.0 for key in SUPPORTED_REVERSI_STYLE_VARIANTS}),
    )
    if not isinstance(raw_weights, Mapping):
        return dict(params)
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_REVERSI_STYLE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_REVERSI_STYLE_VARIANTS):
        return dict(params)
    if max(positives) - min(positives) > 1e-9:
        return dict(params)
    return _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
        supported_query_ids=supported_query_ids,
    )


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one query id."""

    return {
        "legal_move_count": "legal_move_count_support",
        "corner_move_count": "corner_move_count_support",
        "flip_count_for_marked_move": "flip_count_support",
        "black_frontier_disc_count": "frontier_disc_count_support",
        "white_frontier_disc_count": "frontier_disc_count_support",
    }[str(query_id)]


def _board_size_for_scene(scene_variant: str) -> int:
    """Return the visible board size for one Reversi scene family."""

    return 6 if str(scene_variant) == "compact_board" else 8


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str] = SUPPORTED_QUERY_IDS,
) -> _ResolvedAxes:
    """Resolve all semantic and visual sampling axes for one Reversi instance."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported_query_ids,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_scene_variant_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
            supported_query_ids=supported_query_ids,
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
            supported_query_ids=supported_query_ids,
        ),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_REVERSI_STYLE_VARIANTS,
    )
    target_support_key = _target_support_key(str(query_id))
    target_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
        supported_query_ids=supported_query_ids,
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
        board_size=int(_board_size_for_scene(str(scene_variant))),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> ReversiRenderParams:
    """Resolve Reversi rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.reversi.font_family",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.reversi.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.reversi.layout",
        ),
        unit_scale_meta,
    )
    return ReversiRenderParams(
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
            min_px=360,
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
            min_px=7,
        ),
        cell_line_width_px=scale_games_px(
            params.get("cell_line_width_px", group_default(_RENDER_DEFAULTS, "cell_line_width_px", _DEFAULTS.cell_line_width_px)),
            unit_scale,
            min_px=1,
        ),
        marked_square_outline_width_px=scale_games_px(
            params.get(
                "marked_square_outline_width_px",
                group_default(_RENDER_DEFAULTS, "marked_square_outline_width_px", _DEFAULTS.marked_square_outline_width_px),
            ),
            unit_scale,
            min_px=3,
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
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
        instance_seed=int(instance_seed),
    )


def _empty_board(board_size: int) -> List[List[int]]:
    """Return one mutable empty board."""

    return [[0 for _ in range(int(board_size))] for _ in range(int(board_size))]


def _freeze_board(board: Sequence[Sequence[int]]) -> Board:
    """Freeze one mutable board into the canonical tuple form."""

    return tuple(tuple(int(cell) for cell in row) for row in board)


def _set_cell(board: List[List[int]], coord: Coord, value: int) -> None:
    """Write one board cell in-place."""

    board[int(coord[0])][int(coord[1])] = int(value)


def _resolve_current_player(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve the current player for one scene."""

    explicit = params.get("current_player")
    if explicit is None:
        return int(BLACK if int(rng.randrange(2)) == 0 else WHITE)
    text = str(explicit).strip().lower()
    if text in {"black", "b", "1"}:
        return int(BLACK)
    if text in {"white", "w", "-1"}:
        return int(WHITE)
    raise ValueError(f"unsupported current_player: {explicit}")


def _construct_legal_move_board(*, rng, board_size: int, current_player: int, target_answer: int) -> _SampledReversiScene:
    """Search for one reachable board with an exact number of legal moves."""

    max_plies = max(int(board_size) + 2, (int(board_size) * int(board_size)) - 4)
    if int(target_answer) == 0:
        min_plies = max(int(board_size) + 6, int(0.65 * max_plies))
    elif int(target_answer) >= 5:
        min_plies = max(4, int(0.22 * max_plies))
        max_plies = max(min_plies + 4, int(0.62 * max_plies))
    else:
        min_plies = max(4, int(0.35 * max_plies))

    for _ in range(192):
        frozen_board = simulate_random_state(
            rng=rng,
            board_size=int(board_size),
            min_plies=int(min_plies),
            max_plies=int(max_plies),
        )
        legal_moves = legal_moves_with_flips(frozen_board, int(current_player))
        if int(len(legal_moves)) != int(target_answer):
            continue
        annotation_coords = tuple(sorted((int(row), int(col)) for row, col in legal_moves.keys()))
        return _SampledReversiScene(
            board=frozen_board,
            current_player=int(current_player),
            legal_moves=legal_moves,
            annotation_coords=annotation_coords,
            annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in annotation_coords),
            marked_move=None,
            marked_move_flips=tuple(),
            construction_mode="simulated_legal_count",
        )

    raise ValueError("failed to find a reachable board with the requested legal-move count")


def _construct_corner_move_board(*, rng, board_size: int, current_player: int, target_answer: int) -> _SampledReversiScene:
    """Construct one board with an exact number of legal corner moves."""

    board = _empty_board(int(board_size))
    opponent = int(WHITE if int(current_player) == int(BLACK) else BLACK)
    corners = list(corner_coords(int(board_size)))
    selected_corners = [] if int(target_answer) == 0 else list(rng.sample(corners, k=int(target_answer)))
    corner_pattern_specs = {
        (0, 0): ((0, 1), (0, 2)),
        (0, int(board_size) - 1): ((0, int(board_size) - 2), (0, int(board_size) - 3)),
        (int(board_size) - 1, 0): ((int(board_size) - 1, 1), (int(board_size) - 1, 2)),
        (
            int(board_size) - 1,
            int(board_size) - 1,
        ): ((int(board_size) - 1, int(board_size) - 2), (int(board_size) - 1, int(board_size) - 3)),
    }
    for corner in corners:
        if tuple(corner) in {tuple(item) for item in selected_corners}:
            adjacent_coord, terminal_coord = corner_pattern_specs[tuple(corner)]
            _set_cell(board, adjacent_coord, opponent)
            _set_cell(board, terminal_coord, current_player)
        else:
            _set_cell(board, tuple(corner), current_player if int(corner[0] + corner[1]) % 2 == 0 else opponent)
    frozen_board = _freeze_board(board)
    legal_moves = legal_moves_with_flips(frozen_board, int(current_player))
    annotation_coords = tuple(sorted(move for move in legal_moves if tuple(move) in set(corners)))
    if int(len(annotation_coords)) != int(target_answer):
        raise ValueError("constructed corner-move board did not match the target answer")
    return _SampledReversiScene(
        board=frozen_board,
        current_player=int(current_player),
        legal_moves=legal_moves,
        annotation_coords=annotation_coords,
        annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in annotation_coords),
        marked_move=None,
        marked_move_flips=tuple(),
        construction_mode="corner_patterns",
    )


def _construct_flip_count_board(*, rng, board_size: int, current_player: int, target_answer: int) -> _SampledReversiScene:
    """Construct a simple marked move that flips an exact number of discs."""

    board = _empty_board(int(board_size))
    opponent = int(WHITE if int(current_player) == int(BLACK) else BLACK)
    edge_specs = (
        ((0, 0), (0, 1), (1, 0)),
        ((0, int(board_size) - 1), (1, 0), (0, -1)),
        ((int(board_size) - 1, int(board_size) - 1), (0, -1), (-1, 0)),
        ((int(board_size) - 1, 0), (-1, 0), (0, 1)),
    )
    marked_move, primary_direction, secondary_direction = edge_specs[int(rng.randrange(len(edge_specs)))]

    if int(target_answer) <= int(board_size) - 2:
        line_specs = ((primary_direction, int(target_answer)),)
    else:
        # A 6x6 board cannot fit five or more flips in one line, so keep it to
        # two easy-to-scan edge lines rather than several short directions.
        line_specs = ((primary_direction, 3), (secondary_direction, int(target_answer) - 3))

    flipped_coords: List[Coord] = []
    for direction, length in line_specs:
        row_delta, col_delta = int(direction[0]), int(direction[1])
        for step in range(1, int(length) + 1):
            flipped_coord = (
                int(marked_move[0] + (step * row_delta)),
                int(marked_move[1] + (step * col_delta)),
            )
            _set_cell(board, flipped_coord, opponent)
            flipped_coords.append(flipped_coord)
        terminal_coord = (
            int(marked_move[0] + ((int(length) + 1) * row_delta)),
            int(marked_move[1] + ((int(length) + 1) * col_delta)),
        )
        _set_cell(board, terminal_coord, current_player)
    frozen_board = _freeze_board(board)
    legal_moves = legal_moves_with_flips(frozen_board, int(current_player))
    marked_flips = tuple(sorted(legal_moves.get(tuple(marked_move), ())))
    if len(marked_flips) != int(target_answer):
        raise ValueError("constructed flip-count board did not match the target answer")
    return _SampledReversiScene(
        board=frozen_board,
        current_player=int(current_player),
        legal_moves=legal_moves,
        annotation_coords=marked_flips,
        annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in marked_flips),
        marked_move=tuple(int(value) for value in marked_move),
        marked_move_flips=marked_flips,
        construction_mode="marked_flip",
    )


def _frontier_query_player(query_id: str) -> int:
    """Return the queried disc color for one frontier query id."""

    if str(query_id) == "black_frontier_disc_count":
        return int(BLACK)
    if str(query_id) == "white_frontier_disc_count":
        return int(WHITE)
    raise ValueError(f"unsupported frontier query id: {query_id}")


def _frontier_ply_windows(*, board_size: int, target_answer: int) -> Tuple[Tuple[int, int], ...]:
    """Return target-aware simulation windows for reachable frontier boards."""

    size = int(board_size)
    target = int(target_answer)
    max_plies = max(size + 4, (size * size) - 4)
    if target == 0:
        return ((max(size + 8, int(0.75 * max_plies)), max_plies),)
    if target <= 2:
        return (
            (4, max(size + 4, int(0.30 * max_plies))),
            (max(size + 6, int(0.70 * max_plies)), max_plies),
        )
    if target <= 5:
        return (
            (4, max(size + 8, int(0.42 * max_plies))),
            (max(6, int(0.32 * max_plies)), max(size + 12, int(0.58 * max_plies))),
        )
    return (
        (max(4, int(0.22 * max_plies)), max(size + 14, int(0.62 * max_plies))),
        (max(6, int(0.35 * max_plies)), max(size + 18, int(0.78 * max_plies))),
    )


def _construct_frontier_disc_board(*, rng, board_size: int, query_id: str, target_answer: int) -> _SampledReversiScene:
    """Search for a reachable board with an exact frontier-disc count."""

    query_player = _frontier_query_player(str(query_id))
    windows = _frontier_ply_windows(board_size=int(board_size), target_answer=int(target_answer))
    for attempt_index in range(420):
        min_plies, max_plies = windows[int(attempt_index) % len(windows)]
        frozen_board = simulate_random_state(
            rng=rng,
            board_size=int(board_size),
            min_plies=int(min_plies),
            max_plies=int(max_plies),
        )
        annotation_coords = frontier_disc_coords(frozen_board, int(query_player))
        if int(len(annotation_coords)) != int(target_answer):
            continue
        return _SampledReversiScene(
            board=frozen_board,
            current_player=int(query_player),
            legal_moves=legal_moves_with_flips(frozen_board, int(query_player)),
            annotation_coords=tuple(annotation_coords),
            annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in annotation_coords),
            marked_move=None,
            marked_move_flips=tuple(),
            construction_mode="simulated_frontier_disc_count",
        )
    raise ValueError("failed to find a reachable board with the requested frontier-disc count")


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SampledReversiScene:
    """Construct one Reversi scene consistent with the requested axes."""

    current_player = _resolve_current_player(rng, params=params)
    if str(axes.query_id) in FRONTIER_QUERY_IDS:
        return _construct_frontier_disc_board(
            rng=rng,
            board_size=int(axes.board_size),
            query_id=str(axes.query_id),
            target_answer=int(axes.target_answer),
        )
    if str(axes.query_id) == "legal_move_count":
        return _construct_legal_move_board(
            rng=rng,
            board_size=int(axes.board_size),
            current_player=int(current_player),
            target_answer=int(axes.target_answer),
        )
    if str(axes.query_id) == "corner_move_count":
        return _construct_corner_move_board(
            rng=rng,
            board_size=int(axes.board_size),
            current_player=int(current_player),
            target_answer=int(axes.target_answer),
        )
    return _construct_flip_count_board(
        rng=rng,
        board_size=int(axes.board_size),
        current_player=int(current_player),
        target_answer=int(axes.target_answer),
    )


def _build_prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for the active Reversi query id."""

    answer_value = 3 if str(query_id) in {"flip_count_for_marked_move", *FRONTIER_QUERY_IDS} else 2
    annotation_value = (
        [[144, 216], [216, 216], [288, 216]]
        if str(query_id) in {"flip_count_for_marked_move", *FRONTIER_QUERY_IDS}
        else [[112, 184, 176, 248], [184, 184, 248, 248]]
    )
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesReversiMoveCountTask:
    """Return one grounded counting query over a visible Reversi board."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    supported_query_ids: Tuple[str, ...] = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(
            int(instance_seed),
            params=params,
            supported_query_ids=tuple(self.supported_query_ids),
        )
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: _SampledReversiScene | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.reversi.panel_scene_style",
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
        rendered_scene = render_reversi_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            current_player=int(sampled_scene.current_player),
            params=render_params,
            marked_move=sampled_scene.marked_move,
            panel_style=panel_style,
        )
        if str(axes.query_id) == "flip_count_for_marked_move" or str(axes.query_id) in FRONTIER_QUERY_IDS:
            annotation_type = "point_set"
            annotation_value = [
                list(rendered_scene.render_map["disc_points_px"][str(entity_id)])
                for entity_id in sampled_scene.annotation_entity_ids
            ]
        else:
            annotation_type = "bbox_set"
            annotation_value = [
                list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
                for entity_id in sampled_scene.annotation_entity_ids
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
                "object_description_compact_board",
                "object_description_classic_board",
                "legal_move_rule_text",
                "corner_rule_text",
                "marked_move_rule_text",
                "flip_rule_text",
                "frontier_rule_text",
                "answer_hint_legal_move_count",
                "answer_hint_corner_move_count",
                "answer_hint_flip_count_for_marked_move",
                "answer_hint_black_frontier_disc_count",
                "answer_hint_white_frontier_disc_count",
                "annotation_hint_legal_move_count",
                "annotation_hint_corner_move_count",
                "annotation_hint_flip_count_for_marked_move",
                "annotation_hint_black_frontier_disc_count",
                "annotation_hint_white_frontier_disc_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_id=str(axes.query_id))
        current_player_name = player_name(int(sampled_scene.current_player))
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "current_player_name": str(current_player_name),
                "legal_move_rule_text": str(prompt_defaults["legal_move_rule_text"]),
                "corner_rule_text": str(prompt_defaults["corner_rule_text"]),
                "marked_move_rule_text": str(prompt_defaults["marked_move_rule_text"]),
                "flip_rule_text": str(prompt_defaults["flip_rule_text"]),
                "frontier_rule_text": str(prompt_defaults["frontier_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        annotation_gt = TypedValue(type=str(annotation_type), value=[list(item) for item in annotation_value])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }

        legal_move_specs = [
            {
                "coord": [int(coord[0]), int(coord[1])],
                "cell_id": str(coord_to_cell_id(coord)),
                "flip_count": int(len(flips)),
            }
            for coord, flips in sorted(sampled_scene.legal_moves.items())
        ]
        board_rows = [[int(cell) for cell in row] for row in sampled_scene.board]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_reversi_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(axes.board_size),
                    "current_player": str(current_player_name),
                    "target_answer": int(axes.target_answer),
                    "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
                    "marked_move_cell_id": None
                    if sampled_scene.marked_move is None
                    else str(coord_to_cell_id(sampled_scene.marked_move)),
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
                    "board_size": int(axes.board_size),
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
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "board_size": int(axes.board_size),
                "current_player": str(current_player_name),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "board_rows": board_rows,
                "construction_mode": str(sampled_scene.construction_mode),
                "legal_move_count": int(len(sampled_scene.legal_moves)),
                "frontier_disc_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.annotation_coords]
                if str(axes.query_id) in FRONTIER_QUERY_IDS
                else [],
                "legal_move_specs": legal_move_specs,
                "marked_move": None
                if sampled_scene.marked_move is None
                else [int(sampled_scene.marked_move[0]), int(sampled_scene.marked_move[1])],
                "marked_move_cell_id": None
                if sampled_scene.marked_move is None
                else str(coord_to_cell_id(sampled_scene.marked_move)),
                "marked_move_flip_coords": [
                    [int(coord[0]), int(coord[1])] for coord in sampled_scene.marked_move_flips
                ],
                "annotation_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.annotation_coords],
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            },
            "projected_annotation": {
                str(annotation_type): [list(item) for item in annotation_value],
            },
            "background": background_meta,
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
            task_versions=default_task_versions(),
            scene_id="reversi",
            query_id=str(axes.query_id),
        )
        return rewrite_public_query_output(
            output,
            query_id=str(axes.query_id),
            query_id_probabilities=axes.query_id_probabilities,
        )


@register_task
class GamesReversiLegalDestinationCountTask(GamesReversiMoveCountTask):
    """Count all legal destination squares or legal corner destinations."""

    task_id = "task_games__reversi__legal_destination_count"
    supported_query_ids = ("legal_move_count", "corner_move_count")


class GamesReversiFlipCountForMarkedMoveTask(FixedQueryVariantTaskMixin, GamesReversiMoveCountTask):
    """Count discs flipped by the marked Reversi move."""

    task_id = "task_games__reversi__marked_move_flip_count"
    fixed_query_id = "flip_count_for_marked_move"
    supported_query_ids = ("flip_count_for_marked_move",)


class GamesReversiFrontierDiscCountTask(GamesReversiMoveCountTask):
    """Count queried-color discs touching at least one empty square."""

    task_id = "task_games__reversi__frontier_disc_count"
    supported_query_ids = FRONTIER_QUERY_IDS


__all__ = [
    "GamesReversiFrontierDiscCountTask",
    "GamesReversiFlipCountForMarkedMoveTask",
    "GamesReversiLegalDestinationCountTask",
]
