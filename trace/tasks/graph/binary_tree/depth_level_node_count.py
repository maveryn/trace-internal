"""Count binary-tree nodes at a requested depth level."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ...shared.fixed_query import force_query_id_params
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from .shared.node_count import build_node_count_render_bundle, build_node_count_trace_payload


TASK_ID = "task_graph__binary_tree__depth_level_node_count"
SCENE_ID = "binary_tree"
QUERY_ID = "depth_level_node_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)

_SCENE_DEFAULTS = get_scene_defaults("graph", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class GraphCountingBinaryTreeDepthLevelNodeCountTask:
    """Count nodes at one depth in a rooted binary-tree diagram."""

    task_id = TASK_ID
    domain = "graph"
    scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        forced_params = force_query_id_params(params, query_id=QUERY_ID)
        bundle = build_node_count_render_bundle(
            instance_seed=int(instance_seed),
            params=forced_params,
            max_attempts=int(max_attempts),
        )
        prompt_defaults = dict(_PROMPT_DEFAULTS)
        annotation_hint = str(prompt_defaults["annotation_hint_depth_level_node_count"]).format(
            target_depth=str(bundle.query.target_depth)
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(bundle.query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_depth": str(bundle.query.target_depth),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": annotation_hint,
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_gt = TypedValue(type="integer", value=int(len(bundle.target_labels)))
        annotation_gt = TypedValue(type="bbox_set", value=list(bundle.annotation_bboxes))
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=bundle.image,
            image_id="img0",
            trace_payload=build_node_count_trace_payload(
                bundle=bundle,
                prompt_defaults=prompt_defaults,
                prompt_artifacts=prompt_artifacts,
                trace_task_id=TASK_ID,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(bundle.query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphCountingBinaryTreeDepthLevelNodeCountTask", "TASK_ID"]
