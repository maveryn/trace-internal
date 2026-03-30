"""Config regression tests for physics mechanics defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_mechanics_force_diagram_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_task_group_defaults("physics", "mechanics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_physics_mechanics_force_diagram",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_target_force_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {
        "free_body_box",
        "surface_block",
        "textured_block",
    }
    assert set(generation["query_variant_weights"].keys()) == {
        "net_horizontal_force",
        "net_vertical_force",
        "balancing_force_horizontal",
        "balancing_force_vertical",
    }
    assert list(generation["target_force_support"]) == list(range(0, 13))
    assert list(generation["balancing_force_support"]) == list(range(1, 13))
    assert int(rendering["object_base_side_min_px"]) >= 140
    assert int(rendering["object_min_side_px"]) >= 104
    assert int(rendering["arrow_length_px"]) > 0
    assert int(rendering["label_font_size_px"]) > 0
    assert str(prompt["bundle_id"]) == "physics_mechanics_v1"
    assert "textured block" in str(prompt["object_description_textured_block"])
    assert "force arrows" in str(prompt["evidence_hint"])
