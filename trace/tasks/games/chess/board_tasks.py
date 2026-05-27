"""Games Chess-board tasks for single-step movement and attack queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

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
from ..shared.chess_common import (
    BLACK,
    BOARD_SIZE,
    NON_KING_PIECE_KINDS,
    WHITE,
    Board,
    ChessPiece,
    Coord,
    attackers_to_square,
    capturable_opponent_coords,
    color_name,
    coord_to_cell_id,
    empty_board,
    freeze_board,
    in_bounds,
    king_escape_squares,
    occupied_coords,
    occupied_piece_count,
    opponent,
    piece_capture_targets,
    piece_move_destinations,
    piece_name,
    piece_to_entity_id,
    serialize_board,
)
from ..shared.chess_scene import ChessRenderParams, render_chess_board_scene
from ..shared.complexity import build_games_chess_board_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.style import SUPPORTED_CHESS_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_chess_board_base"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("sparse_board", "crowded_board")
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "marked_piece_move_count",
    "marked_piece_capture_count",
    "player_capture_piece_count",
    "check_attacker_count",
    "king_escape_square_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Chess-board scenes."""

    marked_piece_move_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
    marked_piece_capture_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    player_capture_piece_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    check_attacker_count_support: Tuple[int, ...] = (1, 2, 3, 4)
    king_escape_square_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    sparse_min_occupied_count: int = 6
    sparse_max_occupied_count: int = 10
    crowded_min_occupied_count: int = 11
    crowded_max_occupied_count: int = 16
    canvas_width: int = 980
    canvas_height: int = 920
    panel_margin_px: int = 48
    player_badge_height_px: int = 52
    player_badge_width_px: int = 270
    header_gap_px: int = 18
    max_board_size_px: int = 780
    board_corner_radius_px: int = 26
    board_frame_width_px: int = 10
    piece_inset_fraction: float = 0.12
    piece_font_size_px: int = 78
    marked_square_outline_width_px: int = 7
    player_badge_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Chess scene."""

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
    evidence_coords: Tuple[Coord, ...]
    evidence_entity_ids: Tuple[str, ...]
    evidence_kind: str
    marked_coord: Coord | None
    player_color: str
    marked_piece: ChessPiece | None
    destination_coords: Tuple[Coord, ...]
    capture_coords: Tuple[Coord, ...]
    attacker_coords: Tuple[Coord, ...]


@dataclass(frozen=True)
class _SampledChessScene:
    """One sampled Chess scene plus query-specific witness metadata."""

    board: Board
    evaluation: _SceneEvaluation
    occupied_count: int
    construction_mode: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "chess")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="chess")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="chess", apply_prob=0.0)


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one query id."""

    return {
        "marked_piece_move_count": "marked_piece_move_count_support",
        "marked_piece_capture_count": "marked_piece_capture_count_support",
        "player_capture_piece_count": "player_capture_piece_count_support",
        "check_attacker_count": "check_attacker_count_support",
        "king_escape_square_count": "king_escape_square_count_support",
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


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return cycle_params


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
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
    supported: Tuple[str, ...],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named Chess axis."""

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
    """Resolve all semantic and visual axes for one Chess instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_CHESS_STYLE_VARIANTS,
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


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> ChessRenderParams:
    """Resolve Chess rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.chess.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.chess.layout",
        ),
        unit_scale_meta,
    )
    return ChessRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        player_badge_height_px=int(params.get("player_badge_height_px", group_default(_RENDER_DEFAULTS, "player_badge_height_px", _DEFAULTS.player_badge_height_px))),
        player_badge_width_px=int(params.get("player_badge_width_px", group_default(_RENDER_DEFAULTS, "player_badge_width_px", _DEFAULTS.player_badge_width_px))),
        header_gap_px=int(params.get("header_gap_px", group_default(_RENDER_DEFAULTS, "header_gap_px", _DEFAULTS.header_gap_px))),
        max_board_size_px=scale_games_px(params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)), unit_scale, min_px=390),
        board_corner_radius_px=scale_games_px(params.get("board_corner_radius_px", group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px)), unit_scale, min_px=10),
        board_frame_width_px=scale_games_px(params.get("board_frame_width_px", group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px)), unit_scale, min_px=5),
        piece_inset_fraction=float(params.get("piece_inset_fraction", group_default(_RENDER_DEFAULTS, "piece_inset_fraction", _DEFAULTS.piece_inset_fraction))),
        piece_font_size_px=scale_games_px(params.get("piece_font_size_px", group_default(_RENDER_DEFAULTS, "piece_font_size_px", _DEFAULTS.piece_font_size_px)), unit_scale, min_px=36),
        marked_square_outline_width_px=scale_games_px(params.get("marked_square_outline_width_px", group_default(_RENDER_DEFAULTS, "marked_square_outline_width_px", _DEFAULTS.marked_square_outline_width_px)), unit_scale, min_px=3),
        player_badge_font_size_px=int(params.get("player_badge_font_size_px", group_default(_RENDER_DEFAULTS, "player_badge_font_size_px", _DEFAULTS.player_badge_font_size_px))),
        layout_jitter_meta=layout_jitter,
    )


def _resolve_player_color(rng, *, params: Mapping[str, Any]) -> str:
    """Resolve the prompt-facing player color for one scene."""

    explicit = params.get("player_color")
    if explicit is None:
        return WHITE if int(rng.randrange(2)) == 0 else BLACK
    text = str(explicit).strip().lower()
    if text in {"white", "w"}:
        return WHITE
    if text in {"black", "b"}:
        return BLACK
    raise ValueError(f"unsupported player_color: {explicit}")


def _piece_count_range(scene_variant: str) -> Tuple[int, int]:
    """Return target occupied-piece bounds for one scene variant."""

    if str(scene_variant) == "crowded_board":
        return int(_DEFAULTS.crowded_min_occupied_count), int(_DEFAULTS.crowded_max_occupied_count)
    return int(_DEFAULTS.sparse_min_occupied_count), int(_DEFAULTS.sparse_max_occupied_count)


def _valid_pawn_row(color: str, row: int) -> bool:
    """Return whether a pawn can be shown on this row without promotion ambiguity."""

    return 1 <= int(row) <= 6


def _coords_adjacent(a: Coord, b: Coord) -> bool:
    """Return whether two coordinates are king-adjacent."""

    return max(abs(int(a[0]) - int(b[0])), abs(int(a[1]) - int(b[1]))) <= 1


def _random_empty_coord(rng, mutable: list[list[ChessPiece | None]]) -> Coord:
    """Sample one currently empty board coordinate."""

    empties = [(row, col) for row in range(BOARD_SIZE) for col in range(BOARD_SIZE) if mutable[row][col] is None]
    if not empties:
        raise ValueError("no empty chess board cells remain")
    return tuple(rng.choice(empties))


def _sample_random_board(*, rng, scene_variant: str) -> Board:
    """Construct one random sparse standard-piece board."""

    minimum, maximum = _piece_count_range(str(scene_variant))
    desired_count = int(rng.randint(int(minimum), int(maximum)))
    mutable = [list(row) for row in empty_board()]
    white_king = (int(rng.randint(1, 6)), int(rng.randint(1, 6)))
    mutable[white_king[0]][white_king[1]] = ChessPiece(WHITE, "king")
    for _ in range(128):
        black_king = (int(rng.randint(1, 6)), int(rng.randint(1, 6)))
        if mutable[black_king[0]][black_king[1]] is None and not _coords_adjacent(white_king, black_king):
            mutable[black_king[0]][black_king[1]] = ChessPiece(BLACK, "king")
            break
    else:
        raise ValueError("failed to place separated kings")

    kinds = ("queen", "rook", "bishop", "knight", "pawn", "pawn", "pawn")
    attempts = 0
    while occupied_piece_count(mutable) < desired_count and attempts < 320:
        attempts += 1
        row, col = _random_empty_coord(rng, mutable)
        color = WHITE if int(rng.randrange(2)) == 0 else BLACK
        kind = str(rng.choice(kinds))
        if str(kind) == "pawn" and not _valid_pawn_row(color, int(row)):
            continue
        mutable[row][col] = ChessPiece(color, kind)
    if occupied_piece_count(mutable) < minimum:
        raise ValueError("failed to reach requested chess density")
    return freeze_board(mutable)


def _piece_entity_ids(board: Board, coords: Tuple[Coord, ...]) -> Tuple[str, ...]:
    """Return piece entity ids for occupied coordinates."""

    ids = []
    for coord in coords:
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None:
            raise ValueError("piece evidence coordinate is empty")
        ids.append(piece_to_entity_id(coord, piece))
    return tuple(ids)


def _evaluate_board(
    *,
    board: Board,
    query_id: str,
    player_color: str,
    marked_coord: Coord | None,
) -> _SceneEvaluation | None:
    """Evaluate one finalized board under one query semantics."""

    if str(query_id) == "marked_piece_move_count":
        if marked_coord is None:
            return None
        piece = board[int(marked_coord[0])][int(marked_coord[1])]
        if piece is None or str(piece.kind) == "king":
            return None
        destinations = tuple(sorted(piece_move_destinations(board, marked_coord)))
        return _SceneEvaluation(
            answer=int(len(destinations)),
            evidence_coords=destinations,
            evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in destinations),
            evidence_kind="cell",
            marked_coord=marked_coord,
            player_color=str(piece.color),
            marked_piece=piece,
            destination_coords=destinations,
            capture_coords=(),
            attacker_coords=(),
        )
    if str(query_id) == "marked_piece_capture_count":
        if marked_coord is None:
            return None
        piece = board[int(marked_coord[0])][int(marked_coord[1])]
        if piece is None or str(piece.kind) == "king":
            return None
        captures = tuple(sorted(piece_capture_targets(board, marked_coord)))
        return _SceneEvaluation(
            answer=int(len(captures)),
            evidence_coords=captures,
            evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in captures),
            evidence_kind="cell",
            marked_coord=marked_coord,
            player_color=str(piece.color),
            marked_piece=piece,
            destination_coords=captures,
            capture_coords=captures,
            attacker_coords=(),
        )
    if str(query_id) == "player_capture_piece_count":
        captures = tuple(capturable_opponent_coords(board, str(player_color)))
        return _SceneEvaluation(
            answer=int(len(captures)),
            evidence_coords=captures,
            evidence_entity_ids=_piece_entity_ids(board, captures),
            evidence_kind="piece",
            marked_coord=None,
            player_color=str(player_color),
            marked_piece=None,
            destination_coords=(),
            capture_coords=captures,
            attacker_coords=(),
        )
    if str(query_id) == "check_attacker_count":
        if marked_coord is None:
            return None
        king = board[int(marked_coord[0])][int(marked_coord[1])]
        if king is None or str(king.kind) != "king":
            return None
        attackers = attackers_to_square(board, marked_coord, opponent(str(king.color)))
        return _SceneEvaluation(
            answer=int(len(attackers)),
            evidence_coords=attackers,
            evidence_entity_ids=_piece_entity_ids(board, attackers),
            evidence_kind="piece",
            marked_coord=marked_coord,
            player_color=str(king.color),
            marked_piece=king,
            destination_coords=(),
            capture_coords=(),
            attacker_coords=attackers,
        )
    if str(query_id) == "king_escape_square_count":
        if marked_coord is None:
            return None
        king = board[int(marked_coord[0])][int(marked_coord[1])]
        if king is None or str(king.kind) != "king":
            return None
        escapes = tuple(king_escape_squares(board, marked_coord))
        return _SceneEvaluation(
            answer=int(len(escapes)),
            evidence_coords=escapes,
            evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in escapes),
            evidence_kind="cell",
            marked_coord=marked_coord,
            player_color=str(king.color),
            marked_piece=king,
            destination_coords=escapes,
            capture_coords=(),
            attacker_coords=(),
        )
    raise ValueError(f"unsupported Chess query_id: {query_id}")


def _candidate_marked_coords(board: Board, *, query_id: str, target_answer: int) -> Tuple[Coord, ...]:
    """Return non-king pieces whose active metric matches the target answer."""

    coords = []
    for coord in occupied_coords(board):
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None or str(piece.kind) == "king":
            continue
        evaluation = _evaluate_board(
            board=board,
            query_id=str(query_id),
            player_color=str(piece.color),
            marked_coord=coord,
        )
        if evaluation is not None and int(evaluation.answer) == int(target_answer):
            coords.append(coord)
    return tuple(coords)


def _line_clear_between(a: Coord, b: Coord, coord: Coord) -> bool:
    """Return whether coord lies strictly between a and b on a row, file, or diagonal."""

    ar, ac = int(a[0]), int(a[1])
    br, bc = int(b[0]), int(b[1])
    cr, cc = int(coord[0]), int(coord[1])
    dr = 0 if br == ar else (1 if br > ar else -1)
    dc = 0 if bc == ac else (1 if bc > ac else -1)
    if not (ar == br or ac == bc or abs(ar - br) == abs(ac - bc)):
        return False
    r, c = ar + dr, ac + dc
    while (r, c) != (br, bc):
        if (r, c) == (cr, cc):
            return True
        r += dr
        c += dc
    return False


def _attacker_slots_for_king(king_coord: Coord, attacker_color: str) -> Tuple[Tuple[Coord, str], ...]:
    """Return candidate attacker placements around one marked king."""

    row, col = int(king_coord[0]), int(king_coord[1])
    slots: list[Tuple[Coord, str]] = []
    for dr, dc, kind in (
        (-2, -1, "knight"),
        (-2, 1, "knight"),
        (-1, -2, "knight"),
        (-1, 2, "knight"),
        (1, -2, "knight"),
        (1, 2, "knight"),
        (2, -1, "knight"),
        (2, 1, "knight"),
    ):
        coord = (row + dr, col + dc)
        if in_bounds(*coord):
            slots.append((coord, kind))
    pawn_row = row - 1 if str(attacker_color) == BLACK else row + 1
    for dc in (-1, 1):
        coord = (pawn_row, col + dc)
        if in_bounds(*coord) and _valid_pawn_row(attacker_color, coord[0]):
            slots.append((coord, "pawn"))
    for dr, dc, kind in (
        (-1, 0, "rook"),
        (1, 0, "rook"),
        (0, -1, "rook"),
        (0, 1, "rook"),
        (-1, -1, "bishop"),
        (-1, 1, "bishop"),
        (1, -1, "bishop"),
        (1, 1, "bishop"),
    ):
        for distance in (2, 3, 4):
            coord = (row + (dr * distance), col + (dc * distance))
            if in_bounds(*coord):
                slots.append((coord, kind))
                break
    return tuple(slots)


def _try_add_fillers_preserving(
    *,
    rng,
    board: Board,
    axes: _ResolvedAxes,
    evaluation: _SceneEvaluation,
    params: Mapping[str, Any],
) -> Tuple[Board, _SceneEvaluation]:
    """Add random filler pieces while preserving the active answer."""

    del params
    minimum, maximum = _piece_count_range(str(axes.scene_variant))
    desired_count = int(rng.randint(max(int(minimum), occupied_piece_count(board)), int(maximum)))
    mutable = [list(row) for row in board]
    attempts = 0
    while occupied_piece_count(mutable) < desired_count and attempts < 520:
        attempts += 1
        row, col = _random_empty_coord(rng, mutable)
        color = WHITE if int(rng.randrange(2)) == 0 else BLACK
        kind = str(rng.choice(("queen", "rook", "bishop", "knight", "pawn", "pawn")))
        if str(kind) == "pawn" and not _valid_pawn_row(color, int(row)):
            continue
        mutable[row][col] = ChessPiece(color, kind)
        frozen = freeze_board(mutable)
        if evaluation.marked_coord is not None:
            marked_piece = frozen[int(evaluation.marked_coord[0])][int(evaluation.marked_coord[1])]
            if marked_piece != evaluation.marked_piece:
                mutable[row][col] = None
                continue
        candidate = _evaluate_board(
            board=frozen,
            query_id=str(axes.query_id),
            player_color=str(evaluation.player_color),
            marked_coord=evaluation.marked_coord,
        )
        if candidate is None or int(candidate.answer) != int(axes.target_answer):
            mutable[row][col] = None
            continue
        evaluation = candidate
    frozen = freeze_board(mutable)
    if occupied_piece_count(frozen) < int(minimum):
        raise ValueError("failed to reach requested Chess density while preserving answer")
    return frozen, evaluation


def _sample_check_attacker_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a board with a marked king attacked by the requested count."""

    mutable = [list(row) for row in empty_board()]
    king_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
    attacker_color = opponent(king_color)
    king_coord = (int(rng.randint(2, 5)), int(rng.randint(2, 5)))
    mutable[king_coord[0]][king_coord[1]] = ChessPiece(king_color, "king")
    slots = list(_attacker_slots_for_king(king_coord, attacker_color))
    rng.shuffle(slots)
    selected: list[Tuple[Coord, str]] = []
    for coord, kind in slots:
        if mutable[int(coord[0])][int(coord[1])] is not None:
            continue
        if any(coord == other for other, _kind in selected):
            continue
        if any(_line_clear_between(king_coord, other, coord) or _line_clear_between(king_coord, coord, other) for other, _kind in selected):
            continue
        selected.append((coord, kind))
        if len(selected) == int(axes.target_answer):
            break
    if len(selected) != int(axes.target_answer):
        raise ValueError("failed to choose requested check attackers")
    for coord, kind in selected:
        mutable[int(coord[0])][int(coord[1])] = ChessPiece(attacker_color, kind)
    for _ in range(128):
        other_king = (int(rng.randint(0, 7)), int(rng.randint(0, 7)))
        if mutable[other_king[0]][other_king[1]] is None and not _coords_adjacent(king_coord, other_king):
            mutable[other_king[0]][other_king[1]] = ChessPiece(attacker_color, "king")
            break
    else:
        raise ValueError("failed to place opposite king")
    board = freeze_board(mutable)
    evaluation = _evaluate_board(
        board=board,
        query_id=str(axes.query_id),
        player_color=king_color,
        marked_coord=king_coord,
    )
    if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
        raise ValueError("constructed check-attacker board does not match requested answer")
    board, evaluation = _try_add_fillers_preserving(rng=rng, board=board, axes=axes, evaluation=evaluation, params={})
    return _SampledChessScene(
        board=board,
        evaluation=evaluation,
        occupied_count=int(occupied_piece_count(board)),
        construction_mode="direct_king_attackers",
    )


def _sample_king_escape_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a board with a marked king and the requested safe one-step escapes."""

    mutable = [list(row) for row in empty_board()]
    king_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
    king_coord = (int(rng.randint(2, 5)), int(rng.randint(2, 5)))
    mutable[king_coord[0]][king_coord[1]] = ChessPiece(king_color, "king")

    adjacent = [
        (int(king_coord[0] + dr), int(king_coord[1] + dc))
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
        if not (int(dr) == 0 and int(dc) == 0)
    ]
    rng.shuffle(adjacent)
    safe_coords = set(adjacent[: int(axes.target_answer)])
    blocker_coords = [coord for coord in adjacent if coord not in safe_coords]
    for coord in blocker_coords:
        kind = str(rng.choice(NON_KING_PIECE_KINDS))
        if str(kind) == "pawn" and not _valid_pawn_row(king_color, int(coord[0])):
            kind = "knight"
        mutable[int(coord[0])][int(coord[1])] = ChessPiece(king_color, kind)

    opponent_color = opponent(king_color)
    possible_opponent_king_coords = [
        (row, col)
        for row in range(BOARD_SIZE)
        for col in range(BOARD_SIZE)
        if mutable[row][col] is None
        and not _coords_adjacent((row, col), king_coord)
        and all(not _coords_adjacent((row, col), coord) for coord in safe_coords)
    ]
    if not possible_opponent_king_coords:
        raise ValueError("failed to place non-interfering opposite king")
    other_king = tuple(rng.choice(possible_opponent_king_coords))
    mutable[int(other_king[0])][int(other_king[1])] = ChessPiece(opponent_color, "king")

    board = freeze_board(mutable)
    evaluation = _evaluate_board(
        board=board,
        query_id=str(axes.query_id),
        player_color=king_color,
        marked_coord=king_coord,
    )
    if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
        raise ValueError("constructed king-escape board does not match requested answer")
    board, evaluation = _try_add_fillers_preserving(rng=rng, board=board, axes=axes, evaluation=evaluation, params={})
    return _SampledChessScene(
        board=board,
        evaluation=evaluation,
        occupied_count=int(occupied_piece_count(board)),
        construction_mode="direct_king_escape_squares",
    )


def _allocate_rook_free_squares(*, rng, target_answer: int, capacities: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """Allocate an exact rook move count across four rays."""

    remaining = int(target_answer)
    allocations = [0, 0, 0, 0]
    order = list(range(4))
    rng.shuffle(order)
    for position, ray_index in enumerate(order):
        remaining_capacity = sum(int(capacities[idx]) for idx in order[position + 1 :])
        lower = max(0, int(remaining) - int(remaining_capacity))
        upper = min(int(capacities[ray_index]), int(remaining))
        value = int(rng.randint(int(lower), int(upper)))
        allocations[int(ray_index)] = int(value)
        remaining -= int(value)
    if int(remaining) != 0:
        raise ValueError("failed to allocate requested rook move count")
    return tuple(int(value) for value in allocations)


def _sample_marked_piece_move_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a marked-rook board with the requested destination count."""

    directions: Tuple[Coord, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
    for _ in range(96):
        mutable = [list(row) for row in empty_board()]
        marked_coord = tuple(rng.choice(((3, 3), (3, 4), (4, 3), (4, 4))))
        piece_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
        mutable[int(marked_coord[0])][int(marked_coord[1])] = ChessPiece(piece_color, "rook")
        capacities = tuple(
            sum(
                1
                for distance in range(1, BOARD_SIZE)
                if in_bounds(
                    int(marked_coord[0]) + int(dr) * int(distance),
                    int(marked_coord[1]) + int(dc) * int(distance),
                )
            )
            for dr, dc in directions
        )
        if int(axes.target_answer) > sum(int(value) for value in capacities):
            continue
        allocations = _allocate_rook_free_squares(
            rng=rng,
            target_answer=int(axes.target_answer),
            capacities=capacities,
        )
        for (dr, dc), free_count, capacity in zip(directions, allocations, capacities):
            if int(free_count) >= int(capacity):
                continue
            blocker_distance = int(free_count) + 1
            blocker_coord = (
                int(marked_coord[0]) + int(dr) * int(blocker_distance),
                int(marked_coord[1]) + int(dc) * int(blocker_distance),
            )
            mutable[int(blocker_coord[0])][int(blocker_coord[1])] = ChessPiece(piece_color, "knight")

        placed_kings: list[Coord] = []
        for color in (piece_color, opponent(piece_color)):
            for _attempt in range(128):
                coord = _random_empty_coord(rng, mutable)
                if any(_coords_adjacent(coord, other) for other in placed_kings):
                    continue
                mutable[int(coord[0])][int(coord[1])] = ChessPiece(color, "king")
                placed_kings.append(coord)
                break
            else:
                raise ValueError("failed to place kings for marked-rook construction")

        board = freeze_board(mutable)
        evaluation = _evaluate_board(
            board=board,
            query_id=str(axes.query_id),
            player_color=str(piece_color),
            marked_coord=marked_coord,
        )
        if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
            continue
        board, evaluation = _try_add_fillers_preserving(rng=rng, board=board, axes=axes, evaluation=evaluation, params={})
        return _SampledChessScene(
            board=board,
            evaluation=evaluation,
            occupied_count=int(occupied_piece_count(board)),
            construction_mode="direct_marked_rook_moves",
        )
    raise ValueError("failed to construct requested marked-piece move count")


def _sample_player_capture_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a board with an exact side-wide capture count."""

    directions: Tuple[Coord, ...] = (
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
    )
    queen_coord: Coord = (3, 3)
    ray_targets = [
        (
            int(queen_coord[0]) + int(dr),
            int(queen_coord[1]) + int(dc),
        )
        for dr, dc in directions
        if in_bounds(int(queen_coord[0]) + int(dr), int(queen_coord[1]) + int(dc))
    ]
    if int(axes.target_answer) > len(ray_targets):
        raise ValueError("target capture count exceeds queen-ray construction support")

    for _ in range(96):
        mutable = [list(row) for row in empty_board()]
        player_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
        opposing_color = opponent(player_color)
        mutable[int(queen_coord[0])][int(queen_coord[1])] = ChessPiece(player_color, "queen")
        selected_targets = list(ray_targets)
        rng.shuffle(selected_targets)
        selected_targets = selected_targets[: int(axes.target_answer)]
        for coord in selected_targets:
            kind = str(rng.choice(("rook", "bishop", "knight", "pawn")))
            if str(kind) == "pawn" and not _valid_pawn_row(opposing_color, int(coord[0])):
                kind = "knight"
            mutable[int(coord[0])][int(coord[1])] = ChessPiece(opposing_color, kind)

        placed_kings: list[Coord] = []
        for color in (player_color, opposing_color):
            for _attempt in range(160):
                coord = _random_empty_coord(rng, mutable)
                if any(_coords_adjacent(coord, other) for other in placed_kings):
                    continue
                mutable[int(coord[0])][int(coord[1])] = ChessPiece(color, "king")
                board = freeze_board(mutable)
                evaluation = _evaluate_board(
                    board=board,
                    query_id=str(axes.query_id),
                    player_color=str(player_color),
                    marked_coord=None,
                )
                if evaluation is None or int(evaluation.answer) > int(axes.target_answer):
                    mutable[int(coord[0])][int(coord[1])] = None
                    continue
                placed_kings.append(coord)
                break
            else:
                raise ValueError("failed to place kings for player-capture construction")

        board = freeze_board(mutable)
        evaluation = _evaluate_board(
            board=board,
            query_id=str(axes.query_id),
            player_color=str(player_color),
            marked_coord=None,
        )
        if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
            continue
        board, evaluation = _try_add_fillers_preserving(rng=rng, board=board, axes=axes, evaluation=evaluation, params={})
        return _SampledChessScene(
            board=board,
            evaluation=evaluation,
            occupied_count=int(occupied_piece_count(board)),
            construction_mode="direct_player_capture_count",
        )
    raise ValueError("failed to construct requested side-wide capture count")


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SampledChessScene:
    """Construct one Chess scene consistent with the requested axes."""

    if str(axes.query_id) == "check_attacker_count":
        return _sample_check_attacker_scene(rng=rng, axes=axes)
    if str(axes.query_id) == "king_escape_square_count":
        return _sample_king_escape_scene(rng=rng, axes=axes)

    search_budget = 320 if str(axes.query_id) == "marked_piece_move_count" else 180
    for _ in range(int(search_budget)):
        board = _sample_random_board(rng=rng, scene_variant=str(axes.scene_variant))
        player_color = _resolve_player_color(rng, params=params)
        if str(axes.query_id) in {"marked_piece_move_count", "marked_piece_capture_count"}:
            candidates = _candidate_marked_coords(
                board,
                query_id=str(axes.query_id),
                target_answer=int(axes.target_answer),
            )
            candidates = tuple(
                coord
                for coord in candidates
                if board[int(coord[0])][int(coord[1])] is not None
                and str(board[int(coord[0])][int(coord[1])].color) == str(player_color)
            ) or candidates
            if not candidates:
                continue
            marked_coord = tuple(rng.choice(candidates))
            evaluation = _evaluate_board(
                board=board,
                query_id=str(axes.query_id),
                player_color=str(board[int(marked_coord[0])][int(marked_coord[1])].color),
                marked_coord=marked_coord,
            )
        else:
            evaluation = _evaluate_board(
                board=board,
                query_id=str(axes.query_id),
                player_color=str(player_color),
                marked_coord=None,
            )
        if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
            continue
        return _SampledChessScene(
            board=board,
            evaluation=evaluation,
            occupied_count=int(occupied_piece_count(board)),
            construction_mode="random_board_search",
        )
    if str(axes.query_id) == "marked_piece_move_count":
        return _sample_marked_piece_move_scene(rng=rng, axes=axes)
    if str(axes.query_id) == "player_capture_piece_count":
        return _sample_player_capture_scene(rng=rng, axes=axes)
    raise ValueError("failed to sample requested Chess answer")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Chess JSON output."""

    answer_value = 2 if str(query_id) != "marked_piece_move_count" else 4
    evidence_value = [[140, 220, 210, 290], [210, 220, 280, 290]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _badge_text(evaluation: _SceneEvaluation, query_id: str) -> str:
    """Return compact text displayed above the board."""

    if evaluation.marked_piece is not None:
        return f"Marked {piece_name(evaluation.marked_piece)}"
    if str(query_id) == "player_capture_piece_count":
        return f"{color_name(evaluation.player_color)} to inspect"
    return f"Marked {color_name(evaluation.player_color)} king"


class GamesChessBoardTask:
    """Return one grounded query over a visible Chess board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "chess"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: _SampledChessScene | None = None
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
        rendered_scene = render_chess_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            badge_text=_badge_text(sampled_scene.evaluation, str(axes.query_id)),
            marked_coord=sampled_scene.evaluation.marked_coord,
            params=render_params,
        )
        if sampled_scene.evaluation.evidence_kind == "cell":
            evidence_bboxes = [
                list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
                for entity_id in sampled_scene.evaluation.evidence_entity_ids
            ]
        else:
            evidence_bboxes = [
                list(rendered_scene.render_map["piece_bboxes_px"][str(entity_id)])
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
                "object_description_sparse_board",
                "object_description_crowded_board",
                "standard_rule_text",
                "marked_piece_rule_text",
                "player_rule_text",
                "check_rule_text",
                "king_escape_rule_text",
                "answer_hint_marked_piece_move_count",
                "answer_hint_marked_piece_capture_count",
                "answer_hint_player_capture_piece_count",
                "answer_hint_check_attacker_count",
                "answer_hint_king_escape_square_count",
                "evidence_hint_marked_piece_move_count",
                "evidence_hint_marked_piece_capture_count",
                "evidence_hint_player_capture_piece_count",
                "evidence_hint_check_attacker_count",
                "evidence_hint_king_escape_square_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        evaluation = sampled_scene.evaluation
        marked_piece_text = piece_name(evaluation.marked_piece) if evaluation.marked_piece is not None else ""
        player_color_name = color_name(evaluation.player_color)
        opponent_color_name = color_name(opponent(evaluation.player_color))
        hint_slots = {
            "player_color_name": str(player_color_name),
            "opponent_color_name": str(opponent_color_name),
        }
        answer_hint = str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]).format(**hint_slots)
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]).format(**hint_slots)
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
                "answer_hint": str(answer_hint),
                "evidence_hint": str(evidence_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "standard_rule_text": str(prompt_defaults["standard_rule_text"]),
                "marked_piece_rule_text": str(prompt_defaults["marked_piece_rule_text"]),
                "player_rule_text": str(prompt_defaults["player_rule_text"]),
                "check_rule_text": str(prompt_defaults["check_rule_text"]),
                "king_escape_rule_text": str(prompt_defaults["king_escape_rule_text"]),
                "player_color_name": str(player_color_name),
                "opponent_color_name": str(opponent_color_name),
                "marked_piece_text": str(marked_piece_text),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(evaluation.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_chess_board_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            occupied_count=int(sampled_scene.occupied_count),
            target_answer=int(evaluation.answer),
            evidence_count=len(evaluation.evidence_entity_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_chess_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(BOARD_SIZE),
                    "player_color": str(evaluation.player_color),
                    "target_answer": int(evaluation.answer),
                    "marked_cell_id": None if evaluation.marked_coord is None else coord_to_cell_id(evaluation.marked_coord),
                    "evidence_entity_ids": [str(entity_id) for entity_id in evaluation.evidence_entity_ids],
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
                    "target_answer": int(evaluation.answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "player_color": str(evaluation.player_color),
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
                "target_answer": int(evaluation.answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "board_size": int(BOARD_SIZE),
                "board_rows": serialize_board(sampled_scene.board),
                "construction_mode": str(sampled_scene.construction_mode),
                "occupied_count": int(sampled_scene.occupied_count),
                "player_color": str(evaluation.player_color),
                "marked_coord": None if evaluation.marked_coord is None else [int(evaluation.marked_coord[0]), int(evaluation.marked_coord[1])],
                "marked_piece": None if evaluation.marked_piece is None else {"color": evaluation.marked_piece.color, "kind": evaluation.marked_piece.kind},
                "destination_coords": [[int(row), int(col)] for row, col in evaluation.destination_coords],
                "capture_coords": [[int(row), int(col)] for row, col in evaluation.capture_coords],
                "attacker_coords": [[int(row), int(col)] for row, col in evaluation.attacker_coords],
                "evidence_kind": str(evaluation.evidence_kind),
                "evidence_coords": [[int(row), int(col)] for row, col in evaluation.evidence_coords],
                "evidence_entity_ids": [str(entity_id) for entity_id in evaluation.evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in evaluation.evidence_entity_ids],
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
            scene_id="chess",
            query_id=str(axes.query_id),
        )


@register_task
class GamesChessMarkedPieceDestinationCountTask(QuerySubsetTaskMixin, GamesChessBoardTask):
    """Count marked-piece destination squares matching a sampled move condition."""

    task_id = "task_games__chess__marked_piece_destination_count"
    supported_query_ids = (
        "marked_piece_move_count",
        "marked_piece_capture_count",
    )


@register_task
class GamesChessPlayerCapturePieceCountTask(FixedQueryVariantTaskMixin, GamesChessBoardTask):
    """Count opponent pieces capturable by the requested side."""

    task_id = "task_games__chess__player_capture_piece_count"
    fixed_query_id = "player_capture_piece_count"


@register_task
class GamesChessCheckAttackerCountTask(FixedQueryVariantTaskMixin, GamesChessBoardTask):
    """Count opponent pieces attacking the marked king."""

    task_id = "task_games__chess__check_attacker_count"
    fixed_query_id = "check_attacker_count"


@register_task
class GamesChessKingEscapeSquareCountTask(FixedQueryVariantTaskMixin, GamesChessBoardTask):
    """Count safe one-step escape squares for the marked king."""

    task_id = "task_games__chess__king_escape_square_count"
    fixed_query_id = "king_escape_square_count"


__all__ = [
    "GamesChessBoardTask",
    "GamesChessCheckAttackerCountTask",
    "GamesChessKingEscapeSquareCountTask",
    "GamesChessMarkedPieceDestinationCountTask",
    "GamesChessPlayerCapturePieceCountTask",
]
