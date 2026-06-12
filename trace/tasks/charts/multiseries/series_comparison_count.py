"""Count categories satisfying a pairwise series comparison."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions
from ...shared.fixed_query import select_task_query_id
from .shared.comparison_common import (
    DEFAULTS,
    GEN_DEFAULTS,
    PAIRWISE_QUERY_ID,
    REASONING_LOAD_BY_OBJECTIVE,
    SCENE_ID,
)
from .shared.comparison_prompting import comparison_phrase
from .shared.comparison_sampling import (
    internal_pairwise_variant,
    params_for_variant_family,
    resolve_comparison,
    resolve_scene_variant,
    support_params_for_axis_cycle,
)
from .shared.multiseries_pair_datasets import build_pairwise_comparison_count_dataset
from .shared.output import build_trace_payload
from .shared.prompts import build_prompt_artifacts, object_description
from .shared.runtime import mark_annotation_payload, render_multiseries_dataset


TASK_PARAM_DEFAULTS: Dict[str, Any] = {
    "target_answer_min": 0,
    "target_answer_max": 8,
    "category_count_min": 12,
    "category_count_max": 18,
    "series_count_min": 3,
    "series_count_max": 5,
    "value_min": 1,
    "value_max": 99,
}


@register_task
class ChartsMultiseriesSeriesComparisonCountTask:
    """Count category labels where one series is above or below another."""

    task_id = "task_charts__multiseries__series_comparison_count"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "series_comparison_count"
    supported_query_ids = (PAIRWISE_QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=PAIRWISE_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), self.task_id, attempt))
            try:
                return self._generate_once(
                    int(attempt_seed),
                    params=task_params,
                    selected_query_id=str(selected_query_id),
                )
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any], selected_query_id: str) -> TaskOutput:
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
            query_id=str(internal_query_id),
            params=params_for_variant_family(dataset_params, family="pairwise"),
            instance_seed=int(instance_seed),
            gen_defaults=GEN_DEFAULTS,
            defaults=DEFAULTS,
            task_id=self.objective_contract,
        )
        rendered = render_multiseries_dataset(
            values_by_category=values_by_category,
            trace_extras=trace_extras,
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
        )
        annotation_points, projected_annotation = mark_annotation_payload(
            rendered_scene=rendered.rendered_scene,
            category_labels=annotation_labels,
            series_labels=trace_extras["queried_series_labels"],
        )
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=PAIRWISE_QUERY_ID,
            dynamic_slots={
                "object_description": object_description(str(scene_variant)),
                "left_series": str(trace_extras["left_series_label"]),
                "right_series": str(trace_extras["right_series_label"]),
                "comparison_phrase": comparison_phrase(str(comparison)),
            },
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_payload(
            result=rendered,
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            scene_variant=str(scene_variant),
            variant_family="pairwise",
            internal_query_id=str(internal_query_id),
            answer_value=int(answer_value),
            question_format="numeric_open",
            trace_extras=trace_extras,
            relations_extra={
                "annotation_labels": list(annotation_labels),
                "queried_series_labels": list(trace_extras["queried_series_labels"]),
                "comparison": str(comparison),
                "comparison_probabilities": dict(comparison_probabilities),
            },
            query_params_extra={
                "comparison": str(comparison),
                "comparison_probabilities": dict(comparison_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
            },
            execution_extra={
                "answer_value": int(answer_value),
                "annotation_labels": list(annotation_labels),
                "left_series_label": str(trace_extras["left_series_label"]),
                "right_series_label": str(trace_extras["right_series_label"]),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
                "comparison": str(comparison),
                "comparison_probabilities": dict(comparison_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
            },
            witness_symbolic={"type": "object_set", "labels": list(annotation_labels)},
            projected_annotation=projected_annotation,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_points)),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["ChartsMultiseriesSeriesComparisonCountTask"]
