"""Behavior tests for diagrams flow tasks."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from trace.core.seed import hash64
from trace.tasks.diagrams.flow.next_step_label import DiagramsFlowNextStepLabelTask
from tests.helpers import extract_prompt_json_example


def _horizontal_gap(left: Sequence[float], right: Sequence[float]) -> float:
    """Return the horizontal gap between two disjoint bboxes."""

    if float(left[2]) <= float(right[0]):
        return float(right[0] - left[2])
    if float(right[2]) <= float(left[0]):
        return float(left[0] - right[2])
    return 0.0


def test_diagrams_flow_next_step_label_contract_matches_answer_node_bbox() -> None:
    task = DiagramsFlowNextStepLabelTask()
    task_variants = ("direct_next_step", "branch_next_step")
    scene_variants = ("flowchart", "swimlane")

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 50100 + (variant_index * 20) + scene_index
            out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert out.answer_gt.type == "string"
            assert out.evidence_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(out.task_variant) == str(task_variant)
            assert str(execution["task_variant"]) == str(task_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["question_format"]) == "flow_next_step_label"
            assert str(execution["view_family"]) == "process_flow_diagram"
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert len(evidence_bboxes) == 1
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert str(out.answer_gt.value) == str(execution["answer_node_label"])

            expected_bbox = [
                float(value)
                for value in render_map["node_bboxes_px"][str(execution["answer_node_bbox_id"])]
            ]
            assert evidence_bboxes == [expected_bbox]
            assert [str(item) for item in execution["supporting_node_bbox_ids"]] == [str(execution["answer_node_bbox_id"])]
            assert len(execution["node_specs"]) == int(execution["topology_node_count"])
            assert len(render_map["node_bboxes_px"]) == int(execution["topology_node_count"])

            if str(scene_variant) == "swimlane":
                entity_types = {str(entity["entity_type"]) for entity in trace["scene_ir"]["entities"]}
                assert "diagram_lane" in entity_types
                assert int(execution["lane_count"]) == 3
                assert len(render_map["lane_bboxes_px"]) == 3
            else:
                assert int(execution["lane_count"]) == 0
                assert render_map["lane_bboxes_px"] == {}

            if str(task_variant) == "direct_next_step":
                assert execution["query_branch_label"] is None
                assert 5 <= int(execution["topology_node_count"]) <= 6
            else:
                assert str(execution["query_branch_label"]) in {"Yes", "No"}
                assert int(execution["topology_node_count"]) == 6
                assert "Following the" in str(execution["question_text"])


def test_diagrams_flow_prompt_examples_match_variant_contract() -> None:
    task = DiagramsFlowNextStepLabelTask()
    expected = {
        "direct_next_step": (
            {"evidence": [[624, 228, 838, 312]], "answer": "Approve Order"},
            {"answer": "Approve Order"},
        ),
        "branch_next_step": (
            {"evidence": [[624, 228, 838, 312]], "answer": "Fix Record"},
            {"answer": "Fix Record"},
        ),
    }

    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=50160):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_diagrams_flow_next_step_label_is_deterministic() -> None:
    task = DiagramsFlowNextStepLabelTask()
    params = {"task_variant": "branch_next_step", "scene_variant": "swimlane"}
    out_a = task.generate(50210, params=params, max_attempts=10)
    out_b = task.generate(50210, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_diagrams_flow_balanced_sampling_defaults_cover_variants() -> None:
    task = DiagramsFlowNextStepLabelTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(16):
        out = task.generate(hash64(50240, "diagrams_flow", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {"direct_next_step", "branch_next_step"}
    assert set(scene_variants.keys()) == {"flowchart", "swimlane"}


def test_diagrams_flow_same_band_nodes_keep_clear_horizontal_gaps() -> None:
    task = DiagramsFlowNextStepLabelTask()
    min_expected_gap_px = 36.0

    for task_variant, scene_variant in (
        ("direct_next_step", "flowchart"),
        ("direct_next_step", "swimlane"),
        ("branch_next_step", "flowchart"),
        ("branch_next_step", "swimlane"),
    ):
        out = task.generate(
            hash64(50310, f"{task_variant}.{scene_variant}"),
            params={"task_variant": task_variant, "scene_variant": scene_variant},
            max_attempts=10,
        )
        node_specs = out.trace_payload["execution_trace"]["node_specs"]
        bbox_map = out.trace_payload["render_map"]["node_bboxes_px"]

        for index, left_spec in enumerate(node_specs):
            left_bbox = [float(value) for value in bbox_map[str(left_spec["node_bbox_id"])]]
            for right_spec in node_specs[index + 1 :]:
                right_bbox = [float(value) for value in bbox_map[str(right_spec["node_bbox_id"])]]
                vertical_overlap = min(float(left_bbox[3]), float(right_bbox[3])) - max(float(left_bbox[1]), float(right_bbox[1]))
                min_height = min(float(left_bbox[3] - left_bbox[1]), float(right_bbox[3] - right_bbox[1]))
                if float(vertical_overlap) < (0.55 * float(min_height)):
                    continue
                gap_px = _horizontal_gap(left_bbox, right_bbox)
                if float(gap_px) <= 0.0:
                    continue
                assert float(gap_px) >= float(min_expected_gap_px)
