"""Config regression tests for geometry coordinate-relation defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_geometry_coordinate_relation_task_overrides_expose_scene_query_axes() -> None:
    cfg = get_task_group_defaults("geometry", "coordinate")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="geometry_coordinate_relation_base",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {
        "segment_set",
        "line_points",
        "quadrant_points",
        "polygon_lattice",
    }
    assert set(generation["query_variant_weights"].keys()) == {
        "parallel_count",
        "perpendicular_count",
        "collinear_count",
        "same_quadrant_count",
        "point_in_shape_count",
    }
    assert int(generation["segment_candidate_count"]) == 6
    assert int(generation["segment_endpoint_abs_max"]) == 8
    assert list(generation["segment_target_support"]) == [0, 1, 2, 3, 4, 5, 6]
    assert int(generation["collinear_candidate_count"]) == 8
    assert int(generation["collinear_point_abs_max"]) == 8
    assert list(generation["collinear_target_support"]) == [0, 1, 2, 3, 4, 5, 6]
    assert list(generation["same_quadrant_target_support"]) == [0, 1, 2, 3, 4, 5, 6]
    assert list(generation["point_in_shape_target_support"]) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert str(prompt["bundle_id"]) == "geometry_coordinate_v0"
    assert int(rendering["line_width"]) > 0
