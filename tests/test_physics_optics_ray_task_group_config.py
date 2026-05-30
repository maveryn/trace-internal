"""Config regression tests for physics optics defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_optics_ray_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_task_group_defaults("physics", "optics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_optics_ray_trace_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert bool(generation["balanced_accent_color_name_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {
        "single_mirror",
        "double_mirror",
        "triple_mirror",
        "quad_mirror",
        "five_mirror",
    }

    assert set(generation["query_id_weights"].keys()) == {
        "bounce_count",
        "target_hit_count",
    }

    assert list(generation["bounce_count_support_single_mirror"]) == [0, 1]

    assert list(generation["bounce_count_support_double_mirror"]) == [0, 1, 2]

    assert list(generation["bounce_count_support_triple_mirror"]) == [0, 1, 2, 3]

    assert list(generation["bounce_count_support_quad_mirror"]) == [0, 1, 2, 3, 4]

    assert list(generation["bounce_count_support_five_mirror"]) == [1, 2, 3, 4, 5]

    assert list(generation["target_hit_count_support"]) == [1, 2, 3, 4, 5]

    assert int(generation["target_count_max"]) == 5

    assert int(rendering["board_cols"]) == 8

    assert int(rendering["cell_size_px"]) > 0

    assert int(rendering["mirror_width_px"]) == 7

    assert int(rendering["mirror_padding_px"]) == 6

    assert int(rendering["target_radius_px"]) == 18

    assert bool(rendering["layout_jitter_enabled"]) is True

    assert int(rendering["layout_jitter_min_margin_px"]) == 8

    assert str(prompt["bundle_id"]) == "physics_optics_v0"

    assert "graph-paper" in str(prompt["object_description_double_mirror"])

    assert "four diagonal mirrors" in str(prompt["object_description_quad_mirror"])

    assert "five diagonal mirrors" in str(prompt["object_description_five_mirror"])

    assert "image pixel points" in str(prompt["evidence_hint_bounce_count"])
