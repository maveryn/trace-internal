"""Behavior tests for graph adjacency-representation tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.graph.counting.adjacency_component_count import GraphCountingAdjacencyComponentCountTask
from trace.tasks.graph.optimization.adjacency_matrix_mst_weight import GraphOptimizationAdjacencyMatrixMSTWeightTask
from trace.tasks.graph.order.adjacency_traversal_label import GraphOrderAdjacencyTraversalLabelTask


def _assert_bbox_in_image(bbox: list[float], size: tuple[int, int]) -> None:
    width, height = size
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def test_graph_order_adjacency_traversal_label_contracts() -> None:
    task = GraphOrderAdjacencyTraversalLabelTask()

    assert "task_graph__adjacency__traversal_kth_label" in TASK_REGISTRY
    for offset, query_id in enumerate(("bfs_kth_visit_label", "dfs_kth_visit_label")):
        out = task.generate(
            41100 + offset,
            params={
                "query_id": query_id,
                "node_count": 6,
                "traversal_position": 4,
                "label_variant": "letters",
            },
            max_attempts=100,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == "adjacency"
        assert out.query_id == query_id
        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_sequence"
        assert str(out.answer_gt.value) == str(execution["visit_order"][3])
        assert len(out.evidence_gt.value) == 4
        assert trace["projected_evidence"]["bbox_sequence"] == out.evidence_gt.value
        assert trace["scene_ir"]["relations"]["representation_variant"] == "adjacency_list_panel"
        assert len(trace["scene_ir"]["relations"]["adjacency"]) == 6
        for bbox in out.evidence_gt.value:
            _assert_bbox_in_image(bbox, out.image.size)
        assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
        assert "ordered JSON array" in out.prompt_variants["answer_and_evidence"]


def test_graph_counting_adjacency_component_count_contracts() -> None:
    task = GraphCountingAdjacencyComponentCountTask()
    cases = (
        ("undirected_component_count", "adjacency_list_panel"),
        ("directed_strong_component_count", "adjacency_matrix_panel"),
    )

    assert "task_graph__adjacency__component_count" in TASK_REGISTRY
    for offset, (query_id, scene_variant) in enumerate(cases):
        out = task.generate(
            41200 + offset,
            params={
                "query_id": query_id,
                "scene_variant": scene_variant,
                "node_count": 8,
                "component_count": 3,
                "label_variant": "letters",
            },
            max_attempts=100,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == "adjacency"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == 3
        assert len(out.evidence_gt.value) == 3
        assert len(execution["components"]) == 3
        assert len(execution["component_representatives"]) == 3
        assert execution["representation_variant"] == scene_variant
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        prompt_line = str(out.prompt).splitlines()[0].lower()
        if scene_variant == "adjacency_matrix_panel":
            assert "adjacency matrix" in prompt_line
            assert "adjacency list or adjacency matrix" not in prompt_line
        else:
            assert "adjacency list" in prompt_line
            assert "adjacency list or adjacency matrix" not in prompt_line
        for bbox in out.evidence_gt.value:
            _assert_bbox_in_image(bbox, out.image.size)
        assert "one row label from each counted component" in out.prompt_variants["answer_and_evidence"]


def test_graph_optimization_adjacency_matrix_mst_weight_contracts() -> None:
    task = GraphOptimizationAdjacencyMatrixMSTWeightTask()

    assert "task_graph__adjacency__mst_weight" in TASK_REGISTRY
    out = task.generate(
        41300,
        params={
            "query_id": "weighted_matrix_mst_weight",
            "node_count": 5,
            "extra_edge_count": 2,
            "edge_weight_min": 1,
            "edge_weight_max": 12,
            "label_variant": "letters",
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    relation_edges = {tuple(edge) for edge in trace["scene_ir"]["relations"]["minimum_spanning_tree_edges"]}
    weights = {
        tuple(entry["edge"]): int(entry["weight"])
        for entry in trace["scene_ir"]["relations"]["weights"]
    }

    assert out.scene_id == "adjacency"
    assert out.query_id == "weighted_matrix_mst_weight"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert execution["representation_variant"] == "adjacency_matrix_panel"
    assert len(out.evidence_gt.value) == int(execution["node_count"]) - 1
    assert int(out.answer_gt.value) == sum(weights[edge] for edge in relation_edges)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    for bbox in out.evidence_gt.value:
        _assert_bbox_in_image(bbox, out.image.size)
    assert "matrix cell" in out.prompt_variants["answer_and_evidence"]
