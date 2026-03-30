"""Behavior tests for documents relation tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.documents.relation.section_extremum_value import DocumentsRelationSectionExtremumValueTask
from tests.helpers import extract_prompt_json_example


def test_documents_relation_section_extremum_value_contract_matches_trace() -> None:
    task = DocumentsRelationSectionExtremumValueTask()
    scenes_by_variant = {
        "earliest_date_in_section": ("form_sheet", "invoice_sheet", "receipt_sheet"),
        "latest_date_in_section": ("form_sheet", "invoice_sheet", "receipt_sheet"),
        "largest_amount_in_section": ("invoice_sheet", "receipt_sheet"),
        "smallest_amount_in_section": ("invoice_sheet", "receipt_sheet"),
    }

    for variant_index, (task_variant, scene_variants) in enumerate(scenes_by_variant.items()):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 36100 + (variant_index * 20) + scene_index
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
            assert str(execution["question_format"]) == "document_section_extremum_value"
            assert str(execution["view_family"]) == "structured_document"
            assert len(evidence_bboxes) == 1
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert str(out.answer_gt.value) == str(execution["winning_field_value"])

            expected_bbox = [
                float(value)
                for value in render_map["field_value_bboxes_px"][str(execution["winning_value_bbox_id"])]
            ]
            assert evidence_bboxes == [expected_bbox]
            assert str(execution["query_section_id"]) in render_map["section_box_bboxes_px"]
            assert str(execution["query_section_id"]) in render_map["section_label_bboxes_px"]
            assert len(execution["compared_field_ids"]) == 3
            assert len(set(execution["candidate_sort_values"].values())) == 3
            assert all(
                str(spec["section_id"]) == str(execution["query_section_id"])
                for spec in execution["field_specs"]
                if str(spec["field_id"]) in set(execution["compared_field_ids"])
            )
            query_section_field_tops = [
                float(render_map["field_box_bboxes_px"][str(spec["field_id"])][1])
                for spec in execution["field_specs"]
                if str(spec["section_id"]) == str(execution["query_section_id"])
            ]
            section_label_bbox = render_map["section_label_bboxes_px"][str(execution["query_section_id"])]
            assert float(section_label_bbox[3]) <= min(query_section_field_tops)


def test_documents_relation_prompt_examples_match_variant_contract() -> None:
    task = DocumentsRelationSectionExtremumValueTask()
    expected = {
        "earliest_date_in_section": (
            {"evidence": [[150, 260, 364, 294]], "answer": "2026-03-18"},
            {"answer": "2026-03-18"},
        ),
        "latest_date_in_section": (
            {"evidence": [[150, 260, 364, 294]], "answer": "2026-04-27"},
            {"answer": "2026-04-27"},
        ),
        "largest_amount_in_section": (
            {"evidence": [[150, 260, 364, 294]], "answer": "$128.40"},
            {"answer": "$128.40"},
        ),
        "smallest_amount_in_section": (
            {"evidence": [[150, 260, 364, 294]], "answer": "$18.40"},
            {"answer": "$18.40"},
        ),
    }

    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=36240):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_documents_relation_section_extremum_value_is_deterministic() -> None:
    task = DocumentsRelationSectionExtremumValueTask()
    params = {"task_variant": "largest_amount_in_section", "scene_variant": "invoice_sheet"}
    out_a = task.generate(36320, params=params, max_attempts=10)
    out_b = task.generate(36320, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_documents_relation_balanced_sampling_defaults_cover_variants() -> None:
    task = DocumentsRelationSectionExtremumValueTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(48):
        out = task.generate(hash64(36380, "documents_relation", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {
        "earliest_date_in_section",
        "latest_date_in_section",
        "largest_amount_in_section",
        "smallest_amount_in_section",
    }
    assert set(scene_variants.keys()) == {"form_sheet", "invoice_sheet", "receipt_sheet"}


def test_documents_relation_rejects_incompatible_scene_variant() -> None:
    task = DocumentsRelationSectionExtremumValueTask()
    with pytest.raises(ValueError, match="unsupported scene_variant"):
        task.generate(
            36440,
            params={
                "task_variant": "largest_amount_in_section",
                "scene_variant": "form_sheet",
            },
            max_attempts=10,
        )
