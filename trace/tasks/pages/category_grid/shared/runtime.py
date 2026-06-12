"""Category-grid page lookup tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .....core.scene_config import get_scene_defaults
from .....core.seed import spawn_rng
from .....core.types import TypedValue
from .....core.visual.noise import apply_post_image_noise
from ....base import TaskOutput
from ....shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.output_metadata import default_task_versions
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ....shared.text_legibility import draw_text_traced
from ....shared.text_rendering import fit_font_to_box, load_font
from ....shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ....shared.visual_style.information_scene import make_information_scene_background
from ...shared.information_style import resolve_pages_information_style
from ...shared.legible_text import darken_surface_for_light_text, draw_required_page_text
from ...shared.page_text_resources import page_text_resource_metadata, sample_page_context_batch, sample_page_label_batch
from ...shared.visual_defaults import load_pages_scene_noise_defaults


CATEGORY_SLOT_ITEM_TASK_ID = "task_pages__category_grid__category_slot_item_label"
CATEGORY_ITEM_COUNT_TASK_ID = "task_pages__category_grid__category_item_count"
SCENE_ID = "category_grid"
CATEGORY_SLOT_ITEM_QUERY_ID = "category_slot_item_label"
CATEGORY_ITEM_COUNT_QUERY_ID = "category_item_count"
SCENE_VARIANTS: Tuple[str, ...] = ("card_grid", "column_groups", "compact_index")

_ACCENTS: Tuple[Tuple[int, int, int], ...] = (
    (55, 118, 172),
    (42, 142, 112),
    (190, 91, 76),
    (128, 102, 184),
    (198, 142, 58),
    (72, 132, 151),
    (168, 91, 132),
    (89, 122, 92),
)
_ORDINALS: Dict[int, str] = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
}


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
    category_title_font_size_px: int
    subcategory_title_font_size_px: int
    item_font_size_px: int


@dataclass(frozen=True)
class _CategoryItem:
    item_id: str
    label: str


@dataclass(frozen=True)
class _Subcategory:
    subcategory_id: str
    label: str
    items: Tuple[_CategoryItem, ...]


@dataclass(frozen=True)
class _Category:
    category_id: str
    label: str
    accent_rgb: Tuple[int, int, int]
    subcategories: Tuple[_Subcategory, ...]


@dataclass(frozen=True)
class _CategoryGridSpec:
    title: str
    subtitle: str
    categories: Tuple[_Category, ...]
    text_resource_metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedCategoryGrid:
    image: Image.Image
    entities: List[Dict[str, Any]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    category_header_bboxes_px: Dict[str, List[float]]
    subcategory_header_bboxes_px: Dict[str, Dict[str, List[float]]]
    item_row_bboxes_px: Dict[str, Dict[str, Dict[str, List[float]]]]
    item_label_bboxes_px: Dict[str, Dict[str, Dict[str, List[float]]]]
    layout_meta: Dict[str, Any]


_SCENE_DEFAULTS = get_scene_defaults("pages", SCENE_ID)
_SLOT_GEN_DEFAULTS, _SLOT_RENDER_DEFAULTS, _SLOT_PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=CATEGORY_SLOT_ITEM_TASK_ID,
)
_COUNT_GEN_DEFAULTS, _COUNT_RENDER_DEFAULTS, _COUNT_PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=CATEGORY_ITEM_COUNT_TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_pages_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


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
        if int(value) not in values:
            values.append(int(value))
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
        canvas_width=_int_value("canvas_width", 1120, minimum=540),
        canvas_height=_int_value("canvas_height", 900, minimum=560),
        outer_margin_px=_int_value("outer_margin_px", 34, minimum=0),
        header_height_px=_int_value("header_height_px", 88, minimum=54),
        gap_px=_int_value("gap_px", 14, minimum=4),
        corner_radius_px=_int_value("corner_radius_px", 14, minimum=0),
        outline_width_px=_int_value("outline_width_px", 2, minimum=1),
        title_font_size_px=_int_value("title_font_size_px", 30, minimum=14),
        subtitle_font_size_px=_int_value("subtitle_font_size_px", 17, minimum=10),
        category_title_font_size_px=_int_value("category_title_font_size_px", 21, minimum=11),
        subcategory_title_font_size_px=_int_value("subcategory_title_font_size_px", 15, minimum=9),
        item_font_size_px=_int_value("item_font_size_px", 14, minimum=8),
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
            namespace=str(namespace or f"category_grid.{role}"),
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


def _ordinal(value: int) -> str:
    return str(_ORDINALS.get(int(value), f"{int(value)}th"))


def _build_category_grid_spec(
    *,
    category_count: int,
    subcategory_count: int,
    item_count_support: Sequence[int],
    instance_seed: int,
) -> _CategoryGridSpec:
    rng = spawn_rng(int(instance_seed), "category_grid.spec")
    max_items = int(category_count) * int(subcategory_count) * max(int(value) for value in item_count_support)
    title_batch = sample_page_context_batch(
        rng,
        role="category_grid_title",
        count=1,
        manifest_names=("phrases/headlines.txt",),
    )
    subtitle_batch = sample_page_context_batch(
        rng,
        role="category_grid_subtitle",
        count=1,
        manifest_names=("phrases/captions.txt", "phrases/legend_notes.txt"),
    )
    category_batch = sample_page_label_batch(
        rng,
        role="category_grid_category_label",
        count=int(category_count),
        manifest_name="categories/product_labels.txt",
        min_chars=3,
        max_chars=16,
        allow_spaces=True,
        allow_punctuation=False,
    )
    subcategory_batch = sample_page_label_batch(
        rng,
        role="category_grid_subcategory_label",
        count=int(category_count) * int(subcategory_count),
        manifest_name="panel_titles/technical_topics.txt",
        min_chars=3,
        max_chars=18,
        allow_spaces=True,
        allow_punctuation=False,
        exclude=category_batch.values,
    )
    item_batch = sample_page_label_batch(
        rng,
        role="category_grid_item_label",
        count=int(max_items),
        manifest_name="mixed/compact_labels.txt",
        min_chars=5,
        max_chars=18,
        allow_spaces=True,
        allow_punctuation=False,
        exclude=tuple(category_batch.values) + tuple(subcategory_batch.values),
    )
    category_titles = list(category_batch.values)
    subcategory_titles = list(subcategory_batch.values)
    item_labels = list(item_batch.values)

    item_cursor = 0
    subcategory_cursor = 0
    accent_offset = int(rng.randrange(len(_ACCENTS)))
    categories: List[_Category] = []
    for category_index in range(int(category_count)):
        subcategories: List[_Subcategory] = []
        for subcategory_index in range(int(subcategory_count)):
            item_count = int(item_count_support[int(rng.randrange(len(item_count_support)))])
            items: List[_CategoryItem] = []
            for item_index in range(int(item_count)):
                items.append(
                    _CategoryItem(
                        item_id=(
                            f"category_{int(category_index) + 1}_subcategory_{int(subcategory_index) + 1}"
                            f"_item_{int(item_index) + 1}"
                        ),
                        label=str(item_labels[int(item_cursor)]),
                    )
                )
                item_cursor += 1
            subcategories.append(
                _Subcategory(
                    subcategory_id=f"category_{int(category_index) + 1}_subcategory_{int(subcategory_index) + 1}",
                    label=str(subcategory_titles[int(subcategory_cursor)]),
                    items=tuple(items),
                )
            )
            subcategory_cursor += 1
        categories.append(
            _Category(
                category_id=f"category_{int(category_index) + 1}",
                label=str(category_titles[int(category_index)]),
                accent_rgb=tuple(int(value) for value in _ACCENTS[(int(category_index) + int(accent_offset)) % len(_ACCENTS)]),
                subcategories=tuple(subcategories),
            )
        )
    return _CategoryGridSpec(
        title=str(title_batch.values[0]),
        subtitle=str(subtitle_batch.values[0]),
        categories=tuple(categories),
        text_resource_metadata=page_text_resource_metadata(
            title_batch,
            subtitle_batch,
            category_batch,
            subcategory_batch,
            item_batch,
        ),
    )


def _layout_category_boxes(
    *,
    scene_variant: str,
    category_count: int,
    content_bbox: Sequence[float],
    gap_px: int,
) -> Tuple[List[List[float]], Dict[str, Any]]:
    x0, y0, x1, y1 = [float(value) for value in content_bbox]
    width = max(1.0, x1 - x0)
    height = max(1.0, y1 - y0)
    gap = float(gap_px)
    if str(scene_variant) == "column_groups":
        columns = min(max(1, int(category_count)), 4)
        rows = int((int(category_count) + int(columns) - 1) // int(columns))
    elif str(scene_variant) == "compact_index":
        columns = 1
        rows = max(1, int(category_count))
    else:
        columns = 2 if int(category_count) > 1 else 1
        rows = int((int(category_count) + int(columns) - 1) // int(columns))
    cell_w = (width - (float(columns - 1) * gap)) / float(columns)
    cell_h = (height - (float(rows - 1) * gap)) / float(rows)
    boxes: List[List[float]] = []
    for index in range(int(category_count)):
        row = int(index) // int(columns)
        col = int(index) % int(columns)
        left = x0 + float(col) * (cell_w + gap)
        top = y0 + float(row) * (cell_h + gap)
        boxes.append([left, top, left + cell_w, top + cell_h])
    return boxes, {
        "layout_columns": int(columns),
        "layout_rows": int(rows),
        "category_cell_width_px": float(cell_w),
        "category_cell_height_px": float(cell_h),
    }


def _render_category_grid(
    background: Image.Image,
    *,
    spec: _CategoryGridSpec,
    scene_variant: str,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
) -> _RenderedCategoryGrid:
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
    header_fill = tuple(int(value) for value in style.header_rgb)
    title_surface_rgb = tuple(int(value) for value in style.surface_rgb)
    if str(style.chrome_kind) in {"accent_header", "rule_header", "accent_frame"} or str(style.chrome_mode) == "accent_frame":
        header_fill = darken_surface_for_light_text(header_fill, text_rgb=style.header_text_rgb)
        draw.rounded_rectangle(
            (panel_bbox[0], panel_bbox[1], panel_bbox[2], panel_bbox[1] + float(header_h)),
            radius=radius,
            fill=header_fill,
        )
        draw.rectangle(
            (panel_bbox[0], panel_bbox[1] + float(header_h) - float(radius), panel_bbox[2], panel_bbox[1] + float(header_h)),
            fill=header_fill,
        )
        title_rgb = tuple(int(value) for value in style.header_text_rgb)
        subtitle_rgb = tuple(int(value) for value in style.header_text_rgb)
        title_surface_rgb = tuple(int(value) for value in header_fill)
    else:
        title_rgb = tuple(int(value) for value in style.text_rgb)
        subtitle_rgb = tuple(int(value) for value in style.muted_text_rgb)
        y_rule = panel_bbox[1] + float(header_h)
        draw.line((panel_bbox[0] + 20.0, y_rule, panel_bbox[2] - 20.0, y_rule), fill=style.guide_rgb, width=1)

    scale = float(style.typography_scale)
    title_font = load_font(max(10, int(round(render_params.title_font_size_px * scale))), bold=True)
    subtitle_font = load_font(max(8, int(round(render_params.subtitle_font_size_px * scale))), bold=False)
    category_font_size = max(10, int(round(render_params.category_title_font_size_px * scale)))
    subcategory_font_size = max(9, int(round(render_params.subcategory_title_font_size_px * scale)))
    item_font_size = max(8, int(round(render_params.item_font_size_px * scale)))
    title_bbox = _draw_text(
        draw,
        (panel_bbox[0] + 24.0, panel_bbox[1] + 18.0),
        str(spec.title),
        title_font,
        title_rgb,
        role="page_title",
        surface_rgbs=(title_surface_rgb,),
        instance_seed=int(instance_seed),
        namespace=f"{CATEGORY_ITEM_COUNT_TASK_ID}.page_title.{scene_variant}",
    )
    _draw_text(
        draw,
        (panel_bbox[0] + 24.0, panel_bbox[1] + 54.0),
        str(spec.subtitle),
        subtitle_font,
        subtitle_rgb,
        stroke_width=0,
        role="page_subtitle",
        surface_rgbs=(title_surface_rgb,),
        instance_seed=int(instance_seed),
        namespace=f"{CATEGORY_ITEM_COUNT_TASK_ID}.page_subtitle.{scene_variant}",
    )

    content_bbox = [
        panel_bbox[0] + float(style.panel_padding_px),
        panel_bbox[1] + float(header_h) + float(render_params.gap_px),
        panel_bbox[2] - float(style.panel_padding_px),
        panel_bbox[3] - float(style.panel_padding_px),
    ]
    category_boxes, layout_meta = _layout_category_boxes(
        scene_variant=str(scene_variant),
        category_count=len(spec.categories),
        content_bbox=content_bbox,
        gap_px=int(render_params.gap_px),
    )
    text_rgb = tuple(int(value) for value in style.text_rgb)
    muted_rgb = tuple(int(value) for value in style.muted_text_rgb)
    border_rgb = tuple(int(value) for value in style.panel_border_rgb)
    guide_rgb = tuple(int(value) for value in style.guide_rgb)
    category_header_bboxes: Dict[str, List[float]] = {}
    subcategory_header_bboxes: Dict[str, Dict[str, List[float]]] = {}
    item_row_bboxes: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    item_label_bboxes: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    entities: List[Dict[str, Any]] = []

    for category, category_bbox in zip(spec.categories, category_boxes):
        x0, y0, x1, y1 = [float(value) for value in category_bbox]
        accent = tuple(int(value) for value in category.accent_rgb)
        card_radius = max(4, int(radius * 0.65))
        card_fill = _blend_rgb(style.panel_fill_rgb, accent, 0.06 if str(scene_variant) != "compact_index" else 0.035)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=card_radius, fill=card_fill, outline=border_rgb, width=1)
        cat_band_h = max(34.0, min(46.0, (y1 - y0) * (0.20 if str(scene_variant) == "compact_index" else 0.16)))
        band_fill = darken_surface_for_light_text(
            _blend_rgb(style.header_rgb, accent, 0.24),
            text_rgb=style.header_text_rgb,
        )
        draw.rounded_rectangle((x0, y0, x1, y0 + cat_band_h), radius=card_radius, fill=band_fill)
        draw.rectangle((x0, y0 + cat_band_h - float(card_radius), x1, y0 + cat_band_h), fill=band_fill)
        category_font = fit_font_to_box(
            draw,
            text=str(category.label),
            max_width=max(40.0, x1 - x0 - 30.0),
            max_height=max(16.0, cat_band_h - 12.0),
            bold=True,
            min_size_px=10,
            max_size_px=int(category_font_size),
            fill_ratio=0.97,
        )
        cat_probe = _text_bbox(draw, (x0 + 16.0, y0 + 8.0), str(category.label), category_font)
        category_header_bboxes[str(category.category_id)] = _draw_text(
            draw,
            (x0 + 16.0, y0 + max(7.0, (cat_band_h - (cat_probe[3] - cat_probe[1])) / 2.0)),
            str(category.label),
            category_font,
            tuple(int(value) for value in style.header_text_rgb),
            role="category_header",
            surface_rgbs=(band_fill,),
            instance_seed=int(instance_seed),
            namespace=f"{CATEGORY_ITEM_COUNT_TASK_ID}.category_header.{category.category_id}",
        )
        subcategory_header_bboxes[str(category.category_id)] = {}
        item_row_bboxes[str(category.category_id)] = {}
        item_label_bboxes[str(category.category_id)] = {}
        sub_area = [
            x0 + 10.0,
            y0 + cat_band_h + 10.0,
            x1 - 10.0,
            y1 - 10.0,
        ]
        sub_count = len(category.subcategories)
        sub_gap = max(5.0, float(render_params.gap_px) * 0.55)
        if str(scene_variant) == "compact_index":
            sub_w = (sub_area[2] - sub_area[0] - float(sub_count - 1) * sub_gap) / float(max(1, sub_count))
            sub_h = sub_area[3] - sub_area[1]
            sub_boxes = [
                [
                    sub_area[0] + float(index) * (sub_w + sub_gap),
                    sub_area[1],
                    sub_area[0] + float(index) * (sub_w + sub_gap) + sub_w,
                    sub_area[1] + sub_h,
                ]
                for index in range(sub_count)
            ]
        else:
            sub_h = (sub_area[3] - sub_area[1] - float(sub_count - 1) * sub_gap) / float(max(1, sub_count))
            sub_boxes = [
                [
                    sub_area[0],
                    sub_area[1] + float(index) * (sub_h + sub_gap),
                    sub_area[2],
                    sub_area[1] + float(index) * (sub_h + sub_gap) + sub_h,
                ]
                for index in range(sub_count)
            ]

        category_entity = {
            "entity_id": str(category.category_id),
            "kind": "category_grid_category",
            "label": str(category.label),
            "accent_rgb": [int(value) for value in accent],
            "bbox_px": [float(value) for value in category_bbox],
            "header_bbox_px": [float(value) for value in category_header_bboxes[str(category.category_id)]],
            "subcategories": [],
        }
        for subcategory, sub_bbox in zip(category.subcategories, sub_boxes):
            sx0, sy0, sx1, sy1 = [float(value) for value in sub_bbox]
            sub_radius = max(3, int(card_radius * 0.55))
            sub_panel_fill = _blend_rgb(style.surface_alt_rgb, accent, 0.055)
            draw.rounded_rectangle(
                (sx0, sy0, sx1, sy1),
                radius=sub_radius,
                fill=sub_panel_fill,
                outline=guide_rgb,
                width=1,
            )
            sub_band_h = max(24.0, min(32.0, (sy1 - sy0) * 0.28))
            sub_band_fill = _blend_rgb(style.panel_fill_rgb, accent, 0.12)
            draw.rounded_rectangle((sx0, sy0, sx1, sy0 + sub_band_h), radius=sub_radius, fill=sub_band_fill)
            draw.rectangle((sx0, sy0 + sub_band_h - float(sub_radius), sx1, sy0 + sub_band_h), fill=sub_band_fill)
            sub_font = fit_font_to_box(
                draw,
                text=str(subcategory.label),
                max_width=max(30.0, sx1 - sx0 - 20.0),
                max_height=max(12.0, sub_band_h - 8.0),
                bold=True,
                min_size_px=8,
                max_size_px=int(subcategory_font_size),
                fill_ratio=0.97,
            )
            subcategory_header_bboxes[str(category.category_id)][str(subcategory.subcategory_id)] = _draw_text(
                draw,
                (sx0 + 10.0, sy0 + max(5.0, (sub_band_h - float(getattr(sub_font, "size", subcategory_font_size))) / 2.0)),
                str(subcategory.label),
                sub_font,
                text_rgb,
                role="subcategory_header",
                surface_rgbs=(sub_band_fill,),
                instance_seed=int(instance_seed),
                namespace=f"{CATEGORY_ITEM_COUNT_TASK_ID}.subcategory_header.{category.category_id}.{subcategory.subcategory_id}",
            )
            item_row_bboxes[str(category.category_id)][str(subcategory.subcategory_id)] = {}
            item_label_bboxes[str(category.category_id)][str(subcategory.subcategory_id)] = {}
            item_top = sy0 + sub_band_h + 5.0
            item_bottom = sy1 - 5.0
            row_h = max(9.0, (item_bottom - item_top) / float(max(1, len(subcategory.items))))
            item_font_base = load_font(max(6, min(item_font_size, int(row_h * 0.64))), bold=True)
            subcategory_entity = {
                "subcategory_id": str(subcategory.subcategory_id),
                "label": str(subcategory.label),
                "header_bbox_px": [
                    float(value)
                    for value in subcategory_header_bboxes[str(category.category_id)][str(subcategory.subcategory_id)]
                ],
                "items": [],
            }
            for item_index, item in enumerate(subcategory.items):
                row_y0 = item_top + float(item_index) * row_h
                row_y1 = item_top + float(item_index + 1) * row_h
                row_bbox = [sx0 + 7.0, row_y0 + 1.5, sx1 - 7.0, row_y1 - 1.5]
                row_fill = sub_panel_fill
                if int(item_index) % 2 == 0 or str(scene_variant) == "compact_index":
                    row_fill = _blend_rgb(style.panel_fill_rgb, accent, 0.035)
                    draw.rounded_rectangle(
                        tuple(row_bbox),
                        radius=4,
                        fill=row_fill,
                    )
                marker_r = min(4.5, max(2.5, row_h * 0.15))
                marker_cx = row_bbox[0] + 10.0
                marker_cy = (row_bbox[1] + row_bbox[3]) / 2.0
                draw.ellipse((marker_cx - marker_r, marker_cy - marker_r, marker_cx + marker_r, marker_cy + marker_r), fill=accent)
                item_font = fit_font_to_box(
                    draw,
                    text=str(item.label),
                    max_width=max(28.0, row_bbox[2] - row_bbox[0] - 28.0),
                    max_height=max(10.0, row_h - 5.0),
                    bold=True,
                    min_size_px=6,
                    max_size_px=max(6, int(getattr(item_font_base, "size", item_font_size) or item_font_size)),
                    fill_ratio=0.98,
                )
                label_bbox = _draw_text(
                    draw,
                    (row_bbox[0] + 22.0, row_bbox[1] + max(1.0, (row_h - float(getattr(item_font, "size", item_font_size))) / 2.0)),
                    str(item.label),
                    item_font,
                    text_rgb,
                    role="category_grid_item_label",
                    surface_rgbs=(row_fill,),
                    instance_seed=int(instance_seed),
                    namespace=f"{CATEGORY_ITEM_COUNT_TASK_ID}.item_label.{item.item_id}",
                )
                full_row_bbox = [
                    float(row_bbox[0]),
                    min(float(row_bbox[1]), float(label_bbox[1]), marker_cy - marker_r),
                    float(row_bbox[2]),
                    max(float(row_bbox[3]), float(label_bbox[3]), marker_cy + marker_r),
                ]
                item_row_bboxes[str(category.category_id)][str(subcategory.subcategory_id)][str(item.item_id)] = full_row_bbox
                item_label_bboxes[str(category.category_id)][str(subcategory.subcategory_id)][str(item.item_id)] = [
                    float(value) for value in label_bbox
                ]
                subcategory_entity["items"].append(
                    {
                        "item_id": str(item.item_id),
                        "label": str(item.label),
                        "slot_index": int(item_index) + 1,
                        "item_row_bbox_px": [float(value) for value in full_row_bbox],
                        "item_label_bbox_px": [float(value) for value in label_bbox],
                    }
                )
                if int(item_index) < len(subcategory.items) - 1:
                    draw.line((sx0 + 8.0, row_y1, sx1 - 8.0, row_y1), fill=guide_rgb, width=1)
            category_entity["subcategories"].append(subcategory_entity)
        entities.append(category_entity)

    return _RenderedCategoryGrid(
        image=image,
        entities=entities,
        panel_bbox_px=[float(value) for value in panel_bbox],
        title_bbox_px=[float(value) for value in title_bbox],
        category_header_bboxes_px=category_header_bboxes,
        subcategory_header_bboxes_px=subcategory_header_bboxes,
        item_row_bboxes_px=item_row_bboxes,
        item_label_bboxes_px=item_label_bboxes,
        layout_meta={
            "scene_variant": str(scene_variant),
            "content_bbox_px": [float(value) for value in content_bbox],
            "category_count": int(len(spec.categories)),
            "subcategory_count_per_category": int(len(spec.categories[0].subcategories)) if spec.categories else 0,
            **dict(layout_meta),
        },
    )


def _build_prompt_examples(*, query_id: str) -> Tuple[str, str]:
    if str(query_id) == CATEGORY_ITEM_COUNT_QUERY_ID:
        return (
            json.dumps({"annotation": [[20, 80, 180, 104], [20, 110, 180, 134]], "answer": 2}, separators=(",", ":")),
            json.dumps({"answer": 2}, separators=(",", ":")),
        )
    annotation = {
        "category_header": [2, 3, 4, 5],
        "subcategory_header": [3, 4, 5, 6],
        "target_item": [4, 5, 6, 7],
    }
    return (
        json.dumps({"annotation": annotation, "answer": "Amber Leaf"}, separators=(",", ":")),
        json.dumps({"answer": "Amber Leaf"}, separators=(",", ":")),
    )


def _select_target(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    spec: _CategoryGridSpec,
    for_slot_query: bool,
) -> Tuple[_Category, _Subcategory, int | None, _CategoryItem | None]:
    category_count = len(spec.categories)
    category_index = int(params["target_category_index"]) if params.get("target_category_index") is not None else int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_category",
        )
        % int(category_count)
    )
    if category_index < 0 or category_index >= int(category_count):
        raise ValueError("target_category_index out of range")
    target_category = spec.categories[int(category_index)]
    subcategory_count = len(target_category.subcategories)
    subcategory_index = (
        int(params["target_subcategory_index"])
        if params.get("target_subcategory_index") is not None
        else int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.target_subcategory.{category_index}",
            )
            % int(subcategory_count)
        )
    )
    if subcategory_index < 0 or subcategory_index >= int(subcategory_count):
        raise ValueError("target_subcategory_index out of range")
    target_subcategory = target_category.subcategories[int(subcategory_index)]
    if not bool(for_slot_query):
        return target_category, target_subcategory, None, None
    item_count = len(target_subcategory.items)
    slot_index = int(params["target_slot_index"]) if params.get("target_slot_index") is not None else int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_slot.{category_index}.{subcategory_index}",
        )
        % int(item_count)
    )
    if slot_index < 0 or slot_index >= int(item_count):
        raise ValueError("target_slot_index out of range")
    return target_category, target_subcategory, int(slot_index), target_subcategory.items[int(slot_index)]


def _make_category_payload(rendered: _RenderedCategoryGrid, spec: _CategoryGridSpec) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = []
    for category in spec.categories:
        category_payload = {
            "category_id": str(category.category_id),
            "category_label": str(category.label),
            "category_header_bbox_px": [
                float(value) for value in rendered.category_header_bboxes_px[str(category.category_id)]
            ],
            "subcategories": [],
        }
        for subcategory in category.subcategories:
            subcategory_payload = {
                "subcategory_id": str(subcategory.subcategory_id),
                "subcategory_label": str(subcategory.label),
                "subcategory_header_bbox_px": [
                    float(value)
                    for value in rendered.subcategory_header_bboxes_px[str(category.category_id)][str(subcategory.subcategory_id)]
                ],
                "item_count": int(len(subcategory.items)),
                "items": [],
            }
            for item_index, item in enumerate(subcategory.items):
                subcategory_payload["items"].append(
                    {
                        "item_id": str(item.item_id),
                        "item_label": str(item.label),
                        "slot_index": int(item_index) + 1,
                        "slot_ordinal": _ordinal(int(item_index) + 1),
                        "item_row_bbox_px": [
                            float(value)
                            for value in rendered.item_row_bboxes_px[str(category.category_id)][str(subcategory.subcategory_id)][str(item.item_id)]
                        ],
                        "item_label_bbox_px": [
                            float(value)
                            for value in rendered.item_label_bboxes_px[str(category.category_id)][str(subcategory.subcategory_id)][str(item.item_id)]
                        ],
                    }
                )
            category_payload["subcategories"].append(subcategory_payload)
        payload.append(category_payload)
    return payload


def _generate_category_grid_output(
    *,
    task_id: str,
    instance_seed: int,
    params: Dict[str, Any],
    query_id: str,
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults_raw: Mapping[str, Any],
) -> TaskOutput:
    scene_variant, scene_variant_probabilities = _resolve_named_variant(
        task_id=task_id,
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        namespace="scene_variant",
    )
    category_count, category_count_support, category_count_probabilities = _resolve_supported_int(
        task_id=task_id,
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="category_count",
        support_key="category_count_support",
        fallback=(3, 4),
        instance_seed=int(instance_seed),
        namespace="category_count",
    )
    subcategory_count, subcategory_count_support, subcategory_count_probabilities = _resolve_supported_int(
        task_id=task_id,
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="subcategory_count",
        support_key="subcategory_count_support",
        fallback=(2, 3),
        instance_seed=int(instance_seed),
        namespace="subcategory_count",
    )
    item_count_support = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        key="item_count_support",
        fallback=(3, 4),
    )
    spec = _build_category_grid_spec(
        category_count=int(category_count),
        subcategory_count=int(subcategory_count),
        item_count_support=tuple(item_count_support),
        instance_seed=int(instance_seed),
    )
    is_slot_query = str(query_id) == CATEGORY_SLOT_ITEM_QUERY_ID
    target_category, target_subcategory, target_slot_index, target_item = _select_target(
        task_id=str(task_id),
        params=params,
        instance_seed=int(instance_seed),
        spec=spec,
        for_slot_query=bool(is_slot_query),
    )

    render_params = _resolve_render_params(params, render_defaults)
    style, style_meta = resolve_pages_information_style(
        instance_seed=int(instance_seed),
        params=render_defaults,
        scene_id=SCENE_ID,
        allow_dark=False,
    )
    background, background_meta = make_information_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=f"pages.{SCENE_ID}.information_scene_background",
    )
    rendered = _render_category_grid(
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

    target_category_id = str(target_category.category_id)
    target_subcategory_id = str(target_subcategory.subcategory_id)
    if bool(is_slot_query):
        if target_item is None or target_slot_index is None:
            raise RuntimeError("slot query target was not selected")
        answer_value: str | int = str(target_item.label)
        target_item_id = str(target_item.item_id)
        annotation_value: Dict[str, List[float]] | List[List[float]] = {
            "category_header": [float(value) for value in rendered.category_header_bboxes_px[target_category_id]],
            "subcategory_header": [
                float(value) for value in rendered.subcategory_header_bboxes_px[target_category_id][target_subcategory_id]
            ],
            "target_item": [
                float(value)
                for value in rendered.item_row_bboxes_px[target_category_id][target_subcategory_id][target_item_id]
            ],
        }
        answer_type = "string"
        annotation_type = "keyed_bbox_map"
        question_format = "category_grid_category_slot_item_label"
    else:
        answer_value = int(len(target_subcategory.items))
        annotation_value = [
            [
                float(value)
                for value in rendered.item_row_bboxes_px[target_category_id][target_subcategory_id][str(item.item_id)]
            ]
            for item in target_subcategory.items
        ]
        answer_type = "integer"
        annotation_type = "bbox_set"
        question_format = "category_grid_category_item_count"

    prompt_defaults = required_group_defaults(
        prompt_defaults_raw,
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
        context=f"prompt defaults for {task_id}",
    )
    json_example, json_example_answer_only = _build_prompt_examples(query_id=str(query_id))
    slots = {
        "object_description": str(prompt_defaults["object_description"]),
        "category_label": f'"{str(target_category.label)}"',
        "subcategory_label": f'"{str(target_subcategory.label)}"',
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint"]),
        "annotation_hint": str(prompt_defaults["annotation_hint"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }
    if bool(is_slot_query):
        slots["slot_ordinal"] = str(_ordinal(int(target_slot_index) + 1))
    prompt_selection = render_scene_prompt_variants(
        domain="pages",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    target_payload: Dict[str, Any] = {
        "category_id": str(target_category.category_id),
        "category_label": str(target_category.label),
        "subcategory_id": str(target_subcategory.subcategory_id),
        "subcategory_label": str(target_subcategory.label),
    }
    if bool(is_slot_query):
        target_payload.update(
            {
                "slot_index": int(target_slot_index) + 1 if target_slot_index is not None else None,
                "slot_ordinal": _ordinal(int(target_slot_index) + 1) if target_slot_index is not None else None,
                "item_id": str(target_item.item_id) if target_item is not None else "",
                "item_label": str(target_item.label) if target_item is not None else "",
            }
        )
    else:
        target_payload.update(
            {
                "item_count": int(answer_value),
                "item_ids": [str(item.item_id) for item in target_subcategory.items],
            }
        )
    categories_payload = _make_category_payload(rendered, spec)
    trace_payload = {
        "scene_ir": {
            "scene_id": SCENE_ID,
            "scene_kind": "pages_category_grid",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "target": dict(target_payload),
                "answer_value": answer_value,
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
                "target": dict(target_payload),
                "target_answer": answer_value,
                "category_count": int(category_count),
                "subcategory_count": int(subcategory_count),
                "item_count_support": [int(value) for value in item_count_support],
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "category_count_probabilities": dict(category_count_probabilities),
                "subcategory_count_probabilities": dict(subcategory_count_probabilities),
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
            "category_header_bboxes_px": dict(rendered.category_header_bboxes_px),
            "subcategory_header_bboxes_px": dict(rendered.subcategory_header_bboxes_px),
            "item_row_bboxes_px": dict(rendered.item_row_bboxes_px),
            "item_label_bboxes_px": dict(rendered.item_label_bboxes_px),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "question_format": str(question_format),
            "category_count": int(category_count),
            "subcategory_count": int(subcategory_count),
            "category_count_support": [int(value) for value in category_count_support],
            "subcategory_count_support": [int(value) for value in subcategory_count_support],
            "item_count_support": [int(value) for value in item_count_support],
            "target": dict(target_payload),
            "answer_value": answer_value,
            "categories": list(categories_payload),
            "page_text_resources": dict(spec.text_resource_metadata),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "category_count_probabilities": dict(category_count_probabilities),
            "subcategory_count_probabilities": dict(subcategory_count_probabilities),
        },
        "witness_symbolic": {
            "type": str(question_format),
            "target_category_id": str(target_category.category_id),
            "target_subcategory_id": str(target_subcategory.subcategory_id),
            "answer_value": answer_value,
        },
    }
    if bool(is_slot_query):
        keyed_bboxes = dict(annotation_value)  # type: ignore[arg-type]
        trace_payload["projected_annotation"] = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(keyed_bboxes),
            "pixel_keyed_bbox_map": dict(keyed_bboxes),
            "bbox_set": list(keyed_bboxes.values()),
            "target_category_id": str(target_category.category_id),
            "target_subcategory_id": str(target_subcategory.subcategory_id),
        }
    else:
        bbox_set = [list(bbox) for bbox in annotation_value]  # type: ignore[union-attr]
        trace_payload["projected_annotation"] = {
            "type": "bbox_set",
            "bbox_set": list(bbox_set),
            "pixel_bbox_set": list(bbox_set),
            "target_category_id": str(target_category.category_id),
            "target_subcategory_id": str(target_subcategory.subcategory_id),
        }

    total_items = sum(len(subcategory.items) for category in spec.categories for subcategory in category.subcategories)
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type=str(answer_type), value=answer_value),
        annotation_gt=TypedValue(type=str(annotation_type), value=annotation_value),
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(query_id),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


def generate_category_grid_output(
    *,
    public_task_id: str,
    fixed_query_id: str,
    instance_seed: int,
    params: Dict[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Generate one category-grid task from the scene-package public wrapper."""

    del max_attempts
    task_id = str(public_task_id)
    query_id_expected = str(fixed_query_id)

    params = dict(params)
    explicit_query_id = params.get("query_id")
    if explicit_query_id is not None and str(explicit_query_id) != query_id_expected:
        raise ValueError(f"query_id must be {query_id_expected!r} for {task_id}")
    params["query_id"] = query_id_expected
    query_id, _query_id_probabilities = _resolve_named_variant(
        task_id=task_id,
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=(query_id_expected,),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace="query_id",
    )
    query_id_probabilities = {str(query_id): 1.0}
    output.trace_payload["query_spec"]["params"]["query_id_probabilities"] = dict(query_id_probabilities)
    output.trace_payload["execution_trace"]["query_id_probabilities"] = dict(query_id_probabilities)
    return output


__all__ = [
    "CATEGORY_ITEM_COUNT_QUERY_ID",
    "CATEGORY_ITEM_COUNT_TASK_ID",
    "CATEGORY_SLOT_ITEM_QUERY_ID",
    "CATEGORY_SLOT_ITEM_TASK_ID",
    "SCENE_ID",
    "SCENE_VARIANTS",
    "generate_category_grid_output",
]
