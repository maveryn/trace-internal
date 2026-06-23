"""Return the cluster with extremal separation from a reference cluster."""

from __future__ import annotations

from typing import Any

from trace.tasks.registry import register_task

from ._lifecycle import build_scatter_cluster_plan, run_scatter_cluster_task
from .shared.annotations import cluster_pair_bbox_map_annotation
from .shared.data import build_separation_dataset
from .shared.sampling import sample_cluster_inputs
from .shared.state import DOMAIN


TASK_ID = "task_charts__scatter_cluster__cluster_separation_extremum_label"
CLOSEST_QUERY_ID = "closest_to_reference_label"
FARTHEST_QUERY_ID = "farthest_from_reference_label"
SUPPORTED_QUERY_IDS = (CLOSEST_QUERY_ID, FARTHEST_QUERY_ID)
DEFAULT_QUERY_ID = CLOSEST_QUERY_ID
_SEPARATION_BY_BRANCH = {
    CLOSEST_QUERY_ID: "closest",
    FARTHEST_QUERY_ID: "farthest",
}


def _reference_answer_annotation(dataset, rendered):
    return cluster_pair_bbox_map_annotation(
        dataset=dataset,
        rendered=rendered,
        reference_cluster_label=str(dataset.question.params["reference_cluster_label"]),
        answer_cluster_label=str(dataset.question.answer),
    )


def _build_plan(params: dict[str, Any], instance_seed: int, selected: str, probabilities: dict[str, float]):
    """Bind closest/farthest separation from the sampled reference cluster."""

    separation_extremum = _SEPARATION_BY_BRANCH[str(selected)]
    inputs = sample_cluster_inputs(params=params, instance_seed=int(instance_seed))
    dataset = build_separation_dataset(
        params=params,
        instance_seed=int(instance_seed),
        labels=inputs.labels,
        answer_label=str(inputs.answer_label),
        points_per_cluster=int(inputs.points_per_cluster),
        separation_extremum=str(separation_extremum),
        branch_id=str(selected),
        branch_probabilities=dict(probabilities),
        question_params={
            "program_code": "argextreme_label(cluster, distance(center(cluster), center(reference_cluster)), direction)",
        },
    )
    return build_scatter_cluster_plan(
        dataset=dataset,
        inputs=inputs,
        prompt_key=str(selected),
        question_format="scatter_cluster_separation_extremum_label",
        witness_type="scatter_cluster_reference_answer_bbox_map",
        annotation_builder=_reference_answer_annotation,
    )


@register_task
class ChartsScatterClusterSeparationExtremumLabelTask:
    """Return the cluster with extremal separation from a reference cluster."""

    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = "cluster_separation_extremum_label"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    default_dataset_enabled = True
    _build_plan = staticmethod(_build_plan)

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        return run_scatter_cluster_task(self, int(instance_seed), dict(params), int(max_attempts))


__all__ = ["ChartsScatterClusterSeparationExtremumLabelTask", "SUPPORTED_QUERY_IDS"]
