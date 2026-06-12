"""Identify the violating child in a min-heap-style binary tree."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ...shared.fixed_query import force_query_id_params
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from .shared.search_tree_operation import (
    SCENE_ID,
    SUPPORTED_HEAP_PROPERTY_VIOLATION_QUERY_IDS,
    build_operation_prompt_json_examples,
    build_operation_render_bundle,
    build_operation_trace_payload,
)


TASK_ID = "task_graph__binary_tree__heap_property_violation_label"
QUERY_ID = "heap_property_violation_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = tuple(SUPPORTED_HEAP_PROPERTY_VIOLATION_QUERY_IDS)

_SCENE_DEFAULTS = get_scene_defaults("graph", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class GraphRelationHeapPropertyViolationLabelTask:
    """Return the child node label that violates the min-heap order rule."""

    task_id = TASK_ID
    domain = "graph"
    scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = build_operation_prompt_json_examples(str(bundle.query.query_id))
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(bundle.query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults.get("object_description_heap", prompt_defaults["object_description"])),
                "target_key": "",
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(bundle.operation.answer_label)),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(bundle.annotation_keyed_bboxes)),
            image=bundle.image,
            image_id="img0",
            trace_payload=build_operation_trace_payload(
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


__all__ = ["GraphRelationHeapPropertyViolationLabelTask", "TASK_ID"]
