"""Games solitaire-tableau tasks with grounded card and pile annotation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.text import draw_game_text_traced as draw_text_traced
from ..shared.layout import apply_games_layout_jitter_to_bbox, resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "solitaire"
SCENE_ID = "solitaire"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("klondike_tableau", "freecell_tableau")
SUPPORTED_PANEL_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic_cards",
    "ivory_table",
    "casino_felt",
    "slate_cards",
    "paper_tableau",
)
QUERY_MOVE_LEGALITY = "move_legality_label"
QUERY_FOUNDATION_READY = "foundation_ready_count"
QUERY_TABLEAU_SEQUENCE = "tableau_sequence_count"
QUERY_SAME_SUIT_RUN = "same_suit_descending_run_length"
MOVE_OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
CARD_BADGE_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")
SUITS: Tuple[str, ...] = ("hearts", "diamonds", "spades", "clubs")
SUIT_SHORT: Dict[str, str] = {
    "hearts": "H",
    "diamonds": "D",
    "spades": "S",
    "clubs": "C",
}
SUIT_DISPLAY: Dict[str, str] = {
    "hearts": "hearts",
    "diamonds": "diamonds",
    "spades": "spades",
    "clubs": "clubs",
}
RANK_LABEL: Dict[int, str] = {
    1: "A",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "J",
    12: "Q",
    13: "K",
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for solitaire tableau scenes."""

    canvas_width: int = 1060
    canvas_height: int = 820
    card_width_px: int = 74
    card_height_px: int = 104
    card_gap_px: int = 16
    column_gap_px: int = 18
    column_step_y_px: int = 32
    panel_margin_px: int = 44
    foundation_gap_px: int = 14
    card_corner_radius_px: int = 9
    rank_font_size_px: int = 18
    card_center_font_size_px: int = 31
    badge_font_size_px: int = 14
    label_font_size_px: int = 15
    option_font_size_px: int = 22
    option_height_px: int = 46
    option_gap_px: int = 10
    move_option_count_support: Tuple[int, ...] = (4, 5)
    foundation_ready_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    tableau_sequence_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    same_suit_run_length_target_answer_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    tableau_column_count_support: Tuple[int, ...] = (7, 8)


@dataclass(frozen=True)
class _Card:
    """One visible card in the solitaire tableau scene."""

    card_id: str
    rank_value: int
    suit_name: str
    badge_text: str | None = None

    @property
    def rank_label(self) -> str:
        return str(RANK_LABEL[int(self.rank_value)])

    @property
    def suit_short(self) -> str:
        return str(SUIT_SHORT[str(self.suit_name)])

    @property
    def label(self) -> str:
        return f"{self.rank_label}{self.suit_short}"


@dataclass(frozen=True)
class _Foundation:
    """One visible solitaire foundation pile."""

    foundation_id: str
    suit_name: str
    top_rank_value: int

    @property
    def label(self) -> str:
        return f"{SUIT_SHORT[str(self.suit_name)]} pile"


@dataclass(frozen=True)
class _MoveOption:
    """One drawn source-to-target move option."""

    option_id: str
    label: str
    source_card_id: str
    source_badge: str
    target_id: str
    target_label: str
    is_answer: bool

    @property
    def move_text(self) -> str:
        return f"{self.source_badge}->{self.target_label}"


@dataclass(frozen=True)
class _Sample:
    """Constructed solitaire scene plus query-specific witness metadata."""

    query_id: str
    scene_variant: str
    columns: Tuple[Tuple[_Card, ...], ...]
    foundations: Tuple[_Foundation, ...]
    answer: int | str
    answer_type: str
    annotation_entity_ids: Tuple[str, ...]
    move_options: Tuple[_MoveOption, ...]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered solitaire scene and trace-friendly layout maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class _SolitaireVisualStyle:
    """Scene-local nonsemantic colors for the solitaire table and cards."""

    card_fill_rgb: Tuple[int, int, int]
    card_border_rgb: Tuple[int, int, int]
    card_back_rgb: Tuple[int, int, int]
    card_back_accent_rgb: Tuple[int, int, int]
    foundation_fill_rgb: Tuple[int, int, int]
    option_fill_rgb: Tuple[int, int, int]
    badge_fill_rgb: Tuple[int, int, int]
    badge_text_rgb: Tuple[int, int, int]
    red_suit_rgb: Tuple[int, int, int]
    black_suit_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id="games_solitaire_base",
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _int_default(params: Mapping[str, Any], key: str, fallback: int) -> int:
    if str(key) in params:
        return int(params[str(key)])
    return int(group_default(_RENDER_DEFAULTS, str(key), int(fallback)))


def _deck() -> List[Tuple[int, str]]:
    return [(int(rank), str(suit)) for suit in SUITS for rank in range(1, 14)]


def _card_color(suit_name: str) -> str:
    return "red" if str(suit_name) in {"hearts", "diamonds"} else "black"


def _rgb(values: Sequence[int]) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(value))) for value in values[:3])  # type: ignore[return-value]


def _is_legal_tableau_move(source: _Card, target: _Card) -> bool:
    return (
        int(target.rank_value) == int(source.rank_value) + 1
        and _card_color(str(target.suit_name)) != _card_color(str(source.suit_name))
    )


def _is_same_suit_descending_next(upper: _Card, lower: _Card) -> bool:
    """Return whether `lower` continues a same-suit descending run from `upper`."""

    return (
        str(lower.suit_name) == str(upper.suit_name)
        and int(lower.rank_value) == int(upper.rank_value) - 1
    )


def _is_legal_foundation_move(source: _Card, foundation: _Foundation) -> bool:
    return (
        str(source.suit_name) == str(foundation.suit_name)
        and int(source.rank_value) == int(foundation.top_rank_value) + 1
    )


def _remove_card(pool: List[Tuple[int, str]], card: Tuple[int, str]) -> None:
    pool.remove((int(card[0]), str(card[1])))


def _draw_text_center(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    text: str,
    *,
    font,
    fill: Tuple[int, int, int],
    stroke_width: int = 1,
) -> None:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=int(stroke_width))
    width = float(text_bbox[2] - text_bbox[0])
    height = float(text_bbox[3] - text_bbox[1])
    x0, y0, x1, y1 = bbox
    origin = (float(x0 + ((x1 - x0) - width) / 2.0), float(y0 + ((y1 - y0) - height) / 2.0))
    draw_text_traced(draw,
        origin,
        str(text),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_width=int(stroke_width),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(fill)),
     role="readout", required=False,)


def _draw_card(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    card: _Card,
    *,
    fill_rgb: Tuple[int, int, int],
    border_rgb: Tuple[int, int, int],
    radius_px: int,
    rank_font,
    center_font,
    badge_font,
    badge_fill_rgb: Tuple[int, int, int],
    badge_text_rgb: Tuple[int, int, int],
    red_suit_rgb: Tuple[int, int, int],
    black_suit_rgb: Tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=int(radius_px),
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in border_rgb),
        width=2,
    )
    suit_rgb = tuple(red_suit_rgb) if _card_color(str(card.suit_name)) == "red" else tuple(black_suit_rgb)
    label = str(card.label)
    stroke = tuple(int(value) for value in resolve_text_stroke_fill(suit_rgb))
    draw_text_traced(draw,(float(x0 + 8), float(y0 + 8)), label, font=rank_font, fill=suit_rgb, stroke_width=1, stroke_fill=stroke, role="readout", required=False)
    bottom_bbox = draw.textbbox((0, 0), label, font=rank_font, stroke_width=1)
    draw_text_traced(draw,
        (float(x1 - (bottom_bbox[2] - bottom_bbox[0]) - 8), float(y1 - (bottom_bbox[3] - bottom_bbox[1]) - 8)),
        label,
        font=rank_font,
        fill=suit_rgb,
        stroke_width=1,
        stroke_fill=stroke,
     role="readout", required=False,)
    _draw_text_center(draw, (x0 + 6, y0 + 28, x1 - 6, y1 - 20), label, font=center_font, fill=suit_rgb)
    if card.badge_text:
        badge_w = 28
        badge_h = 22
        badge_box = (float(x0 - 6), float(y1 - 30), float(x0 - 6 + badge_w), float(y1 - 30 + badge_h))
        draw.rounded_rectangle(
            badge_box,
            radius=7,
            fill=tuple(int(value) for value in badge_fill_rgb),
            outline=tuple(int(value) for value in border_rgb),
            width=1,
        )
        _draw_text_center(draw, badge_box, str(card.badge_text), font=badge_font, fill=badge_text_rgb, stroke_width=0)


def _draw_card_back(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    *,
    fill_rgb: Tuple[int, int, int],
    border_rgb: Tuple[int, int, int],
    accent_rgb: Tuple[int, int, int],
    radius_px: int,
) -> None:
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=int(radius_px),
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in border_rgb),
        width=2,
    )
    inset = 10
    draw.rounded_rectangle(
        [x0 + inset, y0 + inset, x1 - inset, y1 - inset],
        radius=max(3, int(radius_px) - 3),
        outline=tuple(int(value) for value in accent_rgb),
        width=2,
    )


def _draw_foundation(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    foundation: _Foundation,
    *,
    panel_fill_rgb: Tuple[int, int, int],
    border_rgb: Tuple[int, int, int],
    text_rgb: Tuple[int, int, int],
    rank_font,
    label_font,
    radius_px: int,
) -> None:
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=int(radius_px),
        fill=tuple(int(value) for value in panel_fill_rgb),
        outline=tuple(int(value) for value in border_rgb),
        width=2,
    )
    suit_rgb = (172, 35, 45) if _card_color(str(foundation.suit_name)) == "red" else tuple(int(v) for v in text_rgb)
    top_label = "empty" if int(foundation.top_rank_value) == 0 else f"{RANK_LABEL[int(foundation.top_rank_value)]}{SUIT_SHORT[str(foundation.suit_name)]}"
    _draw_text_center(draw, (x0 + 4, y0 + 8, x1 - 4, y0 + 36), str(foundation.label), font=label_font, fill=text_rgb, stroke_width=0)
    _draw_text_center(draw, (x0 + 4, y0 + 36, x1 - 4, y1 - 4), top_label, font=rank_font, fill=suit_rgb)


def _sample_scene_variant(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported_variants=SUPPORTED_SCENE_VARIANTS,
    )


def _sample_panel_style_variant(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported_variants=SUPPORTED_PANEL_STYLE_VARIANTS,
    )


def _resolve_solitaire_visual_style(style_variant: str, panel_style) -> Tuple[_SolitaireVisualStyle, Dict[str, Any]]:
    """Resolve card/tableau styling separate from the shared canvas treatment."""

    styles: Dict[str, _SolitaireVisualStyle] = {
        "classic_cards": _SolitaireVisualStyle(
            card_fill_rgb=(252, 250, 244),
            card_border_rgb=(82, 88, 101),
            card_back_rgb=(52, 88, 158),
            card_back_accent_rgb=(227, 235, 252),
            foundation_fill_rgb=(240, 245, 247),
            option_fill_rgb=(240, 246, 255),
            badge_fill_rgb=(238, 188, 71),
            badge_text_rgb=(34, 38, 45),
            red_suit_rgb=(172, 35, 45),
            black_suit_rgb=(34, 40, 50),
            text_rgb=_rgb(panel_style.text_rgb),
        ),
        "ivory_table": _SolitaireVisualStyle(
            card_fill_rgb=(255, 250, 235),
            card_border_rgb=(107, 82, 55),
            card_back_rgb=(125, 84, 55),
            card_back_accent_rgb=(241, 211, 154),
            foundation_fill_rgb=(245, 235, 209),
            option_fill_rgb=(248, 232, 190),
            badge_fill_rgb=(214, 163, 79),
            badge_text_rgb=(48, 38, 28),
            red_suit_rgb=(161, 47, 45),
            black_suit_rgb=(44, 39, 35),
            text_rgb=(59, 47, 36),
        ),
        "casino_felt": _SolitaireVisualStyle(
            card_fill_rgb=(249, 251, 246),
            card_border_rgb=(30, 77, 56),
            card_back_rgb=(31, 116, 78),
            card_back_accent_rgb=(190, 238, 205),
            foundation_fill_rgb=(215, 235, 220),
            option_fill_rgb=(223, 242, 225),
            badge_fill_rgb=(246, 211, 80),
            badge_text_rgb=(25, 48, 34),
            red_suit_rgb=(184, 38, 53),
            black_suit_rgb=(24, 45, 35),
            text_rgb=(28, 62, 44),
        ),
        "slate_cards": _SolitaireVisualStyle(
            card_fill_rgb=(233, 238, 243),
            card_border_rgb=(43, 54, 70),
            card_back_rgb=(75, 91, 111),
            card_back_accent_rgb=(199, 212, 226),
            foundation_fill_rgb=(218, 226, 235),
            option_fill_rgb=(225, 232, 241),
            badge_fill_rgb=(102, 149, 190),
            badge_text_rgb=(248, 250, 252),
            red_suit_rgb=(191, 60, 73),
            black_suit_rgb=(31, 38, 50),
            text_rgb=(33, 42, 55),
        ),
        "paper_tableau": _SolitaireVisualStyle(
            card_fill_rgb=(254, 250, 239),
            card_border_rgb=(136, 111, 78),
            card_back_rgb=(209, 185, 139),
            card_back_accent_rgb=(119, 93, 57),
            foundation_fill_rgb=(244, 235, 211),
            option_fill_rgb=(250, 238, 205),
            badge_fill_rgb=(191, 134, 66),
            badge_text_rgb=(46, 35, 24),
            red_suit_rgb=(159, 56, 54),
            black_suit_rgb=(49, 43, 37),
            text_rgb=(66, 52, 38),
        ),
    }
    resolved_key = str(style_variant) if str(style_variant) in styles else "classic_cards"
    return styles[resolved_key], {
        "style_variant": str(resolved_key),
        "available_styles": list(SUPPORTED_PANEL_STYLE_VARIANTS),
        "card_style_policy": "scene_local_solitaire_card_tableau_palette",
    }


def _sample_integer_axis(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[int, Dict[str, float]]:
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=tuple(int(item) for item in fallback_support),
        namespace=f"{str(task_id)}.{str(namespace)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return int(value), dict(probabilities)


def _sample_foundations(rng) -> Tuple[_Foundation, ...]:
    foundations: List[_Foundation] = []
    for suit in SUITS:
        top_rank = int(rng.randrange(0, 7))
        foundations.append(
            _Foundation(
                foundation_id=f"foundation_{SUIT_SHORT[str(suit)].lower()}",
                suit_name=str(suit),
                top_rank_value=int(top_rank),
            )
        )
    return tuple(foundations)


def _deck_after_foundations(foundations: Sequence[_Foundation]) -> List[Tuple[int, str]]:
    top_by_suit = {str(foundation.suit_name): int(foundation.top_rank_value) for foundation in foundations}
    return [
        (int(rank), str(suit))
        for rank, suit in _deck()
        if int(rank) > int(top_by_suit.get(str(suit), 0))
    ]


def _build_columns_from_exposed(
    rng,
    *,
    exposed_cards: Sequence[_Card],
    pool: List[Tuple[int, str]],
    scene_variant: str,
) -> Tuple[Tuple[_Card, ...], ...]:
    columns: List[Tuple[_Card, ...]] = []
    for index, exposed in enumerate(exposed_cards):
        filler_count = int(rng.randrange(0, 3 if str(scene_variant) == "freecell_tableau" else 4))
        filler_cards: List[_Card] = []
        for filler_index in range(filler_count):
            if not pool:
                break
            rank, suit = pool.pop(int(rng.randrange(len(pool))))
            filler_cards.append(
                _Card(
                    card_id=f"col_{index + 1:02d}_card_{filler_index + 1:02d}",
                    rank_value=int(rank),
                    suit_name=str(suit),
                    badge_text=None,
                )
            )
        exposed_id = f"col_{index + 1:02d}_card_{len(filler_cards) + 1:02d}"
        columns.append(
            tuple(
                [
                    *filler_cards,
                    _Card(
                        card_id=str(exposed_id),
                        rank_value=int(exposed.rank_value),
                        suit_name=str(exposed.suit_name),
                        badge_text=str(exposed.badge_text) if exposed.badge_text else None,
                    ),
                ]
            )
        )
    return tuple(columns)


def _exposed_cards(columns: Sequence[Sequence[_Card]]) -> Tuple[_Card, ...]:
    return tuple(column[-1] for column in columns if len(column) > 0)


def _foundation_by_id(foundations: Sequence[_Foundation]) -> Dict[str, _Foundation]:
    return {str(foundation.foundation_id): foundation for foundation in foundations}


def _card_by_id(columns: Sequence[Sequence[_Card]]) -> Dict[str, _Card]:
    return {str(card.card_id): card for column in columns for card in column}


def _target_is_legal(source: _Card, target_id: str, *, columns: Sequence[Sequence[_Card]], foundations: Sequence[_Foundation]) -> bool:
    cards = _card_by_id(columns)
    if str(target_id) in cards:
        return _is_legal_tableau_move(source, cards[str(target_id)])
    foundations_by_id = _foundation_by_id(foundations)
    if str(target_id) in foundations_by_id:
        return _is_legal_foundation_move(source, foundations_by_id[str(target_id)])
    return False


def _sample_move_option_count(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    return _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="move_option_count_support",
        explicit_key="option_count",
        fallback_support=_DEFAULTS.move_option_count_support,
        namespace="move_option_count",
        balanced_flag_key="balanced_option_count_sampling",
    )


def _answer_option_label(*, instance_seed: int, params: Mapping[str, Any], option_count: int) -> str:
    raw = params.get("answer_option_label")
    labels = MOVE_OPTION_LABELS[: int(option_count)]
    if raw is not None:
        label = str(raw).strip().upper()
        if label not in labels:
            raise ValueError(f"unsupported answer_option_label for {option_count} options: {label}")
        return str(label)
    cursor = params.get("_sample_cursor")
    if cursor is not None:
        return str(labels[abs(int(cursor)) % len(labels)])
    rng = spawn_rng(int(instance_seed), "games.solitaire.answer_option_label")
    return str(labels[int(rng.randrange(len(labels)))])


def _sample_move_legality(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> _Sample:
    option_count, option_count_probabilities = _sample_move_option_count(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
    )
    answer_label = _answer_option_label(instance_seed=int(instance_seed), params=params, option_count=int(option_count))
    for _attempt in range(600):
        foundations = _sample_foundations(rng)
        pool = _deck_after_foundations(foundations)
        column_count = 7 if str(scene_variant) == "klondike_tableau" else 8
        mode = "foundation" if int(rng.randrange(2)) == 0 else "tableau"
        exposed_raw: List[Tuple[int, str]] = []
        answer_source: Tuple[int, str]
        answer_target_id: str
        answer_target_label: str
        if mode == "foundation":
            candidate_foundations = [
                foundation
                for foundation in foundations
                if int(foundation.top_rank_value) < 13 and (int(foundation.top_rank_value) + 1, str(foundation.suit_name)) in pool
            ]
            if not candidate_foundations:
                continue
            foundation = candidate_foundations[int(rng.randrange(len(candidate_foundations)))]
            answer_source = (int(foundation.top_rank_value) + 1, str(foundation.suit_name))
            answer_target_id = str(foundation.foundation_id)
            answer_target_label = str(foundation.label)
            _remove_card(pool, answer_source)
            exposed_raw.append(answer_source)
        else:
            target_rank = int(rng.randrange(2, 14))
            target_suit = str(SUITS[int(rng.randrange(len(SUITS)))])
            opposite = [suit for suit in SUITS if _card_color(str(suit)) != _card_color(str(target_suit))]
            source_suit = str(opposite[int(rng.randrange(len(opposite)))])
            answer_source = (int(target_rank - 1), str(source_suit))
            target_raw = (int(target_rank), str(target_suit))
            if answer_source not in pool or target_raw not in pool:
                continue
            _remove_card(pool, answer_source)
            _remove_card(pool, target_raw)
            exposed_raw.extend([answer_source, target_raw])
            answer_target_id = "pending_target_card"
            answer_target_label = "pending"

        while len(exposed_raw) < int(column_count):
            if not pool:
                break
            exposed_raw.append(pool.pop(int(rng.randrange(len(pool)))))
        if len(exposed_raw) != int(column_count):
            continue
        rng.shuffle(exposed_raw)
        exposed_cards = tuple(
            _Card(
                card_id=f"exposed_{index + 1:02d}",
                rank_value=int(rank),
                suit_name=str(suit),
                badge_text=str(CARD_BADGE_LABELS[index]),
            )
            for index, (rank, suit) in enumerate(exposed_raw)
        )
        columns = _build_columns_from_exposed(rng, exposed_cards=exposed_cards, pool=pool, scene_variant=str(scene_variant))
        exposed_by_raw = {
            (int(card.rank_value), str(card.suit_name)): card
            for card in _exposed_cards(columns)
        }
        source_card = exposed_by_raw.get((int(answer_source[0]), str(answer_source[1])))
        if source_card is None:
            continue
        if mode == "tableau":
            legal_targets = [
                card
                for card in _exposed_cards(columns)
                if str(card.card_id) != str(source_card.card_id) and _is_legal_tableau_move(source_card, card)
            ]
            if not legal_targets:
                continue
            target_card = legal_targets[0]
            answer_target_id = str(target_card.card_id)
            answer_target_label = str(target_card.badge_text)
        answer_source_badge = str(source_card.badge_text)

        all_targets: List[Tuple[str, str]] = [
            (str(card.card_id), str(card.badge_text))
            for card in _exposed_cards(columns)
            if str(card.card_id) != str(source_card.card_id)
        ] + [(str(foundation.foundation_id), str(foundation.label)) for foundation in foundations]
        all_sources = [(str(card.card_id), str(card.badge_text)) for card in _exposed_cards(columns)]
        distractor_pairs: List[Tuple[str, str, str, str]] = []
        for src_id, src_badge in all_sources:
            src_card = _card_by_id(columns)[str(src_id)]
            for target_id, target_label in all_targets:
                if str(src_id) == str(target_id):
                    continue
                is_answer_pair = str(src_id) == str(source_card.card_id) and str(target_id) == str(answer_target_id)
                if is_answer_pair:
                    continue
                if not _target_is_legal(src_card, str(target_id), columns=columns, foundations=foundations):
                    distractor_pairs.append((str(src_id), str(src_badge), str(target_id), str(target_label)))
        rng.shuffle(distractor_pairs)
        if len(distractor_pairs) < int(option_count) - 1:
            continue
        options: List[_MoveOption] = []
        distractor_cursor = 0
        for label in MOVE_OPTION_LABELS[: int(option_count)]:
            if str(label) == str(answer_label):
                options.append(
                    _MoveOption(
                        option_id=f"move_option_{str(label).lower()}",
                        label=str(label),
                        source_card_id=str(source_card.card_id),
                        source_badge=str(answer_source_badge),
                        target_id=str(answer_target_id),
                        target_label=str(answer_target_label),
                        is_answer=True,
                    )
                )
            else:
                src_id, src_badge, target_id, target_label = distractor_pairs[int(distractor_cursor)]
                distractor_cursor += 1
                options.append(
                    _MoveOption(
                        option_id=f"move_option_{str(label).lower()}",
                        label=str(label),
                        source_card_id=str(src_id),
                        source_badge=str(src_badge),
                        target_id=str(target_id),
                        target_label=str(target_label),
                        is_answer=False,
                    )
                )
        legal_options = [
            option
            for option in options
            if _target_is_legal(_card_by_id(columns)[str(option.source_card_id)], str(option.target_id), columns=columns, foundations=foundations)
        ]
        if len(legal_options) != 1 or str(legal_options[0].label) != str(answer_label):
            continue
        annotation = (str(source_card.card_id), str(answer_target_id))
        return _Sample(
            query_id=QUERY_MOVE_LEGALITY,
            scene_variant=str(scene_variant),
            columns=tuple(columns),
            foundations=tuple(foundations),
            answer=str(answer_label),
            answer_type="string",
            annotation_entity_ids=tuple(annotation),
            move_options=tuple(options),
            metadata={
                "legal_move_kind": str(mode),
                "answer_option_label": str(answer_label),
                "option_count": int(option_count),
                "option_count_probabilities": dict(option_count_probabilities),
                "legal_source_id": str(source_card.card_id),
                "legal_source_label": str(answer_source_badge),
                "legal_target_id": str(answer_target_id),
                "legal_target_label": str(answer_target_label),
                "legal_move_answer": f"{str(answer_source_badge)}->{str(answer_target_label)}",
                "move_options": [
                    {
                        "label": str(option.label),
                        "source_card_id": str(option.source_card_id),
                        "source_label": str(option.source_badge),
                        "target_id": str(option.target_id),
                        "target_label": str(option.target_label),
                        "move": str(option.move_text),
                        "is_answer": bool(option.is_answer),
                    }
                    for option in options
                ],
            },
        )
    raise ValueError("failed to sample solitaire move-legality scene")


def _sample_foundation_ready(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> _Sample:
    target_answer, target_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="foundation_ready_target_answer_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.foundation_ready_target_answer_support,
        namespace="foundation_ready_target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    for _attempt in range(500):
        foundations = _sample_foundations(rng)
        pool = _deck_after_foundations(foundations)
        ready_raw = [
            (int(foundation.top_rank_value) + 1, str(foundation.suit_name))
            for foundation in foundations
            if int(foundation.top_rank_value) < 13 and (int(foundation.top_rank_value) + 1, str(foundation.suit_name)) in pool
        ]
        if len(ready_raw) < int(target_answer):
            continue
        rng.shuffle(ready_raw)
        selected_ready = ready_raw[: int(target_answer)]
        exposed_raw: List[Tuple[int, str]] = []
        for raw in selected_ready:
            _remove_card(pool, raw)
            exposed_raw.append(raw)
        non_ready_pool = []
        foundation_by_suit = {str(f.suit_name): f for f in foundations}
        for raw in list(pool):
            rank, suit = raw
            candidate_card = _Card(card_id="candidate", rank_value=int(rank), suit_name=str(suit))
            if not _is_legal_foundation_move(candidate_card, foundation_by_suit[str(suit)]):
                non_ready_pool.append(raw)
        column_count = 7 if str(scene_variant) == "klondike_tableau" else 8
        if len(non_ready_pool) < int(column_count) - len(exposed_raw):
            continue
        rng.shuffle(non_ready_pool)
        for raw in non_ready_pool[: int(column_count) - len(exposed_raw)]:
            _remove_card(pool, raw)
            exposed_raw.append(raw)
        rng.shuffle(exposed_raw)
        exposed_cards = tuple(
            _Card(
                card_id=f"exposed_{index + 1:02d}",
                rank_value=int(rank),
                suit_name=str(suit),
                badge_text=str(CARD_BADGE_LABELS[index]),
            )
            for index, (rank, suit) in enumerate(exposed_raw)
        )
        columns = _build_columns_from_exposed(rng, exposed_cards=exposed_cards, pool=pool, scene_variant=str(scene_variant))
        foundation_by_suit = {str(f.suit_name): f for f in foundations}
        ready_ids = tuple(
            str(card.card_id)
            for card in _exposed_cards(columns)
            if _is_legal_foundation_move(card, foundation_by_suit[str(card.suit_name)])
        )
        if len(ready_ids) != int(target_answer):
            continue
        return _Sample(
            query_id=QUERY_FOUNDATION_READY,
            scene_variant=str(scene_variant),
            columns=tuple(columns),
            foundations=tuple(foundations),
            answer=int(target_answer),
            answer_type="integer",
            annotation_entity_ids=tuple([*ready_ids, *[str(f.foundation_id) for f in foundations]]),
            move_options=(),
            metadata={
                "target_answer": int(target_answer),
                "target_answer_probabilities": dict(target_probabilities),
                "ready_card_ids": list(ready_ids),
                "ready_card_labels": [str(_card_by_id(columns)[card_id].badge_text) for card_id in ready_ids],
            },
        )
    raise ValueError("failed to sample solitaire foundation-ready scene")


def _make_sequence_columns(
    rng,
    *,
    target_answer: int,
    scene_variant: str,
) -> Tuple[Tuple[_Card, ...], Tuple[Tuple[str, str], ...]]:
    column_count = 7 if str(scene_variant) == "klondike_tableau" else 8
    lengths = [int(rng.randrange(3, 6)) for _ in range(int(column_count))]
    pair_slots = [(col, pos) for col, length in enumerate(lengths) for pos in range(int(length) - 1)]
    if int(target_answer) > len(pair_slots):
        raise ValueError("target answer exceeds visible adjacent-pair slots")
    rng.shuffle(pair_slots)
    valid_slot_set = set(pair_slots[: int(target_answer)])
    pool = _deck()
    columns: List[Tuple[_Card, ...]] = []
    valid_pairs: List[Tuple[str, str]] = []
    for col_index, length in enumerate(lengths):
        cards: List[_Card] = []
        for pos in range(int(length)):
            card_id = f"col_{col_index + 1:02d}_card_{pos + 1:02d}"
            badge = str(CARD_BADGE_LABELS[col_index]) if pos == int(length) - 1 else None
            if pos == 0:
                raw_candidates = [raw for raw in pool if int(raw[0]) >= 4]
                if not raw_candidates:
                    raise ValueError("empty sequence-card candidate pool")
                raw = raw_candidates[int(rng.randrange(len(raw_candidates)))]
            else:
                previous = cards[-1]
                should_be_valid = (int(col_index), int(pos - 1)) in valid_slot_set
                if should_be_valid and int(previous.rank_value) > 1:
                    candidates = [
                        raw
                        for raw in pool
                        if int(raw[0]) == int(previous.rank_value) - 1
                        and _card_color(str(raw[1])) != _card_color(str(previous.suit_name))
                    ]
                    if not candidates:
                        raise ValueError("no valid descending sequence candidate")
                    raw = candidates[int(rng.randrange(len(candidates)))]
                else:
                    candidates = [
                        raw
                        for raw in pool
                        if not (
                            int(raw[0]) == int(previous.rank_value) - 1
                            and _card_color(str(raw[1])) != _card_color(str(previous.suit_name))
                        )
                    ]
                    if not candidates:
                        raise ValueError("no invalid sequence candidate")
                    raw = candidates[int(rng.randrange(len(candidates)))]
            _remove_card(pool, raw)
            card = _Card(card_id=str(card_id), rank_value=int(raw[0]), suit_name=str(raw[1]), badge_text=badge)
            if pos > 0:
                previous = cards[-1]
                if _is_legal_tableau_move(card, previous):
                    valid_pairs.append((str(previous.card_id), str(card.card_id)))
            cards.append(card)
        columns.append(tuple(cards))
    if len(valid_pairs) != int(target_answer):
        raise ValueError("constructed sequence count mismatch")
    return tuple(columns), tuple(valid_pairs)


def _sample_tableau_sequence(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> _Sample:
    target_answer, target_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="tableau_sequence_target_answer_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.tableau_sequence_target_answer_support,
        namespace="tableau_sequence_target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    for _attempt in range(400):
        try:
            columns, valid_pairs = _make_sequence_columns(
                rng,
                target_answer=int(target_answer),
                scene_variant=str(scene_variant),
            )
        except ValueError:
            continue
        annotation_ids = tuple(dict.fromkeys([card_id for pair in valid_pairs for card_id in pair]))
        return _Sample(
            query_id=QUERY_TABLEAU_SEQUENCE,
            scene_variant=str(scene_variant),
            columns=tuple(columns),
            foundations=_sample_foundations(rng),
            answer=int(target_answer),
            answer_type="integer",
            annotation_entity_ids=tuple(annotation_ids),
            move_options=(),
            metadata={
                "target_answer": int(target_answer),
                "target_answer_probabilities": dict(target_probabilities),
                "valid_sequence_pairs": [[str(a), str(b)] for a, b in valid_pairs],
                "valid_sequence_pair_count": int(len(valid_pairs)),
            },
        )
    raise ValueError("failed to sample solitaire tableau-sequence scene")


def _sample_same_suit_run_length(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> _Sample:
    target_answer, target_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="same_suit_run_length_target_answer_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.same_suit_run_length_target_answer_support,
        namespace="same_suit_run_length_target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    column_count = 7 if str(scene_variant) == "klondike_tableau" else 8
    for _attempt in range(500):
        target_length = int(target_answer)
        if target_length < 1:
            continue
        pool = _deck()
        target_col_index = int(rng.randrange(column_count))
        target_suit = str(SUITS[int(rng.randrange(len(SUITS)))])
        min_start_rank = min(13, max(target_length + 1, target_length))
        if min_start_rank > 13:
            continue
        start_rank = int(rng.randrange(min_start_rank, 14))
        prefix_count = int(rng.randrange(0, 3))
        run_raw = [(int(start_rank - offset), str(target_suit)) for offset in range(target_length)]
        if any(raw not in pool for raw in run_raw):
            continue
        for raw in run_raw:
            _remove_card(pool, raw)

        breaker_candidates = [
            raw
            for raw in pool
            if not (int(raw[0]) == int(start_rank - target_length) and str(raw[1]) == str(target_suit))
        ]
        if not breaker_candidates:
            continue
        breaker_raw = breaker_candidates[int(rng.randrange(len(breaker_candidates)))]
        _remove_card(pool, breaker_raw)

        prefix_raw: List[Tuple[int, str]] = []
        for prefix_index in range(prefix_count):
            candidates = list(pool)
            if prefix_index == int(prefix_count) - 1:
                candidates = [
                    raw
                    for raw in candidates
                    if not (int(raw[0]) == int(start_rank + 1) and str(raw[1]) == str(target_suit))
                ]
            if not candidates:
                break
            raw = candidates[int(rng.randrange(len(candidates)))]
            _remove_card(pool, raw)
            prefix_raw.append(raw)
        if len(prefix_raw) != int(prefix_count):
            continue

        columns: List[Tuple[_Card, ...]] = []
        marked_card_id = ""
        run_card_ids: List[str] = []
        run_card_labels: List[str] = []
        for col_index in range(column_count):
            if int(col_index) == int(target_col_index):
                raw_cards = [*prefix_raw, *run_raw, breaker_raw]
            else:
                length = int(rng.randrange(3, 6))
                if len(pool) < length:
                    raise ValueError("not enough cards for solitaire same-suit run distractor columns")
                raw_cards = []
                for _ in range(length):
                    raw = pool.pop(int(rng.randrange(len(pool))))
                    raw_cards.append(raw)
            cards: List[_Card] = []
            for row_index, raw in enumerate(raw_cards):
                card_id = f"col_{col_index + 1:02d}_card_{row_index + 1:02d}"
                badge = str(CARD_BADGE_LABELS[col_index]) if int(row_index) == len(raw_cards) - 1 else None
                card = _Card(card_id=str(card_id), rank_value=int(raw[0]), suit_name=str(raw[1]), badge_text=badge)
                cards.append(card)
                if int(col_index) == int(target_col_index):
                    run_start = int(prefix_count)
                    run_end = int(prefix_count) + int(target_length)
                    if int(row_index) == run_start:
                        marked_card_id = str(card_id)
                    if run_start <= int(row_index) < run_end:
                        run_card_ids.append(str(card_id))
                        run_card_labels.append(str(card.label))
            columns.append(tuple(cards))

        if not marked_card_id or len(run_card_ids) != int(target_length):
            continue
        card_map = _card_by_id(columns)
        measured_ids = [str(marked_card_id)]
        current_id = str(marked_card_id)
        while True:
            current = card_map[str(current_id)]
            current_spec = next(
                spec
                for spec in (
                    {
                        "card_id": str(card.card_id),
                        "column_index": int(col_index),
                        "row_index": int(row_index),
                    }
                    for col_index, column in enumerate(columns)
                    for row_index, card in enumerate(column)
                )
                if str(spec["card_id"]) == str(current_id)
            )
            next_row_index = int(current_spec["row_index"]) + 1
            column = columns[int(current_spec["column_index"])]
            if next_row_index >= len(column):
                break
            next_card = column[next_row_index]
            if not _is_same_suit_descending_next(current, next_card):
                break
            measured_ids.append(str(next_card.card_id))
            current_id = str(next_card.card_id)
        if tuple(measured_ids) != tuple(run_card_ids):
            continue
        return _Sample(
            query_id=QUERY_SAME_SUIT_RUN,
            scene_variant=str(scene_variant),
            columns=tuple(columns),
            foundations=_sample_foundations(rng),
            answer=int(target_length),
            answer_type="integer",
            annotation_entity_ids=tuple(run_card_ids),
            move_options=(),
            metadata={
                "target_answer": int(target_length),
                "target_answer_probabilities": dict(target_probabilities),
                "marked_card_id": str(marked_card_id),
                "marked_card_column_index": int(target_col_index),
                "marked_card_row_index": int(prefix_count),
                "same_suit_run_card_ids": list(run_card_ids),
                "same_suit_run_card_labels": list(run_card_labels),
                "same_suit_run_length": int(target_length),
                "same_suit_run_suit": str(target_suit),
            },
        )
    raise ValueError("failed to sample solitaire same-suit run-length scene")


def _render_scene(
    *,
    sample: _Sample,
    task_id: str,
    style_variant: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _RenderedScene:
    canvas_width = _int_default(params, "canvas_width", _DEFAULTS.canvas_width)
    canvas_height = _int_default(params, "canvas_height", _DEFAULTS.canvas_height)
    card_width = _int_default(params, "card_width_px", _DEFAULTS.card_width_px)
    card_height = _int_default(params, "card_height_px", _DEFAULTS.card_height_px)
    column_gap = _int_default(params, "column_gap_px", _DEFAULTS.column_gap_px)
    column_step_y = _int_default(params, "column_step_y_px", _DEFAULTS.column_step_y_px)
    margin = _int_default(params, "panel_margin_px", _DEFAULTS.panel_margin_px)
    foundation_gap = _int_default(params, "foundation_gap_px", _DEFAULTS.foundation_gap_px)
    radius = _int_default(params, "card_corner_radius_px", _DEFAULTS.card_corner_radius_px)
    if params.get("canvas_height") is None:
        max_column_len = max((len(column) for column in sample.columns), default=1)
        tableau_bottom = 194 + (max(0, int(max_column_len) - 1) * column_step_y) + card_height
        foundation_bottom = 58 + card_height
        if sample.move_options:
            option_height = _int_default(params, "option_height_px", _DEFAULTS.option_height_px)
            needed_height = max(tableau_bottom, foundation_bottom) + 64 + option_height + margin
            canvas_height = min(int(canvas_height), max(620, int(needed_height)))
        else:
            needed_height = max(tableau_bottom, foundation_bottom) + margin + 28
            canvas_height = min(int(canvas_height), max(560, int(needed_height)))
    style, style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.solitaire_panel_style",
        treatment_weights=group_default(_GEN_DEFAULTS, "panel_treatment_weights", {}),
        palette_weights=group_default(_GEN_DEFAULTS, "panel_palette_weights", {}),
    )
    image, background_meta = make_panel_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=style,
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    layout_jitter = resolve_games_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.solitaire.layout",
    )
    content_bbox = (float(margin), 20.0, float(canvas_width - margin), float(canvas_height - margin))
    _shifted_content_bbox, dx, dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=content_bbox,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.solitaire.font_family",
        params=params,
    )
    rank_font = load_font(_int_default(params, "rank_font_size_px", _DEFAULTS.rank_font_size_px), bold=True, font_family=str(font_family))
    center_font = load_font(_int_default(params, "card_center_font_size_px", _DEFAULTS.card_center_font_size_px), bold=True, font_family=str(font_family))
    badge_font = load_font(_int_default(params, "badge_font_size_px", _DEFAULTS.badge_font_size_px), bold=True, font_family=str(font_family))
    label_font = load_font(_int_default(params, "label_font_size_px", _DEFAULTS.label_font_size_px), bold=True, font_family=str(font_family))
    option_font = load_font(_int_default(params, "option_font_size_px", _DEFAULTS.option_font_size_px), bold=True, font_family=str(font_family))
    solitaire_style, solitaire_style_meta = _resolve_solitaire_visual_style(str(style_variant), style)
    text_rgb = tuple(int(value) for value in solitaire_style.text_rgb)
    border_rgb = tuple(int(value) for value in solitaire_style.card_border_rgb)
    card_fill = tuple(int(value) for value in solitaire_style.card_fill_rgb)
    back_fill = tuple(int(value) for value in solitaire_style.card_back_rgb)
    badge_fill = tuple(int(value) for value in solitaire_style.badge_fill_rgb)
    badge_text = tuple(int(value) for value in solitaire_style.badge_text_rgb)

    foundation_y = 58 + int(round(dy))
    foundation_start_x = int(canvas_width - margin - (4 * card_width) - (3 * foundation_gap) + round(dx))
    foundation_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    for index, foundation in enumerate(sample.foundations):
        x0 = foundation_start_x + index * (card_width + foundation_gap)
        bbox = (float(x0), float(foundation_y), float(x0 + card_width), float(foundation_y + card_height))
        _draw_foundation(
            draw,
            bbox,
            foundation,
            panel_fill_rgb=tuple(int(value) for value in solitaire_style.foundation_fill_rgb),
            border_rgb=border_rgb,
            text_rgb=text_rgb,
            rank_font=rank_font,
            label_font=label_font,
            radius_px=radius,
        )
        foundation_bboxes[str(foundation.foundation_id)] = [float(value) for value in bbox]
        entities.append(
            {
                "entity_id": str(foundation.foundation_id),
                "entity_type": "foundation",
                "suit_name": str(foundation.suit_name),
                "top_rank_value": int(foundation.top_rank_value),
                "bbox_px": [float(value) for value in bbox],
            }
        )

    if str(sample.scene_variant) == "freecell_tableau":
        for index in range(4):
            x0 = margin + int(round(dx)) + index * (card_width + foundation_gap)
            bbox = (float(x0), float(foundation_y), float(x0 + card_width), float(foundation_y + card_height))
            draw.rounded_rectangle(bbox, radius=radius, fill=tuple(style.panel_fill_rgb), outline=border_rgb, width=2)
            _draw_text_center(draw, bbox, f"Free {index + 1}", font=label_font, fill=text_rgb, stroke_width=0)
    else:
        stock_x = margin + int(round(dx))
        waste_x = margin + card_width + foundation_gap
        waste_x += int(round(dx))
        stock_bbox = (float(stock_x), float(foundation_y), float(stock_x + card_width), float(foundation_y + card_height))
        waste_bbox = (float(waste_x), float(foundation_y), float(waste_x + card_width), float(foundation_y + card_height))
        _draw_card_back(
            draw,
            stock_bbox,
            fill_rgb=back_fill,
            border_rgb=border_rgb,
            accent_rgb=tuple(int(value) for value in solitaire_style.card_back_accent_rgb),
            radius_px=radius,
        )
        draw.rounded_rectangle(waste_bbox, radius=radius, fill=tuple(style.panel_fill_rgb), outline=border_rgb, width=2)
        _draw_text_center(draw, waste_bbox, "waste", font=label_font, fill=text_rgb, stroke_width=0)

    tableau_y = 194 + int(round(dy))
    column_count = len(sample.columns)
    total_columns_width = (column_count * card_width) + ((column_count - 1) * column_gap)
    start_x = int((canvas_width - total_columns_width) / 2 + round(dx))
    card_bboxes: Dict[str, List[float]] = {}
    marked_card_id = str(sample.metadata.get("marked_card_id", ""))
    for col_index, column in enumerate(sample.columns):
        x0 = start_x + int(col_index) * (card_width + column_gap)
        header_bbox = (float(x0), float(tableau_y - 28), float(x0 + card_width), float(tableau_y - 4))
        _draw_text_center(draw, header_bbox, f"Col {col_index + 1}", font=label_font, fill=text_rgb, stroke_width=0)
        if str(sample.scene_variant) == "klondike_tableau" and len(column) >= 3:
            back_bbox = (float(x0), float(tableau_y - 12), float(x0 + card_width), float(tableau_y - 12 + card_height))
            _draw_card_back(
                draw,
                back_bbox,
                fill_rgb=back_fill,
                border_rgb=border_rgb,
                accent_rgb=tuple(int(value) for value in solitaire_style.card_back_accent_rgb),
                radius_px=radius,
            )
        for row_index, card in enumerate(column):
            y0 = tableau_y + int(row_index) * column_step_y
            bbox = (float(x0), float(y0), float(x0 + card_width), float(y0 + card_height))
            _draw_card(
                draw,
                bbox,
                card,
                fill_rgb=card_fill,
                border_rgb=border_rgb,
                radius_px=radius,
                rank_font=rank_font,
                center_font=center_font,
                badge_font=badge_font,
                badge_fill_rgb=badge_fill,
                badge_text_rgb=badge_text,
                red_suit_rgb=tuple(int(value) for value in solitaire_style.red_suit_rgb),
                black_suit_rgb=tuple(int(value) for value in solitaire_style.black_suit_rgb),
            )
            if str(card.card_id) == marked_card_id:
                marker_bottom = min(float(y0 + card_height), float(y0 + column_step_y + 6))
                draw.rounded_rectangle(
                    (float(x0 - 4), float(y0 - 4), float(x0 + card_width + 4), float(marker_bottom)),
                    radius=max(4, int(radius // 2)),
                    outline=(218, 39, 49),
                    width=4,
                )
            card_bboxes[str(card.card_id)] = [float(value) for value in bbox]
            entities.append(
                {
                    "entity_id": str(card.card_id),
                    "entity_type": "card",
                    "rank_value": int(card.rank_value),
                    "rank_label": str(card.rank_label),
                    "suit_name": str(card.suit_name),
                    "suit_short": str(card.suit_short),
                    "badge_text": None if card.badge_text is None else str(card.badge_text),
                    "column_index": int(col_index),
                    "row_index": int(row_index),
                    "is_exposed": bool(row_index == len(column) - 1),
                    "is_marked": bool(str(card.card_id) == marked_card_id),
                    "bbox_px": [float(value) for value in bbox],
                }
            )

    option_bboxes: Dict[str, List[float]] = {}
    if sample.move_options:
        option_count = len(sample.move_options)
        option_height = _int_default(params, "option_height_px", _DEFAULTS.option_height_px)
        option_gap = _int_default(params, "option_gap_px", _DEFAULTS.option_gap_px)
        option_area_y = int(canvas_height - margin - option_height + round(dy))
        option_width = int((canvas_width - (2 * margin) - ((option_count - 1) * option_gap)) / option_count)
        for index, option in enumerate(sample.move_options):
            x0 = margin + int(round(dx)) + int(index) * (option_width + option_gap)
            bbox = (float(x0), float(option_area_y), float(x0 + option_width), float(option_area_y + option_height))
            draw.rounded_rectangle(
                bbox,
                radius=10,
                fill=tuple(int(value) for value in solitaire_style.option_fill_rgb),
                outline=border_rgb,
                width=2,
            )
            _draw_text_center(
                draw,
                bbox,
                f"{option.label}: {option.move_text}",
                font=option_font,
                fill=text_rgb,
                stroke_width=0,
            )
            option_bboxes[str(option.option_id)] = [float(value) for value in bbox]
            entities.append(
                {
                    "entity_id": str(option.option_id),
                    "entity_type": "move_option",
                    "label": str(option.label),
                    "move": str(option.move_text),
                    "source_card_id": str(option.source_card_id),
                    "target_id": str(option.target_id),
                    "is_answer": bool(option.is_answer),
                    "bbox_px": [float(value) for value in bbox],
                }
            )

    render_map = {
        "card_bboxes_px": dict(card_bboxes),
        "foundation_bboxes_px": dict(foundation_bboxes),
        "option_bboxes_px": dict(option_bboxes),
        "entity_bboxes_px": {**card_bboxes, **foundation_bboxes, **option_bboxes},
        "marked_card_id": marked_card_id or None,
        "marked_card_bbox_px": None if not marked_card_id else card_bboxes.get(marked_card_id),
        "column_count": int(column_count),
        "scene_variant": str(sample.scene_variant),
        "style": dict(style_meta),
        "panel_scene_style": dict(style_meta),
        "solitaire_tableau_style": dict(solitaire_style_meta),
        "font_family": str(font_family),
        "text_style": {"font_family": str(font_family)},
        "layout_jitter": dict(resolved_jitter),
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=render_map,
        style_meta={
            "panel_scene_style": dict(style_meta),
            "solitaire_tableau_style": dict(solitaire_style_meta),
            "text_style": {
                "font_family": str(font_family),
                "font_asset": get_font_family_record(str(font_family)).to_trace(),
            },
        },
        background_meta=dict(background_meta),
    )


def _json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) == QUERY_MOVE_LEGALITY:
        answer_and_annotation = {
            "annotation": {"source_card": [250, 220, 324, 324], "target": [342, 220, 416, 324]},
            "answer": "C",
        }
        answer_only = {"answer": "C"}
    else:
        answer_and_annotation = {"annotation": [[250, 220, 324, 324], [342, 220, 416, 324]], "answer": 3}
        answer_only = {"answer": 3}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _build_prompt(sample: _Sample, *, instance_seed: int) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_solitaire_tableau",
            f"answer_hint_{str(sample.query_id)}",
            f"annotation_hint_{str(sample.query_id)}",
            "tableau_rule_text",
            "foundation_rule_text",
            "same_suit_run_rule_text",
        ),
        context=f"prompt defaults for {str(sample.query_id)}",
    )
    json_example, json_example_answer_only = _json_examples(str(sample.query_id))
    dynamic_slots = {
        "object_description": str(prompt_defaults["object_description_solitaire_tableau"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[f"answer_hint_{str(sample.query_id)}"]),
        "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(sample.query_id)}"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "tableau_rule_text": str(prompt_defaults["tableau_rule_text"]),
        "foundation_rule_text": str(prompt_defaults["foundation_rule_text"]),
        "same_suit_run_rule_text": str(prompt_defaults["same_suit_run_rule_text"]),
    }
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(sample.query_id),
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




class _SolitaireTableauTask:
    """Shared generator for fixed solitaire-tableau public tasks."""

    domain = "games"
    scene_id = SCENE_ID
    query_id: str

    def _sample(self, rng, *, task_id: str, instance_seed: int, params: Mapping[str, Any], scene_variant: str) -> _Sample:
        raise NotImplementedError

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scene_variant, scene_variant_probabilities = _sample_scene_variant(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
        )
        style_variant, style_variant_probabilities = _sample_panel_style_variant(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
        )
        sample: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{str(self.task_id)}.attempt.{int(attempt_index)}")
            try:
                sample = self._sample(
                    rng,
                    task_id=str(self.task_id),
                    instance_seed=int(instance_seed),
                    params=params,
                    scene_variant=str(scene_variant),
                )
                break
            except ValueError:
                continue
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")
        rendered = _render_scene(
            sample=sample,
            task_id=str(self.task_id),
            style_variant=str(style_variant),
            instance_seed=int(instance_seed),
            params=params,
        )
        if str(sample.query_id) == QUERY_MOVE_LEGALITY:
            annotation_value: Any = {
                "source_card": list(rendered.render_map["entity_bboxes_px"][str(sample.metadata["legal_source_id"])]),
                "target": list(rendered.render_map["entity_bboxes_px"][str(sample.metadata["legal_target_id"])]),
            }
            annotation_type = "keyed_bbox_map"
            projected_annotation = {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_value),
                "pixel_keyed_bbox_map": dict(annotation_value),
            }
            witness_symbolic = {
                "type": "object_map",
                "ids": {
                    "source_card": str(sample.metadata["legal_source_id"]),
                    "target": str(sample.metadata["legal_target_id"]),
                },
            }
            annotation_count = len(annotation_value)
        else:
            annotation_bboxes = [
                list(rendered.render_map["entity_bboxes_px"][str(entity_id)])
                for entity_id in sample.annotation_entity_ids
                if str(entity_id) in rendered.render_map["entity_bboxes_px"]
            ]
            annotation_value = [list(bbox) for bbox in annotation_bboxes]
            annotation_type = "bbox_set"
            projected_annotation = {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_value],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_value],
            }
            witness_symbolic = {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
            }
            annotation_count = len(annotation_value)
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(sample, instance_seed=int(instance_seed))
        answer_gt = TypedValue(type=str(sample.answer_type), value=sample.answer)
        annotation_gt = TypedValue(type=str(annotation_type), value=annotation_value)
        card_specs = [
            {
                "card_id": str(card.card_id),
                "rank_value": int(card.rank_value),
                "rank_label": str(card.rank_label),
                "suit_name": str(card.suit_name),
                "suit_short": str(card.suit_short),
                "badge_text": None if card.badge_text is None else str(card.badge_text),
                "column_index": int(col_index),
                "row_index": int(row_index),
                "is_exposed": bool(row_index == len(column) - 1),
            }
            for col_index, column in enumerate(sample.columns)
            for row_index, card in enumerate(column)
        ]
        foundation_specs = [
            {
                "foundation_id": str(foundation.foundation_id),
                "label": str(foundation.label),
                "suit_name": str(foundation.suit_name),
                "top_rank_value": int(foundation.top_rank_value),
            }
            for foundation in sample.foundations
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_solitaire_tableau",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": str(sample.query_id),
                    "style_variant": str(style_variant),
                    "answer": sample.answer,
                    "annotation_entity_ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": {
                    "scene_variant": str(sample.scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "query_id": str(sample.query_id),
                    "query_id_probabilities": {str(sample.query_id): 1.0},
                    "style_variant": str(style_variant),
                    "style_variant_probabilities": dict(style_variant_probabilities),
                    **dict(sample.metadata),
                },
            },
            "render_spec": {
                "scene_variant": str(sample.scene_variant),
                "style_variant": str(style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "column_count": int(len(sample.columns)),
                "style": dict(rendered.style_meta),
                "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
                "solitaire_tableau_style": dict(rendered.style_meta.get("solitaire_tableau_style", {})),
                "text_style": dict(rendered.style_meta.get("text_style", {})),
                "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "scene_variant": str(sample.scene_variant),
                "query_id": str(sample.query_id),
                "style_variant": str(style_variant),
                "answer": sample.answer,
                "card_specs": card_specs,
                "foundation_specs": foundation_specs,
                "annotation_entity_ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
                **dict(sample.metadata),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_annotation": dict(projected_annotation),
            "background": dict(rendered.background_meta),
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt),
            prompt_variants=dict(prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


class GamesSolitaireMoveLegalityLabelTask(_SolitaireTableauTask):
    """Choose the one legal move option in a visible solitaire tableau."""

    task_id = "task_games__solitaire__move_legality_label"
    query_id = QUERY_MOVE_LEGALITY

    def _sample(self, rng, *, task_id: str, instance_seed: int, params: Mapping[str, Any], scene_variant: str) -> _Sample:
        return _sample_move_legality(
            rng,
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            scene_variant=str(scene_variant),
        )


class GamesSolitaireFoundationReadyCountTask(_SolitaireTableauTask):
    """Count exposed tableau cards that can move to a foundation pile."""

    task_id = "task_games__solitaire__foundation_ready_count"
    query_id = QUERY_FOUNDATION_READY

    def _sample(self, rng, *, task_id: str, instance_seed: int, params: Mapping[str, Any], scene_variant: str) -> _Sample:
        return _sample_foundation_ready(
            rng,
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            scene_variant=str(scene_variant),
        )


@register_task
class GamesSolitaireTableauSequenceCountTask(_SolitaireTableauTask):
    """Count adjacent tableau pairs already in descending alternating-color order."""

    task_id = "task_games__solitaire__tableau_sequence_count"
    query_id = QUERY_TABLEAU_SEQUENCE

    def _sample(self, rng, *, task_id: str, instance_seed: int, params: Mapping[str, Any], scene_variant: str) -> _Sample:
        return _sample_tableau_sequence(
            rng,
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            scene_variant=str(scene_variant),
        )


class GamesSolitaireSameSuitRunLengthValueTask(_SolitaireTableauTask):
    """Measure the same-suit descending run that starts at one marked tableau card."""

    task_id = "task_games__solitaire__same_suit_run_length_value"
    query_id = QUERY_SAME_SUIT_RUN

    def _sample(self, rng, *, task_id: str, instance_seed: int, params: Mapping[str, Any], scene_variant: str) -> _Sample:
        return _sample_same_suit_run_length(
            rng,
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            scene_variant=str(scene_variant),
        )


__all__ = [
    "GamesSolitaireFoundationReadyCountTask",
    "GamesSolitaireMoveLegalityLabelTask",
    "GamesSolitaireSameSuitRunLengthValueTask",
    "GamesSolitaireTableauSequenceCountTask",
]
