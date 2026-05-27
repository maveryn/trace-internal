"""Contract smoke tests for area chart panel tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


AREA_TASKS = {
    "task_charts__area__interval_area_value": "interval_area_value",
    "task_charts__area__stacked_band_interval_sum_value": "stacked_band_interval_sum_value",
    "task_charts__area__stacked_band_dominance_label": "stacked_dominance_label",
}


def test_area_tasks_registered() -> None:
    assert set(AREA_TASKS).issubset(set(TASK_REGISTRY))


def test_area_tasks_generate_default_query_outputs() -> None:
    for seed_index, (task_id, query_id) in enumerate(sorted(AREA_TASKS.items())):
        task = TASK_REGISTRY[task_id]()
        output = task.generate(
            74_000 + seed_index,
            params={},
            max_attempts=80,
        )
        assert output.query_variant == "default"
        assert output.scene_id == "area"
        assert output.query_id == query_id
        assert output.trace_payload["query_spec"]["params"]["query_id"] == query_id
        assert output.answer_gt.type in {"integer", "string"}
        assert output.evidence_gt.type == "point_set"
        assert output.evidence_gt.value
