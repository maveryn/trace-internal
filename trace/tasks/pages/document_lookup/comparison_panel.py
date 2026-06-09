"""Side-by-side comparison-panel page lookup task."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
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
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ....core.visual.noise import apply_post_image_noise
from ...shared.visual_style.information_scene import make_information_scene_background
from ..shared.complexity import build_pages_complexity, normalize_int_with_bounds, resolve_pages_complexity_weights
from ..shared.information_style import resolve_pages_information_style
from ..shared.legible_text import darken_surface_for_light_text, draw_required_page_text
from ..shared.page_text_resources import page_text_resource_metadata, sample_page_context_batch, sample_page_label_batch
from ..shared.visual_defaults import load_pages_noise_defaults


COMPARISON_PANEL_TASK_ID = "task_pages__comparison_panel__side_attribute_value_label"
TASK_GROUP = "document_lookup"
SCENE_ID = "comparison_panel"
QUERY_ID = "side_attribute_value_label"
SCENE_VARIANTS: Tuple[str, ...] = ("matrix_sheet", "feature_bands")
QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)

_ATTRIBUTE_VALUE_BANKS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Access", ("Lobby", "Gate", "Studio", "Dock", "Atrium", "Annex")),
    ("Format", ("Digital", "Print", "Audio", "Field", "Desk", "Hybrid")),
    ("Badge", ("Amber", "Cobalt", "Indigo", "Olive", "Violet", "Silver")),
    ("Code", ("K17", "M42", "R08", "T63", "V29", "X54")),
    ("Level", ("Basic", "Prime", "Select", "Core", "Plus", "Elite")),
    ("Pickup", ("North Pier", "West Loop", "River Bend", "Hill Yard", "Lake Point", "Mesa Park")),
    ("Shift", ("Early", "Midday", "Late", "Night", "Dawn", "Evening")),
    ("Material", ("Canvas", "Steel", "Glass", "Wool", "Cork", "Birch")),
    ("Signal", ("Teal", "Crimson", "Copper", "Navy", "Sage", "Slate")),
    ("Zone", ("Orchid", "Maple", "Quartz", "Pine", "Coral", "Granite")),
)
_ACCENTS: Tuple[Tuple[int, int, int], ...] = (
    (59, 122, 177),
    (46, 142, 112),
    (190, 93, 78),
    (126, 102, 183),
    (196, 142, 61),
    (72, 132, 151),
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
class _ComparisonSide:
    side_id: str
    label: str
    accent_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _ComparisonAttribute:
    attribute_id: str
    label: str
    values_by_side_id: Dict[str, str]


@dataclass(frozen=True)
class _ComparisonSpec:
    title: str
    subtitle: str
    sides: Tuple[_ComparisonSide, ...]
    attributes: Tuple[_ComparisonAttribute, ...]
    text_resource_metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedComparisonPanel:
    image: Image.Image
    entities: List[Dict[str, Any]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    side_header_bboxes_px: Dict[str, List[float]]
    attribute_label_bboxes_px: Dict[str, List[float]]
    value_cell_bboxes_px: Dict[str, Dict[str, List[float]]]
    layout_meta: Dict[str, Any]


_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=COMPARISON_PANEL_TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=COMPARISON_PANEL_TASK_ID)
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


def _resolve_render_params(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> _RenderParams:
    def _int_value(key: str, fallback: int, *, minimum: int = 1) -> int:
        return max(int(minimum), int(params.get(key, group_default(defaults, key, fallback))))

    return _RenderParams(
        canvas_width=_int_value("canvas_width", 1120, minimum=420),
        canvas_height=_int_value("canvas_height", 860, minimum=420),
        outer_margin_px=_int_value("outer_margin_px", 34, minimum=0),
        header_height_px=_int_value("header_height_px", 88, minimum=54),
        gap_px=_int_value("gap_px", 14, minimum=4),
        corner_radius_px=_int_value("corner_radius_px", 14, minimum=0),
        outline_width_px=_int_value("outline_width_px", 2, minimum=1),
        title_font_size_px=_int_value("title_font_size_px", 30, minimum=14),
        subtitle_font_size_px=_int_value("subtitle_font_size_px", 17, minimum=10),
        card_title_font_size_px=_int_value("card_title_font_size_px", 22, minimum=12),
        label_font_size_px=_int_value("label_font_size_px", 16, minimum=9),
        value_font_size_px=_int_value("value_font_size_px", 18, minimum=10),
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
    *,
    stroke_fill: Tuple[int, int, int] | None = None,
    stroke_width: int = 0,
    role: str = "readout",
    surface_rgbs: Sequence[Sequence[int]] | None = None,
    instance_seed: int = 0,
    namespace: str = "",
) -> List[float]:
    if surface_rgbs:
        return draw_required_page_text(
            draw,
            (float(xy[0]), float(xy[1])),
            str(text),
            font,
            role=str(role),
            surface_rgbs=surface_rgbs,
            instance_seed=int(instance_seed),
            namespace=str(namespace or f"comparison_panel.{role}"),
            preferred_rgbs=(fill,),
            stroke_width=max(0, int(stroke_width)),
        )
    kwargs: Dict[str, Any] = {"fill": fill, "font": font}
    if int(stroke_width) > 0 and stroke_fill is not None:
        kwargs["stroke_width"] = int(stroke_width)
        kwargs["stroke_fill"] = stroke_fill
    draw_text_traced(draw, (float(xy[0]), float(xy[1])), str(text), role=str(role), required=True, **kwargs)
    return _text_bbox(draw, xy, str(text), font, stroke_width=int(stroke_width))


def _blend_rgb(color_a: Sequence[int], color_b: Sequence[int], weight_b: float) -> Tuple[int, int, int]:
    weight = max(0.0, min(1.0, float(weight_b)))
    return tuple(
        int(round((float(color_a[index]) * (1.0 - weight)) + (float(color_b[index]) * weight)))
        for index in range(3)
    )


def _build_comparison_spec(
    *,
    side_count: int,
    attribute_count: int,
    instance_seed: int,
) -> _ComparisonSpec:
    rng = spawn_rng(int(instance_seed), "comparison_panel.spec")
    title_batch = sample_page_context_batch(
        rng,
        role="comparison_panel_title",
        count=1,
        manifest_names=("phrases/headlines.txt",),
    )
    subtitle_batch = sample_page_context_batch(
        rng,
        role="comparison_panel_subtitle",
        count=1,
        manifest_names=("phrases/captions.txt", "phrases/legend_notes.txt"),
    )
    side_batch = sample_page_label_batch(
        rng,
        role="comparison_panel_side_label",
        count=int(side_count),
        manifest_name="categories/abstract_group_labels.txt",
        min_chars=3,
        max_chars=14,
        allow_spaces=True,
        allow_punctuation=False,
    )
    side_labels = list(side_batch.values)
    banks = list(_ATTRIBUTE_VALUE_BANKS)
    rng.shuffle(banks)
    if int(attribute_count) > len(banks):
        raise ValueError("attribute_count exceeds available attribute banks")
    accent_offset = int(rng.randrange(len(_ACCENTS)))
    sides = tuple(
        _ComparisonSide(
            side_id=f"side_{index + 1}",
            label=str(side_labels[int(index)]),
            accent_rgb=tuple(int(value) for value in _ACCENTS[(int(index) + int(accent_offset)) % len(_ACCENTS)]),
        )
        for index in range(int(side_count))
    )
    attributes: List[_ComparisonAttribute] = []
    used_values: set[str] = set()
    for attr_index, (attribute_label, values) in enumerate(banks[: int(attribute_count)]):
        shuffled_values = [str(value) for value in values]
        rng.shuffle(shuffled_values)
        selected_values: List[str] = []
        for candidate in shuffled_values:
            if str(candidate) in used_values:
                continue
            selected_values.append(str(candidate))
            used_values.add(str(candidate))
            if len(selected_values) == int(side_count):
                break
        if len(selected_values) < int(side_count):
            raise ValueError(f"not enough unique values for comparison attribute {attribute_label}")
        attributes.append(
            _ComparisonAttribute(
                attribute_id=f"attribute_{int(attr_index) + 1}",
                label=str(attribute_label),
                values_by_side_id={
                    str(side.side_id): str(selected_values[int(index)])
                    for index, side in enumerate(sides)
                },
            )
        )
    return _ComparisonSpec(
        title=str(title_batch.values[0]),
        subtitle=str(subtitle_batch.values[0]),
        sides=tuple(sides),
        attributes=tuple(attributes),
        text_resource_metadata=page_text_resource_metadata(title_batch, subtitle_batch, side_batch),
    )


def _draw_panel_header(
    image: Image.Image,
    *,
    style: Any,
    render_params: _RenderParams,
    title: str,
    subtitle: str,
    instance_seed: int,
) -> Tuple[ImageDraw.ImageDraw, List[float], List[float]]:
    draw = ImageDraw.Draw(image)
    margin = int(render_params.outer_margin_px)
    panel_bbox = [
        float(margin),
        float(margin),
        float(render_params.canvas_width - margin),
        float(render_params.canvas_height - margin),
    ]
    shadow = max(0, int(style.shadow_offset_px))
    radius = max(int(render_params.corner_radius_px), int(style.corner_radius_px))
    if shadow:
        sx0, sy0, sx1, sy1 = [float(value) for value in panel_bbox]
        draw.rounded_rectangle(
            (sx0 + shadow, sy0 + shadow, sx1 + shadow, sy1 + shadow),
            radius=int(radius),
            fill=tuple(int(value) for value in style.shadow_rgb),
        )
    draw.rounded_rectangle(
        tuple(panel_bbox),
        radius=int(radius),
        fill=tuple(int(value) for value in style.surface_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=max(1, int(render_params.outline_width_px), int(style.frame_width_px)),
    )
    title_band_h = max(int(render_params.header_height_px), int(style.title_band_height_px))
    title_surface_rgb = tuple(int(value) for value in style.surface_rgb)
    if str(style.chrome_kind) in {"accent_header", "rule_header", "accent_frame"} or str(style.chrome_mode) == "accent_frame":
        header_fill = darken_surface_for_light_text(style.header_rgb, text_rgb=style.header_text_rgb)
        band_bbox = (panel_bbox[0], panel_bbox[1], panel_bbox[2], panel_bbox[1] + float(title_band_h))
        draw.rounded_rectangle(
            band_bbox,
            radius=int(radius),
            fill=header_fill,
        )
        draw.rectangle(
            (panel_bbox[0], panel_bbox[1] + float(title_band_h) - float(radius), panel_bbox[2], panel_bbox[1] + float(title_band_h)),
            fill=header_fill,
        )
        title_rgb = tuple(int(value) for value in style.header_text_rgb)
        subtitle_rgb = tuple(int(value) for value in style.header_text_rgb)
        title_surface_rgb = tuple(int(value) for value in header_fill)
    else:
        title_rgb = tuple(int(value) for value in style.text_rgb)
        subtitle_rgb = tuple(int(value) for value in style.muted_text_rgb)
        y_rule = float(panel_bbox[1] + title_band_h)
        draw.line((panel_bbox[0] + 20.0, y_rule, panel_bbox[2] - 20.0, y_rule), fill=style.guide_rgb, width=1)

    scale = float(style.typography_scale)
    title_font = load_font(max(10, int(round(render_params.title_font_size_px * scale))), bold=True)
    subtitle_font = load_font(max(8, int(round(render_params.subtitle_font_size_px * scale))), bold=False)
    title_xy = (float(margin + 24), float(margin + 18))
    title_bbox = _draw_text(
        draw,
        title_xy,
        str(title),
        title_font,
        title_rgb,
        role="page_title",
        surface_rgbs=(title_surface_rgb,),
        instance_seed=int(instance_seed),
        namespace=f"{COMPARISON_PANEL_TASK_ID}.page_title",
    )
    _draw_text(
        draw,
        (title_xy[0], title_xy[1] + 38.0),
        str(subtitle),
        subtitle_font,
        subtitle_rgb,
        role="page_subtitle",
        surface_rgbs=(title_surface_rgb,),
        instance_seed=int(instance_seed),
        namespace=f"{COMPARISON_PANEL_TASK_ID}.page_subtitle",
    )
    return draw, panel_bbox, title_bbox


def _render_comparison_panel(
    background: Image.Image,
    *,
    spec: _ComparisonSpec,
    scene_variant: str,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
) -> _RenderedComparisonPanel:
    image = background.convert("RGB")
    draw, panel_bbox, title_bbox = _draw_panel_header(
        image,
        style=style,
        render_params=render_params,
        title=str(spec.title),
        subtitle=str(spec.subtitle),
        instance_seed=int(instance_seed),
    )
    scale = float(style.typography_scale)
    text_rgb = tuple(int(value) for value in style.text_rgb)
    muted_rgb = tuple(int(value) for value in style.muted_text_rgb)
    guide_rgb = tuple(int(value) for value in style.guide_rgb)
    border_rgb = tuple(int(value) for value in style.panel_border_rgb)
    fill_rgb = tuple(int(value) for value in style.panel_fill_rgb)
    alt_rgb = tuple(int(value) for value in style.surface_alt_rgb)
    side_font_size = max(10, int(round(render_params.card_title_font_size_px * scale)))
    label_font_size = max(8, int(round(render_params.label_font_size_px * scale)))
    value_font_size = max(9, int(round(render_params.value_font_size_px * scale)))
    label_font = load_font(label_font_size, bold=True)
    value_font = load_font(value_font_size, bold=True)

    padding = max(14, int(style.panel_padding_px))
    content_left = float(panel_bbox[0] + padding)
    content_right = float(panel_bbox[2] - padding)
    content_top = float(panel_bbox[1] + max(render_params.header_height_px, style.title_band_height_px) + render_params.gap_px)
    content_bottom = float(panel_bbox[3] - padding)
    content_w = max(1.0, content_right - content_left)
    content_h = max(1.0, content_bottom - content_top)
    row_count = len(spec.attributes)
    side_count = len(spec.sides)
    header_h = max(58.0, min(78.0, content_h * 0.16))
    row_h = max(42.0, (content_h - header_h) / float(max(1, row_count)))
    label_col_w = max(176.0, min(270.0, content_w * (0.28 if side_count == 2 else 0.24)))
    value_w = max(1.0, (content_w - label_col_w) / float(max(1, side_count)))
    radius = max(2, int(style.corner_radius_px), int(render_params.corner_radius_px // 2))

    board_bbox = [content_left, content_top, content_right, content_top + header_h + row_h * float(row_count)]
    if str(scene_variant) == "feature_bands":
        draw.rounded_rectangle(tuple(board_bbox), radius=int(radius), fill=alt_rgb, outline=border_rgb, width=1)
    else:
        draw.rounded_rectangle(tuple(board_bbox), radius=int(radius), fill=fill_rgb, outline=border_rgb, width=1)

    # Top-left corner cell.
    draw.rectangle(
        (content_left, content_top, content_left + label_col_w, content_top + header_h),
        fill=_blend_rgb(fill_rgb, style.header_rgb, 0.08),
    )
    _draw_text(
        draw,
        (content_left + 14.0, content_top + max(16.0, (header_h - float(label_font_size)) / 2.0)),
        "Attribute",
        label_font,
        muted_rgb,
        stroke_fill=muted_rgb,
        stroke_width=1,
        role="comparison_axis_label",
    )

    side_header_bboxes: Dict[str, List[float]] = {}
    attribute_label_bboxes: Dict[str, List[float]] = {}
    value_cell_bboxes: Dict[str, Dict[str, List[float]]] = {}
    entities: List[Dict[str, Any]] = []

    for side_index, side in enumerate(spec.sides):
        x0 = content_left + label_col_w + float(side_index) * value_w
        x1 = x0 + value_w
        accent = tuple(int(value) for value in side.accent_rgb)
        header_fill = _blend_rgb(style.panel_fill_rgb, accent, 0.16 if str(scene_variant) == "feature_bands" else 0.10)
        draw.rectangle((x0, content_top, x1, content_top + header_h), fill=header_fill)
        if str(scene_variant) == "feature_bands":
            draw.rectangle((x0, content_top, x1, content_top + 7.0), fill=accent)
        side_font = fit_font_to_box(
            draw,
            text=str(side.label),
            max_width=max(40.0, value_w - 24.0),
            max_height=max(18.0, header_h - 22.0),
            bold=True,
            min_size_px=10,
            max_size_px=int(side_font_size),
            fill_ratio=0.96,
        )
        side_bbox = _text_bbox(
            draw,
            (x0 + 12.0, content_top + max(18.0, (header_h - float(side_font_size)) / 2.0)),
            str(side.label),
            side_font,
        )
        side_x = x0 + max(12.0, (value_w - (side_bbox[2] - side_bbox[0])) / 2.0)
        side_y = content_top + max(18.0, (header_h - (side_bbox[3] - side_bbox[1])) / 2.0)
        side_header_bboxes[str(side.side_id)] = _draw_text(
            draw,
            (side_x, side_y),
            str(side.label),
            side_font,
            text_rgb,
            stroke_fill=text_rgb,
            stroke_width=1,
            role="comparison_side_header",
        )
        entities.append(
            {
                "entity_id": str(side.side_id),
                "kind": "comparison_side",
                "label": str(side.label),
                "header_bbox_px": [float(value) for value in side_header_bboxes[str(side.side_id)]],
                "accent_rgb": [int(value) for value in accent],
            }
        )

    for attr_index, attribute in enumerate(spec.attributes):
        y0 = content_top + header_h + float(attr_index) * row_h
        y1 = y0 + row_h
        if attr_index % 2 == 0:
            row_fill = _blend_rgb(style.surface_alt_rgb, style.panel_fill_rgb, 0.45)
            draw.rectangle((content_left, y0, content_right, y1), fill=row_fill)
        label_fill = _blend_rgb(style.panel_fill_rgb, style.highlight_rgb, 0.10 if str(scene_variant) == "feature_bands" else 0.04)
        draw.rectangle((content_left, y0, content_left + label_col_w, y1), fill=label_fill)
        label_font_fit = fit_font_to_box(
            draw,
            text=str(attribute.label),
            max_width=max(40.0, label_col_w - 28.0),
            max_height=max(18.0, row_h - 14.0),
            bold=True,
            min_size_px=9,
            max_size_px=int(label_font_size),
            fill_ratio=0.96,
        )
        label_bbox_probe = _text_bbox(draw, (content_left + 14.0, y0 + 12.0), str(attribute.label), label_font_fit)
        label_y = y0 + max(10.0, (row_h - (label_bbox_probe[3] - label_bbox_probe[1])) / 2.0)
        attribute_label_bboxes[str(attribute.attribute_id)] = _draw_text(
            draw,
            (content_left + 14.0, label_y),
            str(attribute.label),
            label_font_fit,
            text_rgb,
            stroke_fill=text_rgb,
            stroke_width=1,
            role="comparison_attribute_label",
        )
        value_cell_bboxes[str(attribute.attribute_id)] = {}
        attribute_entity = {
            "entity_id": str(attribute.attribute_id),
            "kind": "comparison_attribute",
            "label": str(attribute.label),
            "label_bbox_px": [float(value) for value in attribute_label_bboxes[str(attribute.attribute_id)]],
            "values": [],
        }
        for side_index, side in enumerate(spec.sides):
            x0 = content_left + label_col_w + float(side_index) * value_w
            x1 = x0 + value_w
            value = str(attribute.values_by_side_id[str(side.side_id)])
            value_font_fit = fit_font_to_box(
                draw,
                text=str(value),
                max_width=max(40.0, value_w - 28.0),
                max_height=max(18.0, row_h - 14.0),
                bold=True,
                min_size_px=9,
                max_size_px=int(value_font_size),
                fill_ratio=0.96,
            )
            probe_bbox = _text_bbox(draw, (x0 + 14.0, y0 + 12.0), str(value), value_font_fit)
            text_x = x0 + max(14.0, (value_w - (probe_bbox[2] - probe_bbox[0])) / 2.0)
            text_y = y0 + max(10.0, (row_h - (probe_bbox[3] - probe_bbox[1])) / 2.0)
            value_bbox = _draw_text(
                draw,
                (text_x, text_y),
                str(value),
                value_font_fit,
                text_rgb,
                stroke_fill=text_rgb,
                stroke_width=1,
                role="comparison_value_cell",
            )
            value_cell_bboxes[str(attribute.attribute_id)][str(side.side_id)] = [float(item) for item in value_bbox]
            attribute_entity["values"].append(
                {
                    "side_id": str(side.side_id),
                    "side_label": str(side.label),
                    "value": str(value),
                    "value_bbox_px": [float(item) for item in value_bbox],
                }
            )
        entities.append(attribute_entity)
        draw.line((content_left, y1, content_right, y1), fill=guide_rgb, width=1)

    for side_index in range(side_count + 1):
        x = content_left + label_col_w + float(side_index) * value_w
        draw.line((x, content_top, x, board_bbox[3]), fill=guide_rgb, width=1)
    draw.line((content_left, content_top + header_h, content_right, content_top + header_h), fill=border_rgb, width=1)

    return _RenderedComparisonPanel(
        image=image,
        entities=entities,
        panel_bbox_px=[float(value) for value in panel_bbox],
        title_bbox_px=[float(value) for value in title_bbox],
        side_header_bboxes_px=side_header_bboxes,
        attribute_label_bboxes_px=attribute_label_bboxes,
        value_cell_bboxes_px=value_cell_bboxes,
        layout_meta={
            "scene_variant": str(scene_variant),
            "content_bbox_px": [float(value) for value in board_bbox],
            "side_count": int(side_count),
            "attribute_count": int(row_count),
            "label_column_width_px": float(label_col_w),
            "value_column_width_px": float(value_w),
            "header_height_px": float(header_h),
            "row_height_px": float(row_h),
        },
    )


def _build_prompt_examples() -> Tuple[str, str]:
    annotation = {
        "side_header": [2, 3, 4, 5],
        "attribute_label": [3, 4, 5, 6],
        "value_cell": [4, 5, 6, 7],
    }
    return (
        json.dumps({"annotation": annotation, "answer": "Digital"}, separators=(",", ":")),
        json.dumps({"answer": "Digital"}, separators=(",", ":")),
    )


@register_task
class PagesComparisonPanelSideAttributeValueLabelTask:
    """Read a visible cell value from a side-by-side comparison panel."""

    task_id = COMPARISON_PANEL_TASK_ID
    domain = "pages"
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_named_variant(
            task_id=self.task_id,
            gen_defaults=_GEN_DEFAULTS,
            params=params,
            instance_seed=int(instance_seed),
            supported=QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            namespace="query_id",
        )
        scene_variant, scene_variant_probabilities = _resolve_named_variant(
            task_id=self.task_id,
            gen_defaults=_GEN_DEFAULTS,
            params=params,
            instance_seed=int(instance_seed),
            supported=SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            namespace="scene_variant",
        )
        side_count, side_count_support, side_count_probabilities = _resolve_supported_int(
            task_id=self.task_id,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="side_count",
            support_key="side_count_support",
            fallback=(2, 3),
            instance_seed=int(instance_seed),
            namespace="side_count",
        )
        attribute_count, attribute_count_support, attribute_count_probabilities = _resolve_supported_int(
            task_id=self.task_id,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="attribute_count",
            support_key="attribute_count_support",
            fallback=(4, 5, 6),
            instance_seed=int(instance_seed),
            namespace="attribute_count",
        )
        spec = _build_comparison_spec(
            side_count=int(side_count),
            attribute_count=int(attribute_count),
            instance_seed=int(instance_seed),
        )
        side_index = int(params["target_side_index"]) if "target_side_index" in params else int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.target_side",
            )
            % int(side_count)
        )
        attribute_index = int(params["target_attribute_index"]) if "target_attribute_index" in params else int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.target_attribute.{side_index}",
            )
            % int(attribute_count)
        )
        if side_index < 0 or side_index >= int(side_count):
            raise ValueError("target_side_index out of range")
        if attribute_index < 0 or attribute_index >= int(attribute_count):
            raise ValueError("target_attribute_index out of range")
        target_side = spec.sides[int(side_index)]
        target_attribute = spec.attributes[int(attribute_index)]
        answer_value = str(target_attribute.values_by_side_id[str(target_side.side_id)])

        render_params = _resolve_render_params(params, _RENDER_DEFAULTS)
        style, style_meta = resolve_pages_information_style(
            instance_seed=int(instance_seed),
            params=_RENDER_DEFAULTS,
            scene_id=SCENE_ID,
            task_group=TASK_GROUP,
            allow_dark=False,
        )
        background, background_meta = make_information_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=style,
            instance_seed=int(instance_seed),
            namespace=f"pages.{TASK_GROUP}.{SCENE_ID}.information_scene_background",
        )
        rendered = _render_comparison_panel(
            background,
            spec=spec,
            scene_variant=str(scene_variant),
            style=style,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        annotation_keyed_bboxes = {
            "side_header": [float(value) for value in rendered.side_header_bboxes_px[str(target_side.side_id)]],
            "attribute_label": [
                float(value)
                for value in rendered.attribute_label_bboxes_px[str(target_attribute.attribute_id)]
            ],
            "value_cell": [
                float(value)
                for value in rendered.value_cell_bboxes_px[str(target_attribute.attribute_id)][str(target_side.side_id)]
            ],
        }

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "annotation_hint",
                "object_description",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "side_label": f'"{str(target_side.label)}"',
                "attribute_label": f'"{str(target_attribute.label)}"',
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        target_payload = {
            "side_id": str(target_side.side_id),
            "side_label": str(target_side.label),
            "attribute_id": str(target_attribute.attribute_id),
            "attribute_label": str(target_attribute.label),
            "value": str(answer_value),
        }
        side_payload = [
            {
                "side_id": str(side.side_id),
                "side_label": str(side.label),
                "header_bbox_px": [float(value) for value in rendered.side_header_bboxes_px[str(side.side_id)]],
            }
            for side in spec.sides
        ]
        attribute_payload = []
        for attribute in spec.attributes:
            attribute_payload.append(
                {
                    "attribute_id": str(attribute.attribute_id),
                    "attribute_label": str(attribute.label),
                    "label_bbox_px": [
                        float(value)
                        for value in rendered.attribute_label_bboxes_px[str(attribute.attribute_id)]
                    ],
                    "values_by_side_id": dict(attribute.values_by_side_id),
                    "value_bboxes_px": dict(rendered.value_cell_bboxes_px[str(attribute.attribute_id)]),
                }
            )
        trace_payload = {
            "scene_ir": {
                "scene_id": SCENE_ID,
                "scene_kind": "pages_comparison_panel",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "target": dict(target_payload),
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
                    "side_count": int(side_count),
                    "attribute_count": int(attribute_count),
                    "target": dict(target_payload),
                    "target_answer": str(answer_value),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "side_count_probabilities": dict(side_count_probabilities),
                    "attribute_count_probabilities": dict(attribute_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "information_scene_style": dict(style_meta),
                "post_image_noise": dict(post_noise_meta),
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "layout": dict(rendered.layout_meta),
                "page_text_resources": dict(spec.text_resource_metadata),
            },
            "render_map": {
                "image_id": "img0",
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "side_header_bboxes_px": dict(rendered.side_header_bboxes_px),
                "attribute_label_bboxes_px": dict(rendered.attribute_label_bboxes_px),
                "value_cell_bboxes_px": dict(rendered.value_cell_bboxes_px),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "comparison_panel_side_attribute_value_label",
                "side_count": int(side_count),
                "attribute_count": int(attribute_count),
                "side_count_support": [int(value) for value in side_count_support],
                "attribute_count_support": [int(value) for value in attribute_count_support],
                "target": dict(target_payload),
                "answer_value": str(answer_value),
                "sides": list(side_payload),
                "attributes": list(attribute_payload),
                "page_text_resources": dict(spec.text_resource_metadata),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "side_count_probabilities": dict(side_count_probabilities),
                "attribute_count_probabilities": dict(attribute_count_probabilities),
            },
            "witness_symbolic": {
                "type": "comparison_panel_side_attribute_lookup",
                "target_side_id": str(target_side.side_id),
                "target_attribute_id": str(target_attribute.attribute_id),
                "answer_value": str(answer_value),
                "annotation_keys": list(annotation_keyed_bboxes.keys()),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_keyed_bboxes),
                "pixel_keyed_bbox_map": dict(annotation_keyed_bboxes),
                "bbox_set": list(annotation_keyed_bboxes.values()),
                "target_side_id": str(target_side.side_id),
                "target_attribute_id": str(target_attribute.attribute_id),
            },
        }
        complexity = build_pages_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "lookup_reasoning": 0.42,
                "visual_scan": normalize_int_with_bounds(
                    int(side_count) * int(attribute_count),
                    [2 * min(side_count_support), 3 * max(attribute_count_support)],
                ),
                "layout_load": 0.48 if str(scene_variant) == "feature_bands" else 0.42,
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(answer_value)),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "COMPARISON_PANEL_TASK_ID",
    "QUERY_ID",
    "QUERY_IDS",
    "SCENE_ID",
    "SCENE_VARIANTS",
    "PagesComparisonPanelSideAttributeValueLabelTask",
]
