from __future__ import annotations

import random

import networkx as nx

from trace.tasks.graph.shared import graph_common_neighbor_sampling
from trace.tasks.graph.shared import graph_edge_sampling
from trace.tasks.graph.shared import graph_source_sink_sampling


def test_directed_edge_helper_rejects_reciprocal_edges() -> None:
    graph = nx.DiGraph()
    graph.add_nodes_from([0, 1, 2])

    assert graph_edge_sampling._add_directed_edge_without_reciprocal(
        graph,
        source=0,
        target=1,
        max_degree=2,
    )
    assert not graph_edge_sampling._add_directed_edge_without_reciprocal(
        graph,
        source=1,
        target=0,
        max_degree=2,
    )


def test_source_sink_sampler_constructs_requested_support() -> None:
    sample = graph_source_sink_sampling.sample_source_sink_count_graph(
        random.Random(1042),
        source_sink_mode="source",
        node_count=6,
        target_count=2,
        max_degree=3,
        topology_profile="balanced",
        label_variant="letters",
        search_attempts=200,
    )

    assert sample.directed is True
    assert sample.source_sink_mode == "source"
    assert sample.degree_mode == "in_degree"
    assert len(sample.target_labels) == 2
    assert all(sample.in_degrees_by_label[label] == 0 for label in sample.target_labels)


def test_common_neighbor_sampler_constructs_requested_support() -> None:
    sample = graph_common_neighbor_sampling.sample_common_neighbor_count_graph(
        random.Random(2042),
        common_neighbor_mode="undirected_common_neighbor",
        node_count=7,
        target_count=2,
        max_degree=4,
        topology_profile="balanced",
        label_variant="letters",
        search_attempts=200,
    )

    query_a = str(sample.query_label_a)
    query_b = str(sample.query_label_b)
    adjacency = {str(key): {str(value) for value in values} for key, values in sample.adjacency_by_label.items()}
    assert sample.directed is False
    assert sample.common_neighbor_mode == "undirected_common_neighbor"
    assert len(sample.target_labels) == 2
    assert sorted(adjacency[query_a] & adjacency[query_b]) == sorted(sample.target_labels)
