"""Config regression tests for consolidated geometry task ids."""

from __future__ import annotations

import pytest

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


@pytest.mark.parametrize(
    ("task_group", "task_id", "expected_query_variants"),
    (
        ("measurement", "task_geometry_measurement_value", {"angle", "length", "area", "perimeter", "slope"}),
        (
            "comparison",
            "task_geometry_comparison_value",
            {
                "largest_angle",
                "smallest_angle",
                "largest_length",
                "smallest_length",
                "largest_area",
                "smallest_area",
                "largest_perimeter",
                "smallest_perimeter",
            },
        ),
        (
            "counting",
            "task_geometry_counting_value",
            {
                "acute_angle",
                "right_angle",
                "obtuse_angle",
                "triangle",
                "quadrilateral",
                "pentagon",
                "hexagon",
                "circle",
                "ellipse",
                "convex_polygon",
                "concave_polygon",
            },
        ),
        ("analytical_2d", "task_geometry_analytical_2d_value", {"area", "length", "perimeter", "composite_area"}),
        ("analytical_3d", "task_geometry_analytical_3d_value", {"volume", "surface_area"}),
    ),
)
def test_consolidated_geometry_task_overrides_expose_scene_and_query_axes(
    task_group: str,
    task_id: str,
    expected_query_variants: set[str],
) -> None:
    cfg = get_task_group_defaults("geometry", task_group)
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg, task_id=task_id)

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert set(generation["query_variant_weights"].keys()).issuperset(expected_query_variants)
    assert generation["scene_variant_weights"]
    assert int(rendering["line_width"]) > 0
    assert str(prompt["task_family_key"]).strip()
    assert str(prompt["json_output_contract"]).strip()
