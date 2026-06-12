"""Neutral sampling helpers for graph flow-network scenes."""

from __future__ import annotations

import random
from itertools import combinations
from typing import Dict, Mapping, Sequence, Tuple

import networkx as nx

from ...shared.graph_sample_types import (
    GraphTopologySample,
    canonicalize_graph_edge_label,
    graph_label_sort_key,
)
from .state import (
    FLOW_INTERNAL_LABELS,
    CutResult,
    FlowNetworkAxes,
    FlowNetworkDefaults,
    FlowNetworkSample,
)


def node_labels(node_count: int) -> Tuple[str, ...]:
    """Return conventional source/sink labels plus compact internal labels."""

    internal_count = max(0, int(node_count) - 2)
    if int(internal_count) > len(FLOW_INTERNAL_LABELS):
        raise ValueError("flow network node_count exceeds available internal labels")
    return ("S", *tuple(FLOW_INTERNAL_LABELS[: int(internal_count)]), "T")


def positive_capacity_parts(
    rng: random.Random,
    *,
    total: int,
    count: int,
    max_part: int,
) -> Tuple[int, ...]:
    """Sample positive integer capacities with a fixed sum and per-edge cap."""

    total_int = int(total)
    count_int = int(count)
    max_part_int = int(max_part)
    if count_int <= 0 or total_int < count_int or total_int > count_int * max_part_int:
        raise ValueError("infeasible capacity composition")
    candidates: list[Tuple[int, ...]] = []

    def _recurse(prefix: Tuple[int, ...], remaining: int, slots: int) -> None:
        if int(slots) == 0:
            if int(remaining) == 0:
                candidates.append(tuple(int(value) for value in prefix))
            return
        low = max(1, int(remaining) - ((int(slots) - 1) * int(max_part_int)))
        high = min(int(max_part_int), int(remaining) - (int(slots) - 1))
        for value in range(int(low), int(high) + 1):
            _recurse((*prefix, int(value)), int(remaining) - int(value), int(slots) - 1)

    _recurse((), int(total_int), int(count_int))
    if not candidates:
        raise ValueError("no capacity composition candidates")
    return tuple(int(value) for value in rng.choice(candidates))


def all_st_cuts(
    graph: nx.DiGraph,
    *,
    source: int,
    sink: int,
    capacity_by_edge: Mapping[Tuple[int, int], int],
) -> Tuple[CutResult, ...]:
    """Enumerate all source-sink cuts for a small directed network."""

    nodes = tuple(sorted(int(node) for node in graph.nodes()))
    internal_nodes = tuple(int(node) for node in nodes if int(node) not in {int(source), int(sink)})
    active_edges = tuple((int(left), int(right)) for left, right in graph.edges())
    cuts: list[CutResult] = []
    for subset_size in range(0, len(internal_nodes) + 1):
        for subset in combinations(internal_nodes, subset_size):
            source_side = tuple(sorted((int(source), *tuple(int(value) for value in subset))))
            source_set = set(source_side)
            sink_side = tuple(sorted(int(node) for node in nodes if int(node) not in source_set))
            cut_edges = tuple(
                sorted(
                    ((int(left), int(right)) for left, right in active_edges if int(left) in source_set and int(right) not in source_set),
                    key=lambda edge: (int(edge[0]), int(edge[1])),
                )
            )
            value = sum(int(capacity_by_edge[(int(left), int(right))]) for left, right in cut_edges)
            cuts.append(
                CutResult(
                    value=int(value),
                    source_side=tuple(int(node) for node in source_side),
                    sink_side=tuple(int(node) for node in sink_side),
                    edges=tuple((int(left), int(right)) for left, right in cut_edges),
                )
            )
    return tuple(cuts)


def unique_min_cut(
    graph: nx.DiGraph,
    *,
    source: int,
    sink: int,
    capacity_by_edge: Mapping[Tuple[int, int], int],
) -> CutResult:
    """Return the unique minimum source-sink cut or raise."""

    cuts = all_st_cuts(
        graph,
        source=int(source),
        sink=int(sink),
        capacity_by_edge=capacity_by_edge,
    )
    if not cuts:
        raise ValueError("no source-sink cuts found")
    min_value = min(int(cut.value) for cut in cuts)
    min_cuts = tuple(cut for cut in cuts if int(cut.value) == int(min_value))
    unique_edge_sets = {tuple(cut.edges) for cut in min_cuts}
    if len(min_cuts) != 1 or len(unique_edge_sets) != 1:
        raise ValueError("minimum source-sink cut is not unique")
    return min_cuts[0]


def build_topology_sample(
    *,
    graph: nx.DiGraph,
    labels: Sequence[str],
) -> GraphTopologySample:
    """Build a generic graph topology record for one directed flow network."""

    label_by_node = {int(node): str(labels[int(node)]) for node in graph.nodes()}
    edge_labels = tuple(
        sorted(
            ((str(label_by_node[int(left)]), str(label_by_node[int(right)])) for left, right in graph.edges()),
            key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1])),
        )
    )
    adjacency_by_label = {
        str(label_by_node[int(node)]): tuple(
            sorted(
                {
                    *[str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node))],
                    *[str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node))],
                },
                key=graph_label_sort_key,
            )
        )
        for node in graph.nodes()
    }
    successors_by_label = {
        str(label_by_node[int(node)]): tuple(
            sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node))), key=graph_label_sort_key)
        )
        for node in graph.nodes()
    }
    predecessors_by_label = {
        str(label_by_node[int(node)]): tuple(
            sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node))), key=graph_label_sort_key)
        )
        for node in graph.nodes()
    }
    return GraphTopologySample(
        graph=graph,
        directed=True,
        node_labels=tuple(str(label_by_node[int(node)]) for node in graph.nodes()),
        edge_labels=tuple((str(left), str(right)) for left, right in edge_labels),
        degrees_by_label={
            str(label_by_node[int(node)]): int(graph.in_degree(int(node)) + graph.out_degree(int(node)))
            for node in graph.nodes()
        },
        in_degrees_by_label={str(label_by_node[int(node)]): int(graph.in_degree(int(node))) for node in graph.nodes()},
        out_degrees_by_label={str(label_by_node[int(node)]): int(graph.out_degree(int(node))) for node in graph.nodes()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in predecessors_by_label.items()},
        edge_count=int(graph.number_of_edges()),
        topology_profile="layered_capacity_network",
        label_variant="source_sink_letters",
    )


def sample_flow_network(
    rng: random.Random,
    *,
    axes: FlowNetworkAxes,
    defaults: FlowNetworkDefaults,
) -> FlowNetworkSample:
    """Construct one capacitated directed graph with a unique source-sink cut."""

    node_count = int(axes.node_count)
    labels = node_labels(node_count)
    source = 0
    sink = int(node_count) - 1
    internal_nodes = tuple(int(node) for node in range(1, int(node_count) - 1))
    if len(internal_nodes) < 2:
        raise ValueError("flow network requires at least two internal nodes")
    source_side_count = int(rng.randint(1, len(internal_nodes) - 1))
    source_internal = tuple(int(node) for node in internal_nodes[: int(source_side_count)])
    sink_internal = tuple(int(node) for node in internal_nodes[int(source_side_count) :])
    source_side_nodes = (int(source), *tuple(int(node) for node in source_internal))
    sink_side_nodes = (*tuple(int(node) for node in sink_internal), int(sink))

    candidate_cut_edges = [
        (int(left), int(right))
        for left in source_side_nodes
        for right in sink_side_nodes
        if int(left) != int(right) and not (int(left) == int(source) and int(right) == int(sink))
    ]
    if len(candidate_cut_edges) < int(axes.target_cut_edge_count):
        raise ValueError("not enough candidate cut edges")
    rng.shuffle(candidate_cut_edges)
    cut_edges = tuple(sorted(candidate_cut_edges[: int(axes.target_cut_edge_count)], key=lambda edge: (int(edge[0]), int(edge[1]))))

    graph = nx.DiGraph()
    graph.add_nodes_from(range(int(node_count)))
    capacity_by_edge: Dict[Tuple[int, int], int] = {}
    high_capacity = int(axes.target_flow_value) + int(rng.randint(5, 9))

    def _add_edge(left: int, right: int, capacity: int) -> None:
        if int(left) == int(right):
            return
        graph.add_edge(int(left), int(right))
        graph[int(left)][int(right)]["capacity"] = int(capacity)
        capacity_by_edge[(int(left), int(right))] = int(capacity)

    for node in source_internal:
        _add_edge(int(source), int(node), int(high_capacity + rng.randint(0, 3)))
    for node in sink_internal:
        _add_edge(int(node), int(sink), int(high_capacity + rng.randint(0, 3)))

    possible_internal = [
        (int(left), int(right))
        for left in source_internal
        for right in source_internal
        if int(left) < int(right)
    ] + [
        (int(left), int(right))
        for left in sink_internal
        for right in sink_internal
        if int(left) < int(right)
    ]
    rng.shuffle(possible_internal)
    for left, right in possible_internal[: int(axes.distractor_edge_count)]:
        _add_edge(int(left), int(right), int(high_capacity + rng.randint(0, 3)))

    parts = positive_capacity_parts(
        rng,
        total=int(axes.target_flow_value),
        count=len(cut_edges),
        max_part=int(defaults.cut_capacity_part_max),
    )
    cut_capacities = {tuple(edge): int(capacity) for edge, capacity in zip(cut_edges, parts)}

    for edge in cut_edges:
        _add_edge(int(edge[0]), int(edge[1]), int(cut_capacities[tuple(edge)]))

    original_cut = unique_min_cut(
        graph,
        source=int(source),
        sink=int(sink),
        capacity_by_edge=capacity_by_edge,
    )
    original_flow = int(nx.maximum_flow_value(graph, int(source), int(sink), capacity="capacity"))
    if int(original_flow) != int(axes.target_flow_value):
        raise ValueError("constructed flow network has wrong max-flow value")

    topology_sample = build_topology_sample(graph=graph, labels=labels)
    capacity_by_label = {
        canonicalize_graph_edge_label(str(labels[int(left)]), str(labels[int(right)]), directed=True): int(capacity)
        for (left, right), capacity in capacity_by_edge.items()
    }

    def _label_edges(edges: Sequence[Tuple[int, int]]) -> Tuple[Tuple[str, str], ...]:
        return tuple(
            sorted(
                (
                    canonicalize_graph_edge_label(str(labels[int(left)]), str(labels[int(right)]), directed=True)
                    for left, right in edges
                ),
                key=lambda edge: (graph_label_sort_key(edge[0]), graph_label_sort_key(edge[1])),
            )
        )

    original_cut_labels = _label_edges(original_cut.edges)
    original_source_side_labels = tuple(sorted((str(labels[int(node)]) for node in original_cut.source_side), key=graph_label_sort_key))
    original_sink_side_labels = tuple(sorted((str(labels[int(node)]) for node in original_cut.sink_side), key=graph_label_sort_key))
    return FlowNetworkSample(
        graph_sample=topology_sample,
        source_label="S",
        sink_label="T",
        capacity_by_edge_label=dict(capacity_by_label),
        original_max_flow_value=int(original_flow),
        original_min_cut_edges=tuple(original_cut_labels),
        original_min_cut_partition=(tuple(original_source_side_labels), tuple(original_sink_side_labels)),
    )


__all__ = [
    "all_st_cuts",
    "build_topology_sample",
    "node_labels",
    "positive_capacity_parts",
    "sample_flow_network",
    "unique_min_cut",
]
