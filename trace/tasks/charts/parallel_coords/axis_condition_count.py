"""Count profiles satisfying two axis predicates."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.output import build_trace_payload
from .shared.profile_common import SCENE_ID
from .shared.profile_sampling import _build_dataset
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.runtime import annotation_payload, render_dataset


CONDITION_QUERY_IDS = ("above_on_both_axes", "below_on_both_axes", "above_on_one_below_on_other")


@register_task
class ChartsParallelCoordinatesAxisConditionCountTask:
    """Count profile lines satisfying a two-axis threshold condition."""

    task_id = "task_charts__parallel_coords__axis_condition_count"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "axis_condition_count"
    supported_query_ids = CONDITION_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id="above_on_both_axes",
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
            except Exception as exc:
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
        dataset = _build_dataset(
            params=params,
            instance_seed=int(instance_seed),
            query_id=str(selected_query_id),
            query_id_probabilities=query_probabilities,
        )
        rendered = render_dataset(dataset=dataset, params=params, instance_seed=int(instance_seed))
        annotation_type, annotation_value, projected_annotation = annotation_payload(dataset, rendered.rendered_scene)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset),
            instance_seed=int(instance_seed),
        )
        answer_value = int(dataset.query.answer)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=TypedValue(type=str(annotation_type), value=annotation_value),
            image=rendered.image,
            image_id="img0",
            trace_payload=build_trace_payload(
                dataset=dataset,
                rendered=rendered,
                prompt_artifacts=prompt_artifacts,
                annotation_type=str(annotation_type),
                projected_annotation=projected_annotation,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["ChartsParallelCoordinatesAxisConditionCountTask"]
