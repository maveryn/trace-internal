"""Return the category label at a ranked change or absolute-gap extremum."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions
from ...shared.fixed_query import select_task_query_id
from .shared.comparison_common import (
    CHANGE_QUERY_ID,
    DEFAULTS,
    GEN_DEFAULTS,
    REASONING_LOAD_BY_MEASURE,
    SCENE_ID,
)
from .shared.comparison_prompting import (
    change_measure_prompt_slots,
    change_prompt_slots,
    extremum_prompt_slots,
    ranked_phrase,
)
from .shared.comparison_sampling import (
    balance_answer_label_for_indexed_probe,
    internal_change_variant,
    params_for_variant_family,
    resolve_change_direction,
    resolve_change_measure,
    resolve_extremum_direction,
    resolve_scene_variant,
    support_params_for_axis_cycle,
)
from .shared.multiseries_derived_datasets import build_delta_extremum_label_dataset
from .shared.output import build_trace_payload
from .shared.prompts import build_prompt_artifacts, object_description
from .shared.runtime import mark_annotation_payload, render_multiseries_dataset


TASK_PARAM_DEFAULTS: Dict[str, Any] = {
    "value_window_span_min": 24,
    "value_window_span_max": 25,
    "delta_category_count_min": 10,
    "delta_category_count_max": 15,
    "delta_series_count_min": 3,
    "delta_series_count_max": 4,
    "delta_value_min": 1,
    "delta_value_max": 30,
    "rank_min": 1,
    "rank_max": 3,
    "derived_score_min": 4,
    "derived_score_max": 24,
    "score_spread_extra_min": 0,
    "score_spread_extra_max": 4,
}


def _reasoning_load(change_measure: str, trace_extras: Dict[str, Any]) -> float:
    rank_min = int(GEN_DEFAULTS.get("rank_min", TASK_PARAM_DEFAULTS["rank_min"]))
    rank_max = int(GEN_DEFAULTS.get("rank_max", TASK_PARAM_DEFAULTS["rank_max"]))
    return (
        0.85 * float(REASONING_LOAD_BY_MEASURE[str(change_measure)])
        + 0.15 * normalize_int_with_bounds(int(trace_extras["answer_rank"]), (rank_min, rank_max))
    )


@register_task
class ChartsMultiseriesRankedChangeExtremumTask:
    """Return the category label at a ranked change or absolute-gap extremum."""

    task_id = "task_charts__multiseries__ranked_change_extremum_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "ranked_change_extremum_label"
    supported_query_ids = (CHANGE_QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=CHANGE_QUERY_ID,
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
        change_measure, change_measure_probabilities = resolve_change_measure(params, instance_seed=int(instance_seed))
        dataset_params = support_params_for_axis_cycle(
            params,
            probabilities=change_measure_probabilities,
            supported_values=("directional_change", "absolute_gap"),
            explicit_key="change_measure",
            weights_key="change_measure_weights",
            balance_flag_key="balanced_change_measure_sampling",
        )
        change_direction = None
        change_direction_probabilities: Dict[str, float] = {}
        extremum_direction = None
        extremum_direction_probabilities: Dict[str, float] = {}
        if str(change_measure) == "directional_change":
            change_direction, change_direction_probabilities = resolve_change_direction(
                dataset_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = support_params_for_axis_cycle(
                dataset_params,
                probabilities=change_direction_probabilities,
                supported_values=("increase", "decrease"),
                explicit_key="change_direction",
                weights_key="change_direction_weights",
                balance_flag_key="balanced_change_direction_sampling",
            )
            prompt_query_key = "ranked_directional_change"
        else:
            extremum_direction, extremum_direction_probabilities = resolve_extremum_direction(
                dataset_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = support_params_for_axis_cycle(
                dataset_params,
                probabilities=extremum_direction_probabilities,
                supported_values=("largest", "smallest"),
                explicit_key="extremum_direction",
                weights_key="extremum_direction_weights",
                balance_flag_key="balanced_extremum_direction_sampling",
            )
            prompt_query_key = "ranked_absolute_gap"
        internal_query_id = internal_change_variant(
            change_measure=str(change_measure),
            change_direction=change_direction,
            extremum_direction=extremum_direction,
        )
        scene_variant, scene_variant_probabilities = resolve_scene_variant(params, instance_seed=int(instance_seed))
        values_by_category, answer_label, annotation_values, trace_extras = build_delta_extremum_label_dataset(
            query_id=str(internal_query_id),
            params=params_for_variant_family(dataset_params, family="delta"),
            instance_seed=int(instance_seed),
            gen_defaults=GEN_DEFAULTS,
            defaults=DEFAULTS,
            task_id=self.objective_contract,
        )
        values_by_category, answer_label, trace_extras = balance_answer_label_for_indexed_probe(
            namespace=self.objective_contract,
            params=dataset_params,
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
        answer_rank = int(trace_extras["answer_rank"])
        dynamic_slots = {
            "object_description": object_description(str(scene_variant)),
            "left_series": str(trace_extras.get("left_series_label", "")),
            "right_series": str(trace_extras.get("right_series_label", "")),
            "rank": answer_rank,
            "ranked_largest": ranked_phrase(answer_rank, "largest"),
            "ranked_greatest": ranked_phrase(answer_rank, "greatest"),
            **change_prompt_slots(change_direction),
            **change_measure_prompt_slots(change_measure, change_direction),
            **extremum_prompt_slots(extremum_direction, answer_rank=answer_rank),
        }
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(prompt_query_key),
            dynamic_slots=dynamic_slots,
            instance_seed=int(instance_seed),
        )
        optional_trace = {
            "left_series_label": str(trace_extras.get("left_series_label", "")),
            "right_series_label": str(trace_extras.get("right_series_label", "")),
            "change_measure": str(change_measure),
            "change_measure_probabilities": dict(change_measure_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "derived_metric": str(trace_extras["derived_metric"]),
            "answer_rank": answer_rank,
            "answer_score": int(trace_extras["answer_score"]),
            "rank_order": str(trace_extras["rank_order"]),
            "ranked_category_labels": list(trace_extras["ranked_category_labels"]),
            "derived_values_by_category": dict(trace_extras["derived_values_by_category"]),
        }
        if change_direction is not None:
            optional_trace["change_direction"] = str(change_direction)
            optional_trace["change_direction_probabilities"] = dict(change_direction_probabilities)
        if extremum_direction is not None:
            optional_trace["extremum_direction"] = str(extremum_direction)
            optional_trace["extremum_direction_probabilities"] = dict(extremum_direction_probabilities)
        trace_payload = build_trace_payload(
            result=rendered,
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            scene_variant=str(scene_variant),
            variant_family="delta",
            internal_query_id=str(internal_query_id),
            answer_value=str(answer_label),
            question_format="label_open",
            trace_extras=trace_extras,
            relations_extra={
                "answer_label": str(answer_label),
                "annotation_values": [int(value) for value in annotation_values],
                "queried_series_labels": list(trace_extras["queried_series_labels"]),
                **optional_trace,
            },
            query_params_extra={
                "answer_label": str(answer_label),
                "value_range": list(trace_extras["value_range"]),
                **optional_trace,
            },
            execution_extra={
                "answer_label": str(answer_label),
                "answer_type": "string",
                "annotation_values": [int(value) for value in annotation_values],
                **optional_trace,
            },
            witness_symbolic={
                "type": "numeric_sequence",
                "value": [int(value) for value in annotation_values],
                "answer_label": str(answer_label),
            },
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


__all__ = ["ChartsMultiseriesRankedChangeExtremumTask"]
