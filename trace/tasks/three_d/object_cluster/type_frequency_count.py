"""Count clustered objects selected by object-type frequency."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.tasks.three_d.shared.task_support import resolve_axis_variant_for_namespace

from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import run_object_cluster_lifecycle
from .shared.output import build_count_request
from .shared.state import ClusterRequest
from ..shared.object_scene import ObjectSceneRenderParams


TASK_ID = "task_three_d__object_cluster__type_frequency_count"
MOST_FREQUENT_QUERY_ID = "most_frequent_type_count"
SINGLETON_QUERY_ID = "singleton_type_count"
SUPPORTED_QUERY_IDS = (MOST_FREQUENT_QUERY_ID, SINGLETON_QUERY_ID)


@register_task
class ThreeDObjectClusterTypeFrequencyCountTask:
    """Count clustered objects selected by object-type frequency."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_object_cluster_lifecycle(int(instance_seed), params=params, max_attempts=int(max_attempts), task_identifier=TASK_ID, build_request=self._build_frequency_request)

    def _build_frequency_request(self, instance_seed: int, params: Mapping[str, Any], gen_defaults: Mapping[str, Any], _prompt_defaults: Mapping[str, Any], render_params: ObjectSceneRenderParams) -> ClusterRequest:
        """Bind the selected public frequency branch to internal frequency semantics."""

        branch, probs = resolve_axis_variant_for_namespace(params, namespace=f"{TASK_ID}.branch", gen_defaults=gen_defaults, instance_seed=int(instance_seed), supported_variants=SUPPORTED_QUERY_IDS, explicit_key="query_id", weights_key="query_id_weights", balance_flag_key="balanced_query_id_sampling")
        mode = "frequency_max" if str(branch) == MOST_FREQUENT_QUERY_ID else "frequency_singletons"
        return build_count_request(mode=mode, external_query=str(branch), prompt_key=str(branch), branch_probabilities=probs, namespace=TASK_ID, instance_seed=int(instance_seed), params=params, gen_defaults=gen_defaults, render_params=render_params)


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDObjectClusterTypeFrequencyCountTask"]
