"""Contract tests for illustration park/playground tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.counting._park_person_activity_branch import _sample_spec as _sample_person_activity_spec
from trace.tasks.illustrations.counting._park_person_zone_branch import _sample_spec as _sample_person_zone_spec
from trace.tasks.illustrations.counting._park_person_equipment_use_branch import (
    _sample_spec as _sample_person_using_equipment_spec,
)
from trace.tasks.illustrations.counting.playground_equipment_count import (
    _sample_spec as _sample_playground_equipment_spec,
)


def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.7) + 1


def _assert_annotation_inside_canvas(out) -> None:
    width, height = out.trace_payload["render_spec"]["canvas_size"]
    for x0, y0, x1, y1 in out.annotation_gt.value:
        assert 0 <= x0 < x1 <= width
        assert 0 <= y0 < y1 <= height


def test_person_activity_count_contract() -> None:
    out = create_task("task_illustrations__park_playground__activity_person_count").generate(
        hash64(2026052407, "park-person-activity", 0),
        params={"query_id": "playing_ball_person_count", "target_count": 3, "person_count": 9},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_person_ids = execution["counted_person_ids"]
    person_bboxes = trace["render_map"]["person_bboxes_px"]

    assert out.scene_id == "park_playground"
    assert out.query_id == "playing_ball_person_count"
    assert trace["query_spec"]["query_id"] == "playing_ball_person_count"
    assert trace["query_spec"]["task_id"] == "task_illustrations__park_playground__activity_person_count"
    assert trace["query_spec"]["branch_id"] == "park_person_activity"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_person_ids) == 3
    assert execution["target_activity"] == "playing_ball"
    assert sorted(out.annotation_gt.value) == sorted(person_bboxes[person_id] for person_id in counted_person_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    for person in execution["persons"]:
        is_target = person["activity"] == "playing_ball"
        assert (person["person_id"] in set(counted_person_ids)) == is_target


def test_person_activity_countseeded_sampler_covers_answers_and_variants() -> None:
    samples = [
        _sample_person_activity_spec(
            instance_seed=hash64(2026052407, "park-person-activity-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(100)
    ]
    answer_counts = Counter(sample.target_count for sample in samples)
    query_counts = Counter(sample.query_id for sample in samples)

    answer_support = set(range(1, 7))
    query_support = {
        "sitting_person_count",
        "walking_person_count",
        "standing_person_count",
        "playing_ball_person_count",
    }
    _assert_hash_balanced_counts(answer_counts, answer_support)
    _assert_hash_balanced_counts(query_counts, query_support)
    for query_id in query_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.query_id == query_id)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers


def test_playground_equipment_count_contract() -> None:
    out = create_task("task_illustrations__park_playground__playground_equipment_count").generate(
        hash64(2026052407, "park-equipment", 0),
        params={"query_id": "slide_count", "target_count": 3, "equipment_count": 6, "person_count": 6},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_equipment_ids = execution["counted_equipment_ids"]
    decor_bboxes = trace["render_map"]["decor_bboxes_px"]

    assert out.scene_id == "park_playground"
    assert out.query_id == "slide_count"
    assert trace["query_spec"]["query_id"] == "slide_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_equipment_ids) == 3
    assert execution["target_equipment_type"] == "slide"
    assert sorted(out.annotation_gt.value) == sorted(decor_bboxes[equipment_id] for equipment_id in counted_equipment_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    for decor in execution["decor"]:
        if str(decor["decor_id"]).startswith("equipment_"):
            is_target = decor["decor_type"] == "slide"
            assert (decor["decor_id"] in set(counted_equipment_ids)) == is_target


def test_playground_equipment_countseeded_sampler_covers_answers_and_variants() -> None:
    samples = [
        _sample_playground_equipment_spec(
            instance_seed=hash64(2026052407, "park-equipment-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(100)
    ]
    answer_counts = Counter(sample.target_count for sample in samples)
    query_counts = Counter(sample.query_id for sample in samples)

    answer_support = set(range(1, 6))
    query_support = {"slide_count", "swing_set_count", "seesaw_count", "climbing_frame_count"}
    _assert_hash_balanced_counts(answer_counts, answer_support)
    _assert_hash_balanced_counts(query_counts, query_support)
    for query_id in query_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.query_id == query_id)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers


def test_person_using_equipment_count_contract() -> None:
    out = create_task("task_illustrations__park_playground__equipment_use_person_count").generate(
        hash64(2026052407, "park-person-using-equipment", 0),
        params={
            "query_id": "person_using_swing_set_count",
            "target_count": 3,
            "person_count": 10,
            "equipment_count": 6,
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_person_ids = execution["counted_person_ids"]
    person_bboxes = trace["render_map"]["person_bboxes_px"]

    assert out.scene_id == "park_playground"
    assert out.query_id == "person_using_swing_set_count"
    assert trace["query_spec"]["query_id"] == "person_using_swing_set_count"
    assert trace["query_spec"]["task_id"] == "task_illustrations__park_playground__equipment_use_person_count"
    assert trace["query_spec"]["branch_id"] == "park_person_equipment_use"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_person_ids) == 3
    assert execution["target_equipment_type"] == "swing_set"
    assert sorted(out.annotation_gt.value) == sorted(person_bboxes[person_id] for person_id in counted_person_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    _assert_annotation_inside_canvas(out)
    for person in execution["persons"]:
        attrs = person["attributes"]
        is_target = attrs.get("using_equipment_type") == "swing_set"
        assert (person["person_id"] in set(counted_person_ids)) == is_target


def test_person_using_equipment_fallback_stays_inside_canvas() -> None:
    cases = [
        (
            2078012179606475,
            {"query_id": "person_using_slide_count", "target_count": 2, "equipment_count": 4, "person_count": 13},
        ),
        (
            2475395254715432,
            {"query_id": "person_using_swing_set_count", "target_count": 3, "equipment_count": 5, "person_count": 14},
        ),
    ]
    for seed, params in cases:
        out = create_task("task_illustrations__park_playground__equipment_use_person_count").generate(
            seed,
            params=params,
            max_attempts=100,
        )
        _assert_annotation_inside_canvas(out)


def test_person_using_equipment_countseeded_sampler_covers_answers_and_variants() -> None:
    samples = [
        _sample_person_using_equipment_spec(
            instance_seed=hash64(2026052407, "park-person-using-equipment-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(100)
    ]
    answer_counts = Counter(sample.target_count for sample in samples)
    query_counts = Counter(sample.query_id for sample in samples)

    answer_support = set(range(1, 6))
    query_support = {
        "person_using_slide_count",
        "person_using_swing_set_count",
        "person_using_seesaw_count",
    }
    _assert_hash_balanced_counts(answer_counts, answer_support)
    _assert_hash_balanced_counts(query_counts, query_support)
    for query_id in query_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.query_id == query_id)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers


def test_person_in_park_zone_count_contract() -> None:
    out = create_task("task_illustrations__park_playground__area_person_count").generate(
        hash64(2026052407, "park-zone", 0),
        params={"query_id": "garden_area_person_count", "target_count": 3, "person_count": 9},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_person_ids = execution["counted_person_ids"]
    person_bboxes = trace["render_map"]["person_bboxes_px"]

    assert out.scene_id == "park_playground"
    assert out.query_id == "garden_area_person_count"
    assert trace["query_spec"]["query_id"] == "garden_area_person_count"
    assert trace["query_spec"]["task_id"] == "task_illustrations__park_playground__area_person_count"
    assert trace["query_spec"]["branch_id"] == "park_person_zone"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_person_ids) == 3
    assert execution["target_zone"] == "garden"
    assert sorted(out.annotation_gt.value) == sorted(person_bboxes[person_id] for person_id in counted_person_ids)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    for person in execution["persons"]:
        is_target = person["attributes"]["zone"] == "garden"
        assert (person["person_id"] in set(counted_person_ids)) == is_target


def test_person_in_park_zone_fallback_stays_inside_zone() -> None:
    out = create_task("task_illustrations__park_playground__area_person_count").generate(
        1263967333006255,
        params={"query_id": "garden_area_person_count", "target_count": 6, "person_count": 9},
        max_attempts=100,
    )
    trace = out.trace_payload
    garden_bbox = trace["render_spec"]["style"]["layout"]["garden_bbox"]
    counted_person_ids = trace["render_map"]["counted_person_ids"]
    person_bboxes = trace["render_map"]["person_bboxes_px"]

    _assert_annotation_inside_canvas(out)
    for person_id in counted_person_ids:
        x0, _y0, x1, y1 = person_bboxes[person_id]
        foot_x = 0.5 * (x0 + x1)
        assert garden_bbox[0] <= foot_x <= garden_bbox[2]
        assert garden_bbox[1] <= y1 <= garden_bbox[3]


def test_person_in_park_zone_countseeded_sampler_covers_answers_and_variants() -> None:
    samples = [
        _sample_person_zone_spec(
            instance_seed=hash64(2026052407, "park-zone-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(100)
    ]
    answer_counts = Counter(sample.target_count for sample in samples)
    query_counts = Counter(sample.query_id for sample in samples)

    answer_support = set(range(1, 7))
    query_support = {
        "playground_area_person_count",
        "garden_area_person_count",
    }
    _assert_hash_balanced_counts(answer_counts, answer_support)
    _assert_hash_balanced_counts(query_counts, query_support)
    for query_id in query_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.query_id == query_id)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers
