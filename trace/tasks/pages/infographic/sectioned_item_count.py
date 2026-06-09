"""Sectioned infographic item-count task."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
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
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...shared.visual_style.information_scene import make_information_scene_background
from ..shared.complexity import build_pages_complexity, normalize_int_with_bounds, resolve_pages_complexity_weights
from ..shared.information_style import resolve_pages_information_style
from ..shared.legible_text import darken_surface_for_light_text, draw_required_page_text
from ..shared.page_semantic_assets import (
    page_semantic_asset_ids,
    page_semantic_asset_label,
    page_semantic_asset_manifest_metadata,
    render_page_semantic_asset_rgba,
)
from ..shared.page_text_resources import page_text_resource_metadata, sample_page_context_batch, sample_page_label_batch
from ..shared.visual_defaults import load_pages_noise_defaults


SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID = "task_pages__sectioned_infographic__section_item_count"
SECTIONED_INFOGRAPHIC_FILTERED_ITEM_TASK_ID = "task_pages__sectioned_infographic__section_filtered_item_label"
TASK_GROUP = "infographic"
SCENE_ID = "sectioned_infographic"
QUERY_ID = "section_item_count"
FILTERED_ITEM_QUERY_ID = "section_filtered_item_label"
QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
FILTERED_ITEM_QUERY_IDS: Tuple[str, ...] = (FILTERED_ITEM_QUERY_ID,)
SCENE_VARIANTS: Tuple[str, ...] = ("topic_cards", "bullet_columns", "checklist_bands")

_BULLET_MARKS: Tuple[str, ...] = page_semantic_asset_ids(semantic_role="marker", allowed_use="filter")
_BULLET_MARK_LABELS: Dict[str, str] = {marker: page_semantic_asset_label(marker) for marker in _BULLET_MARKS}


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
    section_title_font_size_px: int
    item_font_size_px: int


@dataclass(frozen=True)
class _SectionItem:
    item_id: str
    label: str
    marker: str


@dataclass(frozen=True)
class _InfographicSection:
    section_id: str
    title: str
    accent_rgb: Tuple[int, int, int]
    items: Tuple[_SectionItem, ...]


@dataclass(frozen=True)
class _SectionedInfographicSpec:
    title: str
    subtitle: str
    sections: Tuple[_InfographicSection, ...]
    text_resource_metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedSectionedInfographic:
    image: Image.Image
    entities: List[Dict[str, Any]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    section_bboxes_px: Dict[str, List[float]]
    section_title_bboxes_px: Dict[str, List[float]]
    item_row_bboxes_px: Dict[str, Dict[str, List[float]]]
    item_label_bboxes_px: Dict[str, Dict[str, List[float]]]
    item_marker_bboxes_px: Dict[str, Dict[str, List[float]]]
    layout_meta: Dict[str, Any]


_ACCENTS: Tuple[Tuple[int, int, int], ...] = (
    (55, 118, 172),
    (42, 142, 112),
    (190, 91, 76),
    (128, 102, 184),
    (198, 142, 58),
    (72, 132, 151),
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID,
)
_FILTERED_GEN_DEFAULTS, _FILTERED_RENDER_DEFAULTS, _FILTERED_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=SECTIONED_INFOGRAPHIC_FILTERED_ITEM_TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(
    _TASK_GROUP_DEFAULTS,
    task_id=SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID,
)
_FILTERED_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(
    _TASK_GROUP_DEFAULTS,
    task_id=SECTIONED_INFOGRAPHIC_FILTERED_ITEM_TASK_ID,
)
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
        canvas_width=_int_value("canvas_width", 1040, minimum=520),
        canvas_height=_int_value("canvas_height", 980, minimum=520),
        outer_margin_px=_int_value("outer_margin_px", 34, minimum=0),
        header_height_px=_int_value("header_height_px", 86, minimum=52),
        gap_px=_int_value("gap_px", 14, minimum=4),
        corner_radius_px=_int_value("corner_radius_px", 14, minimum=0),
        outline_width_px=_int_value("outline_width_px", 2, minimum=1),
        title_font_size_px=_int_value("title_font_size_px", 30, minimum=14),
        subtitle_font_size_px=_int_value("subtitle_font_size_px", 17, minimum=10),
        section_title_font_size_px=_int_value("section_title_font_size_px", 20, minimum=10),
        item_font_size_px=_int_value("item_font_size_px", 16, minimum=9),
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
    stroke_width: int = 1,
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
            namespace=str(namespace or f"sectioned_infographic.{role}"),
            preferred_rgbs=(fill,),
            stroke_width=max(0, int(stroke_width)),
        )
    draw_text_traced(
        draw,
        (float(xy[0]), float(xy[1])),
        str(text),
        fill=fill,
        font=font,
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=fill,
        role=str(role),
        required=True,
    )
    return _text_bbox(draw, xy, str(text), font, stroke_width=max(0, int(stroke_width)))


def _blend_rgb(color_a: Sequence[int], color_b: Sequence[int], weight_b: float) -> Tuple[int, int, int]:
    weight = max(0.0, min(1.0, float(weight_b)))
    return tuple(
        int(round((float(color_a[index]) * (1.0 - weight)) + (float(color_b[index]) * weight)))
        for index in range(3)
    )


def _build_sectioned_spec(
    *,
    section_count: int,
    item_count_support: Sequence[int],
    instance_seed: int,
) -> _SectionedInfographicSpec:
    rng = spawn_rng(int(instance_seed), "sectioned_infographic.spec")
    max_items = int(section_count) * max(int(value) for value in item_count_support)
    title_batch = sample_page_context_batch(
        rng,
        role="sectioned_infographic_title",
        count=1,
        manifest_names=("phrases/headlines.txt",),
    )
    subtitle_batch = sample_page_context_batch(
        rng,
        role="sectioned_infographic_subtitle",
        count=1,
        manifest_names=("phrases/captions.txt", "phrases/legend_notes.txt"),
    )
    section_batch = sample_page_label_batch(
        rng,
        role="sectioned_infographic_section_title",
        count=int(section_count),
        manifest_name="categories/product_labels.txt",
        min_chars=3,
        max_chars=16,
        allow_spaces=True,
        allow_punctuation=False,
    )
    item_batch = sample_page_label_batch(
        rng,
        role="sectioned_infographic_item_label",
        count=int(max_items),
        manifest_name="mixed/compact_labels.txt",
        min_chars=5,
        max_chars=18,
        allow_spaces=True,
        allow_punctuation=False,
        exclude=section_batch.values,
    )
    text_resource_meta = page_text_resource_metadata(title_batch, subtitle_batch, section_batch, item_batch)
    section_titles = list(section_batch.values)
    item_labels = list(item_batch.values)
    item_cursor = 0
    accent_offset = int(rng.randrange(len(_ACCENTS)))
    sections: List[_InfographicSection] = []
    for section_index in range(int(section_count)):
        item_count_index = int(rng.randrange(len(item_count_support)))
        item_count = int(item_count_support[int(item_count_index)])
        items: List[_SectionItem] = []
        marker_offset = int(rng.randrange(len(_BULLET_MARKS)))
        for item_index in range(item_count):
            marker = _BULLET_MARKS[(int(marker_offset) + int(item_index)) % len(_BULLET_MARKS)]
            items.append(
                _SectionItem(
                    item_id=f"section_{section_index + 1}_item_{item_index + 1}",
                    label=str(item_labels[int(item_cursor)]),
                    marker=str(marker),
                )
            )
            item_cursor += 1
        sections.append(
            _InfographicSection(
                section_id=f"section_{section_index + 1}",
                title=str(section_titles[int(section_index)]),
                accent_rgb=tuple(int(value) for value in _ACCENTS[(int(section_index) + int(accent_offset)) % len(_ACCENTS)]),
                items=tuple(items),
            )
        )
    return _SectionedInfographicSpec(
        title=str(title_batch.values[0]),
        subtitle=str(subtitle_batch.values[0]),
        sections=tuple(sections),
        text_resource_metadata=dict(text_resource_meta),
    )


def _layout_section_bboxes(
    *,
    scene_variant: str,
    section_count: int,
    content_bbox: Sequence[float],
    gap_px: int,
) -> Tuple[List[List[float]], Dict[str, Any]]:
    x0, y0, x1, y1 = [float(value) for value in content_bbox]
    width = max(1.0, x1 - x0)
    height = max(1.0, y1 - y0)
    gap = float(gap_px)
    boxes: List[List[float]] = []
    if str(scene_variant) == "bullet_columns":
        columns = min(3, max(1, int(section_count)))
        rows = int((int(section_count) + columns - 1) // columns)
    elif str(scene_variant) == "checklist_bands":
        columns = 1
        rows = max(1, int(section_count))
    else:
        columns = 2 if int(section_count) > 1 else 1
        rows = int((int(section_count) + columns - 1) // columns)
    cell_w = (width - (float(columns - 1) * gap)) / float(columns)
    cell_h = (height - (float(rows - 1) * gap)) / float(rows)
    for index in range(int(section_count)):
        row = int(index) // int(columns)
        col = int(index) % int(columns)
        left = x0 + float(col) * (cell_w + gap)
        top = y0 + float(row) * (cell_h + gap)
        boxes.append([left, top, left + cell_w, top + cell_h])
    return boxes, {
        "layout_columns": int(columns),
        "layout_rows": int(rows),
        "section_cell_width_px": float(cell_w),
        "section_cell_height_px": float(cell_h),
    }


def _draw_marker(
    image: Image.Image,
    *,
    marker: str,
    center: Tuple[float, float],
    radius: float,
    fill: Tuple[int, int, int],
) -> List[float]:
    cx, cy = [float(value) for value in center]
    r = max(2.0, float(radius))
    bbox = [cx - r, cy - r, cx + r, cy + r]
    rendered = render_page_semantic_asset_rgba(
        str(marker),
        size_px=(max(1, int(round(2.0 * r))), max(1, int(round(2.0 * r)))),
        tint_rgb=tuple(int(value) for value in fill),
    )
    paste_x = int(round(cx - rendered.width * 0.5))
    paste_y = int(round(cy - rendered.height * 0.5))
    image.paste(rendered, (paste_x, paste_y), rendered)
    return [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]


def _render_sectioned_infographic(
    background: Image.Image,
    *,
    spec: _SectionedInfographicSpec,
    scene_variant: str,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
) -> _RenderedSectionedInfographic:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    margin = int(render_params.outer_margin_px)
    panel_bbox = [
        float(margin),
        float(margin),
        float(render_params.canvas_width - margin),
        float(render_params.canvas_height - margin),
    ]
    radius = max(int(render_params.corner_radius_px), int(style.corner_radius_px))
    shadow = max(0, int(style.shadow_offset_px))
    if shadow:
        draw.rounded_rectangle(
            (panel_bbox[0] + shadow, panel_bbox[1] + shadow, panel_bbox[2] + shadow, panel_bbox[3] + shadow),
            radius=radius,
            fill=tuple(int(value) for value in style.shadow_rgb),
        )
    draw.rounded_rectangle(
        tuple(panel_bbox),
        radius=radius,
        fill=tuple(int(value) for value in style.surface_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=max(1, int(render_params.outline_width_px), int(style.frame_width_px)),
    )
    header_h = max(int(render_params.header_height_px), int(style.title_band_height_px))
    header_fill = darken_surface_for_light_text(style.header_rgb, text_rgb=style.header_text_rgb)
    draw.rounded_rectangle(
        (panel_bbox[0], panel_bbox[1], panel_bbox[2], panel_bbox[1] + float(header_h)),
        radius=radius,
        fill=header_fill,
    )
    draw.rectangle(
        (panel_bbox[0], panel_bbox[1] + float(header_h) - float(radius), panel_bbox[2], panel_bbox[1] + float(header_h)),
        fill=header_fill,
    )

    scale = float(style.typography_scale)
    title_font = load_font(max(10, int(round(render_params.title_font_size_px * scale))), bold=True)
    subtitle_font = load_font(max(8, int(round(render_params.subtitle_font_size_px * scale))), bold=False)
    section_font_size = max(10, int(round(render_params.section_title_font_size_px * scale)))
    item_font_size = max(9, int(round(render_params.item_font_size_px * scale)))
    title_bbox = _draw_text(
        draw,
        (panel_bbox[0] + 24.0, panel_bbox[1] + 18.0),
        str(spec.title),
        title_font,
        tuple(int(value) for value in style.header_text_rgb),
        role="page_title",
        surface_rgbs=(header_fill,),
        instance_seed=int(instance_seed),
        namespace=f"{SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID}.page_title.{scene_variant}",
    )
    _draw_text(
        draw,
        (panel_bbox[0] + 24.0, panel_bbox[1] + 54.0),
        str(spec.subtitle),
        subtitle_font,
        tuple(int(value) for value in style.header_text_rgb),
        stroke_width=0,
        role="page_subtitle",
        surface_rgbs=(header_fill,),
        instance_seed=int(instance_seed),
        namespace=f"{SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID}.page_subtitle.{scene_variant}",
    )

    content_bbox = [
        panel_bbox[0] + float(style.panel_padding_px),
        panel_bbox[1] + float(header_h) + float(render_params.gap_px),
        panel_bbox[2] - float(style.panel_padding_px),
        panel_bbox[3] - float(style.panel_padding_px),
    ]
    section_boxes, layout_meta = _layout_section_bboxes(
        scene_variant=str(scene_variant),
        section_count=len(spec.sections),
        content_bbox=content_bbox,
        gap_px=int(render_params.gap_px),
    )
    section_bboxes: Dict[str, List[float]] = {}
    section_title_bboxes: Dict[str, List[float]] = {}
    item_row_bboxes: Dict[str, Dict[str, List[float]]] = {}
    item_label_bboxes: Dict[str, Dict[str, List[float]]] = {}
    item_marker_bboxes: Dict[str, Dict[str, List[float]]] = {}
    entities: List[Dict[str, Any]] = []
    text_rgb = tuple(int(value) for value in style.text_rgb)
    muted_rgb = tuple(int(value) for value in style.muted_text_rgb)
    border_rgb = tuple(int(value) for value in style.panel_border_rgb)
    guide_rgb = tuple(int(value) for value in style.guide_rgb)

    for section_index, (section, bbox) in enumerate(zip(spec.sections, section_boxes)):
        x0, y0, x1, y1 = [float(value) for value in bbox]
        accent = tuple(int(value) for value in section.accent_rgb)
        fill_weight = 0.10 if str(scene_variant) == "topic_cards" else 0.06
        section_fill = _blend_rgb(style.panel_fill_rgb, accent, fill_weight)
        section_radius = max(4, int(radius * 0.65))
        draw.rounded_rectangle((x0, y0, x1, y1), radius=section_radius, fill=section_fill, outline=border_rgb, width=1)
        band_h = max(34.0, min(48.0, (y1 - y0) * 0.18))
        if str(scene_variant) in {"topic_cards", "checklist_bands"}:
            section_band_fill = darken_surface_for_light_text(
                _blend_rgb(style.header_rgb, accent, 0.30),
                text_rgb=style.header_text_rgb,
            )
            draw.rounded_rectangle((x0, y0, x1, y0 + band_h), radius=section_radius, fill=section_band_fill)
            draw.rectangle((x0, y0 + band_h - float(section_radius), x1, y0 + band_h), fill=section_band_fill)
            section_title_rgb = tuple(int(value) for value in style.header_text_rgb)
        else:
            draw.rectangle((x0, y0, x0 + 7.0, y1), fill=accent)
            section_title_rgb = text_rgb
            section_band_fill = section_fill
        title_font_fit = fit_font_to_box(
            draw,
            text=str(section.title),
            max_width=max(40.0, x1 - x0 - 30.0),
            max_height=max(18.0, band_h - 12.0),
            bold=True,
            min_size_px=10,
            max_size_px=int(section_font_size),
            fill_ratio=0.97,
        )
        title_y = y0 + max(8.0, (band_h - float(section_font_size)) / 2.0)
        if str(scene_variant) == "bullet_columns":
            title_y = y0 + 14.0
        section_title_bboxes[str(section.section_id)] = _draw_text(
            draw,
            (x0 + 18.0, title_y),
            str(section.title),
            title_font_fit,
            section_title_rgb,
            role="section_title",
            surface_rgbs=(section_band_fill,),
            instance_seed=int(instance_seed),
            namespace=f"{SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID}.section_title.{section.section_id}",
        )
        section_bboxes[str(section.section_id)] = [float(value) for value in bbox]
        item_row_bboxes[str(section.section_id)] = {}
        item_label_bboxes[str(section.section_id)] = {}
        item_marker_bboxes[str(section.section_id)] = {}
        item_top = y0 + band_h + 10.0 if str(scene_variant) != "bullet_columns" else y0 + band_h + 2.0
        item_bottom = y1 - 10.0
        row_h = max(18.0, (item_bottom - item_top) / float(max(1, len(section.items))))
        item_font_base = load_font(max(9, min(item_font_size, int(row_h * 0.58))), bold=True)
        section_entity = {
            "entity_id": str(section.section_id),
            "kind": "sectioned_infographic_section",
            "title": str(section.title),
            "bbox_px": [float(value) for value in bbox],
            "title_bbox_px": [float(value) for value in section_title_bboxes[str(section.section_id)]],
            "items": [],
        }
        for item_index, item in enumerate(section.items):
            row_y0 = item_top + float(item_index) * row_h
            row_y1 = item_top + float(item_index + 1) * row_h
            row_bbox = [x0 + 12.0, row_y0 + 2.0, x1 - 12.0, row_y1 - 2.0]
            row_fill = section_fill
            if str(scene_variant) == "checklist_bands" or item_index % 2 == 0:
                row_fill = _blend_rgb(style.surface_alt_rgb, accent, 0.035)
                draw.rounded_rectangle(
                    tuple(row_bbox),
                    radius=5,
                    fill=row_fill,
                    outline=guide_rgb if str(scene_variant) == "checklist_bands" else None,
                    width=1,
                )
            marker_bbox = _draw_marker(
                image,
                marker=str(item.marker),
                center=(row_bbox[0] + 14.0, (row_bbox[1] + row_bbox[3]) / 2.0),
                radius=min(5.0, max(3.0, row_h * 0.16)),
                fill=accent,
            )
            item_font = fit_font_to_box(
                draw,
                text=str(item.label),
                max_width=max(36.0, row_bbox[2] - row_bbox[0] - 42.0),
                max_height=max(12.0, row_h - 8.0),
                bold=True,
                min_size_px=9,
                max_size_px=max(9, int(getattr(item_font_base, "size", item_font_size) or item_font_size)),
                fill_ratio=0.98,
            )
            text_bbox = _draw_text(
                draw,
                (row_bbox[0] + 32.0, row_bbox[1] + max(2.0, (row_h - float(getattr(item_font, "size", item_font_size))) / 2.0)),
                str(item.label),
                item_font,
                text_rgb,
                role="section_item_label",
                surface_rgbs=(row_fill,),
                instance_seed=int(instance_seed),
                namespace=f"{SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID}.item_label.{item.item_id}",
            )
            full_item_bbox = [
                min(float(row_bbox[0]), float(marker_bbox[0]), float(text_bbox[0])),
                min(float(row_bbox[1]), float(marker_bbox[1]), float(text_bbox[1])),
                max(float(row_bbox[2]), float(marker_bbox[2]), float(text_bbox[2])),
                max(float(row_bbox[3]), float(marker_bbox[3]), float(text_bbox[3])),
            ]
            item_row_bboxes[str(section.section_id)][str(item.item_id)] = full_item_bbox
            item_label_bboxes[str(section.section_id)][str(item.item_id)] = [float(value) for value in text_bbox]
            item_marker_bboxes[str(section.section_id)][str(item.item_id)] = [float(value) for value in marker_bbox]
            section_entity["items"].append(
                {
                    "item_id": str(item.item_id),
                    "label": str(item.label),
                    "marker": str(item.marker),
                    "item_row_bbox_px": [float(value) for value in full_item_bbox],
                    "label_bbox_px": [float(value) for value in text_bbox],
                    "marker_bbox_px": [float(value) for value in marker_bbox],
                }
            )
        entities.append(section_entity)
        if section_index < len(section_boxes) - 1 and str(scene_variant) == "bullet_columns":
            draw.line((x1 + float(render_params.gap_px) / 2.0, y0, x1 + float(render_params.gap_px) / 2.0, y1), fill=guide_rgb, width=1)

    return _RenderedSectionedInfographic(
        image=image,
        entities=entities,
        panel_bbox_px=[float(value) for value in panel_bbox],
        title_bbox_px=[float(value) for value in title_bbox],
        section_bboxes_px=section_bboxes,
        section_title_bboxes_px=section_title_bboxes,
        item_row_bboxes_px=item_row_bboxes,
        item_label_bboxes_px=item_label_bboxes,
        item_marker_bboxes_px=item_marker_bboxes,
        layout_meta={
            "scene_variant": str(scene_variant),
            "content_bbox_px": [float(value) for value in content_bbox],
            "section_count": int(len(spec.sections)),
            **dict(layout_meta),
        },
    )


def _build_prompt_examples(query_id: str = QUERY_ID) -> Tuple[str, str]:
    if str(query_id) == FILTERED_ITEM_QUERY_ID:
        annotation = {
            "section_title": [20, 40, 180, 66],
            "filter_marker": [28, 88, 42, 102],
            "target_item": [20, 80, 180, 104],
        }
        return (
            json.dumps({"annotation": annotation, "answer": "Check lights"}, separators=(",", ":")),
            json.dumps({"answer": "Check lights"}, separators=(",", ":")),
        )
    return (
        json.dumps({"annotation": [[20, 80, 180, 104], [20, 110, 180, 134]], "answer": 2}, separators=(",", ":")),
        json.dumps({"answer": 2}, separators=(",", ":")),
    )


def _unique_marker_items(section: _InfographicSection) -> List[_SectionItem]:
    marker_counts: Dict[str, int] = {}
    for item in section.items:
        marker_counts[str(item.marker)] = int(marker_counts.get(str(item.marker), 0)) + 1
    return [item for item in section.items if int(marker_counts.get(str(item.marker), 0)) == 1]


def _select_sectioned_target_section(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    sections: Sequence[_InfographicSection],
    require_unique_marker: bool,
) -> _InfographicSection:
    eligible_sections = [
        section for section in sections if (not bool(require_unique_marker)) or bool(_unique_marker_items(section))
    ]
    if not eligible_sections:
        raise ValueError("no section has a unique item marker for section_filtered_item_label")
    if params.get("target_section_index") is not None:
        target_index = int(params["target_section_index"])
        if target_index < 0 or target_index >= len(sections):
            raise ValueError("target_section_index out of range")
        target_section = sections[int(target_index)]
        if bool(require_unique_marker) and not _unique_marker_items(target_section):
            raise ValueError("target_section_index does not have a unique item marker")
        return target_section
    selected_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_section",
        )
        % int(len(eligible_sections))
    )
    return eligible_sections[int(selected_index)]


def _select_unique_marker_item(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    section: _InfographicSection,
) -> _SectionItem:
    unique_items = _unique_marker_items(section)
    if not unique_items:
        raise ValueError("target section has no unique item marker")
    requested_marker = params.get("target_marker")
    if requested_marker is not None:
        for item in unique_items:
            if str(item.marker) == str(requested_marker):
                return item
        raise ValueError("target_marker must be unique within the selected section")
    requested_item_index = params.get("target_item_index")
    if requested_item_index is not None:
        target_index = int(requested_item_index)
        if target_index < 0 or target_index >= len(section.items):
            raise ValueError("target_item_index out of range")
        target_item = section.items[int(target_index)]
        if target_item not in unique_items:
            raise ValueError("target_item_index must select an item with a unique marker")
        return target_item
    selected_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_marker.{section.section_id}",
        )
        % int(len(unique_items))
    )
    return unique_items[int(selected_index)]


@register_task
class PagesSectionedInfographicSectionItemCountTask:
    """Count visible list items in one named infographic section."""

    task_id = SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID
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
            weights_key="sectioned_query_id_weights",
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
        section_count, section_count_support, section_count_probabilities = _resolve_supported_int(
            task_id=self.task_id,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="section_count",
            support_key="section_count_support",
            fallback=(3, 4, 5),
            instance_seed=int(instance_seed),
            namespace="section_count",
        )
        item_count_support = _resolve_int_support(
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            key="item_count_support",
            fallback=(3, 4, 5, 6, 7),
        )
        spec = _build_sectioned_spec(
            section_count=int(section_count),
            item_count_support=tuple(item_count_support),
            instance_seed=int(instance_seed),
        )
        if params.get("target_section_index") is not None:
            target_index = int(params["target_section_index"])
        else:
            target_index = int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{self.task_id}.target_section",
                )
                % int(section_count)
            )
        if target_index < 0 or target_index >= int(section_count):
            raise ValueError("target_section_index out of range")
        target_section = spec.sections[int(target_index)]
        answer_value = int(len(target_section.items))

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
        rendered = _render_sectioned_infographic(
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
        annotation_bboxes = [
            [float(value) for value in rendered.item_row_bboxes_px[str(target_section.section_id)][str(item.item_id)]]
            for item in target_section.items
        ]

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key_sectioned",
                "task_key_sectioned",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_section_item_count",
                "annotation_hint_section_item_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key_sectioned"]),
            task_key=str(prompt_defaults["task_key_sectioned"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "target_section": f'"{str(target_section.title)}"',
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint_section_item_count"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_section_item_count"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        target_payload = {
            "section_id": str(target_section.section_id),
            "section_title": str(target_section.title),
            "item_count": int(answer_value),
            "item_ids": [str(item.item_id) for item in target_section.items],
        }
        sections_payload = [
            {
                "section_id": str(section.section_id),
                "section_title": str(section.title),
                "section_bbox_px": [float(value) for value in rendered.section_bboxes_px[str(section.section_id)]],
                "section_title_bbox_px": [
                    float(value)
                    for value in rendered.section_title_bboxes_px[str(section.section_id)]
                ],
                "item_count": int(len(section.items)),
                "items": [
                    {
                        "item_id": str(item.item_id),
                        "label": str(item.label),
                        "marker": str(item.marker),
                        "item_row_bbox_px": [
                            float(value)
                            for value in rendered.item_row_bboxes_px[str(section.section_id)][str(item.item_id)]
                        ],
                        "item_label_bbox_px": [
                            float(value)
                            for value in rendered.item_label_bboxes_px[str(section.section_id)][str(item.item_id)]
                        ],
                        "marker_bbox_px": [
                            float(value)
                            for value in rendered.item_marker_bboxes_px[str(section.section_id)][str(item.item_id)]
                        ],
                    }
                    for item in section.items
                ],
            }
            for section in spec.sections
        ]
        trace_payload = {
            "scene_ir": {
                "scene_id": SCENE_ID,
                "scene_kind": "pages_sectioned_infographic",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "target_section": dict(target_payload),
                    "answer_value": int(answer_value),
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
                    "target_section": dict(target_payload),
                    "target_answer": int(answer_value),
                    "section_count": int(section_count),
                    "item_count_support": [int(value) for value in item_count_support],
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "section_count_probabilities": dict(section_count_probabilities),
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
                "page_semantic_assets": page_semantic_asset_manifest_metadata(
                    semantic_role="marker",
                    allowed_use="filter",
                ),
            },
            "render_map": {
                "image_id": "img0",
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "section_bboxes_px": dict(rendered.section_bboxes_px),
                "section_title_bboxes_px": dict(rendered.section_title_bboxes_px),
                "item_row_bboxes_px": dict(rendered.item_row_bboxes_px),
                "item_label_bboxes_px": dict(rendered.item_label_bboxes_px),
                "item_marker_bboxes_px": dict(rendered.item_marker_bboxes_px),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "sectioned_infographic_section_item_count",
                "section_count": int(section_count),
                "section_count_support": [int(value) for value in section_count_support],
                "item_count_support": [int(value) for value in item_count_support],
                "target_section": dict(target_payload),
                "answer_value": int(answer_value),
                "sections": list(sections_payload),
                "page_text_resources": dict(spec.text_resource_metadata),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "section_count_probabilities": dict(section_count_probabilities),
            },
            "witness_symbolic": {
                "type": "sectioned_infographic_section_item_count",
                "target_section_id": str(target_section.section_id),
                "answer_value": int(answer_value),
                "annotation_item_ids": [str(item.item_id) for item in target_section.items],
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
                "target_section_id": str(target_section.section_id),
            },
        }
        complexity = build_pages_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "lookup_reasoning": 0.34,
                "visual_scan": normalize_int_with_bounds(
                    int(answer_value),
                    [min(item_count_support), max(item_count_support)],
                ),
                "layout_load": {
                    "topic_cards": 0.44,
                    "bullet_columns": 0.50,
                    "checklist_bands": 0.54,
                }.get(str(scene_variant), 0.46),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes]),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesSectionedInfographicSectionFilteredItemLabelTask:
    """Read the unique item label in a section matching one visible marker."""

    task_id = SECTIONED_INFOGRAPHIC_FILTERED_ITEM_TASK_ID
    domain = "pages"
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_named_variant(
            task_id=self.task_id,
            gen_defaults=_FILTERED_GEN_DEFAULTS,
            params=params,
            instance_seed=int(instance_seed),
            supported=FILTERED_ITEM_QUERY_IDS,
            explicit_key="query_id",
            weights_key="sectioned_query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            namespace="query_id",
        )
        scene_variant, scene_variant_probabilities = _resolve_named_variant(
            task_id=self.task_id,
            gen_defaults=_FILTERED_GEN_DEFAULTS,
            params=params,
            instance_seed=int(instance_seed),
            supported=SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            namespace="scene_variant",
        )
        section_count, section_count_support, section_count_probabilities = _resolve_supported_int(
            task_id=self.task_id,
            params=params,
            gen_defaults=_FILTERED_GEN_DEFAULTS,
            explicit_key="section_count",
            support_key="section_count_support",
            fallback=(3, 4, 5),
            instance_seed=int(instance_seed),
            namespace="section_count",
        )
        item_count_support = _resolve_int_support(
            params=params,
            gen_defaults=_FILTERED_GEN_DEFAULTS,
            key="item_count_support",
            fallback=(3, 4, 5, 6, 7),
        )
        spec = _build_sectioned_spec(
            section_count=int(section_count),
            item_count_support=tuple(item_count_support),
            instance_seed=int(instance_seed),
        )
        target_section = _select_sectioned_target_section(
            task_id=self.task_id,
            params=params,
            instance_seed=int(instance_seed),
            sections=spec.sections,
            require_unique_marker=True,
        )
        target_item = _select_unique_marker_item(
            task_id=self.task_id,
            params=params,
            instance_seed=int(instance_seed),
            section=target_section,
        )
        answer_value = str(target_item.label)
        filter_marker_label = str(_BULLET_MARK_LABELS[str(target_item.marker)])

        render_params = _resolve_render_params(params, _FILTERED_RENDER_DEFAULTS)
        style, style_meta = resolve_pages_information_style(
            instance_seed=int(instance_seed),
            params=_FILTERED_RENDER_DEFAULTS,
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
        rendered = _render_sectioned_infographic(
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
        section_id = str(target_section.section_id)
        item_id = str(target_item.item_id)
        annotation_keyed_bboxes = {
            "section_title": [float(value) for value in rendered.section_title_bboxes_px[section_id]],
            "filter_marker": [float(value) for value in rendered.item_marker_bboxes_px[section_id][item_id]],
            "target_item": [float(value) for value in rendered.item_row_bboxes_px[section_id][item_id]],
        }

        prompt_defaults = required_group_defaults(
            _FILTERED_PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key_sectioned",
                "task_key_sectioned",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_section_filtered_item",
                "annotation_hint_section_filtered_item",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_examples(str(query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key_sectioned"]),
            task_key=str(prompt_defaults["task_key_sectioned"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "target_section": f'"{str(target_section.title)}"',
                "filter_marker_label": str(filter_marker_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint_section_filtered_item"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_section_filtered_item"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        target_payload = {
            "section_id": str(target_section.section_id),
            "section_title": str(target_section.title),
            "item_id": str(target_item.item_id),
            "item_label": str(target_item.label),
            "marker": str(target_item.marker),
            "filter_marker_label": str(filter_marker_label),
        }
        sections_payload = [
            {
                "section_id": str(section.section_id),
                "section_title": str(section.title),
                "section_bbox_px": [float(value) for value in rendered.section_bboxes_px[str(section.section_id)]],
                "section_title_bbox_px": [
                    float(value)
                    for value in rendered.section_title_bboxes_px[str(section.section_id)]
                ],
                "item_count": int(len(section.items)),
                "items": [
                    {
                        "item_id": str(item.item_id),
                        "label": str(item.label),
                        "marker": str(item.marker),
                        "marker_label": str(_BULLET_MARK_LABELS[str(item.marker)]),
                        "item_row_bbox_px": [
                            float(value)
                            for value in rendered.item_row_bboxes_px[str(section.section_id)][str(item.item_id)]
                        ],
                        "item_label_bbox_px": [
                            float(value)
                            for value in rendered.item_label_bboxes_px[str(section.section_id)][str(item.item_id)]
                        ],
                        "marker_bbox_px": [
                            float(value)
                            for value in rendered.item_marker_bboxes_px[str(section.section_id)][str(item.item_id)]
                        ],
                    }
                    for item in section.items
                ],
            }
            for section in spec.sections
        ]
        trace_payload = {
            "scene_ir": {
                "scene_id": SCENE_ID,
                "scene_kind": "pages_sectioned_infographic",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "target_section": dict(target_payload),
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
                    "target_section": dict(target_payload),
                    "target_answer": str(answer_value),
                    "section_count": int(section_count),
                    "item_count_support": [int(value) for value in item_count_support],
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "section_count_probabilities": dict(section_count_probabilities),
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
                "page_semantic_assets": page_semantic_asset_manifest_metadata(
                    semantic_role="marker",
                    allowed_use="filter",
                ),
            },
            "render_map": {
                "image_id": "img0",
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "section_bboxes_px": dict(rendered.section_bboxes_px),
                "section_title_bboxes_px": dict(rendered.section_title_bboxes_px),
                "item_row_bboxes_px": dict(rendered.item_row_bboxes_px),
                "item_label_bboxes_px": dict(rendered.item_label_bboxes_px),
                "item_marker_bboxes_px": dict(rendered.item_marker_bboxes_px),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "sectioned_infographic_section_filtered_item_label",
                "section_count": int(section_count),
                "section_count_support": [int(value) for value in section_count_support],
                "item_count_support": [int(value) for value in item_count_support],
                "target_section": dict(target_payload),
                "answer_value": str(answer_value),
                "sections": list(sections_payload),
                "page_text_resources": dict(spec.text_resource_metadata),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "section_count_probabilities": dict(section_count_probabilities),
            },
            "witness_symbolic": {
                "type": "sectioned_infographic_section_filtered_item_label",
                "target_section_id": str(target_section.section_id),
                "target_item_id": str(target_item.item_id),
                "target_marker": str(target_item.marker),
                "answer_value": str(answer_value),
                "annotation_keys": list(annotation_keyed_bboxes.keys()),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_keyed_bboxes),
                "pixel_keyed_bbox_map": dict(annotation_keyed_bboxes),
                "bbox_set": list(annotation_keyed_bboxes.values()),
                "target_section_id": str(target_section.section_id),
                "target_item_id": str(target_item.item_id),
            },
        }
        complexity = build_pages_complexity(
            weights=_FILTERED_COMPLEXITY_WEIGHTS,
            components={
                "lookup_reasoning": 0.46,
                "visual_scan": normalize_int_with_bounds(
                    int(len(target_section.items)),
                    [min(item_count_support), max(item_count_support)],
                ),
                "layout_load": {
                    "topic_cards": 0.46,
                    "bullet_columns": 0.52,
                    "checklist_bands": 0.56,
                }.get(str(scene_variant), 0.50),
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
    "FILTERED_ITEM_QUERY_ID",
    "FILTERED_ITEM_QUERY_IDS",
    "QUERY_ID",
    "QUERY_IDS",
    "SCENE_ID",
    "SCENE_VARIANTS",
    "SECTIONED_INFOGRAPHIC_FILTERED_ITEM_TASK_ID",
    "SECTIONED_INFOGRAPHIC_ITEM_COUNT_TASK_ID",
    "PagesSectionedInfographicSectionFilteredItemLabelTask",
    "PagesSectionedInfographicSectionItemCountTask",
]
