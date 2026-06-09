"""Behavior tests for pictogram/waffle chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.pictogram.waffle_chart import (
    SUPPORTED_GLYPHS,
    SUPPORTED_SCENE_VARIANTS,
    ChartsPictogramCategoryTotalValueTask,
    ChartsPictogramGroupDifferenceValueTask,
    ChartsPictogramThresholdCountTask,
)
from trace.tasks.registry import list_default_task_ids


TASK_CASES = (
    (ChartsPictogramCategoryTotalValueTask, "category_total_value"),
    (ChartsPictogramGroupDifferenceValueTask, "group_difference_value"),
    (ChartsPictogramThresholdCountTask, "threshold_count"),
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict, query_params: dict, query_id: str) -> int:
    totals_by_category = {str(label): int(value) for label, value in execution["totals_by_category"].items()}
    if query_id == "category_total_value":
        return int(totals_by_category[str(query_params["target_category_label"])])
    if query_id == "group_difference_value":
        a = int(totals_by_category[str(query_params["category_label_a"])])
        b = int(totals_by_category[str(query_params["category_label_b"])])
        return abs(a - b)
    if query_id == "threshold_count":
        threshold = int(query_params["threshold_value"])
        if str(query_params["threshold_direction"]) == "greater_than":
            return sum(1 for value in totals_by_category.values() if int(value) > threshold)
        return sum(1 for value in totals_by_category.values() if int(value) < threshold)
    raise AssertionError(f"unsupported query_id: {query_id}")


@pytest.mark.parametrize(("task_cls", "query_id"), TASK_CASES)
def test_charts_pictogram_tasks_match_contract(task_cls: type, query_id: str) -> None:
    task = task_cls()
    out = task.generate(91200 + len(query_id), params={"query_id": query_id}, max_attempts=60)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    query_params = trace["query_spec"]["params"]

    assert task_cls.task_id in list_default_task_ids()
    assert out.scene_id == "pictogram"
    assert out.query_id == query_id
    assert str(execution["query_id"]) == query_id
    assert str(query_params["query_id"]) == query_id
    assert out.answer_gt.type == "integer"
    expected_annotation_type = "bbox_set" if query_id == "threshold_count" else "keyed_bbox_map"
    assert out.annotation_gt.type == expected_annotation_type
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(execution["question_format"]) == "pictogram_quantity"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert str(render["glyph_name"]) in SUPPORTED_GLYPHS
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 6 <= int(execution["category_count"]) <= 10
    assert 1 <= int(execution["unit_scale"]) <= 5

    expected = _expected_answer(execution, query_params, query_id)
    assert int(out.answer_gt.value) == int(expected)
    assert int(execution["answer_value"]) == int(expected)
    assert trace["projected_annotation"]["type"] == expected_annotation_type

    annotation_category_ids = [str(value) for value in trace["projected_annotation"]["category_ids"]]
    annotation_category_labels = [str(value) for value in trace["projected_annotation"]["category_labels"]]
    expected_boxes = [render_map["category_bboxes_px"][category_id] for category_id in annotation_category_ids]
    if expected_annotation_type == "keyed_bbox_map":
        expected_keyed = {
            str(execution["category_id_to_label"][category_id]): box
            for category_id, box in zip(annotation_category_ids, expected_boxes)
        }
        assert out.annotation_gt.value == expected_keyed
        assert trace["projected_annotation"]["keyed_bbox_map"] == expected_keyed
        assert trace["projected_annotation"]["pixel_keyed_bbox_map"] == expected_keyed
        assert trace["projected_annotation"]["bbox_set"] == list(expected_keyed.values())
        boxes_to_check = list(out.annotation_gt.value.values())
    else:
        assert out.annotation_gt.value == expected_boxes
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        boxes_to_check = list(out.annotation_gt.value)
    assert annotation_category_labels == [str(execution["category_id_to_label"][category_id]) for category_id in annotation_category_ids]
    for bbox in boxes_to_check:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    if query_id == "category_total_value":
        assert len(out.annotation_gt.value) == 1
    elif query_id == "group_difference_value":
        assert len(out.annotation_gt.value) == 2
    else:
        assert int(out.answer_gt.value) == len(out.annotation_gt.value)
        assert 1 <= int(out.answer_gt.value) <= 5

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_charts_pictogram_prompt_examples_match_contract() -> None:
    for task_cls, query_id in TASK_CASES:
        out = task_cls().generate(91300 + len(task_cls.task_id) + len(query_id), params={"query_id": query_id}, max_attempts=60)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert isinstance(answer_and_annotation["answer"], int)
        if query_id == "threshold_count":
            assert isinstance(answer_and_annotation["annotation"], list)
        else:
            assert isinstance(answer_and_annotation["annotation"], dict)
        assert isinstance(answer_only["answer"], int)


def test_charts_pictogram_balanced_sampling_covers_scene_and_glyph_axes() -> None:
    task = ChartsPictogramThresholdCountTask()
    scenes: Counter[str] = Counter()
    glyphs: Counter[str] = Counter()

    for index in range(48):
        out = task.generate(hash64(91400, "charts_pictogram", index), params={}, max_attempts=60)
        execution = out.trace_payload["execution_trace"]
        render = out.trace_payload["render_spec"]
        scenes[str(execution["scene_variant"])] += 1
        glyphs[str(render["glyph_name"])] += 1

    assert set(scenes) == set(SUPPORTED_SCENE_VARIANTS)
    assert set(glyphs) == set(SUPPORTED_GLYPHS)


def test_charts_pictogram_is_deterministic() -> None:
    params = {"query_id": "group_difference_value", "scene_variant": "pictogram_rows", "glyph_name": "star"}
    out_a = ChartsPictogramGroupDifferenceValueTask().generate(91500, params=params, max_attempts=60)
    out_b = ChartsPictogramGroupDifferenceValueTask().generate(91500, params=params, max_attempts=60)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()
