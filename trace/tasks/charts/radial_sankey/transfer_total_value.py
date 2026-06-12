"""Radial Sankey grouped transfer total task."""

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
from .shared.radial_sankey_common import SCENE_ID, TRANSFER_TOTAL_QUERY_IDS, _resolve_scene_variant
from .shared.radial_sankey_sampling import _construct_dataset
from .shared.runtime import render_radial_sankey_dataset


TASK_PARAM_DEFAULTS: Dict[str, Any] = {
    "radial_group_size_min": 2,
    "radial_group_size_max": 2,
    "radial_source_count_min": 4,
    "radial_source_count_max": 4,
    "radial_target_count_min": 4,
    "radial_target_count_max": 4,
    "radial_link_count_min": 5,
    "radial_link_count_max": 7,
}


@register_task
class ChartsFlowRadialSankeyTransferTotalValuePublicTask:
    """Return a grouped transfer total from a radial Sankey chart."""

    task_id = "task_charts__radial_sankey__transfer_total_value"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "transfer_total_value"
    supported_query_ids = TRANSFER_TOTAL_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id="source_to_targets_total",
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
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
        )
        rendered = render_radial_sankey_dataset(
            dataset=dataset,
            params=params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
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
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
        )


__all__ = ["ChartsFlowRadialSankeyTransferTotalValuePublicTask"]
