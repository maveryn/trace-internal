"""Annotated single-series chart tasks.

The scene keeps the underlying chart grammar shared with other single-series
chart tasks, but adds a visible annotation layer that defines the query scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union, round_bbox
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.context_text_assets import sample_context_text
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import draw_text_centered, load_font, temporary_default_font_family
from ...shared.visual_style.context_layer import (
    ContextTextElement,
    context_text_layer_metadata,
    draw_dashboard_reserved_margin_context,
    resolve_dashboard_context_layout,
)
from ..shared.chart_scene import RenderedChartScene, render_labeled_chart_scene, value_axis_render_metadata
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.labeled_chart_common import (
    LabeledChartDefaults,
    balanced_choice_from_values,
    build_chart_mark_specs,
    choose_mark_count,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
    sample_chart_labels,
)
from ..shared.information_style import prepare_chart_information_scene
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_annotated_series_query_base"
SCENE_ID = "annotated_series"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "event_window_extremum_label",
    "event_window_threshold_count",
    "callout_endpoint_change_value",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "line",
    "bar",
    "area",
    "dot_plot",
    "lollipop",
)
SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("highest", "lowest")
SUPPORTED_THRESHOLD_COMPARISONS: Tuple[str, ...] = ("greater_than", "less_than")
SUPPORTED_ENDPOINT_SIDES: Tuple[str, ...] = ("first", "last")

_DEFAULTS = LabeledChartDefaults(mark_count_min=8, mark_count_max=14, value_min=10, value_max=90)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "annotated_series")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="annotated_series")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="annotated_series", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "line": 0.22,
    "bar": 0.30,
    "area": 0.42,
    "dot_plot": 0.50,
    "lollipop": 0.58,
}
_REASONING_LOADS: Dict[str, float] = {
    "event_window_extremum_label": 0.50,
    "event_window_threshold_count": 0.68,
    "callout_endpoint_change_value": 0.62,
}

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class _Dataset:
    query_id: str
    scene_variant: str
    labels: Tuple[str, ...]
    values: Tuple[int, ...]
    window_labels: Tuple[str, ...]
    evidence_labels: Tuple[str, ...]
    answer_value: str | int
    answer_type: str
    query_params: Dict[str, Any]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Annotation:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    point_set: Tuple[List[float], ...]
    annotation_bboxes: Dict[str, List[float]]


_CONTEXT_PARAM_KEYS: Tuple[str, ...] = (
    "context_text_enabled",
    "context_text_mode_weights",
    "context_text_top_reserved_px",
    "context_text_bottom_reserved_px",
    "context_text_left_margin_px",
    "context_text_right_margin_px",
    "context_text_sidebar_width_px",
    "context_text_sidebar_width_min_px",
    "context_text_sidebar_width_max_px",
    "context_text_sidebar_gap_px",
    "context_text_bottom_band_height_min_px",
    "context_text_bottom_band_height_max_px",
    "context_text_bottom_band_gap_px",
    "context_text_box_count_min",
    "context_text_box_count_max",
    "context_text_font_family_weights",
    "context_text_chrome_font_family",
    "context_text_chip_font_family",
    "context_text_box_font_family",
)


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _probability_map_from_weights(
    params: Mapping[str, Any],
    *,
    key: str,
    supported: Sequence[str],
) -> Dict[str, float]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), {str(item): 1.0 for item in supported}))
    if not isinstance(raw, Mapping):
        raise ValueError(f"{key} must be a mapping")
    weights = {
        str(item): max(0.0, float(raw.get(str(item), 0.0)))
        for item in supported
    }
    total = float(sum(weights.values()))
    if total <= 0.0:
        weights = {str(item): 1.0 for item in supported}
        total = float(len(weights))
    return {str(key): float(value) / float(total) for key, value in sorted(weights.items())}


def _render_default_value(params: Mapping[str, Any], key: str, fallback: Any) -> Any:
    return params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), fallback))


def _render_choice(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: str,
    instance_seed: int,
    namespace: str,
) -> str:
    explicit = params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), None))
    if explicit is not None:
        return str(explicit)
    options = params.get(f"{str(key)}_options", group_default(_RENDER_DEFAULTS, f"{str(key)}_options", ()))
    if isinstance(options, Sequence) and options and not isinstance(options, (str, bytes)):
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{str(namespace)}.{str(key)}",
        )
        return str(options[int(index) % len(options)])
    return str(fallback)


def _context_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    resolved: Dict[str, Any] = {}
    for key in _CONTEXT_PARAM_KEYS:
        value = params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), None))
        if value is not None:
            resolved[str(key)] = value
    return resolved


def _choose_context_mode(*, params: Mapping[str, Any], instance_seed: int) -> str:
    if not bool(_render_default_value(params, "context_text_enabled", False)):
        return "clean"
    supported = ("clean", "light_context", "right_sidebar", "bottom_band")
    raw_weights = _render_default_value(
        params,
        "context_text_mode_weights",
        {"clean": 0.5, "light_context": 0.3, "right_sidebar": 0.1, "bottom_band": 0.1},
    )
    if not isinstance(raw_weights, Mapping):
        raw_weights = {"clean": 1.0}
    weights = []
    for mode in supported:
        weight = max(0.0, float(raw_weights.get(str(mode), 0.0)))
        if weight > 0.0:
            weights.append((str(mode), float(weight)))
    if not weights:
        return "clean"
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.context_text_mode")
    cursor = rng.random() * sum(weight for _, weight in weights)
    running = 0.0
    for mode, weight in weights:
        running += float(weight)
        if cursor <= running:
            return str(mode)
    return str(weights[-1][0])


def _resolve_context_layout(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
) -> Dict[str, Any]:
    mode = _choose_context_mode(params=params, instance_seed=int(instance_seed))
    context_params = _context_params(params)
    top_reserved = int(context_params.get("context_text_top_reserved_px", 64))
    bottom_reserved = int(context_params.get("context_text_bottom_reserved_px", 28))
    if str(mode) == "clean":
        return {
            "enabled": False,
            "mode": "clean",
            "layout_mode": "clean",
            "placement": "none",
            "context_params": context_params,
            "top_reserved_px": int(top_reserved),
            "bottom_reserved_px": int(bottom_reserved),
        }
    if str(mode) == "light_context":
        return {
            "enabled": True,
            "mode": "light_context",
            "layout_mode": "light_context",
            "placement": "top_bottom_notes",
            "box_count": 0,
            "context_params": context_params,
            "top_reserved_px": int(top_reserved),
            "bottom_reserved_px": int(bottom_reserved),
        }
    placement = "right_sidebar" if str(mode) == "right_sidebar" else "bottom_band"
    layout = resolve_dashboard_context_layout(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.context",
        params={**context_params, "context_text_enabled": True, "context_text_placement": str(placement)},
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        top_reserved_px=int(top_reserved),
        bottom_reserved_px=int(bottom_reserved),
        left_margin_px=int(context_params.get("context_text_left_margin_px", 24)),
        right_margin_px=int(context_params.get("context_text_right_margin_px", 24)),
    )
    return {
        **dict(layout),
        "enabled": True,
        "mode": str(mode),
        "context_params": context_params,
    }


def _apply_context_margin_overrides(
    params: Mapping[str, Any],
    *,
    context_layout: Mapping[str, Any],
) -> Dict[str, Any]:
    resolved = dict(params)
    if not bool(context_layout.get("enabled", False)):
        return resolved

    base_left = int(_render_default_value(params, "plot_margin_left_px", _DEFAULTS.plot_margin_left_px))
    base_right = int(_render_default_value(params, "plot_margin_right_px", _DEFAULTS.plot_margin_right_px))
    base_bottom = int(_render_default_value(params, "plot_margin_bottom_px", _DEFAULTS.plot_margin_bottom_px))
    placement = str(context_layout.get("placement", "none"))
    if placement == "right_sidebar":
        sidebar_width = int(context_layout.get("sidebar_width_px", 0))
        sidebar_gap = int(context_layout.get("sidebar_gap_px", 14))
        resolved["plot_margin_right_px"] = int(base_right + max(0, sidebar_width) + max(0, sidebar_gap))
        resolved["plot_margin_left_px"] = int(base_left)
        resolved["layout_jitter_x_px"] = 0
    elif placement == "bottom_band":
        bottom_height = int(context_layout.get("bottom_band_height_px", 0))
        bottom_gap = int(context_layout.get("bottom_band_gap_px", 14))
        resolved["plot_margin_bottom_px"] = int(base_bottom + max(0, bottom_height) + max(0, bottom_gap))
        resolved["layout_jitter_y_px"] = 0
    return resolved


def _choose_string_axis(
    params: Mapping[str, Any],
    *,
    axis: str,
    supported: Sequence[str],
    weights_key: str,
    balance_key: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    explicit = params.get(str(axis))
    supported_values = tuple(str(item) for item in supported)
    if explicit is not None:
        value = str(explicit)
        if value not in set(supported_values):
            raise ValueError(f"unsupported {axis}: {value}")
        return value, {item: (1.0 if item == value else 0.0) for item in sorted(supported_values)}
    probabilities = _probability_map_from_weights(params, key=str(weights_key), supported=supported_values)
    positives = [item for item in supported_values if float(probabilities.get(str(item), 0.0)) > 0.0]
    if not positives:
        raise ValueError(f"no positive support for {axis}")
    use_balanced = bool(params.get(str(balance_key), group_default(_GEN_DEFAULTS, str(balance_key), True)))
    if bool(use_balanced) and max(probabilities[item] for item in positives) - min(probabilities[item] for item in positives) <= 1e-9:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.{axis}")
        return str(positives[int(index) % len(positives)]), dict(probabilities)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{axis}")
    threshold = rng.random()
    cumulative = 0.0
    for item in positives:
        cumulative += float(probabilities[item])
        if float(threshold) <= float(cumulative):
            return str(item), dict(probabilities)
    return str(positives[-1]), dict(probabilities)


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


def _choose_window(
    params: Mapping[str, Any],
    *,
    mark_count: int,
    instance_seed: int,
    min_window_size: int = 2,
) -> Tuple[int, int]:
    min_size, max_size = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="window_size_min",
        max_key="window_size_max",
        fallback_min=3,
        fallback_max=6,
        context=f"generation defaults for {TASK_ID}",
    )
    min_size = max(int(min_window_size), min(int(min_size), int(mark_count)))
    max_size = max(int(min_size), min(int(max_size), int(mark_count)))
    window_size = balanced_choice_from_values(
        [int(value) for value in range(int(min_size), int(max_size) + 1)],
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.window_size",
    )
    start_values = [int(value) for value in range(0, int(mark_count) - int(window_size) + 1)]
    start_index = balanced_choice_from_values(
        start_values,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.window_start",
    )
    return int(start_index), int(window_size)


def _sample_values(*, count: int, params: Mapping[str, Any], instance_seed: int) -> Tuple[int, ...]:
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=_DEFAULTS.value_min,
        fallback_max=_DEFAULTS.value_max,
        context=f"generation defaults for {TASK_ID}",
    )
    support = [int(value) for value in range(int(value_min), int(value_max) + 1)]
    if len(support) < int(count):
        raise ValueError("annotated_series requires enough distinct values for all marks")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.values")
    values = [int(value) for value in rng.sample(support, k=int(count))]
    return tuple(int(value) for value in values)


def _build_extremum_dataset(
    *,
    query_id: str,
    scene_variant: str,
    labels: Sequence[str],
    values: Sequence[int],
    window_start: int,
    window_size: int,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float],
) -> _Dataset:
    direction, direction_probabilities = _choose_string_axis(
        params,
        axis="extremum_direction",
        supported=SUPPORTED_EXTREMUM_DIRECTIONS,
        weights_key="extremum_direction_weights",
        balance_key="balanced_extremum_direction_sampling",
        instance_seed=int(instance_seed),
    )
    window_pairs = [
        (int(value), str(label))
        for label, value in zip(labels[int(window_start) : int(window_start) + int(window_size)], values[int(window_start) : int(window_start) + int(window_size)])
    ]
    answer_value, answer_label = (
        max(window_pairs, key=lambda item: (item[0], item[1]))
        if direction == "highest"
        else min(window_pairs, key=lambda item: (item[0], item[1]))
    )
    del answer_value
    return _Dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        labels=tuple(str(label) for label in labels),
        values=tuple(int(value) for value in values),
        window_labels=tuple(str(label) for label in labels[int(window_start) : int(window_start) + int(window_size)]),
        evidence_labels=(str(answer_label),),
        answer_value=str(answer_label),
        answer_type="string",
        query_params={
            "extremum_direction": str(direction),
            "extremum_direction_probabilities": dict(direction_probabilities),
            "window_start_index": int(window_start),
            "window_size": int(window_size),
        },
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
    )


def _build_threshold_dataset(
    *,
    query_id: str,
    scene_variant: str,
    labels: Sequence[str],
    values: Sequence[int],
    window_start: int,
    window_size: int,
    target_count: int,
    target_answer_range: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
    query_id_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float],
) -> _Dataset:
    comparison, comparison_probabilities = _choose_string_axis(
        params,
        axis="threshold_comparison",
        supported=SUPPORTED_THRESHOLD_COMPARISONS,
        weights_key="threshold_comparison_weights",
        balance_key="balanced_threshold_comparison_sampling",
        instance_seed=int(instance_seed),
    )
    window_labels = [str(label) for label in labels[int(window_start) : int(window_start) + int(window_size)]]
    window_values = [int(value) for value in values[int(window_start) : int(window_start) + int(window_size)]]
    sorted_values = sorted(window_values)
    if str(comparison) == "greater_than":
        threshold = int(sorted_values[-int(target_count)] - 1)
        evidence_labels = [
            str(label)
            for label, value in zip(window_labels, window_values)
            if int(value) > int(threshold)
        ]
        comparison_phrase = "greater than"
    else:
        threshold = int(sorted_values[int(target_count) - 1] + 1)
        evidence_labels = [
            str(label)
            for label, value in zip(window_labels, window_values)
            if int(value) < int(threshold)
        ]
        comparison_phrase = "less than"
    if len(evidence_labels) != int(target_count):
        raise RuntimeError("threshold construction did not preserve the requested answer")
    return _Dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        labels=tuple(str(label) for label in labels),
        values=tuple(int(value) for value in values),
        window_labels=tuple(window_labels),
        evidence_labels=tuple(str(label) for label in evidence_labels),
        answer_value=int(target_count),
        answer_type="integer",
        query_params={
            "threshold_comparison": str(comparison),
            "threshold_comparison_probabilities": dict(comparison_probabilities),
            "threshold_comparison_phrase": str(comparison_phrase),
            "threshold": int(threshold),
            "target_answer": int(target_count),
            "target_answer_range": [int(target_answer_range[0]), int(target_answer_range[1])],
            "window_start_index": int(window_start),
            "window_size": int(window_size),
        },
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
    )


def _build_callout_dataset(
    *,
    query_id: str,
    scene_variant: str,
    labels: Sequence[str],
    values: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
    query_id_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float],
) -> _Dataset:
    endpoint_side, endpoint_side_probabilities = _choose_string_axis(
        params,
        axis="endpoint_side",
        supported=SUPPORTED_ENDPOINT_SIDES,
        weights_key="endpoint_side_weights",
        balance_key="balanced_endpoint_side_sampling",
        instance_seed=int(instance_seed),
    )
    endpoint_index = 0 if str(endpoint_side) == "first" else len(labels) - 1
    min_gap = max(2, _gen_int(params, "callout_gap_min", 3))
    max_gap = max(int(min_gap), _gen_int(params, "callout_gap_max", 9))
    feasible_indices = [
        int(index)
        for index in range(1, len(labels) - 1)
        if int(index) != int(endpoint_index)
        and int(min_gap) <= abs(int(index) - int(endpoint_index)) <= int(max_gap)
    ]
    if not feasible_indices:
        feasible_indices = [int(index) for index in range(1, len(labels) - 1) if int(index) != int(endpoint_index)]
    anchor_index = balanced_choice_from_values(
        feasible_indices,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.callout_anchor_index",
    )
    answer_value = abs(int(values[int(anchor_index)]) - int(values[int(endpoint_index)]))
    return _Dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        labels=tuple(str(label) for label in labels),
        values=tuple(int(value) for value in values),
        window_labels=(),
        evidence_labels=(str(labels[int(anchor_index)]), str(labels[int(endpoint_index)])),
        answer_value=int(answer_value),
        answer_type="integer",
        query_params={
            "endpoint_side": str(endpoint_side),
            "endpoint_side_probabilities": dict(endpoint_side_probabilities),
            "anchor_label": str(labels[int(anchor_index)]),
            "endpoint_label": str(labels[int(endpoint_index)]),
            "anchor_index": int(anchor_index),
            "endpoint_index": int(endpoint_index),
        },
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
    )


def _build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
    query_id_probabilities = {str(query_id): 1.0}

    mark_count_min, mark_count_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="mark_count_min",
        max_key="mark_count_max",
        fallback_min=_DEFAULTS.mark_count_min,
        fallback_max=_DEFAULTS.mark_count_max,
        context=f"generation defaults for {TASK_ID}",
    )
    mark_count = choose_mark_count(
        [int(value) for value in range(int(mark_count_min), int(mark_count_max) + 1)],
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.mark_count",
    )
    labels = sample_chart_labels(
        count=int(mark_count),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.labels:{str(query_id)}:{int(mark_count)}",
    )
    values = _sample_values(count=int(mark_count), params=params, instance_seed=int(instance_seed))
    if str(query_id) == "event_window_extremum_label":
        window_start, window_size = _choose_window(params, mark_count=int(mark_count), instance_seed=int(instance_seed))
        return _build_extremum_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            labels=labels,
            values=values,
            window_start=int(window_start),
            window_size=int(window_size),
            params=params,
            instance_seed=int(instance_seed),
            query_id_probabilities=query_id_probabilities,
            scene_variant_probabilities=scene_variant_probabilities,
        )
    if str(query_id) == "event_window_threshold_count":
        target_min, target_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="threshold_count_min",
            max_key="threshold_count_max",
            fallback_min=1,
            fallback_max=5,
            context=f"generation defaults for {TASK_ID}",
        )
        target_max = min(int(target_max), max(1, _gen_int(params, "window_size_max", 6) - 1))
        target_min = max(1, min(int(target_min), int(target_max)))
        target_count = balanced_choice_from_values(
            [int(value) for value in range(int(target_min), int(target_max) + 1)],
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold_count_target",
        )
        window_start, window_size = _choose_window(
            params,
            mark_count=int(mark_count),
            instance_seed=int(instance_seed),
            min_window_size=int(target_count) + 1,
        )
        return _build_threshold_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            labels=labels,
            values=values,
            window_start=int(window_start),
            window_size=int(window_size),
            target_count=int(target_count),
            target_answer_range=(int(target_min), int(target_max)),
            params=params,
            instance_seed=int(instance_seed),
            query_id_probabilities=query_id_probabilities,
            scene_variant_probabilities=scene_variant_probabilities,
        )
    if str(query_id) == "callout_endpoint_change_value":
        return _build_callout_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            labels=labels,
            values=values,
            params=params,
            instance_seed=int(instance_seed),
            query_id_probabilities=query_id_probabilities,
            scene_variant_probabilities=scene_variant_probabilities,
        )
    raise ValueError(f"unsupported annotated_series query id: {query_id}")


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, center: Tuple[float, float], font: Any) -> List[float]:
    try:
        raw = draw.textbbox((0, 0), str(text), font=font)
        width = float(raw[2] - raw[0])
        height = float(raw[3] - raw[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        width = float(width)
        height = float(height)
    return round_bbox(
        [
            float(center[0]) - 0.5 * float(width),
            float(center[1]) - 0.5 * float(height),
            float(center[0]) + 0.5 * float(width),
            float(center[1]) + 0.5 * float(height),
        ]
    )


def _fit_context_text(draw: ImageDraw.ImageDraw, text: str, *, font: Any, max_width_px: int) -> str:
    raw = " ".join(str(text).split())
    if not raw:
        return ""
    max_width = max(20, int(max_width_px))
    if draw.textbbox((0, 0), raw, font=font)[2] <= int(max_width):
        return raw
    suffix = "..."
    words = raw.split()
    fitted = ""
    for word in words:
        candidate = f"{fitted} {word}".strip()
        if draw.textbbox((0, 0), f"{candidate}{suffix}", font=font)[2] > int(max_width):
            break
        fitted = candidate
    if fitted:
        return f"{fitted}{suffix}"
    chars: List[str] = []
    for char in raw:
        candidate = "".join(chars) + str(char)
        if draw.textbbox((0, 0), f"{candidate}{suffix}", font=font)[2] > int(max_width):
            break
        chars.append(str(char))
    return f"{''.join(chars).strip()}{suffix}" if chars else suffix


def _draw_light_context_text(
    draw: ImageDraw.ImageDraw,
    *,
    elements: List[ContextTextElement],
    rng: Any,
    role: str,
    manifest_path: str,
    xy: Tuple[float, float],
    anchor: str,
    font: Any,
    font_family: str,
    fill_rgb: RGB,
    max_width_px: int,
    canvas_width: int,
    canvas_height: int,
) -> None:
    selection = sample_context_text(str(manifest_path), rng=rng)
    fitted = _fit_context_text(draw, str(selection.text), font=font, max_width_px=int(max_width_px))
    try:
        bbox_raw = draw.textbbox(tuple(xy), str(fitted), font=font, anchor=str(anchor))
    except TypeError:
        bbox_raw = draw.textbbox(tuple(xy), str(fitted), font=font)
    draw_text_traced(draw,tuple(xy), str(fitted), font=font, fill=tuple(fill_rgb), anchor=str(anchor), role="readout", required=False)
    bbox = (
        max(0, min(int(canvas_width) - 1, int(round(float(bbox_raw[0]))))),
        max(0, min(int(canvas_height) - 1, int(round(float(bbox_raw[1]))))),
        max(1, min(int(canvas_width), int(round(float(bbox_raw[2]))))),
        max(1, min(int(canvas_height), int(round(float(bbox_raw[3]))))),
    )
    elements.append(
        ContextTextElement(
            context_id=f"context_{len(elements):02d}",
            role=str(role),
            text=str(fitted),
            bbox_xyxy=tuple(int(value) for value in bbox),
            manifest_path=str(selection.manifest_path),
            source_ids=tuple(str(source_id) for source_id in selection.source_ids),
            row_index=int(selection.row_index),
            layout_mode="light_context:top_bottom_notes",
            font_family=str(font_family),
        )
    )


def _sample_short_annotation_label(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
    manifest_key: str,
    max_chars_key: str,
    sample_attempts_key: str,
    fallback_text: str,
    fallback_max_chars: int,
    draw: ImageDraw.ImageDraw | None = None,
    font: Any | None = None,
    max_width_px: int | None = None,
) -> Tuple[str, Dict[str, Any]]:
    manifest_path = str(_render_default_value(params, str(manifest_key), "phrases/callout_phrases.txt"))
    max_chars = max(4, int(_render_default_value(params, str(max_chars_key), int(fallback_max_chars))))
    sample_attempts = max(1, int(_render_default_value(params, str(sample_attempts_key), 128)))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{str(namespace)}")
    width_limit = int(max_width_px) if max_width_px is not None else None
    last_short: Tuple[str, Dict[str, Any]] | None = None
    for draw_index in range(int(sample_attempts)):
        selection = sample_context_text(manifest_path, rng=rng)
        candidate = " ".join(str(selection.text).split())
        if not candidate or len(candidate) > int(max_chars):
            continue
        trace = {
            "text": str(candidate),
            "manifest_path": str(selection.manifest_path),
            "row_index": int(selection.row_index),
            "source_ids": [str(source_id) for source_id in selection.source_ids],
            "max_chars": int(max_chars),
            "sample_attempts": int(sample_attempts),
            "selected_after_draws": int(draw_index + 1),
        }
        last_short = (str(candidate), dict(trace))
        if draw is not None and font is not None and width_limit is not None:
            try:
                text_width = int(draw.textbbox((0, 0), str(candidate), font=font)[2])
            except Exception:
                text_width = int(draw.textsize(str(candidate), font=font)[0])
            if int(text_width) > int(width_limit):
                continue
        return str(candidate), dict(trace)
    if last_short is not None:
        text, trace = last_short
        trace = dict(trace)
        trace["selected_after_draws"] = int(sample_attempts)
        trace["width_fallback"] = bool(draw is not None and font is not None and width_limit is not None)
        return str(text), trace
    fallback = str(fallback_text)[: int(max_chars)].strip() or "Note"
    return fallback, {
        "text": str(fallback),
        "manifest_path": str(manifest_path),
        "row_index": -1,
        "source_ids": [],
        "max_chars": int(max_chars),
        "sample_attempts": int(sample_attempts),
        "selected_after_draws": int(sample_attempts),
        "fallback_used": True,
    }


def _rgb_role(information_style_meta: Mapping[str, Any], role: str, fallback: RGB) -> RGB:
    roles = information_style_meta.get("roles_rgb", {})
    if isinstance(roles, Mapping):
        value = roles.get(str(role))
        if isinstance(value, Sequence) and len(value) >= 3:
            return (int(value[0]), int(value[1]), int(value[2]))
    return tuple(int(value) for value in fallback)


def _draw_context_layer(
    image: Image.Image,
    *,
    context_layout: Mapping[str, Any],
    information_style_meta: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[ContextTextElement, ...]:
    if not bool(context_layout.get("enabled", False)):
        return tuple()

    context_params = dict(context_layout.get("context_params", {})) if isinstance(context_layout.get("context_params", {}), Mapping) else {}
    text_rgb = _rgb_role(information_style_meta, "text", (35, 40, 48))
    muted_rgb = _rgb_role(information_style_meta, "muted_text", (90, 96, 108))
    panel_fill_rgb = _rgb_role(information_style_meta, "panel_fill", (255, 255, 255))
    panel_border_rgb = _rgb_role(information_style_meta, "panel_border", (200, 207, 216))
    accent_rgb = _rgb_role(information_style_meta, "accent", (35, 99, 180))

    mode = str(context_layout.get("mode", context_layout.get("layout_mode", "clean")))
    if mode in {"right_sidebar", "bottom_band"}:
        return draw_dashboard_reserved_margin_context(
            image,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.context",
            params=context_params,
            text_rgb=text_rgb,
            muted_text_rgb=muted_rgb,
            panel_fill_rgb=panel_fill_rgb,
            panel_border_rgb=panel_border_rgb,
            accent_rgb=accent_rgb,
            top_reserved_px=int(context_layout.get("top_reserved_px", 64)),
            bottom_reserved_px=int(context_layout.get("bottom_reserved_px", 28)),
            left_margin_px=int(context_layout.get("left_margin_px", 24)),
            right_margin_px=int(context_layout.get("right_margin_px", 24)),
            layout_spec=context_layout,
        )

    draw = ImageDraw.Draw(image)
    font_family = sample_font_family(
        role="context",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.context_light_font",
        params=context_params,
        exclude_tags=("mono", "display", "script", "handwriting"),
        explicit_key="context_text_light_font_family",
        weights_key="context_text_font_family_weights",
    )
    header_font = load_font(14, bold=True, font_family=font_family)
    small_font = load_font(12, bold=False, font_family=font_family)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.context_light")
    width, height = image.size
    elements: List[ContextTextElement] = []
    left_margin = 24
    right_margin = 24
    _draw_light_context_text(
        draw,
        elements=elements,
        rng=rng,
        role="header",
        manifest_path="phrases/headlines.txt",
        xy=(float(left_margin), 12.0),
        anchor="la",
        font=header_font,
        font_family=str(font_family),
        fill_rgb=text_rgb,
        max_width_px=max(180, int(width * 0.34)),
        canvas_width=int(width),
        canvas_height=int(height),
    )
    _draw_light_context_text(
        draw,
        elements=elements,
        rng=rng,
        role="source_note",
        manifest_path="phrases/source_notes.txt",
        xy=(float(width - right_margin), 12.0),
        anchor="ra",
        font=small_font,
        font_family=str(font_family),
        fill_rgb=muted_rgb,
        max_width_px=max(180, int(width * 0.34)),
        canvas_width=int(width),
        canvas_height=int(height),
    )
    _draw_light_context_text(
        draw,
        elements=elements,
        rng=rng,
        role="footer",
        manifest_path="phrases/footers.txt",
        xy=(float(left_margin), float(height - 18)),
        anchor="lm",
        font=small_font,
        font_family=str(font_family),
        fill_rgb=muted_rgb,
        max_width_px=max(220, int(width * 0.45)),
        canvas_width=int(width),
        canvas_height=int(height),
    )
    draw.line((left_margin, 40, width - right_margin, 40), fill=panel_border_rgb, width=1)
    draw.line((left_margin, height - 38, width - right_margin, height - 38), fill=panel_border_rgb, width=1)
    return tuple(elements)


def _trace_by_label(rendered_scene: RenderedChartScene) -> Dict[str, Dict[str, Any]]:
    return {str(item["label"]): dict(item) for item in rendered_scene.mark_traces}


def _window_bbox(rendered_scene: RenderedChartScene, labels: Sequence[str]) -> List[float]:
    traces = _trace_by_label(rendered_scene)
    selected = [traces[str(label)] for label in labels]
    plot_left, plot_top, plot_right, plot_bottom = [float(value) for value in rendered_scene.plot_bbox_px]
    centers = [float(item["mark_center_px"][0]) for item in selected]
    all_centers = sorted(float(item["mark_center_px"][0]) for item in rendered_scene.mark_traces)
    gaps = [all_centers[index + 1] - all_centers[index] for index in range(len(all_centers) - 1)]
    slot_pad = 0.5 * float(min(gaps) if gaps else max(32.0, plot_right - plot_left))
    x0 = max(float(plot_left), min(centers) - slot_pad)
    x1 = min(float(plot_right), max(centers) + slot_pad)
    return round_bbox([x0, plot_top, x1, plot_bottom])


def _mark_evidence_point(mark_trace: Mapping[str, Any]) -> List[float]:
    center = [float(value) for value in mark_trace["mark_center_px"]]
    return [round(float(center[0]), 3), round(float(center[1]), 3)]


def _apply_window_annotation(
    *,
    image: Image.Image,
    rendered_scene: RenderedChartScene,
    labels: Sequence[str],
    evidence_labels: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Annotation:
    window = _window_bbox(rendered_scene, labels)
    fill_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "annotation_fill_rgb",
        (247, 180, 68),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    outline_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "annotation_outline_rgb",
        (174, 91, 28),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    alpha = max(24, min(96, int(params.get("annotation_fill_alpha", group_default(_RENDER_DEFAULTS, "annotation_fill_alpha", 46)))))
    outline_width = max(2, int(params.get("annotation_outline_width_px", group_default(_RENDER_DEFAULTS, "annotation_outline_width_px", 3))))
    corner_radius = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "annotation_corner_radius_px",
        0,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )

    base = image.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    if int(corner_radius) > 0:
        overlay_draw.rounded_rectangle(
            tuple(float(v) for v in window),
            radius=int(corner_radius),
            fill=(*fill_rgb, int(alpha)),
            outline=(*outline_rgb, 210),
            width=int(outline_width),
        )
    else:
        overlay_draw.rectangle(
            tuple(float(v) for v in window),
            fill=(*fill_rgb, int(alpha)),
            outline=(*outline_rgb, 210),
            width=int(outline_width),
        )
    annotated = Image.alpha_composite(base, overlay).convert("RGB")
    draw = ImageDraw.Draw(annotated)

    font = load_font(int(params.get("annotation_label_font_size_px", group_default(_RENDER_DEFAULTS, "annotation_label_font_size_px", 18))), bold=True)
    label_text, label_source_trace = _sample_short_annotation_label(
        params,
        instance_seed=int(instance_seed),
        namespace="window_label",
        manifest_key="annotation_label_manifest_path",
        max_chars_key="annotation_label_max_chars",
        sample_attempts_key="annotation_label_sample_attempts",
        fallback_text="Window",
        fallback_max_chars=18,
    )
    try:
        raw_bbox = draw.textbbox((0, 0), str(label_text), font=font)
        text_width = float(raw_bbox[2] - raw_bbox[0])
        text_height = float(raw_bbox[3] - raw_bbox[1])
    except Exception:
        text_width, text_height = draw.textsize(str(label_text), font=font)
        text_width = float(text_width)
        text_height = float(text_height)
    pad_x = 10.0
    pad_y = 5.0
    box_width = float(text_width) + 2.0 * pad_x
    box_height = float(text_height) + 2.0 * pad_y
    label_position = _render_choice(
        params,
        key="annotation_label_position",
        fallback="top_left",
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    if str(label_position) == "top_right":
        label_left = float(window[2]) - 8.0 - float(box_width)
        label_top = float(window[1]) + 8.0
    elif str(label_position) == "bottom_left":
        label_left = float(window[0]) + 8.0
        label_top = float(window[3]) - 8.0 - float(box_height)
    else:
        label_left = float(window[0]) + 8.0
        label_top = float(window[1]) + 8.0
    label_left = max(4.0, min(float(label_left), float(image.size[0]) - float(box_width) - 4.0))
    label_top = max(4.0, min(float(label_top), float(image.size[1]) - float(box_height) - 4.0))
    label_box = [label_left, label_top, label_left + box_width, label_top + box_height]
    label_radius = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "annotation_label_radius_px",
        6,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    draw.rounded_rectangle(tuple(label_box), radius=int(label_radius), fill=(255, 255, 255), outline=outline_rgb, width=2)
    draw_text_centered(
        draw,
        text=str(label_text),
        center=(0.5 * (label_box[0] + label_box[2]), 0.5 * (label_box[1] + label_box[3])),
        font=font,
        fill=outline_rgb,
        stroke_fill=(255, 255, 255),
        stroke_width=0,
    )
    label_bbox = round_bbox(label_box)
    traces = _trace_by_label(rendered_scene)
    evidence_points = [_mark_evidence_point(traces[str(label)]) for label in evidence_labels]
    entities = (
        {
            "entity_id": "annotation_window",
            "entity_type": "annotation_window",
            "attrs": {
                "bbox_px": list(window),
                "label": str(label_text),
                "label_bbox_px": list(label_bbox),
                "covered_labels": [str(label) for label in labels],
                "label_source": dict(label_source_trace),
                "annotation_fill_rgb": list(fill_rgb),
                "annotation_outline_rgb": list(outline_rgb),
                "annotation_corner_radius_px": int(corner_radius),
                "annotation_label_position": str(label_position),
                "annotation_label_radius_px": int(label_radius),
            },
        },
    )
    return _Annotation(
        image=annotated,
        entities=tuple(dict(item) for item in entities),
        point_set=tuple(list(item) for item in evidence_points),
        annotation_bboxes={
            "annotation_window": list(window),
            "annotation_label": list(label_bbox),
        },
    )


def _apply_callout_annotation(
    *,
    image: Image.Image,
    rendered_scene: RenderedChartScene,
    anchor_label: str,
    endpoint_label: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Annotation:
    traces = _trace_by_label(rendered_scene)
    anchor_trace = traces[str(anchor_label)]
    endpoint_trace = traces[str(endpoint_label)]
    anchor_center = [float(value) for value in anchor_trace["mark_center_px"]]
    plot_left, plot_top, plot_right, _plot_bottom = [float(value) for value in rendered_scene.plot_bbox_px]
    box_width = float(params.get("callout_box_width_px", group_default(_RENDER_DEFAULTS, "callout_box_width_px", 138)))
    box_height = float(params.get("callout_box_height_px", group_default(_RENDER_DEFAULTS, "callout_box_height_px", 48)))
    gap = 18.0
    if float(anchor_center[0]) < 0.5 * (float(plot_left) + float(plot_right)):
        box_left = float(plot_right) - float(box_width) - float(gap)
    else:
        box_left = float(plot_left) + float(gap)
    box_top = float(plot_top) + float(gap)
    callout_box = round_bbox([box_left, box_top, box_left + box_width, box_top + box_height])
    callout_center = (0.5 * (callout_box[0] + callout_box[2]), 0.5 * (callout_box[1] + callout_box[3]))

    fill_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "callout_fill_rgb",
        (255, 255, 255),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    outline_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "callout_outline_rgb",
        (48, 98, 170),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    text_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "callout_text_rgb",
        (38, 42, 50),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    corner_radius = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "callout_corner_radius_px",
        8,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    arrow_width = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "callout_arrow_width_px",
        3,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    annotated = image.convert("RGB")
    draw = ImageDraw.Draw(annotated)
    draw.rounded_rectangle(
        tuple(float(value) for value in callout_box),
        radius=int(corner_radius),
        fill=fill_rgb,
        outline=outline_rgb,
        width=max(2, int(arrow_width)),
    )
    font = load_font(int(params.get("callout_font_size_px", group_default(_RENDER_DEFAULTS, "callout_font_size_px", 20))), bold=True)
    callout_text, callout_source_trace = _sample_short_annotation_label(
        params,
        instance_seed=int(instance_seed),
        namespace="callout_label",
        manifest_key="callout_label_manifest_path",
        max_chars_key="callout_label_max_chars",
        sample_attempts_key="callout_label_sample_attempts",
        fallback_text="Callout",
        fallback_max_chars=14,
        draw=draw,
        font=font,
        max_width_px=max(48, int(box_width - 18)),
    )
    draw_text_centered(
        draw,
        text=str(callout_text),
        center=callout_center,
        font=font,
        fill=text_rgb,
        stroke_fill=(255, 255, 255),
        stroke_width=0,
    )
    line_start = (
        float(callout_box[0] if float(anchor_center[0]) < float(callout_center[0]) else callout_box[2]),
        float(callout_center[1]),
    )
    line_end = (float(anchor_center[0]), float(anchor_center[1]))
    draw.line((line_start, line_end), fill=outline_rgb, width=max(2, int(arrow_width)))
    arrow_r = float(max(5, int(arrow_width) + 3))
    draw.ellipse(
        (
            float(anchor_center[0] - arrow_r),
            float(anchor_center[1] - arrow_r),
            float(anchor_center[0] + arrow_r),
            float(anchor_center[1] + arrow_r),
        ),
        fill=outline_rgb,
        outline=(255, 255, 255),
        width=2,
    )
    arrow_bbox = bbox_union(
        [
            [float(line_start[0]), float(line_start[1]), float(line_end[0]), float(line_end[1])],
            [float(anchor_center[0] - arrow_r), float(anchor_center[1] - arrow_r), float(anchor_center[0] + arrow_r), float(anchor_center[1] + arrow_r)],
        ],
        padding=3.0,
    )
    label_bbox = _text_bbox(draw, str(callout_text), callout_center, font)
    evidence_points = [
        _mark_evidence_point(anchor_trace),
        _mark_evidence_point(endpoint_trace),
    ]
    entities = (
        {
            "entity_id": "annotation_callout",
            "entity_type": "annotation_callout",
            "attrs": {
                "bbox_px": list(callout_box),
                "label": str(callout_text),
                "label_bbox_px": list(label_bbox),
                "arrow_bbox_px": list(arrow_bbox),
                "anchor_label": str(anchor_label),
                "endpoint_label": str(endpoint_label),
                "label_source": dict(callout_source_trace),
                "callout_fill_rgb": list(fill_rgb),
                "callout_outline_rgb": list(outline_rgb),
                "callout_corner_radius_px": int(corner_radius),
                "callout_arrow_width_px": int(arrow_width),
            },
        },
    )
    return _Annotation(
        image=annotated,
        entities=tuple(dict(item) for item in entities),
        point_set=tuple(list(item) for item in evidence_points),
        annotation_bboxes={
            "annotation_callout": list(callout_box),
            "annotation_callout_label": list(label_bbox),
            "annotation_callout_arrow": list(arrow_bbox),
        },
    )


def _apply_annotation(
    *,
    image: Image.Image,
    rendered_scene: RenderedChartScene,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Annotation:
    if dataset.query_id in {"event_window_extremum_label", "event_window_threshold_count"}:
        return _apply_window_annotation(
            image=image,
            rendered_scene=rendered_scene,
            labels=dataset.window_labels,
            evidence_labels=dataset.evidence_labels,
            params=params,
            instance_seed=int(instance_seed),
        )
    return _apply_callout_annotation(
        image=image,
        rendered_scene=rendered_scene,
        anchor_label=str(dataset.query_params["anchor_label"]),
        endpoint_label=str(dataset.query_params["endpoint_label"]),
        params=params,
        instance_seed=int(instance_seed),
    )


def _prompt_object_description(scene_variant: str, prompt_defaults: Mapping[str, Any]) -> str:
    key = f"object_description_{str(scene_variant)}"
    return str(prompt_defaults[key])


class ChartsAnnotatedSeriesBaseTask:
    """Shared implementation for annotated single-series chart public tasks."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "annotated_series"
    query_id = ""
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id = str(params.get("query_id", self.query_id) or self.query_id)
        if query_id not in set(SUPPORTED_QUERY_IDS):
            raise ValueError(f"unsupported annotated_series query id: {query_id}")
        if self.query_id and query_id != self.query_id:
            raise ValueError(f"{self.task_id} only supports query_id={self.query_id}")

        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        mark_style = resolve_chart_mark_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            scene_variant=str(dataset.scene_variant),
            mark_count=len(dataset.labels),
        )
        marks = build_chart_mark_specs(
            labels=dataset.labels,
            values=dataset.values,
            scene_variant=str(dataset.scene_variant),
            mark_style=mark_style,
        )
        context_layout = _resolve_context_layout(
            params=params,
            instance_seed=int(instance_seed),
            canvas_width=int(_render_default_value(params, "canvas_width", _DEFAULTS.canvas_width)),
            canvas_height=int(_render_default_value(params, "canvas_height", _DEFAULTS.canvas_height)),
        )
        render_input_params = _apply_context_margin_overrides(
            {**dict(params), **mark_style},
            context_layout=context_layout,
        )
        render_params = resolve_chart_render_params_for_task(
            render_input_params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params, background, background_meta, information_style_meta = prepare_chart_information_scene(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=self.task_group,
            render_params=render_params,
        )
        chart_font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
        annotation_font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.annotation_font",
            params=params,
            explicit_key="annotation_font_family",
            weights_key="annotation_font_family_weights",
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered_scene = render_labeled_chart_scene(
                background,
                scene_variant=str(dataset.scene_variant),
                marks=marks,
                render_params=render_params,
                instance_seed=int(instance_seed),
            )
        with temporary_default_font_family(str(annotation_font_family)):
            annotation = _apply_annotation(
                image=rendered_scene.image,
                rendered_scene=rendered_scene,
                dataset=dataset,
                params=params,
                instance_seed=int(instance_seed),
            )
        context_elements = _draw_context_layer(
            annotation.image,
            context_layout=context_layout,
            information_style_meta=information_style_meta,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            annotation.image,
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
                "answer_hint_label",
                "answer_hint_count",
                "answer_hint_value",
                "object_description_line",
                "object_description_bar",
                "object_description_area",
                "object_description_dot_plot",
                "object_description_lollipop",
                "evidence_hint_event_window_extremum_label",
                "evidence_hint_event_window_threshold_count",
                "evidence_hint_callout_endpoint_change_value",
                "json_example_event_window_extremum_label",
                "json_example_event_window_threshold_count",
                "json_example_callout_endpoint_change_value",
                "json_example_answer_only_event_window_extremum_label",
                "json_example_answer_only_event_window_threshold_count",
                "json_example_answer_only_callout_endpoint_change_value",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint = (
            prompt_defaults["answer_hint_label"]
            if dataset.answer_type == "string"
            else prompt_defaults["answer_hint_count"]
            if str(dataset.query_id) == "event_window_threshold_count"
            else prompt_defaults["answer_hint_value"]
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": _prompt_object_description(str(dataset.scene_variant), prompt_defaults),
                "extremum_direction": str(dataset.query_params.get("extremum_direction", "")),
                "threshold_comparison_phrase": str(dataset.query_params.get("threshold_comparison_phrase", "")),
                "threshold": str(dataset.query_params.get("threshold", "")),
                "endpoint_label": str(dataset.query_params.get("endpoint_label", "")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{dataset.query_id}"]),
                "answer_hint": str(answer_hint),
                "json_example": str(prompt_defaults[f"json_example_{dataset.query_id}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{dataset.query_id}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        values_by_label = {
            str(mark["label"]): int(mark["value"])
            for mark in rendered_scene.mark_traces
        }
        mark_bbox_by_label = {
            str(mark["label"]): list(mark["mark_bbox_px"])
            for mark in rendered_scene.mark_traces
        }
        mark_center_by_label = {
            str(mark["label"]): list(mark["mark_center_px"])
            for mark in rendered_scene.mark_traces
        }
        answer_gt = TypedValue(type=str(dataset.answer_type), value=dataset.answer_value)
        evidence_points = [list(item) for item in annotation.point_set]
        if str(dataset.query_id) == "callout_endpoint_change_value":
            keyed_points = {
                "callout_mark": list(evidence_points[0]),
                "endpoint_mark": list(evidence_points[1]),
            }
            evidence_gt = TypedValue(type="keyed_point_map", value=dict(keyed_points))
            witness_symbolic = {
                "type": "object_key_map",
                "keys": {
                    "callout_mark": str(dataset.query_params["anchor_label"]),
                    "endpoint_mark": str(dataset.query_params["endpoint_label"]),
                },
            }
            projected_evidence = {
                "type": "keyed_point_map",
                "keyed_point_map": dict(keyed_points),
                "pixel_keyed_point_map": dict(keyed_points),
            }
        else:
            evidence_gt = TypedValue(type="point_set", value=evidence_points)
            witness_symbolic = {
                "type": "point_set",
                "count": len(evidence_points),
            }
            projected_evidence = {
                "type": "point_set",
                "point_set": list(evidence_points),
                "pixel_point_set": list(evidence_points),
            }
        context_element_traces = [element.to_trace() for element in context_elements]
        context_entities = [
            {
                "entity_id": str(element["context_id"]),
                "entity_type": "non_answer_context_text",
                "attrs": dict(element),
            }
            for element in context_element_traces
        ]

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(dataset.scene_variant)}_annotated_series",
                "entities": [dict(entity) for entity in rendered_scene.entities]
                + [dict(entity) for entity in annotation.entities]
                + [dict(entity) for entity in context_entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "annotation_kind": "callout" if str(dataset.query_id) == "callout_endpoint_change_value" else "event_window",
                    "evidence_labels": [str(label) for label in dataset.evidence_labels],
                    "window_labels": [str(label) for label in dataset.window_labels],
                    **dict(dataset.query_params),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(dataset.query_id),
                    "query_id_probabilities": dict(dataset.query_id_probabilities),
                    "scene_variant": str(dataset.scene_variant),
                    "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
                    "mark_count": int(len(dataset.labels)),
                    "mark_count_range": [
                        _gen_int(params, "mark_count_min", _DEFAULTS.mark_count_min),
                        _gen_int(params, "mark_count_max", _DEFAULTS.mark_count_max),
                    ],
                    **dict(dataset.query_params),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "scene_variant": str(dataset.scene_variant),
                "information_scene_style": dict(information_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(render_params.layout_jitter_meta or {}),
                "context_text_layer": context_text_layer_metadata(
                    context_elements,
                    enabled=bool(context_layout.get("enabled", False)),
                    layout_mode=f"{context_layout.get('layout_mode', context_layout.get('mode', 'clean'))}:{context_layout.get('placement', 'none')}",
                    layout_spec={str(key): value for key, value in dict(context_layout).items() if str(key) != "context_params"},
                ),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "tick_font_size_px": int(render_params.tick_font_size_px),
                    "label_stroke_width_px": int(render_params.label_stroke_width_px),
                    "font_asset_version": str(font_asset_version()),
                    "chart_font_family": str(chart_font_family),
                    "annotation_font_family": str(annotation_font_family),
                    "chart_font_exclude_tags": [],
                    "annotation_font_exclude_tags": [],
                    "context_font_exclude_tags": ["mono", "display", "script", "handwriting"],
                },
                "axis_style": {
                    "axis_line_width_px": int(render_params.axis_line_width_px),
                    "grid_line_width_px": int(render_params.grid_line_width_px),
                    "tick_length_px": int(render_params.tick_length_px),
                },
                "mark_style": {
                    "sampling_policy": str(mark_style["sampling_policy"]),
                    "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                    **{
                        str(key): value
                        for key, value in mark_style.items()
                        if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                    },
                },
                "annotation_bboxes": dict(annotation.annotation_bboxes),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "label_centers_px": dict(label_centers),
                "mark_bbox_by_label": dict(mark_bbox_by_label),
                "mark_center_by_label": dict(mark_center_by_label),
                "annotation_bboxes": dict(annotation.annotation_bboxes),
            },
            "execution_trace": {
                "query_id": str(dataset.query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer_value": dataset.answer_value,
                "evidence_labels": [str(label) for label in dataset.evidence_labels],
                "labels": [str(label) for label in dataset.labels],
                "values": [int(value) for value in dataset.values],
                "values_by_label": dict(values_by_label),
                "window_labels": [str(label) for label in dataset.window_labels],
                "mark_count": int(len(dataset.labels)),
                "mark_count_range": [
                    _gen_int(params, "mark_count_min", _DEFAULTS.mark_count_min),
                    _gen_int(params, "mark_count_max", _DEFAULTS.mark_count_max),
                ],
                "query_id_probabilities": dict(dataset.query_id_probabilities),
                "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
                "question_format": "string_open" if dataset.answer_type == "string" else "numeric_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                },
                **dict(dataset.query_params),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_evidence": dict(projected_evidence),
        }

        mark_count_bounds = [
            _gen_int(params, "mark_count_min", _DEFAULTS.mark_count_min),
            _gen_int(params, "mark_count_max", _DEFAULTS.mark_count_max),
        ]
        window_bounds = [
            _gen_int(params, "window_size_min", 3),
            _gen_int(params, "window_size_max", 6),
        ]
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(len(dataset.labels)), mark_count_bounds),
                "reasoning_load": float(_REASONING_LOADS[str(dataset.query_id)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(dataset.scene_variant)]),
                "annotation_scope": (
                    normalize_int_with_bounds(int(len(dataset.window_labels)), window_bounds)
                    if dataset.window_labels
                    else clamp_unit_interval(
                        abs(int(dataset.query_params.get("anchor_index", 0)) - int(dataset.query_params.get("endpoint_index", 0))) / max(1.0, float(len(dataset.labels) - 1))
                    )
                ),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsAnnotatedSeriesEventWindowExtremumLabelTask(ChartsAnnotatedSeriesBaseTask):
    """Identify an extremum label inside the highlighted event window."""

    task_id = "task_charts__annotated_series__event_window_extremum_label"
    query_id = "event_window_extremum_label"


@register_task
class ChartsAnnotatedSeriesEventWindowThresholdCountTask(ChartsAnnotatedSeriesBaseTask):
    """Count highlighted-window marks satisfying a threshold."""

    task_id = "task_charts__annotated_series__event_window_threshold_count"
    query_id = "event_window_threshold_count"


@register_task
class ChartsAnnotatedSeriesCalloutEndpointChangeValueTask(ChartsAnnotatedSeriesBaseTask):
    """Compute endpoint change from a callout-anchored mark."""

    task_id = "task_charts__annotated_series__callout_endpoint_change_value"
    query_id = "callout_endpoint_change_value"


__all__ = [
    "ChartsAnnotatedSeriesBaseTask",
    "ChartsAnnotatedSeriesCalloutEndpointChangeValueTask",
    "ChartsAnnotatedSeriesEventWindowExtremumLabelTask",
    "ChartsAnnotatedSeriesEventWindowThresholdCountTask",
]
