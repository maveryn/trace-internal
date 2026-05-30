"""Contracts for arithmetic-constraint logic puzzle tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.logic.arithmetic_constraint import (
    CRYPTARITHM_QUERY_IDS,
    CRYPTARITHM_TASK_ID,
    NUMBER_WALL_QUERY_IDS,
    NUMBER_WALL_TASK_ID,
    OPERATOR_GRID_QUERY_IDS,
    OPERATOR_GRID_TASK_ID,
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    PuzzlesLogicArithmeticConstraintValueTask,
    PuzzlesLogicCryptarithmDigitValueTask,
    PuzzlesLogicNumberWallValueTask,
    PuzzlesLogicOperatorGridValueTask,
)


def test_arithmetic_constraint_task_is_registered() -> None:
    assert TASK_REGISTRY[TASK_ID] is PuzzlesLogicArithmeticConstraintValueTask


def test_arithmetic_constraint_task_emits_public_contract() -> None:
    task = PuzzlesLogicArithmeticConstraintValueTask()
    out = task.generate(2026052301, params={}, max_attempts=80)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id in set(SUPPORTED_QUERY_IDS)
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert sorted(out.prompt_variants) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert trace["render_spec"]["scene_id"] == SCENE_ID
    assert trace["render_spec"]["text_style"]["font"]["font_family"]
    assert trace["render_map"]["evidence_source"] == "item_bboxes_px"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert execution["scene_id"] == SCENE_ID
    assert execution["query_id"] == out.query_id
    assert execution["supporting_item_ids"]
    assert len(out.evidence_gt.value) == len(execution["supporting_item_ids"])
    assert out.image.size == (
        int(trace["render_spec"]["canvas_width"]),
        int(trace["render_spec"]["canvas_height"]),
    )
    for bbox in out.evidence_gt.value:
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_arithmetic_constraint_scene_tasks_use_target_only_evidence() -> None:
    task_specs = (
        (PuzzlesLogicArithmeticConstraintValueTask(), TASK_ID, SUPPORTED_QUERY_IDS),
        (PuzzlesLogicCryptarithmDigitValueTask(), CRYPTARITHM_TASK_ID, CRYPTARITHM_QUERY_IDS),
        (PuzzlesLogicOperatorGridValueTask(), OPERATOR_GRID_TASK_ID, OPERATOR_GRID_QUERY_IDS),
        (PuzzlesLogicNumberWallValueTask(), NUMBER_WALL_TASK_ID, NUMBER_WALL_QUERY_IDS),
    )
    for task, task_id, query_ids in task_specs:
        assert TASK_REGISTRY[str(task_id)] is task.__class__
        for index, query_id in enumerate(query_ids):
            out = task.generate(
                2026052400 + (101 * len(str(task_id))) + index,
                params={"query_id": str(query_id)},
                max_attempts=120,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            item_bboxes = trace["render_map"]["item_bboxes_px"]
            supporting_item_ids = [str(item_id) for item_id in execution["supporting_item_ids"]]

            assert out.query_id == str(query_id)
            assert out.evidence_gt.type == "bbox_set"
            assert len(out.evidence_gt.value) == 1
            assert len(supporting_item_ids) == 1
            assert supporting_item_ids[0] != "diagram_panel"
            assert supporting_item_ids[0] in item_bboxes
            assert out.evidence_gt.value[0] == item_bboxes[supporting_item_ids[0]]
            assert out.evidence_gt.value[0] != item_bboxes["diagram_panel"]


def test_forced_arithmetic_constraint_queries_are_valid() -> None:
    task = PuzzlesLogicArithmeticConstraintValueTask()
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS):
        out = task.generate(
            2026052310 + index,
            params={"query_id": query_id},
            max_attempts=120,
        )
        trace = out.trace_payload["execution_trace"]
        data = trace["constraint_data"]

        assert out.query_id == query_id
        assert int(out.answer_gt.value) == int(trace["answer_value"])
        assert int(out.answer_gt.value) == int(data["answer_value"])

        if query_id == "equal_sum_line_constraint_value":
            side_total = int(data["side_total"])
            nodes = {str(node["node_id"]): int(node["value"]) for node in data["nodes"]}
            for side_index in range(int(data["side_count"])):
                total = (
                    nodes[f"corner_{side_index}"]
                    + nodes[f"side_mid_{side_index}"]
                    + nodes[f"corner_{(side_index + 1) % int(data['side_count'])}"]
                )
                assert total == side_total
        elif query_id == "paired_cluster_sum_relation_value":
            left_total = sum(int(value) for value in data["left_values"])
            right_total = sum(int(value) for value in data["right_values"])
            assert left_total == int(data["left_total"])
            assert right_total == int(data["right_total"])
            assert right_total == (int(data["relation_multiplier"]) * left_total) + int(data["relation_offset"])
        elif query_id == "consecutive_window_sum_value":
            values = [int(value) for value in data["sequence_values"]]
            window_size = int(data["window_size"])
            for start in range(0, len(values) - window_size + 1):
                assert sum(values[start : start + window_size]) == int(data["window_total"])


def test_arithmetic_constraint_task_is_deterministic() -> None:
    task = PuzzlesLogicArithmeticConstraintValueTask()
    params = {
        "query_id": "paired_cluster_sum_relation_value",
        "scene_variant": "constraint_card",
    }
    out_a = task.generate(2026052399, params=params, max_attempts=120)
    out_b = task.generate(2026052399, params=params, max_attempts=120)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
