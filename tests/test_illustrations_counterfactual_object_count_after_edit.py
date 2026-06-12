"""Contract tests for illustration object-count after hypothetical edit."""
from __future__ import annotations
from collections import Counter
from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.illustrations.counting import park_person_count as _park_person_count_tasks
from trace.tasks.illustrations.counting import worker_safety_gear_count as _worker_safety_gear_count_tasks
from trace.tasks.illustrations.source_scene_edit.object_count_after_edit import ADDED_VARIANT, REMOVED_VARIANT, SUPPORTED_QUERY_IDS, TASK_ID

def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.7) + 1

def test_illustrations_counterfactual_object_count_after_edit_is_registered() -> None:
    task = TASK_REGISTRY[TASK_ID]()
    assert task.domain == 'illustrations'
    assert not hasattr(task, 'scene_id')
    assert task.default_dataset_enabled is True

def test_illustrations_counterfactual_object_count_after_edit_contracts_match_trace() -> None:
    cases = [(ADDED_VARIANT, 5, 2, 7), (REMOVED_VARIANT, 5, 2, 3)]
    task = create_task(TASK_ID)

def test_illustrations_counterfactual_object_count_after_edit_sampling_distribution() -> None:
    task = create_task(TASK_ID)
    variants = Counter()
    answers_by_variant: dict[str, Counter[int]] = {variant: Counter() for variant in SUPPORTED_QUERY_IDS}
    for index in range(100):
        out = task.generate(2026052900 + index, params={}, max_attempts=120)
        variants[str(out.query_id)] += 1
        answers_by_variant[str(out.query_id)][int(out.answer_gt.value)] += 1
        assert len(out.annotation_gt.value) == int(out.trace_payload['execution_trace']['current_count'])
    _assert_hash_balanced_counts(variants, SUPPORTED_QUERY_IDS)
    assert len(answers_by_variant[ADDED_VARIANT]) >= 5
    assert len(answers_by_variant[REMOVED_VARIANT]) >= 5
    assert max(answers_by_variant[ADDED_VARIANT].values()) <= 13
    assert max(answers_by_variant[REMOVED_VARIANT].values()) <= 13
