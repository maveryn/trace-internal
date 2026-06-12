"""Trace serialization and output helpers for graph node-link tasks."""

from __future__ import annotations

from typing import Any

def node_entities(rendered_scene: Any) -> list[dict[str, Any]]:
    """Return generic rendered-node entities for trace inspection."""

    return [
        {
            "entity_id": f"node_{node.label}",
            "entity_kind": "graph_node",
            "label": str(node.label),
            "degree": int(node.degree),
            "neighbors": list(node.neighbors),
            "successors": list(node.successors),
            "predecessors": list(node.predecessors),
            "center_px": list(node.center_xy),
            "bbox_xyxy": list(node.bbox_xyxy),
        }
        for node in rendered_scene.nodes
    ]


def edge_entities(rendered_scene: Any, sample: Any) -> list[dict[str, Any]]:
    """Return generic rendered-edge entities for trace inspection."""

    labels_by_edge = getattr(sample, "edge_attribute_labels_by_label", {})
    colors_by_edge = getattr(sample, "edge_color_names_by_label", {})
    weights_by_edge = getattr(sample, "edge_weights_by_label", {})
    return [
        {
            "entity_id": str(edge.edge_id),
            "entity_kind": "graph_edge",
            "node_u_label": str(edge.node_u_label),
            "node_v_label": str(edge.node_v_label),
            "directed": bool(edge.directed),
            "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
            "route_variant": str(edge.route_variant),
            "control_px": list(edge.control_px) if edge.control_px is not None else None,
            "edge_text_label": labels_by_edge.get((str(edge.node_u_label), str(edge.node_v_label))),
            "edge_color_name": colors_by_edge.get((str(edge.node_u_label), str(edge.node_v_label))),
            "edge_weight": weights_by_edge.get((str(edge.node_u_label), str(edge.node_v_label))),
        }
        for edge in rendered_scene.edges
    ]


__all__ = [
    "edge_entities",
    "node_entities",
]
