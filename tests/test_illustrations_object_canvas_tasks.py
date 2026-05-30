"""Contract tests for illustration mixed-object tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.counting.type_count import _sample_spec as _sample_type_count_spec
from trace.tasks.illustrations.counting.visible_part_count import _resolve_sample_spec as _sample_visible_part_spec


def test_type_count_contract() -> None:
    out = create_task("task_illustrations__object_field__object_type_count").generate(
        hash64(2026052301, "type-count", 0),
        params={"object_type": "duck", "target_count": 3, "object_count": 12},
        max_attempts=300,
    )
    trace = out.trace_payload
    counted_ids = trace["execution_trace"]["counted_object_ids"]
    object_bboxes = trace["render_map"]["object_bboxes_px"]
    assert out.scene_id == "object_field"
    assert out.query_id == "type_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_ids) == 3
    assert sorted(out.evidence_gt.value) == sorted(object_bboxes[object_id] for object_id in counted_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value


def test_type_countseeded_sampler_balances_answer_counts_before_object_type_cycle() -> None:
    answers = [
        _sample_type_count_spec(
            instance_seed=hash64(2026052301, "type-count-sampling", index),
            params={},
            attempt_index=0,
        ).target_count
        for index in range(100)
    ]
    counts = Counter(answers)
    assert sorted(counts) == list(range(1, 11))
    assert min(counts.values()) >= 4
    assert max(counts.values()) <= 25


def test_visible_part_countseeded_sampler_balances_small_answer_counts() -> None:
    samples = [
        _sample_visible_part_spec(
            instance_seed=hash64(2026052301, "visible-part-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(120)
    ]
    answer_counts = Counter(sample.target_count for sample in samples)
    part_counts = Counter(sample.part_kind for sample in samples)
    object_counts = Counter(sample.object_count for sample in samples)
    assert sorted(answer_counts) == [1, 2, 3, 4, 5, 6]
    assert min(answer_counts.values()) >= 10
    assert max(answer_counts.values()) <= 35
    assert sorted(part_counts) == ["door", "eye", "handle", "tail", "wing"]
    assert min(part_counts.values()) >= 10
    assert max(part_counts.values()) <= 40
    assert sorted(object_counts) == [6, 7, 8, 9]
    assert min(object_counts.values()) >= 15
    assert max(object_counts.values()) <= 45


def test_visible_part_count_contract_records_final_placement_layout() -> None:
    out = create_task("task_illustrations__object_field__visible_part_count").generate(
        hash64(2026052301, "visible-part-count", 0),
        params={"part_kind": "wing", "target_count": 3, "object_count": 7},
        max_attempts=300,
    )
    trace = out.trace_payload
    counted_ids = trace["execution_trace"]["counted_part_ids"]
    part_bboxes = trace["render_map"]["part_bboxes_px"]
    background_layout = trace["render_spec"]["style"]["background_layout"]

    assert out.scene_id == "object_field"
    assert out.query_id == "visible_part_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_ids) == 3
    assert sorted(out.evidence_gt.value) == sorted(part_bboxes[part_id] for part_id in counted_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert background_layout["placement_layout_id"] in {"free_scatter", "loose_grid", "two_clusters", "diagonal_band"}


def test_named_object_side_count_contract() -> None:
    out = create_task("task_illustrations__object_field__named_object_side_count").generate(
        hash64(2026052301, "named-side-count", 0),
        params={"reference_type": "bicycle", "relation": "left", "object_count": 10},
        max_attempts=500,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_ids = execution["counted_object_ids"]
    object_bboxes = trace["render_map"]["object_bboxes_px"]
    assert out.scene_id == "object_field"
    assert out.query_id == "named_object_side_count"
    assert execution["reference_type"] == "bicycle"
    assert execution["relation"] == "left"
    assert int(out.answer_gt.value) == len(counted_ids)
    assert trace["render_map"]["reference_object_id"] == execution["reference_object_id"]
    assert sorted(out.evidence_gt.value) == sorted(object_bboxes[object_id] for object_id in counted_ids)
