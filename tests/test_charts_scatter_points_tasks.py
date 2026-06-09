"""Behavior tests for scatter point chart tasks."""

from __future__ import annotations

from collections import Counter, defaultdict

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks import create_task
from trace.tasks.charts.scatter.points_query import (
    ChartsScatterPointsAxisThresholdPointCountTask,
    ChartsScatterPointsCategoryAxisMeanExtremumLabelTask,
    ChartsScatterPointsCategoryThresholdPointCountTask,
)


CASES = (
    (ChartsScatterPointsAxisThresholdPointCountTask, "axis_threshold_point_count", "integer"),
    (ChartsScatterPointsCategoryAxisMeanExtremumLabelTask, "category_axis_mean_extremum_label", "string"),
    (ChartsScatterPointsCategoryThresholdPointCountTask, "category_threshold_point_count", "integer"),
)


def _points(execution: dict) -> list[dict]:
    return [dict(point) for point in execution["points"]]


def _matching_threshold(point: dict, *, axis: str, direction: str, threshold: int) -> bool:
    value = float(point[f"{axis}_value"])
    if direction == "above":
        return value > float(threshold)
    return value < float(threshold)


def _expected_answer(execution: dict, query_id: str) -> int | str:
    points = _points(execution)
    if query_id == "axis_threshold_point_count":
        axis = str(execution["threshold_axis"])
        direction = str(execution["threshold_direction"])
        threshold = int(execution["threshold_value"])
        return sum(1 for point in points if _matching_threshold(point, axis=axis, direction=direction, threshold=threshold))

    if query_id == "category_axis_mean_extremum_label":
        axis = str(execution["mean_axis"])
        means: dict[str, list[float]] = defaultdict(list)
        for point in points:
            means[str(point["category_label"])].append(float(point[f"{axis}_value"]))
        mean_by_category = {label: sum(values) / len(values) for label, values in means.items()}
        if str(execution["mean_extremum"]) == "largest":
            return max(sorted(mean_by_category), key=lambda label: (mean_by_category[label], label))
        return min(sorted(mean_by_category), key=lambda label: (mean_by_category[label], label))

    if query_id == "category_threshold_point_count":
        axis = str(execution["threshold_axis"])
        direction = str(execution["threshold_direction"])
        threshold = int(execution["threshold_value"])
        target = str(execution["target_category_label"])
        return sum(
            1
            for point in points
            if str(point["category_label"]) == target
            and _matching_threshold(point, axis=axis, direction=direction, threshold=threshold)
        )

    raise AssertionError(f"unsupported query id: {query_id}")


def _expected_annotation_point_ids(execution: dict, query_id: str) -> list[str]:
    points = _points(execution)
    if query_id == "axis_threshold_point_count":
        axis = str(execution["threshold_axis"])
        direction = str(execution["threshold_direction"])
        threshold = int(execution["threshold_value"])
        return [
            str(point["point_id"])
            for point in points
            if _matching_threshold(point, axis=axis, direction=direction, threshold=threshold)
        ]

    if query_id == "category_axis_mean_extremum_label":
        answer = str(_expected_answer(execution, query_id))
        return [str(point["point_id"]) for point in points if str(point["category_label"]) == answer]

    if query_id == "category_threshold_point_count":
        axis = str(execution["threshold_axis"])
        direction = str(execution["threshold_direction"])
        threshold = int(execution["threshold_value"])
        target = str(execution["target_category_label"])
        return [
            str(point["point_id"])
            for point in points
            if str(point["category_label"]) == target
            and _matching_threshold(point, axis=axis, direction=direction, threshold=threshold)
        ]

    raise AssertionError(f"unsupported query id: {query_id}")


@pytest.mark.parametrize(("task_cls", "query_id", "answer_type"), CASES)
def test_chart_scatter_points_queries_match_contract(task_cls, query_id: str, answer_type: str) -> None:
    task = task_cls()
    out = task.generate(142100 + CASES.index((task_cls, query_id, answer_type)), params={"query_id": query_id}, max_attempts=80)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]

    assert out.scene_id == "scatter_points"
    assert out.query_id == query_id
    assert out.answer_gt.type == answer_type
    assert out.annotation_gt.type == "point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(execution["question_format"]) == "scatter_points_query"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert str(render["font_asset_version"])
    assert str(render["chart_font_family"])
    assert str(render["font_assets"]["chart_font_family"]) == str(render["chart_font_family"])

    expected_answer = _expected_answer(execution, query_id)
    assert out.answer_gt.value == expected_answer
    assert execution["answer"] == expected_answer
    expected_point_ids = _expected_annotation_point_ids(execution, query_id)
    assert execution["annotation_point_ids"] == expected_point_ids
    expected_points = [render_map["point_centers_px"][point_id] for point_id in expected_point_ids]
    assert out.annotation_gt.value == expected_points
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == expected_points
    assert trace["projected_annotation"]["pixel_point_set"] == expected_points
    assert trace["projected_annotation"]["point_ids"] == expected_point_ids

    for point in out.annotation_gt.value:
        assert len(point) == 2
        x, y = [float(value) for value in point]
        assert 0 <= x <= int(render["canvas_width"])
        assert 0 <= y <= int(render["canvas_height"])

    if query_id == "axis_threshold_point_count":
        assert 28 <= int(execution["point_count"]) <= 54
        assert 4 <= int(out.answer_gt.value) <= 18
        assert not execution["categories"]
        assert render_map["threshold_guide_bbox_px"]
    elif query_id == "category_axis_mean_extremum_label":
        assert 4 <= int(execution["category_count"]) <= 6
        assert len(execution["categories"]) == int(execution["category_count"])
        assert str(out.answer_gt.value) in {str(category["label"]) for category in execution["categories"]}
        assert float(execution["mean_margin"]) > 0.0
        assert not render_map["threshold_guide_bbox_px"]
    elif query_id == "category_threshold_point_count":
        assert 4 <= int(execution["category_count"]) <= 6
        assert 2 <= int(out.answer_gt.value) <= 9
        assert str(execution["target_category_label"]) in {str(category["label"]) for category in execution["categories"]}
        assert render_map["threshold_guide_bbox_px"]

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }


def test_chart_scatter_points_prompt_examples_match_contract() -> None:
    for index, (task_cls, query_id, answer_type) in enumerate(CASES, start=142200):
        out = task_cls().generate(index, params={"query_id": query_id}, max_attempts=80)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert isinstance(answer_and_annotation["annotation"], list)
        assert all(isinstance(point, list) and len(point) == 2 for point in answer_and_annotation["annotation"])
        if answer_type == "integer":
            assert isinstance(answer_and_annotation["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_annotation["answer"], str)
            assert len(str(answer_and_annotation["answer"])) > 1
            assert isinstance(answer_only["answer"], str)
        assert "The image shows" in out.prompt
        assert "Displayed is" not in out.prompt
        assert "Shown is" not in out.prompt


def test_chart_scatter_points_balanced_sampling_covers_variant_axes() -> None:
    axis_task = ChartsScatterPointsAxisThresholdPointCountTask()
    mean_task = ChartsScatterPointsCategoryAxisMeanExtremumLabelTask()
    category_task = ChartsScatterPointsCategoryThresholdPointCountTask()
    threshold_axes: Counter[str] = Counter()
    threshold_directions: Counter[str] = Counter()
    mean_axes: Counter[str] = Counter()
    mean_extrema: Counter[str] = Counter()
    axis_answers: Counter[int] = Counter()
    category_answers: Counter[int] = Counter()
    category_counts: Counter[int] = Counter()

    for index in range(72):
        out = axis_task.generate(hash64(142300, "scatter_points_axis", index), params={}, max_attempts=80)
        execution = out.trace_payload["execution_trace"]
        threshold_axes[str(execution["threshold_axis"])] += 1
        threshold_directions[str(execution["threshold_direction"])] += 1
        axis_answers[int(out.answer_gt.value)] += 1

        out = mean_task.generate(hash64(142400, "scatter_points_mean", index), params={}, max_attempts=80)
        execution = out.trace_payload["execution_trace"]
        mean_axes[str(execution["mean_axis"])] += 1
        mean_extrema[str(execution["mean_extremum"])] += 1
        category_counts[int(execution["category_count"])] += 1

        out = category_task.generate(hash64(142500, "scatter_points_category_threshold", index), params={}, max_attempts=80)
        execution = out.trace_payload["execution_trace"]
        threshold_axes[str(execution["threshold_axis"])] += 1
        threshold_directions[str(execution["threshold_direction"])] += 1
        category_answers[int(out.answer_gt.value)] += 1
        category_counts[int(execution["category_count"])] += 1

    assert set(threshold_axes) == {"x", "y"}
    assert set(threshold_directions) == {"above", "below"}
    assert set(mean_axes) == {"x", "y"}
    assert set(mean_extrema) == {"largest", "smallest"}
    assert len(axis_answers) >= 8
    assert len(category_answers) >= 5
    assert min(category_counts) >= 4
    assert max(category_counts) <= 6


def test_chart_scatter_points_is_deterministic() -> None:
    params = {"query_id": "category_threshold_point_count", "threshold_axis": "y", "threshold_direction": "below"}
    task = ChartsScatterPointsCategoryThresholdPointCountTask()
    out_a = task.generate(142600, params=params, max_attempts=80)
    out_b = task.generate(142600, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_chart_scatter_points_registered_and_group_config_loaded() -> None:
    assert (
        create_task("task_charts__scatter_points__axis_threshold_point_count").task_id
        == "task_charts__scatter_points__axis_threshold_point_count"
    )
    assert (
        create_task("task_charts__scatter_points__category_axis_mean_extremum_label").task_id
        == "task_charts__scatter_points__category_axis_mean_extremum_label"
    )
    assert (
        create_task("task_charts__scatter_points__category_threshold_point_count").task_id
        == "task_charts__scatter_points__category_threshold_point_count"
    )

    cfg = get_task_group_defaults("charts", "scatter")
    generation = cfg["generation"]["task_overrides"]["charts_scatter_points_query_base"]
    assert int(generation["scatter_points_count_min"]) == 28
    assert int(generation["scatter_points_count_max"]) == 54
    assert sorted(generation["query_id_weights"]) == sorted(query_id for _task, query_id, _answer in CASES)

    prompt = cfg["prompt"]["task_overrides"]["charts_scatter_points_query_base"]
    assert str(prompt["scene_key"]) == "scatter_points"
    assert str(prompt["task_key"]) == "scatter_points_query"
