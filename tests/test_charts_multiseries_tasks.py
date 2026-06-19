"""Behavior tests for migrated chart multiseries tasks."""

from __future__ import annotations

import json
from typing import Any

import pytest

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.charts.multiseries.category_total_extremum_label import (
    ChartsMultiseriesCategoryTotalExtremumLabelTask,
)
from trace.tasks.charts.multiseries.pair_equality_label import ChartsMultiseriesPairEqualityLabelTask
from trace.tasks.charts.multiseries.ranked_change_extremum_label import (
    ChartsMultiseriesRankedChangeExtremumTask,
)
from trace.tasks.charts.multiseries.ranked_pair_ratio_extremum_label import (
    ChartsMultiseriesRankedPairRatioExtremumTask,
)
from trace.tasks.charts.multiseries.ranked_series_share_extremum_label import (
    ChartsMultiseriesRankedSeriesShareExtremumTask,
)
from trace.tasks.charts.multiseries.series_comparison_count import ChartsMultiseriesSeriesComparisonCountTask
from trace.tasks.charts.multiseries.series_rank_at_category_label import (
    ChartsMultiseriesSeriesRankAtCategoryLabelTask,
)


TASK_CLASSES = (
    ChartsMultiseriesCategoryTotalExtremumLabelTask,
    ChartsMultiseriesPairEqualityLabelTask,
    ChartsMultiseriesRankedChangeExtremumTask,
    ChartsMultiseriesRankedPairRatioExtremumTask,
    ChartsMultiseriesRankedSeriesShareExtremumTask,
    ChartsMultiseriesSeriesComparisonCountTask,
    ChartsMultiseriesSeriesRankAtCategoryLabelTask,
)


def _extract_prompt_json_example(prompt: str) -> dict[str, Any]:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    return json.loads(str(prompt).split(marker, 1)[1].strip())


def _execution(out: Any) -> dict[str, Any]:
    return dict(out.trace_payload["execution_trace"])


def _values_by_category(out: Any) -> dict[str, dict[str, int]]:
    return {
        str(category): {str(series): int(value) for series, value in series_values.items()}
        for category, series_values in _execution(out)["values_by_category"].items()
    }


def _assert_common_public_task_contract(out: Any, *, expected_answer_type: str) -> None:
    trace = out.trace_payload
    render = trace["render_spec"]
    projected = trace["projected_annotation"]

    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == expected_answer_type
    assert out.annotation_gt.type == "point_map"
    assert projected["type"] == "point_map"
    assert projected["point_map"] == out.annotation_gt.value
    assert projected["pixel_point_map"] == out.annotation_gt.value
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert _extract_prompt_json_example(out.prompt_variants["answer_only"]).keys() == {"answer"}
    assert _extract_prompt_json_example(out.prompt_variants["answer_and_annotation"]).keys() == {
        "annotation",
        "answer",
    }
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert trace["query_spec"]["query_id"] == SINGLE_QUERY_ID
    assert _execution(out)["query_id"] == SINGLE_QUERY_ID
    assert _execution(out)["internal_query_id"]
    assert _execution(out)["scene_variant"] == render["scene_variant"]

    for key, point in out.annotation_gt.value.items():
        assert ":" in str(key)
        x_coord, y_coord = [float(value) for value in point]
        assert 0 <= x_coord <= int(render["canvas_width"])
        assert 0 <= y_coord <= int(render["canvas_height"])


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_chart_multiseries_public_tasks_use_single_query_id(task_cls: type) -> None:
    task = task_cls()
    out = task.generate(12000, params={"query_id": SINGLE_QUERY_ID}, max_attempts=100)

    assert task.supported_query_ids == (SINGLE_QUERY_ID,)
    _assert_common_public_task_contract(out, expected_answer_type=out.answer_gt.type)


def test_chart_multiseries_series_comparison_count_matches_contract() -> None:
    task = ChartsMultiseriesSeriesComparisonCountTask()
    out = task.generate(12010, params={"comparison": "less_than"}, max_attempts=100)
    execution = _execution(out)
    values_by_category = _values_by_category(out)
    left_series, right_series = [str(label) for label in execution["queried_series_labels"]]

    _assert_common_public_task_contract(out, expected_answer_type="integer")
    assert execution["comparison"] == "less_than"
    matching_categories = [
        str(category)
        for category, series_values in values_by_category.items()
        if int(series_values[left_series]) < int(series_values[right_series])
    ]
    assert int(out.answer_gt.value) == len(matching_categories)
    expected_keys = {
        f"{category}:{series_label}"
        for category in matching_categories
        for series_label in (left_series, right_series)
    }
    assert set(out.annotation_gt.value.keys()) == expected_keys


def test_chart_multiseries_category_total_extremum_matches_contract() -> None:
    task = ChartsMultiseriesCategoryTotalExtremumLabelTask()
    out = task.generate(12020, params={"extremum_direction": "largest"}, max_attempts=100)
    execution = _execution(out)
    answer_label = str(out.answer_gt.value)
    series_labels = [str(label) for label in execution["series_labels"]]

    _assert_common_public_task_contract(out, expected_answer_type="string")
    assert answer_label == str(execution["ranked_category_labels"][int(execution["answer_rank"]) - 1])
    totals = {str(label): int(value) for label, value in execution["category_totals_by_category"].items()}
    assert totals[answer_label] == max(totals.values())
    assert set(out.annotation_gt.value.keys()) == {f"{answer_label}:{series_label}" for series_label in series_labels}


def test_chart_multiseries_pair_equality_matches_contract() -> None:
    task = ChartsMultiseriesPairEqualityLabelTask()
    out = task.generate(12030, params={}, max_attempts=100)
    execution = _execution(out)
    values_by_category = _values_by_category(out)
    answer_label = str(out.answer_gt.value)
    left_series, right_series = [str(label) for label in execution["queried_series_labels"]]

    _assert_common_public_task_contract(out, expected_answer_type="string")
    equality_labels = [
        str(category)
        for category, series_values in values_by_category.items()
        if int(series_values[left_series]) == int(series_values[right_series])
    ]
    assert equality_labels == [answer_label]
    assert set(out.annotation_gt.value.keys()) == {
        f"{answer_label}:{left_series}",
        f"{answer_label}:{right_series}",
    }


def test_chart_multiseries_ranked_change_extremum_matches_contract() -> None:
    task = ChartsMultiseriesRankedChangeExtremumTask()
    out = task.generate(
        12040,
        params={"change_measure": "directional_change", "change_direction": "increase"},
        max_attempts=100,
    )
    execution = _execution(out)
    answer_label = str(out.answer_gt.value)
    left_series, right_series = [str(label) for label in execution["queried_series_labels"]]

    _assert_common_public_task_contract(out, expected_answer_type="string")
    assert answer_label == str(execution["ranked_category_labels"][int(execution["answer_rank"]) - 1])
    assert execution["internal_query_id"] == "ranked_largest_increase"
    assert set(out.annotation_gt.value.keys()) == {
        f"{answer_label}:{left_series}",
        f"{answer_label}:{right_series}",
    }


def test_chart_multiseries_ranked_pair_ratio_extremum_matches_contract() -> None:
    task = ChartsMultiseriesRankedPairRatioExtremumTask()
    out = task.generate(12050, params={"extremum_direction": "smallest"}, max_attempts=100)
    execution = _execution(out)
    answer_label = str(out.answer_gt.value)
    numerator = str(execution["numerator_series_label"])
    denominator = str(execution["denominator_series_label"])

    _assert_common_public_task_contract(out, expected_answer_type="string")
    assert answer_label == str(execution["ranked_category_labels"][int(execution["answer_rank"]) - 1])
    assert execution["internal_query_id"] == "ranked_smallest_pair_ratio"
    assert set(out.annotation_gt.value.keys()) == {
        f"{answer_label}:{numerator}",
        f"{answer_label}:{denominator}",
    }


def test_chart_multiseries_ranked_series_share_extremum_matches_contract() -> None:
    task = ChartsMultiseriesRankedSeriesShareExtremumTask()
    out = task.generate(12060, params={"extremum_direction": "largest"}, max_attempts=100)
    execution = _execution(out)
    answer_label = str(out.answer_gt.value)
    series_labels = [str(label) for label in execution["series_labels"]]

    _assert_common_public_task_contract(out, expected_answer_type="string")
    assert answer_label == str(execution["ranked_category_labels"][int(execution["answer_rank"]) - 1])
    assert execution["internal_query_id"] == "ranked_largest_series_share"
    assert set(out.annotation_gt.value.keys()) == {f"{answer_label}:{series_label}" for series_label in series_labels}


def test_chart_multiseries_series_rank_at_category_matches_contract() -> None:
    task = ChartsMultiseriesSeriesRankAtCategoryLabelTask()
    out = task.generate(12070, params={"extremum_direction": "smallest"}, max_attempts=100)
    execution = _execution(out)
    answer_label = str(out.answer_gt.value)
    target_category = str(execution["target_category_label"])
    series_values = {str(label): int(value) for label, value in execution["values_by_series_at_target_category"].items()}
    ranked_series = sorted(series_values, key=lambda label: (series_values[label], label))

    _assert_common_public_task_contract(out, expected_answer_type="string")
    assert answer_label == ranked_series[int(execution["answer_rank"]) - 1]
    assert set(out.annotation_gt.value.keys()) == {
        f"{target_category}:{series_label}"
        for series_label in execution["series_labels"]
    }


def test_chart_multiseries_task_is_deterministic() -> None:
    task = ChartsMultiseriesRankedChangeExtremumTask()
    params = {
        "scene_variant": "multi_line",
        "change_measure": "absolute_gap",
        "extremum_direction": "largest",
    }
    out_a = task.generate(12080, params=params, max_attempts=100)
    out_b = task.generate(12080, params=params, max_attempts=100)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
