"""Public task for `task_charts__waterfall__threshold_crossing_label`."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.charts.shared.unanswerable import UNANSWERABLE_ANSWER, absence_proof, should_use_unanswerable_branch
from trace.tasks.charts.waterfall._lifecycle import WaterfallTaskPlan, run_waterfall_lifecycle
from trace.tasks.charts.waterfall.shared.annotations import bbox_set_map_artifacts
from trace.tasks.charts.waterfall.shared.defaults import DOMAIN
from trace.tasks.charts.waterfall.shared.sampling import sample_waterfall_dataset, threshold_options
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.registry import register_task


TASK_ID = "task_charts__waterfall__threshold_crossing_label"
OBJECTIVE_CONTRACT = "threshold_crossing_label"
AT_LEAST_QUERY_ID = "first_total_at_least_threshold"
AT_MOST_QUERY_ID = "first_total_at_most_threshold"
SUPPORTED_QUERY_IDS = (AT_LEAST_QUERY_ID, AT_MOST_QUERY_ID)
DEFAULT_QUERY_ID = AT_LEAST_QUERY_ID
_DIRECTION_BY_QUERY = {AT_LEAST_QUERY_ID: "at_least", AT_MOST_QUERY_ID: "at_most"}
_RELATION_PHRASE_BY_DIRECTION = {"at_least": "at least", "at_most": "at most"}


def _first_crossing_plan(dataset, direction, params, instance_seed, selected_branch):
    options = threshold_options(dataset, direction=str(direction))
    if not options:
        raise ValueError(f"no feasible waterfall threshold crossing for {selected_branch}")
    option_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_branch}.target",
    )
    crossing_index, threshold_value = options[int(option_index) % len(options)]
    crossing_step = dataset.steps[int(crossing_index)]
    running_ids = ("start",) + tuple(step.step_id for step in dataset.steps[: int(crossing_index) + 1])
    return int(crossing_index), int(threshold_value), crossing_step, running_ids


def _unanswerable_threshold(dataset, direction):
    totals = [int(step.running_after) for step in dataset.steps]
    if str(direction) == "at_least":
        return int(max(totals) + 1)
    return int(min(totals) - 1)


def _build_plan(params, instance_seed, selected_branch, query_probabilities):
    """Bind threshold-crossing semantics and preserve answerability metadata."""

    if str(selected_branch) not in _DIRECTION_BY_QUERY:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
    direction = str(_DIRECTION_BY_QUERY[str(selected_branch)])
    relation_phrase = str(_RELATION_PHRASE_BY_DIRECTION[str(direction)])
    dataset = sample_waterfall_dataset(params, instance_seed=int(instance_seed))
    use_unanswerable = should_use_unanswerable_branch(
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_branch}",
        enabled=True,
    )

    if use_unanswerable:
        threshold_value = _unanswerable_threshold(dataset, direction)

        def _bind_empty_annotation(rendered):
            return bbox_set_map_artifacts({})

        proof = absence_proof(
            requested_item=f"first contribution step with running total {relation_phrase} {threshold_value}",
            visible_candidates=[str(step.label) for step in dataset.steps],
            checked_scope="waterfall contribution steps and running totals",
            absence_reason="no contribution step makes the running total satisfy the threshold rule",
        )
        return WaterfallTaskPlan(
            dataset=dataset,
            answer_gt=TypedValue(type="string", value=UNANSWERABLE_ANSWER),
            annotation_builder=_bind_empty_annotation,
            prompt_query_key=str(selected_branch),
            dynamic_slots={
                "threshold_relation_phrase": relation_phrase,
                "threshold_value": int(threshold_value),
            },
            query_params={
                "threshold_direction": str(direction),
                "threshold_value": int(threshold_value),
                "answerability": "unanswerable",
                "absence_proof": dict(proof),
            },
            relations={
                "threshold_direction": str(direction),
                "threshold_value": int(threshold_value),
                "answerability": "unanswerable",
                "absence_proof": dict(proof),
                "query_id_probabilities": dict(query_probabilities),
            },
            witness_symbolic={
                "type": "waterfall_threshold_absence_witness",
                "answerability": "unanswerable",
                "absence_proof": dict(proof),
            },
            question_format="waterfall_threshold_crossing_label",
            threshold_value=int(threshold_value),
        )

    answer_index, threshold_value, answer_step, running_ids = _first_crossing_plan(
        dataset,
        direction,
        params,
        int(instance_seed),
        str(selected_branch),
    )

    def _bind_annotation(rendered):
        return bbox_set_map_artifacts(
            {
                "running_values": [rendered.value_label_bboxes_px[str(bar_id)] for bar_id in running_ids],
                "threshold_label": [rendered.extra_bboxes_px["threshold_label"]],
            }
        )

    return WaterfallTaskPlan(
        dataset=dataset,
        answer_gt=TypedValue(type="string", value=str(answer_step.label)),
        annotation_builder=_bind_annotation,
        prompt_query_key=str(selected_branch),
        dynamic_slots={
            "threshold_relation_phrase": relation_phrase,
            "threshold_value": int(threshold_value),
        },
        query_params={
            "threshold_direction": str(direction),
            "threshold_value": int(threshold_value),
            "answer_step_id": str(answer_step.step_id),
            "answer_step_label": str(answer_step.label),
            "answer_step_index": int(answer_index),
            "answerability": "answerable",
            "annotation_roles": {
                "running_values": list(running_ids),
                "threshold_label": ["threshold_label"],
            },
        },
        relations={
            "threshold_direction": str(direction),
            "threshold_value": int(threshold_value),
            "answer_step_id": str(answer_step.step_id),
            "answer_step_label": str(answer_step.label),
            "answer_step_index": int(answer_index),
            "answerability": "answerable",
            "query_id_probabilities": dict(query_probabilities),
        },
        witness_symbolic={
            "type": "waterfall_threshold_crossing_witness",
            "running_value_bar_ids": list(running_ids),
            "threshold_label": "threshold_label",
            "answer_step_id": str(answer_step.step_id),
            "answer": str(answer_step.label),
        },
        question_format="waterfall_threshold_crossing_label",
        threshold_value=int(threshold_value),
    )


class ChartsWaterfallThresholdCrossingLabelTask:
    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = OBJECTIVE_CONTRACT
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return run_waterfall_lifecycle(
            task=self,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            default_query_id=DEFAULT_QUERY_ID,
            build_plan=_build_plan,
        )


register_task(ChartsWaterfallThresholdCrossingLabelTask)


__all__ = ["ChartsWaterfallThresholdCrossingLabelTask"]
