"""Task-group config tests for the games dots-and-boxes capture-count task."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_dots_and_boxes_capture_count_task_group_defaults_present() -> None:
    defaults = get_task_group_defaults("games", "dots_and_boxes")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        defaults,
        task_id="task_games_dots_and_boxes_capture_count",
    )
    assert generation["scene_variant_weights"] == {"single_board": 1.0}
    assert generation["query_variant_weights"] == {"forced_turn_capture_count": 1.0}
    assert generation["capture_count_support"] == [1, 2, 3, 4, 5, 6]
    assert generation["balanced_target_answer_sampling"] is True
    assert int(rendering["board_width_px"]) > 0
    assert int(rendering["board_height_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_dots_and_boxes_v1"
    assert str(prompt["task_family_key"]) == "visible_dots_and_boxes_board"
    assert str(prompt["task_key"]) == "dots_and_boxes_capture_query"
    assert "forced_turn_rule_text" in prompt
