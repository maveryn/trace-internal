"""Shared graph-domain sampling helpers for simple node-link scenes."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Mapping, Sequence, Tuple

import networkx as nx

from ...shared.labeling import LABEL_POOL_A_L, assign_shuffled_labels


SUPPORTED_LAYOUT_VARIANTS: Tuple[str, ...] = ("circular", "shell", "spring")
SUPPORTED_TOPOLOGY_PROFILES: Tuple[str, ...] = ("balanced", "low_degree", "hub_heavy")
SUPPORTED_LABEL_VARIANTS: Tuple[str, ...] = ("letters", "numbers")
LABEL_POOL_1_12: Tuple[str, ...] = tuple(str(value) for value in range(1, 13))


@dataclass(frozen=True)
class GraphCountSample:
    """Trace-ready simple graph sample for graph counting tasks."""

    graph: nx.Graph
    node_labels: Tuple[str, ...]
    edge_labels: Tuple[Tuple[str, str], ...]
    degrees_by_label: Dict[str, int]
    adjacency_by_label: Dict[str, Tuple[str, ...]]
    target_labels: Tuple[str, ...]
    degree_sequence: Tuple[int, ...]
    query_degree: int
    edge_count: int
    topology_profile: str
    label_variant: str


def graph_label_sort_key(label: str) -> Tuple[int, int | str]:
    """Return one natural sort key for graph node labels."""

    text = str(label)
    if str(text).isdigit():
        return (0, int(text))
    return (1, str(text))


def _profile_weight(degree_value: int, *, topology_profile: str) -> float:
    """Return one degree-sampling weight for the requested topology profile."""

    degree = int(degree_value)
    profile = str(topology_profile)
    if profile == "low_degree":
        return float({0: 4.0, 1: 4.0, 2: 3.0, 3: 1.5, 4: 1.0, 5: 0.75}.get(degree, 0.5))
    if profile == "hub_heavy":
        return float({0: 0.8, 1: 1.0, 2: 1.5, 3: 2.5, 4: 3.5, 5: 4.0}.get(degree, 1.0))
    return 1.0


def _draw_other_degree(
    rng: random.Random,
    *,
    allowed_degrees: Sequence[int],
    query_degree: int,
    topology_profile: str,
) -> int:
    """Draw one non-query degree under the requested topology profile."""

    candidates = [int(value) for value in allowed_degrees if int(value) != int(query_degree)]
    if not candidates:
        raise ValueError("no non-query degrees available")
    weights = [_profile_weight(value, topology_profile=str(topology_profile)) for value in candidates]
    return int(rng.choices(candidates, weights=weights, k=1)[0])


def _parity_adjusted_sequence(
    rng: random.Random,
    *,
    node_count: int,
    query_degree: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
) -> Tuple[int, ...] | None:
    """Sample one parity-valid candidate degree sequence with exact query-degree count."""

    allowed = tuple(range(0, min(int(max_degree), int(node_count) - 1) + 1))
    if int(query_degree) not in allowed:
        return None
    remainder_count = int(node_count) - int(target_count)
    if int(remainder_count) < 0:
        return None
    other_allowed = tuple(int(value) for value in allowed if int(value) != int(query_degree))
    if int(remainder_count) > 0 and not other_allowed:
        return None

    sequence = [int(query_degree)] * int(target_count)
    sequence.extend(
        _draw_other_degree(
            rng,
            allowed_degrees=other_allowed,
            query_degree=int(query_degree),
            topology_profile=str(topology_profile),
        )
        for _ in range(int(remainder_count))
    )
    if not sequence:
        return None
    if sum(sequence) % 2 == 0:
        rng.shuffle(sequence)
        return tuple(int(value) for value in sequence)

    adjustable_indices = list(range(int(target_count), len(sequence)))
    rng.shuffle(adjustable_indices)
    for index in adjustable_indices:
        current = int(sequence[index])
        parity_flipped = [
            int(value)
            for value in other_allowed
            if int(value) != int(current) and (int(value) % 2) != (int(current) % 2)
        ]
        if parity_flipped:
            sequence[index] = int(rng.choice(parity_flipped))
            rng.shuffle(sequence)
            return tuple(int(value) for value in sequence)
    return None


def _find_graph_with_degree_count(
    rng: random.Random,
    *,
    node_count: int,
    query_degree: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    search_attempts: int,
) -> Tuple[nx.Graph, Tuple[int, ...]] | None:
    """Search for one simple graph with exactly ``target_count`` query-degree nodes."""

    for _ in range(max(1, int(search_attempts))):
        candidate_sequence = _parity_adjusted_sequence(
            rng,
            node_count=int(node_count),
            query_degree=int(query_degree),
            target_count=int(target_count),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
        )
        if candidate_sequence is None:
            continue
        if not nx.is_graphical(candidate_sequence, method="hh"):
            continue
        graph = nx.havel_hakimi_graph(candidate_sequence)
        if sum(1 for _, degree in graph.degree() if int(degree) == int(query_degree)) != int(target_count):
            continue
        if graph.number_of_edges() >= 2:
            nswap = max(1, min(int(graph.number_of_edges()) * 2, 16))
            try:
                nx.double_edge_swap(
                    graph,
                    nswap=int(nswap),
                    max_tries=int(nswap) * 10,
                    seed=int(rng.randrange(1, 2**31 - 1)),
                )
            except Exception:
                pass
        return graph, tuple(int(value) for value in candidate_sequence)
    return None


@lru_cache(maxsize=128)
def feasible_node_counts_for_degree_count(
    *,
    query_degree: int,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
    max_degree: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize the requested degree-count query."""

    support = []
    for node_count in range(int(node_count_min), int(node_count_max) + 1):
        feasibility_rng = random.Random(
            f"graph-degree-feasibility:{int(node_count)}:{int(query_degree)}:{int(target_count)}:{int(max_degree)}"
        )
        result = _find_graph_with_degree_count(
            feasibility_rng,
            node_count=int(node_count),
            query_degree=int(query_degree),
            target_count=int(target_count),
            max_degree=int(max_degree),
            topology_profile="balanced",
            search_attempts=600,
        )
        if result is not None:
            support.append(int(node_count))
    return tuple(int(value) for value in support)


def sample_degree_count_graph(
    rng: random.Random,
    *,
    node_count: int,
    query_degree: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    label_variant: str,
    search_attempts: int,
) -> GraphCountSample:
    """Construct one labeled undirected graph with the requested degree count."""

    result = _find_graph_with_degree_count(
        rng,
        node_count=int(node_count),
        query_degree=int(query_degree),
        target_count=int(target_count),
        max_degree=int(max_degree),
        topology_profile=str(topology_profile),
        search_attempts=int(search_attempts),
    )
    if result is None:
        raise ValueError("failed to sample a simple graph for the requested degree-count support")
    graph, degree_sequence = result

    node_order = tuple(int(node) for node in graph.nodes())
    if str(label_variant) == "numbers":
        label_pool = LABEL_POOL_1_12
    else:
        label_pool = LABEL_POOL_A_L
    labels = assign_shuffled_labels(rng, object_count=int(node_count), label_pool=label_pool)
    label_by_node = {int(node): str(label) for node, label in zip(node_order, labels)}

    labeled_edges = sorted(
        (
            tuple(sorted((str(label_by_node[int(left)]), str(label_by_node[int(right)]))))
            for left, right in graph.edges()
        ),
        key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1])),
    )
    degrees_by_label = {
        str(label_by_node[int(node)]): int(degree)
        for node, degree in graph.degree()
    }
    adjacency_by_label = {
        str(label_by_node[int(node)]): tuple(
            sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.neighbors(int(node))), key=graph_label_sort_key)
        )
        for node in node_order
    }
    target_labels = tuple(
        sorted((label for label, degree in degrees_by_label.items() if int(degree) == int(query_degree)), key=graph_label_sort_key)
    )
    return GraphCountSample(
        graph=graph,
        node_labels=tuple(str(label_by_node[int(node)]) for node in node_order),
        edge_labels=tuple((str(left), str(right)) for left, right in labeled_edges),
        degrees_by_label={str(key): int(value) for key, value in degrees_by_label.items()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in adjacency_by_label.items()},
        target_labels=tuple(str(label) for label in target_labels),
        degree_sequence=tuple(int(value) for value in degree_sequence),
        query_degree=int(query_degree),
        edge_count=int(graph.number_of_edges()),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )


__all__ = [
    "GraphCountSample",
    "LABEL_POOL_1_12",
    "SUPPORTED_LAYOUT_VARIANTS",
    "SUPPORTED_LABEL_VARIANTS",
    "SUPPORTED_TOPOLOGY_PROFILES",
    "feasible_node_counts_for_degree_count",
    "graph_label_sort_key",
    "sample_degree_count_graph",
]
