"""Public task for `task_charts__combo_mark__cross_mark_difference_value`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64, spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.combo_mark.shared.annotations import keyed_point_artifacts
from trace.tasks.charts.combo_mark.shared.panel_common import DOMAIN, SCENE_ID
from trace.tasks.charts.combo_mark.shared.panel_sampling import (
    sample_base_dataset,
    select_cross_mark_difference,
)
from trace.tasks.charts.combo_mark.shared.prompts import build_prompt_artifacts
from trace.tasks.charts.combo_mark.shared.runtime import build_trace_scaffold, render_dataset
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


PRIMARY_MINUS_LINE_QUERY_ID = "primary_minus_line_at_label"
LINE_MINUS_PRIMARY_QUERY_ID = "line_minus_primary_at_label"
TASK_PARAM_DEFAULTS = {
    "label_count_min": 9,
    "label_count_max": 12,
}
ALLOWED_SCENE_VARIANTS = ("bar_line_shared_axis", "stacked_bar_line")


def _mode(selected_query_id: str) -> str:
    if str(selected_query_id) == PRIMARY_MINUS_LINE_QUERY_ID:
        return "primary_minus_line"
    if str(selected_query_id) == LINE_MINUS_PRIMARY_QUERY_ID:
        return "line_minus_primary"
    raise ValueError(f"unsupported combo difference query: {selected_query_id}")


@register_task
class ChartsComboCrossMarkDifferenceValueTask:
    """Compute the signed difference between primary and overlaid line marks at one label."""

    task_id = "task_charts__combo_mark__cross_mark_difference_value"
    domain = DOMAIN
    scene_id = SCENE_ID
    objective_contract = "cross_mark_difference_value"
    supported_query_ids = (PRIMARY_MINUS_LINE_QUERY_ID, LINE_MINUS_PRIMARY_QUERY_ID)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        dataset, dataset_trace = sample_base_dataset(
            params=effective_params,
            instance_seed=int(instance_seed),
            allowed_scene_variants=ALLOWED_SCENE_VARIANTS,
            label_count_bounds=(9, 12),
            scene_sampling_divisor=len(self.supported_query_ids),
        )
        artifacts = render_dataset(dataset=dataset, params=effective_params, instance_seed=int(instance_seed))
        selection = select_cross_mark_difference(
            artifacts.scene,
            mode=_mode(str(selected_query_id)),
            rng=spawn_rng(int(instance_seed), f"{self.task_id}.selection"),
        )
        annotation = keyed_point_artifacts(selection.annotation_points)
        dynamic_slots = {
            "primary_name": f'"{dataset.primary_name}"',
            "line_name": f'"{dataset.line_name}"',
            "target_label": f'"{selection.trace["target_label"]}"',
        }
        prompt_artifacts = build_prompt_artifacts(
            scene_variant=dataset.scene_variant,
            prompt_query_key=str(selected_query_id),
            dynamic_slots=dynamic_slots,
            instance_seed=int(instance_seed),
        )
        relations = {
            **dict(dataset_trace),
            **dict(selection.trace),
            "question_format": str(selection.question_format),
            "answer": int(selection.answer),
            "answer_type": str(selection.answer_type),
            "labels": list(dataset.labels),
            "primary_name": str(dataset.primary_name),
            "line_name": str(dataset.line_name),
            "primary_values": [int(value) for value in dataset.primary_values],
            "line_values": [int(value) for value in dataset.line_values],
        }
        trace_payload = build_trace_scaffold(
            artifacts=artifacts,
            annotation=annotation,
            relations=relations,
        )
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params={"query_id": str(selected_query_id), **relations},
        )
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(selection.answer)),
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
            default_query_id=PRIMARY_MINUS_LINE_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt == 0
                else int(hash64(int(instance_seed), "charts.combo_mark.retry", int(attempt)))
            )
            try:
                return self._generate_once(
                    int(attempt_seed),
                    params=task_params,
                    selected_query_id=str(selected_query_id),
                )
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsComboCrossMarkDifferenceValueTask"]
