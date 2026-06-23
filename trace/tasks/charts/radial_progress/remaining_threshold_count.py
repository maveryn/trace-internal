from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from ._lifecycle import build_count_dataset_from_frame, build_count_plan, run_radial_progress_task
from .shared.sampling import (
    sample_answer_count,
    sample_condition_values,
    sample_progress_frame,
    sample_threshold,
)
from .shared.state import DOMAIN


TASK_ID = "task_charts__radial_progress__remaining_threshold_count"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)


def _build_plan(params, instance_seed, selected, probabilities):
    """Bind a remaining-progress threshold and construct the exact matching count."""

    frame = sample_progress_frame(params, instance_seed=int(instance_seed))
    answer_count, answer_support, answer_probabilities = sample_answer_count(
        params,
        item_count=int(frame.item_count),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.answer_count",
    )
    threshold = sample_threshold(params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.threshold")
    values, annotation_item_ids = sample_condition_values(
        item_count=int(frame.item_count),
        answer_count=int(answer_count),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.values",
        target_predicate=lambda value: int(100 - int(value)) >= int(threshold),
    )
    dataset = build_count_dataset_from_frame(
        frame=frame,
        values=values,
        branch_id=SINGLE_QUERY_ID,
        branch_probabilities=dict(probabilities),
        answer_count=int(answer_count),
        answer_support=list(answer_support),
        answer_probabilities=dict(answer_probabilities),
        annotation_type="bbox_set",
        annotation_item_ids=tuple(annotation_item_ids),
        question_params={
            "threshold_value": int(threshold),
            "threshold_phrase": f"at least {threshold}% remaining",
            "count_condition": "remaining_at_least_threshold",
            "max_value_for_remaining": int(100 - int(threshold)),
        },
    )
    return build_count_plan(
        dataset=dataset,
        prompt_key="remaining_at_least_threshold_count",
        scene_probabilities=dict(frame.scene_probabilities),
    )


@register_task
class ChartsRadialProgressRemainingThresholdCountTask:
    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = "remaining_threshold_count"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SINGLE_QUERY_ID
    default_dataset_enabled = True
    _build_plan = staticmethod(_build_plan)

    def generate(self, instance_seed, *, params, max_attempts):
        return run_radial_progress_task(self, int(instance_seed), dict(params), int(max_attempts))


__all__ = ["ChartsRadialProgressRemainingThresholdCountTask", "SUPPORTED_QUERY_IDS"]
