"""Behavior tests for population-pyramid chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.population_pyramid.age_group_threshold_count import (
    THRESHOLD_QUERY_IDS,
    ChartsPopulationPyramidAgeGroupThresholdCountTask,
)
from trace.tasks.charts.population_pyramid.side_gap_extremum_label import (
    GAP_QUERY_IDS,
    ChartsPopulationPyramidSideGapExtremumLabelTask,
)
from trace.tasks.registry import create_task


TASK_CASES = (
    *[(ChartsPopulationPyramidSideGapExtremumLabelTask, query_id, "string", "bbox") for query_id in GAP_QUERY_IDS],
    *[(ChartsPopulationPyramidAgeGroupThresholdCountTask, query_id, "integer", "bbox_set") for query_id in THRESHOLD_QUERY_IDS],
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict, query_id: str) -> int | str:
    rows = list(execution["rows"])
    if query_id in GAP_QUERY_IDS:
        gaps = [(str(row["label"]), int(row["gap"])) for row in rows]
        if query_id == "largest_side_gap_label":
            target_gap = max(gap for _label, gap in gaps)
        else:
            target_gap = min(gap for _label, gap in gaps if int(gap) > 0)
        winners = [label for label, gap in gaps if int(gap) == int(target_gap)]
        assert len(winners) == 1
        return str(winners[0])

    threshold = int(execution["threshold_value"])
    side = str(execution["threshold_side"])
    relation = str(execution["threshold_relation"])

    def metric(row: dict) -> int:
        if side == "left":
            return int(row["left_value"])
        if side == "right":
            return int(row["right_value"])
        if side == "combined_total":
            return int(row["total"])
        raise AssertionError(f"unsupported threshold side: {side}")

    if relation == "at_least":
        return sum(1 for row in rows if metric(row) >= threshold)
    if relation == "at_most":
        return sum(1 for row in rows if metric(row) <= threshold)
    raise AssertionError(f"unsupported relation: {relation}")


@pytest.mark.parametrize(("task_cls", "query_id", "answer_type", "annotation_type"), TASK_CASES)
def test_charts_population_pyramid_tasks_match_contract(
    task_cls: type,
    query_id: str,
    answer_type: str,
    annotation_type: str,
) -> None:
    out = task_cls().generate(246000 + len(task_cls.task_id) + len(query_id), params={"query_id": query_id}, max_attempts=80)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    projected = trace["projected_annotation"]

    assert isinstance(create_task(task_cls.task_id), task_cls)
    assert out.scene_id == "population_pyramid"
    assert out.query_id == query_id
    assert str(execution["query_id"]) == query_id
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert out.answer_gt.type == answer_type
    assert out.annotation_gt.type == annotation_type
    assert trace["projected_annotation"]["type"] == annotation_type
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(execution["question_format"]) == "population_pyramid"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 8 <= int(execution["row_count"]) <= 14

    expected_answer = _expected_answer(execution, query_id)
    assert out.answer_gt.value == expected_answer
    assert execution["answer_value"] == expected_answer

    row_ids = [str(value) for value in projected["row_ids"]]
    expected_boxes = [render_map["row_bar_bboxes_px"][row_id] for row_id in row_ids]
    if annotation_type == "bbox":
        assert len(row_ids) == 1
        assert out.annotation_gt.value == expected_boxes[0]
        boxes_to_check = [list(out.annotation_gt.value)]
    else:
        assert len(row_ids) == int(out.answer_gt.value)
        assert out.annotation_gt.value == expected_boxes
        assert projected["bbox_set"] == expected_boxes
        boxes_to_check = list(out.annotation_gt.value)
    for bbox in boxes_to_check:
        _assert_bbox_inside_canvas([float(value) for value in bbox], width=int(render["canvas_width"]), height=int(render["canvas_height"]))


def test_charts_population_pyramid_prompt_examples_match_contract() -> None:
    for task_cls, query_id, answer_type, annotation_type in TASK_CASES:
        out = task_cls().generate(246500 + len(task_cls.task_id) + len(query_id), params={"query_id": query_id}, max_attempts=80)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        if answer_type == "integer":
            assert isinstance(answer_and_annotation["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_annotation["answer"], str)
            assert isinstance(answer_only["answer"], str)
            assert len(answer_and_annotation["answer"]) > 1
        if annotation_type == "bbox":
            assert isinstance(answer_and_annotation["annotation"], list)
            assert len(answer_and_annotation["annotation"]) == 4
        else:
            assert isinstance(answer_and_annotation["annotation"], list)
            assert all(isinstance(item, list) and len(item) == 4 for item in answer_and_annotation["annotation"])


def test_charts_population_pyramid_balanced_sampling_covers_queries() -> None:
    gap_queries: Counter[str] = Counter()
    threshold_queries: Counter[str] = Counter()
    for index in range(96):
        gap_out = ChartsPopulationPyramidSideGapExtremumLabelTask().generate(
            hash64(246100, "population_pyramid_gap", index),
            params={},
            max_attempts=80,
        )
        gap_queries[str(gap_out.query_id)] += 1
        count_out = ChartsPopulationPyramidAgeGroupThresholdCountTask().generate(
            hash64(246200, "population_pyramid_count", index),
            params={},
            max_attempts=80,
        )
        threshold_queries[str(count_out.query_id)] += 1
    assert set(gap_queries) == set(GAP_QUERY_IDS)
    assert set(threshold_queries) == set(THRESHOLD_QUERY_IDS)


def test_charts_population_pyramid_is_deterministic() -> None:
    params = {"query_id": "combined_total_at_least_threshold_count"}
    out_a = ChartsPopulationPyramidAgeGroupThresholdCountTask().generate(246300, params=params, max_attempts=80)
    out_b = ChartsPopulationPyramidAgeGroupThresholdCountTask().generate(246300, params=params, max_attempts=80)
    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
