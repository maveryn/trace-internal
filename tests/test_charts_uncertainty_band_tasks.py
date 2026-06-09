"""Behavior tests for uncertainty-band chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.uncertainty_band.band_query import (
    OVERLAP_QUERY_IDS,
    WIDTH_EXTREMUM_QUERY_IDS,
    ChartsUncertaintyBandOverlapCountTask,
    ChartsUncertaintyBandWidthExtremumXLabelTask,
)
from trace.tasks.registry import list_default_task_ids


TASK_CASES = (
    (ChartsUncertaintyBandOverlapCountTask, OVERLAP_QUERY_IDS, "integer", "point_set"),
    (ChartsUncertaintyBandWidthExtremumXLabelTask, WIDTH_EXTREMUM_QUERY_IDS, "string", "keyed_point_map"),
)


def _assert_point_inside_canvas(point: list[float], *, width: int, height: int) -> None:
    assert len(point) == 2
    x, y = [float(value) for value in point]
    assert 0 <= x <= width
    assert 0 <= y <= height


def _series_by_id(execution: dict) -> dict[str, dict]:
    return {str(series["series_id"]): dict(series) for series in execution["series"]}


def _expected_answer(execution: dict, query_id: str) -> int | str:
    series = list(execution["series"])
    if query_id == "band_overlap_count":
        count = 0
        for index in range(int(execution["x_count"])):
            low = max(int(series[0]["lower_values"][index]), int(series[1]["lower_values"][index]))
            high = min(int(series[0]["upper_values"][index]), int(series[1]["upper_values"][index]))
            if int(low) <= int(high):
                count += 1
        return int(count)
    target = _series_by_id(execution)[str(execution["target_series_id"])]
    widths = [int(high) - int(low) for low, high in zip(target["lower_values"], target["upper_values"])]
    if query_id == "widest_band_x_label":
        index = max(range(len(widths)), key=lambda idx: widths[idx])
    elif query_id == "narrowest_band_x_label":
        index = min(range(len(widths)), key=lambda idx: widths[idx])
    else:
        raise AssertionError(f"unsupported query_id: {query_id}")
    return str(execution["x_labels"][int(index)])


@pytest.mark.parametrize(("task_cls", "query_ids", "answer_type", "annotation_type"), TASK_CASES)
def test_charts_uncertainty_band_tasks_match_contract(
    task_cls: type,
    query_ids: tuple[str, ...],
    answer_type: str,
    annotation_type: str,
) -> None:
    task = task_cls()
    for query_id in query_ids:
        out = task.generate(241000 + len(query_id), params={"query_id": query_id}, max_attempts=60)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        assert task_cls.task_id in list_default_task_ids()
        assert out.scene_id == "uncertainty_band"
        assert out.query_id == query_id
        assert str(execution["query_id"]) == query_id
        assert str(execution["question_format"]) == "uncertainty_band"
        assert out.answer_gt.type == answer_type
        assert out.annotation_gt.type == annotation_type
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 6 <= int(execution["x_count"]) <= 9
        assert len(execution["series"]) == 2

        expected = _expected_answer(execution, query_id)
        assert out.answer_gt.value == expected
        assert execution["answer_value"] == expected

        if query_id == "band_overlap_count":
            assert int(out.answer_gt.value) == len(out.annotation_gt.value)
            assert 1 <= int(out.answer_gt.value) <= 5
            assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
            for point in out.annotation_gt.value:
                _assert_point_inside_canvas(
                    [float(value) for value in point],
                    width=int(render["canvas_width"]),
                    height=int(render["canvas_height"]),
                )
        else:
            assert set(out.annotation_gt.value.keys()) == {"upper_bound", "lower_bound"}
            assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
            for point in out.annotation_gt.value.values():
                _assert_point_inside_canvas(
                    [float(value) for value in point],
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


def test_charts_uncertainty_band_prompt_examples_match_contract() -> None:
    for task_cls, _query_ids, answer_type, annotation_type in TASK_CASES:
        out = task_cls().generate(242000 + len(task_cls.task_id), params={}, max_attempts=60)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        if answer_type == "integer":
            assert isinstance(answer_and_annotation["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_annotation["answer"], str)
            assert isinstance(answer_only["answer"], str)
            assert len(answer_and_annotation["answer"]) > 1
        if annotation_type == "point_set":
            assert isinstance(answer_and_annotation["annotation"], list)
        else:
            assert set(answer_and_annotation["annotation"].keys()) == {"upper_bound", "lower_bound"}


def test_charts_uncertainty_band_balanced_sampling_covers_width_queries() -> None:
    queries: Counter[str] = Counter()
    for index in range(48):
        out = ChartsUncertaintyBandWidthExtremumXLabelTask().generate(
            hash64(243000, "charts_uncertainty_band", index),
            params={},
            max_attempts=60,
        )
        queries[str(out.query_id)] += 1
    assert set(queries) == set(WIDTH_EXTREMUM_QUERY_IDS)


def test_charts_uncertainty_band_is_deterministic() -> None:
    params = {"query_id": "widest_band_x_label"}
    out_a = ChartsUncertaintyBandWidthExtremumXLabelTask().generate(244000, params=params, max_attempts=60)
    out_b = ChartsUncertaintyBandWidthExtremumXLabelTask().generate(244000, params=params, max_attempts=60)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()
