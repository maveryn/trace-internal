"""Tests for the synthetic 3D room wall-mounted object count task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.room.wall_mounted_object_count import (
    QUERY_OBJECT_TYPE_BY_VARIANT,
    ROOM_FRONT_Y,
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
)


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_wall_mounted_object_count_answer_and_evidence(query_id: str) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260521,
        params={
            "query_id": query_id,
            "scene_variant": "living_room",
            "target_count": 2,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=80,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_type = QUERY_OBJECT_TYPE_BY_VARIANT[query_id]
    target_specs = [
        spec
        for spec in trace["wall_object_specs"]
        if str(spec["object_type"]) == str(target_type) and bool(spec["is_wall_mounted"])
    ]
    same_type_floor_specs = [
        spec
        for spec in trace["floor_object_specs"]
        if str(spec["object_type"]) == str(target_type) and not bool(spec["is_wall_mounted"])
    ]
    mounted_query_type_context = [
        spec
        for spec in trace["wall_object_specs"]
        if str(spec["object_type"]) in set(QUERY_OBJECT_TYPE_BY_VARIANT.values())
        and str(spec["object_type"]) != str(target_type)
    ]
    expected_ids = [str(spec["object_id"]) for spec in sorted(
        target_specs,
        key=lambda spec: (str(spec.get("wall", "")), float(spec["base_xyz"][2]), float(spec["world_xyz"][0]), float(spec["world_xyz"][1])),
    )]
    assert output.scene_id == SCENE_ID
    assert output.query_id == query_id
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == len(target_specs) == 2
    assert output.evidence_gt.type == "bbox_set"
    assert output.evidence_gt.value == [
        render_map["object_bboxes_px"][object_id]
        for object_id in expected_ids
    ]
    assert trace["target_object_ids"] == expected_ids
    assert trace["target_count"] == len(target_specs)
    assert trace["same_type_floor_distractor_count"] == len(same_type_floor_specs)
    assert len(same_type_floor_specs) >= 1
    assert min(float(spec["base_xyz"][1]) for spec in trace["floor_object_specs"]) <= ROOM_FRONT_Y + 0.55
    assert mounted_query_type_context == []
    if target_type in {"tv", "clock", "picture_frame"}:
        assert trace["same_type_surface_distractor_count"] >= 1
        assert any(str(spec["mounting"]) == "on_furniture" for spec in same_type_floor_specs)
        assert any(spec.get("support_object_id") for spec in same_type_floor_specs)
    if target_type == "picture_frame":
        assert all(str(spec.get("scenery_variant", "")) for spec in [*target_specs, *same_type_floor_specs])
        assert all(str(spec.get("picture_content", "")).startswith("simple ") for spec in [*target_specs, *same_type_floor_specs])
    assert all(str(spec["wall"]) == "back" for spec in target_specs)
    room_shell = next(entity for entity in output.trace_payload["scene_ir"]["entities"] if entity["entity_id"] == "room_shell")
    assert float(room_shell["attrs"]["render_front_y"]) < float(room_shell["attrs"]["semantic_front_y"])
    assert float(room_shell["attrs"]["render_side_wall_front_y"]) < float(room_shell["attrs"]["semantic_front_y"])
    assert float(room_shell["attrs"]["render_side_wall_front_y"]) >= float(room_shell["attrs"]["render_front_y"])
    assert 9.0 <= float(trace["camera"]["pitch_degrees"]) <= 18.0
    assert output.image.size == (1180, 900)


def test_wall_mounted_object_count_allows_zero_targets() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260522,
        params={
            "query_id": "tv_wall_mounted_count",
            "scene_variant": "studio_room",
            "target_count": 0,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=80,
    )

    trace = output.trace_payload["execution_trace"]

    assert output.answer_gt.value == 0
    assert output.evidence_gt.value == []
    assert trace["target_object_ids"] == []
    assert trace["same_type_floor_distractor_count"] >= 1


def test_wall_mounted_object_count_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_task_group == "room"
