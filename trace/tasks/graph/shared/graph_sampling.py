"""Compatibility facade for graph-domain sampling helpers.

Implementation lives in family-specific modules in this package. Keep this
module as the stable import surface for graph tasks and tests.
"""

from __future__ import annotations

from .graph_bridge_articulation_sampling import *  # noqa: F403
from .graph_common_neighbor_sampling import *  # noqa: F403
from .graph_component_sampling import *  # noqa: F403
from .graph_degree_sampling import *  # noqa: F403
from .graph_edge_path_label_sampling import *  # noqa: F403
from .graph_edge_sampling import *  # noqa: F403
from .graph_feasibility import *  # noqa: F403
from .graph_isolation_sampling import *  # noqa: F403
from .graph_label_color_sampling import *  # noqa: F403
from .graph_mst_sampling import *  # noqa: F403
from .graph_node_degree_sampling import *  # noqa: F403
from .graph_path_order_sampling import *  # noqa: F403
from .graph_reachability_sampling import *  # noqa: F403
from .graph_sample_types import *  # noqa: F403
from .graph_source_sink_sampling import *  # noqa: F403
from .graph_profile_sampling import (
    _choose_attachment_parent,
    _edge_weight_for_profile,
    _sample_profile_extra_edges,
    _sample_profile_tree_graph,
)
from .graph_topology_helpers import (
    _build_labeled_graph_topology_sample,
    _has_reciprocal_edges,
)
from .label_assets import LABEL_POOL_1_20


__all__ = [
    'GraphArticulationPointSample',
    'GraphBridgeSample',
    'GraphComponentAfterEdgeEditSample',
    'GraphCommonNeighborSample',
    'GraphComponentSample',
    'GraphCrossColorEdgeCountSample',
    'GraphCountSample',
    'GraphEdgeColorCountSample',
    'GraphEdgeTextLabelCountSample',
    'GraphExtremeDegreeSample',
    'GraphHamiltonianCycleNeighborSample',
    'GraphIsolatedAfterNodeRemovalSample',
    'GraphLargestComponentSample',
    'GraphLargestChordlessCycleSample',
    'GraphLongestPathSample',
    'GraphMinimumSpanningTreeSample',
    'GraphNamedNodeDegreeSample',
    'GraphNodeColorCountSample',
    'GraphReachableAfterEdgeEditSample',
    'GraphReachableSample',
    'GraphShortestPathSample',
    'GraphSourceSinkSample',
    'GraphTopologicalOrderSample',
    'GraphTopologySample',
    'GraphUniqueCycleSample',
    'GraphUniqueNodeLabelRelationSample',
    'LABEL_POOL_1_20',
    'SUPPORTED_ARTICULATION_QUERY_IDS',
    'SUPPORTED_BRIDGE_QUERY_IDS',
    'SUPPORTED_CHORDLESS_CYCLE_QUERY_IDS',
    'SUPPORTED_COMMON_NEIGHBOR_MODES',
    'SUPPORTED_COMPONENT_EDGE_EDIT_MODES',
    'SUPPORTED_COMPONENT_QUERY_IDS',
    'SUPPORTED_COMPONENT_COMPARISON_QUERY_IDS',
    'SUPPORTED_CROSS_COLOR_EDGE_COUNT_DIRECTIONS',
    'SUPPORTED_CYCLE_QUERY_IDS',
    'SUPPORTED_DEGREE_QUERY_IDS',
    'SUPPORTED_DIRECTED_DEGREE_MODES',
    'SUPPORTED_EDGE_COLOR_COUNT_DIRECTIONS',
    'SUPPORTED_EXTREME_DEGREE_DIRECTIONS',
    'SUPPORTED_EXTREME_DEGREE_DIRECTED_MODES',
    'SUPPORTED_EXTREME_DEGREE_EXTREMA',
    'SUPPORTED_HAMILTONIAN_CYCLE_QUERY_IDS',
    'SUPPORTED_ISOLATED_AFTER_NODE_REMOVAL_DIRECTIONS',
    'SUPPORTED_LAYOUT_VARIANTS',
    'SUPPORTED_LABEL_VARIANTS',
    'SUPPORTED_NAMED_NODE_DEGREE_DIRECTIONS',
    'SUPPORTED_NAMED_NODE_DIRECTED_DEGREE_MODES',
    'SUPPORTED_NODE_LINK_LABEL_VARIANTS',
    'SUPPORTED_NODE_COLOR_COUNT_DIRECTIONS',
    'SUPPORTED_LONGEST_PATH_QUERY_IDS',
    'SUPPORTED_SOURCE_SINK_MODES',
    'SUPPORTED_OPTIMIZATION_QUERY_IDS',
    'SUPPORTED_ORDER_QUERY_IDS',
    'SUPPORTED_REACHABLE_EDGE_EDIT_MODES',
    'SUPPORTED_REACHABLE_QUERY_IDS',
    'SUPPORTED_PATH_QUERY_IDS',
    'SUPPORTED_TOPOLOGY_PROFILES',
    'SUPPORTED_UNIQUE_NODE_LABEL_RELATION_MODES',
    'canonicalize_graph_edge_label',
    'feasible_node_counts_for_articulation_point_count',
    'feasible_node_counts_for_bridge_count',
    'feasible_node_counts_for_common_neighbor_count',
    'feasible_node_counts_for_component_query',
    'feasible_node_counts_for_component_size_after_edge_edit',
    'feasible_node_counts_for_degree_count',
    'feasible_node_counts_for_extreme_degree_value',
    'feasible_node_counts_for_hamiltonian_cycle_neighbor',
    'feasible_node_counts_for_isolated_node_count_after_node_removal',
    'feasible_node_counts_for_largest_chordless_cycle_size',
    'feasible_node_counts_for_longest_path_length',
    'feasible_node_counts_for_named_node_degree_value',
    'feasible_node_counts_for_source_sink_count',
    'feasible_extra_edge_counts_for_minimum_spanning_tree',
    'feasible_node_counts_for_reachable_count',
    'feasible_node_counts_for_reachable_count_after_edge_edit',
    'feasible_node_counts_for_shortest_path_length',
    'feasible_node_counts_for_topological_position',
    'feasible_node_counts_for_unique_cycle_size',
    'feasible_node_counts_for_unique_largest_component',
    'graph_degree_mode_for_query_id',
    'graph_directionality_for_query_id',
    'graph_label_sort_key',
    'SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS',
    'sample_edge_attribute_label_graph',
    'sample_edge_attribute_path_label_graph',
    'sample_articulation_point_count_graph',
    'sample_bridge_count_graph',
    'sample_common_neighbor_count_graph',
    'sample_component_size_after_edge_edit_graph',
    'sample_component_count_graph',
    'sample_cross_color_edge_count_graph',
    'sample_degree_count_graph',
    'sample_edge_color_count_graph',
    'sample_edge_text_label_count_graph',
    'sample_extreme_degree_graph',
    'sample_hamiltonian_cycle_neighbor_graph',
    'sample_isolated_node_count_after_node_removal_graph',
    'sample_largest_chordless_cycle_graph',
    'sample_largest_component_size_graph',
    'sample_longest_path_length_graph',
    'sample_minimum_spanning_tree_weight_graph',
    'sample_named_node_degree_graph',
    'sample_node_color_count_graph',
    'sample_source_sink_count_graph',
    'sample_reachable_count_after_edge_edit_graph',
    'sample_reachable_count_graph',
    'sample_shortest_path_length_graph',
    'sample_topological_position_graph',
    'sample_unique_node_label_relation_graph',
    'sort_graph_edge_labels',
    'sample_unique_cycle_graph',
]
