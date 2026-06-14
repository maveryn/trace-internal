"""Behavior tests for chart heatmap scene-package tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import assert_counter_support_within, extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.heatmap.axis_cell_extremum_label import ChartsHeatmapAxisCellExtremumLabelTask
from trace.tasks.charts.heatmap.axis_condition_extremum_label import ChartsHeatmapAxisConditionExtremumLabelTask
from trace.tasks.charts.heatmap.colorbar_interval_cell_count import ChartsHeatmapColorbarIntervalCellCountTask
from trace.tasks.charts.heatmap.colorbar_threshold_cell_count import ChartsHeatmapColorbarThresholdCellCountTask
from trace.tasks.charts.heatmap.condition_run_extremum_label import ChartsHeatmapConditionRunExtremumLabelTask
from trace.tasks.charts.heatmap.shared.defaults import SUPPORTED_SCENE_VARIANTS


DISCRETE_SCENE_VARIANTS = tuple(value for value in SUPPORTED_SCENE_VARIANTS if value != "continuous_colorbar_heatmap")
TASK_CASES = tuple(
    (cls, str(query_id))
    for cls in (
        ChartsHeatmapAxisConditionExtremumLabelTask,
        ChartsHeatmapAxisCellExtremumLabelTask,
        ChartsHeatmapConditionRunExtremumLabelTask,
        ChartsHeatmapColorbarThresholdCellCountTask,
        ChartsHeatmapColorbarIntervalCellCountTask,
    )
    for query_id in cls.supported_query_ids
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _condition_matches(value: int, *, condition_kind: str, bin_count: int) -> bool:
    midpoint = int(bin_count) // 2
    if condition_kind == "hot":
        return int(value) >= max(0, int(bin_count) - 2)
    if condition_kind == "cool":
        return int(value) <= 1
    if condition_kind == "increase":
        return int(value) > int(midpoint)
    if condition_kind == "decrease":
        return int(value) < int(midpoint)
    raise AssertionError(f"unsupported condition_kind: {condition_kind}")


def _longest_run(mask: list[bool]) -> int:
    best = 0
    current = 0
    for active in mask:
        current = int(current + 1) if bool(active) else 0
        best = max(int(best), int(current))
    return int(best)


def _expected_answer(execution: dict) -> int | str:
    prompt_key = str(execution["prompt_key"])
    row_labels = [str(item) for item in execution["row_labels"]]
    column_labels = [str(item) for item in execution["column_labels"]]
    values = [[int(value) for value in row] for row in execution["values"]]
    bin_count = int(execution["heat_bin_count"])
    if prompt_key == "axis_condition_extremum_label":
        condition = str(execution["condition_kind"])
        if str(execution["query_axis"]) == "row":
            counts = [
                sum(
                    1
                    for value in row
                    if _condition_matches(int(value), condition_kind=condition, bin_count=bin_count)
                )
                for row in values
            ]
            labels = row_labels
        else:
            counts = [
                sum(
                    1
                    for row in values
                    if _condition_matches(int(row[column_index]), condition_kind=condition, bin_count=bin_count)
                )
                for column_index in range(len(column_labels))
            ]
            labels = column_labels
        maximum = max(counts)
        winners = [index for index, count in enumerate(counts) if int(count) == int(maximum)]
        assert len(winners) == 1
        return labels[int(winners[0])]
    if prompt_key == "axis_cell_extremum_label" and str(execution["query_axis"]) == "column":
        column_index = int(execution["answer_column_index"])
        column_values = [row[int(column_index)] for row in values]
        direction = str(execution["extremum_direction"])
        target = max(column_values) if direction == "hottest" else min(column_values)
        winners = [index for index, value in enumerate(column_values) if int(value) == int(target)]
        assert len(winners) == 1
        return row_labels[int(winners[0])]
    if prompt_key == "axis_cell_extremum_label" and str(execution["query_axis"]) == "row":
        row_index = int(execution["answer_row_index"])
        row_values = list(values[int(row_index)])
        direction = str(execution["extremum_direction"])
        target = max(row_values) if direction == "hottest" else min(row_values)
        winners = [index for index, value in enumerate(row_values) if int(value) == int(target)]
        assert len(winners) == 1
        return column_labels[int(winners[0])]
    if prompt_key == "condition_run_extremum_label":
        condition = str(execution["condition_kind"])
        run_lengths = [
            _longest_run(
                [
                    _condition_matches(int(value), condition_kind=condition, bin_count=bin_count)
                    for value in row
                ]
            )
            for row in values
        ]
        maximum = max(run_lengths)
        winners = [index for index, run_length in enumerate(run_lengths) if int(run_length) == int(maximum)]
        assert len(winners) == 1
        assert int(maximum) >= 2
        return row_labels[int(winners[0])]
    if prompt_key == "colorbar_above_threshold_cell_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for row in values for value in row if int(value) > int(threshold))
    if prompt_key == "colorbar_below_threshold_cell_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for row in values for value in row if int(value) < int(threshold))
    if prompt_key == "colorbar_interval_cell_count":
        lower = int(execution["lower_bound"])
        upper = int(execution["upper_bound"])
        return sum(1 for row in values for value in row if int(lower) <= int(value) <= int(upper))
    raise AssertionError(f"unsupported prompt key: {prompt_key}")


@pytest.mark.parametrize(("task_cls", "query_id"), TASK_CASES)
def test_chart_heatmap_task_queries_match_contract(task_cls: type, query_id: str) -> None:
    task = task_cls()
    seed = 80100 + TASK_CASES.index((task_cls, query_id))
    out = task.generate(seed, params={"query_id": query_id, "unanswerable_probability": 0.0}, max_attempts=512)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    prompt_key = str(execution["prompt_key"])

    assert out.query_id == query_id
    expected_answer_type = "integer" if str(prompt_key).startswith("colorbar_") else "string"
    assert out.answer_gt.type == expected_answer_type
    assert out.annotation_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(execution["question_format"]) == "heatmap_query"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert len(execution["cells"]) == int(execution["row_count"]) * int(execution["column_count"])
    assert len(render_map["cell_bboxes_px"]) == len(execution["cells"])

    if str(prompt_key).startswith("colorbar_"):
        assert str(execution["scene_variant"]) == "continuous_colorbar_heatmap"
        assert 5 <= int(execution["row_count"]) <= 7
        assert 6 <= int(execution["column_count"]) <= 8
        assert int(execution["heat_bin_count"]) == 101
        assert int(render["colorbar_value_min"]) == 0
        assert int(render["colorbar_value_max"]) == 100
        assert render["colorbar_ticks"] == list(range(0, 101, 10))
    else:
        assert 5 <= int(execution["row_count"]) <= 10
        assert int(execution["column_count"]) in set(range(7, 13))
        assert int(execution["heat_bin_count"]) == 5

    expected_answer = _expected_answer(execution)
    assert out.answer_gt.value == expected_answer
    assert execution["answer_value"] == expected_answer
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    annotation_cell_ids = [str(cell_id) for cell_id in execution["annotation_cell_ids"]]
    expected_bboxes = [render_map["cell_bboxes_px"][cell_id] for cell_id in annotation_cell_ids]
    assert out.annotation_gt.value == expected_bboxes
    assert trace["projected_annotation"]["cell_ids"] == annotation_cell_ids
    assert annotation_cell_ids
    if str(prompt_key).startswith("colorbar_"):
        assert len(annotation_cell_ids) == int(out.answer_gt.value)
    for bbox in out.annotation_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )


def test_chart_heatmap_prompt_examples_match_contract() -> None:
    expected = {
        ChartsHeatmapAxisConditionExtremumLabelTask: ("row_condition_extremum_label", "Cedar"),
        ChartsHeatmapAxisCellExtremumLabelTask: ("row_hottest_column_label", "Orly"),
        ChartsHeatmapConditionRunExtremumLabelTask: ("single", "Mesa"),
        ChartsHeatmapColorbarThresholdCellCountTask: ("colorbar_above_threshold_cell_count", 3),
        ChartsHeatmapColorbarIntervalCellCountTask: ("single", 2),
    }
    for index, (cls, (query_id, answer)) in enumerate(expected.items(), start=80200):
        out = cls().generate(index, params={"query_id": query_id}, max_attempts=512)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation["answer"] == answer
        assert answer_only == {"answer": answer}
        assert isinstance(answer_and_annotation["annotation"], list)


def test_chart_heatmap_balanced_sampling_covers_scene_axes() -> None:
    scenes: Counter[str] = Counter()
    condition_by_scene: Counter[tuple[str, str]] = Counter()
    directions: Counter[str] = Counter()
    query_axes: Counter[str] = Counter()

    for index in range(72):
        out = ChartsHeatmapAxisCellExtremumLabelTask().generate(
            hash64(80300, "charts_heatmap_axis_cell", index),
            params={"unanswerable_probability": 0.0},
            max_attempts=512,
        )
        execution = out.trace_payload["execution_trace"]
        scenes[str(execution["scene_variant"])] += 1
        directions[str(execution["extremum_direction"])] += 1
        query_axes[str(execution["query_axis"])] += 1

    for index in range(72):
        out = ChartsHeatmapAxisConditionExtremumLabelTask().generate(
            hash64(80300, "charts_heatmap_axis_condition", index),
            params={"unanswerable_probability": 0.0},
            max_attempts=512,
        )
        execution = out.trace_payload["execution_trace"]
        scenes[str(execution["scene_variant"])] += 1
        condition_by_scene[str(execution["scene_variant"]), str(execution["condition_kind"])] += 1
        query_axes[str(execution["query_axis"])] += 1

    assert_counter_support_within(scenes, DISCRETE_SCENE_VARIANTS, expected_per_key=48, tolerance=20)
    assert {"hottest", "coolest"}.issubset(set(directions.keys()))
    assert query_axes["row"] > 0
    assert query_axes["column"] > 0
    assert any(condition == "increase" for _, condition in condition_by_scene.keys())
    assert any(condition == "hot" for _, condition in condition_by_scene.keys())


def test_chart_heatmap_colorbar_public_tasks_match_contract() -> None:
    for cls in (ChartsHeatmapColorbarThresholdCellCountTask, ChartsHeatmapColorbarIntervalCellCountTask):
        out = cls().generate(80500, params={}, max_attempts=512)
        execution = out.trace_payload["execution_trace"]
        assert str(execution["scene_variant"]) == "continuous_colorbar_heatmap"
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == _expected_answer(execution)
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        if cls is ChartsHeatmapColorbarThresholdCellCountTask:
            assert str(out.query_id) in {"colorbar_above_threshold_cell_count", "colorbar_below_threshold_cell_count"}
        else:
            assert str(out.query_id) == "single"


def test_chart_heatmap_is_deterministic() -> None:
    task = ChartsHeatmapConditionRunExtremumLabelTask()
    params = {"query_id": "single", "scene_variant": "signed_change_heatmap"}
    out_a = task.generate(80400, params=params, max_attempts=512)
    out_b = task.generate(80400, params=params, max_attempts=512)
    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert list(out_a.image.getdata()) == list(out_b.image.getdata())
