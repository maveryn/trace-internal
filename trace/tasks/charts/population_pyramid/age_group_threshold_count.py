"""Population-pyramid age-group threshold count task."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.output import annotation_bboxes, build_trace_payload
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.pyramid import SCENE_ID, THRESHOLD_QUERY_IDS, _sample_dataset
from .shared.runtime import render_population_pyramid_dataset


TASK_PARAM_DEFAULTS: Dict[str, Any] = {}


@register_task
class ChartsPopulationPyramidAgeGroupThresholdCountTask:
    """Count age groups satisfying a side or combined-total threshold."""

    task_id = "task_charts__population_pyramid__age_group_threshold_count"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "age_group_threshold_count"
    supported_query_ids = THRESHOLD_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id="left_side_threshold_count",
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), self.task_id, attempt))
            try:
                return self._generate_once(
                    int(attempt_seed),
                    params=task_params,
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
        dataset = _sample_dataset(
            params,
            query_id=str(selected_query_id),
            query_id_probabilities=query_probabilities,
            instance_seed=int(instance_seed),
        )
        rendered = render_population_pyramid_dataset(dataset=dataset, params=params, instance_seed=int(instance_seed))
        boxes = annotation_bboxes(dataset=dataset, rendered=rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset=dataset),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_payload(
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            annotation_bboxes_px=boxes,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type="integer", value=int(dataset.query.answer)),
            annotation_gt=TypedValue(type="bbox_set", value=list(boxes)),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
        )


__all__ = ["ChartsPopulationPyramidAgeGroupThresholdCountTask"]
