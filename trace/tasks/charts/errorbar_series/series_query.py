"""Scientific error-bar series chart tasks."""

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
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font, temporary_default_font_family
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_axis_labels, resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_background_defaults,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "charts_errorbar_series_base"
SCENE_ID = "errorbar_series"
THRESHOLD_QUERY_IDS: Tuple[str, ...] = (
    "entirely_above_threshold_count",
    "entirely_below_threshold_count",
    "contains_threshold_count",
)
BOUND_EXTREMUM_QUERY_IDS: Tuple[str, ...] = (
    "highest_upper_bound_x_label",
    "lowest_lower_bound_x_label",
)
OVERLAP_QUERY_IDS: Tuple[str, ...] = ("overlap_target_errorbar_at_x_count",)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = THRESHOLD_QUERY_IDS + BOUND_EXTREMUM_QUERY_IDS + OVERLAP_QUERY_IDS
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "marker_errorbar",
    "line_marker_errorbar",
    "grouped_errorbar",
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "errorbar_series")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="errorbar_series")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="errorbar_series", apply_prob=0.0)

_QUERY_REASONING_LOADS: Dict[str, float] = {
    "entirely_above_threshold_count": 0.62,
    "entirely_below_threshold_count": 0.62,
    "contains_threshold_count": 0.66,
    "highest_upper_bound_x_label": 0.58,
    "lowest_lower_bound_x_label": 0.58,
    "overlap_target_errorbar_at_x_count": 0.76,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "marker_errorbar": 0.56,
    "line_marker_errorbar": 0.62,
    "grouped_errorbar": 0.68,
}

RGB = Tuple[int, int, int]
BBox = List[float]
Point = List[float]


@dataclass(frozen=True)
class _ErrorbarSeries:
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
    annotation_kind: str
    annotation_item_keys: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    x_labels: Tuple[str, ...]
    x_label_meta: Dict[str, Any]
    series: Tuple[_ErrorbarSeries, ...]
    series_label_meta: Dict[str, Any]
    scene_variant: str
    scene_variant_probabilities: Dict[str, float]
    query_id: str
    query_id_probabilities: Dict[str, float]
    threshold_value: int | None
    target_series_id: str
    target_x_index: int | None
    title: str
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    margin_left_px: int
    margin_right_px: int
    margin_top_px: int
    margin_bottom_px: int
    title_font_size_px: int
    tick_font_size_px: int
    label_font_size_px: int
    legend_font_size_px: int
    axis_min: int
    axis_max: int
    tick_step: int
    axis_line_width_px: int
    grid_line_width_px: int
    errorbar_line_width_px: int
    center_line_width_px: int
    cap_width_px: int
    point_radius_px: int
    series_offset_px: int
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    axis_rgb: RGB
    grid_rgb: RGB
    panel_fill_rgb: RGB
    panel_outline_rgb: RGB
    threshold_rgb: RGB
    font_family: str
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    errorbar_bboxes_px: Dict[str, BBox]
    point_map_px: Dict[str, Dict[str, Dict[str, Point]]]
    threshold_bbox_px: BBox | None
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _point(x: float, y: float) -> Point:
    return [round(float(x), 3), round(float(y), 3)]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _support_probability_map(values: Sequence[int | str]) -> Dict[str, float]:
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


def _resolve_count(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {TASK_ID}",
    )
    return int(
        _choose_from_values(
            params,
            values=tuple(range(int(low), int(high) + 1)),
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
    )


def _resolve_palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw_palette = params.get("series_palette_rgb", group_default(_RENDER_DEFAULTS, "series_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw_palette, Sequence) and not isinstance(raw_palette, (str, bytes)):
        for item in raw_palette:
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 3:
                colors.append(_as_rgb(item, (0, 0, 0)))
    return tuple(colors) if colors else (
        (47, 111, 196),
        (216, 104, 62),
        (42, 147, 112),
        (126, 93, 190),
    )


def _sample_labels(params: Mapping[str, Any], *, x_count: int, series_count: int, instance_seed: int) -> Tuple[Tuple[str, ...], Dict[str, Any], Tuple[str, ...], Dict[str, Any]]:
    label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.labels")
    x_bucket_weights = params.get("x_label_bucket_weights", group_default(_GEN_DEFAULTS, "x_label_bucket_weights", None))
    x_resolved = resolve_chart_axis_labels(
        label_rng,
        count=int(x_count),
        min_chars=int(params.get("x_label_min_chars", group_default(_GEN_DEFAULTS, "x_label_min_chars", 2))),
        max_chars=int(params.get("x_label_max_chars", group_default(_GEN_DEFAULTS, "x_label_max_chars", 6))),
        bucket_weights=x_bucket_weights if isinstance(x_bucket_weights, Mapping) else None,
    )
    series_resolved = resolve_chart_entity_labels(
        label_rng,
        count=int(series_count),
        min_chars=2,
        max_chars=8,
        allow_spaces=False,
    )
    return (
        tuple(str(label) for label in x_resolved.labels),
        {
            "label_source_kind": str(x_resolved.label_source_kind),
            "label_bucket": str(x_resolved.label_bucket),
            "label_manifest": str(x_resolved.label_manifest),
            "label_filter": dict(x_resolved.label_filter),
            "label_bucket_probabilities": dict(x_resolved.label_bucket_probabilities),
        },
        tuple(str(label) for label in series_resolved.labels),
        {
            "label_source_kind": str(series_resolved.label_source_kind),
            "label_bucket": str(series_resolved.label_bucket),
            "label_manifest": str(series_resolved.label_manifest),
            "label_filter": dict(series_resolved.label_filter),
            "label_bucket_probabilities": dict(series_resolved.label_bucket_probabilities),
        },
    )


def _random_interval(rng: Any, *, low_min: int = 10, high_max: int = 90) -> Tuple[int, int, int]:
    mid = int(rng.randint(int(low_min) + 10, int(high_max) - 10))
    err_low = int(rng.randint(5, 13))
    err_high = int(rng.randint(5, 13))
    lower = max(0, int(mid) - int(err_low))
    upper = min(100, int(mid) + int(err_high))
    return int(lower), int(mid), int(upper)


def _make_series(
    *,
    series_id: str,
    label: str,
    color_rgb: RGB,
    triples: Sequence[Tuple[int, int, int]],
) -> _ErrorbarSeries:
    return _ErrorbarSeries(
        series_id=str(series_id),
        label=str(label),
        color_rgb=tuple(int(value) for value in color_rgb),
        lower_values=tuple(int(triple[0]) for triple in triples),
        mid_values=tuple(int(triple[1]) for triple in triples),
        upper_values=tuple(int(triple[2]) for triple in triples),
    )


def _random_series_triples(rng: Any, *, x_count: int) -> List[Tuple[int, int, int]]:
    return [_random_interval(rng) for _ in range(int(x_count))]


def _series_count(params: Mapping[str, Any], *, query_id: str, instance_seed: int) -> int:
    if str(query_id) == "overlap_target_errorbar_at_x_count":
        return _resolve_count(
            params,
            min_key="overlap_series_count_min",
            max_key="overlap_series_count_max",
            fallback_min=3,
            fallback_max=4,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.overlap_series_count",
        )
    return _resolve_count(
        params,
        min_key="series_count_min",
        max_key="series_count_max",
        fallback_min=2,
        fallback_max=4,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.series_count",
    )


def _build_threshold_dataset(params: Mapping[str, Any], *, query_id: str, instance_seed: int) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.threshold")
    scene_variant, scene_probs = _resolve_scene_variant(params, instance_seed=int(instance_seed))
    x_count = _resolve_count(
        params,
        min_key="x_count_min",
        max_key="x_count_max",
        fallback_min=5,
        fallback_max=8,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.x_count",
    )
    series_count = _series_count(params, query_id=str(query_id), instance_seed=int(instance_seed))
    x_labels, x_meta, series_labels, series_meta = _sample_labels(
        params,
        x_count=int(x_count),
        series_count=int(series_count),
        instance_seed=int(instance_seed),
    )
    threshold_low, threshold_high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="threshold_value_min",
        max_key="threshold_value_max",
        fallback_min=38,
        fallback_max=62,
        context=f"generation defaults for {TASK_ID}",
    )
    threshold = int(
        _choose_from_values(
            params,
            values=tuple(range(int(threshold_low), int(threshold_high) + 1)),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold_value",
        )
    )
    answer_min, answer_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="threshold_answer_count_min",
        max_key="threshold_answer_count_max",
        fallback_min=1,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    max_answer = min(int(answer_max), int(x_count))
    answer_count = int(
        _choose_from_values(
            params,
            values=tuple(range(int(answer_min), int(max_answer) + 1)),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold_answer_count",
        )
    )
    target_series_index = int(
        _choose_from_values(
            params,
            values=tuple(range(int(series_count))),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold.target_series",
        )
    )
    answer_indices = set(rng.sample(list(range(int(x_count))), k=int(answer_count)))
    palette = _resolve_palette(params)
    series: List[_ErrorbarSeries] = []
    for series_index in range(int(series_count)):
        triples = _random_series_triples(rng, x_count=int(x_count))
        if int(series_index) == int(target_series_index):
            adjusted: List[Tuple[int, int, int]] = []
            for x_index in range(int(x_count)):
                selected = int(x_index) in answer_indices
                if str(query_id) == "entirely_above_threshold_count":
                    if selected:
                        lower = min(92, int(threshold) + int(rng.randint(6, 18)))
                        upper = min(100, lower + int(rng.randint(6, 16)))
                    else:
                        if rng.random() < 0.55:
                            lower = max(0, int(threshold) - int(rng.randint(8, 18)))
                            upper = int(threshold) + int(rng.randint(2, 10))
                        else:
                            upper = max(2, int(threshold) - int(rng.randint(2, 13)))
                            lower = max(0, upper - int(rng.randint(6, 16)))
                    mid = int(round((lower + upper) / 2))
                elif str(query_id) == "entirely_below_threshold_count":
                    if selected:
                        upper = max(8, int(threshold) - int(rng.randint(6, 18)))
                        lower = max(0, upper - int(rng.randint(6, 16)))
                    else:
                        if rng.random() < 0.55:
                            lower = max(0, int(threshold) - int(rng.randint(8, 18)))
                            upper = int(threshold) + int(rng.randint(2, 10))
                        else:
                            lower = min(92, int(threshold) + int(rng.randint(2, 13)))
                            upper = min(100, lower + int(rng.randint(6, 16)))
                    mid = int(round((lower + upper) / 2))
                else:
                    if selected:
                        lower = max(0, int(threshold) - int(rng.randint(6, 18)))
                        upper = min(100, int(threshold) + int(rng.randint(6, 18)))
                    else:
                        if rng.random() < 0.5:
                            upper = max(3, int(threshold) - int(rng.randint(3, 16)))
                            lower = max(0, upper - int(rng.randint(6, 16)))
                        else:
                            lower = min(94, int(threshold) + int(rng.randint(3, 16)))
                            upper = min(100, lower + int(rng.randint(6, 16)))
                    mid = int(round((lower + upper) / 2))
                adjusted.append((int(lower), int(mid), int(upper)))
            triples = adjusted
        series.append(
            _make_series(
                series_id=f"series_{series_index}",
                label=str(series_labels[int(series_index)]),
                color_rgb=palette[int(series_index) % len(palette)],
                triples=triples,
            )
        )
    target = series[int(target_series_index)]
    target_label = str(target.label)
    annotation_keys = tuple(f"{target_label}:{x_labels[index]}" for index in sorted(answer_indices))
    return _Dataset(
        x_labels=tuple(x_labels),
        x_label_meta=dict(x_meta),
        series=tuple(series),
        series_label_meta=dict(series_meta),
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_probs),
        query_id=str(query_id),
        query_id_probabilities={str(query_id): 1.0},
        threshold_value=int(threshold),
        target_series_id=str(target.series_id),
        target_x_index=None,
        title=str(_choose_title(params, instance_seed=int(instance_seed))),
        query=_Query(
            query_id=str(query_id),
            answer=int(answer_count),
            answer_type="integer",
            annotation_kind="bbox_set",
            annotation_item_keys=tuple(annotation_keys),
            params={
                "target_series_id": str(target.series_id),
                "target_series_label": str(target.label),
                "threshold_value": int(threshold),
                "threshold_relation": str(query_id).replace("_threshold_count", ""),
                "answer_x_indices": sorted(int(index) for index in answer_indices),
            },
        ),
    )


def _build_bound_extremum_dataset(params: Mapping[str, Any], *, query_id: str, instance_seed: int) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.bound_extremum")
    scene_variant, scene_probs = _resolve_scene_variant(params, instance_seed=int(instance_seed))
    x_count = _resolve_count(
        params,
        min_key="x_count_min",
        max_key="x_count_max",
        fallback_min=5,
        fallback_max=8,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.x_count",
    )
    series_count = _series_count(params, query_id=str(query_id), instance_seed=int(instance_seed))
    x_labels, x_meta, series_labels, series_meta = _sample_labels(
        params,
        x_count=int(x_count),
        series_count=int(series_count),
        instance_seed=int(instance_seed),
    )
    target_series_index = int(
        _choose_from_values(
            params,
            values=tuple(range(int(series_count))),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.bound.target_series",
        )
    )
    answer_index = int(
        _choose_from_values(
            params,
            values=tuple(range(int(x_count))),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.bound.answer_x",
        )
    )
    palette = _resolve_palette(params)
    series: List[_ErrorbarSeries] = []
    for series_index in range(int(series_count)):
        triples = _random_series_triples(rng, x_count=int(x_count))
        if int(series_index) == int(target_series_index):
            adjusted: List[Tuple[int, int, int]] = []
            for x_index in range(int(x_count)):
                if str(query_id) == "highest_upper_bound_x_label":
                    if int(x_index) == int(answer_index):
                        upper = 95
                        lower = int(rng.randint(58, 72))
                    else:
                        upper = int(rng.randint(45, 82))
                        lower = max(0, upper - int(rng.randint(7, 20)))
                    mid = int(round((lower + upper) / 2))
                else:
                    if int(x_index) == int(answer_index):
                        lower = 5
                        upper = int(rng.randint(26, 42))
                    else:
                        lower = int(rng.randint(18, 55))
                        upper = min(100, lower + int(rng.randint(7, 20)))
                    mid = int(round((lower + upper) / 2))
                adjusted.append((int(lower), int(mid), int(upper)))
            triples = adjusted
        series.append(
            _make_series(
                series_id=f"series_{series_index}",
                label=str(series_labels[int(series_index)]),
                color_rgb=palette[int(series_index) % len(palette)],
                triples=triples,
            )
        )
    target = series[int(target_series_index)]
    annotation_key = f"{target.label}:{x_labels[int(answer_index)]}"
    return _Dataset(
        x_labels=tuple(x_labels),
        x_label_meta=dict(x_meta),
        series=tuple(series),
        series_label_meta=dict(series_meta),
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_probs),
        query_id=str(query_id),
        query_id_probabilities={str(query_id): 1.0},
        threshold_value=None,
        target_series_id=str(target.series_id),
        target_x_index=int(answer_index),
        title=str(_choose_title(params, instance_seed=int(instance_seed))),
        query=_Query(
            query_id=str(query_id),
            answer=str(x_labels[int(answer_index)]),
            answer_type="string",
            annotation_kind="keyed_point_map",
            annotation_item_keys=(str(annotation_key),),
            params={
                "target_series_id": str(target.series_id),
                "target_series_label": str(target.label),
                "answer_x_index": int(answer_index),
                "answer_x_label": str(x_labels[int(answer_index)]),
                "bound_kind": "upper" if str(query_id) == "highest_upper_bound_x_label" else "lower",
                "extremum_direction": "highest" if str(query_id) == "highest_upper_bound_x_label" else "lowest",
            },
        ),
    )


def _build_overlap_dataset(params: Mapping[str, Any], *, query_id: str, instance_seed: int) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.overlap")
    scene_variant, scene_probs = _resolve_scene_variant(params, instance_seed=int(instance_seed))
    x_count = _resolve_count(
        params,
        min_key="x_count_min",
        max_key="x_count_max",
        fallback_min=5,
        fallback_max=8,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.x_count",
    )
    series_count = _series_count(params, query_id=str(query_id), instance_seed=int(instance_seed))
    x_labels, x_meta, series_labels, series_meta = _sample_labels(
        params,
        x_count=int(x_count),
        series_count=int(series_count),
        instance_seed=int(instance_seed),
    )
    target_series_index = int(
        _choose_from_values(
            params,
            values=tuple(range(int(series_count))),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.overlap.target_series",
        )
    )
    target_x_index = int(
        _choose_from_values(
            params,
            values=tuple(range(int(x_count))),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.overlap.target_x",
        )
    )
    max_overlap = min(int(series_count) - 1, int(params.get("overlap_answer_count_max", group_default(_GEN_DEFAULTS, "overlap_answer_count_max", 3))))
    min_overlap = min(max_overlap, int(params.get("overlap_answer_count_min", group_default(_GEN_DEFAULTS, "overlap_answer_count_min", 1))))
    answer_count = int(
        _choose_from_values(
            params,
            values=tuple(range(int(min_overlap), int(max_overlap) + 1)),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.overlap.answer_count",
        )
    )
    other_indices = [index for index in range(int(series_count)) if int(index) != int(target_series_index)]
    rng.shuffle(other_indices)
    overlapping_indices = set(other_indices[: int(answer_count)])
    target_low = int(rng.randint(34, 48))
    target_high = int(target_low + rng.randint(18, 28))
    target_mid = int(round((target_low + target_high) / 2))
    palette = _resolve_palette(params)
    series: List[_ErrorbarSeries] = []
    for series_index in range(int(series_count)):
        triples = _random_series_triples(rng, x_count=int(x_count))
        adjusted = list(triples)
        if int(series_index) == int(target_series_index):
            adjusted[int(target_x_index)] = (int(target_low), int(target_mid), int(target_high))
        elif int(series_index) in overlapping_indices:
            low = int(rng.randint(max(0, target_low - 12), min(target_high - 2, target_low + 10)))
            high = int(rng.randint(max(low + 6, target_low + 2), min(100, target_high + 14)))
            mid = int(round((low + high) / 2))
            adjusted[int(target_x_index)] = (int(low), int(mid), int(high))
        else:
            if rng.random() < 0.5:
                high = max(6, int(target_low) - int(rng.randint(4, 14)))
                low = max(0, high - int(rng.randint(8, 18)))
            else:
                low = min(92, int(target_high) + int(rng.randint(4, 14)))
                high = min(100, low + int(rng.randint(8, 18)))
            mid = int(round((low + high) / 2))
            adjusted[int(target_x_index)] = (int(low), int(mid), int(high))
        series.append(
            _make_series(
                series_id=f"series_{series_index}",
                label=str(series_labels[int(series_index)]),
                color_rgb=palette[int(series_index) % len(palette)],
                triples=adjusted,
            )
        )
    target = series[int(target_series_index)]
    counted_labels = [str(series[index].label) for index in sorted(overlapping_indices)]
    annotation_keys = tuple([f"{target.label}:{x_labels[int(target_x_index)]}"] + [f"{label}:{x_labels[int(target_x_index)]}" for label in counted_labels])
    return _Dataset(
        x_labels=tuple(x_labels),
        x_label_meta=dict(x_meta),
        series=tuple(series),
        series_label_meta=dict(series_meta),
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_probs),
        query_id=str(query_id),
        query_id_probabilities={str(query_id): 1.0},
        threshold_value=None,
        target_series_id=str(target.series_id),
        target_x_index=int(target_x_index),
        title=str(_choose_title(params, instance_seed=int(instance_seed))),
        query=_Query(
            query_id=str(query_id),
            answer=int(answer_count),
            answer_type="integer",
            annotation_kind="keyed_bbox_map",
            annotation_item_keys=tuple(annotation_keys),
            params={
                "target_series_id": str(target.series_id),
                "target_series_label": str(target.label),
                "target_x_index": int(target_x_index),
                "target_x_label": str(x_labels[int(target_x_index)]),
                "overlapping_series_labels": list(counted_labels),
                "overlapping_series_ids": [str(series[index].series_id) for index in sorted(overlapping_indices)],
            },
        ),
    )


def _build_dataset(params: Mapping[str, Any], *, query_id: str, instance_seed: int) -> _Dataset:
    if str(query_id) in set(THRESHOLD_QUERY_IDS):
        return _build_threshold_dataset(params, query_id=str(query_id), instance_seed=int(instance_seed))
    if str(query_id) in set(BOUND_EXTREMUM_QUERY_IDS):
        return _build_bound_extremum_dataset(params, query_id=str(query_id), instance_seed=int(instance_seed))
    if str(query_id) in set(OVERLAP_QUERY_IDS):
        return _build_overlap_dataset(params, query_id=str(query_id), instance_seed=int(instance_seed))
    raise ValueError(f"unsupported query id: {query_id}")


def _choose_title(params: Mapping[str, Any], *, instance_seed: int) -> str:
    raw_titles = params.get("title_options", group_default(_RENDER_DEFAULTS, "title_options", ()))
    titles = tuple(str(value) for value in raw_titles) if isinstance(raw_titles, Sequence) and not isinstance(raw_titles, (str, bytes)) else ()
    if not titles:
        titles = ("Error-Bar Series", "Scientific Estimate Profile", "Point Estimate Ranges")
    return str(
        _choose_from_values(
            params,
            values=titles,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.title",
        )
    )


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


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int, chart_font_family: str) -> _RenderParams:
    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    left, right, top, bottom, jitter = apply_layout_jitter_to_margins(
        left_px=_resolve_int(params, "plot_margin_left_px", 90),
        right_px=_resolve_int(params, "plot_margin_right_px", 180),
        top_px=_resolve_int(params, "plot_margin_top_px", 88),
        bottom_px=_resolve_int(params, "plot_margin_bottom_px", 94),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    return _RenderParams(
        canvas_width=_resolve_int(params, "canvas_width", 1280),
        canvas_height=_resolve_int(params, "canvas_height", 820),
        margin_left_px=int(left),
        margin_right_px=int(right),
        margin_top_px=int(top),
        margin_bottom_px=int(bottom),
        title_font_size_px=_resolve_int(params, "title_font_size_px", 26),
        tick_font_size_px=_resolve_int(params, "tick_font_size_px", 15),
        label_font_size_px=_resolve_int(params, "label_font_size_px", 17),
        legend_font_size_px=_resolve_int(params, "legend_font_size_px", 16),
        axis_min=_resolve_int(params, "axis_min", 0),
        axis_max=_resolve_int(params, "axis_max", 100),
        tick_step=_resolve_int(params, "tick_step", 20),
        axis_line_width_px=_resolve_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_resolve_int(params, "grid_line_width_px", 1),
        errorbar_line_width_px=_resolve_int(params, "errorbar_line_width_px", 3),
        center_line_width_px=_resolve_int(params, "center_line_width_px", 2),
        cap_width_px=_resolve_int(params, "cap_width_px", 14),
        point_radius_px=_resolve_int(params, "point_radius_px", 5),
        series_offset_px=_resolve_int(params, "series_offset_px", 11),
        text_rgb=_resolve_rgb(params, "text_rgb", (36, 42, 54)),
        muted_text_rgb=_resolve_rgb(params, "muted_text_rgb", (86, 94, 110)),
        text_stroke_rgb=_resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        axis_rgb=_resolve_rgb(params, "axis_rgb", (62, 68, 78)),
        grid_rgb=_resolve_rgb(params, "grid_rgb", (222, 227, 234)),
        panel_fill_rgb=_resolve_rgb(params, "panel_fill_rgb", (255, 255, 255)),
        panel_outline_rgb=_resolve_rgb(params, "panel_outline_rgb", (194, 202, 214)),
        threshold_rgb=_resolve_rgb(params, "threshold_rgb", (95, 84, 74)),
        font_family=str(chart_font_family),
        layout_jitter_meta=dict(jitter),
    )


def _plot_bbox(rp: _RenderParams) -> BBox:
    return _bbox(
        [
            float(rp.margin_left_px),
            float(rp.margin_top_px),
            float(rp.canvas_width - rp.margin_right_px),
            float(rp.canvas_height - rp.margin_bottom_px),
        ]
    )


def _scale_y(value: float, *, rp: _RenderParams, plot_bbox: Sequence[float]) -> float:
    _x0, y0, _x1, y1 = (float(value) for value in plot_bbox)
    denom = max(1.0, float(rp.axis_max) - float(rp.axis_min))
    return y1 - ((float(value) - float(rp.axis_min)) / denom) * (y1 - y0)


def _x_positions(dataset: _Dataset, *, plot_bbox: Sequence[float], rp: _RenderParams) -> Dict[str, Dict[str, float]]:
    x0, _y0, x1, _y1 = (float(value) for value in plot_bbox)
    count = len(dataset.x_labels)
    if count <= 1:
        base_positions = [x0 + ((x1 - x0) / 2.0)]
    else:
        step = (x1 - x0) / float(count - 1)
        base_positions = [x0 + step * index for index in range(count)]
    offsets: Dict[str, Dict[str, float]] = {}
    series_count = len(dataset.series)
    for series_index, series in enumerate(dataset.series):
        if str(dataset.scene_variant) == "grouped_errorbar":
            offset = (float(series_index) - ((float(series_count) - 1.0) / 2.0)) * float(rp.series_offset_px) * 1.35
        else:
            offset = (float(series_index) - ((float(series_count) - 1.0) / 2.0)) * float(rp.series_offset_px)
        offsets[str(series.series_id)] = {
            str(label): float(base_positions[index] + offset)
            for index, label in enumerate(dataset.x_labels)
        }
    return offsets


def _draw_axes(draw: ImageDraw.ImageDraw, *, dataset: _Dataset, rp: _RenderParams, plot_bbox: Sequence[float]) -> None:
    x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    draw.rectangle([x0, y0, x1, y1], fill=rp.panel_fill_rgb, outline=rp.panel_outline_rgb, width=1)
    tick_font = load_font(int(rp.tick_font_size_px), bold=False)
    label_font = load_font(int(rp.label_font_size_px), bold=False)
    for tick in range(int(rp.axis_min), int(rp.axis_max) + 1, max(1, int(rp.tick_step))):
        sy = _scale_y(float(tick), rp=rp, plot_bbox=plot_bbox)
        draw.line([x0, sy, x1, sy], fill=rp.grid_rgb, width=max(1, int(rp.grid_line_width_px)))
        draw_text_traced(draw, (x0 - 12.0, sy), str(tick), font=tick_font, fill=rp.muted_text_rgb, anchor="rm", role="readout", required=False)
    draw.line([x0, y1, x1, y1], fill=rp.axis_rgb, width=max(1, int(rp.axis_line_width_px)))
    draw.line([x0, y0, x0, y1], fill=rp.axis_rgb, width=max(1, int(rp.axis_line_width_px)))
    base_positions = _x_positions(dataset, plot_bbox=plot_bbox, rp=rp)[str(dataset.series[0].series_id)]
    for label in dataset.x_labels:
        x = float(base_positions[str(label)])
        draw.line([x, y1, x, y1 + 5.0], fill=rp.axis_rgb, width=1)
        draw_text_traced(draw, (x, y1 + 13.0), str(label), font=label_font, fill=rp.text_rgb, anchor="mt", role="readout", required=False)


def _draw_threshold(draw: ImageDraw.ImageDraw, *, threshold_value: int | None, rp: _RenderParams, plot_bbox: Sequence[float]) -> BBox | None:
    if threshold_value is None:
        return None
    x0, _y0, x1, _y1 = (float(value) for value in plot_bbox)
    sy = _scale_y(float(threshold_value), rp=rp, plot_bbox=plot_bbox)
    draw.line([x0, sy, x1, sy], fill=rp.threshold_rgb, width=2)
    font = load_font(int(rp.tick_font_size_px), bold=False)
    draw_text_traced(
        draw,
        (x1 + 10.0, sy),
        f"ref {int(threshold_value)}",
        font=font,
        fill=rp.threshold_rgb,
        stroke_fill=rp.text_stroke_rgb,
        stroke_width=2,
        anchor="lm",
        role="readout",
        required=False,
    )
    return _bbox([x0, sy - 2.0, x1, sy + 2.0])


def _draw_legend(draw: ImageDraw.ImageDraw, *, dataset: _Dataset, rp: _RenderParams, plot_bbox: Sequence[float]) -> None:
    _x0, y0, x1, _y1 = (float(value) for value in plot_bbox)
    font = load_font(int(rp.legend_font_size_px), bold=False)
    legend_x = x1 + 24.0
    legend_y = y0 + 24.0
    for index, series in enumerate(dataset.series):
        y = legend_y + float(index) * 30.0
        draw.line([legend_x, y, legend_x + 28.0, y], fill=series.color_rgb, width=max(2, int(rp.center_line_width_px)))
        radius = 4.0
        draw.ellipse([legend_x + 12.0 - radius, y - radius, legend_x + 12.0 + radius, y + radius], fill=series.color_rgb, outline=rp.panel_fill_rgb, width=1)
        draw_text_traced(draw, (legend_x + 38.0, y), str(series.label), font=font, fill=rp.text_rgb, anchor="lm", role="readout", required=False)


def _errorbar_key(series: _ErrorbarSeries, x_label: str) -> str:
    return f"{series.label}:{x_label}"


def _draw_series_marks(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _Dataset,
    rp: _RenderParams,
    plot_bbox: Sequence[float],
) -> Tuple[Tuple[Dict[str, Any], ...], Dict[str, BBox], Dict[str, Dict[str, Dict[str, Point]]]]:
    x_positions = _x_positions(dataset, plot_bbox=plot_bbox, rp=rp)
    entities: List[Dict[str, Any]] = []
    errorbar_bboxes: Dict[str, BBox] = {}
    point_map: Dict[str, Dict[str, Dict[str, Point]]] = {}
    for series in dataset.series:
        mark_rows: List[Tuple[int, str, float, float, float, float]] = []
        for x_index, x_label in enumerate(dataset.x_labels):
            x = float(x_positions[str(series.series_id)][str(x_label)])
            y_lower = _scale_y(float(series.lower_values[int(x_index)]), rp=rp, plot_bbox=plot_bbox)
            y_mid = _scale_y(float(series.mid_values[int(x_index)]), rp=rp, plot_bbox=plot_bbox)
            y_upper = _scale_y(float(series.upper_values[int(x_index)]), rp=rp, plot_bbox=plot_bbox)
            mark_rows.append((int(x_index), str(x_label), float(x), float(y_lower), float(y_mid), float(y_upper)))
        if str(dataset.scene_variant) == "line_marker_errorbar":
            mid_points = [(float(row[2]), float(row[4])) for row in mark_rows]
            for first, second in zip(mid_points, mid_points[1:]):
                draw.line([first[0], first[1], second[0], second[1]], fill=series.color_rgb, width=max(1, int(rp.center_line_width_px)))
        for x_index, x_label, x, y_lower, y_mid, y_upper in mark_rows:
            cap = float(rp.cap_width_px)
            radius = float(rp.point_radius_px)
            draw.line([x, y_upper, x, y_lower], fill=series.color_rgb, width=max(1, int(rp.errorbar_line_width_px)))
            draw.line([x - cap / 2.0, y_upper, x + cap / 2.0, y_upper], fill=series.color_rgb, width=max(1, int(rp.errorbar_line_width_px)))
            draw.line([x - cap / 2.0, y_lower, x + cap / 2.0, y_lower], fill=series.color_rgb, width=max(1, int(rp.errorbar_line_width_px)))
            draw.ellipse([x - radius, y_mid - radius, x + radius, y_mid + radius], fill=series.color_rgb, outline=rp.panel_fill_rgb, width=2)
            key = _errorbar_key(series, str(x_label))
            bbox = _bbox([x - cap / 2.0 - radius, y_upper - radius, x + cap / 2.0 + radius, y_lower + radius])
            errorbar_bboxes[str(key)] = bbox
            point_map.setdefault(str(series.label), {})[str(x_label)] = {
                "lower_bound": _point(x, y_lower),
                "midpoint": _point(x, y_mid),
                "upper_bound": _point(x, y_upper),
            }
            entities.append(
                {
                    "entity_id": str(key),
                    "entity_type": "errorbar_mark",
                    "bbox_px": list(bbox),
                    "attrs": {
                        "series_id": str(series.series_id),
                        "series_label": str(series.label),
                        "x_index": int(x_index),
                        "x_label": str(x_label),
                        "lower": int(series.lower_values[int(x_index)]),
                        "mid": int(series.mid_values[int(x_index)]),
                        "upper": int(series.upper_values[int(x_index)]),
                    },
                }
            )
    return tuple(entities), dict(errorbar_bboxes), dict(point_map)


def _render_dataset(dataset: _Dataset, *, params: Mapping[str, Any], instance_seed: int, chart_font_family: str) -> _Rendered:
    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    rp = _resolve_render_params(params, instance_seed=int(instance_seed), chart_font_family=str(chart_font_family))
    background, background_meta = make_background_canvas(
        canvas_width=int(rp.canvas_width),
        canvas_height=int(rp.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_bbox = _plot_bbox(rp)
    title_font = load_font(int(rp.title_font_size_px), bold=True)
    draw_text_traced(draw, (float(rp.margin_left_px), 30.0), str(dataset.title), font=title_font, fill=rp.text_rgb, role="readout", required=False)
    _draw_axes(draw, dataset=dataset, rp=rp, plot_bbox=plot_bbox)
    threshold_bbox = _draw_threshold(draw, threshold_value=dataset.threshold_value, rp=rp, plot_bbox=plot_bbox)
    entities, errorbar_bboxes, point_map = _draw_series_marks(draw, dataset=dataset, rp=rp, plot_bbox=plot_bbox)
    _draw_legend(draw, dataset=dataset, rp=rp, plot_bbox=plot_bbox)
    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        errorbar_bboxes_px=dict(errorbar_bboxes),
        point_map_px=dict(point_map),
        threshold_bbox_px=list(threshold_bbox) if threshold_bbox is not None else None,
        render_meta={
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "layout_jitter": dict(rp.layout_jitter_meta),
        },
    )


def _build_annotation(dataset: _Dataset, rendered: _Rendered) -> TypedValue:
    if str(dataset.query.annotation_kind) == "bbox_set":
        boxes = []
        for key in dataset.query.annotation_item_keys:
            if str(key) not in rendered.errorbar_bboxes_px:
                raise RuntimeError(f"missing errorbar bbox for {key}")
            boxes.append(list(rendered.errorbar_bboxes_px[str(key)]))
        return TypedValue(type="bbox_set", value=boxes)
    if str(dataset.query.annotation_kind) == "keyed_point_map":
        key = str(dataset.query.annotation_item_keys[0])
        series_label, x_label = key.split(":", 1)
        bound_kind = str(dataset.query.params["bound_kind"])
        point = rendered.point_map_px[str(series_label)][str(x_label)][f"{bound_kind}_bound"]
        return TypedValue(type="keyed_point_map", value={"selected_bound_endpoint": list(point)})
    if str(dataset.query.annotation_kind) == "keyed_bbox_map":
        mapping: Dict[str, BBox] = {}
        for index, key in enumerate(dataset.query.annotation_item_keys):
            if str(key) not in rendered.errorbar_bboxes_px:
                raise RuntimeError(f"missing errorbar bbox for {key}")
            if int(index) == 0:
                role = "target_errorbar"
            else:
                role = str(key).split(":", 1)[0]
            mapping[str(role)] = list(rendered.errorbar_bboxes_px[str(key)])
        return TypedValue(type="keyed_bbox_map", value=dict(mapping))
    raise ValueError(f"unsupported annotation kind: {dataset.query.annotation_kind}")


def _series_trace(dataset: _Dataset) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for series in dataset.series:
        rows.append(
            {
                "series_id": str(series.series_id),
                "label": str(series.label),
                "color_rgb": list(series.color_rgb),
                "lower_values": list(series.lower_values),
                "mid_values": list(series.mid_values),
                "upper_values": list(series.upper_values),
            }
        )
    return rows


def _projected_annotation(annotation_gt: TypedValue) -> Dict[str, Any]:
    if str(annotation_gt.type) == "bbox_set":
        return {"type": "bbox_set", "bbox_set": list(annotation_gt.value), "pixel_bbox_set": list(annotation_gt.value)}
    if str(annotation_gt.type) == "keyed_point_map":
        return {
            "type": "keyed_point_map",
            "keyed_point_map": dict(annotation_gt.value),
            "pixel_keyed_point_map": dict(annotation_gt.value),
        }
    if str(annotation_gt.type) == "keyed_bbox_map":
        return {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_gt.value),
            "pixel_keyed_bbox_map": dict(annotation_gt.value),
        }
    return {"type": str(annotation_gt.type), str(annotation_gt.type): annotation_gt.value}


class ChartsErrorbarSeriesBaseTask:
    """Answer scientific error-bar series questions."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "errorbar_series"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_params = {**dict(params), "_attempt_index": int(attempt_index)}
                dataset = _build_dataset(attempt_params, query_id=str(query_id), instance_seed=int(instance_seed) + int(attempt_index))
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error
        dataset = _Dataset(
            x_labels=dataset.x_labels,
            x_label_meta=dataset.x_label_meta,
            series=dataset.series,
            series_label_meta=dataset.series_label_meta,
            scene_variant=dataset.scene_variant,
            scene_variant_probabilities=dataset.scene_variant_probabilities,
            query_id=dataset.query_id,
            query_id_probabilities=dict(query_probabilities),
            threshold_value=dataset.threshold_value,
            target_series_id=dataset.target_series_id,
            target_x_index=dataset.target_x_index,
            title=dataset.title,
            query=dataset.query,
        )

        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_dataset(dataset, params=params, instance_seed=int(instance_seed), chart_font_family=str(chart_font_family))
        annotation_gt = _build_annotation(dataset, rendered)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "answer_hint_count",
                "answer_hint_label",
                "annotation_hint_threshold_support_count",
                "annotation_hint_bound_extremum_x_label",
                "annotation_hint_same_x_interval_overlap_count",
                "json_example_threshold_support_count",
                "json_example_bound_extremum_x_label",
                "json_example_same_x_interval_overlap_count",
                "json_example_answer_only_threshold_support_count",
                "json_example_answer_only_bound_extremum_x_label",
                "json_example_answer_only_same_x_interval_overlap_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_family = (
            "threshold_support_count"
            if str(dataset.query.query_id) in set(THRESHOLD_QUERY_IDS)
            else "bound_extremum_x_label"
            if str(dataset.query.query_id) in set(BOUND_EXTREMUM_QUERY_IDS)
            else "same_x_interval_overlap_count"
        )
        answer_hint_key = "answer_hint_count" if str(dataset.query.answer_type) == "integer" else "answer_hint_label"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_series_label": str(dataset.query.params.get("target_series_label", "")),
                "threshold_value": "" if dataset.threshold_value is None else str(dataset.threshold_value),
                "target_x_label": str(dataset.query.params.get("target_x_label", "")),
                "bound_phrase": "upper error-bar endpoint" if dataset.query.params.get("bound_kind") == "upper" else "lower error-bar endpoint",
                "extremum_phrase": str(dataset.query.params.get("extremum_direction", "")),
                "threshold_relation_phrase": {
                    "entirely_above_threshold_count": "entirely above",
                    "entirely_below_threshold_count": "entirely below",
                    "contains_threshold_count": "containing",
                }.get(str(dataset.query.query_id), ""),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{prompt_family}"]),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "json_example": str(prompt_defaults[f"json_example_{prompt_family}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{prompt_family}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer)
        execution_trace = {
            "query_id": str(dataset.query.query_id),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "question_format": "errorbar_series",
            "answer_value": dataset.query.answer,
            "answer_type": str(dataset.query.answer_type),
            "x_count": int(len(dataset.x_labels)),
            "series_count": int(len(dataset.series)),
            "x_labels": list(dataset.x_labels),
            "x_label_meta": dict(dataset.x_label_meta),
            "series_label_meta": dict(dataset.series_label_meta),
            "series": _series_trace(dataset),
            "target_series_id": str(dataset.target_series_id),
            "target_x_index": dataset.target_x_index,
            "threshold_value": dataset.threshold_value,
            "query_params": dict(dataset.query.params),
            "annotation_item_keys": list(dataset.query.annotation_item_keys),
            "query_id_probabilities": dict(dataset.query_id_probabilities),
            "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_errorbar_series",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "target_series_id": str(dataset.target_series_id),
                    "target_x_index": dataset.target_x_index,
                },
            },
            "query_spec": {
                "query_id": str(dataset.query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(dataset.query.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(dataset.scene_variant),
                    "query_id_probabilities": dict(dataset.query_id_probabilities),
                    **dict(dataset.query.params),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered.image.size[0]),
                "canvas_height": int(rendered.image.size[1]),
                "coord_space": "pixel",
                "scene_variant": str(dataset.scene_variant),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "errorbar_bboxes_px": dict(rendered.errorbar_bboxes_px),
                "point_map_px": dict(rendered.point_map_px),
                "threshold_bbox_px": rendered.threshold_bbox_px,
            },
            "execution_trace": dict(execution_trace),
            "witness_symbolic": {
                "type": "errorbar_series_witness",
                "annotation_kind": str(dataset.query.annotation_kind),
                "annotation_item_keys": list(dataset.query.annotation_item_keys),
                "answer": dataset.query.answer,
            },
            "projected_annotation": _projected_annotation(annotation_gt),
        }
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(len(dataset.x_labels) * len(dataset.series)), [10, 32]),
                "reasoning_load": clamp_unit_interval(float(_QUERY_REASONING_LOADS[str(dataset.query.query_id)])),
                "scene_variant_load": clamp_unit_interval(float(_SCENE_VARIANT_LOADS[str(dataset.scene_variant)])),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsErrorbarSeriesThresholdSupportCountTask(MergedChartQueryVariantTaskMixin, ChartsErrorbarSeriesBaseTask):
    """Count x positions whose error bars support a threshold relation."""

    task_id = "task_charts__errorbar_series__threshold_support_count"
    allowed_query_ids = THRESHOLD_QUERY_IDS


@register_task
class ChartsErrorbarSeriesBoundExtremumXLabelTask(MergedChartQueryVariantTaskMixin, ChartsErrorbarSeriesBaseTask):
    """Find the x-axis label with an extremal error-bar bound."""

    task_id = "task_charts__errorbar_series__bound_extremum_x_label"
    allowed_query_ids = BOUND_EXTREMUM_QUERY_IDS


@register_task
class ChartsErrorbarSeriesSameXIntervalOverlapCountTask(MergedChartQueryVariantTaskMixin, ChartsErrorbarSeriesBaseTask):
    """Count same-x error bars overlapping a target series interval."""

    task_id = "task_charts__errorbar_series__same_x_interval_overlap_count"
    allowed_query_ids = OVERLAP_QUERY_IDS


__all__ = [
    "BOUND_EXTREMUM_QUERY_IDS",
    "OVERLAP_QUERY_IDS",
    "SUPPORTED_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
    "THRESHOLD_QUERY_IDS",
    "ChartsErrorbarSeriesBaseTask",
    "ChartsErrorbarSeriesBoundExtremumXLabelTask",
    "ChartsErrorbarSeriesSameXIntervalOverlapCountTask",
    "ChartsErrorbarSeriesThresholdSupportCountTask",
]
