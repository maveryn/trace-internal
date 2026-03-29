"""Behavior tests for puzzle logic tasks."""

from __future__ import annotations

from trace.tasks.puzzles.logic.adjacency_completion_label import PuzzlesLogicAdjacencyCompletionLabelTask
from trace.tasks.puzzles.logic.grid_completion_label import PuzzlesLogicGridCompletionLabelTask
from tests.helpers import extract_prompt_json_example


def _column_values(board_values: list[list[str]], col_index: int) -> list[str]:
    """Return one board column as a string list."""

    return [str(row[col_index]) for row in board_values]


def _king_neighbors(board_values: list[list[str]], row_index: int, col_index: int) -> list[str]:
    """Return all king-move neighbor values around one board cell."""

    board_size = int(len(board_values))
    values: list[str] = []
    for delta_row in (-1, 0, 1):
        for delta_col in (-1, 0, 1):
            if delta_row == 0 and delta_col == 0:
                continue
            nbr_row = int(row_index + delta_row)
            nbr_col = int(col_index + delta_col)
            if 0 <= nbr_row < board_size and 0 <= nbr_col < board_size:
                values.append(str(board_values[nbr_row][nbr_col]))
    return values


def test_puzzle_logic_adjacency_completion_label_contract_matches_winning_option_panel() -> None:
    task = PuzzlesLogicAdjacencyCompletionLabelTask()
    scene_variants = (
        "logic_strip",
        "logic_card",
        "logic_outline",
    )

    for scene_index, scene_variant in enumerate(scene_variants):
        seed = 24720 + scene_index
        out = task.generate(
            seed,
            params={"scene_variant": scene_variant},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        solver = execution["solver_trace"]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        board_values = [[str(value) for value in row] for row in execution["board_values"]]
        symbol_pool = [str(value) for value in execution["symbol_pool"]]

        assert str(out.task_variant) == "king_non_touch"
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "bbox_set"
        assert len(evidence_bboxes) == 1
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert list(execution["board_size_range"]) == [3, 5]
        assert list(execution["cell_count_range"]) == [9, 25]
        assert 3 <= int(execution["board_size"]) <= 5
        assert int(execution["cell_count"]) == int(execution["board_size"]) ** 2
        assert int(execution["option_count"]) == 6
        assert str(execution["question_format"]) == "logic_adjacency_mcq"
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert [str(option_id) for option_id in execution["supporting_option_panel_ids"]] == [
            str(execution["correct_option_panel_id"])
        ]
        assert str(out.answer_gt.value) == str(execution["answer_option_label"])
        assert str(out.answer_gt.value) in {"A", "B", "C", "D", "E", "F"}

        expected_bbox = [
            float(value)
            for value in render_map["option_panel_bboxes_px"][str(execution["correct_option_panel_id"])]
        ]
        assert evidence_bboxes[0] == expected_bbox

        option_specs = execution["option_specs"]
        assert len(option_specs) == 6
        assert [str(option["option_label"]) for option in option_specs] == ["A", "B", "C", "D", "E", "F"]
        assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
        winning_option = next(option for option in option_specs if bool(option["is_correct"]))
        assert str(winning_option["option_label"]) == str(out.answer_gt.value)
        assert str(winning_option["option_panel_id"]) == str(execution["correct_option_panel_id"])
        assert str(winning_option["object_type"]) == str(execution["answer_object_type"])

        query_row = int(execution["query_row_index"])
        query_col = int(execution["query_col_index"])
        neighbors = _king_neighbors(board_values, query_row, query_col)
        assert len(neighbors) == len(execution["neighbor_coords"])
        assert len(set(neighbors)) == 5
        assert str(execution["answer_object_type"]) not in set(neighbors)
        assert execution["valid_option_object_types"] == [str(execution["answer_object_type"])]

        for row_index, row in enumerate(board_values):
            for col_index, value in enumerate(row):
                other_neighbors = _king_neighbors(board_values, row_index, col_index)
                assert str(value) not in other_neighbors

        assert str(solver["rule_type"]) == "king_non_touch"
        assert str(solver["touch_rule"]) == "no_identical_symbols_touch_orthogonally_or_diagonally"
        assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
        assert int(solver["correct_option_index"]) == int(execution["correct_option_index"])
        assert len(solver["option_object_types"]) == 6
        assert sorted(symbol_pool) == sorted(["circle", "triangle", "diamond", "square", "hexagon", "star"])


def test_puzzle_logic_adjacency_prompt_examples_match_selected_variant() -> None:
    task = PuzzlesLogicAdjacencyCompletionLabelTask()
    out = task.generate(24780, params={"task_variant": "king_non_touch"}, max_attempts=10)
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_evidence == {"evidence": [[118, 621, 262, 793]], "answer": "A"}
    assert answer_only == {"answer": "A"}


def test_puzzle_logic_adjacency_completion_label_task_is_deterministic() -> None:
    task = PuzzlesLogicAdjacencyCompletionLabelTask()
    params = {"task_variant": "king_non_touch", "scene_variant": "logic_card"}
    out_a = task.generate(24810, params=params, max_attempts=10)
    out_b = task.generate(24810, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_logic_adjacency_answer_letters_cover_all_six_options() -> None:
    task = PuzzlesLogicAdjacencyCompletionLabelTask()
    observed_letters = set()
    for seed in range(24840, 24865):
        out = task.generate(seed, params={"task_variant": "king_non_touch"}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
    assert observed_letters == {"A", "B", "C", "D", "E", "F"}


def test_puzzle_logic_grid_completion_label_contract_matches_winning_option_panel() -> None:
    task = PuzzlesLogicGridCompletionLabelTask()
    task_variants = (
        "row_uniqueness",
        "column_uniqueness",
        "row_and_column_uniqueness",
    )
    scene_variants = (
        "logic_strip",
        "logic_card",
        "logic_outline",
    )

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 24510 + (variant_index * 20) + scene_index
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
            board_values = [[str(value) for value in row] for row in execution["board_values"]]
            symbol_pool = [str(value) for value in execution["symbol_pool"]]

            assert str(out.task_variant) == str(task_variant)
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert list(execution["board_size_range"]) == [3, 5]
            assert list(execution["cell_count_range"]) == [9, 25]
            assert 3 <= int(execution["board_size"]) <= 5
            assert int(execution["cell_count"]) == int(execution["board_size"]) ** 2
            assert int(execution["option_count"]) == 6
            assert str(execution["question_format"]) == "logic_grid_mcq"
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert [str(option_id) for option_id in execution["supporting_option_panel_ids"]] == [
                str(execution["correct_option_panel_id"])
            ]
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])
            assert str(out.answer_gt.value) in {"A", "B", "C", "D", "E", "F"}

            expected_bbox = [
                float(value)
                for value in render_map["option_panel_bboxes_px"][str(execution["correct_option_panel_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox
            assert all(float(bbox[0]) >= 0.0 for bbox in render_map["cell_bboxes_px"].values())
            assert all(float(bbox[2]) <= float(render["canvas_width"]) for bbox in render_map["option_panel_bboxes_px"].values())

            unknown_cells = [
                cell
                for row in execution["grid_rows"]
                for cell in row
                if bool(cell["is_unknown"])
            ]
            assert len(unknown_cells) == 1
            assert str(unknown_cells[0]["cell_id"]) == str(execution["query_cell_id"])
            assert int(execution["query_row_index"]) in range(int(execution["board_size"]))
            assert int(execution["query_col_index"]) in range(int(execution["board_size"]))
            assert str(execution["answer_object_type"]) == str(
                board_values[int(execution["query_row_index"])][int(execution["query_col_index"])]
            )

            option_specs = execution["option_specs"]
            assert len(option_specs) == 6
            assert [str(option["option_label"]) for option in option_specs] == ["A", "B", "C", "D", "E", "F"]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            winning_option = next(option for option in option_specs if bool(option["is_correct"]))
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_panel_id"]) == str(execution["correct_option_panel_id"])
            assert str(winning_option["object_type"]) == str(execution["answer_object_type"])

            if str(task_variant) in {"row_uniqueness", "row_and_column_uniqueness"}:
                for row in board_values:
                    assert sorted(row) == sorted(symbol_pool)
            if str(task_variant) in {"column_uniqueness", "row_and_column_uniqueness"}:
                for col_index in range(int(execution["board_size"])):
                    assert sorted(_column_values(board_values, col_index)) == sorted(symbol_pool)

            assert str(solver["rule_type"]) == str(task_variant)
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(execution["correct_option_index"])
            assert len(solver["option_object_types"]) == 6


def test_puzzle_logic_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesLogicGridCompletionLabelTask()
    expected = {
        "row_uniqueness": (
            {"evidence": [[176, 650, 320, 822]], "answer": "C"},
            {"answer": "C"},
        ),
        "column_uniqueness": (
            {"evidence": [[340, 650, 484, 822]], "answer": "D"},
            {"answer": "D"},
        ),
        "row_and_column_uniqueness": (
            {"evidence": [[504, 650, 648, 822]], "answer": "B"},
            {"answer": "B"},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=24580):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_logic_grid_completion_label_task_is_deterministic() -> None:
    task = PuzzlesLogicGridCompletionLabelTask()
    params = {"task_variant": "row_and_column_uniqueness", "scene_variant": "logic_card"}
    out_a = task.generate(24640, params=params, max_attempts=10)
    out_b = task.generate(24640, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_logic_answer_letters_cover_all_six_options() -> None:
    task = PuzzlesLogicGridCompletionLabelTask()
    observed_letters = set()
    for seed in range(24680, 24705):
        out = task.generate(seed, params={"task_variant": "row_uniqueness"}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
    assert observed_letters == {"A", "B", "C", "D", "E", "F"}
