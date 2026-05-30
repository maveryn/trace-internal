"""Task-group config tests for the games dots-and-boxes capture-count task."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_dots_and_boxes_capture_count_task_group_defaults_present() -> None:
    defaults = get_task_group_defaults("games", "dots_and_boxes")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        defaults,
        task_id="task_games__dots_and_boxes__capture_move_count",
    )
    assert generation["scene_variant_weights"] == {"single_board": 1.0}
    assert generation["query_id_weights"] == {
        "three_sided_box_count": 1.0,
        "capture_move_count": 1.0,
        "highlighted_candidate_capture_count": 1.0,
    }
    assert generation["capture_move_query_id_weights"] == {
        "capture_move_count": 1.0,
        "highlighted_candidate_capture_count": 1.0,
    }
    assert set(generation["style_variant_weights"].keys()) == {
        "classic",
        "soft",
        "outlined",
        "notebook",
        "slate",
        "wood_panel",
    }
    assert generation["three_sided_box_count_support"] == [0, 1, 2, 3, 4, 5]
    assert generation["capture_move_count_support"] == [0, 1, 2, 3, 4, 5]
    assert generation["highlighted_candidate_capture_count_support"] == [0, 1, 2, 3, 4, 5]
    assert generation["box_rows_support"] == [3, 4]
    assert generation["box_cols_support"] == [3, 4]
    assert generation["candidate_edge_count_support"] == [5, 6, 7, 8]
    assert generation["balanced_target_answer_sampling"] is True
    assert generation["balanced_board_shape_sampling"] is True
    assert generation["balanced_candidate_edge_count_sampling"] is True
    assert generation["balanced_capture_move_query_id_sampling"] is True
    assert int(rendering["board_width_px"]) > 0
    assert int(rendering["board_height_px"]) > 0
    assert rendering["dynamic_canvas_size_enabled"] is True
    assert int(rendering["canvas_min_width_px"]) >= 620
    assert int(rendering["canvas_min_height_px"]) >= 520
    assert str(prompt["bundle_id"]) == "games_dots_and_boxes_v0"
    assert str(prompt["scene_key"]) == "visible_dots_and_boxes_board"
    assert str(prompt["task_key"]) == "dots_and_boxes_capture_query"
    assert str(prompt["object_description_single_board"]) == "a dots-and-boxes grid with some edges already drawn"
    assert "answer_hint_capture_move_count" in prompt
    assert "evidence_hint_highlighted_candidate_capture_count" in prompt
    assert "some questions" not in str(prompt["object_description_single_board"])
