"""Shared node-link visual-axis resolution for graph tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence

from ....core.seed import spawn_rng
from .graph_sampling import SUPPORTED_LAYOUT_VARIANTS, SUPPORTED_NODE_LINK_LABEL_VARIANTS
from .node_link_render_types import (
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
)
from .style import SUPPORTED_NODE_COLOR_NAMES
from .task_support import resolve_graph_named_variant


@dataclass(frozen=True)
class NodeLinkVisualAxes:
    """Resolved non-semantic node-link style/layout axes."""

    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]

    def value_fields(self, *, node_color_field_name: str = "node_color_name") -> Dict[str, str]:
        """Return resolved axis values keyed for common task query dataclasses."""

        return {
            "layout_variant": str(self.layout_variant),
            "label_variant": str(self.label_variant),
            "node_shape_variant": str(self.node_shape_variant),
            "layout_transform_variant": str(self.layout_transform_variant),
            "edge_routing_variant": str(self.edge_routing_variant),
            str(node_color_field_name): str(self.node_color_name),
        }

    def probability_fields(self, *, node_color_field_name: str = "node_color_name") -> Dict[str, Dict[str, float]]:
        """Return resolved axis probabilities keyed for common task query dataclasses."""

        return {
            "layout_variant_probabilities": dict(self.layout_variant_probabilities),
            "label_variant_probabilities": dict(self.label_variant_probabilities),
            "node_shape_variant_probabilities": dict(self.node_shape_variant_probabilities),
            "layout_transform_variant_probabilities": dict(self.layout_transform_variant_probabilities),
            "edge_routing_variant_probabilities": dict(self.edge_routing_variant_probabilities),
            f"{str(node_color_field_name)}_probabilities": dict(self.node_color_name_probabilities),
        }


def resolve_node_link_visual_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    task_id: str,
    supported_layout_variants: Sequence[str] = SUPPORTED_LAYOUT_VARIANTS,
    supported_label_variants: Sequence[str] = SUPPORTED_NODE_LINK_LABEL_VARIANTS,
    supported_node_shape_variants: Sequence[str] = SUPPORTED_NODE_SHAPE_VARIANTS,
    supported_layout_transform_variants: Sequence[str] = SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    supported_edge_routing_variants: Sequence[str] = SUPPORTED_EDGE_ROUTING_VARIANTS,
    supported_node_color_names: Sequence[str] = SUPPORTED_NODE_COLOR_NAMES,
    include_edge_routing_axis: bool = True,
    include_node_color_axis: bool = True,
    node_color_explicit_key: str = "node_color_name",
    node_color_weights_key: str = "node_color_name_weights",
    node_color_balance_flag_key: str = "balanced_node_color_name_sampling",
    node_color_namespace: str = "node_color_name",
) -> NodeLinkVisualAxes:
    """Resolve common node-link visual axes with existing graph balancing semantics."""

    layout_variant, layout_probabilities = resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{str(task_id)}.layout_variant"),
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=tuple(str(value) for value in supported_layout_variants),
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="layout_variant",
    )
    label_variant, label_probabilities = resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{str(task_id)}.label_variant"),
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="label_variant",
        weights_key="label_variant_weights",
        balance_flag_key="balanced_label_variant_sampling",
        supported=tuple(str(value) for value in supported_label_variants),
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="label_variant",
    )
    node_shape_variant, node_shape_probabilities = resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{str(task_id)}.node_shape_variant"),
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="node_shape_variant",
        weights_key="node_shape_variant_weights",
        balance_flag_key="balanced_node_shape_variant_sampling",
        supported=tuple(str(value) for value in supported_node_shape_variants),
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="node_shape_variant",
    )
    layout_transform_variant, layout_transform_probabilities = resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{str(task_id)}.layout_transform_variant"),
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="layout_transform_variant",
        weights_key="layout_transform_variant_weights",
        balance_flag_key="balanced_layout_transform_variant_sampling",
        supported=tuple(str(value) for value in supported_layout_transform_variants),
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="layout_transform_variant",
    )
    if bool(include_edge_routing_axis):
        edge_routing_variant, edge_routing_probabilities = resolve_graph_named_variant(
            spawn_rng(int(instance_seed), f"{str(task_id)}.edge_routing_variant"),
            params=params,
            gen_defaults=gen_defaults,
            explicit_key="edge_routing_variant",
            weights_key="edge_routing_variant_weights",
            balance_flag_key="balanced_edge_routing_variant_sampling",
            supported=tuple(str(value) for value in supported_edge_routing_variants),
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            namespace="edge_routing_variant",
        )
    else:
        edge_routing_variant = ""
        edge_routing_probabilities = {}
    if bool(include_node_color_axis):
        node_color_name, node_color_probabilities = resolve_graph_named_variant(
            spawn_rng(int(instance_seed), f"{str(task_id)}.node_color_name"),
            params=params,
            gen_defaults=gen_defaults,
            explicit_key=str(node_color_explicit_key),
            weights_key=str(node_color_weights_key),
            balance_flag_key=str(node_color_balance_flag_key),
            supported=tuple(str(value) for value in supported_node_color_names),
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            namespace=str(node_color_namespace),
        )
    else:
        node_color_name = ""
        node_color_probabilities = {}
    return NodeLinkVisualAxes(
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        layout_variant_probabilities=dict(layout_probabilities),
        label_variant_probabilities=dict(label_probabilities),
        node_shape_variant_probabilities=dict(node_shape_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_probabilities),
        edge_routing_variant_probabilities=dict(edge_routing_probabilities),
        node_color_name_probabilities=dict(node_color_probabilities),
    )


__all__ = [
    "NodeLinkVisualAxes",
    "resolve_node_link_visual_axes",
]
