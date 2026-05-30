"""Behavior tests for pages document-lookup tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks.pages.document_lookup.card_and_list_lookup import (
    PROFILE_QUERY_IDS,
    PROFILE_SCENE_VARIANTS,
    RANKED_QUERY_IDS,
    RANKED_SCENE_VARIANTS,
    PagesProfileCardGridAttributeLookupLabelTask,
    PagesRankedListOrdinalEntryLabelTask,
)


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    return json.loads(str(prompt).split(marker, 1)[1].strip())


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


@pytest.mark.parametrize("query_id", PROFILE_QUERY_IDS)
def test_profile_card_grid_lookup_variants_match_contract(query_id: str) -> None:
    task = PagesProfileCardGridAttributeLookupLabelTask()
    out = task.generate(
        77100 + PROFILE_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "card_count": 6, "pages_context_text_enabled": False},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    target = execution["target_profile"]
    profile_id = str(target["profile_id"])
    field_label = str(target["field_label"])

    assert out.scene_id == "profile_card_grid"
    assert out.query_id == query_id
    assert out.answer_gt.type == "string"
    assert out.evidence_gt.type == "keyed_bbox_map"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["card_count"]) == 6
    assert len(execution["cards"]) == 6

    expected = (
        str(target["field_value"])
        if query_id == "value_for_named_profile_field"
        else str(target["profile_name"])
    )
    assert str(out.answer_gt.value) == expected
    assert str(execution["answer_value"]) == expected
    assert str(trace["query_spec"]["params"]["target_answer"]) == expected
    assert trace["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value

    evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value.values()]
    assert list(out.evidence_gt.value) == ["profile_name", "field_label", "field_value"]
    for bbox in evidence_bboxes:
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    assert out.evidence_gt.value["profile_name"] == trace["render_map"]["name_bboxes_px"][profile_id]
    assert out.evidence_gt.value["field_label"] == trace["render_map"]["field_label_bboxes_px"][profile_id][field_label]
    assert out.evidence_gt.value["field_value"] == trace["render_map"]["field_value_bboxes_px"][profile_id][field_label]

    example = _extract_prompt_json_example(out.prompt)
    assert sorted(example.keys()) == ["answer", "evidence"]
    assert isinstance(example["answer"], str)
    assert list(example["evidence"]) == ["profile_name", "field_label", "field_value"]


@pytest.mark.parametrize("scene_variant", PROFILE_SCENE_VARIANTS)
def test_profile_card_grid_scene_variants_render_inside_canvas(scene_variant: str) -> None:
    task = PagesProfileCardGridAttributeLookupLabelTask()
    out = task.generate(
        77220 + PROFILE_SCENE_VARIANTS.index(scene_variant),
        params={
            "query_id": "value_for_named_profile_field",
            "scene_variant": scene_variant,
            "card_count": 9,
            "pages_context_text_enabled": False,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    render = trace["render_spec"]
    assert str(render["scene_variant"]) == scene_variant
    for card in trace["execution_trace"]["cards"]:
        _assert_bbox_inside_canvas(
            card["card_bbox_px"],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )
        _assert_bbox_inside_canvas(
            card["name_bbox_px"],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )
        for bbox in card["field_value_bboxes_px"].values():
            _assert_bbox_inside_canvas(
                bbox,
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )


@pytest.mark.parametrize("query_id", RANKED_QUERY_IDS)
def test_ranked_list_lookup_variants_match_contract(query_id: str) -> None:
    task = PagesRankedListOrdinalEntryLabelTask()
    out = task.generate(
        77340 + RANKED_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "section_count": 2, "item_count": 6, "pages_context_text_enabled": False},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    target = execution["target_entry"]
    section_id = str(target["section_id"])
    item_id = f"{section_id}_item_{int(target['target_position'])}"

    assert out.scene_id == "ranked_list"
    assert out.query_id == query_id
    assert out.answer_gt.type == "string"
    assert out.evidence_gt.type == "keyed_bbox_map"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["section_count"]) == 2
    assert int(execution["item_count"]) == 6
    assert str(out.answer_gt.value) == str(target["answer_value"])
    assert trace["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value

    evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value.values()]
    expected_keys = ["section_title", "source_item", "target_item"] if query_id == "entry_after_named_entry" else ["section_title", "target_item"]
    assert list(out.evidence_gt.value) == expected_keys
    for bbox in evidence_bboxes:
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    assert out.evidence_gt.value["section_title"] == trace["render_map"]["section_title_bboxes_px"][section_id]
    assert out.evidence_gt.value["target_item"] == trace["render_map"]["item_bboxes_px"][section_id][item_id]
    if query_id == "entry_after_named_entry":
        source_item_id = f"{section_id}_item_{int(target['source_index']) + 1}"
        assert out.evidence_gt.value["source_item"] == trace["render_map"]["item_bboxes_px"][section_id][source_item_id]

    example = _extract_prompt_json_example(out.prompt)
    assert sorted(example.keys()) == ["answer", "evidence"]
    assert isinstance(example["answer"], str)
    assert "section_title" in example["evidence"]
    assert "target_item" in example["evidence"]


@pytest.mark.parametrize("scene_variant", RANKED_SCENE_VARIANTS)
def test_ranked_list_scene_variants_render_inside_canvas(scene_variant: str) -> None:
    task = PagesRankedListOrdinalEntryLabelTask()
    out = task.generate(
        77460 + RANKED_SCENE_VARIANTS.index(scene_variant),
        params={
            "query_id": "nth_entry_label",
            "scene_variant": scene_variant,
            "section_count": 3,
            "item_count": 7,
            "pages_context_text_enabled": False,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    render = trace["render_spec"]
    assert str(render["scene_variant"]) == scene_variant
    for section in trace["execution_trace"]["sections"]:
        _assert_bbox_inside_canvas(
            section["section_bbox_px"],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )
        for bbox in section["item_bboxes_px"].values():
            _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))


def test_pages_document_lookup_tasks_are_deterministic() -> None:
    profile_task = PagesProfileCardGridAttributeLookupLabelTask()
    ranked_task = PagesRankedListOrdinalEntryLabelTask()
    profile_params = {
        "query_id": "profile_for_field_value",
        "card_count": 9,
        "profile_index": 3,
        "field_label": "Code",
        "pages_context_text_enabled": False,
    }
    ranked_params = {
        "query_id": "entry_after_named_entry",
        "section_count": 3,
        "item_count": 7,
        "section_index": 1,
        "source_item_index": 2,
        "pages_context_text_enabled": False,
    }
    profile_a = profile_task.generate(77901, params=profile_params, max_attempts=10)
    profile_b = profile_task.generate(77901, params=profile_params, max_attempts=10)
    ranked_a = ranked_task.generate(77902, params=ranked_params, max_attempts=10)
    ranked_b = ranked_task.generate(77902, params=ranked_params, max_attempts=10)

    assert profile_a.prompt == profile_b.prompt
    assert profile_a.answer_gt.to_dict() == profile_b.answer_gt.to_dict()
    assert profile_a.evidence_gt.to_dict() == profile_b.evidence_gt.to_dict()
    assert profile_a.trace_payload["execution_trace"] == profile_b.trace_payload["execution_trace"]
    assert ranked_a.prompt == ranked_b.prompt
    assert ranked_a.answer_gt.to_dict() == ranked_b.answer_gt.to_dict()
    assert ranked_a.evidence_gt.to_dict() == ranked_b.evidence_gt.to_dict()
    assert ranked_a.trace_payload["execution_trace"] == ranked_b.trace_payload["execution_trace"]
