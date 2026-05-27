"""Behavior tests for puzzle logic tasks."""

from __future__ import annotations

import json
from collections import Counter

from trace.tasks.puzzles.logic.grid_completion_label import (
    PuzzlesLogicGridKingNonTouchLabelTask,
    PuzzlesLogicGridUniquenessCompletionLabelTask,
)
from trace.tasks.puzzles.logic.raven_matrix_label import (
    PuzzlesLogicRavenAnalogicalTransformLabelTask,
    PuzzlesLogicRavenCountProgressionLabelTask,
    PuzzlesLogicRavenPositionProgressionLabelTask,
    PuzzlesLogicRavenSetOperationLabelTask,
    PuzzlesLogicRavenSpatialTransformLabelTask,
)
from tests.helpers import extract_prompt_json_example


def _panel_signature(panel_spec: dict) -> str:
    """Return a stable signature for one Raven panel spec."""

    return json.dumps(panel_spec, sort_keys=True, separators=(",", ":"))


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


def test_puzzle_logic_grid_completion_king_non_touch_contract_matches_winning_option_panel() -> None:
    task = PuzzlesLogicGridKingNonTouchLabelTask()
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

        assert str(out.query_id) == "default"
        assert str(out.query_id) == "king_non_touch"
        assert str(trace["query_spec"]["query_id"]) == "default"
        assert str(trace["query_spec"]["query_id"]) == "king_non_touch"
        assert str(execution["query_id"]) == "default"
        assert str(execution["query_id"]) == "king_non_touch"
        assert str(execution["internal_query_id"]) == "king_non_touch"
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


def test_puzzle_logic_grid_king_non_touch_prompt_examples_match_selected_variant() -> None:
    task = PuzzlesLogicGridKingNonTouchLabelTask()
    out = task.generate(24780, params={}, max_attempts=10)
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_evidence == {"evidence": [[118, 621, 262, 793]], "answer": "A"}
    assert answer_only == {"answer": "A"}


def test_puzzle_logic_grid_king_non_touch_task_is_deterministic() -> None:
    task = PuzzlesLogicGridKingNonTouchLabelTask()
    params = {"scene_variant": "logic_card"}
    out_a = task.generate(24810, params=params, max_attempts=10)
    out_b = task.generate(24810, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_logic_grid_king_non_touch_answer_letters_cover_all_six_options() -> None:
    task = PuzzlesLogicGridKingNonTouchLabelTask()
    observed_letters = set()
    for seed in range(24840, 24865):
        out = task.generate(seed, params={}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
    assert observed_letters == {"A", "B", "C", "D", "E", "F"}


def test_puzzle_logic_grid_completion_label_contract_matches_winning_option_panel() -> None:
    task = PuzzlesLogicGridUniquenessCompletionLabelTask()
    task_cases = (
        ("row_uniqueness", {"uniqueness_query": "axis_uniqueness", "uniqueness_axis": "row"}),
        ("column_uniqueness", {"uniqueness_query": "axis_uniqueness", "uniqueness_axis": "column"}),
        ("row_and_column_uniqueness", {"uniqueness_query": "row_and_column_uniqueness"}),
    )
    scene_variants = (
        "logic_strip",
        "logic_card",
        "logic_outline",
    )

    for query_id_index, (query_id, base_params) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 24510 + (query_id_index * 20) + scene_index
            params = dict(base_params)
            params["scene_variant"] = scene_variant
            out = task.generate(
                seed,
                params=params,
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
            assert str(out.query_id) == "default"
            assert str(out.query_id) == "grid_uniqueness_completion"
            assert str(trace["query_spec"]["query_id"]) == "default"
            assert str(trace["query_spec"]["query_id"]) == "grid_uniqueness_completion"
            assert str(execution["query_id"]) == "default"
            assert str(execution["query_id"]) == "grid_uniqueness_completion"
            assert str(execution["internal_query_id"]) == str(query_id)
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert list(execution["board_size_range"]) == [5, 7]
            assert list(execution["cell_count_range"]) == [25, 49]
            assert 5 <= int(execution["board_size"]) <= 7
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
            assert all(float(bbox[1]) >= 0.0 for bbox in render_map["cell_bboxes_px"].values())
            assert all(float(bbox[2]) <= float(render["canvas_width"]) for bbox in render_map["option_panel_bboxes_px"].values())
            assert all(float(bbox[3]) <= float(render["canvas_height"]) for bbox in render_map["option_panel_bboxes_px"].values())
            assert float(render["scene_bbox_px"][3]) <= float(render["canvas_height"])

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

            if str(query_id) in {"row_uniqueness", "row_and_column_uniqueness"}:
                for row in board_values:
                    assert sorted(row) == sorted(symbol_pool)
            if str(query_id) in {"column_uniqueness", "row_and_column_uniqueness"}:
                for col_index in range(int(execution["board_size"])):
                    assert sorted(_column_values(board_values, col_index)) == sorted(symbol_pool)

            assert str(solver["rule_type"]) == str(query_id)
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(execution["correct_option_index"])
            assert len(solver["option_object_types"]) == 6


def test_puzzle_logic_prompt_examples_match_selected_variants() -> None:
    cases = (
        (
            PuzzlesLogicGridUniquenessCompletionLabelTask(),
            {"uniqueness_query": "axis_uniqueness", "uniqueness_axis": "row"},
            {"evidence": [[176, 650, 320, 822]], "answer": "C"},
            {"answer": "C"},
        ),
        (
            PuzzlesLogicGridUniquenessCompletionLabelTask(),
            {"uniqueness_query": "row_and_column_uniqueness"},
            {"evidence": [[504, 650, 648, 822]], "answer": "B"},
            {"answer": "B"},
        ),
        (
            PuzzlesLogicGridKingNonTouchLabelTask(),
            {},
            {"evidence": [[118, 621, 262, 793]], "answer": "A"},
            {"answer": "A"},
        ),
    )
    for index, (task, params, expected_answer_and_evidence, expected_answer_only) in enumerate(cases, start=24580):
        out = task.generate(index, params=params, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_logic_grid_completion_label_task_is_deterministic() -> None:
    task = PuzzlesLogicGridUniquenessCompletionLabelTask()
    params = {"uniqueness_query": "row_and_column_uniqueness", "scene_variant": "logic_card"}
    out_a = task.generate(24640, params=params, max_attempts=10)
    out_b = task.generate(24640, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_logic_answer_letters_cover_all_six_options() -> None:
    task = PuzzlesLogicGridUniquenessCompletionLabelTask()
    observed_letters = set()
    for seed in range(24680, 24705):
        out = task.generate(seed, params={"uniqueness_query": "axis_uniqueness", "uniqueness_axis": "row"}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
    assert observed_letters == {"A", "B", "C", "D", "E", "F"}


def test_puzzle_logic_grid_sampler_index_covers_answer_letters_per_variant() -> None:
    task = PuzzlesLogicGridUniquenessCompletionLabelTask()
    task_cases = (
        {"uniqueness_query": "axis_uniqueness", "uniqueness_axis": "row"},
        {"uniqueness_query": "axis_uniqueness", "uniqueness_axis": "column"},
        {"uniqueness_query": "row_and_column_uniqueness"},
    )

    for query_id_index, base_params in enumerate(task_cases):
        observed_letters = []
        observed_board_sizes = []
        for local_index in range(54):
            sampling_index = local_index
            params = dict(base_params)
            out = task.generate(
                24920 + sampling_index,
                params=params,
                max_attempts=10,
            )
            observed_letters.append(str(out.answer_gt.value))
            observed_board_sizes.append(int(out.trace_payload["execution_trace"]["board_size"]))
        board_size_counts = Counter(observed_board_sizes)
        letter_counts = Counter(observed_letters)
        assert set(board_size_counts) == {5, 6, 7}
        assert set(letter_counts) == {"A", "B", "C", "D", "E", "F"}
        assert max(board_size_counts.values()) <= 30
        assert max(letter_counts.values()) <= 18


def test_puzzle_logic_grid_king_non_touch_sampler_index_covers_board_size() -> None:
    task = PuzzlesLogicGridKingNonTouchLabelTask()
    observed_board_sizes = []
    for local_index in range(18):
        sampling_index = local_index
        out = task.generate(
            25010 + sampling_index,
            params={},
            max_attempts=10,
        )
        observed_board_sizes.append(int(out.trace_payload["execution_trace"]["board_size"]))
    board_size_counts = Counter(observed_board_sizes)
    assert set(board_size_counts) == {3, 4, 5}
    assert max(board_size_counts.values()) <= 10


def test_puzzle_logic_grid_completion_label_supports_seven_by_seven() -> None:
    task = PuzzlesLogicGridUniquenessCompletionLabelTask()
    out = task.generate(
        24980,
        params={
            "uniqueness_query": "row_and_column_uniqueness",
            "scene_variant": "logic_outline",
        },
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]
    render = out.trace_payload["render_spec"]
    render_map = out.trace_payload["render_map"]
    board_values = [[str(value) for value in row] for row in execution["board_values"]]
    symbol_pool = [str(value) for value in execution["symbol_pool"]]

    assert int(execution["board_size"]) == 7
    assert int(execution["cell_count"]) == 49
    assert "pentagon" in symbol_pool
    for row in board_values:
        assert sorted(row) == sorted(symbol_pool)
    for col_index in range(7):
        assert sorted(_column_values(board_values, col_index)) == sorted(symbol_pool)
    assert all(
        float(bbox[3]) <= float(render["canvas_height"])
        for bbox in render_map["option_panel_bboxes_px"].values()
    )
    assert float(render["scene_bbox_px"][3]) <= float(render["canvas_height"])


def test_puzzle_logic_raven_matrix_label_contract_matches_winning_option_panel() -> None:
    task_cases = (
        (PuzzlesLogicRavenCountProgressionLabelTask(), "count_progression_matrix"),
        (PuzzlesLogicRavenSpatialTransformLabelTask(), "spatial_transform_matrix"),
        (PuzzlesLogicRavenSetOperationLabelTask(), "set_operation_matrix"),
        (PuzzlesLogicRavenAnalogicalTransformLabelTask(), "analogical_transform_matrix"),
        (PuzzlesLogicRavenPositionProgressionLabelTask(), "position_progression_matrix"),
    )
    scene_variants = (
        "raven_strip",
        "raven_card",
        "raven_outline",
    )

    for query_id_index, (task, query_id) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 25100 + (query_id_index * 20) + scene_index
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

            assert str(out.query_id) == "default"
            assert str(out.query_id) == str(query_id)
            assert str(trace["query_spec"]["query_id"]) == "default"
            assert str(trace["query_spec"]["query_id"]) == str(query_id)
            assert str(execution["query_id"]) == "default"
            assert str(execution["query_id"]) == str(query_id)
            assert str(execution["internal_query_id"]) == str(query_id)
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert int(execution["matrix_size"]) == 3
            assert int(execution["cell_count"]) == 9
            assert int(execution["visible_matrix_cell_count"]) == 8
            assert int(execution["option_count"]) == 6
            assert trace["query_spec"]["prompt_variant"]["query_key"] is None
            assert str(execution["question_format"]) == "raven_matrix_mcq"
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
            assert all(float(bbox[0]) >= 0.0 for bbox in render_map["matrix_cell_bboxes_px"].values())
            assert all(float(bbox[1]) >= 0.0 for bbox in render_map["matrix_cell_bboxes_px"].values())
            assert all(float(bbox[2]) <= float(render["canvas_width"]) for bbox in render_map["option_panel_bboxes_px"].values())
            assert all(float(bbox[3]) <= float(render["canvas_height"]) for bbox in render_map["option_panel_bboxes_px"].values())

            matrix_rows = execution["matrix_rows"]
            matrix_panel_specs = execution["matrix_panel_specs"]
            unknown_cells = [
                cell
                for row in matrix_rows
                for cell in row
                if bool(cell["is_unknown"])
            ]
            assert len(unknown_cells) == 1
            assert str(unknown_cells[0]["cell_id"]) == "cell_2_2"
            assert int(execution["query_row_index"]) == 2
            assert int(execution["query_col_index"]) == 2
            assert execution["answer_panel_spec"] == matrix_panel_specs[2][2]

            option_specs = execution["option_specs"]
            assert len(option_specs) == 6
            assert [str(option["option_label"]) for option in option_specs] == ["A", "B", "C", "D", "E", "F"]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_panel_signature(dict(option["panel_spec"])) for option in option_specs}) == 6
            winning_option = next(option for option in option_specs if bool(option["is_correct"]))
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_panel_id"]) == str(execution["correct_option_panel_id"])
            assert dict(winning_option["panel_spec"]) == dict(execution["answer_panel_spec"])
            assert str(winning_option["panel_spec"]["panel_kind"]) in {"attribute", "count", "pattern"}

            assert str(solver["rule_type"]) == str(query_id)
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(execution["correct_option_index"])
            if str(query_id) == "count_progression_matrix":
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "count"
                assert int(execution["answer_panel_spec"]["count"]) == int(solver["count_table"][2][2])
                assert int(execution["answer_panel_spec"]["count"]) == int(solver["answer_count"])
            elif str(query_id) == "spatial_transform_matrix":
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "pattern"
                assert execution["answer_panel_spec"]["cells"] == solver["answer_cells"]
                allowed_transforms = {"identity", "rot90", "rot180", "flip_h", "flip_v"}
                assert set(str(value) for value in solver["row_transforms"]) <= allowed_transforms
                assert set(str(value) for value in solver["column_transforms"]) <= allowed_transforms
            elif str(query_id) == "set_operation_matrix":
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "pattern"
                assert str(solver["operation"]) in {"union", "intersection", "xor"}
                assert execution["answer_panel_spec"]["cells"] == solver["answer_cells"]
            elif str(query_id) == "analogical_transform_matrix":
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "attribute"
                assert str(solver["transform_kind"]) in {"shape_cycle", "color_cycle", "size_cycle"}
            else:
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "pattern"
                assert len(execution["answer_panel_spec"]["cells"]) == 1
                assert execution["answer_panel_spec"]["cells"][0] == solver["answer_position"]


def test_puzzle_logic_raven_prompt_examples_match_selected_variants() -> None:
    cases = (
        (
            PuzzlesLogicRavenCountProgressionLabelTask(),
            {},
            {"evidence": [[504, 650, 648, 822]], "answer": "B"},
            {"answer": "B"},
        ),
        (
            PuzzlesLogicRavenSpatialTransformLabelTask(),
            {},
            {"evidence": [[668, 650, 812, 822]], "answer": "D"},
            {"answer": "D"},
        ),
        (
            PuzzlesLogicRavenSetOperationLabelTask(),
            {},
            {"evidence": [[832, 650, 976, 822]], "answer": "E"},
            {"answer": "E"},
        ),
        (
            PuzzlesLogicRavenAnalogicalTransformLabelTask(),
            {},
            {"evidence": [[996, 650, 1140, 822]], "answer": "F"},
            {"answer": "F"},
        ),
        (
            PuzzlesLogicRavenPositionProgressionLabelTask(),
            {},
            {"evidence": [[12, 650, 156, 822]], "answer": "A"},
            {"answer": "A"},
        ),
    )
    for index, (task, params, expected_answer_and_evidence, expected_answer_only) in enumerate(cases, start=25200):
        out = task.generate(index, params=params, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_logic_raven_matrix_label_task_is_deterministic() -> None:
    task = PuzzlesLogicRavenSpatialTransformLabelTask()
    params = {"scene_variant": "raven_card"}
    out_a = task.generate(25250, params=params, max_attempts=10)
    out_b = task.generate(25250, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_logic_raven_sampler_index_covers_answer_letters_per_variant() -> None:
    task_cases = (
        PuzzlesLogicRavenCountProgressionLabelTask(),
        PuzzlesLogicRavenSpatialTransformLabelTask(),
        PuzzlesLogicRavenSetOperationLabelTask(),
        PuzzlesLogicRavenAnalogicalTransformLabelTask(),
        PuzzlesLogicRavenPositionProgressionLabelTask(),
    )

    for query_id_index, task in enumerate(task_cases):
        observed_letters = []
        for local_index in range(18):
            sampling_index = local_index
            out = task.generate(
                25290 + sampling_index,
                params={},
                max_attempts=10,
            )
            observed_letters.append(str(out.answer_gt.value))
        letter_counts = Counter(observed_letters)
        assert set(letter_counts) == {"A", "B", "C", "D", "E", "F"}
        assert max(letter_counts.values()) <= 8
