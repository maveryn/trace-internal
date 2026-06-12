"""Public task for `task_charts__combo_mark__series_threshold_crossing_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.combo_mark.shared.annotations import keyed_point_artifacts
from trace.tasks.charts.combo_mark.shared.panel_common import DOMAIN, SCENE_ID
from trace.tasks.charts.combo_mark.shared.panel_sampling import (
    construct_threshold_crossing_values,
    dataset_with_values,
    sample_base_dataset,
    select_threshold_crossing,
)
from trace.tasks.charts.combo_mark.shared.prompts import build_prompt_artifacts
from trace.tasks.charts.combo_mark.shared.runtime import build_trace_scaffold, render_dataset
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


PRIMARY_ABOVE_QUERY_ID = "primary_first_above_threshold_label"
PRIMARY_BELOW_QUERY_ID = "primary_first_below_threshold_label"
LINE_ABOVE_QUERY_ID = "line_first_above_threshold_label"
LINE_BELOW_QUERY_ID = "line_first_below_threshold_label"
TASK_PARAM_DEFAULTS = {
    "crossing_index_min": 2,
    "crossing_index_max": 8,
}


def _target_role_and_direction(selected_query_id: str) -> tuple[str, bool]:
    if str(selected_query_id) == PRIMARY_ABOVE_QUERY_ID:
        return "primary", True
    if str(selected_query_id) == PRIMARY_BELOW_QUERY_ID:
        return "primary", False
    if str(selected_query_id) == LINE_ABOVE_QUERY_ID:
        return "line", True
    if str(selected_query_id) == LINE_BELOW_QUERY_ID:
        return "line", False
    raise ValueError(f"unsupported threshold-crossing query: {selected_query_id}")


@register_task
class ChartsComboSeriesThresholdCrossingLabelTask:
    """Return the first category where one combo series crosses a threshold."""

    task_id = "task_charts__combo_mark__series_threshold_crossing_label"
    domain = DOMAIN
    scene_id = SCENE_ID
    objective_contract = "series_threshold_crossing_label"
    supported_query_ids = (
        PRIMARY_ABOVE_QUERY_ID,
        PRIMARY_BELOW_QUERY_ID,
        LINE_ABOVE_QUERY_ID,
        LINE_BELOW_QUERY_ID,
    )
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        target_role, above = _target_role_and_direction(str(selected_query_id))
        dataset, dataset_trace = sample_base_dataset(
            params=effective_params,
            instance_seed=int(instance_seed),
            scene_sampling_divisor=len(self.supported_query_ids),
        )
        value_min, value_max = [int(value) for value in dataset_trace["value_range"]]
        crossing_values, crossing_trace = construct_threshold_crossing_values(
            target_role=str(target_role),
            above=bool(above),
            label_count=len(dataset.labels),
            value_min=int(value_min),
            value_max=int(value_max),
            params=effective_params,
            instance_seed=int(instance_seed),
            target_sampling_divisor=len(self.supported_query_ids),
        )
        if str(target_role) == "primary":
            dataset = dataset_with_values(dataset, primary_values=crossing_values)
        else:
            dataset = dataset_with_values(dataset, line_values=crossing_values)
        artifacts = render_dataset(dataset=dataset, params=effective_params, instance_seed=int(instance_seed))
        selection = select_threshold_crossing(
            artifacts.scene,
            target_role=str(target_role),
            above=bool(above),
            crossing_trace=crossing_trace,
        )
        annotation = keyed_point_artifacts(selection.annotation_points)
        prompt_artifacts = build_prompt_artifacts(
            scene_variant=dataset.scene_variant,
            prompt_query_key=str(selected_query_id),
            dynamic_slots={
                "primary_name": f'"{dataset.primary_name}"',
                "line_name": f'"{dataset.line_name}"',
                "target_series_name": f'"{selection.trace["target_series_name"]}"',
                "threshold_value": str(selection.trace["threshold_value"]),
                "comparison_phrase": str(selection.trace["comparison_phrase"]),
            },
            instance_seed=int(instance_seed),
        )
        relations = {
            **dict(dataset_trace),
            **dict(selection.trace),
            "question_format": str(selection.question_format),
            "answer": str(selection.answer),
            "answer_type": str(selection.answer_type),
            "labels": list(dataset.labels),
            "primary_name": str(dataset.primary_name),
            "line_name": str(dataset.line_name),
            "primary_values": [int(value) for value in dataset.primary_values],
            "line_values": [int(value) for value in dataset.line_values],
        }
        trace_payload = build_trace_scaffold(artifacts=artifacts, annotation=annotation, relations=relations)
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params={"query_id": str(selected_query_id), **relations},
        )
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(selection.answer)),
            annotation_gt=annotation.annotation_gt,
            image=artifacts.scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=PRIMARY_ABOVE_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.combo_mark.retry", int(attempt)))
            try:
                return self._generate_once(int(attempt_seed), params=task_params, selected_query_id=str(selected_query_id))
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsComboSeriesThresholdCrossingLabelTask"]
