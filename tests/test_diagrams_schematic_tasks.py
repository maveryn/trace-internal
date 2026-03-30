"""Behavior tests for diagrams schematic tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.diagrams.schematic.callout_target_label import DiagramsSchematicCalloutTargetLabelTask
from tests.helpers import extract_prompt_json_example


def test_diagrams_schematic_callout_target_label_contract_matches_target_part_bbox() -> None:
    task = DiagramsSchematicCalloutTargetLabelTask()
    task_variants = ("callout_for_named_part", "callout_for_highlighted_part")

    for variant_index, task_variant in enumerate(task_variants):
        seed = 62100 + variant_index
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": "annotated_schematic"}, max_attempts=10)
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
        assert str(execution["scene_variant"]) == "annotated_schematic"
        assert str(execution["question_format"]) == "schematic_callout_target_label"
        assert str(execution["view_family"]) == "annotated_schematic_diagram"
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert str(out.answer_gt.value) == str(execution["answer_callout_label"])

        expected_bbox = [
            float(value)
            for value in render_map["part_bboxes_px"][str(execution["answer_part_bbox_id"])]
        ]
        assert evidence_bboxes == [expected_bbox]
        assert [str(item) for item in execution["supporting_part_bbox_ids"]] == [str(execution["answer_part_bbox_id"])]
        assert len(execution["part_specs"]) == int(execution["part_count"])
        assert len(render_map["part_bboxes_px"]) == int(execution["part_count"])
        assert len(render_map["callout_bboxes_px"]) == int(execution["part_count"])

        if str(task_variant) == "callout_for_named_part":
            assert execution["query_part_label"] is not None
            assert execution["highlight_part_id"] is None
        else:
            assert execution["query_part_label"] is None
            assert str(execution["highlight_part_id"]) == str(execution["answer_part_id"])


def test_diagrams_schematic_prompt_examples_match_variant_contract() -> None:
    task = DiagramsSchematicCalloutTargetLabelTask()
    expected = {
        "callout_for_named_part": (
            {"evidence": [[406, 334, 595, 445]], "answer": "B"},
            {"answer": "B"},
        ),
        "callout_for_highlighted_part": (
            {"evidence": [[406, 334, 595, 445]], "answer": "F"},
            {"answer": "F"},
        ),
    }

    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=62160):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_diagrams_schematic_callout_target_label_is_deterministic() -> None:
    task = DiagramsSchematicCalloutTargetLabelTask()
    params = {"task_variant": "callout_for_named_part", "scene_variant": "annotated_schematic"}
    out_a = task.generate(62210, params=params, max_attempts=10)
    out_b = task.generate(62210, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_diagrams_schematic_balanced_sampling_defaults_cover_variants() -> None:
    task = DiagramsSchematicCalloutTargetLabelTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(12):
        out = task.generate(hash64(62240, "diagrams_schematic", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {"callout_for_named_part", "callout_for_highlighted_part"}
    assert set(scene_variants.keys()) == {"annotated_schematic"}


def test_diagrams_schematic_part_counts_and_callout_labels_stay_in_range() -> None:
    task = DiagramsSchematicCalloutTargetLabelTask()
    out = task.generate(62280, params={"task_variant": "callout_for_named_part", "scene_variant": "annotated_schematic"}, max_attempts=10)
    execution = out.trace_payload["execution_trace"]
    part_specs = execution["part_specs"]

    assert 5 <= int(execution["part_count"]) <= 7
    callout_labels = [str(spec["callout_label"]) for spec in part_specs]
    assert len(callout_labels) == len(set(callout_labels))
    assert all(label in "ABCDEFG" for label in callout_labels)
    for spec in part_specs:
        label = str(spec["part_label"])
        assert 4 <= len(label) <= 7
        assert " " not in label


def test_diagrams_schematic_named_query_is_harder_than_highlighted_query() -> None:
    task = DiagramsSchematicCalloutTargetLabelTask()
    highlighted = task.generate(62310, params={"task_variant": "callout_for_highlighted_part", "scene_variant": "annotated_schematic"}, max_attempts=10)
    named = task.generate(62310, params={"task_variant": "callout_for_named_part", "scene_variant": "annotated_schematic"}, max_attempts=10)

    assert float(named.complexity.complexity_components["reasoning_load"]) > float(
        highlighted.complexity.complexity_components["reasoning_load"]
    )


def test_diagrams_schematic_parts_and_callouts_do_not_overlap_each_other() -> None:
    task = DiagramsSchematicCalloutTargetLabelTask()
    out = task.generate(62340, params={"task_variant": "callout_for_highlighted_part", "scene_variant": "annotated_schematic"}, max_attempts=10)
    render_map = out.trace_payload["render_map"]
    part_bboxes = [[float(value) for value in bbox] for bbox in render_map["part_bboxes_px"].values()]
    callout_bboxes = [[float(value) for value in bbox] for bbox in render_map["callout_bboxes_px"].values()]

    def _overlaps(left: list[float], right: list[float]) -> bool:
        return not (
            left[2] <= right[0]
            or right[2] <= left[0]
            or left[3] <= right[1]
            or right[3] <= left[1]
        )

    for index, left_bbox in enumerate(part_bboxes):
        for right_bbox in part_bboxes[index + 1 :]:
            assert not _overlaps(left_bbox, right_bbox)
    for index, left_bbox in enumerate(callout_bboxes):
        for right_bbox in callout_bboxes[index + 1 :]:
            assert not _overlaps(left_bbox, right_bbox)
    for part_bbox in part_bboxes:
        for callout_bbox in callout_bboxes:
            assert not _overlaps(part_bbox, callout_bbox)
