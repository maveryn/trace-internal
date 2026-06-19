"""Public task for `task_charts__multiseries__series_comparison_count`."""
from __future__ import annotations

from typing import Any, Mapping

from ....core.query_ids import SINGLE_QUERY_ID
from ....core.types import TypedValue
from ._lifecycle import (
    MultiseriesTaskPlan,
    run_configured_multiseries_task,
)
from .shared.defaults import DEFAULTS, DOMAIN, GEN_DEFAULTS
from .shared.output import common_trace_fields
from ...registry import register_task
from .shared.data import build_pairwise_comparison_count_dataset
from .shared.prompts import build_prompt_artifacts, comparison_phrase, object_description
from .shared.sampling import (
    internal_pairwise_variant,
    params_for_variant_family,
    resolve_comparison,
    resolve_scene_variant,
    support_params_for_axis_cycle,
)


TASK_PARAM_DEFAULTS: dict[str, Any] = {
    "target_answer_min": 0,
    "target_answer_max": 8,
    "category_count_min": 12,
    "category_count_max": 18,
    "series_count_min": 3,
    "series_count_max": 5,
    "value_min": 1,
    "value_max": 99,
}


def _build_plan(instance_seed: int, params: Mapping[str, Any], selected_query_id: str) -> MultiseriesTaskPlan:
    """Bind the pairwise comparison-count objective before rendering."""

    comparison, comparison_probabilities = resolve_comparison(params, instance_seed=int(instance_seed))
    dataset_params = support_params_for_axis_cycle(
        params,
        probabilities=comparison_probabilities,
        supported_values=("greater_than", "less_than"),
        explicit_key="comparison",
        weights_key="comparison_weights",
        balance_flag_key="balanced_comparison_sampling",
    )
    internal_query_id = internal_pairwise_variant(str(comparison))
    scene_variant, scene_variant_probabilities = resolve_scene_variant(params, instance_seed=int(instance_seed))
    values_by_category, answer_value, annotation_labels, trace_extras = build_pairwise_comparison_count_dataset(
        variant_key=str(internal_query_id),
        params=params_for_variant_family(dataset_params, family="pairwise"),
        instance_seed=int(instance_seed),
        gen_defaults=GEN_DEFAULTS,
        defaults=DEFAULTS,
        namespace="series_comparison_count",
    )
    prompt_artifacts = build_prompt_artifacts(
        prompt_query_key="series_comparison_count",
        dynamic_slots={
            "object_description": object_description(str(scene_variant)),
            "left_series": str(trace_extras["left_series_label"]),
            "right_series": str(trace_extras["right_series_label"]),
            "comparison_phrase": comparison_phrase(str(comparison)),
        },
        instance_seed=int(instance_seed),
    )
    relations_extra = {
        "annotation_labels": list(annotation_labels),
        "queried_series_labels": list(trace_extras["queried_series_labels"]),
        "comparison": str(comparison),
        "comparison_probabilities": dict(comparison_probabilities),
    }
    query_params_extra = {
        "comparison": str(comparison),
        "comparison_probabilities": dict(comparison_probabilities),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "target_answer": int(trace_extras["target_answer"]),
        "target_answer_range": list(trace_extras["target_answer_range"]),
    }
    execution_extra = {
        "answer_value": int(answer_value),
        "annotation_labels": list(annotation_labels),
        "left_series_label": str(trace_extras["left_series_label"]),
        "right_series_label": str(trace_extras["right_series_label"]),
        "target_answer": int(trace_extras["target_answer"]),
        "target_answer_range": list(trace_extras["target_answer_range"]),
        "comparison": str(comparison),
        "comparison_probabilities": dict(comparison_probabilities),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
    }
    return MultiseriesTaskPlan(
        values_by_category=values_by_category,
        trace_extras=trace_extras,
        scene_variant=str(scene_variant),
        prompt_artifacts=prompt_artifacts,
        answer_gt=TypedValue(type="integer", value=int(answer_value)),
        answer_value=int(answer_value),
        annotation_category_labels=[str(label) for label in annotation_labels],
        annotation_series_labels=trace_extras["queried_series_labels"],
        variant_family="pairwise",
        internal_query_id=str(internal_query_id),
        question_format="numeric_open",
        relations_extra=relations_extra,
        query_params_extra=query_params_extra,
        execution_extra=execution_extra,
        witness_symbolic={"type": "object_set", "labels": list(annotation_labels)},
    )


@register_task
class ChartsMultiseriesSeriesComparisonCountTask:
    """Count category labels where one series is above or below another."""

    task_id = "task_charts__multiseries__series_comparison_count"
    domain = DOMAIN
    objective_contract = "series_comparison_count"
    supported_query_ids = (SINGLE_QUERY_ID,)
    default_dataset_enabled = True

    default_query_id = SINGLE_QUERY_ID
    task_param_defaults = TASK_PARAM_DEFAULTS
    _build_plan = staticmethod(_build_plan)

    def generate(self, instance_seed, *, params, max_attempts):
        return run_configured_multiseries_task(self, int(instance_seed), dict(params), int(max_attempts))


__all__ = ["ChartsMultiseriesSeriesComparisonCountTask"]
