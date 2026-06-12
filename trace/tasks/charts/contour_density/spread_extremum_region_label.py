"""Public task for `task_charts__contour_density__spread_extremum_region_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.contour_density.shared.field_query import (
    SCENE_ID,
    annotation_value,
    answer_value,
    build_spread_extremum_dataset,
    build_trace_scaffold,
    render_dataset,
)
from trace.tasks.charts.contour_density.shared.prompts import build_prompt_artifacts
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


QUERY_ID = "spread_extremum_region_label"


@register_task
class ChartsContourDensitySpreadExtremumRegionLabelTask:
    """Return the region label with the widest or narrowest visible footprint."""

    task_id = "task_charts__contour_density__spread_extremum_region_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "spread_extremum_region_label"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        dataset = build_spread_extremum_dataset(params, instance_seed=int(instance_seed))
        rendered, chart_font_family = render_dataset(dataset, params=params, instance_seed=int(instance_seed))
        annotation = annotation_value(dataset, rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=QUERY_ID,
            dynamic_slots={"spread_extremum_phrase": str(dataset.query.trace["spread_extremum_phrase"])},
            instance_seed=int(instance_seed),
        )
        resolved_answer = answer_value(dataset)
        annotation_gt = TypedValue(type="keyed_bbox_map", value={key: list(value) for key, value in annotation.items()})
        trace_payload = build_trace_scaffold(
            dataset=dataset,
            rendered=rendered,
            annotation=annotation,
            chart_font_family=str(chart_font_family),
        )
        relation_params = {
            "query_id": str(selected_query_id),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "region_count": int(len(dataset.regions)),
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
            answer_gt=TypedValue(type=str(dataset.query.answer_type), value=resolved_answer),
            annotation_gt=annotation_gt,
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
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), "charts.contour_density.retry", int(attempt_index)))
            try:
                return self._generate_once(int(attempt_seed), params=task_params, selected_query_id=str(selected_query_id))
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsContourDensitySpreadExtremumRegionLabelTask"]
