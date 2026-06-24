"""Count route changes in a metro trip that passes through a named station."""

from __future__ import annotations

from typing import Dict, Tuple

from ....core.seed import spawn_rng
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import force_query_id_params, select_task_query_id
from ._lifecycle import (
    finish_metro_result,
    prepare_metro_assets,
    resolve_route_metric_axes,
)
from .shared.algorithms import feasible_transfer_change_counts
from .shared.sampling import sample_transfer_change_network


TASK_ID = "task_graph__metro__transfer_count"
QUERY_ID = "single"
PROMPT_QUERY_KEY = "metro_transfer_count"
PROMPT_ANNOTATION_KEY = "annotation_hint_transfer_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)


@register_task
class GraphPathMetroTransferCountTask:
    """Count route changes in a unique source-via-goal metro trip."""

    task_id = TASK_ID
    domain = "graph"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Sample a source-via-goal route and bind the selected station path."""

        del max_attempts
        branch_name, _branch_probs, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=SUPPORTED_QUERY_IDS, default_query_id=QUERY_ID, task_id=TASK_ID, namespace=f"{TASK_ID}.query")
        forced_params = force_query_id_params(task_params, query_id=str(branch_name))
        axes = resolve_route_metric_axes(
            instance_seed=int(instance_seed),
            params=forced_params,
            owner_id=TASK_ID,
            feasible_values_fn=feasible_transfer_change_counts,
            explicit_target_keys=("target_count",),
            balanced_target_selection=True,
        )
        sample = sample_transfer_change_network(spawn_rng(int(instance_seed), f"{TASK_ID}.metro_network"), transfer_count_value=int(axes.target_count), route_count=int(axes.route_count), label_variant=str(axes.label_variant))
        assets = prepare_metro_assets(owner_id=TASK_ID, branch_name=str(branch_name), prompt_query_key=PROMPT_QUERY_KEY, prompt_annotation_key=PROMPT_ANNOTATION_KEY, instance_seed=int(instance_seed), params=forced_params, sample=sample, axes=axes, answer_value=int(sample.target_route_transfer_count), annotation_labels=tuple(sample.target_labels), ordered_annotation=True, witness_extra={"route_sequence": list(sample.target_route_sequence), "route_change_station_labels": list(sample.target_path_transfer_labels)})
        return finish_metro_result(assets=assets, branch_name=str(branch_name))


__all__ = ["GraphPathMetroTransferCountTask", "TASK_ID"]
