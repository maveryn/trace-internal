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
SUPPORTED_DEGREE_TASK_VARIANTS: Tuple[str, ...] = ("degree_count", "in_degree_count", "out_degree_count")
SUPPORTED_ARTICULATION_TASK_VARIANTS: Tuple[str, ...] = ("articulation_point_count",)
SUPPORTED_COMPONENT_TASK_VARIANTS: Tuple[str, ...] = ("same_component_count",)
SUPPORTED_CYCLE_TASK_VARIANTS: Tuple[str, ...] = ("unique_cycle_size",)
SUPPORTED_COMPONENT_COMPARISON_TASK_VARIANTS: Tuple[str, ...] = ("largest_component_size",)
LABEL_POOL_1_12: Tuple[str, ...] = tuple(str(value) for value in range(1, 13))


@dataclass(frozen=True)
class GraphTopologySample:
    """Trace-ready labeled graph topology shared across graph tasks."""

    graph: nx.Graph | nx.DiGraph
    directed: bool
    node_labels: Tuple[str, ...]
    edge_labels: Tuple[Tuple[str, str], ...]
    degrees_by_label: Dict[str, int]
    in_degrees_by_label: Dict[str, int]
    out_degrees_by_label: Dict[str, int]
    adjacency_by_label: Dict[str, Tuple[str, ...]]
    successors_by_label: Dict[str, Tuple[str, ...]]
    predecessors_by_label: Dict[str, Tuple[str, ...]]
    edge_count: int
    topology_profile: str
    label_variant: str


@dataclass(frozen=True)
class GraphCountSample(GraphTopologySample):
    """Trace-ready simple graph sample for graph counting tasks."""

    target_labels: Tuple[str, ...]
    degree_sequence: Tuple[int, ...]
    in_degree_sequence: Tuple[int, ...]
    out_degree_sequence: Tuple[int, ...]
    query_degree: int
    degree_mode: str


@dataclass(frozen=True)
class GraphComponentSample(GraphTopologySample):
    """Trace-ready disconnected graph sample for component-relation tasks."""

    query_label: str
    target_labels: Tuple[str, ...]
    components_by_label: Tuple[Tuple[str, ...], ...]
    component_sizes: Tuple[int, ...]
    component_count: int
    target_component_size: int


@dataclass(frozen=True)
class GraphLargestComponentSample(GraphTopologySample):
    """Trace-ready disconnected graph sample for largest-component tasks."""

    target_labels: Tuple[str, ...]
    components_by_label: Tuple[Tuple[str, ...], ...]
    component_sizes: Tuple[int, ...]
    component_count: int
    target_largest_component_size: int


@dataclass(frozen=True)
class GraphUniqueCycleSample(GraphTopologySample):
    """Trace-ready unicyclic graph sample for unique-cycle tasks."""

    target_labels: Tuple[str, ...]
    target_cycle_size: int
    attachment_count: int


@dataclass(frozen=True)
class GraphArticulationPointSample(GraphTopologySample):
    """Trace-ready graph sample for articulation-point counting tasks."""

    target_labels: Tuple[str, ...]
    target_count: int


def graph_label_sort_key(label: str) -> Tuple[int, int | str]:
    """Return one natural sort key for graph node labels."""

    text = str(label)
    if str(text).isdigit():
        return (0, int(text))
    return (1, str(text))


def graph_directionality_for_task_variant(task_variant: str) -> str:
    """Return the graph directionality implied by one task variant."""

    variant = str(task_variant)
    if variant in {"in_degree_count", "out_degree_count"}:
        return "directed"
    return "undirected"


def graph_degree_mode_for_task_variant(task_variant: str) -> str:
    """Return the query-degree mode implied by one task variant."""

    variant = str(task_variant)
    if variant == "in_degree_count":
        return "in_degree"
    if variant == "out_degree_count":
        return "out_degree"
    return "degree"


def _profile_weight(degree_value: int, *, topology_profile: str) -> float:
    """Return one degree-sampling weight for the requested topology profile."""

    degree = int(degree_value)
    profile = str(topology_profile)
    if profile == "low_degree":
        return float({0: 4.0, 1: 4.0, 2: 3.0, 3: 1.5, 4: 1.0, 5: 0.75}.get(degree, 0.5))
    if profile == "hub_heavy":
        return float({0: 0.8, 1: 1.0, 2: 1.5, 3: 2.5, 4: 3.5, 5: 4.0}.get(degree, 1.0))
    return 1.0


def _draw_degree(
    rng: random.Random,
    *,
    allowed_degrees: Sequence[int],
    topology_profile: str,
) -> int:
    """Draw one degree value under the requested topology profile."""

    candidates = [int(value) for value in allowed_degrees]
    if not candidates:
        raise ValueError("no degree candidates available")
    weights = [_profile_weight(value, topology_profile=str(topology_profile)) for value in candidates]
    return int(rng.choices(candidates, weights=weights, k=1)[0])


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
    return _draw_degree(rng, allowed_degrees=candidates, topology_profile=str(topology_profile))


def _sample_exact_query_sequence(
    rng: random.Random,
    *,
    node_count: int,
    query_degree: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
) -> Tuple[int, ...] | None:
    """Sample one degree sequence with exactly ``target_count`` query-degree entries."""

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
    rng.shuffle(sequence)
    return tuple(int(value) for value in sequence)


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
    other_allowed = tuple(int(value) for value in allowed if int(value) != int(query_degree))
    sequence = _sample_exact_query_sequence(
        rng,
        node_count=int(node_count),
        query_degree=int(query_degree),
        target_count=int(target_count),
        max_degree=int(max_degree),
        topology_profile=str(topology_profile),
    )
    if not sequence:
        return None
    if sum(sequence) % 2 == 0:
        return tuple(int(value) for value in sequence)

    mutable = list(int(value) for value in sequence)
    adjustable_indices = list(range(int(target_count), len(mutable)))
    rng.shuffle(adjustable_indices)
    for index in adjustable_indices:
        current = int(mutable[index])
        parity_flipped = [
            int(value)
            for value in other_allowed
            if int(value) != int(current) and (int(value) % 2) != (int(current) % 2)
        ]
        if parity_flipped:
            mutable[index] = int(rng.choice(parity_flipped))
            rng.shuffle(mutable)
            return tuple(int(value) for value in mutable)
    return None


def _sample_sum_matched_sequence(
    rng: random.Random,
    *,
    node_count: int,
    total_sum: int,
    max_degree: int,
    topology_profile: str,
) -> Tuple[int, ...] | None:
    """Sample one degree sequence whose entries stay within bounds and sum to ``total_sum``."""

    allowed = tuple(range(0, min(int(max_degree), int(node_count) - 1) + 1))
    if not allowed:
        return None
    min_total = int(min(allowed)) * int(node_count)
    max_total = int(max(allowed)) * int(node_count)
    if int(total_sum) < int(min_total) or int(total_sum) > int(max_total):
        return None
    sequence = [
        _draw_degree(
            rng,
            allowed_degrees=allowed,
            topology_profile=str(topology_profile),
        )
        for _ in range(int(node_count))
    ]
    current_total = int(sum(sequence))
    max_steps = max(16, int(node_count) * int(max_degree) * 4)
    for _ in range(int(max_steps)):
        if int(current_total) == int(total_sum):
            rng.shuffle(sequence)
            return tuple(int(value) for value in sequence)
        if int(current_total) < int(total_sum):
            adjustable = [index for index, value in enumerate(sequence) if int(value) < int(max(allowed))]
            if not adjustable:
                return None
            index = int(rng.choice(adjustable))
            sequence[index] = int(sequence[index]) + 1
            current_total += 1
        else:
            adjustable = [index for index, value in enumerate(sequence) if int(value) > int(min(allowed))]
            if not adjustable:
                return None
            index = int(rng.choice(adjustable))
            sequence[index] = int(sequence[index]) - 1
            current_total -= 1
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


def _label_pool_for_variant(label_variant: str) -> Tuple[str, ...]:
    """Return the configured node-label pool for one graph label variant."""

    if str(label_variant) == "numbers":
        return LABEL_POOL_1_12
    return LABEL_POOL_A_L


def _build_labeled_graph_topology_sample(
    rng: random.Random,
    *,
    graph: nx.Graph | nx.DiGraph,
    directed: bool,
    topology_profile: str,
    label_variant: str,
) -> Tuple[GraphTopologySample, Dict[int, str]]:
    """Attach prompt-facing labels and sorted adjacency metadata to one graph."""

    node_order = tuple(int(node) for node in graph.nodes())
    labels = assign_shuffled_labels(
        rng,
        object_count=int(graph.number_of_nodes()),
        label_pool=_label_pool_for_variant(str(label_variant)),
    )
    label_by_node = {int(node): str(label) for node, label in zip(node_order, labels)}

    if bool(directed):
        labeled_edges = sorted(
            (
                (str(label_by_node[int(left)]), str(label_by_node[int(right)]))
                for left, right in graph.edges()
            ),
            key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1])),
        )
        in_degrees_by_label = {str(label_by_node[int(node)]): int(degree) for node, degree in graph.in_degree()}
        out_degrees_by_label = {str(label_by_node[int(node)]): int(degree) for node, degree in graph.out_degree()}
        adjacency_by_label = {
            str(label_by_node[int(node)]): tuple(
                sorted(
                    (
                        {
                            *[str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node))],
                            *[str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node))],
                        }
                    ),
                    key=graph_label_sort_key,
                )
            )
            for node in node_order
        }
        successors_by_label = {
            str(label_by_node[int(node)]): tuple(
                sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node))), key=graph_label_sort_key)
            )
            for node in node_order
        }
        predecessors_by_label = {
            str(label_by_node[int(node)]): tuple(
                sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node))), key=graph_label_sort_key)
            )
            for node in node_order
        }
    else:
        labeled_edges = sorted(
            (
                tuple(sorted((str(label_by_node[int(left)]), str(label_by_node[int(right)])), key=graph_label_sort_key))
                for left, right in graph.edges()
            ),
            key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1])),
        )
        in_degrees_by_label = {str(label_by_node[int(node)]): int(degree) for node, degree in graph.degree()}
        out_degrees_by_label = {str(label_by_node[int(node)]): int(degree) for node, degree in graph.degree()}
        adjacency_by_label = {
            str(label_by_node[int(node)]): tuple(
                sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.neighbors(int(node))), key=graph_label_sort_key)
            )
            for node in node_order
        }
        successors_by_label = dict(adjacency_by_label)
        predecessors_by_label = dict(adjacency_by_label)

    topology = GraphTopologySample(
        graph=graph,
        directed=bool(directed),
        node_labels=tuple(str(label_by_node[int(node)]) for node in node_order),
        edge_labels=tuple((str(left), str(right)) for left, right in labeled_edges),
        degrees_by_label={str(key): int(value) for key, value in in_degrees_by_label.items()},
        in_degrees_by_label={str(key): int(value) for key, value in in_degrees_by_label.items()},
        out_degrees_by_label={str(key): int(value) for key, value in out_degrees_by_label.items()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in predecessors_by_label.items()},
        edge_count=int(graph.number_of_edges()),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    return topology, label_by_node


def _has_reciprocal_edges(graph: nx.DiGraph) -> bool:
    """Return whether one directed graph contains any reciprocal edge pair."""

    for left, right in graph.edges():
        if int(left) == int(right):
            return True
        if graph.has_edge(int(right), int(left)):
            return True
    return False


def _find_directed_graph_with_degree_count(
    rng: random.Random,
    *,
    node_count: int,
    query_degree: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    degree_mode: str,
    search_attempts: int,
) -> Tuple[nx.DiGraph, Tuple[int, ...], Tuple[int, ...]] | None:
    """Search for one simple directed graph with exact in/out-degree support."""

    mode = str(degree_mode)
    if mode not in {"in_degree", "out_degree"}:
        raise ValueError(f"unsupported directed degree mode: {degree_mode}")

    for _ in range(max(1, int(search_attempts))):
        queried_sequence = _sample_exact_query_sequence(
            rng,
            node_count=int(node_count),
            query_degree=int(query_degree),
            target_count=int(target_count),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
        )
        if queried_sequence is None:
            continue
        other_sequence = _sample_sum_matched_sequence(
            rng,
            node_count=int(node_count),
            total_sum=int(sum(queried_sequence)),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
        )
        if other_sequence is None:
            continue
        if mode == "in_degree":
            in_sequence = tuple(int(value) for value in queried_sequence)
            out_sequence = tuple(int(value) for value in other_sequence)
        else:
            in_sequence = tuple(int(value) for value in other_sequence)
            out_sequence = tuple(int(value) for value in queried_sequence)
        if not nx.is_digraphical(in_sequence, out_sequence):
            continue
        try:
            graph = nx.directed_havel_hakimi_graph(in_sequence, out_sequence)
        except Exception:
            continue
        if any(int(node) == int(neighbor) for node, neighbor in graph.edges()):
            continue
        if _has_reciprocal_edges(graph):
            continue
        observed = graph.in_degree if mode == "in_degree" else graph.out_degree
        if sum(1 for _, degree in observed() if int(degree) == int(query_degree)) != int(target_count):
            continue
        return graph, tuple(int(value) for value in in_sequence), tuple(int(value) for value in out_sequence)
    return None


@lru_cache(maxsize=128)
def feasible_node_counts_for_degree_count(
    *,
    task_variant: str,
    query_degree: int,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
    max_degree: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize the requested degree-count query."""

    support = []
    degree_mode = graph_degree_mode_for_task_variant(str(task_variant))
    for node_count in range(int(node_count_min), int(node_count_max) + 1):
        feasibility_rng = random.Random(
            f"graph-degree-feasibility:{str(task_variant)}:{int(node_count)}:{int(query_degree)}:{int(target_count)}:{int(max_degree)}"
        )
        if str(graph_directionality_for_task_variant(str(task_variant))) == "directed":
            result = _find_directed_graph_with_degree_count(
                feasibility_rng,
                node_count=int(node_count),
                query_degree=int(query_degree),
                target_count=int(target_count),
                max_degree=int(max_degree),
                topology_profile="balanced",
                degree_mode=str(degree_mode),
                search_attempts=600,
            )
        else:
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
    task_variant: str,
    node_count: int,
    query_degree: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    label_variant: str,
    search_attempts: int,
) -> GraphCountSample:
    """Construct one labeled graph with the requested degree-count support."""

    task_variant_text = str(task_variant)
    directionality = str(graph_directionality_for_task_variant(task_variant_text))
    degree_mode = str(graph_degree_mode_for_task_variant(task_variant_text))
    if directionality == "directed":
        result = _find_directed_graph_with_degree_count(
            rng,
            node_count=int(node_count),
            query_degree=int(query_degree),
            target_count=int(target_count),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
            degree_mode=str(degree_mode),
            search_attempts=int(search_attempts),
        )
        if result is None:
            raise ValueError("failed to sample a simple directed graph for the requested degree-count support")
        graph, in_degree_sequence, out_degree_sequence = result
        degree_sequence = in_degree_sequence if degree_mode == "in_degree" else out_degree_sequence
    else:
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
        in_degree_sequence = tuple(int(value) for value in degree_sequence)
        out_degree_sequence = tuple(int(value) for value in degree_sequence)

    topology_sample, _label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directionality == "directed"),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    if degree_mode == "in_degree":
        degrees_by_label = {str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()}
    elif degree_mode == "out_degree":
        degrees_by_label = {str(key): int(value) for key, value in topology_sample.out_degrees_by_label.items()}
    else:
        degrees_by_label = {str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()}
    target_labels = tuple(
        sorted((label for label, degree in degrees_by_label.items() if int(degree) == int(query_degree)), key=graph_label_sort_key)
    )
    return GraphCountSample(
        graph=topology_sample.graph,
        directed=bool(topology_sample.directed),
        node_labels=tuple(str(label) for label in topology_sample.node_labels),
        edge_labels=tuple((str(left), str(right)) for left, right in topology_sample.edge_labels),
        degrees_by_label={str(key): int(value) for key, value in degrees_by_label.items()},
        in_degrees_by_label={str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()},
        out_degrees_by_label={str(key): int(value) for key, value in topology_sample.out_degrees_by_label.items()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.predecessors_by_label.items()},
        edge_count=int(topology_sample.edge_count),
        topology_profile=str(topology_sample.topology_profile),
        label_variant=str(topology_sample.label_variant),
        target_labels=tuple(str(label) for label in target_labels),
        degree_sequence=tuple(int(value) for value in degree_sequence),
        in_degree_sequence=tuple(int(value) for value in in_degree_sequence),
        out_degree_sequence=tuple(int(value) for value in out_degree_sequence),
        query_degree=int(query_degree),
        degree_mode=str(degree_mode),
    )


def feasible_node_counts_for_component_query(
    *,
    target_component_size: int,
    component_count: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one disconnected component query."""

    minimum = max(int(node_count_min), int(target_component_size) + int(component_count) - 1)
    maximum = int(node_count_max)
    if int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def feasible_node_counts_for_unique_largest_component(
    *,
    target_largest_component_size: int,
    component_count: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one unique-largest-component query."""

    target_size = int(target_largest_component_size)
    components = int(component_count)
    if int(target_size) <= 1 or int(components) <= 1:
        return ()
    minimum = max(int(node_count_min), int(target_size) + int(components) - 1)
    maximum = min(int(node_count_max), int(target_size) + ((int(components) - 1) * (int(target_size) - 1)))
    if int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def feasible_node_counts_for_unique_cycle_size(
    *,
    target_cycle_size: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one unique-cycle-size query."""

    target_size = int(target_cycle_size)
    minimum = max(int(node_count_min), 4, int(target_size) + 1)
    maximum = int(node_count_max)
    if int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def feasible_node_counts_for_articulation_point_count(
    *,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one articulation-point count query."""

    target_int = int(target_count)
    if int(target_int) < 0:
        return ()
    minimum = int(node_count_min)
    if int(target_int) > 0:
        minimum = max(int(minimum), int(target_int) + 2)
    maximum = int(node_count_max)
    if int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def _random_positive_composition(
    rng: random.Random,
    *,
    total: int,
    parts: int,
) -> Tuple[int, ...]:
    """Split ``total`` into ``parts`` positive integers."""

    if int(parts) <= 0:
        if int(total) != 0:
            raise ValueError("cannot split a non-zero total into zero parts")
        return ()
    if int(total) < int(parts):
        raise ValueError("positive composition requires total >= parts")
    remaining = int(total) - int(parts)
    buckets = [1] * int(parts)
    for _ in range(int(remaining)):
        buckets[int(rng.randrange(int(parts)))] += 1
    rng.shuffle(buckets)
    return tuple(int(value) for value in buckets)


def _random_bounded_positive_composition(
    rng: random.Random,
    *,
    total: int,
    parts: int,
    max_value: int,
    attempts: int = 200,
) -> Tuple[int, ...] | None:
    """Split ``total`` into bounded positive integers when possible."""

    total_int = int(total)
    parts_int = int(parts)
    max_value_int = int(max_value)
    if int(parts_int) <= 0:
        return () if int(total_int) == 0 else None
    if int(total_int) < int(parts_int) or int(max_value_int) <= 0:
        return None
    if int(total_int) > int(parts_int * max_value_int):
        return None
    for _ in range(max(1, int(attempts))):
        values = [1] * int(parts_int)
        remaining = int(total_int - parts_int)
        while int(remaining) > 0:
            adjustable = [index for index, value in enumerate(values) if int(value) < int(max_value_int)]
            if not adjustable:
                break
            index = int(rng.choice(adjustable))
            values[index] += 1
            remaining -= 1
        if int(remaining) == 0:
            rng.shuffle(values)
            return tuple(int(value) for value in values)
    return None


def _random_tree_graph(rng: random.Random, *, size: int) -> nx.Graph:
    """Return one deterministic connected tree with ``size`` nodes."""

    graph = nx.Graph()
    graph.add_nodes_from(range(int(size)))
    for node in range(1, int(size)):
        graph.add_edge(int(node), int(rng.randrange(int(node))))
    return graph


def _add_random_non_edges(
    graph: nx.Graph,
    rng: random.Random,
    *,
    extra_edges: int,
) -> None:
    """Add up to ``extra_edges`` random non-edges to one simple graph."""

    non_edges = list(nx.non_edges(graph))
    rng.shuffle(non_edges)
    for left, right in non_edges[: max(0, int(extra_edges))]:
        graph.add_edge(int(left), int(right))


def _choose_attachment_parent(
    rng: random.Random,
    *,
    graph: nx.Graph,
    topology_profile: str,
) -> int:
    """Choose one attachment parent under the requested topology profile."""

    nodes = [int(node) for node in graph.nodes()]
    if not nodes:
        raise ValueError("attachment parent sampling requires at least one node")
    profile = str(topology_profile)
    if profile == "hub_heavy":
        weights = [float(graph.degree(int(node)) + 1) ** 2 for node in nodes]
    elif profile == "low_degree":
        weights = [1.0 / float(graph.degree(int(node)) + 1) for node in nodes]
    else:
        weights = [1.0 for _ in nodes]
    return int(rng.choices(nodes, weights=weights, k=1)[0])


def _sample_unicyclic_graph(
    rng: random.Random,
    *,
    node_count: int,
    cycle_size: int,
    topology_profile: str,
) -> nx.Graph:
    """Return one connected unicyclic graph with the requested unique cycle size."""

    node_count_int = int(node_count)
    cycle_size_int = int(cycle_size)
    if int(cycle_size_int) < 3 or int(cycle_size_int) > int(node_count_int):
        raise ValueError("cycle size must lie in [3, node_count] for unicyclic sampling")

    graph = nx.cycle_graph(int(cycle_size_int))
    next_node = int(cycle_size_int)
    while int(next_node) < int(node_count_int):
        parent = _choose_attachment_parent(
            rng,
            graph=graph,
            topology_profile=str(topology_profile),
        )
        graph.add_node(int(next_node))
        graph.add_edge(int(parent), int(next_node))
        next_node += 1

    cycle_basis = nx.cycle_basis(graph)
    if len(cycle_basis) != 1 or len(cycle_basis[0]) != int(cycle_size_int):
        raise ValueError("unicyclic sampler failed to preserve the requested unique cycle")
    return graph


def _sample_zero_articulation_graph(
    rng: random.Random,
    *,
    node_count: int,
    topology_profile: str,
) -> nx.Graph:
    """Return one simple graph with zero articulation points."""

    node_count_int = int(node_count)
    if int(node_count_int) < 3:
        raise ValueError("zero-articulation sampling requires at least three nodes")
    graph = nx.cycle_graph(int(node_count_int))
    profile = str(topology_profile)
    if profile != "low_degree":
        max_extra = max(0, min(int(node_count_int // 2), ((node_count_int * (node_count_int - 1)) // 2) - int(node_count_int)))
        extra_edges = int(rng.randint(0, max_extra))
        _add_random_non_edges(graph, rng, extra_edges=int(extra_edges))
    if any(True for _ in nx.articulation_points(graph)):
        raise ValueError("zero-articulation sampler produced an articulation point")
    return graph


def _edge_weight_for_profile(
    graph: nx.Graph,
    *,
    edge: Tuple[int, int],
    topology_profile: str,
) -> float:
    """Return one edge-selection weight for articulation-preserving expansion."""

    left, right = int(edge[0]), int(edge[1])
    profile = str(topology_profile)
    degree_sum = float(graph.degree(left) + graph.degree(right))
    if profile == "hub_heavy":
        return float((degree_sum + 2.0) ** 2)
    if profile == "low_degree":
        return 1.0 / float(degree_sum + 2.0)
    return 1.0


def _sample_articulation_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_count: int,
    topology_profile: str,
    attempts: int = 200,
) -> nx.Graph:
    """Return one graph with the requested articulation-point count."""

    node_count_int = int(node_count)
    target_count_int = int(target_count)
    if int(target_count_int) < 0 or int(target_count_int) > max(0, int(node_count_int) - 2):
        raise ValueError("target articulation count is outside feasible bounds")
    if int(target_count_int) == 0:
        return _sample_zero_articulation_graph(
            rng,
            node_count=int(node_count_int),
            topology_profile=str(topology_profile),
        )

    for _ in range(max(1, int(attempts))):
        graph = nx.path_graph(int(target_count_int) + 2)
        next_node = int(target_count_int) + 2
        while int(next_node) < int(node_count_int):
            edges = [(int(left), int(right)) for left, right in graph.edges()]
            if not edges:
                break
            weights = [
                _edge_weight_for_profile(
                    graph,
                    edge=(int(left), int(right)),
                    topology_profile=str(topology_profile),
                )
                for left, right in edges
            ]
            left, right = rng.choices(edges, weights=weights, k=1)[0]
            graph.add_node(int(next_node))
            graph.add_edge(int(next_node), int(left))
            graph.add_edge(int(next_node), int(right))
            next_node += 1
        articulation_nodes = tuple(sorted((int(node) for node in nx.articulation_points(graph))))
        if len(articulation_nodes) == int(target_count_int):
            return graph
    raise ValueError("failed to sample the requested articulation-point support")


def _sample_connected_component_graph(
    rng: random.Random,
    *,
    size: int,
    topology_profile: str,
) -> nx.Graph:
    """Return one connected component graph matching the requested profile."""

    node_count = int(size)
    if int(node_count) <= 0:
        raise ValueError("component size must be positive")
    if int(node_count) == 1:
        graph = nx.Graph()
        graph.add_node(0)
        return graph

    profile = str(topology_profile)
    if profile == "hub_heavy":
        graph = nx.star_graph(int(node_count) - 1)
        max_extra = max(0, min(int(node_count - 2), ((int(node_count) - 1) * (int(node_count) - 2)) // 2))
        _add_random_non_edges(graph, rng, extra_edges=int(rng.randint(0, max_extra if max_extra > 0 else 0)))
        return graph

    graph = _random_tree_graph(rng, size=int(node_count))
    if profile == "low_degree":
        max_extra = 1 if int(node_count) >= 4 else 0
    else:
        complete_edges = (int(node_count) * (int(node_count) - 1)) // 2
        max_extra = max(0, min(complete_edges - (int(node_count) - 1), int(node_count // 2) + 1))
    _add_random_non_edges(graph, rng, extra_edges=int(rng.randint(0, max_extra if max_extra > 0 else 0)))
    return graph


def _build_disconnected_component_graph(
    rng: random.Random,
    *,
    component_sizes: Sequence[int],
    topology_profile: str,
    label_variant: str,
) -> Tuple[GraphTopologySample, Dict[int, str], Tuple[Tuple[int, ...], ...]]:
    """Build one labeled disconnected graph from explicit component sizes."""

    graph = nx.Graph()
    component_nodes: list[Tuple[int, ...]] = []
    node_offset = 0
    for size in component_sizes:
        component_graph = _sample_connected_component_graph(
            rng,
            size=int(size),
            topology_profile=str(topology_profile),
        )
        mapping = {int(node): int(node + node_offset) for node in component_graph.nodes()}
        component_graph = nx.relabel_nodes(component_graph, mapping, copy=True)
        graph.add_nodes_from(component_graph.nodes())
        graph.add_edges_from(component_graph.edges())
        ordered_nodes = tuple(sorted((int(node) for node in component_graph.nodes())))
        component_nodes.append(ordered_nodes)
        node_offset += int(size)

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=False,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    return topology_sample, label_by_node, tuple(component_nodes)


def sample_component_count_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_component_size: int,
    component_count: int,
    topology_profile: str,
    label_variant: str,
) -> GraphComponentSample:
    """Construct one disconnected undirected graph for same-component queries."""

    node_count_int = int(node_count)
    target_size_int = int(target_component_size)
    component_count_int = int(component_count)
    feasible_node_support = feasible_node_counts_for_component_query(
        target_component_size=int(target_size_int),
        component_count=int(component_count_int),
        node_count_min=int(target_size_int + component_count_int - 1),
        node_count_max=int(node_count_int),
    )
    if int(node_count_int) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested component query")

    target_component_index = int(rng.randrange(int(component_count_int)))
    remaining_nodes = int(node_count_int - target_size_int)
    other_sizes = list(
        _random_positive_composition(
            rng,
            total=int(remaining_nodes),
            parts=int(component_count_int - 1),
        )
    )
    component_sizes = []
    for component_index in range(int(component_count_int)):
        if int(component_index) == int(target_component_index):
            component_sizes.append(int(target_size_int))
        else:
            component_sizes.append(int(other_sizes.pop()))

    topology_sample, label_by_node, component_nodes = _build_disconnected_component_graph(
        rng,
        component_sizes=tuple(int(size) for size in component_sizes),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    target_nodes = tuple(int(node) for node in component_nodes[int(target_component_index)])
    query_node = int(rng.choice(target_nodes))
    component_labels = [
        tuple(sorted((str(label_by_node[int(node)]) for node in nodes), key=graph_label_sort_key))
        for nodes in component_nodes
    ]
    component_labels = sorted(component_labels, key=lambda labels: graph_label_sort_key(labels[0]) if labels else (0, ""))
    target_labels = tuple(sorted((str(label_by_node[int(node)]) for node in target_nodes), key=graph_label_sort_key))
    return GraphComponentSample(
        graph=topology_sample.graph,
        directed=False,
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
        query_label=str(label_by_node[int(query_node)]),
        target_labels=tuple(str(label) for label in target_labels),
        components_by_label=tuple(tuple(str(label) for label in labels) for labels in component_labels),
        component_sizes=tuple(int(len(labels)) for labels in component_labels),
        component_count=int(component_count_int),
        target_component_size=int(target_size_int),
    )


def sample_largest_component_size_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_largest_component_size: int,
    component_count: int,
    topology_profile: str,
    label_variant: str,
) -> GraphLargestComponentSample:
    """Construct one disconnected undirected graph with a unique largest component."""

    node_count_int = int(node_count)
    target_size_int = int(target_largest_component_size)
    component_count_int = int(component_count)
    feasible_node_support = feasible_node_counts_for_unique_largest_component(
        target_largest_component_size=int(target_size_int),
        component_count=int(component_count_int),
        node_count_min=int(node_count_int),
        node_count_max=int(node_count_int),
    )
    if int(node_count_int) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested largest-component query")

    target_component_index = int(rng.randrange(int(component_count_int)))
    other_sizes = _random_bounded_positive_composition(
        rng,
        total=int(node_count_int - target_size_int),
        parts=int(component_count_int - 1),
        max_value=int(target_size_int - 1),
    )
    if other_sizes is None:
        raise ValueError("failed to sample a bounded positive component-size partition")

    component_sizes = []
    other_sizes_list = list(int(size) for size in other_sizes)
    for component_index in range(int(component_count_int)):
        if int(component_index) == int(target_component_index):
            component_sizes.append(int(target_size_int))
        else:
            component_sizes.append(int(other_sizes_list.pop()))

    topology_sample, label_by_node, component_nodes = _build_disconnected_component_graph(
        rng,
        component_sizes=tuple(int(size) for size in component_sizes),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    component_labels = [
        tuple(sorted((str(label_by_node[int(node)]) for node in nodes), key=graph_label_sort_key))
        for nodes in component_nodes
    ]
    component_labels = sorted(component_labels, key=lambda labels: graph_label_sort_key(labels[0]) if labels else (0, ""))
    target_nodes = tuple(int(node) for node in component_nodes[int(target_component_index)])
    target_labels = tuple(sorted((str(label_by_node[int(node)]) for node in target_nodes), key=graph_label_sort_key))
    return GraphLargestComponentSample(
        graph=topology_sample.graph,
        directed=False,
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
        target_labels=tuple(str(label) for label in target_labels),
        components_by_label=tuple(tuple(str(label) for label in labels) for labels in component_labels),
        component_sizes=tuple(int(len(labels)) for labels in component_labels),
        component_count=int(component_count_int),
        target_largest_component_size=int(target_size_int),
    )


def sample_unique_cycle_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_cycle_size: int,
    topology_profile: str,
    label_variant: str,
) -> GraphUniqueCycleSample:
    """Construct one connected unicyclic graph for unique-cycle-size queries."""

    feasible_node_support = feasible_node_counts_for_unique_cycle_size(
        target_cycle_size=int(target_cycle_size),
        node_count_min=int(node_count),
        node_count_max=int(node_count),
    )
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested unique-cycle query")

    graph = _sample_unicyclic_graph(
        rng,
        node_count=int(node_count),
        cycle_size=int(target_cycle_size),
        topology_profile=str(topology_profile),
    )
    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=False,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    cycle_basis = nx.cycle_basis(graph)
    if len(cycle_basis) != 1:
        raise ValueError("unique-cycle sampler failed to produce exactly one cycle")
    cycle_nodes = tuple(int(node) for node in cycle_basis[0])
    target_labels = tuple(sorted((str(label_by_node[int(node)]) for node in cycle_nodes), key=graph_label_sort_key))
    return GraphUniqueCycleSample(
        graph=topology_sample.graph,
        directed=False,
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
        target_labels=tuple(str(label) for label in target_labels),
        target_cycle_size=int(target_cycle_size),
        attachment_count=int(node_count) - int(target_cycle_size),
    )


def sample_articulation_point_count_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_count: int,
    topology_profile: str,
    label_variant: str,
    attempts: int = 200,
) -> GraphArticulationPointSample:
    """Construct one graph with the requested articulation-point count."""

    feasible_node_support = feasible_node_counts_for_articulation_point_count(
        target_count=int(target_count),
        node_count_min=int(node_count),
        node_count_max=int(node_count),
    )
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested articulation query")

    graph = _sample_articulation_graph(
        rng,
        node_count=int(node_count),
        target_count=int(target_count),
        topology_profile=str(topology_profile),
        attempts=int(attempts),
    )
    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=False,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    articulation_nodes = tuple(int(node) for node in nx.articulation_points(graph))
    target_labels = tuple(sorted((str(label_by_node[int(node)]) for node in articulation_nodes), key=graph_label_sort_key))
    return GraphArticulationPointSample(
        graph=topology_sample.graph,
        directed=False,
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
        target_labels=tuple(str(label) for label in target_labels),
        target_count=int(target_count),
    )


__all__ = [
    "GraphArticulationPointSample",
    "GraphComponentSample",
    "GraphCountSample",
    "GraphLargestComponentSample",
    "GraphTopologySample",
    "GraphUniqueCycleSample",
    "LABEL_POOL_1_12",
    "SUPPORTED_ARTICULATION_TASK_VARIANTS",
    "SUPPORTED_COMPONENT_TASK_VARIANTS",
    "SUPPORTED_COMPONENT_COMPARISON_TASK_VARIANTS",
    "SUPPORTED_CYCLE_TASK_VARIANTS",
    "SUPPORTED_DEGREE_TASK_VARIANTS",
    "SUPPORTED_LAYOUT_VARIANTS",
    "SUPPORTED_LABEL_VARIANTS",
    "SUPPORTED_TOPOLOGY_PROFILES",
    "feasible_node_counts_for_articulation_point_count",
    "feasible_node_counts_for_component_query",
    "feasible_node_counts_for_degree_count",
    "feasible_node_counts_for_unique_cycle_size",
    "feasible_node_counts_for_unique_largest_component",
    "graph_degree_mode_for_task_variant",
    "graph_directionality_for_task_variant",
    "graph_label_sort_key",
    "sample_articulation_point_count_graph",
    "sample_component_count_graph",
    "sample_degree_count_graph",
    "sample_largest_component_size_graph",
    "sample_unique_cycle_graph",
]
