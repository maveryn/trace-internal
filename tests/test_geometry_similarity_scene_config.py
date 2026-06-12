"""Config regression tests for geometry similarity defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_geometry_similarity_task_overrides_expose_scene_query_and_count_axes() -> None:
    cfg = get_scene_defaults("geometry", "similarity")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="geometry_similarity_count_base",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"triangle", "quadrilateral"}
    assert set(generation["query_id_weights"].keys()) == {"congruent_count", "similar_count"}
    assert len(generation["candidate_label_pool"]) == 5
    assert len(generation["candidate_slots"]) == 5
    assert list(generation["target_count_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["similar_scale_support"]) == [1, 2]
    assert int(rendering["line_width"]) > 0
    assert str(prompt["bundle_id"]) == "geometry_similarity_v0"
