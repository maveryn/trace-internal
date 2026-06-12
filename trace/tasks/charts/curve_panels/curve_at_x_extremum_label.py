"""Public task for `task_charts__curve_panels__curve_at_x_extremum_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.curve_panels.shared.multipanel_common import SCENE_ID
from trace.tasks.charts.curve_panels.shared.multipanel_datasets import build_curve_at_x_dataset
from trace.tasks.charts.curve_panels.shared.prompts import build_prompt_artifacts
from trace.tasks.charts.curve_panels.shared.runtime import (
    annotation_payload,
    build_trace_scaffold,
    render_dataset,
)
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


QUERY_ID = "curve_at_x_extremum_label"
TASK_PARAM_DEFAULTS: dict[str, Any] = {"panel_count_min": 6, "panel_count_max": 8, "method_count_min": 6, "method_count_max": 6, "x_tick_count_min": 8, "x_tick_count_max": 10, "curve_at_x_winner_min": 62, "curve_at_x_winner_max": 88, "curve_at_x_gap_min": 4, "curve_at_x_gap_max": 18}


@register_task
class ChartsScientificCurveAtXExtremumLabelTask:
    """Return the method label with the highest value at one x-position in one subplot."""

    task_id = "task_charts__curve_panels__curve_at_x_extremum_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "curve_at_x_extremum_label"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        dataset = build_curve_at_x_dataset(effective_params, instance_seed=int(instance_seed))
        rendered, chart_font_family = render_dataset(dataset, params=effective_params, instance_seed=int(instance_seed))
        annotation_type, annotation = annotation_payload(dataset, rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=QUERY_ID,
            dynamic_slots={
                "panel_label": f'"{dataset.query.panel_label}"',
                "x_value": str(dataset.query.x_value),
            },
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_scaffold(
            dataset=dataset,
            rendered=rendered,
            annotation_type=str(annotation_type),
            annotation=annotation,
            chart_font_family=str(chart_font_family),
            params=effective_params,
        )
        relation_params = {
            "query_id": str(selected_query_id),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "panel_count": int(len(dataset.panels)),
            "method_count": int(len(dataset.panels[0].curves)),
            "x_tick_count": int(len(dataset.x_values)),
            "threshold_direction": str(dataset.query.threshold_direction),
            "question_format": "curve_panels_subplot_query",
            **dict(dataset.query.trace),
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
            answer_gt=TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer),
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
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), "charts.curve_panels.retry", int(attempt_index)))
            try:
                return self._generate_once(int(attempt_seed), params=task_params, selected_query_id=str(selected_query_id))
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsScientificCurveAtXExtremumLabelTask"]
