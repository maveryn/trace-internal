"""Contract smoke tests for sunburst hierarchy chart tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


SUNBURST_TASKS = {
    "task_charts__sunburst__parent_total_value": {
        "parent_total_from_leaves_value",
    },
    "task_charts__sunburst__parent_total_extremum_label": {
        "highest_parent_total_label",
        "lowest_parent_total_label",
    },
    "task_charts__sunburst__conditional_leaf_count": {
        "leaf_threshold_count_under_parent",
        "leaf_range_count_under_parent",
    },
}


def test_sunburst_tasks_registered() -> None:
    assert set(SUNBURST_TASKS).issubset(set(TASK_REGISTRY))


def test_sunburst_tasks_generate_default_query_outputs() -> None:
    for seed_index, (task_id, allowed_query_ids) in enumerate(sorted(SUNBURST_TASKS.items())):
        task = TASK_REGISTRY[task_id]()
        output = task.generate(
            103_000 + seed_index,
            params={},
            max_attempts=120,
        )
        assert output.query_variant == "default"
        assert output.scene_id == "sunburst"
        assert output.query_id in allowed_query_ids
        assert output.trace_payload["query_spec"]["params"]["query_id"] == output.query_id
        assert output.answer_gt.type in {"integer", "string"}
        assert output.evidence_gt.type == "bbox_set"
        assert output.evidence_gt.value
        assert output.trace_payload["render_spec"]["not_to_scale"] is True
        assert output.trace_payload["render_map"]["node_traces"]


def test_sunburst_tasks_generate_each_query_branch() -> None:
    seed_index = 0
    for task_id, allowed_query_ids in sorted(SUNBURST_TASKS.items()):
        task = TASK_REGISTRY[task_id]()
        for query_id in sorted(allowed_query_ids):
            output = task.generate(
                104_000 + seed_index,
                params={"query_variant": query_id},
                max_attempts=160,
            )
            assert output.query_variant == "default"
            assert output.scene_id == "sunburst"
            assert output.query_id == query_id
            assert output.trace_payload["query_spec"]["params"]["query_id"] == query_id
            assert output.evidence_gt.value
            seed_index += 1
