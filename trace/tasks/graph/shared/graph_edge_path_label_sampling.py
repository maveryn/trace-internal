"""Shared graph-domain edge-label path samplers."""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Any, Dict, Mapping, Sequence, Tuple

import networkx as nx

from ...shared.graph_algorithms import bfs_dist_count_by_adjacency, reconstruct_unique_shortest_path_by_adjacency
from .graph_edge_sampling import (
    _add_directed_edge_without_reciprocal,
    _add_random_directed_distractor_edges,
    _add_random_undirected_distractor_edges,
    _profile_extra_edge_budget,
)
from .graph_feasibility import *  # noqa: F403
from .graph_profile_sampling import (
    _choose_attachment_parent,
    _edge_weight_for_profile,
    _sample_profile_extra_edges,
    _sample_profile_tree_graph,
)
from .graph_sample_types import *  # noqa: F403
from .graph_topology_helpers import (
    _build_labeled_graph_topology_sample,
    _components_by_label_for_graph,
    _digraph_predecessor_adjacency_by_node,
    _digraph_successor_adjacency_by_node,
    _directed_adjacency_by_label_for_graph,
    _directed_predecessors_by_label_for_graph,
    _directed_successors_by_label_for_graph,
    _graph_adjacency_by_node,
    _has_reciprocal_edges,
    _post_removal_degree_maps_by_label,
    _undirected_adjacency_by_label_for_graph,
)
from .graph_path_order_sampling import sample_shortest_path_length_graph


def sample_edge_attribute_path_label_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    node_count: int,
    target_shortest_path_length: int,
    target_edge_label: str,
    edge_label_support: Sequence[str],
    topology_profile: str,
    label_variant: str,
) -> GraphEdgeAttributeLabelSample:
    """Construct one labeled graph and query the first edge on a unique shortest path."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS:
        raise ValueError(f"unsupported graph_directionality: {graph_directionality}")
    edge_labels_supported = tuple(str(label).strip().lower() for label in edge_label_support if str(label).strip())
    if len(set(edge_labels_supported)) != len(edge_labels_supported) or len(edge_labels_supported) < 2:
        raise ValueError("edge_label_support must contain at least two unique labels")
    target_label = str(target_edge_label).strip().lower()
    if target_label not in set(edge_labels_supported):
        raise ValueError("target_edge_label is outside edge_label_support")

    path_query_id = "directed_shortest_path_length" if directionality == "directed" else "shortest_path_length"
    topology_sample = sample_shortest_path_length_graph(
        rng,
        query_id=str(path_query_id),
        node_count=int(node_count),
        target_shortest_path_length=int(target_shortest_path_length),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    path_labels = tuple(str(label) for label in topology_sample.target_labels)
    if len(path_labels) < 2:
        raise ValueError("shortest path must contain at least one edge")
    query_edge = canonicalize_graph_edge_label(
        str(path_labels[0]),
        str(path_labels[1]),
        directed=bool(directionality == "directed"),
    )
    edge_labels = tuple((str(left), str(right)) for left, right in topology_sample.edge_labels)
    if tuple(query_edge) not in set(edge_labels):
        raise ValueError("queried shortest-path edge is absent from labeled edge set")

    edge_attribute_labels_by_label: Dict[Tuple[str, str], str] = {}
    for edge in edge_labels:
        canonical_edge = (str(edge[0]), str(edge[1]))
        if canonical_edge == tuple(query_edge):
            edge_attribute_labels_by_label[canonical_edge] = str(target_label)
        else:
            edge_attribute_labels_by_label[canonical_edge] = str(rng.choice(edge_labels_supported))
    edge_label_counts_by_value = {
        str(label): sum(
            1
            for edge in edge_labels
            if str(edge_attribute_labels_by_label[(str(edge[0]), str(edge[1]))]) == str(label)
        )
        for label in edge_labels_supported
    }

    return GraphEdgeAttributeLabelSample(
        graph=topology_sample.graph,
        directed=bool(topology_sample.directed),
        node_labels=tuple(str(label) for label in topology_sample.node_labels),
        edge_labels=tuple((str(left), str(right)) for left, right in topology_sample.edge_labels),
        degrees_by_label={str(key): int(value) for key, value in topology_sample.degrees_by_label.items()},
        in_degrees_by_label={str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()},
        out_degrees_by_label={str(key): int(value) for key, value in topology_sample.out_degrees_by_label.items()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.predecessors_by_label.items()},
        edge_count=int(topology_sample.edge_count),
        topology_profile=str(topology_sample.topology_profile),
        label_variant=str(topology_sample.label_variant),
        query_edge=(str(query_edge[0]), str(query_edge[1])),
        target_edge_label=str(target_label),
        edge_attribute_labels_by_label={
            (str(left), str(right)): str(label)
            for (left, right), label in edge_attribute_labels_by_label.items()
        },
        edge_label_counts_by_value={str(key): int(value) for key, value in edge_label_counts_by_value.items()},
        graph_directionality=str(directionality),
        query_path_labels=tuple(str(label) for label in path_labels),
        query_path_edge_index=0,
        query_path_edge_position="first",
    )


__all__ = [
    'sample_edge_attribute_path_label_graph',
]
