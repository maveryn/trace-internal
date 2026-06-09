"""Behavior tests for mixed-dashboard chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import assert_counter_support_within, extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks import create_task
from trace.tasks.charts.dashboard.cross_panel_query import (
    SUPPORTED_PANEL_KINDS,
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_QUERY_IDS,
    ChartsDashboardCrossPanelQueryTask,
    ChartsDashboardStatementOptionSelectionLabelTask,
)


def _assert_point_inside_canvas(point: list[float], *, width: int, height: int) -> None:
    assert len(point) == 2
    x, y = [float(value) for value in point]
    assert 0 <= x < width
    assert 0 <= y < height


def _value(execution: dict, panel_id: str, category_id: str) -> int:
    return int(execution["values_by_panel"][str(panel_id)]["values_by_category_id"][str(category_id)])


def _rank_positions(execution: dict, panel_id: str, direction: str) -> dict[str, int]:
    reverse = str(direction) == "largest"
    ordered = sorted(
        execution["categories"],
        key=lambda category: _value(execution, str(panel_id), str(category["category_id"])),
        reverse=reverse,
    )
    return {
        str(category["category_id"]): int(index + 1)
        for index, category in enumerate(ordered)
    }


def _expected_answer(execution: dict) -> int | str:
    variant = str(execution["query_id"])

    if variant == "source_rank_target_value":
        return _value(execution, execution["target_panel_id"], execution["selected_category_id"])

    if variant == "source_rank_difference_value":
        category_id = str(execution["selected_category_id"])
        return abs(
            _value(execution, execution["source_panel_id"], category_id)
            - _value(execution, execution["target_panel_id"], category_id)
        )

    if variant == "dual_source_target_sum_value":
        return (
            _value(execution, execution["target_panel_id"], execution["first_category_id"])
            + _value(execution, execution["target_panel_id"], execution["second_category_id"])
        )

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
        first_panel_id = str(execution["first_gap_panel_id"])
        second_panel_id = str(execution["second_gap_panel_id"])
        reverse = str(execution["gap_extremum_direction"]) == "largest"
        gaps = {
            str(category["category_id"]): abs(
                _value(execution, first_panel_id, str(category["category_id"]))
                - _value(execution, second_panel_id, str(category["category_id"]))
            )
            for category in execution["categories"]
        }
        answer_category_id = sorted(gaps, key=lambda category_id: gaps[category_id], reverse=reverse)[0]
        labels = {str(category["category_id"]): str(category["label"]) for category in execution["categories"]}
        return labels[answer_category_id]

    if variant == "shared_label_rank_gap_extremum":
        first_panel_id = str(execution["first_rank_gap_panel_id"])
        second_panel_id = str(execution["second_rank_gap_panel_id"])
        first_ranks = _rank_positions(execution, first_panel_id, str(execution["rank_direction"]))
        second_ranks = _rank_positions(execution, second_panel_id, str(execution["rank_direction"]))
        gaps = {
            str(category["category_id"]): abs(
                int(first_ranks[str(category["category_id"])])
                - int(second_ranks[str(category["category_id"])])
            )
            for category in execution["categories"]
        }
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
        matching_options: list[dict] = []
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


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_chart_dashboard_variants_match_contract(query_id: str) -> None:
    task = ChartsDashboardCrossPanelQueryTask()
    out = task.generate(
        hash64(20260503, "charts_dashboard", SUPPORTED_QUERY_IDS.index(query_id)),
        params={"query_id": query_id},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_id == query_id
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert str(execution["question_format"]) == "dashboard_cross_panel_query"
    if query_id in {
        "source_rank_target_value",
        "source_rank_difference_value",
        "dual_source_target_sum_value",
        "panel_gap_extremum_category_label",
        "shared_label_rank_gap_extremum",
        "statement_option_selection_label",
    }:
        assert out.annotation_gt.type == "keyed_point_map"
    else:
        assert out.annotation_gt.type == "point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 4 <= int(execution["category_count"]) <= 12
    assert 4 <= int(execution["panel_count"]) <= 9
    assert len(execution["panel_order"]) == int(execution["panel_count"])
    assert len(set(str(item) for item in execution["panel_order"])) == int(execution["panel_count"])
    assert all(str(kind) in SUPPORTED_PANEL_KINDS for kind in execution["panel_kinds"])
    assert len(execution["panels"]) == int(execution["panel_count"])

    expected_answer = _expected_answer(execution)
    assert out.answer_gt.value == expected_answer
    assert execution["answer"] == expected_answer
    if query_id == "statement_option_selection_label":
        assert out.answer_gt.type == "option_letter"
    elif query_id in {"panel_gap_extremum_category_label", "shared_label_rank_gap_extremum"}:
        assert out.answer_gt.type == "string"
    else:
        assert out.answer_gt.type == "integer"

    expected_points = [
        list(trace["render_map"]["support_points_px"][str(panel_id)][str(category_id)])
        for panel_id, category_id in execution["annotation_refs"]
    ]
    assert trace["projected_annotation"]["type"] == out.annotation_gt.type
    assert len(trace["projected_annotation"]["annotation_refs"]) == len(expected_points)

    if out.annotation_gt.type == "point_set":
        assert out.annotation_gt.value == expected_points
        assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
        assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value
        for point in out.annotation_gt.value:
            _assert_point_inside_canvas(
                [float(value) for value in point],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )
    else:
        assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
        assert trace["projected_annotation"]["pixel_keyed_point_map"] == out.annotation_gt.value
        for point in out.annotation_gt.value.values():
            _assert_point_inside_canvas(
                [float(value) for value in point],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )
        if query_id in {"source_rank_target_value", "source_rank_difference_value"}:
            assert out.annotation_gt.value == {"source_panel": expected_points[0], "target_panel": expected_points[1]}
        if query_id == "dual_source_target_sum_value":
            assert out.annotation_gt.value == {
                "first_source_panel": expected_points[0],
                "second_source_panel": expected_points[1],
                "target_first_category": expected_points[2],
                "target_second_category": expected_points[3],
            }
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
    if query_id in {"panel_gap_extremum_category_label", "shared_label_rank_gap_extremum"}:
        assert len(out.annotation_gt.value) == 2
    if query_id == "statement_option_selection_label":
        assert len(out.annotation_gt.value) == 2
        assert 4 <= int(execution["option_count"]) <= 6
        assert len(execution["statement_options"]) == int(execution["option_count"])
        assert out.answer_gt.value in execution["option_labels"]
        for option in execution["statement_options"]:
            assert str(option["text"]) not in out.prompt
            assert f"option_{option['option_label']}" in trace["render_map"]["option_statement_bboxes_px"]

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }


def test_chart_dashboard_prompt_examples_match_contract() -> None:
    task = ChartsDashboardCrossPanelQueryTask()
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS, start=93100):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=100)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert "annotation" in answer_and_annotation
        if query_id == "statement_option_selection_label":
            assert isinstance(answer_and_annotation["answer"], str)
            assert isinstance(answer_only["answer"], str)
            assert len(answer_and_annotation["answer"]) == 1
        elif query_id in {"panel_gap_extremum_category_label", "shared_label_rank_gap_extremum"}:
            assert isinstance(answer_and_annotation["answer"], str)
            assert isinstance(answer_only["answer"], str)
        else:
            assert isinstance(answer_and_annotation["answer"], int)
            assert isinstance(answer_only["answer"], int)


def test_chart_dashboard_balanced_sampling_covers_variants() -> None:
    task = ChartsDashboardCrossPanelQueryTask()
    variants: Counter[str] = Counter()
    category_counts: Counter[int] = Counter()
    panel_counts: Counter[int] = Counter()
    duplicate_kind_instances = 0
    answer_types: Counter[str] = Counter()

    for index in range(135):
        out = task.generate(hash64(93200, "charts_dashboard", index), params={}, max_attempts=160)
        execution = out.trace_payload["execution_trace"]
        variants[str(execution["query_id"])] += 1
        category_counts[int(execution["category_count"])] += 1
        panel_counts[int(execution["panel_count"])] += 1
        duplicate_kind_instances += int(len(set(str(kind) for kind in execution["panel_kinds"])) < int(execution["panel_count"]))
        answer_types[str(out.answer_gt.type)] += 1

    assert_counter_support_within(variants, SUPPORTED_QUERY_IDS, expected_per_key=15, tolerance=10)
    assert set(category_counts).issubset({4, 5, 6, 7, 8, 9, 10, 11, 12})
    assert set(category_counts) == {4, 5, 6, 7, 8, 9, 10, 11, 12}
    assert set(panel_counts).issubset({4, 5, 6, 7, 8, 9})
    assert set(panel_counts) == {4, 5, 6, 7, 8, 9}
    assert duplicate_kind_instances > 0
    assert set(answer_types) == {"integer", "option_letter", "string"}
    assert answer_types["integer"] >= 75
    assert answer_types["string"] >= 15
    assert answer_types["option_letter"] >= 5


@pytest.mark.parametrize("option_count", [4, 6])
@pytest.mark.parametrize("requested_truth", ["true", "false"])
def test_chart_dashboard_statement_option_selection_contract(option_count: int, requested_truth: str) -> None:
    task = ChartsDashboardStatementOptionSelectionLabelTask()
    out = task.generate(
        hash64(20260604, "charts_dashboard_statement_option", option_count, requested_truth),
        params={"option_count": option_count, "requested_truth": requested_truth},
        max_attempts=160,
    )
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
    expected_refs = [
        [str(selected["first_panel_id"]), str(selected["first_category_id"])],
        [str(selected["second_panel_id"]), str(selected["second_category_id"])],
    ]
    assert execution["annotation_refs"] == expected_refs
    expected_points = [
        list(trace["render_map"]["support_points_px"][panel_id][category_id])
        for panel_id, category_id in expected_refs
    ]
    assert out.annotation_gt.value == {"first_mark": expected_points[0], "second_mark": expected_points[1]}
    for option in execution["statement_options"]:
        assert str(option["text"]) not in out.prompt


def test_chart_dashboard_is_deterministic() -> None:
    task = ChartsDashboardCrossPanelQueryTask()
    params = {"query_id": "dual_condition_count", "first_condition_comparison": "greater_than"}
    out_a = task.generate(93300, params=params, max_attempts=100)
    out_b = task.generate(93300, params=params, max_attempts=100)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_chart_dashboard_registered_and_group_config_loaded() -> None:
    assert (
        create_task("task_charts__dashboard__source_rank_target_value").task_id
        == "task_charts__dashboard__source_rank_target_value"
    )
    assert (
        create_task("task_charts__dashboard__source_rank_difference_value").task_id
        == "task_charts__dashboard__source_rank_difference_value"
    )
    assert (
        create_task("task_charts__dashboard__top_k_overlap_count").task_id
        == "task_charts__dashboard__top_k_overlap_count"
    )
    assert (
        create_task("task_charts__dashboard__category_panel_condition_count").task_id
        == "task_charts__dashboard__category_panel_condition_count"
    )
    assert (
        create_task("task_charts__dashboard__shared_label_rank_gap_extremum").task_id
        == "task_charts__dashboard__shared_label_rank_gap_extremum"
    )
    assert (
        create_task("task_charts__dashboard__statement_option_selection_label").task_id
        == "task_charts__dashboard__statement_option_selection_label"
    )

    cfg = get_task_group_defaults("charts", "dashboard")
    assert isinstance(cfg.get("generation"), dict)
    assert isinstance(cfg.get("rendering"), dict)
    assert isinstance(cfg.get("prompt"), dict)

    generation = cfg["generation"]["shared"]
    assert sorted(generation["query_id_weights"].keys()) == sorted(SUPPORTED_QUERY_IDS)
    assert int(generation["panel_count_min"]) == 4
    assert int(generation["panel_count_max"]) == 9
    assert int(generation["category_count_min"]) == 4
    assert int(generation["category_count_max"]) == 12
    assert sorted(generation["panel_kind_weights"].keys()) == sorted(SUPPORTED_PANEL_KINDS)

    prompt = cfg["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_dashboard_v0"
    assert str(prompt["scene_key"]) == "dashboard_mixed_chart"
    assert str(prompt["task_key"]) == "dashboard_cross_panel_query"
