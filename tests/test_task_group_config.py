"""Regression tests for task-group default config loading."""

from __future__ import annotations

import json
import math

import pytest

from trace.core.task_group_config import (
    get_domain_defaults,
    get_task_group_defaults,
    resolve_task_group_section_defaults,
)
from trace.tasks.shared.config_defaults import (
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)


def _polygon_area(points: list[list[int]]) -> int:
    double_area = 0
    for index, (x_value, y_value) in enumerate(points):
        next_x, next_y = points[(index + 1) % len(points)]
        double_area += (int(x_value) * int(next_y)) - (int(y_value) * int(next_x))
    assert abs(int(double_area)) % 2 == 0
    return int(abs(int(double_area)) // 2)


def _polygon_perimeter(points: list[list[int]]) -> int:
    total = 0.0
    for index, (x_value, y_value) in enumerate(points):
        next_x, next_y = points[(index + 1) % len(points)]
        total += math.hypot(float(next_x) - float(x_value), float(next_y) - float(y_value))
    rounded = int(round(total))
    assert abs(float(total) - float(rounded)) <= 1e-9
    return int(rounded)


def test_geometry_measurement_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["graph_cells_min"]) > 0
    assert int(render_shared["graph_cells_max"]) >= int(render_shared["graph_cells_min"])
    assert int(render_shared["line_width_min"]) >= 1
    assert int(render_shared["line_width_max"]) >= int(render_shared["line_width_min"])
    assert int(render_shared["label_stroke_width_min"]) >= 1
    assert int(render_shared["label_stroke_width_max"]) >= int(render_shared["label_stroke_width_min"])

    generation_overrides = cfg["generation"]["task_overrides"]
    assert "task_geometry_measurement_angle" in generation_overrides
    assert int(cfg["generation"]["shared"]["answer_min"]) >= 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["task_family_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()

    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_angle",
    )
    for key in ("min_angle", "max_angle", "angle_step"):
        assert key in angle_generation
    assert int(angle_generation["max_angle"]) >= int(angle_generation["min_angle"])
    assert int(angle_generation["angle_step"]) > 0
    assert int(angle_rendering["line_width"]) > 0
    assert str(angle_prompt["evidence_hint"]).strip()
    assert str(angle_prompt["answer_hint"]).strip()
    assert str(angle_prompt["json_example"]).strip()
    assert str(angle_prompt["json_example_answer_only"]).strip()

    area_generation, area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_area",
    )
    assert sorted(area_generation["variant_weights"].keys()) == ["ellipse", "quadrilateral", "triangle"]
    assert bool(area_generation["balanced_variant_sampling"]) is True
    assert bool(area_generation["ellipse_allow_circle"]) is True
    assert int(area_rendering["line_width"]) > 0
    assert str(area_prompt["question_text_polygon"]).strip()
    assert str(area_prompt["question_text_ellipse"]).strip()
    assert str(area_prompt["evidence_hint_polygon"]).strip()
    assert str(area_prompt["evidence_hint_ellipse"]).strip()
    assert str(area_prompt["answer_hint_integer"]).strip()
    assert str(area_prompt["answer_hint_pi"]).strip()
    assert str(area_prompt["json_example_triangle"]).strip()
    assert str(area_prompt["json_example_quadrilateral"]).strip()
    assert str(area_prompt["json_example_ellipse"]).strip()
    assert str(area_prompt["json_example_integer"]).strip()
    assert str(area_prompt["json_example_pi"]).strip()
    assert str(area_prompt["json_example_answer_only_integer"]).strip()
    assert str(area_prompt["json_example_answer_only_pi"]).strip()

    perim_generation, perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_perimeter",
    )
    assert sorted(perim_generation["variant_weights"].keys()) == ["circle", "quadrilateral", "triangle"]
    assert bool(perim_generation["balanced_variant_sampling"]) is True
    assert int(perim_generation["circle_radius_min"]) >= 1
    assert int(perim_generation["circle_radius_max"]) >= int(perim_generation["circle_radius_min"])
    assert int(perim_rendering["line_width"]) > 0
    assert str(perim_prompt["question_text_polygon"]).strip()
    assert str(perim_prompt["question_text_circle"]).strip()
    assert str(perim_prompt["evidence_hint_polygon"]).strip()
    assert str(perim_prompt["evidence_hint_circle"]).strip()
    assert str(perim_prompt["answer_hint_integer"]).strip()
    assert str(perim_prompt["answer_hint_pi"]).strip()
    assert str(perim_prompt["json_example_triangle"]).strip()
    assert str(perim_prompt["json_example_quadrilateral"]).strip()
    assert str(perim_prompt["json_example_circle"]).strip()
    assert str(perim_prompt["json_example_integer"]).strip()
    assert str(perim_prompt["json_example_pi"]).strip()
    assert str(perim_prompt["json_example_answer_only_integer"]).strip()
    assert str(perim_prompt["json_example_answer_only_pi"]).strip()

    length_generation, length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_length",
    )
    assert sorted(length_generation["variant_weights"].keys()) == [
        "circle_diameter",
        "circle_radius",
        "ellipse_major_axis",
        "ellipse_minor_axis",
        "pentagon",
        "quadrilateral",
        "segment",
        "triangle",
    ]
    assert bool(length_generation["balanced_variant_sampling"]) is True
    assert int(length_generation["answer_min"]) <= int(length_generation["answer_max"])
    assert int(length_generation["segment_length_min"]) >= 1
    assert int(length_generation["segment_length_max"]) >= int(length_generation["segment_length_min"])
    assert int(length_rendering["line_width"]) > 0
    assert str(length_prompt["question_template_segment"]).strip()
    assert str(length_prompt["question_template_polygon_side"]).strip()
    assert str(length_prompt["question_text_circle_radius"]).strip()
    assert str(length_prompt["question_text_circle_diameter"]).strip()
    assert str(length_prompt["question_text_ellipse_major_axis"]).strip()
    assert str(length_prompt["question_text_ellipse_minor_axis"]).strip()
    assert str(length_prompt["evidence_hint_segment"]).strip()
    assert str(length_prompt["evidence_hint_polygon_side"]).strip()
    assert str(length_prompt["evidence_hint_circle_center"]).strip()
    assert str(length_prompt["evidence_hint_ellipse_axis"]).strip()
    assert str(length_prompt["answer_hint_integer"]).strip()
    assert str(length_prompt["json_example_segment_integer"]).strip()
    assert str(length_prompt["json_example_polygon_side_integer"]).strip()
    assert str(length_prompt["json_example_circle_radius_integer"]).strip()
    assert str(length_prompt["json_example_circle_diameter_integer"]).strip()
    assert str(length_prompt["json_example_ellipse_major_axis_integer"]).strip()
    assert str(length_prompt["json_example_ellipse_minor_axis_integer"]).strip()
    assert str(length_prompt["json_example_integer"]).strip()
    assert str(length_prompt["json_example_answer_only_integer"]).strip()

    slope_generation, slope_rendering, slope_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_slope",
    )
    assert int(slope_generation["slope_tenths_min"]) < 0
    assert int(slope_generation["slope_tenths_max"]) > 0
    assert bool(slope_generation["balanced_sampling"]) is True
    assert int(slope_rendering["line_width"]) > 0
    assert str(slope_prompt["object_description"]).strip()
    assert str(slope_prompt["question_text"]).strip()
    assert str(slope_prompt["evidence_hint"]).strip()
    assert str(slope_prompt["answer_hint"]).strip()
    assert str(slope_prompt["json_example"]).strip()
    assert str(slope_prompt["json_example_answer_only"]).strip()


def test_geometry_analytical_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "analytical_2d")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["answer_min"]) >= 0
    assert int(generation_shared["answer_max"]) >= int(generation_shared["answer_min"])
    assert sorted(generation_shared["shape_weights"].keys()) == [
        "circle",
        "ellipse",
        "parallelogram",
        "rectangle",
        "rhombus",
        "trapezoid",
        "triangle",
    ]
    assert sorted(generation_shared["mode_weights"].keys()) == ["derived", "explicit"]
    assert bool(generation_shared["balanced_shape_sampling"]) is True
    assert bool(generation_shared["balanced_mode_sampling"]) is True

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["graph_cells_min"]) > 0
    assert int(render_shared["graph_cells_max"]) >= int(render_shared["graph_cells_min"])
    assert int(render_shared["line_width_min"]) >= 1
    assert int(render_shared["line_width_max"]) >= int(render_shared["line_width_min"])
    assert int(render_shared["helper_line_width_min"]) >= 1
    assert int(render_shared["helper_line_width_max"]) >= int(render_shared["helper_line_width_min"])
    assert int(render_shared["label_stroke_width_min"]) >= 1
    assert int(render_shared["label_stroke_width_max"]) >= int(render_shared["label_stroke_width_min"])
    assert int(render_shared["analytical_unit_spacing_px"]) >= 2
    assert int(render_shared["analytical_unit_padding_px"]) >= 0
    visual_background = cfg["visual"]["background"]
    assert bool(visual_background["enabled"]) is True
    assert {"solid_cool", "solid_offwhite", "solid_warm"}.issubset(set(visual_background["styles"].keys()))
    assert float(visual_background["weights"]["graph_paper"]) == 0.0
    assert float(visual_background["weights"]["solid_offwhite"]) > 0.0

    prompt_generation, prompt_rendering, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_area",
    )
    assert int(prompt_generation["side_min"]) > 0
    assert int(prompt_generation["side_max"]) >= int(prompt_generation["side_min"])
    assert int(prompt_generation["circle_radius_min"]) > 0
    assert int(prompt_generation["circle_radius_max"]) >= int(prompt_generation["circle_radius_min"])
    assert int(prompt_generation["ellipse_axis_min"]) > 0
    assert int(prompt_generation["ellipse_axis_max"]) >= int(prompt_generation["ellipse_axis_min"])
    assert int(prompt_rendering["line_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip()
    assert str(prompt_defaults["task_family_key"]).strip()
    assert str(prompt_defaults["task_key"]).strip()
    assert str(prompt_defaults["object_description"]).strip()
    assert str(prompt_defaults["evidence_hint_measurement_map"]).strip()
    assert str(prompt_defaults["answer_hint_integer"]).strip()
    assert str(prompt_defaults["answer_hint_pi"]).strip()
    assert str(prompt_defaults["json_example_answer_only_integer"]).strip()
    assert str(prompt_defaults["json_example_answer_only_pi"]).strip()
    for key in (
        "rectangle_explicit",
        "rectangle_derived",
        "triangle_explicit",
        "triangle_derived",
        "parallelogram_explicit",
        "parallelogram_derived",
        "trapezoid_explicit",
        "trapezoid_derived",
        "rhombus_explicit",
        "rhombus_derived",
        "circle_explicit",
        "circle_derived",
        "ellipse_explicit",
        "ellipse_derived",
    ):
        assert str(prompt_defaults[f"question_text_{key}"]).strip()
        assert str(prompt_defaults[f"json_example_{key}"]).strip()


def test_geometry_analytical_3d_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "analytical_3d")
    for section in ("generation", "rendering", "prompt"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["answer_min"]) >= 0
    assert int(generation_shared["answer_max"]) >= int(generation_shared["answer_min"])
    assert int(generation_shared["dimension_min"]) > 0
    assert int(generation_shared["dimension_max"]) >= int(generation_shared["dimension_min"])
    assert int(generation_shared["radius_min"]) > 0
    assert int(generation_shared["radius_max"]) >= int(generation_shared["radius_min"])
    assert int(generation_shared["sphere_radius_min"]) > 0
    assert int(generation_shared["sphere_radius_max"]) >= int(generation_shared["sphere_radius_min"])
    assert "task_geometry_analytical_3d_volume" in cfg["generation"]["task_overrides"]
    assert "task_geometry_analytical_3d_surface_area" in cfg["generation"]["task_overrides"]

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["line_width_min"]) >= 1
    assert int(render_shared["line_width_max"]) >= int(render_shared["line_width_min"])
    assert int(render_shared["helper_line_width_min"]) >= 1
    assert int(render_shared["helper_line_width_max"]) >= int(render_shared["helper_line_width_min"])
    assert int(render_shared["label_stroke_width_min"]) >= 1
    assert int(render_shared["label_stroke_width_max"]) >= int(render_shared["label_stroke_width_min"])

    gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_3d_volume",
    )
    assert sorted(gen_defaults["variant_weights"].keys()) == [
        "cone_given_r_h",
        "cylinder_given_r_h",
        "rectangular_prism_given_lwh",
        "sphere_given_r",
        "square_pyramid_given_base_height",
        "triangular_prism_given_b_h_l",
    ]
    assert bool(gen_defaults["balanced_variant_sampling"]) is True
    assert int(render_defaults["line_width"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip()
    assert str(prompt_defaults["task_family_key"]).strip()
    assert str(prompt_defaults["task_key"]).strip()
    assert str(prompt_defaults["object_description"]).strip()
    assert str(prompt_defaults["evidence_hint_measurement_map"]).strip()
    assert str(prompt_defaults["answer_hint_integer"]).strip()
    assert str(prompt_defaults["answer_hint_pi"]).strip()
    assert str(prompt_defaults["json_example_answer_only_integer"]).strip()
    assert str(prompt_defaults["json_example_answer_only_pi"]).strip()
    for key in (
        "rectangular_prism_given_lwh",
        "triangular_prism_given_b_h_l",
        "square_pyramid_given_base_height",
        "cylinder_given_r_h",
        "cone_given_r_h",
        "sphere_given_r",
    ):
        assert str(prompt_defaults[f"question_text_{key}"]).strip()

    surface_generation, _surface_rendering, surface_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_3d_surface_area",
    )
    assert sorted(surface_generation["variant_weights"].keys()) == [
        "cone_given_r_slant_height",
        "cylinder_given_r_h",
        "rectangular_prism_given_lwh",
        "sphere_given_r",
        "square_pyramid_given_base_side_slant_height",
        "triangular_prism_given_a_b_c_l",
    ]
    assert bool(surface_generation["balanced_variant_sampling"]) is True
    assert str(surface_prompt["bundle_id"]).strip() == "geometry_analytical_surface_area_v1"
    assert str(surface_prompt["task_key"]).strip() == "analytical_surface_area_query"
    for key in (
        "rectangular_prism_given_lwh",
        "triangular_prism_given_a_b_c_l",
        "square_pyramid_given_base_side_slant_height",
        "cylinder_given_r_h",
        "cone_given_r_slant_height",
        "sphere_given_r",
    ):
        assert str(surface_prompt[f"question_text_{key}"]).strip()


def test_tile_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "path")
    for section in ("generation", "rendering", "prompt", "visual"):
        assert isinstance(cfg.get(section), dict)
    assert "task_tile_path_shortest_path" in cfg["generation"]["task_overrides"]
    assert isinstance(cfg["visual"]["background"]["styles"], dict)
    assert cfg["visual"]["background"]["styles"]

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_path_shortest_path",
    )
    assert int(generation["rows"]) > 0
    assert int(rendering["canvas_size"]) > 0
    assert str(prompt["bundle_id"]).strip()
    assert str(prompt["task_family_key"]).strip()
    assert str(prompt["task_key"]).strip()
    assert str(prompt["json_output_contract"]).strip()
    assert str(prompt["json_output_contract_answer_only"]).strip()
    assert str(prompt["answer_hint"]).strip()
    assert str(prompt["evidence_hint_point_path"]).strip()
    assert str(prompt["evidence_hint_bbox_set"]).strip()
    assert str(prompt["json_example_point_path"]).strip()
    assert str(prompt["json_example_bbox_set"]).strip()
    assert str(prompt["json_example_answer_only"]).strip()


def test_domain_defaults_and_missing_group_behavior() -> None:
    assert get_task_group_defaults("missing_domain", "missing_group") == {}
    domain_cfg = get_domain_defaults("geometry")
    cfg = get_task_group_defaults("geometry", "missing_group")
    assert cfg["rendering"]["shared"] == domain_cfg["rendering"]["shared"]


def test_measurement_prompt_examples_are_task_valid() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")

    _angle_generation, _angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_angle",
    )
    angle_example = json.loads(str(angle_prompt["json_example"]))
    assert list(angle_example.keys()) == ["evidence", "answer"]
    assert isinstance(angle_example["evidence"], list)
    assert len(angle_example["evidence"]) == 3
    assert isinstance(angle_example["answer"], int)
    angle_answer_only_example = json.loads(str(angle_prompt["json_example_answer_only"]))
    assert list(angle_answer_only_example.keys()) == ["answer"]
    assert isinstance(angle_answer_only_example["answer"], int)

    _slope_generation, _slope_rendering, slope_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_slope",
    )
    slope_example = json.loads(str(slope_prompt["json_example"]))
    assert list(slope_example.keys()) == ["evidence", "answer"]
    assert isinstance(slope_example["evidence"], list)
    assert len(slope_example["evidence"]) == 2
    assert int(slope_example["evidence"][1]) == 0
    assert isinstance(slope_example["answer"], float)
    slope_answer_only_example = json.loads(str(slope_prompt["json_example_answer_only"]))
    assert list(slope_answer_only_example.keys()) == ["answer"]
    assert isinstance(slope_answer_only_example["answer"], float)

    _area_generation, _area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_area",
    )
    area_example = json.loads(str(area_prompt["json_example_integer"]))
    assert list(area_example.keys()) == ["evidence", "answer"]
    assert isinstance(area_example["evidence"], list)
    area_points = [[int(point[0]), int(point[1])] for point in area_example["evidence"]]
    assert len(area_points) >= 3
    assert int(area_example["answer"]) == int(_polygon_area(area_points))
    for key, expected_points in (
        ("json_example_triangle", 3),
        ("json_example_quadrilateral", 4),
    ):
        polygon_example = json.loads(str(area_prompt[key]))
        assert list(polygon_example.keys()) == ["evidence", "answer"]
        assert isinstance(polygon_example["evidence"], list)
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example["evidence"]]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example["answer"]) == int(_polygon_area(polygon_points))
    area_pi_example = json.loads(str(area_prompt["json_example_pi"]))
    assert list(area_pi_example.keys()) == ["evidence", "answer"]
    assert area_pi_example["evidence"] == [[0, 0]]
    assert str(area_pi_example["answer"]).endswith("π")
    area_answer_only_integer = json.loads(str(area_prompt["json_example_answer_only_integer"]))
    assert list(area_answer_only_integer.keys()) == ["answer"]
    assert int(area_answer_only_integer["answer"]) >= 0
    area_answer_only_pi = json.loads(str(area_prompt["json_example_answer_only_pi"]))
    assert list(area_answer_only_pi.keys()) == ["answer"]
    assert str(area_answer_only_pi["answer"]).endswith("π")

    _perim_generation, _perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_perimeter",
    )
    perim_example = json.loads(str(perim_prompt["json_example_integer"]))
    assert list(perim_example.keys()) == ["evidence", "answer"]
    assert isinstance(perim_example["evidence"], list)
    perim_points = [[int(point[0]), int(point[1])] for point in perim_example["evidence"]]
    assert len(perim_points) >= 3
    assert int(perim_example["answer"]) == int(_polygon_perimeter(perim_points))
    for key, expected_points in (
        ("json_example_triangle", 3),
        ("json_example_quadrilateral", 4),
    ):
        polygon_example = json.loads(str(perim_prompt[key]))
        assert list(polygon_example.keys()) == ["evidence", "answer"]
        assert isinstance(polygon_example["evidence"], list)
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example["evidence"]]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example["answer"]) == int(_polygon_perimeter(polygon_points))
    perim_pi_example = json.loads(str(perim_prompt["json_example_pi"]))
    assert list(perim_pi_example.keys()) == ["evidence", "answer"]
    assert perim_pi_example["evidence"] == [[0, 0]]
    assert str(perim_pi_example["answer"]).endswith("π")
    perim_answer_only_integer = json.loads(str(perim_prompt["json_example_answer_only_integer"]))
    assert list(perim_answer_only_integer.keys()) == ["answer"]
    assert int(perim_answer_only_integer["answer"]) >= 0
    perim_answer_only_pi = json.loads(str(perim_prompt["json_example_answer_only_pi"]))
    assert list(perim_answer_only_pi.keys()) == ["answer"]
    assert str(perim_answer_only_pi["answer"]).endswith("π")

    _length_generation, _length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_length",
    )
    length_example = json.loads(str(length_prompt["json_example_integer"]))
    assert list(length_example.keys()) == ["evidence", "answer"]
    assert isinstance(length_example["evidence"], list)
    length_points = [[int(point[0]), int(point[1])] for point in length_example["evidence"]]
    assert len(length_points) == 2
    dx = int(length_points[1][0]) - int(length_points[0][0])
    dy = int(length_points[1][1]) - int(length_points[0][1])
    assert int(length_example["answer"]) == int(round(math.hypot(float(dx), float(dy))))
    center_example = json.loads(str(length_prompt["json_example_circle_radius_integer"]))
    assert list(center_example.keys()) == ["evidence", "answer"]
    assert isinstance(center_example["evidence"], list)
    assert len(center_example["evidence"]) == 1
    only_point = center_example["evidence"][0]
    assert isinstance(only_point, list) and len(only_point) == 2
    length_answer_only_example = json.loads(str(length_prompt["json_example_answer_only_integer"]))
    assert list(length_answer_only_example.keys()) == ["answer"]
    assert int(length_answer_only_example["answer"]) >= 0


def test_analytical_prompt_examples_are_task_valid() -> None:
    cfg = get_task_group_defaults("geometry", "analytical_2d")
    _generation, _rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_analytical_2d_area",
    )
    integer_answer_only = json.loads(str(prompt["json_example_answer_only_integer"]))
    assert list(integer_answer_only.keys()) == ["answer"]
    assert int(integer_answer_only["answer"]) >= 0

    pi_answer_only = json.loads(str(prompt["json_example_answer_only_pi"]))
    assert list(pi_answer_only.keys()) == ["answer"]
    assert str(pi_answer_only["answer"]).endswith("π")

    for key in (
        "json_example_rectangle_explicit",
        "json_example_rectangle_derived",
        "json_example_triangle_explicit",
        "json_example_triangle_derived",
        "json_example_parallelogram_explicit",
        "json_example_parallelogram_derived",
        "json_example_trapezoid_explicit",
        "json_example_trapezoid_derived",
        "json_example_rhombus_explicit",
        "json_example_rhombus_derived",
        "json_example_circle_explicit",
        "json_example_circle_derived",
        "json_example_ellipse_explicit",
        "json_example_ellipse_derived",
    ):
        parsed = json.loads(str(prompt[key]))
        assert list(parsed.keys()) == ["evidence", "answer"]
        assert isinstance(parsed["evidence"], dict)
        assert parsed["evidence"]
        for annotation, payload in parsed["evidence"].items():
            assert str(annotation).strip()
            assert isinstance(payload, (int, float, str))
        if str(key).startswith(("json_example_circle", "json_example_ellipse")):
            assert isinstance(parsed["answer"], str)
            assert str(parsed["answer"]).endswith("π")
        else:
            assert int(parsed["answer"]) >= 0


def test_section_defaults_require_shared_and_task_overrides_schema() -> None:
    mapping = {
        "rendering": {
            "canvas_size_min": 111,
            "shared": {"canvas_size_min": 512},
            "task_overrides": {"demo_task": {"canvas_size_min": 768}},
        }
    }
    shared_only = resolve_task_group_section_defaults(mapping, "rendering")
    task_specific = resolve_task_group_section_defaults(mapping, "rendering", task_id="demo_task")
    assert int(shared_only["canvas_size_min"]) == 512
    assert int(task_specific["canvas_size_min"]) == 768
    assert resolve_task_group_section_defaults({"rendering": {"canvas_size_min": 111}}, "rendering") == {}


def test_required_group_helpers_enforce_presence_and_nonempty() -> None:
    assert required_group_default({"value": 3}, "value", context="test") == 3
    resolved = required_group_defaults({"a": 1, "b": "ok"}, ("a", "b"), context="test")
    assert resolved == {"a": 1, "b": "ok"}
    with pytest.raises(ValueError):
        required_group_default({}, "value", context="test")
    with pytest.raises(ValueError):
        required_group_default({"value": "   "}, "value", context="test")
    with pytest.raises(ValueError):
        required_group_defaults({"a": 1}, ("a", "b"), context="test")


def test_resolve_numeric_bounds_helpers() -> None:
    assert resolve_optional_int_bounds(
        {"answer_min": 3},
        {"answer_max": 9},
        min_key="answer_min",
        max_key="answer_max",
        context="test",
    ) == (3, 9)
    assert resolve_optional_int_bounds(
        {},
        {},
        min_key="answer_min",
        max_key="answer_max",
        context="test",
    ) == (None, None)
    with pytest.raises(ValueError):
        resolve_optional_int_bounds(
            {"answer_min": 10, "answer_max": 2},
            {},
            min_key="answer_min",
            max_key="answer_max",
            context="test",
        )
    assert resolve_required_int_bounds(
        {"min": 2},
        {"max": 8},
        min_key="min",
        max_key="max",
        fallback_min=1,
        fallback_max=9,
        context="test",
    ) == (2, 8)
    assert resolve_required_float_bounds(
        {"min_f": 0.1},
        {"max_f": 0.6},
        min_key="min_f",
        max_key="max_f",
        fallback_min=0.0,
        fallback_max=1.0,
        context="test",
    ) == (0.1, 0.6)
    with pytest.raises(ValueError):
        resolve_required_int_bounds(
            {"min": 9, "max": 2},
            {},
            min_key="min",
            max_key="max",
            fallback_min=0,
            fallback_max=1,
            context="test",
        )
    with pytest.raises(ValueError):
        resolve_required_float_bounds(
            {"min_f": 0.9, "max_f": 0.2},
            {},
            min_key="min_f",
            max_key="max_f",
            fallback_min=0.0,
            fallback_max=1.0,
            context="test",
        )
