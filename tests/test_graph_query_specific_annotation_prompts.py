"""Regression tests for query-specific graph annotation instructions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from trace.tasks.graph.comparison.extreme_degree_value import (
    GraphComparisonExtremeDegreeValueTask,
)
from trace.tasks.graph.counting.adjacency_component_count import (
    GraphCountingAdjacencyComponentCountTask,
)
from trace.tasks.graph.counting.binary_tree_node_count import (
    GraphCountingBinaryTreeChildStructureNodeCountTask,
)
from trace.tasks.graph.counting.cross_color_edge_count import (
    GraphCountingCrossColorEdgeCountTask,
)
from trace.tasks.graph.counting.degree_count import GraphCountingDegreeValueFilterCountTask
from trace.tasks.graph.counting.named_node_degree_value import (
    GraphCountingNamedNodeDegreeValueTask,
)
from trace.tasks.graph.counting.node_count_after_degree_filter import (
    GraphCountingNodeCountAfterDegreeFilterTask,
)
from trace.tasks.graph.counting.source_sink_count import (
    GraphCountingSourceSinkCountTask,
)
from trace.tasks.graph.order.adjacency_traversal_label import (
    GraphOrderAdjacencyTraversalLabelTask,
)
from trace.tasks.graph.order.binary_tree_traversal_label import (
    GraphOrderBinaryTreeTraversalLabelTask,
)
from trace.tasks.graph.path.shortest_path_length import GraphPathShortestPathLengthTask
from trace.tasks.graph.automaton.state_after_input_label import (
    GraphRelationAutomatonStateSimulationLabelTask,
)
from trace.tasks.graph.automaton.nfa_accepted_string_label import (
    GraphRelationAutomatonNfaAcceptedStringLabelTask,
)
from trace.tasks.graph.relation.binary_tree_node_label import (
    GraphRelationBinaryTreeLowestCommonAncestorLabelTask,
)
from trace.tasks.graph.relation.component_size_after_edge_edit import (
    GraphRelationComponentSizeAfterEdgeEditTask,
)
from trace.tasks.graph.relation.edge_attribute_label import (
    GraphRelationShortestPathFirstEdgeLabelTask,
)
from trace.tasks.graph.relation.reachable_count_after_edge_edit import (
    GraphRelationReachableCountAfterEdgeEditTask,
)
from trace.tasks.graph.relation.search_tree_operation_label import (
    GraphRelationBstPathOperationLabelTask,
)
from trace.tasks.graph.relation.unique_node_label import (
    GraphRelationUniqueNodeLabelTask,
)

FORBIDDEN_GENERIC_ANNOTATION_PHRASES = (
    "requested degree condition",
    "requested source or sink condition",
    "hypothetical arrow edit",
    "queried edge or arrow",
    "visited search or insertion path",
    "hypothetical edge edit",
    "queried extreme degree value",
    "source or sink",
    "common-neighbor, common-successor, or common-predecessor",
)


def _annotation_sentence(prompt: str) -> str:
    marker = "Annotation format: "
    assert marker in str(prompt)
    return str(prompt).split(marker, 1)[1].split("\n", 1)[0]


@pytest.mark.parametrize(
    ("task_cls", "seed", "params", "expected_phrases"),
    [
        (
            GraphCountingDegreeValueFilterCountTask,
            30101,
            {
                "query_id": "degree_count",
                "query_degree": 2,
                "target_count": 1,
                "node_count": 6,
            },
            ("nodes with degree 2",),
        ),
        (
            GraphCountingDegreeValueFilterCountTask,
            30102,
            {
                "query_id": "directed_degree_count",
                "degree_mode": "in_degree",
                "query_degree": 1,
                "target_count": 1,
                "node_count": 6,
            },
            ("nodes with in-degree 1",),
        ),
        (
            GraphCountingDegreeValueFilterCountTask,
            30103,
            {
                "query_id": "directed_degree_count",
                "degree_mode": "out_degree",
                "query_degree": 1,
                "target_count": 1,
                "node_count": 6,
            },
            ("nodes with out-degree 1",),
        ),
        (
            GraphCountingSourceSinkCountTask,
            30104,
            {"source_sink_mode": "source", "target_count": 1, "node_count": 6},
            ("source nodes", "no incoming arrows"),
        ),
        (
            GraphCountingSourceSinkCountTask,
            30105,
            {"source_sink_mode": "sink", "target_count": 1, "node_count": 6},
            ("sink nodes", "no outgoing arrows"),
        ),
        (
            GraphCountingNodeCountAfterDegreeFilterTask,
            30106,
            {
                "graph_directionality": "directed",
                "degree_mode": "in_degree",
                "target_count": 4,
                "node_count": 7,
            },
            ("removing every node with in-degree 1",),
        ),
        (
            GraphCountingNodeCountAfterDegreeFilterTask,
            30107,
            {
                "graph_directionality": "directed",
                "degree_mode": "out_degree",
                "target_count": 4,
                "node_count": 7,
            },
            ("removing every node with out-degree 1",),
        ),
        (
            GraphCountingCrossColorEdgeCountTask,
            30108,
            {"graph_directionality": "directed", "target_count": 1, "node_count": 8},
            ("every arrow from", "source_x"),
        ),
        (
            GraphCountingNamedNodeDegreeValueTask,
            30109,
            {
                "graph_directionality": "directed",
                "degree_mode": "in_degree",
                "target_degree": 1,
                "node_count": 6,
            },
            ("every arrow pointing into node",),
        ),
        (
            GraphCountingAdjacencyComponentCountTask,
            30110,
            {
                "query_id": "directed_strong_component_count",
                "component_count": 2,
                "node_count": 6,
            },
            ("strongly connected component",),
        ),
        (
            GraphCountingBinaryTreeChildStructureNodeCountTask,
            30111,
            {"query_id": "leaf_node_count", "target_count": 3},
            ("every leaf node",),
        ),
        (
            GraphComparisonExtremeDegreeValueTask,
            30112,
            {
                "graph_directionality": "directed",
                "degree_mode": "out_degree",
                "extremum_mode": "max",
                "target_degree": 2,
                "node_count": 7,
            },
            ("maximum out-degree value",),
        ),
        (
            GraphPathShortestPathLengthTask,
            30113,
            {
                "query_id": "directed_shortest_path_length",
                "target_shortest_path_length": 3,
                "node_count": 7,
            },
            ("following arrow directions",),
        ),
        (
            GraphOrderAdjacencyTraversalLabelTask,
            30114,
            {
                "query_id": "bfs_kth_visit_label",
                "traversal_position": 3,
                "node_count": 6,
            },
            ("breadth-first search",),
        ),
        (
            GraphOrderBinaryTreeTraversalLabelTask,
            30115,
            {"query_id": "postorder_kth_node_label", "traversal_position": 3},
            ("postorder traversal",),
        ),
        (
            GraphRelationReachableCountAfterEdgeEditTask,
            30116,
            {
                "edge_edit_operation": "edge_addition",
                "target_reachable_count": 3,
                "node_count": 7,
            },
            ("after adding an arrow",),
        ),
        (
            GraphRelationComponentSizeAfterEdgeEditTask,
            30117,
            {
                "edge_edit_operation": "edge_removal",
                "target_component_size": 3,
                "node_count": 7,
            },
            ("after removing the edge",),
        ),
        (
            GraphRelationShortestPathFirstEdgeLabelTask,
            30118,
            {
                "query_id": "shortest_path_first_edge_label",
                "target_shortest_path_length": 2,
                "node_count": 6,
            },
            ("first", "unique shortest path"),
        ),
        (
            GraphRelationUniqueNodeLabelTask,
            30119,
            {"query_id": "unique_predecessor_label", "node_count": 6},
            ("arrow pointing into",),
        ),
        (
            GraphRelationBstPathOperationLabelTask,
            30120,
            {"query_id": "bst_insert_parent_label", "node_count": 7},
            ("visited insertion path", "new key would attach"),
        ),
        (
            GraphRelationAutomatonStateSimulationLabelTask,
            30121,
            {"query_id": "transition_step_state_label"},
            ("through transition step",),
        ),
        (
            GraphRelationAutomatonNfaAcceptedStringLabelTask,
            30122,
            {"query_id": "nfa_accepted_string_label"},
            ("accepting NFA path",),
        ),
        (
            GraphRelationBinaryTreeLowestCommonAncestorLabelTask,
            30123,
            {"query_id": "lowest_common_ancestor_label"},
            ("node_a", "node_b", "lowest_common_ancestor"),
        ),
    ],
)
def test_graph_annotation_prompt_matches_query_branch(
    task_cls: type,
    seed: int,
    params: Mapping[str, Any],
    expected_phrases: tuple[str, ...],
) -> None:
    task = task_cls()
    out = task.generate(seed, params=dict(params), max_attempts=300)

    sentence = _annotation_sentence(out.prompt_variants["answer_and_annotation"])
    sentence_lower = sentence.lower()
    for phrase in expected_phrases:
        assert phrase.lower() in sentence_lower
    for phrase in FORBIDDEN_GENERIC_ANNOTATION_PHRASES:
        assert phrase not in sentence_lower
