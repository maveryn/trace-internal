"""Return the cluster label at a requested shaded-footprint area rank."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.cluster_dataset import _dataset_for_area_rank
from .shared.output import build_scatter_cluster_task_components
from .shared.runtime import sample_cluster_inputs


QUERY_IDS = (
    "largest_cluster_area_label",
    "second_largest_cluster_area_label",
    "smallest_cluster_area_label",
)
TASK_PARAM_DEFAULTS: Dict[str, Any] = {}


@register_task
class ChartsScatterClusterAreaRankLabelTask:
    """Return the cluster label at a requested shaded-footprint area rank."""

    task_id = "task_charts__scatter_cluster__cluster_area_rank_label"
    domain = "charts"
    scene_id = "scatter_cluster"
    objective_contract = "cluster_area_rank_label"
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id="largest_cluster_area_label",
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
        dataset = _dataset_for_area_rank(
            params=params,
            instance_seed=int(instance_seed),
            labels=inputs.labels,
            points_per_cluster=int(inputs.points_per_cluster),
            query_id=str(selected_query_id),
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


__all__ = ["ChartsScatterClusterAreaRankLabelTask"]
