"""Contract tests for misc Boolean logic-gate notation tasks."""

from __future__ import annotations

from trace.core.prompts import load_prompt_bundle
from trace.core.prompts.schema import REQUIRED_PROMPT_VARIANTS
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import TASK_REGISTRY
from trace.tasks.misc.notation.logic_gate import (
    ASSIGNMENT_OUTPUTS_ONE_QUERY_ID,
    ASSIGNMENT_OUTPUTS_ZERO_QUERY_ID,
    COUNT_QUERY_IDS,
    OUTPUT_ONE_COUNT_QUERY_ID,
    OUTPUT_VALUE_COUNT_TASK_ID,
    OUTPUT_ZERO_COUNT_QUERY_ID,
    SATISFYING_ASSIGNMENT_TASK_ID,
    SCENE_ID,
    MiscLogicGateOutputValueCountTask,
    MiscLogicGateSatisfyingAssignmentLabelTask,
)
from trace.tasks.misc.shared.logic_gate_scene import evaluate_logic_gate


def test_logic_gate_tasks_are_registered_and_taxonomized() -> None:
    assert TASK_REGISTRY[OUTPUT_VALUE_COUNT_TASK_ID] is MiscLogicGateOutputValueCountTask
    assert TASK_REGISTRY[SATISFYING_ASSIGNMENT_TASK_ID] is MiscLogicGateSatisfyingAssignmentLabelTask
    for task_id in (OUTPUT_VALUE_COUNT_TASK_ID, SATISFYING_ASSIGNMENT_TASK_ID):
        task = TASK_REGISTRY[task_id]()
        taxonomy = resolve_task_taxonomy(task_id)
        assert task.domain == "misc"
        assert task.task_group == "notation"
        assert taxonomy.domain == "misc"
        assert taxonomy.scene_id == SCENE_ID
        assert taxonomy.source_task_group == "notation"


def test_logic_gate_truth_tables() -> None:
    assert evaluate_logic_gate("AND", [1, 1]) == 1
    assert evaluate_logic_gate("AND", [1, 0]) == 0
    assert evaluate_logic_gate("OR", [0, 1]) == 1
    assert evaluate_logic_gate("OR", [0, 0]) == 0
    assert evaluate_logic_gate("NOT", [0]) == 1
    assert evaluate_logic_gate("NOT", [1]) == 0
    assert evaluate_logic_gate("XOR", [1, 0]) == 1
    assert evaluate_logic_gate("XOR", [1, 1]) == 0
    assert evaluate_logic_gate("NAND", [1, 1]) == 0
    assert evaluate_logic_gate("NAND", [1, 0]) == 1
    assert evaluate_logic_gate("NOR", [0, 0]) == 1
    assert evaluate_logic_gate("NOR", [0, 1]) == 0


def test_logic_gate_output_one_count_contract() -> None:
    out = MiscLogicGateOutputValueCountTask().generate(
        2026060701,
        params={"query_id": OUTPUT_ONE_COUNT_QUERY_ID, "answer_value": 3, "scene_variant": "clean_worksheet"},
        max_attempts=12,
    )
    trace = out.trace_payload
    circuits = trace["execution_trace"]["circuits"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == OUTPUT_ONE_COUNT_QUERY_ID
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 3
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == 3
    assert len([circuit for circuit in circuits if circuit["output_value"] == 1]) == 3
    assert trace["render_map"]["annotation_source"] == "output_points_px"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["execution_trace"]["answer_value"] == out.answer_gt.value
    assert set(COUNT_QUERY_IDS) == {OUTPUT_ONE_COUNT_QUERY_ID, OUTPUT_ZERO_COUNT_QUERY_ID}

    width, height = out.image.size
    for point in out.annotation_gt.value:
        assert len(point) == 2
        assert 0 <= float(point[0]) <= width
        assert 0 <= float(point[1]) <= height


def test_logic_gate_output_zero_count_allows_zero_annotation() -> None:
    out = MiscLogicGateOutputValueCountTask().generate(
        2026060702,
        params={"query_id": OUTPUT_ZERO_COUNT_QUERY_ID, "answer_value": 0, "scene_variant": "exam_scan"},
        max_attempts=12,
    )
    trace = out.trace_payload

    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 0
    assert out.annotation_gt.type == "point_set"
    assert out.annotation_gt.value == []
    assert len([circuit for circuit in trace["execution_trace"]["circuits"] if circuit["output_value"] == 0]) == 0
    assert trace["projected_annotation"]["point_set"] == []


def test_logic_gate_satisfying_assignment_contract() -> None:
    out = MiscLogicGateSatisfyingAssignmentLabelTask().generate(
        2026060703,
        params={
            "query_id": ASSIGNMENT_OUTPUTS_ZERO_QUERY_ID,
            "answer_label": "D",
            "correct_values": {"x": 1, "y": 0, "z": 1},
            "scene_variant": "notebook_problem",
        },
        max_attempts=12,
    )
    trace = out.trace_payload
    candidates = trace["execution_trace"]["candidates"]
    correct_candidates = [candidate for candidate in candidates if candidate["output_value"] == 0]

    assert out.scene_id == SCENE_ID
    assert out.query_id == ASSIGNMENT_OUTPUTS_ZERO_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert sorted(out.annotation_gt.value.keys()) == ["selected_option", "source_circuit"]
    assert len(candidates) == 6
    assert [candidate["label"] for candidate in candidates] == ["A", "B", "C", "D", "E", "F"]
    assert len(correct_candidates) == 1
    assert correct_candidates[0]["label"] == "D"
    assert correct_candidates[0]["values"] == {"x": 1, "y": 0, "z": 1}
    assert trace["render_map"]["annotation_source"] == "item_bboxes_px"
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert trace["execution_trace"]["answer_value"] == out.answer_gt.value

    width, height = out.image.size
    for bbox in out.annotation_gt.value.values():
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= width
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= height


def test_logic_gate_generation_is_deterministic() -> None:
    params = {"query_id": ASSIGNMENT_OUTPUTS_ONE_QUERY_ID, "answer_label": "B", "scene_variant": "exam_scan"}
    out_a = MiscLogicGateSatisfyingAssignmentLabelTask().generate(2026060799, params=params, max_attempts=12)
    out_b = MiscLogicGateSatisfyingAssignmentLabelTask().generate(2026060799, params=params, max_attempts=12)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_misc_notation_prompt_bundle_supports_logic_gate_queries() -> None:
    bundle = load_prompt_bundle("misc", "notation", "misc_v0")
    assert "logic_gate_circuit" in bundle.scene_templates
    assert len(bundle.task_templates["logic_gate_output_value_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["logic_gate_satisfying_assignment_label"]) == REQUIRED_PROMPT_VARIANTS
    for query_id in (
        OUTPUT_ONE_COUNT_QUERY_ID,
        OUTPUT_ZERO_COUNT_QUERY_ID,
        ASSIGNMENT_OUTPUTS_ONE_QUERY_ID,
        ASSIGNMENT_OUTPUTS_ZERO_QUERY_ID,
    ):
        assert len(bundle.query_templates[query_id]) == REQUIRED_PROMPT_VARIANTS
        assert list(bundle.required_slots_by_key[f"query:{query_id}"]) == []
    assert list(bundle.required_slots_by_key["scene:logic_gate_circuit"]) == ["object_description"]
