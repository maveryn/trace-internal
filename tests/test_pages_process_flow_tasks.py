"""Behavior tests for pages process-flow diagram tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.pages.process_flow.diagram_tasks import (
    ACTOR_HANDOFF_COUNT_TASK_ID,
    CONDITION_PATH_ENDPOINT_TASK_ID,
    FILTERED_NODE_COUNT_TASK_ID,
    PagesProcessFlowActorHandoffCountTask,
    PagesProcessFlowConditionPathEndpointLabelTask,
    PagesProcessFlowFilteredNodeCountTask,
)


def _assert_bboxes_inside_image(out) -> None:
    width, height = out.image.size
    for bbox in out.evidence_gt.value:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 <= x1 <= float(width)
        assert 0.0 <= y0 <= y1 <= float(height)


def test_pages_process_flow_tasks_are_registered_in_public_taxonomy() -> None:
    for task_id in [FILTERED_NODE_COUNT_TASK_ID, CONDITION_PATH_ENDPOINT_TASK_ID, ACTOR_HANDOFF_COUNT_TASK_ID]:
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "pages"
        assert taxonomy.scene_id == "process_flow"
        assert taxonomy.source_task_group == "process_flow"


def test_pages_process_flow_filtered_node_count_contract() -> None:
    task = PagesProcessFlowFilteredNodeCountTask()
    for query_id in ("shape_node_count", "status_node_count", "role_node_count"):
        out = task.generate(83100, params={"query_id": query_id, "layout_variant": "vertical_swimlane"}, max_attempts=10)
        trace = out.trace_payload
        query = trace["execution_trace"]["query"]
        evidence_ids = [str(item) for item in query["evidence_node_ids"]]
        expected = [trace["render_map"]["node_bboxes_px"][node_id] for node_id in evidence_ids]

        assert out.scene_id == "process_flow"
        assert out.query_id == "default"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == int(query["answer"])
        assert len(out.evidence_gt.value) == int(out.answer_gt.value)
        assert out.evidence_gt.value == expected
        assert sorted(out.prompt_variants) == ["answer_and_evidence", "answer_only"]
        _assert_bboxes_inside_image(out)


def test_pages_process_flow_condition_path_endpoint_contract() -> None:
    task = PagesProcessFlowConditionPathEndpointLabelTask()
    out = task.generate(83120, params={"layout_variant": "horizontal_swimlane"}, max_attempts=10)
    trace = out.trace_payload
    query = trace["execution_trace"]["query"]
    render_map = trace["render_map"]
    expected = []
    for node_id in query["evidence_node_ids"]:
        expected.append(render_map["node_bboxes_px"][str(node_id)])
    for edge_id in query["evidence_edge_label_ids"]:
        expected.append(render_map["edge_label_bboxes_px"][str(edge_id)])

    assert out.scene_id == "process_flow"
    assert out.query_id == "default"
    assert out.query_id == "condition_path_endpoint_label"
    assert out.answer_gt.type == "string"
    assert str(out.answer_gt.value) == str(query["answer"])
    assert out.evidence_gt.value == expected
    assert len(query["condition_labels"]) == 2
    for label in query["condition_labels"]:
        assert f'"{label}"' in out.prompt
    _assert_bboxes_inside_image(out)


def test_pages_process_flow_actor_handoff_count_contract() -> None:
    task = PagesProcessFlowActorHandoffCountTask()
    for query_id in ("all_cross_lane_handoff_count", "lane_outgoing_handoff_count", "lane_involved_handoff_count"):
        out = task.generate(83140, params={"query_id": query_id, "layout_variant": "staggered_columns"}, max_attempts=10)
        trace = out.trace_payload
        query = trace["execution_trace"]["query"]
        evidence_ids = [str(item) for item in query["evidence_edge_ids"]]
        expected = [trace["render_map"]["edge_bboxes_px"][edge_id] for edge_id in evidence_ids]

        assert out.scene_id == "process_flow"
        assert out.query_id == "default"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == int(query["answer"])
        assert len(out.evidence_gt.value) == int(out.answer_gt.value)
        assert out.evidence_gt.value == expected
        _assert_bboxes_inside_image(out)


def test_pages_process_flow_generation_is_deterministic() -> None:
    task = PagesProcessFlowConditionPathEndpointLabelTask()
    params = {"layout_variant": "compact_rows", "style_variant": "warm_memo"}
    out_a = task.generate(83180, params=params, max_attempts=10)
    out_b = task.generate(83180, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_process_flow_sampling_covers_visual_and_text_axes() -> None:
    task = PagesProcessFlowFilteredNodeCountTask()
    layouts: Counter[str] = Counter()
    styles: Counter[str] = Counter()
    contexts: Counter[str] = Counter()
    queries: Counter[str] = Counter()

    for index in range(24):
        out = task.generate(hash64(83220, "process_flow_axes", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        layouts[str(execution["layout_variant"])] += 1
        styles[str(execution["style_variant"])] += 1
        contexts[str(execution["context_id"])] += 1
        queries[str(execution["query_id"])] += 1

    assert set(layouts) == {"vertical_swimlane", "horizontal_swimlane", "staggered_columns", "compact_rows"}
    assert set(styles) == {"blueprint", "pastel_cards", "graphite", "warm_memo"}
    assert len(contexts) >= 5
    assert set(queries) == {"shape_node_count", "status_node_count", "role_node_count"}
