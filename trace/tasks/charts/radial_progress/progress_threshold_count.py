"""Radial-progress threshold count task."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.output import annotation_payload, build_trace_payload
from .shared.progress_chart import SCENE_ID, _construct_dataset, _resolve_scene_variant
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.runtime import render_radial_progress_dataset


SUPPORTED_QUERY_IDS = ("at_least_threshold_count", "below_threshold_count")
TASK_PARAM_DEFAULTS: Dict[str, Any] = {}


@register_task
class ChartsRadialProgressThresholdCountTask:
    """Count radial progress widgets satisfying a progress threshold."""

    task_id = "task_charts__radial_progress__progress_threshold_count"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "progress_threshold_count"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id="at_least_threshold_count",
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
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = _construct_dataset(
            query_id=str(selected_query_id),
            query_probabilities=query_probabilities,
            scene_variant=str(scene_variant),
            scene_variant_probabilities=scene_variant_probabilities,
            params=params,
            instance_seed=int(instance_seed),
        )
        rendered = render_radial_progress_dataset(dataset=dataset, params=params, instance_seed=int(instance_seed))
        annotation = annotation_payload(dataset=dataset, rendered=rendered)
        answer_value = int(dataset.query.answer)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            is_label_answer=False,
            dynamic_slot_values=dynamic_slots(dataset=dataset),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_payload(
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            answer_value=answer_value,
            annotation_payload=annotation,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation["bboxes"])),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
        )


__all__ = ["ChartsRadialProgressThresholdCountTask", "SUPPORTED_QUERY_IDS"]
