"""Contract smoke tests for treemap composition chart tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


TREEMAP_TASKS = {
    "task_charts__treemap__group_total_value": {
        "treemap_group_total_value",
    },
    "task_charts__treemap__repeated_leaf_aggregate_value": {
        "treemap_repeated_leaf_sum_value",
        "treemap_repeated_leaf_average_value",
    },
}


def test_treemap_tasks_registered() -> None:
    assert set(TREEMAP_TASKS).issubset(set(TASK_REGISTRY))


def test_treemap_tasks_generate_default_query_outputs() -> None:
    for seed_index, (task_id, allowed_query_ids) in enumerate(sorted(TREEMAP_TASKS.items())):
        task = TASK_REGISTRY[task_id]()
        output = task.generate(
            203_000 + seed_index,
            params={},
            max_attempts=160,
        )
        assert output.query_id == "default"
        assert output.scene_id == "treemap_part_whole"
        assert output.query_id in allowed_query_ids
        assert output.trace_payload["query_spec"]["params"]["query_id"] == output.query_id
        assert output.answer_gt.type == "integer"
        assert output.evidence_gt.type == "bbox_set"
        assert output.evidence_gt.value
        assert output.trace_payload["render_spec"]["value_source"] == "printed_leaf_values"
        assert output.trace_payload["render_map"]["leaf_traces"]
        assert output.trace_payload["render_map"]["parent_traces"]


def test_treemap_tasks_generate_each_query_branch() -> None:
    seed_index = 0
    for task_id, allowed_query_ids in sorted(TREEMAP_TASKS.items()):
        task = TASK_REGISTRY[task_id]()
        for query_id in sorted(allowed_query_ids):
            output = task.generate(
                204_000 + seed_index,
                params={"query_id": query_id},
                max_attempts=200,
            )
            assert output.query_id == "default"
            assert output.scene_id == "treemap_part_whole"
            assert output.query_id == query_id
            assert output.trace_payload["query_spec"]["params"]["query_id"] == query_id
            assert output.evidence_gt.value
            seed_index += 1
