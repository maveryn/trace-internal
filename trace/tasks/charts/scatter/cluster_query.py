"""Scatter cluster pattern query task."""

from __future__ import annotations

import math
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
from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import load_font, temporary_default_font_family
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_scatter_cluster_query_base"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "cluster_trend_direction_label",
    "cluster_separation_extremum_label",
    "cluster_spread_extremum_label",
)
_SUPPORTED_TREND_DIRECTIONS: Tuple[str, ...] = ("upward", "downward")
_SUPPORTED_SEPARATION_EXTREMA: Tuple[str, ...] = ("closest", "farthest")
_SUPPORTED_SPREAD_AXES: Tuple[str, ...] = ("horizontal", "vertical", "overall")
_SUPPORTED_SPREAD_EXTREMA: Tuple[str, ...] = ("largest", "smallest")
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("single_scatter",)

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

_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "cluster_trend_direction_label": 0.62,
    "cluster_separation_extremum_label": 0.68,
    "cluster_spread_extremum_label": 0.72,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {"single_scatter": 0.58}

RGB = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _Point:
    point_id: str
    cluster_label: str
    x_value: float
    y_value: float


@dataclass(frozen=True)
class _Cluster:
    cluster_label: str
    color_rgb: RGB
    center_x: float
    center_y: float
    slope: float
    spread_x: float
    spread_y: float
    points: Tuple[_Point, ...]


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer_label: str
    answer_type: str
    evidence_cluster_labels: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    clusters: Tuple[_Cluster, ...]
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
    legend_font_size_px: int
    title_font_size_px: int
    cluster_hull_padding_px: int
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
    cluster_bboxes: Dict[str, List[float]]
    cluster_label_bboxes: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


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


def _gen_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), float(fallback))))


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


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


def _resolve_trend_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TREND_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="trend_direction",
        weights_key="trend_direction_weights",
        balance_flag_key="balanced_trend_direction_sampling",
        axis_namespace="trend_direction",
    )


def _resolve_separation_extremum(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SEPARATION_EXTREMA,
        task_id=TASK_ID,
        explicit_key="separation_extremum",
        weights_key="separation_extremum_weights",
        balance_flag_key="balanced_separation_extremum_sampling",
        axis_namespace="separation_extremum",
    )


def _resolve_spread_axis(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SPREAD_AXES,
        task_id=TASK_ID,
        explicit_key="spread_axis",
        weights_key="spread_axis_weights",
        balance_flag_key="balanced_spread_axis_sampling",
        axis_namespace="spread_axis",
    )


def _resolve_spread_extremum(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SPREAD_EXTREMA,
        task_id=TASK_ID,
        explicit_key="spread_extremum",
        weights_key="spread_extremum_weights",
        balance_flag_key="balanced_spread_extremum_sampling",
        axis_namespace="spread_extremum",
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


def _support_sampling_params(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None or params.get("query_id") is not None:
        return support_params
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) == len(_SUPPORTED_QUERY_IDS) and max(positives) - min(positives) <= 1e-9:
        support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_QUERY_IDS))
    return support_params


def _sample_cluster_labels(*, cluster_count: int, instance_seed: int) -> Tuple[str, ...]:
    label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.cluster_labels")
    labels = resolve_chart_entity_labels(
        label_rng,
        count=int(cluster_count),
        min_chars=2,
        max_chars=6,
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels)


def _target_answer_label(params: Mapping[str, Any], *, instance_seed: int, labels: Sequence[str]) -> str:
    sampling_index = params.get("_sample_cursor")
    if sampling_index is not None:
        occurrence = int(sampling_index)
    else:
        occurrence = abs(int(instance_seed))
    return str(labels[int(occurrence) % max(1, len(labels))])


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("cluster_palette_rgb", _RENDER_DEFAULTS.get("cluster_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            colors.append(_as_rgb(item, (60, 110, 180)))
    if len(colors) >= 8:
        return tuple(colors[:8])
    return (
        (38, 101, 176),
        (218, 91, 75),
        (56, 150, 96),
        (142, 92, 188),
        (218, 145, 46),
        (78, 159, 191),
        (188, 87, 132),
        (109, 125, 55),
    )


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    margin_left = _resolve_int(params, "plot_margin_left_px", 110)
    margin_right = _resolve_int(params, "plot_margin_right_px", 260)
    margin_top = _resolve_int(params, "plot_margin_top_px", 72)
    margin_bottom = _resolve_int(params, "plot_margin_bottom_px", 112)
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
        canvas_width=_resolve_int(params, "canvas_width", 1280),
        canvas_height=_resolve_int(params, "canvas_height", 820),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=_resolve_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_resolve_int(params, "grid_line_width_px", 1),
        tick_length_px=_resolve_int(params, "tick_length_px", 8),
        point_radius_px=_resolve_int(params, "point_radius_px", 7),
        tick_font_size_px=_resolve_int(params, "tick_font_size_px", 17),
        legend_font_size_px=_resolve_int(params, "legend_font_size_px", 22),
        title_font_size_px=_resolve_int(params, "title_font_size_px", 26),
        cluster_hull_padding_px=_resolve_int(params, "cluster_hull_padding_px", 14),
        axis_color_rgb=_resolve_rgb(params, "axis_color_rgb", (74, 78, 86)),
        grid_color_rgb=_resolve_rgb(params, "grid_color_rgb", (225, 228, 234)),
        text_color_rgb=_resolve_rgb(params, "text_color_rgb", (38, 41, 48)),
        text_stroke_rgb=_resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        plot_fill_rgb=_resolve_rgb(params, "plot_fill_rgb", (255, 255, 255)),
        panel_fill_rgb=_resolve_rgb(params, "panel_fill_rgb", (252, 253, 255)),
        panel_border_rgb=_resolve_rgb(params, "panel_border_rgb", (204, 210, 220)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _cluster_centers(labels: Sequence[str], *, rng: Any) -> Dict[str, Tuple[float, float]]:
    base = [
        (31.0, 34.0),
        (32.0, 66.0),
        (50.0, 48.0),
        (68.0, 34.0),
        (69.0, 66.0),
        (50.0, 78.0),
        (82.0, 48.0),
        (18.0, 48.0),
    ]
    return {
        str(label): (
            _clamp(float(center[0]) + rng.uniform(-3.0, 3.0), 14.0, 86.0),
            _clamp(float(center[1]) + rng.uniform(-3.0, 3.0), 26.0, 80.0),
        )
        for label, center in zip([str(item) for item in labels], base)
    }


def _make_points(
    *,
    cluster_label: str,
    center: Tuple[float, float],
    slope: float,
    spread_x: float,
    spread_y: float,
    count: int,
    instance_seed: int,
    x_jitter: float = 0.9,
    y_jitter: float = 0.9,
    y_jitter_scale: float = 0.28,
    flat_y_jitter_scale: float = 1.0,
) -> Tuple[_Point, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.points.{cluster_label}")
    offsets = [((float(index) - ((float(count) - 1.0) / 2.0)) / max(1.0, (float(count) - 1.0) / 2.0)) for index in range(int(count))]
    rng.shuffle(offsets)
    points: List[_Point] = []
    for index, raw_offset in enumerate(offsets):
        x_offset = float(raw_offset) * float(spread_x) + rng.uniform(-float(x_jitter), float(x_jitter))
        y_offset = (float(slope) * float(raw_offset) * float(spread_y)) + rng.uniform(-float(y_jitter), float(y_jitter)) * max(1.0, float(spread_y) * float(y_jitter_scale))
        if abs(float(slope)) < 0.12:
            y_offset += rng.uniform(-1.0, 1.0) * float(spread_y) * float(flat_y_jitter_scale)
        x_value = _clamp(float(center[0]) + x_offset, 4.0, 96.0)
        y_value = _clamp(float(center[1]) + y_offset, 4.0, 96.0)
        points.append(
            _Point(
                point_id=f"{str(cluster_label)}_{int(index):02d}",
                cluster_label=str(cluster_label),
                x_value=float(x_value),
                y_value=float(y_value),
            )
        )
    return tuple(points)


def _build_clusters(
    *,
    labels: Sequence[str],
    palette: Sequence[RGB],
    centers: Mapping[str, Tuple[float, float]],
    slopes: Mapping[str, float],
    spreads: Mapping[str, Tuple[float, float]],
    points_per_cluster: int,
    instance_seed: int,
    point_jitter_by_label: Mapping[str, Mapping[str, float]] | None = None,
) -> Tuple[_Cluster, ...]:
    clusters: List[_Cluster] = []
    for index, label in enumerate(labels):
        spread = spreads[str(label)]
        slope = float(slopes[str(label)])
        center = centers[str(label)]
        jitter = dict(point_jitter_by_label.get(str(label), {})) if point_jitter_by_label else {}
        points = _make_points(
            cluster_label=str(label),
            center=center,
            slope=slope,
            spread_x=float(spread[0]),
            spread_y=float(spread[1]),
            count=int(points_per_cluster),
            instance_seed=int(instance_seed),
            x_jitter=float(jitter.get("x_jitter", 0.9)),
            y_jitter=float(jitter.get("y_jitter", 0.9)),
            y_jitter_scale=float(jitter.get("y_jitter_scale", 0.28)),
            flat_y_jitter_scale=float(jitter.get("flat_y_jitter_scale", 1.0)),
        )
        clusters.append(
            _Cluster(
                cluster_label=str(label),
                color_rgb=tuple(palette[int(index) % len(palette)]),
                center_x=float(center[0]),
                center_y=float(center[1]),
                slope=float(slope),
                spread_x=float(spread[0]),
                spread_y=float(spread[1]),
                points=tuple(points),
            )
        )
    return tuple(clusters)


def _dataset_for_trend(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    labels: Sequence[str],
    answer_label: str,
    points_per_cluster: int,
    trend_direction: str,
    trend_direction_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.trend")
    centers = _cluster_centers(labels, rng=rng)
    distractor_count = max(0, len(labels) - 1)
    target_abs_slope_min = _gen_float(params, "trend_target_abs_slope_min", 1.35)
    target_abs_slope_max = max(float(target_abs_slope_min), _gen_float(params, "trend_target_abs_slope_max", 1.9))
    margin_min = _gen_float(params, "trend_slope_margin_min", 0.55)
    margin_max = max(float(margin_min), _gen_float(params, "trend_slope_margin_max", 1.1))
    same_direction_floor = _gen_float(params, "trend_same_direction_abs_slope_floor", 0.18)
    target_abs_slope = rng.uniform(float(target_abs_slope_min), float(target_abs_slope_max))
    max_margin_for_target = max(float(margin_min), float(target_abs_slope) - float(same_direction_floor))
    trend_slope_margin_target = rng.uniform(float(margin_min), min(float(margin_max), float(max_margin_for_target)))
    same_direction_peak = max(float(same_direction_floor), float(target_abs_slope) - float(trend_slope_margin_target))
    same_direction_count = rng.randint(2, 4)
    same_direction_candidates = [float(same_direction_peak)]
    for _ in range(max(0, int(same_direction_count) - 1)):
        same_direction_candidates.append(rng.uniform(0.08, max(0.09, float(same_direction_peak) - 0.08)))
    opposite_direction_count = rng.randint(3, 5)
    opposite_slope_min = _gen_float(params, "trend_opposite_abs_slope_min", 0.35)
    opposite_slope_max = max(float(opposite_slope_min), _gen_float(params, "trend_opposite_abs_slope_max", 1.2))
    opposite_direction_candidates = [rng.uniform(float(opposite_slope_min), float(opposite_slope_max)) for _ in range(int(opposite_direction_count))]
    neutral_candidates = [rng.uniform(-0.12, 0.12) for _ in range(2)]
    signed_same_direction_peak = float(same_direction_peak)
    distractor_abs_slopes = same_direction_candidates[1:] + [-float(value) for value in opposite_direction_candidates] + neutral_candidates
    if str(trend_direction) == "downward":
        signed_same_direction_peak = -float(signed_same_direction_peak)
        distractor_abs_slopes = [-value for value in distractor_abs_slopes]
    rng.shuffle(distractor_abs_slopes)
    other_slopes = [round(float(signed_same_direction_peak), 3)] + [
        round(float(value), 3) for value in distractor_abs_slopes[: max(0, int(distractor_count) - 1)]
    ]
    while len(other_slopes) < distractor_count:
        filler = rng.uniform(-float(opposite_slope_max), float(opposite_slope_max))
        same_direction_ceiling = max(0.08, float(target_abs_slope) - float(trend_slope_margin_target))
        if str(trend_direction) == "upward" and filler >= float(same_direction_ceiling):
            filler = rng.uniform(0.08, float(same_direction_ceiling))
        if str(trend_direction) == "downward" and filler <= -float(same_direction_ceiling):
            filler = -rng.uniform(0.08, float(same_direction_ceiling))
        other_slopes.append(round(float(filler), 3))
    slopes: Dict[str, float] = {}
    for label in labels:
        if str(label) == str(answer_label):
            slopes[str(label)] = round(float(target_abs_slope), 3) if str(trend_direction) == "upward" else -round(float(target_abs_slope), 3)
        else:
            slopes[str(label)] = float(other_slopes.pop())
    if str(trend_direction) == "upward":
        strongest_distractor = max(float(value) for key, value in slopes.items() if str(key) != str(answer_label))
        trend_slope_margin = float(slopes[str(answer_label)]) - strongest_distractor
    else:
        strongest_distractor = min(float(value) for key, value in slopes.items() if str(key) != str(answer_label))
        trend_slope_margin = strongest_distractor - float(slopes[str(answer_label)])
    spreads = {str(label): ((10.0, 8.2) if str(label) == str(answer_label) else (8.6, 7.4)) for label in labels}
    answer_x_jitter = _gen_float(params, "trend_answer_x_jitter", 0.45)
    answer_y_jitter = _gen_float(params, "trend_answer_y_jitter", 0.55)
    answer_y_jitter_scale = _gen_float(params, "trend_answer_y_jitter_scale", 0.16)
    distractor_x_jitter = _gen_float(params, "trend_distractor_x_jitter", 0.65)
    distractor_y_jitter = _gen_float(params, "trend_distractor_y_jitter", 0.75)
    distractor_y_jitter_scale = _gen_float(params, "trend_distractor_y_jitter_scale", 0.20)
    point_jitter = {
        str(label): {
            "x_jitter": float(answer_x_jitter) if str(label) == str(answer_label) else float(distractor_x_jitter),
            "y_jitter": float(answer_y_jitter) if str(label) == str(answer_label) else float(distractor_y_jitter),
            "y_jitter_scale": float(answer_y_jitter_scale) if str(label) == str(answer_label) else float(distractor_y_jitter_scale),
            "flat_y_jitter_scale": 0.35,
        }
        for label in labels
    }
    clusters = _build_clusters(
        labels=labels,
        palette=_palette(params),
        centers=centers,
        slopes=slopes,
        spreads=spreads,
        points_per_cluster=int(points_per_cluster),
        instance_seed=int(instance_seed),
        point_jitter_by_label=point_jitter,
    )
    return _Dataset(
        scene_variant="single_scatter",
        clusters=clusters,
        query=_Query(
            query_id="cluster_trend_direction_label",
            answer_label=str(answer_label),
            answer_type="string",
            evidence_cluster_labels=(str(answer_label),),
            trace={
                "trend_direction": str(trend_direction),
                "trend_direction_probabilities": dict(trend_direction_probabilities),
                "cluster_slopes": {str(key): round(float(value), 4) for key, value in slopes.items()},
                "trend_slope_margin": round(float(trend_slope_margin), 4),
                "target_abs_slope_range": [round(float(target_abs_slope_min), 4), round(float(target_abs_slope_max), 4)],
                "trend_slope_margin_range": [round(float(margin_min), 4), round(float(margin_max), 4)],
                "trend_slope_margin_target": round(float(trend_slope_margin_target), 4),
                "trend_point_jitter": {
                    "answer": {
                        "x_jitter": round(float(answer_x_jitter), 4),
                        "y_jitter": round(float(answer_y_jitter), 4),
                        "y_jitter_scale": round(float(answer_y_jitter_scale), 4),
                    },
                    "distractor": {
                        "x_jitter": round(float(distractor_x_jitter), 4),
                        "y_jitter": round(float(distractor_y_jitter), 4),
                        "y_jitter_scale": round(float(distractor_y_jitter_scale), 4),
                    },
                },
            },
        ),
    )


def _dataset_for_separation(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    labels: Sequence[str],
    answer_label: str,
    points_per_cluster: int,
    separation_extremum: str,
    separation_extremum_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.separation")
    label_list = [str(label) for label in labels]
    answer_index = label_list.index(str(answer_label))
    reference_label = label_list[(int(answer_index) + 2) % len(label_list)]
    remaining = [label for label in label_list if label not in {str(answer_label), str(reference_label)}]
    centers: Dict[str, Tuple[float, float]] = {str(reference_label): (50.0, 50.0)}
    if str(separation_extremum) == "closest":
        centers[str(answer_label)] = (59.0, 54.0)
        candidate_centers = [(37.0, 42.0), (44.0, 67.0), (66.0, 42.0), (67.0, 65.0), (32.0, 57.0), (58.0, 70.0)]
    else:
        centers[str(answer_label)] = (29.0, 34.0)
        candidate_centers = [(43.0, 46.0), (61.0, 43.0), (48.0, 68.0), (66.0, 62.0), (35.0, 58.0), (58.0, 32.0)]
    rng.shuffle(candidate_centers)
    for label, center in zip(remaining, candidate_centers):
        centers[str(label)] = (float(center[0]) + rng.uniform(-1.5, 1.5), float(center[1]) + rng.uniform(-1.5, 1.5))
    slopes = {str(label): 0.0 for label in labels}
    spreads = {str(label): (6.0, 6.0) for label in labels}
    clusters = _build_clusters(
        labels=labels,
        palette=_palette(params),
        centers=centers,
        slopes=slopes,
        spreads=spreads,
        points_per_cluster=int(points_per_cluster),
        instance_seed=int(instance_seed),
    )
    distances = {
        str(label): round(math.hypot(float(centers[str(label)][0]) - float(centers[str(reference_label)][0]), float(centers[str(label)][1]) - float(centers[str(reference_label)][1])), 4)
        for label in label_list
        if str(label) != str(reference_label)
    }
    return _Dataset(
        scene_variant="single_scatter",
        clusters=clusters,
        query=_Query(
            query_id="cluster_separation_extremum_label",
            answer_label=str(answer_label),
            answer_type="string",
            evidence_cluster_labels=(str(reference_label), str(answer_label)),
            trace={
                "reference_cluster_label": str(reference_label),
                "separation_extremum": str(separation_extremum),
                "separation_extremum_probabilities": dict(separation_extremum_probabilities),
                "centroid_distances_from_reference": dict(distances),
            },
        ),
    )


def _spread_metric(spread: Tuple[float, float], axis: str) -> float:
    if str(axis) == "horizontal":
        return float(spread[0])
    if str(axis) == "vertical":
        return float(spread[1])
    return math.hypot(float(spread[0]), float(spread[1]))


def _dataset_for_spread(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    labels: Sequence[str],
    answer_label: str,
    points_per_cluster: int,
    spread_axis: str,
    spread_extremum: str,
    spread_axis_probabilities: Mapping[str, float],
    spread_extremum_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.spread")
    centers = _cluster_centers(labels, rng=rng)
    other_large = [(7.2, 5.6), (5.6, 7.2), (7.0, 7.0), (6.4, 6.0), (6.0, 6.8), (7.7, 5.4), (5.4, 7.7)]
    other_small = [(4.0, 3.4), (3.4, 4.0), (4.2, 3.6), (3.6, 4.2), (4.0, 4.0), (3.2, 3.8), (4.3, 3.2)]
    rng.shuffle(other_large)
    rng.shuffle(other_small)
    spreads: Dict[str, Tuple[float, float]] = {}
    for label in labels:
        if str(label) == str(answer_label):
            if str(spread_extremum) == "largest":
                if str(spread_axis) == "horizontal":
                    spreads[str(label)] = (13.5, 2.9)
                elif str(spread_axis) == "vertical":
                    spreads[str(label)] = (2.9, 13.5)
                else:
                    spreads[str(label)] = (10.2, 10.2)
            else:
                if str(spread_axis) == "horizontal":
                    spreads[str(label)] = (2.0, 4.2)
                elif str(spread_axis) == "vertical":
                    spreads[str(label)] = (4.2, 2.0)
                else:
                    spreads[str(label)] = (2.4, 2.4)
        else:
            spreads[str(label)] = tuple(other_small.pop() if str(spread_extremum) == "largest" else other_large.pop())
    slopes = {str(label): 0.0 for label in labels}
    clusters = _build_clusters(
        labels=labels,
        palette=_palette(params),
        centers=centers,
        slopes=slopes,
        spreads=spreads,
        points_per_cluster=int(points_per_cluster),
        instance_seed=int(instance_seed),
    )
    metrics = {str(label): round(_spread_metric(spreads[str(label)], str(spread_axis)), 4) for label in labels}
    return _Dataset(
        scene_variant="single_scatter",
        clusters=clusters,
        query=_Query(
            query_id="cluster_spread_extremum_label",
            answer_label=str(answer_label),
            answer_type="string",
            evidence_cluster_labels=(str(answer_label),),
            trace={
                "spread_axis": str(spread_axis),
                "spread_extremum": str(spread_extremum),
                "spread_axis_probabilities": dict(spread_axis_probabilities),
                "spread_extremum_probabilities": dict(spread_extremum_probabilities),
                "cluster_spread_metrics": dict(metrics),
            },
        ),
    )


def _draw_text_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: Tuple[float, float],
    *,
    font: Any,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 0,
) -> List[float]:
    try:
        draw_text_traced(draw,(float(xy[0]), float(xy[1])), str(text), font=font, fill=fill, stroke_fill=stroke_fill, stroke_width=int(stroke_width), role="readout", required=False)
        box = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=int(stroke_width))
        return _bbox(box)
    except Exception:
        draw_text_traced(draw,(float(xy[0]), float(xy[1])), str(text), font=font, fill=fill, role="readout", required=False)
        width, height = draw.textsize(str(text), font=font)
        return _bbox([float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)])


def _plot_xy(point: _Point, *, plot_bbox: Sequence[float]) -> Tuple[float, float]:
    left, top, right, bottom = [float(value) for value in plot_bbox]
    x = left + (float(point.x_value) / 100.0) * (right - left)
    y = bottom - (float(point.y_value) / 100.0) * (bottom - top)
    return (float(x), float(y))


def _render_scatter(
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
    axis_label_font = load_font(18, bold=True)
    legend_font = load_font(int(render_params.legend_font_size_px), bold=True)
    legend_letter_font = load_font(max(18, int(render_params.legend_font_size_px) + 2), bold=True)
    panel_bbox = [
        float(plot_bbox[0] - 56.0),
        float(plot_bbox[1] - 52.0),
        float(width - 36.0),
        float(plot_bbox[3] + 72.0),
    ]
    draw.rounded_rectangle(panel_bbox, radius=6, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=2)
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb, outline=render_params.axis_color_rgb, width=int(render_params.axis_line_width_px))
    for tick in range(0, 101, 20):
        x = plot_bbox[0] + (float(tick) / 100.0) * (plot_bbox[2] - plot_bbox[0])
        y = plot_bbox[3] - (float(tick) / 100.0) * (plot_bbox[3] - plot_bbox[1])
        draw.line([x, plot_bbox[1], x, plot_bbox[3]], fill=render_params.grid_color_rgb, width=int(render_params.grid_line_width_px))
        draw.line([plot_bbox[0], y, plot_bbox[2], y], fill=render_params.grid_color_rgb, width=int(render_params.grid_line_width_px))
        draw.line([x, plot_bbox[3], x, plot_bbox[3] + render_params.tick_length_px], fill=render_params.axis_color_rgb, width=1)
        draw.line([plot_bbox[0] - render_params.tick_length_px, y, plot_bbox[0], y], fill=render_params.axis_color_rgb, width=1)
        draw_text_traced(draw,(x, plot_bbox[3] + 12), str(tick), font=tick_font, fill=render_params.text_color_rgb, anchor="mt", role="readout", required=False)
        draw_text_traced(draw,(plot_bbox[0] - 13, y), str(tick), font=tick_font, fill=render_params.text_color_rgb, anchor="rm", role="readout", required=False)

    title_bbox = _draw_text_box(
        draw,
        "Cluster Scatter Plot",
        (plot_bbox[0], panel_bbox[1] + 16),
        font=title_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
    )
    x_label_box = _draw_text_box(
        draw,
        "X score",
        ((plot_bbox[0] + plot_bbox[2]) / 2.0 - 28, plot_bbox[3] + 54),
        font=axis_label_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
    )
    y_label_box = _draw_text_box(
        draw,
        "Y score",
        (plot_bbox[0] - 84, plot_bbox[1] - 28),
        font=axis_label_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
    )

    point_bboxes: Dict[str, List[float]] = {}
    cluster_bboxes: Dict[str, List[float]] = {}
    cluster_label_bboxes: Dict[str, List[float]] = {}
    legend_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = [
        {"entity_id": "scatter_panel", "entity_type": "chart_panel", "bbox_xyxy": _bbox(panel_bbox), "attrs": {}},
        {"entity_id": "scatter_plot", "entity_type": "scatter_plot", "bbox_xyxy": _bbox(plot_bbox), "attrs": {}},
        {"entity_id": "chart_title", "entity_type": "chart_title", "bbox_xyxy": title_bbox, "attrs": {"title": "Cluster Scatter Plot"}},
        {"entity_id": "x_axis_label", "entity_type": "axis_label", "bbox_xyxy": x_label_box, "attrs": {"axis": "x"}},
        {"entity_id": "y_axis_label", "entity_type": "axis_label", "bbox_xyxy": y_label_box, "attrs": {"axis": "y"}},
    ]

    radius = float(render_params.point_radius_px)
    for cluster in dataset.clusters:
        plotted = [_plot_xy(point, plot_bbox=plot_bbox) for point in cluster.points]
        point_boxes_for_cluster: List[List[float]] = []
        for point, (px, py) in zip(cluster.points, plotted):
            bbox = [px - radius, py - radius, px + radius, py + radius]
            point_bboxes[str(point.point_id)] = _bbox(bbox)
            point_boxes_for_cluster.append(_bbox(bbox))
        hull = _bbox_union(point_boxes_for_cluster)
        hull_pad = float(render_params.cluster_hull_padding_px)
        hull = _bbox([hull[0] - hull_pad, hull[1] - hull_pad, hull[2] + hull_pad, hull[3] + hull_pad])
        cluster_bboxes[str(cluster.cluster_label)] = list(hull)
        for point, (px, py) in zip(cluster.points, plotted):
            point_box = point_bboxes[str(point.point_id)]
            draw.ellipse(point_box, fill=cluster.color_rgb, outline=(255, 255, 255), width=2)
            entities.append(
                {
                    "entity_id": str(point.point_id),
                    "entity_type": "scatter_point",
                    "bbox_xyxy": list(point_box),
                    "attrs": {
                        "cluster_label": str(cluster.cluster_label),
                        "x_value": round(float(point.x_value), 3),
                        "y_value": round(float(point.y_value), 3),
                    },
                }
            )
        entities.append(
            {
                "entity_id": f"cluster_{cluster.cluster_label}",
                "entity_type": "scatter_cluster",
                "bbox_xyxy": list(hull),
                "attrs": {
                    "cluster_label": str(cluster.cluster_label),
                    "center_x": round(float(cluster.center_x), 3),
                    "center_y": round(float(cluster.center_y), 3),
                    "slope": round(float(cluster.slope), 4),
                    "spread_x": round(float(cluster.spread_x), 3),
                    "spread_y": round(float(cluster.spread_y), 3),
                    "point_ids": [str(point.point_id) for point in cluster.points],
                },
            }
        )

    legend_left = plot_bbox[2] + 36.0
    legend_top = plot_bbox[1] + 34.0
    legend_row_height = 54.0
    legend_swatch_size = 32.0
    legend_row_right = float(width - 54.0)
    _draw_text_box(
        draw,
        "Clusters",
        (legend_left, legend_top - 32.0),
        font=legend_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
    )
    for index, cluster in enumerate(dataset.clusters):
        y = legend_top + float(index) * legend_row_height
        row_box = [legend_left - 10.0, y - 7.0, legend_row_right, y + legend_swatch_size + 7.0]
        draw.rounded_rectangle(row_box, radius=6, fill=(255, 255, 255), outline=render_params.panel_border_rgb, width=1)
        swatch = [legend_left, y, legend_left + legend_swatch_size, y + legend_swatch_size]
        draw.rounded_rectangle(swatch, radius=7, fill=cluster.color_rgb, outline=(255, 255, 255), width=2)
        letter_center = ((swatch[0] + swatch[2]) / 2.0, (swatch[1] + swatch[3]) / 2.0 + 1.0)
        draw_text_traced(draw,
            letter_center,
            str(cluster.cluster_label),
            font=legend_letter_font,
            fill=(255, 255, 255),
            anchor="mm",
            stroke_width=1,
            stroke_fill=(0, 0, 0),
         role="readout", required=False,)
        text_box = _draw_text_box(
            draw,
            f"Cluster {cluster.cluster_label}",
            (legend_left + legend_swatch_size + 14.0, y + 1.0),
            font=legend_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
        )
        cluster_label_bboxes[str(cluster.cluster_label)] = list(text_box)
        legend_bboxes[str(cluster.cluster_label)] = _bbox_union([row_box, swatch, text_box])
        entities.append(
            {
                "entity_id": f"legend_{cluster.cluster_label}",
                "entity_type": "legend_entry",
                "bbox_xyxy": list(legend_bboxes[str(cluster.cluster_label)]),
                "attrs": {"cluster_label": str(cluster.cluster_label)},
            }
        )

    return _Rendered(
        image=image,
        entities=tuple(dict(item) for item in entities),
        plot_bbox_px=_bbox(plot_bbox),
        point_bboxes=dict(point_bboxes),
        cluster_bboxes=dict(cluster_bboxes),
        cluster_label_bboxes=dict(cluster_label_bboxes),
        legend_bboxes=dict(legend_bboxes),
    )


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    trace = dict(dataset.query.trace)
    return {
        "object_description": str(prompt_defaults["object_description_single_scatter"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "evidence_hint": str(prompt_defaults["evidence_hint"]),
        "answer_hint": str(prompt_defaults["answer_hint"]),
        "json_example": str(prompt_defaults["json_example"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
        "trend_direction_phrase": str(trace.get("trend_direction", "")),
        "reference_cluster_label": str(trace.get("reference_cluster_label", "")),
        "separation_extremum_phrase": "closest to" if str(trace.get("separation_extremum")) == "closest" else "farthest from",
        "spread_axis_phrase": str(trace.get("spread_axis", "")),
        "spread_extremum_phrase": str(trace.get("spread_extremum", "")),
    }


class ChartsScatterClusterQueryTask:
    """Answer cluster and trend questions over a scatter plot."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "scatter"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_id_probabilities=query_id_probabilities)
        cluster_min = _gen_int(params, "cluster_count_min", 5)
        cluster_max = _gen_int(params, "cluster_count_max", 8)
        cluster_count_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.cluster_count")
        cluster_count = int(cluster_count_rng.randint(int(cluster_min), int(cluster_max)))
        cluster_count = max(4, min(8, int(cluster_count)))
        labels = _sample_cluster_labels(cluster_count=int(cluster_count), instance_seed=int(instance_seed))
        points_min = _gen_int(params, "points_per_cluster_min", 8)
        points_max = _gen_int(params, "points_per_cluster_max", 12)
        point_count_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.point_count")
        points_per_cluster = int(point_count_rng.randint(int(points_min), int(points_max)))
        answer_label = _target_answer_label(support_params, instance_seed=int(instance_seed), labels=labels)

        if str(query_id) == "cluster_trend_direction_label":
            trend_direction, trend_direction_probabilities = _resolve_trend_direction(
                support_params,
                instance_seed=int(instance_seed),
            )
            dataset = _dataset_for_trend(
                params=params,
                instance_seed=int(instance_seed),
                labels=labels,
                answer_label=str(answer_label),
                points_per_cluster=int(points_per_cluster),
                trend_direction=str(trend_direction),
                trend_direction_probabilities=trend_direction_probabilities,
            )
        elif str(query_id) == "cluster_separation_extremum_label":
            separation_extremum, separation_extremum_probabilities = _resolve_separation_extremum(
                support_params,
                instance_seed=int(instance_seed),
            )
            dataset = _dataset_for_separation(
                params=params,
                instance_seed=int(instance_seed),
                labels=labels,
                answer_label=str(answer_label),
                points_per_cluster=int(points_per_cluster),
                separation_extremum=str(separation_extremum),
                separation_extremum_probabilities=separation_extremum_probabilities,
            )
        else:
            spread_axis, spread_axis_probabilities = _resolve_spread_axis(support_params, instance_seed=int(instance_seed))
            spread_params = dict(support_params)
            sampling_index = spread_params.get("_sample_cursor")
            if sampling_index is not None and spread_params.get("spread_axis") is None:
                spread_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_SPREAD_AXES))
            spread_extremum, spread_extremum_probabilities = _resolve_spread_extremum(
                spread_params,
                instance_seed=int(instance_seed),
            )
            dataset = _dataset_for_spread(
                params=params,
                instance_seed=int(instance_seed),
                labels=labels,
                answer_label=str(answer_label),
                points_per_cluster=int(points_per_cluster),
                spread_axis=str(spread_axis),
                spread_extremum=str(spread_extremum),
                spread_axis_probabilities=spread_axis_probabilities,
                spread_extremum_probabilities=spread_extremum_probabilities,
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
            rendered = _render_scatter(background, dataset=dataset, render_params=render_params)
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
                "answer_hint",
                "evidence_hint",
                "json_example",
                "json_example_answer_only",
                "object_description_single_scatter",
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
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=_build_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_cluster_labels = [str(label) for label in dataset.query.evidence_cluster_labels]
        evidence_point_ids = [
            str(point.point_id)
            for cluster in dataset.clusters
            if str(cluster.cluster_label) in set(evidence_cluster_labels)
            for point in cluster.points
        ]
        evidence_bbox_map: Dict[str, List[float]] = {
            "answer_cluster": list(rendered.cluster_bboxes[str(dataset.query.answer_label)])
        }
        if str(dataset.query.query_id) == "cluster_separation_extremum_label":
            reference_label = str(dataset.query.trace["reference_cluster_label"])
            evidence_bbox_map = {
                "reference_cluster": list(rendered.cluster_bboxes[str(reference_label)]),
                "answer_cluster": list(rendered.cluster_bboxes[str(dataset.query.answer_label)]),
            }
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=str(dataset.query.answer_label))
        evidence_gt = TypedValue(type="keyed_bbox_map", value=dict(evidence_bbox_map))
        projected_evidence = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(evidence_bbox_map),
            "pixel_keyed_bbox_map": dict(evidence_bbox_map),
            "point_ids": list(evidence_point_ids),
            "cluster_labels": list(evidence_cluster_labels),
            "cluster_bboxes": {
                str(label): list(rendered.cluster_bboxes[str(label)])
                for label in evidence_cluster_labels
            },
        }

        total_points = int(sum(len(cluster.points) for cluster in dataset.clusters))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(total_points), [24, 60]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_id)])),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )
        values_by_cluster = {
            str(cluster.cluster_label): {
                "center": [round(float(cluster.center_x), 3), round(float(cluster.center_y), 3)],
                "slope": round(float(cluster.slope), 4),
                "spread_x": round(float(cluster.spread_x), 3),
                "spread_y": round(float(cluster.spread_y), 3),
                "points": [
                    {
                        "point_id": str(point.point_id),
                        "x_value": round(float(point.x_value), 3),
                        "y_value": round(float(point.y_value), 3),
                    }
                    for point in cluster.points
                ],
            }
            for cluster in dataset.clusters
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_scatter_cluster",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": str(dataset.query.answer_label),
                    "evidence_point_ids": list(evidence_point_ids),
                    "evidence_cluster_labels": list(evidence_cluster_labels),
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
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": {"single_scatter": 1.0},
                    "cluster_count": int(cluster_count),
                    "points_per_cluster": int(points_per_cluster),
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
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_asset_version": font_asset_version(),
                "chart_font_family": str(chart_font_family),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_bboxes_px": dict(rendered.point_bboxes),
                "cluster_bboxes_px": dict(rendered.cluster_bboxes),
                "cluster_label_bboxes_px": dict(rendered.cluster_label_bboxes),
                "legend_bboxes_px": dict(rendered.legend_bboxes),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "scatter_cluster_query",
                "answer": str(dataset.query.answer_label),
                "answer_type": str(dataset.query.answer_type),
                "cluster_labels": list(labels),
                "cluster_count": int(cluster_count),
                "points_per_cluster": int(points_per_cluster),
                "total_point_count": int(total_points),
                "values_by_cluster": dict(values_by_cluster),
                "evidence_point_ids": list(evidence_point_ids),
                "evidence_cluster_labels": list(evidence_cluster_labels),
                "query_id_probabilities": dict(query_id_probabilities),
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "scatter_cluster_witness",
                "point_ids": list(evidence_point_ids),
                "cluster_labels": list(evidence_cluster_labels),
                "answer": str(dataset.query.answer_label),
            },
            "projected_evidence": dict(projected_evidence),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }
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


@register_task
class ChartsScatterClusterTrendDirectionLabelTask(FixedChartQueryVariantTaskMixin, ChartsScatterClusterQueryTask):
    """Return the cluster label with a requested trend direction."""

    task_id = "task_charts__scatter_cluster__cluster_trend_direction_label"
    fixed_query_id = "cluster_trend_direction_label"


@register_task
class ChartsScatterClusterFeatureExtremumLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsScatterClusterQueryTask,
):
    """Return the cluster label with a requested extremal feature."""

    task_id = "task_charts__scatter_cluster__cluster_feature_extremum_label"
    allowed_query_ids = ("cluster_separation_extremum_label", "cluster_spread_extremum_label")


__all__ = [
    "ChartsScatterClusterFeatureExtremumLabelTask",
    "ChartsScatterClusterQueryTask",
    "ChartsScatterClusterTrendDirectionLabelTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
