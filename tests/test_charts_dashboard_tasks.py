"""Behavior tests for mixed-dashboard chart tasks."""
from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.scene_config import get_scene_defaults
from trace.tasks import create_task
from trace.tasks.charts.dashboard.category_panel_condition_count import ChartsDashboardCategoryPanelConditionCountTask
from trace.tasks.charts.dashboard.dual_condition_count import ChartsDashboardDualConditionCountTask
from trace.tasks.charts.dashboard.dual_source_target_sum_value import ChartsDashboardDualSourceTargetSumValueTask
from trace.tasks.charts.dashboard.panel_gap_extremum_category_label import ChartsDashboardPanelGapExtremumCategoryLabelTask
from trace.tasks.charts.dashboard.shared.state import SUPPORTED_PANEL_KINDS, SUPPORTED_SCENE_VARIANTS
from trace.tasks.charts.dashboard.shared_label_rank_gap_extremum import ChartsDashboardSharedLabelRankGapExtremumTask
from trace.tasks.charts.dashboard.source_rank_difference_value import ChartsDashboardSourceRankDifferenceValueTask
from trace.tasks.charts.dashboard.source_rank_target_value import ChartsDashboardSourceRankTargetValueTask
from trace.tasks.charts.dashboard.statement_option_selection_label import ChartsDashboardStatementOptionSelectionLabelTask
from trace.tasks.charts.dashboard.top_k_overlap_count import ChartsDashboardTopKOverlapCountTask

TASK_CASES = (
    ("task_charts__dashboard__category_panel_condition_count", ChartsDashboardCategoryPanelConditionCountTask, "category_panel_condition_count", "integer", "point_set"),
    ("task_charts__dashboard__dual_condition_count", ChartsDashboardDualConditionCountTask, "dual_condition_count", "integer", "point_set"),
    ("task_charts__dashboard__dual_source_target_sum_value", ChartsDashboardDualSourceTargetSumValueTask, "dual_source_target_sum_value", "integer", "keyed_point_map"),
    ("task_charts__dashboard__panel_gap_extremum_category_label", ChartsDashboardPanelGapExtremumCategoryLabelTask, "panel_gap_extremum_category_label", "string", "keyed_point_map"),
    ("task_charts__dashboard__shared_label_rank_gap_extremum", ChartsDashboardSharedLabelRankGapExtremumTask, "shared_label_rank_gap_extremum", "string", "keyed_point_map"),
    ("task_charts__dashboard__source_rank_difference_value", ChartsDashboardSourceRankDifferenceValueTask, "source_rank_difference_value", "integer", "keyed_point_map"),
    ("task_charts__dashboard__source_rank_target_value", ChartsDashboardSourceRankTargetValueTask, "source_rank_target_value", "integer", "keyed_point_map"),
    ("task_charts__dashboard__statement_option_selection_label", ChartsDashboardStatementOptionSelectionLabelTask, "statement_option_selection_label", "option_letter", "keyed_point_map"),
    ("task_charts__dashboard__top_k_overlap_count", ChartsDashboardTopKOverlapCountTask, "top_k_overlap_count", "integer", "point_set"),
)
TASK_IDS = tuple(case[0] for case in TASK_CASES)
QUERY_IDS = tuple(case[2] for case in TASK_CASES)


def _assert_point_inside_canvas(point: list[float], *, width: int, height: int) -> None:
    assert len(point) == 2
    x, y = [float(value) for value in point]
    assert 0 <= x < width
    assert 0 <= y < height


def _value(execution: dict[str, Any], panel_id: str, category_id: str) -> int:
    return int(execution["values_by_panel"][str(panel_id)]["values_by_category_id"][str(category_id)])


def _rank_positions(execution: dict[str, Any], panel_id: str, direction: str) -> dict[str, int]:
    reverse = str(direction) == "largest"
    ordered = sorted(execution["categories"], key=lambda category: _value(execution, str(panel_id), str(category["category_id"])), reverse=reverse)
    return {str(category["category_id"]): int(index + 1) for index, category in enumerate(ordered)}


def _expected_answer(execution: dict[str, Any]) -> int | str:
    variant = str(execution["query_id"])
    if variant == "source_rank_target_value":
        return _value(execution, execution["target_panel_id"], execution["selected_category_id"])
    if variant == "source_rank_difference_value":
        category_id = str(execution["selected_category_id"])
        return abs(_value(execution, execution["source_panel_id"], category_id) - _value(execution, execution["target_panel_id"], category_id))
    if variant == "dual_source_target_sum_value":
        return _value(execution, execution["target_panel_id"], execution["first_category_id"]) + _value(execution, execution["target_panel_id"], execution["second_category_id"])
    if variant == "dual_condition_count":
        first_panel_id = str(execution["first_condition_panel_id"])
        second_panel_id = str(execution["second_condition_panel_id"])
        first_threshold = int(execution["first_threshold"])
        second_threshold = int(execution["second_threshold"])
        first_comparison = str(execution["first_condition_comparison"])
        second_comparison = str(execution["second_condition_comparison"])
        total = 0
        for category in execution["categories"]:
            category_id = str(category["category_id"])
            first_value = _value(execution, first_panel_id, category_id)
            second_value = _value(execution, second_panel_id, category_id)
            first_match = first_value > first_threshold if first_comparison == "greater_than" else first_value < first_threshold
            second_match = second_value > second_threshold if second_comparison == "greater_than" else second_value < second_threshold
            total += int(bool(first_match and second_match))
        return int(total)
    if variant == "panel_gap_extremum_category_label":
        if str(execution.get("answerability", "answerable")) == "unanswerable":
            return "unanswerable"
        first_panel_id = str(execution["first_gap_panel_id"])
        second_panel_id = str(execution["second_gap_panel_id"])
        reverse = str(execution["gap_extremum_direction"]) == "largest"
        gaps = {str(category["category_id"]): abs(_value(execution, first_panel_id, str(category["category_id"])) - _value(execution, second_panel_id, str(category["category_id"]))) for category in execution["categories"]}
        answer_category_id = sorted(gaps, key=lambda category_id: gaps[category_id], reverse=reverse)[0]
        labels = {str(category["category_id"]): str(category["label"]) for category in execution["categories"]}
        return labels[answer_category_id]
    if variant == "shared_label_rank_gap_extremum":
        first_panel_id = str(execution["first_rank_gap_panel_id"])
        second_panel_id = str(execution["second_rank_gap_panel_id"])
        first_ranks = _rank_positions(execution, first_panel_id, str(execution["rank_direction"]))
        second_ranks = _rank_positions(execution, second_panel_id, str(execution["rank_direction"]))
        gaps = {str(category["category_id"]): abs(int(first_ranks[str(category["category_id"])]) - int(second_ranks[str(category["category_id"])])) for category in execution["categories"]}
        reverse = str(execution["gap_extremum_direction"]) == "largest"
        target_gap = max(gaps.values()) if reverse else min(gaps.values())
        assert sum(1 for gap in gaps.values() if int(gap) == int(target_gap)) == 1
        answer_category_id = sorted(gaps, key=lambda category_id: gaps[category_id], reverse=reverse)[0]
        labels = {str(category["category_id"]): str(category["label"]) for category in execution["categories"]}
        assert int(execution["answer_rank_gap"]) == int(target_gap)
        assert int(execution["first_rank_position"]) == int(first_ranks[answer_category_id])
        assert int(execution["second_rank_position"]) == int(second_ranks[answer_category_id])
        return labels[answer_category_id]
    if variant == "statement_option_selection_label":
        requested_truth = str(execution["requested_truth"]) == "true"
        matching_options: list[dict[str, Any]] = []
        for option in execution["statement_options"]:
            first_value = _value(execution, str(option["first_panel_id"]), str(option["first_category_id"]))
            second_value = _value(execution, str(option["second_panel_id"]), str(option["second_category_id"]))
            if str(option["comparison"]) == "greater_than":
                truth_value = first_value > second_value
            elif str(option["comparison"]) == "less_than":
                truth_value = first_value < second_value
            else:
                raise AssertionError(f"unsupported comparison: {option['comparison']}")
            assert bool(option["truth_value"]) is bool(truth_value)
            if bool(truth_value) is bool(requested_truth):
                matching_options.append(option)
        assert len(matching_options) == 1
        selected = matching_options[0]
        assert selected == execution["selected_statement"]
        assert str(selected["option_label"]) == str(execution["answer_option_label"])
        return str(selected["option_label"])
    if variant == "top_k_overlap_count":
        return len(execution["overlap_category_ids"])
    if variant == "category_panel_condition_count":
        category_id = str(execution["condition_category_id"])
        threshold = int(execution["panel_threshold"])
        comparison = str(execution["panel_condition_comparison"])
        total = 0
        for panel in execution["panels"]:
            panel_id = str(panel["panel_id"])
            value = _value(execution, panel_id, category_id)
            match = value > threshold if comparison == "greater_than" else value < threshold
            total += int(bool(match))
        return int(total)
    raise AssertionError(f"unsupported variant: {variant}")


@pytest.mark.parametrize("case_index, case", tuple(enumerate(TASK_CASES)))
def test_chart_dashboard_tasks_match_contract(case_index: int, case: tuple[str, type, str, str, str]) -> None:
    task_id, task_cls, query_id, answer_type, annotation_type = case
    task = task_cls()
    out = task.generate(hash64(20260503, "charts_dashboard", case_index), params={"query_id": query_id}, max_attempts=120)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    assert task.task_id == task_id
    assert out.query_id == query_id
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert str(execution["question_format"]) == "dashboard_cross_panel_query"
    assert out.annotation_gt.type == annotation_type
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 4 <= int(execution["category_count"]) <= 12
    assert 4 <= int(execution["panel_count"]) <= 9
    assert len(execution["panel_order"]) == int(execution["panel_count"])
    assert len({str(item) for item in execution["panel_order"]}) == int(execution["panel_count"])
    assert all(str(kind) in SUPPORTED_PANEL_KINDS for kind in execution["panel_kinds"])
    assert len(execution["panels"]) == int(execution["panel_count"])
    expected_answer = _expected_answer(execution)
    assert out.answer_gt.type == answer_type
    assert out.answer_gt.value == expected_answer
    assert execution["answer"] == expected_answer
    expected_points = [list(trace["render_map"]["support_points_px"][str(panel_id)][str(category_id)]) for panel_id, category_id in execution["annotation_refs"]]
    assert trace["projected_annotation"]["type"] == out.annotation_gt.type
    assert len(trace["projected_annotation"]["annotation_refs"]) == len(expected_points)
    if out.annotation_gt.type == "point_set":
        assert out.annotation_gt.value == expected_points
        assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
        for point in out.annotation_gt.value:
            _assert_point_inside_canvas([float(value) for value in point], width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    else:
        assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
        for point in out.annotation_gt.value.values():
            _assert_point_inside_canvas([float(value) for value in point], width=int(render["canvas_width"]), height=int(render["canvas_height"]))
        if query_id in {"source_rank_target_value", "source_rank_difference_value"}:
            assert out.annotation_gt.value == {"source_panel": expected_points[0], "target_panel": expected_points[1]}
        if query_id == "dual_source_target_sum_value":
            assert out.annotation_gt.value == {"first_source_panel": expected_points[0], "second_source_panel": expected_points[1], "target_first_category": expected_points[2], "target_second_category": expected_points[3]}
        if query_id in {"panel_gap_extremum_category_label", "shared_label_rank_gap_extremum"} and expected_points:
            assert out.annotation_gt.value == {"first_panel": expected_points[0], "second_panel": expected_points[1]}
        if query_id == "statement_option_selection_label":
            assert out.annotation_gt.value == {"first_mark": expected_points[0], "second_mark": expected_points[1]}
    if query_id == "dual_condition_count":
        assert len(out.annotation_gt.value) == int(out.answer_gt.value) * 2
    if query_id == "top_k_overlap_count":
        assert len(out.annotation_gt.value) == int(out.answer_gt.value) * 2
    if query_id == "category_panel_condition_count":
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    if query_id == "panel_gap_extremum_category_label" and str(execution.get("answerability")) == "unanswerable":
        assert out.annotation_gt.value == {}
    if query_id == "statement_option_selection_label":
        assert int(execution["option_count"]) in {4, 6}
        assert len(execution["statement_options"]) == int(execution["option_count"])
        assert out.answer_gt.value in execution["option_labels"]
        for option in execution["statement_options"]:
            assert str(option["text"]) not in out.prompt
            assert f"option_{option['option_label']}" in trace["render_map"]["option_statement_bboxes_px"]


@pytest.mark.parametrize("task_id, task_cls, query_id, answer_type, annotation_type", TASK_CASES)
def test_chart_dashboard_prompt_examples_match_contract(task_id: str, task_cls: type, query_id: str, answer_type: str, annotation_type: str) -> None:
    del task_id, query_id, annotation_type
    out = task_cls().generate(hash64(93100, task_cls.__name__), params={}, max_attempts=120)
    answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert "annotation" in answer_and_annotation
    if answer_type == "integer":
        assert isinstance(answer_and_annotation["answer"], int)
        assert isinstance(answer_only["answer"], int)
    else:
        assert isinstance(answer_and_annotation["answer"], str)
        assert isinstance(answer_only["answer"], str)


@pytest.mark.parametrize("option_count", [4, 6])
@pytest.mark.parametrize("requested_truth", ["true", "false"])
def test_chart_dashboard_statement_option_selection_contract(option_count: int, requested_truth: str) -> None:
    task = ChartsDashboardStatementOptionSelectionLabelTask()
    out = task.generate(hash64(20260604, "charts_dashboard_statement_option", option_count, requested_truth), params={"option_count": option_count, "requested_truth": requested_truth}, max_attempts=160)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    assert out.query_id == "statement_option_selection_label"
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "keyed_point_map"
    assert set(out.annotation_gt.value) == {"first_mark", "second_mark"}
    assert int(execution["option_count"]) == int(option_count)
    assert str(execution["requested_truth"]) == str(requested_truth)
    assert len(execution["statement_options"]) == int(option_count)
    assert len(trace["render_map"]["option_statement_bboxes_px"]) == int(option_count)
    expected_answer = _expected_answer(execution)
    assert out.answer_gt.value == expected_answer
    selected = execution["selected_statement"]
    expected_refs = [[str(selected["first_panel_id"]), str(selected["first_category_id"])], [str(selected["second_panel_id"]), str(selected["second_category_id"])]]
    assert execution["annotation_refs"] == expected_refs
    expected_points = [list(trace["render_map"]["support_points_px"][panel_id][category_id]) for panel_id, category_id in expected_refs]
    assert out.annotation_gt.value == {"first_mark": expected_points[0], "second_mark": expected_points[1]}
    for option in execution["statement_options"]:
        assert str(option["text"]) not in out.prompt


def test_chart_dashboard_all_tasks_are_deterministic() -> None:
    for task_index, (_task_id, task_cls, query_id, _answer_type, _annotation_type) in enumerate(TASK_CASES):
        params = {"query_id": query_id}
        if query_id == "dual_condition_count":
            params["first_condition_comparison"] = "greater_than"
        out_a = task_cls().generate(hash64(93300, task_index), params=params, max_attempts=120)
        out_b = task_cls().generate(hash64(93300, task_index), params=params, max_attempts=120)
        assert out_a.prompt == out_b.prompt
        assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
        assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
        assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]


def test_chart_dashboard_registered_and_scene_config_loaded() -> None:
    for task_id in TASK_IDS:
        assert create_task(task_id).task_id == task_id
    cfg = get_scene_defaults("charts", "dashboard")
    assert isinstance(cfg.get("generation"), dict)
    assert isinstance(cfg.get("rendering"), dict)
    assert isinstance(cfg.get("prompt"), dict)
    generation = cfg["generation"]["shared"]
    assert "query_id_weights" not in generation
    assert int(generation["panel_count_min"]) == 4
    assert int(generation["panel_count_max"]) == 9
    assert int(generation["category_count_min"]) == 4
    assert int(generation["category_count_max"]) == 12
    assert sorted(generation["panel_kind_weights"].keys()) == sorted(SUPPORTED_PANEL_KINDS)
    prompt = cfg["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_dashboard_v1"
    assert str(prompt["scene_key"]) == "dashboard_mixed_chart"
    assert str(prompt["task_key"]) == "dashboard_cross_panel_query"


def test_chart_dashboard_sampling_covers_scene_ranges() -> None:
    category_counts: Counter[int] = Counter()
    panel_counts: Counter[int] = Counter()
    answer_types: Counter[str] = Counter()
    for task_index, (_task_id, task_cls, query_id, _answer_type, _annotation_type) in enumerate(TASK_CASES):
        for sample_index in range(16):
            out = task_cls().generate(hash64(93200, task_index, sample_index), params={"query_id": query_id}, max_attempts=160)
            execution = out.trace_payload["execution_trace"]
            category_counts[int(execution["category_count"])] += 1
            panel_counts[int(execution["panel_count"])] += 1
            answer_types[str(out.answer_gt.type)] += 1
    assert set(category_counts).issubset({4, 5, 6, 7, 8, 9, 10, 11, 12})
    assert set(panel_counts).issubset({4, 5, 6, 7, 8, 9})
    assert {"integer", "option_letter", "string"}.issubset(set(answer_types))
