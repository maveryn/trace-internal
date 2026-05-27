"""Contract tests for illustration transit-terminal tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.counting._terminal_boarding_area_luggage_branch import (
    _sample_spec as _sample_luggage_spec,
)
from trace.tasks.illustrations.counting._terminal_boarding_area_person_branch import (
    _sample_spec as _sample_boarding_area_spec,
)
from trace.tasks.illustrations.counting._terminal_queue_person_branch import _sample_spec as _sample_queue_spec


def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.7) + 1


def test_person_at_boarding_area_count_contract() -> None:
    out = create_task("task_illustrations__transit_terminal__entity_location_count").generate(
        hash64(2026052407, "transit-boarding-area", 0),
        params={"query_id": "boarding_area_b_person_count", "target_count": 5, "person_count": 18},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_person_ids = execution["counted_person_ids"]
    person_bboxes = trace["render_map"]["person_bboxes_px"]

    assert out.scene_id == "transit_terminal"
    assert out.query_id == "boarding_area_b_person_count"
    assert out.query_variant == "default"
    assert trace["query_spec"]["task_id"] == "task_illustrations__transit_terminal__entity_location_count"
    assert trace["query_spec"]["branch_id"] == "terminal_boarding_area_person"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 5
    assert len(counted_person_ids) == 5
    assert execution["target_area_id"] == "area_b"
    assert sorted(out.evidence_gt.value) == sorted(person_bboxes[person_id] for person_id in counted_person_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    for person in execution["persons"]:
        is_target = person["area_id"] == "area_b"
        assert (person["person_id"] in set(counted_person_ids)) == is_target


def test_person_at_boarding_areaseeded_sampler_covers_answers_and_variants() -> None:
    samples = [
        _sample_boarding_area_spec(
            instance_seed=hash64(2026052407, "transit-boarding-area-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(100)
    ]
    answer_counts = Counter(sample.target_count for sample in samples)
    query_counts = Counter(sample.query_id for sample in samples)

    answer_support = set(range(2, 9))
    query_support = {
        "boarding_area_a_person_count",
        "boarding_area_b_person_count",
        "boarding_area_c_person_count",
        "boarding_area_d_person_count",
    }
    _assert_hash_balanced_counts(answer_counts, answer_support)
    _assert_hash_balanced_counts(query_counts, query_support)
    for query_id in query_counts:
        per_query_answers = Counter(sample.target_count for sample in samples if sample.query_id == query_id)
        assert set(per_query_answers) <= answer_support
        assert per_query_answers


def test_luggage_in_boarding_area_count_contract() -> None:
    out = create_task("task_illustrations__transit_terminal__entity_location_count").generate(
        hash64(2026052407, "transit-luggage-area", 0),
        params={
            "query_id": "backpack_in_boarding_area_count",
            "area_id": "area_c",
            "target_count": 4,
            "luggage_count": 14,
            "person_count": 12,
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_luggage_ids = execution["counted_luggage_ids"]
    luggage_bboxes = trace["render_map"]["luggage_bboxes_px"]

    assert out.scene_id == "transit_terminal"
    assert out.query_id == "backpack_in_boarding_area_count"
    assert out.query_variant == "default"
    assert trace["query_spec"]["task_id"] == "task_illustrations__transit_terminal__entity_location_count"
    assert trace["query_spec"]["branch_id"] == "terminal_boarding_area_luggage"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 4
    assert len(counted_luggage_ids) == 4
    assert execution["target_area_id"] == "area_c"
    assert execution["target_luggage_type"] == "backpack"
    assert sorted(out.evidence_gt.value) == sorted(luggage_bboxes[luggage_id] for luggage_id in counted_luggage_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    for item in execution["luggage"]:
        is_target = item["area_id"] == "area_c" and item["luggage_type"] == "backpack"
        assert (item["luggage_id"] in set(counted_luggage_ids)) == is_target


def test_luggage_in_boarding_areaseeded_sampler_covers_answers_and_variants() -> None:
    samples = [
        _sample_luggage_spec(
            instance_seed=hash64(2026052407, "transit-luggage-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(100)
    ]
    answer_counts = Counter(sample.target_count for sample in samples)
    query_counts = Counter(sample.query_id for sample in samples)
    area_counts = Counter(sample.area_id for sample in samples)

    answer_support = set(range(2, 7))
    query_support = {
        "suitcase_in_boarding_area_count",
        "backpack_in_boarding_area_count",
        "luggage_cart_in_boarding_area_count",
    }
    _assert_hash_balanced_counts(answer_counts, answer_support)
    _assert_hash_balanced_counts(query_counts, query_support)
    _assert_hash_balanced_counts(area_counts, {"area_a", "area_b", "area_c", "area_d"})


def test_queue_person_count_contract() -> None:
    out = create_task("task_illustrations__transit_terminal__entity_location_count").generate(
        hash64(2026052407, "transit-queue", 0),
        params={
            "query_id": "ticket_counter_queue_person_count",
            "target_count": 5,
            "distractor_queue_count": 5,
            "background_person_count": 8,
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_person_ids = execution["counted_person_ids"]
    person_bboxes = trace["render_map"]["person_bboxes_px"]

    assert out.scene_id == "transit_terminal"
    assert out.query_id == "ticket_counter_queue_person_count"
    assert out.query_variant == "default"
    assert trace["query_spec"]["task_id"] == "task_illustrations__transit_terminal__entity_location_count"
    assert trace["query_spec"]["branch_id"] == "terminal_queue_person"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 5
    assert len(counted_person_ids) == 5
    assert execution["target_service_point_id"] == "ticket_counter"
    assert sorted(out.evidence_gt.value) == sorted(person_bboxes[person_id] for person_id in counted_person_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    for person in execution["persons"]:
        attrs = person["attributes"]
        is_target = bool(attrs.get("queue_member")) and attrs.get("service_point_id") == "ticket_counter"
        assert (person["person_id"] in set(counted_person_ids)) == is_target


def test_queue_personseeded_sampler_covers_answers_and_variants() -> None:
    samples = [
        _sample_queue_spec(
            instance_seed=hash64(2026052407, "transit-queue-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(100)
    ]
    answer_counts = Counter(sample.target_count for sample in samples)
    query_counts = Counter(sample.query_id for sample in samples)

    answer_support = set(range(2, 8))
    query_support = {
        "security_queue_person_count",
        "ticket_counter_queue_person_count",
        "gate_queue_person_count",
    }
    _assert_hash_balanced_counts(answer_counts, answer_support)
    _assert_hash_balanced_counts(query_counts, query_support)
