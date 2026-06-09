"""Contract tests for Ultimate Tic-Tac-Toe game tasks."""

from __future__ import annotations

import json
from pathlib import Path

import trace.tasks  # noqa: F401
from trace.core.task_group_config import get_task_group_defaults
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import create_task, list_default_task_ids
from trace.tasks.games.ultimate_tictactoe.board_tasks import _immediate_winning_cells
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_ultimate_tictactoe_defaults_and_prompt_bundle() -> None:
    cfg = get_task_group_defaults("games", "ultimate_tictactoe")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg)

    assert set(generation["status_count_query_id_weights"].keys()) == {
        "x_won_board_count",
        "o_won_board_count",
        "neither_won_board_count",
        "drawn_board_count",
    }
    assert set(generation["local_tactic_query_id_weights"].keys()) == {
        "x_winning_move_label",
        "o_winning_move_label",
        "x_blocking_move_label",
        "o_blocking_move_label",
    }
    assert set(generation["macro_threat_query_id_weights"].keys()) == {
        "x_immediate_win_board_count",
        "o_immediate_win_board_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {
        "classic_grid",
        "soft_marker",
        "paper_grid",
        "neon_board",
        "tournament_board",
    }
    assert int(rendering["canvas_width"]) == 820
    assert int(rendering["canvas_height"]) == 820
    assert bool(rendering["dynamic_canvas_size_enabled"])
    assert float(rendering["unit_size_scale_max"]) / float(rendering["unit_size_scale_min"]) >= 2.0
    assert list(generation["macro_threat_board_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert str(prompt["bundle_id"]) == "games_ultimate_tictactoe_v0"


def test_games_ultimate_tictactoe_prompt_bundle_has_queries() -> None:
    bundle = json.loads(
        Path("prompts/games/ultimate_tictactoe/games_ultimate_tictactoe_v0.json").read_text(encoding="utf-8")
    )
    assert set(bundle["query_templates"].keys()) == {
        "x_won_board_count",
        "o_won_board_count",
        "neither_won_board_count",
        "drawn_board_count",
        "x_winning_move_label",
        "o_winning_move_label",
        "x_blocking_move_label",
        "o_blocking_move_label",
        "x_immediate_win_board_count",
        "o_immediate_win_board_count",
    }


def test_games_ultimate_tictactoe_registry_and_taxonomy() -> None:
    ids = set(list_default_task_ids())
    for task_id in (
        "task_games__ultimate_tictactoe__small_board_status_count",
        "task_games__ultimate_tictactoe__line_completion_move_label",
        "task_games__ultimate_tictactoe__macro_threat_board_count",
    ):
        assert task_id in ids
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "games"
        assert taxonomy.scene_id == "ultimate_tictactoe"
        assert taxonomy.source_task_group == "ultimate_tictactoe"


def test_games_ultimate_tictactoe_status_count_matches_trace() -> None:
    out = create_task("task_games__ultimate_tictactoe__small_board_status_count").generate(
        81021,
        params={"query_id": "x_won_board_count", "target_answer": 3},
        max_attempts=500,
    )
    boards = out.trace_payload["execution_trace"]["small_boards"]
    matching = [board for board in boards if board["status"] == "X_won"]

    assert out.query_id == "x_won_board_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert len(matching) == 3
    assert len(out.annotation_gt.value) == 3
    assert out.trace_payload["projected_annotation"]["type"] == "bbox_set"


def test_games_ultimate_tictactoe_macro_threat_count_matches_trace() -> None:
    out = create_task("task_games__ultimate_tictactoe__macro_threat_board_count").generate(
        81041,
        params={"query_id": "x_immediate_win_board_count", "target_answer": 4},
        max_attempts=500,
    )
    boards = out.trace_payload["execution_trace"]["small_boards"]
    matching = [
        board
        for board in boards
        if board["status"] == "open" and _immediate_winning_cells(board["cells"], "X")
    ]

    assert out.query_id == "x_immediate_win_board_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert len(matching) == 4
    assert len(out.annotation_gt.value) == 4
    assert len(out.trace_payload["execution_trace"]["matching_small_boards"]) == 4
    assert out.trace_payload["projected_annotation"]["type"] == "bbox_set"
    assert out.trace_payload["render_spec"]["ultimate_tictactoe_board_style"]["style_variant"]
    assert out.trace_payload["render_spec"]["text_style"]["font_family"]


def test_games_ultimate_tictactoe_local_tactic_has_unique_winning_cell() -> None:
    out = create_task("task_games__ultimate_tictactoe__line_completion_move_label").generate(
        81031,
        params={"query_id": "o_blocking_move_label", "answer_option_index": 2},
        max_attempts=500,
    )
    trace = out.trace_payload["execution_trace"]
    params = out.trace_payload["query_spec"]["params"]

    assert out.query_id == "o_blocking_move_label"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "C"
    assert trace["answer_cell"] in trace["option_cells"]
    assert trace["answer_cell"] == params["answer_cell"]
    assert len(trace["support_cells"]) == 2
    assert len(out.annotation_gt.value) == 3
    assert out.trace_payload["projected_annotation"]["type"] == "bbox_set"
