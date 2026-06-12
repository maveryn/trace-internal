"""Return the category label where two series have equal values."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions
from ...shared.fixed_query import select_task_query_id
from .shared.comparison_common import DEFAULTS, EQUALITY_QUERY_ID, GEN_DEFAULTS, REASONING_LOAD_BY_OBJECTIVE, SCENE_ID
from .shared.comparison_sampling import (
    balance_answer_label_for_indexed_probe,
    params_for_variant_family,
    resolve_scene_variant,
)
from .shared.multiseries_pair_datasets import build_pair_equality_label_dataset
from .shared.output import build_trace_payload
from .shared.prompts import build_prompt_artifacts, object_description
from .shared.runtime import mark_annotation_payload, render_multiseries_dataset


TASK_PARAM_DEFAULTS: Dict[str, Any] = {
    "equality_category_count_min": 6,
    "equality_category_count_max": 12,
    "equality_series_count_min": 3,
    "equality_series_count_max": 5,
    "equality_value_min": 1,
    "equality_value_max": 99,
}


@register_task
class ChartsMultiseriesPairEqualityLabelTask:
    """Return the unique category where two queried series match exactly."""

    task_id = "task_charts__multiseries__pair_equality_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "pair_equality_label"
    supported_query_ids = (EQUALITY_QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=EQUALITY_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), self.task_id, attempt))
            try:
                return self._generate_once(int(attempt_seed), params=task_params, selected_query_id=str(selected_query_id))
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any], selected_query_id: str) -> TaskOutput:
        scene_variant, scene_variant_probabilities = resolve_scene_variant(params, instance_seed=int(instance_seed))
        values_by_category, answer_label, annotation_values, trace_extras = build_pair_equality_label_dataset(
            query_id=EQUALITY_QUERY_ID,
            params=params_for_variant_family(params, family="equality"),
            instance_seed=int(instance_seed),
            gen_defaults=GEN_DEFAULTS,
            defaults=DEFAULTS,
            task_id=self.objective_contract,
        )
        values_by_category, answer_label, trace_extras = balance_answer_label_for_indexed_probe(
            namespace=self.objective_contract,
            params=params,
            instance_seed=int(instance_seed),
            values_by_category=values_by_category,
            answer_label=str(answer_label),
            trace_extras=trace_extras,
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
            category_labels=[str(answer_label)],
            series_labels=trace_extras["queried_series_labels"],
        )
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=EQUALITY_QUERY_ID,
            dynamic_slots={
                "object_description": object_description(str(scene_variant)),
                "left_series": str(trace_extras["left_series_label"]),
                "right_series": str(trace_extras["right_series_label"]),
            },
            instance_seed=int(instance_seed),
        )
        optional_trace = {
            "left_series_label": str(trace_extras["left_series_label"]),
            "right_series_label": str(trace_extras["right_series_label"]),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "answer_rank": int(trace_extras["answer_rank"]),
            "answer_score": int(trace_extras["answer_score"]),
            "answer_equal_value": int(trace_extras["answer_equal_value"]),
            "derived_metric": str(trace_extras["derived_metric"]),
            "rank_order": str(trace_extras["rank_order"]),
            "ranked_category_labels": list(trace_extras["ranked_category_labels"]),
            "equality_by_category": dict(trace_extras["equality_by_category"]),
            "derived_values_by_category": dict(trace_extras["derived_values_by_category"]),
        }
        trace_payload = build_trace_payload(
            result=rendered,
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            scene_variant=str(scene_variant),
            variant_family="equality",
            internal_query_id=EQUALITY_QUERY_ID,
            answer_value=str(answer_label),
            question_format="label_open",
            trace_extras=trace_extras,
            relations_extra={"answer_label": str(answer_label), "annotation_values": [int(value) for value in annotation_values], "queried_series_labels": list(trace_extras["queried_series_labels"]), **optional_trace},
            query_params_extra={"answer_label": str(answer_label), "value_range": list(trace_extras["value_range"]), **optional_trace},
            execution_extra={"answer_label": str(answer_label), "answer_type": "string", "annotation_values": [int(value) for value in annotation_values], **optional_trace},
            witness_symbolic={"type": "numeric_sequence", "value": [int(value) for value in annotation_values], "answer_label": str(answer_label)},
            projected_annotation=projected_annotation,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(answer_label)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_points)),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["ChartsMultiseriesPairEqualityLabelTask"]
