"""Regression tests for combo chart panel tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import create_task, list_default_task_ids


COMBO_TASK_IDS = (
    "task_charts__combo_mark__cross_mark_difference_value",
    "task_charts__combo_mark__conditioned_line_extremum_label",
    "task_charts__combo_mark__conditioned_primary_extremum_label",
    "task_charts__combo_mark__dual_threshold_condition_count",
    "task_charts__combo_mark__interval_threshold_condition_count",
    "task_charts__combo_mark__absolute_gap_extremum_label",
    "task_charts__combo_mark__directional_gap_extremum_label",
    "task_charts__combo_mark__series_threshold_crossing_label",
)


def test_combo_tasks_are_default_and_taxonomy_aligned() -> None:
    default_task_ids = set(list_default_task_ids())
    for task_id in COMBO_TASK_IDS:
        assert task_id in default_task_ids
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "charts"
        assert taxonomy.scene_id == "combo_mark"
        assert not taxonomy.source_scene_id


def test_combo_tasks_generate_default_public_variant() -> None:
    for offset, task_id in enumerate(COMBO_TASK_IDS):
        output = create_task(task_id).generate(
            2026052200 + offset,
            params={},
            max_attempts=160,
        )
        assert output.scene_id == "combo_mark"
        assert output.query_id
        assert output.answer_gt.value is not None
        assert output.annotation_gt.type == "keyed_point_map"
        assert output.annotation_gt.value
        assert all(
            str(key).endswith((".primary", ".line"))
            and not str(key).startswith(("target_", "candidate_", "matching_", "start_", "end_"))
            for key in output.annotation_gt.value
        )
        assert output.trace_payload["projected_annotation"]["type"] == "keyed_point_map"
        assert output.trace_payload["projected_annotation"]["keyed_point_map"] == output.annotation_gt.value
        assert output.image.size[0] > 0
        assert output.image.size[1] > 0


def test_combo_label_answer_tasks_use_only_answer_mark_annotation() -> None:
    for offset, task_id in enumerate(
        (
            "task_charts__combo_mark__conditioned_line_extremum_label",
            "task_charts__combo_mark__conditioned_primary_extremum_label",
            "task_charts__combo_mark__absolute_gap_extremum_label",
            "task_charts__combo_mark__directional_gap_extremum_label",
        )
    ):
        output = create_task(task_id).generate(
            2026052810 + offset,
            params={},
            max_attempts=200,
        )
        assert output.answer_gt.type == "string"
        assert output.annotation_gt.type == "keyed_point_map"
        assert len(output.annotation_gt.value) == 2
        assert set(str(key).split(".", 1)[0] for key in output.annotation_gt.value) == {str(output.answer_gt.value)}
        assert {str(key).split(".", 1)[1] for key in output.annotation_gt.value} == {"primary", "line"}


def test_combo_cross_mark_difference_uses_calibrated_signed_queries() -> None:
    supported_queries = set()
    supported_scenes = set()
    label_counts = set()
    for offset in range(16):
        output = create_task("task_charts__combo_mark__cross_mark_difference_value").generate(
            2026052300 + offset,
            params={},
            max_attempts=160,
        )
        supported_queries.add(str(output.query_id))
        execution_trace = output.trace_payload["execution_trace"]
        supported_scenes.add(str(execution_trace["scene_variant"]))
        label_counts.add(int(execution_trace["label_count"]))

    assert supported_queries <= {
        "primary_minus_line_at_label",
        "line_minus_primary_at_label",
    }
    assert supported_scenes <= {
        "bar_line_shared_axis",
        "stacked_bar_line",
    }
    assert min(label_counts) >= 9
    assert max(label_counts) <= 12


def test_combo_series_threshold_crossing_label_matches_contract() -> None:
    task_id = "task_charts__combo_mark__series_threshold_crossing_label"
    query_ids = (
        "primary_first_above_threshold_label",
        "primary_first_below_threshold_label",
        "line_first_above_threshold_label",
        "line_first_below_threshold_label",
    )
    for offset, query_id in enumerate(query_ids):
        output = create_task(task_id).generate(
            2026060400 + offset,
            params={"query_id": query_id},
            max_attempts=160,
        )
        execution_trace = output.trace_payload["execution_trace"]
        labels = [str(label) for label in execution_trace["labels"]]
        target_role = str(execution_trace["target_series_role"])
        target_values = [
            int(value)
            for value in (
                execution_trace["primary_values"]
                if target_role == "primary"
                else execution_trace["line_values"]
            )
        ]
        threshold = int(execution_trace["threshold_value"])
        answer_index = int(execution_trace["answer_index"])
        answer_label = str(labels[int(answer_index)])
        above = str(execution_trace["crossing_direction"]) == "above"

        assert output.answer_gt.type == "string"
        assert str(output.answer_gt.value) == answer_label
        assert output.annotation_gt.type == "keyed_point_map"
        assert 2 <= int(execution_trace["crossing_index"]) <= min(8, len(labels) - 2)
        assert str(execution_trace["query_id"]) == str(query_id)
        assert f'"{execution_trace["target_series_name"]}"' in str(output.prompt)
        assert str(threshold) in str(output.prompt)

        for index, value in enumerate(target_values):
            satisfies = int(value) > int(threshold) if above else int(value) < int(threshold)
            if int(index) < int(answer_index):
                assert not satisfies
            if int(index) == int(answer_index):
                assert satisfies

        expected_keys = {
            f"{labels[index]}.{target_role}"
            for index in range(0, int(answer_index) + 1)
        }
        assert set(output.annotation_gt.value) == expected_keys
        assert all(str(key).endswith(f".{target_role}") for key in output.annotation_gt.value)
