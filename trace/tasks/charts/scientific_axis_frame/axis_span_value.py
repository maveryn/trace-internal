"""Compute a visible numeric axis span in a scientific plot frame."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.axis_frame_query import AXIS_SPAN_QUERY_IDS, _build_dataset
from .shared.output import build_axis_frame_task_components


DEFAULT_QUERY_ID = "x_axis_span_value"
TASK_PARAM_DEFAULTS: Dict[str, Any] = {}


@register_task
class ChartsScientificAxisFrameAxisSpanValueTask:
    """Compute the visible numeric span of one axis."""

    task_id = "task_charts__scientific_axis_frame__axis_span_value"
    domain = "charts"
    scene_id = "scientific_axis_frame"
    objective_contract = "axis_span_value"
    supported_query_ids = AXIS_SPAN_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=DEFAULT_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), self.task_id, attempt_index))
            try:
                dataset = _build_dataset(
                    {**dict(task_params), "_attempt_index": int(attempt_index)},
                    instance_seed=int(attempt_seed),
                    query_id=str(selected_query_id),
                    query_probabilities=query_probabilities,
                )
                components = build_axis_frame_task_components(
                    dataset=dataset,
                    params=task_params,
                    instance_seed=int(attempt_seed),
                    query_id=str(selected_query_id),
                    query_id_probabilities=query_probabilities,
                )
                return TaskOutput(
                    prompt=str(components.prompt),
                    prompt_variants=dict(components.prompt_variants),
                    answer_gt=TypedValue(type=str(components.answer_type), value=int(components.answer_value)),
                    annotation_gt=TypedValue(type=str(components.annotation_type), value=dict(components.annotation_value)),
                    image=components.image,
                    image_id="img0",
                    trace_payload=dict(components.trace_payload),
                    task_versions=default_task_versions(),
                    scene_id="scientific_axis_frame",
                    query_id=str(components.query_id),
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsScientificAxisFrameAxisSpanValueTask"]
