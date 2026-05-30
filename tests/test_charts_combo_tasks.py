"""Regression tests for combo chart panel tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import create_task, list_default_task_ids


COMBO_TASK_IDS = (
    "task_charts__combo_mark__cross_mark_difference_value",
    "task_charts__combo_mark__conditioned_extremum_label",
    "task_charts__combo_mark__dual_condition_count",
    "task_charts__combo_mark__interval_change_comparison_value",
    "task_charts__combo_mark__gap_extremum_label",
)


def test_combo_tasks_are_default_and_taxonomy_aligned() -> None:
    default_task_ids = set(list_default_task_ids())
    for task_id in COMBO_TASK_IDS:
        assert task_id in default_task_ids
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "charts"
        assert taxonomy.scene_id == "combo_mark"
        assert taxonomy.source_task_group == "combo"


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
        assert output.evidence_gt.type == "keyed_point_map"
        assert output.evidence_gt.value
        assert all(
            str(key).endswith((".primary", ".line"))
            and not str(key).startswith(("target_", "candidate_", "matching_", "start_", "end_"))
            for key in output.evidence_gt.value
        )
        assert output.trace_payload["projected_evidence"]["type"] == "keyed_point_map"
        assert output.trace_payload["projected_evidence"]["keyed_point_map"] == output.evidence_gt.value
        assert output.image.size[0] > 0
        assert output.image.size[1] > 0


def test_combo_label_answer_tasks_use_only_answer_mark_evidence() -> None:
    for offset, task_id in enumerate(
        (
            "task_charts__combo_mark__conditioned_extremum_label",
            "task_charts__combo_mark__gap_extremum_label",
        )
    ):
        output = create_task(task_id).generate(
            2026052810 + offset,
            params={},
            max_attempts=200,
        )
        assert output.answer_gt.type == "string"
        assert output.evidence_gt.type == "keyed_point_map"
        assert len(output.evidence_gt.value) == 2
        assert set(str(key).split(".", 1)[0] for key in output.evidence_gt.value) == {str(output.answer_gt.value)}
        assert {str(key).split(".", 1)[1] for key in output.evidence_gt.value} == {"primary", "line"}


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
        "grouped_bar_line",
    }
    assert min(label_counts) >= 9
    assert max(label_counts) <= 12
