"""Contract smoke tests for 3D bar-grid chart tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


THREE_D_BAR_TASKS = {
    "task_charts__bar_3d__axis_total_value": {
        "series_total_value",
        "category_total_value",
        "series_interval_total_value",
    },
    "task_charts__bar_3d__axis_gap_value": {
        "series_total_gap_value",
        "category_total_gap_value",
        "category_extremum_gap_value",
    },
    "task_charts__bar_3d__condition_count": {
        "series_threshold_count",
        "category_threshold_count",
        "series_comparison_count",
    },
}


def test_three_d_bar_tasks_registered() -> None:
    assert set(THREE_D_BAR_TASKS).issubset(set(TASK_REGISTRY))


def test_three_d_bar_tasks_generate_default_query_outputs() -> None:
    for seed_index, (task_id, allowed_query_ids) in enumerate(sorted(THREE_D_BAR_TASKS.items())):
        task = TASK_REGISTRY[task_id]()
        output = task.generate(
            91_000 + seed_index,
            params={},
            max_attempts=100,
        )
        assert output.query_variant == "default"
        assert output.scene_id == "bar_3d"
        assert output.query_id in allowed_query_ids
        assert output.trace_payload["query_spec"]["params"]["query_id"] == output.query_id
        assert output.answer_gt.type == "integer"
        assert output.evidence_gt.type == "point_set"
        assert output.evidence_gt.value
        assert output.trace_payload["render_map"]["bar_traces"]


def test_three_d_bar_tasks_generate_each_query_branch() -> None:
    seed_index = 0
    for task_id, allowed_query_ids in sorted(THREE_D_BAR_TASKS.items()):
        task = TASK_REGISTRY[task_id]()
        for query_id in sorted(allowed_query_ids):
            output = task.generate(
                92_000 + seed_index,
                params={"query_variant": query_id},
                max_attempts=100,
            )
            assert output.query_variant == "default"
            assert output.scene_id == "bar_3d"
            assert output.query_id == query_id
            assert output.trace_payload["query_spec"]["params"]["query_id"] == query_id
            assert output.answer_gt.type == "integer"
            assert output.evidence_gt.value
            seed_index += 1


def test_three_d_bar_axis_total_uses_calibrated_grid_size() -> None:
    task = TASK_REGISTRY["task_charts__bar_3d__axis_total_value"]()
    output = task.generate(
        92_500,
        params={"query_variant": "series_interval_total_value"},
        max_attempts=100,
    )
    execution = output.trace_payload["execution_trace"]
    assert int(execution["category_count"]) == 4
    assert int(execution["series_count"]) == 4
    assert list(execution["category_count_range"]) == [4, 4]
    assert list(execution["series_count_range"]) == [4, 4]
    assert list(execution["interval_category_count_range"]) == [3, 4]
    assert 3 <= int(execution["interval_category_count"]) <= 4
