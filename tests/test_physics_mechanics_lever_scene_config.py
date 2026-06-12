"""Config regression tests for physics mechanics lever-balance defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_mechanics_lever_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_scene_defaults("physics", "mechanics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_mechanics_lever_balance_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

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

    assert set(generation["query_id_weights"].keys()) == {"side_torque", "missing_weight_to_balance"}

    assert set(generation["torque_side_weights"].keys()) == {"left", "right"}

    assert list(generation["distance_support"]) == list(range(1, 9))

    assert list(generation["missing_weight_support"]) == list(range(1, 7))

    assert int(generation["max_side_weights"]) == 4

    assert int(generation["missing_weight_max_side_weights"]) == 2

    assert set(generation["missing_weight_scene_variant_weights"].keys()) == {"textured_beam"}

    assert int(rendering["canvas_width"]) == 1280

    assert int(rendering["beam_width_px"]) > 0

    assert list(rendering["distance_support"]) == list(range(1, 9))

    assert int(rendering["weight_box_width_px"]) > 0
    assert bool(rendering["layout_jitter_enabled"]) is True

    assert str(prompt["bundle_id"]) == "physics_mechanics_v0"

    assert "textured lever beam" in str(prompt["object_description_textured_beam"])

    assert "queried side" in str(prompt["annotation_hint_torque"])

    assert "known weight blocks" in str(prompt["annotation_hint_missing_weight"])

    assert "marked `?` weight" in str(prompt["annotation_hint_missing_weight"])
