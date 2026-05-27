"""Config regression tests for physics mechanics pulley defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_mechanics_pulley_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_task_group_defaults("physics", "mechanics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_physics__pulley__pulley_mechanical_advantage",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_variant_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert bool(generation["balanced_accent_color_name_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {
        "open_block",
        "compact_block",
        "tall_block",
    }

    assert set(generation["query_variant_weights"].keys()) == {
        "force_relation",
    }

    assert set(generation["solve_for_weights"].keys()) == {"effort_force", "load_force"}

    assert bool(generation["balanced_solve_for_sampling"]) is True

    assert bool(generation["balanced_connected_support_count_sampling"]) is False

    assert bool(generation["balanced_disconnected_segment_count_sampling"]) is False

    assert list(generation["connected_support_count_support"]) == [2, 3, 4, 5, 6]

    assert list(generation["disconnected_segment_count_support"]) == [0, 1, 2, 3, 4]

    assert list(generation["effort_force_support"]) == list(range(4, 19))

    assert int(min(generation["load_force_support"])) == 8

    assert int(max(generation["load_force_support"])) == 108

    assert int(generation["effort_force_min"]) == 4

    assert int(generation["effort_force_max"]) == 18

    assert int(rendering["canvas_width"]) == 1280

    assert int(rendering["canvas_height"]) == 760

    assert int(rendering["support_segment_gap_px"]) > int(rendering["pulley_radius_px"])

    assert int(rendering["load_width_px"]) > 0

    assert str(prompt["bundle_id"]) == "physics_mechanics_v0"

    assert "one open" in str(prompt["object_description_open_block"])

    assert "optional cut non-supporting strands" in str(prompt["object_description_open_block"])

    assert "marked `?` effort label" in str(prompt["evidence_hint_effort_force"])

    assert "marked `?` load label" in str(prompt["evidence_hint_load_force"])

    assert "exclude cut strands" in str(prompt["evidence_hint_load_force"])
