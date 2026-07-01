"""Behavior tests for pages numbered step-list lookup tasks."""

from __future__ import annotations

import json

import pytest

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.pages.step_list import _lifecycle
from trace.tasks.pages.step_list.nth_step_field_label import PagesStepListNthStepFieldLabelTask
from trace.tasks.pages.step_list.step_after_named_step_label import (
    PagesStepListStepAfterNamedStepLabelTask,
)
from trace.tasks.pages.step_list.step_for_detail_label import PagesStepListStepForDetailLabelTask


STEP_LIST_CASES = (
    ("nth_step_title", "nth_step_title", PagesStepListNthStepFieldLabelTask),
    ("nth_step_detail", "nth_step_detail", PagesStepListNthStepFieldLabelTask),
    ("step_after_named_step", SINGLE_QUERY_ID, PagesStepListStepAfterNamedStepLabelTask),
    ("step_title_for_detail", "step_title_for_detail", PagesStepListStepForDetailLabelTask),
    ("step_number_for_detail", "step_number_for_detail", PagesStepListStepForDetailLabelTask),
)


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict) -> str:
    source_query_id = str(execution["source_query_id"])
    target_step = dict(execution["target_step"])
    if source_query_id == "nth_step_detail":
        return str(target_step["detail"])
    if source_query_id == "step_number_for_detail":
        return str(target_step["step_number"])
    return str(target_step["title"])


@pytest.mark.parametrize("source_query_id, public_query_id, task_cls", STEP_LIST_CASES)
def test_pages_step_list_query_variants_match_contract(
    source_query_id: str,
    public_query_id: str,
    task_cls,
) -> None:
    params = {"step_count": 6, "pages_context_text_enabled": False}
    if public_query_id != SINGLE_QUERY_ID:
        params["query_id"] = public_query_id
    task = task_cls()
    out = task.generate(
        67120 + [case[0] for case in STEP_LIST_CASES].index(source_query_id),
        params=params,
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    assert out.query_id == public_query_id
    assert out.scene_id == "step_list"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "bbox"
    assert execution["source_query_id"] == source_query_id
    assert execution["prompt_query_key"] == source_query_id
    assert trace["query_spec"]["prompt_variant"]["prompt_schema_version"] == "v1"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["step_count"]) == 6
    assert len(execution["steps"]) == 6
    assert len(trace["scene_ir"]["entities"]) == 6
    expected = _expected_answer(execution)
    assert str(out.answer_gt.value) == expected
    assert str(execution["answer_value"]) == expected
    assert str(trace["query_spec"]["params"]["target_answer"]) == expected
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_bbox"] == out.annotation_gt.value
    _assert_bbox_inside_canvas(
        [float(value) for value in out.annotation_gt.value],
        width=int(render["canvas_width"]),
        height=int(render["canvas_height"]),
    )
    reasoning_bboxes = {
        str(key): [float(value) for value in bbox]
        for key, bbox in trace["render_map"]["reasoning_bboxes_px"].items()
    }
    target_step_id = str(execution["target_step"]["step_id"])
    if source_query_id == "nth_step_detail":
        assert set(reasoning_bboxes) == {"target_detail"}
        assert out.annotation_gt.value == trace["render_map"]["detail_bboxes_px"][target_step_id]
        assert reasoning_bboxes["target_detail"] == out.annotation_gt.value
    elif source_query_id == "step_title_for_detail":
        assert set(reasoning_bboxes) == {"source_detail", "target_title"}
        assert reasoning_bboxes["source_detail"] == trace["render_map"]["detail_bboxes_px"][target_step_id]
        assert out.annotation_gt.value == trace["render_map"]["title_bboxes_px"][target_step_id]
        assert reasoning_bboxes["target_title"] == out.annotation_gt.value
        assert str(execution["source_step_detail"]) == str(execution["target_step"]["detail"])
    elif source_query_id == "step_number_for_detail":
        assert set(reasoning_bboxes) == {"source_detail", "target_number"}
        assert reasoning_bboxes["source_detail"] == trace["render_map"]["detail_bboxes_px"][target_step_id]
        assert out.annotation_gt.value == trace["render_map"]["number_badge_bboxes_px"][target_step_id]
        assert reasoning_bboxes["target_number"] == out.annotation_gt.value
        assert str(execution["source_step_detail"]) == str(execution["target_step"]["detail"])
    else:
        assert "target_title" in reasoning_bboxes
        assert out.annotation_gt.value == trace["render_map"]["title_bboxes_px"][target_step_id]
        assert reasoning_bboxes["target_title"] == out.annotation_gt.value
    if source_query_id == "step_after_named_step":
        source_step_id = str(execution["source_step"]["step_id"])
        assert set(reasoning_bboxes) == {"source_title", "target_title"}
        assert int(execution["target_step"]["order_index"]) == int(execution["source_step"]["order_index"]) + 1
        assert reasoning_bboxes["source_title"] == trace["render_map"]["title_bboxes_px"][source_step_id]
    else:
        assert execution["source_step"] is None
    example = _extract_prompt_json_example(out.prompt)
    assert list(example.keys()) == ["annotation", "answer"]
    assert isinstance(example["answer"], str)
    assert isinstance(example["annotation"], list)
    assert len(example["annotation"]) == 4


@pytest.mark.parametrize("scene_variant", _lifecycle.SUPPORTED_SCENE_VARIANTS)
def test_pages_step_list_scene_variants_render_inside_canvas(scene_variant: str) -> None:
    task = PagesStepListNthStepFieldLabelTask()
    out = task.generate(
        67440 + _lifecycle.SUPPORTED_SCENE_VARIANTS.index(scene_variant),
        params={
            "query_id": "nth_step_title",
            "scene_variant": scene_variant,
            "step_count": 8,
            "pages_context_text_enabled": False,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    render = trace["render_spec"]
    assert str(render["scene_variant"]) == scene_variant
    assert int(trace["execution_trace"]["step_count"]) == 8
    for step in trace["execution_trace"]["steps"]:
        for key in ("card_bbox_px", "number_badge_bbox_px", "number_bbox_px", "title_bbox_px", "detail_bbox_px"):
            _assert_bbox_inside_canvas(step[key], width=int(render["canvas_width"]), height=int(render["canvas_height"]))


def test_pages_step_list_is_deterministic() -> None:
    task = PagesStepListStepAfterNamedStepLabelTask()
    params = {
        "scene_variant": "two_column_cards",
        "step_count": 7,
        "source_step_index": 2,
        "pages_context_text_enabled": False,
    }
    out_a = task.generate(67991, params=params, max_attempts=10)
    out_b = task.generate(67991, params=params, max_attempts=10)
    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
