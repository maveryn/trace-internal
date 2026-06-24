"""Tests for the 3D warehouse shelf-level item count task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.warehouse.scoped_attribute_count import (
    SCENE_ID,
    SHELF_LEVELS_BY_QUERY_ID,
    SHELF_LEVEL_NAMES,
    SUPPORTED_AISLE_HEADINGS,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
)
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


@pytest.mark.parametrize(
    ("query_id", "target_count", "aisle_heading"),
    [
        ("top_shelf_item_count", 0, "east"),
        ("middle_shelf_item_count", 3, "north"),
        ("bottom_shelf_item_count", 5, "west"),
    ],
)
def test_warehouse_shelf_level_count_answer_annotation_and_geometry(
    query_id: str,
    target_count: int,
    aisle_heading: str,
) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260601 + int(target_count),
        params={
            "query_id": query_id,
            "scene_variant": "storage_aisle",
            "aisle_heading": aisle_heading,
            "rack_count": 4,
            "target_count": target_count,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=1200,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    entities = output.trace_payload["scene_ir"]["entities"]
    target_item_ids = [str(object_id) for object_id in trace["target_item_ids"]]
    target_level_name, target_level_index = SHELF_LEVELS_BY_QUERY_ID[query_id]
    target_rack_id = str(trace["target_rack_id"])
    shelf_items = list(trace["shelf_item_specs"])
    racks = list(trace["rack_specs"])
    expected_target_ids = [
        str(spec["object_id"])
        for spec in sorted(shelf_items, key=lambda item: str(item["object_id"]))
        if str(spec["rack_id"]) == target_rack_id and str(spec["shelf_level"]) == target_level_name
    ]

    assert output.scene_id == SCENE_ID
    assert output.query_id == query_id
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == target_count
    assert output.annotation_gt.type == "bbox_set"
    assert target_item_ids == expected_target_ids
    assert len(output.annotation_gt.value) == int(output.answer_gt.value)
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_item_ids]
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert 2 <= int(trace["rack_count"]) <= 4
    assert len(racks) == int(trace["rack_count"])
    assert len({str(rack["rack_color_name"]) for rack in racks}) == int(trace["rack_count"])
    assert all(int(rack["shelf_levels"]) == 3 for rack in racks)
    assert all(list(rack["shelf_level_names"]) == list(SHELF_LEVEL_NAMES) for rack in racks)
    assert all(list(rack["shelf_load_slots"]) == [] for rack in racks)
    assert all(str(item["object_role"]) == "warehouse_shelf_item" for item in shelf_items)
    shelf_item_entity = next(entity for entity in entities if str(entity["entity_type"]) == "three_d_warehouse_shelf_item")
    shelf_item_record = shelf_item_entity["attrs"]["object_record"]
    assert shelf_item_record["object_id"] == str(shelf_item_entity["entity_id"])
    assert shelf_item_record["visual_attributes"]["renderer_id"] == "warehouse_object"
    assert shelf_item_record["visual_attributes"]["renderer_style"] == "projected_3d"
    assert all(bool(item.get("is_countable_object", False)) for item in shelf_items)
    assert all(not bool(item.get("is_answer_candidate", False)) for item in shelf_items)
    assert all(bool(item["matches_query"]) == (str(item["object_id"]) in set(target_item_ids)) for item in shelf_items)
    assert all(str(item["rack_id"]) == target_rack_id for item in shelf_items if bool(item["matches_query"]))
    assert all(str(item["shelf_level"]) == target_level_name for item in shelf_items if bool(item["matches_query"]))
    assert int(trace["target_shelf_level_index"]) == int(target_level_index)
    assert str(trace["target_shelf_level"]) == target_level_name
    assert str(trace["target_rack_color_label"]) in output.prompt
    assert target_level_name in output.prompt
    assert "How many" in output.prompt or "Count" in output.prompt or "number" in output.prompt
    assert "option" not in output.prompt.lower()
    assert "red-boxed" not in output.prompt
    assert "clear prompt colors" not in output.prompt
    assert_three_d_canvas_contract(output)


def test_warehouse_shelf_level_count_registered() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_scene_id == ""
    assert SUPPORTED_QUERY_IDS == (
        "top_shelf_item_count",
        "middle_shelf_item_count",
        "bottom_shelf_item_count",
    )
    assert SUPPORTED_AISLE_HEADINGS == ("east", "north", "west", "south")
