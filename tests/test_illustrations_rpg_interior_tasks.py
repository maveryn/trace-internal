from __future__ import annotations

from collections import Counter
from inspect import getsourcefile
from pathlib import Path

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.rpg_interior.shared.rendering import (
    INTERIOR_TYPES,
    SCENE_ID,
    TARGET_OBJECT_TYPES,
    ZONE_IDS,
    draw_rpg_interior_debug_overlay,
    render_rpg_interior_scene,
)


TASK_ID = "task_illustrations__rpg_interior__object_zone_count"


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= float(width)
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def _assert_point_inside_canvas(point: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(point[0]) <= float(width)
    assert 0 <= float(point[1]) <= float(height)


def test_rpg_interior_renderer_is_deterministic_and_profile_safe() -> None:
    for width, height in ((1200, 800), (960, 960), (800, 1200)):
        first = render_rpg_interior_scene(
            2026061601,
            width=width,
            height=height,
            required_zone_object_counts={"counter": {"bottle": 3}},
        )
        second = render_rpg_interior_scene(
            2026061601,
            width=width,
            height=height,
            required_zone_object_counts={"counter": {"bottle": 3}},
        )

        assert first.image.size == (width, height)
        assert first.image.tobytes() == second.image.tobytes()
        assert first.trace == second.trace
        assert first.trace["scene_id"] == SCENE_ID
        assert draw_rpg_interior_debug_overlay(first).size == first.image.size
        for entity in first.entities:
            _assert_bbox_inside_canvas(
                [float(value) for value in entity.bbox_xyxy],
                width=width,
                height=height,
            )
            record = entity.metadata["object_record"]
            assert record["object_id"] == entity.entity_id
            assert record["visual_attributes"]["renderer_style"] == "top_down_pixel_rpg"
        for region in first.regions:
            _assert_bbox_inside_canvas(
                [float(value) for value in region.bbox_xyxy],
                width=width,
                height=height,
            )


def test_rpg_interior_renderer_covers_room_variants() -> None:
    interior_types = set()
    themes = set()
    floors = set()
    for seed in range(2026061602, 2026061645):
        scene = render_rpg_interior_scene(
            seed,
            required_zone_object_counts={"table": {"mug": 2}},
        )
        interior_types.add(scene.trace["interior_type"])
        themes.add(scene.trace["theme_id"])
        floors.add(scene.trace["floor_pattern"])

    assert set(INTERIOR_TYPES).issubset(interior_types)
    assert len(themes) >= 3
    assert len(floors) >= 2


def test_rpg_interior_object_zone_count_contract() -> None:
    task = create_task(TASK_ID)
    assert not hasattr(task, "scene_id")
    assert Path(getsourcefile(task.__class__) or "").as_posix().endswith(
        "trace/tasks/illustrations/rpg_interior/object_zone_count.py"
    )

    out = task.generate(
        hash64(2026061603, TASK_ID, 0),
        params={
            "canvas_profile": "landscape",
            "target_object_type": "candle",
            "target_zone_id": "table",
            "target_count": 4,
        },
        max_attempts=80,
    )
    trace = out.trace_payload
    params = trace["query_spec"]["params"]
    render_map = trace["render_map"]
    counted_ids = render_map["counted_entity_ids"]
    entities = {entity["entity_id"]: entity for entity in trace["scene_ir"]["entities"]}

    assert out.scene_id == "rpg_interior"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 4
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == 4
    assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_rpg_interior_v0"
    assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == "rpg_interior"
    assert params["query_id"] == "single"
    assert params["target_object_type"] == "candle"
    assert params["target_zone_id"] == "table"
    assert params["zone_relation"] == "on"
    assert params["target_count"] == 4
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert render_map["counted_entity_points_px"] == out.annotation_gt.value

    width, height = out.image.size
    for point in out.annotation_gt.value:
        _assert_point_inside_canvas(point, width=width, height=height)
    for entity_id in counted_ids:
        entity = entities[entity_id]
        assert entity["object_type"] == "candle"
        assert entity["zone_id"] == "table"
        assert entity["countable"] is True
        _assert_bbox_inside_canvas(entity["bbox"], width=width, height=height)


def test_rpg_interior_object_zone_count_support_is_sampled() -> None:
    target_counts: Counter[str] = Counter()
    zone_counts: Counter[str] = Counter()
    for index in range(180):
        out = create_task(TASK_ID).generate(
            hash64(2026061604, TASK_ID, index),
            params={"_sample_cursor": index},
            max_attempts=80,
        )
        params = out.trace_payload["query_spec"]["params"]
        target_counts[str(params["target_object_type"])] += 1
        zone_counts[str(params["target_zone_id"])] += 1
        assert 1 <= int(out.answer_gt.value) <= 5
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)

    assert set(TARGET_OBJECT_TYPES).issubset(set(target_counts))
    assert set(ZONE_IDS).issubset(set(zone_counts))
