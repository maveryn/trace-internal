"""Radar highlighted-metric threshold panel count task."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.annotations import annotation_for_query
from .shared.output import build_trace_payload
from .shared.profile_common import SCENE_ID
from .shared.profile_sampling import _build_highlighted_metric_threshold_dataset
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.runtime import render_radar_dataset


QUERY_ID = "highlighted_metric_threshold_panel_count"
TASK_PARAM_DEFAULTS: Dict[str, Any] = {}


@register_task
class ChartsRadarHighlightedMetricThresholdPanelCountTask:
    """Count radar panels where the highlighted metric satisfies a threshold."""

    task_id = "task_charts__radar__highlighted_metric_threshold_panel_count"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "highlighted_metric_threshold_panel_count"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), self.task_id, attempt_index))
            try:
                attempt_params = {**dict(task_params), "_attempt_index": int(attempt_index)}
                return self._generate_once(
                    int(attempt_seed),
                    params=attempt_params,
                    selected_query_id=str(selected_query_id),
                    query_probabilities=query_probabilities,
                )
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")

    def _generate_once(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        selected_query_id: str,
        query_probabilities: Dict[str, float],
    ) -> TaskOutput:
        dataset = _build_highlighted_metric_threshold_dataset(params, instance_seed=int(instance_seed))
        rendered = render_radar_dataset(dataset=dataset, params=params, instance_seed=int(instance_seed))
        annotation_type, annotation_value, projected_annotation = annotation_for_query(dataset, rendered.rendered_scene)
        if not annotation_value:
            raise RuntimeError(f"{self.task_id} produced empty annotation")
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset=dataset),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_payload(
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            query_id_probabilities=query_probabilities,
            annotation_type=str(annotation_type),
            annotation_value=list(annotation_value),
            projected_annotation=projected_annotation,
            params=params,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer),
            annotation_gt=TypedValue(type=str(annotation_type), value=list(annotation_value)),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
        )


__all__ = ["ChartsRadarHighlightedMetricThresholdPanelCountTask"]
