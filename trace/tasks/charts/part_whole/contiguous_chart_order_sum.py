"""Sum shares over a contiguous run of chart segments."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.output import build_trace_payload
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.runtime import annotation_payload, render_part_whole_dataset
from .shared.share_arithmetic_common import CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID, SCENE_ID, resolve_scene_variant
from .shared.share_arithmetic_dataset import build_dataset


TASK_PARAM_DEFAULTS: Dict[str, Any] = {
    "contiguous_category_count_min": 4,
    "contiguous_category_count_max": 6,
    "contiguous_span_count_min": 2,
    "contiguous_span_count_max": 3,
}


@register_task
class ChartsCompositionChartContiguousOrderSumTask:
    """Return the combined share across a contiguous chart-order segment."""

    task_id = "task_charts__part_whole__contiguous_chart_order_sum"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "contiguous_chart_order_sum"
    supported_query_ids = (CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), self.task_id, attempt))
            try:
                return self._generate_once(int(attempt_seed), params=task_params, selected_query_id=str(selected_query_id))
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any], selected_query_id: str) -> TaskOutput:
        scene_variant, scene_variant_probabilities = resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_dataset(query_id=str(selected_query_id), params=params, instance_seed=int(instance_seed))
        rendered = render_part_whole_dataset(
            dataset=dataset,
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
        )
        annotation = annotation_payload(dataset=dataset, rendered_scene=rendered.rendered_scene)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset.trace_extras, scene_variant=str(scene_variant)),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_payload(
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            scene_variant=str(scene_variant),
            scene_variant_probabilities=scene_variant_probabilities,
            annotation_payload=annotation,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(dataset.answer_value)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation["keyed_points"])),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["ChartsCompositionChartContiguousOrderSumTask"]
