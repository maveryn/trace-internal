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
    SUPPORTED_QUERY_VARIANTS,
    ChartsDashboardCrossPanelQueryTask,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _value(execution: dict, panel_id: str, category_id: str) -> int:
    return int(execution["values_by_panel"][str(panel_id)]["values_by_category_id"][str(category_id)])


def _expected_answer(execution: dict) -> int | str:
    variant = str(execution["query_variant"])

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

    raise AssertionError(f"unsupported variant: {variant}")


@pytest.mark.parametrize("query_variant", SUPPORTED_QUERY_VARIANTS)
def test_chart_dashboard_variants_match_contract(query_variant: str) -> None:
    task = ChartsDashboardCrossPanelQueryTask()
    out = task.generate(
        hash64(20260503, "charts_dashboard", SUPPORTED_QUERY_VARIANTS.index(query_variant)),
        params={"query_variant": query_variant},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_variant == query_variant
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert str(execution["question_format"]) == "dashboard_cross_panel_query"
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
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
    if query_variant == "panel_gap_extremum_category_label":
        assert out.answer_gt.type == "string"
    else:
        assert out.answer_gt.type == "integer"

    expected_bboxes = [
        list(trace["render_map"]["support_bboxes_px"][str(panel_id)][str(category_id)])
        for panel_id, category_id in execution["evidence_refs"]
    ]
    assert out.evidence_gt.value == expected_bboxes
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(trace["projected_evidence"]["evidence_refs"]) == len(out.evidence_gt.value)

    for bbox in out.evidence_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    if query_variant == "dual_condition_count":
        assert len(out.evidence_gt.value) == int(out.answer_gt.value) * 2
    if query_variant == "panel_gap_extremum_category_label":
        assert len(out.evidence_gt.value) == 2

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }


def test_chart_dashboard_prompt_examples_match_contract() -> None:
    task = ChartsDashboardCrossPanelQueryTask()
    for index, query_variant in enumerate(SUPPORTED_QUERY_VARIANTS, start=93100):
        out = task.generate(index, params={"query_variant": query_variant}, max_attempts=100)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert "evidence" in answer_and_evidence
        if query_variant == "panel_gap_extremum_category_label":
            assert isinstance(answer_and_evidence["answer"], str)
            assert isinstance(answer_only["answer"], str)
        else:
            assert isinstance(answer_and_evidence["answer"], int)
            assert isinstance(answer_only["answer"], int)


def test_chart_dashboard_balanced_sampling_covers_variants() -> None:
    task = ChartsDashboardCrossPanelQueryTask()
    variants: Counter[str] = Counter()
    category_counts: Counter[int] = Counter()
    panel_counts: Counter[int] = Counter()
    duplicate_kind_instances = 0
    answer_types: Counter[str] = Counter()

    for index in range(100):
        out = task.generate(hash64(93200, "charts_dashboard", index), params={}, max_attempts=160)
        execution = out.trace_payload["execution_trace"]
        variants[str(execution["query_variant"])] += 1
        category_counts[int(execution["category_count"])] += 1
        panel_counts[int(execution["panel_count"])] += 1
        duplicate_kind_instances += int(len(set(str(kind) for kind in execution["panel_kinds"])) < int(execution["panel_count"]))
        answer_types[str(out.answer_gt.type)] += 1

    assert_counter_support_within(variants, SUPPORTED_QUERY_VARIANTS, expected_per_key=20, tolerance=10)
    assert set(category_counts).issubset({4, 5, 6, 7, 8, 9, 10, 11, 12})
    assert set(category_counts) == {4, 5, 6, 7, 8, 9, 10, 11, 12}
    assert set(panel_counts).issubset({4, 5, 6, 7, 8, 9})
    assert set(panel_counts) == {4, 5, 6, 7, 8, 9}
    assert duplicate_kind_instances > 0
    assert set(answer_types) == {"integer", "string"}
    assert 70 <= answer_types["integer"] <= 90
    assert 10 <= answer_types["string"] <= 30


def test_chart_dashboard_is_deterministic() -> None:
    task = ChartsDashboardCrossPanelQueryTask()
    params = {"query_variant": "dual_condition_count", "first_condition_comparison": "greater_than"}
    out_a = task.generate(93300, params=params, max_attempts=100)
    out_b = task.generate(93300, params=params, max_attempts=100)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_chart_dashboard_registered_and_group_config_loaded() -> None:
    assert create_task("task_charts__dashboard__source_rank_target_value").task_id == "task_charts__dashboard__source_rank_target_value"

    cfg = get_task_group_defaults("charts", "dashboard")
    assert isinstance(cfg.get("generation"), dict)
    assert isinstance(cfg.get("rendering"), dict)
    assert isinstance(cfg.get("prompt"), dict)

    generation = cfg["generation"]["shared"]
    assert sorted(generation["query_variant_weights"].keys()) == sorted(SUPPORTED_QUERY_VARIANTS)
    assert int(generation["panel_count_min"]) == 4
    assert int(generation["panel_count_max"]) == 9
    assert int(generation["category_count_min"]) == 4
    assert int(generation["category_count_max"]) == 12
    assert sorted(generation["panel_kind_weights"].keys()) == sorted(SUPPORTED_PANEL_KINDS)

    prompt = cfg["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_dashboard_v0"
    assert str(prompt["scene_key"]) == "dashboard_mixed_chart"
    assert str(prompt["task_key"]) == "dashboard_cross_panel_query"
