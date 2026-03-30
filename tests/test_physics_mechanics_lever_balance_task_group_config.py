"""Config regression tests for physics mechanics lever-balance defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_mechanics_lever_balance_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_task_group_defaults("physics", "mechanics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_physics_mechanics_lever_balance",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_accent_color_name_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {
        "center_fulcrum",
        "offset_fulcrum",
        "textured_beam",
    }
    assert set(generation["accent_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert set(generation["query_variant_weights"].keys()) == {
        "left_torque",
        "right_torque",
        "missing_weight_to_balance",
    }
    assert list(generation["distance_support"]) == [1, 2, 3, 4]
    assert list(generation["missing_weight_support"]) == list(range(1, 13))
    assert int(rendering["beam_width_px"]) > 0
    assert int(rendering["weight_box_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "physics_mechanics_v1"
    assert "textured beam" in str(prompt["object_description_textured_beam"])
    assert "queried side" in str(prompt["evidence_hint_torque"])
    assert "`?` weight" in str(prompt["evidence_hint_missing_weight"])
