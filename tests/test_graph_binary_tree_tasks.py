"""Behavior tests for graph binary-tree diagram tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.graph.counting.binary_tree_node_count import GraphCountingBinaryTreeNodeCountTask
from trace.tasks.graph.order.binary_tree_traversal_label import GraphOrderBinaryTreeTraversalLabelTask
from trace.tasks.graph.relation.binary_tree_node_label import GraphRelationBinaryTreeNodeLabelTask
from trace.tasks.graph.relation.search_tree_operation_label import GraphRelationSearchTreeOperationLabelTask


def _binary_tree_nodes(trace_payload: dict) -> list[dict]:
    return [
        entity
        for entity in trace_payload["scene_ir"]["entities"]
        if entity["entity_kind"] == "binary_tree_node"
    ]


def _binary_tree_edges(trace_payload: dict) -> list[dict]:
    return [
        entity
        for entity in trace_payload["scene_ir"]["entities"]
        if entity["entity_kind"] == "binary_tree_edge"
    ]


def test_graph_counting_binary_tree_node_count_contracts() -> None:
    task = GraphCountingBinaryTreeNodeCountTask()
    cases = (
        ("leaf_node_count", 4, None),
        ("internal_node_count", 5, None),
        ("single_child_node_count", 3, None),
        ("two_child_node_count", 3, None),
        ("depth_level_node_count", 2, 3),
    )

    assert "task_graph__binary_tree__node_property_count" in TASK_REGISTRY
    for offset, (query_id, target_count, target_depth) in enumerate(cases):
        params = {
            "query_id": query_id,
            "target_count": target_count,
            "label_variant": "letters",
            "scene_variant": "classic_tree",
        }
        if target_depth is not None:
            params["target_depth"] = target_depth
        out = task.generate(23000 + offset, params=params, max_attempts=300)
        trace = out.trace_payload
        nodes = _binary_tree_nodes(trace)
        edges = _binary_tree_edges(trace)

        assert out.scene_id == "binary_tree"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == target_count
        assert len(out.evidence_gt.value) == target_count
        assert trace["scene_ir"]["scene_kind"] == "binary_tree"
        assert trace["execution_trace"]["query_id"] == "default"
        assert trace["execution_trace"]["query_id"] == query_id
        assert trace["execution_trace"]["internal_query_id"] == query_id
        assert len(nodes) == int(trace["execution_trace"]["node_count"])
        assert len(edges) == len(nodes) - 1
        assert any(node["left_label"] is not None or node["right_label"] is not None for node in nodes)
        assert trace["projected_evidence"]["type"] == "bbox_set"
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
        assert "[x0,y0,x1,y1]" in out.prompt_variants["answer_and_evidence"]


def test_graph_order_binary_tree_traversal_label_contracts() -> None:
    task = GraphOrderBinaryTreeTraversalLabelTask()
    traversal_keys = {
        "preorder_kth_node_label": "preorder_labels",
        "inorder_kth_node_label": "inorder_labels",
        "postorder_kth_node_label": "postorder_labels",
        "level_order_kth_node_label": "level_order_labels",
    }

    assert "task_graph__binary_tree__traversal_kth_label" in TASK_REGISTRY
    for offset, (query_id, traversal_key) in enumerate(traversal_keys.items()):
        out = task.generate(
            23100 + offset,
            params={
                "query_id": query_id,
                "traversal_position": 4,
                "label_variant": "letters",
                "scene_variant": "paper_tree",
            },
            max_attempts=300,
        )
        trace = out.trace_payload
        nodes = _binary_tree_nodes(trace)
        edges = _binary_tree_edges(trace)
        traversal_labels = trace["scene_ir"]["relations"][traversal_key]

        assert out.scene_id == "binary_tree"
        assert out.query_id == query_id
        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_sequence"
        assert str(out.answer_gt.value) == str(traversal_labels[3])
        assert len(out.evidence_gt.value) == 4
        assert len(nodes) == int(trace["execution_trace"]["node_count"])
        assert len(edges) == len(nodes) - 1
        assert trace["projected_evidence"]["type"] == "bbox_sequence"
        assert trace["projected_evidence"]["bbox_sequence"] == out.evidence_gt.value
        assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
        assert "ordered JSON array" in out.prompt_variants["answer_and_evidence"]


def test_graph_relation_binary_tree_node_label_contracts() -> None:
    task = GraphRelationBinaryTreeNodeLabelTask()
    query_ids = (
        "parent_label",
        "left_child_label",
        "right_child_label",
        "sibling_label",
        "lowest_common_ancestor_label",
    )

    assert "task_graph__binary_tree__node_relation_label" in TASK_REGISTRY
    for offset, query_id in enumerate(query_ids):
        out = task.generate(
            23200 + offset,
            params={
                "query_id": query_id,
                "label_variant": "letters",
                "scene_variant": "boxed_tree",
            },
            max_attempts=300,
        )
        trace = out.trace_payload
        nodes = _binary_tree_nodes(trace)
        edges = _binary_tree_edges(trace)
        execution = trace["execution_trace"]

        assert out.scene_id == "binary_tree"
        assert out.query_id == query_id
        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_set"
        assert str(out.answer_gt.value) == str(execution["answer_label"])
        assert len(out.evidence_gt.value) == (3 if query_id == "lowest_common_ancestor_label" else 2)
        assert len(nodes) == int(execution["node_count"])
        assert len(edges) == len(nodes) - 1
        assert trace["projected_evidence"]["type"] == "bbox_set"
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert sum(1 for node in nodes if node["is_answer_node"]) == 1
        assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
        assert "[x0,y0,x1,y1]" in out.prompt_variants["answer_and_evidence"]


def test_graph_relation_search_tree_operation_label_contracts() -> None:
    task = GraphRelationSearchTreeOperationLabelTask()
    query_ids = (
        "bst_search_terminal_label",
        "bst_insert_parent_label",
        "heap_property_violation_label",
    )

    assert "task_graph__binary_tree__tree_operation_label" in TASK_REGISTRY
    for offset, query_id in enumerate(query_ids):
        out = task.generate(
            23300 + offset,
            params={
                "query_id": query_id,
                "node_count": 9,
                "scene_variant": "classic_tree",
            },
            max_attempts=300,
        )
        trace = out.trace_payload
        nodes = _binary_tree_nodes(trace)
        edges = _binary_tree_edges(trace)
        execution = trace["execution_trace"]

        assert out.scene_id == "binary_tree"
        assert out.query_id == query_id
        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_sequence"
        assert str(out.answer_gt.value) == str(execution["answer_label"])
        assert len(out.evidence_gt.value) >= 2
        assert len(nodes) == int(execution["node_count"])
        assert len(edges) == len(nodes) - 1
        assert trace["scene_ir"]["scene_kind"] == "search_tree_operation_diagram"
        assert trace["projected_evidence"]["type"] == "bbox_sequence"
        assert trace["projected_evidence"]["bbox_sequence"] == out.evidence_gt.value
        assert sum(1 for node in nodes if node["is_answer_node"]) == 1
        if query_id.startswith("bst_"):
            assert execution["target_key"] is not None
        else:
            assert execution["target_key"] is None
            assert len(out.evidence_gt.value) == 2
        assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
        assert "ordered JSON array" in out.prompt_variants["answer_and_evidence"]
