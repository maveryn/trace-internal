"""Behavior tests for pages form-section arithmetic tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.pages.form_section.sum_minus_amount_in_section_value import (
    PagesFormSectionSumMinusAmountInSectionValueTask,
)
from trace.tasks.pages.form_section.two_amount_arithmetic_value import (
    PagesFormSectionTwoAmountArithmeticValueTask,
)
from tests.helpers import extract_prompt_json_example


TASK_CASES = (
    (
        PagesFormSectionTwoAmountArithmeticValueTask,
        "sum_two_amounts_in_section_value",
        "sum_two_amounts_in_section_value",
        ("+",),
        ("first_operand", "second_operand"),
    ),
    (
        PagesFormSectionTwoAmountArithmeticValueTask,
        "difference_two_amounts_in_section_value",
        "difference_two_amounts_in_section_value",
        ("-",),
        ("first_operand", "second_operand"),
    ),
    (
        PagesFormSectionSumMinusAmountInSectionValueTask,
        "sum_minus_amount_in_section_value",
        "single",
        ("+", "-"),
        ("first_operand", "second_operand", "third_operand"),
    ),
)
SCENE_VARIANTS = ("form_sheet", "invoice_sheet", "receipt_sheet")


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


def test_pages_form_section_arithmetic_contract_matches_trace() -> None:
    for task_index, (task_cls, prompt_key, query_id, operators, expected_roles) in enumerate(TASK_CASES):
        task = task_cls()
        for scene_index, scene_variant in enumerate(SCENE_VARIANTS):
            seed = 38100 + (task_index * 20) + scene_index
            out = task.generate(seed, params={"query_id": query_id, "scene_variant": scene_variant}, max_attempts=10)
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render_map = trace["render_map"]
            annotation_bboxes = {
                str(key): [float(value) for value in bbox]
                for key, bbox in dict(out.annotation_gt.value).items()
            }

            assert out.scene_id == "form_section"
            assert out.query_id == query_id
            assert out.answer_gt.type == "string"
            assert out.annotation_gt.type == "bbox_map"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
            assert str(trace["query_spec"]["query_id"]) == query_id
            assert str(trace["query_spec"]["scene_id"]) == "form_section"
            assert str(execution["query_id"]) == query_id
            assert str(execution["prompt_query_key"]) == prompt_key
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["question_format"]).startswith("form_section_")
            assert str(execution["view_family"]) == "structured_document"
            assert trace["projected_annotation"]["type"] == "bbox_map"
            assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
            assert trace["projected_annotation"]["pixel_bbox_map"] == out.annotation_gt.value
            assert str(out.answer_gt.value) == str(execution["result_value"])
            assert tuple(annotation_bboxes.keys()) == tuple(expected_roles)
            assert tuple(execution["operator_sequence"]) == tuple(operators)

            role_to_bbox_id = trace["witness_symbolic"]["operand_role_to_bbox_id"]
            expected_bboxes = {
                str(role): [float(value) for value in render_map["field_box_bboxes_px"][str(bbox_id)]]
                for role, bbox_id in role_to_bbox_id.items()
            }
            assert annotation_bboxes == expected_bboxes

            for role, field_id in trace["witness_symbolic"]["operand_role_to_field_id"].items():
                assert annotation_bboxes[str(role)] == render_map["field_box_bboxes_px"][str(field_id)]
                value_bbox_id = execution["operand_value_bbox_ids"][list(annotation_bboxes.keys()).index(str(role))]
                value_bbox = render_map["field_value_bboxes_px"][str(value_bbox_id)]
                field_bbox = annotation_bboxes[str(role)]
                assert field_bbox[0] <= float(value_bbox[0])
                assert field_bbox[1] <= float(value_bbox[1])
                assert field_bbox[2] >= float(value_bbox[2])
                assert field_bbox[3] >= float(value_bbox[3])

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


def test_pages_form_section_prompt_examples_match_task_contract() -> None:
    expected = {
        (PagesFormSectionTwoAmountArithmeticValueTask, "sum_two_amounts_in_section_value"): (
            {
                "annotation": {
                    "first_operand": [120, 248, 420, 306],
                    "second_operand": [120, 308, 420, 366],
                },
                "answer": "$146.80",
            },
            {"answer": "$146.80"},
        ),
        (PagesFormSectionTwoAmountArithmeticValueTask, "difference_two_amounts_in_section_value"): (
            {
                "annotation": {
                    "first_operand": [120, 248, 420, 306],
                    "second_operand": [120, 308, 420, 366],
                },
                "answer": "$42.50",
            },
            {"answer": "$42.50"},
        ),
        (PagesFormSectionSumMinusAmountInSectionValueTask, "single"): (
            {
                "annotation": {
                    "first_operand": [120, 248, 420, 306],
                    "second_operand": [120, 308, 420, 366],
                    "third_operand": [120, 368, 420, 426],
                },
                "answer": "$133.30",
            },
            {"answer": "$133.30"},
        ),
    }

    for index, ((task_cls, query_id), (expected_answer_and_annotation, expected_answer_only)) in enumerate(
        expected.items(),
        start=38240,
    ):
        out = task_cls().generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_pages_form_section_arithmetic_task_is_deterministic() -> None:
    task = PagesFormSectionSumMinusAmountInSectionValueTask()
    params = {"query_id": "single", "scene_variant": "invoice_sheet"}
    out_a = task.generate(38320, params=params, max_attempts=10)
    out_b = task.generate(38320, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_form_section_scene_variant_sampling_defaults_cover_variants() -> None:
    task = PagesFormSectionTwoAmountArithmeticValueTask()
    scene_variants: Counter[str] = Counter()

    for index in range(36):
        out = task.generate(hash64(38380, "pages_form_section", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(scene_variants.keys()) == {"form_sheet", "invoice_sheet", "receipt_sheet"}
