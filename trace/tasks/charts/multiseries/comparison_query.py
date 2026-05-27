"""Answer comparison queries over multiseries charts."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.chart_scene import render_multiseries_chart_scene, value_axis_render_metadata
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.labeled_chart_common import (
    CHART_LABEL_POOL_UP_TO_25,
    resolve_chart_axis_variant,
    resolve_chart_render_params_for_task,
)
from ..shared.multiseries_chart_common import (
    MultiseriesChartDefaults,
    SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS,
    build_category_total_extremum_label_dataset,
    build_conditional_gap_value_dataset,
    build_delta_extremum_label_dataset,
    build_multiseries_mark_specs,
    build_pairwise_comparison_count_dataset,
    build_ratio_extremum_label_dataset,
    projected_multiseries_mark_evidence,
    resolve_multiseries_chart_colors,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_multiseries_comparison_query_base"
_CHANGE_QUERY_VARIANT = "ranked_change_extremum"
_RATIO_QUERY_VARIANT = "ranked_ratio_extremum"
_PAIRWISE_QUERY_VARIANT = "series_comparison_count"
_CONDITIONAL_AGGREGATE_QUERY_VARIANT = "conditional_gap_aggregate_value"
_CONDITIONAL_SUM_QUERY_VARIANT = "conditional_gap_sum_value"
_CONDITIONAL_MEAN_QUERY_VARIANT = "conditional_gap_mean_value"
_CONDITIONAL_RANGE_QUERY_VARIANT = "conditional_gap_range_value"
_CONDITIONAL_EXTREMUM_QUERY_VARIANT = "conditional_gap_extremum_value"
_CATEGORY_TOTAL_QUERY_VARIANT = "category_total_extremum_label"
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    _CHANGE_QUERY_VARIANT,
    _RATIO_QUERY_VARIANT,
    _PAIRWISE_QUERY_VARIANT,
    _CONDITIONAL_AGGREGATE_QUERY_VARIANT,
    _CONDITIONAL_EXTREMUM_QUERY_VARIANT,
    _CATEGORY_TOTAL_QUERY_VARIANT,
)
_SUPPORTED_CHANGE_MEASURES: Tuple[str, ...] = (
    "directional_change",
    "absolute_gap",
)
_SUPPORTED_RATIO_MEASURES: Tuple[str, ...] = (
    "series_share",
    "pair_ratio",
)
_SUPPORTED_CHANGE_DIRECTIONS: Tuple[str, ...] = (
    "increase",
    "decrease",
)
_SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = (
    "largest",
    "smallest",
)
_SUPPORTED_COMPARISONS: Tuple[str, ...] = (
    "greater_than",
    "less_than",
)
_SUPPORTED_CONDITIONAL_GAP_AGGREGATE_KINDS: Tuple[str, ...] = (
    "sum",
    "mean",
    "range",
)
_CONDITIONAL_GAP_AGGREGATE_KIND_TO_INTERNAL: Dict[str, str] = {
    "sum": _CONDITIONAL_SUM_QUERY_VARIANT,
    "mean": _CONDITIONAL_MEAN_QUERY_VARIANT,
    "range": _CONDITIONAL_RANGE_QUERY_VARIANT,
}
_CONDITIONAL_QUERY_VARIANTS: Tuple[str, ...] = (
    _CONDITIONAL_AGGREGATE_QUERY_VARIANT,
    _CONDITIONAL_EXTREMUM_QUERY_VARIANT,
)

_DEFAULTS = MultiseriesChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "multiseries")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="multiseries")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="multiseries", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    _PAIRWISE_QUERY_VARIANT: 0.0,
    _CHANGE_QUERY_VARIANT: 0.75,
    _RATIO_QUERY_VARIANT: 0.20,
    _CONDITIONAL_AGGREGATE_QUERY_VARIANT: 0.70,
    _CONDITIONAL_EXTREMUM_QUERY_VARIANT: 0.66,
    _CATEGORY_TOTAL_QUERY_VARIANT: 0.46,
}
_CONDITIONAL_AGGREGATE_REASONING_LOADS: Dict[str, float] = {
    "sum": 0.62,
    "mean": 0.70,
    "range": 0.78,
}
_REASONING_LOAD_BY_MEASURE: Dict[str, float] = {
    "directional_change": 0.65,
    "absolute_gap": 0.85,
    "series_share": 0.21,
    "pair_ratio": 0.14,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "grouped_bar": 0.0,
    "grouped_horizontal_bar": 0.50,
    "grouped_lollipop": 0.55,
    "multi_line": 1.0,
}
_FAMILY_RANGE_KEYS: Tuple[str, ...] = (
    "category_count_min",
    "category_count_max",
    "series_count_min",
    "series_count_max",
    "value_min",
    "value_max",
)


def _ordinal(value: int) -> str:
    """Return a compact English ordinal for prompt slots."""

    if 10 <= int(value) % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(int(value) % 10, "th")
    return f"{int(value)}{suffix}"


def _ranked_phrase(rank: int, base: str) -> str:
    """Return natural rank wording for an extremum phrase."""

    if int(rank) == 1:
        return str(base)
    return f"{_ordinal(int(rank))} {str(base)}"


def _normalize_multiseries_visual_scan(trace_extras: Mapping[str, Any]) -> float:
    """Normalize multiseries visual load from category and series counts."""

    if "filtered_category_count" in trace_extras:
        category_range = trace_extras.get("category_count_range", [0, 0])
        series_range = trace_extras.get("series_count_range", [0, 0])
        filter_range = trace_extras.get("filtered_category_count_range", [0, 0])
        total_marks = int(trace_extras["category_count"]) * int(trace_extras["series_count"])
        total_bounds = [
            int(category_range[0]) * int(series_range[0]),
            int(category_range[1]) * int(series_range[1]),
        ]
        mark_scan = normalize_int_with_bounds(int(total_marks), total_bounds)
        filter_scan = normalize_int_with_bounds(
            int(trace_extras["filtered_category_count"]),
            (int(filter_range[0]), int(filter_range[1])),
        )
        return min(1.0, (0.72 * float(mark_scan)) + (0.28 * float(filter_scan)))

    category_range = trace_extras.get("category_count_range", [0, 0])
    series_range = trace_extras.get("series_count_range", [0, 0])
    category_bounds = [
        min(
            int(_GEN_DEFAULTS.get("delta_category_count_min", category_range[0])),
            int(_GEN_DEFAULTS.get("ratio_category_count_min", category_range[0])),
        ),
        max(
            int(_GEN_DEFAULTS.get("delta_category_count_max", category_range[1])),
            int(_GEN_DEFAULTS.get("ratio_category_count_max", category_range[1])),
        ),
    ]
    series_bounds = [
        min(
            int(_GEN_DEFAULTS.get("delta_series_count_min", series_range[0])),
            int(_GEN_DEFAULTS.get("ratio_series_count_min", series_range[0])),
        ),
        max(
            int(_GEN_DEFAULTS.get("delta_series_count_max", series_range[1])),
            int(_GEN_DEFAULTS.get("ratio_series_count_max", series_range[1])),
        ),
    ]
    category_norm = normalize_int_with_bounds(int(trace_extras["category_count"]), category_bounds)
    series_norm = normalize_int_with_bounds(int(trace_extras["series_count"]), series_bounds)
    return min(1.0, (0.70 * float(category_norm)) + (0.30 * float(series_norm)))


def _variant_family(query_variant: str) -> str:
    """Return the config/prompt family for the merged extremum variant."""

    if str(query_variant) == _CHANGE_QUERY_VARIANT:
        return "delta"
    if str(query_variant) == _RATIO_QUERY_VARIANT:
        return "ratio"
    if str(query_variant) == _PAIRWISE_QUERY_VARIANT:
        return "pairwise"
    if str(query_variant) in _CONDITIONAL_QUERY_VARIANTS:
        return "conditional_gap"
    if str(query_variant) == _CATEGORY_TOTAL_QUERY_VARIANT:
        return "category_total"
    raise ValueError(f"unsupported multiseries comparison query_variant: {query_variant}")


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


def _comparison_phrase(comparison: str) -> str:
    """Return prompt wording for one strict comparator."""

    if str(comparison) == "greater_than":
        return "higher than"
    if str(comparison) == "less_than":
        return "lower than"
    raise ValueError(f"unsupported comparison: {comparison}")


def _conditional_gap_aggregate_prompt_slots(aggregate_kind: str | None) -> Dict[str, str]:
    """Return prompt wording for one conditional-gap aggregate kind."""

    if str(aggregate_kind) == "sum":
        return {
            "conditional_gap_aggregate_kind": "sum",
            "conditional_gap_aggregate_instruction": "sum",
        }
    if str(aggregate_kind) == "mean":
        return {
            "conditional_gap_aggregate_kind": "mean",
            "conditional_gap_aggregate_instruction": "integer average",
        }
    if str(aggregate_kind) == "range":
        return {
            "conditional_gap_aggregate_kind": "range",
            "conditional_gap_aggregate_instruction": "range, meaning largest minus smallest",
        }
    return {
        "conditional_gap_aggregate_kind": "",
        "conditional_gap_aggregate_instruction": "",
    }


def _conditional_gap_internal_query_variant(query_variant: str, aggregate_kind: str | None) -> str:
    """Map the public conditional-gap variant to the shared dataset-builder variant."""

    if str(query_variant) == _CONDITIONAL_AGGREGATE_QUERY_VARIANT:
        internal_query_variant = _CONDITIONAL_GAP_AGGREGATE_KIND_TO_INTERNAL.get(str(aggregate_kind))
        if internal_query_variant is None:
            raise ValueError(f"unsupported conditional_gap_aggregate_kind: {aggregate_kind}")
        return str(internal_query_variant)
    if str(query_variant) == _CONDITIONAL_EXTREMUM_QUERY_VARIANT:
        return str(_CONDITIONAL_EXTREMUM_QUERY_VARIANT)
    raise ValueError(f"unsupported conditional-gap query_variant: {query_variant}")


def _internal_pairwise_variant(comparison: str) -> str:
    """Map a public pairwise comparator to the construction variant."""

    if str(comparison) == "greater_than":
        return "series_a_gt_b_count"
    if str(comparison) == "less_than":
        return "series_a_lt_b_count"
    raise ValueError(f"unsupported comparison: {comparison}")


def _internal_extremum_variant(
    query_variant: str,
    *,
    change_measure: str | None,
    ratio_measure: str | None,
    change_direction: str | None,
    extremum_direction: str | None,
) -> str:
    """Map the public multiseries variant plus query parameter to the construction variant."""

    if str(query_variant) == _CHANGE_QUERY_VARIANT and str(change_measure) == "directional_change":
        if str(change_direction) == "increase":
            return "ranked_largest_increase"
        if str(change_direction) == "decrease":
            return "ranked_largest_decrease"
        raise ValueError(f"unsupported change_direction: {change_direction}")
    if str(query_variant) == _CHANGE_QUERY_VARIANT and str(change_measure) == "absolute_gap":
        if str(extremum_direction) == "largest":
            return "ranked_largest_gap"
        if str(extremum_direction) == "smallest":
            return "ranked_smallest_gap"
        raise ValueError(f"unsupported extremum_direction: {extremum_direction}")
    if str(query_variant) == _RATIO_QUERY_VARIANT and str(ratio_measure) == "series_share":
        if str(extremum_direction) == "largest":
            return "ranked_largest_series_share"
        if str(extremum_direction) == "smallest":
            return "ranked_smallest_series_share"
        raise ValueError(f"unsupported extremum_direction: {extremum_direction}")
    if str(query_variant) == _RATIO_QUERY_VARIANT and str(ratio_measure) == "pair_ratio":
        if str(extremum_direction) == "largest":
            return "ranked_largest_pair_ratio"
        if str(extremum_direction) == "smallest":
            return "ranked_smallest_pair_ratio"
        raise ValueError(f"unsupported extremum_direction: {extremum_direction}")
    raise ValueError(f"unsupported multiseries extremum query_variant: {query_variant}")


def _change_prompt_slots(change_direction: str | None) -> Dict[str, str]:
    """Return prompt slots for directional-change queries."""

    if str(change_direction) == "increase":
        return {
            "change_direction": "increase",
            "change_expression": "the second queried series minus the first queried series",
            "change_action": "increase from first to second",
        }
    if str(change_direction) == "decrease":
        return {
            "change_direction": "decrease",
            "change_expression": "the first queried series minus the second queried series",
            "change_action": "decrease from first to second",
        }
    return {
        "change_direction": "",
        "change_expression": "",
        "change_action": "",
    }


def _change_measure_prompt_slots(change_measure: str | None, change_direction: str | None) -> Dict[str, str]:
    """Return prompt wording for the sampled change measure."""

    if str(change_measure) == "directional_change":
        return {
            "change_measure": "directional change",
            "change_measure_prompt": str(_change_prompt_slots(change_direction)["change_action"]),
        }
    if str(change_measure) == "absolute_gap":
        return {
            "change_measure": "absolute gap",
            "change_measure_prompt": "absolute gap",
        }
    return {
        "change_measure": "",
        "change_measure_prompt": "",
    }


def _extremum_prompt_slots(extremum_direction: str | None, *, answer_rank: int) -> Dict[str, str]:
    """Return prompt slots for largest/smallest extremum wording."""

    if str(extremum_direction) == "smallest":
        return {
            "extremum_direction": "smallest",
            "ranked_extremum": _ranked_phrase(int(answer_rank), "smallest"),
        }
    return {
        "extremum_direction": "largest",
        "ranked_extremum": _ranked_phrase(int(answer_rank), "largest"),
    }


def _ratio_measure_prompt_slots(
    ratio_measure: str | None,
    *,
    target_series: str,
    numerator_series: str,
    denominator_series: str,
) -> Dict[str, str]:
    """Return prompt wording for the sampled ratio measure."""

    if str(ratio_measure) == "series_share":
        return {
            "ratio_measure": "series share",
            "ratio_measure_prompt": f'percentage share for "{str(target_series)}" out of each category total',
        }
    if str(ratio_measure) == "pair_ratio":
        return {
            "ratio_measure": "pair ratio",
            "ratio_measure_prompt": f'percentage ratio of "{str(numerator_series)}" to "{str(denominator_series)}"',
        }
    return {
        "ratio_measure": "",
        "ratio_measure_prompt": "",
    }


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


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic multiseries extremum variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_VARIANTS,
        task_id=TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def _uses_uniform_query_variant_cycle(
    params: Mapping[str, Any],
    *,
    query_variant_probabilities: Mapping[str, float],
) -> bool:
    """Return true when `_sample_cursor` is driving the default query-variant cycle."""

    if params.get("query_variant") is not None or params.get("query_variant_weights") is not None:
        return False
    enabled = bool(params.get("balanced_query_variant_sampling", _GEN_DEFAULTS.get("balanced_query_variant_sampling", True)))
    if not bool(enabled):
        return False
    positives = [float(value) for value in query_variant_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(_SUPPORTED_QUERY_VARIANTS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_params_for_query_variant_cycle(
    params: Mapping[str, Any],
    *,
    query_variant_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-public-variant occurrence index for subparameter and support cycling."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_variant_cycle(params, query_variant_probabilities=query_variant_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_QUERY_VARIANTS))
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


def _scene_sampling_params(params: Mapping[str, Any], *, query_variant: str) -> Dict[str, Any]:
    """Decorrelate balanced scene cycling from balanced query-variant cycling."""

    scene_params = dict(params)
    if "scene_variant" in scene_params or "_sample_cursor" not in scene_params:
        return scene_params
    query_variant_index = _SUPPORTED_QUERY_VARIANTS.index(str(query_variant))
    scene_params["_sample_cursor"] = (int(scene_params["_sample_cursor"]) // len(_SUPPORTED_QUERY_VARIANTS)) + int(
        query_variant_index
    )
    return scene_params


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    query_variant: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the multiseries chart scene variant."""

    return resolve_chart_axis_variant(
        params=_scene_sampling_params(params, query_variant=str(query_variant)),
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
    query_variant: str,
    instance_seed: int | None = None,
) -> str | None:
    """Return a deterministic answer-label target for review/probe builds."""

    sampling_index = params.get("_sample_cursor")
    if sampling_index is None and instance_seed is None:
        return None
    variant_index = _SUPPORTED_QUERY_VARIANTS.index(str(query_variant))
    occurrence_index = (
        int(sampling_index)
        if sampling_index is not None
        else abs(int(instance_seed or 0))
    )
    pool = [str(label) for label in CHART_LABEL_POOL_UP_TO_25]
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
    query_variant: str,
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
        query_variant=str(query_variant),
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


class ChartsMultiseriesComparisonQueryTask:
    """Answer label, count, and aggregate comparison queries over multiseries charts."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "multiseries"

    def _generate_conditional_gap(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        query_variant: str,
        query_params: Dict[str, Any],
        query_variant_probabilities: Mapping[str, float],
    ) -> TaskOutput:
        conditional_gap_aggregate_kind = None
        conditional_gap_aggregate_kind_probabilities: Dict[str, float] = {}
        condition_query_params = dict(query_params)
        if str(query_variant) == _CONDITIONAL_AGGREGATE_QUERY_VARIANT:
            conditional_gap_aggregate_kind, conditional_gap_aggregate_kind_probabilities = (
                _resolve_conditional_gap_aggregate_kind(
                    query_params,
                    instance_seed=int(instance_seed),
                )
            )
            condition_query_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=conditional_gap_aggregate_kind_probabilities,
                supported_values=_SUPPORTED_CONDITIONAL_GAP_AGGREGATE_KINDS,
                explicit_key="conditional_gap_aggregate_kind",
                weights_key="conditional_gap_aggregate_kind_weights",
                balance_flag_key="balanced_conditional_gap_aggregate_kind_sampling",
            )
        condition_comparison, condition_comparison_probabilities = _resolve_condition_comparison(
            condition_query_params,
            instance_seed=int(instance_seed),
        )
        extremum_query_params = _support_params_for_query_axis_cycle(
            condition_query_params,
            probabilities=condition_comparison_probabilities,
            supported_values=_SUPPORTED_COMPARISONS,
            explicit_key="condition_comparison",
            weights_key="condition_comparison_weights",
            balance_flag_key="balanced_condition_comparison_sampling",
        )
        # Condition and extremum mirrors are prompt/query axes. Keep construction
        # support cycling at the public variant occurrence level so mirror pairs
        # do not duplicate the same numeric answer in exact 100-sample probes.
        dataset_params = dict(query_params)
        extremum_direction = None
        extremum_direction_probabilities: Dict[str, float] = {}
        if str(query_variant) == _CONDITIONAL_EXTREMUM_QUERY_VARIANT:
            extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                extremum_query_params,
                instance_seed=int(instance_seed),
            )
        internal_query_variant = _conditional_gap_internal_query_variant(
            str(query_variant),
            conditional_gap_aggregate_kind,
        )

        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            query_variant=str(query_variant),
            instance_seed=int(instance_seed),
        )
        (
            values_by_category,
            answer_value,
            evidence_labels,
            evidence_series_by_category,
            trace_extras,
        ) = build_conditional_gap_value_dataset(
            query_variant=str(internal_query_variant),
            condition_comparison=str(condition_comparison),
            extremum_direction=extremum_direction,
            params=dataset_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        category_labels = [str(label) for label in trace_extras["category_labels"]]
        series_labels = [str(label) for label in trace_extras["series_labels"]]
        mark_style = resolve_multiseries_chart_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            series_count=len(series_labels),
        )
        marks = build_multiseries_mark_specs(
            category_labels=category_labels,
            series_labels=series_labels,
            values_by_category=values_by_category,
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_multiseries_chart_scene(
            background,
            scene_variant=str(scene_variant),
            marks=marks,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key_conditional_gap",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_conditional_gap_value",
                "object_description_grouped_bar",
                "object_description_grouped_horizontal_bar",
                "object_description_multi_line",
                "object_description_grouped_lollipop",
                "evidence_hint_conditional_gap_value",
                "json_example_conditional_gap_value",
                "json_example_answer_only_conditional_gap_value",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key_conditional_gap"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "condition_left_series": str(trace_extras["condition_left_series_label"]),
                "condition_right_series": str(trace_extras["condition_right_series_label"]),
                "target_left_series": str(trace_extras["target_left_series_label"]),
                "target_right_series": str(trace_extras["target_right_series_label"]),
                "comparison_phrase": _comparison_phrase(str(condition_comparison)),
                **_conditional_gap_aggregate_prompt_slots(conditional_gap_aggregate_kind),
                "extremum_direction": str(extremum_direction or trace_extras.get("extremum_direction", "largest")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_conditional_gap_value"]),
                "answer_hint": str(prompt_defaults["answer_hint_conditional_gap_value"]),
                "json_example": str(prompt_defaults["json_example_conditional_gap_value"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_conditional_gap_value"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(answer_value))
        category_label_centers = {
            str(mark["category_label"]): list(mark["category_label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        evidence_projection = projected_multiseries_mark_evidence(
            rendered_scene,
            evidence_labels,
            evidence_series_by_category,
        )
        evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
        evidence_gt = TypedValue(type="point_set", value=evidence_points)

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_multiseries",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "internal_query_variant": str(internal_query_variant),
                    "scene_variant": str(scene_variant),
                    "variant_family": "conditional_gap",
                    "evidence_labels": list(evidence_labels),
                    "evidence_series_labels_by_category": dict(evidence_series_by_category),
                    "condition_comparison": str(condition_comparison),
                    "condition_comparison_probabilities": dict(condition_comparison_probabilities),
                    **(
                        {"conditional_gap_aggregate_kind": str(conditional_gap_aggregate_kind)}
                        if conditional_gap_aggregate_kind is not None
                        else {}
                    ),
                    **(
                        {
                            "conditional_gap_aggregate_kind_probabilities": dict(
                                conditional_gap_aggregate_kind_probabilities
                            )
                        }
                        if conditional_gap_aggregate_kind_probabilities
                        else {}
                    ),
                    **(
                        {"extremum_direction": str(extremum_direction)}
                        if extremum_direction is not None
                        else {}
                    ),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "internal_query_variant": str(internal_query_variant),
                    "scene_variant": str(scene_variant),
                    "variant_family": "conditional_gap",
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    **(
                        {"conditional_gap_aggregate_kind": str(conditional_gap_aggregate_kind)}
                        if conditional_gap_aggregate_kind is not None
                        else {}
                    ),
                    **(
                        {
                            "conditional_gap_aggregate_kind_probabilities": dict(
                                conditional_gap_aggregate_kind_probabilities
                            )
                        }
                        if conditional_gap_aggregate_kind_probabilities
                        else {}
                    ),
                    "condition_comparison": str(condition_comparison),
                    "condition_comparison_probabilities": dict(condition_comparison_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "series_count": int(trace_extras["series_count"]),
                    "series_count_range": list(trace_extras["series_count_range"]),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "filtered_category_count": int(trace_extras["filtered_category_count"]),
                    "filtered_category_count_range": list(trace_extras["filtered_category_count_range"]),
                    "target_gap_range": list(trace_extras["target_gap_range"]),
                    "answer_range": list(trace_extras["answer_range"]),
                    **(
                        {"extremum_direction": str(extremum_direction)}
                        if extremum_direction is not None
                        else {}
                    ),
                    **(
                        {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                        if extremum_direction_probabilities
                        else {}
                    ),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(render_params.layout_jitter_meta or {}),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "tick_font_size_px": int(render_params.tick_font_size_px),
                    "label_stroke_width_px": int(render_params.label_stroke_width_px),
                },
                "axis_style": {
                    "axis_line_width_px": int(render_params.axis_line_width_px),
                    "grid_line_width_px": int(render_params.grid_line_width_px),
                    "tick_length_px": int(render_params.tick_length_px),
                },
                "mark_style": {
                    "sampling_policy": str(mark_style["sampling_policy"]),
                    **{str(key): value for key, value in mark_style.items()},
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "category_label_centers_px": dict(category_label_centers),
            },
            "execution_trace": {
                "query_variant": str(query_variant),
                "internal_query_variant": str(internal_query_variant),
                "scene_variant": str(scene_variant),
                "variant_family": "conditional_gap",
                "answer_value": int(answer_value),
                "evidence_labels": list(evidence_labels),
                "evidence_series_labels_by_category": dict(evidence_series_by_category),
                "category_labels": list(category_labels),
                "series_labels": list(series_labels),
                "queried_series_labels": list(trace_extras["queried_series_labels"]),
                "condition_series_labels": list(trace_extras["condition_series_labels"]),
                "target_series_labels": list(trace_extras["target_series_labels"]),
                "condition_left_series_label": str(trace_extras["condition_left_series_label"]),
                "condition_right_series_label": str(trace_extras["condition_right_series_label"]),
                "target_left_series_label": str(trace_extras["target_left_series_label"]),
                "target_right_series_label": str(trace_extras["target_right_series_label"]),
                "condition_comparison": str(condition_comparison),
                "condition_comparison_probabilities": dict(condition_comparison_probabilities),
                **(
                    {"conditional_gap_aggregate_kind": str(conditional_gap_aggregate_kind)}
                    if conditional_gap_aggregate_kind is not None
                    else {}
                ),
                **(
                    {
                        "conditional_gap_aggregate_kind_probabilities": dict(
                            conditional_gap_aggregate_kind_probabilities
                        )
                    }
                    if conditional_gap_aggregate_kind_probabilities
                    else {}
                ),
                "series_count": int(trace_extras["series_count"]),
                "series_count_range": list(trace_extras["series_count_range"]),
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "filtered_category_count": int(trace_extras["filtered_category_count"]),
                "filtered_category_count_range": list(trace_extras["filtered_category_count_range"]),
                "filtered_category_labels": list(trace_extras["filtered_category_labels"]),
                "filtered_gap_values": list(trace_extras["filtered_gap_values"]),
                "target_gap_by_category": dict(trace_extras["target_gap_by_category"]),
                "condition_holds_by_category": dict(trace_extras["condition_holds_by_category"]),
                "target_gap_range": list(trace_extras["target_gap_range"]),
                "answer_range": list(trace_extras["answer_range"]),
                "value_range": list(trace_extras["value_range"]),
                "values_by_category": dict(trace_extras["values_by_category"]),
                "query_variant_probabilities": dict(query_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "numeric_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                **(
                    {"extremum_direction": str(extremum_direction)}
                    if extremum_direction is not None
                    else {}
                ),
                **(
                    {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                    if extremum_direction_probabilities
                    else {}
                ),
                **{str(key): value for key, value in mark_style.items() if key != "sampling_policy"},
            },
            "witness_symbolic": {
                "type": "numeric_sequence",
                "value": [int(value) for value in trace_extras["filtered_gap_values"]],
                "filtered_category_labels": list(evidence_labels),
            },
            "projected_evidence": {
                "point_set": list(evidence_points),
                **dict(evidence_projection),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": _normalize_multiseries_visual_scan(trace_extras),
                "reasoning_load": float(
                    _CONDITIONAL_AGGREGATE_REASONING_LOADS[str(conditional_gap_aggregate_kind)]
                    if conditional_gap_aggregate_kind is not None
                    else _REASONING_LOAD_BY_VARIANT[str(query_variant)]
                ),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
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
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        query_params = _support_params_for_query_variant_cycle(
            params,
            query_variant_probabilities=query_variant_probabilities,
        )
        family = _variant_family(str(query_variant))
        if str(family) == "conditional_gap":
            return self._generate_conditional_gap(
                int(instance_seed),
                params=params,
                query_variant=str(query_variant),
                query_params=query_params,
                query_variant_probabilities=query_variant_probabilities,
            )

        change_measure = None
        change_measure_probabilities: Dict[str, float] = {}
        ratio_measure = None
        ratio_measure_probabilities: Dict[str, float] = {}
        change_direction = None
        change_direction_probabilities: Dict[str, float] = {}
        extremum_direction = None
        extremum_direction_probabilities: Dict[str, float] = {}
        comparison = None
        comparison_probabilities: Dict[str, float] = {}
        dataset_params = dict(query_params)
        if str(family) == "delta":
            change_measure, change_measure_probabilities = _resolve_change_measure(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=change_measure_probabilities,
                supported_values=_SUPPORTED_CHANGE_MEASURES,
                explicit_key="change_measure",
                weights_key="change_measure_weights",
                balance_flag_key="balanced_change_measure_sampling",
            )
            if str(change_measure) == "directional_change":
                change_direction, change_direction_probabilities = _resolve_change_direction(
                    dataset_params,
                    instance_seed=int(instance_seed),
                )
                dataset_params = _support_params_for_query_axis_cycle(
                    dataset_params,
                    probabilities=change_direction_probabilities,
                    supported_values=_SUPPORTED_CHANGE_DIRECTIONS,
                    explicit_key="change_direction",
                    weights_key="change_direction_weights",
                    balance_flag_key="balanced_change_direction_sampling",
                )
            else:
                extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                    dataset_params,
                    instance_seed=int(instance_seed),
                )
                dataset_params = _support_params_for_query_axis_cycle(
                    dataset_params,
                    probabilities=extremum_direction_probabilities,
                    supported_values=_SUPPORTED_EXTREMUM_DIRECTIONS,
                    explicit_key="extremum_direction",
                    weights_key="extremum_direction_weights",
                    balance_flag_key="balanced_extremum_direction_sampling",
                )
        elif str(family) == "ratio":
            ratio_measure, ratio_measure_probabilities = _resolve_ratio_measure(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=ratio_measure_probabilities,
                supported_values=_SUPPORTED_RATIO_MEASURES,
                explicit_key="ratio_measure",
                weights_key="ratio_measure_weights",
                balance_flag_key="balanced_ratio_measure_sampling",
            )
            extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                dataset_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                dataset_params,
                probabilities=extremum_direction_probabilities,
                supported_values=_SUPPORTED_EXTREMUM_DIRECTIONS,
                explicit_key="extremum_direction",
                weights_key="extremum_direction_weights",
                balance_flag_key="balanced_extremum_direction_sampling",
            )
        elif str(family) == "category_total":
            extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=extremum_direction_probabilities,
                supported_values=_SUPPORTED_EXTREMUM_DIRECTIONS,
                explicit_key="extremum_direction",
                weights_key="extremum_direction_weights",
                balance_flag_key="balanced_extremum_direction_sampling",
            )
        else:
            comparison, comparison_probabilities = _resolve_comparison(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=comparison_probabilities,
                supported_values=_SUPPORTED_COMPARISONS,
                explicit_key="comparison",
                weights_key="comparison_weights",
                balance_flag_key="balanced_comparison_sampling",
            )
        extremum_variant = ""
        pairwise_variant = ""
        if str(family) in {"delta", "ratio"}:
            extremum_variant = _internal_extremum_variant(
                str(query_variant),
                change_measure=change_measure,
                ratio_measure=ratio_measure,
                change_direction=change_direction,
                extremum_direction=extremum_direction,
            )
        elif str(family) == "category_total":
            extremum_variant = str(_CATEGORY_TOTAL_QUERY_VARIANT)
        else:
            pairwise_variant = _internal_pairwise_variant(str(comparison))
        family_params = _params_for_variant_family(dataset_params, family=str(family))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            query_variant=str(query_variant),
            instance_seed=int(instance_seed),
        )
        if str(family) == "delta":
            values_by_category, answer_label, evidence_values, trace_extras = build_delta_extremum_label_dataset(
                query_variant=str(extremum_variant),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        elif str(family) == "ratio":
            values_by_category, answer_label, evidence_values, trace_extras = build_ratio_extremum_label_dataset(
                query_variant=str(extremum_variant),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        elif str(family) == "category_total":
            values_by_category, answer_label, evidence_values, trace_extras = build_category_total_extremum_label_dataset(
                query_variant=str(extremum_variant),
                extremum_direction=str(extremum_direction),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        else:
            values_by_category, answer_value, evidence_labels, trace_extras = build_pairwise_comparison_count_dataset(
                query_variant=str(pairwise_variant),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
            answer_label = ""
            evidence_values = []
        if str(family) in {"delta", "ratio", "category_total"}:
            values_by_category, answer_label, trace_extras = _balance_answer_label_for_indexed_probe(
                query_variant=str(query_variant),
                params=dataset_params,
                instance_seed=int(instance_seed),
                values_by_category=values_by_category,
                answer_label=str(answer_label),
                trace_extras=trace_extras,
            )

        category_labels = [str(label) for label in trace_extras["category_labels"]]
        series_labels = [str(label) for label in trace_extras["series_labels"]]
        mark_style = resolve_multiseries_chart_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            series_count=len(series_labels),
        )
        marks = build_multiseries_mark_specs(
            category_labels=category_labels,
            series_labels=series_labels,
            values_by_category=values_by_category,
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_multiseries_chart_scene(
            background,
            scene_variant=str(scene_variant),
            marks=marks,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key_pairwise",
                "task_key_delta",
                "task_key_ratio",
                "task_key_category_total",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_count",
                "answer_hint_label",
                "object_description_grouped_bar",
                "object_description_grouped_horizontal_bar",
                "object_description_multi_line",
                "object_description_grouped_lollipop",
                "evidence_hint_series_comparison_count",
                "evidence_hint_ranked_directional_change",
                "evidence_hint_ranked_absolute_gap",
                "evidence_hint_ranked_series_share",
                "evidence_hint_ranked_pair_ratio",
                "evidence_hint_category_total_extremum",
                "json_example_series_comparison_count",
                "json_example_ranked_directional_change",
                "json_example_ranked_absolute_gap",
                "json_example_ranked_series_share",
                "json_example_ranked_pair_ratio",
                "json_example_category_total_extremum",
                "json_example_answer_only_series_comparison_count",
                "json_example_answer_only_ranked_directional_change",
                "json_example_answer_only_ranked_absolute_gap",
                "json_example_answer_only_ranked_series_share",
                "json_example_answer_only_ranked_pair_ratio",
                "json_example_answer_only_category_total_extremum",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        if str(family) == "delta":
            prompt_metric_key = "ranked_directional_change" if str(change_measure) == "directional_change" else "ranked_absolute_gap"
            task_key = str(prompt_defaults["task_key_delta"])
            answer_hint = str(prompt_defaults["answer_hint_label"])
        elif str(family) == "ratio":
            prompt_metric_key = "ranked_series_share" if str(ratio_measure) == "series_share" else "ranked_pair_ratio"
            task_key = str(prompt_defaults["task_key_ratio"])
            answer_hint = str(prompt_defaults["answer_hint_label"])
        elif str(family) == "category_total":
            prompt_metric_key = "category_total_extremum"
            task_key = str(prompt_defaults["task_key_category_total"])
            answer_hint = str(prompt_defaults["answer_hint_label"])
        else:
            prompt_metric_key = "series_comparison_count"
            task_key = str(prompt_defaults["task_key_pairwise"])
            answer_hint = str(prompt_defaults["answer_hint_count"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(prompt_metric_key)}"])
        json_example = str(prompt_defaults[f"json_example_{str(prompt_metric_key)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(prompt_metric_key)}"])

        if str(family) == "pairwise":
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(task_key),
                query_key=str(query_variant),
                answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(object_description),
                    "left_series": str(trace_extras["left_series_label"]),
                    "right_series": str(trace_extras["right_series_label"]),
                    "comparison_phrase": _comparison_phrase(str(comparison)),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "evidence_hint": str(evidence_hint),
                    "answer_hint": str(answer_hint),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(answer_value))
            category_label_centers = {
                str(mark["category_label"]): list(mark["category_label_center_px"])
                for mark in rendered_scene.mark_traces
            }
            evidence_projection = projected_multiseries_mark_evidence(
                rendered_scene,
                evidence_labels,
                trace_extras["queried_series_labels"],
            )
            evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
            evidence_gt = TypedValue(type="point_set", value=evidence_points)
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"chart_{str(scene_variant)}_multiseries",
                    "entities": [dict(entity) for entity in rendered_scene.entities],
                    "relations": {
                        "query_variant": str(query_variant),
                        "scene_variant": str(scene_variant),
                        "variant_family": str(family),
                        "internal_query_variant": str(pairwise_variant),
                        "evidence_labels": list(evidence_labels),
                        "queried_series_labels": list(trace_extras["queried_series_labels"]),
                        "comparison": str(trace_extras["comparison"]),
                        "comparison_probabilities": dict(comparison_probabilities),
                    },
                },
                "query_spec": {
                    "query_variant": str(query_variant),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "query_variant": str(query_variant),
                        "scene_variant": str(scene_variant),
                        "variant_family": str(family),
                        "internal_query_variant": str(pairwise_variant),
                        "query_variant_probabilities": dict(query_variant_probabilities),
                        "comparison": str(comparison),
                        "comparison_probabilities": dict(comparison_probabilities),
                        "scene_variant_probabilities": dict(scene_variant_probabilities),
                        "target_answer": int(trace_extras["target_answer"]),
                        "target_answer_range": list(trace_extras["target_answer_range"]),
                        "series_count": int(trace_extras["series_count"]),
                        "series_count_range": list(trace_extras["series_count_range"]),
                        "category_count": int(trace_extras["category_count"]),
                        "category_count_range": list(trace_extras["category_count_range"]),
                        "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    },
                },
                "render_spec": {
                    "canvas_width": int(render_params.canvas_width),
                    "canvas_height": int(render_params.canvas_height),
                    "coord_space": "pixel",
                    "scene_variant": str(scene_variant),
                    "background_style": dict(background_meta),
                    "post_image_noise": dict(post_noise_meta),
                    "layout_jitter": dict(render_params.layout_jitter_meta or {}),
                    "text_style": {
                        "label_font_size_px": int(render_params.label_font_size_px),
                        "tick_font_size_px": int(render_params.tick_font_size_px),
                        "label_stroke_width_px": int(render_params.label_stroke_width_px),
                    },
                    "axis_style": {
                        "axis_line_width_px": int(render_params.axis_line_width_px),
                        "grid_line_width_px": int(render_params.grid_line_width_px),
                        "tick_length_px": int(render_params.tick_length_px),
                    },
                    "mark_style": {
                        "sampling_policy": str(mark_style["sampling_policy"]),
                        **{str(key): value for key, value in mark_style.items()},
                    },
                    "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                    "y_axis_max": int(rendered_scene.y_axis_max),
                    "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                    **value_axis_render_metadata(rendered_scene),
                },
                "render_map": {
                    "image_id": "img0",
                    "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                    "category_label_centers_px": dict(category_label_centers),
                },
                "execution_trace": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "variant_family": str(family),
                    "internal_query_variant": str(pairwise_variant),
                    "answer_value": int(answer_value),
                    "evidence_labels": list(evidence_labels),
                    "category_labels": list(category_labels),
                    "series_labels": list(series_labels),
                    "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    "left_series_label": str(trace_extras["left_series_label"]),
                    "right_series_label": str(trace_extras["right_series_label"]),
                    "series_count": int(trace_extras["series_count"]),
                    "series_count_range": list(trace_extras["series_count_range"]),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "target_answer": int(trace_extras["target_answer"]),
                    "target_answer_range": list(trace_extras["target_answer_range"]),
                    "values_by_category": dict(trace_extras["values_by_category"]),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "comparison": str(comparison),
                    "comparison_probabilities": dict(comparison_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "question_format": "numeric_open",
                    "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                    **{str(key): value for key, value in mark_style.items() if key != "sampling_policy"},
                },
                "witness_symbolic": {
                    "type": "object_set",
                    "labels": list(evidence_labels),
                },
                "projected_evidence": {
                    "point_set": list(evidence_points),
                    **dict(evidence_projection),
                },
            }
            complexity = build_chart_complexity(
                weights=_COMPLEXITY_WEIGHTS,
                components={
                    "visual_scan": _normalize_multiseries_visual_scan(trace_extras),
                    "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_variant)]),
                    "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
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
                query_variant=str(query_variant),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
            )

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(task_key),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "left_series": str(trace_extras.get("left_series_label", "")),
                "right_series": str(trace_extras.get("right_series_label", "")),
                "target_series": str(trace_extras.get("target_series_label", "")),
                "numerator_series": str(trace_extras.get("numerator_series_label", "")),
                "denominator_series": str(trace_extras.get("denominator_series_label", "")),
                "rank": int(trace_extras["answer_rank"]),
                "rank_ordinal": _ordinal(int(trace_extras["answer_rank"])),
                "ranked_largest": _ranked_phrase(int(trace_extras["answer_rank"]), "largest"),
                "ranked_greatest": _ranked_phrase(int(trace_extras["answer_rank"]), "greatest"),
                "ranked_smallest": _ranked_phrase(int(trace_extras["answer_rank"]), "smallest"),
                **_change_prompt_slots(change_direction),
                **_change_measure_prompt_slots(change_measure, change_direction),
                **_extremum_prompt_slots(extremum_direction, answer_rank=int(trace_extras["answer_rank"])),
                **_ratio_measure_prompt_slots(
                    ratio_measure,
                    target_series=str(trace_extras.get("target_series_label", "")),
                    numerator_series=str(trace_extras.get("numerator_series_label", "")),
                    denominator_series=str(trace_extras.get("denominator_series_label", "")),
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        category_label_centers = {
            str(mark["category_label"]): list(mark["category_label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        evidence_series_labels = (
            list(series_labels)
            if str(trace_extras.get("calculation_scope", "")) in {"category_total_share", "category_total"}
            else [str(label) for label in trace_extras["queried_series_labels"]]
        )
        evidence_projection = projected_multiseries_mark_evidence(
            rendered_scene,
            [str(answer_label)],
            evidence_series_labels,
        )
        evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
        evidence_gt = TypedValue(type="point_set", value=evidence_points)

        optional_trace_keys = (
            "left_series_label",
            "right_series_label",
            "target_series_label",
            "numerator_series_label",
            "denominator_series_label",
            "score_percent_range",
            "category_total_range",
            "category_totals_by_category",
            "answer_score_percent",
            "denominator_values_by_category",
            "ratio_percent_by_category",
            "calculation_scope",
            "direction",
            "change_measure",
            "change_direction",
            "ratio_measure",
            "extremum_direction",
        )
        optional_trace = {
            str(key): trace_extras[key]
            for key in optional_trace_keys
            if key in trace_extras and trace_extras[key] is not None
        }
        if change_direction is not None:
            optional_trace["change_direction"] = str(change_direction)
        if change_measure is not None:
            optional_trace["change_measure"] = str(change_measure)
        if ratio_measure is not None:
            optional_trace["ratio_measure"] = str(ratio_measure)
        if extremum_direction is not None:
            optional_trace["extremum_direction"] = str(extremum_direction)
        if change_measure_probabilities:
            optional_trace["change_measure_probabilities"] = dict(change_measure_probabilities)
        if ratio_measure_probabilities:
            optional_trace["ratio_measure_probabilities"] = dict(ratio_measure_probabilities)
        if change_direction_probabilities:
            optional_trace["change_direction_probabilities"] = dict(change_direction_probabilities)
        if extremum_direction_probabilities:
            optional_trace["extremum_direction_probabilities"] = dict(extremum_direction_probabilities)

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_multiseries",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "variant_family": str(family),
                    "internal_query_variant": str(extremum_variant),
                    "answer_label": str(answer_label),
                    "evidence_values": [int(value) for value in evidence_values],
                    "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    "derived_metric": str(trace_extras["derived_metric"]),
                    "answer_rank": int(trace_extras["answer_rank"]),
                    **dict(optional_trace),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "variant_family": str(family),
                    "internal_query_variant": str(extremum_variant),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    **(
                        {"change_direction": str(change_direction)}
                        if change_direction is not None
                        else {}
                    ),
                    **(
                        {"extremum_direction": str(extremum_direction)}
                        if extremum_direction is not None
                        else {}
                    ),
                    **(
                        {"change_direction_probabilities": dict(change_direction_probabilities)}
                        if change_direction_probabilities
                        else {}
                    ),
                    **(
                        {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                        if extremum_direction_probabilities
                        else {}
                    ),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "series_count": int(trace_extras["series_count"]),
                    "series_count_range": list(trace_extras["series_count_range"]),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    "derived_metric": str(trace_extras["derived_metric"]),
                    "answer_rank": int(trace_extras["answer_rank"]),
                    "value_range": list(trace_extras["value_range"]),
                    **dict(optional_trace),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(render_params.layout_jitter_meta or {}),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "tick_font_size_px": int(render_params.tick_font_size_px),
                    "label_stroke_width_px": int(render_params.label_stroke_width_px),
                },
                "axis_style": {
                    "axis_line_width_px": int(render_params.axis_line_width_px),
                    "grid_line_width_px": int(render_params.grid_line_width_px),
                    "tick_length_px": int(render_params.tick_length_px),
                },
                "mark_style": {
                    "sampling_policy": str(mark_style["sampling_policy"]),
                    **{str(key): value for key, value in mark_style.items()},
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "category_label_centers_px": dict(category_label_centers),
            },
            "execution_trace": {
                "query_variant": str(query_variant),
                "scene_variant": str(scene_variant),
                "variant_family": str(family),
                "internal_query_variant": str(extremum_variant),
                "answer_label": str(answer_label),
                "answer_score": int(trace_extras["answer_score"]),
                "answer_rank": int(trace_extras["answer_rank"]),
                "evidence_values": [int(value) for value in evidence_values],
                "category_labels": list(category_labels),
                "series_labels": list(series_labels),
                "queried_series_labels": list(trace_extras["queried_series_labels"]),
                "series_count": int(trace_extras["series_count"]),
                "series_count_range": list(trace_extras["series_count_range"]),
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "value_range": list(trace_extras["value_range"]),
                "values_by_category": dict(trace_extras["values_by_category"]),
                "derived_values_by_category": dict(trace_extras["derived_values_by_category"]),
                "derived_metric": str(trace_extras["derived_metric"]),
                "rank_order": str(trace_extras["rank_order"]),
                "ranked_category_labels": list(trace_extras["ranked_category_labels"]),
                "query_variant_probabilities": dict(query_variant_probabilities),
                **(
                    {"change_direction": str(change_direction)}
                    if change_direction is not None
                    else {}
                ),
                **(
                    {"extremum_direction": str(extremum_direction)}
                    if extremum_direction is not None
                    else {}
                ),
                **(
                    {"change_direction_probabilities": dict(change_direction_probabilities)}
                    if change_direction_probabilities
                    else {}
                ),
                **(
                    {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                    if extremum_direction_probabilities
                    else {}
                ),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "label_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                **dict(optional_trace),
                **{str(key): value for key, value in mark_style.items() if key != "sampling_policy"},
            },
            "witness_symbolic": {
                "type": "numeric_sequence",
                "value": [int(value) for value in evidence_values],
                "answer_label": str(answer_label),
            },
            "projected_evidence": {
                "point_set": list(evidence_points),
                **dict(evidence_projection),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": _normalize_multiseries_visual_scan(trace_extras),
                "reasoning_load": (
                    0.85
                    * float(
                        _REASONING_LOAD_BY_MEASURE.get(
                            str(change_measure or ratio_measure),
                            _REASONING_LOAD_BY_VARIANT[str(query_variant)],
                        )
                    )
                    + 0.15
                    * normalize_int_with_bounds(
                        int(trace_extras["answer_rank"]),
                        (int(_GEN_DEFAULTS.get("rank_min", 1)), int(_GEN_DEFAULTS.get("rank_max", 3))),
                    )
                ),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
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
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsMultiseriesRankedMetricExtremumTask(
    MergedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Return the category label at a sampled ranked multiseries metric extremum."""

    task_id = "task_charts__multiseries__ranked_metric_extremum_label"
    allowed_query_variants = ("ranked_change_extremum", "ranked_ratio_extremum")


@register_task
class ChartsMultiseriesSeriesComparisonCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Count categories satisfying a pairwise series comparison."""

    task_id = "task_charts__multiseries__series_comparison_count"
    fixed_query_variant = "series_comparison_count"


@register_task
class ChartsMultiseriesCategoryTotalExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMultiseriesComparisonQueryTask,
):
    """Return a category label ranked by total across all series."""

    task_id = "task_charts__multiseries__category_total_extremum_label"
    fixed_query_variant = "category_total_extremum_label"


__all__ = [
    "ChartsMultiseriesComparisonQueryTask",
    "ChartsMultiseriesCategoryTotalExtremumLabelTask",
    "ChartsMultiseriesRankedMetricExtremumTask",
    "ChartsMultiseriesSeriesComparisonCountTask",
]
