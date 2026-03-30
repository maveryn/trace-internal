"""Behavior tests for documents layout tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.documents.layout.section_membership_label import (
    DocumentsLayoutSectionMembershipLabelTask,
)
from tests.helpers import extract_prompt_json_example


def test_documents_layout_section_membership_label_contract_matches_trace() -> None:
    task = DocumentsLayoutSectionMembershipLabelTask()
    task_variants = (
        "section_of_field_label",
        "section_of_field_value",
        "section_of_label_value_pair",
    )
    scene_variants = ("form_sheet", "invoice_sheet", "receipt_sheet")

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 39100 + (variant_index * 20) + scene_index
            out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render_map = trace["render_map"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert out.answer_gt.type == "string"
            assert out.evidence_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(out.task_variant) == str(task_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["task_variant"]) == str(task_variant)
            assert str(execution["question_format"]) == "document_section_membership_label"
            assert str(execution["view_family"]) == "structured_document"
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert str(out.answer_gt.value) == str(execution["query_section_label"])
            assert len(evidence_bboxes) == 1

            expected_bbox = [
                float(value)
                for value in render_map["section_label_bboxes_px"][str(execution["query_section_label_bbox_id"])]
            ]
            assert evidence_bboxes == [expected_bbox]
            assert str(execution["query_section_id"]) in render_map["section_box_bboxes_px"]
            assert str(execution["query_section_id"]) in render_map["section_label_bboxes_px"]
            assert any(
                str(spec["field_id"]) == str(execution["query_field_id"])
                and str(spec["section_id"]) == str(execution["query_section_id"])
                for spec in execution["field_specs"]
            )
            query_section_field_tops = [
                float(render_map["field_box_bboxes_px"][str(spec["field_id"])][1])
                for spec in execution["field_specs"]
                if str(spec["section_id"]) == str(execution["query_section_id"])
            ]
            section_label_bbox = render_map["section_label_bboxes_px"][str(execution["query_section_id"])]
            assert float(section_label_bbox[3]) <= min(query_section_field_tops)


def test_documents_layout_prompt_examples_match_variant_contract() -> None:
    task = DocumentsLayoutSectionMembershipLabelTask()
    expected = {
        "section_of_field_label": (
            {"evidence": [[132, 182, 260, 214]], "answer": "Billing Summary"},
            {"answer": "Billing Summary"},
        ),
        "section_of_field_value": (
            {"evidence": [[132, 182, 260, 214]], "answer": "Billing Summary"},
            {"answer": "Billing Summary"},
        ),
        "section_of_label_value_pair": (
            {"evidence": [[132, 182, 260, 214]], "answer": "Billing Summary"},
            {"answer": "Billing Summary"},
        ),
    }

    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=39240):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_documents_layout_section_membership_label_is_deterministic() -> None:
    task = DocumentsLayoutSectionMembershipLabelTask()
    params = {"task_variant": "section_of_field_value", "scene_variant": "invoice_sheet"}
    out_a = task.generate(39320, params=params, max_attempts=10)
    out_b = task.generate(39320, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_documents_layout_balanced_sampling_defaults_cover_variants() -> None:
    task = DocumentsLayoutSectionMembershipLabelTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(36):
        out = task.generate(hash64(39380, "documents_layout", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {
        "section_of_field_label",
        "section_of_field_value",
        "section_of_label_value_pair",
    }
    assert set(scene_variants.keys()) == {"form_sheet", "invoice_sheet", "receipt_sheet"}
