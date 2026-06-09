"""Multi-series scatter readout chart tasks."""

from __future__ import annotations

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
from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import load_font, temporary_default_font_family
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.unanswerable import (
    UNANSWERABLE_ANSWER,
    absence_proof,
    choose_missing_label,
    should_use_unanswerable_branch,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_scatter_series_readout_base"
SCENE_ID = "scatter_readout"
_EXTREMUM_QUERY_IDS: Tuple[str, ...] = (
    "series_highest_x_label",
    "series_lowest_x_label",
)
_LOOKUP_QUERY_IDS: Tuple[str, ...] = (
    "series_pair_value_gap_at_x",
    "series_y_anchor_other_series_value",
)
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = _EXTREMUM_QUERY_IDS + _LOOKUP_QUERY_IDS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("marker_scatter",)

SUPPORTED_QUERY_IDS = _SUPPORTED_QUERY_IDS
SUPPORTED_SCENE_VARIANTS = _SUPPORTED_SCENE_VARIANTS

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "scatter")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="scatter")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="scatter", apply_prob=0.0)

_MONTH_LABELS: Tuple[str, ...] = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct")
_MARKER_SHAPES: Tuple[str, ...] = ("circle", "square", "diamond", "triangle", "ring")
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "series_highest_x_label": 0.56,
    "series_lowest_x_label": 0.56,
    "series_pair_value_gap_at_x": 0.70,
    "series_y_anchor_other_series_value": 0.74,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {"marker_scatter": 0.60}

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class _Point:
    point_id: str
    series_label: str
    x_label: str
    x_index: int
    y_value: int


@dataclass(frozen=True)
class _Series:
    label: str
    color_rgb: RGB
    marker_shape: str
    points: Tuple[_Point, ...]


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    target_series_label: str
    target_point_id: str
    annotation_point_ids: Tuple[str, ...]
    annotation_x_label: str
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    x_axis_title: str
    y_axis_title: str
    x_labels: Tuple[str, ...]
    series: Tuple[_Series, ...]
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    tick_length_px: int
    point_radius_px: int
    tick_font_size_px: int
    label_font_size_px: int
    value_font_size_px: int
    legend_font_size_px: int
    title_font_size_px: int
    legend_gap_px: int
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    text_color_rgb: RGB
    text_stroke_rgb: RGB
    plot_fill_rgb: RGB
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    point_bboxes: Dict[str, List[float]]
    value_label_bboxes: Dict[str, List[float]]
    point_annotation_bboxes: Dict[str, List[float]]
    x_label_bboxes: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


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


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("series_palette_rgb", _RENDER_DEFAULTS.get("series_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            colors.append(_as_rgb(item, (48, 105, 180)))
    if len(colors) >= 5:
        return tuple(colors[:5])
    return (
        (45, 103, 178),
        (211, 86, 70),
        (55, 145, 92),
        (133, 86, 175),
        (213, 136, 41),
    )


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    margin_left = _resolve_int(params, "readout_plot_margin_left_px", 112)
    margin_right = _resolve_int(params, "readout_plot_margin_right_px", 370)
    margin_top = _resolve_int(params, "readout_plot_margin_top_px", 78)
    margin_bottom = _resolve_int(params, "readout_plot_margin_bottom_px", 126)
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    return _RenderParams(
        canvas_width=_resolve_int(params, "readout_canvas_width", 1440),
        canvas_height=_resolve_int(params, "readout_canvas_height", 820),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=_resolve_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_resolve_int(params, "grid_line_width_px", 1),
        tick_length_px=_resolve_int(params, "tick_length_px", 8),
        point_radius_px=_resolve_int(params, "readout_point_radius_px", 8),
        tick_font_size_px=_resolve_int(params, "readout_tick_font_size_px", 17),
        label_font_size_px=_resolve_int(params, "readout_axis_label_font_size_px", 19),
        value_font_size_px=_resolve_int(params, "readout_value_font_size_px", 16),
        legend_font_size_px=_resolve_int(params, "readout_legend_font_size_px", 21),
        title_font_size_px=_resolve_int(params, "readout_title_font_size_px", 26),
        legend_gap_px=_resolve_int(params, "readout_legend_gap_px", 80),
        axis_color_rgb=_resolve_rgb(params, "axis_color_rgb", (65, 70, 78)),
        grid_color_rgb=_resolve_rgb(params, "grid_color_rgb", (224, 228, 235)),
        text_color_rgb=_resolve_rgb(params, "text_color_rgb", (35, 38, 45)),
        text_stroke_rgb=_resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        plot_fill_rgb=_resolve_rgb(params, "plot_fill_rgb", (255, 255, 255)),
        panel_fill_rgb=_resolve_rgb(params, "panel_fill_rgb", (252, 253, 255)),
        panel_border_rgb=_resolve_rgb(params, "panel_border_rgb", (203, 209, 219)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def _sample_x_axis(*, params: Mapping[str, Any], instance_seed: int, x_count: int) -> Tuple[str, Tuple[str, ...]]:
    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.x_axis")
    axis_kinds = ("year", "month", "period")
    axis_kind = str(params.get("x_axis_kind", axis_kinds[axis_rng.randint(0, len(axis_kinds) - 1)]))
    if axis_kind == "month":
        return "Month", tuple(_MONTH_LABELS[: int(x_count)])
    if axis_kind == "period":
        start = axis_rng.randint(1, 9)
        return "Time", tuple(f"T{int(start) + index}" for index in range(int(x_count)))
    start_year = axis_rng.randint(2010, 2027 - int(x_count))
    return "Year", tuple(str(int(start_year) + index) for index in range(int(x_count)))


def _sample_series_labels(*, series_count: int, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.series_labels")
    labels = resolve_chart_entity_labels(
        rng,
        count=int(series_count),
        min_chars=2,
        max_chars=7,
        allow_spaces=False,
    ).labels
    return tuple(str(value) for value in labels)


def _sample_y_matrix(*, series_count: int, x_count: int, params: Mapping[str, Any], instance_seed: int) -> List[List[int]]:
    value_min = _gen_int(params, "readout_y_value_min", 10)
    value_max = _gen_int(params, "readout_y_value_max", 90)
    min_gap_at_x = _gen_int(params, "readout_min_series_gap_at_x", 6)
    pool = list(range(int(value_min), int(value_max) + 1))
    if len(pool) < int(x_count):
        raise ValueError("readout y-value range is too small for unique per-series values")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.y_values")
    for _ in range(500):
        rows: List[List[int]] = []
        for _series_index in range(int(series_count)):
            shuffled = list(pool)
            rng.shuffle(shuffled)
            rows.append([int(value) for value in shuffled[: int(x_count)]])
        valid = True
        for x_index in range(int(x_count)):
            column = sorted(row[int(x_index)] for row in rows)
            if any(int(b) - int(a) < int(min_gap_at_x) for a, b in zip(column, column[1:])):
                valid = False
                break
        if valid:
            return rows
    return rows


def _point_by_id(series: Sequence[_Series], point_id: str) -> _Point:
    for series_item in series:
        for point in series_item.points:
            if str(point.point_id) == str(point_id):
                return point
    raise ValueError(f"unknown point id: {point_id}")


def _build_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    series_min = _gen_int(params, "readout_series_count_min", 3)
    series_max = _gen_int(params, "readout_series_count_max", 5)
    x_count_min = _gen_int(params, "readout_x_count_min", 6)
    x_count_max = _gen_int(params, "readout_x_count_max", 10)
    count_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.counts")
    series_count = int(count_rng.randint(int(series_min), int(series_max)))
    x_count = int(count_rng.randint(int(x_count_min), int(x_count_max)))
    series_count = max(3, min(5, int(series_count)))
    x_count = max(5, min(10, int(x_count)))

    x_axis_title, x_labels = _sample_x_axis(params=params, instance_seed=int(instance_seed), x_count=int(x_count))
    series_labels = _sample_series_labels(series_count=int(series_count), instance_seed=int(instance_seed))
    y_values = _sample_y_matrix(series_count=int(series_count), x_count=int(x_count), params=params, instance_seed=int(instance_seed))
    palette = _palette(params)

    series_items: List[_Series] = []
    for series_index, label in enumerate(series_labels):
        points = tuple(
            _Point(
                point_id=f"s{int(series_index)}_x{int(x_index)}",
                series_label=str(label),
                x_label=str(x_labels[int(x_index)]),
                x_index=int(x_index),
                y_value=int(y_values[int(series_index)][int(x_index)]),
            )
            for x_index in range(int(x_count))
        )
        series_items.append(
            _Series(
                label=str(label),
                color_rgb=tuple(palette[int(series_index) % len(palette)]),
                marker_shape=str(_MARKER_SHAPES[int(series_index) % len(_MARKER_SHAPES)]),
                points=points,
            )
        )

    selection = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_id}.target",
    )
    target_series = series_items[int(selection) % len(series_items)]
    target_point: _Point
    trace: Dict[str, Any] = {
        "query_id": str(query_id),
        "query_id_probabilities": dict(query_probabilities),
        "target_series_label": str(target_series.label),
    }

    if str(query_id) in _EXTREMUM_QUERY_IDS and should_use_unanswerable_branch(
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_id}",
        enabled=bool(params.get("_enable_unanswerable", False)),
    ):
        missing_series = choose_missing_label(
            visible_labels=series_labels,
            candidate_labels=resolve_chart_entity_labels(
                spawn_rng(int(instance_seed), f"{TASK_ID}.missing_series_candidates"),
                count=max(12, len(series_labels) + 6),
                min_chars=2,
                max_chars=7,
                allow_spaces=False,
            ).labels,
            fallback_prefix="Series ",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.missing_series",
        )
        trace.update(
            {
                "target_series_label": str(missing_series),
                "target_point_id": "",
                "target_x_label": "",
                "target_y_value": "",
                "annotation_point_ids": [],
                "annotation_x_label": "",
                "answer": UNANSWERABLE_ANSWER,
                "answer_type": "string",
                "answerability": "unanswerable",
                "absence_proof": absence_proof(
                    requested_item=str(missing_series),
                    visible_candidates=[str(label) for label in series_labels],
                    checked_scope="scatter plot legend series labels",
                    absence_reason="requested series label is not visible in the legend",
                ),
                "extremum": "highest" if str(query_id) == "series_highest_x_label" else "lowest",
            }
        )
        return _Dataset(
            scene_variant="marker_scatter",
            x_axis_title=str(x_axis_title),
            y_axis_title="Value",
            x_labels=tuple(str(value) for value in x_labels),
            series=tuple(series_items),
            query=_Query(
                query_id=str(query_id),
                answer=UNANSWERABLE_ANSWER,
                answer_type="string",
                target_series_label=str(missing_series),
                target_point_id="",
                annotation_point_ids=(),
                annotation_x_label="",
                trace=dict(trace),
            ),
        )

    if str(query_id) == "series_highest_x_label":
        target_point = max(target_series.points, key=lambda point: (int(point.y_value), str(point.x_label)))
        answer: int | str = str(target_point.x_label)
        answer_type = "string"
        annotation_point_ids = (str(target_point.point_id),)
        annotation_x_label = str(target_point.x_label)
        trace["extremum"] = "highest"
    elif str(query_id) == "series_lowest_x_label":
        target_point = min(target_series.points, key=lambda point: (int(point.y_value), str(point.x_label)))
        answer = str(target_point.x_label)
        answer_type = "string"
        annotation_point_ids = (str(target_point.point_id),)
        annotation_x_label = str(target_point.x_label)
        trace["extremum"] = "lowest"
    else:
        target_point = target_series.points[int(selection // max(1, len(series_items))) % len(target_series.points)]
        comparison_candidates = [series for series in series_items if str(series.label) != str(target_series.label)]
        comparison_series = comparison_candidates[
            int(selection // max(1, len(series_items) * len(target_series.points))) % len(comparison_candidates)
        ]
        comparison_point = comparison_series.points[int(target_point.x_index)]
        answer_type = "integer"
        annotation_point_ids = (str(target_point.point_id), str(comparison_point.point_id))
        annotation_x_label = str(target_point.x_label)
        if str(query_id) == "series_pair_value_gap_at_x":
            answer = abs(int(target_point.y_value) - int(comparison_point.y_value))
            trace.update(
                {
                    "comparison_series_label": str(comparison_series.label),
                    "comparison_point_id": str(comparison_point.point_id),
                    "comparison_y_value": int(comparison_point.y_value),
                    "operation": "absolute_difference",
                }
            )
        else:
            answer = int(comparison_point.y_value)
            trace.update(
                {
                    "comparison_series_label": str(comparison_series.label),
                    "comparison_point_id": str(comparison_point.point_id),
                    "comparison_y_value": int(comparison_point.y_value),
                    "operation": "same_x_transfer_value",
                }
            )

    trace.update(
        {
            "target_point_id": str(target_point.point_id),
            "target_x_label": str(target_point.x_label),
            "target_y_value": int(target_point.y_value),
            "annotation_point_ids": list(annotation_point_ids),
            "annotation_x_label": str(annotation_x_label),
            "answer": answer,
            "answer_type": str(answer_type),
        }
    )
    return _Dataset(
        scene_variant="marker_scatter",
        x_axis_title=str(x_axis_title),
        y_axis_title="Value",
        x_labels=tuple(str(value) for value in x_labels),
        series=tuple(series_items),
        query=_Query(
            query_id=str(query_id),
            answer=answer,
            answer_type=str(answer_type),
            target_series_label=str(target_series.label),
            target_point_id=str(target_point.point_id),
            annotation_point_ids=tuple(str(point_id) for point_id in annotation_point_ids),
            annotation_x_label=str(annotation_x_label),
            trace=dict(trace),
        ),
    )


def _draw_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: Tuple[float, float],
    *,
    font: Any,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 0,
    anchor: str | None = None,
) -> List[float]:
    kwargs: Dict[str, Any] = {
        "font": font,
        "fill": fill,
        "stroke_fill": stroke_fill,
        "stroke_width": int(stroke_width),
    }
    if anchor is not None:
        kwargs["anchor"] = str(anchor)
    try:
        draw_text_traced(draw, (float(xy[0]), float(xy[1])), str(text), **kwargs, role="readout", required=False)
        return _bbox(draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=int(stroke_width), anchor=anchor))
    except Exception:
        kwargs.pop("anchor", None)
        draw_text_traced(draw, (float(xy[0]), float(xy[1])), str(text), **kwargs, role="readout", required=False)
        width, height = draw.textsize(str(text), font=font)
        return _bbox([float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)])


def _point_xy(point: _Point, *, x_count: int, plot_bbox: Sequence[float]) -> Tuple[float, float]:
    left, top, right, bottom = [float(value) for value in plot_bbox]
    if int(x_count) <= 1:
        x_fraction = 0.5
    else:
        x_fraction = float(point.x_index) / float(int(x_count) - 1)
    x = left + x_fraction * (right - left)
    y = bottom - (float(point.y_value) / 100.0) * (bottom - top)
    return float(x), float(y)


def _draw_marker(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius: float,
    shape: str,
    fill: RGB,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    r = float(radius)
    bbox = [cx - r, cy - r, cx + r, cy + r]
    if str(shape) == "square":
        draw.rectangle(bbox, fill=fill, outline=(255, 255, 255), width=2)
    elif str(shape) == "diamond":
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill, outline=(255, 255, 255))
    elif str(shape) == "triangle":
        draw.polygon([(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)], fill=fill, outline=(255, 255, 255))
    elif str(shape) == "ring":
        draw.ellipse(bbox, fill=(255, 255, 255), outline=fill, width=4)
    else:
        draw.ellipse(bbox, fill=fill, outline=(255, 255, 255), width=2)
    return _bbox(bbox)


def _render_scatter_readout(
    image: Image.Image,
    *,
    dataset: _Dataset,
    render_params: _RenderParams,
) -> _Rendered:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    plot_bbox = [
        float(render_params.plot_margin_left_px),
        float(render_params.plot_margin_top_px),
        float(width - render_params.plot_margin_right_px),
        float(height - render_params.plot_margin_bottom_px),
    ]
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    axis_font = load_font(int(render_params.label_font_size_px), bold=True)
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    legend_font = load_font(int(render_params.legend_font_size_px), bold=True)

    panel_bbox = [
        float(plot_bbox[0] - 60.0),
        float(plot_bbox[1] - 54.0),
        float(width - 36.0),
        float(plot_bbox[3] + 78.0),
    ]
    draw.rounded_rectangle(panel_bbox, radius=6, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=2)
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb, outline=render_params.axis_color_rgb, width=int(render_params.axis_line_width_px))

    x_label_bboxes: Dict[str, List[float]] = {}
    for tick in range(0, 101, 20):
        y = plot_bbox[3] - (float(tick) / 100.0) * (plot_bbox[3] - plot_bbox[1])
        draw.line([plot_bbox[0], y, plot_bbox[2], y], fill=render_params.grid_color_rgb, width=int(render_params.grid_line_width_px))
        draw.line([plot_bbox[0] - render_params.tick_length_px, y, plot_bbox[0], y], fill=render_params.axis_color_rgb, width=1)
        _draw_text(
            draw,
            str(tick),
            (plot_bbox[0] - 13.0, y),
            font=tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            anchor="rm",
        )

    x_count = len(dataset.x_labels)
    for index, label in enumerate(dataset.x_labels):
        if x_count <= 1:
            x = (plot_bbox[0] + plot_bbox[2]) / 2.0
        else:
            x = plot_bbox[0] + (float(index) / float(x_count - 1)) * (plot_bbox[2] - plot_bbox[0])
        draw.line([x, plot_bbox[1], x, plot_bbox[3]], fill=render_params.grid_color_rgb, width=int(render_params.grid_line_width_px))
        draw.line([x, plot_bbox[3], x, plot_bbox[3] + render_params.tick_length_px], fill=render_params.axis_color_rgb, width=1)
        x_label_bboxes[str(label)] = _draw_text(
            draw,
            str(label),
            (x, plot_bbox[3] + 14.0),
            font=tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            anchor="mt",
        )

    title_box = _draw_text(
        draw,
        "Series Scatter Plot",
        (plot_bbox[0], panel_bbox[1] + 16.0),
        font=title_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
    )
    x_axis_box = _draw_text(
        draw,
        dataset.x_axis_title,
        ((plot_bbox[0] + plot_bbox[2]) / 2.0, plot_bbox[3] + 58.0),
        font=axis_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        anchor="mt",
    )
    y_axis_box = _draw_text(
        draw,
        dataset.y_axis_title,
        (plot_bbox[0] - 80.0, plot_bbox[1] - 30.0),
        font=axis_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
    )

    entities: List[Dict[str, Any]] = [
        {"entity_id": "scatter_panel", "entity_type": "chart_panel", "bbox_xyxy": _bbox(panel_bbox), "attrs": {}},
        {"entity_id": "scatter_plot", "entity_type": "scatter_plot", "bbox_xyxy": _bbox(plot_bbox), "attrs": {}},
        {"entity_id": "chart_title", "entity_type": "chart_title", "bbox_xyxy": title_box, "attrs": {"title": "Series Scatter Plot"}},
        {"entity_id": "x_axis_label", "entity_type": "axis_label", "bbox_xyxy": x_axis_box, "attrs": {"axis": "x", "label": dataset.x_axis_title}},
        {"entity_id": "y_axis_label", "entity_type": "axis_label", "bbox_xyxy": y_axis_box, "attrs": {"axis": "y", "label": dataset.y_axis_title}},
    ]

    point_bboxes: Dict[str, List[float]] = {}
    value_label_bboxes: Dict[str, List[float]] = {}
    point_annotation_bboxes: Dict[str, List[float]] = {}
    label_offsets = [(-22.0, -18.0), (22.0, -18.0), (-22.0, 18.0), (22.0, 18.0), (0.0, -30.0)]
    for series_index, series_item in enumerate(dataset.series):
        for point in series_item.points:
            px, py = _point_xy(point, x_count=x_count, plot_bbox=plot_bbox)
            point_box = _draw_marker(
                draw,
                center=(px, py),
                radius=float(render_params.point_radius_px),
                shape=str(series_item.marker_shape),
                fill=series_item.color_rgb,
            )
            point_bboxes[str(point.point_id)] = list(point_box)
            offset = label_offsets[int(series_index) % len(label_offsets)]
            value_box = _draw_text(
                draw,
                str(point.y_value),
                (px + float(offset[0]), py + float(offset[1])),
                font=value_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=2,
                anchor="mm",
            )
            value_label_bboxes[str(point.point_id)] = list(value_box)
            point_annotation_bboxes[str(point.point_id)] = _bbox_union([point_box, value_box])
            entities.append(
                {
                    "entity_id": str(point.point_id),
                    "entity_type": "scatter_series_point",
                    "bbox_xyxy": list(point_box),
                    "attrs": {
                        "series_label": str(series_item.label),
                        "x_label": str(point.x_label),
                        "x_index": int(point.x_index),
                        "y_value": int(point.y_value),
                        "value_label_bbox_xyxy": list(value_box),
                    },
                }
            )

    legend_bboxes: Dict[str, List[float]] = {}
    legend_left = plot_bbox[2] + float(render_params.legend_gap_px)
    legend_top = plot_bbox[1] + 30.0
    legend_row_height = 52.0
    _draw_text(
        draw,
        "Series",
        (legend_left, legend_top - 31.0),
        font=legend_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
    )
    for index, series_item in enumerate(dataset.series):
        y = legend_top + float(index) * legend_row_height
        row_box = [legend_left - 10.0, y - 8.0, float(width - 54.0), y + 36.0]
        draw.rounded_rectangle(row_box, radius=6, fill=(255, 255, 255), outline=render_params.panel_border_rgb, width=1)
        marker_box = _draw_marker(
            draw,
            center=(legend_left + 15.0, y + 14.0),
            radius=10.0,
            shape=str(series_item.marker_shape),
            fill=series_item.color_rgb,
        )
        text_box = _draw_text(
            draw,
            str(series_item.label),
            (legend_left + 44.0, y + 2.0),
            font=legend_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
        )
        legend_bboxes[str(series_item.label)] = _bbox_union([row_box, marker_box, text_box])
        entities.append(
            {
                "entity_id": f"legend_{series_item.label}",
                "entity_type": "legend_entry",
                "bbox_xyxy": list(legend_bboxes[str(series_item.label)]),
                "attrs": {"series_label": str(series_item.label)},
            }
        )

    return _Rendered(
        image=image,
        entities=tuple(dict(item) for item in entities),
        plot_bbox_px=_bbox(plot_bbox),
        point_bboxes=dict(point_bboxes),
        value_label_bboxes=dict(value_label_bboxes),
        point_annotation_bboxes=dict(point_annotation_bboxes),
        x_label_bboxes=dict(x_label_bboxes),
        legend_bboxes=dict(legend_bboxes),
    )


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    trace = dict(dataset.query.trace)
    if str(dataset.query.answer_type) == "integer":
        answer_hint = str(prompt_defaults["answer_hint_y_value"])
        json_example = str(prompt_defaults["json_example_y_value"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_y_value"])
    else:
        answer_hint = str(prompt_defaults["answer_hint_x_label"])
        json_example = str(prompt_defaults["json_example_x_label"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_x_label"])
    return {
        "object_description": str(prompt_defaults["object_description_scatter_series_readout"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_defaults["annotation_hint"]),
        "answer_hint": str(answer_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "series_label": str(trace.get("target_series_label", "")),
        "comparison_series_label": str(trace.get("comparison_series_label", "")),
        "extremum_phrase": str(trace.get("extremum", "")),
        "target_y_value": str(trace.get("target_y_value", "")),
        "target_x_label": str(trace.get("target_x_label", "")),
        "unanswerable_instruction": str(prompt_defaults.get("unanswerable_instruction", "")),
    }


def _build_keyed_annotation_bboxes(dataset: _Dataset, rendered: _Rendered) -> Dict[str, List[float]]:
    """Return role-bound annotation boxes for the scatter readout query."""

    if str(dataset.query.answer) == UNANSWERABLE_ANSWER:
        return {}

    trace = dict(dataset.query.trace)
    keyed: Dict[str, List[float]] = {}
    target_point_id = str(dataset.query.target_point_id)
    if target_point_id:
        keyed["target_point_readout"] = list(rendered.point_annotation_bboxes[str(target_point_id)])

    comparison_point_id = str(trace.get("comparison_point_id", ""))
    if comparison_point_id:
        keyed["comparison_point_readout"] = list(rendered.point_annotation_bboxes[str(comparison_point_id)])

    if str(dataset.query.annotation_x_label):
        keyed["x_axis_label"] = list(rendered.x_label_bboxes[str(dataset.query.annotation_x_label)])
    return dict(keyed)


class ChartsScatterSeriesReadoutTask:
    """Answer value readout questions over a multi-series scatter chart."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "scatter"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset_params = {**dict(params), "_enable_unanswerable": bool(getattr(self, "supports_unanswerable", False))}
        dataset = _build_dataset(
            params=dataset_params,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            query_probabilities=query_probabilities,
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
        chart_font_family = _sample_chart_font_family(int(instance_seed), params)
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_scatter_readout(background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_x_label",
                "answer_hint_y_value",
                "annotation_hint",
                "json_example_x_label",
                "json_example_y_value",
                "json_example_answer_only_x_label",
                "json_example_answer_only_y_value",
                "object_description_scatter_series_readout",
                "unanswerable_instruction",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots=_build_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        is_unanswerable = str(dataset.query.answer) == UNANSWERABLE_ANSWER
        target_point = None if is_unanswerable else _point_by_id(dataset.series, str(dataset.query.target_point_id))
        annotation_point_ids = [str(point_id) for point_id in dataset.query.annotation_point_ids]
        annotation_bboxes_by_role = _build_keyed_annotation_bboxes(dataset, rendered)
        annotation_bboxes = [list(bbox) for bbox in annotation_bboxes_by_role.values()]
        answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bboxes_by_role))

        total_points = sum(len(series.points) for series in dataset.series)
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(total_points), [18, 50]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_id)])),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )
        values_by_series = {
            str(series.label): [
                {
                    "point_id": str(point.point_id),
                    "x_label": str(point.x_label),
                    "x_index": int(point.x_index),
                    "y_value": int(point.y_value),
                }
                for point in series.points
            ]
            for series in dataset.series
        }
        projected_annotation = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_bboxes_by_role),
            "pixel_keyed_bbox_map": dict(annotation_bboxes_by_role),
            "bbox_set": list(annotation_bboxes),
            "point_id": "" if target_point is None else str(target_point.point_id),
            "point_ids": list(annotation_point_ids),
            "series_label": str(dataset.query.target_series_label),
            "x_label": "" if target_point is None else str(target_point.x_label),
            "y_value": None if target_point is None else int(target_point.y_value),
            "annotation_x_label": str(dataset.query.annotation_x_label),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_scatter_series_readout",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": answer_value,
                    "target_point_id": "" if target_point is None else str(target_point.point_id),
                    "annotation_point_ids": list(annotation_point_ids),
                    "answerability": "unanswerable" if is_unanswerable else "answerable",
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
                    "scene_variant": str(dataset.scene_variant),
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant_probabilities": {"marker_scatter": 1.0},
                    "series_count": len(dataset.series),
                    "x_count": len(dataset.x_labels),
                    **dict(dataset.query.trace),
                },
            },
            "render_spec": {
                "scene_variant": str(dataset.scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_radius_px": int(render_params.point_radius_px),
                "legend_gap_px": int(render_params.legend_gap_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_assets": {
                    "font_asset_version": font_asset_version(),
                    "chart_font_family": str(chart_font_family),
                },
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_bboxes_px": dict(rendered.point_bboxes),
                "value_label_bboxes_px": dict(rendered.value_label_bboxes),
                "point_annotation_bboxes_px": dict(rendered.point_annotation_bboxes),
                "x_label_bboxes_px": dict(rendered.x_label_bboxes),
                "legend_bboxes_px": dict(rendered.legend_bboxes),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "scatter_series_readout_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "x_axis_title": str(dataset.x_axis_title),
                "y_axis_title": str(dataset.y_axis_title),
                "x_labels": list(dataset.x_labels),
                "series_labels": [str(series.label) for series in dataset.series],
                "series_count": len(dataset.series),
                "x_count": len(dataset.x_labels),
                "total_point_count": int(total_points),
                "values_by_series": dict(values_by_series),
                "target_point_id": "" if target_point is None else str(target_point.point_id),
                "target_series_label": str(dataset.query.target_series_label),
                "target_x_label": "" if target_point is None else str(target_point.x_label),
                "target_y_value": None if target_point is None else int(target_point.y_value),
                "query_id_probabilities": dict(query_probabilities),
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "scatter_series_readout_witness",
                "point_id": "" if target_point is None else str(target_point.point_id),
                "point_ids": list(annotation_point_ids),
                "series_label": str(dataset.query.target_series_label),
                "x_label": "" if target_point is None else str(target_point.x_label),
                "y_value": None if target_point is None else int(target_point.y_value),
                "answer": answer_value,
                "answerability": "unanswerable" if is_unanswerable else "answerable",
                **({"absence_proof": dict(dataset.query.trace["absence_proof"])} if is_unanswerable else {}),
            },
            "projected_annotation": dict(projected_annotation),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
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
class ChartsScatterSeriesExtremumXLabelTask(MergedChartQueryVariantTaskMixin, ChartsScatterSeriesReadoutTask):
    """Return the x-axis label where a named series reaches its high or low point."""

    task_id = "task_charts__scatter_readout__series_x_extremum_label"
    allowed_query_ids = _EXTREMUM_QUERY_IDS
    supports_unanswerable = True


@register_task
class ChartsScatterSeriesYAnchorOtherSeriesValueTask(MergedChartQueryVariantTaskMixin, ChartsScatterSeriesReadoutTask):
    """Use one series value as an anchor to read another series value."""

    task_id = "task_charts__scatter_readout__series_y_anchor_other_series_value"
    allowed_query_ids = ("series_y_anchor_other_series_value",)


@register_task
class ChartsScatterSeriesPairValueGapAtXTask(MergedChartQueryVariantTaskMixin, ChartsScatterSeriesReadoutTask):
    """Compute the value gap between two series at a named x-axis position."""

    task_id = "task_charts__scatter_readout__series_pair_value_gap_at_x"
    allowed_query_ids = ("series_pair_value_gap_at_x",)


__all__ = [
    "ChartsScatterSeriesExtremumXLabelTask",
    "ChartsScatterSeriesPairValueGapAtXTask",
    "ChartsScatterSeriesReadoutTask",
    "ChartsScatterSeriesYAnchorOtherSeriesValueTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
