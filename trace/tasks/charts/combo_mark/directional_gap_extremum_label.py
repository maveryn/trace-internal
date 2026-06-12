"""Public task for `task_charts__combo_mark__directional_gap_extremum_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.combo_mark.shared.annotations import keyed_point_artifacts
from trace.tasks.charts.combo_mark.shared.panel_common import DOMAIN, SCENE_ID
from trace.tasks.charts.combo_mark.shared.panel_sampling import sample_base_dataset, select_gap_extremum
from trace.tasks.charts.combo_mark.shared.prompts import build_prompt_artifacts
from trace.tasks.charts.combo_mark.shared.runtime import build_trace_scaffold, render_dataset
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


PRIMARY_OVER_LINE_QUERY_ID = "largest_primary_over_line_gap_label"
LINE_OVER_PRIMARY_QUERY_ID = "largest_line_over_primary_gap_label"


def _gap_mode(selected_query_id: str) -> str:
    if str(selected_query_id) == PRIMARY_OVER_LINE_QUERY_ID:
        return "largest_primary_over_line"
    if str(selected_query_id) == LINE_OVER_PRIMARY_QUERY_ID:
        return "largest_line_over_primary"
    raise ValueError(f"unsupported directional-gap query: {selected_query_id}")


@register_task
class ChartsComboDirectionalGapExtremumLabelTask:
    """Find the category with the largest directional gap between the two encodings."""

    task_id = "task_charts__combo_mark__directional_gap_extremum_label"
    domain = DOMAIN
    scene_id = SCENE_ID
    objective_contract = "directional_gap_extremum_label"
    supported_query_ids = (PRIMARY_OVER_LINE_QUERY_ID, LINE_OVER_PRIMARY_QUERY_ID)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        dataset, dataset_trace = sample_base_dataset(
            params=params,
            instance_seed=int(instance_seed),
            scene_sampling_divisor=len(self.supported_query_ids),
        )
        artifacts = render_dataset(dataset=dataset, params=params, instance_seed=int(instance_seed))
        selection = select_gap_extremum(artifacts.scene, gap_mode=_gap_mode(str(selected_query_id)))
        annotation = keyed_point_artifacts(selection.annotation_points)
        prompt_artifacts = build_prompt_artifacts(
            scene_variant=dataset.scene_variant,
            prompt_query_key=str(selected_query_id),
            dynamic_slots={
                "primary_name": f'"{dataset.primary_name}"',
                "line_name": f'"{dataset.line_name}"',
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
            default_query_id=PRIMARY_OVER_LINE_QUERY_ID,
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


__all__ = ["ChartsComboDirectionalGapExtremumLabelTask"]
