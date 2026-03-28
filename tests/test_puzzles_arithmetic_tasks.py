"""Behavior tests for puzzle arithmetic tasks."""

from __future__ import annotations

from trace.tasks.puzzles.arithmetic.balance_value import PuzzlesArithmeticBalanceValueTask
from trace.tasks.puzzles.arithmetic.equation_value import PuzzlesArithmeticEquationValueTask
from trace.tasks.puzzles.arithmetic.grid_value import PuzzlesArithmeticGridValueTask
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


def _resolve_balance_item_value(item: dict[str, object], *, object_values: dict[str, int]) -> int:
    if str(item.get("kind")) == "number":
        return int(item["value"])
    return int(object_values[str(item["object_type"])])


def _evaluate_grid_rule(*, left_value: int, right_value: int, operator_symbol: str) -> int:
    if str(operator_symbol) == "+":
        return int(left_value + right_value)
    if str(operator_symbol) == "-":
        return int(left_value - right_value)
    if str(operator_symbol) == "×":
        return int(left_value * right_value)
    raise AssertionError(f"unexpected grid operator: {operator_symbol}")


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


def test_puzzle_arithmetic_grid_value_contract_matches_unknown_cell() -> None:
    task = PuzzlesArithmeticGridValueTask()
    task_variants = (
        "sum_rule_missing",
        "difference_rule_missing",
        "product_rule_missing",
    )
    scene_variants = (
        "grid_strip",
        "grid_card",
        "grid_outline",
    )
    expected_operator_by_variant = {
        "sum_rule_missing": "+",
        "difference_rule_missing": "-",
        "product_rule_missing": "×",
    }

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 23180 + (variant_index * 20) + scene_index
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
            assert list(execution["row_count_range"]) == [3, 5]
            assert int(execution["col_count"]) == 3
            assert list(execution["cell_count_range"]) == [9, 15]
            assert 3 <= int(execution["row_count"]) <= 5
            assert int(execution["cell_count"]) == int(execution["row_count"]) * 3
            assert str(execution["question_format"]) == "unknown_cell_grid"
            assert int(execution["answer_value"]) == int(out.answer_gt.value)
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert [str(cell_id) for cell_id in execution["supporting_cell_ids"]] == [str(execution["query_cell_id"])]
            assert str(solver["operator_symbol"]) == str(expected_operator_by_variant[str(task_variant)])
            assert bool(solver["complete_rows_unique_operator"]) is True
            assert len(execution["visible_example_rows"]) == int(execution["row_count"]) - 1

            expected_bbox = [
                float(value)
                for value in render_map["cell_bboxes_px"][str(execution["query_cell_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox
            assert all(float(bbox[0]) >= 0.0 for bbox in render_map["cell_bboxes_px"].values())
            assert all(float(bbox[2]) <= float(render["canvas_width"]) for bbox in render_map["cell_bboxes_px"].values())

            for row in execution["visible_example_rows"]:
                assert len(row) == 3
                assert int(row[2]) == _evaluate_grid_rule(
                    left_value=int(row[0]),
                    right_value=int(row[1]),
                    operator_symbol=str(solver["operator_symbol"]),
                )

            row_values = [[int(value) for value in row] for row in execution["row_values"]]
            query_row_index = int(execution["query_row_index"])
            query_col_index = int(execution["query_col_index"])
            assert int(out.answer_gt.value) == int(row_values[query_row_index][query_col_index])


def test_puzzle_arithmetic_grid_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesArithmeticGridValueTask()
    expected = {
        "sum_rule_missing": (
            {"evidence": [[420, 250, 540, 350]], "answer": 7},
            {"answer": 7},
        ),
        "difference_rule_missing": (
            {"evidence": [[420, 250, 540, 350]], "answer": 6},
            {"answer": 6},
        ),
        "product_rule_missing": (
            {"evidence": [[420, 250, 540, 350]], "answer": 8},
            {"answer": 8},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=23220):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_arithmetic_grid_task_is_deterministic() -> None:
    task = PuzzlesArithmeticGridValueTask()
    params = {"task_variant": "product_rule_missing", "scene_variant": "grid_card"}
    out_a = task.generate(23240, params=params, max_attempts=10)
    out_b = task.generate(23240, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_arithmetic_grid_row_count_and_hidden_position_vary_with_seed() -> None:
    task = PuzzlesArithmeticGridValueTask()
    row_counts = set()
    query_positions = set()
    for seed in range(23280, 23294):
        out = task.generate(seed, params={"task_variant": "sum_rule_missing"}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        row_counts.add(int(execution["row_count"]))
        query_positions.add((int(execution["query_row_index"]), int(execution["query_col_index"])))
    assert all(3 <= int(row_count) <= 5 for row_count in row_counts)
    assert len(row_counts) >= 2
    assert len(query_positions) >= 3


def test_puzzle_arithmetic_balance_value_contract_matches_query_answer_box() -> None:
    task = PuzzlesArithmeticBalanceValueTask()
    task_variants = (
        "sum_pair_unknown",
        "two_panel_chain_unknown",
        "three_panel_chain_unknown",
    )
    scene_variants = (
        "balance_strip",
        "balance_card",
        "balance_outline",
    )

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 23260 + (variant_index * 20) + scene_index
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
            assert list(execution["panel_count_range"]) == [2, 3]
            assert list(execution["total_box_count_range"]) == [8, 11]
            assert 2 <= int(execution["panel_count"]) <= 3
            assert 8 <= int(execution["total_box_count"]) <= 11
            assert str(execution["question_format"]) == "query_answer_box_balance"
            assert int(execution["answer_value"]) == int(out.answer_gt.value)
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert [str(box_id) for box_id in execution["supporting_box_ids"]] == [str(execution["query_box_id"])]

            expected_bbox = [
                float(value)
                for value in render_map["box_bboxes_px"][str(execution["query_box_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox
            assert all(float(bbox[0]) >= 0.0 for bbox in render_map["box_bboxes_px"].values())
            assert all(float(bbox[2]) <= float(render["canvas_width"]) for bbox in render_map["box_bboxes_px"].values())

            object_values = {str(key): int(value) for key, value in solver["object_values"].items()}
            for panel in execution["panel_specs"]:
                left_total = sum(
                    _resolve_balance_item_value(item, object_values=object_values)
                    for item in panel["left_items"]
                )
                right_total = sum(
                    _resolve_balance_item_value(item, object_values=object_values)
                    for item in panel["right_items"]
                )
                assert int(left_total) == int(right_total)
            assert int(out.answer_gt.value) == int(object_values[str(execution["query_object_type"])])
            assert str(execution["query_object_box_id"]) in render_map["box_bboxes_px"]
            equal_entities = [
                entity
                for entity in trace["scene_ir"]["entities"]
                if str(entity.get("entity_type")) == "puzzle_balance_equals"
            ]
            assert len(equal_entities) == int(execution["panel_count"]) + 1
            plus_entities = [
                entity
                for entity in trace["scene_ir"]["entities"]
                if str(entity.get("entity_type")) == "puzzle_balance_operator"
            ]
            expected_plus_count = sum(
                max(0, len(panel["left_items"]) - 1) + max(0, len(panel["right_items"]) - 1)
                for panel in execution["panel_specs"]
            )
            assert len(plus_entities) == int(expected_plus_count)


def test_puzzle_arithmetic_balance_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesArithmeticBalanceValueTask()
    expected = {
        "sum_pair_unknown": (
            {"evidence": [[574, 508, 686, 620]], "answer": 7},
            {"answer": 7},
        ),
        "two_panel_chain_unknown": (
            {"evidence": [[574, 508, 686, 620]], "answer": 8},
            {"answer": 8},
        ),
        "three_panel_chain_unknown": (
            {"evidence": [[574, 508, 686, 620]], "answer": 5},
            {"answer": 5},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=23310):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_arithmetic_balance_value_task_is_deterministic() -> None:
    task = PuzzlesArithmeticBalanceValueTask()
    params = {"task_variant": "three_panel_chain_unknown", "scene_variant": "balance_card"}
    out_a = task.generate(23360, params=params, max_attempts=10)
    out_b = task.generate(23360, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


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
