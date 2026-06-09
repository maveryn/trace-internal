"""Compatibility facade for shared node-link graph rendering helpers."""

from __future__ import annotations

from .node_link_context import (
    apply_graph_content_layout_jitter,
    draw_graph_context_text_blocks,
    draw_graph_context_text_chips,
)
from .node_link_geometry import _segment_intersects_bbox
from .node_link_projection import (
    projected_edge_label_bbox_annotation,
    projected_edge_pair_annotation,
    projected_node_point_annotation,
)
from .node_link_render_types import (
    BBox,
    GraphRenderParams,
    Point,
    RenderedGraphEdge,
    RenderedGraphNode,
    RenderedGraphScene,
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
)
from .node_link_renderer import render_graph_scene


__all__ = [
    "BBox",
    "GraphRenderParams",
    "Point",
    "RenderedGraphEdge",
    "RenderedGraphNode",
    "RenderedGraphScene",
    "SUPPORTED_EDGE_ROUTING_VARIANTS",
    "SUPPORTED_LAYOUT_TRANSFORM_VARIANTS",
    "SUPPORTED_NODE_SHAPE_VARIANTS",
    "_segment_intersects_bbox",
    "apply_graph_content_layout_jitter",
    "draw_graph_context_text_blocks",
    "draw_graph_context_text_chips",
    "projected_edge_label_bbox_annotation",
    "projected_edge_pair_annotation",
    "projected_node_point_annotation",
    "render_graph_scene",
]
