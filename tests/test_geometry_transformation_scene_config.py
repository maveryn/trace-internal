"""Config regression tests for geometry transformation defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_geometry_transformation_task_overrides_expose_scene_and_query_axes() -> None:
    cfg = get_scene_defaults("geometry", "transformation")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="geometry_transformation_match_base",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"triangle", "quadrilateral"}
    assert set(generation["query_id_weights"].keys()) == {
        "translation_match",
        "reflection_match",
        "rotation_match",
    }
    assert len(generation["candidate_label_pool"]) == 6
    assert len(generation["candidate_slots"]) == 6
    assert len(generation["translation_vectors"]) >= 3
    assert int(rendering["line_width"]) > 0
    assert str(prompt["bundle_id"]) == "geometry_transformation_v0"
