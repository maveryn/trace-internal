"""Behavior tests for pages document-lookup tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks.pages.document_lookup.card_and_list_lookup import (
    PROFILE_QUERY_IDS,
    PROFILE_SCENE_VARIANTS,
    RANKED_QUERY_IDS,
    RANKED_SCENE_VARIANTS,
    PagesProfileCardGridFieldExtremumProfileLabelTask,
    PagesProfileCardGridFieldRankedProfileLabelTask,
    PagesProfileCardGridProfileForFieldValueTask,
    PagesProfileCardGridValueForNamedProfileFieldTask,
    PagesRankedListEntryAfterNamedEntryLabelTask,
    PagesRankedListOrdinalEntryLabelTask,
)
from trace.tasks.pages.document_lookup.category_grid import (
    CATEGORY_ITEM_COUNT_QUERY_ID,
    CATEGORY_ITEM_COUNT_TASK_ID,
    CATEGORY_SLOT_ITEM_QUERY_ID,
    CATEGORY_SLOT_ITEM_TASK_ID,
    SCENE_VARIANTS as CATEGORY_GRID_SCENE_VARIANTS,
    PagesCategoryGridCategoryItemCountTask,
    PagesCategoryGridCategorySlotItemLabelTask,
)
from trace.tasks.pages.document_lookup.comparison_panel import (
    COMPARISON_PANEL_TASK_ID,
    QUERY_ID as COMPARISON_QUERY_ID,
    SCENE_VARIANTS as COMPARISON_SCENE_VARIANTS,
    PagesComparisonPanelSideAttributeValueLabelTask,
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


def _profile_task_for_query(query_id: str):
    if str(query_id) == "profile_for_field_value":
        return PagesProfileCardGridProfileForFieldValueTask()
    if str(query_id) == "value_for_named_profile_field":
        return PagesProfileCardGridValueForNamedProfileFieldTask()
    if str(query_id) in {"highest_field_profile_label", "lowest_field_profile_label"}:
        return PagesProfileCardGridFieldExtremumProfileLabelTask()
    if str(query_id) in {"nth_highest_field_profile_label", "nth_lowest_field_profile_label"}:
        return PagesProfileCardGridFieldRankedProfileLabelTask()
    raise AssertionError(f"unexpected profile-card query id: {query_id}")


def _ranked_task_for_query(query_id: str):
    if str(query_id) == "entry_after_named_entry":
        return PagesRankedListEntryAfterNamedEntryLabelTask()
    return PagesRankedListOrdinalEntryLabelTask()


def test_comparison_panel_side_attribute_value_contract() -> None:
    task = PagesComparisonPanelSideAttributeValueLabelTask()
    out = task.generate(
        77590,
        params={
            "query_id": COMPARISON_QUERY_ID,
            "scene_variant": "matrix_sheet",
            "side_count": 3,
            "attribute_count": 5,
            "pages_context_text_enabled": False,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    target = execution["target"]
    side_id = str(target["side_id"])
    attribute_id = str(target["attribute_id"])

    assert task.task_id == COMPARISON_PANEL_TASK_ID
    assert out.scene_id == "comparison_panel"
    assert out.query_id == COMPARISON_QUERY_ID
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert list(out.annotation_gt.value) == ["side_header", "attribute_label", "value_cell"]
    assert str(out.answer_gt.value) == str(target["value"])
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["side_count"]) == 3
    assert int(execution["attribute_count"]) == 5
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert out.annotation_gt.value["side_header"] == trace["render_map"]["side_header_bboxes_px"][side_id]
    assert out.annotation_gt.value["attribute_label"] == trace["render_map"]["attribute_label_bboxes_px"][attribute_id]
    assert out.annotation_gt.value["value_cell"] == trace["render_map"]["value_cell_bboxes_px"][attribute_id][side_id]
    assert str(render["background_style"]["style_spec"]["kind"]) == "information_scene_style"
    assert str(render["information_scene_style"]["kind"]) == "information_scene_style"
    for bbox in out.annotation_gt.value.values():
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))

    example = _extract_prompt_json_example(out.prompt)
    assert list(example.keys()) == ["annotation", "answer"]
    assert list(example["annotation"]) == ["side_header", "attribute_label", "value_cell"]


def test_category_grid_slot_item_label_contract() -> None:
    task = PagesCategoryGridCategorySlotItemLabelTask()
    out = task.generate(
        78701,
        params={
            "query_id": CATEGORY_SLOT_ITEM_QUERY_ID,
            "scene_variant": "card_grid",
            "category_count": 3,
            "subcategory_count": 2,
            "item_count_support": [3],
            "target_category_index": 1,
            "target_subcategory_index": 0,
            "target_slot_index": 2,
            "pages_context_text_enabled": False,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    target = execution["target"]
    category_id = str(target["category_id"])
    subcategory_id = str(target["subcategory_id"])
    item_id = str(target["item_id"])

    assert task.task_id == CATEGORY_SLOT_ITEM_TASK_ID
    assert out.scene_id == "category_grid"
    assert out.query_id == CATEGORY_SLOT_ITEM_QUERY_ID
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert list(out.annotation_gt.value) == ["category_header", "subcategory_header", "target_item"]
    assert str(out.answer_gt.value) == str(target["item_label"])
    assert int(target["slot_index"]) == 3
    assert str(target["slot_ordinal"]) == "third"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert out.annotation_gt.value["category_header"] == trace["render_map"]["category_header_bboxes_px"][category_id]
    assert out.annotation_gt.value["subcategory_header"] == trace["render_map"]["subcategory_header_bboxes_px"][category_id][subcategory_id]
    assert out.annotation_gt.value["target_item"] == trace["render_map"]["item_row_bboxes_px"][category_id][subcategory_id][item_id]
    assert str(render["background_style"]["style_spec"]["kind"]) == "information_scene_style"
    assert str(render["information_scene_style"]["kind"]) == "information_scene_style"
    assert str(render["layout"]["scene_variant"]) == "card_grid"
    for bbox in out.annotation_gt.value.values():
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))

    example = _extract_prompt_json_example(out.prompt)
    assert list(example.keys()) == ["annotation", "answer"]
    assert list(example["annotation"]) == ["category_header", "subcategory_header", "target_item"]


def test_category_grid_item_count_contract() -> None:
    task = PagesCategoryGridCategoryItemCountTask()
    out = task.generate(
        78711,
        params={
            "query_id": CATEGORY_ITEM_COUNT_QUERY_ID,
            "scene_variant": "column_groups",
            "category_count": 4,
            "subcategory_count": 3,
            "item_count_support": [4],
            "target_category_index": 2,
            "target_subcategory_index": 1,
            "pages_context_text_enabled": False,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    target = execution["target"]
    category_id = str(target["category_id"])
    subcategory_id = str(target["subcategory_id"])
    target_category = next(category for category in execution["categories"] if str(category["category_id"]) == category_id)
    target_subcategory = next(
        subcategory
        for subcategory in target_category["subcategories"]
        if str(subcategory["subcategory_id"]) == subcategory_id
    )
    expected_bboxes = [
        trace["render_map"]["item_row_bboxes_px"][category_id][subcategory_id][str(item["item_id"])]
        for item in target_subcategory["items"]
    ]

    assert task.task_id == CATEGORY_ITEM_COUNT_TASK_ID
    assert out.scene_id == "category_grid"
    assert out.query_id == CATEGORY_ITEM_COUNT_QUERY_ID
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == int(target["item_count"]) == 4
    assert out.annotation_gt.value == expected_bboxes
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert str(render["layout"]["scene_variant"]) == "column_groups"
    for bbox in out.annotation_gt.value:
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))

    example = _extract_prompt_json_example(out.prompt)
    assert list(example.keys()) == ["annotation", "answer"]
    assert isinstance(example["answer"], int)
    assert isinstance(example["annotation"], list)


@pytest.mark.parametrize("scene_variant", CATEGORY_GRID_SCENE_VARIANTS)
def test_category_grid_scene_variants_render_inside_canvas(scene_variant: str) -> None:
    task = PagesCategoryGridCategorySlotItemLabelTask()
    out = task.generate(
        78730 + CATEGORY_GRID_SCENE_VARIANTS.index(scene_variant),
        params={
            "query_id": CATEGORY_SLOT_ITEM_QUERY_ID,
            "scene_variant": scene_variant,
            "category_count": 4,
            "subcategory_count": 3,
            "item_count_support": [3],
            "pages_context_text_enabled": False,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    render = trace["render_spec"]
    assert str(render["scene_variant"]) == scene_variant
    assert len(trace["execution_trace"]["categories"]) == 4
    for bbox in trace["render_map"]["category_header_bboxes_px"].values():
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    for category_map in trace["render_map"]["subcategory_header_bboxes_px"].values():
        for bbox in category_map.values():
            _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    for category_map in trace["render_map"]["item_row_bboxes_px"].values():
        for subcategory_map in category_map.values():
            for bbox in subcategory_map.values():
                _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))


@pytest.mark.parametrize("scene_variant", COMPARISON_SCENE_VARIANTS)
def test_comparison_panel_scene_variants_render_inside_canvas(scene_variant: str) -> None:
    task = PagesComparisonPanelSideAttributeValueLabelTask()
    out = task.generate(
        77630 + COMPARISON_SCENE_VARIANTS.index(scene_variant),
        params={
            "query_id": COMPARISON_QUERY_ID,
            "scene_variant": scene_variant,
            "side_count": 2,
            "attribute_count": 4,
            "pages_context_text_enabled": False,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    render = trace["render_spec"]
    assert str(render["scene_variant"]) == scene_variant
    for bbox in trace["render_map"]["side_header_bboxes_px"].values():
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    for bbox in trace["render_map"]["attribute_label_bboxes_px"].values():
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    for attribute_values in trace["render_map"]["value_cell_bboxes_px"].values():
        for bbox in attribute_values.values():
            _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))


@pytest.mark.parametrize("query_id", PROFILE_QUERY_IDS)
def test_profile_card_grid_lookup_variants_match_contract(query_id: str) -> None:
    task = _profile_task_for_query(query_id)
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
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["card_count"]) == 6
    assert len(execution["cards"]) == 6

    expected = str(target["field_value"]) if query_id == "value_for_named_profile_field" else str(target["profile_name"])
    assert str(out.answer_gt.value) == expected
    assert str(execution["answer_value"]) == expected
    assert str(trace["query_spec"]["params"]["target_answer"]) == expected
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value

    annotation_bboxes = [[float(value) for value in bbox] for bbox in out.annotation_gt.value.values()]
    is_extremum_query = query_id in {"highest_field_profile_label", "lowest_field_profile_label"}
    is_ranked_query = query_id in {"nth_highest_field_profile_label", "nth_lowest_field_profile_label"}
    is_order_query = bool(is_extremum_query or is_ranked_query)
    expected_annotation_keys = (
        ["target_profile", "field_label", "target_value"]
        if is_order_query
        else ["profile_name", "field_label", "field_value"]
    )
    assert list(out.annotation_gt.value) == expected_annotation_keys
    for bbox in annotation_bboxes:
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    if is_order_query:
        assert out.annotation_gt.value["target_profile"] == trace["render_map"]["name_bboxes_px"][profile_id]
        assert out.annotation_gt.value["field_label"] == trace["render_map"]["field_label_bboxes_px"][profile_id][field_label]
        assert out.annotation_gt.value["target_value"] == trace["render_map"]["field_value_bboxes_px"][profile_id][field_label]
        candidates = list(execution["candidate_profiles"])
        values = [int(candidate["numeric_value"]) for candidate in candidates]
        assert len(candidates) == 6
        assert len(values) == len(set(values))
        target_numeric_value = int(target["field_numeric_value"])
        rank_direction = "highest" if query_id in {"highest_field_profile_label", "nth_highest_field_profile_label"} else "lowest"
        sorted_values = sorted(values, reverse=(rank_direction == "highest"))
        assert values == sorted_values
        if is_extremum_query and rank_direction == "highest":
            assert target_numeric_value == sorted_values[0]
            assert str(execution["extremum_direction"]) == rank_direction
        elif is_extremum_query:
            assert target_numeric_value == sorted_values[0]
            assert str(execution["extremum_direction"]) == rank_direction
        else:
            rank_position = int(execution["rank_position"])
            assert rank_position in {2, 3}
            assert str(execution["rank_direction"]) == rank_direction
            assert str(execution["rank_ordinal"]) in {"second", "third"}
            assert target_numeric_value == sorted_values[int(rank_position) - 1]
            assert int(trace["query_spec"]["params"]["rank_position"]) == rank_position
            assert str(trace["query_spec"]["params"]["rank_ordinal"]) == str(execution["rank_ordinal"])
            assert str(execution["rank_ordinal"]) in out.prompt
        assert any(
            str(candidate["profile_id"]) == profile_id and int(candidate["numeric_value"]) == target_numeric_value
            for candidate in candidates
        )
        for candidate in candidates:
            assert str(candidate["field_label"]) == field_label
            _assert_bbox_inside_canvas(
                candidate["profile_name_bbox_px"],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )
            _assert_bbox_inside_canvas(
                candidate["field_label_bbox_px"],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )
            _assert_bbox_inside_canvas(
                candidate["field_value_bbox_px"],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )
    else:
        assert out.annotation_gt.value["profile_name"] == trace["render_map"]["name_bboxes_px"][profile_id]
        assert out.annotation_gt.value["field_label"] == trace["render_map"]["field_label_bboxes_px"][profile_id][field_label]
        assert out.annotation_gt.value["field_value"] == trace["render_map"]["field_value_bboxes_px"][profile_id][field_label]

    example = _extract_prompt_json_example(out.prompt)
    assert list(example.keys()) == ["annotation", "answer"]
    assert isinstance(example["answer"], str)
    assert list(example["annotation"]) == expected_annotation_keys


@pytest.mark.parametrize("scene_variant", PROFILE_SCENE_VARIANTS)
def test_profile_card_grid_scene_variants_render_inside_canvas(scene_variant: str) -> None:
    task = PagesProfileCardGridValueForNamedProfileFieldTask()
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
    task = _ranked_task_for_query(query_id)
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
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["section_count"]) == 2
    assert int(execution["item_count"]) == 6
    assert str(out.answer_gt.value) == str(target["answer_value"])
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value

    annotation_bboxes = [[float(value) for value in bbox] for bbox in out.annotation_gt.value.values()]
    expected_keys = ["section_title", "source_item", "target_item"] if query_id == "entry_after_named_entry" else ["section_title", "target_item"]
    assert list(out.annotation_gt.value) == expected_keys
    for bbox in annotation_bboxes:
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))
    assert out.annotation_gt.value["section_title"] == trace["render_map"]["section_title_bboxes_px"][section_id]
    assert out.annotation_gt.value["target_item"] == trace["render_map"]["item_bboxes_px"][section_id][item_id]
    if query_id == "entry_after_named_entry":
        source_item_id = f"{section_id}_item_{int(target['source_index']) + 1}"
        assert out.annotation_gt.value["source_item"] == trace["render_map"]["item_bboxes_px"][section_id][source_item_id]

    example = _extract_prompt_json_example(out.prompt)
    assert list(example.keys()) == ["annotation", "answer"]
    assert isinstance(example["answer"], str)
    assert "section_title" in example["annotation"]
    assert "target_item" in example["annotation"]


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
    category_task = PagesCategoryGridCategorySlotItemLabelTask()
    profile_task = PagesProfileCardGridProfileForFieldValueTask()
    extremum_task = PagesProfileCardGridFieldExtremumProfileLabelTask()
    profile_ranked_task = PagesProfileCardGridFieldRankedProfileLabelTask()
    ranked_task = PagesRankedListEntryAfterNamedEntryLabelTask()
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
    extremum_params = {
        "query_id": "highest_field_profile_label",
        "card_count": 9,
        "field_label": "Score",
        "pages_context_text_enabled": False,
    }
    profile_ranked_params = {
        "query_id": "nth_lowest_field_profile_label",
        "card_count": 9,
        "field_label": "Cases",
        "rank_position": 3,
        "pages_context_text_enabled": False,
    }
    category_params = {
        "query_id": CATEGORY_SLOT_ITEM_QUERY_ID,
        "scene_variant": "compact_index",
        "category_count": 4,
        "subcategory_count": 2,
        "item_count_support": [3],
        "target_category_index": 1,
        "target_subcategory_index": 1,
        "target_slot_index": 0,
        "pages_context_text_enabled": False,
    }
    category_a = category_task.generate(77900, params=category_params, max_attempts=10)
    category_b = category_task.generate(77900, params=category_params, max_attempts=10)
    profile_a = profile_task.generate(77901, params=profile_params, max_attempts=10)
    profile_b = profile_task.generate(77901, params=profile_params, max_attempts=10)
    extremum_a = extremum_task.generate(77903, params=extremum_params, max_attempts=10)
    extremum_b = extremum_task.generate(77903, params=extremum_params, max_attempts=10)
    profile_ranked_a = profile_ranked_task.generate(77904, params=profile_ranked_params, max_attempts=10)
    profile_ranked_b = profile_ranked_task.generate(77904, params=profile_ranked_params, max_attempts=10)
    ranked_a = ranked_task.generate(77902, params=ranked_params, max_attempts=10)
    ranked_b = ranked_task.generate(77902, params=ranked_params, max_attempts=10)

    assert category_a.prompt == category_b.prompt
    assert category_a.answer_gt.to_dict() == category_b.answer_gt.to_dict()
    assert category_a.annotation_gt.to_dict() == category_b.annotation_gt.to_dict()
    assert category_a.trace_payload["execution_trace"] == category_b.trace_payload["execution_trace"]
    assert profile_a.prompt == profile_b.prompt
    assert profile_a.answer_gt.to_dict() == profile_b.answer_gt.to_dict()
    assert profile_a.annotation_gt.to_dict() == profile_b.annotation_gt.to_dict()
    assert profile_a.trace_payload["execution_trace"] == profile_b.trace_payload["execution_trace"]
    assert extremum_a.prompt == extremum_b.prompt
    assert extremum_a.answer_gt.to_dict() == extremum_b.answer_gt.to_dict()
    assert extremum_a.annotation_gt.to_dict() == extremum_b.annotation_gt.to_dict()
    assert extremum_a.trace_payload["execution_trace"] == extremum_b.trace_payload["execution_trace"]
    assert profile_ranked_a.prompt == profile_ranked_b.prompt
    assert profile_ranked_a.answer_gt.to_dict() == profile_ranked_b.answer_gt.to_dict()
    assert profile_ranked_a.annotation_gt.to_dict() == profile_ranked_b.annotation_gt.to_dict()
    assert profile_ranked_a.trace_payload["execution_trace"] == profile_ranked_b.trace_payload["execution_trace"]
    assert ranked_a.prompt == ranked_b.prompt
    assert ranked_a.answer_gt.to_dict() == ranked_b.answer_gt.to_dict()
    assert ranked_a.annotation_gt.to_dict() == ranked_b.annotation_gt.to_dict()
    assert ranked_a.trace_payload["execution_trace"] == ranked_b.trace_payload["execution_trace"]
