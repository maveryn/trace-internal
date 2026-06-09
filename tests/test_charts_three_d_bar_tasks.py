"""Contract smoke tests for 3D bar-grid chart tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


THREE_D_BAR_TASKS = {
    "task_charts__bar_3d__series_category_scope_total_value": {"series_total_value", "series_interval_total_value"},
    "task_charts__bar_3d__category_total_value": {"category_total_value"},
    "task_charts__bar_3d__series_total_gap_value": {"series_total_gap_value"},
    "task_charts__bar_3d__category_total_gap_value": {"category_total_gap_value"},
    "task_charts__bar_3d__category_extremum_gap_value": {"category_extremum_gap_value"},
    "task_charts__bar_3d__series_threshold_count": {"series_threshold_count"},
    "task_charts__bar_3d__category_threshold_count": {"category_threshold_count"},
    "task_charts__bar_3d__pairwise_comparison_count": {
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
        assert output.scene_id == "bar_3d"
        assert output.query_id in allowed_query_ids
        assert output.trace_payload["query_spec"]["params"]["query_id"] == output.query_id
        assert output.answer_gt.type == "integer"
        assert output.annotation_gt.type == "point_set"
        assert output.annotation_gt.value
        projected = output.trace_payload["projected_annotation"]
        assert projected["type"] == "point_set"
        assert projected["point_set"] == output.annotation_gt.value
        assert projected["pixel_point_set"] == output.annotation_gt.value
        assert output.trace_payload["render_spec"]["font_assets"]["chart_font_family"]
        assert output.trace_payload["render_map"]["bar_traces"]


def test_three_d_bar_tasks_generate_each_query_branch() -> None:
    seed_index = 0
    for task_id, allowed_query_ids in sorted(THREE_D_BAR_TASKS.items()):
        task = TASK_REGISTRY[task_id]()
        for query_id in sorted(allowed_query_ids):
            output = task.generate(
                92_000 + seed_index,
                params={"query_id": query_id},
                max_attempts=100,
            )
            assert output.scene_id == "bar_3d"
            assert output.query_id == query_id
            assert output.trace_payload["query_spec"]["params"]["query_id"] == query_id
            assert output.answer_gt.type == "integer"
            assert output.annotation_gt.value
            seed_index += 1


def test_three_d_bar_axis_aggregate_uses_calibrated_grid_size() -> None:
    task = TASK_REGISTRY["task_charts__bar_3d__series_category_scope_total_value"]()
    output = task.generate(
        92_500,
        params={"query_id": "series_interval_total_value"},
        max_attempts=100,
    )
    execution = output.trace_payload["execution_trace"]
    assert list(execution["category_count_range"]) == [3, 6]
    assert list(execution["series_count_range"]) == [3, 6]
    assert 3 <= int(execution["category_count"]) <= 6
    assert 3 <= int(execution["series_count"]) <= 6
    assert int(execution["max_bar_count"]) == 24
    assert int(execution["category_count"]) * int(execution["series_count"]) <= 24
    interval_range = list(execution["interval_category_count_range"])
    assert interval_range[0] == 3
    assert 3 <= interval_range[1] <= 4
    assert interval_range[0] <= int(execution["interval_category_count"]) <= interval_range[1]


def test_three_d_bar_condition_tasks_avoid_too_small_or_crowded_grids() -> None:
    for task_id, query_id, expected_category_range, expected_series_range in (
        ("task_charts__bar_3d__series_threshold_count", "series_threshold_count", [6, 6], [3, 4]),
        ("task_charts__bar_3d__category_threshold_count", "category_threshold_count", [3, 4], [6, 6]),
        ("task_charts__bar_3d__pairwise_comparison_count", "series_comparison_count", [4, 6], [4, 6]),
    ):
        output = TASK_REGISTRY[task_id]().generate(
            92_700,
            params={"query_id": query_id},
            max_attempts=100,
        )
        execution = output.trace_payload["execution_trace"]
        assert list(execution["category_count_range"]) == expected_category_range
        assert list(execution["series_count_range"]) == expected_series_range
        assert int(expected_category_range[0]) <= int(execution["category_count"]) <= int(expected_category_range[1])
        assert int(expected_series_range[0]) <= int(execution["series_count"]) <= int(expected_series_range[1])
        assert int(execution["max_bar_count"]) == 24
        assert int(execution["category_count"]) * int(execution["series_count"]) <= 24
        if query_id in {"series_threshold_count", "category_threshold_count", "series_comparison_count"}:
            assert int(execution["target_count"]) == int(output.answer_gt.value)


def test_three_d_bar_sampling_never_exceeds_max_bar_count() -> None:
    for seed in range(93_000, 93_040):
        for task_id, query_ids in THREE_D_BAR_TASKS.items():
            output = TASK_REGISTRY[task_id]().generate(
                seed,
                params={"query_id": sorted(query_ids)[0]},
                max_attempts=100,
            )
            execution = output.trace_payload["execution_trace"]
            assert int(execution["category_count"]) * int(execution["series_count"]) <= 24
