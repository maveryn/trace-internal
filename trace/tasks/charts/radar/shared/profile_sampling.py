"""Dataset and query sampling for radar chart profile tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import group_default, resolve_required_int_bounds
from ....shared.deterministic_sampling import resolve_selection_index
from ...shared.label_assets import (
    resolve_chart_entity_labels,
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)
from .profile_common import (
    TASK_ID,
    _GEN_DEFAULTS,
    _PANEL_LABELS,
    _Dataset,
    _Panel,
    _Profile,
    _Query,
    _palette,
    _resolve_gen_int,
)

def _choice_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))

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
    high = int(high)
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
    labels = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=8,
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels)

def _sample_axis_metrics(count: int, *, instance_seed: int) -> Tuple[str, ...]:
    return _sample_metrics(int(count), instance_seed=int(instance_seed) + 101)

def _resolved_label_metadata(resolved: Any) -> Dict[str, Any]:
    return {
        "label_variant": str(resolved.label_variant),
        "label_pool_kind": str(resolved.label_pool_kind),
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
        "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
    }

def _sample_panel_labels(
    count: int,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    reserved_labels: Sequence[str],
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    resolved = resolve_chart_panel_labels(
        spawn_rng(int(instance_seed), f"{TASK_ID}.panel_labels"),
        count=int(count),
        min_chars=1,
        max_chars=10,
        allow_spaces=False,
        variant_weights=params.get(
            "panel_label_variant_weights",
            group_default(
                _GEN_DEFAULTS,
                "panel_label_variant_weights",
                {
                    "subplot_letters": 1.0,
                    "named_compact": 0.75,
                    "technical_topics": 0.75,
                    "condition_labels": 0.5,
                    "temporal_sequence": 0.25,
                },
            ),
        ),
        reserved_labels=tuple(str(label) for label in reserved_labels),
    )
    collision_check = validate_chart_label_namespaces(
        panel_labels=resolved.labels,
        other_label_groups={"metric_or_profile_labels": tuple(str(label) for label in reserved_labels)},
        context="radar panel labels",
    )
    return tuple(str(label) for label in resolved.labels), {
        "panel_label_resolution": _resolved_label_metadata(resolved),
        "panel_label_collision_check": dict(collision_check),
    }

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
    target_count = _balanced_choice(
        _target_count_support(params, upper=min(6, int(panel_count) - 1)),
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.highlighted_metric_threshold_panel_count.target_count",
    )
    threshold = _threshold(non_answer_params, instance_seed=int(instance_seed))
    metric_count = _axis_metric_count(non_answer_params, min_required=5, instance_seed=int(instance_seed))
    metrics = _sample_axis_metrics(int(metric_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _sample_panel_labels(
        int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=tuple(metrics) + ("Profile",),
    )
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
    annotation_ids = tuple(f"{str(panel)}|Profile|{str(metric_label)}" for panel in panel_labels if str(panel) in matching_set)
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
        annotation_point_ids=annotation_ids,
        trace={
            "query_metric_label": str(metric_label),
            "threshold_value": int(threshold),
            "matching_panel_labels": [str(panel) for panel in panel_labels if str(panel) in matching_set],
            "panel_layout_labels": [str(panel) for panel in layout_panel_labels],
            "values_by_panel": values,
            **dict(panel_label_meta),
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
    metrics = _sample_metrics(int(metric_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _sample_panel_labels(
        int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=tuple(metrics) + ("Profile",),
    )
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
    annotation_ids = tuple(
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
        annotation_point_ids=annotation_ids,
        trace={
            "query_panel_label": str(query_panel_label),
            "threshold_value": int(threshold),
            "matching_metric_labels": [
                str(metric)
                for metric in metrics
                if int(values[str(query_panel_label)][str(metric)]) > int(threshold)
            ],
            "values_by_panel": values,
            **dict(panel_label_meta),
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
    profile_labels = resolve_chart_entity_labels(
        spawn_rng(int(instance_seed), f"{TASK_ID}.profile_advantage.profile_labels"),
        count=2,
        min_chars=2,
        max_chars=7,
        allow_spaces=False,
    ).labels
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
            _Profile(profile_label=str(profile_labels[0]), values=dict(values_a), color_rgb=tuple(palette[0])),
            _Profile(profile_label=str(profile_labels[1]), values=dict(values_b), color_rgb=tuple(palette[1])),
        ),
    )
    annotation_ids: List[str] = []
    for metric in metrics:
        if int(values_a[str(metric)]) > int(values_b[str(metric)]):
            annotation_ids.append(f"|{str(profile_labels[0])}|{str(metric)}")
            annotation_ids.append(f"|{str(profile_labels[1])}|{str(metric)}")
    query = _Query(
        query_id="profile_advantage_count",
        scene_variant="single_radar_multi_profile",
        answer=int(target_count),
        answer_type="integer",
        metric_label="",
        panel_label="",
        profile_a_label=str(profile_labels[0]),
        profile_b_label=str(profile_labels[1]),
        threshold_value=0,
        minimum_metric_count=0,
        annotation_point_ids=tuple(annotation_ids),
        trace={
            "profile_a_label": str(profile_labels[0]),
            "profile_b_label": str(profile_labels[1]),
            "advantage_metric_labels": [
                str(metric)
                for metric in metrics
                if int(values_a[str(metric)]) > int(values_b[str(metric)])
            ],
            "values_by_profile": {
                str(profile_labels[0]): dict(values_a),
                str(profile_labels[1]): dict(values_b),
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
    metrics = _sample_metrics(int(metric_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _sample_panel_labels(
        int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=tuple(metrics) + ("Profile",),
    )
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
    annotation_ids = tuple(
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
        annotation_point_ids=annotation_ids,
        trace={
            "threshold_value": int(threshold),
            "minimum_metric_count": int(minimum_metric_count),
            "matching_panel_labels": list(matching_labels),
            "values_by_panel": values,
            **dict(panel_label_meta),
        },
    )
    return _Dataset(metrics=tuple(metrics), panels=panels, query=query)
