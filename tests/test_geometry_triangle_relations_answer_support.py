from __future__ import annotations

import pytest

from trace.tasks.geometry.shared.measurement_rendering import fmt_measure
from trace.tasks.geometry.triangle_relations.shared import construction


MIN_UNIQUE_ANSWERS = 80


@pytest.mark.parametrize(
    "case_builder_name",
    (
        "similar_side_cases",
        "parallel_section_cross_cases",
        "parallel_section_base_cases",
        "chained_rectangle_diagonal_cases",
        "rectangle_triangle_shared_height_cases",
        "angle_bisector_split_cases",
        "angle_bisector_base_cases",
        "centroid_vertex_cases",
        "centroid_whole_cases",
        "height_from_angle_ground_cases",
        "ground_from_angle_height_cases",
        "hypotenuse_from_angle_height_cases",
        "height_from_angle_hypotenuse_cases",
        "ground_from_angle_hypotenuse_cases",
        "angle_from_opposite_adjacent_cases",
        "angle_from_opposite_hypotenuse_cases",
        "angle_from_adjacent_hypotenuse_cases",
        "angle_of_elevation_cases",
        "angle_bisector_variable_cases",
        "split_triangle_angle_cases",
        "split_triangle_trig_side_cases",
        "altitude_from_two_projections_cases",
        "projection_from_altitude_cases",
        "leg_from_projection_cases",
        "projection_from_leg_cases",
        "parallel_segment_expression_length_cases",
        "parallel_segment_variable_cases",
    ),
)
def test_triangle_relations_construction_pools_have_broad_answer_support(case_builder_name: str) -> None:
    cases = getattr(construction, case_builder_name)()
    unique_answers = {str(fmt_measure(float(case.answer))) for case in cases}

    assert len(unique_answers) >= MIN_UNIQUE_ANSWERS
