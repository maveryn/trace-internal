"""Behavior tests for pages numbered step-list lookup tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks.pages.step_list.ordinal_step_detail_label import (
    SUPPORTED_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    PagesStepListNthStepDetailLabelTask,
    PagesStepListNthStepTitleLabelTask,
    PagesStepListOrdinalStepDetailLabelTask,
    PagesStepListStepAfterNamedStepLabelTask,
    PagesStepListStepForDetailLabelTask,
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


def _assert_keyed_bboxes_inside_canvas(annotation: dict, *, width: int, height: int) -> None:
    assert annotation
    for bbox in annotation.values():
        _assert_bbox_inside_canvas([float(value) for value in bbox], width=int(width), height=int(height))


def _expected_answer(execution: dict) -> str:
    query_id = str(execution.get("internal_query_id") or execution["query_id"])
    target_step = dict(execution["target_step"])
    if query_id == "nth_step_detail":
        return str(target_step["detail"])
    if query_id == "step_number_for_detail":
        return str(target_step["step_number"])
    return str(target_step["title"])


def _task_for_query(query_id: str):
    return {
        "nth_step_title": PagesStepListNthStepTitleLabelTask,
        "nth_step_detail": PagesStepListNthStepDetailLabelTask,
        "step_after_named_step": PagesStepListStepAfterNamedStepLabelTask,
        "step_title_for_detail": PagesStepListStepForDetailLabelTask,
        "step_number_for_detail": PagesStepListStepForDetailLabelTask,
    }[str(query_id)]()


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_pages_step_list_query_variants_match_contract(query_id: str) -> None:
    task = _task_for_query(query_id)
    out = task.generate(
        67120 + SUPPORTED_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "step_count": 6, "pages_context_text_enabled": False},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_id == query_id
    assert out.scene_id == "step_list"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["step_count"]) == 6
    assert len(execution["steps"]) == 6
    assert len(trace["scene_ir"]["entities"]) == 6

    expected = _expected_answer(execution)
    assert str(out.answer_gt.value) == expected
    assert str(execution["answer_value"]) == expected
    assert str(trace["query_spec"]["params"]["target_answer"]) == expected
    assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value

    annotation_bboxes = {str(key): [float(value) for value in bbox] for key, bbox in out.annotation_gt.value.items()}
    _assert_keyed_bboxes_inside_canvas(
        annotation_bboxes,
        width=int(render["canvas_width"]),
        height=int(render["canvas_height"]),
    )

    target_step_id = str(execution["target_step"]["step_id"])
    if query_id == "nth_step_detail":
        assert set(annotation_bboxes) == {"target_detail"}
        assert annotation_bboxes["target_detail"] == trace["render_map"]["detail_bboxes_px"][target_step_id]
    elif query_id == "step_title_for_detail":
        assert set(annotation_bboxes) == {"source_detail", "target_title"}
        assert annotation_bboxes["source_detail"] == trace["render_map"]["detail_bboxes_px"][target_step_id]
        assert annotation_bboxes["target_title"] == trace["render_map"]["title_bboxes_px"][target_step_id]
        assert str(execution["source_step_detail"]) == str(execution["target_step"]["detail"])
    elif query_id == "step_number_for_detail":
        assert set(annotation_bboxes) == {"source_detail", "target_number"}
        assert annotation_bboxes["source_detail"] == trace["render_map"]["detail_bboxes_px"][target_step_id]
        assert annotation_bboxes["target_number"] == trace["render_map"]["number_bboxes_px"][target_step_id]
        assert str(execution["source_step_detail"]) == str(execution["target_step"]["detail"])
    else:
        assert "target_title" in annotation_bboxes
        assert annotation_bboxes["target_title"] == trace["render_map"]["title_bboxes_px"][target_step_id]

    if query_id == "step_after_named_step":
        source_step_id = str(execution["source_step"]["step_id"])
        assert set(annotation_bboxes) == {"source_title", "target_title"}
        assert int(execution["target_step"]["order_index"]) == int(execution["source_step"]["order_index"]) + 1
        assert annotation_bboxes["source_title"] == trace["render_map"]["title_bboxes_px"][source_step_id]
    else:
        assert execution["source_step"] is None

    example = _extract_prompt_json_example(out.prompt)
    assert list(example.keys()) == ["annotation", "answer"]
    assert isinstance(example["answer"], str)
    assert isinstance(example["annotation"], dict)


@pytest.mark.parametrize("scene_variant", SUPPORTED_SCENE_VARIANTS)
def test_pages_step_list_scene_variants_render_inside_canvas(scene_variant: str) -> None:
    task = PagesStepListOrdinalStepDetailLabelTask()
    out = task.generate(
        67440 + SUPPORTED_SCENE_VARIANTS.index(scene_variant),
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
        for key in ("card_bbox_px", "number_bbox_px", "title_bbox_px", "detail_bbox_px"):
            _assert_bbox_inside_canvas(
                step[key],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )


def test_pages_step_list_is_deterministic() -> None:
    task = PagesStepListOrdinalStepDetailLabelTask()
    params = {
        "query_id": "step_after_named_step",
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
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()
