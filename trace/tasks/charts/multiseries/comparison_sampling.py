"""Sampling and query-axis helpers for multiseries comparison tasks."""

from __future__ import annotations

import random
from typing import Any, Dict, Mapping, Tuple

from ..shared.label_assets import resolve_chart_category_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.multiseries_chart_common import SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS
from .comparison_common import (
    TASK_ID,
    _CATEGORY_TOTAL_QUERY_ID,
    _CHANGE_QUERY_ID,
    _CONDITIONAL_AGGREGATE_QUERY_ID,
    _CONDITIONAL_EXTREMUM_QUERY_ID,
    _CONDITIONAL_GAP_AGGREGATE_KIND_TO_INTERNAL,
    _CONDITIONAL_QUERY_IDS,
    _EQUALITY_QUERY_ID,
    _FAMILY_RANGE_KEYS,
    _GEN_DEFAULTS,
    _PAIRWISE_QUERY_ID,
    _RATIO_QUERY_ID,
    _SERIES_RANK_QUERY_ID,
    _SUPPORTED_CHANGE_DIRECTIONS,
    _SUPPORTED_CHANGE_MEASURES,
    _SUPPORTED_COMPARISONS,
    _SUPPORTED_CONDITIONAL_GAP_AGGREGATE_KINDS,
    _SUPPORTED_EXTREMUM_DIRECTIONS,
    _SUPPORTED_QUERY_IDS,
    _SUPPORTED_RATIO_MEASURES,
)


def _variant_family(query_id: str) -> str:
    """Return the config/prompt family for the merged extremum variant."""

    if str(query_id) == _CHANGE_QUERY_ID:
        return "delta"
    if str(query_id) == _RATIO_QUERY_ID:
        return "ratio"
    if str(query_id) == _PAIRWISE_QUERY_ID:
        return "pairwise"
    if str(query_id) == _EQUALITY_QUERY_ID:
        return "equality"
    if str(query_id) == _SERIES_RANK_QUERY_ID:
        return "series_rank"
    if str(query_id) in _CONDITIONAL_QUERY_IDS:
        return "conditional_gap"
    if str(query_id) == _CATEGORY_TOTAL_QUERY_ID:
        return "category_total"
    raise ValueError(f"unsupported multiseries comparison query_id: {query_id}")


def _resolve_change_measure(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve directional-change versus absolute-gap inside the change family."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_CHANGE_MEASURES,
        task_id=TASK_ID,
        explicit_key="change_measure",
        weights_key="change_measure_weights",
        balance_flag_key="balanced_change_measure_sampling",
        axis_namespace="change_measure",
    )


def _resolve_ratio_measure(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve share versus pair-ratio inside the ratio family."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_RATIO_MEASURES,
        task_id=TASK_ID,
        explicit_key="ratio_measure",
        weights_key="ratio_measure_weights",
        balance_flag_key="balanced_ratio_measure_sampling",
        axis_namespace="ratio_measure",
    )


def _resolve_change_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve increase/decrease for directional-change queries."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_CHANGE_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="change_direction",
        weights_key="change_direction_weights",
        balance_flag_key="balanced_change_direction_sampling",
        axis_namespace="change_direction",
    )


def _resolve_extremum_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve largest/smallest for merged extremum queries."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_EXTREMUM_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        balance_flag_key="balanced_extremum_direction_sampling",
        axis_namespace="extremum_direction",
    )


def _resolve_comparison(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve strict greater-than/less-than for pairwise comparison counts."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_COMPARISONS,
        task_id=TASK_ID,
        explicit_key="comparison",
        weights_key="comparison_weights",
        balance_flag_key="balanced_comparison_sampling",
        axis_namespace="comparison",
    )


def _resolve_condition_comparison(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the filter comparator for conditional-gap queries."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_COMPARISONS,
        task_id=TASK_ID,
        explicit_key="condition_comparison",
        weights_key="condition_comparison_weights",
        balance_flag_key="balanced_condition_comparison_sampling",
        axis_namespace="condition_comparison",
    )


def _resolve_conditional_gap_aggregate_kind(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the aggregate arithmetic kind inside the conditional-gap aggregate variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_CONDITIONAL_GAP_AGGREGATE_KINDS,
        task_id=TASK_ID,
        explicit_key="conditional_gap_aggregate_kind",
        weights_key="conditional_gap_aggregate_kind_weights",
        balance_flag_key="balanced_conditional_gap_aggregate_kind_sampling",
        axis_namespace="conditional_gap_aggregate_kind",
    )

def _conditional_gap_internal_query_id(query_id: str, aggregate_kind: str | None) -> str:
    """Map the public conditional-gap variant to the shared dataset-builder variant."""

    if str(query_id) == _CONDITIONAL_AGGREGATE_QUERY_ID:
        internal_query_id = _CONDITIONAL_GAP_AGGREGATE_KIND_TO_INTERNAL.get(str(aggregate_kind))
        if internal_query_id is None:
            raise ValueError(f"unsupported conditional_gap_aggregate_kind: {aggregate_kind}")
        return str(internal_query_id)
    if str(query_id) == _CONDITIONAL_EXTREMUM_QUERY_ID:
        return str(_CONDITIONAL_EXTREMUM_QUERY_ID)
    raise ValueError(f"unsupported conditional-gap query_id: {query_id}")


def _internal_pairwise_variant(comparison: str) -> str:
    """Map a public pairwise comparator to the construction variant."""

    if str(comparison) == "greater_than":
        return "series_a_gt_b_count"
    if str(comparison) == "less_than":
        return "series_a_lt_b_count"
    raise ValueError(f"unsupported comparison: {comparison}")


def _internal_extremum_variant(
    query_id: str,
    *,
    change_measure: str | None,
    ratio_measure: str | None,
    change_direction: str | None,
    extremum_direction: str | None,
) -> str:
    """Map the public multiseries variant plus query parameter to the construction variant."""

    if str(query_id) == _CHANGE_QUERY_ID and str(change_measure) == "directional_change":
        if str(change_direction) == "increase":
            return "ranked_largest_increase"
        if str(change_direction) == "decrease":
            return "ranked_largest_decrease"
        raise ValueError(f"unsupported change_direction: {change_direction}")
    if str(query_id) == _CHANGE_QUERY_ID and str(change_measure) == "absolute_gap":
        if str(extremum_direction) == "largest":
            return "ranked_largest_gap"
        if str(extremum_direction) == "smallest":
            return "ranked_smallest_gap"
        raise ValueError(f"unsupported extremum_direction: {extremum_direction}")
    if str(query_id) == _RATIO_QUERY_ID and str(ratio_measure) == "series_share":
        if str(extremum_direction) == "largest":
            return "ranked_largest_series_share"
        if str(extremum_direction) == "smallest":
            return "ranked_smallest_series_share"
        raise ValueError(f"unsupported extremum_direction: {extremum_direction}")
    if str(query_id) == _RATIO_QUERY_ID and str(ratio_measure) == "pair_ratio":
        if str(extremum_direction) == "largest":
            return "ranked_largest_pair_ratio"
        if str(extremum_direction) == "smallest":
            return "ranked_smallest_pair_ratio"
        raise ValueError(f"unsupported extremum_direction: {extremum_direction}")
    raise ValueError(f"unsupported multiseries extremum query_id: {query_id}")

def _params_for_variant_family(params: Mapping[str, Any], *, family: str) -> Dict[str, Any]:
    """Apply family-prefixed ranges while still honoring explicit standard keys."""

    resolved = dict(params)
    for key in _FAMILY_RANGE_KEYS:
        if key in resolved:
            continue
        prefixed_key = f"{family}_{key}"
        if prefixed_key in resolved:
            resolved[key] = resolved[prefixed_key]
        elif prefixed_key in _GEN_DEFAULTS:
            resolved[key] = _GEN_DEFAULTS[prefixed_key]
    return resolved


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic multiseries extremum variant."""

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


def _uses_uniform_axis_cycle(
    params: Mapping[str, Any],
    *,
    probabilities: Mapping[str, float],
    supported_values: Tuple[str, ...],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
) -> bool:
    """Return true when `_sample_cursor` is driving one balanced query-parameter cycle."""

    if params.get(str(explicit_key)) is not None or params.get(str(weights_key)) is not None:
        return False
    enabled = bool(params.get(str(balance_flag_key), _GEN_DEFAULTS.get(str(balance_flag_key), True)))
    if not bool(enabled):
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(supported_values):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_params_for_query_axis_cycle(
    params: Mapping[str, Any],
    *,
    probabilities: Mapping[str, float],
    supported_values: Tuple[str, ...],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
) -> Dict[str, Any]:
    """Use a per-query-parameter occurrence index for answer-support cycling."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_axis_cycle(
        params,
        probabilities=probabilities,
        supported_values=supported_values,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
    ):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(supported_values))
    return support_params


def _scene_sampling_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Decorrelate balanced scene cycling from balanced query-id cycling."""

    scene_params = dict(params)
    if "scene_variant" in scene_params or "_sample_cursor" not in scene_params:
        return scene_params
    query_id_index = _SUPPORTED_QUERY_IDS.index(str(query_id))
    scene_params["_sample_cursor"] = (int(scene_params["_sample_cursor"]) // len(_SUPPORTED_QUERY_IDS)) + int(
        query_id_index
    )
    return scene_params


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    query_id: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the multiseries chart scene variant."""

    return resolve_chart_axis_variant(
        params=_scene_sampling_params(params, query_id=str(query_id)),
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _balanced_answer_label_target(
    params: Mapping[str, Any],
    *,
    query_id: str,
    instance_seed: int | None = None,
) -> str | None:
    """Return a deterministic answer-label target for review/probe builds."""

    sampling_index = params.get("_sample_cursor")
    if sampling_index is None and instance_seed is None:
        return None
    variant_index = _SUPPORTED_QUERY_IDS.index(str(query_id))
    occurrence_index = (
        int(sampling_index)
        if sampling_index is not None
        else abs(int(instance_seed or 0))
    )
    pool = [
        str(label)
        for label in resolve_chart_category_labels(
            random.Random(73_009 + int(variant_index)),
            count=25,
            min_chars=2,
            max_chars=6,
            allow_spaces=False,
        ).labels
    ]
    return str(pool[(int(occurrence_index) + int(variant_index)) % len(pool)])


def _remap_category_labels(value: Any, mapping: Mapping[str, str]) -> Any:
    """Recursively remap category-label strings inside trace metadata."""

    if isinstance(value, str):
        return str(mapping.get(str(value), str(value)))
    if isinstance(value, list):
        return [_remap_category_labels(item, mapping) for item in value]
    if isinstance(value, tuple):
        return tuple(_remap_category_labels(item, mapping) for item in value)
    if isinstance(value, dict):
        return {
            str(mapping.get(str(key), str(key))): _remap_category_labels(item, mapping)
            for key, item in value.items()
        }
    return value


def _balance_answer_label_for_indexed_probe(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    values_by_category: Mapping[str, Mapping[str, int]],
    answer_label: str,
    trace_extras: Mapping[str, Any],
) -> Tuple[Dict[str, Dict[str, int]], str, Dict[str, Any]]:
    """Relabel categories so indexed probes do not concentrate on one answer letter."""

    normalized_values = {
        str(category): {str(series): int(value) for series, value in series_values.items()}
        for category, series_values in values_by_category.items()
    }
    target_label = _balanced_answer_label_target(
        params,
        query_id=str(query_id),
        instance_seed=int(instance_seed),
    )
    if target_label is None or str(target_label) == str(answer_label):
        return normalized_values, str(answer_label), dict(trace_extras)
    category_labels = [str(label) for label in trace_extras.get("category_labels", normalized_values.keys())]
    mapping = {str(label): str(label) for label in category_labels}
    if str(target_label) in mapping:
        mapping[str(target_label)] = str(answer_label)
    mapping[str(answer_label)] = str(target_label)
    remapped_values = {
        str(mapping.get(str(category), str(category))): dict(series_values)
        for category, series_values in normalized_values.items()
    }
    remapped_trace = _remap_category_labels(dict(trace_extras), mapping)
    return remapped_values, str(target_label), dict(remapped_trace)
