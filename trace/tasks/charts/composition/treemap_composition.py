"""Treemap composition chart tasks."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_composition_treemap_base"
SCENE_ID = "treemap_part_whole"

GROUP_TOTAL_QUERY_IDS: Tuple[str, ...] = ("treemap_group_total_value",)
REPEATED_LEAF_QUERY_IDS: Tuple[str, ...] = (
    "treemap_repeated_leaf_sum_value",
    "treemap_repeated_leaf_average_value",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = GROUP_TOTAL_QUERY_IDS + REPEATED_LEAF_QUERY_IDS

RGB = Tuple[int, int, int]
BBox = List[float]

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "composition")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="composition")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="composition", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

_QUERY_REASONING_LOAD: Dict[str, float] = {
    "treemap_group_total_value": 0.70,
    "treemap_repeated_leaf_sum_value": 0.74,
    "treemap_repeated_leaf_average_value": 0.78,
}

_THEMES: Tuple[Dict[str, Any], ...] = (
    {
        "title": "Community Program Breakdown",
        "parent_axis": "program",
        "leaf_axis": "audience",
        "parents": ("Festival", "Tournament", "Health Fair", "Cleanup", "Workshop", "Forum"),
        "leaves": ("Adults", "Youth", "Seniors", "Families", "Volunteers", "Guests"),
    },
    {
        "title": "Method Adoption by Industry",
        "parent_axis": "industry",
        "leaf_axis": "method",
        "parents": ("Healthcare", "Finance", "Education", "Retail", "Manufacturing", "Logistics"),
        "leaves": ("Scrum", "Kanban", "Extreme", "Waterfall", "Lean", "Hybrid"),
    },
    {
        "title": "Habitat Species by Category",
        "parent_axis": "habitat",
        "leaf_axis": "species group",
        "parents": ("Polar", "Forest", "Wetland", "Desert", "Marine", "Grassland"),
        "leaves": ("Birds", "Mammals", "Reptiles", "Fish", "Plants", "Insects"),
    },
    {
        "title": "Department Time Allocation",
        "parent_axis": "department",
        "leaf_axis": "activity",
        "parents": ("Council", "Planning", "Budget", "Outreach", "Services", "Media"),
        "leaves": ("Meetings", "Research", "Review", "Events", "Relations", "Audits"),
    },
    {
        "title": "Household Expense Composition",
        "parent_axis": "expense group",
        "leaf_axis": "expense item",
        "parents": ("Housing", "Food", "Utilities", "Transport", "Debt", "Care"),
        "leaves": ("Rent", "Groceries", "Water", "Electricity", "Internet", "Fuel"),
    },
    {
        "title": "Streaming Revenue Composition",
        "parent_axis": "genre",
        "leaf_axis": "platform",
        "parents": ("Rock", "Hip-Hop", "Jazz", "Electronic", "Country", "Classical"),
        "leaves": ("Spotify", "Apple", "Amazon", "YouTube", "Tidal", "Deezer"),
    },
)


@dataclass(frozen=True)
class _Leaf:
    leaf_id: str
    parent_id: str
    parent_label: str
    label: str
    value: int
    color_rgb: RGB


@dataclass(frozen=True)
class _Parent:
    parent_id: str
    label: str
    leaf_ids: Tuple[str, ...]
    value: int
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int
    evidence_leaf_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    title: str
    parent_axis: str
    leaf_axis: str
    parents: Tuple[_Parent, ...]
    leaves: Tuple[_Leaf, ...]
    query: _Query
    generation_ranges: Dict[str, Any]


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    title_font_size_px: int
    parent_font_size_px: int
    leaf_font_size_px: int
    value_font_size_px: int
    note_font_size_px: int
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    text_color_rgb: RGB
    muted_text_rgb: RGB
    separator_rgb: RGB
    text_stroke_rgb: RGB
    label_stroke_width_px: int


@dataclass(frozen=True)
class _RenderedTreemap:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    leaf_traces: Tuple[Dict[str, Any], ...]
    parent_traces: Tuple[Dict[str, Any], ...]
    evidence_bbox_by_leaf_id: Dict[str, BBox]
    chart_bbox_px: BBox
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    return load_font(max(8, int(size)), bold=bool(bold))


def _quote(value: str) -> str:
    return f'"{str(value)}"'


def _truncate(text: str, max_chars: int) -> str:
    clean = str(text)
    if len(clean) <= int(max_chars):
        return clean
    return clean[: max(1, int(max_chars) - 1)] + "."


def _lighten(color: RGB, amount: float) -> RGB:
    return tuple(
        max(0, min(255, int(round(float(channel) + (255.0 - float(channel)) * float(amount)))))
        for channel in color
    )


def _darken(color: RGB, amount: float) -> RGB:
    return tuple(max(0, min(255, int(round(float(channel) * (1.0 - float(amount)))))) for channel in color)


def _theme_color(index: int, count: int, *, instance_seed: int) -> RGB:
    rng = spawn_rng(int(instance_seed), "charts.composition.treemap.palette")
    offset = rng.random()
    hue = (float(offset) + float(index) / max(1.0, float(count))) % 1.0
    sat = 0.45 + 0.18 * rng.random()
    val = 0.74 + 0.12 * rng.random()
    r, g, b = colorsys.hsv_to_rgb(float(hue), float(sat), float(val))
    return int(r * 255), int(g * 255), int(b * 255)


def _resolve_range(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {TASK_ID}",
    )


def _sample_query_id(params: Mapping[str, Any], *, allowed_query_ids: Sequence[str], instance_seed: int) -> str:
    allowed = tuple(str(item) for item in allowed_query_ids)
    explicit = params.get("query_id", params.get("query_variant", params.get("query_variant")))
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in set(allowed):
            raise ValueError(f"unsupported treemap query_id for this public task: {query_id}")
        return query_id
    if params.get("_sample_cursor") is not None:
        return str(allowed[abs(int(params["_sample_cursor"])) % len(allowed)])
    rng = spawn_rng(int(instance_seed), "charts.composition.treemap.query_id")
    return str(allowed[int(rng.randrange(len(allowed)))])


def _build_values(
    *,
    parent_count: int,
    leaf_count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> Tuple[Tuple[int, ...], ...]:
    rng = spawn_rng(int(instance_seed), "charts.composition.treemap.values")
    matrix: List[List[int]] = [[0 for _ in range(int(leaf_count))] for _ in range(int(parent_count))]
    for leaf_index in range(int(leaf_count)):
        subtotal = 0
        for parent_index in range(max(0, int(parent_count) - 1)):
            value = int(rng.randint(int(value_min), int(value_max)))
            matrix[parent_index][leaf_index] = int(value)
            subtotal += int(value)
        valid_last_values = [
            value
            for value in range(int(value_min), int(value_max) + 1)
            if (int(subtotal) + int(value)) % max(1, int(parent_count)) == 0
        ]
        if not valid_last_values:
            raise ValueError("treemap value range cannot produce integer repeated-leaf averages")
        matrix[int(parent_count) - 1][leaf_index] = int(valid_last_values[int(rng.randrange(len(valid_last_values)))])
    return tuple(tuple(int(value) for value in row) for row in matrix)


def _build_tree(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, str, str, Tuple[_Parent, ...], Tuple[_Leaf, ...], Dict[str, Any]]:
    parent_min, parent_max = _resolve_range(
        params,
        min_key="treemap_parent_count_min",
        max_key="treemap_parent_count_max",
        fallback_min=4,
        fallback_max=6,
    )
    leaf_min, leaf_max = _resolve_range(
        params,
        min_key="treemap_leaf_count_min",
        max_key="treemap_leaf_count_max",
        fallback_min=4,
        fallback_max=6,
    )
    value_min, value_max = _resolve_range(
        params,
        min_key="treemap_value_min",
        max_key="treemap_value_max",
        fallback_min=16,
        fallback_max=88,
    )
    rng = spawn_rng(int(instance_seed), "charts.composition.treemap.tree")
    theme = dict(_THEMES[int(rng.randrange(len(_THEMES)))])
    parent_count = int(rng.randint(int(parent_min), min(int(parent_max), len(theme["parents"]))))
    leaf_count = int(rng.randint(int(leaf_min), min(int(leaf_max), len(theme["leaves"]))))
    parent_labels = list(str(item) for item in theme["parents"])
    leaf_labels = list(str(item) for item in theme["leaves"])
    rng.shuffle(parent_labels)
    rng.shuffle(leaf_labels)
    parent_labels = parent_labels[:parent_count]
    leaf_labels = leaf_labels[:leaf_count]
    values = _build_values(
        parent_count=int(parent_count),
        leaf_count=int(leaf_count),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
    )
    leaves: List[_Leaf] = []
    parents: List[_Parent] = []
    for parent_index, parent_label in enumerate(parent_labels):
        parent_id = f"parent_{parent_index}"
        base_color = _theme_color(parent_index, parent_count, instance_seed=int(instance_seed))
        leaf_ids: List[str] = []
        parent_total = 0
        for leaf_index, leaf_label in enumerate(leaf_labels):
            leaf_id = f"{parent_id}_leaf_{leaf_index}"
            value = int(values[parent_index][leaf_index])
            leaf_ids.append(leaf_id)
            parent_total += int(value)
            leaves.append(
                _Leaf(
                    leaf_id=str(leaf_id),
                    parent_id=str(parent_id),
                    parent_label=str(parent_label),
                    label=str(leaf_label),
                    value=int(value),
                    color_rgb=_lighten(base_color, 0.08 + 0.08 * (leaf_index % 4)),
                )
            )
        parents.append(
            _Parent(
                parent_id=str(parent_id),
                label=str(parent_label),
                leaf_ids=tuple(leaf_ids),
                value=int(parent_total),
                color_rgb=base_color,
            )
        )
    ranges = {
        "parent_count_range": [int(parent_min), int(parent_max)],
        "leaf_count_range": [int(leaf_min), int(leaf_max)],
        "value_range": [int(value_min), int(value_max)],
    }
    return str(theme["title"]), str(theme["parent_axis"]), str(theme["leaf_axis"]), tuple(parents), tuple(leaves), ranges


def _build_query(
    *,
    query_id: str,
    parents: Sequence[_Parent],
    leaves: Sequence[_Leaf],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Query:
    rng = spawn_rng(int(instance_seed), f"charts.composition.treemap.query.{query_id}")
    leaves_by_id = {str(leaf.leaf_id): leaf for leaf in leaves}
    if str(query_id) == "treemap_group_total_value":
        parent = parents[abs(int(params.get("_sample_cursor", rng.randrange(len(parents))))) % len(parents)]
        evidence_leaf_ids = tuple(str(leaf_id) for leaf_id in parent.leaf_ids)
        return _Query(
            query_id=str(query_id),
            answer=int(parent.value),
            evidence_leaf_ids=tuple(evidence_leaf_ids),
            trace={
                "parent_id": str(parent.parent_id),
                "parent_label": str(parent.label),
                "leaf_ids": [str(leaf_id) for leaf_id in evidence_leaf_ids],
                "leaf_values": [int(leaves_by_id[leaf_id].value) for leaf_id in evidence_leaf_ids],
                "operation": "sum",
            },
        )
    if str(query_id) in {"treemap_repeated_leaf_sum_value", "treemap_repeated_leaf_average_value"}:
        leaf_labels = sorted({str(leaf.label) for leaf in leaves})
        leaf_label = leaf_labels[abs(int(params.get("_sample_cursor", rng.randrange(len(leaf_labels))))) % len(leaf_labels)]
        matching = tuple(leaf for leaf in leaves if str(leaf.label) == str(leaf_label))
        total = int(sum(int(leaf.value) for leaf in matching))
        if str(query_id) == "treemap_repeated_leaf_average_value":
            if total % len(matching) != 0:
                raise ValueError("treemap repeated leaf average is not an integer")
            answer = int(total // len(matching))
            operation = "average"
        else:
            answer = int(total)
            operation = "sum"
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            evidence_leaf_ids=tuple(str(leaf.leaf_id) for leaf in matching),
            trace={
                "leaf_label": str(leaf_label),
                "leaf_ids": [str(leaf.leaf_id) for leaf in matching],
                "leaf_values": [int(leaf.value) for leaf in matching],
                "operation": str(operation),
                "parent_labels": [str(leaf.parent_label) for leaf in matching],
            },
        )
    raise ValueError(f"unsupported treemap query_id: {query_id}")


def _build_dataset(*, query_id: str, params: Mapping[str, Any], instance_seed: int) -> _Dataset:
    title, parent_axis, leaf_axis, parents, leaves, ranges = _build_tree(params, instance_seed=int(instance_seed))
    query = _build_query(
        query_id=str(query_id),
        parents=parents,
        leaves=leaves,
        params=params,
        instance_seed=int(instance_seed),
    )
    return _Dataset(
        title=str(title),
        parent_axis=str(parent_axis),
        leaf_axis=str(leaf_axis),
        parents=tuple(parents),
        leaves=tuple(leaves),
        query=query,
        generation_ranges=dict(ranges),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    return _RenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1280))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 940))),
        plot_margin_left_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "plot_margin_left_px", 62, instance_seed=int(instance_seed), namespace=TASK_ID)),
        plot_margin_right_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "plot_margin_right_px", 78, instance_seed=int(instance_seed), namespace=TASK_ID)),
        plot_margin_top_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "plot_margin_top_px", 78, instance_seed=int(instance_seed), namespace=TASK_ID)),
        plot_margin_bottom_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "plot_margin_bottom_px", 56, instance_seed=int(instance_seed), namespace=TASK_ID)),
        title_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "title_font_size_px", 26, instance_seed=int(instance_seed), namespace=TASK_ID)),
        parent_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "parent_font_size_px", 18, instance_seed=int(instance_seed), namespace=TASK_ID)),
        leaf_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "leaf_font_size_px", 15, instance_seed=int(instance_seed), namespace=TASK_ID)),
        value_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "value_font_size_px", 16, instance_seed=int(instance_seed), namespace=TASK_ID)),
        note_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "note_font_size_px", 14, instance_seed=int(instance_seed), namespace=TASK_ID)),
        panel_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_fill_rgb", (252, 253, 250), instance_seed=int(instance_seed), namespace=TASK_ID),
        panel_border_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_border_rgb", (44, 50, 60), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_color_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_color_rgb", (26, 31, 38), instance_seed=int(instance_seed), namespace=TASK_ID),
        muted_text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "muted_text_rgb", (78, 86, 98), instance_seed=int(instance_seed), namespace=TASK_ID),
        separator_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "separator_rgb", (246, 248, 250), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        label_stroke_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "label_stroke_width_px", 1, instance_seed=int(instance_seed), namespace=TASK_ID)),
    )


def _slice_rects(
    items: Sequence[Tuple[str, int]],
    rect: Tuple[float, float, float, float],
    *,
    horizontal: bool,
) -> Dict[str, Tuple[float, float, float, float]]:
    total = max(1.0, float(sum(max(0, int(value)) for _, value in items)))
    x0, y0, x1, y1 = (float(value) for value in rect)
    cursor = x0 if horizontal else y0
    rects: Dict[str, Tuple[float, float, float, float]] = {}
    for index, (item_id, value) in enumerate(items):
        share = float(max(0, int(value))) / total
        if horizontal:
            next_cursor = x1 if index == len(items) - 1 else cursor + (x1 - x0) * share
            rects[str(item_id)] = (cursor, y0, next_cursor, y1)
        else:
            next_cursor = y1 if index == len(items) - 1 else cursor + (y1 - y0) * share
            rects[str(item_id)] = (x0, cursor, x1, next_cursor)
        cursor = next_cursor
    return rects


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    *,
    font: ImageFont.ImageFont,
    anchor: str,
    stroke_width: int = 0,
) -> BBox:
    return _bbox(draw.textbbox(xy, str(text), font=font, anchor=anchor, stroke_width=max(0, int(stroke_width))))


def _draw_label_value(
    draw: ImageDraw.ImageDraw,
    rect: Tuple[float, float, float, float],
    *,
    label: str,
    value: int,
    text_color: RGB,
    muted_text: RGB,
    stroke: RGB,
    label_font: ImageFont.ImageFont,
    value_font: ImageFont.ImageFont,
    stroke_width: int,
) -> BBox:
    x0, y0, x1, y1 = rect
    width = max(1.0, float(x1 - x0))
    height = max(1.0, float(y1 - y0))
    max_chars = max(4, int(width // 9))
    label_text = _truncate(str(label), max_chars=max_chars)
    value_text = str(int(value))
    if height >= 54 and width >= 86:
        label_xy = (x0 + 8, y0 + 11)
        draw.text(label_xy, label_text, font=label_font, fill=muted_text, anchor="la", stroke_fill=stroke, stroke_width=max(0, int(stroke_width)))
        value_xy = (x0 + 8, y0 + 33)
        draw.text(value_xy, value_text, font=value_font, fill=text_color, anchor="la", stroke_fill=stroke, stroke_width=max(0, int(stroke_width)))
        return _text_bbox(draw, value_xy, value_text, font=value_font, anchor="la", stroke_width=stroke_width)
    if height >= 28 and width >= 118:
        label_xy = (x0 + 7, (y0 + y1) / 2.0)
        value_xy = (x1 - 7, (y0 + y1) / 2.0)
        draw.text(label_xy, label_text, font=label_font, fill=muted_text, anchor="lm", stroke_fill=stroke, stroke_width=max(0, int(stroke_width)))
        draw.text(value_xy, value_text, font=value_font, fill=text_color, anchor="rm", stroke_fill=stroke, stroke_width=max(0, int(stroke_width)))
        return _text_bbox(draw, value_xy, value_text, font=value_font, anchor="rm", stroke_width=stroke_width)
    value_xy = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
    draw.text(value_xy, value_text, font=value_font, fill=text_color, anchor="mm", stroke_fill=stroke, stroke_width=max(0, int(stroke_width)))
    return _text_bbox(draw, value_xy, value_text, font=value_font, anchor="mm", stroke_width=stroke_width)


def _render_treemap(
    background: Image.Image,
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _RenderedTreemap:
    rp = _render_params(params, instance_seed=int(instance_seed))
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    title_font = _font(rp.title_font_size_px, bold=True)
    parent_font = _font(rp.parent_font_size_px, bold=True)
    leaf_font = _font(rp.leaf_font_size_px)
    value_font = _font(rp.value_font_size_px, bold=True)
    note_font = _font(rp.note_font_size_px)
    chart_bbox = (
        float(rp.plot_margin_left_px),
        float(rp.plot_margin_top_px),
        float(rp.canvas_width - rp.plot_margin_right_px),
        float(rp.canvas_height - rp.plot_margin_bottom_px),
    )
    draw.rounded_rectangle(
        [chart_bbox[0] - 16, chart_bbox[1] - 54, chart_bbox[2] + 16, chart_bbox[3] + 16],
        radius=6,
        fill=rp.panel_fill_rgb,
        outline=_lighten(rp.panel_border_rgb, 0.35),
        width=2,
    )
    draw.text(
        (rp.canvas_width / 2.0, 32),
        str(dataset.title),
        font=title_font,
        fill=rp.text_color_rgb,
        anchor="mm",
        stroke_fill=rp.text_stroke_rgb,
        stroke_width=1,
    )
    draw.text(
        (chart_bbox[0], chart_bbox[1] - 22),
        f"Parent: {dataset.parent_axis}    Child: {dataset.leaf_axis}",
        font=note_font,
        fill=rp.muted_text_rgb,
        anchor="la",
    )
    leaves_by_id = {str(leaf.leaf_id): leaf for leaf in dataset.leaves}
    parent_rects = _slice_rects(
        [(str(parent.parent_id), int(parent.value)) for parent in dataset.parents],
        chart_bbox,
        horizontal=True,
    )
    entities: List[Dict[str, Any]] = []
    parent_traces: List[Dict[str, Any]] = []
    leaf_traces: List[Dict[str, Any]] = []
    evidence_bbox_by_leaf_id: Dict[str, BBox] = {}
    for parent_index, parent in enumerate(dataset.parents):
        px0, py0, px1, py1 = parent_rects[str(parent.parent_id)]
        parent_rect = (px0 + 3, py0 + 3, px1 - 3, py1 - 3)
        draw.rectangle(parent_rect, fill=_lighten(parent.color_rgb, 0.18), outline=rp.panel_border_rgb, width=2)
        header_h = 30
        header_rect = (parent_rect[0], parent_rect[1], parent_rect[2], min(parent_rect[3], parent_rect[1] + header_h))
        draw.rectangle(header_rect, fill=_darken(parent.color_rgb, 0.10), outline=rp.panel_border_rgb, width=1)
        parent_text = _truncate(str(parent.label), max_chars=max(5, int((parent_rect[2] - parent_rect[0]) // 9)))
        draw.text(
            (header_rect[0] + 7, (header_rect[1] + header_rect[3]) / 2.0),
            parent_text,
            font=parent_font,
            fill=(255, 255, 255),
            anchor="lm",
            stroke_fill=_darken(parent.color_rgb, 0.35),
            stroke_width=1,
        )
        leaf_area = (parent_rect[0], header_rect[3], parent_rect[2], parent_rect[3])
        leaf_rects = _slice_rects(
            [(str(leaf_id), int(leaves_by_id[str(leaf_id)].value)) for leaf_id in parent.leaf_ids],
            leaf_area,
            horizontal=False,
        )
        parent_bbox = _bbox(parent_rect)
        entities.append(
            {
                "entity_id": str(parent.parent_id),
                "entity_type": "treemap_parent",
                "label": str(parent.label),
                "bbox_px": list(parent_bbox),
                "value": int(parent.value),
            }
        )
        parent_traces.append(
            {
                "parent_id": str(parent.parent_id),
                "label": str(parent.label),
                "value": int(parent.value),
                "leaf_ids": [str(leaf_id) for leaf_id in parent.leaf_ids],
                "bbox_px": list(parent_bbox),
            }
        )
        for leaf_id in parent.leaf_ids:
            leaf = leaves_by_id[str(leaf_id)]
            lx0, ly0, lx1, ly1 = leaf_rects[str(leaf_id)]
            leaf_rect = (lx0 + 1.5, ly0 + 1.5, lx1 - 1.5, ly1 - 1.5)
            draw.rectangle(
                leaf_rect,
                fill=leaf.color_rgb,
                outline=rp.separator_rgb,
                width=2,
            )
            value_bbox = _draw_label_value(
                draw,
                leaf_rect,
                label=str(leaf.label),
                value=int(leaf.value),
                text_color=rp.text_color_rgb,
                muted_text=rp.muted_text_rgb,
                stroke=rp.text_stroke_rgb,
                label_font=leaf_font,
                value_font=value_font,
                stroke_width=rp.label_stroke_width_px,
            )
            leaf_bbox = _bbox(leaf_rect)
            evidence_bbox_by_leaf_id[str(leaf.leaf_id)] = list(value_bbox)
            entities.append(
                {
                    "entity_id": str(leaf.leaf_id),
                    "entity_type": "treemap_leaf",
                    "label": str(leaf.label),
                    "parent_id": str(leaf.parent_id),
                    "parent_label": str(leaf.parent_label),
                    "bbox_px": list(leaf_bbox),
                    "value_bbox_px": list(value_bbox),
                    "value": int(leaf.value),
                }
            )
            leaf_traces.append(
                {
                    "leaf_id": str(leaf.leaf_id),
                    "parent_id": str(leaf.parent_id),
                    "parent_label": str(leaf.parent_label),
                    "label": str(leaf.label),
                    "value": int(leaf.value),
                    "bbox_px": list(leaf_bbox),
                    "value_bbox_px": list(value_bbox),
                }
            )
    render_meta = {
        "not_to_scale": False,
        "value_source": "printed_leaf_values",
        "layout": "slice_and_dice_treemap",
        "parent_count": int(len(dataset.parents)),
        "leaf_count_per_parent": int(len(dataset.parents[0].leaf_ids)) if dataset.parents else 0,
    }
    return _RenderedTreemap(
        image=image,
        entities=tuple(dict(entity) for entity in entities),
        leaf_traces=tuple(dict(trace) for trace in leaf_traces),
        parent_traces=tuple(dict(trace) for trace in parent_traces),
        evidence_bbox_by_leaf_id=dict(evidence_bbox_by_leaf_id),
        chart_bbox_px=_bbox(chart_bbox),
        render_meta=dict(render_meta),
    )


def _make_prompt(
    *,
    query_id: str,
    prompt_defaults: Mapping[str, Any],
    slots: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any], Dict[str, Any], str]:
    prompt_selection = render_task_prompt_variants(
        domain="charts",
        task_group="composition",
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    artifacts = build_prompt_trace_artifacts(prompt_selection)
    return (
        str(artifacts.prompt),
        dict(artifacts.prompt_variants),
        dict(artifacts.prompt_variant),
        dict(artifacts.prompt_variants_for_trace),
        str(artifacts.prompt_variant_active_key),
    )


def _evidence_hint_key(query_id: str) -> str:
    if str(query_id) in set(GROUP_TOTAL_QUERY_IDS):
        return "evidence_hint_treemap_group_total_value"
    if str(query_id) in set(REPEATED_LEAF_QUERY_IDS):
        return "evidence_hint_treemap_repeated_leaf_aggregate_value"
    raise ValueError(f"unsupported treemap query_id: {query_id}")


def _json_example_key(query_id: str, *, answer_only: bool = False) -> str:
    prefix = "json_example_answer_only" if bool(answer_only) else "json_example"
    if str(query_id) in set(GROUP_TOTAL_QUERY_IDS):
        return f"{prefix}_treemap_group_total_value"
    if str(query_id) in set(REPEATED_LEAF_QUERY_IDS):
        return f"{prefix}_treemap_repeated_leaf_aggregate_value"
    raise ValueError(f"unsupported treemap query_id: {query_id}")


class ChartsCompositionTreemapTask:
    """Generate one treemap composition chart query."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "composition"
    default_dataset_enabled = False
    allowed_query_ids: Tuple[str, ...] = GROUP_TOTAL_QUERY_IDS

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id = _sample_query_id(params, allowed_query_ids=self.allowed_query_ids, instance_seed=int(instance_seed))
        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_treemap",
                "answer_hint_integer",
                "evidence_hint_treemap_group_total_value",
                "evidence_hint_treemap_repeated_leaf_aggregate_value",
                "json_example_treemap_group_total_value",
                "json_example_treemap_repeated_leaf_aggregate_value",
                "json_example_answer_only_treemap_group_total_value",
                "json_example_answer_only_treemap_repeated_leaf_aggregate_value",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1280))),
            canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 940))),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_treemap(background, dataset=dataset, params=params, instance_seed=int(instance_seed))
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        query_trace = dict(dataset.query.trace)
        slots = {
            "object_description": str(prompt_defaults["object_description_treemap"]),
            "parent_label": _quote(str(query_trace.get("parent_label", ""))),
            "leaf_label": _quote(str(query_trace.get("leaf_label", ""))),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(prompt_defaults[_evidence_hint_key(str(query_id))]),
            "answer_hint": str(prompt_defaults["answer_hint_integer"]),
            "json_example": str(prompt_defaults[_json_example_key(str(query_id))]),
            "json_example_answer_only": str(prompt_defaults[_json_example_key(str(query_id), answer_only=True)]),
        }
        prompt, prompt_variants, prompt_variant, prompt_variants_for_trace, active_prompt_key = _make_prompt(
            query_id=str(query_id),
            prompt_defaults=prompt_defaults,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        evidence_bboxes = [
            list(rendered.evidence_bbox_by_leaf_id[str(leaf_id)])
            for leaf_id in dataset.query.evidence_leaf_ids
            if str(leaf_id) in rendered.evidence_bbox_by_leaf_id
        ]
        if not evidence_bboxes:
            raise ValueError("treemap query produced no projected evidence")
        parent_rows = [
            {
                "parent_id": str(parent.parent_id),
                "label": str(parent.label),
                "value": int(parent.value),
                "leaf_ids": [str(leaf_id) for leaf_id in parent.leaf_ids],
            }
            for parent in dataset.parents
        ]
        leaf_rows = [
            {
                "leaf_id": str(leaf.leaf_id),
                "parent_id": str(leaf.parent_id),
                "parent_label": str(leaf.parent_label),
                "label": str(leaf.label),
                "value": int(leaf.value),
            }
            for leaf in dataset.leaves
        ]
        query_params = {
            "query_variant": "default",
            "query_id": str(query_id),
            "query_variant": str(query_id),
            "public_task_id": str(self.task_id),
            "parent_count": int(len(dataset.parents)),
            "leaf_count_per_parent": int(len(dataset.parents[0].leaf_ids)) if dataset.parents else 0,
            "parent_labels": [str(parent.label) for parent in dataset.parents],
            "leaf_labels": sorted({str(leaf.label) for leaf in dataset.leaves}),
            "evidence_leaf_ids": [str(leaf_id) for leaf_id in dataset.query.evidence_leaf_ids],
            "answer_value": int(dataset.query.answer),
            **dict(dataset.generation_ranges),
            **dict(query_trace),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_treemap_composition",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": dict(query_params),
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(query_id),
                "query_variant": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_variant),
                "prompt_variant_active_key": str(active_prompt_key),
                "prompt_variants": dict(prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "coord_space": "pixel",
                "scene_variant": "treemap_composition",
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "chart_bbox_px": list(rendered.chart_bbox_px),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "chart_bbox_px": list(rendered.chart_bbox_px),
                "parent_traces": [dict(trace) for trace in rendered.parent_traces],
                "leaf_traces": [dict(trace) for trace in rendered.leaf_traces],
                "evidence_bbox_by_leaf_id": {
                    str(leaf_id): list(bbox)
                    for leaf_id, bbox in rendered.evidence_bbox_by_leaf_id.items()
                },
            },
            "execution_trace": {
                "query_variant": "default",
                "query_id": str(query_id),
                "query_variant": str(query_id),
                "answer_value": int(dataset.query.answer),
                "question_format": "numeric_open",
                "parents": list(parent_rows),
                "leaves": list(leaf_rows),
                "evidence_leaf_ids": [str(leaf_id) for leaf_id in dataset.query.evidence_leaf_ids],
                **dict(query_params),
            },
            "witness_symbolic": {
                "type": "treemap_composition_values",
                "query_id": str(query_id),
                "answer_value": int(dataset.query.answer),
                "evidence_leaf_ids": [str(leaf_id) for leaf_id in dataset.query.evidence_leaf_ids],
                "calculation": dict(query_trace),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                "evidence_leaf_ids": [str(leaf_id) for leaf_id in dataset.query.evidence_leaf_ids],
            },
        }
        max_leaf_count = int(dataset.generation_ranges["parent_count_range"][1]) * int(dataset.generation_ranges["leaf_count_range"][1])
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(len(dataset.leaves)), (1, max(1, int(max_leaf_count)))),
                "reasoning_load": float(_QUERY_REASONING_LOAD[str(query_id)]),
                "scene_variant_load": 0.66,
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=TypedValue(type="integer", value=int(dataset.query.answer)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_bboxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        attempts = max(1, int(max_attempts))
        last_error: Exception | None = None
        for attempt in range(attempts):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.treemap.retry", int(attempt)))
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


@register_task
class ChartsCompositionTreemapGroupTotalValueTask(ChartsCompositionTreemapTask):
    """Compute a parent-group total from child rectangle values in a treemap."""

    task_id = "task_charts__treemap__group_total_value"
    allowed_query_ids = GROUP_TOTAL_QUERY_IDS
    default_dataset_enabled = True


@register_task
class ChartsCompositionTreemapRepeatedLeafAggregateValueTask(ChartsCompositionTreemapTask):
    """Aggregate a repeated child label across parent groups."""

    task_id = "task_charts__treemap__repeated_leaf_aggregate_value"
    allowed_query_ids = REPEATED_LEAF_QUERY_IDS
    default_dataset_enabled = True
