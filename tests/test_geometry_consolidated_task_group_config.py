"""Config regression tests for consolidated geometry task ids."""

from __future__ import annotations

import pytest

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


@pytest.mark.parametrize(
    ("task_group", "task_id", "expected_query_variants"),
    (
        ("measurement", "geometry_measurement_value_base", {"angle", "area", "perimeter", "slope"}),
        (
            "comparison",
            "geometry_comparison_value_base",
            {
                "angle_extremum",
                "length_extremum",
                "area_extremum",
                "perimeter_extremum",
            },
        ),
        (
            "counting",
            "geometry_counting_value_base",
            {
                "angle_type_count",
                "triangle_type_count",
                "quadrilateral_type_count",
                "shape_type_count",
                "polygon_convexity_count",
            },
        ),
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
    if task_id == "geometry_comparison_value_base":
        assert bool(generation["balanced_extremum_direction_sampling"]) is True
        assert set(generation["extremum_direction_weights"].keys()) == {"largest", "smallest"}
    assert set(generation["query_variant_weights"].keys()).issuperset(expected_query_variants)
    assert generation["scene_variant_weights"]
    assert int(rendering["line_width"]) > 0
    assert str(prompt["scene_key"]).strip()
    assert str(prompt["json_output_contract"]).strip()
