"""Uncertainty-band chart tasks for chart-domain visual reasoning."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.color_distance import sample_color_palette_with_distance_constraints
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
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from ...shared.text_legibility import draw_traced_text
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_axis_labels, resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.information_style import make_chart_information_background, resolve_chart_information_style
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "charts_uncertainty_band_base"
SCENE_ID = "uncertainty_band"
OVERLAP_QUERY_IDS: Tuple[str, ...] = ("band_overlap_count",)
WIDTH_EXTREMUM_QUERY_IDS: Tuple[str, ...] = ("widest_band_x_label", "narrowest_band_x_label")
SUPPORTED_QUERY_IDS: Tuple[str, ...] = OVERLAP_QUERY_IDS + WIDTH_EXTREMUM_QUERY_IDS

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "uncertainty_band")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="uncertainty_band", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

RGB = Tuple[int, int, int]
Point = List[float]

_QUERY_REASONING_LOADS: Dict[str, float] = {
    "band_overlap_count": 0.64,
    "widest_band_x_label": 0.58,
    "narrowest_band_x_label": 0.58,
}


@dataclass(frozen=True)
class _BandSeries:
    series_id: str
    label: str
    color_rgb: RGB
    lower_values: Tuple[int, ...]
    mid_values: Tuple[int, ...]
    upper_values: Tuple[int, ...]


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    annotation_x_indices: Tuple[int, ...]
    target_series_id: str | None
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    x_labels: Tuple[str, ...]
    x_label_meta: Dict[str, Any]
    series: Tuple[_BandSeries, _BandSeries]
    query_id: str
    query_id_probabilities: Dict[str, float]
    query: _Query
    title: str


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    margin_left_px: int
    margin_right_px: int
    margin_top_px: int
    margin_bottom_px: int
    title_band_height_px: int
    legend_width_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    band_outline_width_px: int
    center_line_width_px: int
    point_radius_px: int
    title_font_size_px: int
    label_font_size_px: int
    tick_font_size_px: int
    legend_font_size_px: int
    axis_min: int
    axis_max: int
    tick_step: int
    band_alpha: int
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    axis_rgb: RGB
    grid_rgb: RGB
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    font_family: str
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    series_band_bboxes_px: Dict[str, List[float]]
    point_map_px: Dict[str, Dict[str, Dict[str, Point]]]
    overlap_points_px: Dict[str, Point]
    render_meta: Dict[str, Any]


def _probability_map(values: Sequence[int | str]) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    weight = 1.0 / float(len(support))
    return {str(value): float(weight) for value in support}


def _selection_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        return abs(int(sample_cursor))
    return abs(int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))))


def _choose_from_values(
    params: Mapping[str, Any],
    *,
    values: Sequence[int | str],
    instance_seed: int,
    namespace: str,
) -> int | str:
    candidates = tuple(values)
    if not candidates:
        raise ValueError(f"empty support for {namespace}")
    index = _selection_index(params, instance_seed=int(instance_seed), namespace=str(namespace))
    return candidates[int(index) % len(candidates)]


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_x_count(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Dict[str, float]]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="x_count_min",
        max_key="x_count_max",
        fallback_min=6,
        fallback_max=9,
        context=f"generation defaults for {TASK_ID}",
    )
    support = tuple(range(int(low), int(high) + 1))
    return int(_choose_from_values(params, values=support, instance_seed=instance_seed, namespace="charts.uncertainty_band.x_count")), _probability_map(support)


def _resolve_colors(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[RGB, RGB]:
    configured = params.get("series_palette_rgb", group_default(_RENDER_DEFAULTS, "series_palette_rgb", None))
    if isinstance(configured, Sequence) and not isinstance(configured, (str, bytes)):
        colors: List[RGB] = []
        for raw in configured:
            if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and len(raw) >= 3:
                colors.append(tuple(max(0, min(255, int(channel))) for channel in raw[:3]))  # type: ignore[arg-type]
        if len(colors) >= 2:
            offset = _selection_index(params, instance_seed=int(instance_seed), namespace="charts.uncertainty_band.palette")
            return colors[int(offset) % len(colors)], colors[(int(offset) + 1) % len(colors)]
    rng = spawn_rng(int(instance_seed), "charts.uncertainty_band.palette")
    palette = sample_color_palette_with_distance_constraints(
        rng,
        palette_size=2,
        channel_min=20,
        channel_max=210,
        anchor_colors=((255, 255, 255), (20, 20, 20)),
        min_distance=42.0,
        distance_space="lab",
    )
    return tuple(palette[0]), tuple(palette[1])


def _interval_from_mid_width(midpoint: int, width: int) -> Tuple[int, int, int]:
    width = max(4, int(width))
    lower = int(midpoint) - int(width // 2)
    upper = int(lower) + int(width)
    if lower < 0:
        upper -= int(lower)
        lower = 0
    if upper > 100:
        lower -= int(upper) - 100
        upper = 100
    midpoint = int(round((int(lower) + int(upper)) / 2.0))
    return int(lower), int(midpoint), int(upper)


def _sample_x_labels(*, count: int, instance_seed: int) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), "charts.uncertainty_band.x_labels")
    resolved = resolve_chart_axis_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=6,
    )
    return tuple(str(label) for label in resolved.labels), {
        "label_variant": str(resolved.label_variant),
        "label_pool_kind": str(resolved.label_pool_kind),
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
        "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
    }


def _sample_series_labels(*, instance_seed: int) -> Tuple[str, str, Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), "charts.uncertainty_band.series_labels")
    resolved = resolve_chart_entity_labels(rng, count=2, min_chars=3, max_chars=8, allow_spaces=False)
    labels = tuple(str(label) for label in resolved.labels)
    return labels[0], labels[1], {
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
    }


def _sample_overlap_dataset(
    *,
    x_count: int,
    x_labels: Sequence[str],
    series_labels: Tuple[str, str],
    colors: Tuple[RGB, RGB],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_BandSeries, _BandSeries], _Query]:
    rng = spawn_rng(int(instance_seed), "charts.uncertainty_band.overlap")
    answer_min = int(params.get("overlap_answer_count_min", group_default(_GEN_DEFAULTS, "overlap_answer_count_min", 1)))
    answer_max = int(params.get("overlap_answer_count_max", group_default(_GEN_DEFAULTS, "overlap_answer_count_max", 5)))
    support = tuple(range(max(1, int(answer_min)), min(int(answer_max), int(x_count)) + 1))
    overlap_count = int(
        _choose_from_values(
            params,
            values=support,
            instance_seed=int(instance_seed),
            namespace="charts.uncertainty_band.overlap_answer_count",
        )
    )
    overlap_indices = tuple(sorted(rng.sample(list(range(int(x_count))), k=int(overlap_count))))
    overlap_index_set = set(int(index) for index in overlap_indices)

    lower_a: List[int] = []
    mid_a: List[int] = []
    upper_a: List[int] = []
    lower_b: List[int] = []
    mid_b: List[int] = []
    upper_b: List[int] = []
    overlap_intervals: Dict[str, Dict[str, int]] = {}

    for index in range(int(x_count)):
        if int(index) in overlap_index_set:
            width_a = int(rng.randint(16, 26))
            width_b = int(rng.randint(16, 26))
            base_mid = int(rng.randint(34, 66))
            half_sum = int(width_a // 2) + int(width_b // 2)
            delta_limit = max(1, int(half_sum) - 4)
            b_mid = max(18, min(82, int(base_mid + rng.randint(-delta_limit, delta_limit))))
            a_low, a_mid, a_high = _interval_from_mid_width(base_mid, width_a)
            b_low, b_mid, b_high = _interval_from_mid_width(b_mid, width_b)
        else:
            width_a = int(rng.randint(12, 18))
            width_b = int(rng.randint(12, 18))
            if bool(rng.randint(0, 1)):
                a_low, a_mid, a_high = _interval_from_mid_width(int(rng.randint(62, 78)), width_a)
                b_low, b_mid, b_high = _interval_from_mid_width(int(rng.randint(22, 38)), width_b)
            else:
                a_low, a_mid, a_high = _interval_from_mid_width(int(rng.randint(22, 38)), width_a)
                b_low, b_mid, b_high = _interval_from_mid_width(int(rng.randint(62, 78)), width_b)
        lower_a.append(int(a_low))
        mid_a.append(int(a_mid))
        upper_a.append(int(a_high))
        lower_b.append(int(b_low))
        mid_b.append(int(b_mid))
        upper_b.append(int(b_high))
        if max(int(a_low), int(b_low)) <= min(int(a_high), int(b_high)):
            overlap_intervals[str(x_labels[index])] = {
                "x_index": int(index),
                "lower": max(int(a_low), int(b_low)),
                "upper": min(int(a_high), int(b_high)),
            }

    if len(overlap_intervals) != int(overlap_count):
        raise ValueError("constructed overlap support does not match target count")

    series = (
        _BandSeries("series_a", str(series_labels[0]), tuple(colors[0]), tuple(lower_a), tuple(mid_a), tuple(upper_a)),
        _BandSeries("series_b", str(series_labels[1]), tuple(colors[1]), tuple(lower_b), tuple(mid_b), tuple(upper_b)),
    )
    query = _Query(
        query_id="band_overlap_count",
        answer=int(overlap_count),
        answer_type="integer",
        annotation_x_indices=tuple(int(index) for index in overlap_indices),
        target_series_id=None,
        params={
            "overlap_count": int(overlap_count),
            "overlap_answer_count_probabilities": _probability_map(support),
            "overlap_x_labels": [str(x_labels[index]) for index in overlap_indices],
            "overlap_intervals_by_label": dict(overlap_intervals),
        },
    )
    return series, query


def _sample_width_dataset(
    *,
    query_id: str,
    x_count: int,
    x_labels: Sequence[str],
    series_labels: Tuple[str, str],
    colors: Tuple[RGB, RGB],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_BandSeries, _BandSeries], _Query]:
    rng = spawn_rng(int(instance_seed), f"charts.uncertainty_band.width.{query_id}")
    answer_index = int(
        _choose_from_values(
            params,
            values=tuple(range(int(x_count))),
            instance_seed=int(instance_seed),
            namespace=f"charts.uncertainty_band.width.answer_index.{query_id}",
        )
    )
    target_series_index = int(
        _choose_from_values(
            params,
            values=(0, 1),
            instance_seed=int(instance_seed),
            namespace=f"charts.uncertainty_band.width.target_series.{query_id}",
        )
    )

    series_values: List[Tuple[List[int], List[int], List[int], List[int]]] = []
    for series_index in range(2):
        widths = [int(rng.randint(12, 22)) for _ in range(int(x_count))]
        if int(series_index) == int(target_series_index):
            if str(query_id) == "widest_band_x_label":
                widths = [int(rng.randint(12, 22)) for _ in range(int(x_count))]
                widths[int(answer_index)] = int(rng.randint(28, 34))
            else:
                widths = [int(rng.randint(14, 26)) for _ in range(int(x_count))]
                widths[int(answer_index)] = int(rng.randint(6, 9))
        lowers: List[int] = []
        mids: List[int] = []
        uppers: List[int] = []
        for index, width in enumerate(widths):
            mid = int(rng.randint(30, 70))
            # Add a tiny deterministic trend so the band looks like a series,
            # while preserving the exact width construction.
            mid = max(18, min(82, int(mid + round(4.0 * math.sin((index + series_index) * 0.9)))))
            lower, midpoint, upper = _interval_from_mid_width(mid, int(width))
            lowers.append(int(lower))
            mids.append(int(midpoint))
            uppers.append(int(upper))
        series_values.append((list(widths), lowers, mids, uppers))

    series = (
        _BandSeries("series_a", str(series_labels[0]), tuple(colors[0]), tuple(series_values[0][1]), tuple(series_values[0][2]), tuple(series_values[0][3])),
        _BandSeries("series_b", str(series_labels[1]), tuple(colors[1]), tuple(series_values[1][1]), tuple(series_values[1][2]), tuple(series_values[1][3])),
    )
    target_series = series[int(target_series_index)]
    target_widths = [
        int(high) - int(low)
        for low, high in zip(target_series.lower_values, target_series.upper_values)
    ]
    if str(query_id) == "widest_band_x_label":
        resolved_index = max(range(len(target_widths)), key=lambda index: target_widths[index])
        rank_phrase = "widest"
    else:
        resolved_index = min(range(len(target_widths)), key=lambda index: target_widths[index])
        rank_phrase = "narrowest"
    if int(resolved_index) != int(answer_index):
        raise ValueError("constructed width support does not match target index")
    query = _Query(
        query_id=str(query_id),
        answer=str(x_labels[int(answer_index)]),
        answer_type="string",
        annotation_x_indices=(int(answer_index),),
        target_series_id=str(target_series.series_id),
        params={
            "target_series_id": str(target_series.series_id),
            "target_series_label": str(target_series.label),
            "target_x_index": int(answer_index),
            "target_x_label": str(x_labels[int(answer_index)]),
            "rank_phrase": str(rank_phrase),
            "target_band_widths": [int(value) for value in target_widths],
            "answer_band_width": int(target_widths[int(answer_index)]),
            "target_series_index_probabilities": {"series_a": 0.5, "series_b": 0.5},
        },
    )
    return series, query


def _sample_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    query_id, query_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
    x_count, x_count_probabilities = _resolve_x_count(params, instance_seed=int(instance_seed))
    x_labels, x_label_meta = _sample_x_labels(count=int(x_count), instance_seed=int(instance_seed))
    series_label_a, series_label_b, series_label_meta = _sample_series_labels(instance_seed=int(instance_seed))
    colors = _resolve_colors(params, instance_seed=int(instance_seed))
    if str(query_id) == "band_overlap_count":
        series, query = _sample_overlap_dataset(
            x_count=int(x_count),
            x_labels=x_labels,
            series_labels=(series_label_a, series_label_b),
            colors=colors,
            params=params,
            instance_seed=int(instance_seed),
        )
    else:
        series, query = _sample_width_dataset(
            query_id=str(query_id),
            x_count=int(x_count),
            x_labels=x_labels,
            series_labels=(series_label_a, series_label_b),
            colors=colors,
            params=params,
            instance_seed=int(instance_seed),
        )
    title_options = params.get("title_options", group_default(_RENDER_DEFAULTS, "title_options", ("Uncertainty Bands",)))
    if not isinstance(title_options, Sequence) or isinstance(title_options, (str, bytes)) or not title_options:
        title_options = ("Uncertainty Bands",)
    title_index = _selection_index(params, instance_seed=int(instance_seed), namespace="charts.uncertainty_band.title")
    query.params.update(
        {
            "x_count": int(x_count),
            "x_count_probabilities": dict(x_count_probabilities),
            "x_label_meta": dict(x_label_meta),
            "series_label_meta": dict(series_label_meta),
        }
    )
    return _Dataset(
        x_labels=tuple(str(label) for label in x_labels),
        x_label_meta=dict(x_label_meta),
        series=series,
        query_id=str(query_id),
        query_id_probabilities=dict(query_probabilities),
        query=query,
        title=str(title_options[int(title_index) % len(title_options)]),
    )


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    left = int(params.get("plot_margin_left_px", group_default(_RENDER_DEFAULTS, "plot_margin_left_px", 84)))
    right = int(params.get("plot_margin_right_px", group_default(_RENDER_DEFAULTS, "plot_margin_right_px", 172)))
    top = int(params.get("plot_margin_top_px", group_default(_RENDER_DEFAULTS, "plot_margin_top_px", 84)))
    bottom = int(params.get("plot_margin_bottom_px", group_default(_RENDER_DEFAULTS, "plot_margin_bottom_px", 92)))
    left, right, top, bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=left,
        right_px=right,
        top_px=top,
        bottom_px=bottom,
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="charts.uncertainty_band.layout",
    )
    font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace="charts.uncertainty_band.font",
        params=params,
        exclude_tags=("display",),
    )
    return _RenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1180))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 760))),
        margin_left_px=int(left),
        margin_right_px=int(right),
        margin_top_px=int(top),
        margin_bottom_px=int(bottom),
        title_band_height_px=int(params.get("title_band_height_px", group_default(_RENDER_DEFAULTS, "title_band_height_px", 58))),
        legend_width_px=int(params.get("legend_width_px", group_default(_RENDER_DEFAULTS, "legend_width_px", 156))),
        axis_line_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "axis_line_width_px", 2, instance_seed=int(instance_seed), namespace=TASK_ID)),
        grid_line_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "grid_line_width_px", 1, instance_seed=int(instance_seed), namespace=TASK_ID)),
        band_outline_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "band_outline_width_px", 2, instance_seed=int(instance_seed), namespace=TASK_ID)),
        center_line_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "center_line_width_px", 4, instance_seed=int(instance_seed), namespace=TASK_ID)),
        point_radius_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "point_radius_px", 5, instance_seed=int(instance_seed), namespace=TASK_ID)),
        title_font_size_px=int(params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", 28))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", 17))),
        tick_font_size_px=int(params.get("tick_font_size_px", group_default(_RENDER_DEFAULTS, "tick_font_size_px", 15))),
        legend_font_size_px=int(params.get("legend_font_size_px", group_default(_RENDER_DEFAULTS, "legend_font_size_px", 17))),
        axis_min=int(params.get("axis_min", group_default(_RENDER_DEFAULTS, "axis_min", 0))),
        axis_max=int(params.get("axis_max", group_default(_RENDER_DEFAULTS, "axis_max", 100))),
        tick_step=int(params.get("tick_step", group_default(_RENDER_DEFAULTS, "tick_step", 20))),
        band_alpha=max(40, min(170, int(params.get("band_alpha", group_default(_RENDER_DEFAULTS, "band_alpha", 82))))),
        panel_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_fill_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        panel_border_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_border_rgb", (190, 198, 208), instance_seed=int(instance_seed), namespace=TASK_ID),
        axis_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "axis_rgb", (64, 68, 76), instance_seed=int(instance_seed), namespace=TASK_ID),
        grid_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "grid_rgb", (224, 227, 232), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_rgb", (38, 41, 48), instance_seed=int(instance_seed), namespace=TASK_ID),
        muted_text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "muted_text_rgb", (88, 96, 112), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        font_family=str(font_family),
        layout_jitter_meta=dict(jitter_meta),
    )


def _darken(color: RGB, factor: float = 0.72) -> RGB:
    return tuple(max(0, min(255, int(round(float(channel) * float(factor))))) for channel in color)  # type: ignore[return-value]


def _relative_luminance(color: Sequence[int]) -> float:
    def _channel(value: int) -> float:
        normalized = float(value) / 255.0
        if normalized <= 0.03928:
            return normalized / 12.92
        return ((normalized + 0.055) / 1.055) ** 2.4

    rgb = [max(0, min(255, int(channel))) for channel in color[:3]]
    return (0.2126 * _channel(rgb[0])) + (0.7152 * _channel(rgb[1])) + (0.0722 * _channel(rgb[2]))


def _readable_chart_text_colors(surface_rgb: Sequence[int]) -> Tuple[RGB, RGB, RGB]:
    """Return readable primary, muted, and stroke colors for one chart surface."""

    if _relative_luminance(surface_rgb) >= 0.55:
        return (34, 42, 54), (72, 84, 100), (34, 42, 54)
    return (246, 250, 255), (205, 218, 232), (18, 24, 32)


def _scale_y(value: int | float, *, plot_bottom: float, plot_height: float, axis_min: int, axis_max: int) -> float:
    span = max(1.0, float(axis_max) - float(axis_min))
    norm = (float(value) - float(axis_min)) / span
    return float(plot_bottom) - (float(norm) * float(plot_height))


def _draw_text(
    draw: ImageDraw.ImageDraw,
    *,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: RGB,
    stroke: RGB,
    stroke_width: int = 1,
) -> None:
    draw_traced_text(
        draw,
        xy=(float(xy[0]), float(xy[1])),
        text=str(text),
        font=font,
        fill_rgb=tuple(int(value) for value in fill),
        stroke_rgb=tuple(int(value) for value in stroke),
        stroke_width=int(stroke_width),
        role="chart_text",
        required=True,
    )


def _render_dataset(dataset: _Dataset, params: Mapping[str, Any], *, instance_seed: int) -> _Rendered:
    render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
    style, style_meta = resolve_chart_information_style(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        task_group="uncertainty_band",
        protected_colors=[series.color_rgb for series in dataset.series],
        allow_dark=False,
        allow_colored_surface=True,
    )
    image, background_meta = make_chart_information_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace="charts.uncertainty_band.background",
    )
    panel_fill_rgb = tuple(int(value) for value in style.surface_rgb)
    panel_border_rgb = tuple(int(value) for value in style.panel_border_rgb)
    axis_rgb = tuple(int(value) for value in style.axis_rgb)
    grid_rgb = tuple(int(value) for value in style.grid_rgb)
    text_rgb, muted_text_rgb, text_stroke_rgb = _readable_chart_text_colors(panel_fill_rgb)
    text_stroke_width = 1
    if image.mode != "RGB":
        image = image.convert("RGB")
    draw = ImageDraw.Draw(image)

    plot_left = float(render_params.margin_left_px)
    plot_right = float(render_params.canvas_width - render_params.margin_right_px)
    plot_top = float(render_params.margin_top_px + render_params.title_band_height_px)
    plot_bottom = float(render_params.canvas_height - render_params.margin_bottom_px)
    plot_width = float(plot_right - plot_left)
    plot_height = float(plot_bottom - plot_top)
    if plot_width <= 10 or plot_height <= 10:
        raise ValueError("uncertainty band plot area is too small")
    panel_bbox = [
        float(plot_left - 42),
        float(render_params.margin_top_px),
        float(min(render_params.canvas_width - 26, plot_right + render_params.legend_width_px)),
        float(plot_bottom + 54),
    ]
    draw.rounded_rectangle(
        tuple(panel_bbox),
        radius=14,
        fill=panel_fill_rgb,
        outline=panel_border_rgb,
        width=2,
    )

    title_font = load_font(render_params.title_font_size_px, bold=True, font_family=render_params.font_family)
    tick_font = load_font(render_params.tick_font_size_px, bold=False, font_family=render_params.font_family)
    label_font = load_font(render_params.label_font_size_px, bold=True, font_family=render_params.font_family)
    legend_font = load_font(render_params.legend_font_size_px, bold=True, font_family=render_params.font_family)
    _draw_text(
        draw,
        xy=(plot_left, float(render_params.margin_top_px + 12)),
        text=str(dataset.title),
        font=title_font,
        fill=text_rgb,
        stroke=text_stroke_rgb,
        stroke_width=int(text_stroke_width),
    )

    # Grid and axes.
    for tick in range(int(render_params.axis_min), int(render_params.axis_max) + 1, int(render_params.tick_step)):
        y = _scale_y(tick, plot_bottom=plot_bottom, plot_height=plot_height, axis_min=render_params.axis_min, axis_max=render_params.axis_max)
        draw.line((plot_left, y, plot_right, y), fill=grid_rgb, width=int(render_params.grid_line_width_px))
        label = str(tick)
        bbox = draw.textbbox((0, 0), label, font=tick_font, stroke_width=1)
        _draw_text(
            draw,
            xy=(plot_left - 14 - float(bbox[2] - bbox[0]), y - (0.5 * float(bbox[3] - bbox[1]))),
            text=label,
            font=tick_font,
            fill=text_rgb,
            stroke=text_stroke_rgb,
            stroke_width=int(text_stroke_width),
        )
    draw.line((plot_left, plot_bottom, plot_right, plot_bottom), fill=axis_rgb, width=int(render_params.axis_line_width_px))
    draw.line((plot_left, plot_top, plot_left, plot_bottom), fill=axis_rgb, width=int(render_params.axis_line_width_px))

    x_positions: List[float] = []
    if len(dataset.x_labels) == 1:
        x_positions = [0.5 * (plot_left + plot_right)]
    else:
        step = plot_width / float(len(dataset.x_labels) - 1)
        x_positions = [float(plot_left + (index * step)) for index in range(len(dataset.x_labels))]

    for index, label in enumerate(dataset.x_labels):
        x = float(x_positions[index])
        draw.line((x, plot_bottom, x, plot_bottom + 7), fill=axis_rgb, width=1)
        max_label_width = max(42.0, plot_width / max(1, len(dataset.x_labels)) - 6.0)
        fitted = fit_font_to_box(
            draw,
            text=str(label),
            max_width=float(max_label_width),
            max_height=28.0,
            bold=True,
            font_family=render_params.font_family,
            min_size_px=9,
            max_size_px=render_params.label_font_size_px,
        )
        draw_text_centered(
            draw,
            text=str(label),
            center=(x, plot_bottom + 25),
            font=fitted,
            fill=text_rgb,
            stroke_fill=text_stroke_rgb,
            stroke_width=int(text_stroke_width),
        )

    point_map: Dict[str, Dict[str, Dict[str, Point]]] = {}
    series_band_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []

    base_rgba = image.convert("RGBA")
    overlay = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    for series in dataset.series:
        upper_points: List[Tuple[float, float]] = []
        mid_points: List[Tuple[float, float]] = []
        lower_points: List[Tuple[float, float]] = []
        point_map[str(series.series_id)] = {}
        for index, x_label in enumerate(dataset.x_labels):
            x = float(x_positions[index])
            upper_y = _scale_y(series.upper_values[index], plot_bottom=plot_bottom, plot_height=plot_height, axis_min=render_params.axis_min, axis_max=render_params.axis_max)
            mid_y = _scale_y(series.mid_values[index], plot_bottom=plot_bottom, plot_height=plot_height, axis_min=render_params.axis_min, axis_max=render_params.axis_max)
            lower_y = _scale_y(series.lower_values[index], plot_bottom=plot_bottom, plot_height=plot_height, axis_min=render_params.axis_min, axis_max=render_params.axis_max)
            upper_points.append((x, upper_y))
            mid_points.append((x, mid_y))
            lower_points.append((x, lower_y))
            point_map[str(series.series_id)][str(x_label)] = {
                "upper_bound": [round(float(x), 3), round(float(upper_y), 3)],
                "center_line": [round(float(x), 3), round(float(mid_y), 3)],
                "lower_bound": [round(float(x), 3), round(float(lower_y), 3)],
            }
            entities.append(
                {
                    "entity_id": f"{series.series_id}:{index}",
                    "entity_type": "uncertainty_band_point",
                    "series_id": str(series.series_id),
                    "series_label": str(series.label),
                    "x_index": int(index),
                    "x_label": str(x_label),
                    "lower": int(series.lower_values[index]),
                    "midpoint": int(series.mid_values[index]),
                    "upper": int(series.upper_values[index]),
                    "upper_point_px": point_map[str(series.series_id)][str(x_label)]["upper_bound"],
                    "center_point_px": point_map[str(series.series_id)][str(x_label)]["center_line"],
                    "lower_point_px": point_map[str(series.series_id)][str(x_label)]["lower_bound"],
                }
            )
        polygon = list(upper_points) + list(reversed(lower_points))
        overlay_draw.polygon(polygon, fill=(*tuple(int(value) for value in series.color_rgb), int(render_params.band_alpha)))
        outline_rgb = _darken(series.color_rgb, 0.62)
        overlay_draw.line(upper_points, fill=(*outline_rgb, 210), width=int(render_params.band_outline_width_px))
        overlay_draw.line(lower_points, fill=(*outline_rgb, 210), width=int(render_params.band_outline_width_px))
        overlay_draw.line(mid_points, fill=(*outline_rgb, 255), width=int(render_params.center_line_width_px), joint="curve")
        xs = [point[0] for point in polygon]
        ys = [point[1] for point in polygon]
        series_band_bboxes[str(series.series_id)] = [
            round(min(xs), 3),
            round(min(ys), 3),
            round(max(xs), 3),
            round(max(ys), 3),
        ]

    image = Image.alpha_composite(base_rgba, overlay).convert("RGB")
    draw = ImageDraw.Draw(image)

    for series in dataset.series:
        for index, x_label in enumerate(dataset.x_labels):
            center = point_map[str(series.series_id)][str(x_label)]["center_line"]
            r = int(render_params.point_radius_px)
            x, y = float(center[0]), float(center[1])
            draw.ellipse(
                (x - r, y - r, x + r, y + r),
                fill=tuple(int(value) for value in _darken(series.color_rgb, 0.60)),
                outline=text_stroke_rgb,
                width=1,
            )

    # Legend outside the plot area but inside the panel.
    legend_x = float(plot_right + 26)
    legend_y = float(plot_top + 8)
    for index, series in enumerate(dataset.series):
        y = float(legend_y + (index * 34))
        draw.rounded_rectangle((legend_x, y + 3, legend_x + 24, y + 17), radius=4, fill=series.color_rgb, outline=_darken(series.color_rgb, 0.62), width=1)
        _draw_text(
            draw,
            xy=(legend_x + 34, y),
            text=str(series.label),
            font=legend_font,
            fill=text_rgb,
            stroke=text_stroke_rgb,
            stroke_width=int(text_stroke_width),
        )

    overlap_points: Dict[str, Point] = {}
    series_a, series_b = dataset.series
    for index, x_label in enumerate(dataset.x_labels):
        low = max(int(series_a.lower_values[index]), int(series_b.lower_values[index]))
        high = min(int(series_a.upper_values[index]), int(series_b.upper_values[index]))
        if int(low) <= int(high):
            value = 0.5 * (float(low) + float(high))
            overlap_points[str(x_label)] = [
                round(float(x_positions[index]), 3),
                round(_scale_y(value, plot_bottom=plot_bottom, plot_height=plot_height, axis_min=render_params.axis_min, axis_max=render_params.axis_max), 3),
            ]

    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=[round(plot_left, 3), round(plot_top, 3), round(plot_right, 3), round(plot_bottom, 3)],
        series_band_bboxes_px=dict(series_band_bboxes),
        point_map_px=dict(point_map),
        overlap_points_px=dict(overlap_points),
        render_meta={
            "panel_bbox_px": [round(float(value), 3) for value in panel_bbox],
            "font_assets": chart_font_asset_metadata(render_params.font_family),
            "layout_jitter": dict(render_params.layout_jitter_meta),
            "background": dict(background_meta),
            "information_style": dict(style_meta),
            "axis_min": int(render_params.axis_min),
            "axis_max": int(render_params.axis_max),
            "tick_step": int(render_params.tick_step),
        },
    )


def _query_phrase(query_id: str) -> str:
    if str(query_id) == "widest_band_x_label":
        return "widest"
    if str(query_id) == "narrowest_band_x_label":
        return "narrowest"
    return ""


class ChartsUncertaintyBandTask:
    """Shared uncertainty-band chart generator."""

    domain = "charts"
    task_group = "uncertainty_band"
    task_id = TASK_ID
    default_dataset_enabled = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "answer_hint_count",
                "answer_hint_label",
                "annotation_hint_band_overlap_count",
                "annotation_hint_band_width_extremum_x_label",
                "json_example_band_overlap_count",
                "json_example_band_width_extremum_x_label",
                "json_example_answer_only_band_overlap_count",
                "json_example_answer_only_band_width_extremum_x_label",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )

        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + int(attempt)
            try:
                dataset = _sample_dataset(params, instance_seed=int(attempt_seed))
                rendered = _render_dataset(dataset, params, instance_seed=int(attempt_seed))
                image, post_noise_meta = apply_post_image_noise(
                    rendered.image,
                    instance_seed=int(attempt_seed),
                    params=params,
                    default_config=POST_IMAGE_NOISE_DEFAULTS,
                )

                query_id = str(dataset.query_id)
                answer_hint_key = "answer_hint_count" if query_id == "band_overlap_count" else "answer_hint_label"
                annotation_hint_key = "annotation_hint_band_overlap_count" if query_id == "band_overlap_count" else "annotation_hint_band_width_extremum_x_label"
                json_example_key = "json_example_band_overlap_count" if query_id == "band_overlap_count" else "json_example_band_width_extremum_x_label"
                answer_only_example_key = "json_example_answer_only_band_overlap_count" if query_id == "band_overlap_count" else "json_example_answer_only_band_width_extremum_x_label"
                target_series_label = ""
                if dataset.query.target_series_id:
                    target_series_label = next(
                        series.label
                        for series in dataset.series
                        if str(series.series_id) == str(dataset.query.target_series_id)
                    )
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
                        "json_output_contract": str(prompt_defaults["json_output_contract"]),
                        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                        "answer_hint": str(prompt_defaults[answer_hint_key]),
                        "annotation_hint": str(prompt_defaults[annotation_hint_key]),
                        "json_example": str(prompt_defaults[json_example_key]),
                        "json_example_answer_only": str(prompt_defaults[answer_only_example_key]),
                        "series_a_label": str(dataset.series[0].label),
                        "series_b_label": str(dataset.series[1].label),
                        "target_series_label": str(target_series_label),
                        "rank_phrase": _query_phrase(str(query_id)),
                    },
                    instance_seed=int(attempt_seed),
                )
                prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

                if query_id == "band_overlap_count":
                    annotation_points = [
                        list(rendered.overlap_points_px[str(dataset.x_labels[index])])
                        for index in dataset.query.annotation_x_indices
                    ]
                    annotation_gt = TypedValue(type="point_set", value=annotation_points)
                else:
                    if not dataset.query.target_series_id:
                        raise ValueError("width query missing target series")
                    answer_label = str(dataset.query.answer)
                    series_points = rendered.point_map_px[str(dataset.query.target_series_id)][answer_label]
                    annotation_gt = TypedValue(
                        type="keyed_point_map",
                        value={
                            "upper_bound": list(series_points["upper_bound"]),
                            "lower_bound": list(series_points["lower_bound"]),
                        },
                    )
                answer_gt = TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer)

                series_payload = [
                    {
                        "series_id": str(series.series_id),
                        "label": str(series.label),
                        "color_rgb": [int(value) for value in series.color_rgb],
                        "lower_values": [int(value) for value in series.lower_values],
                        "mid_values": [int(value) for value in series.mid_values],
                        "upper_values": [int(value) for value in series.upper_values],
                        "band_widths": [int(high) - int(low) for low, high in zip(series.lower_values, series.upper_values)],
                    }
                    for series in dataset.series
                ]
                visual_scan = normalize_int_with_bounds(len(dataset.x_labels), [6, 9])
                annotation_load = normalize_int_with_bounds(len(dataset.query.annotation_x_indices), [1, 5])
                reasoning_load = clamp_unit_interval(float(_QUERY_REASONING_LOADS[str(query_id)]) + (0.08 * float(annotation_load)))
                complexity = build_chart_complexity(
                    weights=_COMPLEXITY_WEIGHTS,
                    components={
                        "visual_scan": float(visual_scan),
                        "reasoning_load": float(reasoning_load),
                        "scene_variant_load": 0.55,
                    },
                )
                query_params = {
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(dataset.query_id_probabilities),
                    "answer_value": dataset.query.answer,
                    "answer_type": str(dataset.query.answer_type),
                    **dict(dataset.query.params),
                }
                trace_payload = {
                    "scene_ir": {
                        "scene_kind": SCENE_ID,
                        "entities": [dict(entity) for entity in rendered.entities],
                        "relations": {
                            "query_id": str(query_id),
                            "answer_value": dataset.query.answer,
                            "annotation_x_indices": [int(value) for value in dataset.query.annotation_x_indices],
                            "target_series_id": dataset.query.target_series_id,
                        },
                    },
                    "query_spec": {
                        "query_id": str(query_id),
                        "template_id": str(prompt_defaults["bundle_id"]),
                        "prompt_variant": dict(prompt_artifacts.prompt_variant),
                        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                        "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                        "params": dict(query_params),
                    },
                    "render_spec": {
                        "canvas_width": int(image.size[0]),
                        "canvas_height": int(image.size[1]),
                        "x_labels": [str(label) for label in dataset.x_labels],
                        "series_labels": [str(series.label) for series in dataset.series],
                        "render_meta": dict(rendered.render_meta),
                        "post_image_noise": dict(post_noise_meta),
                    },
                    "render_map": {
                        "plot_bbox_px": list(rendered.plot_bbox_px),
                        "series_band_bboxes_px": dict(rendered.series_band_bboxes_px),
                        "point_map_px": dict(rendered.point_map_px),
                        "overlap_points_px": dict(rendered.overlap_points_px),
                    },
                    "execution_trace": {
                        "query_id": str(query_id),
                        "question_format": "uncertainty_band",
                        "x_count": int(len(dataset.x_labels)),
                        "x_labels": [str(label) for label in dataset.x_labels],
                        "series": series_payload,
                        "answer_value": dataset.query.answer,
                        "answer_type": str(dataset.query.answer_type),
                        "annotation_x_indices": [int(value) for value in dataset.query.annotation_x_indices],
                        "target_series_id": dataset.query.target_series_id,
                        **dict(dataset.query.params),
                    },
                    "witness_symbolic": {
                        "type": "uncertainty_band_witness",
                        "answer_value": dataset.query.answer,
                        "annotation_x_indices": [int(value) for value in dataset.query.annotation_x_indices],
                        "target_series_id": dataset.query.target_series_id,
                    },
                    "projected_annotation": {
                        str(annotation_gt.type): annotation_gt.value,
                        "annotation_x_indices": [int(value) for value in dataset.query.annotation_x_indices],
                    },
                    "post_image_noise": dict(post_noise_meta),
                }
                return TaskOutput(
                    prompt=str(prompt_artifacts.prompt),
                    prompt_variants=dict(prompt_artifacts.prompt_variants),
                    answer_gt=answer_gt,
                    annotation_gt=annotation_gt,
                    image=image,
                    image_id="img0",
                    trace_payload=trace_payload,
                    complexity=complexity,
                    task_versions=default_task_versions(),
                    scene_id=SCENE_ID,
                    query_id=str(query_id),
                )
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate uncertainty-band chart after {max_attempts} attempts") from last_error


@register_task
class ChartsUncertaintyBandOverlapCountTask(MergedChartQueryVariantTaskMixin, ChartsUncertaintyBandTask):
    """Count labeled x positions where two uncertainty bands overlap."""

    task_id = "task_charts__uncertainty_band__band_overlap_count"
    default_dataset_enabled = True
    allowed_query_ids = OVERLAP_QUERY_IDS


@register_task
class ChartsUncertaintyBandWidthExtremumXLabelTask(MergedChartQueryVariantTaskMixin, ChartsUncertaintyBandTask):
    """Find the x label where a target uncertainty band is widest or narrowest."""

    task_id = "task_charts__uncertainty_band__band_width_extremum_x_label"
    default_dataset_enabled = True
    allowed_query_ids = WIDTH_EXTREMUM_QUERY_IDS


__all__ = [
    "ChartsUncertaintyBandTask",
    "ChartsUncertaintyBandOverlapCountTask",
    "ChartsUncertaintyBandWidthExtremumXLabelTask",
    "OVERLAP_QUERY_IDS",
    "WIDTH_EXTREMUM_QUERY_IDS",
    "SUPPORTED_QUERY_IDS",
]
