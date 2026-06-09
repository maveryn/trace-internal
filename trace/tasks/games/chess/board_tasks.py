"""Games Chess-board tasks for single-step movement and attack queries."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
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
from ..shared.chess_common import (
    BLACK,
    BOARD_SIZE,
    PIECE_KINDS,
    WHITE,
    Board,
    ChessPiece,
    Coord,
    apply_chess_move,
    attackers_to_square,
    capturable_opponent_coords,
    color_name,
    coord_to_cell_id,
    coord_to_square_name,
    coords_adjacent,
    empty_board,
    find_king,
    freeze_board,
    in_bounds,
    is_king_in_check,
    king_escape_squares,
    legal_chess_moves_for_color,
    move_checkmates,
    occupied_coords,
    occupied_piece_count,
    opponent,
    piece_attacks_square,
    piece_capture_targets,
    piece_move_destinations,
    piece_name,
    piece_to_entity_id,
    sample_material_piece,
    serialize_board,
    standard_pawn_row_valid,
    validate_square_chess_material,
)
from ..shared.chess_scene import ChessRenderParams, render_chess_board_scene
from ..shared.complexity import build_games_chess_board_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_CHESS_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_chess_board_base"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("sparse_board", "crowded_board")
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "marked_piece_move_count",
    "marked_piece_capture_count",
    "player_capture_piece_count",
    "king_square_attacker_count",
    "white_piece_attacks_target_square_count",
    "black_piece_attacks_target_square_count",
    "rook_line_blocker_count",
    "bishop_diagonal_blocker_count",
    "queen_line_blocker_count",
    "king_escape_square_count",
    "piece_kind_count",
    "colored_piece_kind_count",
)

PIECE_COUNT_QUERY_IDS: Tuple[str, ...] = ("piece_kind_count", "colored_piece_kind_count")
TARGET_SQUARE_ATTACKER_QUERY_IDS: Tuple[str, ...] = (
    "king_square_attacker_count",
    "white_piece_attacks_target_square_count",
    "black_piece_attacks_target_square_count",
)
MARKED_PIECE_BLOCKER_QUERY_IDS: Tuple[str, ...] = (
    "rook_line_blocker_count",
    "bishop_diagonal_blocker_count",
    "queen_line_blocker_count",
)
PIECE_COUNT_KIND_SUPPORT: Tuple[str, ...] = tuple(str(kind) for kind in PIECE_KINDS)
PIECE_COUNT_COLOR_SUPPORT: Tuple[str, ...] = (WHITE, BLACK)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Chess-board scenes."""

    marked_piece_move_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
    marked_piece_capture_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    player_capture_piece_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    target_square_attacker_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    marked_piece_blocker_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    king_escape_square_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    piece_type_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    piece_count_distractor_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
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
    coordinate_label_font_size_px: int = 18
    option_panel_gap_px: int = 18
    option_panel_height_px: int = 0
    option_panel_font_size_px: int = 20
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 560
    canvas_min_height_px: int = 560
    canvas_side_padding_px: int = 132
    canvas_vertical_padding_px: int = 92


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
    target_piece_kind: str
    target_piece_color: str
    target_piece_kind_probabilities: Dict[str, float]
    target_piece_color_probabilities: Dict[str, float]
    distractor_count: int
    distractor_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SceneEvaluation:
    """Query-specific evaluation payload derived from one finalized board."""

    answer: int
    annotation_coords: Tuple[Coord, ...]
    annotation_entity_ids: Tuple[str, ...]
    annotation_kind: str
    marked_coord: Coord | None
    player_color: str
    marked_piece: ChessPiece | None
    destination_coords: Tuple[Coord, ...]
    capture_coords: Tuple[Coord, ...]
    attacker_coords: Tuple[Coord, ...]
    target_piece_kind: str = ""
    target_piece_color: str = ""
    target_coord: Coord | None = None
    blocker_coords: Tuple[Coord, ...] = ()


@dataclass(frozen=True)
class _SampledChessScene:
    """One sampled Chess scene plus query-specific witness metadata."""

    board: Board
    evaluation: _SceneEvaluation
    occupied_count: int
    construction_mode: str


@dataclass(frozen=True)
class _CheckmateMoveOption:
    """One prompt-facing checkmate move option."""

    label: str
    source: Coord
    destination: Coord
    piece: ChessPiece

    @property
    def text(self) -> str:
        """Return the encoded move text shown in the image option panel."""

        return (
            f"{self.label}: {str(self.piece.kind).capitalize()} "
            f"{coord_to_square_name(self.source)} -> {coord_to_square_name(self.destination)}"
        )


@dataclass(frozen=True)
class _CheckmateSample:
    """One sampled mate-in-one chess position with candidate move options."""

    board: Board
    player_color: str
    defender_color: str
    correct_option: _CheckmateMoveOption
    options: Tuple[_CheckmateMoveOption, ...]
    defender_king_coord: Coord
    occupied_count: int
    scene_variant: str
    style_variant: str
    construction_mode: str
    option_count: int
    option_label_support: Tuple[str, ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "chess")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="chess", apply_prob=0.0)
CHECKMATE_TASK_ID = "task_games__chess__checkmate_move_label"
CHECKMATE_QUERY_ID = "checkmate_move_label"
CHECKMATE_OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one query id."""

    return {
        "marked_piece_move_count": "marked_piece_move_count_support",
        "marked_piece_capture_count": "marked_piece_capture_count_support",
        "player_capture_piece_count": "player_capture_piece_count_support",
        "king_square_attacker_count": "target_square_attacker_count_support",
        "white_piece_attacks_target_square_count": "target_square_attacker_count_support",
        "black_piece_attacks_target_square_count": "target_square_attacker_count_support",
        "rook_line_blocker_count": "marked_piece_blocker_count_support",
        "bishop_diagonal_blocker_count": "marked_piece_blocker_count_support",
        "queen_line_blocker_count": "marked_piece_blocker_count_support",
        "king_escape_square_count": "king_escape_square_count_support",
        "piece_kind_count": "piece_type_count_support",
        "colored_piece_kind_count": "piece_type_count_support",
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
    target_piece_kind, target_piece_kind_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="target_piece_kind",
        explicit_key="target_piece_kind",
        weights_key="target_piece_kind_weights",
        balance_flag_key="balanced_target_piece_kind_sampling",
        supported=PIECE_COUNT_KIND_SUPPORT,
    )
    target_piece_color, target_piece_color_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="target_piece_color",
        explicit_key="target_piece_color",
        weights_key="target_piece_color_weights",
        balance_flag_key="balanced_target_piece_color_sampling",
        supported=PIECE_COUNT_COLOR_SUPPORT,
    )
    distractor_count, distractor_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="piece_count_distractor_count_support",
        explicit_key="piece_count_distractor_count",
        fallback_support=_DEFAULTS.piece_count_distractor_count_support,
        namespace=f"{TASK_ID}.piece_count_distractor_count.{str(query_id)}",
        balanced_flag_key="balanced_piece_count_distractor_count_sampling",
        namespace_support_permutation=True,
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
        target_piece_kind=str(target_piece_kind),
        target_piece_color=str(target_piece_color),
        target_piece_kind_probabilities=dict(target_piece_kind_probabilities),
        target_piece_color_probabilities=dict(target_piece_color_probabilities),
        distractor_count=int(distractor_count),
        distractor_count_probabilities=dict(distractor_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> ChessRenderParams:
    """Resolve Chess rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.chess.text_font",
        params=params,
    )
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
    max_board_size_px = scale_games_px(
        params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)),
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
                        float(max_board_size_px)
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
                        float(max_board_size_px)
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
    return ChessRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        player_badge_height_px=int(player_badge_height_px),
        player_badge_width_px=int(player_badge_width_px),
        header_gap_px=int(header_gap_px),
        max_board_size_px=int(max_board_size_px),
        board_corner_radius_px=scale_games_px(params.get("board_corner_radius_px", group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px)), unit_scale, min_px=10),
        board_frame_width_px=scale_games_px(params.get("board_frame_width_px", group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px)), unit_scale, min_px=5),
        piece_inset_fraction=float(params.get("piece_inset_fraction", group_default(_RENDER_DEFAULTS, "piece_inset_fraction", _DEFAULTS.piece_inset_fraction))),
        piece_font_size_px=scale_games_px(params.get("piece_font_size_px", group_default(_RENDER_DEFAULTS, "piece_font_size_px", _DEFAULTS.piece_font_size_px)), unit_scale, min_px=36),
        marked_square_outline_width_px=scale_games_px(params.get("marked_square_outline_width_px", group_default(_RENDER_DEFAULTS, "marked_square_outline_width_px", _DEFAULTS.marked_square_outline_width_px)), unit_scale, min_px=3),
        player_badge_font_size_px=int(params.get("player_badge_font_size_px", group_default(_RENDER_DEFAULTS, "player_badge_font_size_px", _DEFAULTS.player_badge_font_size_px))),
        coordinate_label_font_size_px=int(params.get("coordinate_label_font_size_px", group_default(_RENDER_DEFAULTS, "coordinate_label_font_size_px", _DEFAULTS.coordinate_label_font_size_px))),
        option_panel_gap_px=scale_games_px(params.get("option_panel_gap_px", group_default(_RENDER_DEFAULTS, "option_panel_gap_px", _DEFAULTS.option_panel_gap_px)), unit_scale, min_px=8),
        option_panel_height_px=scale_games_px(params.get("option_panel_height_px", group_default(_RENDER_DEFAULTS, "option_panel_height_px", _DEFAULTS.option_panel_height_px)), unit_scale, min_px=0),
        option_panel_font_size_px=int(params.get("option_panel_font_size_px", group_default(_RENDER_DEFAULTS, "option_panel_font_size_px", _DEFAULTS.option_panel_font_size_px))),
        layout_jitter_meta=layout_jitter,
        font_family=str(font_family),
        instance_seed=int(instance_seed),
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


def _piece_kind_plural(kind: str) -> str:
    """Return a prompt-facing plural for one chess piece kind."""

    if str(kind) == "king":
        return "kings"
    return f"{str(kind)}s"


def _piece_count_range(scene_variant: str) -> Tuple[int, int]:
    """Return target occupied-piece bounds for one scene variant."""

    if str(scene_variant) == "crowded_board":
        return int(_DEFAULTS.crowded_min_occupied_count), int(_DEFAULTS.crowded_max_occupied_count)
    return int(_DEFAULTS.sparse_min_occupied_count), int(_DEFAULTS.sparse_max_occupied_count)


def _valid_pawn_row(color: str, row: int) -> bool:
    """Return whether a pawn can be shown on this row without promotion ambiguity."""

    del color
    return standard_pawn_row_valid(int(row))


def _coords_adjacent(a: Coord, b: Coord) -> bool:
    """Return whether two coordinates are king-adjacent."""

    return coords_adjacent(a, b)


def _place_capped_random_piece(
    *,
    rng,
    mutable: list[list[ChessPiece | None]],
    coord: Coord,
    colors: Sequence[str] = (WHITE, BLACK),
    kinds: Sequence[str] = PIECE_KINDS,
) -> bool:
    """Place one material-capped standard chess piece on an empty square."""

    row, col = int(coord[0]), int(coord[1])
    if mutable[row][col] is not None:
        return False
    piece = sample_material_piece(
        rng,
        freeze_board(mutable),
        colors=colors,
        kinds=kinds,
        row=int(row),
        enforce_standard_pawn_rows=True,
    )
    if piece is None:
        return False
    mutable[row][col] = piece
    return True


def _place_capped_piece(
    *,
    mutable: list[list[ChessPiece | None]],
    coord: Coord,
    piece: ChessPiece,
) -> bool:
    """Place one requested piece if doing so preserves standard material caps."""

    row, col = int(coord[0]), int(coord[1])
    if mutable[row][col] is not None:
        return False
    candidate = [list(board_row) for board_row in mutable]
    candidate[row][col] = piece
    if not validate_square_chess_material(
        freeze_board(candidate),
        require_both_kings=False,
        enforce_standard_pawn_rows=True,
        enforce_non_adjacent_kings=False,
    ):
        return False
    mutable[row][col] = piece
    return True


def _board_after_king_move(board: Board, king_coord: Coord, dest: Coord) -> Board:
    """Return a board with the marked king moved to one destination."""

    row, col = int(king_coord[0]), int(king_coord[1])
    piece = board[row][col]
    if piece is None or str(piece.kind) != "king":
        raise ValueError("king move requested for a non-king square")
    mutable = [list(board_row) for board_row in board]
    mutable[row][col] = None
    mutable[int(dest[0])][int(dest[1])] = piece
    return freeze_board(mutable)


def _opponent_attackers_after_king_move(board: Board, king_coord: Coord, dest: Coord, king_color: str) -> Tuple[Coord, ...]:
    """Return opponent pieces attacking one candidate square after the king moves."""

    moved_board = _board_after_king_move(board, king_coord, dest)
    return attackers_to_square(moved_board, dest, opponent(str(king_color)))


def _same_color_slider_points_to_escape(board: Board, *, color: str, escape_coords: Tuple[Coord, ...]) -> bool:
    """Return whether a friendly slider visually points at an escape witness square."""

    if not escape_coords:
        return False
    for coord in occupied_coords(board):
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None or str(piece.color) != str(color) or str(piece.kind) not in {"queen", "rook", "bishop"}:
            continue
        if any(piece_attacks_square(board, coord, escape_coord) for escape_coord in escape_coords):
            return True
    return False


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

    attempts = 0
    while occupied_piece_count(mutable) < desired_count and attempts < 320:
        attempts += 1
        row, col = _random_empty_coord(rng, mutable)
        if not _place_capped_random_piece(
            rng=rng,
            mutable=mutable,
            coord=(row, col),
            kinds=("queen", "rook", "bishop", "knight", "pawn"),
        ):
            continue
    if occupied_piece_count(mutable) < minimum:
        raise ValueError("failed to reach requested chess density")
    board = freeze_board(mutable)
    if not validate_square_chess_material(board):
        raise ValueError("sampled chess board is not material-plausible")
    return board


def _piece_entity_ids(board: Board, coords: Tuple[Coord, ...]) -> Tuple[str, ...]:
    """Return piece entity ids for occupied coordinates."""

    ids = []
    for coord in coords:
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None:
            raise ValueError("piece annotation coordinate is empty")
        ids.append(piece_to_entity_id(coord, piece))
    return tuple(ids)


def _evaluate_board(
    *,
    board: Board,
    query_id: str,
    player_color: str,
    marked_coord: Coord | None,
    target_coord: Coord | None = None,
    target_piece_kind: str = "",
    target_piece_color: str = "",
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
            annotation_coords=destinations,
            annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in destinations),
            annotation_kind="cell",
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
            annotation_coords=captures,
            annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in captures),
            annotation_kind="cell",
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
            annotation_coords=captures,
            annotation_entity_ids=_piece_entity_ids(board, captures),
            annotation_kind="piece",
            marked_coord=None,
            player_color=str(player_color),
            marked_piece=None,
            destination_coords=(),
            capture_coords=captures,
            attacker_coords=(),
        )
    if str(query_id) == "king_square_attacker_count":
        if marked_coord is None:
            return None
        king = board[int(marked_coord[0])][int(marked_coord[1])]
        if king is None or str(king.kind) != "king":
            return None
        attackers = attackers_to_square(board, marked_coord, opponent(str(king.color)))
        return _SceneEvaluation(
            answer=int(len(attackers)),
            annotation_coords=attackers,
            annotation_entity_ids=_piece_entity_ids(board, attackers),
            annotation_kind="piece",
            marked_coord=marked_coord,
            player_color=str(king.color),
            marked_piece=king,
            destination_coords=(),
            capture_coords=(),
            attacker_coords=attackers,
        )
    if str(query_id) in {"white_piece_attacks_target_square_count", "black_piece_attacks_target_square_count"}:
        if marked_coord is None:
            return None
        if board[int(marked_coord[0])][int(marked_coord[1])] is not None:
            return None
        attacker_color = WHITE if str(query_id) == "white_piece_attacks_target_square_count" else BLACK
        attackers = attackers_to_square(board, marked_coord, attacker_color)
        return _SceneEvaluation(
            answer=int(len(attackers)),
            annotation_coords=attackers,
            annotation_entity_ids=_piece_entity_ids(board, attackers),
            annotation_kind="piece",
            marked_coord=marked_coord,
            player_color=str(attacker_color),
            marked_piece=None,
            destination_coords=(),
            capture_coords=(),
            attacker_coords=attackers,
            target_coord=marked_coord,
        )
    if str(query_id) in MARKED_PIECE_BLOCKER_QUERY_IDS:
        if marked_coord is None or target_coord is None:
            return None
        piece = board[int(marked_coord[0])][int(marked_coord[1])]
        if piece is None or str(piece.kind) != _blocker_query_piece_kind(str(query_id)):
            return None
        if board[int(target_coord[0])][int(target_coord[1])] is not None:
            return None
        between = _coords_between(marked_coord, target_coord)
        if not between or not _blocker_query_allows_line(str(query_id), marked_coord, target_coord):
            return None
        blockers = tuple(coord for coord in between if board[int(coord[0])][int(coord[1])] is not None)
        return _SceneEvaluation(
            answer=int(len(blockers)),
            annotation_coords=tuple(sorted(blockers)),
            annotation_entity_ids=_piece_entity_ids(board, tuple(sorted(blockers))),
            annotation_kind="piece",
            marked_coord=marked_coord,
            player_color=str(piece.color),
            marked_piece=piece,
            destination_coords=(),
            capture_coords=(),
            attacker_coords=(),
            target_coord=target_coord,
            blocker_coords=tuple(sorted(blockers)),
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
            annotation_coords=escapes,
            annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in escapes),
            annotation_kind="cell",
            marked_coord=marked_coord,
            player_color=str(king.color),
            marked_piece=king,
            destination_coords=escapes,
            capture_coords=(),
            attacker_coords=(),
        )
    if str(query_id) in PIECE_COUNT_QUERY_IDS:
        target_kind = str(target_piece_kind)
        if target_kind not in PIECE_COUNT_KIND_SUPPORT:
            return None
        target_color = str(target_piece_color)
        if str(query_id) == "colored_piece_kind_count" and target_color not in PIECE_COUNT_COLOR_SUPPORT:
            return None
        matches = []
        for coord in occupied_coords(board):
            piece = board[int(coord[0])][int(coord[1])]
            if piece is None or str(piece.kind) != target_kind:
                continue
            if str(query_id) == "colored_piece_kind_count" and str(piece.color) != target_color:
                continue
            matches.append(coord)
        matches_tuple = tuple(sorted(matches))
        return _SceneEvaluation(
            answer=int(len(matches_tuple)),
            annotation_coords=matches_tuple,
            annotation_entity_ids=_piece_entity_ids(board, matches_tuple),
            annotation_kind="piece",
            marked_coord=None,
            player_color=target_color if target_color in PIECE_COUNT_COLOR_SUPPORT else WHITE,
            marked_piece=None,
            destination_coords=(),
            capture_coords=(),
            attacker_coords=(),
            target_piece_kind=str(target_kind),
            target_piece_color=str(target_color),
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


def _line_step_between(a: Coord, b: Coord) -> Coord | None:
    """Return one unit row/file/diagonal step from a to b, or None if unaligned."""

    ar, ac = int(a[0]), int(a[1])
    br, bc = int(b[0]), int(b[1])
    if (ar, ac) == (br, bc):
        return None
    if ar == br:
        return (0, 1 if bc > ac else -1)
    if ac == bc:
        return (1 if br > ar else -1, 0)
    if abs(ar - br) == abs(ac - bc):
        return (1 if br > ar else -1, 1 if bc > ac else -1)
    return None


def _coords_between(a: Coord, b: Coord) -> Tuple[Coord, ...]:
    """Return board coordinates strictly between two aligned coordinates."""

    step = _line_step_between(a, b)
    if step is None:
        return ()
    out: list[Coord] = []
    r, c = int(a[0]) + int(step[0]), int(a[1]) + int(step[1])
    while (int(r), int(c)) != (int(b[0]), int(b[1])):
        out.append((int(r), int(c)))
        r += int(step[0])
        c += int(step[1])
    return tuple(out)


def _blocker_query_piece_kind(query_id: str) -> str:
    """Return the marked sliding piece kind required by one blocker query."""

    return {
        "rook_line_blocker_count": "rook",
        "bishop_diagonal_blocker_count": "bishop",
        "queen_line_blocker_count": "queen",
    }[str(query_id)]


def _blocker_query_directions(query_id: str) -> Tuple[Coord, ...]:
    """Return source-to-target line directions allowed by one blocker query."""

    if str(query_id) == "rook_line_blocker_count":
        return ((-1, 0), (1, 0), (0, -1), (0, 1))
    if str(query_id) == "bishop_diagonal_blocker_count":
        return ((-1, -1), (-1, 1), (1, -1), (1, 1))
    if str(query_id) == "queen_line_blocker_count":
        return ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    raise ValueError(f"unsupported blocker query_id: {query_id}")


def _blocker_query_allows_line(query_id: str, source: Coord, target: Coord) -> bool:
    """Return whether target lies on an allowed ray from source for the query."""

    step = _line_step_between(source, target)
    return step is not None and tuple(step) in _blocker_query_directions(str(query_id))


def _attacker_slots_for_square(target_coord: Coord, attacker_color: str) -> Tuple[Tuple[Coord, str], ...]:
    """Return candidate attacker placements around one marked target square."""

    row, col = int(target_coord[0]), int(target_coord[1])
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


def _place_non_attacking_kings(
    *,
    rng,
    mutable: list[list[ChessPiece | None]],
    target_coord: Coord,
    attacker_color: str,
) -> None:
    """Place both kings without adding an attacker to the marked target square."""

    placed_kings: list[Coord] = []
    for color in (attacker_color, opponent(attacker_color)):
        for _attempt in range(192):
            coord = _random_empty_coord(rng, mutable)
            if coord == target_coord:
                continue
            if _coords_adjacent(coord, target_coord):
                continue
            if any(_coords_adjacent(coord, other) for other in placed_kings):
                continue
            mutable[int(coord[0])][int(coord[1])] = ChessPiece(str(color), "king")
            placed_kings.append(coord)
            break
        else:
            raise ValueError("failed to place non-attacking kings")


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
        if (
            str(axes.query_id) == "king_escape_square_count"
            and evaluation.marked_coord is not None
            and _coords_adjacent((int(row), int(col)), evaluation.marked_coord)
        ):
            continue
        if not _place_capped_random_piece(
            rng=rng,
            mutable=mutable,
            coord=(row, col),
            kinds=("queen", "rook", "bishop", "knight", "pawn"),
        ):
            continue
        frozen = freeze_board(mutable)
        if not validate_square_chess_material(
            frozen,
            require_both_kings=False,
            enforce_standard_pawn_rows=True,
            enforce_non_adjacent_kings=True,
        ):
            mutable[row][col] = None
            continue
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
            target_coord=evaluation.target_coord,
        )
        if candidate is None or int(candidate.answer) != int(axes.target_answer):
            mutable[row][col] = None
            continue
        if (
            str(axes.query_id) == "king_escape_square_count"
            and candidate.marked_piece is not None
            and _same_color_slider_points_to_escape(
                frozen,
                color=str(candidate.marked_piece.color),
                escape_coords=tuple(candidate.destination_coords),
            )
        ):
            mutable[row][col] = None
            continue
        evaluation = candidate
    frozen = freeze_board(mutable)
    if occupied_piece_count(frozen) < int(minimum):
        raise ValueError("failed to reach requested Chess density while preserving answer")
    if not validate_square_chess_material(frozen):
        raise ValueError("filler-added chess board is not material-plausible")
    return frozen, evaluation


def _sample_king_square_attacker_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a board with a marked king attacked by the requested count."""

    mutable = [list(row) for row in empty_board()]
    king_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
    attacker_color = opponent(king_color)
    king_coord = (int(rng.randint(2, 5)), int(rng.randint(2, 5)))
    mutable[king_coord[0]][king_coord[1]] = ChessPiece(king_color, "king")
    slots = list(_attacker_slots_for_square(king_coord, attacker_color))
    rng.shuffle(slots)
    selected: list[Tuple[Coord, str]] = []
    if int(axes.target_answer) > 0:
        for coord, kind in slots:
            if mutable[int(coord[0])][int(coord[1])] is not None:
                continue
            if any(coord == other for other, _kind in selected):
                continue
            if any(_line_clear_between(king_coord, other, coord) or _line_clear_between(king_coord, coord, other) for other, _kind in selected):
                continue
            if not _place_capped_piece(
                mutable=mutable,
                coord=coord,
                piece=ChessPiece(attacker_color, kind),
            ):
                continue
            selected.append((coord, kind))
            if len(selected) == int(axes.target_answer):
                break
    if len(selected) != int(axes.target_answer):
        raise ValueError("failed to choose requested king-square attackers")
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
        raise ValueError("constructed king-square attacker board does not match requested answer")
    board, evaluation = _try_add_fillers_preserving(rng=rng, board=board, axes=axes, evaluation=evaluation, params={})
    return _SampledChessScene(
        board=board,
        evaluation=evaluation,
        occupied_count=int(occupied_piece_count(board)),
        construction_mode="direct_king_attackers",
    )


def _sample_empty_target_square_attacker_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a board with an empty marked target square attacked by one side."""

    attacker_color = WHITE if str(axes.query_id) == "white_piece_attacks_target_square_count" else BLACK
    for _attempt in range(128):
        mutable = [list(row) for row in empty_board()]
        target_coord = (int(rng.randint(2, 5)), int(rng.randint(2, 5)))
        slots = list(_attacker_slots_for_square(target_coord, attacker_color))
        rng.shuffle(slots)
        selected: list[Tuple[Coord, str]] = []
        if int(axes.target_answer) > 0:
            for coord, kind in slots:
                if mutable[int(coord[0])][int(coord[1])] is not None:
                    continue
                if coord == target_coord:
                    continue
                if any(coord == other for other, _kind in selected):
                    continue
                if any(
                    _line_clear_between(target_coord, other, coord)
                    or _line_clear_between(target_coord, coord, other)
                    for other, _kind in selected
                ):
                    continue
                if not _place_capped_piece(
                    mutable=mutable,
                    coord=coord,
                    piece=ChessPiece(attacker_color, kind),
                ):
                    continue
                selected.append((coord, kind))
                if len(selected) == int(axes.target_answer):
                    break
        if len(selected) != int(axes.target_answer):
            continue
        try:
            _place_non_attacking_kings(
                rng=rng,
                mutable=mutable,
                target_coord=target_coord,
                attacker_color=attacker_color,
            )
        except ValueError:
            continue
        board = freeze_board(mutable)
        evaluation = _evaluate_board(
            board=board,
            query_id=str(axes.query_id),
            player_color=attacker_color,
            marked_coord=target_coord,
        )
        if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
            continue
        board, evaluation = _try_add_fillers_preserving(
            rng=rng,
            board=board,
            axes=axes,
            evaluation=evaluation,
            params={},
        )
        return _SampledChessScene(
            board=board,
            evaluation=evaluation,
            occupied_count=int(occupied_piece_count(board)),
            construction_mode="direct_empty_target_square_attackers",
        )
    raise ValueError("failed to construct requested target-square attacker count")


def _sample_marked_piece_blocker_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a board with a marked slider and exact blockers before an empty target."""

    query_id = str(axes.query_id)
    source_kind = _blocker_query_piece_kind(query_id)
    candidate_pairs: list[Tuple[Coord, Coord, Tuple[Coord, ...]]] = []
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            source = (int(row), int(col))
            for dr, dc in _blocker_query_directions(query_id):
                for distance in range(max(2, int(axes.target_answer) + 1), BOARD_SIZE):
                    target = (int(row + (dr * distance)), int(col + (dc * distance)))
                    if not in_bounds(*target):
                        break
                    between = _coords_between(source, target)
                    if len(between) >= int(axes.target_answer):
                        candidate_pairs.append((source, target, between))
    if not candidate_pairs:
        raise ValueError("no feasible source-target line for requested blocker count")

    for _attempt in range(160):
        mutable = [list(row) for row in empty_board()]
        source_coord, target_coord, between_coords = tuple(rng.choice(candidate_pairs))
        source_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
        if not _place_capped_piece(
            mutable=mutable,
            coord=source_coord,
            piece=ChessPiece(source_color, source_kind),
        ):
            continue

        blocker_positions = list(between_coords)
        rng.shuffle(blocker_positions)
        blocker_positions = blocker_positions[: int(axes.target_answer)]
        failed = False
        for coord in blocker_positions:
            if not _place_capped_random_piece(
                rng=rng,
                mutable=mutable,
                coord=coord,
                kinds=("queen", "rook", "bishop", "knight", "pawn"),
            ):
                failed = True
                break
        if failed:
            continue

        placed_kings: list[Coord] = []
        forbidden = {source_coord, target_coord, *between_coords}
        for color in (source_color, opponent(source_color)):
            placed = False
            for _king_attempt in range(192):
                coord = _random_empty_coord(rng, mutable)
                if coord in forbidden:
                    continue
                if any(_coords_adjacent(coord, other) for other in placed_kings):
                    continue
                mutable[int(coord[0])][int(coord[1])] = ChessPiece(color, "king")
                placed_kings.append(coord)
                placed = True
                break
            if not placed:
                break
        if len(placed_kings) != 2:
            continue

        board = freeze_board(mutable)
        evaluation = _evaluate_board(
            board=board,
            query_id=query_id,
            player_color=source_color,
            marked_coord=source_coord,
            target_coord=target_coord,
        )
        if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
            continue
        board, evaluation = _try_add_fillers_preserving(
            rng=rng,
            board=board,
            axes=axes,
            evaluation=evaluation,
            params={},
        )
        return _SampledChessScene(
            board=board,
            evaluation=evaluation,
            occupied_count=int(occupied_piece_count(board)),
            construction_mode="direct_marked_piece_blocker_count",
        )
    raise ValueError("failed to construct requested marked-piece blocker count")


_KNIGHT_ATTACK_DELTAS: Tuple[Coord, ...] = (
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
)


def _place_knight_attacker_for_escape_square(
    *,
    rng,
    mutable: list[list[ChessPiece | None]],
    target_coord: Coord,
    king_coord: Coord,
    attacker_color: str,
    safe_coords: Tuple[Coord, ...],
    adjacent_coords: Tuple[Coord, ...],
) -> bool:
    """Place one opponent knight that attacks an unsafe king-escape candidate."""

    candidates: list[Coord] = []
    for dr, dc in _KNIGHT_ATTACK_DELTAS:
        origin = (int(target_coord[0]) - int(dr), int(target_coord[1]) - int(dc))
        if not in_bounds(*origin):
            continue
        if origin == king_coord or origin in adjacent_coords:
            continue
        if mutable[int(origin[0])][int(origin[1])] is not None:
            continue
        candidates.append(origin)
    rng.shuffle(candidates)
    for origin in candidates:
        if not _place_capped_piece(
            mutable=mutable,
            coord=origin,
            piece=ChessPiece(attacker_color, "knight"),
        ):
            continue
        board = freeze_board(mutable)
        attacks_safe_square = any(piece_attacks_square(board, origin, safe_coord) for safe_coord in safe_coords)
        attacks_target = piece_attacks_square(board, origin, target_coord)
        if attacks_target and not attacks_safe_square:
            return True
        mutable[int(origin[0])][int(origin[1])] = None
    return False


def _sample_king_escape_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a board with a marked king and the requested safe one-step escapes."""

    for _attempt in range(160):
        mutable = [list(row) for row in empty_board()]
        king_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
        opponent_color = opponent(king_color)
        king_coord = (int(rng.randint(2, 5)), int(rng.randint(2, 5)))
        mutable[king_coord[0]][king_coord[1]] = ChessPiece(king_color, "king")

        adjacent = [
            (int(king_coord[0] + dr), int(king_coord[1] + dc))
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if not (int(dr) == 0 and int(dc) == 0)
        ]
        rng.shuffle(adjacent)
        safe_coords = tuple(adjacent[: int(axes.target_answer)])
        unsafe_coords = [coord for coord in adjacent if coord not in safe_coords]
        rng.shuffle(unsafe_coords)

        attacked_unsafe: list[Coord] = []
        if unsafe_coords:
            lower_attack_count = 1
            upper_attack_count = max(lower_attack_count, min(len(unsafe_coords), 2))
            attack_count = int(rng.randint(lower_attack_count, upper_attack_count))
            attacked_unsafe = list(unsafe_coords[:attack_count])
        blocked_unsafe = [coord for coord in unsafe_coords if coord not in attacked_unsafe]

        failed = False
        for coord in attacked_unsafe:
            if not _place_knight_attacker_for_escape_square(
                rng=rng,
                mutable=mutable,
                target_coord=coord,
                king_coord=king_coord,
                attacker_color=opponent_color,
                safe_coords=safe_coords,
                adjacent_coords=tuple(adjacent),
            ):
                failed = True
                break
        if failed:
            continue

        for coord in blocked_unsafe:
            if not _place_capped_random_piece(
                rng=rng,
                mutable=mutable,
                coord=coord,
                colors=(king_color,),
                kinds=("knight", "pawn"),
            ):
                failed = True
                break
        if failed:
            continue

        possible_opponent_king_coords = [
            (row, col)
            for row in range(BOARD_SIZE)
            for col in range(BOARD_SIZE)
            if mutable[row][col] is None
            and not _coords_adjacent((row, col), king_coord)
            and all(not _coords_adjacent((row, col), coord) for coord in safe_coords)
        ]
        if not possible_opponent_king_coords:
            continue
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
            continue
        if _same_color_slider_points_to_escape(board, color=king_color, escape_coords=tuple(evaluation.destination_coords)):
            continue
        if unsafe_coords and not any(
            _opponent_attackers_after_king_move(board, king_coord, coord, king_color)
            for coord in unsafe_coords
            if board[int(coord[0])][int(coord[1])] is None
        ):
            continue
        board, evaluation = _try_add_fillers_preserving(rng=rng, board=board, axes=axes, evaluation=evaluation, params={})
        return _SampledChessScene(
            board=board,
            evaluation=evaluation,
            occupied_count=int(occupied_piece_count(board)),
            construction_mode="direct_king_escape_attacked_and_blocked_squares",
        )
    raise ValueError("failed to construct requested king-escape count")


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
        if not _place_capped_piece(
            mutable=mutable,
            coord=marked_coord,
            piece=ChessPiece(piece_color, "rook"),
        ):
            continue
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
        failed = False
        for (dr, dc), free_count, capacity in zip(directions, allocations, capacities):
            if int(free_count) >= int(capacity):
                continue
            blocker_distance = int(free_count) + 1
            blocker_coord = (
                int(marked_coord[0]) + int(dr) * int(blocker_distance),
                int(marked_coord[1]) + int(dc) * int(blocker_distance),
            )
            if not _place_capped_random_piece(
                rng=rng,
                mutable=mutable,
                coord=blocker_coord,
                colors=(piece_color,),
                kinds=("queen", "rook", "bishop", "knight", "pawn"),
            ):
                failed = True
                break
        if failed:
            continue

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
        if not _place_capped_piece(
            mutable=mutable,
            coord=queen_coord,
            piece=ChessPiece(player_color, "queen"),
        ):
            continue
        selected_targets = list(ray_targets)
        rng.shuffle(selected_targets)
        selected_targets = selected_targets[: int(axes.target_answer)]
        failed = False
        for coord in selected_targets:
            if not _place_capped_random_piece(
                rng=rng,
                mutable=mutable,
                coord=coord,
                colors=(opposing_color,),
                kinds=("rook", "bishop", "knight", "pawn"),
            ):
                failed = True
                break
        if failed:
            continue

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


def _empty_coords_for_piece_kind(mutable: list[list[ChessPiece | None]], kind: str) -> Tuple[Coord, ...]:
    """Return empty cells suitable for displaying one piece kind."""

    coords = []
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if mutable[row][col] is not None:
                continue
            if str(kind) == "pawn" and not _valid_pawn_row(WHITE, int(row)):
                continue
            coords.append((int(row), int(col)))
    return tuple(coords)


def _place_display_piece(*, rng, mutable: list[list[ChessPiece | None]], color: str, kind: str) -> bool:
    """Place one non-position-legal chess display piece on an empty board cell."""

    candidates = list(_empty_coords_for_piece_kind(mutable, str(kind)))
    if not candidates:
        return False
    coord = tuple(rng.choice(candidates))
    mutable[int(coord[0])][int(coord[1])] = ChessPiece(str(color), str(kind))
    return True


def _sample_piece_type_count_scene(*, rng, axes: _ResolvedAxes) -> _SampledChessScene:
    """Construct a display board with an exact count of one chess piece type."""

    target_kind = str(axes.target_piece_kind)
    if target_kind not in PIECE_COUNT_KIND_SUPPORT:
        raise ValueError(f"unsupported target chess piece kind: {target_kind}")
    target_color = str(axes.target_piece_color)
    if target_color not in PIECE_COUNT_COLOR_SUPPORT:
        raise ValueError(f"unsupported target chess piece color: {target_color}")

    for _attempt in range(96):
        mutable = [list(row) for row in empty_board()]
        for _ in range(int(axes.target_answer)):
            color = target_color if str(axes.query_id) == "colored_piece_kind_count" else str(rng.choice(PIECE_COUNT_COLOR_SUPPORT))
            if not _place_display_piece(rng=rng, mutable=mutable, color=color, kind=target_kind):
                raise ValueError("failed to place requested target chess pieces")

        distractor_specs: list[Tuple[str, str]] = []
        for color in PIECE_COUNT_COLOR_SUPPORT:
            for kind in PIECE_COUNT_KIND_SUPPORT:
                if str(axes.query_id) == "piece_kind_count" and str(kind) == target_kind:
                    continue
                if str(axes.query_id) == "colored_piece_kind_count" and str(kind) == target_kind and str(color) == target_color:
                    continue
                distractor_specs.append((str(color), str(kind)))

        failed = False
        for _ in range(int(axes.distractor_count)):
            color, kind = tuple(rng.choice(distractor_specs))
            if not _place_display_piece(rng=rng, mutable=mutable, color=color, kind=kind):
                failed = True
                break
        if failed:
            continue

        board = freeze_board(mutable)
        evaluation = _evaluate_board(
            board=board,
            query_id=str(axes.query_id),
            player_color=target_color,
            marked_coord=None,
            target_piece_kind=target_kind,
            target_piece_color=target_color,
        )
        if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
            continue
        return _SampledChessScene(
            board=board,
            evaluation=evaluation,
            occupied_count=int(occupied_piece_count(board)),
            construction_mode="display_piece_type_count",
        )
    raise ValueError("failed to construct requested chess piece-type count")


def _string_probability_map(values: Sequence[str], selected: str) -> Dict[str, float]:
    """Return a one-hot probability map for string-valued trace axes."""

    return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in values}


def _resolve_checkmate_option_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[int, Tuple[str, ...], Dict[str, float]]:
    """Resolve the visible move-option count for the checkmate task."""

    support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="checkmate_option_count_support",
        fallback=(4, 6),
    )
    option_count, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="checkmate_option_count_support",
        explicit_key="option_count",
        fallback_support=support,
        namespace=f"{CHECKMATE_TASK_ID}.option_count",
        balanced_flag_key="balanced_checkmate_option_count_sampling",
        namespace_support_permutation=True,
    )
    option_count = int(option_count)
    if option_count not in {4, 6}:
        raise ValueError("checkmate option_count must be either 4 or 6")
    return option_count, tuple(CHECKMATE_OPTION_LABELS[:option_count]), dict(probabilities)


def _resolve_checkmate_answer_label(
    *,
    rng,
    params: Mapping[str, Any],
    labels: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the correct option label for the checkmate task."""

    explicit = params.get("answer_option_label", params.get("target_label"))
    labels_tuple = tuple(str(label) for label in labels)
    if explicit is not None:
        label = str(explicit).strip().upper()
        if label not in labels_tuple:
            raise ValueError(f"answer_option_label={label!r} is not available for labels {labels_tuple}")
        return label, _string_probability_map(labels_tuple, label)
    sampling_index = params.get("_sample_cursor")
    balanced = bool(
        params.get(
            "balanced_checkmate_answer_label_sampling",
            group_default(_GEN_DEFAULTS, "balanced_checkmate_answer_label_sampling", True),
        )
    )
    if balanced and sampling_index is not None:
        label = labels_tuple[abs(int(sampling_index)) % len(labels_tuple)]
    else:
        label = str(rng.choice(labels_tuple))
    return label, _string_probability_map(labels_tuple, label)


def _base_checkmate_board(*, player_color: str, mirror_columns: bool) -> Tuple[Board, Coord, Coord]:
    """Return a compact queen mate-in-one pattern and the mating move."""

    def maybe_mirror(coord: Coord) -> Coord:
        if not bool(mirror_columns):
            return (int(coord[0]), int(coord[1]))
        return (int(coord[0]), int(BOARD_SIZE - 1 - int(coord[1])))

    mutable = [list(row) for row in empty_board()]
    if str(player_color) == WHITE:
        defender_color = BLACK
        defender_king = maybe_mirror((0, 7))
        attacker_king = maybe_mirror((2, 5))
        queen_source = maybe_mirror((2, 6))
        queen_destination = maybe_mirror((1, 6))
    else:
        defender_color = WHITE
        defender_king = maybe_mirror((7, 7))
        attacker_king = maybe_mirror((5, 5))
        queen_source = maybe_mirror((5, 6))
        queen_destination = maybe_mirror((6, 6))
    mutable[int(defender_king[0])][int(defender_king[1])] = ChessPiece(defender_color, "king")
    mutable[int(attacker_king[0])][int(attacker_king[1])] = ChessPiece(str(player_color), "king")
    mutable[int(queen_source[0])][int(queen_source[1])] = ChessPiece(str(player_color), "queen")
    return freeze_board(mutable), queen_source, queen_destination


def _checkmate_board_valid(board: Board, *, player_color: str, correct_source: Coord, correct_destination: Coord) -> bool:
    """Return whether the current position preserves the intended mate-in-one contract."""

    defender_color = opponent(str(player_color))
    if find_king(board, str(player_color)) is None or find_king(board, defender_color) is None:
        return False
    if is_king_in_check(board, str(player_color)) or is_king_in_check(board, defender_color):
        return False
    return move_checkmates(board, correct_source, correct_destination)


def _try_add_checkmate_fillers(
    *,
    rng,
    board: Board,
    player_color: str,
    correct_source: Coord,
    correct_destination: Coord,
    scene_variant: str,
) -> Board:
    """Add nonsemantic filler pieces while preserving the mate-in-one contract."""

    lower, upper = (6, 9) if str(scene_variant) == "sparse_board" else (9, 13)
    desired_count = int(rng.randint(int(lower), int(upper)))
    mutable = [list(row) for row in board]
    protected = {tuple(correct_source), tuple(correct_destination)}
    attempts = 0
    while occupied_piece_count(mutable) < desired_count and attempts < 360:
        attempts += 1
        coord = _random_empty_coord(rng, mutable)
        if coord in protected:
            continue
        if not _place_capped_random_piece(
            rng=rng,
            mutable=mutable,
            coord=coord,
            kinds=("rook", "bishop", "knight", "pawn"),
        ):
            continue
        candidate = freeze_board(mutable)
        if not validate_square_chess_material(candidate):
            mutable[int(coord[0])][int(coord[1])] = None
            continue
        if not _checkmate_board_valid(
            candidate,
            player_color=str(player_color),
            correct_source=correct_source,
            correct_destination=correct_destination,
        ):
            mutable[int(coord[0])][int(coord[1])] = None
    board = freeze_board(mutable)
    if not validate_square_chess_material(board):
        raise ValueError("checkmate board is not material-plausible")
    return board


def _option_from_move(board: Board, *, label: str, move: Tuple[Coord, Coord]) -> _CheckmateMoveOption:
    """Build one visible option record from a board move."""

    source, destination = move
    piece = board[int(source[0])][int(source[1])]
    if piece is None:
        raise ValueError("cannot build a move option from an empty source square")
    return _CheckmateMoveOption(
        label=str(label),
        source=(int(source[0]), int(source[1])),
        destination=(int(destination[0]), int(destination[1])),
        piece=piece,
    )


def _sample_checkmate_scene(
    *,
    instance_seed: int,
    rng,
    params: Mapping[str, Any],
) -> Tuple[_CheckmateSample, Dict[str, Any]]:
    """Construct one chess mate-in-one option-selection scene."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="checkmate_scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="checkmate_style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_CHESS_STYLE_VARIANTS,
    )
    option_count, option_label_support, option_count_probabilities = _resolve_checkmate_option_count(
        instance_seed=int(instance_seed),
        params=params,
    )
    answer_label, answer_label_probabilities = _resolve_checkmate_answer_label(
        rng=rng,
        params=params,
        labels=option_label_support,
    )
    player_color_raw = params.get("player_color")
    if player_color_raw is None:
        player_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
    else:
        player_color = str(player_color_raw).strip().lower()
        if player_color not in {WHITE, BLACK}:
            raise ValueError(f"unsupported player_color for checkmate task: {player_color_raw}")
    player_color_probabilities = _string_probability_map((WHITE, BLACK), player_color)
    mirror_columns = bool(rng.randrange(2))

    for _attempt in range(80):
        board, correct_source, correct_destination = _base_checkmate_board(
            player_color=str(player_color),
            mirror_columns=bool(mirror_columns),
        )
        if not _checkmate_board_valid(
            board,
            player_color=str(player_color),
            correct_source=correct_source,
            correct_destination=correct_destination,
        ):
            mirror_columns = not bool(mirror_columns)
            continue
        board = _try_add_checkmate_fillers(
            rng=rng,
            board=board,
            player_color=str(player_color),
            correct_source=correct_source,
            correct_destination=correct_destination,
            scene_variant=str(scene_variant),
        )
        legal_moves = list(legal_chess_moves_for_color(board, str(player_color)))
        correct_move = (tuple(correct_source), tuple(correct_destination))
        if correct_move not in legal_moves or not move_checkmates(board, correct_source, correct_destination):
            mirror_columns = not bool(mirror_columns)
            continue
        distractor_moves = [
            move
            for move in legal_moves
            if tuple(move) != tuple(correct_move) and not move_checkmates(board, move[0], move[1])
        ]
        rng.shuffle(distractor_moves)
        if len(distractor_moves) < int(option_count) - 1:
            mirror_columns = not bool(mirror_columns)
            continue
        labels = list(option_label_support)
        correct_index = labels.index(str(answer_label))
        selected_moves = distractor_moves[: int(option_count) - 1]
        options: list[_CheckmateMoveOption] = []
        distractor_iter = iter(selected_moves)
        for index, label in enumerate(labels):
            if int(index) == int(correct_index):
                options.append(_option_from_move(board, label=str(label), move=correct_move))
            else:
                options.append(_option_from_move(board, label=str(label), move=next(distractor_iter)))
        mate_option_labels = [
            option.label
            for option in options
            if move_checkmates(board, option.source, option.destination)
        ]
        if mate_option_labels != [str(answer_label)]:
            mirror_columns = not bool(mirror_columns)
            continue
        defender_color = opponent(str(player_color))
        defender_king = find_king(board, defender_color)
        if defender_king is None:
            raise ValueError("checkmate scene lacks defender king")
        sample = _CheckmateSample(
            board=board,
            player_color=str(player_color),
            defender_color=str(defender_color),
            correct_option=options[int(correct_index)],
            options=tuple(options),
            defender_king_coord=defender_king,
            occupied_count=int(occupied_piece_count(board)),
            scene_variant=str(scene_variant),
            style_variant=str(style_variant),
            construction_mode="queen_corner_mate_in_one_with_legal_distractors",
            option_count=int(option_count),
            option_label_support=tuple(option_label_support),
        )
        axes_meta = {
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "style_variant_probabilities": dict(style_variant_probabilities),
            "option_count_probabilities": dict(option_count_probabilities),
            "answer_label_probabilities": dict(answer_label_probabilities),
            "player_color_probabilities": dict(player_color_probabilities),
            "mirror_columns": bool(mirror_columns),
        }
        return sample, axes_meta
    raise ValueError("failed to construct chess checkmate move-label scene")


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SampledChessScene:
    """Construct one Chess scene consistent with the requested axes."""

    if str(axes.query_id) in PIECE_COUNT_QUERY_IDS:
        return _sample_piece_type_count_scene(rng=rng, axes=axes)
    if str(axes.query_id) == "king_square_attacker_count":
        return _sample_king_square_attacker_scene(rng=rng, axes=axes)
    if str(axes.query_id) in {"white_piece_attacks_target_square_count", "black_piece_attacks_target_square_count"}:
        return _sample_empty_target_square_attacker_scene(rng=rng, axes=axes)
    if str(axes.query_id) in MARKED_PIECE_BLOCKER_QUERY_IDS:
        return _sample_marked_piece_blocker_scene(rng=rng, axes=axes)
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
    annotation_value = [[140, 220, 210, 290], [210, 220, 280, 290]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _badge_text(evaluation: _SceneEvaluation, query_id: str) -> str:
    """Return compact text displayed above the board."""

    if str(query_id) in PIECE_COUNT_QUERY_IDS:
        return "Chess-piece count"
    if str(query_id) in {"white_piece_attacks_target_square_count", "black_piece_attacks_target_square_count"}:
        return "Marked target square"
    if str(query_id) in MARKED_PIECE_BLOCKER_QUERY_IDS:
        return "Marked line target"
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
            namespace="games.chess_board.panel_scene_style",
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
        rendered_scene = render_chess_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            badge_text=_badge_text(sampled_scene.evaluation, str(axes.query_id)),
            marked_coord=sampled_scene.evaluation.marked_coord,
            params=render_params,
            target_coord=sampled_scene.evaluation.target_coord,
            panel_style=panel_style,
        )
        if sampled_scene.evaluation.annotation_kind == "cell":
            annotation_bboxes = [
                list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
                for entity_id in sampled_scene.evaluation.annotation_entity_ids
            ]
        else:
            annotation_bboxes = [
                list(rendered_scene.render_map["piece_bboxes_px"][str(entity_id)])
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
                "object_description_sparse_board",
                "object_description_crowded_board",
                "standard_rule_text",
                "marked_piece_rule_text",
                "player_rule_text",
                "target_square_rule_text",
                "king_square_attacker_rule_text",
                "blocker_rule_text",
                "king_escape_rule_text",
                "answer_hint_marked_piece_move_count",
                "answer_hint_marked_piece_capture_count",
                "answer_hint_player_capture_piece_count",
                "answer_hint_king_square_attacker_count",
                "answer_hint_white_piece_attacks_target_square_count",
                "answer_hint_black_piece_attacks_target_square_count",
                "answer_hint_rook_line_blocker_count",
                "answer_hint_bishop_diagonal_blocker_count",
                "answer_hint_queen_line_blocker_count",
                "answer_hint_king_escape_square_count",
                "answer_hint_piece_kind_count",
                "answer_hint_colored_piece_kind_count",
                "annotation_hint_marked_piece_move_count",
                "annotation_hint_marked_piece_capture_count",
                "annotation_hint_player_capture_piece_count",
                "annotation_hint_king_square_attacker_count",
                "annotation_hint_white_piece_attacks_target_square_count",
                "annotation_hint_black_piece_attacks_target_square_count",
                "annotation_hint_rook_line_blocker_count",
                "annotation_hint_bishop_diagonal_blocker_count",
                "annotation_hint_queen_line_blocker_count",
                "annotation_hint_king_escape_square_count",
                "annotation_hint_piece_kind_count",
                "annotation_hint_colored_piece_kind_count",
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
            "target_color_name": str(color_name(axes.target_piece_color)),
            "target_piece_kind": str(axes.target_piece_kind),
            "target_piece_kind_plural": str(_piece_kind_plural(axes.target_piece_kind)),
        }
        answer_hint = str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]).format(**hint_slots)
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]).format(**hint_slots)
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
                "answer_hint": str(answer_hint),
                "annotation_hint": str(annotation_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "standard_rule_text": str(prompt_defaults["standard_rule_text"]),
                "marked_piece_rule_text": str(prompt_defaults["marked_piece_rule_text"]),
                "player_rule_text": str(prompt_defaults["player_rule_text"]),
                "target_square_rule_text": str(prompt_defaults["target_square_rule_text"]),
                "king_square_attacker_rule_text": str(prompt_defaults["king_square_attacker_rule_text"]),
                "blocker_rule_text": str(prompt_defaults["blocker_rule_text"]),
                "king_escape_rule_text": str(prompt_defaults["king_escape_rule_text"]),
                "player_color_name": str(player_color_name),
                "opponent_color_name": str(opponent_color_name),
                "target_color_name": str(color_name(axes.target_piece_color)),
                "target_piece_kind": str(axes.target_piece_kind),
                "target_piece_kind_plural": str(_piece_kind_plural(axes.target_piece_kind)),
                "marked_piece_text": str(marked_piece_text),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(evaluation.answer))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
            "piece_symbol_font_family": "system_fallback",
        }
        complexity = build_games_chess_board_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            occupied_count=int(sampled_scene.occupied_count),
            target_answer=int(evaluation.answer),
            annotation_count=len(evaluation.annotation_entity_ids),
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
                    "target_piece_kind": str(evaluation.target_piece_kind),
                    "target_piece_color": str(evaluation.target_piece_color),
                    "marked_cell_id": None if evaluation.marked_coord is None else coord_to_cell_id(evaluation.marked_coord),
                    "target_cell_id": None if evaluation.target_coord is None else coord_to_cell_id(evaluation.target_coord),
                    "annotation_entity_ids": [str(entity_id) for entity_id in evaluation.annotation_entity_ids],
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
                    "target_piece_kind": str(axes.target_piece_kind),
                    "target_piece_color": str(axes.target_piece_color),
                    "target_piece_kind_probabilities": dict(axes.target_piece_kind_probabilities),
                    "target_piece_color_probabilities": dict(axes.target_piece_color_probabilities),
                    "piece_count_distractor_count": int(axes.distractor_count),
                    "piece_count_distractor_count_probabilities": dict(axes.distractor_count_probabilities),
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
                "effective_cell_size_px": rendered_scene.render_map.get("effective_cell_size_px"),
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
                "target_piece_kind": str(evaluation.target_piece_kind),
                "target_piece_color": str(evaluation.target_piece_color),
                "piece_count_distractor_count": int(axes.distractor_count),
                "marked_coord": None if evaluation.marked_coord is None else [int(evaluation.marked_coord[0]), int(evaluation.marked_coord[1])],
                "target_coord": None if evaluation.target_coord is None else [int(evaluation.target_coord[0]), int(evaluation.target_coord[1])],
                "marked_piece": None if evaluation.marked_piece is None else {"color": evaluation.marked_piece.color, "kind": evaluation.marked_piece.kind},
                "destination_coords": [[int(row), int(col)] for row, col in evaluation.destination_coords],
                "capture_coords": [[int(row), int(col)] for row, col in evaluation.capture_coords],
                "attacker_coords": [[int(row), int(col)] for row, col in evaluation.attacker_coords],
                "blocker_coords": [[int(row), int(col)] for row, col in evaluation.blocker_coords],
                "annotation_kind": str(evaluation.annotation_kind),
                "annotation_coords": [[int(row), int(col)] for row, col in evaluation.annotation_coords],
                "annotation_entity_ids": [str(entity_id) for entity_id in evaluation.annotation_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in evaluation.annotation_entity_ids],
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
            scene_id="chess",
            query_id=str(axes.query_id),
        )


def _build_checkmate_prompt_json_examples() -> Tuple[str, str]:
    """Return deterministic JSON examples for the checkmate move task."""

    annotation_value = {
        "from": [392, 318, 466, 392],
        "to": [392, 244, 466, 318],
        "king": [466, 170, 540, 244],
    }
    answer_value = "C"
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


@register_task
class GamesChessCheckmateMoveLabelTask:
    """Select the encoded move option that gives immediate checkmate."""

    task_id = CHECKMATE_TASK_ID
    domain = "games"
    task_group = "chess"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        sample: _CheckmateSample | None = None
        axes_meta: Dict[str, Any] = {}
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{CHECKMATE_TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample, axes_meta = _sample_checkmate_scene(
                    instance_seed=int(instance_seed) + int(attempt_index),
                    rng=attempt_rng,
                    params=params,
                )
            except ValueError:
                continue
            break
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        render_param_source = dict(params)
        render_param_source.setdefault(
            "max_board_size_px",
            group_default(_RENDER_DEFAULTS, "checkmate_max_board_size_px", 640),
        )
        render_param_source.setdefault(
            "board_frame_width_px",
            group_default(_RENDER_DEFAULTS, "checkmate_board_frame_width_px", 28),
        )
        render_param_source.setdefault(
            "option_panel_height_px",
            group_default(_RENDER_DEFAULTS, "checkmate_option_panel_height_px", 154),
        )
        render_param_source.setdefault(
            "option_panel_gap_px",
            group_default(_RENDER_DEFAULTS, "checkmate_option_panel_gap_px", 18),
        )
        render_param_source.setdefault(
            "option_panel_font_size_px",
            group_default(_RENDER_DEFAULTS, "checkmate_option_panel_font_size_px", 18),
        )
        render_param_source.setdefault(
            "coordinate_label_font_size_px",
            group_default(_RENDER_DEFAULTS, "checkmate_coordinate_label_font_size_px", 18),
        )
        render_param_source.setdefault(
            "canvas_min_width_px",
            max(
                780,
                int(
                    group_default(
                        _RENDER_DEFAULTS,
                        "canvas_min_width_px",
                        _DEFAULTS.canvas_min_width_px,
                    )
                ),
            ),
        )
        render_params = _render_params(render_param_source, instance_seed=int(instance_seed))
        render_params = replace(
            render_params,
            option_panel_height_px=max(132, int(render_params.option_panel_height_px)),
            board_frame_width_px=max(6, int(render_params.board_frame_width_px)),
            coordinate_label_font_size_px=max(14, int(render_params.coordinate_label_font_size_px)),
            option_panel_gap_px=max(42, int(render_params.option_panel_gap_px)),
            option_panel_font_size_px=max(16, int(render_params.option_panel_font_size_px)),
        )

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
            namespace="games.chess_checkmate.panel_scene_style",
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
        rendered_scene = render_chess_board_scene(
            board=sample.board,
            background=background,
            scene_variant=str(sample.scene_variant),
            style_variant=str(sample.style_variant),
            badge_text=f"{color_name(sample.player_color)} to move",
            marked_coord=None,
            params=render_params,
            target_coord=None,
            panel_style=panel_style,
            show_coordinates=True,
            move_options=tuple({"label": option.label, "text": option.text} for option in sample.options),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        cell_bboxes = rendered_scene.render_map["cell_bboxes_px"]
        annotation_map = {
            "from": list(cell_bboxes[coord_to_cell_id(sample.correct_option.source)]),
            "to": list(cell_bboxes[coord_to_cell_id(sample.correct_option.destination)]),
            "king": list(cell_bboxes[coord_to_cell_id(sample.defender_king_coord)]),
        }
        correct_move_board = apply_chess_move(sample.board, sample.correct_option.source, sample.correct_option.destination)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_checkmate_board",
                "standard_rule_text",
                "coordinate_rule_text",
                "checkmate_rule_text",
                "answer_hint_checkmate_move_label",
                "annotation_hint_checkmate_move_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_checkmate_prompt_json_examples()
        answer_hint = str(prompt_defaults["answer_hint_checkmate_move_label"]).format(
            option_labels=", ".join(sample.option_label_support)
        )
        annotation_hint = str(prompt_defaults["annotation_hint_checkmate_move_label"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=CHECKMATE_QUERY_ID,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_checkmate_board"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(answer_hint),
                "annotation_hint": str(annotation_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "standard_rule_text": str(prompt_defaults["standard_rule_text"]),
                "coordinate_rule_text": str(prompt_defaults["coordinate_rule_text"]),
                "checkmate_rule_text": str(prompt_defaults["checkmate_rule_text"]),
                "player_color_name": str(color_name(sample.player_color)),
                "defender_color_name": str(color_name(sample.defender_color)),
                "option_labels": ", ".join(sample.option_label_support),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(sample.correct_option.label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(key): list(value) for key, value in annotation_map.items()})
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
            "piece_symbol_font_family": "system_fallback",
        }
        complexity = build_games_chess_board_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(sample.scene_variant),
            query_id=CHECKMATE_QUERY_ID,
            occupied_count=int(sample.occupied_count),
            target_answer=int(sample.option_count),
            annotation_count=len(annotation_map),
        )

        move_options_trace = [
            {
                "label": str(option.label),
                "text": str(option.text),
                "source_coord": [int(option.source[0]), int(option.source[1])],
                "destination_coord": [int(option.destination[0]), int(option.destination[1])],
                "source_square": coord_to_square_name(option.source),
                "destination_square": coord_to_square_name(option.destination),
                "piece": {"color": str(option.piece.color), "kind": str(option.piece.kind)},
                "is_checkmate": bool(move_checkmates(sample.board, option.source, option.destination)),
            }
            for option in sample.options
        ]

        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_chess_board_checkmate_options",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": CHECKMATE_QUERY_ID,
                    "style_variant": str(sample.style_variant),
                    "board_size": int(BOARD_SIZE),
                    "player_color": str(sample.player_color),
                    "defender_color": str(sample.defender_color),
                    "answer_option_label": str(sample.correct_option.label),
                    "option_labels": [str(label) for label in sample.option_label_support],
                    "annotation_keys": list(annotation_map.keys()),
                },
            },
            "query_spec": {
                "query_id": CHECKMATE_QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": CHECKMATE_QUERY_ID,
                    "style_variant": str(sample.style_variant),
                    "scene_variant_probabilities": dict(axes_meta.get("scene_variant_probabilities", {})),
                    "style_variant_probabilities": dict(axes_meta.get("style_variant_probabilities", {})),
                    "player_color": str(sample.player_color),
                    "player_color_probabilities": dict(axes_meta.get("player_color_probabilities", {})),
                    "option_count": int(sample.option_count),
                    "option_count_probabilities": dict(axes_meta.get("option_count_probabilities", {})),
                    "answer_option_label": str(sample.correct_option.label),
                    "answer_support": [str(label) for label in sample.option_label_support],
                    "answer_label_probabilities": dict(axes_meta.get("answer_label_probabilities", {})),
                    "mirror_columns": bool(axes_meta.get("mirror_columns", False)),
                },
            },
            "render_spec": {
                "scene_variant": str(sample.scene_variant),
                "style_variant": str(sample.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
                "effective_cell_size_px": rendered_scene.render_map.get("effective_cell_size_px"),
                "show_coordinates": True,
                "option_count": int(sample.option_count),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(sample.scene_variant),
                "query_id": CHECKMATE_QUERY_ID,
                "style_variant": str(sample.style_variant),
                "board_size": int(BOARD_SIZE),
                "board_rows": serialize_board(sample.board),
                "result_board_rows": serialize_board(correct_move_board),
                "construction_mode": str(sample.construction_mode),
                "occupied_count": int(sample.occupied_count),
                "player_color": str(sample.player_color),
                "defender_color": str(sample.defender_color),
                "defender_king_coord": [int(sample.defender_king_coord[0]), int(sample.defender_king_coord[1])],
                "correct_source_coord": [int(sample.correct_option.source[0]), int(sample.correct_option.source[1])],
                "correct_destination_coord": [
                    int(sample.correct_option.destination[0]),
                    int(sample.correct_option.destination[1]),
                ],
                "correct_source_square": coord_to_square_name(sample.correct_option.source),
                "correct_destination_square": coord_to_square_name(sample.correct_option.destination),
                "answer_option_label": str(sample.correct_option.label),
                "answer_support": [str(label) for label in sample.option_label_support],
                "move_options": move_options_trace,
                "annotation_kind": "keyed_bbox_map",
                "annotation_keys": list(annotation_map.keys()),
                "annotation_cell_ids": {
                    "from": coord_to_cell_id(sample.correct_option.source),
                    "to": coord_to_cell_id(sample.correct_option.destination),
                    "king": coord_to_cell_id(sample.defender_king_coord),
                },
            },
            "witness_symbolic": {
                "type": "object_map",
                "ids": {
                    "from": coord_to_cell_id(sample.correct_option.source),
                    "to": coord_to_cell_id(sample.correct_option.destination),
                    "king": coord_to_cell_id(sample.defender_king_coord),
                },
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": {str(key): list(value) for key, value in annotation_map.items()},
                "pixel_keyed_bbox_map": {str(key): list(value) for key, value in annotation_map.items()},
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
            scene_id="chess",
            query_id=CHECKMATE_QUERY_ID,
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
class GamesChessTargetSquareAttackerCountTask(QuerySubsetTaskMixin, GamesChessBoardTask):
    """Count pieces of one side attacking the marked target square."""

    task_id = "task_games__chess__target_square_attacker_count"
    supported_query_ids = TARGET_SQUARE_ATTACKER_QUERY_IDS


@register_task
class GamesChessMarkedPieceBlockerCountTask(QuerySubsetTaskMixin, GamesChessBoardTask):
    """Count pieces between a marked slider and a marked target square."""

    task_id = "task_games__chess__marked_piece_blocker_count"
    supported_query_ids = MARKED_PIECE_BLOCKER_QUERY_IDS


@register_task
class GamesChessKingEscapeSquareCountTask(FixedQueryVariantTaskMixin, GamesChessBoardTask):
    """Count safe one-step escape squares for the marked king."""

    task_id = "task_games__chess__king_escape_square_count"
    fixed_query_id = "king_escape_square_count"


@register_task
class GamesChessPieceKindCountTask(QuerySubsetTaskMixin, GamesChessBoardTask):
    """Count visible chess pieces matching a sampled piece kind."""

    task_id = "task_games__chess__piece_kind_count"
    supported_query_ids = ("piece_kind_count",)


@register_task
class GamesChessColoredPieceKindCountTask(QuerySubsetTaskMixin, GamesChessBoardTask):
    """Count visible chess pieces matching a sampled color and piece kind."""

    task_id = "task_games__chess__colored_piece_kind_count"
    supported_query_ids = ("colored_piece_kind_count",)


__all__ = [
    "GamesChessBoardTask",
    "GamesChessCheckmateMoveLabelTask",
    "GamesChessColoredPieceKindCountTask",
    "GamesChessKingEscapeSquareCountTask",
    "GamesChessMarkedPieceBlockerCountTask",
    "GamesChessMarkedPieceDestinationCountTask",
    "GamesChessPieceKindCountTask",
    "GamesChessPlayerCapturePieceCountTask",
    "GamesChessTargetSquareAttackerCountTask",
]
