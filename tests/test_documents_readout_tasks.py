"""Behavior tests for documents readout tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.documents.readout.field_value import DocumentsReadoutFieldValueTask
from tests.helpers import extract_prompt_json_example


def test_documents_readout_field_value_contract_matches_trace() -> None:
    task = DocumentsReadoutFieldValueTask()
    task_variants = (
        "lookup_identifier",
        "lookup_name",
        "lookup_date",
        "lookup_contact",
        "lookup_amount",
    )
    scene_variants = ("form_sheet", "invoice_sheet", "receipt_sheet")

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 35100 + (variant_index * 20) + scene_index
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
            assert str(execution["question_format"]) == "document_field_lookup"
            assert str(execution["view_family"]) == "structured_document"
            assert len(evidence_bboxes) == 2
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert str(out.answer_gt.value) == str(execution["query_field_value"])
            assert str(execution["query_field_category"]) == str(task_variant)

            expected_bboxes = [
                [float(value) for value in render_map["field_label_bboxes_px"][str(execution["query_label_bbox_id"])]],
                [float(value) for value in render_map["field_value_bboxes_px"][str(execution["query_value_bbox_id"])]],
            ]
            assert evidence_bboxes == expected_bboxes

            field_specs = execution["field_specs"]
            visible_values = [str(spec["field_value"]) for spec in field_specs]
            assert len(field_specs) == int(execution["field_count"])
            assert len(visible_values) == len(set(visible_values))
            assert any(str(spec["field_id"]) == str(execution["query_field_id"]) for spec in field_specs)
            assert len(render_map["field_label_bboxes_px"]) == len(field_specs)
            assert len(render_map["field_value_bboxes_px"]) == len(field_specs)
            assert len(render_map["field_box_bboxes_px"]) == len(field_specs)


def test_documents_readout_prompt_examples_match_variant_contract() -> None:
    task = DocumentsReadoutFieldValueTask()
    expected = {
        "lookup_identifier": (
            {"evidence": [[148, 218, 314, 244], [150, 260, 364, 294]], "answer": "INV-48217"},
            {"answer": "INV-48217"},
        ),
        "lookup_name": (
            {"evidence": [[148, 218, 314, 244], [150, 260, 364, 294]], "answer": "Ava Lee"},
            {"answer": "Ava Lee"},
        ),
        "lookup_date": (
            {"evidence": [[148, 218, 314, 244], [150, 260, 364, 294]], "answer": "2026-03-18"},
            {"answer": "2026-03-18"},
        ),
        "lookup_contact": (
            {"evidence": [[148, 218, 314, 244], [150, 260, 364, 294]], "answer": "ava.lee@example.com"},
            {"answer": "ava.lee@example.com"},
        ),
        "lookup_amount": (
            {"evidence": [[148, 218, 314, 244], [150, 260, 364, 294]], "answer": "$128.40"},
            {"answer": "$128.40"},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=35240):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_documents_readout_field_value_is_deterministic() -> None:
    task = DocumentsReadoutFieldValueTask()
    params = {"task_variant": "lookup_contact", "scene_variant": "invoice_sheet"}
    out_a = task.generate(35320, params=params, max_attempts=10)
    out_b = task.generate(35320, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_documents_readout_balanced_sampling_defaults_cover_variants() -> None:
    task = DocumentsReadoutFieldValueTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(30):
        out = task.generate(hash64(35380, "documents_readout", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {
        "lookup_identifier",
        "lookup_name",
        "lookup_date",
        "lookup_contact",
        "lookup_amount",
    }
    assert set(scene_variants.keys()) == {"form_sheet", "invoice_sheet", "receipt_sheet"}
