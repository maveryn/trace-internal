"""Sampling helpers for scatter cluster chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import group_default
from ....shared.deterministic_sampling import resolve_selection_index
from ...shared.label_assets import resolve_chart_entity_labels
from ...shared.labeled_chart_common import resolve_chart_axis_variant
from .cluster_common import (
    TASK_ID,
    _GEN_DEFAULTS,
    _OPTION_LABELS,
    _SUPPORTED_SEPARATION_EXTREMA,
    _SUPPORTED_SPREAD_AXES,
    _SUPPORTED_SPREAD_EXTREMA,
    _SUPPORTED_TREND_DIRECTIONS,
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


def _option_count_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    explicit = params.get("option_count")
    if explicit is not None:
        count = int(explicit)
        if count not in {4, 6}:
            raise ValueError("option_count must be either 4 or 6 for scatter centroid option tasks")
        return (int(count),)
    raw_support = params.get(
        "centroid_option_count_support",
        group_default(_GEN_DEFAULTS, "centroid_option_count_support", (4, 6)),
    )
    if isinstance(raw_support, Sequence) and not isinstance(raw_support, (str, bytes)):
        support = tuple(sorted({int(value) for value in raw_support if int(value) in {4, 6}}))
    else:
        support = ()
    if not support:
        raise ValueError("centroid_option_count_support must contain 4 and/or 6")
    return support


def _target_option_count(params: Mapping[str, Any], *, instance_seed: int) -> int:
    support = _option_count_support(params)
    base_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.centroid_option.option_count",
    )
    return int(support[abs(int(base_index)) % len(support)])


def _option_labels_for_count(option_count: int) -> Tuple[str, ...]:
    if int(option_count) not in {4, 6}:
        raise ValueError("option_count must be either 4 or 6")
    return tuple(_OPTION_LABELS[: int(option_count)])


def _target_option_label(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    cluster_count: int,
    option_labels: Sequence[str],
) -> str:
    sampling_index = params.get("_sample_cursor")
    if sampling_index is not None:
        occurrence = abs(int(sampling_index)) // max(1, int(cluster_count))
    else:
        occurrence = abs(int(instance_seed))
    return str(option_labels[int(occurrence) % len(option_labels)])
