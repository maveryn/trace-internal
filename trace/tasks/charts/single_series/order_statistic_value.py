"""Return a sampled order-statistic value from a labeled chart."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.summary_query import build_summary_query_task_components


QUERY_ID = "order_statistic_value"
TASK_PARAM_DEFAULTS: Dict[str, Any] = {}


@register_task
class ChartsSingleSeriesOrderStatisticValueTask:
    """Return a sampled order-statistic value from a labeled chart."""

    task_id = "task_charts__single_series__order_statistic_value"
    domain = "charts"
    scene_id = "single_series"
    objective_contract = "order_statistic_value"
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
                components = build_summary_query_task_components(
                    task_id=self.task_id,
                    instance_seed=int(attempt_seed),
                    params={**dict(task_params), "_attempt_index": int(attempt_index)},
                    selected_query_id=str(selected_query_id),
                    query_id_probabilities=query_probabilities,
                )
                return TaskOutput(
                    prompt=str(components.prompt),
                    prompt_variants=dict(components.prompt_variants),
                    answer_gt=TypedValue(type=str(components.answer_type), value=components.answer_value),
                    annotation_gt=TypedValue(type=str(components.annotation_type), value=list(components.annotation_value)),
                    image=components.image,
                    image_id="img0",
                    trace_payload=dict(components.trace_payload),
                    task_versions=default_task_versions(),
                    scene_id="single_series",
                    query_id=str(components.query_id),
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsSingleSeriesOrderStatisticValueTask"]
