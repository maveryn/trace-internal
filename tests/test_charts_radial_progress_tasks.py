"""Behavior tests for radial progress chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.radial_progress.progress_chart import (
    SUPPORTED_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    ChartsRadialProgressConditionCountTask,
)
from trace.tasks.registry import list_default_task_ids


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict, query_id: str) -> int:
    items = list(execution["items"])
    if query_id == "at_least_threshold_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for item in items if int(item["value"]) >= threshold)
    if query_id == "below_threshold_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for item in items if int(item["value"]) < threshold)
    if query_id == "within_range_count":
        lower = int(execution["range_lower"])
        upper = int(execution["range_upper"])
        return sum(1 for item in items if lower <= int(item["value"]) <= upper)
    if query_id == "remaining_at_least_threshold_count":
        threshold = int(execution["threshold_value"])
        return sum(1 for item in items if 100 - int(item["value"]) >= threshold)
    raise AssertionError(f"unsupported query_id: {query_id}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_charts_radial_progress_task_matches_contract(query_id: str) -> None:
    task = ChartsRadialProgressConditionCountTask()
    out = task.generate(126000 + len(query_id), params={"query_id": query_id}, max_attempts=60)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]

    assert task.task_id in list_default_task_ids()
    assert out.scene_id == "radial_progress"
    assert out.query_id == "default"
    assert out.query_id == query_id
    assert str(execution["query_id"]) == query_id
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["question_format"]) == "radial_progress_condition_count"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 6 <= int(execution["item_count"]) <= 10

    expected = _expected_answer(execution, query_id)
    assert out.answer_gt.value == expected
    assert int(execution["answer_value"]) == expected
    assert 1 <= int(out.answer_gt.value) <= 5
    assert int(out.answer_gt.value) == len(out.evidence_gt.value)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    evidence_item_ids = [str(value) for value in trace["projected_evidence"]["item_ids"]]
    expected_boxes = [render_map["item_bboxes_px"][item_id] for item_id in evidence_item_ids]
    assert out.evidence_gt.value == expected_boxes
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


def test_charts_radial_progress_prompt_examples_match_contract() -> None:
    out = ChartsRadialProgressConditionCountTask().generate(127000, params={}, max_attempts=60)
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert isinstance(answer_and_evidence["answer"], int)
    assert isinstance(answer_only["answer"], int)
    assert isinstance(answer_and_evidence["evidence"], list)


def test_charts_radial_progress_balanced_sampling_covers_axes() -> None:
    scenes: Counter[str] = Counter()
    queries: Counter[str] = Counter()

    for index in range(96):
        out = ChartsRadialProgressConditionCountTask().generate(
            hash64(128000, "charts_radial_progress", index),
            params={},
            max_attempts=60,
        )
        scenes[str(out.trace_payload["execution_trace"]["scene_variant"])] += 1
        queries[str(out.query_id)] += 1

    assert set(scenes) == set(SUPPORTED_SCENE_VARIANTS)
    assert set(queries) == set(SUPPORTED_QUERY_IDS)


def test_charts_radial_progress_is_deterministic() -> None:
    params = {"scene_variant": "semicircle_gauges", "query_id": "within_range_count"}
    out_a = ChartsRadialProgressConditionCountTask().generate(129000, params=params, max_attempts=60)
    out_b = ChartsRadialProgressConditionCountTask().generate(129000, params=params, max_attempts=60)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()
