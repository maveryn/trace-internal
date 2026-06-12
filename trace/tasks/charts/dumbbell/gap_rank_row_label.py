"""Public task for `task_charts__dumbbell__gap_rank_row_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.dumbbell.shared.pairwise_comparison_query import SCENE_ID, build_dumbbell_dataset
from trace.tasks.charts.dumbbell.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.dumbbell.shared.runtime import (
    annotation_payload,
    answer_typed_value,
    build_trace_scaffold,
    render_dataset,
)
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


QUERY_ID = "gap_rank_row_label"
TASK_PARAM_DEFAULTS: dict[str, Any] = {"row_count_min": 10, "row_count_max": 12}


@register_task
class ChartsDumbbellGapRankRowLabelTask:
    """Return the row label at a requested absolute gap rank."""

    task_id = "task_charts__dumbbell__gap_rank_row_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "gap_rank_row_label"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        dataset = build_dumbbell_dataset(effective_params, instance_seed=int(instance_seed), prompt_key=str(selected_query_id))
        rendered, render_meta, sidecar_meta = render_dataset(dataset, params=effective_params, instance_seed=int(instance_seed))
        answer_gt = answer_typed_value(dataset)
        annotation_type, annotation, projected_annotation, annotation_refs = annotation_payload(dataset=dataset, rendered=rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_scaffold(
            dataset=dataset,
            rendered=rendered,
            render_meta=render_meta,
            sidecar_meta=sidecar_meta,
            projected_annotation=projected_annotation,
            annotation_refs=annotation_refs,
            answer_value=answer_gt.value,
        )
        relation_params = {
            "query_id": str(selected_query_id),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            **dict(dataset.query.params),
        }
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params=relation_params,
        )
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=TypedValue(type=str(annotation_type), value=annotation),
            image=rendered.image,
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
            default_query_id=QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), self.task_id, int(attempt_index)))
            try:
                return self._generate_once(int(attempt_seed), params=task_params, selected_query_id=str(selected_query_id))
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}") from last_error


__all__ = ["ChartsDumbbellGapRankRowLabelTask"]
