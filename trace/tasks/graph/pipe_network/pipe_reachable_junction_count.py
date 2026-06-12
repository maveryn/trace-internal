"""Count junctions reachable through open pipes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import force_query_id_params, select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.instance import PUBLIC_PIPE_SCENE_ID, build_pipe_junction_instance


TASK_ID = "task_graph__pipe_network__pipe_reachable_junction_count"
QUERY_ID = "pipe_reachable_junction_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)


def _trace_for_public_task(trace_payload: Mapping[str, Any], query_probs: Mapping[str, float]) -> Dict[str, Any]:
    """Attach public task-owned metadata to a neutral pipe instance trace."""

    trace = dict(trace_payload)
    scene_ir = dict(trace.get("scene_ir") or {})
    scene_ir["task_id"] = TASK_ID
    trace["scene_ir"] = scene_ir
    query_spec = dict(trace.get("query_spec") or {})
    params = dict(query_spec.get("params") or {})
    params["query_id_probabilities"] = {str(key): float(value) for key, value in query_probs.items()}
    query_spec["params"] = params
    trace["query_spec"] = query_spec
    return trace


@register_task
class GraphRelationPipeReachableJunctionCountTask:
    """Count junctions in the same open-pipe connected region as the query junction."""

    task_id = TASK_ID
    domain = "graph"
    scene_id = PUBLIC_PIPE_SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probs, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        forced_params = force_query_id_params(task_params, query_id=str(query_id))
        bundle = build_pipe_junction_instance(
            config_scope_key=TASK_ID,
            query_id=str(query_id),
            prompt_annotation_key="annotation_hint_reachable_count",
            prompt_task_key_fallback="reachable_count_query",
            instance_seed=int(instance_seed),
            params=forced_params,
            max_attempts=int(max_attempts),
            domain=self.domain,
        )
        return TaskOutput(
            prompt=str(bundle.prompt),
            answer_gt=TypedValue(type=str(bundle.answer_type), value=bundle.answer_value),
            annotation_gt=TypedValue(type=str(bundle.annotation_type), value=list(bundle.annotation_value)),
            image=bundle.image,
            image_id="img0",
            trace_payload=_trace_for_public_task(bundle.trace_payload, query_probs),
            task_versions=default_task_versions(),
            scene_id=PUBLIC_PIPE_SCENE_ID,
            query_id=str(bundle.query_id),
            prompt_variants=dict(bundle.prompt_variants),
        )


__all__ = ["GraphRelationPipeReachableJunctionCountTask", "TASK_ID"]
