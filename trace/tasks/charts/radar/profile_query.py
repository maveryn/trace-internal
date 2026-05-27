"""Radar chart profile query task."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

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
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_radar_query_base"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "highlighted_metric_threshold_panel_count",
    "threshold_metric_count_for_panel",
    "profile_advantage_count",
    "matching_condition_panel_count",
)
SMALL_MULTIPLE_VARIANTS = frozenset(
    {
        "highlighted_metric_threshold_panel_count",
        "threshold_metric_count_for_panel",
        "matching_condition_panel_count",
    }
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "small_multiple_radar",
    "single_radar_multi_profile",
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "radar")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="radar")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="radar", apply_prob=0.0)

_METRIC_LABEL_POOL: Tuple[str, ...] = (
    "Speed",
    "Quality",
    "Reach",
    "Safety",
    "Cost",
    "Yield",
    "Growth",
    "Reliability",
    "Access",
    "Coverage",
    "Stability",
    "Capacity",
)
_AXIS_METRIC_LABEL_POOL: Tuple[str, ...] = ("M1", "M2", "M3", "M4", "M5", "M6", "M7")
_PANEL_LABELS: Tuple[str, ...] = tuple("ABCDEFGH")
_PROFILE_LABELS: Tuple[str, str] = ("Profile A", "Profile B")
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "highlighted_metric_threshold_panel_count": 0.56,
    "threshold_metric_count_for_panel": 0.58,
    "profile_advantage_count": 0.70,
    "matching_condition_panel_count": 0.82,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "small_multiple_radar": 0.72,
    "single_radar_multi_profile": 0.58,
}

BBox = Tuple[float, float, float, float]
RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class _Profile:
    profile_label: str
    values: Dict[str, int]
    color_rgb: RGB


@dataclass(frozen=True)
class _Panel:
    panel_label: str
    profiles: Tuple[_Profile, ...]


@dataclass(frozen=True)
class _Query:
    query_id: str
    scene_variant: str
    answer: str | int
    answer_type: str
    metric_label: str
    panel_label: str
    profile_a_label: str
    profile_b_label: str
    threshold_value: int
    minimum_metric_count: int
    evidence_point_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    metrics: Tuple[str, ...]
    panels: Tuple[_Panel, ...]
    query: _Query


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    point_bboxes: Dict[str, List[float]]
    panel_bboxes: Dict[str, List[float]]
    panel_title_bboxes: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]
    plot_bbox_px: List[float]
    render_meta: Dict[str, Any]


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


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _resolve_gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


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


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("profile_palette_rgb", _RENDER_DEFAULTS.get("profile_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 3:
                colors.append(tuple(max(0, min(255, int(channel))) for channel in item[:3]))  # type: ignore[index]
    if colors:
        return tuple(colors)
    return (
        (41, 108, 179),
        (205, 82, 74),
        (55, 148, 104),
        (139, 92, 186),
        (214, 139, 44),
        (54, 148, 168),
    )


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    *,
    stroke_width: int = 0,
) -> List[float]:
    try:
        box = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return _bbox(box)
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return _bbox([float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)])


def _center_text(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: RGB,
    stroke_fill: RGB = (255, 255, 255),
    stroke_width: int = 0,
) -> List[float]:
    try:
        box = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        width = float(box[2] - box[0])
        height = float(box[3] - box[1])
        x = float(center[0]) - (0.5 * width) - float(box[0])
        y = float(center[1]) - (0.5 * height) - float(box[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        x = float(center[0]) - (0.5 * float(width))
        y = float(center[1]) - (0.5 * float(height))
    draw.text(
        (float(x), float(y)),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
    )
    return _text_bbox(draw, (float(x), float(y)), str(text), font, stroke_width=max(0, int(stroke_width)))


def _choice_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))


def _uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> bool:
    if params.get("query_id") is not None or params.get("query_id_weights") is not None:
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_sampling_params(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    ):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return support_params


def _without_sample_cursor(params: Mapping[str, Any]) -> Dict[str, Any]:
    derived_params = dict(params)
    derived_params.pop("_sample_cursor", None)
    return derived_params


def _balanced_choice(values: Sequence[int], params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    support = [int(value) for value in values]
    if not support:
        raise ValueError(f"empty support for {namespace}")
    index = _choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(support[int(index) % len(support)])


def _rng_choice(values: Sequence[int], rng: Any) -> int:
    support = [int(value) for value in values]
    if not support:
        raise ValueError("empty integer support")
    return int(support[int(rng.randint(0, len(support) - 1))])


def _metric_count(params: Mapping[str, Any], *, min_required: int = 1, instance_seed: int) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="metric_count_min",
        max_key="metric_count_max",
        fallback_min=5,
        fallback_max=7,
        context=f"generation defaults for {TASK_ID}",
    )
    low = max(int(low), int(min_required))
    if int(low) > int(high):
        raise ValueError("metric_count support is too small for requested query")
    return _balanced_choice(
        list(range(int(low), int(high) + 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.metric_count:{int(min_required)}",
    )


def _axis_metric_count(params: Mapping[str, Any], *, min_required: int = 1, instance_seed: int) -> int:
    low = _resolve_gen_int(params, "axis_metric_count_min", _resolve_gen_int(params, "metric_count_min", 5))
    high = _resolve_gen_int(params, "axis_metric_count_max", _resolve_gen_int(params, "metric_count_max", 7))
    low = max(int(low), int(min_required))
    high = min(len(_AXIS_METRIC_LABEL_POOL), int(high))
    if int(low) > int(high):
        raise ValueError("axis metric count support is too small for requested query")
    return _balanced_choice(
        list(range(int(low), int(high) + 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.axis_metric_count:{int(min_required)}",
    )


def _panel_count(params: Mapping[str, Any], *, min_required: int = 1, instance_seed: int) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="panel_count_min",
        max_key="panel_count_max",
        fallback_min=5,
        fallback_max=8,
        context=f"generation defaults for {TASK_ID}",
    )
    low = max(int(low), int(min_required))
    if int(low) > int(high):
        raise ValueError("panel_count support is too small for requested query")
    return _balanced_choice(
        list(range(int(low), int(high) + 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.panel_count:{int(min_required)}",
    )


def _axis_panel_count(params: Mapping[str, Any], *, min_required: int = 1, instance_seed: int) -> int:
    low = _resolve_gen_int(params, "axis_panel_count_min", _resolve_gen_int(params, "panel_count_min", 5))
    high = _resolve_gen_int(params, "axis_panel_count_max", _resolve_gen_int(params, "panel_count_max", 8))
    low = max(int(low), int(min_required))
    high = min(len(_PANEL_LABELS), int(high))
    if int(low) > int(high):
        raise ValueError("axis panel count support is too small for requested query")
    return _balanced_choice(
        list(range(int(low), int(high) + 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.axis_panel_count:{int(min_required)}",
    )


def _target_count_support(params: Mapping[str, Any], *, upper: int) -> List[int]:
    low = _resolve_gen_int(params, "target_count_min", 1)
    high = _resolve_gen_int(params, "target_count_max", 6)
    low = max(1, int(low))
    high = min(int(high), int(upper))
    if int(low) > int(high):
        raise ValueError("target count support is empty")
    return [int(value) for value in range(int(low), int(high) + 1)]


def _sample_metrics(count: int, *, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.metric_labels:{int(count)}")
    labels = list(_METRIC_LABEL_POOL)
    rng.shuffle(labels)
    return tuple(str(label) for label in labels[: int(count)])


def _sample_axis_metrics(count: int) -> Tuple[str, ...]:
    return tuple(str(label) for label in _AXIS_METRIC_LABEL_POOL[: int(count)])


def _value_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low = _resolve_gen_int(params, "value_min", 1)
    high = _resolve_gen_int(params, "value_max", 10)
    if int(low) >= int(high):
        raise ValueError("value_min must be lower than value_max")
    return int(low), int(high)


def _threshold(params: Mapping[str, Any], *, instance_seed: int) -> int:
    low = _resolve_gen_int(params, "threshold_min", 4)
    high = _resolve_gen_int(params, "threshold_max", 7)
    if int(low) > int(high):
        raise ValueError("threshold support is empty")
    return _balanced_choice(
        list(range(int(low), int(high) + 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold",
    )


def _make_random_panel_values(
    *,
    metrics: Sequence[str],
    panel_labels: Sequence[str],
    value_min: int,
    value_max: int,
    instance_seed: int,
    namespace: str,
) -> Dict[str, Dict[str, int]]:
    rng = spawn_rng(int(instance_seed), str(namespace))
    return {
        str(panel): {
            str(metric): int(rng.randint(int(value_min), int(value_max)))
            for metric in metrics
        }
        for panel in panel_labels
    }


def _build_highlighted_metric_threshold_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    value_min, value_max = _value_bounds(params)
    non_answer_params = _without_sample_cursor(params)
    panel_count = _axis_panel_count(non_answer_params, min_required=5, instance_seed=int(instance_seed))
    panel_labels = _PANEL_LABELS[: int(panel_count)]
    target_count = _balanced_choice(
        _target_count_support(params, upper=min(6, int(panel_count) - 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.highlighted_metric_threshold_panel_count.target_count",
    )
    threshold = _threshold(non_answer_params, instance_seed=int(instance_seed))
    metric_count = _axis_metric_count(non_answer_params, min_required=5, instance_seed=int(instance_seed))
    metrics = _sample_axis_metrics(int(metric_count))
    metric_index = _choice_index(
        non_answer_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.highlighted_metric",
    ) % len(metrics)
    metric_label = str(metrics[int(metric_index)])
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.highlighted_metric_threshold")
    values = _make_random_panel_values(
        metrics=metrics,
        panel_labels=panel_labels,
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.highlighted_metric_threshold.values",
    )
    matching_panel_labels = list(panel_labels)
    rng.shuffle(matching_panel_labels)
    matching_set = set(str(panel) for panel in matching_panel_labels[: int(target_count)])
    for panel in panel_labels:
        if str(panel) in matching_set:
            values[str(panel)][str(metric_label)] = int(rng.randint(int(threshold) + 1, int(value_max)))
        else:
            values[str(panel)][str(metric_label)] = int(rng.randint(int(value_min), int(threshold)))

    palette = _palette(params)
    layout_panel_labels = list(panel_labels)
    layout_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.highlighted_metric_threshold.panel_layout")
    layout_rng.shuffle(layout_panel_labels)
    panels = tuple(
        _Panel(
            panel_label=str(panel),
            profiles=(
                _Profile(
                    profile_label="Profile",
                    values=dict(values[str(panel)]),
                    color_rgb=tuple(palette[index % len(palette)]),
                ),
            ),
        )
        for index, panel in enumerate(layout_panel_labels)
    )
    evidence_ids = tuple(f"{str(panel)}|Profile|{str(metric_label)}" for panel in panel_labels if str(panel) in matching_set)
    query = _Query(
        query_id="highlighted_metric_threshold_panel_count",
        scene_variant="small_multiple_radar",
        answer=int(target_count),
        answer_type="integer",
        metric_label=str(metric_label),
        panel_label="",
        profile_a_label="",
        profile_b_label="",
        threshold_value=int(threshold),
        minimum_metric_count=0,
        evidence_point_ids=evidence_ids,
        trace={
            "query_metric_label": str(metric_label),
            "threshold_value": int(threshold),
            "matching_panel_labels": [str(panel) for panel in panel_labels if str(panel) in matching_set],
            "panel_layout_labels": [str(panel) for panel in layout_panel_labels],
            "values_by_panel": values,
        },
    )
    return _Dataset(metrics=tuple(metrics), panels=panels, query=query)


def _build_threshold_metric_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    value_min, value_max = _value_bounds(params)
    non_answer_params = _without_sample_cursor(params)
    threshold = _threshold(non_answer_params, instance_seed=int(instance_seed))
    target_count = _balanced_choice(
        _target_count_support(params, upper=min(6, _resolve_gen_int(params, "metric_count_max", 7) - 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold_metric_count_for_panel.target_count",
    )
    metric_count = _metric_count(non_answer_params, min_required=int(target_count) + 1, instance_seed=int(instance_seed))
    panel_count = _panel_count(non_answer_params, min_required=5, instance_seed=int(instance_seed))
    panel_labels = _PANEL_LABELS[: int(panel_count)]
    metrics = _sample_metrics(int(metric_count), instance_seed=int(instance_seed))
    query_panel_index = _choice_index(
        non_answer_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold.panel",
    ) % len(panel_labels)
    query_panel_label = str(panel_labels[int(query_panel_index)])
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.threshold_metric_count")
    values = _make_random_panel_values(
        metrics=metrics,
        panel_labels=panel_labels,
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold_metric_count.values",
    )
    metric_indices = list(range(len(metrics)))
    rng.shuffle(metric_indices)
    high_indices = set(int(index) for index in metric_indices[: int(target_count)])
    for index, metric in enumerate(metrics):
        if int(index) in high_indices:
            values[str(query_panel_label)][str(metric)] = int(rng.randint(int(threshold) + 1, int(value_max)))
        else:
            values[str(query_panel_label)][str(metric)] = int(rng.randint(int(value_min), int(threshold)))

    palette = _palette(params)
    panels = tuple(
        _Panel(
            panel_label=str(panel),
            profiles=(
                _Profile(
                    profile_label="Profile",
                    values=dict(values[str(panel)]),
                    color_rgb=tuple(palette[index % len(palette)]),
                ),
            ),
        )
        for index, panel in enumerate(panel_labels)
    )
    evidence_ids = tuple(
        f"{str(query_panel_label)}|Profile|{str(metric)}"
        for metric in metrics
        if int(values[str(query_panel_label)][str(metric)]) > int(threshold)
    )
    query = _Query(
        query_id="threshold_metric_count_for_panel",
        scene_variant="small_multiple_radar",
        answer=int(target_count),
        answer_type="integer",
        metric_label="",
        panel_label=str(query_panel_label),
        profile_a_label="",
        profile_b_label="",
        threshold_value=int(threshold),
        minimum_metric_count=0,
        evidence_point_ids=evidence_ids,
        trace={
            "query_panel_label": str(query_panel_label),
            "threshold_value": int(threshold),
            "matching_metric_labels": [
                str(metric)
                for metric in metrics
                if int(values[str(query_panel_label)][str(metric)]) > int(threshold)
            ],
            "values_by_panel": values,
        },
    )
    return _Dataset(metrics=tuple(metrics), panels=panels, query=query)


def _build_profile_advantage_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    value_min, value_max = _value_bounds(params)
    non_answer_params = _without_sample_cursor(params)
    target_count = _balanced_choice(
        _target_count_support(params, upper=min(6, _resolve_gen_int(params, "metric_count_max", 7) - 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.profile_advantage_count.target_count",
    )
    metric_count = _metric_count(non_answer_params, min_required=int(target_count) + 1, instance_seed=int(instance_seed))
    metrics = _sample_metrics(int(metric_count), instance_seed=int(instance_seed))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.profile_advantage")
    metric_indices = list(range(len(metrics)))
    rng.shuffle(metric_indices)
    advantage_indices = set(int(index) for index in metric_indices[: int(target_count)])
    values_a: Dict[str, int] = {}
    values_b: Dict[str, int] = {}
    for index, metric in enumerate(metrics):
        if int(index) in advantage_indices:
            high = int(rng.randint(max(int(value_min) + 1, 4), int(value_max)))
            low = int(rng.randint(int(value_min), int(high) - 1))
            values_a[str(metric)] = int(high)
            values_b[str(metric)] = int(low)
        else:
            high = int(rng.randint(max(int(value_min) + 1, 4), int(value_max)))
            low = int(rng.randint(int(value_min), int(high)))
            values_a[str(metric)] = int(low)
            values_b[str(metric)] = int(high)

    palette = _palette(params)
    panel = _Panel(
        panel_label="",
        profiles=(
            _Profile(profile_label=_PROFILE_LABELS[0], values=dict(values_a), color_rgb=tuple(palette[0])),
            _Profile(profile_label=_PROFILE_LABELS[1], values=dict(values_b), color_rgb=tuple(palette[1])),
        ),
    )
    evidence_ids: List[str] = []
    for metric in metrics:
        if int(values_a[str(metric)]) > int(values_b[str(metric)]):
            evidence_ids.append(f"|{_PROFILE_LABELS[0]}|{str(metric)}")
            evidence_ids.append(f"|{_PROFILE_LABELS[1]}|{str(metric)}")
    query = _Query(
        query_id="profile_advantage_count",
        scene_variant="single_radar_multi_profile",
        answer=int(target_count),
        answer_type="integer",
        metric_label="",
        panel_label="",
        profile_a_label=str(_PROFILE_LABELS[0]),
        profile_b_label=str(_PROFILE_LABELS[1]),
        threshold_value=0,
        minimum_metric_count=0,
        evidence_point_ids=tuple(evidence_ids),
        trace={
            "profile_a_label": str(_PROFILE_LABELS[0]),
            "profile_b_label": str(_PROFILE_LABELS[1]),
            "advantage_metric_labels": [
                str(metric)
                for metric in metrics
                if int(values_a[str(metric)]) > int(values_b[str(metric)])
            ],
            "values_by_profile": {
                str(_PROFILE_LABELS[0]): dict(values_a),
                str(_PROFILE_LABELS[1]): dict(values_b),
            },
        },
    )
    return _Dataset(metrics=tuple(metrics), panels=(panel,), query=query)


def _build_matching_condition_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    value_min, value_max = _value_bounds(params)
    non_answer_params = _without_sample_cursor(params)
    threshold = _threshold(non_answer_params, instance_seed=int(instance_seed))
    target_count = _balanced_choice(
        _target_count_support(params, upper=min(6, _resolve_gen_int(params, "panel_count_max", 8) - 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.matching_condition_panel_count.target_count",
    )
    panel_count = _panel_count(non_answer_params, min_required=int(target_count) + 1, instance_seed=int(instance_seed))
    metric_count = _metric_count(non_answer_params, min_required=5, instance_seed=int(instance_seed))
    min_condition_low = _resolve_gen_int(params, "min_condition_metric_count_min", 2)
    min_condition_high = min(_resolve_gen_int(params, "min_condition_metric_count_max", 4), int(metric_count))
    minimum_metric_count = _balanced_choice(
        list(range(int(min_condition_low), int(min_condition_high) + 1)),
        non_answer_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.matching_condition_panel_count.minimum_metric_count",
    )
    panel_labels = _PANEL_LABELS[: int(panel_count)]
    metrics = _sample_metrics(int(metric_count), instance_seed=int(instance_seed))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.matching_condition")
    panel_indices = list(range(len(panel_labels)))
    rng.shuffle(panel_indices)
    matching_panel_indices = set(int(index) for index in panel_indices[: int(target_count)])
    values: Dict[str, Dict[str, int]] = {str(panel): {} for panel in panel_labels}
    matching_labels: List[str] = []
    for panel_index, panel in enumerate(panel_labels):
        metric_indices = list(range(len(metrics)))
        rng.shuffle(metric_indices)
        if int(panel_index) in matching_panel_indices:
            above_count = int(rng.randint(int(minimum_metric_count), int(metric_count)))
            matching_labels.append(str(panel))
        else:
            above_count = int(rng.randint(0, int(minimum_metric_count) - 1))
        above_indices = set(int(index) for index in metric_indices[: int(above_count)])
        for metric_index, metric in enumerate(metrics):
            if int(metric_index) in above_indices:
                values[str(panel)][str(metric)] = int(rng.randint(int(threshold) + 1, int(value_max)))
            else:
                values[str(panel)][str(metric)] = int(rng.randint(int(value_min), int(threshold)))

    palette = _palette(params)
    panels = tuple(
        _Panel(
            panel_label=str(panel),
            profiles=(
                _Profile(
                    profile_label="Profile",
                    values=dict(values[str(panel)]),
                    color_rgb=tuple(palette[index % len(palette)]),
                ),
            ),
        )
        for index, panel in enumerate(panel_labels)
    )
    evidence_ids = tuple(
        f"{str(panel)}|Profile|{str(metric)}"
        for panel in panel_labels
        if str(panel) in set(matching_labels)
        for metric in metrics
        if int(values[str(panel)][str(metric)]) > int(threshold)
    )
    query = _Query(
        query_id="matching_condition_panel_count",
        scene_variant="small_multiple_radar",
        answer=int(target_count),
        answer_type="integer",
        metric_label="",
        panel_label="",
        profile_a_label="",
        profile_b_label="",
        threshold_value=int(threshold),
        minimum_metric_count=int(minimum_metric_count),
        evidence_point_ids=evidence_ids,
        trace={
            "threshold_value": int(threshold),
            "minimum_metric_count": int(minimum_metric_count),
            "matching_panel_labels": list(matching_labels),
            "values_by_panel": values,
        },
    )
    return _Dataset(metrics=tuple(metrics), panels=panels, query=query)


def _build_dataset(query_id: str, params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    if str(query_id) == "highlighted_metric_threshold_panel_count":
        return _build_highlighted_metric_threshold_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "threshold_metric_count_for_panel":
        return _build_threshold_metric_count_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "profile_advantage_count":
        return _build_profile_advantage_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "matching_condition_panel_count":
        return _build_matching_condition_dataset(params, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported query_id: {query_id}")


def _panel_layout(plot_bbox: BBox, panel_count: int, gap: float) -> List[BBox]:
    x1, y1, x2, y2 = (float(value) for value in plot_bbox)
    if int(panel_count) <= 1:
        return [(x1, y1, x2, y2)]
    cols = 2 if int(panel_count) <= 4 else (3 if int(panel_count) <= 6 else 4)
    rows = int(math.ceil(float(panel_count) / float(cols)))
    width = (x2 - x1 - (float(cols - 1) * float(gap))) / float(cols)
    height = (y2 - y1 - (float(rows - 1) * float(gap))) / float(rows)
    boxes: List[BBox] = []
    for index in range(int(panel_count)):
        row = int(index) // int(cols)
        col = int(index) % int(cols)
        px1 = x1 + (float(col) * (width + float(gap)))
        py1 = y1 + (float(row) * (height + float(gap)))
        boxes.append((px1, py1, px1 + width, py1 + height))
    return boxes


def _radar_points(
    *,
    center: Tuple[float, float],
    radius: float,
    metrics: Sequence[str],
    values: Mapping[str, int],
    max_value: int,
) -> Dict[str, Tuple[float, float]]:
    points: Dict[str, Tuple[float, float]] = {}
    for index, metric in enumerate(metrics):
        angle = (-math.pi / 2.0) + ((2.0 * math.pi * float(index)) / float(len(metrics)))
        radial = float(radius) * (float(values[str(metric)]) / float(max(1, int(max_value))))
        points[str(metric)] = (
            float(center[0]) + (float(radial) * math.cos(float(angle))),
            float(center[1]) + (float(radial) * math.sin(float(angle))),
        )
    return points


def _ring_points(*, center: Tuple[float, float], radius: float, metrics: Sequence[str]) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for index in range(len(metrics)):
        angle = (-math.pi / 2.0) + ((2.0 * math.pi * float(index)) / float(len(metrics)))
        points.append(
            (
                float(center[0]) + (float(radius) * math.cos(float(angle))),
                float(center[1]) + (float(radius) * math.sin(float(angle))),
            )
        )
    return points


def _draw_radar_panel(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    metrics: Sequence[str],
    panel: _Panel,
    params: Mapping[str, Any],
    max_value: int,
    show_title: bool,
    single_panel: bool,
    highlight_metric: str = "",
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]], List[float]]:
    x1, y1, x2, y2 = (float(value) for value in bbox)
    text_rgb = _resolve_rgb(params, "text_rgb", (37, 45, 58))
    muted_rgb = _resolve_rgb(params, "muted_text_rgb", (88, 99, 116))
    grid_rgb = _resolve_rgb(params, "grid_rgb", (207, 214, 225))
    spoke_rgb = _resolve_rgb(params, "spoke_rgb", (186, 196, 210))
    query_spoke_rgb = _resolve_rgb(params, "query_spoke_rgb", (70, 91, 118))
    query_metric_label_rgb = _resolve_rgb(params, "query_metric_label_rgb", (26, 54, 93))
    panel_title_font = load_font(_resolve_int(params, "panel_title_font_size_px", 20), bold=True)
    metric_font = load_font(_resolve_int(params, "metric_font_size_px", 15 if not bool(single_panel) else 18), bold=True)
    tick_font = load_font(_resolve_int(params, "tick_font_size_px", 13 if not bool(single_panel) else 15), bold=False)
    point_radius = float(_resolve_int(params, "point_radius_px", 6 if not bool(single_panel) else 8))
    title_bbox = [float(x1), float(y1), float(x1), float(y1)]
    title_height = 0.0
    if bool(show_title) and str(panel.panel_label):
        title_text = f"Panel {str(panel.panel_label)}"
        title_xy = (float(x1) + 14.0, float(y1) + 10.0)
        draw.text(title_xy, title_text, font=panel_title_font, fill=text_rgb)
        title_bbox = _text_bbox(draw, title_xy, title_text, panel_title_font)
        title_height = 34.0

    label_pad = 58.0 if bool(single_panel) else 40.0
    content_top = float(y1) + float(title_height) + 18.0
    content_bottom = float(y2) - 18.0
    center = (0.5 * (float(x1) + float(x2)), 0.5 * (float(content_top) + float(content_bottom)) + 6.0)
    radius = 0.5 * min(float(x2 - x1), float(content_bottom - content_top)) - float(label_pad)
    radius = max(54.0 if not bool(single_panel) else 160.0, float(radius))

    ring_count = max(2, _resolve_int(params, "ring_count", 5))
    for ring_index in range(1, int(ring_count) + 1):
        ring_value = int(round((float(max_value) * float(ring_index)) / float(ring_count)))
        ring_radius = float(radius) * (float(ring_value) / float(max(1, int(max_value))))
        points = _ring_points(center=center, radius=ring_radius, metrics=metrics)
        draw.line([*points, points[0]], fill=grid_rgb, width=_resolve_int(params, "grid_line_width_px", 1))
        if ring_index in {int(ring_count), max(1, int(ring_count) // 2)}:
            _center_text(
                draw,
                center=(float(center[0]), float(center[1]) - float(ring_radius) - 10.0),
                text=str(ring_value),
                font=tick_font,
                fill=muted_rgb,
                stroke_fill=(255, 255, 255),
                stroke_width=1,
            )

    for index, metric in enumerate(metrics):
        is_highlighted_metric = bool(highlight_metric) and str(metric) == str(highlight_metric)
        angle = (-math.pi / 2.0) + ((2.0 * math.pi * float(index)) / float(len(metrics)))
        spoke_end = (
            float(center[0]) + (float(radius) * math.cos(float(angle))),
            float(center[1]) + (float(radius) * math.sin(float(angle))),
        )
        draw.line(
            [center, spoke_end],
            fill=query_spoke_rgb if bool(is_highlighted_metric) else spoke_rgb,
            width=(
                _resolve_int(params, "query_spoke_width_px", 3)
                if bool(is_highlighted_metric)
                else _resolve_int(params, "grid_line_width_px", 1)
            ),
        )
        label_radius = float(radius) + (34.0 if bool(single_panel) else 24.0)
        raw_label_center = (
            float(center[0]) + (float(label_radius) * math.cos(float(angle))),
            float(center[1]) + (float(label_radius) * math.sin(float(angle))),
        )
        label_font = metric_font
        if not bool(single_panel):
            label_font = fit_font_to_box(
                draw,
                text=str(metric),
                max_width=72,
                max_height=22,
                bold=True,
                min_size_px=10,
                max_size_px=_resolve_int(params, "metric_font_size_px", 15),
                fill_ratio=0.95,
            )
        _center_text(
            draw,
            center=raw_label_center,
            text=str(metric),
            font=label_font,
            fill=query_metric_label_rgb if bool(is_highlighted_metric) else text_rgb,
            stroke_fill=(255, 255, 255),
            stroke_width=2 if bool(is_highlighted_metric) else 1,
        )

    point_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    for profile in panel.profiles:
        points_by_metric = _radar_points(
            center=center,
            radius=float(radius),
            metrics=metrics,
            values=profile.values,
            max_value=int(max_value),
        )
        polygon = [points_by_metric[str(metric)] for metric in metrics]
        if len(polygon) >= 2:
            draw.line(
                [*polygon, polygon[0]],
                fill=tuple(int(value) for value in profile.color_rgb),
                width=_resolve_int(params, "profile_line_width_px", 4),
            )
        for metric in metrics:
            cx, cy = points_by_metric[str(metric)]
            marker_bbox = [
                float(cx) - float(point_radius),
                float(cy) - float(point_radius),
                float(cx) + float(point_radius),
                float(cy) + float(point_radius),
            ]
            draw.ellipse(
                marker_bbox,
                fill=tuple(int(value) for value in profile.color_rgb),
                outline=(255, 255, 255),
                width=_resolve_int(params, "point_outline_width_px", 2),
            )
            point_id = f"{str(panel.panel_label)}|{str(profile.profile_label)}|{str(metric)}"
            point_bboxes[str(point_id)] = _bbox(marker_bbox)
            entities.append(
                {
                    "entity_id": str(point_id),
                    "entity_type": "chart_radar_vertex",
                    "bbox_px": _bbox(marker_bbox),
                    "attrs": {
                        "panel_label": str(panel.panel_label),
                        "profile_label": str(profile.profile_label),
                        "metric_label": str(metric),
                        "value": int(profile.values[str(metric)]),
                        "center_px": [round(float(cx), 3), round(float(cy), 3)],
                    },
                }
            )
    return entities, point_bboxes, list(title_bbox)


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    *,
    profiles: Sequence[_Profile],
    params: Mapping[str, Any],
    origin: Tuple[float, float],
) -> Dict[str, List[float]]:
    font = load_font(_resolve_int(params, "legend_font_size_px", 18), bold=True)
    text_rgb = _resolve_rgb(params, "text_rgb", (37, 45, 58))
    legend_bboxes: Dict[str, List[float]] = {}
    x = float(origin[0])
    y = float(origin[1])
    for profile in profiles:
        swatch = [x, y + 5.0, x + 24.0, y + 19.0]
        draw.rounded_rectangle(swatch, radius=4, fill=profile.color_rgb, outline=(255, 255, 255), width=1)
        label_xy = (x + 32.0, y)
        draw.text(label_xy, str(profile.profile_label), font=font, fill=text_rgb)
        text_box = _text_bbox(draw, label_xy, str(profile.profile_label), font)
        legend_bboxes[str(profile.profile_label)] = _bbox([swatch[0], swatch[1], text_box[2], text_box[3]])
        x = float(text_box[2]) + 42.0
    return legend_bboxes


def _render_dataset(dataset: _Dataset, *, params: Mapping[str, Any], instance_seed: int) -> _Rendered:
    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    canvas_width = _resolve_int(params, "canvas_width", 1600)
    canvas_height = _resolve_int(params, "canvas_height", 1000)
    background, background_meta = make_background_canvas(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    outer = _resolve_int(params, "outer_margin_px", 42)
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(outer),
        right_px=int(outer),
        top_px=int(outer),
        bottom_px=int(outer),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    title_band = _resolve_int(params, "title_band_height_px", 86)
    panel_gap = _resolve_int(params, "panel_gap_px", 26)
    panel_padding = _resolve_int(params, "panel_padding_px", 18)
    panel_fill = _resolve_rgb(params, "panel_fill_rgb", (255, 255, 255))
    panel_border = _resolve_rgb(params, "panel_border_rgb", (190, 199, 212))
    text_rgb = _resolve_rgb(params, "text_rgb", (37, 45, 58))
    muted_rgb = _resolve_rgb(params, "muted_text_rgb", (88, 99, 116))
    title_font = load_font(_resolve_int(params, "title_font_size_px", 30), bold=True)
    subtitle_font = load_font(_resolve_int(params, "subtitle_font_size_px", 18), bold=False)

    draw.text((float(margin_left), 22.0 + float(layout_jitter_meta.get("dy_px", 0))), "Radar Profile Charts", font=title_font, fill=text_rgb)
    subtitle = "Compare radial profile vertices against metric spokes and ring values."
    draw.text((float(margin_left), 58.0 + float(layout_jitter_meta.get("dy_px", 0))), subtitle, font=subtitle_font, fill=muted_rgb)

    entities: List[Dict[str, Any]] = []
    point_bboxes: Dict[str, List[float]] = {}
    panel_title_bboxes: Dict[str, List[float]] = {}
    panel_bboxes: Dict[str, List[float]] = {}
    legend_bboxes: Dict[str, List[float]] = {}
    plot_bbox = [
        float(margin_left),
        float(title_band) + float(layout_jitter_meta.get("dy_px", 0)),
        float(canvas_width - margin_right),
        float(canvas_height - margin_bottom),
    ]
    max_value = _resolve_gen_int(params, "value_max", 10)

    if str(dataset.query.scene_variant) == "single_radar_multi_profile":
        legend_bboxes = _draw_legend(
            draw,
            profiles=dataset.panels[0].profiles,
            params=params,
            origin=(float(canvas_width) - 380.0, 34.0),
        )

    panel_boxes = _panel_layout(tuple(plot_bbox), len(dataset.panels), gap=float(panel_gap))
    for panel, panel_bbox in zip(dataset.panels, panel_boxes):
        px1, py1, px2, py2 = (float(value) for value in panel_bbox)
        draw.rounded_rectangle(
            [px1, py1, px2, py2],
            radius=_resolve_int(params, "panel_corner_radius_px", 8),
            fill=panel_fill,
            outline=panel_border,
            width=_resolve_int(params, "panel_border_width_px", 2),
        )
        content_bbox = (
            px1 + float(panel_padding),
            py1 + float(panel_padding),
            px2 - float(panel_padding),
            py2 - float(panel_padding),
        )
        rendered_entities, rendered_points, title_bbox = _draw_radar_panel(
            draw,
            bbox=content_bbox,
            metrics=dataset.metrics,
            panel=panel,
            params=params,
            max_value=int(max_value),
            show_title=str(dataset.query.scene_variant) == "small_multiple_radar",
            single_panel=str(dataset.query.scene_variant) == "single_radar_multi_profile",
            highlight_metric=(
                str(dataset.query.metric_label)
                if str(dataset.query.query_id) == "highlighted_metric_threshold_panel_count"
                else ""
            ),
        )
        panel_bboxes[str(panel.panel_label)] = _bbox(panel_bbox)
        if str(panel.panel_label):
            panel_title_bboxes[str(panel.panel_label)] = list(title_bbox)
        entities.extend(rendered_entities)
        point_bboxes.update(rendered_points)
        entities.append(
            {
                "entity_id": f"radar_panel_{str(panel.panel_label) or 'single'}",
                "entity_type": "chart_radar_panel",
                "bbox_px": _bbox(panel_bbox),
                "attrs": {
                    "panel_label": str(panel.panel_label),
                    "profile_count": int(len(panel.profiles)),
                    "metric_count": int(len(dataset.metrics)),
                },
            }
        )

    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return _Rendered(
        image=image,
        entities=tuple(entities),
        point_bboxes=dict(point_bboxes),
        panel_bboxes=dict(panel_bboxes),
        panel_title_bboxes=dict(panel_title_bboxes),
        legend_bboxes=dict(legend_bboxes),
        plot_bbox_px=_bbox(plot_bbox),
        render_meta={
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "layout_jitter": dict(layout_jitter_meta),
            "panel_bboxes_px": dict(panel_bboxes),
            "metric_labels": list(dataset.metrics),
            "highlight_metric_label": (
                str(dataset.query.metric_label)
                if str(dataset.query.query_id) == "highlighted_metric_threshold_panel_count"
                else ""
            ),
        },
    )


def _evidence_bboxes(dataset: _Dataset, rendered: _Rendered) -> List[List[float]]:
    boxes: List[List[float]] = []
    for point_id in dataset.query.evidence_point_ids:
        bbox = rendered.point_bboxes.get(str(point_id))
        if bbox is not None:
            boxes.append(list(bbox))
    return boxes


class ChartsRadarMultiplotQueryTask:
    """Answer comparison and filtering queries on radar chart displays."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "radar"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(
            params,
            query_id_probabilities=query_id_probabilities,
        )
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_params = {**dict(support_params), "_attempt_index": int(attempt_index)}
                dataset = _build_dataset(str(query_id), attempt_params, instance_seed=int(instance_seed) + int(attempt_index))
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        rendered = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
        evidence_boxes = _evidence_bboxes(dataset, rendered)
        if not evidence_boxes:
            raise RuntimeError(f"{self.task_id} produced empty evidence")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_label",
                "answer_hint_count",
                "object_description_small_multiple_radar",
                "object_description_single_radar_multi_profile",
                "evidence_hint_highlighted_metric_threshold_panel_count",
                "evidence_hint_threshold_metric_count_for_panel",
                "evidence_hint_profile_advantage_count",
                "evidence_hint_matching_condition_panel_count",
                "json_example_highlighted_metric_threshold_panel_count",
                "json_example_threshold_metric_count_for_panel",
                "json_example_profile_advantage_count",
                "json_example_matching_condition_panel_count",
                "json_example_answer_only_highlighted_metric_threshold_panel_count",
                "json_example_answer_only_threshold_metric_count_for_panel",
                "json_example_answer_only_profile_advantage_count",
                "json_example_answer_only_matching_condition_panel_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint_key = "answer_hint_count" if str(dataset.query.answer_type) == "integer" else "answer_hint_label"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(dataset.query.scene_variant)}"]),
                "metric_label": str(dataset.query.metric_label),
                "panel_label": str(dataset.query.panel_label),
                "profile_a_label": str(dataset.query.profile_a_label),
                "profile_b_label": str(dataset.query.profile_b_label),
                "threshold_value": str(dataset.query.threshold_value),
                "minimum_metric_count": str(dataset.query.minimum_metric_count),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(query_id)}"]),
                "answer_hint": str(prompt_defaults[str(answer_hint_key)]),
                "json_example": str(prompt_defaults[f"json_example_{str(query_id)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer)
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_boxes])
        values_by_panel_profile = {
            str(panel.panel_label): {
                str(profile.profile_label): dict(profile.values)
                for profile in panel.profiles
            }
            for panel in dataset.panels
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_radar_{str(dataset.query.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.query.scene_variant),
                    "answer": dataset.query.answer,
                    "evidence_point_ids": list(dataset.query.evidence_point_ids),
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
                    "scene_variant": str(dataset.query.scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "metric_count": int(len(dataset.metrics)),
                    "panel_count": int(len(dataset.panels)),
                    "question_format": "radar_profile_query",
                },
            },
            "render_spec": {
                "canvas_width": _resolve_int(params, "canvas_width", 1600),
                "canvas_height": _resolve_int(params, "canvas_height", 1000),
                "coord_space": "pixel",
                "scene_variant": str(dataset.query.scene_variant),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_bboxes_px": dict(rendered.point_bboxes),
                "panel_bboxes_px": dict(rendered.panel_bboxes),
                "panel_title_bboxes_px": dict(rendered.panel_title_bboxes),
                "legend_bboxes_px": dict(rendered.legend_bboxes),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.query.scene_variant),
                "answer": dataset.query.answer,
                "answer_type": str(dataset.query.answer_type),
                "metrics": list(dataset.metrics),
                "metric_count": int(len(dataset.metrics)),
                "panel_labels": [str(panel.panel_label) for panel in dataset.panels if str(panel.panel_label)],
                "panel_count": int(len(dataset.panels)),
                "values_by_panel_profile": values_by_panel_profile,
                "evidence_point_ids": list(dataset.query.evidence_point_ids),
                "query_id_probabilities": dict(query_id_probabilities),
                "question_format": "radar_profile_query",
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "radar_vertices",
                "point_ids": list(dataset.query.evidence_point_ids),
                "answer": dataset.query.answer,
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_boxes],
                "evidence_point_ids": list(dataset.query.evidence_point_ids),
            },
        }

        visual_max = max(
            int(_resolve_gen_int(params, "panel_count_max", 8)) * int(_resolve_gen_int(params, "metric_count_max", 7)),
            2 * int(_resolve_gen_int(params, "metric_count_max", 7)),
        )
        visual_count = int(len(dataset.panels)) * int(len(dataset.metrics)) * max(
            1,
            max(len(panel.profiles) for panel in dataset.panels),
        )
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(visual_count), [10, int(visual_max)]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_id)])),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.query.scene_variant)]),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsRadarThresholdPanelCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsRadarMultiplotQueryTask,
):
    """Count radar panels satisfying sampled threshold conditions."""

    task_id = "task_charts__radar__threshold_panel_count"
    allowed_query_ids = (
        "highlighted_metric_threshold_panel_count",
        "matching_condition_panel_count",
    )


@register_task
class ChartsRadarThresholdMetricCountForPanelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsRadarMultiplotQueryTask,
):
    """Count metrics in one radar panel satisfying a threshold."""

    task_id = "task_charts__radar__threshold_metric_count_for_panel"
    fixed_query_id = "threshold_metric_count_for_panel"


@register_task
class ChartsRadarProfileAdvantageCountTask(FixedChartQueryVariantTaskMixin, ChartsRadarMultiplotQueryTask):
    """Count metrics where one radar profile exceeds another."""

    task_id = "task_charts__radar__profile_advantage_count"
    fixed_query_id = "profile_advantage_count"


__all__ = [
    "ChartsRadarMultiplotQueryTask",
    "ChartsRadarProfileAdvantageCountTask",
    "ChartsRadarThresholdPanelCountTask",
    "ChartsRadarThresholdMetricCountForPanelTask",
]
