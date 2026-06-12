"""Public task for `task_charts__dashboard__dual_condition_count`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.dashboard.shared.cross_panel_common import SCENE_ID
from trace.tasks.charts.dashboard.shared.cross_panel_sampling import build_dual_condition_count_dataset
from trace.tasks.charts.dashboard.shared.prompts import build_prompt_artifacts, build_prompt_slots
from trace.tasks.charts.dashboard.shared.runtime import (
    annotation_payload,
    answer_typed_value,
    build_trace_scaffold,
    render_dataset,
)
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


QUERY_ID = "dual_condition_count"
TASK_PARAM_DEFAULTS: dict[str, Any] = {}
ANNOTATION_KIND = "point_set"


@register_task
class ChartsDashboardDualConditionCountTask:
    """Count categories satisfying two dashboard panel conditions."""

    task_id = "task_charts__dashboard__dual_condition_count"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "dual_condition_count"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        dataset = build_dual_condition_count_dataset(effective_params, instance_seed=int(instance_seed))
        rendered, render_meta, sidecar_meta = render_dataset(dataset, params=effective_params, instance_seed=int(instance_seed))
        answer_gt = answer_typed_value(dataset)
        annotation_type, annotation, projected_annotation, annotation_refs = annotation_payload(
            dataset=dataset,
            rendered=rendered,
            annotation_kind=ANNOTATION_KIND,
        )
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=QUERY_ID,
            dynamic_slots=build_prompt_slots(dataset=dataset),
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
            "question_format": "dashboard_cross_panel_query",
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
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), "charts.dashboard.retry", int(attempt_index)))
            try:
                return self._generate_once(int(attempt_seed), params=task_params, selected_query_id=str(selected_query_id))
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsDashboardDualConditionCountTask"]
