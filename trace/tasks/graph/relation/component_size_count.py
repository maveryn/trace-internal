"""Merged connected-component size/count graph task."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, Mapping, Tuple

from ...base import TaskOutput
from ...registry import register_task
from ..shared.fixed_query_task import (
    decoupled_merged_branch_params,
    FixedGraphQueryTaskMixin,
    rewrite_graph_public_task_output,
    select_merged_graph_query_id,
)


COMPONENT_SIZE_AFTER_EDGE_EDIT_TASK_ID = "task_graph__node_link__component_size_after_edge_edit"
LARGEST_COMPONENT_SIZE_TASK_ID = "task_graph__node_link__largest_component_size"
SAME_COMPONENT_COUNT_TASK_ID = "task_graph__node_link__same_component_count"

_MERGED_QUERY_IDS: Tuple[str, ...] = (
    "same_component_count",
    "largest_component_size",
    "component_size_after_edge_removal",
    "component_size_after_edge_addition",
)

_MERGED_QUERY_ALIASES: Dict[str, str] = {
    "largest_component": "largest_component_size",
    "largest_component_count": "largest_component_size",
    "component_after_edge_removal": "component_size_after_edge_removal",
    "component_after_edge_addition": "component_size_after_edge_addition",
    "edge_removal": "component_size_after_edge_removal",
    "edge_addition": "component_size_after_edge_addition",
}


def _selected_query_from_params(params: Mapping[str, Any], instance_seed: int) -> str:
    """Return the public component-size query id for this merged task."""

    if params.get("target_largest_component_size") is not None:
        return "largest_component_size"
    for key in ("edit_operation", "edge_edit_operation"):
        value = params.get(str(key))
        if value is None:
            continue
        text = str(value)
        if text in {"edge_removal", "remove_edge", "component_size_after_edge_removal"}:
            return "component_size_after_edge_removal"
        if text in {"edge_addition", "add_edge", "component_size_after_edge_addition"}:
            return "component_size_after_edge_addition"
    return select_merged_graph_query_id(
        params=params,
        instance_seed=int(instance_seed),
        task_id=COMPONENT_SIZE_AFTER_EDGE_EDIT_TASK_ID,
        supported_query_ids=_MERGED_QUERY_IDS,
        aliases=_MERGED_QUERY_ALIASES,
    )


def _edge_edit_params(params: Mapping[str, Any], query_id: str) -> Dict[str, Any]:
    """Return params forcing the absorbed component edge-edit branch."""

    forced = dict(params)
    forced["query_id"] = str(query_id)
    forced["edit_operation"] = (
        "edge_removal" if str(query_id) == "component_size_after_edge_removal" else "edge_addition"
    )
    return forced


def _rewrite_largest_component_prompt_bundle(output: TaskOutput) -> TaskOutput:
    """Move the absorbed largest-component prompt trace under the relation bundle."""

    payload = deepcopy(output.trace_payload)
    query_spec = payload.get("query_spec")
    if isinstance(query_spec, dict):
        query_spec["template_id"] = "graph_relation_v0"
        prompt_variant = query_spec.get("prompt_variant")
        if isinstance(prompt_variant, dict):
            prompt_variant["prompt_bundle_id"] = "graph_relation_v0"
            prompt_variant["scene_key"] = "single_graph_relation"
            prompt_variant["template_paths"] = ["graph/relation/graph_relation_v0.json"]
            counts = prompt_variant.get("variant_count_by_key")
            if isinstance(counts, dict) and "scene:single_graph_comparison" in counts:
                counts["scene:single_graph_relation"] = counts.pop("scene:single_graph_comparison")
        prompt_variants = query_spec.get("prompt_variants")
        if isinstance(prompt_variants, dict):
            for variant in prompt_variants.values():
                if isinstance(variant, dict):
                    pv = variant.get("prompt_variant")
                    if isinstance(pv, dict):
                        pv["prompt_bundle_id"] = "graph_relation_v0"
                        pv["scene_key"] = "single_graph_relation"
                        pv["template_paths"] = ["graph/relation/graph_relation_v0.json"]
                        counts = pv.get("variant_count_by_key")
                        if isinstance(counts, dict) and "scene:single_graph_comparison" in counts:
                            counts["scene:single_graph_relation"] = counts.pop("scene:single_graph_comparison")
    return replace(output, trace_payload=payload)


@register_task
class GraphRelationSameComponentCountTaskPublic(FixedGraphQueryTaskMixin):
    """Count nodes in the same connected component as a queried node."""

    task_id = SAME_COMPONENT_COUNT_TASK_ID
    domain = "graph"
    task_group = "relation"
    fixed_query_id = "same_component_count"
    from .same_component_count import GraphRelationSameComponentCountTask as source_task_cls


@register_task
class GraphComparisonLargestComponentSizeTaskPublic(FixedGraphQueryTaskMixin):
    """Return the size of the unique largest connected component."""

    task_id = LARGEST_COMPONENT_SIZE_TASK_ID
    domain = "graph"
    task_group = "comparison"
    fixed_query_id = "largest_component_size"
    from ..comparison.largest_component_size import GraphComparisonLargestComponentSizeTask as source_task_cls


@register_task
class GraphRelationComponentSizeAfterEdgeEditTaskPublic:
    """Count the component containing a queried node after one edge edit."""

    task_id = COMPONENT_SIZE_AFTER_EDGE_EDIT_TASK_ID
    domain = "graph"
    task_group = "relation"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        branch_base_params = decoupled_merged_branch_params(
            params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_query_ids=("component_size_after_edge_removal", "component_size_after_edge_addition"),
            aliases=_MERGED_QUERY_ALIASES,
        )
        query_id = _selected_query_from_params(params, int(instance_seed))
        if str(query_id) not in {"component_size_after_edge_removal", "component_size_after_edge_addition"}:
            query_id = select_merged_graph_query_id(
                params=params,
                instance_seed=int(instance_seed),
                task_id=self.task_id,
                supported_query_ids=("component_size_after_edge_removal", "component_size_after_edge_addition"),
                aliases=_MERGED_QUERY_ALIASES,
            )
        from .component_size_after_edge_edit import GraphRelationComponentSizeAfterEdgeEditTask

        output = GraphRelationComponentSizeAfterEdgeEditTask().generate(
            int(instance_seed),
            params=_edge_edit_params(branch_base_params, str(query_id)),
            max_attempts=int(max_attempts),
        )
        return rewrite_graph_public_task_output(output, task_id=self.task_id, query_id=output.query_id)


__all__ = [
    "GraphRelationSameComponentCountTaskPublic",
    "GraphComparisonLargestComponentSizeTaskPublic",
    "GraphRelationComponentSizeAfterEdgeEditTaskPublic",
]
