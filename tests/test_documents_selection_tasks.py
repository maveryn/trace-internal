"""Behavior tests for documents selection tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.documents.selection.checkbox_count import DocumentsSelectionCheckboxCountTask
from tests.helpers import extract_prompt_json_example


def test_documents_selection_checkbox_count_contract_matches_trace() -> None:
    task = DocumentsSelectionCheckboxCountTask()
    task_variants = ("checked_box_count", "unchecked_box_count")
    scene_variants = ("form_sheet", "invoice_sheet", "receipt_sheet")

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 37100 + (variant_index * 20) + scene_index
            out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render_map = trace["render_map"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(out.task_variant) == str(task_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["task_variant"]) == str(task_variant)
            assert str(execution["question_format"]) == "document_checkbox_count"
            assert str(execution["view_family"]) == "structured_document"
            assert str(execution["query_selection_strategy"]) in {
                "balanced_sampling_index_mod_support",
                "combined_hash_mod_support",
            }
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert int(out.answer_gt.value) == int(execution["answer_count"])
            assert int(execution["checkbox_item_count"]) == 4
            assert len(execution["target_checkbox_ids"]) == 4
            assert str(execution["query_section_id"]) in render_map["section_box_bboxes_px"]
            assert str(execution["query_section_id"]) in render_map["section_label_bboxes_px"]

            expected_bboxes = [
                [float(value) for value in render_map["checkbox_bboxes_px"][str(bbox_id)]]
                for bbox_id in execution["evidence_checkbox_bbox_ids"]
            ]
            assert evidence_bboxes == expected_bboxes
            assert len(evidence_bboxes) == int(out.answer_gt.value)

            target_checkbox_bboxes = [
                [float(value) for value in render_map["checkbox_bboxes_px"][f"{str(item_id)}:checkbox"]]
                for item_id in execution["target_checkbox_ids"]
            ]
            section_label_bbox = render_map["section_label_bboxes_px"][str(execution["query_section_id"])]
            assert float(section_label_bbox[3]) <= min(float(bbox[1]) for bbox in target_checkbox_bboxes)

            target_states = dict(execution["target_checkbox_states"])
            if str(task_variant) == "checked_box_count":
                expected_item_ids = [
                    str(item_id)
                    for item_id in execution["target_checkbox_ids"]
                    if bool(target_states[str(item_id)])
                ]
            else:
                expected_item_ids = [
                    str(item_id)
                    for item_id in execution["target_checkbox_ids"]
                    if not bool(target_states[str(item_id)])
                ]
            assert [bbox_id.removesuffix(":checkbox") for bbox_id in execution["evidence_checkbox_bbox_ids"]] == expected_item_ids


def test_documents_selection_prompt_examples_match_variant_contract() -> None:
    task = DocumentsSelectionCheckboxCountTask()
    expected = {
        "checked_box_count": (
            {"evidence": [[154, 252, 178, 276], [154, 304, 178, 328]], "answer": 2},
            {"answer": 2},
        ),
        "unchecked_box_count": (
            {"evidence": [[154, 356, 178, 380]], "answer": 1},
            {"answer": 1},
        ),
    }

    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=37240):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_documents_selection_checkbox_count_is_deterministic() -> None:
    task = DocumentsSelectionCheckboxCountTask()
    params = {"task_variant": "checked_box_count", "scene_variant": "invoice_sheet"}
    out_a = task.generate(37320, params=params, max_attempts=10)
    out_b = task.generate(37320, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_documents_selection_balanced_sampling_defaults_cover_variants() -> None:
    task = DocumentsSelectionCheckboxCountTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(24):
        out = task.generate(hash64(37380, "documents_selection", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {"checked_box_count", "unchecked_box_count"}
    assert set(scene_variants.keys()) == {"form_sheet", "invoice_sheet", "receipt_sheet"}


def test_documents_selection_sampling_index_cycles_full_answer_support() -> None:
    task = DocumentsSelectionCheckboxCountTask()

    for task_variant in ("checked_box_count", "unchecked_box_count"):
        answers = [
            int(
                task.generate(
                    37420 + index,
                    params={"task_variant": task_variant, "_sampling_index": index},
                    max_attempts=10,
                ).answer_gt.value
            )
            for index in range(10)
        ]
        assert set(answers) == {0, 1, 2, 3, 4}


def test_documents_selection_zero_count_uses_empty_evidence() -> None:
    task = DocumentsSelectionCheckboxCountTask()

    found_zero = False
    for seed in range(37400, 37550):
        out = task.generate(seed, params={"task_variant": "checked_box_count"}, max_attempts=10)
        if int(out.answer_gt.value) != 0:
            continue
        found_zero = True
        assert out.evidence_gt.value == []
        assert out.trace_payload["execution_trace"]["evidence_checkbox_bbox_ids"] == []
        assert out.trace_payload["projected_evidence"]["bbox_set"] == []
        break

    assert found_zero, "expected at least one zero-count checked-box instance in sampled seeds"


def test_documents_selection_receipt_sections_do_not_overlap() -> None:
    task = DocumentsSelectionCheckboxCountTask()
    out = task.generate(
        37580,
        params={"scene_variant": "receipt_sheet", "task_variant": "checked_box_count"},
        max_attempts=10,
    )
    render_map = out.trace_payload["render_map"]
    execution = out.trace_payload["execution_trace"]

    section_ids = [
        str(section_spec["section_id"])
        for section_spec in execution["checkbox_section_specs"]
    ]
    first_box = render_map["section_box_bboxes_px"][section_ids[0]]
    second_box = render_map["section_box_bboxes_px"][section_ids[1]]
    assert float(first_box[3]) < float(second_box[1])
