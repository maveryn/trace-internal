"""Tests for the synthetic 3D logical predicate count task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.shared.named_colors import available_named_colors
from trace.tasks.three_d.shared.object_scene_logical_predicate_count import (
    MULTI_ATTRIBUTE_AND_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_OR_COUNT_TASK_ID,
    MULTI_ATTRIBUTE_XOR_COUNT_TASK_ID,
    PROMPT_COLOR_RGB,
    SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID,
)
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract

TASK_ID_BY_QUERY_ID = {
    "object_type_count": SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID,
    "object_type_union_count": SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID,
    "color_union_count": SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID,
    "object_type_and_color_count": MULTI_ATTRIBUTE_AND_COUNT_TASK_ID,
    "object_type_or_color_count": MULTI_ATTRIBUTE_OR_COUNT_TASK_ID,
    "exactly_one_object_type_or_color_count": MULTI_ATTRIBUTE_XOR_COUNT_TASK_ID,
    "object_type_and_not_color_count": MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID,
    "color_and_not_object_type_count": MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID,
}


def test_logical_predicate_count_prompt_colors_use_canonical_palette() -> None:
    canonical = {
        str(name): (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        for name, rgb in available_named_colors()
    }

    assert dict(PROMPT_COLOR_RGB) == canonical


def _spec_matches_target(spec: dict, target_spec: dict) -> bool:
    shape_type = str(spec["shape_type"])
    color_name = str(spec["color_name"])
    query_id = str(target_spec["query_id"])
    target_shape_type = target_spec.get("target_shape_type")
    target_color_name = target_spec.get("target_color_name")
    target_shape_types = {str(value) for value in target_spec.get("target_shape_types", [])}
    target_color_names = {str(value) for value in target_spec.get("target_color_names", [])}

    if query_id == "object_type_count":
        return shape_type == str(target_shape_type)
    if query_id == "object_type_union_count":
        return shape_type in target_shape_types
    if query_id == "color_union_count":
        return color_name in target_color_names
    if query_id == "object_type_and_color_count":
        return shape_type == str(target_shape_type) and color_name == str(target_color_name)
    if query_id == "object_type_or_color_count":
        return shape_type == str(target_shape_type) or color_name == str(target_color_name)
    if query_id == "exactly_one_object_type_or_color_count":
        return (shape_type == str(target_shape_type)) ^ (color_name == str(target_color_name))
    if query_id == "object_type_and_not_color_count":
        return shape_type == str(target_shape_type) and color_name != str(target_color_name)
    if query_id == "color_and_not_object_type_count":
        return color_name == str(target_color_name) and shape_type != str(target_shape_type)
    raise AssertionError(f"unsupported query_id in test: {query_id}")


@pytest.mark.parametrize(
    ("query_id", "params"),
    [
        ("object_type_count", {"target_shape_type": "cylinder"}),
        ("object_type_union_count", {"target_shape_types": ["sphere", "cone"]}),
        ("color_union_count", {"target_color_names": ["red", "blue"]}),
        ("object_type_and_color_count", {"target_shape_type": "cube", "target_color_name": "red"}),
        ("object_type_or_color_count", {"target_shape_type": "cube", "target_color_name": "red"}),
        ("exactly_one_object_type_or_color_count", {"target_shape_type": "cube", "target_color_name": "red"}),
        ("object_type_and_not_color_count", {"target_shape_type": "cube", "target_color_name": "red"}),
        ("color_and_not_object_type_count", {"target_shape_type": "cube", "target_color_name": "red"}),
    ],
)
def test_logical_predicate_count_answer_and_annotation(query_id: str, params: dict) -> None:
    task = create_task(TASK_ID_BY_QUERY_ID[query_id])
    request_params = {
        "scene_variant": "floor_grid_room",
        "object_count": 13,
        "target_count": 4,
        "post_image_noise_apply_prob": 0.0,
        **params,
    }
    if len(tuple(getattr(task, "supported_query_ids", ()))) > 1:
        request_params["query_id"] = query_id
    output = task.generate(
        20260531 + len(query_id),
        params=request_params,
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    target_spec = dict(trace["target_spec"])
    object_specs = list(trace["object_specs"])
    expected_ids = [
        str(spec["object_id"])
        for spec in sorted(object_specs, key=lambda item: str(item["object_id"]))
        if _spec_matches_target(spec, target_spec)
    ]

    assert output.scene_id == "object_scene"
    assert output.query_id == (query_id if "query_id" in request_params else "single")
    assert target_spec["query_id"] == query_id
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == 4
    assert output.answer_gt.value == len(target_object_ids)
    assert output.annotation_gt.type == "bbox_set"
    assert target_object_ids == expected_ids
    assert len(output.annotation_gt.value) == int(output.answer_gt.value)
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_object_ids]
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert all(bool(spec.get("is_countable_object", False)) for spec in object_specs)
    assert all(not bool(spec.get("is_answer_candidate", False)) for spec in object_specs)
    assert all("color_name" in spec and "fill_rgb" in spec for spec in object_specs)
    assert all(bool(spec.get("matches_query", False)) == _spec_matches_target(spec, target_spec) for spec in object_specs)
    assert "clear prompt colors" not in output.prompt
    prompt_lower = str(output.prompt).lower()
    assert "how many" in prompt_lower or "count" in prompt_lower or "what is the number" in prompt_lower
    assert_three_d_canvas_contract(output)


@pytest.mark.parametrize("task_id", sorted(set(TASK_ID_BY_QUERY_ID.values())))
def test_logical_predicate_count_task_registered_in_three_d_taxonomy(task_id: str) -> None:
    taxonomy = resolve_task_taxonomy(task_id)

    assert task_id in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_scene"
    assert not taxonomy.source_scene_id
