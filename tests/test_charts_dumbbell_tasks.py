"""Behavior tests for dumbbell pairwise chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import assert_counter_support_within, extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks import create_task
from trace.tasks.charts.dumbbell.pairwise_comparison_query import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_QUERY_IDS,
    ChartsDumbbellPairwiseComparisonQueryTask,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict) -> str | int:
    rows = list(execution["rows"])
    variant = str(execution["query_id"])

    if variant == "gap_rank_row_label":
        reverse = str(execution["rank_order"]) == "largest"
        rank = int(execution["rank_n"])
        ranked_gaps = sorted({int(row["gap"]) for row in rows}, reverse=reverse)
        target_gap = int(ranked_gaps[rank - 1])
        winners = [row for row in rows if int(row["gap"]) == target_gap]
        assert len(winners) == 1
        return str(winners[0]["label"])

    if variant == "side_winner_count":
        threshold = int(execution["threshold_value"])
        if str(execution["side_direction"]) == "series_a_greater":
            return sum(1 for row in rows if int(row["signed_delta_a_minus_b"]) >= threshold)
        return sum(1 for row in rows if -int(row["signed_delta_a_minus_b"]) >= threshold)

    if variant == "absolute_gap_threshold_count":
        threshold = int(execution["gap_threshold_value"])
        if str(execution["gap_threshold_relation"]) == "at_least":
            return sum(1 for row in rows if int(row["gap"]) >= threshold)
        return sum(1 for row in rows if int(row["gap"]) <= threshold)

    raise AssertionError(f"unsupported variant: {variant}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_chart_dumbbell_variants_match_contract(query_id: str) -> None:
    task = ChartsDumbbellPairwiseComparisonQueryTask()
    out = task.generate(
        hash64(20260503, "charts_dumbbell", SUPPORTED_QUERY_IDS.index(query_id)),
        params={"query_id": query_id},
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_id == query_id
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert str(execution["question_format"]) == "dumbbell_pairwise_comparison_query"
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 10 <= int(execution["row_count"]) <= 16
    assert len(execution["rows"]) == int(execution["row_count"])
    assert len(set(execution["row_labels"])) == int(execution["row_count"])

    expected_answer = _expected_answer(execution)
    assert out.answer_gt.value == expected_answer
    assert execution["answer"] == expected_answer
    if query_id in {"side_winner_count", "absolute_gap_threshold_count"}:
        assert out.answer_gt.type == "integer"
        assert 2 <= int(out.answer_gt.value) <= 10
    else:
        assert out.answer_gt.type == "string"
        assert str(out.answer_gt.value) in set(execution["row_labels"])

    evidence_row_ids = [str(row_id) for row_id in execution["evidence_row_ids"]]
    expected_bboxes = [trace["render_map"]["row_pair_bboxes_px"][row_id] for row_id in evidence_row_ids]
    assert out.evidence_gt.value == expected_bboxes
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert trace["projected_evidence"]["row_ids"] == evidence_row_ids
    if query_id in {"side_winner_count", "absolute_gap_threshold_count"}:
        assert len(evidence_row_ids) == int(out.answer_gt.value)
    else:
        assert len(evidence_row_ids) == 1

    for bbox in out.evidence_gt.value:
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


def test_chart_dumbbell_prompt_examples_match_contract() -> None:
    task = ChartsDumbbellPairwiseComparisonQueryTask()
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS, start=92100):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=80)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert "evidence" in answer_and_evidence
        if query_id in {"side_winner_count", "absolute_gap_threshold_count"}:
            assert isinstance(answer_and_evidence["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_evidence["answer"], str)
            assert isinstance(answer_only["answer"], str)


def test_chart_dumbbell_balanced_sampling_covers_axes() -> None:
    task = ChartsDumbbellPairwiseComparisonQueryTask()
    variants: Counter[str] = Counter()
    row_counts: Counter[int] = Counter()
    rank_orders: Counter[str] = Counter()
    rank_ns: Counter[int] = Counter()
    side_directions: Counter[str] = Counter()
    gap_relations: Counter[str] = Counter()
    answers: Counter[str] = Counter()

    for index in range(96):
        out = task.generate(hash64(92200, "charts_dumbbell", index), params={}, max_attempts=120)
        execution = out.trace_payload["execution_trace"]
        variants[str(execution["query_id"])] += 1
        row_counts[int(execution["row_count"])] += 1
        answers[str(execution["answer"])] += 1
        if str(execution["query_id"]) == "gap_rank_row_label":
            rank_orders[str(execution["rank_order"])] += 1
            rank_ns[int(execution["rank_n"])] += 1
        if str(execution["query_id"]) == "side_winner_count":
            side_directions[str(execution["side_direction"])] += 1
        if str(execution["query_id"]) == "absolute_gap_threshold_count":
            gap_relations[str(execution["gap_threshold_relation"])] += 1

    assert_counter_support_within(variants, SUPPORTED_QUERY_IDS, expected_per_key=32, tolerance=12)
    assert set(row_counts).issubset(set(range(10, 17)))
    assert 10 in row_counts
    assert 16 in row_counts
    assert set(rank_orders) == {"largest", "smallest"}
    assert set(rank_ns) == {2, 3, 4}
    assert set(side_directions) == {"series_a_greater", "series_b_greater"}
    assert set(gap_relations) == {"at_least", "at_most"}
    assert len(answers) >= 12


def test_chart_dumbbell_is_deterministic() -> None:
    task = ChartsDumbbellPairwiseComparisonQueryTask()
    params = {"query_id": "gap_rank_row_label", "rank_order": "largest", "rank_n": 3}
    out_a = task.generate(92300, params=params, max_attempts=80)
    out_b = task.generate(92300, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_chart_dumbbell_registered_and_group_config_loaded() -> None:
    assert create_task("task_charts__dumbbell__gap_rank_row_label").task_id == "task_charts__dumbbell__gap_rank_row_label"

    cfg = get_task_group_defaults("charts", "dumbbell")
    assert isinstance(cfg.get("generation"), dict)
    assert isinstance(cfg.get("rendering"), dict)
    assert isinstance(cfg.get("prompt"), dict)

    generation = cfg["generation"]["shared"]
    assert int(generation["row_count_min"]) == 10
    assert int(generation["row_count_max"]) == 16
    assert sorted(generation["query_id_weights"].keys()) == sorted(SUPPORTED_QUERY_IDS)

    prompt = cfg["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_dumbbell_v0"
    assert str(prompt["scene_key"]) == "dumbbell_pairwise_chart"
    assert str(prompt["task_key"]) == "dumbbell_pairwise_comparison_query"
