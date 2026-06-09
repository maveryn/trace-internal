"""Behavior tests for error interval chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.error_interval.interval_chart import (
    REFERENCE_COUNT_QUERY_IDS,
    RELATION_LABEL_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    ChartsErrorIntervalReferenceContainmentCountTask,
    ChartsErrorIntervalReferenceExclusionSideCountTask,
    ChartsErrorIntervalRelationLabelTask,
)
from trace.tasks.registry import list_default_task_ids


TASK_CASES = (
    (ChartsErrorIntervalReferenceContainmentCountTask, ("contains_reference_count",), "integer"),
    (
        ChartsErrorIntervalReferenceExclusionSideCountTask,
        ("entirely_above_reference_count", "entirely_below_reference_count"),
        "integer",
    ),
    (ChartsErrorIntervalRelationLabelTask, RELATION_LABEL_QUERY_IDS, "string"),
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict, query_id: str) -> int | str:
    items = list(execution["items"])
    if query_id == "contains_reference_count":
        reference = int(execution["reference_value"])
        return sum(1 for item in items if int(item["lower"]) <= reference <= int(item["upper"]))
    if query_id == "entirely_above_reference_count":
        reference = int(execution["reference_value"])
        return sum(1 for item in items if int(item["lower"]) > reference)
    if query_id == "entirely_below_reference_count":
        reference = int(execution["reference_value"])
        return sum(1 for item in items if int(item["upper"]) < reference)
    if query_id == "widest_interval_label":
        return max(items, key=lambda item: int(item["upper"]) - int(item["lower"]))["label"]
    if query_id == "narrowest_interval_label":
        return min(items, key=lambda item: int(item["upper"]) - int(item["lower"]))["label"]
    if query_id == "second_widest_interval_label":
        return sorted(items, key=lambda item: int(item["upper"]) - int(item["lower"]), reverse=True)[1]["label"]
    if query_id == "second_narrowest_interval_label":
        return sorted(items, key=lambda item: int(item["upper"]) - int(item["lower"]))[1]["label"]
    raise AssertionError(f"unsupported query_id: {query_id}")


@pytest.mark.parametrize(("task_cls", "query_ids", "answer_type"), TASK_CASES)
def test_charts_error_interval_tasks_match_contract(task_cls: type, query_ids: tuple[str, ...], answer_type: str) -> None:
    task = task_cls()
    for query_id in query_ids:
        out = task.generate(117000 + len(query_id), params={"query_id": query_id}, max_attempts=60)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]

        assert task_cls.task_id in list_default_task_ids()
        assert out.scene_id == "error_interval"
        assert out.query_id == query_id
        assert str(execution["query_id"]) == query_id
        assert out.answer_gt.type == answer_type
        assert out.annotation_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert str(execution["question_format"]) == "error_interval"
        assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 6 <= int(execution["category_count"]) <= 10

        expected = _expected_answer(execution, query_id)
        assert out.answer_gt.value == expected
        assert execution["answer_value"] == expected
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value

        annotation_item_ids = [str(value) for value in trace["projected_annotation"]["item_ids"]]
        expected_boxes = [render_map["interval_bboxes_px"][item_id] for item_id in annotation_item_ids]
        assert out.annotation_gt.value == expected_boxes
        for bbox in out.annotation_gt.value:
            _assert_bbox_inside_canvas(
                [float(value) for value in bbox],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )

        if query_id in REFERENCE_COUNT_QUERY_IDS:
            assert int(out.answer_gt.value) == len(out.annotation_gt.value)
            assert 1 <= int(out.answer_gt.value) <= 5
        else:
            assert len(out.annotation_gt.value) == 1

        complexity = out.complexity.to_dict()
        assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
        assert set(complexity["complexity_components"].keys()) == {
            "reasoning_load",
            "scene_variant_load",
            "visual_scan",
        }


def test_charts_error_interval_prompt_examples_match_contract() -> None:
    for task_cls, _query_ids, answer_type in TASK_CASES:
        out = task_cls().generate(118000 + len(task_cls.task_id), params={}, max_attempts=60)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        if answer_type == "integer":
            assert isinstance(answer_and_annotation["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_annotation["answer"], str)
            assert isinstance(answer_only["answer"], str)
        assert isinstance(answer_and_annotation["annotation"], list)


def test_charts_error_interval_balanced_sampling_covers_scene_axis() -> None:
    scenes: Counter[str] = Counter()
    queries: Counter[str] = Counter()

    for index in range(64):
        out = ChartsErrorIntervalReferenceContainmentCountTask().generate(
            hash64(119000, "charts_error_interval", index),
            params={},
            max_attempts=60,
        )
        scenes[str(out.trace_payload["execution_trace"]["scene_variant"])] += 1
        queries[str(out.query_id)] += 1

    assert set(scenes) == set(SUPPORTED_SCENE_VARIANTS)
    assert set(queries) == {"contains_reference_count"}


def test_charts_error_interval_is_deterministic() -> None:
    params = {"scene_variant": "bar_with_error", "query_id": "widest_interval_label"}
    out_a = ChartsErrorIntervalRelationLabelTask().generate(120000, params=params, max_attempts=60)
    out_b = ChartsErrorIntervalRelationLabelTask().generate(120000, params=params, max_attempts=60)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()
