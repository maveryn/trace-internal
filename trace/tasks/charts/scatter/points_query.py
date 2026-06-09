"""Scatter point-count and category summary chart tasks."""

from __future__ import annotations

import math
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
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.font_assets import font_asset_version
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font, temporary_default_font_family
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from ..shared.label_assets import ResolvedChartLabels, resolve_chart_category_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import chart_font_asset_metadata, load_chart_background_defaults, load_chart_noise_defaults, sample_chart_font_family


TASK_ID = "charts_scatter_points_query_base"
SCENE_ID = "scatter_points"

_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "axis_threshold_point_count",
    "category_axis_mean_extremum_label",
    "category_threshold_point_count",
)
_SUPPORTED_THRESHOLD_AXES: Tuple[str, ...] = ("x", "y")
_SUPPORTED_THRESHOLD_DIRECTIONS: Tuple[str, ...] = ("above", "below")
_SUPPORTED_MEAN_AXES: Tuple[str, ...] = ("x", "y")
_SUPPORTED_MEAN_EXTREMA: Tuple[str, ...] = ("largest", "smallest")
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("plain_scatter", "categorized_scatter")
_MARKER_SHAPES: Tuple[str, ...] = ("circle", "square", "diamond", "triangle", "ring", "pentagon")

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

_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "axis_threshold_point_count": 0.58,
    "category_axis_mean_extremum_label": 0.70,
    "category_threshold_point_count": 0.74,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "plain_scatter": 0.54,
    "categorized_scatter": 0.66,
}

RGB = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _Point:
    point_id: str
    x_value: float
    y_value: float
    category_label: str
    color_rgb: RGB
    marker_shape: str


@dataclass(frozen=True)
class _Category:
    label: str
    color_rgb: RGB
    marker_shape: str
    point_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    annotation_point_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    points: Tuple[_Point, ...]
    categories: Tuple[_Category, ...]
    query: _Query
    label_resolution: ResolvedChartLabels | None = None


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
    legend_font_size_px: int
    title_font_size_px: int
    legend_gap_px: int
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    text_color_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    plot_fill_rgb: RGB
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    threshold_line_rgb: RGB
    threshold_label_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    panel_bbox_px: List[float]
    point_bboxes: Dict[str, List[float]]
    point_centers: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]
    threshold_guide_bbox_px: List[float]
    title_bbox_px: List[float]
    x_axis_label_bbox_px: List[float]
    y_axis_label_bbox_px: List[float]
    title_text: str


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _bbox_union(boxes: Sequence[Sequence[float]]) -> List[float]:
    valid = [tuple(float(value) for value in box[:4]) for box in boxes if len(box) >= 4]
    if not valid:
        return []
    return _bbox(
        (
            min(box[0] for box in valid),
            min(box[1] for box in valid),
            max(box[2] for box in valid),
            max(box[3] for box in valid),
        )
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


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


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _gen_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), float(fallback))))


def _gen_sequence(params: Mapping[str, Any], key: str, fallback: Sequence[Any]) -> Tuple[Any, ...]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return tuple(raw)
    return tuple(fallback)


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


def _resolve_threshold_axis(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_THRESHOLD_AXES,
        task_id=TASK_ID,
        explicit_key="threshold_axis",
        weights_key="threshold_axis_weights",
        balance_flag_key="balanced_threshold_axis_sampling",
        axis_namespace="threshold_axis",
    )


def _resolve_threshold_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_THRESHOLD_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="threshold_direction",
        weights_key="threshold_direction_weights",
        balance_flag_key="balanced_threshold_direction_sampling",
        axis_namespace="threshold_direction",
    )


def _resolve_mean_axis(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_MEAN_AXES,
        task_id=TASK_ID,
        explicit_key="mean_axis",
        weights_key="mean_axis_weights",
        balance_flag_key="balanced_mean_axis_sampling",
        axis_namespace="mean_axis",
    )


def _resolve_mean_extremum(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_MEAN_EXTREMA,
        task_id=TASK_ID,
        explicit_key="mean_extremum",
        weights_key="mean_extremum_weights",
        balance_flag_key="balanced_mean_extremum_sampling",
        axis_namespace="mean_extremum",
    )


def _sample_count(rng, *, low: int, high: int) -> int:
    low = int(low)
    high = max(int(low), int(high))
    return int(rng.randint(low, high))


def _sample_threshold(rng, params: Mapping[str, Any]) -> int:
    values = [int(value) for value in _gen_sequence(params, "threshold_values", (20, 30, 40, 50, 60, 70, 80))]
    if not values:
        values = [20, 30, 40, 50, 60, 70, 80]
    return int(rng.choice(values))


def _coord_on_side(rng, *, threshold: float, direction: str, match: bool, margin: float = 4.0) -> float:
    direction_text = str(direction)
    threshold = float(threshold)
    if direction_text == "above":
        low, high = (threshold + margin, 96.0) if bool(match) else (4.0, threshold - margin)
    else:
        low, high = (4.0, threshold - margin) if bool(match) else (threshold + margin, 96.0)
    if low > high:
        low, high = min(low, high), max(low, high)
    return round(float(rng.uniform(float(low), float(high))), 3)


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("scatter_points_category_palette_rgb", _RENDER_DEFAULTS.get("scatter_points_category_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            colors.append(_as_rgb(item, (42, 96, 176)))
    if len(colors) >= 6:
        return tuple(colors)
    return (
        (42, 96, 176),
        (210, 83, 72),
        (52, 144, 92),
        (138, 82, 178),
        (215, 137, 42),
        (44, 148, 169),
        (184, 73, 124),
    )


def _label_metadata(label_resolution: ResolvedChartLabels | None) -> Dict[str, Any]:
    if label_resolution is None:
        return {}
    return {
        "labels": list(label_resolution.labels),
        "label_variant": str(label_resolution.label_variant),
        "label_pool_kind": str(label_resolution.label_pool_kind),
        "label_source_kind": str(label_resolution.label_source_kind),
        "label_bucket": str(label_resolution.label_bucket),
        "label_manifest": str(label_resolution.label_manifest),
        "label_filter": dict(label_resolution.label_filter),
        "label_bucket_probabilities": dict(label_resolution.label_bucket_probabilities),
    }


def _resolve_category_labels(rng, params: Mapping[str, Any], count: int) -> ResolvedChartLabels:
    weights = params.get("category_label_bucket_weights", _GEN_DEFAULTS.get("category_label_bucket_weights"))
    return resolve_chart_category_labels(
        rng,
        count=int(count),
        min_chars=int(_gen_int(params, "category_label_min_chars", 3)),
        max_chars=int(_gen_int(params, "category_label_max_chars", 12)),
        allow_spaces=bool(params.get("category_label_allow_spaces", group_default(_GEN_DEFAULTS, "category_label_allow_spaces", True))),
        bucket_weights=weights if isinstance(weights, Mapping) else None,
    )


def _new_point(
    *,
    point_id: str,
    x_value: float,
    y_value: float,
    category_label: str,
    color_rgb: RGB,
    marker_shape: str,
) -> _Point:
    return _Point(
        point_id=str(point_id),
        x_value=round(float(x_value), 3),
        y_value=round(float(y_value), 3),
        category_label=str(category_label),
        color_rgb=tuple(int(channel) for channel in color_rgb),
        marker_shape=str(marker_shape),
    )


def _build_axis_threshold_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axis_threshold")
    threshold_axis, threshold_axis_probs = _resolve_threshold_axis(params, instance_seed=int(instance_seed))
    threshold_direction, threshold_direction_probs = _resolve_threshold_direction(params, instance_seed=int(instance_seed))
    point_count = _sample_count(
        rng,
        low=_gen_int(params, "scatter_points_count_min", 28),
        high=_gen_int(params, "scatter_points_count_max", 54),
    )
    threshold_value = _sample_threshold(rng, params)
    answer_low = max(1, _gen_int(params, "axis_threshold_answer_min", 4))
    answer_high = min(point_count - 1, _gen_int(params, "axis_threshold_answer_max", 18))
    answer_count = _sample_count(rng, low=answer_low, high=max(answer_low, answer_high))
    matching_indices = set(rng.sample(range(point_count), k=int(answer_count)))
    color_rgb = _as_rgb(params.get("plain_point_rgb", _RENDER_DEFAULTS.get("plain_point_rgb")), (48, 99, 176))
    marker_shape = str(params.get("plain_marker_shape", group_default(_GEN_DEFAULTS, "plain_marker_shape", "circle")))

    points: List[_Point] = []
    annotation_point_ids: List[str] = []
    for index in range(point_count):
        point_id = f"P{index + 1:02d}"
        matches = index in matching_indices
        queried_value = _coord_on_side(rng, threshold=float(threshold_value), direction=str(threshold_direction), match=matches)
        other_value = round(float(rng.uniform(4.0, 96.0)), 3)
        if str(threshold_axis) == "x":
            point = _new_point(
                point_id=point_id,
                x_value=queried_value,
                y_value=other_value,
                category_label="",
                color_rgb=color_rgb,
                marker_shape=marker_shape,
            )
        else:
            point = _new_point(
                point_id=point_id,
                x_value=other_value,
                y_value=queried_value,
                category_label="",
                color_rgb=color_rgb,
                marker_shape=marker_shape,
            )
        points.append(point)
        if matches:
            annotation_point_ids.append(str(point_id))

    trace = {
        "threshold_axis": str(threshold_axis),
        "threshold_direction": str(threshold_direction),
        "threshold_value": int(threshold_value),
        "threshold_axis_probabilities": dict(threshold_axis_probs),
        "threshold_direction_probabilities": dict(threshold_direction_probs),
        "query_id_probabilities": dict(query_probabilities),
        "target_answer_count": int(answer_count),
    }
    return _Dataset(
        scene_variant="plain_scatter",
        points=tuple(points),
        categories=(),
        query=_Query(
            query_id=str(query_id),
            answer=int(answer_count),
            answer_type="integer",
            annotation_point_ids=tuple(annotation_point_ids),
            trace=trace,
        ),
    )


def _build_category_mean_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.category_mean")
    mean_axis, mean_axis_probs = _resolve_mean_axis(params, instance_seed=int(instance_seed))
    mean_extremum, mean_extremum_probs = _resolve_mean_extremum(params, instance_seed=int(instance_seed))
    category_count = _sample_count(
        rng,
        low=_gen_int(params, "scatter_points_category_count_min", 4),
        high=_gen_int(params, "scatter_points_category_count_max", 6),
    )
    points_per_category = _sample_count(
        rng,
        low=_gen_int(params, "scatter_points_per_category_min", 6),
        high=_gen_int(params, "scatter_points_per_category_max", 10),
    )
    label_resolution = _resolve_category_labels(rng, params, int(category_count))
    labels = tuple(str(label) for label in label_resolution.labels)
    colors = _palette(params)
    target_index = int(rng.randrange(int(category_count)))
    target_label = str(labels[target_index])
    margin = max(3.0, _gen_float(params, "mean_extremum_margin_min", 8.0))
    target_center = float(rng.uniform(72.0, 88.0) if str(mean_extremum) == "largest" else rng.uniform(12.0, 28.0))
    distractor_low = 10.0 if str(mean_extremum) == "largest" else min(96.0, target_center + margin)
    distractor_high = max(4.0, target_center - margin) if str(mean_extremum) == "largest" else 90.0
    if distractor_low > distractor_high:
        distractor_low, distractor_high = min(distractor_low, distractor_high), max(distractor_low, distractor_high)

    points: List[_Point] = []
    categories: List[_Category] = []
    annotation_point_ids: List[str] = []
    means: Dict[str, Dict[str, float]] = {}

    for category_index, label in enumerate(labels):
        is_target = int(category_index) == int(target_index)
        marker_shape = _MARKER_SHAPES[int(category_index) % len(_MARKER_SHAPES)]
        color_rgb = colors[int(category_index) % len(colors)]
        point_ids: List[str] = []
        queried_center = target_center if is_target else float(rng.uniform(distractor_low, distractor_high))
        other_center = float(rng.uniform(18.0, 82.0))
        xs: List[float] = []
        ys: List[float] = []
        for point_index in range(int(points_per_category)):
            point_id = f"C{category_index + 1:02d}P{point_index + 1:02d}"
            queried_value = _clamp(float(rng.gauss(queried_center, 4.0)), 4.0, 96.0)
            other_value = _clamp(float(rng.gauss(other_center, 12.0)), 4.0, 96.0)
            if str(mean_axis) == "x":
                x_value, y_value = queried_value, other_value
            else:
                x_value, y_value = other_value, queried_value
            point = _new_point(
                point_id=point_id,
                x_value=x_value,
                y_value=y_value,
                category_label=str(label),
                color_rgb=color_rgb,
                marker_shape=marker_shape,
            )
            points.append(point)
            point_ids.append(str(point_id))
            xs.append(float(point.x_value))
            ys.append(float(point.y_value))
            if is_target:
                annotation_point_ids.append(str(point_id))
        categories.append(_Category(label=str(label), color_rgb=color_rgb, marker_shape=marker_shape, point_ids=tuple(point_ids)))
        means[str(label)] = {
            "x": round(float(sum(xs) / len(xs)), 4),
            "y": round(float(sum(ys) / len(ys)), 4),
        }

    target_mean = float(means[target_label][str(mean_axis)])
    other_means = [float(values[str(mean_axis)]) for label, values in means.items() if str(label) != target_label]
    actual_margin = (
        target_mean - max(other_means)
        if str(mean_extremum) == "largest"
        else min(other_means) - target_mean
    )
    trace = {
        "mean_axis": str(mean_axis),
        "mean_extremum": str(mean_extremum),
        "mean_axis_probabilities": dict(mean_axis_probs),
        "mean_extremum_probabilities": dict(mean_extremum_probs),
        "query_id_probabilities": dict(query_probabilities),
        "target_category_label": str(target_label),
        "category_means": dict(means),
        "mean_margin": round(float(actual_margin), 4),
        "label_resolution": _label_metadata(label_resolution),
    }
    return _Dataset(
        scene_variant="categorized_scatter",
        points=tuple(points),
        categories=tuple(categories),
        query=_Query(
            query_id=str(query_id),
            answer=str(target_label),
            answer_type="string",
            annotation_point_ids=tuple(annotation_point_ids),
            trace=trace,
        ),
        label_resolution=label_resolution,
    )


def _build_category_threshold_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.category_threshold")
    threshold_axis, threshold_axis_probs = _resolve_threshold_axis(params, instance_seed=int(instance_seed))
    threshold_direction, threshold_direction_probs = _resolve_threshold_direction(params, instance_seed=int(instance_seed))
    category_count = _sample_count(
        rng,
        low=_gen_int(params, "scatter_points_category_count_min", 4),
        high=_gen_int(params, "scatter_points_category_count_max", 6),
    )
    points_per_category = _sample_count(
        rng,
        low=_gen_int(params, "category_threshold_points_per_category_min", 7),
        high=_gen_int(params, "category_threshold_points_per_category_max", 12),
    )
    threshold_value = _sample_threshold(rng, params)
    label_resolution = _resolve_category_labels(rng, params, int(category_count))
    labels = tuple(str(label) for label in label_resolution.labels)
    colors = _palette(params)
    target_index = int(rng.randrange(int(category_count)))
    target_label = str(labels[target_index])
    answer_low = max(1, _gen_int(params, "category_threshold_answer_min", 2))
    answer_high = min(int(points_per_category) - 1, _gen_int(params, "category_threshold_answer_max", 9))
    answer_count = _sample_count(rng, low=answer_low, high=max(answer_low, answer_high))
    target_matching_indices = set(rng.sample(range(int(points_per_category)), k=int(answer_count)))

    points: List[_Point] = []
    categories: List[_Category] = []
    annotation_point_ids: List[str] = []
    match_counts_by_category: Dict[str, int] = {}
    for category_index, label in enumerate(labels):
        marker_shape = _MARKER_SHAPES[int(category_index) % len(_MARKER_SHAPES)]
        color_rgb = colors[int(category_index) % len(colors)]
        point_ids: List[str] = []
        category_match_count = 0
        for point_index in range(int(points_per_category)):
            point_id = f"C{category_index + 1:02d}P{point_index + 1:02d}"
            if int(category_index) == int(target_index):
                matches = int(point_index) in target_matching_indices
            else:
                matches = bool(rng.random() < 0.42)
            queried_value = _coord_on_side(rng, threshold=float(threshold_value), direction=str(threshold_direction), match=matches)
            other_value = round(float(rng.uniform(4.0, 96.0)), 3)
            if str(threshold_axis) == "x":
                x_value, y_value = queried_value, other_value
            else:
                x_value, y_value = other_value, queried_value
            point = _new_point(
                point_id=point_id,
                x_value=x_value,
                y_value=y_value,
                category_label=str(label),
                color_rgb=color_rgb,
                marker_shape=marker_shape,
            )
            points.append(point)
            point_ids.append(str(point_id))
            if matches:
                category_match_count += 1
                if int(category_index) == int(target_index):
                    annotation_point_ids.append(str(point_id))
        categories.append(_Category(label=str(label), color_rgb=color_rgb, marker_shape=marker_shape, point_ids=tuple(point_ids)))
        match_counts_by_category[str(label)] = int(category_match_count)

    trace = {
        "threshold_axis": str(threshold_axis),
        "threshold_direction": str(threshold_direction),
        "threshold_value": int(threshold_value),
        "target_category_label": str(target_label),
        "threshold_axis_probabilities": dict(threshold_axis_probs),
        "threshold_direction_probabilities": dict(threshold_direction_probs),
        "query_id_probabilities": dict(query_probabilities),
        "match_counts_by_category": dict(match_counts_by_category),
        "label_resolution": _label_metadata(label_resolution),
    }
    return _Dataset(
        scene_variant="categorized_scatter",
        points=tuple(points),
        categories=tuple(categories),
        query=_Query(
            query_id=str(query_id),
            answer=int(answer_count),
            answer_type="integer",
            annotation_point_ids=tuple(annotation_point_ids),
            trace=trace,
        ),
        label_resolution=label_resolution,
    )


def _build_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    if str(query_id) == "axis_threshold_point_count":
        return _build_axis_threshold_dataset(
            params=params,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            query_probabilities=query_probabilities,
        )
    if str(query_id) == "category_axis_mean_extremum_label":
        return _build_category_mean_dataset(
            params=params,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            query_probabilities=query_probabilities,
        )
    if str(query_id) == "category_threshold_point_count":
        return _build_category_threshold_dataset(
            params=params,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            query_probabilities=query_probabilities,
        )
    raise ValueError(f"unsupported scatter points query id: {query_id}")


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    margin_left = _resolve_int(params, "scatter_points_plot_margin_left_px", 112)
    margin_right = _resolve_int(params, "scatter_points_plot_margin_right_px", 292)
    margin_top = _resolve_int(params, "scatter_points_plot_margin_top_px", 80)
    margin_bottom = _resolve_int(params, "scatter_points_plot_margin_bottom_px", 118)
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )
    return _RenderParams(
        canvas_width=_resolve_int(params, "scatter_points_canvas_width", 1280),
        canvas_height=_resolve_int(params, "scatter_points_canvas_height", 820),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=_resolve_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_resolve_int(params, "grid_line_width_px", 1),
        tick_length_px=_resolve_int(params, "tick_length_px", 8),
        point_radius_px=_resolve_int(params, "scatter_points_point_radius_px", 6),
        tick_font_size_px=_resolve_int(params, "scatter_points_tick_font_size_px", 16),
        label_font_size_px=_resolve_int(params, "scatter_points_label_font_size_px", 19),
        legend_font_size_px=_resolve_int(params, "scatter_points_legend_font_size_px", 20),
        title_font_size_px=_resolve_int(params, "scatter_points_title_font_size_px", 26),
        legend_gap_px=_resolve_int(params, "scatter_points_legend_gap_px", 78),
        axis_color_rgb=_resolve_rgb(params, "axis_color_rgb", (34, 43, 58)),
        grid_color_rgb=_resolve_rgb(params, "grid_color_rgb", (209, 216, 226)),
        text_color_rgb=_resolve_rgb(params, "text_color_rgb", (20, 28, 40)),
        muted_text_rgb=_resolve_rgb(params, "muted_text_rgb", (82, 93, 110)),
        text_stroke_rgb=_resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        plot_fill_rgb=_resolve_rgb(params, "plot_fill_rgb", (250, 251, 253)),
        panel_fill_rgb=_resolve_rgb(params, "panel_fill_rgb", (246, 248, 252)),
        panel_border_rgb=_resolve_rgb(params, "panel_border_rgb", (160, 170, 184)),
        threshold_line_rgb=_resolve_rgb(params, "scatter_points_threshold_line_rgb", (31, 91, 170)),
        threshold_label_rgb=_resolve_rgb(params, "scatter_points_threshold_label_rgb", (20, 60, 126)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _data_to_pixel(x_value: float, y_value: float, plot_bbox: BBox) -> Tuple[float, float]:
    x0, y0, x1, y1 = [float(value) for value in plot_bbox]
    px = x0 + (float(x_value) / 100.0) * (x1 - x0)
    py = y1 - (float(y_value) / 100.0) * (y1 - y0)
    return (float(px), float(py))


def _text_bbox(draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, font, *, anchor: str | None = None, stroke_width: int = 0) -> List[float]:
    bbox = draw.textbbox(tuple(float(value) for value in xy), str(text), font=font, anchor=anchor, stroke_width=max(0, int(stroke_width)))
    return _bbox(bbox)


def _draw_dashed_line(draw: ImageDraw.ImageDraw, start: Tuple[float, float], end: Tuple[float, float], *, fill: RGB, width: int, dash_px: int = 10, gap_px: int = 7) -> None:
    x0, y0 = start
    x1, y1 = end
    length = math.hypot(x1 - x0, y1 - y0)
    if length <= 0:
        return
    dx = (x1 - x0) / length
    dy = (y1 - y0) / length
    position = 0.0
    while position < length:
        segment_end = min(length, position + float(dash_px))
        draw.line(
            (
                x0 + dx * position,
                y0 + dy * position,
                x0 + dx * segment_end,
                y0 + dy * segment_end,
            ),
            fill=fill,
            width=max(1, int(width)),
        )
        position += float(dash_px + gap_px)


def _draw_marker(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius: float,
    shape: str,
    fill: RGB,
    outline: RGB,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    r = float(radius)
    bbox = (cx - r, cy - r, cx + r, cy + r)
    shape_text = str(shape)
    if shape_text == "square":
        draw.rectangle(bbox, fill=fill, outline=outline, width=2)
    elif shape_text == "diamond":
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill, outline=outline)
    elif shape_text == "triangle":
        draw.polygon([(cx, cy - r), (cx + r * 0.9, cy + r * 0.8), (cx - r * 0.9, cy + r * 0.8)], fill=fill, outline=outline)
    elif shape_text == "ring":
        draw.ellipse(bbox, fill=(255, 255, 255), outline=outline, width=2)
        inner = (cx - r * 0.58, cy - r * 0.58, cx + r * 0.58, cy + r * 0.58)
        draw.ellipse(inner, fill=fill, outline=fill)
    elif shape_text == "pentagon":
        points = [
            (
                cx + math.cos((-90.0 + 72.0 * index) * math.pi / 180.0) * r,
                cy + math.sin((-90.0 + 72.0 * index) * math.pi / 180.0) * r,
            )
            for index in range(5)
        ]
        draw.polygon(points, fill=fill, outline=outline)
    else:
        draw.ellipse(bbox, fill=fill, outline=outline, width=2)
    return _bbox(bbox)


def _draw_rotated_y_label(image: Image.Image, *, text: str, font, fill: RGB, position: Tuple[float, float]) -> List[float]:
    text_bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), str(text), font=font)
    width = max(1, int(text_bbox[2] - text_bbox[0] + 10))
    height = max(1, int(text_bbox[3] - text_bbox[1] + 10))
    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.text((5 - text_bbox[0], 5 - text_bbox[1]), str(text), font=font, fill=tuple(fill) + (255,))
    rotated = overlay.rotate(90, expand=True)
    x = int(round(float(position[0]) - rotated.size[0] / 2.0))
    y = int(round(float(position[1]) - rotated.size[1] / 2.0))
    image.paste(rotated, (x, y), rotated)
    return _bbox((x, y, x + rotated.size[0], y + rotated.size[1]))


def _title_options(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("scatter_points_title_options", _RENDER_DEFAULTS.get("scatter_points_title_options", ()))
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        titles = tuple(str(value) for value in raw if str(value).strip())
        if titles:
            return titles
    return ("Point Distribution", "Scatter Measurements", "Sample Point Map", "Observed Points")


def _render_scatter_points(image: Image.Image, *, dataset: _Dataset, render_params: _RenderParams, instance_seed: int, params: Mapping[str, Any]) -> _Rendered:
    draw = ImageDraw.Draw(image)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    panel_margin = 34
    panel_bbox = (panel_margin, panel_margin, width - panel_margin, height - panel_margin)
    plot_bbox = (
        float(render_params.plot_margin_left_px),
        float(render_params.plot_margin_top_px),
        float(width - render_params.plot_margin_right_px),
        float(height - render_params.plot_margin_bottom_px),
    )
    draw.rounded_rectangle(panel_bbox, radius=18, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=2)
    draw.rectangle(plot_bbox, fill=render_params.plot_fill_rgb, outline=render_params.panel_border_rgb, width=1)

    title_font = load_font(render_params.title_font_size_px, bold=True)
    label_font = load_font(render_params.label_font_size_px, bold=True)
    tick_font = load_font(render_params.tick_font_size_px, bold=False)
    legend_font = load_font(render_params.legend_font_size_px, bold=True)
    threshold_font = load_font(max(13, render_params.tick_font_size_px - 1), bold=True)
    title_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.title")
    title_text = str(title_rng.choice(_title_options(params)))
    title_x = float(plot_bbox[0])
    title_y = 34.0
    draw_text_traced(
        draw,
        (title_x, title_y),
        title_text,
        font=title_font,
        fill=render_params.text_color_rgb,
        role="readout",
        required=False,
    )
    title_bbox = _text_bbox(draw, (title_x, title_y), title_text, title_font)

    x0, y0, x1, y1 = plot_bbox
    tick_values = [0, 20, 40, 60, 80, 100]
    for tick in tick_values:
        px = x0 + (float(tick) / 100.0) * (x1 - x0)
        py = y1 - (float(tick) / 100.0) * (y1 - y0)
        if tick not in (0, 100):
            draw.line((px, y0, px, y1), fill=render_params.grid_color_rgb, width=render_params.grid_line_width_px)
            draw.line((x0, py, x1, py), fill=render_params.grid_color_rgb, width=render_params.grid_line_width_px)
        draw.line((px, y1, px, y1 + render_params.tick_length_px), fill=render_params.axis_color_rgb, width=render_params.axis_line_width_px)
        draw.line((x0 - render_params.tick_length_px, py, x0, py), fill=render_params.axis_color_rgb, width=render_params.axis_line_width_px)
        draw_text_traced(
            draw,
            (px, y1 + render_params.tick_length_px + 4),
            str(tick),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            anchor="mt",
            role="readout",
            required=False,
        )
        draw_text_traced(
            draw,
            (x0 - render_params.tick_length_px - 8, py),
            str(tick),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            anchor="rm",
            role="readout",
            required=False,
        )

    draw.line((x0, y1, x1, y1), fill=render_params.axis_color_rgb, width=render_params.axis_line_width_px + 1)
    draw.line((x0, y0, x0, y1), fill=render_params.axis_color_rgb, width=render_params.axis_line_width_px + 1)

    x_axis_label = str(params.get("scatter_points_x_axis_label", group_default(_RENDER_DEFAULTS, "scatter_points_x_axis_label", "X value")))
    y_axis_label = str(params.get("scatter_points_y_axis_label", group_default(_RENDER_DEFAULTS, "scatter_points_y_axis_label", "Y value")))
    x_label_xy = ((x0 + x1) / 2.0, height - 47.0)
    draw_text_traced(
        draw,
        x_label_xy,
        x_axis_label,
        font=label_font,
        fill=render_params.text_color_rgb,
        anchor="mm",
        role="readout",
        required=False,
    )
    x_axis_label_bbox = _text_bbox(draw, x_label_xy, x_axis_label, label_font, anchor="mm")
    y_axis_label_bbox = _draw_rotated_y_label(
        image,
        text=y_axis_label,
        font=label_font,
        fill=render_params.text_color_rgb,
        position=(45.0, (y0 + y1) / 2.0),
    )

    threshold_guide_bbox: List[float] = []
    threshold_axis = dataset.query.trace.get("threshold_axis")
    threshold_value = dataset.query.trace.get("threshold_value")
    if threshold_axis in {"x", "y"} and threshold_value is not None:
        value = float(threshold_value)
        if str(threshold_axis) == "x":
            px = x0 + (value / 100.0) * (x1 - x0)
            _draw_dashed_line(
                draw,
                (px, y0),
                (px, y1),
                fill=render_params.threshold_line_rgb,
                width=2,
            )
            label_xy = (px + 8.0, y0 + 12.0)
            text = f"x = {int(value)}"
            draw_text_traced(draw, label_xy, text, font=threshold_font, fill=render_params.threshold_label_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=2, role="readout", required=False)
            label_box = _text_bbox(draw, label_xy, text, threshold_font, stroke_width=2)
            threshold_guide_bbox = _bbox_union([(px - 3, y0, px + 3, y1), label_box])
        else:
            py = y1 - (value / 100.0) * (y1 - y0)
            _draw_dashed_line(
                draw,
                (x0, py),
                (x1, py),
                fill=render_params.threshold_line_rgb,
                width=2,
            )
            label_xy = (x1 - 70.0, py - 24.0)
            text = f"y = {int(value)}"
            draw_text_traced(draw, label_xy, text, font=threshold_font, fill=render_params.threshold_label_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=2, role="readout", required=False)
            label_box = _text_bbox(draw, label_xy, text, threshold_font, stroke_width=2)
            threshold_guide_bbox = _bbox_union([(x0, py - 3, x1, py + 3), label_box])

    entities: List[Dict[str, Any]] = [
        {"entity_id": "plot_area", "entity_type": "plot_area", "bbox_xyxy": _bbox(plot_bbox), "attrs": {}},
    ]
    point_bboxes: Dict[str, List[float]] = {}
    point_centers: Dict[str, List[float]] = {}
    outline_rgb = (255, 255, 255)
    for point in dataset.points:
        center = _data_to_pixel(float(point.x_value), float(point.y_value), plot_bbox)
        bbox = _draw_marker(
            draw,
            center=center,
            radius=float(render_params.point_radius_px),
            shape=str(point.marker_shape),
            fill=point.color_rgb,
            outline=outline_rgb,
        )
        point_bboxes[str(point.point_id)] = list(bbox)
        point_centers[str(point.point_id)] = [round(float(center[0]), 3), round(float(center[1]), 3)]
        entities.append(
            {
                "entity_id": str(point.point_id),
                "entity_type": "scatter_point",
                "bbox_xyxy": list(bbox),
                "attrs": {
                    "x_value": round(float(point.x_value), 3),
                    "y_value": round(float(point.y_value), 3),
                    "category_label": str(point.category_label),
                    "marker_shape": str(point.marker_shape),
                },
            }
        )

    legend_bboxes: Dict[str, List[float]] = {}
    if dataset.categories:
        legend_x = x1 + float(render_params.legend_gap_px)
        legend_y = y0 + 28.0
        row_gap = max(32.0, float(render_params.legend_font_size_px + 16))
        draw_text_traced(draw, (legend_x, legend_y - 34.0), "Legend", font=legend_font, fill=render_params.text_color_rgb, role="readout", required=False)
        for category_index, category in enumerate(dataset.categories):
            cy = legend_y + float(category_index) * row_gap
            marker_box = _draw_marker(
                draw,
                center=(legend_x + 12.0, cy + 8.0),
                radius=max(6.0, float(render_params.point_radius_px)),
                shape=str(category.marker_shape),
                fill=category.color_rgb,
                outline=outline_rgb,
            )
            text_xy = (legend_x + 34.0, cy)
            draw_text_traced(
                draw,
                text_xy,
                str(category.label),
                font=legend_font,
                fill=render_params.text_color_rgb,
                role="readout",
                required=False,
            )
            text_box = _text_bbox(draw, text_xy, str(category.label), legend_font)
            row_box = _bbox_union([marker_box, text_box])
            legend_bboxes[str(category.label)] = list(row_box)
            entities.append(
                {
                    "entity_id": f"legend_{category.label}",
                    "entity_type": "legend_entry",
                    "bbox_xyxy": list(row_box),
                    "attrs": {"category_label": str(category.label)},
                }
            )

    return _Rendered(
        image=image,
        entities=tuple(dict(entity) for entity in entities),
        plot_bbox_px=_bbox(plot_bbox),
        panel_bbox_px=_bbox(panel_bbox),
        point_bboxes=dict(point_bboxes),
        point_centers=dict(point_centers),
        legend_bboxes=dict(legend_bboxes),
        threshold_guide_bbox_px=list(threshold_guide_bbox),
        title_bbox_px=list(title_bbox),
        x_axis_label_bbox_px=list(x_axis_label_bbox),
        y_axis_label_bbox_px=list(y_axis_label_bbox),
        title_text=str(title_text),
    )


def _axis_phrase(axis: str) -> str:
    return "x" if str(axis) == "x" else "y"


def _direction_phrase(direction: str) -> str:
    return "greater than" if str(direction) == "above" else "less than"


def _extremum_phrase(extremum: str) -> str:
    return "largest" if str(extremum) == "largest" else "smallest"


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    trace = dict(dataset.query.trace)
    if str(dataset.query.query_id) == "category_axis_mean_extremum_label":
        answer_hint = str(prompt_defaults["answer_hint_category_label"])
        json_example = str(prompt_defaults["json_example_category_label"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_category_label"])
        object_description = str(prompt_defaults["object_description_scatter_points_categories"])
    else:
        answer_hint = str(prompt_defaults["answer_hint_count"])
        json_example = str(prompt_defaults["json_example_count"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_count"])
        object_description = (
            str(prompt_defaults["object_description_scatter_points_categories"])
            if str(dataset.query.query_id) == "category_threshold_point_count"
            else str(prompt_defaults["object_description_scatter_points_plain"])
        )
    return {
        "object_description": str(object_description),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_defaults["annotation_hint_point_set"]),
        "answer_hint": str(answer_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "axis_phrase": _axis_phrase(str(trace.get("threshold_axis", trace.get("mean_axis", "x")))),
        "threshold_direction_phrase": _direction_phrase(str(trace.get("threshold_direction", "above"))),
        "threshold_value": str(trace.get("threshold_value", "")),
        "mean_extremum_phrase": _extremum_phrase(str(trace.get("mean_extremum", "largest"))),
        "target_category_label": str(trace.get("target_category_label", "")),
    }


def _point_records(points: Sequence[_Point]) -> List[Dict[str, Any]]:
    return [
        {
            "point_id": str(point.point_id),
            "x_value": round(float(point.x_value), 3),
            "y_value": round(float(point.y_value), 3),
            "category_label": str(point.category_label),
            "marker_shape": str(point.marker_shape),
            "color_rgb": [int(channel) for channel in point.color_rgb],
        }
        for point in points
    ]


def _category_records(categories: Sequence[_Category]) -> List[Dict[str, Any]]:
    return [
        {
            "label": str(category.label),
            "color_rgb": [int(channel) for channel in category.color_rgb],
            "marker_shape": str(category.marker_shape),
            "point_ids": [str(point_id) for point_id in category.point_ids],
        }
        for category in categories
    ]


class ChartsScatterPointsQueryTask:
    """Answer threshold-count and category-summary questions over scatter points."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "scatter"
    default_dataset_enabled = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset = _build_dataset(
            params=params,
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
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=TASK_ID,
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_scatter_points(
                background,
                dataset=dataset,
                render_params=render_params,
                instance_seed=int(instance_seed),
                params=params,
            )
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
                "answer_hint_count",
                "answer_hint_category_label",
                "annotation_hint_point_set",
                "json_example_count",
                "json_example_category_label",
                "json_example_answer_only_count",
                "json_example_answer_only_category_label",
                "object_description_scatter_points_plain",
                "object_description_scatter_points_categories",
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

        annotation_point_ids = [str(point_id) for point_id in dataset.query.annotation_point_ids]
        point_set = [list(rendered.point_centers[str(point_id)]) for point_id in annotation_point_ids]
        answer_value: int | str = (
            int(dataset.query.answer)
            if str(dataset.query.answer_type) == "integer"
            else str(dataset.query.answer)
        )
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        annotation_gt = TypedValue(type="point_set", value=list(point_set))
        total_points = len(dataset.points)
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(total_points), [28, 72]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_QUERY[str(query_id)])),
                "scene_variant_load": clamp_unit_interval(float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)])),
            },
        )

        point_records = _point_records(dataset.points)
        category_records = _category_records(dataset.categories)
        projected_annotation = {
            "type": "point_set",
            "point_set": list(point_set),
            "pixel_point_set": list(point_set),
            "point_ids": list(annotation_point_ids),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_scatter_points",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": answer_value,
                    "annotation_point_ids": list(annotation_point_ids),
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
                    "scene_variant_probabilities": {str(dataset.scene_variant): 1.0},
                    "point_count": int(total_points),
                    "category_count": len(dataset.categories),
                    **dict(dataset.query.trace),
                },
            },
            "render_spec": {
                "scene_variant": str(dataset.scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "point_radius_px": int(render_params.point_radius_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_asset_version": font_asset_version(),
                "chart_font_family": str(chart_font_family),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "point_bboxes_px": dict(rendered.point_bboxes),
                "point_centers_px": dict(rendered.point_centers),
                "legend_bboxes_px": dict(rendered.legend_bboxes),
                "threshold_guide_bbox_px": list(rendered.threshold_guide_bbox_px),
                "title_bbox_px": list(rendered.title_bbox_px),
                "x_axis_label_bbox_px": list(rendered.x_axis_label_bbox_px),
                "y_axis_label_bbox_px": list(rendered.y_axis_label_bbox_px),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "scatter_points_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "points": list(point_records),
                "categories": list(category_records),
                "point_count": int(total_points),
                "category_count": len(dataset.categories),
                "annotation_point_ids": list(annotation_point_ids),
                "title_text": str(rendered.title_text),
                "query_id_probabilities": dict(query_probabilities),
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "scatter_points_witness",
                "point_ids": list(annotation_point_ids),
                "answer": answer_value,
                **dict(dataset.query.trace),
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
class ChartsScatterPointsAxisThresholdPointCountTask(FixedChartQueryVariantTaskMixin, ChartsScatterPointsQueryTask):
    """Count scatter points on one side of a visible axis threshold."""

    task_id = "task_charts__scatter_points__axis_threshold_point_count"
    fixed_query_id = "axis_threshold_point_count"


@register_task
class ChartsScatterPointsCategoryAxisMeanExtremumLabelTask(FixedChartQueryVariantTaskMixin, ChartsScatterPointsQueryTask):
    """Return the category with an extremal mean coordinate."""

    task_id = "task_charts__scatter_points__category_axis_mean_extremum_label"
    fixed_query_id = "category_axis_mean_extremum_label"


@register_task
class ChartsScatterPointsCategoryThresholdPointCountTask(FixedChartQueryVariantTaskMixin, ChartsScatterPointsQueryTask):
    """Count threshold-satisfying points inside a named scatter category."""

    task_id = "task_charts__scatter_points__category_threshold_point_count"
    fixed_query_id = "category_threshold_point_count"


__all__ = [
    "ChartsScatterPointsAxisThresholdPointCountTask",
    "ChartsScatterPointsCategoryAxisMeanExtremumLabelTask",
    "ChartsScatterPointsCategoryThresholdPointCountTask",
    "ChartsScatterPointsQueryTask",
    "SUPPORTED_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
]
