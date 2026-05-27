"""Shared graph-domain sampling helpers for simple node-link scenes."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from itertools import product
from functools import lru_cache
from typing import Any, Dict, Mapping, Sequence, Tuple

import networkx as nx

from ...shared.graph_algorithms import bfs_dist_count_by_adjacency, reconstruct_unique_shortest_path_by_adjacency
from .label_assets import LABEL_POOL_1_20, SUPPORTED_GRAPH_LABEL_VARIANTS, resolve_graph_node_labels


SUPPORTED_LAYOUT_VARIANTS: Tuple[str, ...] = (
    "circular",
    "shell",
    "spring",
    "grid_jitter",
    "layered",
    "component_clustered",
    "path_spine",
    "radial_tree",
)
SUPPORTED_TOPOLOGY_PROFILES: Tuple[str, ...] = ("balanced", "low_degree", "hub_heavy")
SUPPORTED_LABEL_VARIANTS: Tuple[str, ...] = SUPPORTED_GRAPH_LABEL_VARIANTS
SUPPORTED_NODE_LINK_LABEL_VARIANTS: Tuple[str, ...] = SUPPORTED_GRAPH_LABEL_VARIANTS
SUPPORTED_DEGREE_QUERY_IDS: Tuple[str, ...] = ("degree_count", "directed_degree_count")
SUPPORTED_DIRECTED_DEGREE_MODES: Tuple[str, ...] = ("in_degree", "out_degree")
SUPPORTED_SOURCE_SINK_MODES: Tuple[str, ...] = ("source", "sink")
SUPPORTED_NODE_COLOR_COUNT_DIRECTIONS: Tuple[str, ...] = ("undirected", "directed")
SUPPORTED_EDGE_COLOR_COUNT_DIRECTIONS: Tuple[str, ...] = ("undirected", "directed")
SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS: Tuple[str, ...] = ("undirected", "directed")
SUPPORTED_CROSS_COLOR_EDGE_COUNT_DIRECTIONS: Tuple[str, ...] = ("undirected", "directed")
SUPPORTED_ISOLATED_AFTER_NODE_REMOVAL_DIRECTIONS: Tuple[str, ...] = ("undirected", "directed")
SUPPORTED_COMMON_NEIGHBOR_MODES: Tuple[str, ...] = (
    "undirected_common_neighbor",
    "directed_common_successor",
    "directed_common_predecessor",
)
SUPPORTED_UNIQUE_NODE_LABEL_RELATION_MODES: Tuple[str, ...] = (
    "undirected_unique_neighbor",
    "directed_unique_successor",
    "directed_unique_predecessor",
)
SUPPORTED_NAMED_NODE_DEGREE_DIRECTIONS: Tuple[str, ...] = ("undirected", "directed")
SUPPORTED_NAMED_NODE_DIRECTED_DEGREE_MODES: Tuple[str, ...] = (
    "in_degree",
    "out_degree",
    "total_degree",
)
SUPPORTED_EXTREME_DEGREE_DIRECTIONS: Tuple[str, ...] = ("undirected", "directed")
SUPPORTED_EXTREME_DEGREE_EXTREMA: Tuple[str, ...] = ("max", "min")
SUPPORTED_EXTREME_DEGREE_DIRECTED_MODES: Tuple[str, ...] = (
    "in_degree",
    "out_degree",
    "total_degree",
)
SUPPORTED_ARTICULATION_QUERY_IDS: Tuple[str, ...] = ("articulation_point_count",)
SUPPORTED_BRIDGE_QUERY_IDS: Tuple[str, ...] = ("bridge_count",)
SUPPORTED_OPTIMIZATION_QUERY_IDS: Tuple[str, ...] = ("minimum_spanning_tree_weight",)
SUPPORTED_COMPONENT_QUERY_IDS: Tuple[str, ...] = ("same_component_count",)
SUPPORTED_COMPONENT_EDGE_EDIT_MODES: Tuple[str, ...] = ("edge_removal", "edge_addition")
SUPPORTED_REACHABLE_QUERY_IDS: Tuple[str, ...] = ("reachable_count",)
SUPPORTED_CYCLE_QUERY_IDS: Tuple[str, ...] = ("unique_cycle_size",)
SUPPORTED_COMPONENT_COMPARISON_QUERY_IDS: Tuple[str, ...] = ("largest_component_size",)
SUPPORTED_PATH_QUERY_IDS: Tuple[str, ...] = ("shortest_path_length", "directed_shortest_path_length")
SUPPORTED_LONGEST_PATH_QUERY_IDS: Tuple[str, ...] = ("directed_longest_path_length",)
SUPPORTED_ORDER_QUERY_IDS: Tuple[str, ...] = ("topological_position",)
SUPPORTED_REACHABLE_EDGE_EDIT_MODES: Tuple[str, ...] = ("edge_removal", "edge_addition")

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
    label_source_kind: str = field(default="", kw_only=True)
    label_bucket: str = field(default="", kw_only=True)
    label_manifest: str = field(default="", kw_only=True)
    label_filter: Dict[str, Any] = field(default_factory=dict, kw_only=True)
    label_bucket_probabilities: Dict[str, float] = field(default_factory=dict, kw_only=True)


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
class GraphSourceSinkSample(GraphTopologySample):
    """Trace-ready directed graph sample for source/sink count tasks."""

    target_labels: Tuple[str, ...]
    target_count: int
    source_sink_mode: str
    degree_mode: str
    in_degree_sequence: Tuple[int, ...]
    out_degree_sequence: Tuple[int, ...]


@dataclass(frozen=True)
class GraphCommonNeighborSample(GraphTopologySample):
    """Trace-ready graph sample for common-neighbor relation count tasks."""

    query_label_a: str
    query_label_b: str
    target_labels: Tuple[str, ...]
    target_count: int
    common_neighbor_mode: str
    graph_directionality: str


@dataclass(frozen=True)
class GraphUniqueNodeLabelRelationSample(GraphTopologySample):
    """Trace-ready graph sample for unique neighbor/successor/predecessor lookup tasks."""

    query_label: str
    answer_label: str
    target_labels: Tuple[str, ...]
    relation_mode: str
    graph_directionality: str
    supporting_edge: Tuple[str, str]


@dataclass(frozen=True)
class GraphNodeColorCountSample(GraphTopologySample):
    """Trace-ready graph sample for semantic node-color counting tasks."""

    target_labels: Tuple[str, ...]
    target_count: int
    target_color_name: str
    node_color_names_by_label: Dict[str, str]
    color_counts_by_name: Dict[str, int]
    graph_directionality: str


@dataclass(frozen=True)
class GraphEdgeColorCountSample(GraphTopologySample):
    """Trace-ready graph sample for semantic edge-color counting tasks."""

    target_edges: Tuple[Tuple[str, str], ...]
    target_count: int
    target_color_name: str
    edge_color_names_by_label: Dict[Tuple[str, str], str]
    color_counts_by_name: Dict[str, int]
    graph_directionality: str


@dataclass(frozen=True)
class GraphEdgeTextLabelCountSample(GraphTopologySample):
    """Trace-ready graph sample for visible edge-text label counting tasks."""

    target_edges: Tuple[Tuple[str, str], ...]
    target_count: int
    target_edge_label: str
    edge_attribute_labels_by_label: Dict[Tuple[str, str], str]
    edge_label_counts_by_value: Dict[str, int]
    graph_directionality: str


@dataclass(frozen=True)
class GraphEdgeAttributeLabelSample(GraphTopologySample):
    """Trace-ready graph sample for visible labeled-edge lookup tasks."""

    query_edge: Tuple[str, str]
    target_edge_label: str
    edge_attribute_labels_by_label: Dict[Tuple[str, str], str]
    edge_label_counts_by_value: Dict[str, int]
    graph_directionality: str
    query_path_labels: Tuple[str, ...] = ()
    query_path_edge_index: int | None = None
    query_path_edge_position: str | None = None


@dataclass(frozen=True)
class GraphCrossColorEdgeCountSample(GraphTopologySample):
    """Trace-ready graph sample for edges connecting queried node colors."""

    target_edges: Tuple[Tuple[str, str], ...]
    target_count: int
    source_color_name: str
    target_color_name: str
    node_color_names_by_label: Dict[str, str]
    color_counts_by_name: Dict[str, int]
    graph_directionality: str


@dataclass(frozen=True)
class GraphIsolatedAfterNodeRemovalSample(GraphTopologySample):
    """Trace-ready graph sample for node-removal isolated-node counting tasks."""

    query_label: str
    removed_node_label: str
    target_labels: Tuple[str, ...]
    target_count: int
    graph_directionality: str
    pre_removal_adjacency_by_label: Dict[str, Tuple[str, ...]]
    post_removal_adjacency_by_label: Dict[str, Tuple[str, ...]]
    pre_removal_successors_by_label: Dict[str, Tuple[str, ...]]
    post_removal_successors_by_label: Dict[str, Tuple[str, ...]]
    pre_removal_predecessors_by_label: Dict[str, Tuple[str, ...]]
    post_removal_predecessors_by_label: Dict[str, Tuple[str, ...]]
    pre_removal_degrees_by_label: Dict[str, int]
    post_removal_degrees_by_label: Dict[str, int]
    pre_removal_in_degrees_by_label: Dict[str, int]
    post_removal_in_degrees_by_label: Dict[str, int]
    pre_removal_out_degrees_by_label: Dict[str, int]
    post_removal_out_degrees_by_label: Dict[str, int]
    post_removal_edge_labels: Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class GraphNamedNodeDegreeSample(GraphTopologySample):
    """Trace-ready graph sample for one queried node's degree value."""

    query_label: str
    target_edges: Tuple[Tuple[str, str], ...]
    target_degree: int
    degree_mode: str
    degree_sequence: Tuple[int, ...]
    in_degree_sequence: Tuple[int, ...]
    out_degree_sequence: Tuple[int, ...]
    total_degrees_by_label: Dict[str, int]


@dataclass(frozen=True)
class GraphExtremeDegreeSample(GraphTopologySample):
    """Trace-ready graph sample for an extreme degree-value comparison."""

    target_labels: Tuple[str, ...]
    target_degree: int
    extremum_mode: str
    degree_mode: str
    degree_sequence: Tuple[int, ...]
    in_degree_sequence: Tuple[int, ...]
    out_degree_sequence: Tuple[int, ...]
    queried_degrees_by_label: Dict[str, int]
    total_degrees_by_label: Dict[str, int]


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
class GraphComponentAfterEdgeEditSample(GraphTopologySample):
    """Trace-ready graph sample for undirected edge-edit component-size tasks."""

    query_label: str
    edit_edge: Tuple[str, str]
    edit_operation: str
    target_labels: Tuple[str, ...]
    target_component_size: int
    pre_edit_adjacency_by_label: Dict[str, Tuple[str, ...]]
    post_edit_adjacency_by_label: Dict[str, Tuple[str, ...]]
    pre_edit_components_by_label: Tuple[Tuple[str, ...], ...]
    post_edit_components_by_label: Tuple[Tuple[str, ...], ...]


@dataclass(frozen=True)
class GraphReachableSample(GraphTopologySample):
    """Trace-ready directed graph sample for reachable-count tasks."""

    query_label: str
    target_labels: Tuple[str, ...]
    target_reachable_count: int
    unreachable_labels: Tuple[str, ...]
    reachable_edge_count: int
    unreachable_edge_count: int


@dataclass(frozen=True)
class GraphReachableAfterEdgeEditSample(GraphTopologySample):
    """Trace-ready directed graph sample for post-edit reachable-count tasks."""

    query_label: str
    edit_edge: Tuple[str, str]
    edit_operation: str
    target_labels: Tuple[str, ...]
    target_reachable_count: int
    unreachable_labels: Tuple[str, ...]
    pre_edit_reachable_labels: Tuple[str, ...]
    post_edit_reachable_labels: Tuple[str, ...]
    pre_edit_successors_by_label: Dict[str, Tuple[str, ...]]
    post_edit_successors_by_label: Dict[str, Tuple[str, ...]]
    pre_edit_predecessors_by_label: Dict[str, Tuple[str, ...]]
    post_edit_predecessors_by_label: Dict[str, Tuple[str, ...]]
    pre_edit_edge_labels: Tuple[Tuple[str, str], ...]
    post_edit_edge_labels: Tuple[Tuple[str, str], ...]


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
class GraphShortestPathSample(GraphTopologySample):
    """Trace-ready graph sample for unique shortest-path tasks."""

    source_label: str
    goal_label: str
    target_labels: Tuple[str, ...]
    target_shortest_path_length: int
    attachment_count: int
    extra_edge_count: int


@dataclass(frozen=True)
class GraphLongestPathSample(GraphTopologySample):
    """Trace-ready directed DAG sample for unique longest-path tasks."""

    source_label: str
    goal_label: str
    target_labels: Tuple[str, ...]
    target_longest_path_length: int
    attachment_count: int
    extra_edge_count: int


@dataclass(frozen=True)
class GraphArticulationPointSample(GraphTopologySample):
    """Trace-ready graph sample for articulation-point counting tasks."""

    target_labels: Tuple[str, ...]
    target_count: int


@dataclass(frozen=True)
class GraphBridgeSample(GraphTopologySample):
    """Trace-ready graph sample for bridge-edge counting tasks."""

    target_edges: Tuple[Tuple[str, str], ...]
    target_count: int


@dataclass(frozen=True)
class GraphMinimumSpanningTreeSample(GraphTopologySample):
    """Trace-ready weighted graph sample for unique MST tasks."""

    edge_weights_by_label: Dict[Tuple[str, str], int]
    target_edges: Tuple[Tuple[str, str], ...]
    target_total_weight: int
    extra_edge_count: int


@dataclass(frozen=True)
class GraphTopologicalOrderSample(GraphTopologySample):
    """Trace-ready directed graph sample for unique topological-order tasks."""

    query_label: str
    target_labels: Tuple[str, ...]
    target_position: int
    extra_edge_count: int


def graph_label_sort_key(label: str) -> Tuple[int, int | str]:
    """Return one natural sort key for graph node labels."""

    text = str(label)
    if str(text).isdigit():
        return (0, int(text))
    return (1, str(text))


def canonicalize_graph_edge_label(
    left_label: str,
    right_label: str,
    *,
    directed: bool = False,
) -> Tuple[str, str]:
    """Return one canonical label pair for a graph edge."""

    left = str(left_label)
    right = str(right_label)
    if bool(directed):
        return (left, right)
    return tuple(sorted((left, right), key=graph_label_sort_key))


def sort_graph_edge_labels(
    edges: Sequence[Tuple[str, str]],
    *,
    directed: bool = False,
) -> Tuple[Tuple[str, str], ...]:
    """Return graph edge labels in deterministic canonical order."""

    canonical = [
        canonicalize_graph_edge_label(str(left), str(right), directed=bool(directed))
        for left, right in edges
    ]
    return tuple(
        sorted(
            canonical,
            key=lambda pair: (graph_label_sort_key(str(pair[0])), graph_label_sort_key(str(pair[1]))),
        )
    )


def graph_directionality_for_query_id(query_id: str) -> str:
    """Return the graph directionality implied by one query id."""

    variant = str(query_id)
    if variant in {"directed_degree_count", "directed_shortest_path_length", "topological_position"}:
        return "directed"
    return "undirected"


def graph_degree_mode_for_query_id(query_id: str, *, degree_mode: str | None = None) -> str:
    """Return the query-degree mode implied by one query id."""

    variant = str(query_id)
    if variant == "directed_degree_count":
        if degree_mode is None:
            return "in_degree"
        mode = str(degree_mode)
        if mode not in SUPPORTED_DIRECTED_DEGREE_MODES:
            raise ValueError(f"unsupported directed degree mode: {degree_mode}")
        return str(mode)
    if degree_mode is not None and str(degree_mode) != "degree":
        raise ValueError(f"unsupported undirected degree mode: {degree_mode}")
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
    resolved_labels = resolve_graph_node_labels(
        rng,
        label_variant=str(label_variant),
        object_count=int(graph.number_of_nodes()),
        max_chars=5,
        sequential_numbers=True,
    )
    labels = tuple(str(label) for label in resolved_labels.labels)
    label_by_node = {int(node): str(label) for node, label in zip(node_order, labels)}

    if bool(directed):
        labeled_edges = sort_graph_edge_labels(
            tuple(
                (str(label_by_node[int(left)]), str(label_by_node[int(right)]))
                for left, right in graph.edges()
            ),
            directed=True,
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
        labeled_edges = sort_graph_edge_labels(
            tuple(
                (str(label_by_node[int(left)]), str(label_by_node[int(right)]))
                for left, right in graph.edges()
            ),
            directed=False,
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
        label_variant=str(resolved_labels.label_variant),
        label_source_kind=str(resolved_labels.label_source_kind),
        label_bucket=str(resolved_labels.label_bucket),
        label_manifest=str(resolved_labels.label_manifest),
        label_filter=dict(resolved_labels.label_filter),
        label_bucket_probabilities=dict(resolved_labels.label_bucket_probabilities),
    )
    return topology, label_by_node


def _graph_adjacency_by_node(graph: nx.Graph) -> Dict[int, Tuple[int, ...]]:
    """Return a deterministic undirected adjacency mapping keyed by node id."""

    return {
        int(node): tuple(sorted((int(neighbor) for neighbor in graph.neighbors(int(node)))))
        for node in sorted((int(value) for value in graph.nodes()))
    }


def _digraph_successor_adjacency_by_node(graph: nx.DiGraph) -> Dict[int, Tuple[int, ...]]:
    """Return a deterministic directed successor adjacency keyed by node id."""

    return {
        int(node): tuple(sorted((int(neighbor) for neighbor in graph.successors(int(node)))))
        for node in sorted((int(value) for value in graph.nodes()))
    }


def _digraph_predecessor_adjacency_by_node(graph: nx.DiGraph) -> Dict[int, Tuple[int, ...]]:
    """Return a deterministic directed predecessor adjacency keyed by node id."""

    return {
        int(node): tuple(sorted((int(neighbor) for neighbor in graph.predecessors(int(node)))))
        for node in sorted((int(value) for value in graph.nodes()))
    }


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
    query_id: str,
    degree_mode: str | None = None,
    query_degree: int,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
    max_degree: int,
    topology_profile: str = "balanced",
) -> Tuple[int, ...]:
    """Return node counts that can realize the requested degree-count query."""

    support = []
    degree_mode = graph_degree_mode_for_query_id(str(query_id), degree_mode=degree_mode)
    for node_count in range(int(node_count_min), int(node_count_max) + 1):
        feasibility_rng = random.Random(
            f"graph-degree-feasibility:{str(query_id)}:{int(node_count)}:{int(query_degree)}:{int(target_count)}:{int(max_degree)}"
        )
        if str(graph_directionality_for_query_id(str(query_id))) == "directed":
            result = _find_directed_graph_with_degree_count(
                feasibility_rng,
                node_count=int(node_count),
                query_degree=int(query_degree),
                target_count=int(target_count),
                max_degree=int(max_degree),
                topology_profile=str(topology_profile),
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
                topology_profile=str(topology_profile),
                search_attempts=600,
            )
        if result is not None:
            support.append(int(node_count))
    return tuple(int(value) for value in support)


def sample_degree_count_graph(
    rng: random.Random,
    *,
    query_id: str,
    degree_mode: str | None = None,
    node_count: int,
    query_degree: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    label_variant: str,
    search_attempts: int,
) -> GraphCountSample:
    """Construct one labeled graph with the requested degree-count support."""

    query_id_text = str(query_id)
    directionality = str(graph_directionality_for_query_id(query_id_text))
    degree_mode = str(graph_degree_mode_for_query_id(query_id_text, degree_mode=degree_mode))
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


def _common_neighbor_nodes(
    graph: nx.Graph | nx.DiGraph,
    *,
    query_a: int,
    query_b: int,
    common_neighbor_mode: str,
) -> Tuple[int, ...]:
    """Return node ids matching one common-neighbor style query."""

    mode = str(common_neighbor_mode)
    query_a_int = int(query_a)
    query_b_int = int(query_b)
    if mode == "undirected_common_neighbor":
        left = set(int(node) for node in graph.neighbors(int(query_a_int)))
        right = set(int(node) for node in graph.neighbors(int(query_b_int)))
    elif mode == "directed_common_successor":
        if not isinstance(graph, nx.DiGraph):
            return ()
        left = set(int(node) for node in graph.successors(int(query_a_int)))
        right = set(int(node) for node in graph.successors(int(query_b_int)))
    elif mode == "directed_common_predecessor":
        if not isinstance(graph, nx.DiGraph):
            return ()
        left = set(int(node) for node in graph.predecessors(int(query_a_int)))
        right = set(int(node) for node in graph.predecessors(int(query_b_int)))
    else:
        raise ValueError(f"unsupported common-neighbor mode: {common_neighbor_mode}")
    return tuple(
        sorted(
            int(node)
            for node in (left & right)
            if int(node) not in {int(query_a_int), int(query_b_int)}
        )
    )


def _try_add_common_neighbor_undirected_edge(
    graph: nx.Graph,
    *,
    left: int,
    right: int,
    query_a: int,
    query_b: int,
    target_nodes: set[int],
    max_degree: int,
) -> bool:
    """Add one undirected edge if it preserves exact common-neighbor support."""

    left_int = int(left)
    right_int = int(right)
    if int(left_int) == int(right_int) or graph.has_edge(int(left_int), int(right_int)):
        return False
    if int(graph.degree(int(left_int))) >= int(max_degree) or int(graph.degree(int(right_int))) >= int(max_degree):
        return False
    graph.add_edge(int(left_int), int(right_int))
    observed = set(
        _common_neighbor_nodes(
            graph,
            query_a=int(query_a),
            query_b=int(query_b),
            common_neighbor_mode="undirected_common_neighbor",
        )
    )
    if observed != {int(node) for node in target_nodes}:
        graph.remove_edge(int(left_int), int(right_int))
        return False
    return True


def _try_sample_common_neighbor_undirected_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
) -> nx.Graph | None:
    """Construct one undirected graph with an exact common-neighbor count."""

    node_count_int = int(node_count)
    target_count_int = int(target_count)
    max_degree_int = max(1, int(max_degree))
    if (
        int(node_count_int) < 3
        or int(target_count_int) < 0
        or int(target_count_int) > int(node_count_int) - 2
        or int(target_count_int) > int(max_degree_int)
    ):
        return None

    graph = nx.Graph()
    graph.add_nodes_from(range(int(node_count_int)))
    nodes = [int(node) for node in range(int(node_count_int))]
    query_a, query_b = rng.sample(nodes, 2)
    remaining_nodes = [int(node) for node in nodes if int(node) not in {int(query_a), int(query_b)}]
    target_nodes = set(rng.sample(remaining_nodes, int(target_count_int))) if int(target_count_int) else set()
    distractor_nodes = [int(node) for node in remaining_nodes if int(node) not in target_nodes]

    for target in sorted(target_nodes):
        graph.add_edge(int(query_a), int(target))
        graph.add_edge(int(query_b), int(target))

    shuffled_distractors = list(distractor_nodes)
    rng.shuffle(shuffled_distractors)
    for distractor in shuffled_distractors:
        if rng.random() < 0.70:
            query = int(query_a) if rng.random() < 0.5 else int(query_b)
            _try_add_common_neighbor_undirected_edge(
                graph,
                left=int(query),
                right=int(distractor),
                query_a=int(query_a),
                query_b=int(query_b),
                target_nodes=set(target_nodes),
                max_degree=int(max_degree_int),
            )

    if rng.random() < 0.35:
        _try_add_common_neighbor_undirected_edge(
            graph,
            left=int(query_a),
            right=int(query_b),
            query_a=int(query_a),
            query_b=int(query_b),
            target_nodes=set(target_nodes),
            max_degree=int(max_degree_int),
        )

    candidates = [
        (int(nodes[left_index]), int(nodes[right_index]))
        for left_index in range(len(nodes))
        for right_index in range(left_index + 1, len(nodes))
    ]
    rng.shuffle(candidates)
    added_extra = 0
    extra_edges = _profile_extra_edge_budget(
        node_count=int(node_count_int),
        topology_profile=str(topology_profile),
        directed=False,
    )
    for left, right in candidates:
        if int(added_extra) >= int(extra_edges):
            break
        if _try_add_common_neighbor_undirected_edge(
            graph,
            left=int(left),
            right=int(right),
            query_a=int(query_a),
            query_b=int(query_b),
            target_nodes=set(target_nodes),
            max_degree=int(max_degree_int),
        ):
            added_extra += 1

    observed = _common_neighbor_nodes(
        graph,
        query_a=int(query_a),
        query_b=int(query_b),
        common_neighbor_mode="undirected_common_neighbor",
    )
    if set(observed) != {int(node) for node in target_nodes}:
        return None
    graph.graph["common_neighbor_query_nodes"] = (int(query_a), int(query_b))
    graph.graph["common_neighbor_target_nodes"] = tuple(sorted(int(node) for node in target_nodes))
    return graph


def _try_add_common_neighbor_directed_edge(
    graph: nx.DiGraph,
    *,
    source: int,
    target: int,
    query_a: int,
    query_b: int,
    target_nodes: set[int],
    common_neighbor_mode: str,
    max_degree: int,
) -> bool:
    """Add one directed edge if it preserves exact common successor/predecessor support."""

    source_int = int(source)
    target_int = int(target)
    mode = str(common_neighbor_mode)
    if not _add_directed_edge_without_reciprocal(
        graph,
        source=int(source_int),
        target=int(target_int),
        max_degree=int(max_degree),
    ):
        return False
    observed = set(
        _common_neighbor_nodes(
            graph,
            query_a=int(query_a),
            query_b=int(query_b),
            common_neighbor_mode=str(mode),
        )
    )
    if observed != {int(node) for node in target_nodes}:
        graph.remove_edge(int(source_int), int(target_int))
        return False
    return True


def _try_sample_common_neighbor_directed_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    common_neighbor_mode: str,
) -> nx.DiGraph | None:
    """Construct one directed graph with an exact common successor/predecessor count."""

    mode = str(common_neighbor_mode)
    if mode not in {"directed_common_successor", "directed_common_predecessor"}:
        raise ValueError(f"unsupported directed common-neighbor mode: {common_neighbor_mode}")
    node_count_int = int(node_count)
    target_count_int = int(target_count)
    max_degree_int = max(1, int(max_degree))
    if (
        int(node_count_int) < 3
        or int(target_count_int) < 0
        or int(target_count_int) > int(node_count_int) - 2
        or int(target_count_int) > int(max_degree_int)
    ):
        return None

    graph = nx.DiGraph()
    graph.add_nodes_from(range(int(node_count_int)))
    nodes = [int(node) for node in range(int(node_count_int))]
    query_a, query_b = rng.sample(nodes, 2)
    remaining_nodes = [int(node) for node in nodes if int(node) not in {int(query_a), int(query_b)}]
    target_nodes = set(rng.sample(remaining_nodes, int(target_count_int))) if int(target_count_int) else set()
    distractor_nodes = [int(node) for node in remaining_nodes if int(node) not in target_nodes]

    for target_node in sorted(target_nodes):
        if mode == "directed_common_successor":
            if not _add_directed_edge_without_reciprocal(
                graph,
                source=int(query_a),
                target=int(target_node),
                max_degree=int(max_degree_int),
            ):
                return None
            if not _add_directed_edge_without_reciprocal(
                graph,
                source=int(query_b),
                target=int(target_node),
                max_degree=int(max_degree_int),
            ):
                return None
        else:
            if not _add_directed_edge_without_reciprocal(
                graph,
                source=int(target_node),
                target=int(query_a),
                max_degree=int(max_degree_int),
            ):
                return None
            if not _add_directed_edge_without_reciprocal(
                graph,
                source=int(target_node),
                target=int(query_b),
                max_degree=int(max_degree_int),
            ):
                return None

    shuffled_distractors = list(distractor_nodes)
    rng.shuffle(shuffled_distractors)
    for distractor in shuffled_distractors:
        if rng.random() >= 0.70:
            continue
        query = int(query_a) if rng.random() < 0.5 else int(query_b)
        if mode == "directed_common_successor":
            _try_add_common_neighbor_directed_edge(
                graph,
                source=int(query),
                target=int(distractor),
                query_a=int(query_a),
                query_b=int(query_b),
                target_nodes=set(target_nodes),
                common_neighbor_mode=str(mode),
                max_degree=int(max_degree_int),
            )
        else:
            _try_add_common_neighbor_directed_edge(
                graph,
                source=int(distractor),
                target=int(query),
                query_a=int(query_a),
                query_b=int(query_b),
                target_nodes=set(target_nodes),
                common_neighbor_mode=str(mode),
                max_degree=int(max_degree_int),
            )

    candidates = [
        (int(source), int(target))
        for source in nodes
        for target in nodes
        if int(source) != int(target)
    ]
    rng.shuffle(candidates)
    added_extra = 0
    extra_edges = _profile_extra_edge_budget(
        node_count=int(node_count_int),
        topology_profile=str(topology_profile),
        directed=True,
    )
    for source, target in candidates:
        if int(added_extra) >= int(extra_edges):
            break
        if _try_add_common_neighbor_directed_edge(
            graph,
            source=int(source),
            target=int(target),
            query_a=int(query_a),
            query_b=int(query_b),
            target_nodes=set(target_nodes),
            common_neighbor_mode=str(mode),
            max_degree=int(max_degree_int),
        ):
            added_extra += 1

    if _has_reciprocal_edges(graph):
        return None
    observed = _common_neighbor_nodes(
        graph,
        query_a=int(query_a),
        query_b=int(query_b),
        common_neighbor_mode=str(mode),
    )
    if set(observed) != {int(node) for node in target_nodes}:
        return None
    graph.graph["common_neighbor_query_nodes"] = (int(query_a), int(query_b))
    graph.graph["common_neighbor_target_nodes"] = tuple(sorted(int(node) for node in target_nodes))
    return graph


@lru_cache(maxsize=128)
def feasible_node_counts_for_common_neighbor_count(
    *,
    common_neighbor_mode: str,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
    max_degree: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize the requested common-neighbor count."""

    if str(common_neighbor_mode) not in SUPPORTED_COMMON_NEIGHBOR_MODES:
        return ()
    if int(max_degree) < 1 or int(target_count) < 0:
        return ()
    return tuple(
        int(node_count)
        for node_count in range(int(node_count_min), int(node_count_max) + 1)
        if int(node_count) >= 3
        and int(target_count) <= int(node_count) - 2
        and int(target_count) <= int(max_degree)
    )


def sample_common_neighbor_count_graph(
    rng: random.Random,
    *,
    common_neighbor_mode: str,
    node_count: int,
    target_count: int,
    max_degree: int,
    topology_profile: str,
    label_variant: str,
    search_attempts: int = 100,
) -> GraphCommonNeighborSample:
    """Construct one labeled graph with the requested common-neighbor support."""

    mode = str(common_neighbor_mode)
    if mode not in SUPPORTED_COMMON_NEIGHBOR_MODES:
        raise ValueError(f"unsupported common-neighbor mode: {common_neighbor_mode}")
    graph: nx.Graph | nx.DiGraph | None = None
    for _ in range(max(1, int(search_attempts))):
        if mode == "undirected_common_neighbor":
            graph = _try_sample_common_neighbor_undirected_graph(
                rng,
                node_count=int(node_count),
                target_count=int(target_count),
                max_degree=int(max_degree),
                topology_profile=str(topology_profile),
            )
        else:
            graph = _try_sample_common_neighbor_directed_graph(
                rng,
                node_count=int(node_count),
                target_count=int(target_count),
                max_degree=int(max_degree),
                topology_profile=str(topology_profile),
                common_neighbor_mode=str(mode),
            )
        if graph is not None:
            break
    if graph is None:
        raise ValueError("failed to sample a graph for the requested common-neighbor count")

    directed = mode != "undirected_common_neighbor"
    query_nodes = tuple(int(node) for node in graph.graph.get("common_neighbor_query_nodes", ()))
    target_nodes = tuple(int(node) for node in graph.graph.get("common_neighbor_target_nodes", ()))
    if not query_nodes or len(query_nodes) != 2:
        common_targets = _common_neighbor_nodes(
            graph,
            query_a=0,
            query_b=1,
            common_neighbor_mode=str(mode),
        )
        # The sampler always stores query nodes, but keep this branch as a
        # defensive fallback for graph objects without normalized metadata.
        query_nodes = (0, 1)
        target_nodes = tuple(common_targets)

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directed),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    query_a, query_b = int(query_nodes[0]), int(query_nodes[1])
    observed_target_nodes = _common_neighbor_nodes(
        graph,
        query_a=int(query_a),
        query_b=int(query_b),
        common_neighbor_mode=str(mode),
    )
    if target_nodes and set(int(node) for node in observed_target_nodes) != set(int(node) for node in target_nodes):
        raise ValueError("common-neighbor sampler produced inconsistent target metadata")
    target_labels = tuple(
        sorted(
            (str(label_by_node[int(node)]) for node in observed_target_nodes),
            key=graph_label_sort_key,
        )
    )
    graph_directionality = "directed" if bool(directed) else "undirected"
    return GraphCommonNeighborSample(
        graph=topology_sample.graph,
        directed=bool(directed),
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
        query_label_a=str(label_by_node[int(query_a)]),
        query_label_b=str(label_by_node[int(query_b)]),
        target_labels=tuple(str(label) for label in target_labels),
        target_count=int(len(target_labels)),
        common_neighbor_mode=str(mode),
        graph_directionality=str(graph_directionality),
    )


def _profile_extra_edge_budget(
    *,
    node_count: int,
    topology_profile: str,
    directed: bool,
) -> int:
    """Return a small distractor-edge budget for one topology profile."""

    node_count_int = int(node_count)
    profile = str(topology_profile)
    multiplier = {
        "low_degree": 0.45,
        "hub_heavy": 1.15,
    }.get(profile, 0.75)
    directed_factor = 1.35 if bool(directed) else 1.0
    return max(0, int(round(float(max(0, node_count_int - 2)) * multiplier * directed_factor)))


def _add_random_undirected_distractor_edges(
    graph: nx.Graph,
    rng: random.Random,
    *,
    nodes: Sequence[int],
    extra_edges: int,
    max_degree: int,
) -> None:
    """Add random non-target undirected edges while respecting max degree."""

    node_list = [int(node) for node in nodes]
    candidates = [
        (int(node_list[left_index]), int(node_list[right_index]))
        for left_index in range(len(node_list))
        for right_index in range(left_index + 1, len(node_list))
    ]
    rng.shuffle(candidates)
    added = 0
    for left, right in candidates:
        if int(added) >= int(extra_edges):
            break
        if graph.has_edge(int(left), int(right)):
            continue
        if int(graph.degree(int(left))) >= int(max_degree) or int(graph.degree(int(right))) >= int(max_degree):
            continue
        graph.add_edge(int(left), int(right))
        added += 1


def _add_directed_edge_without_reciprocal(
    graph: nx.DiGraph,
    *,
    source: int,
    target: int,
    max_degree: int,
) -> bool:
    """Add one directed edge when it preserves simple no-reciprocal support."""

    source_int = int(source)
    target_int = int(target)
    if int(source_int) == int(target_int):
        return False
    if graph.has_edge(int(source_int), int(target_int)) or graph.has_edge(int(target_int), int(source_int)):
        return False
    if int(graph.out_degree(int(source_int))) >= int(max_degree):
        return False
    if int(graph.in_degree(int(target_int))) >= int(max_degree):
        return False
    graph.add_edge(int(source_int), int(target_int))
    return True


def _add_random_directed_distractor_edges(
    graph: nx.DiGraph,
    rng: random.Random,
    *,
    nodes: Sequence[int],
    extra_edges: int,
    max_degree: int,
) -> None:
    """Add random non-target directed edges while avoiding reciprocal pairs."""

    node_list = [int(node) for node in nodes]
    candidates = [
        (int(left), int(right))
        for left in node_list
        for right in node_list
        if int(left) != int(right)
    ]
    rng.shuffle(candidates)
    added = 0
    for source, target in candidates:
        if int(added) >= int(extra_edges):
            break
        if _add_directed_edge_without_reciprocal(
            graph,
            source=int(source),
            target=int(target),
            max_degree=int(max_degree),
        ):
            added += 1


def _sample_unique_node_label_undirected_graph(
    rng: random.Random,
    *,
    node_count: int,
    max_degree: int,
    topology_profile: str,
) -> Tuple[nx.Graph, int, int]:
    """Construct an undirected graph where one query node has one neighbor."""

    node_count_int = int(node_count)
    if int(node_count_int) < 3:
        raise ValueError("unique-neighbor lookup requires at least three nodes")
    max_degree_int = max(1, int(max_degree))

    nodes = list(range(int(node_count_int)))
    query_node = int(rng.choice(nodes))
    answer_node = int(rng.choice([node for node in nodes if int(node) != int(query_node)]))
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_edge(int(query_node), int(answer_node))

    non_query_nodes = [int(node) for node in nodes if int(node) != int(query_node)]
    shuffled = list(non_query_nodes)
    rng.shuffle(shuffled)
    for left, right in zip(shuffled, shuffled[1:]):
        if int(graph.degree(int(left))) < int(max_degree_int) and int(graph.degree(int(right))) < int(max_degree_int):
            graph.add_edge(int(left), int(right))

    _add_random_undirected_distractor_edges(
        graph,
        rng,
        nodes=tuple(non_query_nodes),
        extra_edges=int(
            _profile_extra_edge_budget(
                node_count=int(node_count_int),
                topology_profile=str(topology_profile),
                directed=False,
            )
        ),
        max_degree=int(max_degree_int),
    )
    if int(graph.degree(int(query_node))) != 1:
        raise ValueError("unique-neighbor sampler failed to preserve one query neighbor")
    return graph, int(query_node), int(answer_node)


def _sample_unique_node_label_directed_graph(
    rng: random.Random,
    *,
    relation_mode: str,
    node_count: int,
    max_degree: int,
    topology_profile: str,
) -> Tuple[nx.DiGraph, int, int]:
    """Construct a directed graph with one successor or predecessor for the query node."""

    mode = str(relation_mode)
    if mode not in {"directed_unique_successor", "directed_unique_predecessor"}:
        raise ValueError(f"unsupported directed unique-node relation mode: {relation_mode}")
    node_count_int = int(node_count)
    if int(node_count_int) < 3:
        raise ValueError("unique directed-node lookup requires at least three nodes")
    max_degree_int = max(1, int(max_degree))

    nodes = list(range(int(node_count_int)))
    query_node = int(rng.choice(nodes))
    answer_node = int(rng.choice([node for node in nodes if int(node) != int(query_node)]))
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    if str(mode) == "directed_unique_successor":
        graph.add_edge(int(query_node), int(answer_node))
    else:
        graph.add_edge(int(answer_node), int(query_node))

    non_query_nodes = [int(node) for node in nodes if int(node) != int(query_node)]
    shuffled = list(non_query_nodes)
    rng.shuffle(shuffled)
    for left, right in zip(shuffled, shuffled[1:]):
        if rng.random() < 0.5:
            source, target = int(left), int(right)
        else:
            source, target = int(right), int(left)
        _add_directed_edge_without_reciprocal(
            graph,
            source=int(source),
            target=int(target),
            max_degree=int(max_degree_int),
        )

    candidates = [
        (int(left), int(right))
        for left in nodes
        for right in nodes
        if int(left) != int(right)
    ]
    rng.shuffle(candidates)
    extra_edges = int(
        _profile_extra_edge_budget(
            node_count=int(node_count_int),
            topology_profile=str(topology_profile),
            directed=True,
        )
    )
    added = 0
    for source, target in candidates:
        if int(added) >= int(extra_edges):
            break
        if str(mode) == "directed_unique_successor" and int(source) == int(query_node):
            continue
        if str(mode) == "directed_unique_predecessor" and int(target) == int(query_node):
            continue
        if _add_directed_edge_without_reciprocal(
            graph,
            source=int(source),
            target=int(target),
            max_degree=int(max_degree_int),
        ):
            added += 1

    if _has_reciprocal_edges(graph):
        raise ValueError("unique directed-node sampler produced reciprocal edges")
    if str(mode) == "directed_unique_successor":
        observed = tuple(int(node) for node in graph.successors(int(query_node)))
        if observed != (int(answer_node),):
            raise ValueError("unique-successor sampler failed to preserve one query successor")
    else:
        observed = tuple(int(node) for node in graph.predecessors(int(query_node)))
        if observed != (int(answer_node),):
            raise ValueError("unique-predecessor sampler failed to preserve one query predecessor")
    return graph, int(query_node), int(answer_node)


def sample_unique_node_label_relation_graph(
    rng: random.Random,
    *,
    relation_mode: str,
    node_count: int,
    max_degree: int,
    topology_profile: str,
    label_variant: str,
) -> GraphUniqueNodeLabelRelationSample:
    """Construct one graph for a unique neighbor/successor/predecessor label query."""

    mode = str(relation_mode)
    if mode not in SUPPORTED_UNIQUE_NODE_LABEL_RELATION_MODES:
        raise ValueError(f"unsupported unique-node relation mode: {relation_mode}")
    if str(mode) == "undirected_unique_neighbor":
        graph, query_node, answer_node = _sample_unique_node_label_undirected_graph(
            rng,
            node_count=int(node_count),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
        )
        directed = False
    else:
        graph, query_node, answer_node = _sample_unique_node_label_directed_graph(
            rng,
            relation_mode=str(mode),
            node_count=int(node_count),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
        )
        directed = True

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directed),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    query_label = str(label_by_node[int(query_node)])
    answer_label = str(label_by_node[int(answer_node)])
    if str(mode) == "directed_unique_predecessor":
        supporting_edge = canonicalize_graph_edge_label(str(answer_label), str(query_label), directed=True)
    else:
        supporting_edge = canonicalize_graph_edge_label(str(query_label), str(answer_label), directed=bool(directed))

    if str(mode) == "undirected_unique_neighbor":
        target_labels = tuple(str(label) for label in topology_sample.adjacency_by_label[str(query_label)])
    elif str(mode) == "directed_unique_successor":
        target_labels = tuple(str(label) for label in topology_sample.successors_by_label[str(query_label)])
    else:
        target_labels = tuple(str(label) for label in topology_sample.predecessors_by_label[str(query_label)])
    if tuple(target_labels) != (str(answer_label),):
        raise ValueError("unique-node relation target labels are inconsistent with topology metadata")

    return GraphUniqueNodeLabelRelationSample(
        graph=topology_sample.graph,
        directed=bool(directed),
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
        label_source_kind=str(topology_sample.label_source_kind),
        label_bucket=str(topology_sample.label_bucket),
        label_manifest=str(topology_sample.label_manifest),
        label_filter=dict(topology_sample.label_filter),
        label_bucket_probabilities=dict(topology_sample.label_bucket_probabilities),
        query_label=str(query_label),
        answer_label=str(answer_label),
        target_labels=(str(answer_label),),
        relation_mode=str(mode),
        graph_directionality="directed" if bool(directed) else "undirected",
        supporting_edge=(str(supporting_edge[0]), str(supporting_edge[1])),
    )


def _sample_node_color_count_base_graph(
    rng: random.Random,
    *,
    node_count: int,
    graph_directionality: str,
    topology_profile: str,
    max_degree: int,
) -> nx.Graph | nx.DiGraph:
    """Sample one simple node-link graph for semantic color-count queries."""

    base_graph = _sample_profile_tree_graph(
        rng,
        node_count=int(node_count),
        topology_profile=str(topology_profile),
    )
    extra_edges = _profile_extra_edge_budget(
        node_count=int(node_count),
        topology_profile=str(topology_profile),
        directed=bool(str(graph_directionality) == "directed"),
    )
    if str(graph_directionality) == "directed":
        graph = nx.DiGraph()
        graph.add_nodes_from(int(node) for node in base_graph.nodes())
        for left, right in base_graph.edges():
            if rng.random() < 0.5:
                graph.add_edge(int(left), int(right))
            else:
                graph.add_edge(int(right), int(left))
        _add_random_directed_distractor_edges(
            graph,
            rng,
            nodes=tuple(int(node) for node in graph.nodes()),
            extra_edges=int(extra_edges),
            max_degree=max(1, int(max_degree)),
        )
        if _has_reciprocal_edges(graph):
            raise ValueError("node-color directed sampler produced reciprocal edges")
        return graph

    graph = base_graph.copy()
    _add_random_undirected_distractor_edges(
        graph,
        rng,
        nodes=tuple(int(node) for node in graph.nodes()),
        extra_edges=int(extra_edges),
        max_degree=max(1, int(max_degree)),
    )
    return graph


def sample_node_color_count_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    node_count: int,
    target_count: int,
    target_color_name: str,
    color_support: Sequence[str],
    topology_profile: str,
    label_variant: str,
    max_degree: int,
) -> GraphNodeColorCountSample:
    """Construct one labeled graph with exactly ``target_count`` nodes in one color."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_NODE_COLOR_COUNT_DIRECTIONS:
        raise ValueError(f"unsupported graph_directionality: {graph_directionality}")
    node_count_int = int(node_count)
    target_count_int = int(target_count)
    if int(target_count_int) < 0 or int(target_count_int) > int(node_count_int):
        raise ValueError("target_count must be between zero and node_count")

    colors = tuple(str(color).strip().lower() for color in color_support if str(color).strip())
    if len(set(colors)) != len(colors) or len(colors) < 2:
        raise ValueError("color_support must contain at least two unique color names")
    target_color = str(target_color_name).strip().lower()
    if target_color not in set(colors):
        raise ValueError("target_color_name is outside color_support")
    non_target_colors = tuple(str(color) for color in colors if str(color) != str(target_color))
    if int(target_count_int) < int(node_count_int) and not non_target_colors:
        raise ValueError("non-target nodes require at least one non-target color")

    graph = _sample_node_color_count_base_graph(
        rng,
        node_count=int(node_count_int),
        graph_directionality=str(directionality),
        topology_profile=str(topology_profile),
        max_degree=int(max_degree),
    )
    topology_sample, _label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directionality == "directed"),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    labels = tuple(str(label) for label in topology_sample.node_labels)
    target_label_set = set(str(label) for label in rng.sample(labels, int(target_count_int)))
    node_color_names_by_label: Dict[str, str] = {}
    for label in labels:
        if str(label) in target_label_set:
            node_color_names_by_label[str(label)] = str(target_color)
        else:
            node_color_names_by_label[str(label)] = str(rng.choice(non_target_colors))
    color_counts_by_name = {
        str(color): sum(1 for label in labels if str(node_color_names_by_label[str(label)]) == str(color))
        for color in colors
    }
    target_labels = tuple(sorted((str(label) for label in target_label_set), key=graph_label_sort_key))
    if int(color_counts_by_name[str(target_color)]) != int(target_count_int):
        raise ValueError("node-color sampler produced inconsistent target metadata")

    return GraphNodeColorCountSample(
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
        target_labels=tuple(str(label) for label in target_labels),
        target_count=int(target_count_int),
        target_color_name=str(target_color),
        node_color_names_by_label={str(key): str(value) for key, value in node_color_names_by_label.items()},
        color_counts_by_name={str(key): int(value) for key, value in color_counts_by_name.items()},
        graph_directionality=str(directionality),
    )


def _sample_edge_color_count_base_graph(
    rng: random.Random,
    *,
    node_count: int,
    graph_directionality: str,
    topology_profile: str,
    max_degree: int,
) -> nx.Graph | nx.DiGraph:
    """Sample one simple node-link graph for semantic edge-color queries."""

    return _sample_node_color_count_base_graph(
        rng,
        node_count=int(node_count),
        graph_directionality=str(graph_directionality),
        topology_profile=str(topology_profile),
        max_degree=int(max_degree),
    )


def sample_edge_color_count_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    node_count: int,
    target_count: int,
    target_color_name: str,
    color_support: Sequence[str],
    topology_profile: str,
    label_variant: str,
    max_degree: int,
) -> GraphEdgeColorCountSample:
    """Construct one labeled graph with exactly ``target_count`` edges in one color."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_EDGE_COLOR_COUNT_DIRECTIONS:
        raise ValueError(f"unsupported graph_directionality: {graph_directionality}")
    node_count_int = int(node_count)
    target_count_int = int(target_count)
    if int(target_count_int) < 0:
        raise ValueError("target_count cannot be negative")

    colors = tuple(str(color).strip().lower() for color in color_support if str(color).strip())
    if len(set(colors)) != len(colors) or len(colors) < 2:
        raise ValueError("color_support must contain at least two unique color names")
    target_color = str(target_color_name).strip().lower()
    if target_color not in set(colors):
        raise ValueError("target_color_name is outside color_support")
    non_target_colors = tuple(str(color) for color in colors if str(color) != str(target_color))

    graph = _sample_edge_color_count_base_graph(
        rng,
        node_count=int(node_count_int),
        graph_directionality=str(directionality),
        topology_profile=str(topology_profile),
        max_degree=int(max_degree),
    )
    topology_sample, _label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directionality == "directed"),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    edge_labels = tuple((str(left), str(right)) for left, right in topology_sample.edge_labels)
    if int(target_count_int) > len(edge_labels):
        raise ValueError("target_count must be no larger than the sampled edge count")
    if int(target_count_int) < len(edge_labels) and not non_target_colors:
        raise ValueError("non-target edges require at least one non-target color")

    target_edge_set = set(tuple(edge) for edge in rng.sample(edge_labels, int(target_count_int)))
    edge_color_names_by_label: Dict[Tuple[str, str], str] = {}
    for edge in edge_labels:
        canonical_edge = (str(edge[0]), str(edge[1]))
        if canonical_edge in target_edge_set:
            edge_color_names_by_label[canonical_edge] = str(target_color)
        else:
            edge_color_names_by_label[canonical_edge] = str(rng.choice(non_target_colors))
    color_counts_by_name = {
        str(color): sum(1 for edge in edge_labels if str(edge_color_names_by_label[(str(edge[0]), str(edge[1]))]) == str(color))
        for color in colors
    }
    target_edges = sort_graph_edge_labels(
        tuple((str(left), str(right)) for left, right in target_edge_set),
        directed=bool(directionality == "directed"),
    )
    if int(color_counts_by_name[str(target_color)]) != int(target_count_int):
        raise ValueError("edge-color sampler produced inconsistent target metadata")

    return GraphEdgeColorCountSample(
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
        target_edges=tuple((str(left), str(right)) for left, right in target_edges),
        target_count=int(target_count_int),
        target_color_name=str(target_color),
        edge_color_names_by_label={
            (str(left), str(right)): str(color_name)
            for (left, right), color_name in edge_color_names_by_label.items()
        },
        color_counts_by_name={str(key): int(value) for key, value in color_counts_by_name.items()},
        graph_directionality=str(directionality),
    )


def sample_edge_text_label_count_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    node_count: int,
    target_count: int,
    target_edge_label: str,
    edge_label_support: Sequence[str],
    topology_profile: str,
    label_variant: str,
    max_degree: int,
) -> GraphEdgeTextLabelCountSample:
    """Construct one labeled graph with exactly ``target_count`` visible edge-text labels."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS:
        raise ValueError(f"unsupported graph_directionality: {graph_directionality}")
    node_count_int = int(node_count)
    target_count_int = int(target_count)
    if int(target_count_int) < 0:
        raise ValueError("target_count cannot be negative")

    edge_labels_supported = tuple(str(label).strip().lower() for label in edge_label_support if str(label).strip())
    if len(set(edge_labels_supported)) != len(edge_labels_supported) or len(edge_labels_supported) < 2:
        raise ValueError("edge_label_support must contain at least two unique labels")
    target_label = str(target_edge_label).strip().lower()
    if str(target_label) not in set(edge_labels_supported):
        raise ValueError("target_edge_label is outside edge_label_support")
    non_target_labels = tuple(str(label) for label in edge_labels_supported if str(label) != str(target_label))
    if not non_target_labels:
        raise ValueError("edge_label_support must include a non-target label")

    graph = _sample_edge_color_count_base_graph(
        rng,
        node_count=int(node_count_int),
        graph_directionality=str(directionality),
        topology_profile=str(topology_profile),
        max_degree=int(max_degree),
    )
    topology_sample, _label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directionality == "directed"),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    edge_labels = tuple((str(left), str(right)) for left, right in topology_sample.edge_labels)
    if int(target_count_int) > len(edge_labels):
        raise ValueError("target_count must be no larger than the sampled edge count")

    target_edge_set = set(tuple(edge) for edge in rng.sample(edge_labels, int(target_count_int)))
    edge_attribute_labels_by_label: Dict[Tuple[str, str], str] = {}
    for edge in edge_labels:
        canonical_edge = (str(edge[0]), str(edge[1]))
        if canonical_edge in target_edge_set:
            edge_attribute_labels_by_label[canonical_edge] = str(target_label)
        else:
            edge_attribute_labels_by_label[canonical_edge] = str(rng.choice(non_target_labels))
    edge_label_counts_by_value = {
        str(label): sum(
            1
            for edge in edge_labels
            if str(edge_attribute_labels_by_label[(str(edge[0]), str(edge[1]))]) == str(label)
        )
        for label in edge_labels_supported
    }
    target_edges = sort_graph_edge_labels(
        tuple((str(left), str(right)) for left, right in target_edge_set),
        directed=bool(directionality == "directed"),
    )
    if int(edge_label_counts_by_value[str(target_label)]) != int(target_count_int):
        raise ValueError("edge-text-label sampler produced inconsistent target metadata")

    return GraphEdgeTextLabelCountSample(
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
        label_source_kind=str(topology_sample.label_source_kind),
        label_bucket=str(topology_sample.label_bucket),
        label_manifest=str(topology_sample.label_manifest),
        label_filter=dict(topology_sample.label_filter),
        label_bucket_probabilities=dict(topology_sample.label_bucket_probabilities),
        target_edges=tuple((str(left), str(right)) for left, right in target_edges),
        target_count=int(target_count_int),
        target_edge_label=str(target_label),
        edge_attribute_labels_by_label={
            (str(left), str(right)): str(label)
            for (left, right), label in edge_attribute_labels_by_label.items()
        },
        edge_label_counts_by_value={str(key): int(value) for key, value in edge_label_counts_by_value.items()},
        graph_directionality=str(directionality),
    )


def sample_edge_attribute_label_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    node_count: int,
    target_edge_label: str,
    edge_label_support: Sequence[str],
    topology_profile: str,
    label_variant: str,
    max_degree: int,
) -> GraphEdgeAttributeLabelSample:
    """Construct one labeled graph with visible text labels on every edge."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS:
        raise ValueError(f"unsupported graph_directionality: {graph_directionality}")
    node_count_int = int(node_count)
    if int(node_count_int) < 2:
        raise ValueError("edge-attribute label graphs require at least two nodes")

    edge_labels_supported = tuple(str(label).strip().lower() for label in edge_label_support if str(label).strip())
    if len(set(edge_labels_supported)) != len(edge_labels_supported) or len(edge_labels_supported) < 2:
        raise ValueError("edge_label_support must contain at least two unique labels")
    target_label = str(target_edge_label).strip().lower()
    if target_label not in set(edge_labels_supported):
        raise ValueError("target_edge_label is outside edge_label_support")

    graph = _sample_edge_color_count_base_graph(
        rng,
        node_count=int(node_count_int),
        graph_directionality=str(directionality),
        topology_profile=str(topology_profile),
        max_degree=int(max_degree),
    )
    topology_sample, _label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directionality == "directed"),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    edge_labels = tuple((str(left), str(right)) for left, right in topology_sample.edge_labels)
    if not edge_labels:
        raise ValueError("edge-attribute label graph has no edges")

    query_edge = tuple(str(value) for value in rng.choice(edge_labels))
    non_target_labels = tuple(str(label) for label in edge_labels_supported if str(label) != str(target_label))
    edge_attribute_labels_by_label: Dict[Tuple[str, str], str] = {}
    for edge in edge_labels:
        canonical_edge = (str(edge[0]), str(edge[1]))
        if canonical_edge == tuple(query_edge):
            edge_attribute_labels_by_label[canonical_edge] = str(target_label)
        else:
            # Use all labels, including the target label, as distractors. The queried
            # edge endpoints make the answer unique, so repeated labels are valid.
            edge_attribute_labels_by_label[canonical_edge] = str(rng.choice(edge_labels_supported))
    if not non_target_labels:
        raise ValueError("edge_label_support must include a non-target label")
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
    )


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


def _cross_color_edges_for_assignment(
    *,
    edge_labels: Sequence[Tuple[str, str]],
    node_color_names_by_label: Mapping[str, str],
    directed: bool,
    source_color_name: str,
    target_color_name: str,
) -> Tuple[Tuple[str, str], ...]:
    """Return edges matching one cross-color rule under a node-color assignment."""

    source_color = str(source_color_name)
    target_color = str(target_color_name)
    matches = []
    for left, right in edge_labels:
        left_label = str(left)
        right_label = str(right)
        left_color = str(node_color_names_by_label[left_label])
        right_color = str(node_color_names_by_label[right_label])
        if bool(directed):
            if left_color == source_color and right_color == target_color:
                matches.append((left_label, right_label))
        else:
            if {left_color, right_color} == {source_color, target_color}:
                matches.append((left_label, right_label))
    return sort_graph_edge_labels(tuple(matches), directed=bool(directed))


def _find_cross_color_node_assignment(
    rng: random.Random,
    *,
    labels: Sequence[str],
    edge_labels: Sequence[Tuple[str, str]],
    directed: bool,
    source_color_name: str,
    target_color_name: str,
    color_support: Sequence[str],
    target_count: int,
) -> Tuple[Dict[str, str], Tuple[Tuple[str, str], ...]]:
    """Find node colors that realize exactly ``target_count`` cross-color edges."""

    labels_tuple = tuple(str(label) for label in labels)
    colors = tuple(str(color).strip().lower() for color in color_support if str(color).strip())
    source_color = str(source_color_name).strip().lower()
    target_color = str(target_color_name).strip().lower()
    if source_color == target_color:
        raise ValueError("source_color_name and target_color_name must be distinct")
    if source_color not in set(colors) or target_color not in set(colors):
        raise ValueError("queried colors must be in color_support")
    neutral_colors = tuple(
        str(color) for color in colors if str(color) not in {str(source_color), str(target_color)}
    )
    if not neutral_colors:
        raise ValueError("cross-color edge counts require at least one non-query color")

    target_count_int = int(target_count)

    def build_assignment(states_by_label: Mapping[str, int]) -> Tuple[Dict[str, str], Tuple[Tuple[str, str], ...]] | None:
        state_values = set(int(value) for value in states_by_label.values())
        if 0 not in state_values or 1 not in state_values:
            return None
        color_by_label: Dict[str, str] = {}
        for label in labels_tuple:
            state = int(states_by_label[str(label)])
            if state == 0:
                color_by_label[str(label)] = str(source_color)
            elif state == 1:
                color_by_label[str(label)] = str(target_color)
            else:
                color_by_label[str(label)] = str(rng.choice(neutral_colors))
        matching_edges = _cross_color_edges_for_assignment(
            edge_labels=edge_labels,
            node_color_names_by_label=color_by_label,
            directed=bool(directed),
            source_color_name=str(source_color),
            target_color_name=str(target_color),
        )
        if int(len(matching_edges)) != int(target_count_int):
            return None
        return color_by_label, matching_edges

    for _attempt in range(4096):
        states = {str(label): int(rng.choice((0, 1, 2))) for label in labels_tuple}
        result = build_assignment(states)
        if result is not None:
            return result

    label_order = list(labels_tuple)
    rng.shuffle(label_order)
    state_values = [0, 1, 2]
    rng.shuffle(state_values)
    for state_tuple in product(tuple(state_values), repeat=len(label_order)):
        states = {
            str(label): int(state)
            for label, state in zip(label_order, state_tuple)
        }
        result = build_assignment(states)
        if result is not None:
            return result

    raise ValueError("no node-color assignment realizes the requested cross-color edge count")


def sample_cross_color_edge_count_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    node_count: int,
    target_count: int,
    source_color_name: str,
    target_color_name: str,
    color_support: Sequence[str],
    topology_profile: str,
    label_variant: str,
    max_degree: int,
) -> GraphCrossColorEdgeCountSample:
    """Construct a labeled graph with exactly ``target_count`` queried cross-color edges."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_CROSS_COLOR_EDGE_COUNT_DIRECTIONS:
        raise ValueError(f"unsupported graph_directionality: {graph_directionality}")
    node_count_int = int(node_count)
    target_count_int = int(target_count)
    if int(target_count_int) < 0:
        raise ValueError("target_count cannot be negative")

    colors = tuple(str(color).strip().lower() for color in color_support if str(color).strip())
    if len(set(colors)) != len(colors) or len(colors) < 3:
        raise ValueError("color_support must contain at least three unique color names")
    source_color = str(source_color_name).strip().lower()
    target_color = str(target_color_name).strip().lower()
    if source_color == target_color:
        raise ValueError("source_color_name and target_color_name must be distinct")
    if source_color not in set(colors) or target_color not in set(colors):
        raise ValueError("queried colors must be in color_support")

    last_error: Exception | None = None
    for _attempt in range(100):
        try:
            graph = _sample_node_color_count_base_graph(
                rng,
                node_count=int(node_count_int),
                graph_directionality=str(directionality),
                topology_profile=str(topology_profile),
                max_degree=int(max_degree),
            )
            topology_sample, _label_by_node = _build_labeled_graph_topology_sample(
                rng,
                graph=graph,
                directed=bool(directionality == "directed"),
                topology_profile=str(topology_profile),
                label_variant=str(label_variant),
            )
            edge_labels = tuple((str(left), str(right)) for left, right in topology_sample.edge_labels)
            if int(target_count_int) > int(len(edge_labels)):
                raise ValueError("target_count must be no larger than the sampled edge count")
            node_color_names_by_label, target_edges = _find_cross_color_node_assignment(
                rng,
                labels=topology_sample.node_labels,
                edge_labels=edge_labels,
                directed=bool(directionality == "directed"),
                source_color_name=str(source_color),
                target_color_name=str(target_color),
                color_support=colors,
                target_count=int(target_count_int),
            )
            color_counts_by_name = {
                str(color): sum(
                    1
                    for label in topology_sample.node_labels
                    if str(node_color_names_by_label[str(label)]) == str(color)
                )
                for color in colors
            }
            if int(len(target_edges)) != int(target_count_int):
                raise ValueError("cross-color sampler produced inconsistent target metadata")

            return GraphCrossColorEdgeCountSample(
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
                target_edges=tuple((str(left), str(right)) for left, right in target_edges),
                target_count=int(target_count_int),
                source_color_name=str(source_color),
                target_color_name=str(target_color),
                node_color_names_by_label={str(key): str(value) for key, value in node_color_names_by_label.items()},
                color_counts_by_name={str(key): int(value) for key, value in color_counts_by_name.items()},
                graph_directionality=str(directionality),
            )
        except Exception as exc:
            last_error = exc
            continue
    raise ValueError("failed to sample graph for cross-color edge count") from last_error


@lru_cache(maxsize=128)
def feasible_node_counts_for_isolated_node_count_after_node_removal(
    *,
    graph_directionality: str,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize an exact post-removal isolated-node count."""

    directionality = str(graph_directionality)
    target_count_int = int(target_count)
    if directionality not in SUPPORTED_ISOLATED_AFTER_NODE_REMOVAL_DIRECTIONS:
        return ()
    if int(target_count_int) < 0:
        return ()

    feasible = []
    for node_count in range(int(node_count_min), int(node_count_max) + 1):
        node_count_int = int(node_count)
        if int(node_count_int) < 2:
            continue
        remaining_after_removal = int(node_count_int) - 1
        non_target_remaining = int(remaining_after_removal) - int(target_count_int)
        if int(target_count_int) > int(remaining_after_removal):
            continue
        if int(non_target_remaining) == 1:
            continue
        feasible.append(int(node_count_int))
    return tuple(int(value) for value in feasible)


def _post_removal_isolated_nodes(
    graph: nx.Graph | nx.DiGraph,
    *,
    removed_node: int,
    directed: bool,
) -> Tuple[int, ...]:
    """Return node ids isolated after removing one query node."""

    post_graph = graph.copy()
    post_graph.remove_node(int(removed_node))
    if bool(directed):
        return tuple(
            sorted(
                (
                    int(node)
                    for node in post_graph.nodes()
                    if int(post_graph.in_degree(int(node))) + int(post_graph.out_degree(int(node))) == 0
                )
            )
        )
    return tuple(sorted((int(node) for node in post_graph.nodes() if int(post_graph.degree(int(node))) == 0)))


def _isolated_after_node_removal_is_valid(
    graph: nx.Graph | nx.DiGraph,
    *,
    removed_node: int,
    target_nodes: Sequence[int],
    directed: bool,
) -> bool:
    """Return whether removing one node yields exactly the requested isolated nodes."""

    if bool(directed) and _has_reciprocal_edges(graph):  # type: ignore[arg-type]
        return False
    isolated_nodes = set(
        int(node)
        for node in _post_removal_isolated_nodes(
            graph,
            removed_node=int(removed_node),
            directed=bool(directed),
        )
    )
    return isolated_nodes == {int(node) for node in target_nodes}


def _add_isolated_removal_distractor_edges(
    graph: nx.Graph | nx.DiGraph,
    rng: random.Random,
    *,
    removed_node: int,
    target_nodes: Sequence[int],
    topology_profile: str,
    directed: bool,
) -> nx.Graph | nx.DiGraph:
    """Add safe distractor edges that preserve the post-removal isolated-node witness."""

    nodes = tuple(sorted((int(node) for node in graph.nodes())))
    target_node_set = {int(node) for node in target_nodes}
    extra_budget = _profile_extra_edge_budget(
        node_count=len(nodes),
        topology_profile=str(topology_profile),
        directed=bool(directed),
    )
    added = 0
    if bool(directed):
        candidates = [(int(left), int(right)) for left in nodes for right in nodes if int(left) != int(right)]
    else:
        candidates = [(int(left), int(right)) for left, right in nx.non_edges(graph)]
    rng.shuffle(candidates)

    for left, right in candidates:
        if int(added) >= int(extra_budget):
            break
        source = int(left)
        target = int(right)
        if int(source) in target_node_set and int(target) != int(removed_node):
            continue
        if int(target) in target_node_set and int(source) != int(removed_node):
            continue
        if bool(directed):
            digraph = graph  # type: ignore[assignment]
            if digraph.has_edge(int(source), int(target)) or digraph.has_edge(int(target), int(source)):
                continue
            digraph.add_edge(int(source), int(target))
            if not _isolated_after_node_removal_is_valid(
                digraph,
                removed_node=int(removed_node),
                target_nodes=tuple(int(node) for node in target_nodes),
                directed=True,
            ):
                digraph.remove_edge(int(source), int(target))
                continue
        else:
            undirected_graph = graph  # type: ignore[assignment]
            if undirected_graph.has_edge(int(source), int(target)):
                continue
            undirected_graph.add_edge(int(source), int(target))
            if not _isolated_after_node_removal_is_valid(
                undirected_graph,
                removed_node=int(removed_node),
                target_nodes=tuple(int(node) for node in target_nodes),
                directed=False,
            ):
                undirected_graph.remove_edge(int(source), int(target))
                continue
        added += 1
    return graph


def _sample_isolated_after_node_removal_base_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    node_count: int,
    target_count: int,
    topology_profile: str,
) -> nx.Graph | nx.DiGraph:
    """Build a graph where removing node 0 makes exactly target_count nodes isolated."""

    directionality = str(graph_directionality)
    directed = bool(directionality == "directed")
    node_count_int = int(node_count)
    target_count_int = int(target_count)
    feasible_support = feasible_node_counts_for_isolated_node_count_after_node_removal(
        graph_directionality=str(directionality),
        target_count=int(target_count_int),
        node_count_min=int(node_count_int),
        node_count_max=int(node_count_int),
    )
    if int(node_count_int) not in feasible_support:
        raise ValueError("node_count is outside feasible support for isolated-node-after-removal count")

    graph: nx.Graph | nx.DiGraph = nx.DiGraph() if bool(directed) else nx.Graph()
    graph.add_nodes_from(range(int(node_count_int)))
    removed_node = 0
    target_nodes = tuple(range(1, int(target_count_int) + 1))
    non_target_nodes = tuple(range(int(target_count_int) + 1, int(node_count_int)))

    for node in target_nodes:
        if bool(directed):
            if rng.random() < 0.5:
                graph.add_edge(int(removed_node), int(node))
            else:
                graph.add_edge(int(node), int(removed_node))
        else:
            graph.add_edge(int(removed_node), int(node))

    if len(non_target_nodes) == 1:
        raise ValueError("isolated-node-after-removal sampler cannot protect a single non-target node")
    if len(non_target_nodes) >= 2:
        ordered_non_targets = list(int(node) for node in non_target_nodes)
        rng.shuffle(ordered_non_targets)
        for left, right in zip(ordered_non_targets[:-1], ordered_non_targets[1:]):
            if bool(directed):
                if rng.random() < 0.5:
                    graph.add_edge(int(left), int(right))
                else:
                    graph.add_edge(int(right), int(left))
            else:
                graph.add_edge(int(left), int(right))

    graph = _add_isolated_removal_distractor_edges(
        graph,
        rng,
        removed_node=int(removed_node),
        target_nodes=tuple(int(node) for node in target_nodes),
        topology_profile=str(topology_profile),
        directed=bool(directed),
    )
    if not _isolated_after_node_removal_is_valid(
        graph,
        removed_node=int(removed_node),
        target_nodes=tuple(int(node) for node in target_nodes),
        directed=bool(directed),
    ):
        raise ValueError("isolated-node-after-removal sampler produced inconsistent target metadata")
    return graph


def _directed_adjacency_by_label_for_graph(
    graph: nx.DiGraph,
    *,
    label_by_node: Mapping[int, str],
) -> Dict[str, Tuple[str, ...]]:
    """Return sorted total directed adjacency for one labeled graph."""

    return {
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
        for node in sorted((int(node) for node in graph.nodes()))
    }


def _post_removal_degree_maps_by_label(
    graph: nx.Graph | nx.DiGraph,
    *,
    label_by_node: Mapping[int, str],
    directed: bool,
) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, int]]:
    """Return total, in-, and out-degree maps for one labeled post-removal graph."""

    if bool(directed):
        digraph = graph  # type: ignore[assignment]
        in_degrees = {str(label_by_node[int(node)]): int(digraph.in_degree(int(node))) for node in digraph.nodes()}
        out_degrees = {str(label_by_node[int(node)]): int(digraph.out_degree(int(node))) for node in digraph.nodes()}
        total_degrees = {
            str(label): int(in_degrees[str(label)]) + int(out_degrees[str(label)])
            for label in in_degrees.keys()
        }
        return total_degrees, in_degrees, out_degrees
    undirected_graph = graph  # type: ignore[assignment]
    degrees = {str(label_by_node[int(node)]): int(undirected_graph.degree(int(node))) for node in undirected_graph.nodes()}
    return dict(degrees), dict(degrees), dict(degrees)


def sample_isolated_node_count_after_node_removal_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    node_count: int,
    target_count: int,
    topology_profile: str,
    label_variant: str,
) -> GraphIsolatedAfterNodeRemovalSample:
    """Construct one labeled graph for post-removal isolated-node count queries."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_ISOLATED_AFTER_NODE_REMOVAL_DIRECTIONS:
        raise ValueError(f"unsupported graph_directionality: {graph_directionality}")
    directed = bool(directionality == "directed")
    graph = _sample_isolated_after_node_removal_base_graph(
        rng,
        graph_directionality=str(directionality),
        node_count=int(node_count),
        target_count=int(target_count),
        topology_profile=str(topology_profile),
    )
    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directed),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )

    removed_node = 0
    post_graph = graph.copy()
    post_graph.remove_node(int(removed_node))
    target_nodes = _post_removal_isolated_nodes(
        graph,
        removed_node=int(removed_node),
        directed=bool(directed),
    )
    target_labels = tuple(
        sorted((str(label_by_node[int(node)]) for node in target_nodes), key=graph_label_sort_key)
    )
    if int(len(target_labels)) != int(target_count):
        raise ValueError("isolated-node-after-removal sampler produced the wrong target count")

    if bool(directed):
        pre_adjacency = _directed_adjacency_by_label_for_graph(graph, label_by_node=label_by_node)  # type: ignore[arg-type]
        post_adjacency = _directed_adjacency_by_label_for_graph(post_graph, label_by_node=label_by_node)  # type: ignore[arg-type]
        pre_successors = _directed_successors_by_label_for_graph(graph, label_by_node=label_by_node)  # type: ignore[arg-type]
        post_successors = _directed_successors_by_label_for_graph(post_graph, label_by_node=label_by_node)  # type: ignore[arg-type]
        pre_predecessors = _directed_predecessors_by_label_for_graph(graph, label_by_node=label_by_node)  # type: ignore[arg-type]
        post_predecessors = _directed_predecessors_by_label_for_graph(post_graph, label_by_node=label_by_node)  # type: ignore[arg-type]
    else:
        pre_adjacency = _undirected_adjacency_by_label_for_graph(graph, label_by_node=label_by_node)  # type: ignore[arg-type]
        post_adjacency = _undirected_adjacency_by_label_for_graph(post_graph, label_by_node=label_by_node)  # type: ignore[arg-type]
        pre_successors = dict(pre_adjacency)
        post_successors = dict(post_adjacency)
        pre_predecessors = dict(pre_adjacency)
        post_predecessors = dict(post_adjacency)

    post_degrees, post_in_degrees, post_out_degrees = _post_removal_degree_maps_by_label(
        post_graph,
        label_by_node=label_by_node,
        directed=bool(directed),
    )
    pre_total_degrees = {
        str(label): (
            int(topology_sample.in_degrees_by_label[str(label)]) + int(topology_sample.out_degrees_by_label[str(label)])
            if bool(directed)
            else int(topology_sample.degrees_by_label[str(label)])
        )
        for label in topology_sample.node_labels
    }
    post_edge_labels = sort_graph_edge_labels(
        tuple((str(label_by_node[int(left)]), str(label_by_node[int(right)])) for left, right in post_graph.edges()),
        directed=bool(directed),
    )

    return GraphIsolatedAfterNodeRemovalSample(
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
        query_label=str(label_by_node[int(removed_node)]),
        removed_node_label=str(label_by_node[int(removed_node)]),
        target_labels=tuple(str(label) for label in target_labels),
        target_count=int(target_count),
        graph_directionality=str(directionality),
        pre_removal_adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in pre_adjacency.items()},
        post_removal_adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in post_adjacency.items()},
        pre_removal_successors_by_label={str(key): tuple(str(value) for value in values) for key, values in pre_successors.items()},
        post_removal_successors_by_label={str(key): tuple(str(value) for value in values) for key, values in post_successors.items()},
        pre_removal_predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in pre_predecessors.items()},
        post_removal_predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in post_predecessors.items()},
        pre_removal_degrees_by_label={str(key): int(value) for key, value in pre_total_degrees.items()},
        post_removal_degrees_by_label={str(key): int(value) for key, value in post_degrees.items()},
        pre_removal_in_degrees_by_label={str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()},
        post_removal_in_degrees_by_label={str(key): int(value) for key, value in post_in_degrees.items()},
        pre_removal_out_degrees_by_label={str(key): int(value) for key, value in topology_sample.out_degrees_by_label.items()},
        post_removal_out_degrees_by_label={str(key): int(value) for key, value in post_out_degrees.items()},
        post_removal_edge_labels=tuple((str(left), str(right)) for left, right in post_edge_labels),
    )


def _sample_named_node_undirected_degree_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_degree: int,
    max_degree: int,
    topology_profile: str,
    target_node: int,
) -> nx.Graph:
    """Construct one simple graph where ``target_node`` has exact degree."""

    node_count_int = int(node_count)
    target_degree_int = int(target_degree)
    max_degree_int = max(0, int(max_degree))
    if int(target_degree_int) < 0 or int(target_degree_int) > min(int(max_degree_int), int(node_count_int) - 1):
        raise ValueError("target_degree is infeasible for named-node undirected degree sampling")

    graph = nx.Graph()
    graph.add_nodes_from(range(int(node_count_int)))
    other_nodes = [int(node) for node in range(int(node_count_int)) if int(node) != int(target_node)]
    target_neighbors = rng.sample(other_nodes, int(target_degree_int))
    for neighbor in target_neighbors:
        graph.add_edge(int(target_node), int(neighbor))

    shuffled = list(other_nodes)
    rng.shuffle(shuffled)
    for left, right in zip(shuffled, shuffled[1:]):
        if int(graph.degree(int(left))) >= int(max_degree_int) or int(graph.degree(int(right))) >= int(max_degree_int):
            continue
        graph.add_edge(int(left), int(right))

    _add_random_undirected_distractor_edges(
        graph,
        rng,
        nodes=other_nodes,
        extra_edges=_profile_extra_edge_budget(
            node_count=int(node_count_int),
            topology_profile=str(topology_profile),
            directed=False,
        ),
        max_degree=int(max_degree_int),
    )
    return graph


def _sample_named_node_directed_degree_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_degree: int,
    max_degree: int,
    topology_profile: str,
    degree_mode: str,
    target_node: int,
) -> nx.DiGraph:
    """Construct one simple digraph where ``target_node`` has exact queried degree."""

    node_count_int = int(node_count)
    target_degree_int = int(target_degree)
    max_degree_int = max(0, int(max_degree))
    mode = str(degree_mode)
    if mode not in SUPPORTED_NAMED_NODE_DIRECTED_DEGREE_MODES:
        raise ValueError(f"unsupported directed named-node degree mode: {degree_mode}")
    if int(target_degree_int) < 0 or int(target_degree_int) > min(int(max_degree_int), int(node_count_int) - 1):
        raise ValueError("target_degree is infeasible for named-node directed degree sampling")

    graph = nx.DiGraph()
    graph.add_nodes_from(range(int(node_count_int)))
    other_nodes = [int(node) for node in range(int(node_count_int)) if int(node) != int(target_node)]

    if mode == "in_degree":
        incoming_nodes = rng.sample(other_nodes, int(target_degree_int))
        for source in incoming_nodes:
            graph.add_edge(int(source), int(target_node))
        outgoing_candidates = [int(node) for node in other_nodes if int(node) not in set(incoming_nodes)]
        max_outgoing = min(len(outgoing_candidates), 2, int(max_degree_int) - int(graph.out_degree(int(target_node))))
        outgoing_count = int(rng.randrange(max(0, int(max_outgoing)) + 1))
        for target in rng.sample(outgoing_candidates, int(outgoing_count)):
            _add_directed_edge_without_reciprocal(
                graph,
                source=int(target_node),
                target=int(target),
                max_degree=int(max_degree_int),
            )
    elif mode == "out_degree":
        outgoing_nodes = rng.sample(other_nodes, int(target_degree_int))
        for target in outgoing_nodes:
            graph.add_edge(int(target_node), int(target))
        incoming_candidates = [int(node) for node in other_nodes if int(node) not in set(outgoing_nodes)]
        max_incoming = min(len(incoming_candidates), 2, int(max_degree_int) - int(graph.in_degree(int(target_node))))
        incoming_count = int(rng.randrange(max(0, int(max_incoming)) + 1))
        for source in rng.sample(incoming_candidates, int(incoming_count)):
            _add_directed_edge_without_reciprocal(
                graph,
                source=int(source),
                target=int(target_node),
                max_degree=int(max_degree_int),
            )
    else:
        incident_nodes = rng.sample(other_nodes, int(target_degree_int))
        rng.shuffle(incident_nodes)
        incoming_quota = int(target_degree_int // 2)
        if int(target_degree_int) > 0:
            incoming_quota = int(rng.randint(0, int(target_degree_int)))
        incoming_quota = min(int(incoming_quota), int(max_degree_int))
        outgoing_quota = int(target_degree_int) - int(incoming_quota)
        if int(outgoing_quota) > int(max_degree_int):
            outgoing_quota = int(max_degree_int)
            incoming_quota = int(target_degree_int) - int(outgoing_quota)
        for index, other_node in enumerate(incident_nodes):
            if int(index) < int(incoming_quota):
                graph.add_edge(int(other_node), int(target_node))
            else:
                graph.add_edge(int(target_node), int(other_node))

    shuffled = list(other_nodes)
    rng.shuffle(shuffled)
    for left, right in zip(shuffled, shuffled[1:]):
        if rng.random() < 0.5:
            source, target = int(left), int(right)
        else:
            source, target = int(right), int(left)
        _add_directed_edge_without_reciprocal(
            graph,
            source=int(source),
            target=int(target),
            max_degree=int(max_degree_int),
        )

    _add_random_directed_distractor_edges(
        graph,
        rng,
        nodes=other_nodes,
        extra_edges=_profile_extra_edge_budget(
            node_count=int(node_count_int),
            topology_profile=str(topology_profile),
            directed=True,
        ),
        max_degree=int(max_degree_int),
    )
    return graph


@lru_cache(maxsize=128)
def feasible_node_counts_for_named_node_degree_value(
    *,
    graph_directionality: str,
    degree_mode: str,
    target_degree: int,
    node_count_min: int,
    node_count_max: int,
    max_degree: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize a named-node degree-value query."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_NAMED_NODE_DEGREE_DIRECTIONS:
        return ()
    mode = str(degree_mode)
    if directionality == "undirected" and mode != "degree":
        return ()
    if directionality == "directed" and mode not in SUPPORTED_NAMED_NODE_DIRECTED_DEGREE_MODES:
        return ()
    target_degree_int = int(target_degree)
    max_degree_int = int(max_degree)
    if int(target_degree_int) < 0 or int(target_degree_int) > int(max_degree_int):
        return ()
    feasible = []
    for node_count in range(int(node_count_min), int(node_count_max) + 1):
        if int(target_degree_int) <= int(node_count) - 1:
            feasible.append(int(node_count))
    return tuple(int(value) for value in feasible)


def sample_named_node_degree_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    degree_mode: str,
    node_count: int,
    target_degree: int,
    max_degree: int,
    topology_profile: str,
    label_variant: str,
) -> GraphNamedNodeDegreeSample:
    """Construct one labeled graph for a queried node's degree value."""

    directionality = str(graph_directionality)
    if directionality not in SUPPORTED_NAMED_NODE_DEGREE_DIRECTIONS:
        raise ValueError(f"unsupported graph directionality: {graph_directionality}")
    mode = str(degree_mode)
    if directionality == "undirected":
        if mode != "degree":
            raise ValueError("undirected named-node degree queries require degree_mode=degree")
    elif mode not in SUPPORTED_NAMED_NODE_DIRECTED_DEGREE_MODES:
        raise ValueError(f"unsupported directed named-node degree mode: {degree_mode}")

    node_count_int = int(node_count)
    target_node = int(rng.randrange(int(node_count_int)))
    if directionality == "directed":
        graph = _sample_named_node_directed_degree_graph(
            rng,
            node_count=int(node_count_int),
            target_degree=int(target_degree),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
            degree_mode=str(mode),
            target_node=int(target_node),
        )
        directed = True
    else:
        graph = _sample_named_node_undirected_degree_graph(
            rng,
            node_count=int(node_count_int),
            target_degree=int(target_degree),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
            target_node=int(target_node),
        )
        directed = False

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directed),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    query_label = str(label_by_node[int(target_node)])
    if bool(directed):
        in_degree_sequence = tuple(int(graph.in_degree(int(node))) for node in graph.nodes())
        out_degree_sequence = tuple(int(graph.out_degree(int(node))) for node in graph.nodes())
        degree_sequence = tuple(
            int(graph.in_degree(int(node))) + int(graph.out_degree(int(node)))
            for node in graph.nodes()
        )
        total_degrees_by_label = {
            str(label_by_node[int(node)]): int(graph.in_degree(int(node))) + int(graph.out_degree(int(node)))
            for node in graph.nodes()
        }
        if mode == "in_degree":
            target_edges = tuple(
                (str(label_by_node[int(source)]), str(label_by_node[int(target_node)]))
                for source, _ in graph.in_edges(int(target_node))
            )
        elif mode == "out_degree":
            target_edges = tuple(
                (str(label_by_node[int(target_node)]), str(label_by_node[int(target)]))
                for _, target in graph.out_edges(int(target_node))
            )
        else:
            target_edges = tuple(
                [
                    (str(label_by_node[int(source)]), str(label_by_node[int(target_node)]))
                    for source, _ in graph.in_edges(int(target_node))
                ]
                + [
                    (str(label_by_node[int(target_node)]), str(label_by_node[int(target)]))
                    for _, target in graph.out_edges(int(target_node))
                ]
            )
        sorted_target_edges = sort_graph_edge_labels(target_edges, directed=True)
    else:
        degree_sequence = tuple(int(graph.degree(int(node))) for node in graph.nodes())
        in_degree_sequence = tuple(int(value) for value in degree_sequence)
        out_degree_sequence = tuple(int(value) for value in degree_sequence)
        total_degrees_by_label = {
            str(label_by_node[int(node)]): int(graph.degree(int(node)))
            for node in graph.nodes()
        }
        sorted_target_edges = sort_graph_edge_labels(
            tuple(
                (str(label_by_node[int(target_node)]), str(label_by_node[int(neighbor)]))
                for neighbor in graph.neighbors(int(target_node))
            ),
            directed=False,
        )

    if int(len(sorted_target_edges)) != int(target_degree):
        raise ValueError("named-node degree sampler produced the wrong evidence-edge count")

    return GraphNamedNodeDegreeSample(
        graph=topology_sample.graph,
        directed=bool(topology_sample.directed),
        node_labels=tuple(str(label) for label in topology_sample.node_labels),
        edge_labels=tuple((str(left), str(right)) for left, right in topology_sample.edge_labels),
        degrees_by_label={str(key): int(value) for key, value in total_degrees_by_label.items()},
        in_degrees_by_label={str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()},
        out_degrees_by_label={str(key): int(value) for key, value in topology_sample.out_degrees_by_label.items()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.predecessors_by_label.items()},
        edge_count=int(topology_sample.edge_count),
        topology_profile=str(topology_sample.topology_profile),
        label_variant=str(topology_sample.label_variant),
        query_label=str(query_label),
        target_edges=tuple((str(left), str(right)) for left, right in sorted_target_edges),
        target_degree=int(target_degree),
        degree_mode=str(mode),
        degree_sequence=tuple(int(value) for value in degree_sequence),
        in_degree_sequence=tuple(int(value) for value in in_degree_sequence),
        out_degree_sequence=tuple(int(value) for value in out_degree_sequence),
        total_degrees_by_label={str(key): int(value) for key, value in total_degrees_by_label.items()},
    )


def _add_directed_edge_with_total_cap(
    graph: nx.DiGraph,
    *,
    source: int,
    target: int,
    total_degree_cap: int,
) -> bool:
    """Add one directed edge when both endpoints stay within a total-degree cap."""

    source_int = int(source)
    target_int = int(target)
    cap_int = int(total_degree_cap)
    if int(source_int) == int(target_int):
        return False
    if graph.has_edge(int(source_int), int(target_int)) or graph.has_edge(int(target_int), int(source_int)):
        return False
    source_total = int(graph.in_degree(int(source_int))) + int(graph.out_degree(int(source_int)))
    target_total = int(graph.in_degree(int(target_int))) + int(graph.out_degree(int(target_int)))
    if int(source_total) >= int(cap_int) or int(target_total) >= int(cap_int):
        return False
    graph.add_edge(int(source_int), int(target_int))
    return True


def _sample_extreme_undirected_degree_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_degree: int,
    max_degree: int,
    topology_profile: str,
    extremum_mode: str,
) -> nx.Graph:
    """Construct one simple graph with the requested undirected extreme degree."""

    node_count_int = int(node_count)
    target_degree_int = int(target_degree)
    max_degree_int = max(0, int(max_degree))
    if int(target_degree_int) < 0 or int(target_degree_int) > min(int(max_degree_int), int(node_count_int) - 1):
        raise ValueError("target_degree is infeasible for undirected extreme-degree sampling")

    mode = str(extremum_mode)
    if mode == "max":
        graph = nx.Graph()
        graph.add_nodes_from(range(int(node_count_int)))
        if int(target_degree_int) == 0:
            return graph
        target_node = int(rng.randrange(int(node_count_int)))
        other_nodes = [int(node) for node in range(int(node_count_int)) if int(node) != int(target_node)]
        for neighbor in rng.sample(other_nodes, int(target_degree_int)):
            graph.add_edge(int(target_node), int(neighbor))
        _add_random_undirected_distractor_edges(
            graph,
            rng,
            nodes=tuple(range(int(node_count_int))),
            extra_edges=_profile_extra_edge_budget(
                node_count=int(node_count_int),
                topology_profile=str(topology_profile),
                directed=False,
            ),
            max_degree=int(target_degree_int),
        )
        return graph

    if mode != "min":
        raise ValueError(f"unsupported extreme degree mode: {extremum_mode}")

    if int(target_degree_int) == 0:
        graph = nx.Graph()
        graph.add_nodes_from(range(int(node_count_int)))
        protected = int(rng.randrange(int(node_count_int)))
        other_nodes = [int(node) for node in range(int(node_count_int)) if int(node) != int(protected)]
        shuffled = list(other_nodes)
        rng.shuffle(shuffled)
        for left, right in zip(shuffled, shuffled[1:]):
            graph.add_edge(int(left), int(right))
        _add_random_undirected_distractor_edges(
            graph,
            rng,
            nodes=other_nodes,
            extra_edges=_profile_extra_edge_budget(
                node_count=int(node_count_int),
                topology_profile=str(topology_profile),
                directed=False,
            ),
            max_degree=min(int(max_degree_int), int(node_count_int) - 1),
        )
        return graph

    for _ in range(256):
        graph = nx.Graph()
        graph.add_nodes_from(range(int(node_count_int)))
        steps = 0
        max_steps = max(32, int(node_count_int * node_count_int * 4))
        while min((int(degree) for _, degree in graph.degree()), default=0) < int(target_degree_int):
            deficient = [int(node) for node, degree in graph.degree() if int(degree) < int(target_degree_int)]
            if not deficient:
                break
            left = int(rng.choice(deficient))
            candidates = [
                int(node)
                for node in range(int(node_count_int))
                if int(node) != int(left)
                and not graph.has_edge(int(left), int(node))
                and int(graph.degree(int(node))) < min(int(max_degree_int), int(node_count_int) - 1)
            ]
            if not candidates:
                break
            right = int(rng.choice(candidates))
            graph.add_edge(int(left), int(right))
            steps += 1
            if int(steps) > int(max_steps):
                break
        degrees = [int(degree) for _, degree in graph.degree()]
        if not degrees or min(degrees) != int(target_degree_int):
            continue
        protected_nodes = {int(node) for node, degree in graph.degree() if int(degree) == int(target_degree_int)}
        candidates = [
            (int(left), int(right))
            for left, right in nx.non_edges(graph)
            if int(left) not in protected_nodes
            and int(right) not in protected_nodes
            and int(graph.degree(int(left))) < int(max_degree_int)
            and int(graph.degree(int(right))) < int(max_degree_int)
        ]
        rng.shuffle(candidates)
        extra_budget = _profile_extra_edge_budget(
            node_count=int(node_count_int),
            topology_profile=str(topology_profile),
            directed=False,
        )
        for left, right in candidates[: int(extra_budget)]:
            graph.add_edge(int(left), int(right))
        if min((int(degree) for _, degree in graph.degree()), default=0) == int(target_degree_int):
            return graph
    raise ValueError("failed to sample an undirected graph for the requested min-degree value")


def _sample_extreme_directed_degree_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_degree: int,
    max_degree: int,
    topology_profile: str,
    degree_mode: str,
    extremum_mode: str,
) -> nx.DiGraph:
    """Construct one simple digraph with the requested directed extreme degree."""

    node_count_int = int(node_count)
    target_degree_int = int(target_degree)
    max_degree_int = max(0, int(max_degree))
    degree_mode_text = str(degree_mode)
    extremum_text = str(extremum_mode)
    if degree_mode_text not in SUPPORTED_EXTREME_DEGREE_DIRECTED_MODES:
        raise ValueError(f"unsupported directed extreme-degree mode: {degree_mode}")
    if int(target_degree_int) < 0 or int(target_degree_int) > min(int(max_degree_int), int(node_count_int) - 1):
        raise ValueError("target_degree is infeasible for directed extreme-degree sampling")

    if extremum_text == "max":
        graph = nx.DiGraph()
        graph.add_nodes_from(range(int(node_count_int)))
        if int(target_degree_int) == 0:
            return graph
        target_node = int(rng.randrange(int(node_count_int)))
        other_nodes = [int(node) for node in range(int(node_count_int)) if int(node) != int(target_node)]
        if degree_mode_text == "in_degree":
            for source in rng.sample(other_nodes, int(target_degree_int)):
                graph.add_edge(int(source), int(target_node))
            _add_random_directed_distractor_edges(
                graph,
                rng,
                nodes=tuple(range(int(node_count_int))),
                extra_edges=_profile_extra_edge_budget(
                    node_count=int(node_count_int),
                    topology_profile=str(topology_profile),
                    directed=True,
                ),
                max_degree=max(1, int(target_degree_int)),
            )
            while max((int(degree) for _, degree in graph.in_degree()), default=0) > int(target_degree_int):
                graph.remove_edge(*next(iter(graph.edges())))
        elif degree_mode_text == "out_degree":
            for target in rng.sample(other_nodes, int(target_degree_int)):
                graph.add_edge(int(target_node), int(target))
            _add_random_directed_distractor_edges(
                graph,
                rng,
                nodes=tuple(range(int(node_count_int))),
                extra_edges=_profile_extra_edge_budget(
                    node_count=int(node_count_int),
                    topology_profile=str(topology_profile),
                    directed=True,
                ),
                max_degree=max(1, int(target_degree_int)),
            )
            while max((int(degree) for _, degree in graph.out_degree()), default=0) > int(target_degree_int):
                graph.remove_edge(*next(iter(graph.edges())))
        else:
            incident_nodes = rng.sample(other_nodes, int(target_degree_int))
            rng.shuffle(incident_nodes)
            incoming_count = int(rng.randint(0, int(target_degree_int)))
            for index, other_node in enumerate(incident_nodes):
                if int(index) < int(incoming_count):
                    graph.add_edge(int(other_node), int(target_node))
                else:
                    graph.add_edge(int(target_node), int(other_node))
            candidates = [
                (int(left), int(right))
                for left in range(int(node_count_int))
                for right in range(int(node_count_int))
                if int(left) != int(right)
            ]
            rng.shuffle(candidates)
            added = 0
            extra_budget = _profile_extra_edge_budget(
                node_count=int(node_count_int),
                topology_profile=str(topology_profile),
                directed=True,
            )
            for source, target in candidates:
                if int(added) >= int(extra_budget):
                    break
                if _add_directed_edge_with_total_cap(
                    graph,
                    source=int(source),
                    target=int(target),
                    total_degree_cap=max(1, int(target_degree_int)),
                ):
                    added += 1
        return graph

    if extremum_text != "min":
        raise ValueError(f"unsupported extreme degree mode: {extremum_mode}")

    if int(target_degree_int) == 0:
        graph = nx.DiGraph()
        graph.add_nodes_from(range(int(node_count_int)))
        protected = int(rng.randrange(int(node_count_int)))
        candidates = []
        for source in range(int(node_count_int)):
            for target in range(int(node_count_int)):
                if int(source) == int(target):
                    continue
                if degree_mode_text == "in_degree" and int(target) == int(protected):
                    continue
                if degree_mode_text == "out_degree" and int(source) == int(protected):
                    continue
                if degree_mode_text == "total_degree" and int(protected) in {int(source), int(target)}:
                    continue
                candidates.append((int(source), int(target)))
        rng.shuffle(candidates)
        added = 0
        extra_budget = _profile_extra_edge_budget(
            node_count=int(node_count_int),
            topology_profile=str(topology_profile),
            directed=True,
        )
        for source, target in candidates:
            if int(added) >= int(extra_budget):
                break
            if _add_directed_edge_without_reciprocal(
                graph,
                source=int(source),
                target=int(target),
                max_degree=min(int(max_degree_int), int(node_count_int) - 1),
            ):
                added += 1
        return graph

    for _ in range(256):
        graph = nx.DiGraph()
        graph.add_nodes_from(range(int(node_count_int)))
        steps = 0
        max_steps = max(64, int(node_count_int * node_count_int * 8))
        while True:
            if degree_mode_text == "in_degree":
                values = {int(node): int(graph.in_degree(int(node))) for node in graph.nodes()}
                deficient = [int(node) for node, value in values.items() if int(value) < int(target_degree_int)]
                if not deficient:
                    break
                target = int(rng.choice(deficient))
                sources = [
                    int(node)
                    for node in graph.nodes()
                    if int(node) != int(target)
                    and not graph.has_edge(int(node), int(target))
                    and not graph.has_edge(int(target), int(node))
                ]
                if not sources:
                    break
                graph.add_edge(int(rng.choice(sources)), int(target))
            elif degree_mode_text == "out_degree":
                values = {int(node): int(graph.out_degree(int(node))) for node in graph.nodes()}
                deficient = [int(node) for node, value in values.items() if int(value) < int(target_degree_int)]
                if not deficient:
                    break
                source = int(rng.choice(deficient))
                targets = [
                    int(node)
                    for node in graph.nodes()
                    if int(node) != int(source)
                    and not graph.has_edge(int(source), int(node))
                    and not graph.has_edge(int(node), int(source))
                ]
                if not targets:
                    break
                graph.add_edge(int(source), int(rng.choice(targets)))
            else:
                values = {
                    int(node): int(graph.in_degree(int(node))) + int(graph.out_degree(int(node)))
                    for node in graph.nodes()
                }
                deficient = [int(node) for node, value in values.items() if int(value) < int(target_degree_int)]
                if not deficient:
                    break
                endpoint = int(rng.choice(deficient))
                others = [
                    int(node)
                    for node in graph.nodes()
                    if int(node) != int(endpoint)
                    and not graph.has_edge(int(endpoint), int(node))
                    and not graph.has_edge(int(node), int(endpoint))
                ]
                if not others:
                    break
                other = int(rng.choice(others))
                if rng.random() < 0.5:
                    graph.add_edge(int(endpoint), int(other))
                else:
                    graph.add_edge(int(other), int(endpoint))
            steps += 1
            if int(steps) > int(max_steps):
                break
        if degree_mode_text == "in_degree":
            queried_values = [int(degree) for _, degree in graph.in_degree()]
        elif degree_mode_text == "out_degree":
            queried_values = [int(degree) for _, degree in graph.out_degree()]
        else:
            queried_values = [
                int(graph.in_degree(int(node))) + int(graph.out_degree(int(node)))
                for node in graph.nodes()
            ]
        if queried_values and min(queried_values) == int(target_degree_int):
            return graph
    raise ValueError("failed to sample a directed graph for the requested min-degree value")


@lru_cache(maxsize=128)
def feasible_node_counts_for_extreme_degree_value(
    *,
    graph_directionality: str,
    degree_mode: str,
    extremum_mode: str,
    target_degree: int,
    node_count_min: int,
    node_count_max: int,
    max_degree: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize an extreme degree-value query."""

    directionality = str(graph_directionality)
    mode = str(degree_mode)
    extremum = str(extremum_mode)
    target_degree_int = int(target_degree)
    max_degree_int = int(max_degree)
    if directionality not in SUPPORTED_EXTREME_DEGREE_DIRECTIONS:
        return ()
    if extremum not in SUPPORTED_EXTREME_DEGREE_EXTREMA:
        return ()
    if directionality == "undirected" and mode != "degree":
        return ()
    if directionality == "directed" and mode not in SUPPORTED_EXTREME_DEGREE_DIRECTED_MODES:
        return ()
    if int(target_degree_int) < 0 or int(target_degree_int) > int(max_degree_int):
        return ()

    feasible = []
    for node_count in range(int(node_count_min), int(node_count_max) + 1):
        node_count_int = int(node_count)
        if int(target_degree_int) > int(node_count_int) - 1:
            continue
        if directionality == "directed" and extremum == "min" and mode in {"in_degree", "out_degree"}:
            if int(target_degree_int) > int((node_count_int - 1) // 2):
                continue
        feasible.append(int(node_count_int))
    return tuple(int(value) for value in feasible)


def sample_extreme_degree_graph(
    rng: random.Random,
    *,
    graph_directionality: str,
    degree_mode: str,
    extremum_mode: str,
    node_count: int,
    target_degree: int,
    max_degree: int,
    topology_profile: str,
    label_variant: str,
) -> GraphExtremeDegreeSample:
    """Construct one labeled graph whose queried extreme degree equals target_degree."""

    directionality = str(graph_directionality)
    degree_mode_text = str(degree_mode)
    extremum_text = str(extremum_mode)
    if directionality == "undirected":
        graph = _sample_extreme_undirected_degree_graph(
            rng,
            node_count=int(node_count),
            target_degree=int(target_degree),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
            extremum_mode=str(extremum_text),
        )
        directed = False
    elif directionality == "directed":
        graph = _sample_extreme_directed_degree_graph(
            rng,
            node_count=int(node_count),
            target_degree=int(target_degree),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
            degree_mode=str(degree_mode_text),
            extremum_mode=str(extremum_text),
        )
        directed = True
    else:
        raise ValueError(f"unsupported graph directionality: {graph_directionality}")

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(directed),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    if bool(directed):
        in_degree_sequence = tuple(int(graph.in_degree(int(node))) for node in graph.nodes())
        out_degree_sequence = tuple(int(graph.out_degree(int(node))) for node in graph.nodes())
        degree_sequence = tuple(
            int(graph.in_degree(int(node))) + int(graph.out_degree(int(node)))
            for node in graph.nodes()
        )
        total_degrees_by_label = {
            str(label_by_node[int(node)]): int(graph.in_degree(int(node))) + int(graph.out_degree(int(node)))
            for node in graph.nodes()
        }
        if degree_mode_text == "in_degree":
            queried_degrees_by_label = {str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()}
        elif degree_mode_text == "out_degree":
            queried_degrees_by_label = {str(key): int(value) for key, value in topology_sample.out_degrees_by_label.items()}
        else:
            queried_degrees_by_label = {str(key): int(value) for key, value in total_degrees_by_label.items()}
    else:
        degree_sequence = tuple(int(graph.degree(int(node))) for node in graph.nodes())
        in_degree_sequence = tuple(int(value) for value in degree_sequence)
        out_degree_sequence = tuple(int(value) for value in degree_sequence)
        total_degrees_by_label = {
            str(label_by_node[int(node)]): int(graph.degree(int(node)))
            for node in graph.nodes()
        }
        queried_degrees_by_label = {str(key): int(value) for key, value in total_degrees_by_label.items()}
        degree_mode_text = "degree"

    observed_values = list(int(value) for value in queried_degrees_by_label.values())
    if not observed_values:
        raise ValueError("extreme degree graph has no observed degree values")
    observed_extreme = max(observed_values) if extremum_text == "max" else min(observed_values)
    if int(observed_extreme) != int(target_degree):
        raise ValueError("extreme degree sampler produced the wrong target degree")
    target_labels = tuple(
        sorted(
            (str(label) for label, value in queried_degrees_by_label.items() if int(value) == int(target_degree)),
            key=graph_label_sort_key,
        )
    )

    return GraphExtremeDegreeSample(
        graph=topology_sample.graph,
        directed=bool(topology_sample.directed),
        node_labels=tuple(str(label) for label in topology_sample.node_labels),
        edge_labels=tuple((str(left), str(right)) for left, right in topology_sample.edge_labels),
        degrees_by_label={str(key): int(value) for key, value in total_degrees_by_label.items()},
        in_degrees_by_label={str(key): int(value) for key, value in topology_sample.in_degrees_by_label.items()},
        out_degrees_by_label={str(key): int(value) for key, value in topology_sample.out_degrees_by_label.items()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in topology_sample.predecessors_by_label.items()},
        edge_count=int(topology_sample.edge_count),
        topology_profile=str(topology_sample.topology_profile),
        label_variant=str(topology_sample.label_variant),
        target_labels=tuple(str(label) for label in target_labels),
        target_degree=int(target_degree),
        extremum_mode=str(extremum_text),
        degree_mode=str(degree_mode_text),
        degree_sequence=tuple(int(value) for value in degree_sequence),
        in_degree_sequence=tuple(int(value) for value in in_degree_sequence),
        out_degree_sequence=tuple(int(value) for value in out_degree_sequence),
        queried_degrees_by_label={str(key): int(value) for key, value in queried_degrees_by_label.items()},
        total_degrees_by_label={str(key): int(value) for key, value in total_degrees_by_label.items()},
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


def feasible_node_counts_for_component_size_after_edge_edit(
    *,
    edit_operation: str,
    target_component_size: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one undirected edge-edit component query."""

    operation = str(edit_operation)
    target_size = int(target_component_size)
    if operation == "edge_removal":
        if int(target_size) < 1:
            return ()
        minimum = max(int(node_count_min), int(target_size) + 1)
    elif operation == "edge_addition":
        if int(target_size) < 2:
            return ()
        minimum = max(int(node_count_min), int(target_size))
    else:
        return ()
    maximum = int(node_count_max)
    if int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def feasible_node_counts_for_reachable_count(
    *,
    target_reachable_count: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one directed reachable-count query.

    The queried source node is included in the count, and at least one node
    remains unreachable so the scene never collapses to a fully reachable graph.
    """

    target_count = int(target_reachable_count)
    if int(target_count) < 1:
        return ()
    minimum = max(int(node_count_min), 5, int(target_count) + 1)
    maximum = int(node_count_max)
    if int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def feasible_node_counts_for_reachable_count_after_edge_edit(
    *,
    edit_operation: str,
    target_reachable_count: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one directed edge-edit reachability query."""

    operation = str(edit_operation)
    target_count = int(target_reachable_count)
    if operation == "edge_removal":
        if int(target_count) < 1:
            return ()
        minimum = max(int(node_count_min), 5, int(target_count) + 1)
    elif operation == "edge_addition":
        if int(target_count) < 2:
            return ()
        minimum = max(int(node_count_min), 5, int(target_count))
    else:
        return ()
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


def feasible_node_counts_for_shortest_path_length(
    *,
    target_shortest_path_length: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one unique shortest-path query."""

    target_length = int(target_shortest_path_length)
    minimum = max(int(node_count_min), 5, int(target_length) + 2)
    maximum = int(node_count_max)
    if int(target_length) < 1 or int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def feasible_node_counts_for_longest_path_length(
    *,
    target_longest_path_length: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one unique longest-path DAG query."""

    target_length = int(target_longest_path_length)
    minimum = max(int(node_count_min), 4, int(target_length) + 2)
    maximum = int(node_count_max)
    if int(target_length) < 1 or int(minimum) > int(maximum):
        return ()
    return tuple(range(int(minimum), int(maximum) + 1))


def feasible_node_counts_for_topological_position(
    *,
    target_position: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize a queried topological position."""

    target_position_int = int(target_position)
    minimum = max(int(node_count_min), 3, int(target_position_int))
    maximum = int(node_count_max)
    if int(target_position_int) < 1 or int(minimum) > int(maximum):
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


def feasible_node_counts_for_bridge_count(
    *,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
) -> Tuple[int, ...]:
    """Return node counts that can realize one bridge-edge count query.

    The connected construction uses a tree of bridgeless blocks. This makes
    `target_count + 2` nodes infeasible because it would force exactly one
    extra node beyond the bridge skeleton, which cannot form a bridgeless block.
    """

    target_int = int(target_count)
    if int(target_int) < 0:
        return ()
    feasible: list[int] = []
    for node_count in range(int(node_count_min), int(node_count_max) + 1):
        node_count_int = int(node_count)
        if int(target_int) == 0:
            if int(node_count_int) >= 3:
                feasible.append(int(node_count_int))
            continue
        if int(node_count_int) < int(target_int) + 1:
            continue
        if int(node_count_int) == int(target_int) + 2:
            continue
        feasible.append(int(node_count_int))
    return tuple(int(value) for value in feasible)


def feasible_extra_edge_counts_for_minimum_spanning_tree(
    *,
    node_count: int,
    extra_edge_count_min: int,
    extra_edge_count_max: int,
    edge_weight_min: int,
    edge_weight_max: int,
) -> Tuple[int, ...]:
    """Return feasible non-tree edge counts for one weighted MST query.

    The MST construction uses a connected spanning tree plus a small number of
    additional non-tree edges. We require all rendered edge weights to be
    distinct integers in ``[edge_weight_min, edge_weight_max]``, so the total
    edge count must not exceed the available weight support.
    """

    node_count_int = int(node_count)
    tree_edge_count = max(0, int(node_count_int) - 1)
    max_available_edges = int(edge_weight_max) - int(edge_weight_min) + 1
    if int(tree_edge_count) <= 0 or int(max_available_edges) <= int(tree_edge_count):
        return ()

    max_non_edges = (int(node_count_int) * int(node_count_int - 1) // 2) - int(tree_edge_count)
    feasible_max = min(
        int(extra_edge_count_max),
        int(max_non_edges),
        int(max_available_edges - tree_edge_count),
    )
    feasible_min = max(1, int(extra_edge_count_min))
    if int(feasible_min) > int(feasible_max):
        return ()
    return tuple(range(int(feasible_min), int(feasible_max) + 1))


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


def _sample_unique_shortest_path_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_shortest_path_length: int,
    topology_profile: str,
) -> Tuple[nx.Graph, Tuple[int, ...], int]:
    """Return one connected graph with a unique shortest path of the requested length.

    The construction starts from a backbone path of the requested edge length,
    attaches at least one off-path node, and optionally adds cycle-forming
    non-edges inside the same branch anchor so the unique shortest path between
    the two backbone endpoints remains unchanged.
    """

    node_count_int = int(node_count)
    target_length_int = int(target_shortest_path_length)
    feasible_node_support = feasible_node_counts_for_shortest_path_length(
        target_shortest_path_length=int(target_length_int),
        node_count_min=int(node_count_int),
        node_count_max=int(node_count_int),
    )
    if int(node_count_int) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested shortest-path query")

    path_nodes = tuple(range(int(target_length_int) + 1))
    graph = nx.path_graph(path_nodes)
    anchor_by_node = {int(node): int(node) for node in path_nodes}

    next_node = int(target_length_int) + 1
    while int(next_node) < int(node_count_int):
        parent = _choose_attachment_parent(
            rng,
            graph=graph,
            topology_profile=str(topology_profile),
        )
        graph.add_node(int(next_node))
        graph.add_edge(int(parent), int(next_node))
        anchor_by_node[int(next_node)] = int(anchor_by_node[int(parent)])
        next_node += 1

    source_node = int(path_nodes[0])
    goal_node = int(path_nodes[-1])
    adjacency = _graph_adjacency_by_node(graph)
    dist_start, count_start = bfs_dist_count_by_adjacency(adjacency, start=int(source_node))
    dist_goal, _ = bfs_dist_count_by_adjacency(adjacency, start=int(goal_node))
    unique_path = reconstruct_unique_shortest_path_by_adjacency(
        adjacency,
        start=int(source_node),
        goal=int(goal_node),
        dist_start=dist_start,
        dist_goal=dist_goal,
    )
    if unique_path is None or tuple(int(node) for node in unique_path) != tuple(int(node) for node in path_nodes):
        raise ValueError("backbone construction failed to preserve the requested unique shortest path")

    extra_edge_candidates = [
        (int(left), int(right))
        for left, right in nx.non_edges(graph)
        if int(anchor_by_node[int(left)]) == int(anchor_by_node[int(right)])
        and not (int(left) in path_nodes and int(right) in path_nodes)
    ]
    rng.shuffle(extra_edge_candidates)
    if str(topology_profile) == "hub_heavy":
        extra_edge_budget = min(3, len(extra_edge_candidates))
    elif str(topology_profile) == "balanced":
        extra_edge_budget = min(2, len(extra_edge_candidates))
    else:
        extra_edge_budget = min(1, len(extra_edge_candidates))

    extra_edges_kept = 0
    for left, right in extra_edge_candidates:
        if int(extra_edges_kept) >= int(extra_edge_budget):
            break
        graph.add_edge(int(left), int(right))
        adjacency = _graph_adjacency_by_node(graph)
        dist_start, count_start = bfs_dist_count_by_adjacency(adjacency, start=int(source_node))
        if int(dist_start.get(int(goal_node), -1)) != int(target_length_int) or int(count_start.get(int(goal_node), 0)) != 1:
            graph.remove_edge(int(left), int(right))
            continue
        dist_goal, _ = bfs_dist_count_by_adjacency(adjacency, start=int(goal_node))
        unique_path = reconstruct_unique_shortest_path_by_adjacency(
            adjacency,
            start=int(source_node),
            goal=int(goal_node),
            dist_start=dist_start,
            dist_goal=dist_goal,
        )
        if unique_path is None or tuple(int(node) for node in unique_path) != tuple(int(node) for node in path_nodes):
            graph.remove_edge(int(left), int(right))
            continue
        extra_edges_kept += 1

    return graph, tuple(int(node) for node in path_nodes), int(extra_edges_kept)


def _sample_unique_shortest_path_digraph(
    rng: random.Random,
    *,
    node_count: int,
    target_shortest_path_length: int,
    topology_profile: str,
) -> Tuple[nx.DiGraph, Tuple[int, ...], int]:
    """Return one directed graph with a unique shortest directed path of the requested length.

    The source-to-goal witness path is realized by one directed backbone chain.
    Off-path nodes attach as incoming or outgoing branches, and optional extra
    off-path edges are only retained when they preserve the unique directed
    shortest path between the backbone endpoints.
    """

    node_count_int = int(node_count)
    target_length_int = int(target_shortest_path_length)
    feasible_node_support = feasible_node_counts_for_shortest_path_length(
        target_shortest_path_length=int(target_length_int),
        node_count_min=int(node_count_int),
        node_count_max=int(node_count_int),
    )
    if int(node_count_int) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested directed shortest-path query")

    path_nodes = tuple(range(int(target_length_int) + 1))
    graph = nx.DiGraph()
    graph.add_nodes_from(path_nodes)
    graph.add_edges_from((int(left), int(right)) for left, right in zip(path_nodes[:-1], path_nodes[1:]))
    anchor_by_node = {int(node): int(node) for node in path_nodes}

    profile = str(topology_profile)
    next_node = int(target_length_int) + 1
    while int(next_node) < int(node_count_int):
        parent = _choose_attachment_parent(
            rng,
            graph=graph,
            topology_profile=profile,
        )
        graph.add_node(int(next_node))
        branch_direction = str(
            rng.choices(
                ("out", "in"),
                weights=(2.0, 1.0) if profile == "hub_heavy" else (1.0, 1.0),
                k=1,
            )[0]
        )
        if branch_direction == "out":
            graph.add_edge(int(parent), int(next_node))
        else:
            graph.add_edge(int(next_node), int(parent))
        anchor_by_node[int(next_node)] = int(anchor_by_node[int(parent)])
        next_node += 1

    source_node = int(path_nodes[0])
    goal_node = int(path_nodes[-1])
    successors = _digraph_successor_adjacency_by_node(graph)
    predecessors = _digraph_predecessor_adjacency_by_node(graph)
    dist_start, count_start = bfs_dist_count_by_adjacency(successors, start=int(source_node))
    dist_goal, _ = bfs_dist_count_by_adjacency(predecessors, start=int(goal_node))
    unique_path = reconstruct_unique_shortest_path_by_adjacency(
        successors,
        start=int(source_node),
        goal=int(goal_node),
        dist_start=dist_start,
        dist_goal=dist_goal,
    )
    if unique_path is None or tuple(int(node) for node in unique_path) != tuple(int(node) for node in path_nodes):
        raise ValueError("directed backbone construction failed to preserve the requested unique shortest path")

    extra_edge_candidates = [
        (int(left), int(right))
        for left, right in nx.non_edges(graph)
        if int(anchor_by_node[int(left)]) == int(anchor_by_node[int(right)])
        and not (int(left) in path_nodes and int(right) in path_nodes)
        and not graph.has_edge(int(right), int(left))
    ]
    rng.shuffle(extra_edge_candidates)
    if profile == "hub_heavy":
        extra_edge_budget = min(1, len(extra_edge_candidates))
    elif profile == "balanced":
        extra_edge_budget = min(1, len(extra_edge_candidates))
    else:
        extra_edge_budget = 0

    extra_edges_kept = 0
    for left, right in extra_edge_candidates:
        if int(extra_edges_kept) >= int(extra_edge_budget):
            break
        graph.add_edge(int(left), int(right))
        successors = _digraph_successor_adjacency_by_node(graph)
        predecessors = _digraph_predecessor_adjacency_by_node(graph)
        dist_start, count_start = bfs_dist_count_by_adjacency(successors, start=int(source_node))
        if int(dist_start.get(int(goal_node), -1)) != int(target_length_int) or int(count_start.get(int(goal_node), 0)) != 1:
            graph.remove_edge(int(left), int(right))
            continue
        dist_goal, _ = bfs_dist_count_by_adjacency(predecessors, start=int(goal_node))
        unique_path = reconstruct_unique_shortest_path_by_adjacency(
            successors,
            start=int(source_node),
            goal=int(goal_node),
            dist_start=dist_start,
            dist_goal=dist_goal,
        )
        if unique_path is None or tuple(int(node) for node in unique_path) != tuple(int(node) for node in path_nodes):
            graph.remove_edge(int(left), int(right))
            continue
        extra_edges_kept += 1

    return graph, tuple(int(node) for node in path_nodes), int(extra_edges_kept)


def _unique_longest_path_in_dag(graph: nx.DiGraph) -> Tuple[int, Tuple[int, ...]] | None:
    """Return the unique longest directed path in a DAG, or None when tied."""

    if not nx.is_directed_acyclic_graph(graph):
        return None
    topo_order = tuple(int(node) for node in nx.topological_sort(graph))
    if not topo_order:
        return None
    best_length = {int(node): 0 for node in topo_order}
    best_count = {int(node): 1 for node in topo_order}
    best_path = {int(node): (int(node),) for node in topo_order}
    for source in topo_order:
        for target in sorted((int(node) for node in graph.successors(int(source)))):
            candidate_length = int(best_length[int(source)]) + 1
            if int(candidate_length) > int(best_length[int(target)]):
                best_length[int(target)] = int(candidate_length)
                best_count[int(target)] = int(best_count[int(source)])
                best_path[int(target)] = (*best_path[int(source)], int(target))
            elif int(candidate_length) == int(best_length[int(target)]):
                best_count[int(target)] += int(best_count[int(source)])

    max_length = max(int(value) for value in best_length.values())
    endpoints = [int(node) for node in topo_order if int(best_length[int(node)]) == int(max_length)]
    max_path_count = sum(int(best_count[int(node)]) for node in endpoints)
    if int(max_path_count) != 1:
        return None
    endpoint = next(int(node) for node in endpoints if int(best_count[int(node)]) == 1)
    return int(max_length), tuple(int(node) for node in best_path[int(endpoint)])


def _try_add_dag_edge_preserving_unique_longest_path(
    graph: nx.DiGraph,
    *,
    source: int,
    target: int,
    path_nodes: Tuple[int, ...],
    target_longest_path_length: int,
) -> bool:
    """Add one edge if the requested unique longest path remains unchanged."""

    source_int = int(source)
    target_int = int(target)
    if int(source_int) == int(target_int):
        return False
    if graph.has_edge(int(source_int), int(target_int)) or graph.has_edge(int(target_int), int(source_int)):
        return False
    graph.add_edge(int(source_int), int(target_int))
    observed = _unique_longest_path_in_dag(graph)
    if observed is None:
        graph.remove_edge(int(source_int), int(target_int))
        return False
    observed_length, observed_path = observed
    if int(observed_length) != int(target_longest_path_length) or tuple(int(node) for node in observed_path) != tuple(
        int(node) for node in path_nodes
    ):
        graph.remove_edge(int(source_int), int(target_int))
        return False
    return True


def _sample_unique_longest_path_dag(
    rng: random.Random,
    *,
    node_count: int,
    target_longest_path_length: int,
    topology_profile: str,
) -> Tuple[nx.DiGraph, Tuple[int, ...], int, int]:
    """Return a DAG with one unique global longest directed path."""

    node_count_int = int(node_count)
    target_length_int = int(target_longest_path_length)
    feasible_node_support = feasible_node_counts_for_longest_path_length(
        target_longest_path_length=int(target_length_int),
        node_count_min=int(node_count_int),
        node_count_max=int(node_count_int),
    )
    if int(node_count_int) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested longest-path query")

    path_nodes = tuple(range(int(target_length_int) + 1))
    graph = nx.DiGraph()
    graph.add_nodes_from(range(int(node_count_int)))
    graph.add_edges_from((int(left), int(right)) for left, right in zip(path_nodes[:-1], path_nodes[1:]))

    observed = _unique_longest_path_in_dag(graph)
    if observed is None or int(observed[0]) != int(target_length_int) or tuple(observed[1]) != tuple(path_nodes):
        raise ValueError("longest-path backbone construction failed")

    off_path_nodes = tuple(range(int(target_length_int) + 1, int(node_count_int)))
    attached_off_path_nodes: set[int] = set()
    all_nodes = tuple(range(int(node_count_int)))
    for off_path_node in off_path_nodes:
        existing_nodes = [int(node) for node in all_nodes if int(node) != int(off_path_node)]
        candidates = [
            (int(source), int(target))
            for neighbor in existing_nodes
            for source, target in ((int(neighbor), int(off_path_node)), (int(off_path_node), int(neighbor)))
        ]
        rng.shuffle(candidates)
        attached = False
        for source, target in candidates:
            if _try_add_dag_edge_preserving_unique_longest_path(
                graph,
                source=int(source),
                target=int(target),
                path_nodes=path_nodes,
                target_longest_path_length=int(target_length_int),
            ):
                attached_off_path_nodes.add(int(off_path_node))
                attached = True
                break
        if not bool(attached):
            raise ValueError("failed to attach off-path node while preserving unique longest path")

    extra_edge_candidates = [
        (int(source), int(target))
        for source in all_nodes
        for target in all_nodes
        if int(source) != int(target)
        and not graph.has_edge(int(source), int(target))
        and not graph.has_edge(int(target), int(source))
    ]
    rng.shuffle(extra_edge_candidates)
    if str(topology_profile) == "hub_heavy":
        extra_edge_budget = min(4, len(extra_edge_candidates))
    elif str(topology_profile) == "balanced":
        extra_edge_budget = min(2, len(extra_edge_candidates))
    else:
        extra_edge_budget = min(1, len(extra_edge_candidates))

    extra_edges_kept = 0
    for source, target in extra_edge_candidates:
        if int(extra_edges_kept) >= int(extra_edge_budget):
            break
        if _try_add_dag_edge_preserving_unique_longest_path(
            graph,
            source=int(source),
            target=int(target),
            path_nodes=path_nodes,
            target_longest_path_length=int(target_length_int),
        ):
            if int(source) in off_path_nodes:
                attached_off_path_nodes.add(int(source))
            if int(target) in off_path_nodes:
                attached_off_path_nodes.add(int(target))
            extra_edges_kept += 1

    observed = _unique_longest_path_in_dag(graph)
    if observed is None or int(observed[0]) != int(target_length_int) or tuple(int(node) for node in observed[1]) != tuple(path_nodes):
        raise ValueError("longest-path DAG construction failed final validation")
    return graph, tuple(int(node) for node in path_nodes), int(len(attached_off_path_nodes)), int(extra_edges_kept)


def _sample_unique_topological_order_digraph(
    rng: random.Random,
    *,
    node_count: int,
    topology_profile: str,
) -> Tuple[nx.DiGraph, Tuple[int, ...], int]:
    """Return one DAG whose topological order is unique by construction."""

    node_count_int = int(node_count)
    if int(node_count_int) < 2:
        raise ValueError("topological-order sampling requires at least two nodes")

    order_nodes = tuple(range(int(node_count_int)))
    graph = nx.DiGraph()
    graph.add_nodes_from(order_nodes)
    graph.add_edges_from((int(left), int(right)) for left, right in zip(order_nodes[:-1], order_nodes[1:]))

    candidate_edges = [
        (int(left), int(right))
        for left in order_nodes
        for right in order_nodes
        if int(left) < int(right) - 1 and not graph.has_edge(int(left), int(right))
    ]
    profile = str(topology_profile)
    if profile == "hub_heavy":
        ordered_candidates = sorted(candidate_edges, key=lambda pair: (int(pair[0]), -(int(pair[1]) - int(pair[0]))))
        extra_edge_budget = min(len(ordered_candidates), max(2, min(6, int(node_count_int) - 2)))
    elif profile == "low_degree":
        ordered_candidates = sorted(candidate_edges, key=lambda pair: (int(pair[1]) - int(pair[0]), int(pair[0]), int(pair[1])))
        extra_edge_budget = min(len(ordered_candidates), max(1, min(2, int(node_count_int) - 3)))
    else:
        ordered_candidates = list(candidate_edges)
        rng.shuffle(ordered_candidates)
        extra_edge_budget = min(len(ordered_candidates), max(1, min(4, int(node_count_int) - 2)))

    extra_edges_kept = 0
    for left, right in ordered_candidates:
        if int(extra_edges_kept) >= int(extra_edge_budget):
            break
        graph.add_edge(int(left), int(right))
        extra_edges_kept += 1

    return graph, tuple(int(node) for node in order_nodes), int(extra_edges_kept)


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


def _sample_zero_bridge_graph(
    rng: random.Random,
    *,
    node_count: int,
    topology_profile: str,
) -> nx.Graph:
    """Return one connected graph with zero bridges."""

    node_count_int = int(node_count)
    if int(node_count_int) < 3:
        raise ValueError("zero-bridge sampling requires at least three nodes")
    graph = nx.cycle_graph(int(node_count_int))
    profile = str(topology_profile)
    if profile != "low_degree":
        complete_edges = (int(node_count_int) * (int(node_count_int) - 1)) // 2
        cycle_edges = int(node_count_int)
        max_extra = max(0, min(int(node_count_int // 2), int(complete_edges - cycle_edges)))
        _add_random_non_edges(graph, rng, extra_edges=int(rng.randint(0, max_extra if max_extra > 0 else 0)))
    if any(True for _ in nx.bridges(graph)):
        raise ValueError("zero-bridge sampler produced a bridge edge")
    return graph


def _sample_bridge_block_sizes(
    rng: random.Random,
    *,
    node_count: int,
    target_count: int,
    topology_profile: str,
) -> Tuple[int, ...]:
    """Return block sizes for one connected exact-bridge construction.

    Blocks are either size `1` or bridgeless size `>= 3`. Connecting the blocks
    with a tree therefore yields exactly `target_count` bridge edges.
    """

    node_count_int = int(node_count)
    target_count_int = int(target_count)
    block_count = int(target_count_int) + 1
    if int(block_count) > int(node_count_int):
        raise ValueError("bridge block count exceeds node count")
    extra_nodes = int(node_count_int - block_count)
    if int(extra_nodes) == 1:
        raise ValueError("bridge construction cannot realize exactly one extra node beyond the bridge skeleton")
    sizes = [1] * int(block_count)
    if int(extra_nodes) <= 0:
        return tuple(int(value) for value in sizes)

    max_expanded = min(int(block_count), int(extra_nodes // 2))
    profile = str(topology_profile)
    if profile == "hub_heavy":
        expanded_count = 1
    elif profile == "low_degree":
        expanded_count = max_expanded
    else:
        expanded_count = int(rng.randint(1, max_expanded))
    recipient_indices = list(range(int(block_count)))
    rng.shuffle(recipient_indices)
    recipients = recipient_indices[: int(expanded_count)]
    for index in recipients:
        sizes[int(index)] += 2
    remaining = int(extra_nodes - (2 * expanded_count))
    while int(remaining) > 0:
        recipient = int(rng.choice(recipients))
        sizes[int(recipient)] += 1
        remaining -= 1
    return tuple(int(value) for value in sizes)


def _block_anchor_node(
    block_nodes: Sequence[int],
    *,
    topology_profile: str,
) -> int:
    """Return one anchor node inside a bridgeless block for bridge attachments."""

    nodes = tuple(int(node) for node in block_nodes)
    if not nodes:
        raise ValueError("bridge block anchor selection requires at least one node")
    profile = str(topology_profile)
    if profile == "hub_heavy":
        return int(nodes[0])
    if profile == "low_degree":
        return int(nodes[-1])
    return int(nodes[0])


def _sample_bridge_count_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_count: int,
    topology_profile: str,
) -> nx.Graph:
    """Return one connected graph with the requested number of bridges."""

    node_count_int = int(node_count)
    target_count_int = int(target_count)
    if int(target_count_int) < 0 or int(target_count_int) > max(0, int(node_count_int) - 1):
        raise ValueError("target bridge count is outside feasible bounds")
    if int(target_count_int) == 0:
        return _sample_zero_bridge_graph(
            rng,
            node_count=int(node_count_int),
            topology_profile=str(topology_profile),
        )

    block_sizes = _sample_bridge_block_sizes(
        rng,
        node_count=int(node_count_int),
        target_count=int(target_count_int),
        topology_profile=str(topology_profile),
    )
    block_count = len(block_sizes)
    profile = str(topology_profile)
    if profile == "hub_heavy":
        skeleton = nx.star_graph(int(block_count) - 1)
    elif profile == "low_degree":
        skeleton = nx.path_graph(int(block_count))
    else:
        skeleton = _random_tree_graph(rng, size=int(block_count))

    if profile == "hub_heavy":
        ordered_block_indices = tuple(
            index
            for index, _ in sorted(
                enumerate(block_sizes),
                key=lambda item: (-int(item[1]), int(item[0])),
            )
        )
        skeleton_to_size_index = {int(skeleton_index): int(size_index) for skeleton_index, size_index in enumerate(ordered_block_indices)}
    else:
        skeleton_to_size_index = {int(index): int(index) for index in range(int(block_count))}

    graph = nx.Graph()
    block_nodes_by_skeleton: Dict[int, Tuple[int, ...]] = {}
    anchor_by_skeleton: Dict[int, int] = {}
    next_node = 0
    for skeleton_index in range(int(block_count)):
        size_index = int(skeleton_to_size_index[int(skeleton_index)])
        block_size = int(block_sizes[int(size_index)])
        block_nodes = tuple(range(int(next_node), int(next_node + block_size)))
        next_node += int(block_size)
        graph.add_nodes_from(block_nodes)
        if int(block_size) >= 3:
            cycle_edges = list(zip(block_nodes, block_nodes[1:] + block_nodes[:1]))
            graph.add_edges_from((int(left), int(right)) for left, right in cycle_edges)
            if profile != "low_degree":
                block_subgraph = graph.subgraph(block_nodes).copy()
                complete_edges = (int(block_size) * (int(block_size) - 1)) // 2
                cycle_edge_count = int(block_size)
                max_extra = max(0, min(int(block_size // 2), int(complete_edges - cycle_edge_count)))
                if int(max_extra) > 0:
                    extra_edges = 1 if profile == "hub_heavy" else int(rng.randint(0, max_extra))
                    _add_random_non_edges(block_subgraph, rng, extra_edges=int(min(max_extra, extra_edges)))
                    graph.add_edges_from((int(left), int(right)) for left, right in block_subgraph.edges())
        block_nodes_by_skeleton[int(skeleton_index)] = tuple(int(node) for node in block_nodes)
        anchor_by_skeleton[int(skeleton_index)] = _block_anchor_node(block_nodes, topology_profile=profile)

    for left_block, right_block in skeleton.edges():
        graph.add_edge(int(anchor_by_skeleton[int(left_block)]), int(anchor_by_skeleton[int(right_block)]))

    bridge_edges = tuple(
        sort_graph_edge_labels(
            tuple((str(left), str(right)) for left, right in nx.bridges(graph)),
            directed=False,
        )
    )
    if int(len(bridge_edges)) != int(target_count_int):
        raise ValueError("bridge sampler failed to preserve the requested bridge count")
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


def _build_unlabeled_disconnected_component_graph(
    rng: random.Random,
    *,
    component_sizes: Sequence[int],
    topology_profile: str,
) -> Tuple[nx.Graph, Tuple[Tuple[int, ...], ...]]:
    """Build one unlabeled disconnected graph from explicit component sizes."""

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
    return graph, tuple(component_nodes)


def _build_disconnected_component_graph(
    rng: random.Random,
    *,
    component_sizes: Sequence[int],
    topology_profile: str,
    label_variant: str,
) -> Tuple[GraphTopologySample, Dict[int, str], Tuple[Tuple[int, ...], ...]]:
    """Build one labeled disconnected graph from explicit component sizes."""

    graph, component_nodes = _build_unlabeled_disconnected_component_graph(
        rng,
        component_sizes=component_sizes,
        topology_profile=str(topology_profile),
    )
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


def _undirected_adjacency_by_label_for_graph(
    graph: nx.Graph,
    *,
    label_by_node: Mapping[int, str],
) -> Dict[str, Tuple[str, ...]]:
    """Return sorted label adjacency for one undirected graph."""

    return {
        str(label_by_node[int(node)]): tuple(
            sorted(
                (str(label_by_node[int(neighbor)]) for neighbor in graph.neighbors(int(node))),
                key=graph_label_sort_key,
            )
        )
        for node in sorted((int(node) for node in graph.nodes()))
    }


def _components_by_label_for_graph(
    graph: nx.Graph,
    *,
    label_by_node: Mapping[int, str],
) -> Tuple[Tuple[str, ...], ...]:
    """Return connected components as sorted label tuples."""

    components = [
        tuple(sorted((str(label_by_node[int(node)]) for node in component), key=graph_label_sort_key))
        for component in nx.connected_components(graph)
    ]
    return tuple(
        sorted(
            components,
            key=lambda labels: graph_label_sort_key(labels[0]) if labels else (0, ""),
        )
    )


def _sample_component_size_after_edge_removal_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_component_size: int,
    topology_profile: str,
) -> Tuple[nx.Graph, nx.Graph, Tuple[int, int], int, Tuple[int, ...]]:
    """Build a pre/post graph pair where removing one bridge yields the target component."""

    node_count_int = int(node_count)
    target_size_int = int(target_component_size)
    if int(target_size_int) < 1 or int(target_size_int) >= int(node_count_int):
        raise ValueError("edge-removal target_component_size must be in [1, node_count - 1]")
    other_size = int(node_count_int - target_size_int)
    target_component_index = int(rng.randrange(2))
    component_sizes = [int(other_size), int(other_size)]
    component_sizes[int(target_component_index)] = int(target_size_int)
    component_sizes[1 - int(target_component_index)] = int(other_size)
    base_graph, component_nodes = _build_unlabeled_disconnected_component_graph(
        rng,
        component_sizes=tuple(int(size) for size in component_sizes),
        topology_profile=str(topology_profile),
    )
    target_nodes = tuple(int(node) for node in component_nodes[int(target_component_index)])
    other_nodes = tuple(int(node) for node in component_nodes[1 - int(target_component_index)])
    bridge_left = int(rng.choice(target_nodes))
    bridge_right = int(rng.choice(other_nodes))
    pre_graph = base_graph.copy()
    pre_graph.add_edge(int(bridge_left), int(bridge_right))
    post_graph = base_graph.copy()
    query_node = int(rng.choice(target_nodes))
    return pre_graph, post_graph, (int(bridge_left), int(bridge_right)), int(query_node), tuple(int(node) for node in target_nodes)


def _sample_component_size_after_edge_addition_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_component_size: int,
    topology_profile: str,
) -> Tuple[nx.Graph, nx.Graph, Tuple[int, int], int, Tuple[int, ...]]:
    """Build a pre/post graph pair where adding one edge yields the target component."""

    node_count_int = int(node_count)
    target_size_int = int(target_component_size)
    if int(target_size_int) < 2 or int(target_size_int) > int(node_count_int):
        raise ValueError("edge-addition target_component_size must be in [2, node_count]")
    left_size = int(rng.randint(1, int(target_size_int) - 1))
    right_size = int(target_size_int - left_size)
    component_sizes = [int(left_size), int(right_size)]
    remaining = int(node_count_int - target_size_int)
    if int(remaining) > 0:
        component_sizes.append(int(remaining))
    base_graph, component_nodes = _build_unlabeled_disconnected_component_graph(
        rng,
        component_sizes=tuple(int(size) for size in component_sizes),
        topology_profile=str(topology_profile),
    )
    left_nodes = tuple(int(node) for node in component_nodes[0])
    right_nodes = tuple(int(node) for node in component_nodes[1])
    edit_left = int(rng.choice(left_nodes))
    edit_right = int(rng.choice(right_nodes))
    pre_graph = base_graph.copy()
    post_graph = base_graph.copy()
    post_graph.add_edge(int(edit_left), int(edit_right))
    query_node = int(rng.choice(left_nodes))
    target_nodes = tuple(int(node) for node in (*left_nodes, *right_nodes))
    return pre_graph, post_graph, (int(edit_left), int(edit_right)), int(query_node), tuple(int(node) for node in target_nodes)


def sample_component_size_after_edge_edit_graph(
    rng: random.Random,
    *,
    edit_operation: str,
    node_count: int,
    target_component_size: int,
    topology_profile: str,
    label_variant: str,
) -> GraphComponentAfterEdgeEditSample:
    """Construct one undirected graph with a post-edit component-size witness."""

    operation = str(edit_operation)
    if operation not in SUPPORTED_COMPONENT_EDGE_EDIT_MODES:
        raise ValueError(f"unsupported edit_operation: {edit_operation}")
    if operation == "edge_removal":
        pre_graph, post_graph, edit_edge_nodes, query_node, expected_target_nodes = _sample_component_size_after_edge_removal_graph(
            rng,
            node_count=int(node_count),
            target_component_size=int(target_component_size),
            topology_profile=str(topology_profile),
        )
    else:
        pre_graph, post_graph, edit_edge_nodes, query_node, expected_target_nodes = _sample_component_size_after_edge_addition_graph(
            rng,
            node_count=int(node_count),
            target_component_size=int(target_component_size),
            topology_profile=str(topology_profile),
        )

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=pre_graph,
        directed=False,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    query_label = str(label_by_node[int(query_node)])
    edit_edge = canonicalize_graph_edge_label(
        str(label_by_node[int(edit_edge_nodes[0])]),
        str(label_by_node[int(edit_edge_nodes[1])]),
        directed=False,
    )
    pre_edit_adjacency = _undirected_adjacency_by_label_for_graph(pre_graph, label_by_node=label_by_node)
    post_edit_adjacency = _undirected_adjacency_by_label_for_graph(post_graph, label_by_node=label_by_node)
    pre_components = _components_by_label_for_graph(pre_graph, label_by_node=label_by_node)
    post_components = _components_by_label_for_graph(post_graph, label_by_node=label_by_node)
    expected_target_label_set = {str(label_by_node[int(node)]) for node in expected_target_nodes}
    target_labels = tuple(sorted(expected_target_label_set, key=graph_label_sort_key))
    matching_component = next(
        tuple(str(label) for label in component)
        for component in post_components
        if str(query_label) in {str(label) for label in component}
    )
    if set(str(label) for label in matching_component) != set(str(label) for label in target_labels):
        raise ValueError("edge-edit sampler produced inconsistent post-edit component metadata")
    if int(len(target_labels)) != int(target_component_size):
        raise ValueError("edge-edit sampler produced an unexpected target component size")

    return GraphComponentAfterEdgeEditSample(
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
        query_label=str(query_label),
        edit_edge=(str(edit_edge[0]), str(edit_edge[1])),
        edit_operation=str(operation),
        target_labels=tuple(str(label) for label in target_labels),
        target_component_size=int(target_component_size),
        pre_edit_adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in pre_edit_adjacency.items()},
        post_edit_adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in post_edit_adjacency.items()},
        pre_edit_components_by_label=tuple(tuple(str(label) for label in component) for component in pre_components),
        post_edit_components_by_label=tuple(tuple(str(label) for label in component) for component in post_components),
    )


def _directed_successors_by_label_for_graph(
    graph: nx.DiGraph,
    *,
    label_by_node: Mapping[int, str],
) -> Dict[str, Tuple[str, ...]]:
    """Return sorted directed successor adjacency for one labeled graph."""

    return {
        str(label_by_node[int(node)]): tuple(
            sorted(
                (str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node))),
                key=graph_label_sort_key,
            )
        )
        for node in sorted((int(node) for node in graph.nodes()))
    }


def _directed_predecessors_by_label_for_graph(
    graph: nx.DiGraph,
    *,
    label_by_node: Mapping[int, str],
) -> Dict[str, Tuple[str, ...]]:
    """Return sorted directed predecessor adjacency for one labeled graph."""

    return {
        str(label_by_node[int(node)]): tuple(
            sorted(
                (str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node))),
                key=graph_label_sort_key,
            )
        )
        for node in sorted((int(node) for node in graph.nodes()))
    }


def _reachable_nodes_for_graph(graph: nx.DiGraph, *, source: int) -> Tuple[int, ...]:
    """Return directed nodes reachable from ``source``, including ``source``."""

    successors = _digraph_successor_adjacency_by_node(graph)
    dist_start, _ = bfs_dist_count_by_adjacency(successors, start=int(source))
    return tuple(sorted((int(node) for node in dist_start.keys())))


def _add_reachable_directed_region(
    graph: nx.DiGraph,
    rng: random.Random,
    *,
    ordered_nodes: Sequence[int],
    topology_profile: str,
) -> None:
    """Add a small directed region where the first node reaches all later nodes."""

    nodes = tuple(int(node) for node in ordered_nodes)
    if not nodes:
        return
    graph.add_nodes_from(nodes)
    for index, node in enumerate(nodes[1:], start=1):
        parent = _choose_attachment_parent(
            rng,
            graph=graph.subgraph(nodes[: int(index)]).copy(),
            topology_profile=str(topology_profile),
        )
        graph.add_edge(int(parent), int(node))


def _edge_edit_reachability_pair_is_valid(
    pre_graph: nx.DiGraph,
    post_graph: nx.DiGraph,
    *,
    edit_operation: str,
    edit_edge: Tuple[int, int],
    query_node: int,
    expected_post_nodes: Sequence[int],
) -> bool:
    """Return whether one directed pre/post edit pair preserves the target witness."""

    operation = str(edit_operation)
    edit_source, edit_target = int(edit_edge[0]), int(edit_edge[1])
    if set(int(node) for node in pre_graph.nodes()) != set(int(node) for node in post_graph.nodes()):
        return False
    if _has_reciprocal_edges(pre_graph) or _has_reciprocal_edges(post_graph):
        return False

    pre_edges = {(int(left), int(right)) for left, right in pre_graph.edges()}
    post_edges = {(int(left), int(right)) for left, right in post_graph.edges()}
    edit_edge_set = {(int(edit_source), int(edit_target))}
    if operation == "edge_addition":
        if pre_graph.has_edge(int(edit_source), int(edit_target)) or not post_graph.has_edge(int(edit_source), int(edit_target)):
            return False
        if post_edges != pre_edges | edit_edge_set:
            return False
    elif operation == "edge_removal":
        if not pre_graph.has_edge(int(edit_source), int(edit_target)) or post_graph.has_edge(int(edit_source), int(edit_target)):
            return False
        if pre_edges != post_edges | edit_edge_set:
            return False
    else:
        return False

    expected_set = {int(node) for node in expected_post_nodes}
    post_reachable = set(_reachable_nodes_for_graph(post_graph, source=int(query_node)))
    if post_reachable != expected_set:
        return False
    pre_reachable = set(_reachable_nodes_for_graph(pre_graph, source=int(query_node)))
    return pre_reachable != post_reachable


def _add_reachable_edge_edit_distractor_edges(
    rng: random.Random,
    *,
    pre_graph: nx.DiGraph,
    post_graph: nx.DiGraph,
    edit_operation: str,
    edit_edge: Tuple[int, int],
    query_node: int,
    expected_post_nodes: Sequence[int],
    topology_profile: str,
) -> Tuple[nx.DiGraph, nx.DiGraph]:
    """Add safe directed distractor edges without changing the post-edit witness."""

    operation = str(edit_operation)
    nodes = tuple(sorted((int(node) for node in pre_graph.nodes())))
    candidates = [(int(left), int(right)) for left in nodes for right in nodes if int(left) != int(right)]
    rng.shuffle(candidates)
    extra_budget = _profile_extra_edge_budget(
        node_count=len(nodes),
        topology_profile=str(topology_profile),
        directed=True,
    )
    added = 0
    for source, target in candidates:
        if int(added) >= int(extra_budget):
            break
        if (int(source), int(target)) == (int(edit_edge[0]), int(edit_edge[1])):
            continue
        if operation == "edge_addition":
            if pre_graph.has_edge(int(source), int(target)):
                continue
            candidate_pre = pre_graph.copy()
            candidate_pre.add_edge(int(source), int(target))
            candidate_post = candidate_pre.copy()
            if candidate_post.has_edge(int(edit_edge[0]), int(edit_edge[1])):
                continue
            candidate_post.add_edge(int(edit_edge[0]), int(edit_edge[1]))
        elif operation == "edge_removal":
            if post_graph.has_edge(int(source), int(target)):
                continue
            candidate_post = post_graph.copy()
            candidate_post.add_edge(int(source), int(target))
            candidate_pre = candidate_post.copy()
            if candidate_pre.has_edge(int(edit_edge[0]), int(edit_edge[1])):
                continue
            candidate_pre.add_edge(int(edit_edge[0]), int(edit_edge[1]))
        else:
            raise ValueError(f"unsupported edit_operation: {edit_operation}")
        if not _edge_edit_reachability_pair_is_valid(
            candidate_pre,
            candidate_post,
            edit_operation=str(operation),
            edit_edge=(int(edit_edge[0]), int(edit_edge[1])),
            query_node=int(query_node),
            expected_post_nodes=tuple(int(node) for node in expected_post_nodes),
        ):
            continue
        pre_graph = candidate_pre
        post_graph = candidate_post
        added += 1
    return pre_graph, post_graph


def _sample_reachable_count_after_edge_addition_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_reachable_count: int,
    topology_profile: str,
) -> Tuple[nx.DiGraph, nx.DiGraph, Tuple[int, int], int, Tuple[int, ...]]:
    """Build a pre/post graph pair where adding one arrow yields the target reachability."""

    node_count_int = int(node_count)
    target_count_int = int(target_reachable_count)
    if int(target_count_int) < 2 or int(target_count_int) > int(node_count_int):
        raise ValueError("edge-addition target_reachable_count must be in [2, node_count]")

    pre_count = int(rng.randint(1, int(target_count_int) - 1))
    pre_reachable_nodes = tuple(range(int(pre_count)))
    added_region_nodes = tuple(range(int(pre_count), int(target_count_int)))
    remaining_nodes = tuple(range(int(target_count_int), int(node_count_int)))
    query_node = int(pre_reachable_nodes[0])

    pre_graph = nx.DiGraph()
    pre_graph.add_nodes_from(range(int(node_count_int)))
    _add_reachable_directed_region(
        pre_graph,
        rng,
        ordered_nodes=pre_reachable_nodes,
        topology_profile=str(topology_profile),
    )
    _add_reachable_directed_region(
        pre_graph,
        rng,
        ordered_nodes=added_region_nodes,
        topology_profile=str(topology_profile),
    )
    _add_reachable_directed_region(
        pre_graph,
        rng,
        ordered_nodes=remaining_nodes,
        topology_profile=str(topology_profile),
    )

    edit_edge = (int(rng.choice(pre_reachable_nodes)), int(added_region_nodes[0]))
    post_graph = pre_graph.copy()
    post_graph.add_edge(int(edit_edge[0]), int(edit_edge[1]))
    expected_post_nodes = tuple(range(int(target_count_int)))
    if not _edge_edit_reachability_pair_is_valid(
        pre_graph,
        post_graph,
        edit_operation="edge_addition",
        edit_edge=edit_edge,
        query_node=int(query_node),
        expected_post_nodes=expected_post_nodes,
    ):
        raise ValueError("failed to construct a valid reachable-count edge-addition pair")
    pre_graph, post_graph = _add_reachable_edge_edit_distractor_edges(
        rng,
        pre_graph=pre_graph,
        post_graph=post_graph,
        edit_operation="edge_addition",
        edit_edge=edit_edge,
        query_node=int(query_node),
        expected_post_nodes=expected_post_nodes,
        topology_profile=str(topology_profile),
    )
    return pre_graph, post_graph, edit_edge, int(query_node), tuple(int(node) for node in expected_post_nodes)


def _sample_reachable_count_after_edge_removal_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_reachable_count: int,
    topology_profile: str,
) -> Tuple[nx.DiGraph, nx.DiGraph, Tuple[int, int], int, Tuple[int, ...]]:
    """Build a pre/post graph pair where removing one arrow yields the target reachability."""

    node_count_int = int(node_count)
    target_count_int = int(target_reachable_count)
    if int(target_count_int) < 1 or int(target_count_int) >= int(node_count_int):
        raise ValueError("edge-removal target_reachable_count must be in [1, node_count - 1]")

    detachable_size = int(rng.randint(1, int(node_count_int) - int(target_count_int)))
    target_nodes = tuple(range(int(target_count_int)))
    detachable_nodes = tuple(range(int(target_count_int), int(target_count_int + detachable_size)))
    remaining_nodes = tuple(range(int(target_count_int + detachable_size), int(node_count_int)))
    query_node = int(target_nodes[0])

    post_graph = nx.DiGraph()
    post_graph.add_nodes_from(range(int(node_count_int)))
    _add_reachable_directed_region(
        post_graph,
        rng,
        ordered_nodes=target_nodes,
        topology_profile=str(topology_profile),
    )
    _add_reachable_directed_region(
        post_graph,
        rng,
        ordered_nodes=detachable_nodes,
        topology_profile=str(topology_profile),
    )
    _add_reachable_directed_region(
        post_graph,
        rng,
        ordered_nodes=remaining_nodes,
        topology_profile=str(topology_profile),
    )

    edit_edge = (int(rng.choice(target_nodes)), int(detachable_nodes[0]))
    pre_graph = post_graph.copy()
    pre_graph.add_edge(int(edit_edge[0]), int(edit_edge[1]))
    expected_post_nodes = tuple(int(node) for node in target_nodes)
    if not _edge_edit_reachability_pair_is_valid(
        pre_graph,
        post_graph,
        edit_operation="edge_removal",
        edit_edge=edit_edge,
        query_node=int(query_node),
        expected_post_nodes=expected_post_nodes,
    ):
        raise ValueError("failed to construct a valid reachable-count edge-removal pair")
    pre_graph, post_graph = _add_reachable_edge_edit_distractor_edges(
        rng,
        pre_graph=pre_graph,
        post_graph=post_graph,
        edit_operation="edge_removal",
        edit_edge=edit_edge,
        query_node=int(query_node),
        expected_post_nodes=expected_post_nodes,
        topology_profile=str(topology_profile),
    )
    return pre_graph, post_graph, edit_edge, int(query_node), tuple(int(node) for node in expected_post_nodes)


def sample_reachable_count_after_edge_edit_graph(
    rng: random.Random,
    *,
    edit_operation: str,
    node_count: int,
    target_reachable_count: int,
    topology_profile: str,
    label_variant: str,
) -> GraphReachableAfterEdgeEditSample:
    """Construct one directed graph with a post-edit reachable-count witness."""

    operation = str(edit_operation)
    if operation not in SUPPORTED_REACHABLE_EDGE_EDIT_MODES:
        raise ValueError(f"unsupported edit_operation: {edit_operation}")
    feasible_node_support = feasible_node_counts_for_reachable_count_after_edge_edit(
        edit_operation=str(operation),
        target_reachable_count=int(target_reachable_count),
        node_count_min=int(node_count),
        node_count_max=int(node_count),
    )
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested reachable edge-edit query")

    if operation == "edge_removal":
        pre_graph, post_graph, edit_edge_nodes, query_node, expected_target_nodes = _sample_reachable_count_after_edge_removal_graph(
            rng,
            node_count=int(node_count),
            target_reachable_count=int(target_reachable_count),
            topology_profile=str(topology_profile),
        )
    else:
        pre_graph, post_graph, edit_edge_nodes, query_node, expected_target_nodes = _sample_reachable_count_after_edge_addition_graph(
            rng,
            node_count=int(node_count),
            target_reachable_count=int(target_reachable_count),
            topology_profile=str(topology_profile),
        )

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=pre_graph,
        directed=True,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    query_label = str(label_by_node[int(query_node)])
    edit_edge = canonicalize_graph_edge_label(
        str(label_by_node[int(edit_edge_nodes[0])]),
        str(label_by_node[int(edit_edge_nodes[1])]),
        directed=True,
    )
    pre_edit_successors = _directed_successors_by_label_for_graph(pre_graph, label_by_node=label_by_node)
    post_edit_successors = _directed_successors_by_label_for_graph(post_graph, label_by_node=label_by_node)
    pre_edit_predecessors = _directed_predecessors_by_label_for_graph(pre_graph, label_by_node=label_by_node)
    post_edit_predecessors = _directed_predecessors_by_label_for_graph(post_graph, label_by_node=label_by_node)
    pre_reachable_nodes = _reachable_nodes_for_graph(pre_graph, source=int(query_node))
    post_reachable_nodes = _reachable_nodes_for_graph(post_graph, source=int(query_node))
    expected_target_label_set = {str(label_by_node[int(node)]) for node in expected_target_nodes}
    target_labels = tuple(sorted(expected_target_label_set, key=graph_label_sort_key))
    post_reachable_labels = tuple(
        sorted((str(label_by_node[int(node)]) for node in post_reachable_nodes), key=graph_label_sort_key)
    )
    pre_reachable_labels = tuple(
        sorted((str(label_by_node[int(node)]) for node in pre_reachable_nodes), key=graph_label_sort_key)
    )
    if set(post_reachable_labels) != set(target_labels):
        raise ValueError("reachable edge-edit sampler produced inconsistent post-edit reachable metadata")
    if int(len(target_labels)) != int(target_reachable_count):
        raise ValueError("reachable edge-edit sampler produced an unexpected target reachable count")
    if set(pre_reachable_labels) == set(post_reachable_labels):
        raise ValueError("reachable edge-edit sampler produced a non-changing edit")
    unreachable_labels = tuple(
        sorted(
            (str(label) for label in topology_sample.node_labels if str(label) not in set(target_labels)),
            key=graph_label_sort_key,
        )
    )
    pre_edit_edge_labels = sort_graph_edge_labels(
        tuple((str(label_by_node[int(left)]), str(label_by_node[int(right)])) for left, right in pre_graph.edges()),
        directed=True,
    )
    post_edit_edge_labels = sort_graph_edge_labels(
        tuple((str(label_by_node[int(left)]), str(label_by_node[int(right)])) for left, right in post_graph.edges()),
        directed=True,
    )

    return GraphReachableAfterEdgeEditSample(
        graph=topology_sample.graph,
        directed=True,
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
        query_label=str(query_label),
        edit_edge=(str(edit_edge[0]), str(edit_edge[1])),
        edit_operation=str(operation),
        target_labels=tuple(str(label) for label in target_labels),
        target_reachable_count=int(target_reachable_count),
        unreachable_labels=tuple(str(label) for label in unreachable_labels),
        pre_edit_reachable_labels=tuple(str(label) for label in pre_reachable_labels),
        post_edit_reachable_labels=tuple(str(label) for label in post_reachable_labels),
        pre_edit_successors_by_label={str(key): tuple(str(value) for value in values) for key, values in pre_edit_successors.items()},
        post_edit_successors_by_label={str(key): tuple(str(value) for value in values) for key, values in post_edit_successors.items()},
        pre_edit_predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in pre_edit_predecessors.items()},
        post_edit_predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in post_edit_predecessors.items()},
        pre_edit_edge_labels=tuple((str(left), str(right)) for left, right in pre_edit_edge_labels),
        post_edit_edge_labels=tuple((str(left), str(right)) for left, right in post_edit_edge_labels),
    )


def sample_reachable_count_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_reachable_count: int,
    topology_profile: str,
    label_variant: str,
) -> GraphReachableSample:
    """Construct one directed graph with an exact reachable-count witness set.

    The queried source node is included in the answer/evidence set. Generation
    preserves at least one unreachable node by construction and verifies the
    final directed successor adjacency before returning.
    """

    node_count_int = int(node_count)
    target_count_int = int(target_reachable_count)
    feasible_node_support = feasible_node_counts_for_reachable_count(
        target_reachable_count=int(target_count_int),
        node_count_min=int(node_count_int),
        node_count_max=int(node_count_int),
    )
    if int(node_count_int) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested reachable-count query")

    graph = nx.DiGraph()
    graph.add_nodes_from(range(int(node_count_int)))
    source_node = 0
    reachable_nodes = tuple(range(int(target_count_int)))
    unreachable_nodes = tuple(range(int(target_count_int), int(node_count_int)))
    profile = str(topology_profile)

    for node in reachable_nodes[1:]:
        parent = _choose_attachment_parent(
            rng,
            graph=graph.subgraph(reachable_nodes[: int(node)]).copy(),
            topology_profile=profile,
        )
        graph.add_edge(int(parent), int(node))

    if unreachable_nodes:
        for offset, node in enumerate(unreachable_nodes):
            if int(offset) == 0:
                target = int(rng.choice(reachable_nodes))
                graph.add_edge(int(node), int(target))
                continue
            existing_unreachable = tuple(int(value) for value in unreachable_nodes[: int(offset)])
            target_pool = tuple(int(value) for value in (*reachable_nodes, *existing_unreachable))
            target = int(rng.choice(target_pool))
            if int(target) in reachable_nodes:
                graph.add_edge(int(node), int(target))
            else:
                if bool(rng.randrange(2)):
                    graph.add_edge(int(target), int(node))
                else:
                    graph.add_edge(int(node), int(target))

    candidate_edges = [
        (int(left), int(right))
        for left, right in nx.non_edges(graph)
        if not graph.has_edge(int(right), int(left))
        and not (int(left) in reachable_nodes and int(right) in unreachable_nodes)
    ]
    rng.shuffle(candidate_edges)
    if profile == "hub_heavy":
        extra_edge_budget = min(4, len(candidate_edges))
    elif profile == "balanced":
        extra_edge_budget = min(3, len(candidate_edges))
    else:
        extra_edge_budget = min(2, len(candidate_edges))

    for left, right in candidate_edges:
        if int(extra_edge_budget) <= 0:
            break
        graph.add_edge(int(left), int(right))
        successors = _digraph_successor_adjacency_by_node(graph)
        dist_start, _ = bfs_dist_count_by_adjacency(successors, start=int(source_node))
        reachable_after = {int(node) for node in dist_start.keys()}
        if reachable_after != {int(node) for node in reachable_nodes}:
            graph.remove_edge(int(left), int(right))
            continue
        extra_edge_budget -= 1

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=True,
        topology_profile=profile,
        label_variant=str(label_variant),
    )
    successors_by_label = {
        str(key): tuple(str(value) for value in values)
        for key, values in topology_sample.successors_by_label.items()
    }
    dist_start, _ = bfs_dist_count_by_adjacency(successors_by_label, start=str(label_by_node[int(source_node)]))
    target_labels = tuple(
        sorted((str(label) for label in dist_start.keys()), key=graph_label_sort_key)
    )
    if int(len(target_labels)) != int(target_count_int):
        raise ValueError("reachable-count sampler failed to preserve the requested reachable set")
    unreachable_labels = tuple(
        sorted(
            (str(label_by_node[int(node)]) for node in unreachable_nodes if str(label_by_node[int(node)]) not in set(target_labels)),
            key=graph_label_sort_key,
        )
    )
    reachable_edge_count = sum(
        1
        for left, right in graph.edges()
        if int(left) in reachable_nodes and int(right) in reachable_nodes
    )
    unreachable_edge_count = int(graph.number_of_edges()) - int(reachable_edge_count)
    return GraphReachableSample(
        graph=topology_sample.graph,
        directed=True,
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
        query_label=str(label_by_node[int(source_node)]),
        target_labels=tuple(str(label) for label in target_labels),
        target_reachable_count=int(target_count_int),
        unreachable_labels=tuple(str(label) for label in unreachable_labels),
        reachable_edge_count=int(reachable_edge_count),
        unreachable_edge_count=int(unreachable_edge_count),
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


def sample_shortest_path_length_graph(
    rng: random.Random,
    *,
    query_id: str,
    node_count: int,
    target_shortest_path_length: int,
    topology_profile: str,
    label_variant: str,
) -> GraphShortestPathSample:
    """Construct one connected graph with a unique shortest path of the requested length."""

    feasible_node_support = feasible_node_counts_for_shortest_path_length(
        target_shortest_path_length=int(target_shortest_path_length),
        node_count_min=int(node_count),
        node_count_max=int(node_count),
    )
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested shortest-path query")

    graph_directionality = str(graph_directionality_for_query_id(str(query_id)))
    if graph_directionality == "directed":
        graph, path_nodes, extra_edge_count = _sample_unique_shortest_path_digraph(
            rng,
            node_count=int(node_count),
            target_shortest_path_length=int(target_shortest_path_length),
            topology_profile=str(topology_profile),
        )
    else:
        graph, path_nodes, extra_edge_count = _sample_unique_shortest_path_graph(
            rng,
            node_count=int(node_count),
            target_shortest_path_length=int(target_shortest_path_length),
            topology_profile=str(topology_profile),
        )
    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=bool(graph_directionality == "directed"),
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )

    source_node = int(path_nodes[0])
    goal_node = int(path_nodes[-1])
    source_label = str(label_by_node[int(source_node)])
    goal_label = str(label_by_node[int(goal_node)])
    target_labels = tuple(str(label_by_node[int(node)]) for node in path_nodes)
    return GraphShortestPathSample(
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
        source_label=str(source_label),
        goal_label=str(goal_label),
        target_labels=tuple(str(label) for label in target_labels),
        target_shortest_path_length=int(target_shortest_path_length),
        attachment_count=max(0, int(node_count) - len(path_nodes)),
        extra_edge_count=int(extra_edge_count),
    )


def sample_longest_path_length_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_longest_path_length: int,
    topology_profile: str,
    label_variant: str,
) -> GraphLongestPathSample:
    """Construct one DAG with a unique global longest directed path."""

    feasible_node_support = feasible_node_counts_for_longest_path_length(
        target_longest_path_length=int(target_longest_path_length),
        node_count_min=int(node_count),
        node_count_max=int(node_count),
    )
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested longest-path query")

    graph, path_nodes, attachment_count, extra_edge_count = _sample_unique_longest_path_dag(
        rng,
        node_count=int(node_count),
        target_longest_path_length=int(target_longest_path_length),
        topology_profile=str(topology_profile),
    )
    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=True,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )

    source_node = int(path_nodes[0])
    goal_node = int(path_nodes[-1])
    source_label = str(label_by_node[int(source_node)])
    goal_label = str(label_by_node[int(goal_node)])
    target_labels = tuple(str(label_by_node[int(node)]) for node in path_nodes)
    return GraphLongestPathSample(
        graph=topology_sample.graph,
        directed=True,
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
        source_label=str(source_label),
        goal_label=str(goal_label),
        target_labels=tuple(str(label) for label in target_labels),
        target_longest_path_length=int(target_longest_path_length),
        attachment_count=int(attachment_count),
        extra_edge_count=int(extra_edge_count),
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


def sample_bridge_count_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_count: int,
    topology_profile: str,
    label_variant: str,
) -> GraphBridgeSample:
    """Construct one graph with the requested number of bridge edges."""

    feasible_node_support = feasible_node_counts_for_bridge_count(
        target_count=int(target_count),
        node_count_min=int(node_count),
        node_count_max=int(node_count),
    )
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested bridge query")

    graph = _sample_bridge_count_graph(
        rng,
        node_count=int(node_count),
        target_count=int(target_count),
        topology_profile=str(topology_profile),
    )
    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=False,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    bridge_edges = sort_graph_edge_labels(
        tuple(
            (
                str(label_by_node[int(left)]),
                str(label_by_node[int(right)]),
            )
            for left, right in nx.bridges(graph)
        ),
        directed=False,
    )
    return GraphBridgeSample(
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
        target_edges=tuple((str(left), str(right)) for left, right in bridge_edges),
        target_count=int(target_count),
    )


def _sample_profile_tree_graph(
    rng: random.Random,
    *,
    node_count: int,
    topology_profile: str,
) -> nx.Graph:
    """Return one connected tree whose shape follows the requested profile."""

    node_count_int = int(node_count)
    if int(node_count_int) <= 0:
        raise ValueError("tree sampling requires at least one node")
    graph = nx.Graph()
    graph.add_node(0)
    for next_node in range(1, int(node_count_int)):
        parent = _choose_attachment_parent(
            rng,
            graph=graph,
            topology_profile=str(topology_profile),
        )
        graph.add_node(int(next_node))
        graph.add_edge(int(parent), int(next_node))
    return graph


def _sample_profile_extra_edges(
    rng: random.Random,
    *,
    graph: nx.Graph,
    extra_edge_count: int,
    topology_profile: str,
) -> Tuple[Tuple[int, int], ...]:
    """Add non-tree edges under the requested profile and return them."""

    added_edges: list[Tuple[int, int]] = []
    for _ in range(max(0, int(extra_edge_count))):
        candidates = [(int(left), int(right)) for left, right in nx.non_edges(graph)]
        if not candidates:
            break
        weights = [
            _edge_weight_for_profile(
                graph,
                edge=(int(left), int(right)),
                topology_profile=str(topology_profile),
            )
            for left, right in candidates
        ]
        left, right = rng.choices(candidates, weights=weights, k=1)[0]
        graph.add_edge(int(left), int(right))
        added_edges.append(tuple(sorted((int(left), int(right)))))
    if int(len(added_edges)) != int(extra_edge_count):
        raise ValueError("failed to add the requested number of non-tree edges")
    return tuple(tuple(int(value) for value in edge) for edge in added_edges)


def _assign_unique_mst_weights(
    rng: random.Random,
    *,
    tree_edges: Sequence[Tuple[int, int]],
    extra_edges: Sequence[Tuple[int, int]],
    edge_weight_min: int,
    edge_weight_max: int,
) -> Dict[Tuple[int, int], int]:
    """Assign distinct edge weights that make the tree the unique MST.

    We sample a distinct subset of the allowed integer weights and reserve the
    heaviest sampled weights for the non-tree edges. This guarantees every
    non-tree edge is heavier than every tree edge, so the spanning tree is the
    unique minimum spanning tree by the cycle property.
    """

    tree = [tuple(sorted((int(left), int(right)))) for left, right in tree_edges]
    extras = [tuple(sorted((int(left), int(right)))) for left, right in extra_edges]
    total_edge_count = int(len(tree) + len(extras))
    available_weights = tuple(range(int(edge_weight_min), int(edge_weight_max) + 1))
    if int(total_edge_count) > len(available_weights):
        raise ValueError("not enough distinct edge weights available for weighted MST construction")

    selected_weights = sorted(int(value) for value in rng.sample(available_weights, int(total_edge_count)))
    tree_weights = selected_weights[: len(tree)]
    extra_weights = selected_weights[len(tree) :]
    rng.shuffle(tree_weights)
    rng.shuffle(extra_weights)

    weight_by_edge: Dict[Tuple[int, int], int] = {}
    for edge, weight in zip(tree, tree_weights):
        weight_by_edge[tuple(edge)] = int(weight)
    for edge, weight in zip(extras, extra_weights):
        weight_by_edge[tuple(edge)] = int(weight)
    return weight_by_edge


def sample_minimum_spanning_tree_weight_graph(
    rng: random.Random,
    *,
    node_count: int,
    extra_edge_count: int,
    topology_profile: str,
    label_variant: str,
    edge_weight_min: int,
    edge_weight_max: int,
) -> GraphMinimumSpanningTreeSample:
    """Construct one connected weighted graph with a unique minimum spanning tree."""

    feasible_extra_support = feasible_extra_edge_counts_for_minimum_spanning_tree(
        node_count=int(node_count),
        extra_edge_count_min=int(extra_edge_count),
        extra_edge_count_max=int(extra_edge_count),
        edge_weight_min=int(edge_weight_min),
        edge_weight_max=int(edge_weight_max),
    )
    if int(extra_edge_count) not in feasible_extra_support:
        raise ValueError("extra_edge_count is outside feasible support for the requested MST query")

    tree_graph = _sample_profile_tree_graph(
        rng,
        node_count=int(node_count),
        topology_profile=str(topology_profile),
    )
    tree_edges = [tuple(sorted((int(left), int(right)))) for left, right in tree_graph.edges()]
    graph = tree_graph.copy()
    extra_edges = _sample_profile_extra_edges(
        rng,
        graph=graph,
        extra_edge_count=int(extra_edge_count),
        topology_profile=str(topology_profile),
    )
    weight_by_edge = _assign_unique_mst_weights(
        rng,
        tree_edges=tuple(tree_edges),
        extra_edges=tuple(extra_edges),
        edge_weight_min=int(edge_weight_min),
        edge_weight_max=int(edge_weight_max),
    )
    for left, right in graph.edges():
        graph[int(left)][int(right)]["weight"] = int(weight_by_edge[tuple(sorted((int(left), int(right))))])

    mst_graph = nx.minimum_spanning_tree(graph, weight="weight", algorithm="kruskal")
    mst_edges = sort_graph_edge_labels(
        tuple((str(left), str(right)) for left, right in mst_graph.edges()),
        directed=False,
    )
    tree_edges_canonical = sort_graph_edge_labels(
        tuple((str(left), str(right)) for left, right in tree_edges),
        directed=False,
    )
    if mst_edges != tree_edges_canonical:
        raise ValueError("weighted MST sampler failed to preserve the intended unique spanning tree")

    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=False,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    labeled_weight_by_edge: Dict[Tuple[str, str], int] = {}
    for left, right in graph.edges():
        left_label = str(label_by_node[int(left)])
        right_label = str(label_by_node[int(right)])
        edge_label = canonicalize_graph_edge_label(left_label, right_label, directed=False)
        labeled_weight_by_edge[tuple(edge_label)] = int(graph[int(left)][int(right)]["weight"])

    mst_edge_labels = sort_graph_edge_labels(
        tuple(
            (
                str(label_by_node[int(left)]),
                str(label_by_node[int(right)]),
            )
            for left, right in mst_graph.edges()
        ),
        directed=False,
    )
    target_total_weight = sum(int(labeled_weight_by_edge[tuple(edge)]) for edge in mst_edge_labels)
    return GraphMinimumSpanningTreeSample(
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
        edge_weights_by_label=dict(labeled_weight_by_edge),
        target_edges=tuple((str(left), str(right)) for left, right in mst_edge_labels),
        target_total_weight=int(target_total_weight),
        extra_edge_count=int(extra_edge_count),
    )


def sample_topological_position_graph(
    rng: random.Random,
    *,
    node_count: int,
    target_position: int,
    topology_profile: str,
    label_variant: str,
) -> GraphTopologicalOrderSample:
    """Construct one directed DAG with a unique topological order."""

    feasible_node_support = feasible_node_counts_for_topological_position(
        target_position=int(target_position),
        node_count_min=int(node_count),
        node_count_max=int(node_count),
    )
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested topological-position query")

    graph, order_nodes, extra_edge_count = _sample_unique_topological_order_digraph(
        rng,
        node_count=int(node_count),
        topology_profile=str(topology_profile),
    )
    topology_sample, label_by_node = _build_labeled_graph_topology_sample(
        rng,
        graph=graph,
        directed=True,
        topology_profile=str(topology_profile),
        label_variant=str(label_variant),
    )
    query_node = int(order_nodes[int(target_position) - 1])
    target_labels = tuple(str(label_by_node[int(node)]) for node in order_nodes)
    return GraphTopologicalOrderSample(
        graph=topology_sample.graph,
        directed=True,
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
        target_position=int(target_position),
        extra_edge_count=int(extra_edge_count),
    )


__all__ = [
    "GraphArticulationPointSample",
    "GraphBridgeSample",
    "GraphComponentAfterEdgeEditSample",
    "GraphCommonNeighborSample",
    "GraphComponentSample",
    "GraphCrossColorEdgeCountSample",
    "GraphCountSample",
    "GraphEdgeColorCountSample",
    "GraphEdgeTextLabelCountSample",
    "GraphExtremeDegreeSample",
    "GraphIsolatedAfterNodeRemovalSample",
    "GraphLargestComponentSample",
    "GraphLongestPathSample",
    "GraphMinimumSpanningTreeSample",
    "GraphNamedNodeDegreeSample",
    "GraphNodeColorCountSample",
    "GraphReachableAfterEdgeEditSample",
    "GraphReachableSample",
    "GraphShortestPathSample",
    "GraphSourceSinkSample",
    "GraphTopologicalOrderSample",
    "GraphTopologySample",
    "GraphUniqueCycleSample",
    "GraphUniqueNodeLabelRelationSample",
    "LABEL_POOL_1_20",
    "SUPPORTED_ARTICULATION_QUERY_IDS",
    "SUPPORTED_BRIDGE_QUERY_IDS",
    "SUPPORTED_COMMON_NEIGHBOR_MODES",
    "SUPPORTED_COMPONENT_EDGE_EDIT_MODES",
    "SUPPORTED_COMPONENT_QUERY_IDS",
    "SUPPORTED_COMPONENT_COMPARISON_QUERY_IDS",
    "SUPPORTED_CROSS_COLOR_EDGE_COUNT_DIRECTIONS",
    "SUPPORTED_CYCLE_QUERY_IDS",
    "SUPPORTED_DEGREE_QUERY_IDS",
    "SUPPORTED_DIRECTED_DEGREE_MODES",
    "SUPPORTED_EDGE_COLOR_COUNT_DIRECTIONS",
    "SUPPORTED_EXTREME_DEGREE_DIRECTIONS",
    "SUPPORTED_EXTREME_DEGREE_DIRECTED_MODES",
    "SUPPORTED_EXTREME_DEGREE_EXTREMA",
    "SUPPORTED_ISOLATED_AFTER_NODE_REMOVAL_DIRECTIONS",
    "SUPPORTED_LAYOUT_VARIANTS",
    "SUPPORTED_LABEL_VARIANTS",
    "SUPPORTED_NAMED_NODE_DEGREE_DIRECTIONS",
    "SUPPORTED_NAMED_NODE_DIRECTED_DEGREE_MODES",
    "SUPPORTED_NODE_LINK_LABEL_VARIANTS",
    "SUPPORTED_NODE_COLOR_COUNT_DIRECTIONS",
    "SUPPORTED_LONGEST_PATH_QUERY_IDS",
    "SUPPORTED_SOURCE_SINK_MODES",
    "SUPPORTED_OPTIMIZATION_QUERY_IDS",
    "SUPPORTED_ORDER_QUERY_IDS",
    "SUPPORTED_REACHABLE_EDGE_EDIT_MODES",
    "SUPPORTED_REACHABLE_QUERY_IDS",
    "SUPPORTED_PATH_QUERY_IDS",
    "SUPPORTED_TOPOLOGY_PROFILES",
    "SUPPORTED_UNIQUE_NODE_LABEL_RELATION_MODES",
    "canonicalize_graph_edge_label",
    "feasible_node_counts_for_articulation_point_count",
    "feasible_node_counts_for_bridge_count",
    "feasible_node_counts_for_common_neighbor_count",
    "feasible_node_counts_for_component_query",
    "feasible_node_counts_for_component_size_after_edge_edit",
    "feasible_node_counts_for_degree_count",
    "feasible_node_counts_for_extreme_degree_value",
    "feasible_node_counts_for_isolated_node_count_after_node_removal",
    "feasible_node_counts_for_longest_path_length",
    "feasible_node_counts_for_named_node_degree_value",
    "feasible_node_counts_for_source_sink_count",
    "feasible_extra_edge_counts_for_minimum_spanning_tree",
    "feasible_node_counts_for_reachable_count",
    "feasible_node_counts_for_reachable_count_after_edge_edit",
    "feasible_node_counts_for_shortest_path_length",
    "feasible_node_counts_for_topological_position",
    "feasible_node_counts_for_unique_cycle_size",
    "feasible_node_counts_for_unique_largest_component",
    "graph_degree_mode_for_query_id",
    "graph_directionality_for_query_id",
    "graph_label_sort_key",
    "SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS",
    "sample_edge_attribute_label_graph",
    "sample_edge_attribute_path_label_graph",
    "sample_articulation_point_count_graph",
    "sample_bridge_count_graph",
    "sample_common_neighbor_count_graph",
    "sample_component_size_after_edge_edit_graph",
    "sample_component_count_graph",
    "sample_cross_color_edge_count_graph",
    "sample_degree_count_graph",
    "sample_edge_color_count_graph",
    "sample_edge_text_label_count_graph",
    "sample_extreme_degree_graph",
    "sample_isolated_node_count_after_node_removal_graph",
    "sample_largest_component_size_graph",
    "sample_longest_path_length_graph",
    "sample_minimum_spanning_tree_weight_graph",
    "sample_named_node_degree_graph",
    "sample_node_color_count_graph",
    "sample_source_sink_count_graph",
    "sample_reachable_count_after_edge_edit_graph",
    "sample_reachable_count_graph",
    "sample_shortest_path_length_graph",
    "sample_topological_position_graph",
    "sample_unique_node_label_relation_graph",
    "sort_graph_edge_labels",
    "sample_unique_cycle_graph",
]
