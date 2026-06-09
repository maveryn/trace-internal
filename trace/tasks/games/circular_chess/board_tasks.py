"""Circular Chess movement tasks for the games domain."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.chess_common import (
    BLACK,
    CIRCULAR_CHESS_MATERIAL_CAPS,
    WHITE,
    ChessPiece,
    color_name,
    material_count,
    opponent,
    sample_material_piece,
    validate_circular_chess_material,
)
from ..shared.chess_scene import draw_chess_piece_symbol
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
from ..shared.fixed_query_task import QuerySubsetTaskMixin
from ..shared.layout import apply_games_layout_jitter_to_bbox, attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import GamePanelSceneStyle, draw_panel_scene_chrome, game_panel_scene_style_metadata, make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import build_games_chess_theme
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_circular_chess_board_base"
TASK_GROUP = "circular_chess"
SCENE_ID = "circular_chess"
RING_COUNT = 4
SECTOR_COUNT = 16
MARKED_DESTINATION_TASK_ID = "task_games__circular_chess__marked_piece_destination_count"
TARGET_REACHER_TASK_ID = "task_games__circular_chess__target_cell_reacher_count"
MARKED_MOVE_QUERY_ID = "marked_piece_move_count"
MARKED_CAPTURE_QUERY_ID = "marked_piece_capture_count"
WHITE_REACHER_QUERY_ID = "white_piece_reaches_target_count"
BLACK_REACHER_QUERY_ID = "black_piece_reaches_target_count"

Coord = Tuple[int, int]
Board = Tuple[Tuple[ChessPiece | None, ...], ...]

SUPPORTED_MARKED_QUERY_IDS: Tuple[str, ...] = (MARKED_MOVE_QUERY_ID, MARKED_CAPTURE_QUERY_ID)
SUPPORTED_REACHER_QUERY_IDS: Tuple[str, ...] = (WHITE_REACHER_QUERY_ID, BLACK_REACHER_QUERY_ID)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (*SUPPORTED_MARKED_QUERY_IDS, *SUPPORTED_REACHER_QUERY_IDS)
SUPPORTED_PIECE_KINDS: Tuple[str, ...] = ("king", "queen", "rook", "bishop", "knight")
SUPPORTED_NON_KING_PIECE_KINDS: Tuple[str, ...] = ("queen", "rook", "bishop", "knight")
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("sparse_board", "crowded_board")
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = ("classic_ring", "slate_ring", "parchment_ring", "emerald_ring", "monochrome_ring")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Circular Chess scenes."""

    marked_piece_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8)
    marked_piece_capture_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    white_piece_reaches_target_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    black_piece_reaches_target_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    sparse_min_occupied_count: int = 8
    sparse_max_occupied_count: int = 13
    crowded_min_occupied_count: int = 14
    crowded_max_occupied_count: int = 22
    canvas_width: int = 900
    canvas_height: int = 900
    panel_margin_px: int = 48
    max_board_size_px: int = 700
    board_frame_width_px: int = 8
    cell_outline_width_px: int = 2
    piece_font_size_px: int = 56
    piece_bbox_fraction: float = 0.72
    marker_width_px: int = 5
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 620
    canvas_min_height_px: int = 620
    canvas_side_padding_px: int = 150
    canvas_vertical_padding_px: int = 150


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Circular Chess instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    marked_piece_kind: str
    marked_piece_color: str
    target_color: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    piece_kind_probabilities: Dict[str, float]
    marked_piece_color_probabilities: Dict[str, float]
    target_color_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderParams:
    """Resolved rendering controls."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    max_board_size_px: int
    board_frame_width_px: int
    cell_outline_width_px: int
    piece_font_size_px: int
    piece_bbox_fraction: float
    marker_width_px: int
    layout_jitter_meta: Dict[str, Any]
    font_family: str = ""


@dataclass(frozen=True)
class _CircularChessTheme:
    """Visual palette for one circular chess board."""

    frame_rgb: Tuple[int, int, int]
    inner_hole_rgb: Tuple[int, int, int]
    light_cell_rgb: Tuple[int, int, int]
    dark_cell_rgb: Tuple[int, int, int]
    outline_rgb: Tuple[int, int, int]
    marked_rgb: Tuple[int, int, int]
    target_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]
    chess_style: str


@dataclass(frozen=True)
class _RenderedCircularChessScene:
    """Rendered image plus trace-friendly scene metadata."""

    image: Image.Image
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


@dataclass(frozen=True)
class _Evaluation:
    """Evaluated answer/annotation payload for one query."""

    answer: int
    annotation_coords: Tuple[Coord, ...]
    annotation_entity_ids: Tuple[str, ...]
    annotation_kind: str
    marked_coord: Coord | None = None
    marked_piece: ChessPiece | None = None
    target_coord: Coord | None = None
    target_color: str = ""


@dataclass(frozen=True)
class _Sample:
    """One generated Circular Chess sample."""

    board: Board
    evaluation: _Evaluation
    occupied_count: int
    construction_mode: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def circular_coord_to_cell_id(coord: Coord) -> str:
    """Return a stable id for one circular chess cell."""

    return f"cell_ring{int(coord[0])}_sector{int(coord[1])}"


def circular_piece_to_entity_id(coord: Coord, piece: ChessPiece) -> str:
    """Return a stable id for one circular chess piece."""

    return f"piece_{piece.color}_{piece.kind}_ring{int(coord[0])}_sector{int(coord[1])}"


def in_circular_bounds(ring: int, sector: int) -> bool:
    """Return whether one ring/sector coordinate is on the circular board."""

    return 0 <= int(ring) < RING_COUNT and 0 <= int(sector) < SECTOR_COUNT


def all_coords() -> Tuple[Coord, ...]:
    """Return all circular board cells."""

    return tuple((ring, sector) for ring in range(RING_COUNT) for sector in range(SECTOR_COUNT))


def empty_board() -> Board:
    """Return an empty Circular Chess board."""

    return tuple(tuple(None for _ in range(SECTOR_COUNT)) for _ in range(RING_COUNT))


def freeze_board(board: Sequence[Sequence[ChessPiece | None]]) -> Board:
    """Freeze one mutable board into the canonical tuple representation."""

    return tuple(tuple(cell for cell in row) for row in board)


def serialize_board(board: Board) -> List[List[str | None]]:
    """Return a JSON-friendly board state."""

    return [[None if piece is None else f"{piece.color}_{piece.kind}" for piece in row] for row in board]


def occupied_coords(board: Board) -> Tuple[Coord, ...]:
    """Return occupied circular board coordinates."""

    return tuple(coord for coord in all_coords() if board[int(coord[0])][int(coord[1])] is not None)


def _theme(style_variant: str) -> _CircularChessTheme:
    """Return one resolved Circular Chess theme."""

    variant = str(style_variant)
    if variant == "slate_ring":
        return _CircularChessTheme((42, 48, 58), (230, 235, 238), (214, 221, 229), (105, 124, 145), (38, 45, 54), (218, 54, 62), (50, 111, 214), (24, 29, 36), "charcoal")
    if variant == "parchment_ring":
        return _CircularChessTheme((119, 86, 52), (248, 240, 219), (242, 218, 170), (172, 124, 78), (96, 68, 42), (204, 45, 48), (42, 95, 178), (46, 32, 20), "classic")
    if variant == "emerald_ring":
        return _CircularChessTheme((24, 91, 74), (225, 241, 233), (205, 231, 218), (62, 150, 121), (21, 75, 62), (216, 47, 57), (36, 99, 208), (20, 48, 42), "soft")
    if variant == "monochrome_ring":
        return _CircularChessTheme((34, 34, 38), (246, 246, 244), (230, 230, 226), (132, 134, 138), (48, 50, 54), (210, 44, 54), (40, 88, 190), (24, 24, 26), "monochrome_glyph")
    return _CircularChessTheme((56, 73, 122), (239, 244, 250), (222, 232, 244), (118, 150, 194), (52, 68, 104), (220, 56, 62), (42, 98, 204), (26, 34, 50), "classic")


def _sector_polygon(
    *,
    center: Tuple[float, float],
    inner_radius: float,
    outer_radius: float,
    sector: int,
    segments: int = 8,
) -> Tuple[Tuple[float, float], ...]:
    """Return a polygon approximating one annular board sector."""

    start = -90.0 + (360.0 * float(sector) / float(SECTOR_COUNT))
    end = -90.0 + (360.0 * float(sector + 1) / float(SECTOR_COUNT))
    outer_points: List[Tuple[float, float]] = []
    inner_points: List[Tuple[float, float]] = []
    for index in range(int(segments) + 1):
        angle = math.radians(start + ((end - start) * float(index) / float(segments)))
        outer_points.append((center[0] + (outer_radius * math.cos(angle)), center[1] + (outer_radius * math.sin(angle))))
    for index in range(int(segments), -1, -1):
        angle = math.radians(start + ((end - start) * float(index) / float(segments)))
        inner_points.append((center[0] + (inner_radius * math.cos(angle)), center[1] + (inner_radius * math.sin(angle))))
    return tuple((round(float(x), 3), round(float(y), 3)) for x, y in [*outer_points, *inner_points])


def _coord_center(
    *,
    center: Tuple[float, float],
    inner_radius: float,
    ring_width: float,
    coord: Coord,
) -> Tuple[float, float]:
    """Return the pixel center of one circular board cell."""

    ring, sector = int(coord[0]), int(coord[1])
    radius = float(inner_radius + ((ring + 0.5) * ring_width))
    angle = math.radians(-90.0 + (360.0 * (float(sector) + 0.5) / float(SECTOR_COUNT)))
    return (round(float(center[0] + (radius * math.cos(angle))), 3), round(float(center[1] + (radius * math.sin(angle))), 3))


def _piece_bbox(center: Tuple[float, float], *, size_px: float) -> Tuple[float, float, float, float]:
    half = 0.5 * float(size_px)
    return (
        round(float(center[0] - half), 3),
        round(float(center[1] - half), 3),
        round(float(center[0] + half), 3),
        round(float(center[1] + half), 3),
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
    """Resolve one balanced named Circular Chess axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(value) for value in supported),
    )


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced internal query id."""

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


def _movement_units_for_piece(kind: str, coord: Coord) -> Tuple[Tuple[Coord, ...], ...]:
    """Return independent movement rays/jumps for a piece on an empty circular board."""

    ring, sector = int(coord[0]), int(coord[1])
    kind_text = str(kind)
    if kind_text == "knight":
        units = []
        for dr, ds in ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)):
            target_ring = int(ring + dr)
            if not 0 <= int(target_ring) < RING_COUNT:
                continue
            units.append(((int(target_ring), int((sector + ds) % SECTOR_COUNT)),))
        return tuple(sorted(set(units)))
    directions: Tuple[Tuple[int, int], ...]
    max_steps = SECTOR_COUNT - 1
    if kind_text == "rook":
        directions = ((-1, 0), (1, 0), (0, -1), (0, 1))
    elif kind_text == "bishop":
        directions = ((-1, -1), (-1, 1), (1, -1), (1, 1))
    elif kind_text == "queen":
        directions = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    elif kind_text == "king":
        directions = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
        max_steps = 1
    else:
        raise ValueError(f"unsupported Circular Chess piece kind: {kind}")

    units: List[Tuple[Coord, ...]] = []
    for dr, ds in directions:
        ray: List[Coord] = []
        for step in range(1, int(max_steps) + 1):
            next_ring = int(ring + (int(dr) * step))
            if not 0 <= int(next_ring) < RING_COUNT:
                break
            next_sector = int((sector + (int(ds) * step)) % SECTOR_COUNT)
            ray.append((int(next_ring), int(next_sector)))
            if int(dr) == 0 and int(step) >= SECTOR_COUNT - 1:
                break
        if ray:
            units.append(tuple(ray))
    return tuple(units)


def legal_destinations(board: Board, coord: Coord) -> Tuple[Coord, ...]:
    """Return pseudo-legal destinations for one Circular Chess piece."""

    piece = board[int(coord[0])][int(coord[1])]
    if piece is None:
        return tuple()
    destinations: List[Coord] = []
    for unit in _movement_units_for_piece(str(piece.kind), coord):
        for target in unit:
            occupant = board[int(target[0])][int(target[1])]
            if occupant is None:
                destinations.append(tuple(target))
                continue
            if str(occupant.color) != str(piece.color):
                destinations.append(tuple(target))
            break
    return tuple(sorted(set(destinations)))


def capture_destinations(board: Board, coord: Coord) -> Tuple[Coord, ...]:
    """Return opponent-occupied legal destinations for one piece."""

    piece = board[int(coord[0])][int(coord[1])]
    if piece is None:
        return tuple()
    return tuple(
        coord
        for coord in legal_destinations(board, coord)
        if board[int(coord[0])][int(coord[1])] is not None
        and str(board[int(coord[0])][int(coord[1])].color) != str(piece.color)
    )


def target_reachers(board: Board, *, target_coord: Coord, target_color: str) -> Tuple[Coord, ...]:
    """Return source pieces of `target_color` that can move to `target_coord`."""

    coords: List[Coord] = []
    for coord in occupied_coords(board):
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None or str(piece.color) != str(target_color):
            continue
        if tuple(target_coord) in legal_destinations(board, coord):
            coords.append(tuple(coord))
    return tuple(sorted(coords))


def _target_support_key(query_id: str) -> str:
    return {
        MARKED_MOVE_QUERY_ID: "marked_piece_move_count_support",
        MARKED_CAPTURE_QUERY_ID: "marked_piece_capture_count_support",
        WHITE_REACHER_QUERY_ID: "white_piece_reaches_target_count_support",
        BLACK_REACHER_QUERY_ID: "black_piece_reaches_target_count_support",
    }[str(query_id)]


def _target_support_fallback(query_id: str) -> Tuple[int, ...]:
    return tuple(int(v) for v in getattr(_DEFAULTS, _target_support_key(str(query_id))))


def _max_possible_answer(query_id: str, piece_kind: str) -> int:
    if str(query_id) in SUPPORTED_REACHER_QUERY_IDS:
        return 6
    origin = (1, 0)
    units = _movement_units_for_piece(str(piece_kind), origin)
    if str(query_id) == MARKED_CAPTURE_QUERY_ID:
        return min(6, sum(1 for unit in units if unit))
    return min(8, sum(len(unit) for unit in units))


def _resolve_color_axis(*, instance_seed: int, params: Mapping[str, Any], namespace: str, explicit_key: str) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=f"{str(explicit_key)}_weights",
        balance_flag_key=f"balanced_{str(explicit_key)}_sampling",
        supported=(WHITE, BLACK),
    )
    return str(selected), dict(probabilities)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_STYLE_VARIANTS,
    )
    piece_kind, piece_kind_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="marked_piece_kind",
        explicit_key="marked_piece_kind",
        weights_key="marked_piece_kind_weights",
        balance_flag_key="balanced_marked_piece_kind_sampling",
        supported=SUPPORTED_PIECE_KINDS,
    )
    marked_piece_color, marked_color_probabilities = _resolve_color_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="marked_piece_color",
        explicit_key="marked_piece_color",
    )
    target_color = WHITE if str(query_id) == WHITE_REACHER_QUERY_ID else BLACK
    target_color_probabilities = {WHITE: 1.0 if str(target_color) == WHITE else 0.0, BLACK: 1.0 if str(target_color) == BLACK else 0.0}
    if str(query_id) not in SUPPORTED_REACHER_QUERY_IDS:
        target_color, target_color_probabilities = _resolve_color_axis(
            instance_seed=int(instance_seed),
            params=params,
            namespace="target_color",
            explicit_key="target_color",
        )

    support_key = _target_support_key(str(query_id))
    configured_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=support_key,
        fallback=_target_support_fallback(str(query_id)),
    )
    possible_max = _max_possible_answer(str(query_id), str(piece_kind))
    target_support = tuple(int(value) for value in configured_support if int(value) <= int(possible_max))
    if not target_support:
        target_support = tuple(int(value) for value in _target_support_fallback(str(query_id)) if int(value) <= int(possible_max))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults={**dict(_GEN_DEFAULTS), support_key: list(target_support)},
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=target_support,
        namespace=f"{TASK_ID}.{str(query_id)}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        marked_piece_kind=str(piece_kind),
        marked_piece_color=str(marked_piece_color),
        target_color=str(target_color),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        piece_kind_probabilities=dict(piece_kind_probabilities),
        marked_piece_color_probabilities=dict(marked_color_probabilities),
        target_color_probabilities=dict(target_color_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.circular_chess.text_font",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.circular_chess.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.circular_chess.layout",
        ),
        unit_scale_meta,
    )
    max_board_size_px = scale_games_px(
        params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)),
        unit_scale,
        min_px=360,
    )
    dynamic_canvas_enabled = bool(params.get("dynamic_canvas_size_enabled", group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", _DEFAULTS.dynamic_canvas_size_enabled)))
    base_canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    base_canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    canvas_width = int(base_canvas_width)
    canvas_height = int(base_canvas_height)
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        canvas_width = min(
            int(base_canvas_width),
            max(
                int(params.get("canvas_min_width_px", group_default(_RENDER_DEFAULTS, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px))),
                int(round(float(max_board_size_px) + (2.0 * float(params.get("canvas_side_padding_px", group_default(_RENDER_DEFAULTS, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px)))))),
            ),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        canvas_height = min(
            int(base_canvas_height),
            max(
                int(params.get("canvas_min_height_px", group_default(_RENDER_DEFAULTS, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px))),
                int(round(float(max_board_size_px) + (2.0 * float(params.get("canvas_vertical_padding_px", group_default(_RENDER_DEFAULTS, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px)))))),
            ),
        )
    return _RenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_size_px=int(max_board_size_px),
        board_frame_width_px=scale_games_px(params.get("board_frame_width_px", group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px)), unit_scale, min_px=4),
        cell_outline_width_px=scale_games_px(params.get("cell_outline_width_px", group_default(_RENDER_DEFAULTS, "cell_outline_width_px", _DEFAULTS.cell_outline_width_px)), unit_scale, min_px=1),
        piece_font_size_px=scale_games_px(params.get("piece_font_size_px", group_default(_RENDER_DEFAULTS, "piece_font_size_px", _DEFAULTS.piece_font_size_px)), unit_scale, min_px=34),
        piece_bbox_fraction=float(params.get("piece_bbox_fraction", group_default(_RENDER_DEFAULTS, "piece_bbox_fraction", _DEFAULTS.piece_bbox_fraction))),
        marker_width_px=scale_games_px(params.get("marker_width_px", group_default(_RENDER_DEFAULTS, "marker_width_px", _DEFAULTS.marker_width_px)), unit_scale, min_px=3),
        layout_jitter_meta=dict(layout_jitter),
        font_family=str(font_family),
    )


def _occupancy_bounds(scene_variant: str) -> Tuple[int, int]:
    if str(scene_variant) == "crowded_board":
        return int(_DEFAULTS.crowded_min_occupied_count), int(_DEFAULTS.crowded_max_occupied_count)
    return int(_DEFAULTS.sparse_min_occupied_count), int(_DEFAULTS.sparse_max_occupied_count)


def _opposite_color(color: str) -> str:
    return opponent(str(color))


def _place_circular_piece(
    *,
    rng,
    mutable: list[list[ChessPiece | None]],
    coord: Coord,
    color: str | None = None,
    kinds: Sequence[str] = SUPPORTED_PIECE_KINDS,
) -> bool:
    """Place one material-capped piece on a circular chess cell."""

    ring, sector = int(coord[0]), int(coord[1])
    if mutable[ring][sector] is not None:
        return False
    colors = (str(color),) if color is not None else (WHITE, BLACK)
    piece = sample_material_piece(
        rng,
        freeze_board(mutable),
        colors=colors,
        kinds=kinds,
        caps=CIRCULAR_CHESS_MATERIAL_CAPS,
    )
    if piece is None:
        return False
    mutable[ring][sector] = piece
    return True


def _place_circular_exact_piece(
    *,
    mutable: list[list[ChessPiece | None]],
    coord: Coord,
    piece: ChessPiece,
) -> bool:
    """Place an exact circular chess piece if material caps allow it."""

    ring, sector = int(coord[0]), int(coord[1])
    if mutable[ring][sector] is not None:
        return False
    candidate = [list(row) for row in mutable]
    candidate[ring][sector] = piece
    if not validate_circular_chess_material(freeze_board(candidate)):
        return False
    mutable[ring][sector] = piece
    return True


def _circular_kings_valid(board: Board) -> bool:
    """Return whether the circular board has exactly one king per color."""

    return material_count(board, color=WHITE, kind="king") == 1 and material_count(board, color=BLACK, kind="king") == 1


def _missing_circular_king_count(board: Board) -> int:
    """Return how many side kings still need to be added."""

    return sum(1 for color in (WHITE, BLACK) if material_count(board, color=str(color), kind="king") == 0)


def _evaluate_axes_board(
    *,
    board: Board,
    axes: _ResolvedAxes,
    marked_coord: Coord | None,
    target_coord: Coord | None,
) -> _Evaluation:
    """Evaluate a board under the active circular-chess query."""

    return _evaluate_query(
        board=board,
        query_id=str(axes.query_id),
        marked_coord=marked_coord,
        target_coord=target_coord,
        target_color=str(axes.target_color),
    )


def _add_required_kings_preserving(
    *,
    rng,
    board: Board,
    axes: _ResolvedAxes,
    marked_coord: Coord | None,
    target_coord: Coord | None,
) -> Board:
    """Add one king per color without changing the active answer."""

    mutable = [list(row) for row in board]
    for color in (WHITE, BLACK):
        if material_count(freeze_board(mutable), color=str(color), kind="king") >= 1:
            continue
        candidates = [
            coord
            for coord in all_coords()
            if mutable[int(coord[0])][int(coord[1])] is None and (target_coord is None or tuple(coord) != tuple(target_coord))
        ]
        rng.shuffle(candidates)
        placed = False
        for coord in candidates:
            if not _place_circular_exact_piece(
                mutable=mutable,
                coord=coord,
                piece=ChessPiece(str(color), "king"),
            ):
                continue
            candidate_board = freeze_board(mutable)
            evaluation = _evaluate_axes_board(
                board=candidate_board,
                axes=axes,
                marked_coord=marked_coord,
                target_coord=target_coord,
            )
            if int(evaluation.answer) != int(axes.target_answer):
                mutable[int(coord[0])][int(coord[1])] = None
                continue
            placed = True
            break
        if not placed:
            raise ValueError("failed to add required circular chess king without changing answer")
    final = freeze_board(mutable)
    if not validate_circular_chess_material(final) or not _circular_kings_valid(final):
        raise ValueError("circular chess board is not material-plausible")
    return final


def _allocate_move_destinations(units: Sequence[Sequence[Coord]], target_answer: int, rng) -> Tuple[Tuple[Coord, ...], Tuple[Coord, ...]]:
    """Choose exact legal destination cells and friendly blockers for a move-count target."""

    unit_list = [tuple(unit) for unit in units if unit]
    rng.shuffle(unit_list)
    desired: List[Coord] = []
    blockers: List[Coord] = []
    remaining = int(target_answer)
    for unit in unit_list:
        if int(remaining) <= 0:
            blockers.append(tuple(unit[0]))
            continue
        take = min(int(remaining), len(unit))
        desired.extend(tuple(coord) for coord in unit[:take])
        remaining -= int(take)
        if int(take) < len(unit):
            blockers.append(tuple(unit[int(take)]))
    if int(remaining) > 0:
        raise ValueError("target move count exceeds available Circular Chess movement cells")
    return tuple(sorted(set(desired))), tuple(sorted(set(blockers) - set(desired)))


def _construct_marked_sample(rng, *, axes: _ResolvedAxes) -> _Sample:
    target_answer = int(axes.target_answer)
    capture_query = str(axes.query_id) == MARKED_CAPTURE_QUERY_ID
    candidate_origins = list(all_coords())
    rng.shuffle(candidate_origins)
    for origin in candidate_origins:
        units = _movement_units_for_piece(str(axes.marked_piece_kind), origin)
        if capture_query:
            if int(target_answer) > sum(1 for unit in units if unit):
                continue
            unit_list = [tuple(unit) for unit in units if unit]
            rng.shuffle(unit_list)
            selected_units = tuple(unit_list[: int(target_answer)])
            desired = tuple(sorted(unit[0] for unit in selected_units))
            blockers = tuple(sorted(unit[0] for unit in unit_list[int(target_answer) :]))
        else:
            if int(target_answer) > sum(len(unit) for unit in units):
                continue
            desired, blockers = _allocate_move_destinations(units, target_answer, rng)

        mutable = [list(row) for row in empty_board()]
        marked_piece = ChessPiece(color=str(axes.marked_piece_color), kind=str(axes.marked_piece_kind))
        if not _place_circular_exact_piece(mutable=mutable, coord=origin, piece=marked_piece):
            continue
        for coord in desired:
            if capture_query:
                if not _place_circular_piece(
                    rng=rng,
                    mutable=mutable,
                    coord=coord,
                    color=_opposite_color(str(axes.marked_piece_color)),
                ):
                    raise ValueError("failed to place circular chess capture target")
        for coord in blockers:
            if mutable[int(coord[0])][int(coord[1])] is None:
                if not _place_circular_piece(
                    rng=rng,
                    mutable=mutable,
                    coord=coord,
                    color=str(axes.marked_piece_color),
                ):
                    raise ValueError("failed to place circular chess blocker")

        board = freeze_board(mutable)
        protected = {tuple(origin), *desired, *blockers}
        movement_cells = {coord for unit in units for coord in unit}
        minimum, maximum = _occupancy_bounds(str(axes.scene_variant))
        missing_kings = _missing_circular_king_count(board)
        target_occupied_max = max(len(occupied_coords(board)), min(int(maximum) - int(missing_kings), 26))
        target_occupied = int(rng.randint(max(int(minimum) - int(missing_kings), len(occupied_coords(board))), max(int(minimum), target_occupied_max)))
        available = [coord for coord in all_coords() if coord not in protected and coord not in movement_cells and board[int(coord[0])][int(coord[1])] is None]
        rng.shuffle(available)
        mutable = [list(row) for row in board]
        for coord in available:
            if len(occupied_coords(freeze_board(mutable))) >= int(target_occupied):
                break
            _place_circular_piece(
                rng=rng,
                mutable=mutable,
                coord=coord,
                kinds=SUPPORTED_NON_KING_PIECE_KINDS,
            )
        board = freeze_board(mutable)
        evaluation = _evaluate_query(board=board, query_id=str(axes.query_id), marked_coord=origin, target_coord=None, target_color=str(axes.target_color))
        if evaluation.answer == int(target_answer):
            return _Sample(
                board=board,
                evaluation=evaluation,
                occupied_count=len(occupied_coords(board)),
                construction_mode="constructed_marked_piece_exact_answer",
            )
    raise ValueError("failed to construct marked Circular Chess sample")


def _candidate_reacher_sources(target_coord: Coord) -> Tuple[Tuple[Coord, str], ...]:
    candidates: List[Tuple[Coord, str]] = []
    board_rows = [list(row) for row in empty_board()]
    for coord in all_coords():
        if tuple(coord) == tuple(target_coord):
            continue
        for kind in SUPPORTED_PIECE_KINDS:
            mutable = [list(row) for row in board_rows]
            mutable[int(coord[0])][int(coord[1])] = ChessPiece(color=WHITE, kind=str(kind))
            board = freeze_board(mutable)
            if tuple(target_coord) in legal_destinations(board, coord):
                candidates.append((tuple(coord), str(kind)))
    return tuple(candidates)


def _construct_reacher_sample(rng, *, axes: _ResolvedAxes) -> _Sample:
    target_answer = int(axes.target_answer)
    target_color = WHITE if str(axes.query_id) == WHITE_REACHER_QUERY_ID else BLACK
    target_coords = [(ring, sector) for ring in (1, 2) for sector in range(SECTOR_COUNT)]
    rng.shuffle(target_coords)
    for target_coord in target_coords:
        candidates = list(_candidate_reacher_sources(target_coord))
        rng.shuffle(candidates)
        mutable = [list(row) for row in empty_board()]
        selected: list[Tuple[Coord, str]] = []
        used_coords: set[Coord] = set()
        for coord, kind in candidates:
            if len(selected) >= int(target_answer):
                break
            if tuple(coord) in used_coords:
                continue
            if not _place_circular_exact_piece(
                mutable=mutable,
                coord=coord,
                piece=ChessPiece(color=str(target_color), kind=str(kind)),
            ):
                continue
            selected.append((tuple(coord), str(kind)))
            used_coords.add(tuple(coord))
        if len(selected) != int(target_answer):
            continue
        board = freeze_board(mutable)
        minimum, maximum = _occupancy_bounds(str(axes.scene_variant))
        missing_kings = _missing_circular_king_count(board)
        target_occupied_max = max(len(occupied_coords(board)), min(int(maximum) - int(missing_kings), 24))
        target_occupied = int(rng.randint(max(int(minimum) - int(missing_kings), len(occupied_coords(board))), max(int(minimum), target_occupied_max)))
        all_available = [coord for coord in all_coords() if tuple(coord) != tuple(target_coord) and board[int(coord[0])][int(coord[1])] is None]
        rng.shuffle(all_available)
        mutable = [list(row) for row in board]
        for coord in all_available:
            if len(occupied_coords(freeze_board(mutable))) >= int(target_occupied):
                break
            old = mutable[int(coord[0])][int(coord[1])]
            if not _place_circular_piece(
                rng=rng,
                mutable=mutable,
                coord=coord,
                kinds=SUPPORTED_NON_KING_PIECE_KINDS,
            ):
                continue
            candidate_board = freeze_board(mutable)
            evaluation = _evaluate_query(
                board=candidate_board,
                query_id=str(axes.query_id),
                marked_coord=None,
                target_coord=target_coord,
                target_color=str(target_color),
            )
            if evaluation.answer != int(target_answer):
                mutable[int(coord[0])][int(coord[1])] = old
        board = freeze_board(mutable)
        evaluation = _evaluate_query(
            board=board,
            query_id=str(axes.query_id),
            marked_coord=None,
            target_coord=target_coord,
            target_color=str(target_color),
        )
        if evaluation.answer == int(target_answer):
            return _Sample(
                board=board,
                evaluation=evaluation,
                occupied_count=len(occupied_coords(board)),
                construction_mode="constructed_target_reacher_exact_answer",
            )
    raise ValueError("failed to construct target-reacher Circular Chess sample")


def _evaluate_query(
    *,
    board: Board,
    query_id: str,
    marked_coord: Coord | None,
    target_coord: Coord | None,
    target_color: str,
) -> _Evaluation:
    if str(query_id) in SUPPORTED_MARKED_QUERY_IDS:
        if marked_coord is None:
            raise ValueError("marked query requires marked_coord")
        piece = board[int(marked_coord[0])][int(marked_coord[1])]
        if piece is None:
            raise ValueError("marked query requires a marked piece")
        if str(query_id) == MARKED_CAPTURE_QUERY_ID:
            coords = capture_destinations(board, marked_coord)
        else:
            coords = legal_destinations(board, marked_coord)
        return _Evaluation(
            answer=len(coords),
            annotation_coords=tuple(sorted(coords)),
            annotation_entity_ids=tuple(circular_coord_to_cell_id(coord) for coord in sorted(coords)),
            annotation_kind="destination_cell_centers",
            marked_coord=tuple(marked_coord),
            marked_piece=piece,
        )
    if target_coord is None:
        raise ValueError("target reacher query requires target_coord")
    coords = target_reachers(board, target_coord=target_coord, target_color=str(target_color))
    return _Evaluation(
        answer=len(coords),
        annotation_coords=tuple(sorted(coords)),
        annotation_entity_ids=tuple(circular_piece_to_entity_id(coord, board[int(coord[0])][int(coord[1])]) for coord in sorted(coords) if board[int(coord[0])][int(coord[1])] is not None),
        annotation_kind="source_piece_centers",
        target_coord=tuple(target_coord),
        target_color=str(target_color),
    )


def _sample_scene(*, rng, axes: _ResolvedAxes) -> _Sample:
    if str(axes.query_id) in SUPPORTED_MARKED_QUERY_IDS:
        sample = _construct_marked_sample(rng, axes=axes)
        board = _add_required_kings_preserving(
            rng=rng,
            board=sample.board,
            axes=axes,
            marked_coord=sample.evaluation.marked_coord,
            target_coord=None,
        )
        evaluation = _evaluate_axes_board(
            board=board,
            axes=axes,
            marked_coord=sample.evaluation.marked_coord,
            target_coord=None,
        )
        return _Sample(
            board=board,
            evaluation=evaluation,
            occupied_count=len(occupied_coords(board)),
            construction_mode=str(sample.construction_mode),
        )
    sample = _construct_reacher_sample(rng, axes=axes)
    board = _add_required_kings_preserving(
        rng=rng,
        board=sample.board,
        axes=axes,
        marked_coord=None,
        target_coord=sample.evaluation.target_coord,
    )
    evaluation = _evaluate_axes_board(
        board=board,
        axes=axes,
        marked_coord=None,
        target_coord=sample.evaluation.target_coord,
    )
    return _Sample(
        board=board,
        evaluation=evaluation,
        occupied_count=len(occupied_coords(board)),
        construction_mode=str(sample.construction_mode),
    )


def render_circular_chess_scene(
    *,
    board: Board,
    background: Image.Image,
    style_variant: str,
    params: _RenderParams,
    marked_coord: Coord | None,
    target_coord: Coord | None,
    panel_style: GamePanelSceneStyle | None,
) -> _RenderedCircularChessScene:
    """Render one circular chess board."""

    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    theme = _theme(str(style_variant))
    board_size = int(params.max_board_size_px)
    board_left = int(0.5 * (int(params.canvas_width) - board_size))
    board_top = int(0.5 * (int(params.canvas_height) - board_size))
    board_bbox = (float(board_left), float(board_top), float(board_left + board_size), float(board_top + board_size))
    _group_bbox, dx, dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=dict(params.layout_jitter_meta),
    )
    board_bbox = (
        round(float(board_bbox[0] + dx), 3),
        round(float(board_bbox[1] + dy), 3),
        round(float(board_bbox[2] + dx), 3),
        round(float(board_bbox[3] + dy), 3),
    )
    if panel_style is not None:
        pad = max(18, int(round(float(params.panel_margin_px) * 0.42)))
        panel_bbox = (
            max(4, int(round(board_bbox[0])) - pad),
            max(4, int(round(board_bbox[1])) - pad),
            min(int(params.canvas_width) - 4, int(round(board_bbox[2])) + pad),
            min(int(params.canvas_height) - 4, int(round(board_bbox[3])) + pad),
        )
        draw_panel_scene_chrome(
            draw,
            bbox=panel_bbox,
            style=panel_style,
            radius=30,
            border_width=max(2, int(round(float(params.board_frame_width_px) * 0.45))),
        )
    else:
        panel_bbox = None

    cx = float(0.5 * (board_bbox[0] + board_bbox[2]))
    cy = float(0.5 * (board_bbox[1] + board_bbox[3]))
    outer_radius = float(0.5 * (board_bbox[2] - board_bbox[0]))
    inner_radius = float(0.18 * outer_radius)
    ring_width = float((outer_radius - inner_radius) / float(RING_COUNT))
    center = (float(cx), float(cy))
    draw.ellipse(
        (cx - outer_radius - params.board_frame_width_px, cy - outer_radius - params.board_frame_width_px, cx + outer_radius + params.board_frame_width_px, cy + outer_radius + params.board_frame_width_px),
        fill=tuple(int(value) for value in theme.frame_rgb),
    )

    cell_centers: Dict[str, Tuple[float, float]] = {}
    cell_polygons: Dict[str, List[List[float]]] = {}
    scene_entities: List[Dict[str, Any]] = []
    for ring in range(RING_COUNT):
        inner = float(inner_radius + (ring * ring_width))
        outer = float(inner + ring_width)
        for sector in range(SECTOR_COUNT):
            coord = (int(ring), int(sector))
            cell_id = circular_coord_to_cell_id(coord)
            polygon = _sector_polygon(center=center, inner_radius=inner, outer_radius=outer, sector=int(sector))
            fill_rgb = theme.light_cell_rgb if (int(ring) + int(sector)) % 2 == 0 else theme.dark_cell_rgb
            draw.polygon(polygon, fill=tuple(int(value) for value in fill_rgb))
            draw.line([*polygon, polygon[0]], fill=tuple(int(value) for value in theme.outline_rgb), width=int(params.cell_outline_width_px))
            cell_center = _coord_center(center=center, inner_radius=inner_radius, ring_width=ring_width, coord=coord)
            cell_centers[str(cell_id)] = tuple(cell_center)
            cell_polygons[str(cell_id)] = [[float(x), float(y)] for x, y in polygon]
            occupant = board[int(ring)][int(sector)]
            scene_entities.append(
                {
                    "entity_id": str(cell_id),
                    "entity_type": "circular_chess_cell",
                    "ring": int(ring),
                    "sector": int(sector),
                    "occupant": None if occupant is None else f"{occupant.color}_{occupant.kind}",
                    "center_px": [float(cell_center[0]), float(cell_center[1])],
                    "polygon_px": [[float(x), float(y)] for x, y in polygon],
                }
            )

    draw.ellipse(
        (cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius),
        fill=tuple(int(value) for value in theme.inner_hole_rgb),
        outline=tuple(int(value) for value in theme.outline_rgb),
        width=int(params.cell_outline_width_px),
    )

    piece_centers: Dict[str, Tuple[float, float]] = {}
    piece_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    chess_theme = build_games_chess_theme(style_variant=str(theme.chess_style))
    piece_size = max(20.0, float(params.piece_bbox_fraction) * float(ring_width))
    for coord in occupied_coords(board):
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None:
            continue
        piece_id = circular_piece_to_entity_id(coord, piece)
        center_px = cell_centers[circular_coord_to_cell_id(coord)]
        bbox = _piece_bbox(center_px, size_px=piece_size)
        draw_chess_piece_symbol(draw, bbox_px=bbox, piece=piece, theme=chess_theme, font_size_px=int(params.piece_font_size_px))
        piece_centers[str(piece_id)] = tuple(center_px)
        piece_bboxes[str(piece_id)] = tuple(bbox)
        scene_entities.append(
            {
                "entity_id": str(piece_id),
                "entity_type": "circular_chess_piece",
                "ring": int(coord[0]),
                "sector": int(coord[1]),
                "color": str(piece.color),
                "kind": str(piece.kind),
                "center_px": [float(center_px[0]), float(center_px[1])],
                "bbox_px": [float(value) for value in bbox],
            }
        )

    marker_meta: Dict[str, Any] = {}
    if target_coord is not None:
        target_center = cell_centers[circular_coord_to_cell_id(target_coord)]
        radius = max(10.0, 0.33 * float(ring_width))
        bbox = (
            float(target_center[0] - radius),
            float(target_center[1] - radius),
            float(target_center[0] + radius),
            float(target_center[1] + radius),
        )
        draw.ellipse(bbox, outline=tuple(int(value) for value in theme.target_rgb), width=int(params.marker_width_px))
        marker_meta["target_cell_marker_bbox_px"] = [float(value) for value in bbox]
    if marked_coord is not None:
        marked_center = cell_centers[circular_coord_to_cell_id(marked_coord)]
        radius = max(11.0, 0.36 * float(ring_width))
        bbox = (
            float(marked_center[0] - radius),
            float(marked_center[1] - radius),
            float(marked_center[0] + radius),
            float(marked_center[1] + radius),
        )
        draw.ellipse(bbox, outline=tuple(int(value) for value in theme.marked_rgb), width=int(params.marker_width_px))
        marker_meta["marked_piece_marker_bbox_px"] = [float(value) for value in bbox]

    return _RenderedCircularChessScene(
        image=image,
        scene_entities=tuple(scene_entities),
        render_map={
            "board_bbox_px": [float(value) for value in board_bbox],
            "scene_panel_bbox_px": None if panel_bbox is None else [int(value) for value in panel_bbox],
            "cell_centers_px": {str(key): [float(value[0]), float(value[1])] for key, value in cell_centers.items()},
            "cell_polygons_px": dict(cell_polygons),
            "piece_centers_px": {str(key): [float(value[0]), float(value[1])] for key, value in piece_centers.items()},
            "piece_bboxes_px": {str(key): [float(v) for v in value] for key, value in piece_bboxes.items()},
            "layout_jitter": dict(layout_jitter),
            "panel_scene_style": None if panel_style is None else game_panel_scene_style_metadata(panel_style),
            "style_variant": str(style_variant),
            "effective_ring_width_px": float(ring_width),
            "font_family": str(params.font_family),
            **marker_meta,
        },
    )


def _build_complexity(*, task_id: str, axes: _ResolvedAxes, occupied_count: int, annotation_count: int) -> Any:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=str(task_id))
    visual_scan = normalize_linear(float(occupied_count), min_value=8.0, max_value=24.0)
    reasoning_base = 0.58 if str(axes.query_id) in SUPPORTED_REACHER_QUERY_IDS else 0.48
    if str(axes.marked_piece_kind) in {"queen", "rook"}:
        reasoning_base += 0.08
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": min(1.0, float(reasoning_base) + (0.05 * normalize_linear(float(axes.target_answer), min_value=0.0, max_value=8.0))),
            "ambiguity": normalize_linear(float(annotation_count), min_value=0.0, max_value=10.0),
            "output_burden": normalize_linear(float(annotation_count), min_value=0.0, max_value=10.0),
        },
    )


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    answer_value = 3
    annotation_value = [[420, 210], [502, 244], [536, 328]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesCircularChessBoardTask:
    """Base generator for circular chess movement/reacher queries."""

    task_id = TASK_ID
    domain = "games"
    task_group = TASK_GROUP

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        sample: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{self.task_id}.attempt.{int(attempt_index)}")
            try:
                sample = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid sample after {max_attempts} attempts")

        allowed_panel_treatments_raw = params.get("panel_scene_treatments", group_default(_RENDER_DEFAULTS, "panel_scene_treatments", None))
        if isinstance(allowed_panel_treatments_raw, str):
            allowed_panel_treatments = (str(allowed_panel_treatments_raw),)
        elif allowed_panel_treatments_raw is None:
            allowed_panel_treatments = None
        else:
            allowed_panel_treatments = tuple(str(item) for item in allowed_panel_treatments_raw)
        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.circular_chess.panel_scene_style",
            treatments=allowed_panel_treatments,
            treatment_weights=params.get("panel_scene_treatment_weights", group_default(_RENDER_DEFAULTS, "panel_scene_treatment_weights", None)),
            palette_weights=params.get("panel_scene_palette_weights", group_default(_RENDER_DEFAULTS, "panel_scene_palette_weights", None)),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered = render_circular_chess_scene(
            board=sample.board,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            marked_coord=sample.evaluation.marked_coord,
            target_coord=sample.evaluation.target_coord,
            panel_style=panel_style,
        )
        if sample.evaluation.annotation_kind == "source_piece_centers":
            annotation_points = [list(rendered.render_map["piece_centers_px"][str(entity_id)]) for entity_id in sample.evaluation.annotation_entity_ids]
        else:
            annotation_points = [list(rendered.render_map["cell_centers_px"][str(entity_id)]) for entity_id in sample.evaluation.annotation_entity_ids]
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
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
                "circular_board_rule_text",
                "piece_rule_text_marked",
                "piece_rule_text_mixed",
                "landing_rule_text",
                f"answer_hint_{str(axes.query_id)}",
                f"annotation_hint_{str(axes.query_id)}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        marked_piece_name = ""
        if sample.evaluation.marked_piece is not None:
            marked_piece_name = f"{color_name(sample.evaluation.marked_piece.color)} {sample.evaluation.marked_piece.kind}"
        slots = {
            "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
            "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "circular_board_rule_text": str(prompt_defaults["circular_board_rule_text"]),
            "piece_rule_text": str(prompt_defaults["piece_rule_text_mixed"] if str(axes.query_id) in SUPPORTED_REACHER_QUERY_IDS else prompt_defaults["piece_rule_text_marked"]),
            "landing_rule_text": str(prompt_defaults["landing_rule_text"]),
            "marked_piece_name": str(marked_piece_name),
            "target_color_name": str(color_name(axes.target_color)),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sample.evaluation.answer))
        annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        complexity = _build_complexity(
            task_id=str(self.task_id),
            axes=axes,
            occupied_count=int(sample.occupied_count),
            annotation_count=len(sample.evaluation.annotation_entity_ids),
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_circular_chess_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(axes.query_id),
                    "scene_variant": str(axes.scene_variant),
                    "style_variant": str(axes.style_variant),
                    "marked_piece_kind": str(axes.marked_piece_kind),
                    "target_answer": int(sample.evaluation.answer),
                    "annotation_entity_ids": [str(entity_id) for entity_id in sample.evaluation.annotation_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(axes.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(axes.query_id),
                    "scene_variant": str(axes.scene_variant),
                    "style_variant": str(axes.style_variant),
                    "marked_piece_kind": str(axes.marked_piece_kind),
                    "marked_piece_color": str(axes.marked_piece_color),
                    "target_color": str(axes.target_color),
                    "target_answer": int(sample.evaluation.answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "piece_kind_probabilities": dict(axes.piece_kind_probabilities),
                    "marked_piece_color_probabilities": dict(axes.marked_piece_color_probabilities),
                    "target_color_probabilities": dict(axes.target_color_probabilities),
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "occupied_count": int(sample.occupied_count),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
                "effective_ring_width_px": rendered.render_map.get("effective_ring_width_px"),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": str(axes.query_id),
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "board_rings": serialize_board(sample.board),
                "ring_count": int(RING_COUNT),
                "sector_count": int(SECTOR_COUNT),
                "occupied_count": int(sample.occupied_count),
                "construction_mode": str(sample.construction_mode),
                "marked_coord": None if sample.evaluation.marked_coord is None else [int(sample.evaluation.marked_coord[0]), int(sample.evaluation.marked_coord[1])],
                "target_coord": None if sample.evaluation.target_coord is None else [int(sample.evaluation.target_coord[0]), int(sample.evaluation.target_coord[1])],
                "target_color": str(sample.evaluation.target_color),
                "marked_piece": None if sample.evaluation.marked_piece is None else {"color": str(sample.evaluation.marked_piece.color), "kind": str(sample.evaluation.marked_piece.kind)},
                "annotation_coords": [[int(coord[0]), int(coord[1])] for coord in sample.evaluation.annotation_coords],
                "annotation_entity_ids": [str(entity_id) for entity_id in sample.evaluation.annotation_entity_ids],
            },
            "witness_symbolic": {"type": "object_set", "ids": [str(entity_id) for entity_id in sample.evaluation.annotation_entity_ids]},
            "projected_annotation": {"point_set": [list(point) for point in annotation_points]},
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
            scene_id=SCENE_ID,
        )


@register_task
class GamesCircularChessMarkedPieceDestinationCountTask(QuerySubsetTaskMixin, GamesCircularChessBoardTask):
    """Count legal destinations or captures for one marked Circular Chess piece."""

    task_id = MARKED_DESTINATION_TASK_ID
    supported_query_ids = SUPPORTED_MARKED_QUERY_IDS


@register_task
class GamesCircularChessTargetCellReacherCountTask(QuerySubsetTaskMixin, GamesCircularChessBoardTask):
    """Count pieces of one color that can legally reach a marked Circular Chess cell."""

    task_id = TARGET_REACHER_TASK_ID
    supported_query_ids = SUPPORTED_REACHER_QUERY_IDS


__all__ = [
    "BLACK_REACHER_QUERY_ID",
    "GamesCircularChessMarkedPieceDestinationCountTask",
    "GamesCircularChessTargetCellReacherCountTask",
    "MARKED_CAPTURE_QUERY_ID",
    "MARKED_MOVE_QUERY_ID",
    "WHITE_REACHER_QUERY_ID",
    "capture_destinations",
    "circular_coord_to_cell_id",
    "circular_piece_to_entity_id",
    "empty_board",
    "freeze_board",
    "legal_destinations",
    "target_reachers",
]
