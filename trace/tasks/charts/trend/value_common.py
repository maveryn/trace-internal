"""Shared constants and query helpers for single-series trend chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ..shared.chart_scene import ChartMarkSpec
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.labeled_chart_common import (
    LabeledChartDefaults,
    build_chart_mark_specs,
    resolve_chart_axis_variant,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults

QueryVariant = str
SceneVariant = str

TASK_ID = "charts_trend_value_base"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "turning_point_count",
    "longest_monotone_streak",
    "endpoint_change_value",
    "interval_rate_value",
    "threshold_crossing",
)
_SUPPORTED_TURNING_POINT_TYPES: Tuple[str, ...] = (
    "peak",
    "trough",
)
_SUPPORTED_STREAK_DIRECTIONS: Tuple[str, ...] = (
    "increasing",
    "decreasing",
)
_SUPPORTED_ENDPOINT_CHANGE_KINDS: Tuple[str, ...] = (
    "absolute",
    "signed",
    "percent",
)
_SUPPORTED_CROSSING_DIRECTIONS: Tuple[str, ...] = (
    "above",
    "below",
)
_SUPPORTED_CROSSING_MODES: Tuple[str, ...] = (
    "observed",
    "linear_projection",
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "area",
    "bar",
    "horizontal_bar",
    "line",
    "dot_plot",
    "lollipop",
)
_SUPPORTED_THRESHOLD_SCENE_VARIANTS: Tuple[str, ...] = (
    "area",
    "bar",
    "line",
    "dot_plot",
    "lollipop",
)

_DEFAULTS = LabeledChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "trend")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="trend")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="trend", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_STRUCTURE_REASONING_LOADS: Dict[str, float] = {
    "turning_point_count": 0.0,
    "longest_monotone_streak": 0.55,
}
_ENDPOINT_CHANGE_REASONING_LOADS: Dict[str, float] = {
    "absolute": 0.35,
    "signed": 0.45,
    "percent": 1.0,
}
_INTERVAL_RATE_REASONING_LOAD = 0.75
_THRESHOLD_REASONING_LOADS: Dict[str, float] = {
    "observed": 0.45,
    "linear_projection": 1.0,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "bar": 0.0,
    "horizontal_bar": 0.10,
    "dot_plot": 0.20,
    "lollipop": 0.30,
    "line": 0.38,
    "area": 0.46,
}
_BRANCH_GENERATION_KEYS: Tuple[str, ...] = (
    "mark_count_min",
    "mark_count_max",
    "value_min",
    "value_max",
    "value_hard_max",
    "value_window_enabled",
    "value_window_span_min",
    "value_window_span_max",
)
_THRESHOLD_GENERATION_KEYS: Tuple[str, ...] = (
    "mark_count_min",
    "mark_count_max",
    "value_min",
    "value_max",
    "value_hard_max",
    "value_window_enabled",
    "value_window_span_min",
    "value_window_span_max",
    "threshold_edge_margin",
    "threshold_min",
    "threshold_max",
    "crossing_index_min",
    "crossing_index_max",
    "observed_count_min",
    "observed_count_max",
    "projection_count_min",
    "projection_count_max",
    "projection_step_min",
    "projection_step_max",
)


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the public trend-value variant."""

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


def _uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> bool:
    """Return true when `_sample_cursor` is driving the default query-id cycle."""

    if params.get("query_id") is not None or params.get("query_id_weights") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", _GEN_DEFAULTS.get("balanced_query_id_sampling", True)))
    if not bool(enabled):
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(_SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_params_for_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-public-variant occurrence index for subparameter and support cycling."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_QUERY_IDS))
    return support_params


def _branch_generation_params(params: Mapping[str, Any], *, branch: str) -> Dict[str, Any]:
    """Apply branch-prefixed generation defaults before calling the shared builder."""

    branch_params = dict(params)
    prefix = str(branch).strip()
    for key in _BRANCH_GENERATION_KEYS:
        prefixed_key = f"{prefix}_{key}"
        if prefixed_key in params:
            branch_params[key] = params[prefixed_key]
        elif prefixed_key in _GEN_DEFAULTS:
            branch_params[key] = _GEN_DEFAULTS[prefixed_key]
    return branch_params


def _threshold_generation_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Apply threshold-prefixed generation defaults for the merged crossing variants."""

    threshold_params = dict(params)
    for key in _THRESHOLD_GENERATION_KEYS:
        if key in params:
            continue
        prefixed_key = f"threshold_{key}"
        if prefixed_key in params:
            threshold_params[key] = params[prefixed_key]
        elif prefixed_key in _GEN_DEFAULTS:
            threshold_params[key] = _GEN_DEFAULTS[prefixed_key]
    return threshold_params


def _threshold_support_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Use a per-crossing-direction index for threshold support cycling."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if params.get("crossing_direction") is not None or params.get("crossing_direction_weights") is not None:
        return support_params
    enabled = bool(params.get("balanced_crossing_direction_sampling", _GEN_DEFAULTS.get("balanced_crossing_direction_sampling", True)))
    if not bool(enabled):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_CROSSING_DIRECTIONS))
    return support_params


def _threshold_mode_support_params(
    params: Mapping[str, Any],
    *,
    crossing_mode_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-crossing-mode index before cycling crossing directions."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if params.get("crossing_mode") is not None or params.get("crossing_mode_weights") is not None:
        return support_params
    enabled = bool(params.get("balanced_crossing_mode_sampling", _GEN_DEFAULTS.get("balanced_crossing_mode_sampling", True)))
    if not bool(enabled):
        return support_params
    positives = [float(value) for value in crossing_mode_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(_SUPPORTED_CROSSING_MODES):
        return support_params
    if max(positives) - min(positives) > 1e-9:
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_CROSSING_MODES))
    return support_params


def _resolve_turning_point_type(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve peak/trough for the merged turning-point variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TURNING_POINT_TYPES,
        task_id=TASK_ID,
        explicit_key="turning_point_type",
        weights_key="turning_point_type_weights",
        balance_flag_key="balanced_turning_point_type_sampling",
        axis_namespace="turning_point_type",
    )


def _resolve_streak_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve increasing/decreasing for the merged monotone-streak variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_STREAK_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="streak_direction",
        weights_key="streak_direction_weights",
        balance_flag_key="balanced_streak_direction_sampling",
        axis_namespace="streak_direction",
    )


def _resolve_endpoint_change_kind(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve absolute/signed/percent for the merged endpoint-change variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_ENDPOINT_CHANGE_KINDS,
        task_id=TASK_ID,
        explicit_key="endpoint_change_kind",
        weights_key="endpoint_change_kind_weights",
        balance_flag_key="balanced_endpoint_change_kind_sampling",
        axis_namespace="endpoint_change_kind",
    )


def _resolve_crossing_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve above/below as a query parameter inside threshold-crossing variants."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_CROSSING_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="crossing_direction",
        weights_key="crossing_direction_weights",
        balance_flag_key="balanced_crossing_direction_sampling",
        axis_namespace="crossing_direction",
    )


def _resolve_crossing_mode(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve observed versus projected threshold crossing inside the public crossing variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_CROSSING_MODES,
        task_id=TASK_ID,
        explicit_key="crossing_mode",
        weights_key="crossing_mode_weights",
        balance_flag_key="balanced_crossing_mode_sampling",
        axis_namespace="crossing_mode",
    )


def _internal_structure_variant(
    query_id: str,
    *,
    turning_point_type: str | None,
    streak_direction: str | None,
) -> str:
    """Map the public structure variant plus query parameter to the construction variant."""

    if str(query_id) == "turning_point_count":
        if str(turning_point_type) == "peak":
            return "peak_count"
        if str(turning_point_type) == "trough":
            return "trough_count"
        raise ValueError(f"unsupported turning_point_type: {turning_point_type}")
    if str(query_id) == "longest_monotone_streak":
        if str(streak_direction) == "increasing":
            return "longest_increasing_streak"
        if str(streak_direction) == "decreasing":
            return "longest_decreasing_streak"
        raise ValueError(f"unsupported streak_direction: {streak_direction}")
    raise ValueError(f"unsupported structure query_id: {query_id}")


def _internal_interval_variant(query_id: str, *, endpoint_change_kind: str | None) -> str:
    """Map the merged interval public variants to the construction variant."""

    if str(query_id) == "endpoint_change_value":
        if str(endpoint_change_kind) == "absolute":
            return "absolute_change_between_labels"
        if str(endpoint_change_kind) == "signed":
            return "signed_change_between_labels"
        if str(endpoint_change_kind) == "percent":
            return "percent_change_between_labels"
        raise ValueError(f"unsupported endpoint_change_kind: {endpoint_change_kind}")
    if str(query_id) == "interval_rate_value":
        return "average_rate_over_interval"
    raise ValueError(f"unsupported interval query_id: {query_id}")


def _internal_crossing_variant(crossing_mode: str, crossing_direction: str) -> str:
    """Map a public crossing family plus direction to the construction variant."""

    if str(crossing_mode) == "observed":
        if str(crossing_direction) == "above":
            return "first_crosses_above_threshold"
        if str(crossing_direction) == "below":
            return "first_crosses_below_threshold"
    if str(crossing_mode) == "linear_projection":
        if str(crossing_direction) == "above":
            return "linear_projection_crosses_above"
        if str(crossing_direction) == "below":
            return "linear_projection_crosses_below"
    raise ValueError(f"unsupported crossing mode/direction: {crossing_mode}/{crossing_direction}")


def _turning_point_prompt_slots(turning_point_type: str | None) -> Dict[str, str]:
    """Return prompt slots for one turning-point type."""

    if turning_point_type is None:
        return {
            "turning_point_type": "",
            "turning_point_plural": "",
            "turning_point_comparison": "",
        }
    if str(turning_point_type) == "peak":
        return {
            "turning_point_type": "peak",
            "turning_point_plural": "peaks",
            "turning_point_comparison": "higher than",
        }
    if str(turning_point_type) == "trough":
        return {
            "turning_point_type": "trough",
            "turning_point_plural": "troughs",
            "turning_point_comparison": "lower than",
        }
    raise ValueError(f"unsupported turning_point_type: {turning_point_type}")


def _streak_prompt_slots(streak_direction: str | None) -> Dict[str, str]:
    """Return prompt slots for one monotone-streak direction."""

    if streak_direction is None:
        return {"streak_direction": "", "streak_step_verb": ""}
    if str(streak_direction) == "increasing":
        return {"streak_direction": "increasing", "streak_step_verb": "increases"}
    if str(streak_direction) == "decreasing":
        return {"streak_direction": "decreasing", "streak_step_verb": "decreases"}
    raise ValueError(f"unsupported streak_direction: {streak_direction}")


def _endpoint_change_prompt_slots(endpoint_change_kind: str | None) -> Dict[str, str]:
    """Return prompt slots for the endpoint-change subkind."""

    if endpoint_change_kind is None:
        return {"endpoint_change_kind": "", "endpoint_change_instruction": ""}
    if str(endpoint_change_kind) == "absolute":
        return {
            "endpoint_change_kind": "absolute",
            "endpoint_change_instruction": "absolute change in value",
        }
    if str(endpoint_change_kind) == "signed":
        return {
            "endpoint_change_kind": "signed",
            "endpoint_change_instruction": "signed change in value, keeping decreases negative",
        }
    if str(endpoint_change_kind) == "percent":
        return {
            "endpoint_change_kind": "percent",
            "endpoint_change_instruction": "integer percentage change using the start label's value as the base, omitting the percent sign",
        }
    raise ValueError(f"unsupported endpoint_change_kind: {endpoint_change_kind}")


def _crossing_prompt_slots(crossing_direction: str | None) -> Dict[str, str]:
    """Return prompt wording for one threshold-crossing direction."""

    if crossing_direction is None:
        return {"crossing_direction": "", "comparison_phrase": "", "crossing_direction_verb": ""}
    if str(crossing_direction) == "above":
        return {
            "crossing_direction": "above",
            "comparison_phrase": "greater than",
            "crossing_direction_verb": "rises above",
        }
    if str(crossing_direction) == "below":
        return {
            "crossing_direction": "below",
            "comparison_phrase": "less than",
            "crossing_direction_verb": "falls below",
        }
    raise ValueError(f"unsupported crossing_direction: {crossing_direction}")


def _crossing_mode_prompt_slots(crossing_mode: str | None) -> Dict[str, str]:
    """Return prompt wording for observed versus projected threshold crossing."""

    if crossing_mode is None:
        return {"crossing_mode_instruction": ""}
    if str(crossing_mode) == "observed":
        return {"crossing_mode_instruction": "Follow the plotted labels in displayed order."}
    if str(crossing_mode) == "linear_projection":
        return {
            "crossing_mode_instruction": (
                "The plotted labels form one linear series and the final labels are empty future slots; "
                "extend the same step into those future labels."
            )
        }
    raise ValueError(f"unsupported crossing_mode: {crossing_mode}")


def _build_threshold_mark_specs(
    *,
    labels: Tuple[str, ...],
    values: Tuple[int, ...],
    scene_variant: str,
    mark_style: Mapping[str, Any],
    future_labels: Tuple[str, ...],
) -> Tuple[ChartMarkSpec, ...]:
    """Build marks, hiding future extrapolated y-values from the rendered chart."""

    base_marks = build_chart_mark_specs(
        labels=labels,
        values=values,
        scene_variant=str(scene_variant),
        mark_style=mark_style,
    )
    future = {str(label) for label in future_labels}
    if not future:
        return tuple(base_marks)
    out: list[ChartMarkSpec] = []
    for mark in base_marks:
        if str(mark.label) not in future:
            out.append(mark)
            continue
        out.append(
            ChartMarkSpec(
                label=str(mark.label),
                value=int(mark.value),
                fill_rgb=mark.fill_rgb,
                outline_rgb=mark.outline_rgb,
                visible=False,
            )
        )
    return tuple(out)


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    query_id: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the ordered chart scene variant."""

    supported_variants = (
        _SUPPORTED_THRESHOLD_SCENE_VARIANTS
        if str(query_id) == "threshold_crossing"
        else _SUPPORTED_SCENE_VARIANTS
    )
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=supported_variants,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )
