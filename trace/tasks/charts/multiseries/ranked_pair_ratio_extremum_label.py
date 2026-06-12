"""Return the category label at a ranked pair-ratio extremum."""

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
    RATIO_QUERY_ID,
    REASONING_LOAD_BY_MEASURE,
    SCENE_ID,
)
from .shared.comparison_prompting import extremum_prompt_slots, ratio_measure_prompt_slots
from .shared.comparison_sampling import (
    balance_answer_label_for_indexed_probe,
    internal_ratio_variant,
    params_for_variant_family,
    resolve_extremum_direction,
    resolve_scene_variant,
    support_params_for_axis_cycle,
)
from .shared.multiseries_derived_datasets import build_ratio_extremum_label_dataset
from .shared.output import build_trace_payload
from .shared.prompts import build_prompt_artifacts, object_description
from .shared.runtime import mark_annotation_payload, render_multiseries_dataset


TASK_PARAM_DEFAULTS: Dict[str, Any] = {
    "ratio_category_count_min": 5,
    "ratio_category_count_max": 10,
    "ratio_series_count_min": 3,
    "ratio_series_count_max": 4,
    "ratio_value_min": 1,
    "ratio_value_max": 80,
    "rank_min": 1,
    "rank_max": 3,
    "pair_ratio_percent_min": 40,
    "pair_ratio_percent_max": 260,
    "ratio_score_spread_extra_min": 0,
    "ratio_score_spread_extra_max": 6,
}


def _reasoning_load(trace_extras: Dict[str, Any]) -> float:
    rank_min = int(GEN_DEFAULTS.get("rank_min", TASK_PARAM_DEFAULTS["rank_min"]))
    rank_max = int(GEN_DEFAULTS.get("rank_max", TASK_PARAM_DEFAULTS["rank_max"]))
    return (
        0.85 * float(REASONING_LOAD_BY_MEASURE["pair_ratio"])
        + 0.15 * normalize_int_with_bounds(int(trace_extras["answer_rank"]), (rank_min, rank_max))
    )


@register_task
class ChartsMultiseriesRankedPairRatioExtremumTask:
    """Return the category label ranked by numerator-over-denominator ratio."""

    task_id = "task_charts__multiseries__ranked_pair_ratio_extremum_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "ranked_pair_ratio_extremum_label"
    supported_query_ids = (RATIO_QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=RATIO_QUERY_ID,
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
        extremum_direction, extremum_probabilities = resolve_extremum_direction(params, instance_seed=int(instance_seed))
        dataset_params = support_params_for_axis_cycle(
            {**dict(params), "ratio_measure": "pair_ratio"},
            probabilities=extremum_probabilities,
            supported_values=("largest", "smallest"),
            explicit_key="extremum_direction",
            weights_key="extremum_direction_weights",
            balance_flag_key="balanced_extremum_direction_sampling",
        )
        internal_query_id = internal_ratio_variant(ratio_measure="pair_ratio", extremum_direction=str(extremum_direction))
        scene_variant, scene_variant_probabilities = resolve_scene_variant(params, instance_seed=int(instance_seed))
        values_by_category, answer_label, annotation_values, trace_extras = build_ratio_extremum_label_dataset(
            query_id=str(internal_query_id),
            params=params_for_variant_family(dataset_params, family="ratio"),
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
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key="ranked_pair_ratio",
            dynamic_slots={
                "object_description": object_description(str(scene_variant)),
                "rank": answer_rank,
                "numerator_series": str(trace_extras.get("numerator_series_label", "")),
                "denominator_series": str(trace_extras.get("denominator_series_label", "")),
                **extremum_prompt_slots(str(extremum_direction), answer_rank=answer_rank),
                **ratio_measure_prompt_slots(
                    "pair_ratio",
                    target_series=str(trace_extras.get("target_series_label", "")),
                    numerator_series=str(trace_extras.get("numerator_series_label", "")),
                    denominator_series=str(trace_extras.get("denominator_series_label", "")),
                ),
            },
            instance_seed=int(instance_seed),
        )
        optional_trace = {
            "ratio_measure": "pair_ratio",
            "extremum_direction": str(extremum_direction),
            "extremum_direction_probabilities": dict(extremum_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "numerator_series_label": str(trace_extras.get("numerator_series_label", "")),
            "denominator_series_label": str(trace_extras.get("denominator_series_label", "")),
            "answer_rank": answer_rank,
            "answer_score": int(trace_extras["answer_score"]),
            "derived_metric": str(trace_extras["derived_metric"]),
            "rank_order": str(trace_extras["rank_order"]),
            "ranked_category_labels": list(trace_extras["ranked_category_labels"]),
            "derived_values_by_category": dict(trace_extras["derived_values_by_category"]),
            "ratio_percent_by_category": dict(trace_extras.get("ratio_percent_by_category", {})),
            "denominator_values_by_category": dict(trace_extras.get("denominator_values_by_category", {})),
        }
        trace_payload = build_trace_payload(
            result=rendered,
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            scene_variant=str(scene_variant),
            variant_family="ratio",
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


__all__ = ["ChartsMultiseriesRankedPairRatioExtremumTask"]
