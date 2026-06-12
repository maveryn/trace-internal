"""Scene-local primitives for Ludo board roll-reasoning tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import group_default, required_group_defaults
from trace.tasks.shared.font_assets import font_role_trace, sample_font_family
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.games.shared.layout import apply_games_layout_jitter_to_bbox, resolve_games_layout_jitter
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.scene_style import (
    draw_panel_option_card,
    draw_panel_scene_chrome,
    make_panel_scene_background,
    resolve_game_panel_scene_style,
)
from trace.tasks.games.shared.text import draw_centered_game_text_traced
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "ludo_board"
SCENE_NAMESPACE = "games.ludo_board"
WINNING_ROLL_QUERY_ID = "winning_roll_value"
CAPTURE_ROLL_QUERY_ID = "capture_roll_option_label"
MOVE_RESULT_QUERY_ID = "move_result_option_label"
PLAYER_COLORS: Tuple[str, ...] = ("red", "green", "blue", "yellow")
STYLE_VARIANTS: Tuple[str, ...] = ("classic_bright", "ivory_board", "slate_table", "soft_plastic", "arcade_gloss")
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
Coord = Tuple[int, int]
BBox = Tuple[float, float, float, float]


MAIN_PATH: Tuple[Coord, ...] = (
    (6, 1), (6, 2), (6, 3), (6, 4), (6, 5),
    (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6),
    (0, 7),
    (0, 8), (1, 8), (2, 8), (3, 8), (4, 8), (5, 8),
    (6, 9), (6, 10), (6, 11), (6, 12), (6, 13), (6, 14),
    (7, 14),
    (8, 14), (8, 13), (8, 12), (8, 11), (8, 10), (8, 9),
    (9, 8), (10, 8), (11, 8), (12, 8), (13, 8), (14, 8),
    (14, 7),
    (14, 6), (13, 6), (12, 6), (11, 6), (10, 6), (9, 6),
    (8, 5), (8, 4), (8, 3), (8, 2), (8, 1), (8, 0),
    (7, 0), (6, 0),
)
START_COORDS: Dict[str, Coord] = {
    "red": (6, 1),
    "green": (1, 8),
    "yellow": (8, 13),
    "blue": (13, 6),
}
HOME_LANES: Dict[str, Tuple[Coord, ...]] = {
    "red": ((7, 1), (7, 2), (7, 3), (7, 4), (7, 5)),
    "green": ((1, 7), (2, 7), (3, 7), (4, 7), (5, 7)),
    "yellow": ((7, 13), (7, 12), (7, 11), (7, 10), (7, 9)),
    "blue": ((13, 7), (12, 7), (11, 7), (10, 7), (9, 7)),
}
HOME_ENTRY_COORDS: Dict[str, Coord] = {
    "red": (7, 0),
    "green": (0, 7),
    "yellow": (7, 14),
    "blue": (14, 7),
}
FLOW_ARROW_SPECS: Tuple[Tuple[Coord, Coord, str], ...] = (
    ((6, 2), (6, 3), "start_forward_red"),
    ((2, 8), (3, 8), "start_forward_green"),
    ((8, 12), (8, 11), "start_forward_yellow"),
    ((12, 6), (11, 6), "start_forward_blue"),
    ((6, 5), (5, 6), "corner_turn_top_left"),
    ((5, 8), (6, 9), "corner_turn_top_right"),
    ((8, 9), (9, 8), "corner_turn_bottom_right"),
    ((9, 6), (8, 5), "corner_turn_bottom_left"),
    ((7, 0), (7, 1), "home_entry_red"),
    ((0, 7), (1, 7), "home_entry_green"),
    ((7, 14), (7, 13), "home_entry_yellow"),
    ((14, 7), (13, 7), "home_entry_blue"),
)
FLOW_ARROW_CELLS: frozenset[Coord] = frozenset(coord for start, end, _role in FLOW_ARROW_SPECS for coord in (start, end))
YARD_BBOX_CELLS: Dict[str, Tuple[int, int, int, int]] = {
    "red": (0, 0, 6, 6),
    "green": (0, 9, 6, 15),
    "blue": (9, 0, 15, 6),
    "yellow": (9, 9, 15, 15),
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Ludo board scenes."""

    winning_roll_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    capture_distance_support: Tuple[int, ...] = tuple(range(1, 12))
    move_roll_total_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17)
    option_label_support: Tuple[str, ...] = OPTION_LABELS
    capture_option_count_support: Tuple[int, ...] = (4, 6)
    move_result_option_count_support: Tuple[int, ...] = (4, 5, 6)
    cell_size_min_px: int = 36
    cell_size_max_px: int = 48
    canvas_width: int = 920
    canvas_height: int = 980
    canvas_side_padding_px: int = 180
    canvas_vertical_padding_px: int = 210
    board_padding_px: int = 24
    grid_width_px: int = 2
    token_radius_fraction: float = 0.36
    flow_arrow_enabled: bool = True
    flow_arrow_width_px: int = 2
    option_card_width_px: int = 112
    option_card_height_px: int = 54
    option_card_gap_px: int = 10


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Ludo sample."""

    style_variant: str
    query_color: str
    target_color: str
    winning_roll: int
    capture_distance: int
    answer_option_label: str
    style_variant_probabilities: Dict[str, float]
    query_color_probabilities: Dict[str, float]
    target_color_probabilities: Dict[str, float]
    winning_roll_support: Tuple[int, ...]
    winning_roll_probabilities: Dict[str, float]
    capture_distance_support: Tuple[int, ...]
    capture_distance_probabilities: Dict[str, float]
    move_roll_total: int
    move_roll_total_support: Tuple[int, ...]
    move_roll_total_probabilities: Dict[str, float]
    option_count: int
    option_count_support: Tuple[int, ...]
    option_count_probabilities: Dict[str, float]
    option_label_support: Tuple[str, ...]
    option_label_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RollOption:
    """One image-drawn roll option."""

    label: str
    distance: int
    text: str


@dataclass(frozen=True)
class _DestinationOption:
    """One board-drawn destination option."""

    label: str
    coord: Coord


@dataclass(frozen=True)
class _Sample:
    """One symbolic Ludo sample."""

    query_id: str
    style_variant: str
    token_coords: Dict[str, Coord]
    query_color: str
    target_color: str | None
    winning_roll: int | None
    capture_distance: int | None
    move_roll_total: int | None
    roll_sequence: Tuple[int, ...]
    options: Tuple[_RollOption, ...]
    destination_options: Tuple[_DestinationOption, ...]
    answer: str | int
    construction_mode: str


@dataclass(frozen=True)
class _Theme:
    """Scene-local board theme while preserving semantic player colors."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    track_fill_rgb: Tuple[int, int, int]
    track_outline_rgb: Tuple[int, int, int]
    yard_inner_rgb: Tuple[int, int, int]
    token_outline_rgb: Tuple[int, int, int]
    token_highlight_rgb: Tuple[int, int, int]
    flow_arrow_rgb: Tuple[int, int, int]
    option_text_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered Ludo board plus trace-friendly maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class GeneratedComponents:
    """Rendered and prompted scene components before public output wrapping."""

    prompt: str
    prompt_variants: Dict[str, str]
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Image.Image
    trace_payload: Dict[str, Any]
    query_id: str


_DEFAULTS = _TaskDefaults()
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _path_index(coord: Coord) -> int:
    return int(MAIN_PATH.index(tuple(coord)))


def _color_rgb(color: str) -> Tuple[int, int, int]:
    colors = {
        "red": (221, 55, 61),
        "green": (45, 166, 85),
        "blue": (47, 98, 214),
        "yellow": (241, 199, 49),
    }
    return colors[str(color)]


def _soft_color(color: str, *, amount: float = 0.56) -> Tuple[int, int, int]:
    base = _color_rgb(str(color))
    return tuple(int(round((float(channel) * float(amount)) + (255.0 * (1.0 - float(amount))))) for channel in base)


def _theme_for_style(style_variant: str) -> Tuple[_Theme, Dict[str, Any]]:
    themes: dict[str, _Theme] = {
        "classic_bright": _Theme(
            board_fill_rgb=(242, 238, 220),
            board_border_rgb=(54, 59, 70),
            track_fill_rgb=(252, 250, 238),
            track_outline_rgb=(55, 61, 74),
            yard_inner_rgb=(255, 255, 246),
            token_outline_rgb=(35, 39, 50),
            token_highlight_rgb=(255, 255, 255),
            flow_arrow_rgb=(33, 39, 54),
            option_text_rgb=(31, 36, 48),
        ),
        "ivory_board": _Theme(
            board_fill_rgb=(235, 225, 199),
            board_border_rgb=(92, 77, 55),
            track_fill_rgb=(255, 249, 226),
            track_outline_rgb=(102, 86, 62),
            yard_inner_rgb=(255, 251, 234),
            token_outline_rgb=(70, 57, 42),
            token_highlight_rgb=(255, 255, 244),
            flow_arrow_rgb=(78, 59, 37),
            option_text_rgb=(61, 50, 38),
        ),
        "slate_table": _Theme(
            board_fill_rgb=(55, 65, 78),
            board_border_rgb=(220, 228, 236),
            track_fill_rgb=(229, 234, 238),
            track_outline_rgb=(39, 48, 60),
            yard_inner_rgb=(245, 248, 250),
            token_outline_rgb=(17, 24, 33),
            token_highlight_rgb=(255, 255, 255),
            flow_arrow_rgb=(18, 26, 38),
            option_text_rgb=(24, 31, 42),
        ),
        "soft_plastic": _Theme(
            board_fill_rgb=(224, 236, 232),
            board_border_rgb=(66, 96, 99),
            track_fill_rgb=(252, 253, 246),
            track_outline_rgb=(78, 111, 112),
            yard_inner_rgb=(255, 255, 249),
            token_outline_rgb=(42, 61, 65),
            token_highlight_rgb=(255, 255, 255),
            flow_arrow_rgb=(35, 72, 78),
            option_text_rgb=(35, 55, 58),
        ),
        "arcade_gloss": _Theme(
            board_fill_rgb=(38, 39, 73),
            board_border_rgb=(255, 221, 78),
            track_fill_rgb=(244, 247, 255),
            track_outline_rgb=(34, 38, 72),
            yard_inner_rgb=(255, 255, 250),
            token_outline_rgb=(12, 16, 35),
            token_highlight_rgb=(255, 255, 255),
            flow_arrow_rgb=(28, 34, 82),
            option_text_rgb=(23, 27, 54),
        ),
    }
    resolved = str(style_variant) if str(style_variant) in themes else "classic_bright"
    return themes[resolved], {
        "style_variant": str(resolved),
        "available_styles": list(STYLE_VARIANTS),
        "board_style_policy": "semantic_ludo_colors_with_scene_local_board_theme",
    }


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace_root: str,
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(namespace_root),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=f"{namespace_root}.{namespace}",
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(value) for value in supported),
    )


def resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
    query_id: str = "",
) -> _ResolvedAxes:
    style_variant, style_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=STYLE_VARIANTS,
    )
    query_color, query_color_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="query_color",
        explicit_key="query_color",
        weights_key="query_color_weights",
        balance_flag_key="balanced_query_color_sampling",
        supported=PLAYER_COLORS,
    )
    target_color, target_color_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="target_color",
        explicit_key="target_color",
        weights_key="target_color_weights",
        balance_flag_key="balanced_target_color_sampling",
        supported=PLAYER_COLORS,
    )
    if str(target_color) == str(query_color):
        index = (PLAYER_COLORS.index(str(query_color)) + 1) % len(PLAYER_COLORS)
        target_color = PLAYER_COLORS[index]
    winning_roll, winning_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="winning_roll_support",
        explicit_key="winning_roll",
        fallback_support=_DEFAULTS.winning_roll_support,
        namespace=f"{namespace}.winning_roll",
        balanced_flag_key="balanced_winning_roll_sampling",
        namespace_support_permutation=True,
    )
    winning_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="winning_roll_support",
        fallback=_DEFAULTS.winning_roll_support,
    )
    capture_distance, capture_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="capture_distance_support",
        explicit_key="capture_distance",
        fallback_support=_DEFAULTS.capture_distance_support,
        namespace=f"{namespace}.capture_distance",
        balanced_flag_key="balanced_capture_distance_sampling",
        namespace_support_permutation=True,
    )
    capture_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="capture_distance_support",
        fallback=_DEFAULTS.capture_distance_support,
    )
    move_roll_total, move_roll_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="move_roll_total_support",
        explicit_key="move_roll_total",
        fallback_support=_DEFAULTS.move_roll_total_support,
        namespace=f"{namespace}.move_roll_total",
        balanced_flag_key="balanced_move_roll_total_sampling",
        namespace_support_permutation=True,
    )
    move_roll_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="move_roll_total_support",
        fallback=_DEFAULTS.move_roll_total_support,
    )
    option_count = 0
    option_count_support: Tuple[int, ...] = tuple()
    option_count_probabilities: Dict[str, float] = {}
    if str(query_id) == CAPTURE_ROLL_QUERY_ID:
        option_count, option_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            support_key="capture_option_count_support",
            explicit_key="option_count",
            fallback_support=_DEFAULTS.capture_option_count_support,
            namespace=f"{namespace}.capture_option_count",
            balanced_flag_key="balanced_capture_option_count_sampling",
            namespace_support_permutation=True,
        )
        option_count_support = resolve_integer_support(
            params,
            gen_defaults=gen_defaults,
            key="capture_option_count_support",
            fallback=_DEFAULTS.capture_option_count_support,
        )
    elif str(query_id) == MOVE_RESULT_QUERY_ID:
        option_count, option_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            support_key="move_result_option_count_support",
            explicit_key="option_count",
            fallback_support=_DEFAULTS.move_result_option_count_support,
            namespace=f"{namespace}.move_result_option_count",
            balanced_flag_key="balanced_move_result_option_count_sampling",
            namespace_support_permutation=True,
        )
        option_count_support = resolve_integer_support(
            params,
            gen_defaults=gen_defaults,
            key="move_result_option_count_support",
            fallback=_DEFAULTS.move_result_option_count_support,
        )
    option_label_support = tuple(OPTION_LABELS[: int(option_count)]) if int(option_count) > 0 else tuple(OPTION_LABELS)
    answer_option_label, option_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="answer_option_label",
        explicit_key="answer_option_label",
        weights_key="answer_option_label_weights",
        balance_flag_key="balanced_answer_option_label_sampling",
        supported=option_label_support,
    )
    return _ResolvedAxes(
        style_variant=str(style_variant),
        query_color=str(query_color),
        target_color=str(target_color),
        winning_roll=int(winning_roll),
        capture_distance=int(capture_distance),
        answer_option_label=str(answer_option_label),
        style_variant_probabilities=dict(style_probs),
        query_color_probabilities=dict(query_color_probs),
        target_color_probabilities=dict(target_color_probs),
        winning_roll_support=tuple(int(value) for value in winning_support),
        winning_roll_probabilities=dict(winning_probs),
        capture_distance_support=tuple(int(value) for value in capture_support),
        capture_distance_probabilities=dict(capture_probs),
        move_roll_total=int(move_roll_total),
        move_roll_total_support=tuple(int(value) for value in move_roll_support),
        move_roll_total_probabilities=dict(move_roll_probs),
        option_count=int(option_count),
        option_count_support=tuple(int(value) for value in option_count_support),
        option_count_probabilities=dict(option_count_probabilities),
        option_label_support=tuple(option_label_support),
        option_label_probabilities=dict(option_probs),
    )


def _route_for_color(color: str) -> Tuple[Coord, ...]:
    start_index = _path_index(START_COORDS[str(color)])
    entry_index = _path_index(HOME_ENTRY_COORDS[str(color)])
    if int(entry_index) >= int(start_index):
        main_segment = MAIN_PATH[start_index : entry_index + 1]
    else:
        main_segment = MAIN_PATH[start_index:] + MAIN_PATH[: entry_index + 1]
    return tuple(main_segment) + tuple(HOME_LANES[str(color)])


def _roll_sequence_for_total(total: int) -> Tuple[int, ...]:
    total = int(total)
    if 1 <= total <= 6:
        return (int(total),)
    if 7 <= total <= 11:
        return (6, int(total - 6))
    if 13 <= total <= 17:
        return (6, 6, int(total - 12))
    raise ValueError("Ludo move total must be in 1..11 or 13..17")


def _roll_option_text(distance: int) -> str:
    distance = int(distance)
    if 1 <= distance <= 6:
        return str(distance)
    if 7 <= distance <= 11:
        return f"6 then {distance - 6}"
    raise ValueError("Ludo roll option distance must be in 1..11")


def _make_options(*, rng: Any, correct_distance: int, answer_label: str, option_labels: Sequence[str]) -> Tuple[_RollOption, ...]:
    correct_distance = int(correct_distance)
    labels = [str(label) for label in option_labels]
    correct_index = labels.index(str(answer_label))
    distractor_distances = [distance for distance in range(1, 12) if int(distance) != int(correct_distance)]
    rng.shuffle(distractor_distances)
    selected_distances = distractor_distances[: len(labels) - 1]
    options: list[_RollOption] = []
    distractor_cursor = 0
    for index, label in enumerate(labels):
        if index == correct_index:
            distance = int(correct_distance)
        else:
            distance = int(selected_distances[distractor_cursor])
            distractor_cursor += 1
        options.append(_RollOption(label=str(label), distance=int(distance), text=_roll_option_text(distance)))
    return tuple(options)


def _sample_other_token_coords(*, rng: Any, occupied: set[Coord], colors: Sequence[str]) -> Dict[str, Coord]:
    out: dict[str, Coord] = {}
    path = list(MAIN_PATH)
    for color in colors:
        rng.shuffle(path)
        for coord in path:
            if tuple(coord) not in occupied:
                occupied.add(tuple(coord))
                out[str(color)] = tuple(coord)
                break
        if str(color) not in out:
            raise ValueError("failed to place Ludo token")
    return out


def sample_winning_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    roll = int(axes.winning_roll)
    if roll < 1 or roll > 5:
        raise ValueError("winning roll must be in 1..5")
    lane = HOME_LANES[str(axes.query_color)]
    query_coord = tuple(lane[5 - int(roll)])
    occupied = {query_coord}
    other_colors = [color for color in PLAYER_COLORS if color != str(axes.query_color)]
    token_coords = {str(axes.query_color): query_coord}
    token_coords.update(_sample_other_token_coords(rng=rng, occupied=occupied, colors=other_colors))
    return _Sample(
        query_id=WINNING_ROLL_QUERY_ID,
        style_variant=str(axes.style_variant),
        token_coords=dict(token_coords),
        query_color=str(axes.query_color),
        target_color=None,
        winning_roll=int(roll),
        capture_distance=None,
        move_roll_total=None,
        roll_sequence=(),
        options=(),
        destination_options=(),
        answer=int(roll),
        construction_mode="target_conditioned_exact_finish_roll",
    )


def sample_capture_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    distance = int(axes.capture_distance)
    if distance < 1 or distance > 11:
        raise ValueError("capture distance must be in 1..11")
    start_indices = {_path_index(coord) for coord in START_COORDS.values()}
    for _attempt in range(200):
        mover_index = int(rng.randrange(len(MAIN_PATH)))
        target_index = (int(mover_index) + int(distance)) % len(MAIN_PATH)
        if target_index in start_indices:
            continue
        mover_coord = tuple(MAIN_PATH[mover_index])
        target_coord = tuple(MAIN_PATH[target_index])
        if mover_coord == target_coord:
            continue
        token_coords = {
            str(axes.query_color): mover_coord,
            str(axes.target_color): target_coord,
        }
        occupied = {mover_coord, target_coord}
        other_colors = [
            color
            for color in PLAYER_COLORS
            if color not in {str(axes.query_color), str(axes.target_color)}
        ]
        token_coords.update(_sample_other_token_coords(rng=rng, occupied=occupied, colors=other_colors))
        options = _make_options(
            rng=rng,
            correct_distance=int(distance),
            answer_label=str(axes.answer_option_label),
            option_labels=axes.option_label_support,
        )
        return _Sample(
            query_id=CAPTURE_ROLL_QUERY_ID,
            style_variant=str(axes.style_variant),
            token_coords=dict(token_coords),
            query_color=str(axes.query_color),
            target_color=str(axes.target_color),
            winning_roll=None,
            capture_distance=int(distance),
            move_roll_total=None,
            roll_sequence=(),
            options=tuple(options),
            destination_options=(),
            answer=str(axes.answer_option_label),
            construction_mode="target_conditioned_capture_roll_option",
        )
    raise ValueError("failed to construct Ludo capture sample")


def _make_destination_options(
    *,
    rng: Any,
    route: Sequence[Coord],
    current_index: int,
    final_coord: Coord,
    occupied: set[Coord],
    answer_label: str,
    option_labels: Sequence[str],
) -> Tuple[_DestinationOption, ...]:
    labels = [str(label) for label in option_labels]
    correct_index = labels.index(str(answer_label))
    candidates: list[Coord] = []
    seen = {tuple(final_coord), *{tuple(coord) for coord in occupied}}
    preferred_indices = [int(current_index) + offset for offset in (-8, -6, -4, -2, 2, 4, 6, 8, 10, 12)]
    for index in preferred_indices:
        if 0 <= int(index) < len(route):
            coord = tuple(route[int(index)])
            if coord not in seen:
                candidates.append(coord)
                seen.add(coord)
    random_pool = [tuple(coord) for coord in route if tuple(coord) not in seen]
    rng.shuffle(random_pool)
    candidates.extend(random_pool[: max(0, len(labels) - 1 - len(candidates))])
    if len(candidates) < len(labels) - 1:
        raise ValueError("failed to construct enough Ludo destination options")
    options: list[_DestinationOption] = []
    distractor_cursor = 0
    for index, label in enumerate(labels):
        if int(index) == int(correct_index):
            coord = tuple(final_coord)
        else:
            coord = tuple(candidates[distractor_cursor])
            distractor_cursor += 1
        options.append(_DestinationOption(label=str(label), coord=coord))
    return tuple(options)


def sample_move_result_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    total = int(axes.move_roll_total)
    roll_sequence = _roll_sequence_for_total(total)
    route = _route_for_color(str(axes.query_color))
    valid_indices = [index for index in range(0, len(route) - int(total))]
    rng.shuffle(valid_indices)
    for current_index in valid_indices[:200]:
        start_coord = tuple(route[int(current_index)])
        final_coord = tuple(route[int(current_index) + int(total)])
        token_coords = {str(axes.query_color): start_coord}
        reserved = {start_coord, final_coord}
        other_colors = [color for color in PLAYER_COLORS if color != str(axes.query_color)]
        token_coords.update(_sample_other_token_coords(rng=rng, occupied=reserved, colors=other_colors))
        options = _make_destination_options(
            rng=rng,
            route=route,
            current_index=int(current_index),
            final_coord=final_coord,
            occupied={tuple(coord) for coord in token_coords.values()},
            answer_label=str(axes.answer_option_label),
            option_labels=axes.option_label_support,
        )
        return _Sample(
            query_id=MOVE_RESULT_QUERY_ID,
            style_variant=str(axes.style_variant),
            token_coords=dict(token_coords),
            query_color=str(axes.query_color),
            target_color=None,
            winning_roll=None,
            capture_distance=None,
            move_roll_total=int(total),
            roll_sequence=tuple(int(value) for value in roll_sequence),
            options=(),
            destination_options=tuple(options),
            answer=str(axes.answer_option_label),
            construction_mode="target_conditioned_move_result_option",
        )
    raise ValueError("failed to construct Ludo move-result sample")


def _cell_bbox(board_bbox: Sequence[float], cell_size: float, coord: Coord) -> BBox:
    row, col = int(coord[0]), int(coord[1])
    x0 = float(board_bbox[0]) + (float(col) * float(cell_size))
    y0 = float(board_bbox[1]) + (float(row) * float(cell_size))
    return (round(x0, 3), round(y0, 3), round(x0 + float(cell_size), 3), round(y0 + float(cell_size), 3))


def _bbox_center(bbox: Sequence[float]) -> Tuple[float, float]:
    return (0.5 * (float(bbox[0]) + float(bbox[2])), 0.5 * (float(bbox[1]) + float(bbox[3])))


def _draw_cell(draw: ImageDraw.ImageDraw, bbox: Sequence[float], *, fill: Sequence[int], outline: Sequence[int], width: int) -> None:
    draw.rectangle(tuple(float(v) for v in bbox), fill=tuple(int(v) for v in fill[:3]) + (255,), outline=tuple(int(v) for v in outline[:3]) + (255,), width=max(1, int(width)))


def _draw_token(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    color: str,
    theme: _Theme,
    width: int,
) -> BBox:
    cx, cy = _bbox_center(bbox)
    radius = 0.5 * min(float(bbox[2]) - float(bbox[0]), float(bbox[3]) - float(bbox[1])) * 0.74
    token_bbox = (
        round(float(cx) - radius, 3),
        round(float(cy) - radius, 3),
        round(float(cx) + radius, 3),
        round(float(cy) + radius, 3),
    )
    draw.ellipse(
        token_bbox,
        fill=_color_rgb(str(color)) + (255,),
        outline=tuple(theme.token_outline_rgb) + (255,),
        width=max(2, int(width)),
    )
    shine_radius = max(3.0, radius * 0.26)
    draw.ellipse(
        (
            float(cx) - radius * 0.42,
            float(cy) - radius * 0.48,
            float(cx) - radius * 0.42 + shine_radius,
            float(cy) - radius * 0.48 + shine_radius,
        ),
        fill=tuple(theme.token_highlight_rgb) + (95,),
    )
    return token_bbox


def _draw_flow_arrow(
    draw: ImageDraw.ImageDraw,
    *,
    start_cell_bbox: Sequence[float],
    end_cell_bbox: Sequence[float],
    role: str,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    width: int,
) -> Dict[str, Any]:
    start_center = _bbox_center(start_cell_bbox)
    end_center = _bbox_center(end_cell_bbox)
    dx = float(end_center[0]) - float(start_center[0])
    dy = float(end_center[1]) - float(start_center[1])
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    unit = min(
        float(start_cell_bbox[2]) - float(start_cell_bbox[0]),
        float(start_cell_bbox[3]) - float(start_cell_bbox[1]),
        float(end_cell_bbox[2]) - float(end_cell_bbox[0]),
        float(end_cell_bbox[3]) - float(end_cell_bbox[1]),
    )
    extension = 0.18 * unit
    head_len = 0.21 * unit
    head_half_width = 0.16 * unit
    start = (float(start_center[0]) - ux * extension, float(start_center[1]) - uy * extension)
    end = (float(end_center[0]) + ux * extension, float(end_center[1]) + uy * extension)
    head_base = (end[0] - ux * head_len, end[1] - uy * head_len)
    head_points = (
        end,
        (head_base[0] + px * head_half_width, head_base[1] + py * head_half_width),
        (head_base[0] - px * head_half_width, head_base[1] - py * head_half_width),
    )
    outline_rgba = tuple(int(v) for v in outline_rgb[:3]) + (235,)
    fill_rgba = tuple(int(v) for v in fill_rgb[:3]) + (225,)
    line_width = max(3, int(width) + 2)
    draw.line((start, end), fill=outline_rgba, width=line_width + 2)
    draw.line((start, end), fill=fill_rgba, width=line_width)
    draw.polygon(head_points, fill=fill_rgba, outline=outline_rgba)
    points = (start, end) + head_points
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return {
        "start_center_px": [round(float(start_center[0]), 3), round(float(start_center[1]), 3)],
        "end_center_px": [round(float(end_center[0]), 3), round(float(end_center[1]), 3)],
        "bbox_px": [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)],
        "points_px": [[round(float(x), 3), round(float(y), 3)] for x, y in points],
        "role": str(role),
    }


def _draw_ludo_board(
    draw: ImageDraw.ImageDraw,
    *,
    board_bbox: Sequence[float],
    cell_size: float,
    theme: _Theme,
    grid_width: int,
    flow_arrow_enabled: bool,
    flow_arrow_width: int,
) -> Dict[str, Any]:
    main_set = set(MAIN_PATH)
    lane_cells = {coord: color for color, lane in HOME_LANES.items() for coord in lane}
    board_bg_bbox = tuple(float(value) for value in board_bbox)
    draw.rounded_rectangle(
        board_bg_bbox,
        radius=max(12, int(round(float(cell_size) * 0.35))),
        fill=tuple(theme.board_fill_rgb) + (255,),
        outline=tuple(theme.board_border_rgb) + (255,),
        width=max(2, int(grid_width) + 1),
    )
    for color, cells in YARD_BBOX_CELLS.items():
        r0, c0, r1, c1 = cells
        yard_bbox = (
            float(board_bbox[0]) + c0 * float(cell_size),
            float(board_bbox[1]) + r0 * float(cell_size),
            float(board_bbox[0]) + c1 * float(cell_size),
            float(board_bbox[1]) + r1 * float(cell_size),
        )
        draw.rectangle(yard_bbox, fill=_soft_color(color, amount=0.72) + (255,), outline=tuple(theme.board_border_rgb) + (255,), width=max(1, int(grid_width)))
        inner_pad = float(cell_size) * 0.82
        inner_bbox = (
            yard_bbox[0] + inner_pad,
            yard_bbox[1] + inner_pad,
            yard_bbox[2] - inner_pad,
            yard_bbox[3] - inner_pad,
        )
        draw.rounded_rectangle(
            inner_bbox,
            radius=max(10, int(round(float(cell_size) * 0.35))),
            fill=tuple(theme.yard_inner_rgb) + (245,),
            outline=tuple(theme.track_outline_rgb) + (255,),
            width=max(1, int(grid_width)),
        )
        for dy in (0.32, 0.68):
            for dx in (0.32, 0.68):
                cx = inner_bbox[0] + (inner_bbox[2] - inner_bbox[0]) * dx
                cy = inner_bbox[1] + (inner_bbox[3] - inner_bbox[1]) * dy
                half_side = float(cell_size) * 0.28
                slot_bbox = (cx - half_side, cy - half_side, cx + half_side, cy + half_side)
                draw.rounded_rectangle(
                    slot_bbox,
                    radius=max(3, int(round(float(cell_size) * 0.08))),
                    fill=_soft_color(color, amount=0.48) + (245,),
                    outline=tuple(theme.track_outline_rgb) + (190,),
                    width=max(1, int(grid_width)),
                )

    for coord in sorted(main_set):
        fill = theme.track_fill_rgb
        for color, start in START_COORDS.items():
            if tuple(coord) == tuple(start):
                fill = _soft_color(color, amount=0.85)
        _draw_cell(
            draw,
            _cell_bbox(board_bbox, cell_size, coord),
            fill=fill,
            outline=theme.track_outline_rgb,
            width=max(1, int(grid_width)),
        )
    for coord, color in lane_cells.items():
        _draw_cell(
            draw,
            _cell_bbox(board_bbox, cell_size, coord),
            fill=_soft_color(color, amount=0.72),
            outline=theme.track_outline_rgb,
            width=max(1, int(grid_width)),
        )

    flow_arrow_markers: list[dict[str, Any]] = []
    if bool(flow_arrow_enabled):
        for start_coord, end_coord, role in FLOW_ARROW_SPECS:
            marker = _draw_flow_arrow(
                draw,
                start_cell_bbox=_cell_bbox(board_bbox, cell_size, start_coord),
                end_cell_bbox=_cell_bbox(board_bbox, cell_size, end_coord),
                role=str(role),
                fill_rgb=theme.flow_arrow_rgb,
                outline_rgb=theme.track_fill_rgb,
                width=max(1, int(flow_arrow_width)),
            )
            marker["start_coord"] = [int(start_coord[0]), int(start_coord[1])]
            marker["end_coord"] = [int(end_coord[0]), int(end_coord[1])]
            flow_arrow_markers.append(marker)

    finish_bbox = (
        float(board_bbox[0]) + 6.0 * float(cell_size),
        float(board_bbox[1]) + 6.0 * float(cell_size),
        float(board_bbox[0]) + 9.0 * float(cell_size),
        float(board_bbox[1]) + 9.0 * float(cell_size),
    )
    fx = 0.5 * (finish_bbox[0] + finish_bbox[2])
    fy = 0.5 * (finish_bbox[1] + finish_bbox[3])
    triangles = {
        "red": ((finish_bbox[0], finish_bbox[0] * 0 + finish_bbox[1]), (finish_bbox[0], finish_bbox[3]), (fx, fy)),
        "green": ((finish_bbox[0], finish_bbox[1]), (finish_bbox[2], finish_bbox[1]), (fx, fy)),
        "yellow": ((finish_bbox[2], finish_bbox[1]), (finish_bbox[2], finish_bbox[3]), (fx, fy)),
        "blue": ((finish_bbox[0], finish_bbox[3]), (finish_bbox[2], finish_bbox[3]), (fx, fy)),
    }
    for color, points in triangles.items():
        draw.polygon(points, fill=_soft_color(color, amount=0.84) + (255,), outline=tuple(theme.track_outline_rgb) + (255,))
    draw.rectangle(finish_bbox, outline=tuple(theme.track_outline_rgb) + (255,), width=max(1, int(grid_width) + 1))
    return {
        "finish_bbox_px": [round(float(v), 3) for v in finish_bbox],
        "flow_arrow_markers_px": [dict(marker) for marker in flow_arrow_markers],
    }


def _draw_options(
    draw: ImageDraw.ImageDraw,
    *,
    options: Sequence[_RollOption],
    canvas_width: int,
    option_top: float,
    card_width: int,
    card_height: int,
    card_gap: int,
    panel_style: Any,
    theme: _Theme,
    font_family: str,
    instance_seed: int,
    namespace: str,
) -> Dict[str, List[float]]:
    option_bboxes: dict[str, list[float]] = {}
    if not options:
        return option_bboxes
    label_font = load_font(max(15, int(round(float(card_height) * 0.34))), bold=True, font_family=font_family)
    text_font = load_font(max(13, int(round(float(card_height) * 0.28))), bold=True, font_family=font_family)
    total_width = (len(options) * int(card_width)) + ((len(options) - 1) * int(card_gap))
    left = 0.5 * (float(canvas_width) - float(total_width))
    for index, option in enumerate(options):
        x0 = left + (float(index) * float(card_width + card_gap))
        bbox = (x0, float(option_top), x0 + float(card_width), float(option_top) + float(card_height))
        draw_panel_option_card(draw, bbox=tuple(int(round(v)) for v in bbox), style=panel_style, radius=10, border_width=2)
        label_badge = (bbox[0] + 6.0, bbox[1] + 6.0, bbox[0] + 30.0, bbox[1] + 30.0)
        draw.ellipse(label_badge, fill=(255, 255, 255, 245), outline=tuple(theme.track_outline_rgb) + (255,), width=1)
        draw_centered_game_text_traced(
            draw,
            center=_bbox_center(label_badge),
            text=str(option.label),
            font=label_font,
            fill_rgb=theme.option_text_rgb,
            surface_rgbs=((255, 255, 255),),
            role="option_label",
            required=True,
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.option_label.{option.label}",
        )
        draw_centered_game_text_traced(
            draw,
            center=(bbox[0] + (0.60 * float(card_width)), bbox[1] + (0.53 * float(card_height))),
            text=str(option.text),
            font=text_font,
            fill_rgb=theme.option_text_rgb,
            surface_rgbs=((255, 255, 255), panel_style.panel_fill_rgb),
            role="option_text",
            required=True,
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.option_text.{option.label}",
        )
        option_bboxes[str(option.label)] = [round(float(value), 3) for value in bbox]
    return option_bboxes


def _draw_destination_options(
    draw: ImageDraw.ImageDraw,
    *,
    destination_options: Sequence[_DestinationOption],
    board_bbox: Sequence[float],
    cell_size: float,
    theme: _Theme,
    font_family: str,
    instance_seed: int,
    namespace: str,
) -> Dict[str, Dict[str, List[float]]]:
    cell_bboxes: dict[str, list[float]] = {}
    text_bboxes: dict[str, list[float]] = {}
    centers: dict[str, list[float]] = {}
    if not destination_options:
        return {"cell_bboxes": cell_bboxes, "text_bboxes": text_bboxes, "centers": centers}
    font = load_font(max(17, int(round(float(cell_size) * 0.48))), bold=True, font_family=font_family)
    surface_rgbs = (
        theme.track_fill_rgb,
        _soft_color("red", amount=0.72),
        _soft_color("green", amount=0.72),
        _soft_color("yellow", amount=0.72),
        _soft_color("blue", amount=0.72),
    )
    for option in destination_options:
        cell_bbox = _cell_bbox(board_bbox, float(cell_size), tuple(option.coord))
        center = _bbox_center(cell_bbox)
        record = draw_centered_game_text_traced(
            draw,
            center=center,
            text=str(option.label),
            font=font,
            fill_rgb=theme.option_text_rgb,
            stroke_width=1,
            role="board_mark",
            required=True,
            surface_rgbs=surface_rgbs,
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.destination_option.{option.label}",
        )
        text_bbox = record.get("bbox_px")
        cell_bboxes[str(option.label)] = [round(float(value), 3) for value in cell_bbox]
        centers[str(option.label)] = [round(float(center[0]), 3), round(float(center[1]), 3)]
        if isinstance(text_bbox, list) and len(text_bbox) == 4:
            text_bboxes[str(option.label)] = [round(float(value), 3) for value in text_bbox]
        else:
            text_bboxes[str(option.label)] = list(cell_bboxes[str(option.label)])
    return {"cell_bboxes": cell_bboxes, "text_bboxes": text_bboxes, "centers": centers}


def _draw_roll_sequence(
    draw: ImageDraw.ImageDraw,
    *,
    roll_sequence: Sequence[int],
    canvas_width: int,
    option_top: float,
    card_height: int,
    panel_style: Any,
    theme: _Theme,
    font_family: str,
    instance_seed: int,
    namespace: str,
) -> Dict[str, Any]:
    if not roll_sequence:
        return {}
    box_size = max(34, int(round(float(card_height) * 0.70)))
    gap = max(8, int(round(float(box_size) * 0.22)))
    total_width = (len(roll_sequence) * int(box_size)) + ((len(roll_sequence) - 1) * int(gap))
    left = 0.5 * (float(canvas_width) - float(total_width))
    top = float(option_top) + max(0.0, 0.5 * (float(card_height) - float(box_size)))
    font = load_font(max(16, int(round(float(box_size) * 0.48))), bold=True, font_family=font_family)
    sequence_bbox = (left, top, left + total_width, top + box_size)
    box_bboxes: list[list[float]] = []
    for index, value in enumerate(roll_sequence):
        x0 = left + (float(index) * float(box_size + gap))
        bbox = (x0, top, x0 + float(box_size), top + float(box_size))
        draw.rounded_rectangle(
            bbox,
            radius=max(6, int(round(float(box_size) * 0.16))),
            fill=tuple(panel_style.panel_fill_rgb) + (245,),
            outline=tuple(theme.track_outline_rgb) + (255,),
            width=2,
        )
        draw_centered_game_text_traced(
            draw,
            center=_bbox_center(bbox),
            text=str(int(value)),
            font=font,
            fill_rgb=theme.option_text_rgb,
            stroke_width=1,
            role="readout",
            required=True,
            surface_rgbs=(panel_style.panel_fill_rgb,),
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.roll_sequence.{int(index)}",
        )
        box_bboxes.append([round(float(coord), 3) for coord in bbox])
    return {
        "bbox_px": [round(float(value), 3) for value in sequence_bbox],
        "box_bboxes_px": box_bboxes,
        "values": [int(value) for value in roll_sequence],
    }


def _render_scene(
    *,
    sample: _Sample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    namespace: str,
) -> _RenderedScene:
    from trace.core.seed import spawn_rng

    rng = spawn_rng(int(instance_seed), f"{namespace}.render")
    cell_min = int(params.get("cell_size_min_px", group_default(render_defaults, "cell_size_min_px", _DEFAULTS.cell_size_min_px)))
    cell_max = int(params.get("cell_size_max_px", group_default(render_defaults, "cell_size_max_px", _DEFAULTS.cell_size_max_px)))
    cell_size = int(rng.randint(min(cell_min, cell_max), max(cell_min, cell_max)))
    board_size = int(cell_size) * 15
    card_width = int(params.get("option_card_width_px", group_default(render_defaults, "option_card_width_px", _DEFAULTS.option_card_width_px)))
    card_height = int(params.get("option_card_height_px", group_default(render_defaults, "option_card_height_px", _DEFAULTS.option_card_height_px)))
    card_gap = int(params.get("option_card_gap_px", group_default(render_defaults, "option_card_gap_px", _DEFAULTS.option_card_gap_px)))
    has_options = bool(sample.options)
    has_roll_sequence = bool(sample.roll_sequence)
    has_bottom_area = bool(has_options or has_roll_sequence)
    side_padding = int(params.get("canvas_side_padding_px", group_default(render_defaults, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px)))
    vertical_padding = int(params.get("canvas_vertical_padding_px", group_default(render_defaults, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px)))
    options_height = (card_height + 34) if has_bottom_area else 0
    option_panel_count = len(sample.options) if has_options else 0
    option_panel_width = (
        (int(option_panel_count) * card_width) + ((int(option_panel_count) - 1) * card_gap) + 80
        if int(option_panel_count) > 0
        else 0
    )
    canvas_width = max(int(board_size + side_padding), int(option_panel_width))
    canvas_width = min(int(params.get("canvas_width", group_default(render_defaults, "canvas_width", _DEFAULTS.canvas_width))), int(canvas_width))
    canvas_height = min(
        int(params.get("canvas_height", group_default(render_defaults, "canvas_height", _DEFAULTS.canvas_height))),
        int(board_size + vertical_padding + options_height),
    )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.panel_scene_style",
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(render_defaults, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(render_defaults, "panel_scene_palette_weights", None)),
    )
    image, background_meta = make_panel_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=panel_style,
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme, theme_meta = _theme_for_style(str(axes.style_variant))
    option_area_height = float(card_height + 34) if has_bottom_area else 0.0
    board_bbox = (
        round(0.5 * (float(canvas_width) - float(board_size)), 3),
        round(0.5 * (float(canvas_height) - option_area_height - float(board_size)), 3),
        round(0.5 * (float(canvas_width) + float(board_size)), 3),
        round(0.5 * (float(canvas_height) - option_area_height + float(board_size)), 3),
    )
    layout_jitter = resolve_games_layout_jitter(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.layout",
    )
    board_bbox, _dx, _dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height - option_area_height),
        jitter=layout_jitter,
    )
    board_padding = int(params.get("board_padding_px", group_default(render_defaults, "board_padding_px", _DEFAULTS.board_padding_px)))
    panel_bbox = (
        int(round(float(board_bbox[0]) - float(board_padding))),
        int(round(float(board_bbox[1]) - float(board_padding))),
        int(round(float(board_bbox[2]) + float(board_padding))),
        int(round(float(board_bbox[3]) + float(board_padding))),
    )
    draw_panel_scene_chrome(draw, bbox=panel_bbox, style=panel_style, radius=24, border_width=2)
    grid_width = int(params.get("grid_width_px", group_default(render_defaults, "grid_width_px", _DEFAULTS.grid_width_px)))
    flow_arrow_enabled = bool(params.get("flow_arrow_enabled", group_default(render_defaults, "flow_arrow_enabled", _DEFAULTS.flow_arrow_enabled)))
    flow_arrow_width = int(params.get("flow_arrow_width_px", group_default(render_defaults, "flow_arrow_width_px", _DEFAULTS.flow_arrow_width_px)))
    board_meta = _draw_ludo_board(
        draw,
        board_bbox=board_bbox,
        cell_size=float(cell_size),
        theme=theme,
        grid_width=max(1, int(grid_width)),
        flow_arrow_enabled=bool(flow_arrow_enabled),
        flow_arrow_width=max(1, int(flow_arrow_width)),
    )
    token_bboxes: dict[str, list[float]] = {}
    token_centers: dict[str, list[float]] = {}
    entities: list[dict[str, Any]] = []
    for color in PLAYER_COLORS:
        coord = tuple(sample.token_coords[str(color)])
        cell_bbox = _cell_bbox(board_bbox, float(cell_size), coord)
        token_bbox = _draw_token(draw, bbox=cell_bbox, color=str(color), theme=theme, width=max(2, int(grid_width) + 1))
        center = _bbox_center(token_bbox)
        token_id = f"token_{color}"
        token_bboxes[token_id] = [round(float(value), 3) for value in token_bbox]
        token_centers[token_id] = [round(float(center[0]), 3), round(float(center[1]), 3)]
        entities.append(
            {
                "entity_id": str(token_id),
                "entity_type": "ludo_token",
                "color": str(color),
                "coord": [int(coord[0]), int(coord[1])],
                "center_px": list(token_centers[token_id]),
                "bbox_px": list(token_bboxes[token_id]),
            }
        )
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.labels",
        params=params,
        explicit_key="label_font_family",
        weights_key="label_font_family_weights",
    )
    destination_maps = _draw_destination_options(
        draw,
        destination_options=sample.destination_options,
        board_bbox=board_bbox,
        cell_size=float(cell_size),
        theme=theme,
        font_family=str(font_family),
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    for option in sample.destination_options:
        label = str(option.label)
        entities.append(
            {
                "entity_id": f"destination_option_{label}",
                "entity_type": "ludo_destination_option",
                "label": label,
                "coord": [int(option.coord[0]), int(option.coord[1])],
                "center_px": list(destination_maps["centers"].get(label, [])),
                "bbox_px": list(destination_maps["cell_bboxes"].get(label, [])),
            }
        )
    option_top = float(board_bbox[3]) + 24.0
    option_bboxes = {}
    roll_sequence_map: dict[str, Any] = {}
    if has_options:
        option_bboxes = _draw_options(
            draw,
            options=sample.options,
            canvas_width=int(canvas_width),
            option_top=float(option_top),
            card_width=int(card_width),
            card_height=int(card_height),
            card_gap=int(card_gap),
            panel_style=panel_style,
            theme=theme,
            font_family=str(font_family),
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
    elif has_roll_sequence:
        roll_sequence_map = _draw_roll_sequence(
            draw,
            roll_sequence=sample.roll_sequence,
            canvas_width=int(canvas_width),
            option_top=float(option_top),
            card_height=int(card_height),
            panel_style=panel_style,
            theme=theme,
            font_family=str(font_family),
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
    render_map = {
        "board_bbox_px": [round(float(value), 3) for value in board_bbox],
        "finish_bbox_px": list(board_meta["finish_bbox_px"]),
        "flow_arrow_markers_px": [dict(marker) for marker in board_meta.get("flow_arrow_markers_px", [])],
        "token_bboxes_px": dict(token_bboxes),
        "token_centers_px": dict(token_centers),
        "option_bboxes_px": dict(option_bboxes),
        "destination_option_cell_bboxes_px": dict(destination_maps["cell_bboxes"]),
        "destination_option_text_bboxes_px": dict(destination_maps["text_bboxes"]),
        "destination_option_centers_px": dict(destination_maps["centers"]),
        "roll_sequence_px": dict(roll_sequence_map),
        "layout_jitter": dict(resolved_jitter),
        "effective_cell_size_px": int(cell_size),
        "effective_board_size_px": int(board_size),
        "label_font": font_role_trace(str(font_family), role="readout"),
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=render_map,
        style_meta={
            "panel_scene_style": dict(panel_style_meta),
            "ludo_board_style": dict(theme_meta),
            "label_font": font_role_trace(str(font_family), role="readout"),
        },
        background_meta=dict(background_meta),
    )


def _json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) == CAPTURE_ROLL_QUERY_ID:
        annotation = {"mover_token": [100, 200, 130, 230], "target_token": [260, 200, 290, 230]}
        return (
            json.dumps({"annotation": annotation, "answer": "C"}, separators=(",", ":"), ensure_ascii=True),
            json.dumps({"answer": "C"}, separators=(",", ":"), ensure_ascii=True),
        )
    if str(query_id) == MOVE_RESULT_QUERY_ID:
        annotation = {
            "moving_token": [100, 200, 130, 230],
            "roll_sequence": [180, 760, 285, 810],
            "destination_cell": [320, 260, 365, 305],
        }
        return (
            json.dumps({"annotation": annotation, "answer": "D"}, separators=(",", ":"), ensure_ascii=True),
            json.dumps({"answer": "D"}, separators=(",", ":"), ensure_ascii=True),
        )
    annotation = {"token": [100, 200, 130, 230], "finish": [320, 320, 410, 410]}
    return (
        json.dumps({"annotation": annotation, "answer": 4}, separators=(",", ":"), ensure_ascii=True),
        json.dumps({"answer": 4}, separators=(",", ":"), ensure_ascii=True),
    )


def _build_prompt(
    *,
    sample: _Sample,
    query_id: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    answer_hint_key = f"answer_hint_{str(query_id)}"
    annotation_hint_key = f"annotation_hint_{str(query_id)}"
    required_keys = [
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        "object_description",
        answer_hint_key,
        annotation_hint_key,
    ]
    if str(query_id) == WINNING_ROLL_QUERY_ID:
        required_keys.append("exact_finish_rule_text")
    elif str(query_id) == CAPTURE_ROLL_QUERY_ID:
        required_keys.append("capture_option_rule_text")
    else:
        required_keys.append("move_sequence_rule_text")
    prompt_defaults = required_group_defaults(
        prompt_defaults,
        tuple(required_keys),
        context=f"prompt defaults for {SCENE_ID}",
    )
    json_example, json_example_answer_only = _json_examples(str(query_id))
    dynamic_slots = {
        "object_description": str(prompt_defaults["object_description"]),
        "query_color": str(sample.query_color),
        "target_color": "" if sample.target_color is None else str(sample.target_color),
        "exact_finish_rule_text": str(prompt_defaults.get("exact_finish_rule_text", "")),
        "capture_option_rule_text": str(prompt_defaults.get("capture_option_rule_text", "")),
        "move_sequence_rule_text": str(prompt_defaults.get("move_sequence_rule_text", "")),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[answer_hint_key]),
        "annotation_hint": str(prompt_defaults[annotation_hint_key]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots=dynamic_slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }


def _annotation_for_sample(sample: _Sample, rendered: _RenderedScene) -> Tuple[TypedValue, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    token_bboxes = rendered.render_map["token_bboxes_px"]
    if str(sample.query_id) == CAPTURE_ROLL_QUERY_ID:
        assert sample.target_color is not None
        annotation_map = {
            "mover_token": list(token_bboxes[f"token_{sample.query_color}"]),
            "target_token": list(token_bboxes[f"token_{sample.target_color}"]),
        }
        annotation_ids = {
            "mover_token": f"token_{sample.query_color}",
            "target_token": f"token_{sample.target_color}",
        }
    elif str(sample.query_id) == MOVE_RESULT_QUERY_ID:
        answer_label = str(sample.answer)
        annotation_map = {
            "moving_token": list(token_bboxes[f"token_{sample.query_color}"]),
            "roll_sequence": list(rendered.render_map["roll_sequence_px"]["bbox_px"]),
            "destination_cell": list(rendered.render_map["destination_option_cell_bboxes_px"][answer_label]),
        }
        annotation_ids = {
            "moving_token": f"token_{sample.query_color}",
            "roll_sequence": "roll_sequence",
            "destination_cell": f"destination_option_{answer_label}",
        }
    else:
        annotation_map = {
            "token": list(token_bboxes[f"token_{sample.query_color}"]),
            "finish": list(rendered.render_map["finish_bbox_px"]),
        }
        annotation_ids = {"token": f"token_{sample.query_color}", "finish": "finish"}
    return (
        TypedValue(type="keyed_bbox_map", value=dict(annotation_map)),
        {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_map),
            "pixel_keyed_bbox_map": dict(annotation_map),
        },
        {"type": "keyed_bbox_map", "ids": dict(annotation_ids)},
        dict(annotation_ids),
    )


def build_components(
    *,
    query_id: str,
    sampled: _Sample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    namespace: str,
) -> GeneratedComponents:
    rendered = _render_scene(
        sample=sampled,
        axes=axes,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        namespace=str(namespace),
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    prompt, prompt_variants, prompt_meta = _build_prompt(
        sample=sampled,
        query_id=str(query_id),
        prompt_defaults=prompt_defaults,
        instance_seed=int(instance_seed),
    )
    if str(query_id) == WINNING_ROLL_QUERY_ID:
        answer_gt = TypedValue(type="integer", value=int(sampled.answer))
    elif str(query_id) == MOVE_RESULT_QUERY_ID:
        answer_gt = TypedValue(type="option_letter", value=str(sampled.answer))
    else:
        answer_gt = TypedValue(type="string", value=str(sampled.answer))
    annotation_gt, projected_annotation, witness_symbolic, annotation_entity_ids = _annotation_for_sample(sampled, rendered)
    trace_payload = {
        "scene_ir": {
            "scene_kind": "games_ludo_board",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "query_color": str(sampled.query_color),
                "target_color": sampled.target_color,
                "style_variant": str(sampled.style_variant),
                "annotation_entity_ids": dict(annotation_entity_ids),
            },
        },
        "query_spec": {
            "query_id": str(query_id),
            "template_id": str(prompt_meta["bundle_id"]),
            "prompt_variant": dict(prompt_meta["prompt_variant"]),
            "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
            "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
            "params": {
                "style_variant": str(axes.style_variant),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
                "query_color": str(axes.query_color),
                "query_color_support": list(PLAYER_COLORS),
                "query_color_probabilities": dict(axes.query_color_probabilities),
                "target_color": str(axes.target_color),
                "target_color_support": list(PLAYER_COLORS),
                "target_color_probabilities": dict(axes.target_color_probabilities),
                "winning_roll": int(axes.winning_roll),
                "winning_roll_support": [int(value) for value in axes.winning_roll_support],
                "winning_roll_probabilities": dict(axes.winning_roll_probabilities),
                "capture_distance": int(axes.capture_distance),
                "capture_distance_support": [int(value) for value in axes.capture_distance_support],
                "capture_distance_probabilities": dict(axes.capture_distance_probabilities),
                "move_roll_total": int(axes.move_roll_total),
                "move_roll_total_support": [int(value) for value in axes.move_roll_total_support],
                "move_roll_total_probabilities": dict(axes.move_roll_total_probabilities),
                "option_count": int(axes.option_count),
                "option_count_support": [int(value) for value in axes.option_count_support],
                "option_count_probabilities": dict(axes.option_count_probabilities),
                "answer_option_label": str(axes.answer_option_label),
                "answer_option_label_support": list(axes.option_label_support),
                "answer_option_label_probabilities": dict(axes.option_label_probabilities),
            },
        },
        "render_spec": {
            "style_variant": str(sampled.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
            "ludo_board_style": dict(rendered.style_meta.get("ludo_board_style", {})),
            "label_font": dict(rendered.style_meta.get("label_font", {})),
            "effective_cell_size_px": int(rendered.render_map["effective_cell_size_px"]),
            "flow_arrow_count": int(len(rendered.render_map.get("flow_arrow_markers_px", []))),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "query_id": str(query_id),
            "style_variant": str(sampled.style_variant),
            "construction_mode": str(sampled.construction_mode),
            "token_coords_by_color": {
                str(color): [int(coord[0]), int(coord[1])]
                for color, coord in sampled.token_coords.items()
            },
            "query_color": str(sampled.query_color),
            "target_color": sampled.target_color,
            "winning_roll": sampled.winning_roll,
            "capture_distance": sampled.capture_distance,
            "move_roll_total": sampled.move_roll_total,
            "roll_sequence": [int(value) for value in sampled.roll_sequence],
            "options": [
                {"label": str(option.label), "distance": int(option.distance), "text": str(option.text)}
                for option in sampled.options
            ],
            "destination_options": [
                {"label": str(option.label), "coord": [int(option.coord[0]), int(option.coord[1])]}
                for option in sampled.destination_options
            ],
            "answer": sampled.answer,
            "annotation_entity_ids": dict(annotation_entity_ids),
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
        "background": dict(rendered.background_meta),
        "post_image_noise": post_noise_meta,
    }
    return GeneratedComponents(
        prompt=str(prompt),
        prompt_variants=dict(prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        trace_payload=trace_payload,
        query_id=str(query_id),
    )


__all__ = [
    "CAPTURE_ROLL_QUERY_ID",
    "MOVE_RESULT_QUERY_ID",
    "SCENE_ID",
    "WINNING_ROLL_QUERY_ID",
    "GeneratedComponents",
    "build_components",
    "resolve_axes",
    "sample_capture_scene",
    "sample_move_result_scene",
    "sample_winning_scene",
]
