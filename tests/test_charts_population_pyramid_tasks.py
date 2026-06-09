"""Behavior tests for population-pyramid chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.population_pyramid.pyramid_query import (
    GAP_QUERY_IDS,
    THRESHOLD_QUERY_IDS,
    ChartsPopulationPyramidAgeGroupThresholdCountTask,
    ChartsPopulationPyramidSideGapExtremumLabelTask,
)
from trace.tasks.registry import list_default_task_ids


TASK_CASES = (
    (ChartsPopulationPyramidSideGapExtremumLabelTask, GAP_QUERY_IDS, "string"),
    (ChartsPopulationPyramidAgeGroupThresholdCountTask, THRESHOLD_QUERY_IDS, "integer"),
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict, query_id: str) -> int | str:
    rows = list(execution["rows"])
    if query_id in GAP_QUERY_IDS:
        gaps = [(str(row["label"]), int(row["gap"])) for row in rows]
        if query_id == "largest_side_gap_label":
            target_gap = max(gap for _label, gap in gaps)
        else:
            target_gap = min(gap for _label, gap in gaps if int(gap) > 0)
        winners = [label for label, gap in gaps if int(gap) == int(target_gap)]
        assert len(winners) == 1
        return str(winners[0])

    threshold = int(execution["threshold_value"])
    relation = str(execution["threshold_relation"])

    def metric(row: dict) -> int:
        if query_id == "left_side_threshold_count":
            return int(row["left_value"])
        if query_id == "right_side_threshold_count":
            return int(row["right_value"])
        if query_id == "combined_total_threshold_count":
            return int(row["total"])
        raise AssertionError(f"unsupported query id: {query_id}")

    if relation == "at_least":
        return sum(1 for row in rows if metric(row) >= threshold)
    if relation == "at_most":
        return sum(1 for row in rows if metric(row) <= threshold)
    raise AssertionError(f"unsupported relation: {relation}")


@pytest.mark.parametrize(("task_cls", "query_ids", "answer_type"), TASK_CASES)
def test_charts_population_pyramid_tasks_match_contract(
    task_cls: type,
    query_ids: tuple[str, ...],
    answer_type: str,
) -> None:
    task = task_cls()
    for index, query_id in enumerate(query_ids):
        out = task.generate(
            hash64(20260604, "charts_population_pyramid", index),
            params={"query_id": query_id},
            max_attempts=80,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        assert task_cls.task_id in list_default_task_ids()
        assert out.scene_id == "population_pyramid"
        assert out.query_id == query_id
        assert str(execution["query_id"]) == query_id
        assert str(execution["question_format"]) == "population_pyramid"
        assert out.answer_gt.type == answer_type
        assert out.annotation_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 8 <= int(execution["row_count"]) <= 14
        assert len(execution["rows"]) == int(execution["row_count"])
        assert len(set(execution["row_labels"])) == int(execution["row_count"])

        expected = _expected_answer(execution, query_id)
        assert out.answer_gt.value == expected
        assert execution["answer_value"] == expected
        if query_id in GAP_QUERY_IDS:
            assert str(out.answer_gt.value) in set(execution["row_labels"])
            assert len(out.annotation_gt.value) == 1
        else:
            assert int(out.answer_gt.value) == len(out.annotation_gt.value)
            assert 1 <= int(out.answer_gt.value) <= 9

        annotation_row_ids = [str(row_id) for row_id in execution["annotation_row_ids"]]
        expected_bboxes = [trace["render_map"]["row_bar_bboxes_px"][row_id] for row_id in annotation_row_ids]
        assert out.annotation_gt.value == expected_bboxes
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        for bbox in out.annotation_gt.value:
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


def test_charts_population_pyramid_prompt_examples_match_contract() -> None:
    for task_cls, query_ids, answer_type in TASK_CASES:
        for query_id in query_ids:
            out = task_cls().generate(246000 + len(query_id), params={"query_id": query_id}, max_attempts=80)
            answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
            answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
            assert isinstance(answer_and_annotation["annotation"], list)
            if answer_type == "integer":
                assert isinstance(answer_and_annotation["answer"], int)
                assert isinstance(answer_only["answer"], int)
            else:
                assert isinstance(answer_and_annotation["answer"], str)
                assert isinstance(answer_only["answer"], str)
                assert len(answer_and_annotation["answer"]) > 1


def test_charts_population_pyramid_balanced_sampling_covers_axes() -> None:
    gap_queries: Counter[str] = Counter()
    threshold_queries: Counter[str] = Counter()
    threshold_relations: Counter[str] = Counter()

    for index in range(80):
        gap_out = ChartsPopulationPyramidSideGapExtremumLabelTask().generate(
            hash64(246100, "population_pyramid_gap", index),
            params={},
            max_attempts=80,
        )
        gap_queries[str(gap_out.query_id)] += 1
        count_out = ChartsPopulationPyramidAgeGroupThresholdCountTask().generate(
            hash64(246200, "population_pyramid_count", index),
            params={},
            max_attempts=80,
        )
        threshold_queries[str(count_out.query_id)] += 1
        threshold_relations[str(count_out.trace_payload["execution_trace"]["threshold_relation"])] += 1

    assert set(gap_queries) == set(GAP_QUERY_IDS)
    assert set(threshold_queries) == set(THRESHOLD_QUERY_IDS)
    assert set(threshold_relations) == {"at_least", "at_most"}


def test_charts_population_pyramid_is_deterministic() -> None:
    params = {"query_id": "combined_total_threshold_count"}
    out_a = ChartsPopulationPyramidAgeGroupThresholdCountTask().generate(246300, params=params, max_attempts=80)
    out_b = ChartsPopulationPyramidAgeGroupThresholdCountTask().generate(246300, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()
