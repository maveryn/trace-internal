"""Scientific axis-frame tick reasoning chart tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from .....core.seed import spawn_rng
from .....core.scene_config import get_scene_defaults
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ....shared.text_legibility import draw_text_traced
from ....shared.text_rendering import load_font
from ...shared.visual_defaults import (
    load_chart_scene_background_defaults,
    load_chart_scene_noise_defaults,
)


TASK_ID = "charts_scientific_axis_frame_query_base"
SCENE_ID = "scientific_axis_frame"

TICK_SPACING_QUERY_IDS: Tuple[str, ...] = (
    "x_tick_spacing_value",
    "y_tick_spacing_value",
)
AXIS_SPAN_QUERY_IDS: Tuple[str, ...] = (
    "x_axis_span_value",
    "y_axis_span_value",
)

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "scientific_axis_frame")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="scientific_axis_frame")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="scientific_axis_frame", apply_prob=0.0)

RGB = Tuple[int, int, int]
BBox = List[float]

_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "x_tick_spacing_value": 0.36,
    "y_tick_spacing_value": 0.40,
    "x_axis_span_value": 0.42,
    "y_axis_span_value": 0.46,
}


@dataclass(frozen=True)
class _AxisSpec:
    axis: str
    values: Tuple[int, ...]
    start: int
    step: int
    count: int


@dataclass(frozen=True)
class _Query:
    query_id: str
    axis: str
    answer: int
    answer_type: str
    annotation_keys: Tuple[str, ...]
    tick_values: Dict[str, int]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    x_axis: _AxisSpec
    y_axis: _AxisSpec
    query: _Query
    series_points: Tuple[Tuple[float, float], ...]
    query_id_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    margin_left_px: int
    margin_right_px: int
    margin_top_px: int
    margin_bottom_px: int
    title_font_size_px: int
    axis_label_font_size_px: int
    tick_font_size_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    line_width_px: int
    point_radius_px: int
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    axis_rgb: RGB
    grid_rgb: RGB
    panel_fill_rgb: RGB
    panel_outline_rgb: RGB
    series_rgb: RGB
    marker_rgb: RGB
    font_family: str
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    tick_label_bboxes_px: Dict[str, BBox]
    axis_label_bboxes_px: Dict[str, BBox]
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _point(x: float, y: float) -> List[float]:
    return [round(float(x), 3), round(float(y), 3)]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(
        resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            str(key),
            int(fallback),
            instance_seed=_render_style_seed(params),
            namespace=TASK_ID,
        )
    )


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _selection_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return abs(int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))))


def _balanced_choice(values: Sequence[Any], params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> Any:
    support = tuple(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    index = _selection_index(params, instance_seed=int(instance_seed), namespace=str(namespace))
    return support[int(index) % len(support)]


def _tick_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="axis_frame_tick_count_min",
        max_key="axis_frame_tick_count_max",
        fallback_min=4,
        fallback_max=8,
        context=f"generation defaults for {TASK_ID}",
    )
    return max(3, int(low)), max(max(3, int(low)), int(high))


def _tick_step_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="axis_frame_tick_step_min",
        max_key="axis_frame_tick_step_max",
        fallback_min=2,
        fallback_max=12,
        context=f"generation defaults for {TASK_ID}",
    )
    return max(1, int(low)), max(max(1, int(low)), int(high))


def _axis_start(params: Mapping[str, Any], *, instance_seed: int, axis: str, step: int) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="axis_frame_start_min",
        max_key="axis_frame_start_max",
        fallback_min=-24,
        fallback_max=24,
        context=f"generation defaults for {TASK_ID}",
    )
    support = [int(value) for value in range(int(low), int(high) + 1) if int(value) % max(1, int(step)) == 0]
    if not support:
        support = [0]
    return int(_balanced_choice(support, params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.{axis}.start.{int(step)}"))


def _axis_spec(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    axis: str,
    forced_step: int | None = None,
    forced_count: int | None = None,
) -> _AxisSpec:
    count_min, count_max = _tick_count_bounds(params)
    step_min, step_max = _tick_step_bounds(params)
    count = int(forced_count) if forced_count is not None else int(
        _balanced_choice(
            tuple(range(int(count_min), int(count_max) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{axis}.tick_count",
        )
    )
    step = int(forced_step) if forced_step is not None else int(
        _balanced_choice(
            tuple(range(int(step_min), int(step_max) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{axis}.tick_step",
        )
    )
    if int(count) < 3:
        raise ValueError("axis tick count must be at least 3")
    if int(step) <= 0:
        raise ValueError("axis tick step must be positive")
    start = _axis_start(params, instance_seed=int(instance_seed), axis=str(axis), step=int(step))
    values = tuple(int(start) + (int(index) * int(step)) for index in range(int(count)))
    return _AxisSpec(axis=str(axis), values=values, start=int(start), step=int(step), count=int(count))


def _span_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    count_min, count_max = _tick_count_bounds(params)
    step_min, step_max = _tick_step_bounds(params)
    support = sorted({int(step) * (int(count) - 1) for count in range(count_min, count_max + 1) for step in range(step_min, step_max + 1)})
    return tuple(int(value) for value in support)


def _span_pairs_for(params: Mapping[str, Any], span: int) -> Tuple[Tuple[int, int], ...]:
    count_min, count_max = _tick_count_bounds(params)
    step_min, step_max = _tick_step_bounds(params)
    pairs = [
        (int(count), int(step))
        for count in range(count_min, count_max + 1)
        for step in range(step_min, step_max + 1)
        if int(step) * (int(count) - 1) == int(span)
    ]
    return tuple(pairs)


def _decorative_points(dataset_seed: int, x_axis: _AxisSpec, y_axis: _AxisSpec) -> Tuple[Tuple[float, float], ...]:
    rng = spawn_rng(int(dataset_seed), f"{TASK_ID}.decorative_series")
    points: List[Tuple[float, float]] = []
    y_span = max(1, int(y_axis.values[-1]) - int(y_axis.values[0]))
    base = float(y_axis.values[0]) + (0.48 * float(y_span))
    amplitude = 0.26 * float(y_span)
    phase = float(rng.random()) * math.pi
    for index, x_value in enumerate(x_axis.values):
        y_value = base + (math.sin(float(index) * 0.9 + phase) * amplitude) + float(rng.randint(-2, 2))
        y_value = max(float(y_axis.values[0]), min(float(y_axis.values[-1]), y_value))
        points.append((float(x_value), float(y_value)))
    return tuple(points)


def _build_dataset(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    axis = "x" if str(query_id).startswith("x_") else "y"
    if str(query_id) in set(TICK_SPACING_QUERY_IDS):
        step_min, step_max = _tick_step_bounds(params)
        target_step = int(
            _balanced_choice(
                tuple(range(int(step_min), int(step_max) + 1)),
                params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.tick_spacing.answer",
            )
        )
        target_axis = _axis_spec(params, instance_seed=int(instance_seed), axis=str(axis), forced_step=int(target_step))
    else:
        support = _span_support(params)
        if not support:
            raise ValueError("axis span support is empty")
        target_span = int(
            _balanced_choice(
                support,
                params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.axis_span.answer",
            )
        )
        pairs = _span_pairs_for(params, int(target_span))
        count, step = _balanced_choice(
            pairs,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.axis_span.pair.{int(target_span)}",
        )
        target_axis = _axis_spec(
            params,
            instance_seed=int(instance_seed),
            axis=str(axis),
            forced_step=int(step),
            forced_count=int(count),
        )

    other_axis_name = "y" if str(axis) == "x" else "x"
    other_axis = _axis_spec(params, instance_seed=int(instance_seed) + 17, axis=other_axis_name)
    x_axis = target_axis if str(axis) == "x" else other_axis
    y_axis = target_axis if str(axis) == "y" else other_axis

    if str(query_id) in set(TICK_SPACING_QUERY_IDS):
        target_axis_values = x_axis.values if axis == "x" else y_axis.values
        pair_index = int(
            _balanced_choice(
                tuple(range(0, len(target_axis_values) - 1)),
                params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.tick_spacing.pair_index",
            )
        )
        first_value = int(target_axis_values[int(pair_index)])
        next_value = int(target_axis_values[int(pair_index) + 1])
        answer = int(next_value - first_value)
        annotation_keys = (
            f"{axis}:{first_value}",
            f"{axis}:{next_value}",
        )
        trace = {
            "axis": str(axis),
            "axis_name": f"{axis}-axis",
            "first_tick_value": int(first_value),
            "next_tick_value": int(next_value),
            "tick_pair_index": int(pair_index),
            "program": "difference(next_adjacent_tick_value, first_tick_value)",
        }
        tick_values = {"first_tick": int(first_value), "next_tick": int(next_value)}
    else:
        target_axis_values = x_axis.values if axis == "x" else y_axis.values
        min_value = int(min(target_axis_values))
        max_value = int(max(target_axis_values))
        answer = int(max_value - min_value)
        annotation_keys = (
            f"{axis}:{min_value}",
            f"{axis}:{max_value}",
        )
        trace = {
            "axis": str(axis),
            "axis_name": f"{axis}-axis",
            "min_tick_value": int(min_value),
            "max_tick_value": int(max_value),
            "program": "difference(max_visible_tick_value, min_visible_tick_value)",
        }
        tick_values = {"min_tick": int(min_value), "max_tick": int(max_value)}

    return _Dataset(
        x_axis=x_axis,
        y_axis=y_axis,
        query=_Query(
            query_id=str(query_id),
            axis=str(axis),
            answer=int(answer),
            answer_type="integer",
            annotation_keys=tuple(annotation_keys),
            tick_values=dict(tick_values),
            trace=dict(trace),
        ),
        series_points=_decorative_points(int(instance_seed), x_axis, y_axis),
        query_id_probabilities=dict(query_probabilities),
    )


def _resolve_render_params(params: Mapping[str, Any], *, chart_font_family: str) -> _RenderParams:
    canvas_width = _resolve_int(params, "axis_frame_canvas_width", _resolve_int(params, "canvas_width", 1120))
    canvas_height = _resolve_int(params, "axis_frame_canvas_height", _resolve_int(params, "canvas_height", 760))
    margins = {
        "left": _resolve_int(params, "axis_frame_margin_left_px", 108),
        "right": _resolve_int(params, "axis_frame_margin_right_px", 68),
        "top": _resolve_int(params, "axis_frame_margin_top_px", 90),
        "bottom": _resolve_int(params, "axis_frame_margin_bottom_px", 112),
    }
    left_px, right_px, top_px, bottom_px, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margins["left"]),
        right_px=int(margins["right"]),
        top_px=int(margins["top"]),
        bottom_px=int(margins["bottom"]),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )
    return _RenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        margin_left_px=int(left_px),
        margin_right_px=int(right_px),
        margin_top_px=int(top_px),
        margin_bottom_px=int(bottom_px),
        title_font_size_px=_resolve_int(params, "axis_frame_title_font_size_px", 24),
        axis_label_font_size_px=_resolve_int(params, "axis_frame_axis_label_font_size_px", 17),
        tick_font_size_px=_resolve_int(params, "axis_frame_tick_font_size_px", 16),
        axis_line_width_px=_resolve_int(params, "axis_frame_axis_line_width_px", 2),
        grid_line_width_px=_resolve_int(params, "axis_frame_grid_line_width_px", 1),
        line_width_px=_resolve_int(params, "axis_frame_line_width_px", 3),
        point_radius_px=_resolve_int(params, "axis_frame_point_radius_px", 4),
        text_rgb=_resolve_rgb(params, "axis_frame_text_rgb", (38, 44, 54)),
        muted_text_rgb=_resolve_rgb(params, "axis_frame_muted_text_rgb", (86, 94, 108)),
        text_stroke_rgb=_resolve_rgb(params, "axis_frame_text_stroke_rgb", (255, 255, 255)),
        axis_rgb=_resolve_rgb(params, "axis_frame_axis_rgb", (55, 62, 72)),
        grid_rgb=_resolve_rgb(params, "axis_frame_grid_rgb", (218, 224, 232)),
        panel_fill_rgb=_resolve_rgb(params, "axis_frame_panel_fill_rgb", (255, 255, 255)),
        panel_outline_rgb=_resolve_rgb(params, "axis_frame_panel_outline_rgb", (188, 198, 212)),
        series_rgb=_resolve_rgb(params, "axis_frame_series_rgb", (62, 102, 156)),
        marker_rgb=_resolve_rgb(params, "axis_frame_marker_rgb", (203, 91, 60)),
        font_family=str(chart_font_family),
        layout_jitter_meta=dict(jitter_meta),
    )


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    *,
    anchor: str | None = None,
    stroke_width: int = 0,
) -> BBox:
    try:
        box = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, anchor=anchor, stroke_width=max(0, int(stroke_width)))
        return _bbox(box)
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return _bbox([float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)])


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 0,
) -> BBox:
    try:
        box = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        width = float(box[2] - box[0])
        height = float(box[3] - box[1])
        x = float(center[0]) - 0.5 * width - float(box[0])
        y = float(center[1]) - 0.5 * height - float(box[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        x = float(center[0]) - 0.5 * float(width)
        y = float(center[1]) - 0.5 * float(height)
    draw_text_traced(
        draw,
        (float(x), float(y)),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
        role="readout",
        required=False,
    )
    return _text_bbox(draw, (float(x), float(y)), str(text), font, stroke_width=max(0, int(stroke_width)))


def _scale_x(value: float, *, x_axis: _AxisSpec, plot_left: float, plot_right: float) -> float:
    span = max(1.0, float(x_axis.values[-1]) - float(x_axis.values[0]))
    return float(plot_left) + ((float(value) - float(x_axis.values[0])) / span) * float(plot_right - plot_left)


def _scale_y(value: float, *, y_axis: _AxisSpec, plot_top: float, plot_bottom: float) -> float:
    span = max(1.0, float(y_axis.values[-1]) - float(y_axis.values[0]))
    return float(plot_bottom) - ((float(value) - float(y_axis.values[0])) / span) * float(plot_bottom - plot_top)


def _expanded_bbox(box: Sequence[float], pad: float) -> BBox:
    return _bbox([float(box[0]) - float(pad), float(box[1]) - float(pad), float(box[2]) + float(pad), float(box[3]) + float(pad)])


def _draw_highlight(draw: ImageDraw.ImageDraw, bbox: Sequence[float], *, color: RGB) -> None:
    x0, y0, x1, y1 = _expanded_bbox(bbox, 5.0)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=tuple(color), width=3)


def _render_dataset(
    dataset: _Dataset,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    chart_font_family: str,
) -> _Rendered:
    render_params = _resolve_render_params(params, chart_font_family=str(chart_font_family))
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        fallback_color=(247, 248, 250),
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    axis_label_font = load_font(int(render_params.axis_label_font_size_px), bold=True)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)

    plot_left = float(render_params.margin_left_px)
    plot_top = float(render_params.margin_top_px)
    plot_right = float(render_params.canvas_width - render_params.margin_right_px)
    plot_bottom = float(render_params.canvas_height - render_params.margin_bottom_px)
    plot_bbox = _bbox([plot_left, plot_top, plot_right, plot_bottom])
    draw.rectangle(plot_bbox, fill=render_params.panel_fill_rgb, outline=render_params.panel_outline_rgb, width=1)

    title_options = params.get("axis_frame_title_options", group_default(_RENDER_DEFAULTS, "axis_frame_title_options", ("Measured Response",)))
    titles = tuple(str(value) for value in title_options) if isinstance(title_options, Sequence) and not isinstance(title_options, (str, bytes)) else ("Measured Response",)
    title = str(_balanced_choice(titles, params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.title"))
    title_bbox = _draw_centered(
        draw,
        center=(0.5 * (plot_left + plot_right), max(24.0, plot_top - 42.0)),
        text=str(title),
        font=title_font,
        fill=render_params.text_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )

    tick_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    for value in dataset.y_axis.values:
        y = _scale_y(float(value), y_axis=dataset.y_axis, plot_top=plot_top, plot_bottom=plot_bottom)
        draw.line([(plot_left, y), (plot_right, y)], fill=render_params.grid_rgb, width=int(render_params.grid_line_width_px))
        draw.line([(plot_left - 7.0, y), (plot_left, y)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))
        bbox = _draw_centered(
            draw,
            center=(plot_left - 34.0, y),
            text=str(int(value)),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        key = f"y:{int(value)}"
        tick_bboxes[key] = bbox
        entities.append({"entity_id": key, "entity_type": "axis_tick_label", "bbox_px": list(bbox), "attrs": {"axis": "y", "value": int(value)}})

    for value in dataset.x_axis.values:
        x = _scale_x(float(value), x_axis=dataset.x_axis, plot_left=plot_left, plot_right=plot_right)
        draw.line([(x, plot_top), (x, plot_bottom)], fill=render_params.grid_rgb, width=int(render_params.grid_line_width_px))
        draw.line([(x, plot_bottom), (x, plot_bottom + 7.0)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))
        bbox = _draw_centered(
            draw,
            center=(x, plot_bottom + 28.0),
            text=str(int(value)),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        key = f"x:{int(value)}"
        tick_bboxes[key] = bbox
        entities.append({"entity_id": key, "entity_type": "axis_tick_label", "bbox_px": list(bbox), "attrs": {"axis": "x", "value": int(value)}})

    draw.line([(plot_left, plot_top), (plot_left, plot_bottom)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))
    draw.line([(plot_left, plot_bottom), (plot_right, plot_bottom)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))

    x_axis_label_bbox = _draw_centered(
        draw,
        center=(0.5 * (plot_left + plot_right), plot_bottom + 66.0),
        text="x",
        font=axis_label_font,
        fill=render_params.text_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )
    y_axis_label_bbox = _draw_centered(
        draw,
        center=(plot_left - 70.0, 0.5 * (plot_top + plot_bottom)),
        text="y",
        font=axis_label_font,
        fill=render_params.text_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )

    series_px = [
        (
            _scale_x(float(x), x_axis=dataset.x_axis, plot_left=plot_left, plot_right=plot_right),
            _scale_y(float(y), y_axis=dataset.y_axis, plot_top=plot_top, plot_bottom=plot_bottom),
        )
        for x, y in dataset.series_points
    ]
    if len(series_px) >= 2:
        draw.line(series_px, fill=render_params.series_rgb, width=int(render_params.line_width_px), joint="curve")
    for x, y in series_px:
        radius = float(render_params.point_radius_px)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=render_params.series_rgb, outline=render_params.panel_fill_rgb, width=1)

    if str(dataset.query.query_id) in set(TICK_SPACING_QUERY_IDS):
        for key in dataset.query.annotation_keys:
            _draw_highlight(draw, tick_bboxes[str(key)], color=render_params.marker_rgb)

    image, noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    render_meta = {
        "background_style": dict(background_meta),
        "post_image_noise": dict(noise_meta),
        "chart_font_family": str(chart_font_family),
        "layout_jitter": dict(render_params.layout_jitter_meta),
        "rendering_contract": "scientific_axis_frame_numeric_ticks",
        "title_bbox_px": list(title_bbox),
    }
    return _Rendered(
        image=image,
        entities=tuple(dict(entity) for entity in entities),
        plot_bbox_px=list(plot_bbox),
        tick_label_bboxes_px=dict(tick_bboxes),
        axis_label_bboxes_px={"x": list(x_axis_label_bbox), "y": list(y_axis_label_bbox)},
        render_meta=dict(render_meta),
    )


