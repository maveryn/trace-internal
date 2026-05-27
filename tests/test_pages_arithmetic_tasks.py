"""Behavior tests for pages arithmetic tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.pages.arithmetic.section_expression_value import (
    PagesArithmeticSectionExpressionValueTask,
)
from tests.helpers import extract_prompt_json_example


def _apply_expression(operand_cents: list[int], operators: list[str]) -> int:
    """Recompute one left-to-right cent-valued expression from the trace payload."""

    result = int(operand_cents[0])
    for operator, value in zip(operators, operand_cents[1:]):
        if str(operator) == "+":
            result += int(value)
        elif str(operator) == "-":
            result -= int(value)
        else:
            raise AssertionError(f"unexpected operator {operator}")
    return int(result)


def test_pages_arithmetic_section_expression_value_contract_matches_trace() -> None:
    task = PagesArithmeticSectionExpressionValueTask()
    query_variants = (
        "sum_two_amounts_in_section",
        "difference_two_amounts_in_section",
        "sum_minus_amount_in_section",
    )
    scene_variants = ("form_sheet", "invoice_sheet", "receipt_sheet")

    for variant_index, query_variant in enumerate(query_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 38100 + (variant_index * 20) + scene_index
            out = task.generate(seed, params={"query_variant": query_variant, "scene_variant": scene_variant}, max_attempts=10)
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render_map = trace["render_map"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert out.answer_gt.type == "string"
            assert out.evidence_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(out.query_variant) == "default"
            assert str(out.query_id) == str(query_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["query_variant"]) == "default"
            assert str(execution["query_id"]) == str(query_variant)
            assert str(execution["question_format"]) == "document_section_expression_value"
            assert str(execution["view_family"]) == "structured_document"
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert str(out.answer_gt.value) == str(execution["result_value"])
            assert len(evidence_bboxes) == len(execution["operand_value_bbox_ids"])

            expected_bboxes = [
                [float(value) for value in render_map["field_value_bboxes_px"][str(bbox_id)]]
                for bbox_id in execution["operand_value_bbox_ids"]
            ]
            assert evidence_bboxes == expected_bboxes

            visible_values = [str(spec["field_value"]) for spec in execution["field_specs"]]
            assert str(execution["result_value"]) not in set(visible_values)
            assert str(execution["query_section_id"]) in render_map["section_box_bboxes_px"]
            assert str(execution["query_section_id"]) in render_map["section_label_bboxes_px"]
            assert int(execution["target_amount_candidate_count"]) >= 8
            assert len(execution["target_amount_candidate_field_ids"]) == int(
                execution["target_amount_candidate_count"]
            )
            assert len(execution["operand_field_ids"]) == len(execution["operand_field_labels"])
            assert len(execution["operand_field_ids"]) == len(execution["operand_field_values"])
            assert len(execution["operand_field_ids"]) == len(execution["operator_sequence"]) + 1
            assert set(execution["operand_field_ids"]).issubset(set(execution["target_amount_candidate_field_ids"]))

            expected_cents = _apply_expression(
                [int(value) for value in execution["expression_operand_cents"]],
                [str(value) for value in execution["operator_sequence"]],
            )
            assert expected_cents == int(execution["result_cents"])

            query_section_field_tops = [
                float(render_map["field_box_bboxes_px"][str(spec["field_id"])][1])
                for spec in execution["field_specs"]
                if str(spec["section_id"]) == str(execution["query_section_id"])
            ]
            section_label_bbox = render_map["section_label_bboxes_px"][str(execution["query_section_id"])]
            assert float(section_label_bbox[3]) <= min(query_section_field_tops)


def test_pages_arithmetic_prompt_examples_match_variant_contract() -> None:
    task = PagesArithmeticSectionExpressionValueTask()
    expected = {
        "sum_two_amounts_in_section": (
            {
                "evidence": [[150, 260, 364, 294], [150, 320, 364, 354]],
                "answer": "$146.80",
            },
            {"answer": "$146.80"},
        ),
        "difference_two_amounts_in_section": (
            {
                "evidence": [[150, 260, 364, 294], [150, 320, 364, 354]],
                "answer": "$42.50",
            },
            {"answer": "$42.50"},
        ),
        "sum_minus_amount_in_section": (
            {
                "evidence": [[150, 260, 364, 294], [150, 320, 364, 354], [150, 380, 364, 414]],
                "answer": "$133.30",
            },
            {"answer": "$133.30"},
        ),
    }

    for index, (query_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=38240):
        out = task.generate(index, params={"query_variant": query_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_pages_arithmetic_section_expression_value_is_deterministic() -> None:
    task = PagesArithmeticSectionExpressionValueTask()
    params = {"query_variant": "sum_minus_amount_in_section", "scene_variant": "invoice_sheet"}
    out_a = task.generate(38320, params=params, max_attempts=10)
    out_b = task.generate(38320, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_arithmetic_balanced_sampling_defaults_cover_variants() -> None:
    task = PagesArithmeticSectionExpressionValueTask()
    query_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    pairs: Counter[tuple[str, str]] = Counter()

    for index in range(36):
        out = task.generate(hash64(38380, "pages_arithmetic", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        query_variants[str(execution["query_id"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        pairs[(str(execution["query_id"]), str(execution["scene_variant"]))] += 1

    assert set(query_variants.keys()) == {
        "sum_two_amounts_in_section",
        "difference_two_amounts_in_section",
        "sum_minus_amount_in_section",
    }
    assert set(scene_variants.keys()) == {"form_sheet", "invoice_sheet", "receipt_sheet"}
    assert len(pairs) == 9
