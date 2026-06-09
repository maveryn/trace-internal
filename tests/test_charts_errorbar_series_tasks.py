"""Behavior tests for scientific error-bar series chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.charts.errorbar_series.series_query import (
    BOUND_EXTREMUM_QUERY_IDS,
    OVERLAP_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    THRESHOLD_QUERY_IDS,
    ChartsErrorbarSeriesBoundExtremumXLabelTask,
    ChartsErrorbarSeriesSameXIntervalOverlapCountTask,
    ChartsErrorbarSeriesThresholdSupportCountTask,
)
from trace.tasks.registry import list_default_task_ids


TASK_CASES = (
    (ChartsErrorbarSeriesThresholdSupportCountTask, THRESHOLD_QUERY_IDS, "integer", "bbox_set"),
    (ChartsErrorbarSeriesBoundExtremumXLabelTask, BOUND_EXTREMUM_QUERY_IDS, "string", "keyed_point_map"),
    (ChartsErrorbarSeriesSameXIntervalOverlapCountTask, OVERLAP_QUERY_IDS, "integer", "keyed_bbox_map"),
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _assert_point_inside_canvas(point: list[float], *, width: int, height: int) -> None:
    assert len(point) == 2
    x, y = [float(value) for value in point]
    assert 0 <= x <= width
    assert 0 <= y <= height


def _series_by_id(execution: dict) -> dict[str, dict]:
    return {str(series["series_id"]): dict(series) for series in execution["series"]}


def _expected_answer(execution: dict, query_id: str) -> int | str:
    target = _series_by_id(execution)[str(execution["target_series_id"])]
    if query_id == "entirely_above_threshold_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for lower in target["lower_values"] if int(lower) > threshold)
    if query_id == "entirely_below_threshold_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for upper in target["upper_values"] if int(upper) < threshold)
    if query_id == "contains_threshold_count":
        threshold = int(execution["threshold_value"])
        return sum(
            1
            for lower, upper in zip(target["lower_values"], target["upper_values"])
            if int(lower) <= threshold <= int(upper)
        )
    if query_id == "highest_upper_bound_x_label":
        index = max(range(int(execution["x_count"])), key=lambda idx: int(target["upper_values"][idx]))
        return str(execution["x_labels"][int(index)])
    if query_id == "lowest_lower_bound_x_label":
        index = min(range(int(execution["x_count"])), key=lambda idx: int(target["lower_values"][idx]))
        return str(execution["x_labels"][int(index)])
    if query_id == "overlap_target_errorbar_at_x_count":
        target_x = int(execution["target_x_index"])
        target_low = int(target["lower_values"][target_x])
        target_high = int(target["upper_values"][target_x])
        count = 0
        for series in execution["series"]:
            if str(series["series_id"]) == str(execution["target_series_id"]):
                continue
            low = int(series["lower_values"][target_x])
            high = int(series["upper_values"][target_x])
            if max(target_low, low) <= min(target_high, high):
                count += 1
        return int(count)
    raise AssertionError(f"unsupported query_id: {query_id}")


@pytest.mark.parametrize(("task_cls", "query_ids", "answer_type", "annotation_type"), TASK_CASES)
def test_charts_errorbar_series_tasks_match_contract(
    task_cls: type,
    query_ids: tuple[str, ...],
    answer_type: str,
    annotation_type: str,
) -> None:
    task = task_cls()
    for query_id in query_ids:
        out = task.generate(hash64(20260605, task_cls.task_id, len(query_id)), params={"query_id": query_id}, max_attempts=80)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        assert task_cls.task_id in list_default_task_ids()
        assert out.scene_id == "errorbar_series"
        assert out.query_id == query_id
        assert str(execution["query_id"]) == query_id
        assert str(execution["question_format"]) == "errorbar_series"
        assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
        assert out.answer_gt.type == answer_type
        assert out.annotation_gt.type == annotation_type
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 5 <= int(execution["x_count"]) <= 8
        if query_id == "overlap_target_errorbar_at_x_count":
            assert int(execution["series_count"]) == 5
        else:
            assert 2 <= int(execution["series_count"]) <= 4

        expected = _expected_answer(execution, query_id)
        assert out.answer_gt.value == expected
        assert execution["answer_value"] == expected

        if annotation_type == "bbox_set":
            assert int(out.answer_gt.value) == len(out.annotation_gt.value)
            assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
            for bbox in out.annotation_gt.value:
                _assert_bbox_inside_canvas(
                    [float(value) for value in bbox],
                    width=int(render["canvas_width"]),
                    height=int(render["canvas_height"]),
                )
        elif annotation_type == "keyed_point_map":
            assert set(out.annotation_gt.value.keys()) == {"selected_bound_endpoint"}
            assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
            _assert_point_inside_canvas(
                [float(value) for value in out.annotation_gt.value["selected_bound_endpoint"]],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )
        else:
            assert "target_errorbar" in out.annotation_gt.value
            assert len(out.annotation_gt.value) - 1 == int(out.answer_gt.value)
            assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
            for bbox in out.annotation_gt.value.values():
                _assert_bbox_inside_canvas(
                    [float(value) for value in bbox],
                    width=int(render["canvas_width"]),
                    height=int(render["canvas_height"]),
                )

        complexity = out.complexity.to_dict()
        assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
        assert set(complexity["complexity_components"].keys()) == {
            "reasoning_load",
            "scene_variant_load",
            "visual_scan",
        }


def test_charts_errorbar_series_prompt_examples_match_contract() -> None:
    for task_cls, _query_ids, answer_type, annotation_type in TASK_CASES:
        out = task_cls().generate(hash64(20260605, f"{task_cls.task_id}.prompt", len(task_cls.task_id)), params={}, max_attempts=80)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        if answer_type == "integer":
            assert isinstance(answer_and_annotation["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_annotation["answer"], str)
            assert isinstance(answer_only["answer"], str)
            assert len(answer_and_annotation["answer"]) > 1
        if annotation_type == "bbox_set":
            assert isinstance(answer_and_annotation["annotation"], list)
        else:
            assert isinstance(answer_and_annotation["annotation"], dict)


def test_charts_errorbar_series_balanced_sampling_covers_axes() -> None:
    query_counts: Counter[str] = Counter()
    scene_counts: Counter[str] = Counter()
    for index in range(72):
        out = ChartsErrorbarSeriesThresholdSupportCountTask().generate(
            hash64(20260605, "charts_errorbar_series_axes", index),
            params={},
            max_attempts=80,
        )
        query_counts[str(out.query_id)] += 1
        scene_counts[str(out.trace_payload["execution_trace"]["scene_variant"])] += 1
    assert set(query_counts) == set(THRESHOLD_QUERY_IDS)
    assert set(scene_counts) == set(SUPPORTED_SCENE_VARIANTS)


def test_charts_errorbar_series_is_deterministic() -> None:
    params = {"query_id": "overlap_target_errorbar_at_x_count", "scene_variant": "grouped_errorbar"}
    out_a = ChartsErrorbarSeriesSameXIntervalOverlapCountTask().generate(2026060501, params=params, max_attempts=80)
    out_b = ChartsErrorbarSeriesSameXIntervalOverlapCountTask().generate(2026060501, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_charts_errorbar_series_registry_and_config_are_wired() -> None:
    defaults = get_task_group_defaults("charts", "errorbar_series")
    prompt = defaults["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_errorbar_series_v0"
    assert str(prompt["scene_key"]) == "errorbar_series_scene"
    assert str(prompt["task_key"]) == "errorbar_series_query"
    assert ChartsErrorbarSeriesThresholdSupportCountTask.task_id in list_default_task_ids()
    assert ChartsErrorbarSeriesBoundExtremumXLabelTask.task_id in list_default_task_ids()
    assert ChartsErrorbarSeriesSameXIntervalOverlapCountTask.task_id in list_default_task_ids()
