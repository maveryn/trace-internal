"""Behavior tests for puzzle arithmetic tasks."""

from __future__ import annotations

from trace.tasks.puzzles.arithmetic.equation_value import PuzzlesArithmeticEquationValueTask
from tests.helpers import extract_prompt_json_example


def _evaluate_expression(operand_values: list[int], operator_symbols: list[str]) -> int:
    collapsed_terms = [int(operand_values[0])]
    additive_ops: list[str] = []
    for operator_symbol, operand_value in zip(operator_symbols, operand_values[1:]):
        if str(operator_symbol) == "×":
            collapsed_terms[-1] = int(collapsed_terms[-1] * int(operand_value))
        elif str(operator_symbol) in {"+", "-"}:
            additive_ops.append(str(operator_symbol))
            collapsed_terms.append(int(operand_value))
        else:
            raise AssertionError(f"unexpected operator: {operator_symbol}")
    total = int(collapsed_terms[0])
    for operator_symbol, term_value in zip(additive_ops, collapsed_terms[1:]):
        if str(operator_symbol) == "+":
            total += int(term_value)
        else:
            total -= int(term_value)
    return int(total)


def test_puzzle_arithmetic_equation_value_contract_matches_unknown_slot() -> None:
    task = PuzzlesArithmeticEquationValueTask()
    task_variants = (
        "result_unknown",
        "operand_unknown",
    )
    scene_variants = (
        "equation_strip",
        "equation_card",
        "equation_outline",
    )

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 23010 + (variant_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"task_variant": task_variant, "scene_variant": scene_variant},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            solver = execution["solver_trace"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert str(out.task_variant) == str(task_variant)
            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert all(float(bbox[0]) >= 0.0 for bbox in render_map["slot_bboxes_px"].values())
            assert all(float(bbox[2]) <= float(render["canvas_width"]) for bbox in render_map["slot_bboxes_px"].values())
            assert list(execution["slot_count_range"]) == [3, 6]
            assert list(execution["operand_count_range"]) == [2, 5]
            assert 3 <= int(execution["slot_count"]) <= 6
            assert 2 <= int(execution["operand_count"]) <= 5
            assert int(execution["step_count"]) == 1
            assert int(execution["answer_value"]) == int(out.answer_gt.value)
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert [str(slot_id) for slot_id in execution["supporting_slot_ids"]] == [str(execution["query_slot_id"])]
            assert str(solver["unknown_side"]) in {"left", "right"}
            assert int(solver["operator_count"]) == int(execution["operand_count"]) - 1
            assert len(solver["operand_values"]) == int(execution["operand_count"])
            assert len(solver["operator_symbols"]) == int(solver["operator_count"])

            expected_bbox = [
                float(value)
                for value in render_map["slot_bboxes_px"][str(execution["query_slot_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox

            evaluated_result = _evaluate_expression(
                [int(value) for value in solver["operand_values"]],
                [str(symbol) for symbol in solver["operator_symbols"]],
            )
            assert int(evaluated_result) == int(solver["result_value"])
            assert int(execution["slot_count"]) == int(execution["operand_count"]) + 1

            slot_entities = [
                entity
                for entity in trace["scene_ir"]["entities"]
                if str(entity.get("entity_type")) == "puzzle_slot"
            ]
            operator_entities = [
                entity
                for entity in trace["scene_ir"]["entities"]
                if str(entity.get("entity_type")) == "puzzle_operator"
            ]
            slot_center_y_by_row = {}
            for entity in slot_entities:
                row_index = int(entity["attrs"]["row_index"])
                bbox = [float(value) for value in entity["bbox_px"]]
                slot_center_y_by_row.setdefault(row_index, []).append(0.5 * (bbox[1] + bbox[3]))
            for entity in operator_entities:
                row_index = int(entity["attrs"]["row_index"])
                bbox = [float(value) for value in entity["bbox_px"]]
                operator_center_y = 0.5 * (bbox[1] + bbox[3])
                row_slot_centers = slot_center_y_by_row[row_index]
                expected_center_y = sum(row_slot_centers) / len(row_slot_centers)
                assert abs(operator_center_y - expected_center_y) <= 1.5

            if str(task_variant) == "result_unknown":
                assert str(execution["query_slot_id"]) == "slot_result"
                assert str(solver["unknown_side"]) == "right"
                assert int(out.answer_gt.value) == int(solver["result_value"])
                assert solver["hidden_operand_index"] is None
            else:
                hidden_index = int(solver["hidden_operand_index"])
                assert str(execution["query_slot_id"]) == f"slot_operand_{hidden_index}"
                assert str(solver["unknown_side"]) == "left"
                assert int(out.answer_gt.value) == int(solver["operand_values"][hidden_index])


def test_puzzle_arithmetic_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesArithmeticEquationValueTask()
    expected = {
        "result_unknown": (
            {"evidence": [[680, 180, 800, 276]], "answer": 14},
            {"answer": 14},
        ),
        "operand_unknown": (
            {"evidence": [[120, 180, 240, 276]], "answer": 5},
            {"answer": 5},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=23040):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_arithmetic_equation_value_task_is_deterministic() -> None:
    task = PuzzlesArithmeticEquationValueTask()
    params = {"task_variant": "operand_unknown", "scene_variant": "equation_card"}
    out_a = task.generate(23080, params=params, max_attempts=10)
    out_b = task.generate(23080, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_arithmetic_slot_count_varies_with_seed() -> None:
    task = PuzzlesArithmeticEquationValueTask()
    for task_variant in (
        "result_unknown",
        "operand_unknown",
    ):
        slot_counts = set()
        for seed in range(23120, 23132):
            out = task.generate(seed, params={"task_variant": task_variant}, max_attempts=10)
            slot_counts.add(int(out.trace_payload["execution_trace"]["slot_count"]))
        assert all(3 <= int(slot_count) <= 6 for slot_count in slot_counts)
        assert len(slot_counts) >= 2


def test_puzzle_arithmetic_long_rows_fit_within_canvas() -> None:
    task = PuzzlesArithmeticEquationValueTask()
    out = task.generate(
        23220,
        params={
            "task_variant": "operand_unknown",
            "scene_variant": "equation_strip",
            "operand_count_min": 5,
            "operand_count_max": 5,
        },
        max_attempts=10,
    )
    render = out.trace_payload["render_spec"]
    slot_bboxes = out.trace_payload["render_map"]["slot_bboxes_px"].values()

    assert int(out.trace_payload["execution_trace"]["operand_count"]) == 5
    assert int(out.trace_payload["execution_trace"]["slot_count"]) == 6
    assert max(float(bbox[2]) for bbox in slot_bboxes) <= float(render["canvas_width"])
