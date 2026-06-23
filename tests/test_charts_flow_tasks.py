"""Behavior tests for standard Sankey chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import assert_counter_support_within, extract_prompt_json_example
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import hash64
from trace.tasks.charts.sankey.node_side_total_value import (
    SOURCE_OUTGOING_QUERY_ID,
    TARGET_INCOMING_QUERY_ID,
    SUPPORTED_QUERY_IDS as NODE_SIDE_QUERY_IDS,
    ChartsFlowSankeyNodeSideTotalValuePublicTask,
)
from trace.tasks.charts.sankey.path_bottleneck_value import ChartsFlowSankeyPathBottleneckValuePublicTask
from trace.tasks.charts.sankey.path_flow_difference import ChartsFlowSankeyPathFlowDifferencePublicTask
from trace.tasks.charts.sankey.source_to_target_total_flow import ChartsFlowSankeySourceToTargetTotalFlowPublicTask
from trace.tasks.registry import list_default_task_ids


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_source_target_total(execution: dict) -> int:
    return sum(min(int(path["first_value"]), int(path["second_value"])) for path in execution["query_path_details"])


def _expected_bottleneck(execution: dict) -> int:
    assert len(execution["query_path_details"]) == 1
    path = dict(execution["query_path_details"][0])
    return min(int(path["first_value"]), int(path["second_value"]))


def _expected_difference(execution: dict) -> int:
    assert len(execution["query_path_details"]) == 1
    path = dict(execution["query_path_details"][0])
    return abs(int(path["first_value"]) - int(path["second_value"]))


def _expected_node_total(execution: dict) -> int:
    if str(execution["query_id"]) == SOURCE_OUTGOING_QUERY_ID:
        return sum(int(path["first_value"]) for path in execution["query_path_details"])
    if str(execution["query_id"]) == TARGET_INCOMING_QUERY_ID:
        return sum(int(path["second_value"]) for path in execution["query_path_details"])
    raise AssertionError(f"unsupported Sankey node-side branch: {execution['query_id']}")


@pytest.mark.parametrize(
    ("task_cls", "seed", "expected_answer"),
    [
        (ChartsFlowSankeySourceToTargetTotalFlowPublicTask, 69100, _expected_source_target_total),
        (ChartsFlowSankeyPathBottleneckValuePublicTask, 69140, _expected_bottleneck),
        (ChartsFlowSankeyPathFlowDifferencePublicTask, 69180, _expected_difference),
    ],
)
def test_charts_sankey_single_branch_tasks_match_contract(task_cls, seed: int, expected_answer) -> None:
    task = task_cls()
    out = task.generate(seed, params={"query_id": SINGLE_QUERY_ID}, max_attempts=100)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    assert task.task_id in list_default_task_ids()
    assert task.supported_query_ids == (SINGLE_QUERY_ID,)
    assert out.scene_id == "sankey"
    assert out.query_id == SINGLE_QUERY_ID
    assert str(execution["query_id"]) == SINGLE_QUERY_ID
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 2 <= int(execution["source_count"]) <= 3
    assert 2 <= int(execution["middle_count"]) <= 3
    assert 2 <= int(execution["target_count"]) <= 3
    assert 3 <= int(execution["path_count"]) <= 4
    assert int(out.answer_gt.value) == int(expected_answer(execution))
    refs = [str(value) for value in execution["annotation_segment_ids"]]
    expected_boxes = [render_map["segment_label_bboxes_px"][ref] for ref in refs]
    assert out.annotation_gt.value == expected_boxes
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["query_spec"]["params"]["query_id"] == SINGLE_QUERY_ID
    assert str(render["font_assets"]["font_asset_version"])
    assert str(render["font_assets"]["chart_font_family"])
    for bbox in out.annotation_gt.value:
        _assert_bbox_inside_canvas([float(value) for value in bbox], width=int(render["canvas_width"]), height=int(render["canvas_height"]))


@pytest.mark.parametrize("query_id", NODE_SIDE_QUERY_IDS)
def test_charts_sankey_node_side_total_matches_contract(query_id: str) -> None:
    task = ChartsFlowSankeyNodeSideTotalValuePublicTask()
    out = task.generate(69250 + NODE_SIDE_QUERY_IDS.index(query_id), params={"query_id": query_id}, max_attempts=100)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    assert task.task_id in list_default_task_ids()
    assert out.scene_id == "sankey"
    assert out.query_id == query_id
    assert str(execution["query_id"]) == query_id
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == int(_expected_node_total(execution))
    assert trace["query_spec"]["params"]["query_id"] == query_id
    refs = [str(value) for value in execution["annotation_segment_ids"]]
    expected_boxes = [render_map["segment_label_bboxes_px"][ref] for ref in refs]
    assert out.annotation_gt.value == expected_boxes
    for bbox in out.annotation_gt.value:
        _assert_bbox_inside_canvas([float(value) for value in bbox], width=int(render["canvas_width"]), height=int(render["canvas_height"]))


def test_charts_sankey_prompt_examples_match_contract() -> None:
    for task_cls in (
        ChartsFlowSankeySourceToTargetTotalFlowPublicTask,
        ChartsFlowSankeyPathBottleneckValuePublicTask,
        ChartsFlowSankeyPathFlowDifferencePublicTask,
        ChartsFlowSankeyNodeSideTotalValuePublicTask,
    ):
        out = task_cls().generate(69300 + len(task_cls.__name__), params={}, max_attempts=100)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert isinstance(answer_and_annotation["answer"], int)
        assert isinstance(answer_only["answer"], int)
        assert isinstance(answer_and_annotation["annotation"], list)
        assert answer_and_annotation["annotation"] and all(len(box) == 4 for box in answer_and_annotation["annotation"])


def test_charts_sankey_node_side_sampling_covers_branches() -> None:
    task = ChartsFlowSankeyNodeSideTotalValuePublicTask()
    counts: Counter[str] = Counter()
    for index in range(40):
        out = task.generate(hash64(69400, "charts_sankey_node_side", index), params={}, max_attempts=100)
        counts[str(out.query_id)] += 1
    assert_counter_support_within(counts, NODE_SIDE_QUERY_IDS, expected_per_key=20, tolerance=5)


def test_charts_sankey_generation_is_deterministic() -> None:
    params = {"query_id": TARGET_INCOMING_QUERY_ID}
    first = ChartsFlowSankeyNodeSideTotalValuePublicTask().generate(69500, params=params, max_attempts=100)
    second = ChartsFlowSankeyNodeSideTotalValuePublicTask().generate(69500, params=params, max_attempts=100)
    assert first.prompt == second.prompt
    assert first.answer_gt.to_dict() == second.answer_gt.to_dict()
    assert first.annotation_gt.to_dict() == second.annotation_gt.to_dict()
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
