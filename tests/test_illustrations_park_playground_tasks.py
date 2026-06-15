"""Contract tests for illustration park/playground tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.park_playground.activity_person_count import _sample_spec as _sample_person_activity_spec
from trace.tasks.illustrations.park_playground.area_person_count import _sample_spec as _sample_person_zone_spec
from trace.tasks.illustrations.park_playground.equipment_use_person_count import (
    _sample_spec as _sample_person_using_equipment_spec,
)
from trace.tasks.illustrations.park_playground.jigsaw_arrangement_label import (
    _sample_spec as _sample_jigsaw_arrangement_spec,
)
from trace.tasks.illustrations.park_playground.playground_equipment_count import (
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
        params={"target_activity": "playing_ball", "target_count": 3, "person_count": 9},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_person_ids = execution["counted_person_ids"]
    person_bboxes = trace["render_map"]["person_bboxes_px"]

    assert out.scene_id == "park_playground"
    assert out.query_id == SINGLE_QUERY_ID
    assert trace["query_spec"]["query_id"] == SINGLE_QUERY_ID
    assert trace["query_spec"]["task_id"] == "task_illustrations__park_playground__activity_person_count"
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
    query_counts = Counter(sample.branch_id for sample in samples)
    activity_counts = Counter(sample.target_activity for sample in samples)

    answer_support = set(range(1, 7))
    activity_support = {"sitting", "walking", "standing", "playing_ball"}
    _assert_hash_balanced_counts(answer_counts, answer_support)
    assert query_counts == Counter({SINGLE_QUERY_ID: 100})
    _assert_hash_balanced_counts(activity_counts, activity_support)
    for activity in activity_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.target_activity == activity)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers


def test_playground_equipment_count_contract() -> None:
    out = create_task("task_illustrations__park_playground__playground_equipment_count").generate(
        hash64(2026052407, "park-equipment", 0),
        params={"target_equipment_type": "slide", "target_count": 3, "equipment_count": 6, "person_count": 6},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_equipment_ids = execution["counted_equipment_ids"]
    decor_bboxes = trace["render_map"]["decor_bboxes_px"]

    assert out.scene_id == "park_playground"
    assert out.query_id == SINGLE_QUERY_ID
    assert trace["query_spec"]["query_id"] == SINGLE_QUERY_ID
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
    query_counts = Counter(sample.branch_id for sample in samples)
    equipment_type_counts = Counter(sample.target_equipment_type for sample in samples)

    answer_support = set(range(1, 6))
    _assert_hash_balanced_counts(answer_counts, answer_support)
    assert query_counts == Counter({SINGLE_QUERY_ID: 100})
    _assert_hash_balanced_counts(equipment_type_counts, {"slide", "swing_set", "seesaw", "climbing_frame"})
    for equipment_type in equipment_type_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.target_equipment_type == equipment_type)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers


def test_person_using_equipment_count_contract() -> None:
    out = create_task("task_illustrations__park_playground__equipment_use_person_count").generate(
        hash64(2026052407, "park-person-using-equipment", 0),
        params={
            "target_equipment_type": "swing_set",
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
    assert out.query_id == SINGLE_QUERY_ID
    assert trace["query_spec"]["query_id"] == SINGLE_QUERY_ID
    assert trace["query_spec"]["task_id"] == "task_illustrations__park_playground__equipment_use_person_count"
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
            {"target_equipment_type": "slide", "target_count": 2, "equipment_count": 4, "person_count": 13},
        ),
        (
            2475395254715432,
            {"target_equipment_type": "swing_set", "target_count": 3, "equipment_count": 5, "person_count": 14},
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
    query_counts = Counter(sample.branch_id for sample in samples)
    equipment_type_counts = Counter(sample.target_equipment_type for sample in samples)

    answer_support = set(range(1, 6))
    _assert_hash_balanced_counts(answer_counts, answer_support)
    assert query_counts == Counter({SINGLE_QUERY_ID: 100})
    _assert_hash_balanced_counts(equipment_type_counts, {"slide", "swing_set", "seesaw"})
    for equipment_type in equipment_type_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.target_equipment_type == equipment_type)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers


def test_person_in_park_zone_count_contract() -> None:
    out = create_task("task_illustrations__park_playground__area_person_count").generate(
        hash64(2026052407, "park-zone", 0),
        params={"target_zone": "garden", "target_count": 3, "person_count": 9},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_person_ids = execution["counted_person_ids"]
    person_bboxes = trace["render_map"]["person_bboxes_px"]

    assert out.scene_id == "park_playground"
    assert out.query_id == SINGLE_QUERY_ID
    assert trace["query_spec"]["query_id"] == SINGLE_QUERY_ID
    assert trace["query_spec"]["task_id"] == "task_illustrations__park_playground__area_person_count"
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
        params={"target_zone": "garden", "target_count": 6, "person_count": 9},
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
    query_counts = Counter(sample.branch_id for sample in samples)
    zone_counts = Counter(sample.target_zone for sample in samples)

    answer_support = set(range(1, 7))
    _assert_hash_balanced_counts(answer_counts, answer_support)
    assert query_counts == Counter({SINGLE_QUERY_ID: 100})
    _assert_hash_balanced_counts(zone_counts, {"playground", "garden"})
    for zone in zone_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.target_zone == zone)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers


def test_jigsaw_arrangement_label_contract() -> None:
    out = create_task("task_illustrations__park_playground__jigsaw_arrangement_label").generate(
        hash64(2026061502, "park-jigsaw-arrangement", 0),
        params={"correct_index": 2, "person_count": 9, "equipment_count": 5},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    answer_label = str(out.answer_gt.value)
    option_bboxes = trace["render_map"]["option_bboxes_px_by_label"]
    option_permutations = trace["render_map"]["option_permutations_by_label"]

    assert out.scene_id == "park_playground"
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "bbox_set"
    assert answer_label == "C"
    assert sorted(option_bboxes) == ["A", "B", "C", "D"]
    assert out.annotation_gt.value == [option_bboxes[answer_label]]
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_bbox_set"] == out.annotation_gt.value
    assert trace["render_map"]["selected_option_bbox_px"] == option_bboxes[answer_label]
    assert execution["option_permutations_by_label"][answer_label] == [0, 1, 2, 3]
    assert option_permutations[answer_label] == [0, 1, 2, 3]
    assert sum(perm == [0, 1, 2, 3] for perm in option_permutations.values()) == 1
    assert trace["query_spec"]["params"]["grid_shape"] == [2, 2]
    assert trace["render_map"]["option_layout_shape"] == [2, 2]
    assert min(trace["query_spec"]["params"]["tile_detail_scores"]) >= 600
    assert trace["render_spec"]["canvas_size"] == [1136, 892]
    _assert_annotation_inside_canvas(out)


def test_jigsaw_arrangement_seeded_sampler_covers_answer_labels() -> None:
    samples = [
        _sample_jigsaw_arrangement_spec(
            instance_seed=hash64(2026061502, "park-jigsaw-arrangement-sampling", index),
            params={"_sample_cursor": index},
            attempt_index=0,
        )
        for index in range(100)
    ]
    answer_counts = Counter(sample.correct_index for sample in samples)
    person_counts = Counter(sample.person_count for sample in samples)
    equipment_counts = Counter(sample.equipment_count for sample in samples)

    assert answer_counts == Counter({0: 25, 1: 25, 2: 25, 3: 25})
    assert set(person_counts) <= set(range(8, 14))
    assert set(equipment_counts) <= set(range(4, 8))
    assert person_counts
    assert equipment_counts
