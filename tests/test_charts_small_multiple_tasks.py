"""Behavior tests for chart small-multiple composition tasks."""

from __future__ import annotations

from typing import Any

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks import TASK_REGISTRY
from trace.tasks.charts.small_multiple.average_top_k_minus_average_bottom_k import (
    ChartsCompositionSmallMultiplesAverageTopKMinusAverageBottomKTask,
)
from trace.tasks.charts.small_multiple.composition_shift_l1_distance import (
    ChartsCompositionSmallMultiplesCompositionShiftL1DistanceTask,
)
from trace.tasks.charts.small_multiple.conditioned_panel_sum_from_percent import (
    ChartsCompositionSmallMultiplesConditionedPanelSumFromPercentTask,
)
from trace.tasks.charts.small_multiple.shared.state import SUPPORTED_SCENE_VARIANTS
from trace.tasks.charts.small_multiple.top_k_by_segment_then_sum_other_segment_count import (
    ChartsCompositionSmallMultiplesTopKBySegmentThenSumOtherSegmentCountTask,
)


TASK_CASES = (
    (
        "task_charts__small_multiple__top_k_by_segment_then_sum_other_segment_count",
        ChartsCompositionSmallMultiplesTopKBySegmentThenSumOtherSegmentCountTask,
    ),
    (
        "task_charts__small_multiple__conditioned_panel_sum_from_percent",
        ChartsCompositionSmallMultiplesConditionedPanelSumFromPercentTask,
    ),
    (
        "task_charts__small_multiple__average_top_k_minus_average_bottom_k",
        ChartsCompositionSmallMultiplesAverageTopKMinusAverageBottomKTask,
    ),
    (
        "task_charts__small_multiple__composition_shift_l1_distance",
        ChartsCompositionSmallMultiplesCompositionShiftL1DistanceTask,
    ),
)


def _assert_point_inside_canvas(point: list[float], *, width: int, height: int) -> None:
    assert len(point) == 2
    assert 0 <= float(point[0]) <= int(width)
    assert 0 <= float(point[1]) <= int(height)


def _expected_answer(task_id: str, execution: dict[str, Any]) -> int:
    if task_id.endswith("__top_k_by_segment_then_sum_other_segment_count"):
        return int(sum(int(value) for value in execution["selected_target_counts"]))
    if task_id.endswith("__conditioned_panel_sum_from_percent"):
        return int(sum(int(value) for value in execution["selected_target_counts"]))
    if task_id.endswith("__average_top_k_minus_average_bottom_k"):
        return int(execution["top_average"]) - int(execution["bottom_average"])
    if task_id.endswith("__composition_shift_l1_distance"):
        return int(sum(int(value) for value in execution["segment_changes"]))
    raise AssertionError(f"unsupported task: {task_id}")


@pytest.mark.parametrize(("task_id", "task_cls"), TASK_CASES)
@pytest.mark.parametrize("scene_variant", SUPPORTED_SCENE_VARIANTS)
def test_chart_small_multiple_tasks_match_contract(task_id: str, task_cls: type, scene_variant: str) -> None:
    task = task_cls()
    out = task.generate(79200 + len(task_id) + len(scene_variant), params={"scene_variant": scene_variant}, max_attempts=160)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    projected = trace["projected_annotation"]

    assert out.query_id == SINGLE_QUERY_ID
    assert task.supported_query_ids == (SINGLE_QUERY_ID,)
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_map"
    assert str(execution["scene_variant"]) == str(scene_variant)
    assert str(render["scene_variant"]) == str(scene_variant)
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["panel_count"]) == len(execution["panels"])
    assert int(execution["segment_count"]) == len(execution["segment_labels"])
    assert int(out.answer_gt.value) == int(execution["answer_value"])
    assert int(out.answer_gt.value) == _expected_answer(str(task_id), execution)
    assert trace["query_spec"]["query_id"] == SINGLE_QUERY_ID
    assert trace["query_spec"]["params"]["query_id"] == SINGLE_QUERY_ID
    assert str(execution["program_code"])

    assert projected["type"] == "point_map"
    assert projected["point_map"] == dict(out.annotation_gt.value)
    assert projected["pixel_point_map"] == dict(out.annotation_gt.value)
    assert set(out.annotation_gt.value) == set(execution["annotation_point_keys"])
    assert len(projected["point_set"]) == len(out.annotation_gt.value)
    assert len(execution["annotation_roles"]) == len(out.annotation_gt.value)
    for point in out.annotation_gt.value.values():
        _assert_point_inside_canvas([float(value) for value in point], width=int(render["canvas_width"]), height=int(render["canvas_height"]))


def test_chart_small_multiple_prompt_examples_match_contract() -> None:
    for _task_id, task_cls in TASK_CASES:
        task = task_cls()
        out = task.generate(79300 + len(task.task_id), params={}, max_attempts=160)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert isinstance(answer_and_annotation["annotation"], dict)
        assert isinstance(answer_and_annotation["answer"], int)
        assert isinstance(answer_only["answer"], int)


def test_chart_small_multiple_tasks_are_registered_and_reject_unsupported_query() -> None:
    for task_id, task_cls in TASK_CASES:
        assert task_id in TASK_REGISTRY
        task = task_cls()
        with pytest.raises(ValueError, match="query_id"):
            task.generate(79400, params={"query_id": "__unsupported_query_id__"}, max_attempts=10)


def test_chart_small_multiple_is_deterministic() -> None:
    task = ChartsCompositionSmallMultiplesCompositionShiftL1DistanceTask()
    params = {"scene_variant": "small_multiple_donut"}
    out_a = task.generate(79500, params=params, max_attempts=160)
    out_b = task.generate(79500, params=params, max_attempts=160)
    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
