"""Behavior tests for migrated logic-grid puzzle tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.puzzles.logic_grid.grid_king_non_touch_label import (
    PuzzlesLogicGridKingNonTouchLabelTask,
)
from trace.tasks.puzzles.logic_grid.grid_uniqueness_completion_label import (
    AXIS_UNIQUENESS_QUERY,
    ROW_AND_COLUMN_UNIQUENESS_QUERY,
    PuzzlesLogicGridUniquenessCompletionLabelTask,
)
from tests.helpers import extract_prompt_json_example


def _column_values(board_values: list[list[str]], col_index: int) -> list[str]:
    """Return one board column as a string list."""

    return [str(row[col_index]) for row in board_values]


def _king_neighbors(
    board_values: list[list[str]],
    row_index: int,
    col_index: int,
) -> list[str]:
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


def test_logic_grid_uniqueness_contract_matches_selected_option() -> None:
    task = PuzzlesLogicGridUniquenessCompletionLabelTask()
    cases = (
        (AXIS_UNIQUENESS_QUERY, {"uniqueness_axis": "row"}, "row_uniqueness"),
        (AXIS_UNIQUENESS_QUERY, {"uniqueness_axis": "column"}, "column_uniqueness"),
        (ROW_AND_COLUMN_UNIQUENESS_QUERY, {}, "row_column_uniqueness_rule"),
    )

    for index, (query_id, extra_params, expected_rule) in enumerate(cases):
        params = {
            "query_id": query_id,
            "scene_variant": ("logic_strip", "logic_card", "logic_outline")[index],
            **dict(extra_params),
        }
        out = task.generate(24720 + index, params=params, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        annotation_bboxes = {
            str(key): [float(value) for value in bbox]
            for key, bbox in out.annotation_gt.value.items()
        }
        board_values = [[str(value) for value in row] for row in execution["board_values"]]
        symbol_pool = [str(value) for value in execution["symbol_pool"]]

        assert str(out.query_id) == str(query_id)
        assert str(out.scene_id) == "logic_grid"
        assert task.supported_query_ids == (AXIS_UNIQUENESS_QUERY, ROW_AND_COLUMN_UNIQUENESS_QUERY)
        assert out.answer_gt.type == "option_letter"
        assert out.annotation_gt.type == "bbox_map"
        assert set(annotation_bboxes) == {"source_grid", "selected_option"}
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert str(execution["semantic_rule"]) == str(expected_rule)
        assert str(execution["solver_trace"]["rule_type"]) == str(expected_rule)
        assert 5 <= int(execution["board_size"]) <= 7
        assert int(execution["cell_count"]) == int(execution["board_size"]) ** 2
        assert int(execution["option_count"]) == 6
        assert str(execution["question_format"]) == "logic_grid_mcq"
        assert trace["projected_annotation"]["type"] == "bbox_map"
        assert trace["projected_annotation"]["bbox_map"] == annotation_bboxes
        assert trace["projected_annotation"]["pixel_bbox_map"] == annotation_bboxes
        assert render_map["annotation_source"] == "keyed_source_grid_and_option_bboxes_px"
        assert render["text_style"]["font"]["source"] == "global_font_pool"
        assert str(out.answer_gt.value) == str(execution["answer_option_label"])

        expected_bbox = [
            float(value)
            for value in render_map["option_panel_bboxes_px"][str(execution["correct_option_panel_id"])]
        ]
        assert annotation_bboxes["selected_option"] == expected_bbox
        assert annotation_bboxes["source_grid"] == [float(value) for value in render["board_bbox_px"]]

        option_specs = execution["option_specs"]
        assert [str(option["option_label"]) for option in option_specs] == ["A", "B", "C", "D", "E", "F"]
        assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
        winning_option = next(option for option in option_specs if bool(option["is_correct"]))
        assert str(winning_option["option_label"]) == str(out.answer_gt.value)
        assert str(winning_option["object_type"]) == str(execution["answer_object_type"])

        if str(expected_rule) in {"row_uniqueness", "row_column_uniqueness_rule"}:
            query_row = int(execution["query_row_index"])
            assert sorted(board_values[query_row]) == sorted(symbol_pool)
        if str(expected_rule) in {"column_uniqueness", "row_column_uniqueness_rule"}:
            query_col = int(execution["query_col_index"])
            assert sorted(_column_values(board_values, query_col)) == sorted(symbol_pool)


def test_logic_grid_king_non_touch_contract_matches_selected_option() -> None:
    task = PuzzlesLogicGridKingNonTouchLabelTask()
    out = task.generate(24820, params={"query_id": SINGLE_QUERY_ID}, max_attempts=10)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    annotation_bboxes = {
        str(key): [float(value) for value in bbox]
        for key, bbox in out.annotation_gt.value.items()
    }
    board_values = [[str(value) for value in row] for row in execution["board_values"]]
    row_index = int(execution["query_row_index"])
    col_index = int(execution["query_col_index"])
    answer_type = str(execution["answer_object_type"])

    assert str(out.query_id) == SINGLE_QUERY_ID
    assert task.supported_query_ids == (SINGLE_QUERY_ID,)
    assert str(execution["semantic_rule"]) == "king_non_touch"
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "bbox_map"
    assert set(annotation_bboxes) == {"source_grid", "selected_option"}
    assert 3 <= int(execution["board_size"]) <= 5
    assert int(execution["option_count"]) == 6
    assert str(trace["query_spec"]["prompt_variant"]["query_key"]) == "king_non_touch"
    assert trace["projected_annotation"]["bbox_map"] == annotation_bboxes
    assert annotation_bboxes["source_grid"] == [float(value) for value in render["board_bbox_px"]]
    assert annotation_bboxes["selected_option"] == [
        float(value)
        for value in render_map["option_panel_bboxes_px"][str(execution["correct_option_panel_id"])]
    ]
    assert answer_type not in set(_king_neighbors(board_values, row_index, col_index))
    assert [answer_type] == [str(value) for value in execution["valid_option_object_types"]]
    assert str(out.answer_gt.value) == str(execution["answer_option_label"])


def test_logic_grid_prompt_examples_match_selected_variants() -> None:
    cases = (
        (
            PuzzlesLogicGridUniquenessCompletionLabelTask(),
            {"query_id": AXIS_UNIQUENESS_QUERY, "uniqueness_axis": "row"},
        ),
        (
            PuzzlesLogicGridUniquenessCompletionLabelTask(),
            {"query_id": ROW_AND_COLUMN_UNIQUENESS_QUERY},
        ),
        (
            PuzzlesLogicGridKingNonTouchLabelTask(),
            {"query_id": SINGLE_QUERY_ID},
        ),
    )
    for index, (task, params) in enumerate(cases, start=24920):
        out = task.generate(index, params=params, max_attempts=10)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == {
            "annotation": {
                "source_grid": [150, 90, 580, 520],
                "selected_option": [620, 690, 760, 860],
            },
            "answer": "C",
        }
        assert answer_only == {"answer": "C"}


def test_logic_grid_tasks_are_deterministic() -> None:
    cases = (
        (
            PuzzlesLogicGridUniquenessCompletionLabelTask(),
            {"query_id": ROW_AND_COLUMN_UNIQUENESS_QUERY, "scene_variant": "logic_card"},
        ),
        (
            PuzzlesLogicGridKingNonTouchLabelTask(),
            {"query_id": SINGLE_QUERY_ID, "scene_variant": "logic_outline"},
        ),
    )
    for task, params in cases:
        out_a = task.generate(25040, params=params, max_attempts=10)
        out_b = task.generate(25040, params=params, max_attempts=10)
        assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
        assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
        assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
        assert out_a.prompt == out_b.prompt
        assert out_a.image.tobytes() == out_b.image.tobytes()


def test_logic_grid_answer_labels_and_board_sizes_have_support() -> None:
    task = PuzzlesLogicGridUniquenessCompletionLabelTask()
    observed_letters: Counter[str] = Counter()
    observed_sizes: Counter[int] = Counter()
    for local_index in range(72):
        out = task.generate(
            25120 + local_index,
            params={"query_id": AXIS_UNIQUENESS_QUERY, "uniqueness_axis": "column"},
            max_attempts=10,
        )
        observed_letters[str(out.answer_gt.value)] += 1
        observed_sizes[int(out.trace_payload["execution_trace"]["board_size"])] += 1
    assert set(observed_letters) == {"A", "B", "C", "D", "E", "F"}
    assert set(observed_sizes) == {5, 6, 7}


def test_logic_grid_supports_seven_by_seven_without_canvas_overflow() -> None:
    task = PuzzlesLogicGridUniquenessCompletionLabelTask()
    out = task.generate(
        25220,
        params={
            "query_id": ROW_AND_COLUMN_UNIQUENESS_QUERY,
            "scene_variant": "logic_outline",
            "board_size": 7,
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
