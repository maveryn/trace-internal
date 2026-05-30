"""Profile-card and ranked-list page lookup tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import build_pages_complexity, normalize_int_with_bounds, resolve_pages_complexity_weights
from ..shared.visual_defaults import load_pages_background_defaults, load_pages_noise_defaults


PROFILE_TASK_ID = "task_pages__profile_card_grid__attribute_lookup_label"
RANKED_TASK_ID = "task_pages__ranked_list__ordinal_entry_label"
TASK_GROUP = "document_lookup"
PROFILE_SCENE_ID = "profile_card_grid"
RANKED_SCENE_ID = "ranked_list"

PROFILE_QUERY_IDS: Tuple[str, ...] = (
    "value_for_named_profile_field",
    "profile_for_field_value",
)
PROFILE_SCENE_VARIANTS: Tuple[str, ...] = (
    "directory_grid",
    "compact_cards",
)
RANKED_QUERY_IDS: Tuple[str, ...] = (
    "nth_entry_label",
    "from_end_entry_label",
    "entry_after_named_entry",
)
RANKED_SCENE_VARIANTS: Tuple[str, ...] = (
    "two_column_lists",
    "stacked_lists",
)
ORDINAL_REFERENCES: Tuple[str, ...] = ("first", "interior", "final")
FROM_END_REFERENCES: Tuple[str, ...] = ("last", "second_last", "third_last")

_PROFILE_NAMES: Tuple[str, ...] = (
    "Aster",
    "Boreal",
    "Cinder",
    "Dovetail",
    "Elm",
    "Fable",
    "Grove",
    "Harbor",
    "Iris",
    "Juniper",
    "Keystone",
    "Lumen",
)
_PROFILE_FIELDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "Role",
        ("Analyst", "Curator", "Planner", "Auditor", "Designer", "Coordinator", "Navigator", "Archivist", "Reviewer"),
    ),
    (
        "Region",
        (
            "North Pier",
            "West Loop",
            "Cedar Bay",
            "East Ridge",
            "South Gate",
            "River Bend",
            "Hill Yard",
            "Lake Point",
            "Mesa Park",
        ),
    ),
    ("Signal", ("Amber", "Cobalt", "Indigo", "Violet", "Copper", "Silver", "Teal", "Crimson", "Olive")),
    ("Code", ("K-17", "M-42", "R-08", "T-63", "V-29", "X-54", "B-31", "D-76", "H-90")),
)
_PROFILE_PAGE_TITLES: Tuple[str, ...] = (
    "Team Profile Directory",
    "Field Contact Cards",
    "Assignment Roster",
    "Profile Reference Sheet",
)
_PROFILE_SUBTITLES: Tuple[str, ...] = (
    "short fields for each listed profile",
    "lookup cards with labels and values",
    "compact entity records",
)

_RANKED_LIST_BANK: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Recycling Types", ("Glass", "Paper", "Metal", "Batteries", "Textiles", "Electronics", "Compost")),
    ("Reading Benefits", ("Focus", "Vocabulary", "Memory", "Empathy", "Reasoning", "Patience", "Reflection")),
    ("Weekend Trends", ("Menswear", "Bold Colors", "Leather", "Sneakers", "Denim", "Layering", "Canvas Bags")),
    ("Travel Checks", ("Passport", "Tickets", "Luggage", "Adapters", "Itinerary", "Insurance", "Hotel Code")),
    (
        "Safety Notes",
        ("Lock Doors", "Check Lights", "Clear Aisles", "Test Alarm", "Mark Exits", "Store Tools", "Report Hazards"),
    ),
    ("Workshop Topics", ("Planning", "Budgeting", "Outreach", "Design", "Testing", "Launch", "Review")),
)
_RANKED_PAGE_TITLES: Tuple[str, ...] = (
    "Ranked Reference Lists",
    "Ordered Item Summary",
    "List Index Page",
    "Priority Lists",
)
_RANKED_SUBTITLES: Tuple[str, ...] = (
    "numbered entries grouped by topic",
    "short ordered lists",
    "ranked item groups",
)

_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (57, 118, 172),
    (48, 143, 112),
    (188, 92, 77),
    (129, 101, 183),
    (198, 144, 62),
    (75, 129, 95),
    (173, 89, 132),
    (76, 130, 151),
)


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    header_height_px: int
    gap_px: int
    corner_radius_px: int
    outline_width_px: int
    title_font_size_px: int
    subtitle_font_size_px: int
    card_title_font_size_px: int
    label_font_size_px: int
    value_font_size_px: int


@dataclass(frozen=True)
class _ProfileCard:
    profile_id: str
    name: str
    fields: Dict[str, str]
    accent_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RankedSection:
    section_id: str
    title: str
    items: Tuple[str, ...]
    accent_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedDocument:
    image: Image.Image
    entities: List[Dict[str, Any]]
    item_traces: List[Dict[str, Any]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    layout_meta: Dict[str, Any]


_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", TASK_GROUP)
_PROFILE_GEN_DEFAULTS, _PROFILE_RENDER_DEFAULTS, _PROFILE_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=PROFILE_TASK_ID,
)
_RANKED_GEN_DEFAULTS, _RANKED_RENDER_DEFAULTS, _RANKED_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=RANKED_TASK_ID,
)
_PROFILE_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=PROFILE_TASK_ID)
_RANKED_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=RANKED_TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_pages_background_defaults(task_group=TASK_GROUP)
POST_IMAGE_NOISE_DEFAULTS = load_pages_noise_defaults(task_group=TASK_GROUP, apply_prob=0.0)


def _resolve_named_variant(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.{namespace}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(value) for value in supported],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(value) for value in supported],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{task_id}.{namespace}",
    )
    if str(balanced) != str(selected) and params.get(str(explicit_key)) is not None:
        return str(balanced), {str(key): (1.0 if str(key) == str(balanced) else 0.0) for key in supported}
    return str(balanced), dict(probabilities)


def _resolve_int_support(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
) -> Tuple[int, ...]:
    raw_values = params.get(str(key), group_default(gen_defaults, str(key), fallback))
    values: List[int] = []
    for raw_value in raw_values:
        value = int(raw_value)
        if value not in values:
            values.append(value)
    if not values:
        raise ValueError(f"{key} must not be empty")
    return tuple(int(value) for value in values)


def _resolve_supported_int(
    *,
    task_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    explicit_key: str,
    support_key: str,
    fallback: Sequence[int],
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    support = _resolve_int_support(params=params, gen_defaults=gen_defaults, key=support_key, fallback=fallback)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"{explicit_key} must be in {support} for {task_id}")
        return int(selected), tuple(support), {str(int(selected)): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{namespace}",
    )
    selected = int(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return int(selected), tuple(support), {str(value): float(probability) for value in support}


def _ordinal_label(index: int, *, final_index: int) -> str:
    if int(index) == 0:
        return "first"
    if int(index) == int(final_index):
        return "final"
    number = int(index) + 1
    if 10 <= (number % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _from_end_label(offset: int) -> str:
    if int(offset) == 0:
        return "last"
    if int(offset) == 1:
        return "second from last"
    if int(offset) == 2:
        return "third from last"
    return f"{int(offset) + 1}th from last"


def _resolve_render_params(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> _RenderParams:
    def _int_value(key: str, fallback: int, *, minimum: int = 1) -> int:
        return max(int(minimum), int(params.get(key, group_default(defaults, key, fallback))))

    return _RenderParams(
        canvas_width=_int_value("canvas_width", 1120, minimum=360),
        canvas_height=_int_value("canvas_height", 860, minimum=360),
        outer_margin_px=_int_value("outer_margin_px", 34, minimum=0),
        header_height_px=_int_value("header_height_px", 88, minimum=44),
        gap_px=_int_value("gap_px", 14, minimum=4),
        corner_radius_px=_int_value("corner_radius_px", 14, minimum=0),
        outline_width_px=_int_value("outline_width_px", 2, minimum=1),
        title_font_size_px=_int_value("title_font_size_px", 30, minimum=14),
        subtitle_font_size_px=_int_value("subtitle_font_size_px", 17, minimum=10),
        card_title_font_size_px=_int_value("card_title_font_size_px", 22, minimum=12),
        label_font_size_px=_int_value("label_font_size_px", 15, minimum=9),
        value_font_size_px=_int_value("value_font_size_px", 17, minimum=10),
    )


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    stroke_width: int = 0,
) -> List[float]:
    try:
        bbox = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=int(stroke_width))
        return [float(value) for value in bbox]
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return [float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)]


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: Tuple[int, int, int],
) -> List[float]:
    draw_text_traced(draw,(float(xy[0]), float(xy[1])), str(text), fill=fill, font=font, role="readout", required=False)
    return _text_bbox(draw, xy, str(text), font)


def _blend_rgb(color_a: Sequence[int], color_b: Sequence[int], weight_b: float) -> Tuple[int, int, int]:
    weight = max(0.0, min(1.0, float(weight_b)))
    return tuple(
        int(round((float(color_a[index]) * (1.0 - weight)) + (float(color_b[index]) * weight)))
        for index in range(3)
    )


def _layout_grid(
    *,
    count: int,
    columns: int,
    render_params: _RenderParams,
) -> Tuple[List[List[float]], Dict[str, Any]]:
    rows = int((int(count) + int(columns) - 1) // int(columns))
    margin = int(render_params.outer_margin_px)
    gap = int(render_params.gap_px)
    top = float(margin + render_params.header_height_px)
    left = float(margin)
    right = float(render_params.canvas_width - margin)
    bottom = float(render_params.canvas_height - margin)
    inner_w = max(1.0, right - left)
    inner_h = max(1.0, bottom - top)
    card_w = (inner_w - (float(columns - 1) * float(gap))) / float(columns)
    card_h = (inner_h - (float(rows - 1) * float(gap))) / float(rows)
    bboxes: List[List[float]] = []
    for index in range(int(count)):
        row = int(index) // int(columns)
        col = int(index) % int(columns)
        x0 = left + (float(col) * (card_w + float(gap)))
        y0 = top + (float(row) * (card_h + float(gap)))
        bboxes.append([x0, y0, x0 + card_w, y0 + card_h])
    return bboxes, {"layout_columns": int(columns), "layout_rows": int(rows)}


def _vertical_text_rows(
    *,
    y0: float,
    y1: float,
    top_offset: float,
    row_count: int,
    bottom_padding: float,
    preferred_min_gap: float,
    max_gap: float,
    max_text_height: float,
) -> Tuple[float, float, float]:
    top = float(y0) + float(top_offset)
    count = max(1, int(row_count))
    available = max(1.0, float(y1) - float(top) - float(bottom_padding))
    text_height = min(float(max_text_height), max(8.0, (float(available) / float(count)) * 0.82))
    if count == 1:
        return float(top), 0.0, float(text_height)

    fit_gap = max(1.0, (float(available) - float(text_height)) / float(count - 1))
    if float(fit_gap) >= float(preferred_min_gap):
        row_gap = max(float(preferred_min_gap), min(float(max_gap), float(fit_gap)))
    else:
        row_gap = float(fit_gap)
    return float(top), float(row_gap), float(text_height)


def _draw_panel_header(
    image: Image.Image,
    *,
    render_params: _RenderParams,
    page_title: str,
    page_subtitle: str,
) -> Tuple[ImageDraw.ImageDraw, List[float], List[float]]:
    draw = ImageDraw.Draw(image)
    margin = int(render_params.outer_margin_px)
    panel_bbox = [
        float(margin),
        float(margin),
        float(render_params.canvas_width - margin),
        float(render_params.canvas_height - margin),
    ]
    draw.rounded_rectangle(
        tuple(panel_bbox),
        radius=18,
        fill=(249, 250, 250),
        outline=(205, 212, 220),
        width=2,
    )
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    subtitle_font = load_font(int(render_params.subtitle_font_size_px), bold=False)
    title_xy = (float(margin + 24), float(margin + 18))
    title_bbox = _draw_text(draw, title_xy, str(page_title), title_font, (35, 42, 50))
    _draw_text(draw, (title_xy[0], title_xy[1] + 38.0), str(page_subtitle), subtitle_font, (91, 101, 113))
    return draw, panel_bbox, title_bbox


def _build_profile_cards(*, card_count: int, instance_seed: int) -> Tuple[List[_ProfileCard], str, str]:
    rng = spawn_rng(int(instance_seed), f"{PROFILE_TASK_ID}.cards")
    names = list(_PROFILE_NAMES)
    rng.shuffle(names)
    field_values_by_label: Dict[str, List[str]] = {}
    for field_label, values in _PROFILE_FIELDS:
        shuffled = list(values)
        rng.shuffle(shuffled)
        field_values_by_label[str(field_label)] = shuffled
    if int(card_count) > len(names):
        raise ValueError("profile card count exceeds available unique names")
    cards: List[_ProfileCard] = []
    color_offset = int(rng.randrange(len(_PALETTE)))
    for index in range(int(card_count)):
        fields = {
            str(field_label): str(field_values_by_label[str(field_label)][int(index)])
            for field_label, _values in _PROFILE_FIELDS
        }
        cards.append(
            _ProfileCard(
                profile_id=f"profile_{index + 1}",
                name=str(names[int(index)]),
                fields=fields,
                accent_rgb=_PALETTE[(int(index) + int(color_offset)) % len(_PALETTE)],
            )
        )
    return cards, str(rng.choice(_PROFILE_PAGE_TITLES)), str(rng.choice(_PROFILE_SUBTITLES))


def _render_profile_cards(
    background: Image.Image,
    *,
    cards: Sequence[_ProfileCard],
    page_title: str,
    page_subtitle: str,
    scene_variant: str,
    render_params: _RenderParams,
) -> _RenderedDocument:
    image = background.convert("RGB")
    draw, panel_bbox, title_bbox = _draw_panel_header(
        image,
        render_params=render_params,
        page_title=str(page_title),
        page_subtitle=str(page_subtitle),
    )
    columns = 3 if str(scene_variant) == "directory_grid" else 2
    card_bboxes, layout_meta = _layout_grid(count=len(cards), columns=int(columns), render_params=render_params)
    text_rgb = (35, 42, 50)
    muted_rgb = (91, 101, 113)
    entities: List[Dict[str, Any]] = []
    traces: List[Dict[str, Any]] = []
    for card, bbox in zip(cards, card_bboxes):
        x0, y0, x1, y1 = [float(value) for value in bbox]
        accent = tuple(int(channel) for channel in card.accent_rgb)
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=int(render_params.corner_radius_px),
            fill=_blend_rgb((255, 255, 255), accent, 0.035),
            outline=(205, 212, 220),
            width=int(render_params.outline_width_px),
        )
        draw.rounded_rectangle((x0, y0, x1, y0 + 8.0), radius=int(render_params.corner_radius_px), fill=accent)
        name_font = fit_font_to_box(
            draw,
            text=str(card.name),
            max_width=max(40.0, x1 - x0 - 32.0),
            max_height=30.0,
            bold=True,
            min_size_px=12,
            max_size_px=int(render_params.card_title_font_size_px),
            fill_ratio=0.97,
        )
        name_bbox = _draw_text(draw, (x0 + 16.0, y0 + 22.0), str(card.name), name_font, text_rgb)
        row_top, row_gap, row_text_height = _vertical_text_rows(
            y0=y0,
            y1=y1,
            top_offset=62.0,
            row_count=len(card.fields),
            bottom_padding=16.0,
            preferred_min_gap=28.0,
            max_gap=42.0,
            max_text_height=24.0,
        )
        label_bboxes: Dict[str, List[float]] = {}
        value_bboxes: Dict[str, List[float]] = {}
        for row_index, (field_label, field_value) in enumerate(card.fields.items()):
            fy = row_top + (float(row_index) * float(row_gap))
            label_font = fit_font_to_box(
                draw,
                text=f"{field_label}:",
                max_width=82.0,
                max_height=min(22.0, row_text_height),
                bold=True,
                min_size_px=7,
                max_size_px=min(int(render_params.label_font_size_px), max(7, int(row_text_height))),
                fill_ratio=0.96,
            )
            value_font = fit_font_to_box(
                draw,
                text=str(field_value),
                max_width=max(40.0, x1 - x0 - 118.0),
                max_height=float(row_text_height),
                bold=False,
                min_size_px=7,
                max_size_px=min(int(render_params.value_font_size_px), max(7, int(row_text_height))),
                fill_ratio=0.97,
            )
            label_bbox = _draw_text(draw, (x0 + 18.0, fy), f"{field_label}:", label_font, muted_rgb)
            value_bbox = _draw_text(draw, (x0 + 102.0, fy), str(field_value), value_font, text_rgb)
            label_bboxes[str(field_label)] = [float(value) for value in label_bbox]
            value_bboxes[str(field_label)] = [float(value) for value in value_bbox]

        trace = {
            "profile_id": str(card.profile_id),
            "name": str(card.name),
            "fields": dict(card.fields),
            "card_bbox_px": [float(value) for value in bbox],
            "name_bbox_px": [float(value) for value in name_bbox],
            "field_label_bboxes_px": dict(label_bboxes),
            "field_value_bboxes_px": dict(value_bboxes),
            "accent_rgb": [int(channel) for channel in accent],
        }
        entities.append(
            {
                "id": str(card.profile_id),
                "type": "profile_card",
                "bbox_px": [float(value) for value in bbox],
                "attrs": {"name": str(card.name), "fields": dict(card.fields)},
            }
        )
        traces.append(trace)
    return _RenderedDocument(
        image=image,
        entities=entities,
        item_traces=traces,
        panel_bbox_px=list(panel_bbox),
        title_bbox_px=list(title_bbox),
        layout_meta={"scene_variant": str(scene_variant), "card_count": int(len(cards)), **dict(layout_meta)},
    )


def _profile_maps(
    traces: Sequence[Mapping[str, Any]],
) -> Tuple[
    Dict[str, List[float]],
    Dict[str, List[float]],
    Dict[str, Dict[str, List[float]]],
    Dict[str, Dict[str, List[float]]],
]:
    card_map = {str(trace["profile_id"]): [float(value) for value in trace["card_bbox_px"]] for trace in traces}
    name_map = {str(trace["profile_id"]): [float(value) for value in trace["name_bbox_px"]] for trace in traces}
    label_map = {
        str(trace["profile_id"]): {
            str(field): [float(value) for value in bbox]
            for field, bbox in dict(trace["field_label_bboxes_px"]).items()
        }
        for trace in traces
    }
    value_map = {
        str(trace["profile_id"]): {
            str(field): [float(value) for value in bbox]
            for field, bbox in dict(trace["field_value_bboxes_px"]).items()
        }
        for trace in traces
    }
    return card_map, name_map, label_map, value_map


def _build_ranked_sections(
    *,
    section_count: int,
    item_count: int,
    instance_seed: int,
) -> Tuple[List[_RankedSection], str, str]:
    rng = spawn_rng(int(instance_seed), f"{RANKED_TASK_ID}.sections")
    banks = list(_RANKED_LIST_BANK)
    rng.shuffle(banks)
    if int(section_count) > len(banks):
        raise ValueError("ranked section count exceeds section bank")
    sections: List[_RankedSection] = []
    color_offset = int(rng.randrange(len(_PALETTE)))
    for index in range(int(section_count)):
        title, items = banks[int(index)]
        item_values = list(items)
        if int(item_count) > len(item_values):
            raise ValueError("ranked item count exceeds item bank")
        sections.append(
            _RankedSection(
                section_id=f"section_{index + 1}",
                title=str(title),
                items=tuple(str(value) for value in item_values[: int(item_count)]),
                accent_rgb=_PALETTE[(int(index) + int(color_offset)) % len(_PALETTE)],
            )
        )
    return sections, str(rng.choice(_RANKED_PAGE_TITLES)), str(rng.choice(_RANKED_SUBTITLES))


def _layout_sections(
    *,
    scene_variant: str,
    section_count: int,
    render_params: _RenderParams,
) -> Tuple[List[List[float]], Dict[str, Any]]:
    if str(scene_variant) == "stacked_lists":
        columns = 1
    else:
        columns = min(3, int(section_count))
    return _layout_grid(count=int(section_count), columns=int(columns), render_params=render_params)


def _render_ranked_sections(
    background: Image.Image,
    *,
    sections: Sequence[_RankedSection],
    page_title: str,
    page_subtitle: str,
    scene_variant: str,
    render_params: _RenderParams,
) -> _RenderedDocument:
    image = background.convert("RGB")
    draw, panel_bbox, title_bbox = _draw_panel_header(
        image,
        render_params=render_params,
        page_title=str(page_title),
        page_subtitle=str(page_subtitle),
    )
    section_bboxes, layout_meta = _layout_sections(
        scene_variant=str(scene_variant),
        section_count=len(sections),
        render_params=render_params,
    )
    text_rgb = (35, 42, 50)
    muted_rgb = (91, 101, 113)
    entities: List[Dict[str, Any]] = []
    traces: List[Dict[str, Any]] = []
    for section, bbox in zip(sections, section_bboxes):
        x0, y0, x1, y1 = [float(value) for value in bbox]
        accent = tuple(int(channel) for channel in section.accent_rgb)
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=int(render_params.corner_radius_px),
            fill=_blend_rgb((255, 255, 255), accent, 0.03),
            outline=(205, 212, 220),
            width=int(render_params.outline_width_px),
        )
        draw.rounded_rectangle((x0, y0, x1, y0 + 8.0), radius=int(render_params.corner_radius_px), fill=accent)
        section_font = fit_font_to_box(
            draw,
            text=str(section.title),
            max_width=max(40.0, x1 - x0 - 34.0),
            max_height=30.0,
            bold=True,
            min_size_px=12,
            max_size_px=int(render_params.card_title_font_size_px),
            fill_ratio=0.97,
        )
        section_title_bbox = _draw_text(draw, (x0 + 18.0, y0 + 22.0), str(section.title), section_font, text_rgb)
        item_top, item_gap, item_text_height = _vertical_text_rows(
            y0=y0,
            y1=y1,
            top_offset=64.0,
            row_count=len(section.items),
            bottom_padding=18.0,
            preferred_min_gap=28.0,
            max_gap=42.0,
            max_text_height=24.0,
        )
        item_bboxes: Dict[str, List[float]] = {}
        number_bboxes: Dict[str, List[float]] = {}
        for item_index, item in enumerate(section.items):
            iy = item_top + (float(item_index) * float(item_gap))
            number_text = f"{item_index + 1}."
            number_font = load_font(
                max(7, min(int(render_params.label_font_size_px), int(item_text_height))),
                bold=True,
            )
            item_font = fit_font_to_box(
                draw,
                text=str(item),
                max_width=max(40.0, x1 - x0 - 72.0),
                max_height=float(item_text_height),
                bold=False,
                min_size_px=7,
                max_size_px=min(int(render_params.value_font_size_px), max(7, int(item_text_height))),
                fill_ratio=0.97,
            )
            number_bbox = _draw_text(draw, (x0 + 20.0, iy), number_text, number_font, muted_rgb)
            item_bbox = _draw_text(draw, (x0 + 54.0, iy), str(item), item_font, text_rgb)
            item_id = f"{section.section_id}_item_{item_index + 1}"
            item_bboxes[item_id] = [float(value) for value in item_bbox]
            number_bboxes[item_id] = [float(value) for value in number_bbox]
        trace = {
            "section_id": str(section.section_id),
            "title": str(section.title),
            "items": [str(value) for value in section.items],
            "section_bbox_px": [float(value) for value in bbox],
            "section_title_bbox_px": [float(value) for value in section_title_bbox],
            "item_bboxes_px": dict(item_bboxes),
            "number_bboxes_px": dict(number_bboxes),
            "accent_rgb": [int(channel) for channel in accent],
        }
        entities.append(
            {
                "id": str(section.section_id),
                "type": "ranked_list_section",
                "bbox_px": [float(value) for value in bbox],
                "attrs": {"title": str(section.title), "items": [str(value) for value in section.items]},
            }
        )
        traces.append(trace)
    return _RenderedDocument(
        image=image,
        entities=entities,
        item_traces=traces,
        panel_bbox_px=list(panel_bbox),
        title_bbox_px=list(title_bbox),
        layout_meta={"scene_variant": str(scene_variant), "section_count": int(len(sections)), **dict(layout_meta)},
    )


def _ranked_maps(
    traces: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[str, List[float]], Dict[str, Dict[str, List[float]]]]:
    section_title_map = {
        str(trace["section_id"]): [float(value) for value in trace["section_title_bbox_px"]]
        for trace in traces
    }
    item_map = {
        str(trace["section_id"]): {
            str(item_id): [float(value) for value in bbox]
            for item_id, bbox in dict(trace["item_bboxes_px"]).items()
        }
        for trace in traces
    }
    return section_title_map, item_map


def _build_profile_prompt_examples(*, answer: str) -> Tuple[str, str]:
    evidence = {
        "profile_name": [120, 160, 210, 188],
        "field_label": [120, 216, 174, 244],
        "field_value": [220, 216, 340, 244],
    }
    answer_and_evidence = {"evidence": evidence, "answer": str(answer)}
    answer_only = {"answer": str(answer)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _build_ranked_prompt_examples(*, answer: str, include_source: bool) -> Tuple[str, str]:
    evidence = {
        "section_title": [120, 160, 240, 188],
    }
    if bool(include_source):
        evidence["source_item"] = [160, 216, 260, 244]
    evidence["target_item"] = [160, 256, 270, 284]
    answer_and_evidence = {"evidence": evidence, "answer": str(answer)}
    answer_only = {"answer": str(answer)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


@register_task
class PagesProfileCardGridAttributeLookupLabelTask:
    """Read or reverse-lookup one attribute on a profile-card page."""

    task_id = PROFILE_TASK_ID
    domain = "pages"
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_named_variant(
            task_id=self.task_id,
            gen_defaults=_PROFILE_GEN_DEFAULTS,
            params=params,
            instance_seed=int(instance_seed),
            supported=PROFILE_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            namespace="query_id",
        )
        scene_variant, scene_variant_probabilities = _resolve_named_variant(
            task_id=self.task_id,
            gen_defaults=_PROFILE_GEN_DEFAULTS,
            params=params,
            instance_seed=int(instance_seed),
            supported=PROFILE_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            namespace="scene_variant",
        )
        card_count, card_count_support, card_count_probabilities = _resolve_supported_int(
            task_id=self.task_id,
            params=params,
            gen_defaults=_PROFILE_GEN_DEFAULTS,
            explicit_key="card_count",
            support_key="card_count_support",
            fallback=(6, 9),
            instance_seed=int(instance_seed),
            namespace="card_count",
        )
        cards, page_title, page_subtitle = _build_profile_cards(
            card_count=int(card_count),
            instance_seed=int(instance_seed),
        )
        field_labels = [str(label) for label, _values in _PROFILE_FIELDS]
        explicit_field = params.get("field_label")
        if explicit_field is not None:
            target_field = str(explicit_field)
            if target_field not in field_labels:
                raise ValueError(f"field_label must be one of {field_labels}")
        else:
            field_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.field_label",
            ) % len(field_labels)
            target_field = str(field_labels[int(field_index)])
        explicit_profile_index = params.get("profile_index")
        if explicit_profile_index is not None:
            target_index = int(explicit_profile_index)
            if target_index < 0 or target_index >= int(card_count):
                raise ValueError("profile_index out of range")
        else:
            target_index = int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{self.task_id}.profile_index.{target_field}",
                )
                % int(card_count)
            )
        target_card = cards[int(target_index)]
        target_value = str(target_card.fields[str(target_field)])
        answer_value = str(target_value) if str(query_id) == "value_for_named_profile_field" else str(target_card.name)

        render_params = _resolve_render_params(params, _PROFILE_RENDER_DEFAULTS)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_profile_cards(
            background,
            cards=cards,
            page_title=str(page_title),
            page_subtitle=str(page_subtitle),
            scene_variant=str(scene_variant),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        card_bbox_map, name_bbox_map, field_label_bbox_map, field_value_bbox_map = _profile_maps(rendered.item_traces)
        evidence_keyed_bboxes = {
            "profile_name": [float(value) for value in name_bbox_map[str(target_card.profile_id)]],
            "field_label": [
                float(value)
                for value in field_label_bbox_map[str(target_card.profile_id)][str(target_field)]
            ],
            "field_value": [
                float(value)
                for value in field_value_bbox_map[str(target_card.profile_id)][str(target_field)]
            ],
        }

        prompt_defaults = required_group_defaults(
            _PROFILE_PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint",
                "object_description",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_profile_prompt_examples(answer="North Pier")
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "profile_name": f'"{str(target_card.name)}"',
                "field_label": str(target_field),
                "field_value": f'"{str(target_value)}"',
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        target_profile_payload = {
            "profile_id": str(target_card.profile_id),
            "profile_name": str(target_card.name),
            "field_label": str(target_field),
            "field_value": str(target_value),
        }
        trace_payload = {
            "scene_ir": {
                "scene_id": PROFILE_SCENE_ID,
                "scene_kind": "pages_profile_card_grid",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "target_profile": dict(target_profile_payload),
                    "answer_value": str(answer_value),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "card_count": int(card_count),
                    "target_profile": dict(target_profile_payload),
                    "target_answer": str(answer_value),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "card_count_probabilities": dict(card_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": PROFILE_SCENE_ID,
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "layout": dict(rendered.layout_meta),
            },
            "render_map": {
                "image_id": "img0",
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "card_bboxes_px": dict(card_bbox_map),
                "name_bboxes_px": dict(name_bbox_map),
                "field_label_bboxes_px": dict(field_label_bbox_map),
                "field_value_bboxes_px": dict(field_value_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "profile_card_attribute_lookup_label",
                "card_count": int(card_count),
                "card_count_support": [int(value) for value in card_count_support],
                "target_profile": dict(target_profile_payload),
                "answer_value": str(answer_value),
                "cards": [dict(trace) for trace in rendered.item_traces],
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "card_count_probabilities": dict(card_count_probabilities),
            },
            "witness_symbolic": {
                "type": "profile_card_attribute_lookup",
                "target_profile_id": str(target_card.profile_id),
                "field_label": str(target_field),
                "field_value": str(target_value),
                "answer_value": str(answer_value),
                "evidence_keys": list(evidence_keyed_bboxes.keys()),
            },
            "projected_evidence": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(evidence_keyed_bboxes),
                "pixel_keyed_bbox_map": dict(evidence_keyed_bboxes),
                "bbox_set": list(evidence_keyed_bboxes.values()),
                "target_profile_id": str(target_card.profile_id),
                "field_label": str(target_field),
            },
        }
        complexity = build_pages_complexity(
            weights=_PROFILE_COMPLEXITY_WEIGHTS,
            components={
                "lookup_reasoning": 0.52 if str(query_id) == "profile_for_field_value" else 0.42,
                "visual_scan": normalize_int_with_bounds(
                    int(card_count),
                    [min(card_count_support), max(card_count_support)],
                ),
                "layout_load": 0.48 if str(scene_variant) == "compact_cards" else 0.42,
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(answer_value)),
            evidence_gt=TypedValue(type="keyed_bbox_map", value=dict(evidence_keyed_bboxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesRankedListOrdinalEntryLabelTask:
    """Read one item from a sectioned ranked-list page."""

    task_id = RANKED_TASK_ID
    domain = "pages"
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_named_variant(
            task_id=self.task_id,
            gen_defaults=_RANKED_GEN_DEFAULTS,
            params=params,
            instance_seed=int(instance_seed),
            supported=RANKED_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            namespace="query_id",
        )
        scene_variant, scene_variant_probabilities = _resolve_named_variant(
            task_id=self.task_id,
            gen_defaults=_RANKED_GEN_DEFAULTS,
            params=params,
            instance_seed=int(instance_seed),
            supported=RANKED_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            namespace="scene_variant",
        )
        section_count, section_count_support, section_count_probabilities = _resolve_supported_int(
            task_id=self.task_id,
            params=params,
            gen_defaults=_RANKED_GEN_DEFAULTS,
            explicit_key="section_count",
            support_key="section_count_support",
            fallback=(2, 3),
            instance_seed=int(instance_seed),
            namespace="section_count",
        )
        item_count, item_count_support, item_count_probabilities = _resolve_supported_int(
            task_id=self.task_id,
            params=params,
            gen_defaults=_RANKED_GEN_DEFAULTS,
            explicit_key="item_count",
            support_key="item_count_support",
            fallback=(5, 6, 7),
            instance_seed=int(instance_seed),
            namespace="item_count",
        )
        sections, page_title, page_subtitle = _build_ranked_sections(
            section_count=int(section_count),
            item_count=int(item_count),
            instance_seed=int(instance_seed),
        )
        section_index = int(
            params.get(
                "section_index",
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{self.task_id}.section_index",
                )
                % int(section_count),
            )
        )
        if section_index < 0 or section_index >= int(section_count):
            raise ValueError("section_index out of range")
        target_section = sections[int(section_index)]
        source_index: int | None = None
        if str(query_id) == "entry_after_named_entry":
            source_index = int(
                params.get(
                    "source_item_index",
                    resolve_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{self.task_id}.source_item_index.{section_index}",
                    )
                    % max(1, int(item_count) - 1),
                )
            )
            if source_index < 0 or source_index >= int(item_count) - 1:
                raise ValueError("source_item_index out of range")
            target_index = int(source_index) + 1
            item_reference = "after_named"
            from_end_probabilities: Dict[str, float] = {}
            ordinal_probabilities: Dict[str, float] = {}
        elif str(query_id) == "from_end_entry_label":
            from_end_reference, from_end_probabilities = _resolve_named_variant(
                task_id=self.task_id,
                gen_defaults=_RANKED_GEN_DEFAULTS,
                params=params,
                instance_seed=int(instance_seed),
                supported=FROM_END_REFERENCES,
                explicit_key="from_end_reference",
                weights_key="from_end_reference_weights",
                balance_flag_key="balanced_from_end_reference_sampling",
                namespace="from_end_reference",
            )
            offsets = {"last": 0, "second_last": 1, "third_last": 2}
            target_index = int(item_count) - 1 - int(offsets[str(from_end_reference)])
            item_reference = _from_end_label(int(offsets[str(from_end_reference)]))
            ordinal_probabilities = {}
        else:
            ordinal_reference, ordinal_probabilities = _resolve_named_variant(
                task_id=self.task_id,
                gen_defaults=_RANKED_GEN_DEFAULTS,
                params=params,
                instance_seed=int(instance_seed),
                supported=ORDINAL_REFERENCES,
                explicit_key="ordinal_reference",
                weights_key="ordinal_reference_weights",
                balance_flag_key="balanced_ordinal_reference_sampling",
                namespace="ordinal_reference",
            )
            if str(ordinal_reference) == "first":
                target_index = 0
            elif str(ordinal_reference) == "final":
                target_index = int(item_count) - 1
            else:
                interior_count = max(1, int(item_count) - 2)
                target_index = 1 + int(
                    resolve_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{self.task_id}.interior_item_index.{section_index}.{item_count}",
                    )
                    % int(interior_count)
                )
            item_reference = _ordinal_label(int(target_index), final_index=int(item_count) - 1)
            from_end_probabilities = {}
        answer_value = str(target_section.items[int(target_index)])
        source_item = str(target_section.items[int(source_index)]) if source_index is not None else ""

        render_params = _resolve_render_params(params, _RANKED_RENDER_DEFAULTS)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_ranked_sections(
            background,
            sections=sections,
            page_title=str(page_title),
            page_subtitle=str(page_subtitle),
            scene_variant=str(scene_variant),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        section_title_bbox_map, item_bbox_map = _ranked_maps(rendered.item_traces)
        target_item_id = f"{target_section.section_id}_item_{target_index + 1}"
        evidence_keyed_bboxes = {
            "section_title": [float(value) for value in section_title_bbox_map[str(target_section.section_id)]],
        }
        if source_index is not None:
            source_item_id = f"{target_section.section_id}_item_{source_index + 1}"
            evidence_keyed_bboxes["source_item"] = [
                float(value) for value in item_bbox_map[str(target_section.section_id)][str(source_item_id)]
            ]
        evidence_keyed_bboxes["target_item"] = [
            float(value) for value in item_bbox_map[str(target_section.section_id)][str(target_item_id)]
        ]

        prompt_defaults = required_group_defaults(
            _RANKED_PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint",
                "object_description",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_ranked_prompt_examples(
            answer="Glass",
            include_source=source_index is not None,
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "section_title": f'"{str(target_section.title)}"',
                "item_reference": str(item_reference),
                "source_item": f'"{str(source_item)}"',
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        target_payload = {
            "section_id": str(target_section.section_id),
            "section_title": str(target_section.title),
            "target_index": int(target_index),
            "target_position": int(target_index) + 1,
            "source_index": int(source_index) if source_index is not None else None,
            "source_item": str(source_item),
            "answer_value": str(answer_value),
        }
        trace_payload = {
            "scene_ir": {
                "scene_id": RANKED_SCENE_ID,
                "scene_kind": "pages_ranked_list",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "target_entry": dict(target_payload),
                    "answer_value": str(answer_value),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "section_count": int(section_count),
                    "item_count": int(item_count),
                    "item_reference": str(item_reference),
                    "target_entry": dict(target_payload),
                    "target_answer": str(answer_value),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "section_count_probabilities": dict(section_count_probabilities),
                    "item_count_probabilities": dict(item_count_probabilities),
                    "ordinal_reference_probabilities": dict(ordinal_probabilities),
                    "from_end_reference_probabilities": dict(from_end_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": RANKED_SCENE_ID,
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "layout": dict(rendered.layout_meta),
            },
            "render_map": {
                "image_id": "img0",
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "section_title_bboxes_px": dict(section_title_bbox_map),
                "item_bboxes_px": dict(item_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "ranked_list_ordinal_entry_label",
                "section_count": int(section_count),
                "item_count": int(item_count),
                "target_entry": dict(target_payload),
                "answer_value": str(answer_value),
                "sections": [dict(trace) for trace in rendered.item_traces],
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "section_count_probabilities": dict(section_count_probabilities),
                "item_count_probabilities": dict(item_count_probabilities),
            },
            "witness_symbolic": {
                "type": "ranked_list_entry_lookup",
                "section_id": str(target_section.section_id),
                "target_item_id": str(target_item_id),
                "source_item": str(source_item),
                "answer_value": str(answer_value),
                "evidence_keys": list(evidence_keyed_bboxes.keys()),
            },
            "projected_evidence": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(evidence_keyed_bboxes),
                "pixel_keyed_bbox_map": dict(evidence_keyed_bboxes),
                "bbox_set": list(evidence_keyed_bboxes.values()),
                "section_id": str(target_section.section_id),
                "target_item_id": str(target_item_id),
            },
        }
        complexity = build_pages_complexity(
            weights=_RANKED_COMPLEXITY_WEIGHTS,
            components={
                "lookup_reasoning": 0.58 if str(query_id) == "entry_after_named_entry" else 0.45,
                "visual_scan": normalize_int_with_bounds(
                    int(section_count) * int(item_count),
                    [
                        min(section_count_support) * min(item_count_support),
                        max(section_count_support) * max(item_count_support),
                    ],
                ),
                "layout_load": 0.50 if str(scene_variant) == "two_column_lists" else 0.43,
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(answer_value)),
            evidence_gt=TypedValue(type="keyed_bbox_map", value=dict(evidence_keyed_bboxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "PROFILE_QUERY_IDS",
    "PROFILE_SCENE_VARIANTS",
    "RANKED_QUERY_IDS",
    "RANKED_SCENE_VARIANTS",
    "PagesProfileCardGridAttributeLookupLabelTask",
    "PagesRankedListOrdinalEntryLabelTask",
]
