"""Tests for indoor-room illustration tasks."""

from __future__ import annotations

from collections import Counter
from inspect import getsourcefile
from pathlib import Path

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.indoor_room.shared.state import INDOOR_OBJECT_TYPES


SURFACE_TASK_ID = "task_illustrations__indoor_room__surface_object_count"
FURNITURE_TASK_ID = "task_illustrations__indoor_room__furniture_side_count"
TASK_SOURCE_STEMS = {
    SURFACE_TASK_ID: "surface_object_count.py",
    FURNITURE_TASK_ID: "furniture_side_count.py",
}


def _assert_scene_packaged_task(task_id: str) -> None:
    task = create_task(task_id)
    assert not hasattr(task, "scene_id")
    source = Path(getsourcefile(task.__class__) or "").as_posix()
    assert source.endswith(
        f"trace/tasks/illustrations/indoor_room/{TASK_SOURCE_STEMS[task_id]}"
    )


def _assert_scene_prompt_metadata(trace: dict) -> None:
    prompt_variant = trace["query_spec"]["prompt_variant"]
    assert prompt_variant["prompt_bundle_id"] == "illustrations_indoor_room_v0"
    assert prompt_variant["prompt_scene_id"] == "indoor_room"


def _expected_bboxes(trace: dict, ids: list[str]) -> list[list[float]]:
    boxes = trace["render_map"]["object_bboxes_px"]
    return [boxes[object_id] for object_id in ids]


def _assert_objects_rest_on_surface(trace: dict, ids: list[str], surface_type: str) -> None:
    placements = trace["render_map"]["placements"]
    for object_id in ids:
        bbox_bottom = trace["render_map"]["object_bboxes_px"][object_id][3]
        contact = placements[object_id]["surface_contact_px"]
        assert placements[object_id]["surface_type"] == surface_type
        assert contact is not None
        assert abs(float(bbox_bottom) - float(contact[1])) <= 8.0


def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.7) + 1


def test_object_type_on_surface_count_contract() -> None:
    _assert_scene_packaged_task(SURFACE_TASK_ID)
    out = create_task(SURFACE_TASK_ID).generate(
        hash64(2026052401, "type-on-surface", 0),
        params={"object_type": "mug", "surface_type": "shelf", "target_count": 2, "object_count": 12, "theme_id": "study"},
        max_attempts=80,
    )
    trace = out.trace_payload
    _assert_scene_prompt_metadata(trace)
    execution = trace["execution_trace"]
    placements = trace["render_map"]["placements"]
    assert out.scene_id == "indoor_room"
    assert out.query_id == "single"
    assert execution["object_type"] == "mug"
    assert execution["surface_type"] == "shelf"
    assert int(out.answer_gt.value) == 2
    assert all(
        placements[object_id]["surface_type"] == "shelf" and placements[object_id]["object_type"] == "mug"
        for object_id in execution["counted_object_ids"]
    )
    _assert_objects_rest_on_surface(trace, execution["counted_object_ids"], "shelf")
    assert sorted(out.annotation_gt.value) == sorted(_expected_bboxes(trace, execution["counted_object_ids"]))


def test_counter_objects_rest_on_surface_baseline() -> None:
    out = create_task(SURFACE_TASK_ID).generate(
        hash64(2026052401, "type-on-counter", 0),
        params={"object_type": "mug", "surface_type": "counter", "target_count": 3, "object_count": 13, "theme_id": "kitchen"},
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    placements = trace["render_map"]["placements"]
    surface_ids = [
        object_id
        for object_id, placement in placements.items()
        if placement["surface_type"] == "counter"
    ]
    assert int(out.answer_gt.value) == 3
    assert execution["surface_type"] == "counter"
    _assert_objects_rest_on_surface(trace, surface_ids, "counter")


def test_indoor_object_pool_uses_small_tabletop_items() -> None:
    assert "umbrella" not in INDOOR_OBJECT_TYPES
    assert "banana" not in INDOOR_OBJECT_TYPES
    assert "trash_bin" not in INDOOR_OBJECT_TYPES
    assert "apple" in INDOOR_OBJECT_TYPES
    assert "egg" in INDOOR_OBJECT_TYPES
    assert "spoon" in INDOOR_OBJECT_TYPES
    assert "plate" in INDOOR_OBJECT_TYPES
    assert "book" in INDOOR_OBJECT_TYPES
    assert "remote" in INDOOR_OBJECT_TYPES
    assert "pencil" in INDOOR_OBJECT_TYPES
    assert "ruler" in INDOOR_OBJECT_TYPES
    assert "clock" in INDOOR_OBJECT_TYPES
    assert "vase" in INDOOR_OBJECT_TYPES
    assert "bowl" in INDOOR_OBJECT_TYPES
    assert "candle" in INDOOR_OBJECT_TYPES


def test_furniture_side_count_contract() -> None:
    _assert_scene_packaged_task(FURNITURE_TASK_ID)
    out = create_task(FURNITURE_TASK_ID).generate(
        hash64(2026052401, "furniture-side", 0),
        params={
            "object_type": "mug",
            "furniture_type": "table",
            "relation": "left",
            "target_count": 3,
            "object_count": 10,
            "theme_id": "bedroom",
        },
        max_attempts=80,
    )
    trace = out.trace_payload
    _assert_scene_prompt_metadata(trace)
    execution = trace["execution_trace"]
    placements = trace["render_map"]["placements"]
    furniture_id = execution["furniture_id"]
    assert out.scene_id == "indoor_room"
    assert out.query_id == "left_side"
    assert execution["object_type"] == "mug"
    assert execution["furniture_type"] == "table"
    assert execution["relation"] == "left"
    assert int(out.answer_gt.value) == 3
    assert all(
        placements[object_id]["relations"][furniture_id]["left"] and placements[object_id]["object_type"] == "mug"
        for object_id in execution["counted_object_ids"]
    )
    assert sorted(out.annotation_gt.value) == sorted(_expected_bboxes(trace, execution["counted_object_ids"]))


def test_furniture_side_count_calibration_sampling_is_decoupled() -> None:
    task = create_task(FURNITURE_TASK_ID)
    answer_counts: Counter[int] = Counter()
    object_type_counts: Counter[str] = Counter()
    furniture_relation_counts: Counter[tuple[str, str]] = Counter()

    for index in range(100):
        out = task.generate(
            hash64(2026052401, "furniture-side-sampling", index),
            params={},
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        answer_counts[int(out.answer_gt.value)] += 1
        object_type_counts[str(execution["object_type"])] += 1
        furniture_relation_counts[(str(execution["furniture_type"]), str(execution["relation"]))] += 1

    _assert_hash_balanced_counts(answer_counts, range(1, 7))
    assert len(object_type_counts) >= 18
    assert set(furniture_relation_counts) == {
        ("table", "left"),
        ("table", "right"),
        ("table", "above"),
        ("table", "below"),
        ("sofa", "above"),
        ("sofa", "below"),
        ("cabinet", "above"),
        ("cabinet", "below"),
    }


def test_furniture_side_count_query_id_selects_relation() -> None:
    task = create_task(FURNITURE_TASK_ID)
    for index, (query_id, relation) in enumerate(
        (
            ("left_side", "left"),
            ("right_side", "right"),
            ("above_side", "above"),
            ("below_side", "below"),
        )
    ):
        out = task.generate(
            hash64(2026052401, "furniture-query", index),
            params={
                "query_id": query_id,
                "object_type": "mug",
                "target_count": 1,
                "object_count": 8,
                "theme_id": "living_room",
            },
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        assert out.query_id == query_id
        assert execution["query_id"] == query_id
        assert execution["relation"] == relation
