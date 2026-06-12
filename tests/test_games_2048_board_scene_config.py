"""Config regression tests for games 2048-board defaults."""

from __future__ import annotations

import json
from importlib import import_module

from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults


SUPPORTED_2048_STYLE_VARIANTS = import_module(
    "trace.tasks.games.2048.shared.state"
).SUPPORTED_2048_STYLE_VARIANTS


def test_games_2048_board_defaults_expose_query_style_move_and_answer_axes() -> None:
    generation, rendering, prompt = load_scene_generation_rendering_prompt_defaults(
        "games",
        "2048",
        task_id="task_games__2048__merge_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_style_variant_sampling"]) is True
    assert bool(generation["balanced_move_direction_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert "balanced_query_id_sampling" not in generation
    assert "query_id_weights" not in generation
    assert set(generation["scene_variant_weights"].keys()) == {"standard_board"}
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_2048_STYLE_VARIANTS)
    assert set(generation["move_direction_weights"].keys()) == {"up", "down", "left", "right"}
    assert list(generation["merge_count_support"]) == [0, 1, 2, 3, 4]
    assert "score_value_support" not in generation
    assert "max_tile_value_support" not in generation
    assert "result_board_label_support" not in generation
    assert int(rendering["canvas_width"]) == 900
    assert int(rendering["board_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_2048_v1"
    assert str(prompt["scene_key"]) == "visible_2048_board"
    assert str(prompt["task_key"]) == "twenty_forty_eight_query"
    assert "object_description_standard_board" not in prompt
    assert "move_rule_text" not in prompt
    assert "annotation_hint_move_result_board_label" not in prompt


def test_games_2048_generate_task_samples_omits_scene_id_for_scene_package_task(tmp_path) -> None:
    from scripts.generate_task_samples import _generate_samples_for_task

    task_id = "task_games__2048__merge_count"
    summary, rows = _generate_samples_for_task(
        task_id=task_id,
        out_root=tmp_path,
        count=1,
        base_seed=2048,
        max_attempts_per_instance=128,
        image_format="png",
        params={},
    )
    data_path = tmp_path / "games" / "2048" / task_id / "data" / "000000.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    assert summary["domain"] == "games"
    assert summary["scene_id"] == "2048"
    assert summary["task"] == task_id
    assert summary.get("scene_id")
    assert rows and rows[0].get("scene_id")
    assert payload["domain"] == "games"
    assert payload["scene_id"] == "2048"
    assert payload["task"] == task_id
    assert payload.get("scene_id")
