"""Compute the maximum flow value in a directed capacity network."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from ...shared.fixed_query import force_query_id_params, select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.instance import build_flow_network_instance_bundle, build_flow_network_trace_payload
from .shared.prompts import PROMPT_BUNDLE_ID as FLOW_PROMPT_BUNDLE_ID
from .shared.prompts import build_flow_network_prompt_artifacts
from .shared.state import SCENE_ID


TASK_ID = "task_graph__flow_network__max_flow_value"
QUERY_ID = "max_flow_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "graph",
    SCENE_ID,
    task_id=TASK_ID,
)
PROMPT_BUNDLE_ID = str(group_default(_PROMPT_DEFAULTS, "bundle_id", FLOW_PROMPT_BUNDLE_ID))


@register_task
class GraphFlowNetworkMaxFlowValueTask:
    """Answer maximum-flow value questions on a directed capacity graph."""

    task_id = TASK_ID
    domain = "graph"
    scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, _query_probs, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        forced_params = force_query_id_params(task_params, query_id=str(query_id))
        bundle = build_flow_network_instance_bundle(
            instance_seed=int(instance_seed),
            params=forced_params,
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            query_id=str(query_id),
            answer_mode="max_flow_value",
            sampling_namespace="flow_network_max_flow",
            max_attempts=int(max_attempts),
        )
        prompt_artifacts = build_flow_network_prompt_artifacts(
            domain=self.domain,
            bundle_id=PROMPT_BUNDLE_ID,
            prompt_key=str(bundle.query.query_id),
            dynamic_slots={
                "object_description": "a directed capacity network with source S and sink T",
            },
            instance_seed=int(instance_seed),
        )
        annotation_point_pairs = list(bundle.annotation_point_pairs)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(bundle.answer_value)),
            annotation_gt=TypedValue(type="point_pair_set", value=annotation_point_pairs),
            image=bundle.render.image,
            image_id="img0",
            trace_payload=build_flow_network_trace_payload(
                bundle=bundle,
                prompt_bundle_id=PROMPT_BUNDLE_ID,
                prompt_artifacts=prompt_artifacts,
                trace_task_id=TASK_ID,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(bundle.query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphFlowNetworkMaxFlowValueTask", "TASK_ID"]
