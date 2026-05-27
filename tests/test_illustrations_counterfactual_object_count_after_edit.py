"""Contract tests for illustration object-count after hypothetical edit."""

from __future__ import annotations

from collections import Counter

from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.illustrations.counterfactual.object_count_after_edit import (
    ADDED_VARIANT,
    REMOVED_VARIANT,
    SUPPORTED_QUERY_VARIANTS,
    TASK_ID,
)


def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.7) + 1


def test_illustrations_counterfactual_object_count_after_edit_is_registered() -> None:
    task = TASK_REGISTRY[TASK_ID]()
    assert task.domain == "illustrations"
    assert task.task_group == "counterfactual"
    assert task.default_dataset_enabled is True


def test_illustrations_counterfactual_object_count_after_edit_contracts_match_trace() -> None:
    cases = [(ADDED_VARIANT, 5, 2, 7), (REMOVED_VARIANT, 5, 2, 3)]
    task = create_task(TASK_ID)
    for index, (variant, current_count, edit_count_k, expected_answer) in enumerate(cases):
        out = task.generate(
            2026052800 + index,
            params={
                "query_variant": variant,
                "source_query_key": "mixed_car",
                "current_count": current_count,
                "edit_count_k": edit_count_k,
            },
            max_attempts=120,
        )
        trace = out.trace_payload
        assert out.scene_id == "source_scene_edit"
        assert out.query_variant == "default"
        assert out.query_id == variant
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == int(expected_answer)
        assert out.evidence_gt.type == "bbox_set"
        assert len(out.evidence_gt.value) == int(current_count)
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert trace["execution_trace"]["current_count"] == current_count
        assert trace["execution_trace"]["edit_count_k"] == edit_count_k
        assert trace["execution_trace"]["result_count"] == expected_answer


def test_illustrations_counterfactual_object_count_after_edit_sampling_distribution() -> None:
    task = create_task(TASK_ID)
    variants = Counter()
    answers_by_variant: dict[str, Counter[int]] = {variant: Counter() for variant in SUPPORTED_QUERY_VARIANTS}
    for index in range(100):
        out = task.generate(2026052900 + index, params={}, max_attempts=120)
        variants[str(out.query_id)] += 1
        answers_by_variant[str(out.query_id)][int(out.answer_gt.value)] += 1
        assert len(out.evidence_gt.value) == int(out.trace_payload["execution_trace"]["current_count"])
    _assert_hash_balanced_counts(variants, SUPPORTED_QUERY_VARIANTS)
    assert len(answers_by_variant[ADDED_VARIANT]) >= 5
    assert len(answers_by_variant[REMOVED_VARIANT]) >= 5
    assert max(answers_by_variant[ADDED_VARIANT].values()) <= 13
    assert max(answers_by_variant[REMOVED_VARIANT].values()) <= 13
