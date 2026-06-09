"""Games tasks for visible-rule chess-variant movement."""

from __future__ import annotations

import json
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
from ...shared.text_rendering import fit_font_to_box, resolve_text_stroke_fill
from ..shared.text import draw_game_text_traced
from ..shared.chess_common import (
    BLACK,
    BOARD_SIZE,
    NON_KING_PIECE_KINDS,
    WHITE,
    Board,
    ChessPiece,
    Coord,
    color_name,
    coord_to_cell_id,
    empty_board,
    freeze_board,
    in_bounds,
    occupied_coords,
    occupied_piece_count,
    opponent,
    piece_to_entity_id,
    sample_material_piece,
    serialize_board,
    validate_square_chess_material,
)
from ..shared.complexity import build_games_chess_board_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import apply_games_layout_jitter_to_bbox, attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import (
    GamePanelSceneStyle,
    draw_panel_scene_chrome,
    game_panel_scene_style_metadata,
    make_panel_scene_background,
    resolve_game_panel_scene_style,
)
from ..shared.chess_scene import draw_chess_piece_symbol
from ..shared.style import build_games_chess_theme
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_chess_variant_board_base"
TASK_GROUP = "chess_variant"
SCENE_ID = "chess_variant"

SUPPORTED_MARKED_PIECE_QUERY_IDS: Tuple[str, ...] = (
    "marked_piece_move_count",
    "marked_piece_capture_count",
)
SUPPORTED_TARGET_SQUARE_QUERY_IDS: Tuple[str, ...] = (
    "white_piece_reaches_target_count",
    "black_piece_reaches_target_count",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    *SUPPORTED_MARKED_PIECE_QUERY_IDS,
    *SUPPORTED_TARGET_SQUARE_QUERY_IDS,
)
SUPPORTED_RULE_FAMILIES: Tuple[str, ...] = (
    "straight_range",
    "diagonal_range",
    "straight_or_diagonal_range",
    "leaper_2_1",
    "leaper_3_1",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("sparse_board", "crowded_board")
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = ("classic", "soft", "outlined", "wood_token", "blue_glyph", "monochrome_glyph")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for chess-variant boards."""

    marked_piece_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    marked_piece_capture_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    white_piece_reaches_target_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    black_piece_reaches_target_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    range_k_support: Tuple[int, ...] = (2, 3, 4)
    queen_range_k_support: Tuple[int, ...] = (1, 2, 3)
    sparse_min_occupied_count: int = 7
    sparse_max_occupied_count: int = 12
    crowded_min_occupied_count: int = 13
    crowded_max_occupied_count: int = 18
    canvas_width: int = 980
    canvas_height: int = 920
    panel_margin_px: int = 48
    rule_badge_height_px: int = 58
    rule_badge_width_px: int = 360
    header_gap_px: int = 18
    max_board_size_px: int = 760
    board_corner_radius_px: int = 24
    board_frame_width_px: int = 10
    piece_inset_fraction: float = 0.18
    marked_square_outline_width_px: int = 7
    rule_badge_font_size_px: int = 22
    piece_font_size_px: int = 78
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 560
    canvas_min_height_px: int = 560
    canvas_side_padding_px: int = 132
    canvas_vertical_padding_px: int = 92


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved query, rule, rendering, and answer axes."""

    query_id: str
    rule_family: str
    scene_variant: str
    style_variant: str
    range_k: int
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    rule_family_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    range_k_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderParams:
    """Resolved rendering controls."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    rule_badge_height_px: int
    rule_badge_width_px: int
    header_gap_px: int
    max_board_size_px: int
    board_corner_radius_px: int
    board_frame_width_px: int
    piece_inset_fraction: float
    marked_square_outline_width_px: int
    rule_badge_font_size_px: int
    piece_font_size_px: int
    layout_jitter_meta: Dict[str, Any]
    font_family: str = ""


@dataclass(frozen=True)
class _Evaluation:
    """Evaluation for one query under a visible movement rule."""

    answer: int
    legal_destinations: Tuple[Coord, ...]
    capture_coords: Tuple[Coord, ...]
    annotation_coords: Tuple[Coord, ...]
    annotation_entity_ids: Tuple[str, ...]
    annotation_kind: str
    marked_coord: Coord
    marked_piece: ChessPiece | None
    marker_role: str = "marked_piece"
    target_coord: Coord | None = None
    target_color: str = ""


@dataclass(frozen=True)
class _Sample:
    """One generated chess-variant sample."""

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
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.0)


def _target_support_key(query_id: str) -> str:
    return {
        "marked_piece_move_count": "marked_piece_move_count_support",
        "marked_piece_capture_count": "marked_piece_capture_count_support",
        "white_piece_reaches_target_count": "white_piece_reaches_target_count_support",
        "black_piece_reaches_target_count": "black_piece_reaches_target_count_support",
    }[str(query_id)]


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


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
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


def _range_support_for_rule(rule_family: str) -> Tuple[int, ...]:
    if str(rule_family) == "straight_or_diagonal_range":
        return tuple(int(v) for v in group_default(_GEN_DEFAULTS, "queen_range_k_support", _DEFAULTS.queen_range_k_support))
    if str(rule_family).endswith("_range"):
        return tuple(int(v) for v in group_default(_GEN_DEFAULTS, "range_k_support", _DEFAULTS.range_k_support))
    return (0,)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    rule_family, rule_family_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="rule_family",
        explicit_key="rule_family",
        weights_key="rule_family_weights",
        balance_flag_key="balanced_rule_family_sampling",
        supported=SUPPORTED_RULE_FAMILIES,
    )
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
    range_support = _range_support_for_rule(str(rule_family))
    if len(range_support) == 1:
        range_k = int(range_support[0])
        range_k_probabilities = {str(range_k): 1.0}
    else:
        range_k, range_k_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults={**dict(_GEN_DEFAULTS), "range_k_support": list(range_support)},
            support_key="range_k_support",
            explicit_key="range_k",
            fallback_support=range_support,
            namespace=f"{TASK_ID}.range_k.{str(rule_family)}",
            balanced_flag_key="balanced_range_k_sampling",
            namespace_support_permutation=True,
        )
    support_key = _target_support_key(str(query_id))
    fallback_support = tuple(int(v) for v in getattr(_DEFAULTS, support_key))
    configured_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=fallback_support,
    )
    possible_max = _max_possible_answer_for_rule(
        query_id=str(query_id),
        rule_family=str(rule_family),
        range_k=int(range_k),
    )
    target_support = tuple(int(v) for v in configured_support if int(v) <= int(possible_max))
    if not target_support:
        target_support = tuple(int(v) for v in fallback_support if int(v) <= int(possible_max))
    if not target_support:
        raise ValueError(
            f"no feasible target answers for query={query_id} rule={rule_family} range_k={range_k}"
        )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults={**dict(_GEN_DEFAULTS), str(support_key): list(target_support)},
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=target_support,
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        rule_family=str(rule_family),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        range_k=int(range_k),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(v) for v in target_support),
        query_id_probabilities=dict(query_id_probabilities),
        rule_family_probabilities=dict(rule_family_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        range_k_probabilities=dict(range_k_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.chess_variant.text_font",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.chess_variant.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.chess_variant.layout",
        ),
        unit_scale_meta,
    )
    max_board_size_px = scale_games_px(
        params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)),
        unit_scale,
        min_px=390,
    )
    rule_badge_height_px = scale_games_px(
        params.get(
            "rule_badge_height_px",
            group_default(_RENDER_DEFAULTS, "rule_badge_height_px", _DEFAULTS.rule_badge_height_px),
        ),
        unit_scale,
        min_px=38,
    )
    rule_badge_width_px = scale_games_px(
        params.get(
            "rule_badge_width_px",
            group_default(_RENDER_DEFAULTS, "rule_badge_width_px", _DEFAULTS.rule_badge_width_px),
        ),
        unit_scale,
        min_px=260,
    )
    header_gap_px = scale_games_px(
        params.get("header_gap_px", group_default(_RENDER_DEFAULTS, "header_gap_px", _DEFAULTS.header_gap_px)),
        unit_scale,
        min_px=10,
    )
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
                        + float(rule_badge_height_px)
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
    return _RenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        rule_badge_height_px=int(rule_badge_height_px),
        rule_badge_width_px=int(rule_badge_width_px),
        header_gap_px=int(header_gap_px),
        max_board_size_px=int(max_board_size_px),
        board_corner_radius_px=scale_games_px(params.get("board_corner_radius_px", group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px)), unit_scale, min_px=10),
        board_frame_width_px=scale_games_px(params.get("board_frame_width_px", group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px)), unit_scale, min_px=5),
        piece_inset_fraction=float(params.get("piece_inset_fraction", group_default(_RENDER_DEFAULTS, "piece_inset_fraction", _DEFAULTS.piece_inset_fraction))),
        marked_square_outline_width_px=scale_games_px(params.get("marked_square_outline_width_px", group_default(_RENDER_DEFAULTS, "marked_square_outline_width_px", _DEFAULTS.marked_square_outline_width_px)), unit_scale, min_px=4),
        rule_badge_font_size_px=scale_games_px(params.get("rule_badge_font_size_px", group_default(_RENDER_DEFAULTS, "rule_badge_font_size_px", _DEFAULTS.rule_badge_font_size_px)), unit_scale, min_px=16),
        piece_font_size_px=scale_games_px(
            params.get(
                "piece_font_size_px",
                group_default(
                    _RENDER_DEFAULTS,
                    "piece_font_size_px",
                    group_default(_RENDER_DEFAULTS, "token_label_font_size_px", _DEFAULTS.piece_font_size_px),
                ),
            ),
            unit_scale,
            min_px=32,
        ),
        layout_jitter_meta=layout_jitter,
        font_family=str(font_family),
    )


def _directions_for_rule(rule_family: str) -> Tuple[Tuple[int, int], ...]:
    if str(rule_family) == "straight_range":
        return ((-1, 0), (1, 0), (0, -1), (0, 1))
    if str(rule_family) == "diagonal_range":
        return ((-1, -1), (-1, 1), (1, -1), (1, 1))
    if str(rule_family) == "straight_or_diagonal_range":
        return ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    return ()


def _leaper_offsets(rule_family: str) -> Tuple[Tuple[int, int], ...]:
    if str(rule_family) == "leaper_2_1":
        a, b = 2, 1
    elif str(rule_family) == "leaper_3_1":
        a, b = 3, 1
    else:
        return ()
    offsets = set()
    for sr in (-1, 1):
        for sc in (-1, 1):
            offsets.add((sr * a, sc * b))
            offsets.add((sr * b, sc * a))
    return tuple(sorted(offsets))


def _ray_coords(origin: Coord, direction: Tuple[int, int], *, max_steps: int) -> Tuple[Coord, ...]:
    row, col = int(origin[0]), int(origin[1])
    dr, dc = int(direction[0]), int(direction[1])
    coords: List[Coord] = []
    for step in range(1, int(max_steps) + 1):
        coord = (row + (dr * step), col + (dc * step))
        if not in_bounds(*coord):
            break
        coords.append(coord)
    return tuple(coords)


def _all_empty_board_destinations(rule_family: str, range_k: int, origin: Coord) -> Tuple[Coord, ...]:
    if str(rule_family).endswith("_range"):
        coords: List[Coord] = []
        for direction in _directions_for_rule(str(rule_family)):
            coords.extend(_ray_coords(origin, direction, max_steps=int(range_k)))
        return tuple(coords)
    out = []
    row, col = int(origin[0]), int(origin[1])
    for dr, dc in _leaper_offsets(str(rule_family)):
        coord = (row + int(dr), col + int(dc))
        if in_bounds(*coord):
            out.append(coord)
    return tuple(sorted(out))


def _reacher_color_for_query(query_id: str) -> str:
    """Return the source-piece color requested by a target-square query."""

    return {
        "white_piece_reaches_target_count": WHITE,
        "black_piece_reaches_target_count": BLACK,
    }[str(query_id)]


def _destinations_for_piece_under_rule(
    board: Board,
    *,
    source_coord: Coord,
    rule_family: str,
    range_k: int,
) -> Tuple[Tuple[Coord, ...], Tuple[Coord, ...]]:
    """Return legal destinations and capture destinations under the visible variant rule."""

    piece = board[int(source_coord[0])][int(source_coord[1])]
    if piece is None:
        return tuple(), tuple()
    destinations: List[Coord] = []
    captures: List[Coord] = []
    if str(rule_family).endswith("_range"):
        for direction in _directions_for_rule(str(rule_family)):
            for coord in _ray_coords(source_coord, direction, max_steps=int(range_k)):
                occupant = board[int(coord[0])][int(coord[1])]
                if occupant is None:
                    destinations.append(coord)
                    continue
                if str(occupant.color) != str(piece.color):
                    destinations.append(coord)
                    captures.append(coord)
                break
    else:
        for coord in _all_empty_board_destinations(str(rule_family), int(range_k), source_coord):
            occupant = board[int(coord[0])][int(coord[1])]
            if occupant is None:
                destinations.append(coord)
            elif str(occupant.color) != str(piece.color):
                destinations.append(coord)
                captures.append(coord)
    return tuple(sorted(destinations)), tuple(sorted(captures))


def _source_rays_for_target(rule_family: str, range_k: int, target_coord: Coord) -> Tuple[Tuple[Coord, ...], ...]:
    """Return possible source locations grouped so range rules use at most one source per ray."""

    if str(rule_family).endswith("_range"):
        return tuple(
            ray
            for ray in (
                _ray_coords(target_coord, direction, max_steps=int(range_k))
                for direction in _directions_for_rule(str(rule_family))
            )
            if ray
        )
    rays: List[Tuple[Coord, ...]] = []
    target_row, target_col = int(target_coord[0]), int(target_coord[1])
    for dr, dc in _leaper_offsets(str(rule_family)):
        coord = (target_row + int(dr), target_col + int(dc))
        if in_bounds(*coord):
            rays.append((coord,))
    return tuple(sorted(rays))


def _max_possible_answer_for_rule(*, query_id: str, rule_family: str, range_k: int) -> int:
    """Return the largest feasible answer for one visible movement rule."""

    if str(query_id) in SUPPORTED_TARGET_SQUARE_QUERY_IDS:
        max_count = 0
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                max_count = max(
                    int(max_count),
                    len(_source_rays_for_target(str(rule_family), int(range_k), (row, col))),
                )
        return int(max_count)
    if str(query_id) == "marked_piece_capture_count" and str(rule_family).endswith("_range"):
        max_count = 0
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                ray_count = sum(
                    1
                    for direction in _directions_for_rule(str(rule_family))
                    if _ray_coords((row, col), direction, max_steps=int(range_k))
                )
                max_count = max(int(max_count), int(ray_count))
        return int(max_count)
    max_count = 0
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            max_count = max(
                int(max_count),
                len(_all_empty_board_destinations(str(rule_family), int(range_k), (row, col))),
            )
    return int(max_count)


def _evaluate_board(board: Board, *, marked_coord: Coord, rule_family: str, range_k: int) -> _Evaluation:
    piece = board[int(marked_coord[0])][int(marked_coord[1])]
    if piece is None:
        raise ValueError("marked square is empty")
    legal_destinations, capture_coords = _destinations_for_piece_under_rule(
        board,
        source_coord=marked_coord,
        rule_family=str(rule_family),
        range_k=int(range_k),
    )
    return _Evaluation(
        answer=0,
        legal_destinations=legal_destinations,
        capture_coords=capture_coords,
        annotation_coords=(),
        annotation_entity_ids=(),
        annotation_kind="cell",
        marked_coord=marked_coord,
        marked_piece=piece,
    )


def _evaluate_target_square_reachers(
    board: Board,
    *,
    target_coord: Coord,
    query_id: str,
    rule_family: str,
    range_k: int,
) -> _Evaluation:
    """Evaluate same-side pieces that can legally move to one marked target square."""

    target_color = _reacher_color_for_query(str(query_id))
    target_occupant = board[int(target_coord[0])][int(target_coord[1])]
    if target_occupant is not None and str(target_occupant.color) == str(target_color):
        raise ValueError("target square cannot be occupied by the queried side")
    annotation_coords: List[Coord] = []
    for coord in occupied_coords(board):
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None or str(piece.color) != str(target_color):
            continue
        legal_destinations, _capture_coords = _destinations_for_piece_under_rule(
            board,
            source_coord=coord,
            rule_family=str(rule_family),
            range_k=int(range_k),
        )
        if tuple(target_coord) in set(legal_destinations):
            annotation_coords.append(tuple(coord))
    annotation_coords_tuple = tuple(sorted(annotation_coords))
    return _Evaluation(
        answer=len(annotation_coords_tuple),
        legal_destinations=(),
        capture_coords=(),
        annotation_coords=annotation_coords_tuple,
        annotation_entity_ids=tuple(
            piece_to_entity_id(coord, board[int(coord[0])][int(coord[1])])
            for coord in annotation_coords_tuple
            if board[int(coord[0])][int(coord[1])] is not None
        ),
        annotation_kind="piece_point",
        marked_coord=target_coord,
        marked_piece=None,
        marker_role="target_square",
        target_coord=target_coord,
        target_color=str(target_color),
    )


def _with_query_annotation(board: Board, evaluation: _Evaluation, *, query_id: str) -> _Evaluation:
    if str(query_id) == "marked_piece_move_count":
        annotation_coords = tuple(evaluation.legal_destinations)
        return _Evaluation(
            answer=len(annotation_coords),
            legal_destinations=tuple(evaluation.legal_destinations),
            capture_coords=tuple(evaluation.capture_coords),
            annotation_coords=annotation_coords,
            annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in annotation_coords),
            annotation_kind="cell",
            marked_coord=evaluation.marked_coord,
            marked_piece=evaluation.marked_piece,
            marker_role=str(evaluation.marker_role),
            target_coord=evaluation.target_coord,
            target_color=str(evaluation.target_color),
        )
    if str(query_id) == "marked_piece_capture_count":
        annotation_coords = tuple(evaluation.capture_coords)
        return _Evaluation(
            answer=len(annotation_coords),
            legal_destinations=tuple(evaluation.legal_destinations),
            capture_coords=tuple(evaluation.capture_coords),
            annotation_coords=annotation_coords,
            annotation_entity_ids=tuple(coord_to_cell_id(coord) for coord in annotation_coords),
            annotation_kind="cell",
            marked_coord=evaluation.marked_coord,
            marked_piece=evaluation.marked_piece,
            marker_role=str(evaluation.marker_role),
            target_coord=evaluation.target_coord,
            target_color=str(evaluation.target_color),
        )
    raise ValueError(f"unsupported query id: {query_id}")


def _random_marked_coord(rng, *, rule_family: str, range_k: int, minimum_destinations: int) -> Coord:
    coords = [(row, col) for row in range(BOARD_SIZE) for col in range(BOARD_SIZE)]
    rng.shuffle(coords)
    for coord in coords:
        if len(_all_empty_board_destinations(str(rule_family), int(range_k), coord)) >= int(minimum_destinations):
            return tuple(coord)
    raise ValueError("no marked coordinate has enough destinations")


def _place_variant_piece(
    *,
    rng,
    mutable: list[list[ChessPiece | None]],
    coord: Coord,
    color: str | None = None,
    kinds: Sequence[str] = NON_KING_PIECE_KINDS,
) -> bool:
    """Place one material-capped chess symbol for a rule-card variant board."""

    row, col = int(coord[0]), int(coord[1])
    if mutable[row][col] is not None:
        return False
    colors = (str(color),) if color is not None else (WHITE, BLACK)
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


def _evaluate_axes_board(
    board: Board,
    *,
    axes: _ResolvedAxes,
    marked: Coord | None,
    target: Coord | None,
) -> _Evaluation:
    """Evaluate a board using the active chess-variant query contract."""

    if str(axes.query_id) in SUPPORTED_TARGET_SQUARE_QUERY_IDS:
        if target is None:
            raise ValueError("target-square query requires target")
        return _evaluate_target_square_reachers(
            board,
            target_coord=target,
            query_id=str(axes.query_id),
            rule_family=str(axes.rule_family),
            range_k=int(axes.range_k),
        )
    if marked is None:
        raise ValueError("marked-piece query requires marked coordinate")
    return _with_query_annotation(
        board,
        _evaluate_board(
            board,
            marked_coord=marked,
            rule_family=str(axes.rule_family),
            range_k=int(axes.range_k),
        ),
        query_id=str(axes.query_id),
    )


def _add_required_kings_preserving(
    *,
    rng,
    board: Board,
    axes: _ResolvedAxes,
    marked: Coord | None,
    target: Coord | None,
) -> Board:
    """Add one king per side without changing the active answer."""

    mutable = [list(row) for row in board]
    for color in (WHITE, BLACK):
        if any(piece is not None and str(piece.color) == str(color) and str(piece.kind) == "king" for row in mutable for piece in row):
            continue
        candidates = [
            (row, col)
            for row in range(BOARD_SIZE)
            for col in range(BOARD_SIZE)
            if mutable[row][col] is None and (target is None or (row, col) != tuple(target))
        ]
        rng.shuffle(candidates)
        placed = False
        for coord in candidates:
            mutable[int(coord[0])][int(coord[1])] = ChessPiece(str(color), "king")
            candidate = freeze_board(mutable)
            if not validate_square_chess_material(
                candidate,
                require_both_kings=False,
                enforce_standard_pawn_rows=True,
                enforce_non_adjacent_kings=True,
            ):
                mutable[int(coord[0])][int(coord[1])] = None
                continue
            try:
                evaluation = _evaluate_axes_board(candidate, axes=axes, marked=marked, target=target)
            except ValueError:
                evaluation = None
            if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
                mutable[int(coord[0])][int(coord[1])] = None
                continue
            placed = True
            break
        if not placed:
            raise ValueError("failed to add required chess-variant kings without changing answer")
    final = freeze_board(mutable)
    if not validate_square_chess_material(final):
        raise ValueError("chess-variant board is not material-plausible")
    return final


def _random_composition_with_caps(rng, *, total: int, caps: Sequence[int]) -> Tuple[int, ...] | None:
    counts = [0 for _ in caps]
    remaining = int(total)
    order = list(range(len(caps)))
    rng.shuffle(order)
    for index in order:
        if remaining <= 0:
            break
        max_here = min(int(caps[index]), int(remaining))
        if max_here <= 0:
            continue
        value = int(rng.randint(0, max_here))
        counts[index] = int(value)
        remaining -= int(value)
    while remaining > 0:
        candidates = [i for i, cap in enumerate(caps) if counts[i] < int(cap)]
        if not candidates:
            return None
        index = int(rng.choice(candidates))
        counts[index] += 1
        remaining -= 1
    return tuple(int(v) for v in counts)


def _construct_move_board(*, rng, axes: _ResolvedAxes) -> Tuple[Board, Coord]:
    marked_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
    minimum = int(axes.target_answer)
    marked = _random_marked_coord(rng, rule_family=axes.rule_family, range_k=axes.range_k, minimum_destinations=minimum)
    mutable = [list(row) for row in empty_board()]
    if not _place_variant_piece(rng=rng, mutable=mutable, coord=marked, color=marked_color):
        raise ValueError("failed to place marked chess-variant piece")
    if str(axes.rule_family).endswith("_range"):
        rays = [_ray_coords(marked, direction, max_steps=int(axes.range_k)) for direction in _directions_for_rule(str(axes.rule_family))]
        caps = [len(ray) for ray in rays]
        counts = _random_composition_with_caps(rng, total=int(axes.target_answer), caps=caps)
        if counts is None:
            raise ValueError("failed to distribute move destinations")
        for ray, legal_count in zip(rays, counts):
            for index, coord in enumerate(ray):
                if index < int(legal_count):
                    if int(rng.randrange(5)) == 0:
                        _place_variant_piece(rng=rng, mutable=mutable, coord=coord, color=opponent(marked_color))
                    continue
                if not _place_variant_piece(rng=rng, mutable=mutable, coord=coord, color=marked_color):
                    raise ValueError("failed to place chess-variant range blocker")
                break
    else:
        potentials = list(_all_empty_board_destinations(str(axes.rule_family), int(axes.range_k), marked))
        if len(potentials) < int(axes.target_answer):
            raise ValueError("not enough leaper destinations")
        rng.shuffle(potentials)
        legal = set(tuple(coord) for coord in potentials[: int(axes.target_answer)])
        for coord in potentials:
            if tuple(coord) in legal:
                if int(rng.randrange(5)) == 0:
                    _place_variant_piece(rng=rng, mutable=mutable, coord=coord, color=opponent(marked_color))
            else:
                if not _place_variant_piece(rng=rng, mutable=mutable, coord=coord, color=marked_color):
                    raise ValueError("failed to place chess-variant leaper blocker")
    return freeze_board(mutable), marked


def _construct_capture_board(*, rng, axes: _ResolvedAxes) -> Tuple[Board, Coord]:
    marked_color = WHITE if int(rng.randrange(2)) == 0 else BLACK
    marked = _random_marked_coord(rng, rule_family=axes.rule_family, range_k=axes.range_k, minimum_destinations=int(axes.target_answer))
    mutable = [list(row) for row in empty_board()]
    if not _place_variant_piece(rng=rng, mutable=mutable, coord=marked, color=marked_color):
        raise ValueError("failed to place marked chess-variant piece")
    if str(axes.rule_family).endswith("_range"):
        rays = [_ray_coords(marked, direction, max_steps=int(axes.range_k)) for direction in _directions_for_rule(str(axes.rule_family))]
        available = [ray for ray in rays if ray]
        if len(available) < int(axes.target_answer):
            raise ValueError("not enough capture rays")
        rng.shuffle(available)
        capture_rays = set(tuple(ray[0]) for ray in available[: int(axes.target_answer)])
        for ray in rays:
            if not ray:
                continue
            if tuple(ray[0]) in capture_rays:
                distance = int(rng.randint(1, len(ray)))
                target = ray[distance - 1]
                if not _place_variant_piece(rng=rng, mutable=mutable, coord=target, color=opponent(marked_color)):
                    raise ValueError("failed to place chess-variant capture target")
                continue
            if int(rng.randrange(2)) == 0:
                blocker = ray[int(rng.randint(0, len(ray) - 1))]
                if not _place_variant_piece(rng=rng, mutable=mutable, coord=blocker, color=marked_color):
                    raise ValueError("failed to place chess-variant capture blocker")
    else:
        potentials = list(_all_empty_board_destinations(str(axes.rule_family), int(axes.range_k), marked))
        if len(potentials) < int(axes.target_answer):
            raise ValueError("not enough leaper capture squares")
        rng.shuffle(potentials)
        captures = set(tuple(coord) for coord in potentials[: int(axes.target_answer)])
        for coord in potentials:
            piece_color = opponent(marked_color) if tuple(coord) in captures else marked_color
            if not _place_variant_piece(rng=rng, mutable=mutable, coord=coord, color=piece_color):
                raise ValueError("failed to place chess-variant leaper capture piece")
    return freeze_board(mutable), marked


def _random_target_coord(rng, *, rule_family: str, range_k: int, minimum_sources: int) -> Coord:
    """Return a target square with enough geometrically possible source rays."""

    coords = [(row, col) for row in range(BOARD_SIZE) for col in range(BOARD_SIZE)]
    rng.shuffle(coords)
    for coord in coords:
        if len(_source_rays_for_target(str(rule_family), int(range_k), coord)) >= int(minimum_sources):
            return tuple(coord)
    raise ValueError("no target coordinate has enough source rays")


def _construct_reacher_board(*, rng, axes: _ResolvedAxes) -> Tuple[Board, Coord]:
    """Construct a board with exactly the requested pieces able to reach one target square."""

    target_color = _reacher_color_for_query(str(axes.query_id))
    target = _random_target_coord(
        rng,
        rule_family=str(axes.rule_family),
        range_k=int(axes.range_k),
        minimum_sources=int(axes.target_answer),
    )
    source_rays = list(_source_rays_for_target(str(axes.rule_family), int(axes.range_k), target))
    if len(source_rays) < int(axes.target_answer):
        raise ValueError("not enough source rays for requested target answer")
    rng.shuffle(source_rays)
    selected_rays = source_rays[: int(axes.target_answer)]
    mutable = [list(row) for row in empty_board()]
    if int(rng.randrange(3)) == 0:
        _place_variant_piece(rng=rng, mutable=mutable, coord=target, color=opponent(target_color))
    for ray in selected_rays:
        source = tuple(rng.choice(list(ray)))
        if not _place_variant_piece(rng=rng, mutable=mutable, coord=source, color=target_color):
            raise ValueError("failed to place chess-variant reacher source")
    board = freeze_board(mutable)
    evaluation = _evaluate_target_square_reachers(
        board,
        target_coord=target,
        query_id=str(axes.query_id),
        rule_family=str(axes.rule_family),
        range_k=int(axes.range_k),
    )
    if int(evaluation.answer) != int(axes.target_answer):
        raise ValueError("constructed reacher board does not match target answer")
    return board, target


def _desired_piece_count(rng, scene_variant: str) -> int:
    if str(scene_variant) == "crowded_board":
        return int(rng.randint(_DEFAULTS.crowded_min_occupied_count, _DEFAULTS.crowded_max_occupied_count))
    return int(rng.randint(_DEFAULTS.sparse_min_occupied_count, _DEFAULTS.sparse_max_occupied_count))


def _add_fillers_preserving(*, rng, board: Board, marked: Coord, axes: _ResolvedAxes, desired_count: int) -> Board:
    mutable = [list(row) for row in board]
    target_answer = int(axes.target_answer)
    attempts = 0
    while occupied_piece_count(mutable) < int(desired_count) and attempts < 640:
        attempts += 1
        empties = [(row, col) for row in range(BOARD_SIZE) for col in range(BOARD_SIZE) if mutable[row][col] is None]
        if not empties:
            break
        coord = tuple(rng.choice(empties))
        if not _place_variant_piece(rng=rng, mutable=mutable, coord=coord):
            break
        frozen = freeze_board(mutable)
        if not validate_square_chess_material(
            frozen,
            require_both_kings=False,
            enforce_standard_pawn_rows=True,
            enforce_non_adjacent_kings=True,
        ):
            mutable[int(coord[0])][int(coord[1])] = None
            continue
        candidate = _with_query_annotation(
            frozen,
            _evaluate_board(frozen, marked_coord=marked, rule_family=axes.rule_family, range_k=axes.range_k),
            query_id=axes.query_id,
        )
        if int(candidate.answer) != int(target_answer):
            mutable[int(coord[0])][int(coord[1])] = None
    return freeze_board(mutable)


def _add_fillers_preserving_reachers(*, rng, board: Board, target: Coord, axes: _ResolvedAxes, desired_count: int) -> Board:
    """Add visual filler pieces without changing a target-square reacher answer."""

    mutable = [list(row) for row in board]
    target_answer = int(axes.target_answer)
    attempts = 0
    while occupied_piece_count(mutable) < int(desired_count) and attempts < 960:
        attempts += 1
        empties = [
            (row, col)
            for row in range(BOARD_SIZE)
            for col in range(BOARD_SIZE)
            if mutable[row][col] is None and (row, col) != tuple(target)
        ]
        if not empties:
            break
        coord = tuple(rng.choice(empties))
        if not _place_variant_piece(rng=rng, mutable=mutable, coord=coord):
            break
        frozen = freeze_board(mutable)
        if not validate_square_chess_material(
            frozen,
            require_both_kings=False,
            enforce_standard_pawn_rows=True,
            enforce_non_adjacent_kings=True,
        ):
            mutable[int(coord[0])][int(coord[1])] = None
            continue
        try:
            candidate = _evaluate_target_square_reachers(
                frozen,
                target_coord=target,
                query_id=str(axes.query_id),
                rule_family=str(axes.rule_family),
                range_k=int(axes.range_k),
            )
        except ValueError:
            candidate = None
        if candidate is None or int(candidate.answer) != int(target_answer):
            mutable[int(coord[0])][int(coord[1])] = None
    return freeze_board(mutable)


def _sample_scene(*, rng, axes: _ResolvedAxes) -> _Sample:
    for _ in range(240):
        try:
            if str(axes.query_id) in SUPPORTED_TARGET_SQUARE_QUERY_IDS:
                board, target = _construct_reacher_board(rng=rng, axes=axes)
                board = _add_required_kings_preserving(rng=rng, board=board, axes=axes, marked=None, target=target)
                desired_count = max(_desired_piece_count(rng, axes.scene_variant), occupied_piece_count(board))
                board = _add_fillers_preserving_reachers(
                    rng=rng,
                    board=board,
                    target=target,
                    axes=axes,
                    desired_count=desired_count,
                )
                evaluation = _evaluate_target_square_reachers(
                    board,
                    target_coord=target,
                    query_id=str(axes.query_id),
                    rule_family=str(axes.rule_family),
                    range_k=int(axes.range_k),
                )
            elif str(axes.query_id) == "marked_piece_move_count":
                board, marked = _construct_move_board(rng=rng, axes=axes)
                board = _add_required_kings_preserving(rng=rng, board=board, axes=axes, marked=marked, target=None)
                desired_count = max(_desired_piece_count(rng, axes.scene_variant), occupied_piece_count(board))
                board = _add_fillers_preserving(rng=rng, board=board, marked=marked, axes=axes, desired_count=desired_count)
                evaluation = _with_query_annotation(
                    board,
                    _evaluate_board(board, marked_coord=marked, rule_family=axes.rule_family, range_k=axes.range_k),
                    query_id=axes.query_id,
                )
            else:
                board, marked = _construct_capture_board(rng=rng, axes=axes)
                board = _add_required_kings_preserving(rng=rng, board=board, axes=axes, marked=marked, target=None)
                desired_count = max(_desired_piece_count(rng, axes.scene_variant), occupied_piece_count(board))
                board = _add_fillers_preserving(rng=rng, board=board, marked=marked, axes=axes, desired_count=desired_count)
                evaluation = _with_query_annotation(
                    board,
                    _evaluate_board(board, marked_coord=marked, rule_family=axes.rule_family, range_k=axes.range_k),
                    query_id=axes.query_id,
                )
            if int(evaluation.answer) != int(axes.target_answer):
                continue
            if not validate_square_chess_material(board):
                continue
            return _Sample(
                board=board,
                evaluation=evaluation,
                occupied_count=occupied_piece_count(board),
                construction_mode="direct_rule_constrained_board",
            )
        except ValueError:
            continue
    raise ValueError("failed to sample requested chess-variant board")


def _piece_bbox(cell_bbox: Tuple[float, float, float, float], *, inset_fraction: float) -> Tuple[float, float, float, float]:
    left, top, right, bottom = cell_bbox
    inset = float(max(5.0, float(inset_fraction) * min(right - left, bottom - top)))
    return (round(left + inset, 3), round(top + inset, 3), round(right - inset, 3), round(bottom - inset, 3))


def _rule_badge_text(rule_family: str, range_k: int, prompt_defaults: Mapping[str, Any]) -> str:
    key = f"rule_badge_{str(rule_family)}"
    return str(prompt_defaults[key]).format(range_k=int(range_k))


def _rule_text(rule_family: str, range_k: int, prompt_defaults: Mapping[str, Any]) -> str:
    key = f"rule_text_{str(rule_family)}"
    return str(prompt_defaults[key]).format(range_k=int(range_k))


def _target_rule_text(rule_family: str, range_k: int, prompt_defaults: Mapping[str, Any]) -> str:
    key = f"target_rule_text_{str(rule_family)}"
    return str(prompt_defaults[key]).format(range_k=int(range_k))


def _render_scene(
    *,
    board: Board,
    axes: _ResolvedAxes,
    background: Image.Image,
    params: _RenderParams,
    badge_text: str,
    panel_style: GamePanelSceneStyle | None = None,
) -> Tuple[Image.Image, Dict[str, Any], Tuple[Dict[str, Any], ...]]:
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    theme = build_games_chess_theme(style_variant=str(axes.style_variant))
    cell_size = min(
        int(params.max_board_size_px) // BOARD_SIZE,
        (int(params.canvas_width) - (2 * int(params.panel_margin_px))) // BOARD_SIZE,
        (
            int(params.canvas_height)
            - (2 * int(params.panel_margin_px))
            - int(params.rule_badge_height_px)
            - int(params.header_gap_px)
        )
        // BOARD_SIZE,
    )
    board_size_px = int(cell_size) * BOARD_SIZE
    board_left = int(0.5 * (int(params.canvas_width) - int(board_size_px)))
    available_height = (
        int(params.canvas_height)
        - (2 * int(params.panel_margin_px))
        - int(params.rule_badge_height_px)
        - int(params.header_gap_px)
    )
    board_top = int(params.panel_margin_px + params.rule_badge_height_px + params.header_gap_px + max(0, 0.5 * (available_height - board_size_px)))
    board_bbox = (float(board_left), float(board_top), float(board_left + board_size_px), float(board_top + board_size_px))
    badge_width = int(params.rule_badge_width_px)
    badge_left = int(0.5 * (int(params.canvas_width) - int(badge_width)))
    badge_top = int(params.panel_margin_px)
    badge_bbox = (float(badge_left), float(badge_top), float(badge_left + badge_width), float(badge_top + int(params.rule_badge_height_px)))
    group_bbox = (
        min(board_bbox[0], badge_bbox[0]),
        min(board_bbox[1], badge_bbox[1]),
        max(board_bbox[2], badge_bbox[2]),
        max(board_bbox[3], badge_bbox[3]),
    )
    _group_bbox, dx, dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=group_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    board_left = float(board_left + dx)
    board_top = float(board_top + dy)
    badge_bbox = (badge_bbox[0] + dx, badge_bbox[1] + dy, badge_bbox[2] + dx, badge_bbox[3] + dy)
    board_bbox = (board_bbox[0] + dx, board_bbox[1] + dy, board_bbox[2] + dx, board_bbox[3] + dy)
    scene_panel_bbox: Tuple[int, int, int, int] | None = None
    if panel_style is not None:
        panel_pad = max(18, int(round(float(params.panel_margin_px) * 0.42)))
        scene_panel_bbox = (
            max(4, int(round(min(board_bbox[0], badge_bbox[0]))) - panel_pad),
            max(4, int(round(min(board_bbox[1], badge_bbox[1]))) - panel_pad),
            min(int(params.canvas_width) - 4, int(round(max(board_bbox[2], badge_bbox[2]))) + panel_pad),
            min(int(params.canvas_height) - 4, int(round(max(board_bbox[3], badge_bbox[3]))) + panel_pad),
        )
        draw_panel_scene_chrome(
            draw,
            bbox=scene_panel_bbox,
            style=panel_style,
            radius=26,
            border_width=max(2, int(round(float(params.board_frame_width_px) * 0.55))),
        )
    draw.rounded_rectangle(board_bbox, radius=int(params.board_corner_radius_px), fill=tuple(theme.board_frame_rgb))
    draw.rounded_rectangle(
        badge_bbox,
        radius=int(0.5 * int(params.rule_badge_height_px)),
        fill=tuple(theme.badge_fill_rgb),
        outline=tuple(theme.badge_outline_rgb),
        width=2,
    )
    badge_font = fit_font_to_box(
        draw,
        text=str(badge_text),
        max_width=float((badge_bbox[2] - badge_bbox[0]) - 36),
        max_height=float((badge_bbox[3] - badge_bbox[1]) - 12),
        bold=True,
        font_family=str(params.font_family) or None,
        min_size_px=12,
        max_size_px=int(params.rule_badge_font_size_px),
        fill_ratio=0.98,
    )
    text_bbox = draw.textbbox((0, 0), str(badge_text), font=badge_font, stroke_width=1)
    text_rgb = tuple(theme.badge_text_rgb)
    draw_game_text_traced(draw,
        (
            float(badge_bbox[0] + ((badge_bbox[2] - badge_bbox[0]) - (text_bbox[2] - text_bbox[0])) / 2.0),
            float(badge_bbox[1] + ((badge_bbox[3] - badge_bbox[1]) - (text_bbox[3] - text_bbox[1])) / 2.0 - text_bbox[1]),
        ),
        str(badge_text),
        font=badge_font,
        fill=text_rgb,
        stroke_width=1,
        stroke_fill=tuple(resolve_text_stroke_fill(text_rgb)),
     role="readout", required=False,)

    inner_inset = float(params.board_frame_width_px)
    cell_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    piece_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    entities: List[Dict[str, Any]] = []
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            left = float(board_left + (col * cell_size) + inner_inset)
            top = float(board_top + (row * cell_size) + inner_inset)
            right = float(board_left + ((col + 1) * cell_size) - inner_inset)
            bottom = float(board_top + ((row + 1) * cell_size) - inner_inset)
            cell_bbox = (round(left, 3), round(top, 3), round(right, 3), round(bottom, 3))
            is_light = (row + col) % 2 == 0
            fill_rgb = tuple(theme.light_square_rgb if is_light else theme.dark_square_rgb)
            draw.rectangle(cell_bbox, fill=fill_rgb, outline=tuple(theme.grid_line_rgb), width=int(theme.grid_line_width_px))
            if str(theme.square_rendering) == "inset":
                inset = max(2.0, 0.045 * min(cell_bbox[2] - cell_bbox[0], cell_bbox[3] - cell_bbox[1]))
                draw.rectangle(
                    [cell_bbox[0] + inset, cell_bbox[1] + inset, cell_bbox[2] - inset, cell_bbox[3] - inset],
                    outline=tuple(theme.grid_line_rgb),
                    width=1,
                )
            cell_id = coord_to_cell_id((row, col))
            cell_bboxes[cell_id] = cell_bbox
            occupant = board[row][col]
            occupant_text = "empty" if occupant is None else f"{occupant.color}_{occupant.kind}"
            entities.append({"id": cell_id, "type": "chess_variant_cell", "row": row, "col": col, "occupant": occupant_text, "bbox_px": list(cell_bbox)})
            if occupant is None:
                continue
            piece_bbox = _piece_bbox(cell_bbox, inset_fraction=float(params.piece_inset_fraction))
            draw_chess_piece_symbol(
                draw,
                bbox_px=piece_bbox,
                piece=occupant,
                theme=theme,
                font_size_px=int(params.piece_font_size_px),
            )
            piece_id = piece_to_entity_id((row, col), occupant)
            piece_bboxes[piece_id] = piece_bbox
            entities.append(
                {
                    "id": piece_id,
                    "type": "chess_variant_piece",
                    "color": occupant.color,
                    "kind": occupant.kind,
                    "row": row,
                    "col": col,
                    "bbox_px": list(piece_bbox),
                }
            )
    return image, {
        "board_bbox_px": [round(float(v), 3) for v in board_bbox],
        "scene_panel_bbox_px": None if scene_panel_bbox is None else [int(v) for v in scene_panel_bbox],
        "badge_bbox_px": [round(float(v), 3) for v in badge_bbox],
        "cell_bboxes_px": {str(k): list(v) for k, v in cell_bboxes.items()},
        "piece_bboxes_px": {str(k): list(v) for k, v in piece_bboxes.items()},
        "effective_cell_size_px": float(cell_size),
        "layout_jitter": dict(layout_jitter),
        "panel_scene_style": None if panel_style is None else game_panel_scene_style_metadata(panel_style),
        "font_family": str(params.font_family),
        "board_size": int(BOARD_SIZE),
        "piece_rendering": "filled_chess_glyph",
    }, tuple(entities)


def _draw_marked_outline(
    image: Image.Image,
    render_map: Mapping[str, Any],
    marked_coord: Coord,
    axes: _ResolvedAxes,
    params: _RenderParams,
    *,
    outline_rgb: Tuple[int, int, int] = (220, 38, 38),
) -> None:
    draw = ImageDraw.Draw(image)
    del axes
    cell_id = coord_to_cell_id(marked_coord)
    bbox = render_map["cell_bboxes_px"][cell_id]
    inset = max(3.0, 0.06 * min(float(bbox[2]) - float(bbox[0]), float(bbox[3]) - float(bbox[1])))
    draw.rectangle(
        [float(bbox[0]) + inset, float(bbox[1]) + inset, float(bbox[2]) - inset, float(bbox[3]) - inset],
        fill=None,
    )
    draw.rectangle(
        [float(bbox[0]) + inset, float(bbox[1]) + inset, float(bbox[2]) - inset, float(bbox[3]) - inset],
        outline=tuple(int(v) for v in outline_rgb),
        width=int(params.marked_square_outline_width_px),
    )


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) in SUPPORTED_TARGET_SQUARE_QUERY_IDS:
        answer_value = 3
        annotation_value = [[180, 245], [310, 375], [440, 505]]
        return (
            json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
            json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        )
    answer_value = 4 if str(query_id) == "marked_piece_move_count" else 2
    annotation_value = [[140, 220, 210, 290], [210, 220, 280, 290]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesChessVariantBoardTask:
    """Return one grounded query over a chess-like board with a visible movement rule."""

    task_id = TASK_ID
    domain = "games"
    task_group = TASK_GROUP

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        sample: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{attempt_index}")
            try:
                sample = _sample_scene(rng=rng, axes=axes)
            except ValueError:
                continue
            break
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

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
                "marked_piece_rule_text",
                "target_square_rule_text",
                "landing_rule_text",
                "target_landing_rule_text",
                "slider_block_rule_text",
                "leaper_block_rule_text",
                "target_slider_block_rule_text",
                "target_leaper_block_rule_text",
                "answer_hint_marked_piece_move_count",
                "answer_hint_marked_piece_capture_count",
                "answer_hint_white_piece_reaches_target_count",
                "answer_hint_black_piece_reaches_target_count",
                "annotation_hint_marked_piece_move_count",
                "annotation_hint_marked_piece_capture_count",
                "annotation_hint_white_piece_reaches_target_count",
                "annotation_hint_black_piece_reaches_target_count",
                "rule_text_straight_range",
                "rule_text_diagonal_range",
                "rule_text_straight_or_diagonal_range",
                "rule_text_leaper_2_1",
                "rule_text_leaper_3_1",
                "target_rule_text_straight_range",
                "target_rule_text_diagonal_range",
                "target_rule_text_straight_or_diagonal_range",
                "target_rule_text_leaper_2_1",
                "target_rule_text_leaper_3_1",
                "rule_badge_straight_range",
                "rule_badge_diagonal_range",
                "rule_badge_straight_or_diagonal_range",
                "rule_badge_leaper_2_1",
                "rule_badge_leaper_3_1",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        is_target_square_query = str(axes.query_id) in SUPPORTED_TARGET_SQUARE_QUERY_IDS
        if bool(is_target_square_query):
            rule_text = _target_rule_text(axes.rule_family, axes.range_k, prompt_defaults)
            block_rule_text = str(
                prompt_defaults["target_leaper_block_rule_text"]
                if str(axes.rule_family).startswith("leaper")
                else prompt_defaults["target_slider_block_rule_text"]
            )
        else:
            rule_text = _rule_text(axes.rule_family, axes.range_k, prompt_defaults)
            block_rule_text = str(prompt_defaults["leaper_block_rule_text"] if str(axes.rule_family).startswith("leaper") else prompt_defaults["slider_block_rule_text"])
        badge_text = _rule_badge_text(axes.rule_family, axes.range_k, prompt_defaults)

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
            namespace="games.chess_variant_board.panel_scene_style",
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
        rendered_image, render_map, scene_entities = _render_scene(
            board=sample.board,
            axes=axes,
            background=background,
            params=render_params,
            badge_text=badge_text,
            panel_style=panel_style,
        )
        _draw_marked_outline(
            rendered_image,
            render_map,
            sample.evaluation.marked_coord,
            axes,
            render_params,
            outline_rgb=(35, 95, 220) if bool(is_target_square_query) else (220, 38, 38),
        )
        annotation_points: list[list[float]] = []
        if sample.evaluation.annotation_kind == "cell":
            annotation_bboxes = [list(render_map["cell_bboxes_px"][entity_id]) for entity_id in sample.evaluation.annotation_entity_ids]
        elif sample.evaluation.annotation_kind == "piece_point":
            annotation_bboxes = []
            for entity_id in sample.evaluation.annotation_entity_ids:
                bbox = render_map["piece_bboxes_px"][str(entity_id)]
                annotation_points.append([
                    round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                    round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
                ])
        else:
            annotation_bboxes = [list(render_map["piece_bboxes_px"][entity_id]) for entity_id in sample.evaluation.annotation_entity_ids]
        image, post_noise_meta = apply_post_image_noise(
            rendered_image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        answer_hint = str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"])
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
                "rule_text": str(rule_text),
                "marked_piece_rule_text": str(prompt_defaults["marked_piece_rule_text"]),
                "target_square_rule_text": str(prompt_defaults["target_square_rule_text"]),
                "landing_rule_text": str(prompt_defaults["landing_rule_text"]),
                "target_landing_rule_text": str(prompt_defaults["target_landing_rule_text"]),
                "block_rule_text": str(block_rule_text),
                "target_color_name": (
                    color_name(_reacher_color_for_query(str(axes.query_id)))
                    if bool(is_target_square_query)
                    else ""
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        complexity = build_games_chess_board_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            occupied_count=int(sample.occupied_count),
            target_answer=int(sample.evaluation.answer),
            annotation_count=len(sample.evaluation.annotation_entity_ids),
        )
        answer_gt = TypedValue(type="integer", value=int(sample.evaluation.answer))
        annotation_gt = (
            TypedValue(type="point_set", value=[list(point) for point in annotation_points])
            if bool(is_target_square_query)
            else TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        )
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        marked_piece = sample.evaluation.marked_piece
        marked_piece_payload = (
            None
            if marked_piece is None
            else {"color": str(marked_piece.color), "kind": str(marked_piece.kind)}
        )
        target_coord_payload = (
            None
            if sample.evaluation.target_coord is None
            else [int(sample.evaluation.target_coord[0]), int(sample.evaluation.target_coord[1])]
        )
        projected_annotation = (
            {
                "type": "point_set",
                "point_set": [list(point) for point in annotation_points],
                "pixel_point_set": [list(point) for point in annotation_points],
            }
            if bool(is_target_square_query)
            else {"bbox_set": [list(bbox) for bbox in annotation_bboxes]}
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_chess_variant_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "rule_family": str(axes.rule_family),
                    "range_k": int(axes.range_k),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(BOARD_SIZE),
                    "target_answer": int(sample.evaluation.answer),
                    "marked_cell_id": coord_to_cell_id(sample.evaluation.marked_coord),
                    "marker_role": str(sample.evaluation.marker_role),
                    "target_cell_id": (
                        ""
                        if sample.evaluation.target_coord is None
                        else coord_to_cell_id(sample.evaluation.target_coord)
                    ),
                    "target_color": str(sample.evaluation.target_color),
                    "annotation_entity_ids": [str(v) for v in sample.evaluation.annotation_entity_ids],
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
                    "rule_family": str(axes.rule_family),
                    "range_k": int(axes.range_k),
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "rule_family_probabilities": dict(axes.rule_family_probabilities),
                    "range_k_probabilities": dict(axes.range_k_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer": int(sample.evaluation.answer),
                    "target_answer_support": [int(v) for v in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "marker_role": str(sample.evaluation.marker_role),
                    "target_color": str(sample.evaluation.target_color),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
                "effective_cell_size_px": render_map.get("effective_cell_size_px"),
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "rule_family": str(axes.rule_family),
                "range_k": int(axes.range_k),
                "style_variant": str(axes.style_variant),
                "target_answer": int(sample.evaluation.answer),
                "target_answer_support": [int(v) for v in axes.target_answer_support],
                "board_size": int(BOARD_SIZE),
                "board_rows": serialize_board(sample.board),
                "construction_mode": str(sample.construction_mode),
                "occupied_count": int(sample.occupied_count),
                "marked_coord": [int(sample.evaluation.marked_coord[0]), int(sample.evaluation.marked_coord[1])],
                "marked_piece": marked_piece_payload,
                "marker_role": str(sample.evaluation.marker_role),
                "target_coord": target_coord_payload,
                "target_color": str(sample.evaluation.target_color),
                "target_color_name": color_name(sample.evaluation.target_color) if sample.evaluation.target_color else "",
                "legal_destination_coords": [[int(r), int(c)] for r, c in sample.evaluation.legal_destinations],
                "capture_coords": [[int(r), int(c)] for r, c in sample.evaluation.capture_coords],
                "annotation_kind": str(sample.evaluation.annotation_kind),
                "annotation_coords": [[int(r), int(c)] for r, c in sample.evaluation.annotation_coords],
                "annotation_entity_ids": [str(v) for v in sample.evaluation.annotation_entity_ids],
            },
            "witness_symbolic": {"type": "object_set", "ids": [str(v) for v in sample.evaluation.annotation_entity_ids]},
            "projected_annotation": projected_annotation,
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
            scene_id=SCENE_ID,
            query_id=str(axes.query_id),
        )


@register_task
class GamesChessVariantMarkedPieceDestinationCountTask(QuerySubsetTaskMixin, GamesChessVariantBoardTask):
    """Count marked-token destination squares matching a sampled visible-rule condition."""

    task_id = "task_games__chess_variant__marked_piece_destination_count"
    supported_query_ids = (
        "marked_piece_move_count",
        "marked_piece_capture_count",
    )


@register_task
class GamesChessVariantTargetSquareReacherCountTask(QuerySubsetTaskMixin, GamesChessVariantBoardTask):
    """Count same-side source pieces that can reach one marked target square."""

    task_id = "task_games__chess_variant__target_square_reacher_count"
    supported_query_ids = (
        "white_piece_reaches_target_count",
        "black_piece_reaches_target_count",
    )


__all__ = [
    "GamesChessVariantBoardTask",
    "GamesChessVariantMarkedPieceDestinationCountTask",
    "GamesChessVariantTargetSquareReacherCountTask",
]
