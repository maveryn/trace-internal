"""Contract tests for Ludo-board games tasks."""

from __future__ import annotations

import json
from pathlib import Path

import trace.tasks  # noqa: F401
from trace.core.task_group_config import get_task_group_defaults
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.ludo_board.board_tasks import (
    CAPTURE_ROLL_QUERY_ID,
    CAPTURE_ROLL_TASK_ID,
    FLOW_ARROW_CELLS,
    FLOW_ARROW_SPECS,
    HOME_LANES,
    MAIN_PATH,
    MOVE_RESULT_QUERY_ID,
    MOVE_RESULT_TASK_ID,
    OPTION_LABELS,
    PLAYER_COLORS,
    START_COORDS,
    WINNING_ROLL_QUERY_ID,
    WINNING_ROLL_TASK_ID,
    _roll_sequence_for_total,
    _roll_option_text,
    _route_for_color,
)
from trace.tasks.registry import create_task, list_default_task_ids
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_ludo_board_defaults_and_prompt_bundle() -> None:
    cfg = get_task_group_defaults("games", "ludo_board")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg)

    assert set(generation["style_variant_weights"].keys()) == {
        "classic_bright",
        "ivory_board",
        "slate_table",
        "soft_plastic",
        "arcade_gloss",
    }
    assert set(generation["query_color_weights"].keys()) == set(PLAYER_COLORS)
    assert list(generation["winning_roll_support"]) == [1, 2, 3, 4, 5]
    assert list(generation["capture_distance_support"]) == list(range(1, 12))
    assert list(generation["move_roll_total_support"]) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17]
    assert list(generation["answer_option_label_weights"].keys()) == list(OPTION_LABELS)
    assert int(rendering["cell_size_min_px"]) == 36
    assert int(rendering["cell_size_max_px"]) == 48
    assert bool(rendering["flow_arrow_enabled"]) is True
    assert int(rendering["flow_arrow_width_px"]) == 2
    assert str(prompt["bundle_id"]) == "games_ludo_board_v0"


def test_games_ludo_board_prompt_bundle_has_queries() -> None:
    bundle = json.loads(Path("prompts/games/ludo_board/games_ludo_board_v0.json").read_text(encoding="utf-8"))

    assert set(bundle["query_templates"].keys()) == {
        WINNING_ROLL_QUERY_ID,
        CAPTURE_ROLL_QUERY_ID,
        MOVE_RESULT_QUERY_ID,
    }
    assert bundle["required_slots_by_key"][f"query:{WINNING_ROLL_QUERY_ID}"] == ["exact_finish_rule_text"]
    assert bundle["required_slots_by_key"][f"query:{CAPTURE_ROLL_QUERY_ID}"] == ["capture_option_rule_text"]
    assert bundle["required_slots_by_key"][f"query:{MOVE_RESULT_QUERY_ID}"] == ["move_sequence_rule_text"]
    assert bool(bundle["allow_empty_task_templates"])


def test_games_ludo_board_path_and_roll_encoding() -> None:
    assert len(MAIN_PATH) == 52
    assert len(set(MAIN_PATH)) == 52
    for color, start in START_COORDS.items():
        assert start in MAIN_PATH
        assert len(HOME_LANES[color]) == 5
    assert FLOW_ARROW_SPECS == (
        ((6, 2), (6, 3), "start_forward_red"),
        ((2, 8), (3, 8), "start_forward_green"),
        ((8, 12), (8, 11), "start_forward_yellow"),
        ((12, 6), (11, 6), "start_forward_blue"),
        ((6, 5), (5, 6), "corner_turn_top_left"),
        ((5, 8), (6, 9), "corner_turn_top_right"),
        ((8, 9), (9, 8), "corner_turn_bottom_right"),
        ((9, 6), (8, 5), "corner_turn_bottom_left"),
        ((7, 0), (7, 1), "home_entry_red"),
        ((0, 7), (1, 7), "home_entry_green"),
        ((7, 14), (7, 13), "home_entry_yellow"),
        ((14, 7), (13, 7), "home_entry_blue"),
    )
    playable_cells = set(MAIN_PATH)
    for lane in HOME_LANES.values():
        playable_cells.update(lane)
    assert len(FLOW_ARROW_SPECS) == 12
    assert len(FLOW_ARROW_CELLS) == 24
    assert all(coord in playable_cells for coord in FLOW_ARROW_CELLS)
    for start, end, _role in FLOW_ARROW_SPECS:
        assert max(abs(int(start[0]) - int(end[0])), abs(int(start[1]) - int(end[1]))) == 1

    assert _roll_option_text(1) == "1"
    assert _roll_option_text(6) == "6"
    assert _roll_option_text(7) == "6 then 1"
    assert _roll_option_text(11) == "6 then 5"
    assert _roll_sequence_for_total(1) == (1,)
    assert _roll_sequence_for_total(6) == (6,)
    assert _roll_sequence_for_total(7) == (6, 1)
    assert _roll_sequence_for_total(11) == (6, 5)
    assert _roll_sequence_for_total(13) == (6, 6, 1)
    assert _roll_sequence_for_total(17) == (6, 6, 5)


def test_games_ludo_board_registry_and_taxonomy() -> None:
    default_ids = set(list_default_task_ids())
    assert WINNING_ROLL_TASK_ID in default_ids
    assert CAPTURE_ROLL_TASK_ID in default_ids
    assert MOVE_RESULT_TASK_ID in default_ids
    for task_id in (WINNING_ROLL_TASK_ID, CAPTURE_ROLL_TASK_ID, MOVE_RESULT_TASK_ID):
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "games"
        assert taxonomy.scene_id == "ludo_board"
        assert taxonomy.source_task_group == "ludo_board"


def test_games_ludo_board_winning_roll_answer_matches_trace() -> None:
    for roll in (1, 5):
        out = create_task(WINNING_ROLL_TASK_ID).generate(
            980100 + roll,
            params={"winning_roll": roll, "query_color": "blue"},
            max_attempts=100,
        )
        execution = out.trace_payload["execution_trace"]

        assert out.scene_id == "ludo_board"
        assert out.query_id == WINNING_ROLL_QUERY_ID
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == roll
        assert execution["winning_roll"] == roll
        assert execution["query_color"] == "blue"
        assert execution["token_coords_by_color"]["blue"] == list(HOME_LANES["blue"][5 - roll])
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert set(out.annotation_gt.value.keys()) == {"token", "finish"}
        assert out.trace_payload["projected_annotation"]["type"] == "keyed_bbox_map"
        assert len(out.trace_payload["render_map"]["flow_arrow_markers_px"]) == len(FLOW_ARROW_SPECS)
        assert set(out.trace_payload["render_map"]["flow_arrow_markers_px"][0]) >= {"start_coord", "end_coord", "role"}


def test_games_ludo_board_capture_option_answer_matches_trace() -> None:
    for distance in (1, 6, 7, 11):
        out = create_task(CAPTURE_ROLL_TASK_ID).generate(
            981100 + distance,
            params={
                "capture_distance": distance,
                "query_color": "red",
                "target_color": "green",
                "answer_option_label": "F",
                "option_count": 6,
            },
            max_attempts=100,
        )
        execution = out.trace_payload["execution_trace"]
        correct_options = [option for option in execution["options"] if int(option["distance"]) == distance]

        assert out.scene_id == "ludo_board"
        assert out.query_id == CAPTURE_ROLL_QUERY_ID
        assert out.answer_gt.type == "string"
        assert out.answer_gt.value == "F"
        assert execution["capture_distance"] == distance
        assert execution["answer"] == "F"
        assert correct_options == [{"label": "F", "distance": distance, "text": _roll_option_text(distance)}]
        assert len(execution["options"]) == 6
        assert len(out.trace_payload["render_map"]["flow_arrow_markers_px"]) == len(FLOW_ARROW_SPECS)
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert set(out.annotation_gt.value.keys()) == {"mover_token", "target_token"}
        assert set(out.trace_payload["projected_annotation"]["pixel_keyed_bbox_map"].keys()) == {
            "mover_token",
            "target_token",
        }


def test_games_ludo_board_move_result_answer_matches_trace() -> None:
    for total in (1, 7, 13, 17):
        out = create_task(MOVE_RESULT_TASK_ID).generate(
            982100 + total,
            params={
                "move_roll_total": total,
                "query_color": "blue",
                "answer_option_label": "D",
            },
            max_attempts=100,
        )
        execution = out.trace_payload["execution_trace"]
        route = _route_for_color("blue")
        start_coord = tuple(execution["token_coords_by_color"]["blue"])
        start_index = route.index(start_coord)
        expected_destination = tuple(route[start_index + total])
        destination_options = {
            str(option["label"]): tuple(option["coord"])
            for option in execution["destination_options"]
        }
        token_coords = {tuple(coord) for coord in execution["token_coords_by_color"].values()}

        assert out.scene_id == "ludo_board"
        assert out.query_id == MOVE_RESULT_QUERY_ID
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value == "D"
        assert execution["move_roll_total"] == total
        assert execution["roll_sequence"] == list(_roll_sequence_for_total(total))
        assert execution["answer"] == "D"
        assert destination_options["D"] == expected_destination
        assert len(destination_options) == len(execution["destination_options"])
        assert len(set(destination_options.values())) == len(execution["destination_options"])
        assert not set(destination_options.values()) & token_coords
        assert set(out.annotation_gt.value.keys()) == {"moving_token", "roll_sequence", "destination_cell"}
        assert set(out.trace_payload["projected_annotation"]["pixel_keyed_bbox_map"].keys()) == {
            "moving_token",
            "roll_sequence",
            "destination_cell",
        }
        assert set(out.trace_payload["render_map"]["destination_option_cell_bboxes_px"].keys()) == set(destination_options)
        assert out.trace_payload["render_map"]["roll_sequence_px"]["values"] == list(_roll_sequence_for_total(total))
