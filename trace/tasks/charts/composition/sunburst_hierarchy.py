"""Sunburst hierarchy chart tasks."""

from __future__ import annotations

import colorsys
import math
from collections import defaultdict
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


TASK_ID = "charts_composition_sunburst_hierarchy_base"
SCENE_ID = "sunburst"

PARENT_TOTAL_QUERY_IDS: Tuple[str, ...] = ("parent_total_from_leaves_value",)
PARENT_EXTREMUM_QUERY_IDS: Tuple[str, ...] = (
    "highest_parent_total_label",
    "lowest_parent_total_label",
)
CONDITIONAL_LEAF_QUERY_IDS: Tuple[str, ...] = (
    "leaf_threshold_count_under_parent",
    "leaf_range_count_under_parent",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    PARENT_TOTAL_QUERY_IDS + PARENT_EXTREMUM_QUERY_IDS + CONDITIONAL_LEAF_QUERY_IDS
)

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
    "parent_total_from_leaves_value": 0.70,
    "highest_parent_total_label": 0.78,
    "lowest_parent_total_label": 0.78,
    "leaf_threshold_count_under_parent": 0.68,
    "leaf_range_count_under_parent": 0.72,
}

_THEMES: Tuple[Dict[str, Any], ...] = (
    {
        "parent": "Healthcare",
        "subgroups": {
            "Clinics": ("Mobile", "Rural", "Urgent", "Remote"),
            "Telehealth": ("Video", "Phone", "Portal", "Nurse"),
            "Outreach": ("Home", "Wellness", "Screening", "Transit"),
        },
    },
    {
        "parent": "Transport",
        "subgroups": {
            "Shuttles": ("North", "South", "Evening", "Market"),
            "Rides": ("Medical", "Senior", "Rural", "Weekend"),
            "Drivers": ("Volunteer", "Taxi", "Van", "Rapid"),
        },
    },
    {
        "parent": "Commercial",
        "subgroups": {
            "Cafes": ("Olde", "Market", "Roaster", "Corner"),
            "Markets": ("Farmers", "Craft", "Night", "River"),
            "Retail": ("Books", "Gallery", "Florist", "Depot"),
        },
    },
    {
        "parent": "Historical",
        "subgroups": {
            "War": ("Square", "Marker", "Memorial", "Trail"),
            "Colonial": ("Hall", "Church", "Mansion", "Bridge"),
            "Industry": ("Mill", "Forge", "Depot", "Canal"),
        },
    },
    {
        "parent": "Athletics",
        "subgroups": {
            "Medals": ("Gold", "Silver", "Bronze", "Podium"),
            "Teams": ("National", "Youth", "Club", "League"),
            "Events": ("Track", "Judo", "Table", "Swimming"),
        },
    },
    {
        "parent": "Culture",
        "subgroups": {
            "Museums": ("Local", "Art", "History", "Science"),
            "Music": ("Jazz", "Pop", "Classic", "Folk"),
            "Festivals": ("Spring", "Summer", "Autumn", "Winter"),
        },
    },
    {
        "parent": "Natural",
        "subgroups": {
            "Parks": ("Riverside", "Founders", "Hill", "Lake"),
            "Trails": ("Ridge", "Creek", "Forest", "Valley"),
            "Views": ("Lookout", "Garden", "Harbor", "Sunset"),
        },
    },
    {
        "parent": "Education",
        "subgroups": {
            "Schools": ("Primary", "Middle", "High", "Adult"),
            "Libraries": ("Central", "Branch", "Mobile", "Digital"),
            "Training": ("Career", "STEM", "Language", "Arts"),
        },
    },
)


@dataclass(frozen=True)
class _Node:
    node_id: str
    label: str
    level: str
    parent_id: str | None
    value: int
    child_ids: Tuple[str, ...]
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    evidence_node_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    nodes: Tuple[_Node, ...]
    root_id: str
    parent_ids: Tuple[str, ...]
    subgroup_ids: Tuple[str, ...]
    leaf_ids: Tuple[str, ...]
    query: _Query
    generation_ranges: Dict[str, Any]


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    center_x_px: int
    center_y_px: int
    inner_radius_px: int
    parent_outer_radius_px: int
    subgroup_outer_radius_px: int
    leaf_outer_radius_px: int
    title_font_size_px: int
    parent_font_size_px: int
    subgroup_font_size_px: int
    leaf_font_size_px: int
    value_font_size_px: int
    note_font_size_px: int
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    plot_fill_rgb: RGB
    text_color_rgb: RGB
    muted_text_rgb: RGB
    separator_rgb: RGB
    text_stroke_rgb: RGB
    label_stroke_width_px: int


@dataclass(frozen=True)
class _RenderedSunburst:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    node_traces: Tuple[Dict[str, Any], ...]
    evidence_bbox_by_node_id: Dict[str, BBox]
    chart_bbox_px: BBox
    render_meta: Dict[str, Any]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _lighten(color: RGB, amount: float) -> RGB:
    return tuple(
        max(0, min(255, int(round(float(channel) + (255.0 - float(channel)) * float(amount)))))
        for channel in color
    )


def _darken(color: RGB, amount: float) -> RGB:
    return tuple(max(0, min(255, int(round(float(channel) * (1.0 - float(amount)))))) for channel in color)


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    return load_font(max(8, int(size)), bold=bool(bold))


def _draw_multiline_centered_text(
    draw: ImageDraw.ImageDraw,
    center: Tuple[float, float],
    lines: Sequence[str],
    *,
    font: ImageFont.ImageFont,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int,
    line_gap_px: int = 2,
) -> BBox:
    clean_lines = [str(line) for line in lines if str(line)]
    if not clean_lines:
        return [float(center[0]), float(center[1]), float(center[0]), float(center[1])]
    line_boxes = [draw.textbbox((0, 0), line, font=font, stroke_width=max(0, int(stroke_width))) for line in clean_lines]
    heights = [float(box[3] - box[1]) for box in line_boxes]
    total_h = sum(heights) + max(0, len(clean_lines) - 1) * int(line_gap_px)
    y = float(center[1]) - total_h / 2.0
    boxes: List[BBox] = []
    for line, height in zip(clean_lines, heights):
        xy = (float(center[0]), float(y + height / 2.0))
        draw.text(
            xy,
            line,
            font=font,
            fill=fill,
            anchor="mm",
            stroke_fill=stroke_fill,
            stroke_width=max(0, int(stroke_width)),
        )
        boxes.append(
            _bbox(draw.textbbox(xy, line, font=font, anchor="mm", stroke_width=max(0, int(stroke_width))))
        )
        y += float(height) + int(line_gap_px)
    return _bbox_union(boxes)


def _truncate_label(label: str, *, max_chars: int) -> str:
    text = str(label)
    if len(text) <= int(max_chars):
        return text
    return text[: max(1, int(max_chars) - 1)] + "."


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1400)))
    canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 1180)))
    base_center_x = int(params.get("center_x_px", group_default(_RENDER_DEFAULTS, "center_x_px", canvas_width // 2)))
    base_center_y = int(params.get("center_y_px", group_default(_RENDER_DEFAULTS, "center_y_px", canvas_height // 2 + 18)))
    center_x = base_center_x + int(
        resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            "center_x_jitter_px",
            0,
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
        )
    )
    center_y = base_center_y + int(
        resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            "center_y_jitter_px",
            0,
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
        )
    )
    return _RenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        center_x_px=int(center_x),
        center_y_px=int(center_y),
        inner_radius_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "inner_radius_px", 112, instance_seed=int(instance_seed), namespace=TASK_ID)),
        parent_outer_radius_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "parent_outer_radius_px", 246, instance_seed=int(instance_seed), namespace=TASK_ID)),
        subgroup_outer_radius_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "subgroup_outer_radius_px", 380, instance_seed=int(instance_seed), namespace=TASK_ID)),
        leaf_outer_radius_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "leaf_outer_radius_px", 526, instance_seed=int(instance_seed), namespace=TASK_ID)),
        title_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "title_font_size_px", 28, instance_seed=int(instance_seed), namespace=TASK_ID)),
        parent_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "parent_font_size_px", 18, instance_seed=int(instance_seed), namespace=TASK_ID)),
        subgroup_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "subgroup_font_size_px", 16, instance_seed=int(instance_seed), namespace=TASK_ID)),
        leaf_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "leaf_font_size_px", 14, instance_seed=int(instance_seed), namespace=TASK_ID)),
        value_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "value_font_size_px", 15, instance_seed=int(instance_seed), namespace=TASK_ID)),
        note_font_size_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "note_font_size_px", 15, instance_seed=int(instance_seed), namespace=TASK_ID)),
        panel_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_fill_rgb", (252, 253, 250), instance_seed=int(instance_seed), namespace=TASK_ID),
        panel_border_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_border_rgb", (198, 204, 210), instance_seed=int(instance_seed), namespace=TASK_ID),
        plot_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "plot_fill_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_color_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_color_rgb", (32, 37, 44), instance_seed=int(instance_seed), namespace=TASK_ID),
        muted_text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "muted_text_rgb", (88, 95, 106), instance_seed=int(instance_seed), namespace=TASK_ID),
        separator_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "separator_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        label_stroke_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "label_stroke_width_px", 1, instance_seed=int(instance_seed), namespace=TASK_ID)),
    )


def _sample_query_id(params: Mapping[str, Any], *, allowed_query_ids: Sequence[str], instance_seed: int) -> str:
    allowed = tuple(str(item) for item in allowed_query_ids)
    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in set(allowed):
            raise ValueError(f"unsupported sunburst query_id for this public task: {query_id}")
        return query_id
    rng = spawn_rng(int(instance_seed), "charts.composition.sunburst.query_id")
    raw_weights = params.get("query_id_weights", params.get("query_id_weights"))
    if isinstance(raw_weights, Mapping):
        weights = [max(0.0, float(raw_weights.get(query_id, 0.0))) for query_id in allowed]
        if sum(weights) > 0.0:
            threshold = rng.random() * sum(weights)
            cumulative = 0.0
            for query_id, weight in zip(allowed, weights):
                cumulative += float(weight)
                if threshold <= cumulative:
                    return str(query_id)
    return str(allowed[int(rng.randrange(len(allowed)))])


def _sample_parent_themes(*, count: int, instance_seed: int) -> Tuple[Dict[str, Any], ...]:
    rng = spawn_rng(int(instance_seed), "charts.composition.sunburst.themes")
    themes = list(_THEMES)
    rng.shuffle(themes)
    if int(count) > len(themes):
        raise ValueError("sunburst parent_count exceeds theme pool")
    return tuple(dict(theme) for theme in themes[: int(count)])


def _parent_color(index: int, count: int, *, instance_seed: int) -> RGB:
    rng = spawn_rng(int(instance_seed), "charts.composition.sunburst.palette")
    offset = rng.random()
    hue = (float(offset) + float(index) / max(1.0, float(count))) % 1.0
    sat = 0.48 + 0.14 * rng.random()
    val = 0.76 + 0.12 * rng.random()
    r, g, b = colorsys.hsv_to_rgb(float(hue), float(sat), float(val))
    return int(r * 255), int(g * 255), int(b * 255)


def _resolve_count_range(
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


def _int_sequence_default(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), list(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return tuple(int(value) for value in fallback)
    values = tuple(int(value) for value in raw)
    return values if values else tuple(int(value) for value in fallback)


def _ordered_count_support(
    count_support: Sequence[int],
    *,
    params: Mapping[str, Any],
    rng: Any,
) -> List[int]:
    support = [int(value) for value in count_support]
    if not support:
        return []
    if params.get("_sample_cursor") is not None:
        target = support[abs(int(params["_sample_cursor"])) % len(support)]
        return [int(target)] + [int(value) for value in support if int(value) != int(target)]
    rng.shuffle(support)
    return list(support)


def _build_tree(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[Tuple[_Node, ...], Dict[str, Any]]:
    parent_min, parent_max = _resolve_count_range(
        params,
        min_key="sunburst_parent_count_min",
        max_key="sunburst_parent_count_max",
        fallback_min=4,
        fallback_max=5,
    )
    subgroup_min, subgroup_max = _resolve_count_range(
        params,
        min_key="sunburst_subgroup_count_min",
        max_key="sunburst_subgroup_count_max",
        fallback_min=2,
        fallback_max=3,
    )
    leaf_min, leaf_max = _resolve_count_range(
        params,
        min_key="sunburst_leaf_count_min",
        max_key="sunburst_leaf_count_max",
        fallback_min=1,
        fallback_max=2,
    )
    value_min, value_max = _resolve_count_range(
        params,
        min_key="sunburst_leaf_value_min",
        max_key="sunburst_leaf_value_max",
        fallback_min=5,
        fallback_max=40,
    )
    value_step = max(1, int(params.get("sunburst_leaf_value_step", group_default(_GEN_DEFAULTS, "sunburst_leaf_value_step", 5))))
    rng = spawn_rng(int(instance_seed), "charts.composition.sunburst.tree")
    parent_count = int(rng.randint(int(parent_min), int(parent_max)))
    themes = _sample_parent_themes(count=int(parent_count), instance_seed=int(instance_seed))

    nodes: Dict[str, _Node] = {}
    parent_ids: List[str] = []
    subgroup_ids: List[str] = []
    leaf_ids: List[str] = []
    leaf_value_low = int(math.ceil(int(value_min) / int(value_step)))
    leaf_value_high = int(math.floor(int(value_max) / int(value_step)))
    if leaf_value_low > leaf_value_high:
        raise ValueError("sunburst leaf value range is incompatible with value step")

    for parent_index, theme in enumerate(themes):
        parent_id = f"parent_{parent_index}"
        parent_ids.append(parent_id)
        parent_color = _parent_color(parent_index, parent_count, instance_seed=int(instance_seed))
        raw_subgroups = list(dict(theme["subgroups"]).items())
        rng.shuffle(raw_subgroups)
        subgroup_count = int(rng.randint(int(subgroup_min), min(int(subgroup_max), len(raw_subgroups))))
        value_units = list(range(int(leaf_value_low), int(leaf_value_high) + 1))
        rng.shuffle(value_units)
        parent_child_ids: List[str] = []
        parent_value = 0
        for subgroup_index, (subgroup_label, leaf_pool) in enumerate(raw_subgroups[:subgroup_count]):
            subgroup_id = f"{parent_id}_subgroup_{subgroup_index}"
            subgroup_ids.append(subgroup_id)
            parent_child_ids.append(subgroup_id)
            leaf_labels = [str(item) for item in leaf_pool]
            rng.shuffle(leaf_labels)
            leaf_count = int(rng.randint(int(leaf_min), min(int(leaf_max), len(leaf_labels))))
            subgroup_child_ids: List[str] = []
            subgroup_value = 0
            for leaf_index, leaf_label in enumerate(leaf_labels[:leaf_count]):
                leaf_id = f"{subgroup_id}_leaf_{leaf_index}"
                if value_units:
                    value_unit = int(value_units.pop())
                else:
                    value_unit = int(rng.randint(leaf_value_low, leaf_value_high))
                value = int(value_unit * int(value_step))
                leaf_ids.append(leaf_id)
                subgroup_child_ids.append(leaf_id)
                subgroup_value += int(value)
                nodes[leaf_id] = _Node(
                    node_id=leaf_id,
                    label=str(leaf_label),
                    level="leaf",
                    parent_id=subgroup_id,
                    value=int(value),
                    child_ids=(),
                    color_rgb=_lighten(parent_color, 0.20 + 0.08 * (leaf_index % 3)),
                )
            parent_value += int(subgroup_value)
            nodes[subgroup_id] = _Node(
                node_id=subgroup_id,
                label=str(subgroup_label),
                level="subgroup",
                parent_id=parent_id,
                value=int(subgroup_value),
                child_ids=tuple(subgroup_child_ids),
                color_rgb=_lighten(parent_color, 0.08),
            )
        nodes[parent_id] = _Node(
            node_id=parent_id,
            label=str(theme["parent"]),
            level="parent",
            parent_id="root",
            value=int(parent_value),
            child_ids=tuple(parent_child_ids),
            color_rgb=parent_color,
        )

    root_value = int(sum(int(nodes[parent_id].value) for parent_id in parent_ids))
    nodes["root"] = _Node(
        node_id="root",
        label="Total",
        level="root",
        parent_id=None,
        value=int(root_value),
        child_ids=tuple(parent_ids),
        color_rgb=(224, 232, 190),
    )
    ordered_nodes = [nodes["root"]]
    for parent_id in parent_ids:
        ordered_nodes.append(nodes[parent_id])
        for subgroup_id in nodes[parent_id].child_ids:
            ordered_nodes.append(nodes[subgroup_id])
            for leaf_id in nodes[subgroup_id].child_ids:
                ordered_nodes.append(nodes[leaf_id])

    ranges = {
        "parent_count_range": [int(parent_min), int(parent_max)],
        "subgroup_count_range": [int(subgroup_min), int(subgroup_max)],
        "leaf_count_range": [int(leaf_min), int(leaf_max)],
        "leaf_value_range": [int(value_min), int(value_max)],
        "leaf_value_step": int(value_step),
    }
    return tuple(ordered_nodes), dict(ranges)


def _descendant_leaf_ids(nodes_by_id: Mapping[str, _Node], node_id: str) -> Tuple[str, ...]:
    node = nodes_by_id[str(node_id)]
    if node.level == "leaf":
        return (str(node_id),)
    leaves: List[str] = []
    for child_id in node.child_ids:
        leaves.extend(_descendant_leaf_ids(nodes_by_id, str(child_id)))
    return tuple(leaves)


def _select_threshold_query(
    *,
    nodes_by_id: Mapping[str, _Node],
    parent_ids: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, int, int, Tuple[str, ...]]:
    rng = spawn_rng(int(instance_seed), "charts.composition.sunburst.threshold_query")
    count_support = [int(value) for value in _int_sequence_default(params, "sunburst_condition_count_support", (1, 2, 3, 4, 5))]
    ordered_counts = _ordered_count_support(count_support, params=params, rng=rng)
    parent_order = list(str(parent_id) for parent_id in parent_ids)
    rng.shuffle(parent_order)
    comparison_options = [("at least", True), ("below", False)]
    rng.shuffle(comparison_options)
    for parent_id in parent_order:
        leaf_ids = _descendant_leaf_ids(nodes_by_id, str(parent_id))
        values = [int(nodes_by_id[leaf_id].value) for leaf_id in leaf_ids]
        if len(values) < 3:
            continue
        for phrase, at_least in comparison_options:
            candidates_by_count: Dict[int, List[int]] = defaultdict(list)
            for threshold in range(min(values), max(values) + 1):
                if bool(at_least):
                    count = sum(1 for value in values if int(value) >= int(threshold))
                else:
                    count = sum(1 for value in values if int(value) < int(threshold))
                if 1 <= int(count) <= len(values) - 1:
                    candidates_by_count[int(count)].append(int(threshold))
            available_counts = [count for count in ordered_counts if count in candidates_by_count]
            if not available_counts:
                continue
            answer = int(available_counts[0])
            thresholds = candidates_by_count[int(answer)]
            threshold = int(thresholds[int(rng.randrange(len(thresholds)))])
            return str(parent_id), str(phrase), int(threshold), tuple(leaf_ids)  # type: ignore[return-value]
    raise ValueError("unable to build nontrivial sunburst threshold count query")


def _select_range_query(
    *,
    nodes_by_id: Mapping[str, _Node],
    parent_ids: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, int, int, int, Tuple[str, ...]]:
    rng = spawn_rng(int(instance_seed), "charts.composition.sunburst.range_query")
    count_support = [int(value) for value in _int_sequence_default(params, "sunburst_condition_count_support", (1, 2, 3, 4, 5))]
    ordered_counts = _ordered_count_support(count_support, params=params, rng=rng)
    parent_order = list(str(parent_id) for parent_id in parent_ids)
    rng.shuffle(parent_order)
    for parent_id in parent_order:
        leaf_ids = _descendant_leaf_ids(nodes_by_id, str(parent_id))
        values = sorted(int(nodes_by_id[leaf_id].value) for leaf_id in leaf_ids)
        unique_values = sorted(set(values))
        if len(unique_values) < 3:
            continue
        candidates_by_count: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
        for low_index, low in enumerate(unique_values):
            for high in unique_values[low_index:]:
                count = sum(1 for value in values if int(low) <= int(value) <= int(high))
                if 1 <= int(count) <= len(values) - 1:
                    candidates_by_count[int(count)].append((int(low), int(high)))
        available_counts = [count for count in ordered_counts if count in candidates_by_count]
        if not available_counts:
            continue
        answer = int(available_counts[0])
        ranges = candidates_by_count[int(answer)]
        lower, upper = ranges[int(rng.randrange(len(ranges)))]
        return str(parent_id), int(lower), int(upper), int(answer), tuple(leaf_ids)
    raise ValueError("unable to build nontrivial sunburst range count query")


def _build_query(
    *,
    query_id: str,
    nodes_by_id: Mapping[str, _Node],
    parent_ids: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Query:
    rng = spawn_rng(int(instance_seed), f"charts.composition.sunburst.query.{query_id}")
    parent_nodes = [nodes_by_id[str(parent_id)] for parent_id in parent_ids]
    parent_totals = {str(node.node_id): int(node.value) for node in parent_nodes}

    if str(query_id) == "parent_total_from_leaves_value":
        parent = parent_nodes[int(rng.randrange(len(parent_nodes)))]
        leaf_ids = _descendant_leaf_ids(nodes_by_id, str(parent.node_id))
        return _Query(
            query_id=str(query_id),
            answer=int(parent.value),
            answer_type="integer",
            evidence_node_ids=tuple(leaf_ids),
            trace={
                "parent_id": str(parent.node_id),
                "parent_label": str(parent.label),
                "parent_total": int(parent.value),
                "leaf_ids": [str(leaf_id) for leaf_id in leaf_ids],
                "leaf_values": [int(nodes_by_id[str(leaf_id)].value) for leaf_id in leaf_ids],
            },
        )

    if str(query_id) in {"highest_parent_total_label", "lowest_parent_total_label"}:
        totals = list(parent_totals.values())
        if len(set(totals)) != len(totals):
            raise ValueError("sunburst parent totals must be unique for extremum query")
        want_highest = str(query_id) == "highest_parent_total_label"
        target = max(parent_nodes, key=lambda node: int(node.value)) if want_highest else min(parent_nodes, key=lambda node: int(node.value))
        target_leaf_ids = _descendant_leaf_ids(nodes_by_id, str(target.node_id))
        all_leaf_ids: List[str] = []
        for parent_id in parent_ids:
            all_leaf_ids.extend(_descendant_leaf_ids(nodes_by_id, str(parent_id)))
        return _Query(
            query_id=str(query_id),
            answer=str(target.label),
            answer_type="string",
            evidence_node_ids=tuple(target_leaf_ids),
            trace={
                "extremum": "highest" if want_highest else "lowest",
                "answer_parent_id": str(target.node_id),
                "answer_parent_label": str(target.label),
                "parent_totals": {str(nodes_by_id[parent_id].label): int(nodes_by_id[parent_id].value) for parent_id in parent_ids},
                "answer_leaf_ids": [str(leaf_id) for leaf_id in target_leaf_ids],
                "leaf_ids": [str(leaf_id) for leaf_id in all_leaf_ids],
            },
        )

    if str(query_id) == "leaf_threshold_count_under_parent":
        parent_id, comparison_phrase, threshold, leaf_ids = _select_threshold_query(
            nodes_by_id=nodes_by_id,
            parent_ids=parent_ids,
            params=params,
            instance_seed=int(instance_seed),
        )
        values = [int(nodes_by_id[str(leaf_id)].value) for leaf_id in leaf_ids]
        if str(comparison_phrase) == "at least":
            answer = sum(1 for value in values if int(value) >= int(threshold))
        else:
            answer = sum(1 for value in values if int(value) < int(threshold))
        parent = nodes_by_id[str(parent_id)]
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            answer_type="integer",
            evidence_node_ids=tuple(str(leaf_id) for leaf_id in leaf_ids),
            trace={
                "parent_id": str(parent.node_id),
                "parent_label": str(parent.label),
                "comparison_phrase": str(comparison_phrase),
                "threshold_value": int(threshold),
                "leaf_ids": [str(leaf_id) for leaf_id in leaf_ids],
                "leaf_values": values,
            },
        )

    if str(query_id) == "leaf_range_count_under_parent":
        parent_id, lower, upper, answer, leaf_ids = _select_range_query(
            nodes_by_id=nodes_by_id,
            parent_ids=parent_ids,
            params=params,
            instance_seed=int(instance_seed),
        )
        parent = nodes_by_id[str(parent_id)]
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            answer_type="integer",
            evidence_node_ids=tuple(str(leaf_id) for leaf_id in leaf_ids),
            trace={
                "parent_id": str(parent.node_id),
                "parent_label": str(parent.label),
                "lower_value": int(lower),
                "upper_value": int(upper),
                "leaf_ids": [str(leaf_id) for leaf_id in leaf_ids],
                "leaf_values": [int(nodes_by_id[str(leaf_id)].value) for leaf_id in leaf_ids],
            },
        )

    raise ValueError(f"unsupported sunburst query_id: {query_id}")


def _build_dataset(*, query_id: str, params: Mapping[str, Any], instance_seed: int) -> _Dataset:
    nodes, ranges = _build_tree(params, instance_seed=int(instance_seed))
    nodes_by_id = {str(node.node_id): node for node in nodes}
    root = nodes_by_id["root"]
    parent_ids = tuple(str(child_id) for child_id in root.child_ids)
    subgroup_ids = tuple(str(node.node_id) for node in nodes if node.level == "subgroup")
    leaf_ids = tuple(str(node.node_id) for node in nodes if node.level == "leaf")
    query = _build_query(
        query_id=str(query_id),
        nodes_by_id=nodes_by_id,
        parent_ids=parent_ids,
        params=params,
        instance_seed=int(instance_seed),
    )
    return _Dataset(
        nodes=tuple(nodes),
        root_id="root",
        parent_ids=tuple(parent_ids),
        subgroup_ids=tuple(subgroup_ids),
        leaf_ids=tuple(leaf_ids),
        query=query,
        generation_ranges=dict(ranges),
    )


def _node_angle_spans(dataset: _Dataset) -> Dict[str, Tuple[float, float]]:
    nodes_by_id = {str(node.node_id): node for node in dataset.nodes}
    spans: Dict[str, Tuple[float, float]] = {"root": (0.0, 360.0)}
    cursor = -90.0
    total_leaf_count = max(1, len(dataset.leaf_ids))
    degrees_per_leaf = 360.0 / float(total_leaf_count)
    for parent_id in dataset.parent_ids:
        parent_leaf_count = len(_descendant_leaf_ids(nodes_by_id, parent_id))
        parent_start = cursor
        parent_end = parent_start + float(parent_leaf_count) * float(degrees_per_leaf)
        spans[parent_id] = (float(parent_start), float(parent_end))
        sub_cursor = float(parent_start)
        for subgroup_id in nodes_by_id[parent_id].child_ids:
            subgroup_leaf_count = len(_descendant_leaf_ids(nodes_by_id, subgroup_id))
            subgroup_start = sub_cursor
            subgroup_end = subgroup_start + float(subgroup_leaf_count) * float(degrees_per_leaf)
            spans[str(subgroup_id)] = (float(subgroup_start), float(subgroup_end))
            leaf_cursor = float(subgroup_start)
            for leaf_id in nodes_by_id[str(subgroup_id)].child_ids:
                spans[str(leaf_id)] = (float(leaf_cursor), float(leaf_cursor + degrees_per_leaf))
                leaf_cursor += float(degrees_per_leaf)
            sub_cursor = float(subgroup_end)
        cursor = float(parent_end)
    return spans


def _ring_for_level(render_params: _RenderParams, level: str) -> Tuple[int, int]:
    if str(level) == "parent":
        return int(render_params.inner_radius_px), int(render_params.parent_outer_radius_px)
    if str(level) == "subgroup":
        return int(render_params.parent_outer_radius_px), int(render_params.subgroup_outer_radius_px)
    if str(level) == "leaf":
        return int(render_params.subgroup_outer_radius_px), int(render_params.leaf_outer_radius_px)
    return 0, int(render_params.inner_radius_px)


def _draw_ring_wedge(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    inner_radius: int,
    outer_radius: int,
    start_angle: float,
    end_angle: float,
    fill: RGB,
    hole_fill: RGB,
    outline: RGB,
) -> None:
    cx, cy = float(center[0]), float(center[1])
    outer_box = (cx - outer_radius, cy - outer_radius, cx + outer_radius, cy + outer_radius)
    inner_box = (cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius)
    draw.pieslice(outer_box, start=float(start_angle), end=float(end_angle), fill=fill, outline=outline, width=2)
    if int(inner_radius) > 0:
        draw.pieslice(inner_box, start=float(start_angle), end=float(end_angle), fill=hole_fill)


def _label_center(
    *,
    center: Tuple[float, float],
    inner_radius: int,
    outer_radius: int,
    start_angle: float,
    end_angle: float,
) -> Tuple[float, float]:
    angle = math.radians((float(start_angle) + float(end_angle)) / 2.0)
    radius = (float(inner_radius) + float(outer_radius)) / 2.0
    return float(center[0]) + math.cos(angle) * radius, float(center[1]) + math.sin(angle) * radius


def _render_sunburst(
    background: Image.Image,
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _RenderedSunburst:
    render_params = _render_params(params, instance_seed=int(instance_seed))
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    center = (float(render_params.center_x_px), float(render_params.center_y_px))
    chart_bbox = _bbox(
        (
            center[0] - render_params.leaf_outer_radius_px,
            center[1] - render_params.leaf_outer_radius_px,
            center[0] + render_params.leaf_outer_radius_px,
            center[1] + render_params.leaf_outer_radius_px,
        )
    )
    panel_pad = 34
    panel_bbox = [
        chart_bbox[0] - panel_pad,
        chart_bbox[1] - panel_pad,
        chart_bbox[2] + panel_pad,
        chart_bbox[3] + panel_pad,
    ]
    draw.rounded_rectangle(
        panel_bbox,
        radius=8,
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=2,
    )

    title_font = _font(render_params.title_font_size_px, bold=True)
    parent_font = _font(render_params.parent_font_size_px, bold=True)
    subgroup_font = _font(render_params.subgroup_font_size_px, bold=True)
    leaf_font = _font(render_params.leaf_font_size_px, bold=True)
    value_font = _font(render_params.value_font_size_px, bold=True)
    note_font = _font(render_params.note_font_size_px, bold=False)

    draw.text(
        (float(panel_bbox[0] + 26), float(panel_bbox[1] + 18)),
        "Concentric Hierarchy Chart",
        font=title_font,
        fill=render_params.text_color_rgb,
    )
    draw.text(
        (float(panel_bbox[0] + 28), float(panel_bbox[3] - 30)),
        "Ring sizes show hierarchy; use printed outer values for calculations.",
        font=note_font,
        fill=render_params.muted_text_rgb,
    )

    nodes_by_id = {str(node.node_id): node for node in dataset.nodes}
    spans = _node_angle_spans(dataset)
    node_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    evidence_bbox_by_node_id: Dict[str, BBox] = {}

    for level in ("leaf", "subgroup", "parent"):
        for node in [item for item in dataset.nodes if item.level == level]:
            start, end = spans[str(node.node_id)]
            inner_radius, outer_radius = _ring_for_level(render_params, str(level))
            fill = tuple(int(channel) for channel in node.color_rgb)
            if str(level) == "subgroup":
                fill = _lighten(fill, 0.10)
            elif str(level) == "leaf":
                fill = _lighten(fill, 0.18)
            _draw_ring_wedge(
                draw,
                center=center,
                inner_radius=int(inner_radius),
                outer_radius=int(outer_radius),
                start_angle=float(start),
                end_angle=float(end),
                fill=fill,
                hole_fill=render_params.plot_fill_rgb,
                outline=render_params.separator_rgb,
            )

    draw.ellipse(
        (
            center[0] - render_params.inner_radius_px,
            center[1] - render_params.inner_radius_px,
            center[0] + render_params.inner_radius_px,
            center[1] + render_params.inner_radius_px,
        ),
        fill=_lighten(nodes_by_id["root"].color_rgb, 0.30),
        outline=render_params.separator_rgb,
        width=2,
    )
    _draw_multiline_centered_text(
        draw,
        center,
        ["Hierarchy", "not to scale"],
        font=parent_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
        line_gap_px=4,
    )

    for node in dataset.nodes:
        if node.level == "root":
            continue
        start, end = spans[str(node.node_id)]
        inner_radius, outer_radius = _ring_for_level(render_params, str(node.level))
        label_xy = _label_center(
            center=center,
            inner_radius=int(inner_radius),
            outer_radius=int(outer_radius),
            start_angle=float(start),
            end_angle=float(end),
        )
        sweep = abs(float(end) - float(start))
        if node.level == "parent":
            label_lines = [_truncate_label(node.label, max_chars=14)]
            font = parent_font
            stroke_width = int(render_params.label_stroke_width_px)
        elif node.level == "subgroup":
            label_lines = [_truncate_label(node.label, max_chars=13)]
            font = subgroup_font
            stroke_width = int(render_params.label_stroke_width_px)
        else:
            label_lines = [_truncate_label(node.label, max_chars=12), str(int(node.value))]
            font = leaf_font if sweep >= 16.0 else value_font
            stroke_width = int(render_params.label_stroke_width_px)
        text_bbox = _draw_multiline_centered_text(
            draw,
            label_xy,
            label_lines,
            font=font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=stroke_width,
            line_gap_px=2,
        )
        evidence_bbox_by_node_id[str(node.node_id)] = list(text_bbox)
        wedge_bbox = _bbox(
            (
                center[0] - outer_radius,
                center[1] - outer_radius,
                center[0] + outer_radius,
                center[1] + outer_radius,
            )
        )
        trace = {
            "node_id": str(node.node_id),
            "entity_id": str(node.node_id),
            "label": str(node.label),
            "level": str(node.level),
            "parent_id": str(node.parent_id) if node.parent_id is not None else None,
            "child_ids": [str(child_id) for child_id in node.child_ids],
            "value": int(node.value),
            "start_angle_deg": round(float(start), 3),
            "end_angle_deg": round(float(end), 3),
            "label_center_px": [round(float(label_xy[0]), 3), round(float(label_xy[1]), 3)],
            "label_bbox_px": list(text_bbox),
            "ring_bbox_px": list(wedge_bbox),
            "fill_rgb": [int(channel) for channel in node.color_rgb],
        }
        node_traces.append(dict(trace))
        entities.append(
            {
                "entity_id": str(node.node_id),
                "entity_type": f"sunburst_{node.level}",
                "bbox_xyxy": list(text_bbox),
                "attrs": dict(trace),
            }
        )

    render_meta = {
        "not_to_scale": True,
        "center_px": [int(render_params.center_x_px), int(render_params.center_y_px)],
        "radii_px": {
            "inner": int(render_params.inner_radius_px),
            "parent_outer": int(render_params.parent_outer_radius_px),
            "subgroup_outer": int(render_params.subgroup_outer_radius_px),
            "leaf_outer": int(render_params.leaf_outer_radius_px),
        },
        "value_display_policy": "outer_leaf_values_only",
    }
    return _RenderedSunburst(
        image=image,
        entities=tuple(dict(entity) for entity in entities),
        node_traces=tuple(dict(trace) for trace in node_traces),
        evidence_bbox_by_node_id=dict(evidence_bbox_by_node_id),
        chart_bbox_px=list(chart_bbox),
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


def _quote(value: str) -> str:
    return f'"{str(value)}"'


def _answer_hint_key(query_id: str) -> str:
    return "answer_hint_label" if str(query_id) in set(PARENT_EXTREMUM_QUERY_IDS) else "answer_hint_integer"


def _evidence_hint_key(query_id: str) -> str:
    if str(query_id) in set(PARENT_TOTAL_QUERY_IDS):
        return "evidence_hint_parent_total_from_leaves_value"
    if str(query_id) in set(PARENT_EXTREMUM_QUERY_IDS):
        return "evidence_hint_parent_total_extremum_label"
    return "evidence_hint_conditional_leaf_count"


def _json_example_key(query_id: str, *, answer_only: bool = False) -> str:
    prefix = "json_example_answer_only" if bool(answer_only) else "json_example"
    if str(query_id) in set(PARENT_TOTAL_QUERY_IDS):
        return f"{prefix}_parent_total_from_leaves_value"
    if str(query_id) in set(PARENT_EXTREMUM_QUERY_IDS):
        return f"{prefix}_parent_total_extremum_label"
    return f"{prefix}_conditional_leaf_count"


class ChartsCompositionSunburstHierarchyTask:
    """Generate one sunburst hierarchy chart query."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "composition"
    default_dataset_enabled = False
    allowed_query_ids: Tuple[str, ...] = PARENT_TOTAL_QUERY_IDS

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id = _sample_query_id(params, allowed_query_ids=self.allowed_query_ids, instance_seed=int(instance_seed))
        if query_id not in set(SUPPORTED_QUERY_IDS):
            raise ValueError(f"unsupported sunburst query_id: {query_id}")
        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_sunburst",
                "answer_hint_integer",
                "answer_hint_label",
                "evidence_hint_parent_total_from_leaves_value",
                "evidence_hint_parent_total_extremum_label",
                "evidence_hint_conditional_leaf_count",
                "json_example_parent_total_from_leaves_value",
                "json_example_parent_total_extremum_label",
                "json_example_conditional_leaf_count",
                "json_example_answer_only_parent_total_from_leaves_value",
                "json_example_answer_only_parent_total_extremum_label",
                "json_example_answer_only_conditional_leaf_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1400))),
            canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 1180))),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_sunburst(
            background,
            dataset=dataset,
            params=params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        query_trace = dict(dataset.query.trace)
        slots = {
            "object_description": str(prompt_defaults["object_description_sunburst"]),
            "parent_label": _quote(str(query_trace.get("parent_label", ""))),
            "comparison_phrase": str(query_trace.get("comparison_phrase", "")),
            "threshold_value": str(query_trace.get("threshold_value", "")),
            "lower_value": str(query_trace.get("lower_value", "")),
            "upper_value": str(query_trace.get("upper_value", "")),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(prompt_defaults[_evidence_hint_key(str(query_id))]),
            "answer_hint": str(prompt_defaults[_answer_hint_key(str(query_id))]),
            "json_example": str(prompt_defaults[_json_example_key(str(query_id))]),
            "json_example_answer_only": str(prompt_defaults[_json_example_key(str(query_id), answer_only=True)]),
        }
        prompt, prompt_variants, prompt_variant, prompt_variants_for_trace, active_prompt_key = _make_prompt(
            query_id=str(query_id),
            prompt_defaults=prompt_defaults,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        nodes_by_id = {str(node.node_id): node for node in dataset.nodes}
        evidence_bboxes = [
            list(rendered.evidence_bbox_by_node_id[str(node_id)])
            for node_id in dataset.query.evidence_node_ids
            if str(node_id) in rendered.evidence_bbox_by_node_id
        ]
        if not evidence_bboxes:
            raise ValueError("sunburst query produced no projected evidence")
        hierarchy_rows = [
            {
                "node_id": str(node.node_id),
                "label": str(node.label),
                "level": str(node.level),
                "parent_id": str(node.parent_id) if node.parent_id is not None else None,
                "value": int(node.value),
                "child_ids": [str(child_id) for child_id in node.child_ids],
            }
            for node in dataset.nodes
        ]
        query_params = {
            "query_id": str(query_id),
            "public_task_id": str(self.task_id),
            "parent_count": int(len(dataset.parent_ids)),
            "subgroup_count": int(len(dataset.subgroup_ids)),
            "leaf_count": int(len(dataset.leaf_ids)),
            "parent_labels": [str(nodes_by_id[parent_id].label) for parent_id in dataset.parent_ids],
            "evidence_node_ids": [str(node_id) for node_id in dataset.query.evidence_node_ids],
            "answer_value": dataset.query.answer,
            **dict(dataset.generation_ranges),
            **dict(query_trace),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_sunburst_hierarchy",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": dict(query_params),
            },
            "query_spec": {
                "query_id": str(query_id),
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
                "scene_variant": "sunburst_hierarchy",
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "chart_bbox_px": list(rendered.chart_bbox_px),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "chart_bbox_px": list(rendered.chart_bbox_px),
                "node_traces": [dict(trace) for trace in rendered.node_traces],
                "evidence_bbox_by_node_id": {
                    str(node_id): list(bbox)
                    for node_id, bbox in rendered.evidence_bbox_by_node_id.items()
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "answer_value": dataset.query.answer,
                "question_format": "label_open" if dataset.query.answer_type == "string" else "numeric_open",
                "hierarchy": list(hierarchy_rows),
                "evidence_node_ids": [str(node_id) for node_id in dataset.query.evidence_node_ids],
                **dict(query_params),
            },
            "witness_symbolic": {
                "type": "sunburst_hierarchy_values",
                "query_id": str(query_id),
                "answer_value": dataset.query.answer,
                "evidence_node_ids": [str(node_id) for node_id in dataset.query.evidence_node_ids],
                "calculation": dict(query_trace),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                "evidence_node_ids": [str(node_id) for node_id in dataset.query.evidence_node_ids],
            },
        }
        answer_gt = (
            TypedValue(type="string", value=str(dataset.query.answer))
            if dataset.query.answer_type == "string"
            else TypedValue(type="integer", value=int(dataset.query.answer))
        )
        max_leaf_count = int(dataset.generation_ranges["parent_count_range"][1]) * int(dataset.generation_ranges["subgroup_count_range"][1]) * int(dataset.generation_ranges["leaf_count_range"][1])
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(len(dataset.leaf_ids)), (1, max(1, int(max_leaf_count)))),
                "reasoning_load": float(_QUERY_REASONING_LOAD[str(query_id)]),
                "scene_variant_load": 0.82,
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_bboxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        attempts = max(1, int(max_attempts))
        last_error: Exception | None = None
        for attempt in range(attempts):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.sunburst.retry", int(attempt)))
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


@register_task
class ChartsCompositionSunburstParentTotalValueTask(ChartsCompositionSunburstHierarchyTask):
    """Compute a parent total from outer leaf values in a sunburst hierarchy."""

    task_id = "task_charts__sunburst__parent_total_value"
    allowed_query_ids = PARENT_TOTAL_QUERY_IDS
    default_dataset_enabled = True


@register_task
class ChartsCompositionSunburstParentTotalExtremumLabelTask(ChartsCompositionSunburstHierarchyTask):
    """Find the parent category with the highest or lowest computed total."""

    task_id = "task_charts__sunburst__parent_total_extremum_label"
    allowed_query_ids = PARENT_EXTREMUM_QUERY_IDS
    default_dataset_enabled = True


@register_task
class ChartsCompositionSunburstConditionalLeafCountTask(ChartsCompositionSunburstHierarchyTask):
    """Count outer leaves under a parent that satisfy a value condition."""

    task_id = "task_charts__sunburst__conditional_leaf_count"
    allowed_query_ids = CONDITIONAL_LEAF_QUERY_IDS
    default_dataset_enabled = True


__all__ = [
    "ChartsCompositionSunburstConditionalLeafCountTask",
    "ChartsCompositionSunburstHierarchyTask",
    "ChartsCompositionSunburstParentTotalExtremumLabelTask",
    "ChartsCompositionSunburstParentTotalValueTask",
]
