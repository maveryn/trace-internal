"""Config regression tests for physics mechanics spring-extension defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_mechanics_spring_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_task_group_defaults("physics", "mechanics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_mechanics_spring_extension_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert bool(generation["balanced_accent_color_name_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {
        "paired_springs",
        "staggered_springs",
        "textured_spring",
    }

    assert set(generation["query_id_weights"].keys()) == {"missing_value", "extension_difference"}

    assert set(generation["solve_for_weights"].keys()) == {"weight", "extension"}

    assert list(generation["scale_factor_support"]) == [1, 2, 3]

    assert list(generation["extension_difference_scale_factor_support"]) == [2]

    assert int(generation["weight_value_max"]) == 12

    assert list(generation["missing_weight_support"]) == [1, 2, 3, 4, 5, 6, 7, 8]

    assert list(generation["missing_extension_support"]) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    assert int(generation["extension_value_max"]) == 14

    assert list(generation["extension_difference_support"]) == [2, 4, 8, 10, 12]


    assert int(rendering["canvas_width"]) == 980

    assert int(rendering["canvas_height"]) == 660

    assert int(rendering["card_width_px"]) == 304

    assert int(rendering["ruler_value_max"]) == 14

    assert int(rendering["weight_box_width_px"]) == 78


    assert str(prompt["bundle_id"]) == "physics_mechanics_v0"

    assert str(prompt["scene_key"]) == "paired_spring_diagram"

    assert str(prompt["task_key"]) == "spring_extension_query"

    assert "identical hanging springs" in str(prompt["object_description_paired_springs"])

    assert "red `?` extension tag" in str(prompt["evidence_hint_missing_extension"])
