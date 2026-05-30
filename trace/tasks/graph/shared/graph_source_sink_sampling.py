"""Source/sink count samplers for graph-domain node-link tasks."""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Tuple

import networkx as nx

from .graph_edge_sampling import (
    _add_directed_edge_without_reciprocal,
    _profile_extra_edge_budget,
)
from .graph_sample_types import (
    SUPPORTED_SOURCE_SINK_MODES,
    GraphSourceSinkSample,
    graph_label_sort_key,
)
from .graph_topology_helpers import _build_labeled_graph_topology_sample, _has_reciprocal_edges


def _try_sample_source_sink_directed_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    source_sink_mode: str,
) -> nx.DiGraph | None:
    """Construct one directed graph with an exact source/sink count."""

    node_count_int = int(node_count)
    target_count_int = int(target_count)
    max_degree_int = max(1, int(max_degree))
    if node_count_int < 3 or target_count_int < 0 or target_count_int >= node_count_int:
        return None
    mode = str(source_sink_mode)
    if mode not in SUPPORTED_SOURCE_SINK_MODES:
        raise ValueError(f"unsupported source/sink mode: {source_sink_mode}")

    graph = nx.DiGraph()
    graph.add_nodes_from(range(node_count_int))
    nodes = [int(node) for node in range(node_count_int)]
    target_nodes = set(rng.sample(nodes, int(target_count_int))) if target_count_int else set()
    non_target_nodes = [int(node) for node in nodes if int(node) not in target_nodes]

    if int(target_count_int) == 0:
        cycle_nodes = list(nodes)
        rng.shuffle(cycle_nodes)
        for index, source in enumerate(cycle_nodes):
            target = cycle_nodes[(int(index) + 1) % len(cycle_nodes)]
            graph.add_edge(int(source), int(target))
    elif mode == "source":
        shuffled_targets = list(non_target_nodes)
        rng.shuffle(shuffled_targets)
        for target in shuffled_targets:
            candidates = [int(node) for node in nodes if int(node) != int(target)]
            rng.shuffle(candidates)
            added = False
            for source in candidates:
                if _add_directed_edge_without_reciprocal(
                    graph,
                    source=int(source),
                    target=int(target),
                    max_degree=int(max_degree_int),
                ):
                    added = True
                    break
            if not bool(added):
                return None
    else:
        shuffled_sources = list(non_target_nodes)
        rng.shuffle(shuffled_sources)
        for source in shuffled_sources:
            candidates = [int(node) for node in nodes if int(node) != int(source)]
            rng.shuffle(candidates)
            added = False
            for target in candidates:
                if _add_directed_edge_without_reciprocal(
                    graph,
                    source=int(source),
                    target=int(target),
                    max_degree=int(max_degree_int),
                ):
                    added = True
                    break
            if not bool(added):
                return None

    extra_edges = _profile_extra_edge_budget(
        node_count=int(node_count_int),
        topology_profile=str(topology_profile),
        directed=True,
    )
    candidates = [
        (int(source), int(target))
        for source in nodes
        for target in nodes
        if int(source) != int(target)
    ]
    rng.shuffle(candidates)
    added_extra = 0
    for source, target in candidates:
        if int(added_extra) >= int(extra_edges):
            break
        if mode == "source" and int(target) in target_nodes:
            continue
        if mode == "sink" and int(source) in target_nodes:
            continue
        if _add_directed_edge_without_reciprocal(
            graph,
            source=int(source),
            target=int(target),
            max_degree=int(max_degree_int),
        ):
            added_extra += 1

    if _has_reciprocal_edges(graph):
        return None
    if mode == "source":
        observed = sum(1 for node in nodes if int(graph.in_degree(int(node))) == 0)
    else:
        observed = sum(1 for node in nodes if int(graph.out_degree(int(node))) == 0)
    if int(observed) != int(target_count_int):
        return None
    return graph


@lru_cache(maxsize=128)
def feasible_node_counts_for_source_sink_count(
    *,
    source_sink_mode: str,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
    max_degree: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize the requested source/sink count."""

    if str(source_sink_mode) not in SUPPORTED_SOURCE_SINK_MODES:
        return ()
    if int(max_degree) < 1 or int(target_count) < 0:
        return ()
    return tuple(
        int(node_count)
        for node_count in range(int(node_count_min), int(node_count_max) + 1)
        if int(node_count) >= 3 and int(target_count) < int(node_count)
    )


def sample_source_sink_count_graph(
    rng: random.Random,
    *,
    source_sink_mode: str,
    node_count: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    label_variant: str,
    search_attempts: int = 100,
) -> GraphSourceSinkSample:
    """Construct one labeled directed graph with the requested source/sink support."""

    mode = str(source_sink_mode)
    if mode not in SUPPORTED_SOURCE_SINK_MODES:
        raise ValueError(f"unsupported source/sink mode: {source_sink_mode}")
    graph = None
    for _ in range(max(1, int(search_attempts))):
        graph = _try_sample_source_sink_directed_graph(
            rng,
            node_count=int(node_count),
            target_count=int(target_count),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
            source_sink_mode=str(mode),
        )
        if graph is not None:
            break
    if graph is None:
        raise ValueError("failed to sample a simple directed graph for the requested source/sink count")

    topology_sample, _label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=True,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    degree_mode = "in_degree" if mode == "source" else "out_degree"
    degree_map = topology_sample.in_degrees_by_label if mode == "source" else topology_sample.out_degrees_by_label
    target_labels = tuple(
        sorted((label for label, degree in degree_map.items() if int(degree) == 0), key=graph_label_sort_key)
    )
    return GraphSourceSinkSample(
        graph=topology_sample.graph,
        directed=True,
        node_labels=tuple(str(label) for label in topology_sample.node_labels),
        edge_labels=tuple((str(left), str(right)) for left, right in topology_sample.edge_labels),
        degrees_by_label={str(key): int(value) for key, value in degree_map.items()},
        in_degrees_by_label={str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()},
        out_degrees_by_label={str(key): int(value) for key, value in topology_sample.out_degrees_by_label.items()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.predecessors_by_label.items()},
        edge_count=int(topology_sample.edge_count),
        topology_profile=str(topology_sample.topology_profile),
        label_variant=str(topology_sample.label_variant),
        target_labels=tuple(str(label) for label in target_labels),
        target_count=int(target_count),
        source_sink_mode=str(mode),
        degree_mode=str(degree_mode),
        in_degree_sequence=tuple(int(degree) for _, degree in graph.in_degree()),
        out_degree_sequence=tuple(int(degree) for _, degree in graph.out_degree()),
    )


__all__ = [
    "_try_sample_source_sink_directed_graph",
    "feasible_node_counts_for_source_sink_count",
    "sample_source_sink_count_graph",
]
