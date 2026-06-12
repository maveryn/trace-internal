"""Return the bottleneck value along one Sankey source-middle-target path."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.output import annotation_payload, build_trace_payload
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.runtime import render_sankey_dataset
from .shared.sankey_sampling import _construct_dataset


TASK_PARAM_DEFAULTS: Dict[str, Any] = {}


@register_task
class ChartsFlowSankeyPathBottleneckValuePublicTask:
    """Return the bottleneck value along one Sankey source-middle-target path."""

    task_id = "task_charts__sankey__path_bottleneck_value"
    domain = "charts"
    scene_id = "sankey"
    objective_contract = "path_bottleneck_value"
    supported_query_ids = ('path_bottleneck_value',)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id="path_bottleneck_value",
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
        scene_variant = "three_column_sankey"
        scene_variant_probabilities = {"three_column_sankey": 1.0}
        dataset = _construct_dataset(
            query_id=str(selected_query_id),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
        )
        rendered = render_sankey_dataset(dataset=dataset, params=params, instance_seed=int(instance_seed))
        annotation = annotation_payload(dataset=dataset, rendered=rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset=dataset),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_payload(
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            query_id_probabilities=query_probabilities,
            scene_variant=str(scene_variant),
            scene_variant_probabilities=scene_variant_probabilities,
            annotation_payload=annotation,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type="integer", value=int(dataset["answer_value"])),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation["bboxes"])),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id="sankey",
            query_id=str(selected_query_id),
        )


__all__ = ["ChartsFlowSankeyPathBottleneckValuePublicTask"]
