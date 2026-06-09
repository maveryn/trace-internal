"""Behavior tests for chart heatmap-grid tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import assert_counter_support_within, extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.heatmap.grid_query import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_QUERY_IDS,
    ChartsHeatmapColorbarIntervalCellCountTask,
    ChartsHeatmapColorbarThresholdCellCountTask,
    ChartsHeatmapGridQueryTask,
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
    variant = str(execution["query_id"])
    row_labels = [str(item) for item in execution["row_labels"]]
    column_labels = [str(item) for item in execution["column_labels"]]
    values = [[int(value) for value in row] for row in execution["values"]]
    bin_count = int(execution["heat_bin_count"])

    if variant == "axis_condition_extremum_label":
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

    if variant == "axis_cell_extremum_label" and str(execution["query_axis"]) == "column":
        column_index = int(execution["answer_column_index"])
        column_values = [row[int(column_index)] for row in values]
        direction = str(execution["extremum_direction"])
        target = max(column_values) if direction == "hottest" else min(column_values)
        winners = [index for index, value in enumerate(column_values) if int(value) == int(target)]
        assert len(winners) == 1
        return row_labels[int(winners[0])]

    if variant == "axis_cell_extremum_label" and str(execution["query_axis"]) == "row":
        row_index = int(execution["answer_row_index"])
        row_values = list(values[int(row_index)])
        direction = str(execution["extremum_direction"])
        target = max(row_values) if direction == "hottest" else min(row_values)
        winners = [index for index, value in enumerate(row_values) if int(value) == int(target)]
        assert len(winners) == 1
        return column_labels[int(winners[0])]

    if variant == "condition_run_extremum_label":
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

    if variant == "colorbar_above_threshold_cell_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for row in values for value in row if int(value) > int(threshold))

    if variant == "colorbar_below_threshold_cell_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for row in values for value in row if int(value) < int(threshold))

    if variant == "colorbar_interval_cell_count":
        lower = int(execution["lower_bound"])
        upper = int(execution["upper_bound"])
        return sum(1 for row in values for value in row if int(lower) <= int(value) <= int(upper))

    raise AssertionError(f"unsupported variant: {variant}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_chart_heatmap_variants_match_contract(query_id: str) -> None:
    task = ChartsHeatmapGridQueryTask()
    out = task.generate(80100 + SUPPORTED_QUERY_IDS.index(query_id), params={"query_id": query_id}, max_attempts=10)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]

    assert out.query_id == query_id
    expected_answer_type = "integer" if str(query_id).startswith("colorbar_") else "string"
    assert out.answer_gt.type == expected_answer_type
    assert out.annotation_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(execution["question_format"]) == "heatmap_query"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 5 <= int(execution["row_count"]) <= 10
    if str(query_id).startswith("colorbar_"):
        assert str(execution["scene_variant"]) == "continuous_colorbar_heatmap"
        assert 5 <= int(execution["row_count"]) <= 7
        assert 6 <= int(execution["column_count"]) <= 8
        assert int(execution["heat_bin_count"]) == 101
        assert int(render["colorbar_value_min"]) == 0
        assert int(render["colorbar_value_max"]) == 100
        assert render["colorbar_ticks"] == list(range(0, 101, 10))
    else:
        assert int(execution["column_count"]) in set(range(7, 13))
        assert int(execution["heat_bin_count"]) == 5
    assert len(execution["cells"]) == int(execution["row_count"]) * int(execution["column_count"])
    assert len(render_map["cell_bboxes_px"]) == len(execution["cells"])

    expected_answer = _expected_answer(execution)
    assert out.answer_gt.value == expected_answer
    assert execution["answer_value"] == expected_answer
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value

    annotation_cell_ids = [str(cell_id) for cell_id in execution["annotation_cell_ids"]]
    expected_bboxes = [render_map["cell_bboxes_px"][cell_id] for cell_id in annotation_cell_ids]
    assert out.annotation_gt.value == expected_bboxes
    assert trace["projected_annotation"]["cell_ids"] == annotation_cell_ids
    assert annotation_cell_ids
    if str(query_id).startswith("colorbar_"):
        assert len(annotation_cell_ids) == int(out.answer_gt.value)
    for bbox in out.annotation_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    if str(query_id) == "axis_condition_extremum_label":
        assert str(execution["condition_kind"]) in {"hot", "cool", "increase", "decrease"}
        assert str(execution["query_axis"]) in {"row", "column"}
    elif str(query_id) == "condition_run_extremum_label":
        assert len(annotation_cell_ids) >= 2
        assert str(execution["query_axis"]) == "row"
    elif str(query_id) == "axis_cell_extremum_label":
        assert str(execution["query_axis"]) in {"row", "column"}
        if str(execution["query_axis"]) == "column":
            assert int(execution["answer_column_index"]) >= 0
        else:
            assert int(execution["answer_row_index"]) >= 0
    elif str(query_id) in {"colorbar_above_threshold_cell_count", "colorbar_below_threshold_cell_count"}:
        assert int(execution["threshold_value"]) in {30, 40, 50, 60, 70}
    elif str(query_id) == "colorbar_interval_cell_count":
        assert 0 <= int(execution["lower_bound"]) < int(execution["upper_bound"]) <= 100

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_chart_heatmap_prompt_examples_match_contract() -> None:
    task = ChartsHeatmapGridQueryTask()
    expected = {
        "axis_condition_extremum_label": "Cedar",
        "axis_cell_extremum_label": "Orly",
        "condition_run_extremum_label": "Mesa",
        "colorbar_above_threshold_cell_count": 3,
        "colorbar_below_threshold_cell_count": 3,
        "colorbar_interval_cell_count": 2,
    }

    for index, (query_id, answer) in enumerate(expected.items(), start=80200):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation["answer"] == answer
        assert answer_only == {"answer": answer}
        assert isinstance(answer_and_annotation["annotation"], list)


def test_chart_heatmap_balanced_sampling_covers_variants_and_scenes() -> None:
    task = ChartsHeatmapGridQueryTask()
    variants: Counter[str] = Counter()
    scenes: Counter[str] = Counter()
    condition_by_scene: Counter[tuple[str, str]] = Counter()
    directions: Counter[str] = Counter()
    query_axes: Counter[str] = Counter()

    for index in range(72):
        out = task.generate(hash64(80300, "charts_heatmap", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        variants[str(execution["query_id"])] += 1
        scenes[str(execution["scene_variant"])] += 1
        if str(execution["query_id"]) in {"axis_condition_extremum_label", "condition_run_extremum_label"}:
            condition_by_scene[(str(execution["scene_variant"]), str(execution["condition_kind"]))] += 1
        if str(execution["query_id"]) == "axis_cell_extremum_label":
            directions[str(execution["extremum_direction"])] += 1
        if str(execution["query_id"]) in {"axis_condition_extremum_label", "axis_cell_extremum_label"}:
            query_axes[str(execution["query_axis"])] += 1

    assert_counter_support_within(
        variants,
        SUPPORTED_QUERY_IDS,
        expected_per_key=12,
        tolerance=5,
    )
    assert set(scenes.keys()) == set(SUPPORTED_SCENE_VARIANTS)
    assert {"hottest", "coolest"}.issubset(set(directions.keys()))
    assert query_axes["row"] > 0
    assert query_axes["column"] > 0
    assert any(condition == "increase" for _, condition in condition_by_scene.keys())
    assert any(condition == "hot" for _, condition in condition_by_scene.keys())


def test_chart_heatmap_colorbar_public_tasks_match_contract() -> None:
    for cls in (ChartsHeatmapColorbarThresholdCellCountTask, ChartsHeatmapColorbarIntervalCellCountTask):
        out = cls().generate(80500, params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        assert str(execution["scene_variant"]) == "continuous_colorbar_heatmap"
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == _expected_answer(execution)
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        if cls is ChartsHeatmapColorbarThresholdCellCountTask:
            assert str(out.query_id) in {"colorbar_above_threshold_cell_count", "colorbar_below_threshold_cell_count"}
        else:
            assert str(out.query_id) == "colorbar_interval_cell_count"


def test_chart_heatmap_is_deterministic() -> None:
    task = ChartsHeatmapGridQueryTask()
    params = {"query_id": "condition_run_extremum_label", "scene_variant": "signed_change_heatmap"}
    out_a = task.generate(80400, params=params, max_attempts=10)
    out_b = task.generate(80400, params=params, max_attempts=10)
    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert list(out_a.image.getdata()) == list(out_b.image.getdata())
