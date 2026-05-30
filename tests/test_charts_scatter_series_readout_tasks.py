"""Behavior tests for multi-series scatter readout chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks import create_task
from trace.tasks.charts.scatter.series_readout import (
    ChartsScatterSeriesExtremumXLabelTask,
    ChartsScatterSeriesPointLookupTask,
)


CASES = (
    (ChartsScatterSeriesExtremumXLabelTask, "series_highest_x_label", "string"),
    (ChartsScatterSeriesExtremumXLabelTask, "series_lowest_x_label", "string"),
    (ChartsScatterSeriesPointLookupTask, "series_pair_value_gap_at_x", "integer"),
    (ChartsScatterSeriesPointLookupTask, "series_y_anchor_other_series_value", "integer"),
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


def _expected_answer(execution: dict, query_id: str) -> int | str:
    target_series = str(execution["target_series_label"])
    points = _series_points(execution, target_series)
    if query_id == "series_highest_x_label":
        return str(max(points, key=lambda point: (int(point["y_value"]), str(point["x_label"])))["x_label"])
    if query_id == "series_lowest_x_label":
        return str(min(points, key=lambda point: (int(point["y_value"]), str(point["x_label"])))["x_label"])
    if query_id == "series_pair_value_gap_at_x":
        target_x = str(execution["target_x_label"])
        comparison_series = str(execution["comparison_series_label"])
        source = [point for point in points if str(point["x_label"]) == target_x]
        comparison = [point for point in _series_points(execution, comparison_series) if str(point["x_label"]) == target_x]
        assert len(source) == 1
        assert len(comparison) == 1
        return abs(int(source[0]["y_value"]) - int(comparison[0]["y_value"]))
    if query_id == "series_y_anchor_other_series_value":
        target_y = int(execution["target_y_value"])
        comparison_series = str(execution["comparison_series_label"])
        source = [point for point in points if int(point["y_value"]) == target_y]
        assert len(source) == 1
        target_x = str(source[0]["x_label"])
        comparison = [point for point in _series_points(execution, comparison_series) if str(point["x_label"]) == target_x]
        assert len(comparison) == 1
        return int(comparison[0]["y_value"])
    raise AssertionError(f"unsupported query id: {query_id}")


@pytest.mark.parametrize(("task_cls", "query_id", "answer_type"), CASES)
def test_chart_scatter_series_readout_queries_match_contract(task_cls, query_id: str, answer_type: str) -> None:
    task = task_cls()
    out = task.generate(93100 + CASES.index((task_cls, query_id, answer_type)), params={"query_id": query_id}, max_attempts=80)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]

    assert out.query_id == query_id
    assert out.scene_id == "scatter_readout"
    assert out.answer_gt.type == answer_type
    assert out.evidence_gt.type == "keyed_bbox_map"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["question_format"]) == "scatter_series_readout_query"
    assert str(execution["scene_variant"]) == "marker_scatter"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["series_count"]) == 5
    assert 9 <= int(execution["x_count"]) <= 10
    assert int(execution["total_point_count"]) == int(execution["series_count"]) * int(execution["x_count"])

    expected_answer = _expected_answer(execution, query_id)
    assert out.answer_gt.value == expected_answer
    assert execution["answer"] == expected_answer
    assert trace["projected_evidence"]["type"] == "keyed_bbox_map"
    assert trace["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value
    assert trace["projected_evidence"]["pixel_keyed_bbox_map"] == out.evidence_gt.value
    assert trace["projected_evidence"]["bbox_set"] == list(out.evidence_gt.value.values())

    for bbox in out.evidence_gt.value.values():
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    evidence_point_ids = [str(point_id) for point_id in execution["evidence_point_ids"]]
    target_point_id = str(execution["target_point_id"])
    assert trace["projected_evidence"]["point_id"] == target_point_id
    assert trace["projected_evidence"]["point_ids"] == evidence_point_ids
    assert out.evidence_gt.value["target_point_readout"] == render_map["point_evidence_bboxes_px"][target_point_id]
    if answer_type == "string":
        assert set(out.evidence_gt.value) == {"target_point_readout", "x_axis_label"}
        assert out.evidence_gt.value["x_axis_label"] == render_map["x_label_bboxes_px"][str(execution["target_x_label"])]
    else:
        assert set(out.evidence_gt.value) == {"target_point_readout", "comparison_point_readout", "x_axis_label"}
        assert out.evidence_gt.value["comparison_point_readout"] == render_map["point_evidence_bboxes_px"][str(execution["comparison_point_id"])]
        assert out.evidence_gt.value["x_axis_label"] == render_map["x_label_bboxes_px"][str(execution["target_x_label"])]

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }


def test_chart_scatter_series_readout_prompt_examples_match_contract() -> None:
    for index, (task_cls, query_id, answer_type) in enumerate(CASES, start=93200):
        out = task_cls().generate(index, params={"query_id": query_id}, max_attempts=80)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        if answer_type == "integer":
            assert isinstance(answer_and_evidence["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_evidence["answer"], str)
            assert isinstance(answer_only["answer"], str)
        assert isinstance(answer_and_evidence["evidence"], dict)
        assert "The image shows" in out.prompt
        assert "Displayed is" not in out.prompt
        assert "Shown is" not in out.prompt


def test_chart_scatter_series_readout_balanced_sampling_covers_queries() -> None:
    counts: Counter[str] = Counter()
    answer_types: Counter[str] = Counter()
    for index in range(80):
        task = ChartsScatterSeriesExtremumXLabelTask() if index % 2 == 0 else ChartsScatterSeriesPointLookupTask()
        out = task.generate(hash64(93300, "charts_scatter_series", index), params={}, max_attempts=120)
        counts[str(out.query_id)] += 1
        answer_types[str(out.answer_gt.type)] += 1

    assert set(counts) == {query_id for _cls, query_id, _answer_type in CASES}
    assert all(value >= 15 for value in counts.values())
    assert answer_types["string"] > 0
    assert answer_types["integer"] > 0


def test_chart_scatter_series_readout_registered_and_group_config_loaded() -> None:
    assert create_task("task_charts__scatter_readout__series_x_extremum_label").task_id == "task_charts__scatter_readout__series_x_extremum_label"
    assert create_task("task_charts__scatter_readout__series_point_lookup_value").task_id == "task_charts__scatter_readout__series_point_lookup_value"

    cfg = get_task_group_defaults("charts", "scatter")
    assert isinstance(cfg.get("generation"), dict)
    assert isinstance(cfg.get("rendering"), dict)
    assert isinstance(cfg.get("prompt"), dict)
    prompt = cfg["prompt"]["task_overrides"]["charts_scatter_series_readout_base"]
    assert str(prompt["scene_key"]) == "scatter_series_readout"
    assert str(prompt["task_key"]) == "scatter_series_readout_query"
