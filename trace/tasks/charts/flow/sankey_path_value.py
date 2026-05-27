"""Sankey-style flow chart path arithmetic task."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_raw as _bbox_union, round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import (
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_flow_sankey_path_value_base"
PATH_VALUE_QUERY_VARIANTS: Tuple[str, ...] = (
    "source_to_target_total_flow",
    "path_bottleneck_value",
    "path_flow_difference",
)
NODE_SIDE_TOTAL_QUERY_VARIANTS: Tuple[str, ...] = (
    "source_outgoing_total_flow",
    "target_incoming_total_flow",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = PATH_VALUE_QUERY_VARIANTS + NODE_SIDE_TOTAL_QUERY_VARIANTS
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("three_column_sankey",)

_SOURCE_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D")
_MIDDLE_LABEL_POOL: Tuple[str, ...] = ("K", "L", "M", "N", "P")
_TARGET_LABEL_POOL: Tuple[str, ...] = ("V", "W", "X", "Y")
_TITLE_OPTIONS: Tuple[str, ...] = (
    "Program Flow Summary",
    "Budget Transfer Sankey",
    "Pipeline Flow Paths",
    "Resource Routing Diagram",
    "Channel Flow Map",
)
_FLOW_PALETTE_RGB: Tuple[Tuple[int, int, int], ...] = (
    (51, 113, 176),
    (204, 103, 79),
    (68, 153, 112),
    (139, 111, 190),
    (208, 151, 57),
    (67, 139, 160),
    (176, 89, 136),
    (95, 127, 66),
    (62, 102, 148),
    (190, 126, 84),
    (105, 151, 190),
    (160, 111, 74),
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "source_to_target_total_flow": 0.90,
    "path_bottleneck_value": 0.62,
    "path_flow_difference": 0.70,
    "source_outgoing_total_flow": 0.66,
    "target_incoming_total_flow": 0.66,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {"three_column_sankey": 0.62}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "flow")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="flow")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="flow", apply_prob=0.0)


Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _FlowRenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    title_band_height_px: int
    node_width_px: int
    node_height_px: int
    node_border_width_px: int
    port_separation_px: int
    shared_pair_lane_gap_px: int
    min_flow_width_px: int
    max_flow_width_px: int
    value_label_font_size_px: int
    value_label_gap_px: int
    source_middle_label_t: float
    middle_target_label_t: float
    node_label_font_size_px: int
    title_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    plot_fill_rgb: Tuple[int, int, int]
    node_fill_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    node_text_rgb: Tuple[int, int, int]
    value_label_fill_rgb: Tuple[int, int, int]
    value_label_border_rgb: Tuple[int, int, int]
    value_label_text_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    flow_alpha: int
    layout_offset_x_px: int
    layout_offset_y_px: int
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedSankey:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    plot_bbox_px: List[float]
    node_bbox_map: Dict[str, List[float]]
    node_label_bbox_map: Dict[str, List[float]]
    segment_bbox_map: Dict[str, List[float]]
    segment_label_bbox_map: Dict[str, List[float]]
    segment_center_map: Dict[str, List[float]]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _rgb_param(params: Mapping[str, Any], key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _int_param(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _float_param(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), _RENDER_DEFAULTS.get(str(key), float(fallback))))


def _gen_int_param(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _GEN_DEFAULTS.get(str(key), int(fallback))))


def _resolve_render_params(params: Mapping[str, Any]) -> _FlowRenderParams:
    outer = _int_param(params, "outer_margin_px", 36)
    jitter_left, _jitter_right, jitter_top, _jitter_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(outer),
        right_px=int(outer),
        top_px=int(outer),
        bottom_px=int(outer),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    return _FlowRenderParams(
        canvas_width=_int_param(params, "canvas_width", 1180),
        canvas_height=_int_param(params, "canvas_height", 760),
        outer_margin_px=int(outer),
        panel_padding_px=_int_param(params, "panel_padding_px", 28),
        title_band_height_px=_int_param(params, "title_band_height_px", 62),
        node_width_px=_int_param(params, "node_width_px", 96),
        node_height_px=_int_param(params, "node_height_px", 44),
        node_border_width_px=_int_param(params, "node_border_width_px", 2),
        port_separation_px=max(14, _int_param(params, "port_separation_px", 34)),
        shared_pair_lane_gap_px=max(0, _int_param(params, "shared_pair_lane_gap_px", 72)),
        min_flow_width_px=_int_param(params, "min_flow_width_px", 6),
        max_flow_width_px=_int_param(params, "max_flow_width_px", 18),
        value_label_font_size_px=_int_param(params, "value_label_font_size_px", 19),
        value_label_gap_px=max(0, _int_param(params, "value_label_gap_px", 8)),
        source_middle_label_t=max(0.15, min(0.85, _float_param(params, "source_middle_label_t", 0.34))),
        middle_target_label_t=max(0.15, min(0.85, _float_param(params, "middle_target_label_t", 0.66))),
        node_label_font_size_px=_int_param(params, "node_label_font_size_px", 24),
        title_font_size_px=_int_param(params, "title_font_size_px", 29),
        panel_fill_rgb=_rgb_param(params, "panel_fill_rgb", (252, 253, 251)),
        panel_border_rgb=_rgb_param(params, "panel_border_rgb", (70, 80, 90)),
        plot_fill_rgb=_rgb_param(params, "plot_fill_rgb", (255, 255, 255)),
        node_fill_rgb=_rgb_param(params, "node_fill_rgb", (54, 63, 74)),
        node_border_rgb=_rgb_param(params, "node_border_rgb", (30, 38, 46)),
        node_text_rgb=_rgb_param(params, "node_text_rgb", (255, 255, 255)),
        value_label_fill_rgb=_rgb_param(params, "value_label_fill_rgb", (255, 255, 255)),
        value_label_border_rgb=_rgb_param(params, "value_label_border_rgb", (82, 88, 96)),
        value_label_text_rgb=_rgb_param(params, "value_label_text_rgb", (28, 34, 42)),
        title_color_rgb=_rgb_param(params, "title_color_rgb", (32, 38, 46)),
        flow_alpha=max(40, min(220, _int_param(params, "flow_alpha", 138))),
        layout_offset_x_px=int(jitter_left) - int(outer),
        layout_offset_y_px=int(jitter_top) - int(outer),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _clamp_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    x0 = max(0.0, min(float(width), x0))
    y0 = max(0.0, min(float(height), y0))
    x1 = max(0.0, min(float(width), x1))
    y1 = max(0.0, min(float(height), y1))
    if x1 <= x0:
        x1 = min(float(width), x0 + 1.0)
    if y1 <= y0:
        y1 = min(float(height), y0 + 1.0)
    return _round_bbox((x0, y0, x1, y1))


def _cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - float(t)
    x = (inv**3 * p0[0]) + (3 * inv * inv * t * p1[0]) + (3 * inv * t * t * p2[0]) + (t**3 * p3[0])
    y = (inv**3 * p0[1]) + (3 * inv * inv * t * p1[1]) + (3 * inv * t * t * p2[1]) + (t**3 * p3[1])
    return (float(x), float(y))


def _curve_points(start: Point, end: Point, *, steps: int = 36, lane_offset_y: float = 0.0) -> List[Point]:
    dx = float(end[0] - start[0])
    c1 = (float(start[0] + (0.42 * dx)), float(start[1] + float(lane_offset_y)))
    c2 = (float(end[0] - (0.42 * dx)), float(end[1] + float(lane_offset_y)))
    return [
        _cubic_point(start, c1, c2, end, float(index) / float(max(1, int(steps) - 1)))
        for index in range(int(steps))
    ]


def _curve_bbox(points: Sequence[Point], *, stroke_width: int, canvas_width: int, canvas_height: int) -> List[float]:
    pad = max(2.0, 0.5 * float(stroke_width) + 2.0)
    return _clamp_bbox(
        (
            min(point[0] for point in points) - pad,
            min(point[1] for point in points) - pad,
            max(point[0] for point in points) + pad,
            max(point[1] for point in points) + pad,
        ),
        width=int(canvas_width),
        height=int(canvas_height),
    )


def _node_bboxes(
    *,
    nodes: Sequence[Mapping[str, Any]],
    x_center: float,
    top: float,
    bottom: float,
    render_params: _FlowRenderParams,
) -> Dict[str, BBox]:
    count = len(nodes)
    if int(count) <= 0:
        return {}
    usable_top = float(top + 28.0)
    usable_bottom = float(bottom - 26.0)
    if int(count) == 1:
        centers = [0.5 * (usable_top + usable_bottom)]
    else:
        centers = [
            float(usable_top + ((usable_bottom - usable_top) * float(index) / float(count - 1)))
            for index in range(int(count))
        ]
    half_w = 0.5 * float(render_params.node_width_px)
    half_h = 0.5 * float(render_params.node_height_px)
    return {
        str(node["node_id"]): (
            float(x_center - half_w),
            float(centers[index] - half_h),
            float(x_center + half_w),
            float(centers[index] + half_h),
        )
        for index, node in enumerate(nodes)
    }


def _port_y(
    *,
    node_bbox: Sequence[float],
    ordered_path_ids: Sequence[str],
    path_id: str,
    render_params: _FlowRenderParams,
) -> float:
    center_y = 0.5 * (float(node_bbox[1]) + float(node_bbox[3]))
    total = max(1, len(ordered_path_ids))
    if int(total) == 1:
        return float(center_y)
    index = [str(item) for item in ordered_path_ids].index(str(path_id))
    node_height = float(node_bbox[3] - node_bbox[1])
    available_span = max(0.0, node_height - 12.0)
    min_separation = max(
        14.0,
        float(render_params.port_separation_px),
        float(render_params.max_flow_width_px) + 10.0,
    )
    span = min(float(available_span), max(14.0, float(total - 1) * float(min_separation)))
    offset = (-0.5 * span) + (span * float(index) / float(total - 1))
    return float(center_y + offset)


def _flow_width(value: int, *, render_params: _FlowRenderParams, value_min: int, value_max: int) -> int:
    if int(value_max) <= int(value_min):
        return int(render_params.min_flow_width_px)
    norm = (float(value) - float(value_min)) / float(value_max - value_min)
    width = float(render_params.min_flow_width_px) + (clamp_unit_interval(norm) * float(render_params.max_flow_width_px - render_params.min_flow_width_px))
    return max(1, int(round(width)))


def _value_label_size(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    render_params: _FlowRenderParams,
) -> Tuple[float, float]:
    font = load_font(int(render_params.value_label_font_size_px), bold=True)
    text_bbox = draw.textbbox((0, 0), str(text), font=font)
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    return (max(36.0, float(text_width + 18.0)), max(26.0, float(text_height + 12.0)))


def _value_label_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Point,
    render_params: _FlowRenderParams,
) -> BBox:
    label_width, label_height = _value_label_size(draw, text=str(text), render_params=render_params)
    cx, cy = float(center[0]), float(center[1])
    return (
        float(cx - (0.5 * label_width)),
        float(cy - (0.5 * label_height)),
        float(cx + (0.5 * label_width)),
        float(cy + (0.5 * label_height)),
    )


def _draw_value_label(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Point,
    render_params: _FlowRenderParams,
) -> List[float]:
    font = load_font(int(render_params.value_label_font_size_px), bold=True)
    bbox = _value_label_bbox(draw, text=str(text), center=center, render_params=render_params)
    cx, cy = float(center[0]), float(center[1])
    draw.rounded_rectangle(
        bbox,
        radius=8,
        fill=tuple(int(channel) for channel in render_params.value_label_fill_rgb),
        outline=tuple(int(channel) for channel in render_params.value_label_border_rgb),
        width=1,
    )
    draw_centered_text(
        draw,
        text=str(text),
        center=(float(cx), float(cy)),
        font=font,
        fill=render_params.value_label_text_rgb,
        stroke_fill=render_params.value_label_fill_rgb,
        stroke_width=1,
    )
    return _round_bbox(bbox)


def _resolve_value_label_centers(
    draw: ImageDraw.ImageDraw,
    *,
    label_specs: Sequence[Mapping[str, Any]],
    plot_bbox: Sequence[float],
    render_params: _FlowRenderParams,
) -> Dict[str, Point]:
    resolved: Dict[str, Point] = {}
    gap = float(render_params.value_label_gap_px)
    top_limit = float(plot_bbox[1]) + max(4.0, gap)
    bottom_limit = float(plot_bbox[3]) - max(4.0, gap)
    available_height = max(1.0, float(bottom_limit - top_limit))

    for segment_kind in ("source_middle", "middle_target"):
        group = [
            dict(spec)
            for spec in label_specs
            if str(spec["segment_kind"]) == str(segment_kind)
        ]
        if not group:
            continue
        group = sorted(
            group,
            key=lambda spec: (
                float(spec["desired_center"][1]),
                float(spec["desired_center"][0]),
                str(spec["segment_id"]),
            ),
        )
        heights = [
            _value_label_size(draw, text=str(spec["text"]), render_params=render_params)[1]
            for spec in group
        ]
        if len(group) > 1:
            total_label_height = sum(float(height) for height in heights)
            effective_gap = min(float(gap), max(0.0, (available_height - total_label_height) / float(len(group) - 1)))
        else:
            effective_gap = 0.0

        placed: List[Tuple[Dict[str, Any], float, float]] = []
        previous_bottom = float("-inf")
        for spec, height in zip(group, heights):
            half_height = 0.5 * float(height)
            desired_x, desired_y = [float(value) for value in spec["desired_center"]]
            min_center_y = float(top_limit + half_height)
            max_center_y = float(bottom_limit - half_height)
            desired_y = max(min_center_y, min(max_center_y, float(desired_y)))
            if placed:
                desired_y = max(float(desired_y), float(previous_bottom + effective_gap + half_height))
            placed.append((spec, float(desired_y), float(height)))
            previous_bottom = float(desired_y + half_height)

        overflow = max(0.0, float(previous_bottom - bottom_limit))
        if overflow > 0.0:
            placed = [(spec, float(center_y - overflow), height) for spec, center_y, height in placed]

        first_top = float(placed[0][1] - (0.5 * placed[0][2]))
        underflow = max(0.0, float(top_limit - first_top))
        if underflow > 0.0:
            placed = [(spec, float(center_y + underflow), height) for spec, center_y, height in placed]

        for spec, center_y, _height in placed:
            desired_x = float(spec["desired_center"][0])
            resolved[str(spec["segment_id"])] = (float(desired_x), float(center_y))

    return resolved


def _sorted_paths_for_port(
    paths: Sequence[Mapping[str, Any]],
    *,
    key_fields: Sequence[str],
) -> List[str]:
    return [
        str(path["path_id"])
        for path in sorted(
            paths,
            key=lambda path: tuple(str(path[field]) for field in key_fields),
        )
    ]


def _segment_lane_offsets(
    paths: Sequence[Mapping[str, Any]],
    *,
    segment_kind: str,
    render_params: _FlowRenderParams,
) -> Dict[str, float]:
    """Fan out parallel bands that connect the same pair of Sankey nodes."""

    if int(render_params.shared_pair_lane_gap_px) <= 0:
        return {str(path["path_id"]): 0.0 for path in paths}

    grouped: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for path in paths:
        if str(segment_kind) == "source_middle":
            key = (str(path["source_id"]), str(path["middle_id"]))
        else:
            key = (str(path["middle_id"]), str(path["target_id"]))
        grouped.setdefault(key, []).append(path)

    offsets: Dict[str, float] = {}
    for group in grouped.values():
        if len(group) <= 1:
            offsets[str(group[0]["path_id"])] = 0.0
            continue
        if str(segment_kind) == "source_middle":
            ordered = sorted(group, key=lambda path: (str(path["target_label"]), str(path["path_id"])))
        else:
            ordered = sorted(group, key=lambda path: (str(path["source_label"]), str(path["path_id"])))
        center = 0.5 * float(len(ordered) - 1)
        for index, path in enumerate(ordered):
            offsets[str(path["path_id"])] = (float(index) - center) * float(render_params.shared_pair_lane_gap_px)
    return offsets


def _render_sankey(
    background: Image.Image,
    *,
    scene_title: str,
    sources: Sequence[Mapping[str, Any]],
    middles: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    paths: Sequence[Mapping[str, Any]],
    render_params: _FlowRenderParams,
    value_min: int,
    value_max: int,
) -> _RenderedSankey:
    base = background.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    flow_draw = ImageDraw.Draw(overlay)

    outer = float(render_params.outer_margin_px)
    offset_x = float(render_params.layout_offset_x_px)
    offset_y = float(render_params.layout_offset_y_px)
    panel_bbox: BBox = (
        outer + offset_x,
        outer + offset_y,
        float(render_params.canvas_width) - outer + offset_x,
        float(render_params.canvas_height) - outer + offset_y,
    )
    title_bbox: BBox = (
        panel_bbox[0] + float(render_params.panel_padding_px),
        panel_bbox[1] + 10.0,
        panel_bbox[2] - float(render_params.panel_padding_px),
        panel_bbox[1] + float(render_params.title_band_height_px),
    )
    plot_bbox: BBox = (
        panel_bbox[0] + float(render_params.panel_padding_px),
        title_bbox[3] + 18.0,
        panel_bbox[2] - float(render_params.panel_padding_px),
        panel_bbox[3] - float(render_params.panel_padding_px),
    )
    x_left = float(plot_bbox[0] + 84.0)
    x_middle = float(0.5 * (plot_bbox[0] + plot_bbox[2]))
    x_right = float(plot_bbox[2] - 84.0)
    node_bbox_map_raw: Dict[str, BBox] = {}
    node_bbox_map_raw.update(
        _node_bboxes(
            nodes=sources,
            x_center=float(x_left),
            top=float(plot_bbox[1]),
            bottom=float(plot_bbox[3]),
            render_params=render_params,
        )
    )
    node_bbox_map_raw.update(
        _node_bboxes(
            nodes=middles,
            x_center=float(x_middle),
            top=float(plot_bbox[1]),
            bottom=float(plot_bbox[3]),
            render_params=render_params,
        )
    )
    node_bbox_map_raw.update(
        _node_bboxes(
            nodes=targets,
            x_center=float(x_right),
            top=float(plot_bbox[1]),
            bottom=float(plot_bbox[3]),
            render_params=render_params,
        )
    )

    paths_by_id = {str(path["path_id"]): dict(path) for path in paths}
    source_right: Dict[str, List[str]] = {}
    middle_left: Dict[str, List[str]] = {}
    middle_right: Dict[str, List[str]] = {}
    target_left: Dict[str, List[str]] = {}
    for source in sources:
        source_id = str(source["node_id"])
        source_paths = [dict(path) for path in paths if str(path["source_id"]) == source_id]
        source_right[source_id] = _sorted_paths_for_port(source_paths, key_fields=("middle_label", "target_label", "path_id"))
    for middle in middles:
        middle_id = str(middle["node_id"])
        in_paths = [dict(path) for path in paths if str(path["middle_id"]) == middle_id]
        out_paths = list(in_paths)
        middle_left[middle_id] = _sorted_paths_for_port(in_paths, key_fields=("source_label", "target_label", "path_id"))
        middle_right[middle_id] = _sorted_paths_for_port(out_paths, key_fields=("target_label", "source_label", "path_id"))
    for target in targets:
        target_id = str(target["node_id"])
        target_paths = [dict(path) for path in paths if str(path["target_id"]) == target_id]
        target_left[target_id] = _sorted_paths_for_port(target_paths, key_fields=("middle_label", "source_label", "path_id"))

    source_middle_lane_offsets = _segment_lane_offsets(
        paths,
        segment_kind="source_middle",
        render_params=render_params,
    )
    middle_target_lane_offsets = _segment_lane_offsets(
        paths,
        segment_kind="middle_target",
        render_params=render_params,
    )

    segment_bbox_map: Dict[str, List[float]] = {}
    segment_label_bbox_map: Dict[str, List[float]] = {}
    segment_center_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []

    for index, path in enumerate(paths):
        path_id = str(path["path_id"])
        color = _FLOW_PALETTE_RGB[int(index) % len(_FLOW_PALETTE_RGB)]
        source_bbox = node_bbox_map_raw[str(path["source_id"])]
        middle_bbox = node_bbox_map_raw[str(path["middle_id"])]
        target_bbox = node_bbox_map_raw[str(path["target_id"])]
        first_start = (
            float(source_bbox[2]),
            _port_y(
                node_bbox=source_bbox,
                ordered_path_ids=source_right[str(path["source_id"])],
                path_id=path_id,
                render_params=render_params,
            ),
        )
        first_end = (
            float(middle_bbox[0]),
            _port_y(
                node_bbox=middle_bbox,
                ordered_path_ids=middle_left[str(path["middle_id"])],
                path_id=path_id,
                render_params=render_params,
            ),
        )
        second_start = (
            float(middle_bbox[2]),
            _port_y(
                node_bbox=middle_bbox,
                ordered_path_ids=middle_right[str(path["middle_id"])],
                path_id=path_id,
                render_params=render_params,
            ),
        )
        second_end = (
            float(target_bbox[0]),
            _port_y(
                node_bbox=target_bbox,
                ordered_path_ids=target_left[str(path["target_id"])],
                path_id=path_id,
                render_params=render_params,
            ),
        )
        for segment_kind, start, end, value, label_t in (
            ("source_middle", first_start, first_end, int(path["first_value"]), float(render_params.source_middle_label_t)),
            ("middle_target", second_start, second_end, int(path["second_value"]), float(render_params.middle_target_label_t)),
        ):
            segment_id = f"{path_id}:{segment_kind}"
            lane_offset = (
                float(source_middle_lane_offsets.get(str(path_id), 0.0))
                if str(segment_kind) == "source_middle"
                else float(middle_target_lane_offsets.get(str(path_id), 0.0))
            )
            points = _curve_points(start, end, lane_offset_y=float(lane_offset))
            stroke_width = _flow_width(
                int(value),
                render_params=render_params,
                value_min=int(value_min),
                value_max=int(value_max),
            )
            flow_draw.line(
                points,
                fill=(int(color[0]), int(color[1]), int(color[2]), int(render_params.flow_alpha)),
                width=int(stroke_width),
                joint="curve",
            )
            bbox = _curve_bbox(
                points,
                stroke_width=int(stroke_width),
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
            )
            label_center = _cubic_point(
                points[0],
                points[max(1, len(points) // 3)],
                points[min(len(points) - 2, (2 * len(points)) // 3)],
                points[-1],
                float(label_t),
            )
            segment_bbox_map[str(segment_id)] = list(bbox)
            segment_center_map[str(segment_id)] = [round(float(label_center[0]), 3), round(float(label_center[1]), 3)]

    image = Image.alpha_composite(base, overlay).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(panel_bbox, radius=16, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=2)
    draw.rounded_rectangle(plot_bbox, radius=12, fill=render_params.plot_fill_rgb, outline=render_params.panel_border_rgb, width=1)
    image_with_flows = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image_with_flows)
    title_text_bbox = draw_centered_text(
        draw,
        text=str(scene_title),
        center=(0.5 * (title_bbox[0] + title_bbox[2]), 0.5 * (title_bbox[1] + title_bbox[3])),
        font=load_font(int(render_params.title_font_size_px), bold=True),
        fill=render_params.title_color_rgb,
        stroke_fill=render_params.panel_fill_rgb,
        stroke_width=1,
    )

    value_label_specs: List[Dict[str, Any]] = []
    for path in paths:
        path_id = str(path["path_id"])
        for segment_kind, value in (
            ("source_middle", int(path["first_value"])),
            ("middle_target", int(path["second_value"])),
        ):
            segment_id = f"{path_id}:{segment_kind}"
            value_label_specs.append(
                {
                    "segment_id": str(segment_id),
                    "segment_kind": str(segment_kind),
                    "text": str(value),
                    "desired_center": tuple(float(value) for value in segment_center_map[str(segment_id)]),
                }
            )

    resolved_label_centers = _resolve_value_label_centers(
        draw,
        label_specs=value_label_specs,
        plot_bbox=plot_bbox,
        render_params=render_params,
    )

    for path in paths:
        path_id = str(path["path_id"])
        for segment_kind, value in (
            ("source_middle", int(path["first_value"])),
            ("middle_target", int(path["second_value"])),
        ):
            segment_id = f"{path_id}:{segment_kind}"
            label_center = tuple(float(value) for value in resolved_label_centers[str(segment_id)])
            segment_center_map[str(segment_id)] = [round(float(label_center[0]), 3), round(float(label_center[1]), 3)]
            segment_label_bbox_map[str(segment_id)] = _draw_value_label(
                draw,
                text=str(value),
                center=label_center,
                render_params=render_params,
            )
            entities.append(
                {
                    "entity_id": str(segment_id),
                    "entity_type": "sankey_segment",
                    "bbox_xyxy": list(segment_bbox_map[str(segment_id)]),
                    "attrs": {
                        "path_id": str(path_id),
                        "segment_kind": str(segment_kind),
                        "value": int(value),
                        "label_bbox_xyxy": list(segment_label_bbox_map[str(segment_id)]),
                    },
                }
            )

    node_bbox_map: Dict[str, List[float]] = {}
    node_label_bbox_map: Dict[str, List[float]] = {}
    all_nodes = [*sources, *middles, *targets]
    for node in all_nodes:
        node_id = str(node["node_id"])
        bbox = node_bbox_map_raw[node_id]
        node_bbox_map[node_id] = _round_bbox(bbox)
        draw.rounded_rectangle(
            bbox,
            radius=10,
            fill=tuple(int(channel) for channel in render_params.node_fill_rgb),
            outline=tuple(int(channel) for channel in render_params.node_border_rgb),
            width=max(1, int(render_params.node_border_width_px)),
        )
        label_font = fit_font_to_box(
            draw,
            text=str(node["label"]),
            max_width=float(bbox[2] - bbox[0] - 12.0),
            max_height=float(bbox[3] - bbox[1] - 8.0),
            bold=True,
            min_size_px=12,
            max_size_px=int(render_params.node_label_font_size_px),
            fill_ratio=0.9,
        )
        label_bbox = draw_centered_text(
            draw,
            text=str(node["label"]),
            center=(0.5 * (bbox[0] + bbox[2]), 0.5 * (bbox[1] + bbox[3])),
            font=label_font,
            fill=render_params.node_text_rgb,
            stroke_fill=render_params.node_fill_rgb,
            stroke_width=1,
        )
        node_label_bbox_map[node_id] = list(label_bbox)
        entities.append(
            {
                "entity_id": str(node_id),
                "entity_type": "sankey_node",
                "bbox_xyxy": list(node_bbox_map[node_id]),
                "attrs": {
                    "label": str(node["label"]),
                    "column": str(node["column"]),
                },
            }
        )

    entities.insert(0, {"entity_id": "flow_panel", "entity_type": "flow_panel", "bbox_xyxy": _round_bbox(panel_bbox)})
    entities.insert(
        1,
        {
            "entity_id": "flow_title",
            "entity_type": "flow_title",
            "bbox_xyxy": list(title_text_bbox),
            "attrs": {"title": str(scene_title)},
        },
    )
    return _RenderedSankey(
        image=image_with_flows,
        entities=tuple(dict(item) for item in entities),
        panel_bbox_px=_round_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        plot_bbox_px=_round_bbox(plot_bbox),
        node_bbox_map=dict(node_bbox_map),
        node_label_bbox_map=dict(node_label_bbox_map),
        segment_bbox_map=dict(segment_bbox_map),
        segment_label_bbox_map=dict(segment_label_bbox_map),
        segment_center_map=dict(segment_center_map),
    )


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        task_id=TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _uses_uniform_query_variant_cycle(
    params: Mapping[str, Any],
    *,
    query_variant_probabilities: Mapping[str, float],
) -> bool:
    if params.get("query_variant") is not None or params.get("query_variant_weights") is not None:
        return False
    enabled = bool(params.get("balanced_query_variant_sampling", _GEN_DEFAULTS.get("balanced_query_variant_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in query_variant_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_QUERY_VARIANTS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_sampling_params(
    params: Mapping[str, Any],
    *,
    query_variant_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_variant_cycle(params, query_variant_probabilities=query_variant_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_VARIANTS))
    return support_params


def _balanced_int(
    support: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    ordered = [int(value) for value in support]
    if not ordered:
        raise ValueError(f"empty support for {namespace}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(ordered[int(index) % len(ordered)])


def _resolve_count(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    explicit_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"{TASK_ID} {explicit_key}",
    )
    explicit = params.get(str(explicit_key))
    support = [int(value) for value in range(int(lower), int(upper) + 1)]
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"{explicit_key} must be in {lower}..{upper}")
        return int(selected), (int(lower), int(upper))
    return (
        _balanced_int(support, params=params, instance_seed=int(instance_seed), namespace=str(namespace)),
        (int(lower), int(upper)),
    )


def _node_specs(labels: Sequence[str], *, prefix: str, column: str) -> List[Dict[str, Any]]:
    return [
        {
            "node_id": f"{prefix}_{index}",
            "label": str(label),
            "column": str(column),
            "index": int(index),
        }
        for index, label in enumerate(labels)
    ]


def _path_record(
    *,
    path_id: str,
    source: Mapping[str, Any],
    middle: Mapping[str, Any],
    target: Mapping[str, Any],
    first_value: int,
    second_value: int,
) -> Dict[str, Any]:
    bottleneck = min(int(first_value), int(second_value))
    difference = abs(int(first_value) - int(second_value))
    return {
        "path_id": str(path_id),
        "source_id": str(source["node_id"]),
        "source_label": str(source["label"]),
        "middle_id": str(middle["node_id"]),
        "middle_label": str(middle["label"]),
        "target_id": str(target["node_id"]),
        "target_label": str(target["label"]),
        "first_value": int(first_value),
        "second_value": int(second_value),
        "bottleneck_value": int(bottleneck),
        "absolute_difference": int(difference),
    }


def _sample_labels(rng, *, source_count: int, middle_count: int, target_count: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    source_labels = [str(label) for label in rng.sample(list(_SOURCE_LABEL_POOL), int(source_count))]
    middle_labels = [str(label) for label in rng.sample(list(_MIDDLE_LABEL_POOL), int(middle_count))]
    target_labels = [str(label) for label in rng.sample(list(_TARGET_LABEL_POOL), int(target_count))]
    return (
        _node_specs(source_labels, prefix="source", column="source"),
        _node_specs(middle_labels, prefix="middle", column="middle"),
        _node_specs(target_labels, prefix="target", column="target"),
    )


def _sample_paths(
    *,
    query_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    sources: Sequence[Mapping[str, Any]],
    middles: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    path_count: int,
    value_min: int,
    value_max: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    all_triples = [
        (source, middle, target)
        for source in sources
        for middle in middles
        for target in targets
    ]
    selected_triples: List[Tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]] = []
    query_seed_params: Dict[str, Any] = {}

    if str(query_variant) == "source_to_target_total_flow":
        source_target_pairs = [(source, target) for source in sources for target in targets]
        pair_index = _balanced_int(
            list(range(len(source_target_pairs))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.source_target_pair",
        )
        query_source, query_target = source_target_pairs[int(pair_index)]
        route_min, route_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="source_target_route_count_min",
            max_key="source_target_route_count_max",
            fallback_min=2,
            fallback_max=3,
            context=f"{TASK_ID} source-target route count",
        )
        route_max = min(int(route_max), len(middles), int(path_count))
        route_min = min(int(route_min), int(route_max))
        route_count = _balanced_int(
            list(range(int(route_min), int(route_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.source_target_route_count",
        )
        selected_middles = [middles[index] for index in rng.sample(list(range(len(middles))), int(route_count))]
        selected_triples.extend((query_source, middle, query_target) for middle in selected_middles)
        excluded_pair = (str(query_source["node_id"]), str(query_target["node_id"]))
        remaining = [
            triple
            for triple in all_triples
            if (str(triple[0]["node_id"]), str(triple[2]["node_id"])) != excluded_pair
            and str(triple[0]["node_id"]) != str(query_source["node_id"])
            and str(triple[2]["node_id"]) != str(query_target["node_id"])
        ]
        rng.shuffle(remaining)
        needed_remaining = max(0, int(path_count) - len(selected_triples))
        if len(remaining) < int(needed_remaining):
            raise ValueError(f"not enough uncrowded distractor paths for {TASK_ID}")
        selected_triples.extend(remaining[: int(needed_remaining)])
        query_seed_params = {
            "source_id": str(query_source["node_id"]),
            "source_label": str(query_source["label"]),
            "target_id": str(query_target["node_id"]),
            "target_label": str(query_target["label"]),
            "route_count": int(route_count),
        }
    else:
        selected_triples = rng.sample(list(all_triples), k=int(path_count))

    paths: List[Dict[str, Any]] = []
    for index, (source, middle, target) in enumerate(selected_triples):
        first_value = int(rng.randint(int(value_min), int(value_max)))
        second_value = int(rng.randint(int(value_min), int(value_max)))
        paths.append(
            _path_record(
                path_id=f"path_{index}",
                source=source,
                middle=middle,
                target=target,
                first_value=int(first_value),
                second_value=int(second_value),
            )
        )
    return list(paths), dict(query_seed_params)


def _path_side_counts(paths: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    source_out: Counter[str] = Counter()
    middle_in: Counter[str] = Counter()
    middle_out: Counter[str] = Counter()
    target_in: Counter[str] = Counter()
    for path in paths:
        source_out[str(path["source_id"])] += 1
        middle_in[str(path["middle_id"])] += 1
        middle_out[str(path["middle_id"])] += 1
        target_in[str(path["target_id"])] += 1
    return {
        "source_out": dict(source_out),
        "middle_in": dict(middle_in),
        "middle_out": dict(middle_out),
        "target_in": dict(target_in),
    }


def _paths_respect_side_limit(paths: Sequence[Mapping[str, Any]], *, max_paths_per_node_side: int) -> bool:
    if int(max_paths_per_node_side) <= 0:
        return True
    for counts in _path_side_counts(paths).values():
        if counts and max(int(value) for value in counts.values()) > int(max_paths_per_node_side):
            return False
    return True


def _choose_query(
    *,
    query_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    paths: Sequence[Mapping[str, Any]],
    query_seed_params: Mapping[str, Any],
) -> Dict[str, Any]:
    if str(query_variant) == "source_to_target_total_flow":
        source_id = str(query_seed_params["source_id"])
        target_id = str(query_seed_params["target_id"])
        matching = [
            dict(path)
            for path in paths
            if str(path["source_id"]) == source_id and str(path["target_id"]) == target_id
        ]
        if len(matching) < 2:
            raise ValueError(f"{TASK_ID} requires at least two source-target routes")
        matching = sorted(matching, key=lambda path: (str(path["middle_label"]), str(path["path_id"])))
        answer = sum(int(path["bottleneck_value"]) for path in matching)
        answer_min, answer_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="source_target_answer_min",
            max_key="source_target_answer_max",
            fallback_min=10,
            fallback_max=90,
            context=f"{TASK_ID} source-target answer",
        )
        if int(answer) < int(answer_min) or int(answer) > int(answer_max):
            raise ValueError(f"source-target total {answer} outside configured support")
        evidence_segment_ids = [
            segment_id
            for path in matching
            for segment_id in (f"{path['path_id']}:source_middle", f"{path['path_id']}:middle_target")
        ]
        return {
            "answer_value": int(answer),
            "query_path_ids": [str(path["path_id"]) for path in matching],
            "evidence_segment_ids": list(evidence_segment_ids),
            "source_label": str(query_seed_params["source_label"]),
            "target_label": str(query_seed_params["target_label"]),
            "middle_label": "",
            "route_count": int(len(matching)),
            "expression": " + ".join(str(int(path["bottleneck_value"])) for path in matching),
            "path_details": [dict(path) for path in matching],
        }

    if str(query_variant) == "path_bottleneck_value":
        eligible = [dict(path) for path in paths]
        selected = dict(eligible[int(rng.randrange(len(eligible)))])
        answer = int(selected["bottleneck_value"])
        evidence_segment_ids = [
            f"{selected['path_id']}:source_middle",
            f"{selected['path_id']}:middle_target",
        ]
        return {
            "answer_value": int(answer),
            "query_path_ids": [str(selected["path_id"])],
            "evidence_segment_ids": list(evidence_segment_ids),
            "source_label": str(selected["source_label"]),
            "middle_label": str(selected["middle_label"]),
            "target_label": str(selected["target_label"]),
            "route_count": 1,
            "expression": f"min({int(selected['first_value'])}, {int(selected['second_value'])})",
            "path_details": [dict(selected)],
        }

    if str(query_variant) == "path_flow_difference":
        diff_min, diff_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="path_difference_min",
            max_key="path_difference_max",
            fallback_min=2,
            fallback_max=25,
            context=f"{TASK_ID} path difference",
        )
        eligible = [
            dict(path)
            for path in paths
            if int(diff_min) <= int(path["absolute_difference"]) <= int(diff_max)
        ]
        if not eligible:
            raise ValueError(f"no eligible path difference for {TASK_ID}")
        selected = dict(eligible[int(rng.randrange(len(eligible)))])
        answer = int(selected["absolute_difference"])
        evidence_segment_ids = [
            f"{selected['path_id']}:source_middle",
            f"{selected['path_id']}:middle_target",
        ]
        return {
            "answer_value": int(answer),
            "query_path_ids": [str(selected["path_id"])],
            "evidence_segment_ids": list(evidence_segment_ids),
            "source_label": str(selected["source_label"]),
            "middle_label": str(selected["middle_label"]),
            "target_label": str(selected["target_label"]),
            "route_count": 1,
            "expression": f"abs({int(selected['first_value'])} - {int(selected['second_value'])})",
            "path_details": [dict(selected)],
        }

    if str(query_variant) in NODE_SIDE_TOTAL_QUERY_VARIANTS:
        answer_min, answer_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="node_side_total_answer_min",
            max_key="node_side_total_answer_max",
            fallback_min=10,
            fallback_max=90,
            context=f"{TASK_ID} node-side total answer",
        )
        connected_min, connected_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="node_side_total_connected_min",
            max_key="node_side_total_connected_max",
            fallback_min=2,
            fallback_max=3,
            context=f"{TASK_ID} node-side connected path count",
        )

        if str(query_variant) == "source_outgoing_total_flow":
            source_groups: Dict[str, List[Dict[str, Any]]] = {}
            for path in paths:
                source_groups.setdefault(str(path["source_id"]), []).append(dict(path))
            eligible_sources: List[Tuple[str, str, int, List[Dict[str, Any]]]] = []
            for source_id, group in sorted(source_groups.items()):
                ordered_group = sorted(
                    group,
                    key=lambda path: (str(path["middle_label"]), str(path["target_label"]), str(path["path_id"])),
                )
                if not (int(connected_min) <= len(ordered_group) <= int(connected_max)):
                    continue
                answer = sum(int(path["first_value"]) for path in ordered_group)
                if int(answer_min) <= int(answer) <= int(answer_max):
                    eligible_sources.append((str(source_id), str(ordered_group[0]["source_label"]), int(answer), ordered_group))
            if not eligible_sources:
                raise ValueError(f"no eligible source outgoing total for {TASK_ID}")
            selected_node_id, source_label, answer, selected_paths = eligible_sources[int(rng.randrange(len(eligible_sources)))]
            evidence_segment_ids = [f"{path['path_id']}:source_middle" for path in selected_paths]
            terms = " + ".join(str(int(path["first_value"])) for path in selected_paths)
            return {
                "answer_value": int(answer),
                "query_path_ids": [str(path["path_id"]) for path in selected_paths],
                "evidence_segment_ids": list(evidence_segment_ids),
                "source_id": str(selected_node_id),
                "source_label": str(source_label),
                "middle_label": "",
                "target_label": "",
                "node_side": "source_outgoing",
                "connected_count": int(len(selected_paths)),
                "node_side_total": int(answer),
                "route_count": int(len(selected_paths)),
                "expression": str(terms),
                "path_details": [dict(path) for path in selected_paths],
            }

        if str(query_variant) == "target_incoming_total_flow":
            target_groups: Dict[str, List[Dict[str, Any]]] = {}
            for path in paths:
                target_groups.setdefault(str(path["target_id"]), []).append(dict(path))
            eligible_targets: List[Tuple[str, str, int, List[Dict[str, Any]]]] = []
            for target_id, group in sorted(target_groups.items()):
                ordered_group = sorted(
                    group,
                    key=lambda path: (str(path["source_label"]), str(path["middle_label"]), str(path["path_id"])),
                )
                if not (int(connected_min) <= len(ordered_group) <= int(connected_max)):
                    continue
                answer = sum(int(path["second_value"]) for path in ordered_group)
                if int(answer_min) <= int(answer) <= int(answer_max):
                    eligible_targets.append((str(target_id), str(ordered_group[0]["target_label"]), int(answer), ordered_group))
            if not eligible_targets:
                raise ValueError(f"no eligible target incoming total for {TASK_ID}")
            selected_node_id, target_label, answer, selected_paths = eligible_targets[int(rng.randrange(len(eligible_targets)))]
            evidence_segment_ids = [f"{path['path_id']}:middle_target" for path in selected_paths]
            terms = " + ".join(str(int(path["second_value"])) for path in selected_paths)
            return {
                "answer_value": int(answer),
                "query_path_ids": [str(path["path_id"]) for path in selected_paths],
                "evidence_segment_ids": list(evidence_segment_ids),
                "source_label": "",
                "middle_label": "",
                "target_id": str(selected_node_id),
                "target_label": str(target_label),
                "node_side": "target_incoming",
                "connected_count": int(len(selected_paths)),
                "node_side_total": int(answer),
                "route_count": int(len(selected_paths)),
                "expression": str(terms),
                "path_details": [dict(path) for path in selected_paths],
            }

    raise ValueError(f"unsupported query_variant: {query_variant}")


def _construct_dataset(
    *,
    query_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    if str(scene_variant) != "three_column_sankey":
        raise ValueError(f"unsupported scene_variant: {scene_variant}")

    source_count, source_count_bounds = _resolve_count(
        params,
        min_key="source_count_min",
        max_key="source_count_max",
        explicit_key="source_count",
        fallback_min=3,
        fallback_max=4,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.source_count",
    )
    middle_count, middle_count_bounds = _resolve_count(
        params,
        min_key="middle_count_min",
        max_key="middle_count_max",
        explicit_key="middle_count",
        fallback_min=3,
        fallback_max=5,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.middle_count",
    )
    target_count, target_count_bounds = _resolve_count(
        params,
        min_key="target_count_min",
        max_key="target_count_max",
        explicit_key="target_count",
        fallback_min=3,
        fallback_max=4,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_count",
    )
    path_count, path_count_bounds = _resolve_count(
        params,
        min_key="path_count_min",
        max_key="path_count_max",
        explicit_key="path_count",
        fallback_min=9,
        fallback_max=14,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.path_count",
    )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="link_value_min",
        max_key="link_value_max",
        fallback_min=5,
        fallback_max=35,
        context=f"{TASK_ID} link values",
    )
    if int(path_count) > int(source_count) * int(middle_count) * int(target_count):
        raise ValueError(f"path_count {path_count} exceeds possible unique paths")
    max_paths_per_node_side = max(0, _gen_int_param(params, "max_paths_per_node_side", 2))

    for attempt in range(80):
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset_attempt", int(attempt))
        sources, middles, targets = _sample_labels(
            rng,
            source_count=int(source_count),
            middle_count=int(middle_count),
            target_count=int(target_count),
        )
        try:
            paths, query_seed_params = _sample_paths(
                query_variant=str(query_variant),
                params=params,
                instance_seed=int(instance_seed),
                rng=rng,
                sources=sources,
                middles=middles,
                targets=targets,
                path_count=int(path_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        except ValueError:
            continue
        if not _paths_respect_side_limit(paths, max_paths_per_node_side=int(max_paths_per_node_side)):
            continue
        try:
            query = _choose_query(
                query_variant=str(query_variant),
                params=params,
                instance_seed=int(instance_seed),
                rng=rng,
                paths=paths,
                query_seed_params=query_seed_params,
            )
        except ValueError:
            continue
        return {
            "scene_title": str(rng.choice(_TITLE_OPTIONS)),
            "query_variant": str(query_variant),
            "scene_variant": str(scene_variant),
            "sources": [dict(node) for node in sources],
            "middles": [dict(node) for node in middles],
            "targets": [dict(node) for node in targets],
            "paths": [dict(path) for path in paths],
            "paths_by_id": {str(path["path_id"]): dict(path) for path in paths},
            "source_count": int(source_count),
            "middle_count": int(middle_count),
            "target_count": int(target_count),
            "path_count": int(path_count),
            "max_paths_per_node_side": int(max_paths_per_node_side),
            "path_side_counts": _path_side_counts(paths),
            "source_count_bounds": tuple(int(value) for value in source_count_bounds),
            "middle_count_bounds": tuple(int(value) for value in middle_count_bounds),
            "target_count_bounds": tuple(int(value) for value in target_count_bounds),
            "path_count_bounds": tuple(int(value) for value in path_count_bounds),
            "value_min": int(value_min),
            "value_max": int(value_max),
            "answer_value": int(query["answer_value"]),
            "query": dict(query),
        }
    raise ValueError(f"failed to construct feasible {TASK_ID} instance")


def _json_examples(query_variant: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_variant)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"]),
    )


class ChartsFlowSankeyPathValueTask:
    """Answer path arithmetic questions over a weighted Sankey-style chart."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "flow"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_variant_probabilities=query_variant_probabilities)
        dataset = _construct_dataset(
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            params=support_params,
            instance_seed=int(instance_seed),
        )
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(render_style_params)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = _render_sankey(
            background,
            scene_title=str(dataset["scene_title"]),
            sources=list(dataset["sources"]),
            middles=list(dataset["middles"]),
            targets=list(dataset["targets"]),
            paths=list(dataset["paths"]),
            render_params=render_params,
            value_min=int(dataset["value_min"]),
            value_max=int(dataset["value_max"]),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
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
                "object_description_three_column_sankey",
                "answer_hint",
                "evidence_hint",
                "json_example_source_to_target_total_flow",
                "json_example_path_bottleneck_value",
                "json_example_path_flow_difference",
                "json_example_source_outgoing_total_flow",
                "json_example_target_incoming_total_flow",
                "json_example_answer_only_source_to_target_total_flow",
                "json_example_answer_only_path_bottleneck_value",
                "json_example_answer_only_path_flow_difference",
                "json_example_answer_only_source_outgoing_total_flow",
                "json_example_answer_only_target_incoming_total_flow",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_variant), prompt_defaults=prompt_defaults)
        query = dict(dataset["query"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_three_column_sankey"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "source_label": str(query.get("source_label", "")),
                "middle_label": str(query.get("middle_label", "")),
                "target_label": str(query.get("target_label", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_segment_ids = [str(segment_id) for segment_id in query["evidence_segment_ids"]]
        evidence_bboxes = [list(rendered_scene.segment_label_bbox_map[str(segment_id)]) for segment_id in evidence_segment_ids]
        projected_evidence = {
            "bbox_set": list(evidence_bboxes),
            "pixel_bbox_set": list(evidence_bboxes),
            "segment_ids": list(evidence_segment_ids),
            "segment_label_bbox_map": {
                str(segment_id): list(rendered_scene.segment_label_bbox_map[str(segment_id)])
                for segment_id in evidence_segment_ids
            },
            "segment_bbox_map": {
                str(segment_id): list(rendered_scene.segment_bbox_map[str(segment_id)])
                for segment_id in evidence_segment_ids
            },
        }
        answer_gt = TypedValue(type="integer", value=int(dataset["answer_value"]))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        evidence_scan = normalize_int_with_bounds(len(evidence_segment_ids), [2, 8])
        path_scan = normalize_int_with_bounds(int(dataset["path_count"]), list(dataset["path_count_bounds"]))
        node_bounds = [
            int(dataset["source_count_bounds"][0]) + int(dataset["middle_count_bounds"][0]) + int(dataset["target_count_bounds"][0]),
            int(dataset["source_count_bounds"][1]) + int(dataset["middle_count_bounds"][1]) + int(dataset["target_count_bounds"][1]),
        ]
        node_scan = normalize_int_with_bounds(
            int(dataset["source_count"]) + int(dataset["middle_count"]) + int(dataset["target_count"]),
            node_bounds,
        )
        visual_scan = clamp_unit_interval((0.70 * float(path_scan)) + (0.30 * float(node_scan)))
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_VARIANT[str(query_variant)])
            + (0.10 * float(evidence_scan))
        )
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        query_params = {
            "query_variant": str(query_variant),
            "scene_variant": str(scene_variant),
            "query_variant_probabilities": dict(query_variant_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "source_count": int(dataset["source_count"]),
            "middle_count": int(dataset["middle_count"]),
            "target_count": int(dataset["target_count"]),
            "path_count": int(dataset["path_count"]),
            "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
            "path_side_counts": dict(dataset["path_side_counts"]),
            "source_label": str(query.get("source_label", "")),
            "middle_label": str(query.get("middle_label", "")),
            "target_label": str(query.get("target_label", "")),
            "route_count": int(query.get("route_count", 1)),
            "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
            "incoming_total": int(query["incoming_total"]) if "incoming_total" in query else None,
            "outgoing_total": int(query["outgoing_total"]) if "outgoing_total" in query else None,
            "node_side": str(query.get("node_side", "")),
            "connected_count": int(query["connected_count"]) if "connected_count" in query else None,
            "node_side_total": int(query["node_side_total"]) if "node_side_total" in query else None,
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_sankey",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                "answer_value": int(dataset["answer_value"]),
                "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
                "evidence_segment_ids": list(evidence_segment_ids),
                "incoming_total": int(query["incoming_total"]) if "incoming_total" in query else None,
                "outgoing_total": int(query["outgoing_total"]) if "outgoing_total" in query else None,
            },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "source_count": int(dataset["source_count"]),
                "middle_count": int(dataset["middle_count"]),
                "target_count": int(dataset["target_count"]),
                "path_count": int(dataset["path_count"]),
                "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "min_flow_width_px": int(render_params.min_flow_width_px),
                "max_flow_width_px": int(render_params.max_flow_width_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "node_bboxes_px": dict(rendered_scene.node_bbox_map),
                "node_label_bboxes_px": dict(rendered_scene.node_label_bbox_map),
                "segment_bboxes_px": dict(rendered_scene.segment_bbox_map),
                "segment_label_bboxes_px": dict(rendered_scene.segment_label_bbox_map),
                "segment_centers_px": dict(rendered_scene.segment_center_map),
            },
            "execution_trace": {
                "query_variant": str(query_variant),
                "scene_variant": str(scene_variant),
                "query_variant_probabilities": dict(query_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "sankey_node_side_total_value"
                if str(query_variant) in NODE_SIDE_TOTAL_QUERY_VARIANTS
                else "sankey_path_value",
                "scene_title": str(dataset["scene_title"]),
                "sources": [dict(node) for node in dataset["sources"]],
                "middles": [dict(node) for node in dataset["middles"]],
                "targets": [dict(node) for node in dataset["targets"]],
                "paths": [dict(path) for path in dataset["paths"]],
                "paths_by_id": {str(key): dict(value) for key, value in dict(dataset["paths_by_id"]).items()},
                "source_count": int(dataset["source_count"]),
                "middle_count": int(dataset["middle_count"]),
                "target_count": int(dataset["target_count"]),
                "path_count": int(dataset["path_count"]),
                "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
                "path_side_counts": dict(dataset["path_side_counts"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "answer_value": int(dataset["answer_value"]),
                "answer_type": "integer",
                "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
                "evidence_segment_ids": list(evidence_segment_ids),
                "query_path_details": [dict(path) for path in query["path_details"]],
                "incoming_total": int(query["incoming_total"]) if "incoming_total" in query else None,
                "outgoing_total": int(query["outgoing_total"]) if "outgoing_total" in query else None,
                "node_side": str(query.get("node_side", "")),
                "connected_count": int(query["connected_count"]) if "connected_count" in query else None,
                "node_side_total": int(query["node_side_total"]) if "node_side_total" in query else None,
                "expression": str(query["expression"]),
                "evidence_semantics": str(query_variant),
            },
            "witness_symbolic": {
                "type": "sankey_node_side_total_value_witness"
                if str(query_variant) in NODE_SIDE_TOTAL_QUERY_VARIANTS
                else "sankey_path_value_witness",
                "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
                "evidence_segment_ids": list(evidence_segment_ids),
                "answer_value": int(dataset["answer_value"]),
                "expression": str(query["expression"]),
            },
            "projected_evidence": dict(projected_evidence),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(query_variant),
        )


@register_task
class ChartsFlowSankeyPathValuePublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowSankeyPathValueTask,
):
    """Return one sampled path value from a Sankey flow chart."""

    task_id = "task_charts__sankey__path_value"
    allowed_query_variants = PATH_VALUE_QUERY_VARIANTS


@register_task
class ChartsFlowSankeyNodeSideTotalValuePublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowSankeyPathValueTask,
):
    """Return a one-sided total for a source or target Sankey node."""

    task_id = "task_charts__sankey__node_side_total_value"
    allowed_query_variants = NODE_SIDE_TOTAL_QUERY_VARIANTS


__all__ = [
    "ChartsFlowSankeyNodeSideTotalValuePublicTask",
    "ChartsFlowSankeyPathValueTask",
    "ChartsFlowSankeyPathValuePublicTask",
    "NODE_SIDE_TOTAL_QUERY_VARIANTS",
    "PATH_VALUE_QUERY_VARIANTS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_VARIANTS",
]
