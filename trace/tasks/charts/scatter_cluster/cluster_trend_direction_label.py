"""Return the cluster label with the strongest requested trend direction."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.cluster_dataset import _dataset_for_trend
from .shared.cluster_sampling import _resolve_trend_direction
from .shared.output import build_scatter_cluster_task_components
from .shared.runtime import sample_cluster_inputs


QUERY_ID = "cluster_trend_direction_label"
TASK_PARAM_DEFAULTS: Dict[str, Any] = {}


@register_task
class ChartsScatterClusterTrendDirectionLabelTask:
    """Return the cluster label with the strongest requested trend direction."""

    task_id = "task_charts__scatter_cluster__cluster_trend_direction_label"
    domain = "charts"
    scene_id = "scatter_cluster"
    objective_contract = "cluster_trend_direction_label"
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
        inputs = sample_cluster_inputs(params=params, instance_seed=int(instance_seed))
        trend_direction, trend_direction_probabilities = _resolve_trend_direction(
            params,
            instance_seed=int(instance_seed),
        )
        dataset = _dataset_for_trend(
            params=params,
            instance_seed=int(instance_seed),
            labels=inputs.labels,
            answer_label=str(inputs.answer_label),
            points_per_cluster=int(inputs.points_per_cluster),
            trend_direction=str(trend_direction),
            trend_direction_probabilities=trend_direction_probabilities,
        )
        components = build_scatter_cluster_task_components(
            dataset=dataset,
            inputs=inputs,
            params=params,
            instance_seed=int(instance_seed),
            query_id=str(selected_query_id),
            query_id_probabilities=query_probabilities,
        )
        return TaskOutput(
            prompt=str(components.prompt),
            prompt_variants=dict(components.prompt_variants),
            answer_gt=TypedValue(type=str(components.answer_type), value=str(components.answer_value)),
            annotation_gt=TypedValue(type=str(components.annotation_type), value=dict(components.annotation_value)),
            image=components.image,
            image_id="img0",
            trace_payload=dict(components.trace_payload),
            task_versions=default_task_versions(),
            scene_id="scatter_cluster",
            query_id=str(components.query_id),
        )


__all__ = ["ChartsScatterClusterTrendDirectionLabelTask"]
