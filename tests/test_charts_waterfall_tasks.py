"""Contract smoke tests for waterfall chart tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


WATERFALL_TASKS = {
    "task_charts__waterfall__running_total_value": {"running_total_after_step"},
    "task_charts__waterfall__threshold_crossing_label": {
        "first_total_at_least_threshold",
        "first_total_at_most_threshold",
    },
    "task_charts__waterfall__counterfactual_final_value": {
        "remove_step_final_total",
        "reverse_step_final_total",
    },
}


def _steps_by_id(output):
    return {
        str(step["step_id"]): dict(step)
        for step in output.trace_payload["execution_trace"]["steps"]
    }


def test_waterfall_tasks_registered() -> None:
    assert set(WATERFALL_TASKS).issubset(set(TASK_REGISTRY))


def test_waterfall_tasks_generate_default_query_outputs() -> None:
    for seed_index, (task_id, allowed_query_ids) in enumerate(sorted(WATERFALL_TASKS.items())):
        task = TASK_REGISTRY[task_id]()
        output = task.generate(
            103_000 + seed_index,
            params={},
            max_attempts=100,
        )
        assert output.query_id == "default"
        assert output.scene_id == "waterfall"
        assert output.query_id in allowed_query_ids
        assert output.trace_payload["query_spec"]["params"]["query_id"] == output.query_id
        assert output.evidence_gt.type == "bbox_set"
        assert output.evidence_gt.value
        assert output.trace_payload["render_map"]["bar_bboxes_px"]


def test_waterfall_tasks_generate_each_query_branch_and_answer_contract() -> None:
    seed_index = 0
    for task_id, allowed_query_ids in sorted(WATERFALL_TASKS.items()):
        task = TASK_REGISTRY[task_id]()
        for query_id in sorted(allowed_query_ids):
            output = task.generate(
                104_000 + seed_index,
                params={"query_id": query_id},
                max_attempts=100,
            )
            assert output.query_id == "default"
            assert output.scene_id == "waterfall"
            assert output.query_id == query_id
            execution = output.trace_payload["execution_trace"]
            steps = _steps_by_id(output)

            if query_id == "running_total_after_step":
                target = steps[str(execution["target_step_id"])]
                assert output.answer_gt.type == "integer"
                assert output.answer_gt.value == int(target["running_after"])
            elif query_id == "first_total_at_least_threshold":
                threshold = int(execution["threshold_value"])
                answer_step = steps[str(execution["answer_step_id"])]
                previous = [
                    int(step["running_after"])
                    for step in execution["steps"][: int(execution["answer_step_index"])]
                ]
                previous.append(int(execution["start_value"]))
                assert output.answer_gt.type == "string"
                assert output.answer_gt.value == str(answer_step["label"])
                assert int(answer_step["running_after"]) >= threshold
                assert all(value < threshold for value in previous)
            elif query_id == "first_total_at_most_threshold":
                threshold = int(execution["threshold_value"])
                answer_step = steps[str(execution["answer_step_id"])]
                previous = [
                    int(step["running_after"])
                    for step in execution["steps"][: int(execution["answer_step_index"])]
                ]
                previous.append(int(execution["start_value"]))
                assert output.answer_gt.type == "string"
                assert output.answer_gt.value == str(answer_step["label"])
                assert int(answer_step["running_after"]) <= threshold
                assert all(value > threshold for value in previous)
            elif query_id == "remove_step_final_total":
                target = steps[str(execution["target_step_id"])]
                assert output.answer_gt.type == "integer"
                assert output.answer_gt.value == int(execution["final_value"]) - int(target["delta"])
            elif query_id == "reverse_step_final_total":
                target = steps[str(execution["target_step_id"])]
                assert output.answer_gt.type == "integer"
                assert output.answer_gt.value == int(execution["final_value"]) - (2 * int(target["delta"]))

            seed_index += 1


def test_waterfall_running_total_uses_late_nonfinal_targets() -> None:
    task = TASK_REGISTRY["task_charts__waterfall__running_total_value"]()
    observed_step_counts = set()
    observed_target_indices = set()

    for offset in range(12):
        output = task.generate(
            2026052300 + offset,
            params={},
            max_attempts=100,
        )
        execution = output.trace_payload["execution_trace"]
        step_count = int(execution["step_count"])
        target_index = int(execution["target_step_index"])
        observed_step_counts.add(step_count)
        observed_target_indices.add(target_index)
        assert 8 <= step_count <= 10
        assert 4 <= target_index <= step_count - 2

    assert observed_step_counts
    assert observed_target_indices
