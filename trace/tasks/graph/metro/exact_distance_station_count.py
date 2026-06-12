"""Count stations at an exact metro-route distance from a named station."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import force_query_id_params, select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.instance import PUBLIC_METRO_SCENE_ID, build_metro_route_instance


TASK_ID = "task_graph__metro__exact_distance_station_count"
QUERY_ID = "metro_exact_distance_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)


@register_task
class GraphRelationMetroExactDistanceCountTask:
    """Count stations exactly k route segments away from a queried station."""

    task_id = TASK_ID
    domain = "graph"
    scene_id = PUBLIC_METRO_SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, _query_probs, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        forced_params = force_query_id_params(task_params, query_id=str(query_id))
        bundle = build_metro_route_instance(
            instance_key=TASK_ID,
            query_id=str(query_id),
            prompt_annotation_key="annotation_hint_exact_distance_count",
            prompt_task_key_fallback="exact_distance_count_query",
            instance_seed=int(instance_seed),
            params=forced_params,
            domain=self.domain,
        )
        return TaskOutput(
            prompt=str(bundle.prompt),
            answer_gt=TypedValue(type="integer", value=int(bundle.answer_value)),
            annotation_gt=TypedValue(type=str(bundle.annotation_type), value=list(bundle.annotation_value)),
            image=bundle.image,
            image_id="img0",
            trace_payload=dict(bundle.trace_payload),
            task_versions=default_task_versions(),
            scene_id=PUBLIC_METRO_SCENE_ID,
            query_id=str(bundle.query_id),
            prompt_variants=dict(bundle.prompt_variants),
        )


__all__ = ["GraphRelationMetroExactDistanceCountTask", "TASK_ID"]
