"""Infographic metric-card arithmetic page tasks."""

from __future__ import annotations

import json
import math
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
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import (
    build_pages_complexity,
    normalize_int_with_bounds,
    resolve_pages_complexity_weights,
)
from ..shared.public_query_task import rewrite_pages_query_output
from ..shared.visual_defaults import load_pages_background_defaults, load_pages_noise_defaults


TASK_ID = "pages_infographic_metric_arithmetic_value_base"
SCENE_ID = "infographic"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "sum_named_metrics",
    "section_extrema_arithmetic",
    "section_total_extrema_difference",
    "section_total_except_named",
)
SECTION_RANKED_TOTAL_VARIANTS: Tuple[str, ...] = (
    "section_ranked_total_label",
)
FILTERED_METRIC_TOTAL_VARIANTS: Tuple[str, ...] = (
    "section_icon_total_value",
)
COLUMN_PROFILE_COMPARISON_VARIANTS: Tuple[str, ...] = (
    "section_icon_total_difference_value",
)
FILTERED_SECTION_EXTREMUM_VARIANTS: Tuple[str, ...] = (
    "section_icon_extremum_label",
)
ALL_QUERY_IDS: Tuple[str, ...] = (
    *SUPPORTED_QUERY_IDS,
    *SECTION_RANKED_TOTAL_VARIANTS,
    *FILTERED_METRIC_TOTAL_VARIANTS,
    *COLUMN_PROFILE_COMPARISON_VARIANTS,
    *FILTERED_SECTION_EXTREMUM_VARIANTS,
)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "infographic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_pages_background_defaults(task_group="infographic")
POST_IMAGE_NOISE_DEFAULTS = load_pages_noise_defaults(task_group="infographic", apply_prob=0.0)

_METRIC_LABEL_POOL: Tuple[str, ...] = (
    "Atlas",
    "Beacon",
    "Cedar",
    "Delta",
    "Everest",
    "Fjord",
    "Harbor",
    "Ion",
    "Juniper",
    "Keystone",
    "Lumen",
    "Mesa",
    "Nimbus",
    "Orion",
    "Pulse",
    "Quarry",
    "Relay",
    "Summit",
    "Tango",
    "Umber",
    "Vertex",
    "Willow",
    "Xeno",
    "Yarrow",
    "Zenith",
    "Axiom",
    "Beryl",
    "Coral",
    "Dorian",
    "Echo",
    "Falcon",
    "Grove",
    "Helix",
    "Iris",
    "Jasper",
)
_SECTION_TITLE_POOL: Tuple[str, ...] = (
    "Market Signals",
    "Program Totals",
    "Regional Mix",
    "Quarter Notes",
    "Service Levels",
    "Budget Snapshot",
)
_ICON_KINDS: Tuple[str, ...] = ("ring", "bars", "triangle", "stack", "spark", "dot_grid")
_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (52, 116, 170),
    (39, 139, 112),
    (196, 89, 73),
    (132, 101, 184),
    (202, 143, 56),
    (74, 132, 92),
    (60, 105, 142),
    (172, 85, 128),
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "sum_named_metrics": 0.72,
    "section_extrema_arithmetic": 0.88,
    "section_total_extrema_difference": 1.00,
    "section_total_except_named": 1.00,
    "section_ranked_total_label": 0.92,
    "section_icon_total_value": 0.78,
    "section_icon_total_difference_value": 0.86,
    "section_icon_extremum_label": 0.94,
}
_EXTREMUM_KINDS: Tuple[str, ...] = ("maximum", "minimum")
_EXTREMA_OPERATIONS: Tuple[str, ...] = ("sum", "absolute_difference")
_RANK_DIRECTIONS: Tuple[str, ...] = ("highest", "lowest")
_RANK_POSITION_SUPPORT: Tuple[int, ...] = (2, 3)
_RANK_ORDINALS: Dict[int, str] = {
    1: "highest",
    2: "second",
    3: "third",
}
_INFOGRAPHIC_STYLE_VARIANTS: Tuple[str, ...] = (
    "card_wall",
    "kpi_dashboard",
    "staggered_mosaic",
    "column_fact_sheet",
    "radial_spokes",
    "circular_sections",
)
_STYLE_TITLE_COPY: Dict[str, Tuple[str, str]] = {
    "card_wall": ("Operational Metrics", "Arithmetic from printed values"),
    "kpi_dashboard": ("Program Snapshot", "KPI cards grouped by section"),
    "staggered_mosaic": ("Metrics Bulletin", "Grouped figures with section totals"),
    "column_fact_sheet": ("Field Report", "Column-style metric summary"),
    "radial_spokes": ("Signal Wheel", "Metric groups arranged by section"),
    "circular_sections": ("Metric Orbit", "Section groups arranged in rings"),
}


@dataclass(frozen=True)
class _MetricCard:
    card_id: str
    label: str
    value: int
    display_text: str
    unit: str
    section: str
    icon_kind: str
    color_rgb: Tuple[int, int, int]
    caption_number: int


@dataclass(frozen=True)
class _RenderedInfographic:
    image: Image.Image
    entities: List[Dict[str, Any]]
    card_traces: List[Dict[str, Any]]
    section_bboxes: Dict[str, List[float]]
    layout_jitter_meta: Dict[str, Any]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", 0) or 0)
    except Exception:
        return 0


def _render_rgb(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _probability_map_for_selection(supported: Sequence[str], selected: str) -> Dict[str, float]:
    return {str(key): (1.0 if str(key) == str(selected) else 0.0) for key in supported}


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    raw_supported = params.get("_supported_query_ids", SUPPORTED_QUERY_IDS)
    if isinstance(raw_supported, str):
        supported_variants = tuple(value.strip() for value in raw_supported.split(",") if value.strip())
    else:
        supported_variants = tuple(str(value) for value in raw_supported)
    if not supported_variants:
        supported_variants = tuple(SUPPORTED_QUERY_IDS)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    query_id, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported_variants,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(query_id),
        variant_probabilities=probabilities,
        supported_variants=supported_variants,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    if balanced != query_id and params.get("query_id") is not None:
        return str(balanced), _probability_map_for_selection(supported_variants, str(balanced))
    return str(balanced), dict(probabilities)


def _resolve_int_range(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    min_key: str,
    max_key: str,
    explicit_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
    balanced_flag_key: str = "balanced_count_sampling",
) -> Tuple[int, Tuple[int, int], Dict[str, float]]:
    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {TASK_ID}",
    )
    support = [int(value) for value in range(int(lower), int(upper) + 1)]
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"{explicit_key} must be in {lower}..{upper}")
        return int(selected), (int(lower), int(upper)), {str(int(selected)): 1.0}
    balanced = bool(params.get(str(balanced_flag_key), group_default(gen_defaults, str(balanced_flag_key), True)))
    if balanced:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
        selected = int(support[int(index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), str(namespace))
        selected = int(support[int(rng.randrange(len(support)))])
    probability = 1.0 / float(len(support))
    return int(selected), (int(lower), int(upper)), {str(value): float(probability) for value in support}


def _resolve_section_count(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    query_id: str,
    card_count: int,
    instance_seed: int,
) -> Tuple[int, Tuple[int, int], Dict[str, float]]:
    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="section_count_min",
        max_key="section_count_max",
        fallback_min=2,
        fallback_max=4,
        context=f"generation defaults for {TASK_ID}",
    )
    support = [int(value) for value in range(int(lower), int(upper) + 1)]
    if str(query_id) == "section_total_except_named":
        _, exclusion_max = resolve_required_int_bounds(
            params,
            gen_defaults,
            min_key="excluded_metric_count_min",
            max_key="excluded_metric_count_max",
            fallback_min=2,
            fallback_max=2,
            context=f"generation defaults for {TASK_ID}",
        )
        included_count_min = int(
            params.get(
                "section_except_included_count_min",
                group_default(gen_defaults, "section_except_included_count_min", 3),
            )
        )
        required_section_size = int(exclusion_max) + int(included_count_min)
        support = [
            int(section_count)
            for section_count in support
            if max(_partition_cards(int(card_count), int(section_count))) >= int(required_section_size)
        ]
    if not support:
        raise ValueError(f"no feasible section_count values for {query_id} with card_count={card_count}")
    explicit = params.get("section_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"section_count={selected} is infeasible for {query_id} with card_count={card_count}")
        return int(selected), (min(support), max(support)), {str(int(selected)): 1.0}
    balanced = bool(params.get("balanced_count_sampling", group_default(gen_defaults, "balanced_count_sampling", True)))
    if balanced:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.section_count.{query_id}.{card_count}",
        )
        selected = int(support[int(index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.section_count.{query_id}")
        selected = int(support[int(rng.randrange(len(support)))])
    probability = 1.0 / float(len(support))
    return int(selected), (min(support), max(support)), {str(value): float(probability) for value in support}


def _quote_label(label: str) -> str:
    return f'"{str(label)}"'


def _quoted_label_list(labels: Sequence[str]) -> str:
    quoted = [_quote_label(str(label)) for label in labels]
    if not quoted:
        return ""
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f"{quoted[0]} and {quoted[1]}"
    return f"{', '.join(quoted[:-1])}, and {quoted[-1]}"


def _labels_by_section(
    *,
    labels: Sequence[str],
    section_titles: Sequence[str],
    section_card_counts: Sequence[int],
) -> Dict[str, List[str]]:
    """Return metric labels grouped by their rendered section."""

    grouped: Dict[str, List[str]] = {}
    label_index = 0
    for section_index, section_title in enumerate(section_titles):
        section_labels: List[str] = []
        for _ in range(int(section_card_counts[section_index])):
            section_labels.append(str(labels[label_index]))
            label_index += 1
        grouped[str(section_title)] = section_labels
    return grouped


def _section_totals(
    labels_by_section: Mapping[str, Sequence[str]],
    values_by_label: Mapping[str, int],
) -> Dict[str, int]:
    """Compute section totals from the same label-value map used for answers."""

    return {
        str(section): int(sum(int(values_by_label[str(label)]) for label in labels))
        for section, labels in labels_by_section.items()
    }


def _adjust_value_to_break_tie(
    values_by_label: Dict[str, int],
    *,
    label: str,
    value_min: int,
    value_max: int,
) -> None:
    """Adjust one metric by one step while staying inside the configured value range."""

    current = int(values_by_label[str(label)])
    if current < int(value_max):
        values_by_label[str(label)] = current + 1
    elif current > int(value_min):
        values_by_label[str(label)] = current - 1
    else:
        raise ValueError(f"cannot adjust tied value for label {label!r} inside {value_min}..{value_max}")


def _adjust_section_total(
    values_by_label: Dict[str, int],
    labels: Sequence[str],
    *,
    delta: int,
    value_min: int,
    value_max: int,
) -> bool:
    """Move one section total by a small integer delta while preserving value bounds."""

    direction = 1 if int(delta) > 0 else -1
    for _ in range(abs(int(delta))):
        adjusted = False
        for label in labels:
            current = int(values_by_label[str(label)])
            if direction > 0 and current < int(value_max):
                values_by_label[str(label)] = current + 1
                adjusted = True
                break
            if direction < 0 and current > int(value_min):
                values_by_label[str(label)] = current - 1
                adjusted = True
                break
        if not adjusted:
            return False
    return True


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


def _draw_icon(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    kind: str,
    color: Tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    w = float(x1 - x0)
    h = float(y1 - y0)
    cx = x0 + (0.5 * w)
    cy = y0 + (0.5 * h)
    fill = tuple(int(channel) for channel in color)
    pale = tuple(int(round((0.72 * 255) + (0.28 * channel))) for channel in fill)
    if str(kind) == "ring":
        draw.ellipse((x0 + 4, y0 + 4, x1 - 4, y1 - 4), outline=fill, width=4)
        draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=pale, outline=fill, width=2)
    elif str(kind) == "bars":
        bar_w = max(4.0, w / 5.8)
        for index, frac in enumerate((0.45, 0.72, 0.56)):
            left = x0 + 7 + (index * (bar_w + 5))
            draw.rounded_rectangle(
                (left, y1 - 6 - (h * frac), left + bar_w, y1 - 6),
                radius=3,
                fill=fill,
            )
    elif str(kind) == "triangle":
        draw.polygon(((cx, y0 + 5), (x1 - 5, y1 - 5), (x0 + 5, y1 - 5)), fill=pale, outline=fill)
    elif str(kind) == "stack":
        for offset in (0, 8, 16):
            draw.rounded_rectangle((x0 + 6, y0 + 8 + offset, x1 - 6, y0 + 18 + offset), radius=4, fill=fill)
    elif str(kind) == "spark":
        points = ((cx, y0 + 4), (cx + 6, cy - 5), (x1 - 4, cy), (cx + 6, cy + 5), (cx, y1 - 4), (cx - 6, cy + 5), (x0 + 4, cy), (cx - 6, cy - 5))
        draw.polygon(points, fill=pale, outline=fill)
    else:
        radius = 4.5
        for row in range(2):
            for col in range(3):
                px = x0 + 11 + (col * 13)
                py = y0 + 12 + (row * 14)
                draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=fill)


def _blend_rgb(color_a: Sequence[int], color_b: Sequence[int], weight_b: float) -> Tuple[int, int, int]:
    """Blend two RGB colors with a small deterministic style weight."""

    weight = max(0.0, min(1.0, float(weight_b)))
    return tuple(
        int(round((float(color_a[index]) * (1.0 - weight)) + (float(color_b[index]) * weight)))
        for index in range(3)
    )


def _partition_cards(card_count: int, section_count: int) -> List[int]:
    base = int(card_count) // int(section_count)
    remainder = int(card_count) % int(section_count)
    return [int(base + (1 if index < remainder else 0)) for index in range(int(section_count))]


def _fit_value_font(draw: ImageDraw.ImageDraw, text: str, *, max_width: float, max_height: float) -> Any:
    return fit_font_to_box(
        draw,
        text=str(text),
        max_width=float(max_width),
        max_height=float(max_height),
        bold=True,
        min_size_px=18,
        max_size_px=42,
        fill_ratio=0.95,
    )


def _draw_metric_card(
    draw: ImageDraw.ImageDraw,
    *,
    card: _MetricCard,
    card_bbox: Sequence[float],
    infographic_style: str,
    card_fill: Tuple[int, int, int],
    page_outline: Tuple[int, int, int],
    text_rgb: Tuple[int, int, int],
    muted_rgb: Tuple[int, int, int],
    caption_font: Any,
    label_font_base: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    x0, y0, x1, y1 = [float(value) for value in card_bbox]
    card_w = float(x1 - x0)
    card_h = float(y1 - y0)
    card_fill_i = tuple(int(channel) for channel in card_fill)
    if str(infographic_style) in {"kpi_dashboard", "radial_spokes", "circular_sections"}:
        card_fill_i = _blend_rgb(card_fill, card.color_rgb, 0.06)
    elif str(infographic_style) == "staggered_mosaic":
        card_fill_i = _blend_rgb(card_fill, card.color_rgb, 0.035)

    draw.rounded_rectangle((x0, y0, x1, y1), radius=10, fill=card_fill_i, outline=page_outline, width=1)
    if str(infographic_style) == "circular_sections":
        draw.rounded_rectangle((x0, y0, x1, y0 + 7), radius=7, fill=card.color_rgb)
        icon_bbox = (x0 + 9, y0 + 24, x0 + 38, y0 + 53)
    elif str(infographic_style) == "radial_spokes":
        draw.rounded_rectangle((x0, y0, x1, y0 + 7), radius=7, fill=card.color_rgb)
        icon_bbox = (x0 + 15, y0 + 24, x0 + 54, y0 + 63)
    else:
        draw.rounded_rectangle((x0, y0, x0 + 8, y1), radius=8, fill=card.color_rgb)
        icon_bbox = (x0 + 18, y0 + 20, x0 + 60, y0 + 62)
    _draw_icon(draw, bbox=icon_bbox, kind=card.icon_kind, color=card.color_rgb)

    if str(infographic_style) == "circular_sections":
        text_left = x0 + 44
    else:
        text_left = x0 + (66 if str(infographic_style) == "radial_spokes" else 72)
    label_font = fit_font_to_box(
        draw,
        text=card.label,
        max_width=max(40.0, x1 - text_left - 14),
        max_height=24,
        bold=True,
        min_size_px=12,
        max_size_px=int(label_font_base),
        fill_ratio=0.98,
    )
    label_xy = (text_left, y0 + (20 if str(infographic_style) in {"radial_spokes", "circular_sections"} else 18))
    draw.text(label_xy, card.label, fill=text_rgb, font=label_font)
    label_bbox = _text_bbox(draw, label_xy, card.label, label_font)

    value_font = _fit_value_font(
        draw,
        card.display_text,
        max_width=max(42.0, x1 - text_left - 14),
        max_height=max(30.0, min(44.0, card_h - 58.0)),
    )
    value_xy = (text_left, y0 + (47 if str(infographic_style) in {"radial_spokes", "circular_sections"} else 45))
    draw.text(value_xy, card.display_text, fill=card.color_rgb, font=value_font)
    value_bbox = _text_bbox(draw, value_xy, card.display_text, value_font)

    caption = f"Ref {int(card.caption_number)}"
    caption_xy = (x0 + (10 if str(infographic_style) == "circular_sections" else 18), y1 - 25)
    draw.text(caption_xy, caption, fill=muted_rgb, font=caption_font)
    caption_bbox = _text_bbox(draw, caption_xy, caption, caption_font)

    trace = {
        "card_id": str(card.card_id),
        "label": str(card.label),
        "value": int(card.value),
        "display_text": str(card.display_text),
        "unit": str(card.unit),
        "section": str(card.section),
        "card_bbox_px": [float(x0), float(y0), float(x1), float(y1)],
        "label_bbox_px": list(label_bbox),
        "value_bbox_px": list(value_bbox),
        "caption_bbox_px": list(caption_bbox),
        "icon_bbox_px": [float(value) for value in icon_bbox],
        "icon_kind": str(card.icon_kind),
        "color_rgb": [int(channel) for channel in card.color_rgb],
        "caption_number": int(card.caption_number),
    }
    entity = {
        "id": str(card.card_id),
        "type": "infographic_metric_card",
        "bbox_px": [float(x0), float(y0), float(x1), float(y1)],
        "attrs": {
            "label": str(card.label),
            "value": int(card.value),
            "display_text": str(card.display_text),
            "unit": str(card.unit),
            "section": str(card.section),
            "icon_kind": str(card.icon_kind),
            "caption_number": int(card.caption_number),
        },
    }
    return trace, entity


def _render_infographic(
    background: Image.Image,
    *,
    cards: Sequence[_MetricCard],
    section_titles: Sequence[str],
    section_card_counts: Sequence[int],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> _RenderedInfographic:
    render_defaults = {**dict(render_defaults), "_render_style_seed": int(instance_seed)}
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    margin_x = int(group_default(render_defaults, "page_margin_x_px", 34))
    margin_top = int(group_default(render_defaults, "page_margin_top_px", 30))
    margin_bottom = int(group_default(render_defaults, "page_margin_bottom_px", 30))
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_x),
        right_px=int(margin_x),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=render_defaults,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    section_gap = int(group_default(render_defaults, "section_gap_px", 14))
    card_gap = int(group_default(render_defaults, "card_gap_px", 12))
    section_pad = int(group_default(render_defaults, "section_padding_px", 14))
    header_h = int(group_default(render_defaults, "header_height_px", 62))
    section_header_h = int(group_default(render_defaults, "section_header_height_px", 34))

    title_font = load_font(int(group_default(render_defaults, "title_font_size_px", 30)), bold=True)
    subtitle_font = load_font(int(group_default(render_defaults, "subtitle_font_size_px", 16)), bold=False)
    section_font = load_font(int(group_default(render_defaults, "section_font_size_px", 20)), bold=True)
    label_font_base = int(group_default(render_defaults, "label_font_size_px", 18))
    caption_font = load_font(int(group_default(render_defaults, "caption_font_size_px", 13)), bold=False)

    page_fill = _render_rgb(render_defaults, "page_fill_rgb", (255, 255, 255))
    page_outline = _render_rgb(render_defaults, "page_outline_rgb", (216, 220, 226))
    text_rgb = _render_rgb(render_defaults, "text_rgb", (38, 41, 48))
    muted_rgb = _render_rgb(render_defaults, "muted_text_rgb", (96, 103, 114))
    section_fill = _render_rgb(render_defaults, "section_fill_rgb", (245, 247, 250))
    card_fill = _render_rgb(render_defaults, "card_fill_rgb", (255, 255, 255))
    style_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.infographic_style")
    explicit_style = str(render_defaults.get("infographic_style", "")).strip()
    if explicit_style:
        if explicit_style not in set(_INFOGRAPHIC_STYLE_VARIANTS):
            raise ValueError(f"unsupported infographic_style: {explicit_style}")
        infographic_style = explicit_style
    else:
        infographic_style = str(_INFOGRAPHIC_STYLE_VARIANTS[int(style_rng.randrange(len(_INFOGRAPHIC_STYLE_VARIANTS)))])
    accent_rgb = _PALETTE[int(style_rng.randrange(len(_PALETTE)))]
    accent_alt_rgb = _PALETTE[int(style_rng.randrange(len(_PALETTE)))]
    if str(infographic_style) == "kpi_dashboard":
        page_fill = _blend_rgb((248, 250, 252), accent_rgb, 0.08)
        section_fill = _blend_rgb((255, 255, 255), accent_rgb, 0.10)
        card_fill = _blend_rgb((255, 255, 255), accent_alt_rgb, 0.04)
    elif str(infographic_style) == "staggered_mosaic":
        page_fill = _blend_rgb((250, 251, 252), accent_alt_rgb, 0.05)
        section_fill = _blend_rgb((247, 249, 251), accent_rgb, 0.08)
        card_fill = _blend_rgb((255, 255, 255), accent_alt_rgb, 0.03)
    elif str(infographic_style) == "column_fact_sheet":
        page_fill = _blend_rgb((255, 253, 248), accent_rgb, 0.06)
        section_fill = _blend_rgb((246, 248, 250), accent_alt_rgb, 0.12)
        card_fill = _blend_rgb((255, 255, 255), accent_rgb, 0.03)
    elif str(infographic_style) == "radial_spokes":
        page_fill = _blend_rgb((249, 250, 252), accent_rgb, 0.05)
        section_fill = _blend_rgb((255, 255, 255), accent_alt_rgb, 0.08)
        card_fill = _blend_rgb((255, 255, 255), accent_rgb, 0.02)
    elif str(infographic_style) == "circular_sections":
        page_fill = _blend_rgb((250, 250, 248), accent_alt_rgb, 0.06)
        section_fill = _blend_rgb((255, 255, 255), accent_rgb, 0.10)
        card_fill = _blend_rgb((255, 255, 255), accent_alt_rgb, 0.025)

    page_bbox = (margin_left, margin_top, width - margin_right, height - margin_bottom)
    draw.rounded_rectangle(page_bbox, radius=16, fill=page_fill, outline=page_outline, width=2)
    if str(infographic_style) == "kpi_dashboard":
        draw.rounded_rectangle(
            (margin_left + 14, margin_top + 12, width - margin_right - 14, margin_top + 58),
            radius=12,
            fill=_blend_rgb(accent_rgb, (255, 255, 255), 0.22),
        )
    elif str(infographic_style) == "column_fact_sheet":
        stripe_w = max(18, int((width - margin_left - margin_right) * 0.025))
        draw.rounded_rectangle(
            (margin_left + 14, margin_top + 14, margin_left + 14 + stripe_w, height - margin_bottom - 14),
            radius=10,
            fill=_blend_rgb(accent_rgb, (255, 255, 255), 0.10),
        )
    title_x = margin_left + 26
    title_y = margin_top + 16
    title_text, subtitle_text = _STYLE_TITLE_COPY.get(
        str(infographic_style),
        _STYLE_TITLE_COPY["card_wall"],
    )
    draw.text((title_x, title_y), title_text, fill=text_rgb, font=title_font)
    draw.text((title_x, title_y + 36), subtitle_text, fill=muted_rgb, font=subtitle_font)

    section_count = len(section_titles)
    layout_mode = "stacked"
    if str(infographic_style) == "column_fact_sheet":
        layout_mode = "masonry_columns"
    elif str(infographic_style) == "radial_spokes":
        layout_mode = "radial_spokes"
    elif str(infographic_style) == "circular_sections":
        layout_mode = "circular_sections"

    row_counts: List[int] = []
    col_counts: List[int] = []
    max_columns_per_section = 5 if int(section_count) >= 5 else 4
    for section_index, count in enumerate(section_card_counts):
        if str(layout_mode) in {"masonry_columns", "radial_spokes"}:
            columns = min(2, max(1, int(count)))
        elif str(layout_mode) == "circular_sections":
            columns = min(3, max(1, int(count)))
        else:
            columns = min(int(max_columns_per_section), max(1, int(count)))
            if str(infographic_style) == "staggered_mosaic" and int(count) >= 4 and int(section_index) % 2 == 1:
                columns = max(2, int(columns) - 1)
        rows = int(math.ceil(float(count) / float(columns)))
        col_counts.append(int(columns))
        row_counts.append(int(rows))

    content_top = margin_top + header_h + 22
    content_bottom = height - margin_bottom - 18

    card_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    section_bboxes: Dict[str, List[float]] = {}
    card_index = 0

    if str(layout_mode) == "masonry_columns":
        lane_count = 2
        lane_gap = max(22, int(card_gap) + 10)
        content_left = margin_left + 44
        content_right = width - margin_right - 26
        lane_w = (float(content_right - content_left) - float((lane_count - 1) * lane_gap)) / float(lane_count)
        lane_tops = [float(content_top), float(content_top + 28)]
        card_h = 92
        for section_index, section_title in enumerate(section_titles):
            count = int(section_card_counts[section_index])
            columns = int(col_counts[section_index])
            rows = int(row_counts[section_index])
            lane_index = min(range(lane_count), key=lambda index: lane_tops[int(index)])
            section_x0 = float(content_left + (lane_index * (lane_w + lane_gap)))
            section_y0 = float(lane_tops[int(lane_index)])
            section_h = float(section_header_h + (2 * section_pad) + (rows * card_h) + (max(0, rows - 1) * card_gap))
            section_bbox = (section_x0, section_y0, section_x0 + lane_w, section_y0 + section_h)
            section_bboxes[str(section_title)] = [float(value) for value in section_bbox]
            section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.08)
            draw.rounded_rectangle(section_bbox, radius=12, fill=section_fill_i, outline=page_outline, width=1)
            draw.rectangle(
                (section_bbox[0], section_bbox[1], section_bbox[0] + 8, section_bbox[3]),
                fill=_PALETTE[section_index % len(_PALETTE)],
            )
            draw.text((section_bbox[0] + section_pad, section_bbox[1] + 8), str(section_title), fill=text_rgb, font=section_font)

            grid_left = section_bbox[0] + section_pad
            grid_top = section_bbox[1] + section_header_h + section_pad
            grid_w = section_bbox[2] - section_bbox[0] - (2 * section_pad)
            card_w = (grid_w - ((columns - 1) * card_gap)) / float(columns)
            for local_index in range(count):
                card = cards[card_index]
                row = local_index // columns
                col = local_index % columns
                x0 = grid_left + (col * (card_w + card_gap))
                y0 = grid_top + (row * (card_h + card_gap))
                trace, entity = _draw_metric_card(
                    draw,
                    card=card,
                    card_bbox=[float(x0), float(y0), float(x0 + card_w), float(y0 + card_h)],
                    infographic_style=str(infographic_style),
                    card_fill=card_fill,
                    page_outline=page_outline,
                    text_rgb=text_rgb,
                    muted_rgb=muted_rgb,
                    caption_font=caption_font,
                    label_font_base=label_font_base,
                )
                card_traces.append(dict(trace))
                entities.append(dict(entity))
                card_index += 1
            lane_tops[int(lane_index)] = float(section_y0 + section_h + section_gap + (6 if int(section_index) % 2 else 0))

        return _RenderedInfographic(
            image=image,
            entities=entities,
            card_traces=card_traces,
            section_bboxes=section_bboxes,
            layout_jitter_meta={
                **dict(layout_jitter_meta),
                "infographic_style": str(infographic_style),
                "layout_mode": str(layout_mode),
            },
        )

    if str(layout_mode) == "circular_sections":
        content_left = margin_left + 26
        content_right = width - margin_right - 26
        panel_gap_x = 28
        panel_gap_y = 18
        row_slots = 2 if int(section_count) <= 4 else 3
        panel_w = (float(content_right - content_left) - panel_gap_x) / 2.0
        panel_h = (float(content_bottom - content_top) - ((row_slots - 1) * panel_gap_y)) / float(row_slots)
        if int(section_count) == 4:
            section_slots = [(0.0, 0), (1.0, 0), (0.0, 1), (1.0, 1)]
        elif int(section_count) == 5:
            section_slots = [(0.0, 0), (1.0, 0), (0.0, 1), (1.0, 1), (0.5, 2)]
        else:
            section_slots = [(0.0, 0), (1.0, 0), (0.0, 1), (1.0, 1), (0.0, 2), (1.0, 2)]
        hub_x = (float(content_left) + float(content_right)) * 0.5
        hub_y = float(content_top) + ((float(content_bottom) - float(content_top)) * 0.5)
        draw.ellipse(
            (hub_x - 36, hub_y - 36, hub_x + 36, hub_y + 36),
            fill=_blend_rgb(accent_rgb, (255, 255, 255), 0.24),
            outline=_blend_rgb(page_outline, accent_rgb, 0.35),
            width=2,
        )
        draw.ellipse(
            (hub_x - 9, hub_y - 9, hub_x + 9, hub_y + 9),
            fill=accent_rgb,
        )

        for section_index in range(int(section_count)):
            slot_x, slot_row = section_slots[int(section_index)]
            section_x0 = float(content_left) + float(slot_x) * (float(content_right - content_left) - float(panel_w))
            section_y0 = float(content_top) + (float(slot_row) * (float(panel_h) + float(panel_gap_y)))
            panel_center = (section_x0 + (panel_w * 0.5), section_y0 + (panel_h * 0.5))
            draw.line(
                (hub_x, hub_y, panel_center[0], panel_center[1]),
                fill=_blend_rgb(page_outline, accent_alt_rgb, 0.34),
                width=2,
            )

        ring_slot_order = (
            (1, 0),
            (2, 0),
            (2, 1),
            (2, 2),
            (1, 2),
            (0, 2),
            (0, 1),
            (0, 0),
        )
        ring_indices_by_count: Dict[int, Tuple[int, ...]] = {
            1: (0,),
            2: (6, 2),
            3: (0, 2, 6),
            4: (0, 2, 4, 6),
            5: (0, 2, 3, 5, 6),
            6: (0, 1, 2, 4, 5, 6),
            7: (0, 1, 2, 3, 4, 5, 6),
            8: (0, 1, 2, 3, 4, 5, 6, 7),
        }

        for section_index, section_title in enumerate(section_titles):
            count = int(section_card_counts[section_index])
            slot_x, slot_row = section_slots[int(section_index)]
            section_x0 = float(content_left) + float(slot_x) * (float(content_right - content_left) - float(panel_w))
            section_y0 = float(content_top) + (float(slot_row) * (float(panel_h) + float(panel_gap_y)))
            section_bbox = (section_x0, section_y0, section_x0 + panel_w, section_y0 + panel_h)
            section_bboxes[str(section_title)] = [float(value) for value in section_bbox]
            section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.07)
            draw.rounded_rectangle(section_bbox, radius=20, fill=section_fill_i, outline=page_outline, width=1)
            draw.ellipse(
                (
                    section_bbox[0] + 12,
                    section_bbox[1] + 12,
                    section_bbox[2] - 12,
                    section_bbox[3] - 12,
                ),
                outline=_blend_rgb(_PALETTE[section_index % len(_PALETTE)], page_outline, 0.45),
                width=2,
            )

            grid_pad = 10.0
            ring_gap = 7.0
            grid_left = section_bbox[0] + grid_pad
            grid_top = section_bbox[1] + grid_pad
            grid_w = section_bbox[2] - section_bbox[0] - (2.0 * grid_pad)
            grid_h = section_bbox[3] - section_bbox[1] - (2.0 * grid_pad)
            card_w = (grid_w - (2.0 * ring_gap)) / 3.0
            card_h = max(78.0, min(96.0, (grid_h - (2.0 * ring_gap)) / 3.0))
            grid_y = grid_top + max(0.0, (grid_h - ((3.0 * card_h) + (2.0 * ring_gap))) * 0.5)

            title_pill_w = min(card_w + 18.0, grid_w * 0.38)
            title_pill_h = 31.0
            center_x = grid_left + card_w + ring_gap + (card_w * 0.5)
            center_y = grid_y + card_h + ring_gap + (card_h * 0.5)
            title_bbox = (
                center_x - (title_pill_w * 0.5),
                center_y - (title_pill_h * 0.5),
                center_x + (title_pill_w * 0.5),
                center_y + (title_pill_h * 0.5),
            )
            draw.rounded_rectangle(
                title_bbox,
                radius=14,
                fill=_blend_rgb((255, 255, 255), _PALETTE[section_index % len(_PALETTE)], 0.05),
                outline=_blend_rgb(page_outline, _PALETTE[section_index % len(_PALETTE)], 0.22),
                width=1,
            )
            title_font_fit = fit_font_to_box(
                draw,
                text=str(section_title),
                max_width=max(52.0, title_pill_w - 12.0),
                max_height=20.0,
                bold=True,
                min_size_px=9,
                max_size_px=14,
                fill_ratio=0.96,
            )
            title_text_bbox = _text_bbox(draw, (0, 0), str(section_title), title_font_fit)
            title_text_w = float(title_text_bbox[2] - title_text_bbox[0])
            title_text_h = float(title_text_bbox[3] - title_text_bbox[1])
            draw.text(
                (center_x - (title_text_w * 0.5), center_y - (title_text_h * 0.62)),
                str(section_title),
                fill=text_rgb,
                font=title_font_fit,
            )

            slot_indices = ring_indices_by_count.get(int(count), ring_indices_by_count[8])
            for local_index in range(count):
                card = cards[card_index]
                slot_col, slot_row_inner = ring_slot_order[int(slot_indices[int(local_index) % len(slot_indices)])]
                x0 = grid_left + (float(slot_col) * (card_w + ring_gap))
                y0 = grid_y + (float(slot_row_inner) * (card_h + ring_gap))
                trace, entity = _draw_metric_card(
                    draw,
                    card=card,
                    card_bbox=[float(x0), float(y0), float(x0 + card_w), float(y0 + card_h)],
                    infographic_style=str(infographic_style),
                    card_fill=card_fill,
                    page_outline=page_outline,
                    text_rgb=text_rgb,
                    muted_rgb=muted_rgb,
                    caption_font=caption_font,
                    label_font_base=label_font_base,
                )
                card_traces.append(dict(trace))
                entities.append(dict(entity))
                card_index += 1

        return _RenderedInfographic(
            image=image,
            entities=entities,
            card_traces=card_traces,
            section_bboxes=section_bboxes,
            layout_jitter_meta={
                **dict(layout_jitter_meta),
                "infographic_style": str(infographic_style),
                "layout_mode": str(layout_mode),
            },
        )

    if str(layout_mode) == "radial_spokes":
        content_left = margin_left + 26
        content_right = width - margin_right - 26
        panel_gap_x = 28
        panel_gap_y = 18
        row_slots = 2 if int(section_count) <= 4 else 3
        panel_w = (float(content_right - content_left) - panel_gap_x) / 2.0
        panel_h = (float(content_bottom - content_top) - ((row_slots - 1) * panel_gap_y)) / float(row_slots)
        if int(section_count) == 4:
            slots = [(0.0, 0), (1.0, 0), (0.0, 1), (1.0, 1)]
        elif int(section_count) == 5:
            slots = [(0.0, 0), (1.0, 0), (0.0, 1), (1.0, 1), (0.5, 2)]
        else:
            slots = [(0.0, 0), (1.0, 0), (0.0, 1), (1.0, 1), (0.0, 2), (1.0, 2)]
        hub_x = (float(content_left) + float(content_right)) * 0.5
        hub_y = float(content_top) + ((float(content_bottom) - float(content_top)) * 0.5)
        for section_index in range(int(section_count)):
            slot_x, slot_row = slots[int(section_index)]
            section_x0 = float(content_left) + float(slot_x) * (float(content_right - content_left) - float(panel_w))
            section_y0 = float(content_top) + (float(slot_row) * (float(panel_h) + float(panel_gap_y)))
            panel_center = (section_x0 + (panel_w * 0.5), section_y0 + (panel_h * 0.5))
            draw.line(
                (hub_x, hub_y, panel_center[0], panel_center[1]),
                fill=_blend_rgb(page_outline, accent_rgb, 0.30),
                width=2,
            )
        draw.ellipse(
            (hub_x - 10, hub_y - 10, hub_x + 10, hub_y + 10),
            fill=_blend_rgb(accent_rgb, (255, 255, 255), 0.20),
            outline=page_outline,
            width=2,
        )

        for section_index, section_title in enumerate(section_titles):
            count = int(section_card_counts[section_index])
            columns = int(col_counts[section_index])
            rows = int(row_counts[section_index])
            slot_x, slot_row = slots[int(section_index)]
            section_x0 = float(content_left) + float(slot_x) * (float(content_right - content_left) - float(panel_w))
            section_y0 = float(content_top) + (float(slot_row) * (float(panel_h) + float(panel_gap_y)))
            card_h = int(max(84, min(118, math.floor((panel_h - section_header_h - (2 * section_pad) - (max(0, rows - 1) * card_gap)) / max(1, rows)))))
            section_h = float(section_header_h + (2 * section_pad) + (rows * card_h) + (max(0, rows - 1) * card_gap))
            section_bbox = (section_x0, section_y0, section_x0 + panel_w, section_y0 + section_h)
            section_bboxes[str(section_title)] = [float(value) for value in section_bbox]
            section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.08)
            draw.rounded_rectangle(section_bbox, radius=14, fill=section_fill_i, outline=page_outline, width=1)
            draw.text((section_bbox[0] + section_pad, section_bbox[1] + 8), str(section_title), fill=text_rgb, font=section_font)

            grid_left = section_bbox[0] + section_pad
            grid_top = section_bbox[1] + section_header_h + section_pad
            grid_w = section_bbox[2] - section_bbox[0] - (2 * section_pad)
            card_w = (grid_w - ((columns - 1) * card_gap)) / float(columns)
            for local_index in range(count):
                card = cards[card_index]
                row = local_index // columns
                col = local_index % columns
                x0 = grid_left + (col * (card_w + card_gap))
                y0 = grid_top + (row * (card_h + card_gap))
                trace, entity = _draw_metric_card(
                    draw,
                    card=card,
                    card_bbox=[float(x0), float(y0), float(x0 + card_w), float(y0 + card_h)],
                    infographic_style=str(infographic_style),
                    card_fill=card_fill,
                    page_outline=page_outline,
                    text_rgb=text_rgb,
                    muted_rgb=muted_rgb,
                    caption_font=caption_font,
                    label_font_base=label_font_base,
                )
                card_traces.append(dict(trace))
                entities.append(dict(entity))
                card_index += 1

        return _RenderedInfographic(
            image=image,
            entities=entities,
            card_traces=card_traces,
            section_bboxes=section_bboxes,
            layout_jitter_meta={
                **dict(layout_jitter_meta),
                "infographic_style": str(infographic_style),
                "layout_mode": str(layout_mode),
            },
        )

    total_rows = max(1, sum(row_counts))
    available = float(content_bottom - content_top - ((section_count - 1) * section_gap))
    fixed = float(section_count * (section_header_h + (2 * section_pad)))
    card_h = int(max(86, min(136, math.floor((available - fixed - (sum(max(0, rows - 1) for rows in row_counts) * card_gap)) / total_rows))))

    y = float(content_top)
    for section_index, section_title in enumerate(section_titles):
        count = int(section_card_counts[section_index])
        columns = int(col_counts[section_index])
        rows = int(row_counts[section_index])
        section_h = float(section_header_h + (2 * section_pad) + (rows * card_h) + (max(0, rows - 1) * card_gap))
        left_extra = 0
        right_extra = 0
        if str(infographic_style) == "staggered_mosaic":
            left_extra = (0, 38, 10, 56, 24, 44)[int(section_index) % 6]
            right_extra = (46, 8, 40, 0, 54, 18)[int(section_index) % 6]
        section_bbox = (
            margin_left + 18 + float(left_extra),
            y,
            width - margin_right - 18 - float(right_extra),
            y + section_h,
        )
        section_bboxes[str(section_title)] = [float(value) for value in section_bbox]
        section_fill_i = section_fill
        if str(infographic_style) in {"kpi_dashboard", "staggered_mosaic"}:
            section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.06)
        draw.rounded_rectangle(section_bbox, radius=12, fill=section_fill_i, outline=page_outline, width=1)
        draw.text((section_bbox[0] + section_pad, section_bbox[1] + 8), str(section_title), fill=text_rgb, font=section_font)

        grid_left = section_bbox[0] + section_pad
        grid_top = section_bbox[1] + section_header_h + section_pad
        grid_w = section_bbox[2] - section_bbox[0] - (2 * section_pad)
        card_w = (grid_w - ((columns - 1) * card_gap)) / float(columns)
        for local_index in range(count):
            card = cards[card_index]
            row = local_index // columns
            col = local_index % columns
            x0 = grid_left + (col * (card_w + card_gap))
            y0 = grid_top + (row * (card_h + card_gap))
            trace, entity = _draw_metric_card(
                draw,
                card=card,
                card_bbox=[float(x0), float(y0), float(x0 + card_w), float(y0 + card_h)],
                infographic_style=str(infographic_style),
                card_fill=card_fill,
                page_outline=page_outline,
                text_rgb=text_rgb,
                muted_rgb=muted_rgb,
                caption_font=caption_font,
                label_font_base=label_font_base,
            )
            card_traces.append(dict(trace))
            entities.append(dict(entity))
            card_index += 1
        y += section_h + section_gap

    return _RenderedInfographic(
        image=image,
        entities=entities,
        card_traces=card_traces,
        section_bboxes=section_bboxes,
        layout_jitter_meta={
            **dict(layout_jitter_meta),
            "infographic_style": str(infographic_style),
            "layout_mode": str(layout_mode),
        },
    )


def _build_cards(
    *,
    query_id: str,
    card_count: int,
    section_titles: Sequence[str],
    section_card_counts: Sequence[int],
    values_by_label: Mapping[str, int],
    percent_mode: bool,
    instance_seed: int,
) -> List[_MetricCard]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.cards")
    labels = list(values_by_label.keys())
    cards: List[_MetricCard] = []
    label_index = 0
    repeated_icon_offset = int(rng.randrange(len(_ICON_KINDS))) if str(query_id) == "section_icon_extremum_label" else 0
    for section_index, section_title in enumerate(section_titles):
        for local_index in range(int(section_card_counts[section_index])):
            label = labels[label_index]
            value = int(values_by_label[str(label)])
            unit = "%" if bool(percent_mode) else ""
            display = f"{value}%" if bool(percent_mode) else str(value)
            color = _PALETTE[(label_index + int(rng.randrange(len(_PALETTE)))) % len(_PALETTE)]
            if str(query_id) == "section_icon_extremum_label":
                icon_kind = _ICON_KINDS[(int(local_index) + int(repeated_icon_offset)) % len(_ICON_KINDS)]
            else:
                icon_kind = _ICON_KINDS[(label_index + int(rng.randrange(len(_ICON_KINDS)))) % len(_ICON_KINDS)]
            caption_number = 10 + int(rng.randrange(80))
            cards.append(
                _MetricCard(
                    card_id=f"metric_{label_index}",
                    label=str(label),
                    value=int(value),
                    display_text=str(display),
                    unit=str(unit),
                    section=str(section_title),
                    icon_kind=str(icon_kind),
                    color_rgb=tuple(int(channel) for channel in color),
                    caption_number=int(caption_number),
                )
            )
            label_index += 1
    if len(cards) != int(card_count):
        raise ValueError(f"expected {card_count} cards, built {len(cards)} for {query_id}")
    return cards


def _unique_extremum_for_section(
    labels: Sequence[str],
    values_by_label: Mapping[str, int],
    *,
    extremum_kind: str,
) -> Tuple[str, int] | None:
    section_values = [(str(label), int(values_by_label[str(label)])) for label in labels]
    if not section_values:
        return None
    if str(extremum_kind) == "maximum":
        target_value = max(value for _, value in section_values)
    elif str(extremum_kind) == "minimum":
        target_value = min(value for _, value in section_values)
    else:
        raise ValueError(f"unsupported extremum_kind: {extremum_kind}")
    winners = [(label, value) for label, value in section_values if int(value) == int(target_value)]
    if len(winners) != 1:
        return None
    return str(winners[0][0]), int(winners[0][1])


def _sample_section_extrema_query(
    *,
    rng: Any,
    section_titles: Sequence[str],
    labels_by_section: Mapping[str, Sequence[str]],
    values_by_label: Mapping[str, int],
) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    for section_a in section_titles:
        for section_b in section_titles:
            if str(section_a) == str(section_b):
                continue
            for extremum_a in _EXTREMUM_KINDS:
                selected_a = _unique_extremum_for_section(
                    labels_by_section[str(section_a)],
                    values_by_label,
                    extremum_kind=str(extremum_a),
                )
                if selected_a is None:
                    continue
                for extremum_b in _EXTREMUM_KINDS:
                    selected_b = _unique_extremum_for_section(
                        labels_by_section[str(section_b)],
                        values_by_label,
                        extremum_kind=str(extremum_b),
                    )
                    if selected_b is None:
                        continue
                    label_a, value_a = selected_a
                    label_b, value_b = selected_b
                    for operation in _EXTREMA_OPERATIONS:
                        if str(operation) == "sum":
                            answer = int(value_a) + int(value_b)
                        elif str(operation) == "absolute_difference":
                            answer = abs(int(value_a) - int(value_b))
                            if int(answer) == 0:
                                continue
                        else:
                            raise ValueError(f"unsupported extrema operation: {operation}")
                        candidates.append(
                            {
                                "section_a": str(section_a),
                                "section_b": str(section_b),
                                "extremum_a": str(extremum_a),
                                "extremum_b": str(extremum_b),
                                "operation": str(operation),
                                "label_a": str(label_a),
                                "label_b": str(label_b),
                                "value_a": int(value_a),
                                "value_b": int(value_b),
                                "answer": int(answer),
                            }
                        )
    if not candidates:
        raise ValueError("could not build section extrema query with unique section extrema")
    return dict(candidates[int(rng.randrange(len(candidates)))])


def _sample_section_total_extrema_query(
    *,
    section_titles: Sequence[str],
    labels_by_section: Mapping[str, Sequence[str]],
    values_by_label: Dict[str, int],
    value_min: int,
    value_max: int,
) -> Dict[str, Any]:
    """Select the unique highest-total and lowest-total sections."""

    for _ in range(12):
        section_totals = _section_totals(labels_by_section, values_by_label)
        max_total = max(int(value) for value in section_totals.values())
        min_total = min(int(value) for value in section_totals.values())
        max_sections = [str(section) for section in section_titles if int(section_totals[str(section)]) == int(max_total)]
        min_sections = [str(section) for section in section_titles if int(section_totals[str(section)]) == int(min_total)]
        if len(max_sections) == 1 and len(min_sections) == 1 and int(max_total) > int(min_total):
            high_section = str(max_sections[0])
            low_section = str(min_sections[0])
            return {
                "high_section": high_section,
                "low_section": low_section,
                "high_total": int(max_total),
                "low_total": int(min_total),
                "answer": int(max_total) - int(min_total),
                "section_totals": dict(section_totals),
            }

        if len(max_sections) > 1:
            kept_section = str(max_sections[0])
            for rank, section in enumerate(max_sections[1:], start=1):
                lowered = _adjust_section_total(
                    values_by_label,
                    labels_by_section[str(section)],
                    delta=-int(rank),
                    value_min=int(value_min),
                    value_max=int(value_max),
                )
                if not lowered:
                    _adjust_section_total(
                        values_by_label,
                        labels_by_section[kept_section],
                        delta=int(rank),
                        value_min=int(value_min),
                        value_max=int(value_max),
                    )
            continue

        if len(min_sections) > 1:
            kept_section = str(min_sections[0])
            for rank, section in enumerate(min_sections[1:], start=1):
                raised = _adjust_section_total(
                    values_by_label,
                    labels_by_section[str(section)],
                    delta=int(rank),
                    value_min=int(value_min),
                    value_max=int(value_max),
                )
                if not raised:
                    _adjust_section_total(
                        values_by_label,
                        labels_by_section[kept_section],
                        delta=-int(rank),
                        value_min=int(value_min),
                        value_max=int(value_max),
                    )
            continue

    raise ValueError("could not build section-total extrema query with unique highest and lowest sections")


def _resolve_rank_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    explicit = params.get("rank_direction")
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(_RANK_DIRECTIONS):
            raise ValueError(f"rank_direction must be one of {_RANK_DIRECTIONS}")
        return selected, {selected: 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.rank_direction",
    )
    selected = str(_RANK_DIRECTIONS[int(index) % len(_RANK_DIRECTIONS)])
    probability = 1.0 / float(len(_RANK_DIRECTIONS))
    return selected, {str(direction): probability for direction in _RANK_DIRECTIONS}


def _resolve_rank_position(
    params: Mapping[str, Any],
    *,
    section_count: int,
    instance_seed: int,
) -> Tuple[int, Dict[str, float]]:
    support = [int(value) for value in _RANK_POSITION_SUPPORT if int(value) <= int(section_count)]
    if not support:
        support = [2] if int(section_count) >= 2 else [1]
    explicit = params.get("rank_position")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"rank_position must be in {support} for section_count={section_count}")
        return int(selected), {str(int(selected)): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.rank_position.{section_count}",
    )
    selected = int(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return int(selected), {str(value): probability for value in support}


def _nudge_duplicate_section_totals(
    values_by_label: Dict[str, int],
    *,
    labels_by_section: Mapping[str, Sequence[str]],
    section_titles: Sequence[str],
    value_min: int,
    value_max: int,
) -> bool:
    totals = _section_totals(labels_by_section, values_by_label)
    seen: Dict[int, str] = {}
    for section in section_titles:
        total = int(totals[str(section)])
        if total not in seen:
            seen[total] = str(section)
            continue
        labels = list(labels_by_section[str(section)])
        if _adjust_section_total(
            values_by_label,
            labels,
            delta=1,
            value_min=int(value_min),
            value_max=int(value_max),
        ):
            return True
        return _adjust_section_total(
            values_by_label,
            labels,
            delta=-1,
            value_min=int(value_min),
            value_max=int(value_max),
        )
    return False


def _sample_section_ranked_total_query(
    *,
    params: Mapping[str, Any],
    section_titles: Sequence[str],
    labels_by_section: Mapping[str, Sequence[str]],
    values_by_label: Dict[str, int],
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> Dict[str, Any]:
    """Select a unique ranked section total."""

    direction, direction_probabilities = _resolve_rank_direction(params, instance_seed=int(instance_seed))
    rank_position, rank_position_probabilities = _resolve_rank_position(
        params,
        section_count=len(section_titles),
        instance_seed=int(instance_seed),
    )
    for _ in range(16):
        section_totals = _section_totals(labels_by_section, values_by_label)
        total_values = [int(value) for value in section_totals.values()]
        if len(set(total_values)) == len(total_values):
            reverse = str(direction) == "highest"
            ranked = sorted(
                ((str(section), int(section_totals[str(section)])) for section in section_titles),
                key=lambda item: item[1],
                reverse=reverse,
            )
            section, total = ranked[int(rank_position) - 1]
            return {
                "answer_section": str(section),
                "answer_total": int(total),
                "rank_direction": str(direction),
                "rank_position": int(rank_position),
                "rank_ordinal": str(_RANK_ORDINALS.get(int(rank_position), f"{rank_position}th")),
                "section_totals": dict(section_totals),
                "rank_direction_probabilities": dict(direction_probabilities),
                "rank_position_probabilities": dict(rank_position_probabilities),
            }
        if not _nudge_duplicate_section_totals(
            values_by_label,
            labels_by_section=labels_by_section,
            section_titles=section_titles,
            value_min=int(value_min),
            value_max=int(value_max),
        ):
            break
    raise ValueError("could not build ranked section-total query with unique section totals")


def _sample_section_icon_extremum_query(
    *,
    params: Mapping[str, Any],
    section_titles: Sequence[str],
    cards: Sequence[_MetricCard],
    instance_seed: int,
) -> Dict[str, Any]:
    """Select a unique section whose filtered icon-card total is highest/lowest."""

    direction, direction_probabilities = _resolve_rank_direction(params, instance_seed=int(instance_seed))
    cards_by_section_icon: Dict[Tuple[str, str], List[_MetricCard]] = {}
    for card in cards:
        cards_by_section_icon.setdefault((str(card.section), str(card.icon_kind)), []).append(card)

    candidates: List[Dict[str, Any]] = []
    for icon_kind in _ICON_KINDS:
        filtered_totals: Dict[str, int] = {}
        filtered_labels_by_section: Dict[str, List[str]] = {}
        for section in section_titles:
            icon_cards = list(cards_by_section_icon.get((str(section), str(icon_kind)), []))
            if not icon_cards:
                continue
            filtered_totals[str(section)] = int(sum(int(card.value) for card in icon_cards))
            filtered_labels_by_section[str(section)] = [str(card.label) for card in icon_cards]
        if len(filtered_totals) < 2:
            continue
        target_value = max(filtered_totals.values()) if str(direction) == "highest" else min(filtered_totals.values())
        winners = [str(section) for section, total in filtered_totals.items() if int(total) == int(target_value)]
        if len(winners) != 1:
            continue
        answer_section = str(winners[0])
        candidates.append(
            {
                "icon_kind": str(icon_kind),
                "answer_section": str(answer_section),
                "answer_total": int(target_value),
                "target_labels": [str(label) for label in filtered_labels_by_section[str(answer_section)]],
                "filtered_section_totals": {str(section): int(total) for section, total in filtered_totals.items()},
                "rank_direction": str(direction),
                "rank_direction_probabilities": dict(direction_probabilities),
            }
        )
    if not candidates:
        raise ValueError("could not build section-icon extremum query with a unique filtered section total")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.section_icon_extremum")
    return dict(candidates[int(rng.randrange(len(candidates)))])


def _build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    card_count, card_count_range, card_count_probabilities = _resolve_int_range(
        params,
        gen_defaults=_GEN_DEFAULTS,
        min_key="card_count_min",
        max_key="card_count_max",
        explicit_key="card_count",
        fallback_min=8,
        fallback_max=16,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.card_count",
    )
    section_count, section_count_range, section_count_probabilities = _resolve_section_count(
        params,
        gen_defaults=_GEN_DEFAULTS,
        query_id=str(query_id),
        card_count=int(card_count),
        instance_seed=int(instance_seed),
    )
    if int(section_count) > int(card_count):
        section_count = int(card_count)

    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=10,
        fallback_max=99,
        context=f"generation defaults for {TASK_ID}",
    )
    percent_min, percent_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="percent_value_min",
        max_key="percent_value_max",
        fallback_min=10,
        fallback_max=90,
        context=f"generation defaults for {TASK_ID}",
    )

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset.{query_id}")
    labels = list(_METRIC_LABEL_POOL)
    rng.shuffle(labels)
    labels = labels[: int(card_count)]
    section_titles = list(_SECTION_TITLE_POOL)
    rng.shuffle(section_titles)
    section_titles = section_titles[: int(section_count)]
    section_card_counts = _partition_cards(int(card_count), int(section_count))

    values_by_label: Dict[str, int] = {
        str(label): int(rng.randint(int(value_min), int(value_max)))
        for label in labels
    }
    labels_by_section = _labels_by_section(
        labels=labels,
        section_titles=section_titles,
        section_card_counts=section_card_counts,
    )
    target_labels: List[str]
    target_values: List[int]
    target_groups: Dict[str, List[str]] = {}
    target_sections: List[str] = []
    excluded_labels: List[str] = []
    target_extrema: List[str] = []
    extrema_operation = ""
    rank_direction = ""
    rank_ordinal = ""
    rank_position = 0
    rank_direction_probabilities: Dict[str, float] = {}
    rank_position_probabilities: Dict[str, float] = {}
    target_operand_count = 1
    percent_mode = False
    answer_value: int | str
    answer_type = "integer"
    arithmetic_expression: str
    filter_icon_kind = ""
    comparison_icon_kind = ""
    filtered_section_totals: Dict[str, int] = {}
    prebuilt_cards: List[_MetricCard] | None = None

    if str(query_id) == "sum_named_metrics":
        operand_count, operand_count_range, operand_count_probabilities = _resolve_int_range(
            params,
            gen_defaults=_GEN_DEFAULTS,
            min_key="sum_operand_count_min",
            max_key="sum_operand_count_max",
            explicit_key="operand_count",
            fallback_min=4,
            fallback_max=6,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.sum_operand_count",
        )
        target_operand_count = int(operand_count)
        target_labels = rng.sample(labels, k=int(target_operand_count))
        target_values = [int(values_by_label[label]) for label in target_labels]
        answer_value = int(sum(target_values))
        arithmetic_expression = " + ".join(str(value) for value in target_values)
    elif str(query_id) == "section_extrema_arithmetic":
        extrema_query = _sample_section_extrema_query(
            rng=rng,
            section_titles=section_titles,
            labels_by_section=labels_by_section,
            values_by_label=values_by_label,
        )
        section_a = str(extrema_query["section_a"])
        section_b = str(extrema_query["section_b"])
        label_a = str(extrema_query["label_a"])
        label_b = str(extrema_query["label_b"])
        value_a = int(extrema_query["value_a"])
        value_b = int(extrema_query["value_b"])
        target_sections = [section_a, section_b]
        target_extrema = [str(extrema_query["extremum_a"]), str(extrema_query["extremum_b"])]
        extrema_operation = str(extrema_query["operation"])
        target_groups = {"section_a_extremum": [label_a], "section_b_extremum": [label_b]}
        target_labels = [label_a, label_b]
        target_values = [value_a, value_b]
        target_operand_count = 2
        operand_count_range = (2, 2)
        operand_count_probabilities = {"2": 1.0}
        answer_value = int(extrema_query["answer"])
        if str(extrema_operation) == "sum":
            arithmetic_expression = f"{target_extrema[0]}({section_a}) + {target_extrema[1]}({section_b})"
        else:
            arithmetic_expression = f"abs({target_extrema[0]}({section_a}) - {target_extrema[1]}({section_b}))"
    elif str(query_id) == "section_total_extrema_difference":
        total_query = _sample_section_total_extrema_query(
            section_titles=section_titles,
            labels_by_section=labels_by_section,
            values_by_label=values_by_label,
            value_min=int(value_min),
            value_max=int(value_max),
        )
        section_a = str(total_query["high_section"])
        section_b = str(total_query["low_section"])
        group_a = list(labels_by_section[section_a])
        group_b = list(labels_by_section[section_b])
        target_sections = [section_a, section_b]
        target_groups = {"highest_total_section": list(group_a), "lowest_total_section": list(group_b)}
        target_labels = list(group_a) + list(group_b)
        sum_a = int(total_query["high_total"])
        sum_b = int(total_query["low_total"])
        target_values = [int(values_by_label[label]) for label in target_labels]
        target_operand_count = len(target_labels)
        operand_count_range = (min(section_card_counts) * 2, max(section_card_counts) * 2)
        operand_count_probabilities = {str(target_operand_count): 1.0}
        answer_value = int(sum_a - sum_b)
        target_extrema = ["highest_total", "lowest_total"]
        extrema_operation = "absolute_difference"
        arithmetic_expression = f"sum({section_a}) - sum({section_b})"
    elif str(query_id) == "section_total_except_named":
        exclusion_count, exclusion_count_range, _exclusion_count_probabilities = _resolve_int_range(
            params,
            gen_defaults=_GEN_DEFAULTS,
            min_key="excluded_metric_count_min",
            max_key="excluded_metric_count_max",
            explicit_key="excluded_metric_count",
            fallback_min=2,
            fallback_max=2,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.excluded_metric_count",
        )
        included_count_min = int(params.get(
            "section_except_included_count_min",
            group_default(_GEN_DEFAULTS, "section_except_included_count_min", 3),
        ))
        eligible_sections = [
            str(section_title)
            for section_title, section_labels in labels_by_section.items()
            if len(section_labels) - int(exclusion_count) >= int(included_count_min)
        ]
        if not eligible_sections:
            raise ValueError(
                f"no section has at least {included_count_min} included cards after excluding "
                f"{exclusion_count} cards for {query_id}"
            )
        target_section = str(eligible_sections[int(rng.randrange(len(eligible_sections)))])
        section_labels = list(labels_by_section[target_section])
        excluded_labels = [str(label) for label in rng.sample(section_labels, k=int(exclusion_count))]
        included_labels = [str(label) for label in section_labels if str(label) not in set(excluded_labels)]
        target_sections = [target_section]
        target_groups = {"included": list(included_labels), "excluded": list(excluded_labels)}
        target_labels = list(section_labels)
        target_values = [int(values_by_label[label]) for label in target_labels]
        target_operand_count = len(included_labels)
        operand_count_range = (
            max(1, min(section_card_counts) - int(exclusion_count_range[1])),
            max(section_card_counts) - int(exclusion_count_range[0]),
        )
        operand_count_probabilities = {str(target_operand_count): 1.0}
        answer_value = int(sum(int(values_by_label[label]) for label in included_labels))
        arithmetic_expression = f"sum({target_section}) - ({' + '.join(str(values_by_label[label]) for label in excluded_labels)})"
    elif str(query_id) == "section_ranked_total_label":
        ranked_query = _sample_section_ranked_total_query(
            params=params,
            section_titles=section_titles,
            labels_by_section=labels_by_section,
            values_by_label=values_by_label,
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )
        target_section = str(ranked_query["answer_section"])
        section_labels = [str(label) for label in labels_by_section[target_section]]
        target_sections = [target_section]
        target_groups = {"answer_section": list(section_labels)}
        target_labels = list(section_labels)
        target_values = [int(values_by_label[label]) for label in target_labels]
        target_operand_count = len(target_labels)
        operand_count_range = (min(section_card_counts), max(section_card_counts))
        operand_count_probabilities = {str(target_operand_count): 1.0}
        answer_value = str(target_section)
        answer_type = "string"
        rank_direction = str(ranked_query["rank_direction"])
        rank_ordinal = str(ranked_query["rank_ordinal"])
        rank_position = int(ranked_query["rank_position"])
        rank_direction_probabilities = dict(ranked_query["rank_direction_probabilities"])
        rank_position_probabilities = dict(ranked_query["rank_position_probabilities"])
        arithmetic_expression = f"rank_{rank_position}_{rank_direction}_section_total"
    elif str(query_id) == "section_icon_total_value":
        prebuilt_cards = _build_cards(
            query_id=str(query_id),
            card_count=int(card_count),
            section_titles=section_titles,
            section_card_counts=section_card_counts,
            values_by_label=values_by_label,
            percent_mode=bool(percent_mode),
            instance_seed=int(instance_seed),
        )
        cards_by_section_icon: Dict[Tuple[str, str], List[_MetricCard]] = {}
        for card in prebuilt_cards:
            cards_by_section_icon.setdefault((str(card.section), str(card.icon_kind)), []).append(card)
        preferred = [
            (section, icon, cards_for_icon)
            for (section, icon), cards_for_icon in cards_by_section_icon.items()
            if len(cards_for_icon) >= 2
        ]
        candidates = preferred or [
            (section, icon, cards_for_icon)
            for (section, icon), cards_for_icon in cards_by_section_icon.items()
            if cards_for_icon
        ]
        if not candidates:
            raise ValueError("could not build section-icon filtered total query")
        target_section, filter_icon_kind, icon_cards = candidates[int(rng.randrange(len(candidates)))]
        filtered_labels = [str(card.label) for card in icon_cards]
        target_sections = [str(target_section)]
        target_groups = {"filtered_icon_cards": list(filtered_labels)}
        target_labels = list(filtered_labels)
        target_values = [int(values_by_label[label]) for label in target_labels]
        target_operand_count = len(target_labels)
        operand_count_range = (1, max(section_card_counts))
        operand_count_probabilities = {str(target_operand_count): 1.0}
        answer_value = int(sum(target_values))
        arithmetic_expression = f"sum({target_section}, icon={filter_icon_kind})"
    elif str(query_id) == "section_icon_total_difference_value":
        prebuilt_cards = _build_cards(
            query_id=str(query_id),
            card_count=int(card_count),
            section_titles=section_titles,
            section_card_counts=section_card_counts,
            values_by_label=values_by_label,
            percent_mode=bool(percent_mode),
            instance_seed=int(instance_seed),
        )
        cards_by_section_icon: Dict[Tuple[str, str], List[_MetricCard]] = {}
        for card in prebuilt_cards:
            cards_by_section_icon.setdefault((str(card.section), str(card.icon_kind)), []).append(card)
        candidates: List[Dict[str, Any]] = []
        for icon_kind in _ICON_KINDS:
            sections_with_icon = [
                str(section)
                for section in section_titles
                if cards_by_section_icon.get((str(section), str(icon_kind)))
            ]
            for index_a, section_a in enumerate(sections_with_icon):
                for section_b in sections_with_icon[index_a + 1 :]:
                    group_a = cards_by_section_icon[(str(section_a), str(icon_kind))]
                    group_b = cards_by_section_icon[(str(section_b), str(icon_kind))]
                    total_a = sum(int(card.value) for card in group_a)
                    total_b = sum(int(card.value) for card in group_b)
                    gap = abs(int(total_a) - int(total_b))
                    if int(gap) == 0:
                        continue
                    candidates.append(
                        {
                            "icon_kind": str(icon_kind),
                            "section_a": str(section_a),
                            "section_b": str(section_b),
                            "group_a": [str(card.label) for card in group_a],
                            "group_b": [str(card.label) for card in group_b],
                            "gap": int(gap),
                        }
                    )
        if not candidates:
            raise ValueError("could not build section-icon total difference query")
        selected = dict(candidates[int(rng.randrange(len(candidates)))])
        comparison_icon_kind = str(selected["icon_kind"])
        section_a = str(selected["section_a"])
        section_b = str(selected["section_b"])
        group_a = [str(label) for label in selected["group_a"]]
        group_b = [str(label) for label in selected["group_b"]]
        target_sections = [section_a, section_b]
        target_groups = {"section_a_filtered_icon_cards": list(group_a), "section_b_filtered_icon_cards": list(group_b)}
        target_labels = list(group_a) + list(group_b)
        target_values = [int(values_by_label[label]) for label in target_labels]
        target_operand_count = len(target_labels)
        operand_count_range = (2, max(section_card_counts) * 2)
        operand_count_probabilities = {str(target_operand_count): 1.0}
        answer_value = int(selected["gap"])
        arithmetic_expression = f"abs(sum({section_a}, icon={comparison_icon_kind}) - sum({section_b}, icon={comparison_icon_kind}))"
    elif str(query_id) == "section_icon_extremum_label":
        prebuilt_cards = _build_cards(
            query_id=str(query_id),
            card_count=int(card_count),
            section_titles=section_titles,
            section_card_counts=section_card_counts,
            values_by_label=values_by_label,
            percent_mode=bool(percent_mode),
            instance_seed=int(instance_seed),
        )
        extremum_query = _sample_section_icon_extremum_query(
            params=params,
            section_titles=section_titles,
            cards=prebuilt_cards,
            instance_seed=int(instance_seed),
        )
        comparison_icon_kind = str(extremum_query["icon_kind"])
        target_section = str(extremum_query["answer_section"])
        filtered_labels = [str(label) for label in extremum_query["target_labels"]]
        filtered_section_totals = {
            str(section): int(total)
            for section, total in dict(extremum_query["filtered_section_totals"]).items()
        }
        target_sections = [str(target_section)]
        target_groups = {"answer_section_filtered_icon_cards": list(filtered_labels)}
        target_labels = list(filtered_labels)
        target_values = [int(values_by_label[label]) for label in target_labels]
        target_operand_count = len(target_labels)
        operand_count_range = (1, max(section_card_counts))
        operand_count_probabilities = {str(target_operand_count): 1.0}
        answer_value = str(target_section)
        answer_type = "string"
        rank_direction = str(extremum_query["rank_direction"])
        rank_direction_probabilities = dict(extremum_query["rank_direction_probabilities"])
        arithmetic_expression = f"{rank_direction}_section_total(icon={comparison_icon_kind})"
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    cards = prebuilt_cards or _build_cards(
        query_id=str(query_id),
        card_count=int(card_count),
        section_titles=section_titles,
        section_card_counts=section_card_counts,
        values_by_label=values_by_label,
        percent_mode=bool(percent_mode),
        instance_seed=int(instance_seed),
    )
    return {
        "cards": cards,
        "labels": [str(label) for label in labels],
        "values_by_label": dict(values_by_label),
        "section_titles": [str(title) for title in section_titles],
        "section_card_counts": [int(value) for value in section_card_counts],
        "section_totals": dict(_section_totals(labels_by_section, values_by_label)),
        "card_count": int(card_count),
        "card_count_range": [int(card_count_range[0]), int(card_count_range[1])],
        "card_count_probabilities": dict(card_count_probabilities),
        "section_count": int(section_count),
        "section_count_range": [int(section_count_range[0]), int(section_count_range[1])],
        "section_count_probabilities": dict(section_count_probabilities),
        "target_labels": [str(label) for label in target_labels],
        "target_values": [int(value) for value in target_values],
        "target_groups": {str(key): [str(label) for label in value] for key, value in target_groups.items()},
        "target_sections": [str(section) for section in target_sections],
        "excluded_labels": [str(label) for label in excluded_labels],
        "target_extrema": [str(extremum) for extremum in target_extrema],
        "extrema_operation": str(extrema_operation),
        "target_operand_count": int(target_operand_count),
        "target_operand_count_range": [int(operand_count_range[0]), int(operand_count_range[1])],
        "target_operand_count_probabilities": dict(operand_count_probabilities),
        "answer_value": answer_value if str(answer_type) == "string" else int(answer_value),
        "answer_type": str(answer_type),
        "rank_direction": str(rank_direction),
        "rank_ordinal": str(rank_ordinal),
        "rank_position": int(rank_position),
        "rank_direction_probabilities": dict(rank_direction_probabilities),
        "rank_position_probabilities": dict(rank_position_probabilities),
        "filter_icon_kind": str(filter_icon_kind),
        "comparison_icon_kind": str(comparison_icon_kind),
        "filtered_section_totals": {str(section): int(total) for section, total in filtered_section_totals.items()},
        "arithmetic_expression": str(arithmetic_expression),
        "percent_mode": bool(percent_mode),
        "value_min": int(value_min),
        "value_max": int(value_max),
        "percent_value_min": int(percent_min),
        "percent_value_max": int(percent_max),
    }


def _evidence_bboxes(
    *,
    card_traces: Sequence[Mapping[str, Any]],
    target_labels: Sequence[str],
) -> List[List[float]]:
    by_label = {str(card["label"]): dict(card) for card in card_traces}
    bboxes: List[List[float]] = []
    for label in target_labels:
        card = by_label[str(label)]
        bboxes.append([float(value) for value in card["label_bbox_px"]])
        bboxes.append([float(value) for value in card["value_bbox_px"]])
    return bboxes


def _build_prompt_examples(*, answer_type: str) -> Tuple[str, str]:
    example_answer: int | str = "Program Totals" if str(answer_type) == "string" else 64
    answer_and_evidence = {
        "evidence": [[120, 180, 174, 202], [188, 214, 232, 246], [410, 180, 466, 202], [478, 214, 520, 246]],
        "answer": example_answer,
    }
    answer_only = {"answer": example_answer}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


class PagesInfographicMetricArithmeticValueTask:
    """Compute arithmetic over printed values in a poster-style infographic."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "infographic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))

        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 940)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 900)))
        background, background_meta = make_background_canvas(
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        render_params = dict(_RENDER_DEFAULTS)
        if params.get("infographic_style") is not None:
            render_params["infographic_style"] = params["infographic_style"]
        rendered = _render_infographic(
            background,
            cards=dataset["cards"],
            section_titles=dataset["section_titles"],
            section_card_counts=dataset["section_card_counts"],
            render_defaults=render_params,
            instance_seed=int(instance_seed),
        )
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
                "answer_hint",
                "answer_hint_label",
                "evidence_hint",
                "evidence_hint_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_type = str(dataset.get("answer_type", "integer"))
        answer_value_for_trace: int | str
        if answer_type == "string":
            answer_value_for_trace = str(dataset["answer_value"])
        else:
            answer_value_for_trace = int(dataset["answer_value"])
        json_example, json_example_answer_only = _build_prompt_examples(answer_type=answer_type)
        target_labels = [str(label) for label in dataset["target_labels"]]
        target_values = [int(value) for value in dataset["target_values"]]
        target_groups = {
            str(key): [str(label) for label in value]
            for key, value in dict(dataset["target_groups"]).items()
        }
        target_sections = [str(section) for section in dataset["target_sections"]]
        excluded_labels = [str(label) for label in dataset["excluded_labels"]]
        target_extrema = [str(extremum) for extremum in dataset["target_extrema"]]
        extrema_operation = str(dataset["extrema_operation"])
        extrema_operation_phrase = "absolute difference" if str(extrema_operation) == "absolute_difference" else str(extrema_operation)
        answer_hint_key = "answer_hint_label" if answer_type == "string" else "answer_hint"
        evidence_hint_key = "evidence_hint_label" if answer_type == "string" else "evidence_hint"
        answer_hint = str(prompt_defaults.get(answer_hint_key, prompt_defaults["answer_hint"]))
        evidence_hint = str(prompt_defaults.get(evidence_hint_key, prompt_defaults["evidence_hint"]))
        group_a_labels = target_groups.get("group_a", target_groups.get("section_a", []))
        group_b_labels = target_groups.get("group_b", target_groups.get("section_b", []))
        if not group_a_labels:
            group_a_labels = target_labels[: max(1, len(target_labels) // 2)]
        if not group_b_labels:
            group_b_labels = target_labels[max(1, len(target_labels) // 2) :]
        prompt_slots = {
            "target_label": _quote_label(target_labels[0]),
            "target_label_a": _quote_label(target_labels[0]),
            "target_label_b": _quote_label(target_labels[1]) if len(target_labels) > 1 else "",
            "target_labels": _quoted_label_list(target_labels),
            "target_group_a": _quoted_label_list(group_a_labels),
            "target_group_b": _quoted_label_list(group_b_labels),
            "target_section": _quote_label(target_sections[0]) if target_sections else "",
            "target_section_a": _quote_label(target_sections[0]) if len(target_sections) >= 1 else "",
            "target_section_b": _quote_label(target_sections[1]) if len(target_sections) >= 2 else "",
            "target_extremum_a": str(target_extrema[0]) if len(target_extrema) >= 1 else "",
            "target_extremum_b": str(target_extrema[1]) if len(target_extrema) >= 2 else "",
            "extrema_operation": str(extrema_operation_phrase),
            "rank_direction": str(dataset.get("rank_direction", "")),
            "rank_ordinal": str(dataset.get("rank_ordinal", "")),
            "rank_order_phrase": (
                "highest to lowest"
                if str(dataset.get("rank_direction", "")) == "highest"
                else "lowest to highest"
            ),
            "rank_position": str(dataset.get("rank_position", "")),
            "excluded_labels": _quoted_label_list(excluded_labels) if excluded_labels else "",
            "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
            "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(evidence_hint),
            "answer_hint": str(answer_hint),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bboxes = _evidence_bboxes(card_traces=rendered.card_traces, target_labels=target_labels)
        answer_gt = TypedValue(type=answer_type, value=answer_value_for_trace)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        label_bbox_map = {
            str(card["label"]): [float(value) for value in card["label_bbox_px"]]
            for card in rendered.card_traces
        }
        value_bbox_map = {
            str(card["label"]): [float(value) for value in card["value_bbox_px"]]
            for card in rendered.card_traces
        }
        card_bbox_map = {
            str(card["label"]): [float(value) for value in card["card_bbox_px"]]
            for card in rendered.card_traces
        }

        trace_payload = {
            "scene_ir": {
                "scene_id": SCENE_ID,
                "scene_kind": "pages_infographic_metric_cards",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "target_labels": list(target_labels),
                    "target_values": list(target_values),
                    "target_groups": dict(target_groups),
                    "target_sections": list(target_sections),
                    "excluded_labels": list(excluded_labels),
                    "target_extrema": list(target_extrema),
                    "extrema_operation": str(extrema_operation),
                    "rank_direction": str(dataset.get("rank_direction", "")),
                    "rank_ordinal": str(dataset.get("rank_ordinal", "")),
                    "rank_position": int(dataset.get("rank_position", 0)),
                    "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
                    "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
                    "filtered_section_totals": dict(dataset.get("filtered_section_totals", {})),
                    "answer_value": answer_value_for_trace,
                    "answer_type": str(answer_type),
                    "arithmetic_expression": str(dataset["arithmetic_expression"]),
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
                    "query_id_probabilities": dict(query_id_probabilities),
                    "card_count": int(dataset["card_count"]),
                    "section_count": int(dataset["section_count"]),
                    "target_labels": list(target_labels),
                    "target_values": list(target_values),
                    "target_groups": dict(target_groups),
                    "target_sections": list(target_sections),
                    "excluded_labels": list(excluded_labels),
                    "target_extrema": list(target_extrema),
                    "extrema_operation": str(extrema_operation),
                    "rank_direction": str(dataset.get("rank_direction", "")),
                    "rank_ordinal": str(dataset.get("rank_ordinal", "")),
                    "rank_position": int(dataset.get("rank_position", 0)),
                    "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
                    "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
                    "filtered_section_totals": dict(dataset.get("filtered_section_totals", {})),
                    "target_answer": answer_value_for_trace,
                    "answer_type": str(answer_type),
                },
            },
            "render_spec": {
                "canvas_width": int(canvas_width),
                "canvas_height": int(canvas_height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "scene_variant": str(rendered.layout_jitter_meta.get("infographic_style", "card_wall")),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(rendered.layout_jitter_meta),
                "section_bboxes_px": dict(rendered.section_bboxes),
                "text_style": {
                    "title_font_size_px": int(group_default(_RENDER_DEFAULTS, "title_font_size_px", 30)),
                    "label_font_size_px": int(group_default(_RENDER_DEFAULTS, "label_font_size_px", 18)),
                    "caption_font_size_px": int(group_default(_RENDER_DEFAULTS, "caption_font_size_px", 13)),
                },
            },
            "render_map": {
                "image_id": "img0",
                "card_bboxes_px": dict(card_bbox_map),
                "label_bboxes_px": dict(label_bbox_map),
                "value_bboxes_px": dict(value_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "answer_value": answer_value_for_trace,
                "answer_type": str(answer_type),
                "arithmetic_expression": str(dataset["arithmetic_expression"]),
                "target_labels": list(target_labels),
                "target_values": list(target_values),
                "target_groups": dict(target_groups),
                "target_sections": list(target_sections),
                "excluded_labels": list(excluded_labels),
                "target_extrema": list(target_extrema),
                "extrema_operation": str(extrema_operation),
                "rank_direction": str(dataset.get("rank_direction", "")),
                "rank_ordinal": str(dataset.get("rank_ordinal", "")),
                "rank_position": int(dataset.get("rank_position", 0)),
                "rank_direction_probabilities": dict(dataset.get("rank_direction_probabilities", {})),
                "rank_position_probabilities": dict(dataset.get("rank_position_probabilities", {})),
                "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
                "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
                "filtered_section_totals": {
                    str(section): int(total)
                    for section, total in dict(dataset.get("filtered_section_totals", {})).items()
                },
                "labels": [str(label) for label in dataset["labels"]],
                "values_by_label": {str(label): int(value) for label, value in dataset["values_by_label"].items()},
                "cards": [dict(card) for card in rendered.card_traces],
                "card_count": int(dataset["card_count"]),
                "card_count_range": list(dataset["card_count_range"]),
                "card_count_probabilities": dict(dataset["card_count_probabilities"]),
                "section_count": int(dataset["section_count"]),
                "section_count_range": list(dataset["section_count_range"]),
                "section_count_probabilities": dict(dataset["section_count_probabilities"]),
                "section_titles": [str(title) for title in dataset["section_titles"]],
                "section_card_counts": [int(value) for value in dataset["section_card_counts"]],
                "section_totals": {str(section): int(value) for section, value in dataset["section_totals"].items()},
                "target_operand_count": int(dataset["target_operand_count"]),
                "target_operand_count_range": list(dataset["target_operand_count_range"]),
                "target_operand_count_probabilities": dict(dataset["target_operand_count_probabilities"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "question_format": "label_open" if answer_type == "string" else "numeric_open",
                "percent_mode": bool(dataset["percent_mode"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "percent_value_min": int(dataset["percent_value_min"]),
                "percent_value_max": int(dataset["percent_value_max"]),
            },
            "witness_symbolic": {
                "type": "metric_card_set",
                "labels": list(target_labels),
                "groups": dict(target_groups),
                "sections": list(target_sections),
                "excluded_labels": list(excluded_labels),
                "extrema": list(target_extrema),
                "extrema_operation": str(extrema_operation),
                "rank_direction": str(dataset.get("rank_direction", "")),
                "rank_ordinal": str(dataset.get("rank_ordinal", "")),
                "rank_position": int(dataset.get("rank_position", 0)),
                "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
                "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
                "values": list(target_values),
                "expression": str(dataset["arithmetic_expression"]),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
                "label_bbox_map": dict(label_bbox_map),
                "value_bbox_map": dict(value_bbox_map),
                "target_labels": list(target_labels),
            },
        }

        reasoning_load = float(_REASONING_LOAD_BY_VARIANT[str(query_id)])
        if str(query_id) == "sum_named_metrics":
            reasoning_load = min(
                1.0,
                reasoning_load
                + (0.14 * normalize_int_with_bounds(int(dataset["target_operand_count"]), dataset["target_operand_count_range"])),
            )
        complexity = build_pages_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(dataset["card_count"]), dataset["card_count_range"]),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": normalize_int_with_bounds(int(dataset["section_count"]), dataset["section_count_range"]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


def _scoped_infographic_params(
    params: Mapping[str, Any],
    *,
    allowed_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Restrict the shared infographic generator to one public task's query set."""

    allowed = tuple(str(value) for value in allowed_query_ids if str(value).strip())
    allowed_set = set(allowed)
    scoped = dict(params)
    explicit_query = scoped.get("query_id")
    explicit_task = scoped.get("query_id")
    if explicit_query is not None:
        if explicit_task is not None and str(explicit_task) != str(explicit_query):
            raise ValueError("query_id conflicts with query_id")
        scoped["query_id"] = str(explicit_query)
    explicit_task = scoped.get("query_id")
    if explicit_task is not None and str(explicit_task) not in allowed_set:
        raise ValueError(f"unsupported query id for infographic task: {explicit_task}")
    scoped["_supported_query_ids"] = tuple(allowed)
    if explicit_task is None:
        scoped.pop("query_id_weights", None)
    return scoped


def _query_probabilities_from_output(output: TaskOutput, query_id: str) -> Dict[str, float]:
    payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
    execution = payload.get("execution_trace") if isinstance(payload, Mapping) else {}
    if isinstance(execution, Mapping) and isinstance(execution.get("query_id_probabilities"), Mapping):
        return {str(key): float(value) for key, value in execution["query_id_probabilities"].items()}
    return {str(query_id): 1.0}


class _PagesInfographicPublicTaskMixin:
    default_dataset_enabled = True
    allowed_query_ids: Sequence[str] = ()

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scoped_params = _scoped_infographic_params(
            params,
            allowed_query_ids=tuple(self.allowed_query_ids),
        )
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=scoped_params,
            max_attempts=int(max_attempts),
        )
        query_id = str(output.query_id)
        return rewrite_pages_query_output(
            output,
            query_id=str(query_id),
            scene_id=SCENE_ID,
            query_probabilities=_query_probabilities_from_output(output, query_id),
        )


@register_task
class PagesInfographicMetricArithmeticValuePublicTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Compute one sampled arithmetic value over infographic metric cards."""

    task_id = "task_pages__infographic__metric_arithmetic_value"
    allowed_query_ids = SUPPORTED_QUERY_IDS


@register_task
class PagesInfographicSectionRankedTotalLabelTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Identify a section by ranked aggregate total over infographic metric cards."""

    task_id = "task_pages__infographic__section_ranked_total_label"
    allowed_query_ids = SECTION_RANKED_TOTAL_VARIANTS


@register_task
class PagesInfographicFilteredMetricTotalValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Sum visible metric cards matching an icon filter inside one section."""

    task_id = "task_pages__infographic__filtered_metric_total_value"
    allowed_query_ids = FILTERED_METRIC_TOTAL_VARIANTS


@register_task
class PagesInfographicColumnProfileComparisonValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Compare same-icon metric totals between two infographic sections."""

    task_id = "task_pages__infographic__column_profile_comparison_value"
    allowed_query_ids = COLUMN_PROFILE_COMPARISON_VARIANTS


@register_task
class PagesInfographicFilteredSectionExtremumLabelTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Identify the section with an extreme total after filtering by card icon."""

    task_id = "task_pages__infographic__filtered_section_extremum_label"
    allowed_query_ids = FILTERED_SECTION_EXTREMUM_VARIANTS


__all__ = [
    "ALL_QUERY_IDS",
    "COLUMN_PROFILE_COMPARISON_VARIANTS",
    "FILTERED_SECTION_EXTREMUM_VARIANTS",
    "FILTERED_METRIC_TOTAL_VARIANTS",
    "PagesInfographicColumnProfileComparisonValueTask",
    "PagesInfographicFilteredSectionExtremumLabelTask",
    "PagesInfographicFilteredMetricTotalValueTask",
    "PagesInfographicMetricArithmeticValueTask",
    "PagesInfographicMetricArithmeticValuePublicTask",
    "PagesInfographicSectionRankedTotalLabelTask",
    "SECTION_RANKED_TOTAL_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
