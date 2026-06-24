"""Behavior tests for multi-series scatter readout chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import hash64
from trace.core.scene_config import get_scene_defaults
from trace.tasks import create_task
from trace.tasks.charts.scatter_readout.series_pair_value_gap_at_x import (
    ChartsScatterSeriesPairValueGapAtXTask,
)
from trace.tasks.charts.scatter_readout.series_x_extremum_label import (
    ChartsScatterSeriesExtremumXLabelTask,
)
from trace.tasks.charts.scatter_readout.series_y_anchor_other_series_value import (
    ChartsScatterSeriesYAnchorOtherSeriesValueTask,
)


CASES = (
    (ChartsScatterSeriesExtremumXLabelTask, "series_highest_x_label", "string"),
    (ChartsScatterSeriesExtremumXLabelTask, "series_lowest_x_label", "string"),
    (ChartsScatterSeriesPairValueGapAtXTask, SINGLE_QUERY_ID, "integer"),
    (ChartsScatterSeriesYAnchorOtherSeriesValueTask, SINGLE_QUERY_ID, "integer"),
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _series_points(execution: dict, label: str) -> list[dict]:
    points = execution["values_by_series"][str(label)]
    assert isinstance(points, list)
    return [dict(point) for point in points]


def _expected_answer(execution: dict, answer_type: str) -> int | str:
    if str(execution.get("answerability", "answerable")) == "unanswerable":
        return "unanswerable"

    target_series = str(execution["target_series_label"])
    points = _series_points(execution, target_series)
    if str(answer_type) == "string":
        if str(execution["extremum"]) == "highest":
            return str(max(points, key=lambda point: (int(point["y_value"]), str(point["x_label"])))["x_label"])
        return str(min(points, key=lambda point: (int(point["y_value"]), str(point["x_label"])))["x_label"])

    target_x = str(execution["target_x_label"])
    comparison_series = str(execution["comparison_series_label"])
    source = [point for point in points if str(point["x_label"]) == target_x]
    comparison = [point for point in _series_points(execution, comparison_series) if str(point["x_label"]) == target_x]
    assert len(source) == 1
    assert len(comparison) == 1
    if str(execution["operation"]) == "absolute_difference":
        return abs(int(source[0]["y_value"]) - int(comparison[0]["y_value"]))
    return int(comparison[0]["y_value"])


@pytest.mark.parametrize(("task_cls", "query_id", "answer_type"), CASES)
def test_chart_scatter_series_readout_queries_match_contract(task_cls, query_id: str, answer_type: str) -> None:
    task = task_cls()
    out = task.generate(
        93100 + CASES.index((task_cls, query_id, answer_type)),
        params={"query_id": query_id, "_enable_unanswerable": False},
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    assert out.query_id == query_id
    assert out.scene_id == "scatter_readout"
    assert out.answer_gt.type == answer_type
    assert out.annotation_gt.type == "bbox_map"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(execution["question_format"]) == "scatter_series_readout_query"
    assert str(execution["scene_variant"]) == "marker_scatter"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["series_count"]) == 5
    assert 9 <= int(execution["x_count"]) <= 10
    assert int(execution["total_point_count"]) == int(execution["series_count"]) * int(execution["x_count"])
    expected_answer = _expected_answer(execution, answer_type)
    assert out.answer_gt.value == expected_answer
    assert execution["answer"] == expected_answer
    assert trace["projected_annotation"]["type"] == "bbox_map"
    assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_bbox_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["bbox_set"] == list(out.annotation_gt.value.values())
    for bbox in out.annotation_gt.value.values():
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )
    annotation_point_ids = [str(point_id) for point_id in execution["annotation_point_ids"]]
    target_point_id = str(execution["target_point_id"])
    assert trace["projected_annotation"]["point_id"] == target_point_id
    assert trace["projected_annotation"]["point_ids"] == annotation_point_ids
    assert out.annotation_gt.value["target_point_readout"] == render_map["point_annotation_bboxes_px"][target_point_id]
    if answer_type == "string":
        assert set(out.annotation_gt.value) == {"target_point_readout", "x_axis_label"}
        assert out.annotation_gt.value["x_axis_label"] == render_map["x_label_bboxes_px"][str(execution["target_x_label"])]
    else:
        assert set(out.annotation_gt.value) == {"target_point_readout", "comparison_point_readout", "x_axis_label"}
        assert out.annotation_gt.value["comparison_point_readout"] == render_map["point_annotation_bboxes_px"][
            str(execution["comparison_point_id"])
        ]
        assert out.annotation_gt.value["x_axis_label"] == render_map["x_label_bboxes_px"][str(execution["target_x_label"])]


def test_chart_scatter_series_readout_prompt_examples_match_contract() -> None:
    for index, (task_cls, query_id, answer_type) in enumerate(CASES, start=93200):
        out = task_cls().generate(index, params={"query_id": query_id, "_enable_unanswerable": False}, max_attempts=80)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        if answer_type == "integer":
            assert isinstance(answer_and_annotation["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_annotation["answer"], str)
            assert isinstance(answer_only["answer"], str)
        assert isinstance(answer_and_annotation["annotation"], dict)
        assert "multi-series scatter plot" in out.prompt
        assert "Annotation" in out.prompt or "annotation" in out.prompt


def test_chart_scatter_series_readout_balanced_sampling_covers_queries() -> None:
    counts: Counter[str] = Counter()
    answer_types: Counter[str] = Counter()
    for index in range(80):
        task_cls, _query_id, _answer_type = CASES[int(index) % len(CASES)]
        task = task_cls()
        out = task.generate(hash64(93300, "charts_scatter_series", index), params={}, max_attempts=120)
        counts[str(out.query_id)] += 1
        answer_types[str(out.answer_gt.type)] += 1
    assert set(counts) == {query_id for _cls, query_id, _answer_type in CASES}
    assert counts[SINGLE_QUERY_ID] >= 35
    assert counts["series_highest_x_label"] >= 15
    assert counts["series_lowest_x_label"] >= 15
    assert answer_types["string"] > 0
    assert answer_types["integer"] > 0


def test_chart_scatter_series_readout_registered_and_scene_config_loaded() -> None:
    assert (
        create_task("task_charts__scatter_readout__series_x_extremum_label").task_id
        == "task_charts__scatter_readout__series_x_extremum_label"
    )
    assert (
        create_task("task_charts__scatter_readout__series_pair_value_gap_at_x").task_id
        == "task_charts__scatter_readout__series_pair_value_gap_at_x"
    )
    assert (
        create_task("task_charts__scatter_readout__series_y_anchor_other_series_value").task_id
        == "task_charts__scatter_readout__series_y_anchor_other_series_value"
    )
    cfg = get_scene_defaults("charts", "scatter_readout")
    assert isinstance(cfg.get("generation"), dict)
    assert isinstance(cfg.get("rendering"), dict)
    assert isinstance(cfg.get("prompt"), dict)
    assert str(cfg["prompt"]["shared"]["bundle_id"]) == "charts_scatter_readout_v1"
