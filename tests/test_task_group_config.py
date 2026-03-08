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
    cfg = get_task_group_defaults("geometry", "measurement_2d")
    for section in ("generation", "rendering", "prompt", "sampling"):
        assert isinstance(cfg.get(section), dict)

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["graph_cells_min"]) > 0
    assert int(render_shared["graph_cells_max"]) >= int(render_shared["graph_cells_min"])

    generation_overrides = cfg["generation"]["task_overrides"]
    assert "task_geometry_measurement_2d_angle" in generation_overrides
    assert int(cfg["generation"]["shared"]["answer_min"]) >= 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["task_type_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()
    assert float(cfg["sampling"]["shared"]["query_weights"]["measure"]) > 0.0

    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_2d_angle",
    )
    for key in ("min_angle", "max_angle", "angle_step", "mcq_option_count"):
        assert key in angle_generation
    assert int(angle_generation["max_angle"]) >= int(angle_generation["min_angle"])
    assert int(angle_generation["angle_step"]) > 0
    assert int(angle_generation["mcq_option_count"]) >= 3
    assert int(angle_rendering["line_width"]) > 0
    assert str(angle_prompt["evidence_hint"]).strip()
    assert str(angle_prompt["answer_hint"]).strip()
    assert str(angle_prompt["json_example"]).strip()
    assert str(angle_prompt["json_example_answer_only"]).strip()

    area_generation, area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_2d_area",
    )
    assert sorted(area_generation["variant_weights"].keys()) == ["ellipse", "pentagon", "quadrilateral", "triangle"]
    assert bool(area_generation["balanced_variant_sampling"]) is True
    assert bool(area_generation["ellipse_allow_circle"]) is False
    assert int(area_rendering["line_width"]) > 0
    assert str(area_prompt["question_text_polygon"]).strip()
    assert str(area_prompt["question_text_ellipse"]).strip()
    assert str(area_prompt["evidence_hint_polygon"]).strip()
    assert str(area_prompt["evidence_hint_center"]).strip()
    assert str(area_prompt["answer_hint_integer"]).strip()
    assert str(area_prompt["answer_hint_pi"]).strip()
    assert str(area_prompt["json_example_triangle"]).strip()
    assert str(area_prompt["json_example_quadrilateral"]).strip()
    assert str(area_prompt["json_example_pentagon"]).strip()
    assert str(area_prompt["json_example_integer"]).strip()
    assert str(area_prompt["json_example_pi"]).strip()
    assert str(area_prompt["json_example_answer_only_integer"]).strip()
    assert str(area_prompt["json_example_answer_only_pi"]).strip()

    perim_generation, perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_2d_perimeter",
    )
    assert sorted(perim_generation["variant_weights"].keys()) == ["circle", "pentagon", "quadrilateral", "triangle"]
    assert bool(perim_generation["balanced_variant_sampling"]) is True
    assert int(perim_generation["circle_radius_min"]) >= 1
    assert int(perim_generation["circle_radius_max"]) >= int(perim_generation["circle_radius_min"])
    assert int(perim_rendering["line_width"]) > 0
    assert str(perim_prompt["question_text_polygon"]).strip()
    assert str(perim_prompt["question_text_circle"]).strip()
    assert str(perim_prompt["evidence_hint_polygon"]).strip()
    assert str(perim_prompt["evidence_hint_center"]).strip()
    assert str(perim_prompt["answer_hint_integer"]).strip()
    assert str(perim_prompt["answer_hint_pi"]).strip()
    assert str(perim_prompt["json_example_triangle"]).strip()
    assert str(perim_prompt["json_example_quadrilateral"]).strip()
    assert str(perim_prompt["json_example_pentagon"]).strip()
    assert str(perim_prompt["json_example_integer"]).strip()
    assert str(perim_prompt["json_example_pi"]).strip()
    assert str(perim_prompt["json_example_answer_only_integer"]).strip()
    assert str(perim_prompt["json_example_answer_only_pi"]).strip()

    length_generation, length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_2d_length",
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
    assert str(length_prompt["evidence_hint_endpoints"]).strip()
    assert str(length_prompt["evidence_hint_center"]).strip()
    assert str(length_prompt["answer_hint_integer"]).strip()
    assert str(length_prompt["json_example_integer"]).strip()
    assert str(length_prompt["json_example_center_integer"]).strip()
    assert str(length_prompt["json_example_answer_only_integer"]).strip()


def test_tile_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "path")
    for section in ("generation", "rendering", "prompt", "visual", "sampling"):
        assert isinstance(cfg.get(section), dict)
    assert "task_tile_path_shortest_path" in cfg["generation"]["task_overrides"]
    assert isinstance(cfg["visual"]["background"]["styles"], dict)
    assert cfg["visual"]["background"]["styles"]
    assert float(cfg["sampling"]["shared"]["query_weights"]["shortest_path"]) > 0.0

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_tile_path_shortest_path",
    )
    assert int(generation["rows"]) > 0
    assert int(rendering["canvas_size"]) > 0
    assert str(prompt["bundle_id"]).strip()
    assert str(prompt["task_type_key"]).strip()
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
    cfg = get_task_group_defaults("geometry", "measurement_2d")

    _angle_generation, _angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_2d_angle",
    )
    angle_example = json.loads(str(angle_prompt["json_example"]))
    assert list(angle_example.keys()) == ["evidence", "answer"]
    assert len(angle_example["evidence"]) == 3
    assert str(angle_example["answer"]) in {"A", "B", "C", "D", "E"}
    angle_answer_only_example = json.loads(str(angle_prompt["json_example_answer_only"]))
    assert list(angle_answer_only_example.keys()) == ["answer"]
    assert str(angle_answer_only_example["answer"]) in {"A", "B", "C", "D", "E"}

    _area_generation, _area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_2d_area",
    )
    area_example = json.loads(str(area_prompt["json_example_integer"]))
    assert list(area_example.keys()) == ["evidence", "answer"]
    area_points = [[int(point[0]), int(point[1])] for point in area_example["evidence"]]
    assert len(area_points) >= 3
    assert int(area_example["answer"]) == int(_polygon_area(area_points))
    for key, expected_points in (
        ("json_example_triangle", 3),
        ("json_example_quadrilateral", 4),
        ("json_example_pentagon", 5),
    ):
        polygon_example = json.loads(str(area_prompt[key]))
        assert list(polygon_example.keys()) == ["evidence", "answer"]
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example["evidence"]]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example["answer"]) == int(_polygon_area(polygon_points))
    area_pi_example = json.loads(str(area_prompt["json_example_pi"]))
    assert list(area_pi_example.keys()) == ["evidence", "answer"]
    assert len(area_pi_example["evidence"]) == 1
    assert str(area_pi_example["answer"]).endswith("π")
    area_answer_only_integer = json.loads(str(area_prompt["json_example_answer_only_integer"]))
    assert list(area_answer_only_integer.keys()) == ["answer"]
    assert int(area_answer_only_integer["answer"]) >= 0
    area_answer_only_pi = json.loads(str(area_prompt["json_example_answer_only_pi"]))
    assert list(area_answer_only_pi.keys()) == ["answer"]
    assert str(area_answer_only_pi["answer"]).endswith("π")

    _perim_generation, _perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_2d_perimeter",
    )
    perim_example = json.loads(str(perim_prompt["json_example_integer"]))
    assert list(perim_example.keys()) == ["evidence", "answer"]
    perim_points = [[int(point[0]), int(point[1])] for point in perim_example["evidence"]]
    assert len(perim_points) >= 3
    assert int(perim_example["answer"]) == int(_polygon_perimeter(perim_points))
    for key, expected_points in (
        ("json_example_triangle", 3),
        ("json_example_quadrilateral", 4),
        ("json_example_pentagon", 5),
    ):
        polygon_example = json.loads(str(perim_prompt[key]))
        assert list(polygon_example.keys()) == ["evidence", "answer"]
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example["evidence"]]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example["answer"]) == int(_polygon_perimeter(polygon_points))
    perim_pi_example = json.loads(str(perim_prompt["json_example_pi"]))
    assert list(perim_pi_example.keys()) == ["evidence", "answer"]
    assert len(perim_pi_example["evidence"]) == 1
    assert str(perim_pi_example["answer"]).endswith("π")
    perim_answer_only_integer = json.loads(str(perim_prompt["json_example_answer_only_integer"]))
    assert list(perim_answer_only_integer.keys()) == ["answer"]
    assert int(perim_answer_only_integer["answer"]) >= 0
    perim_answer_only_pi = json.loads(str(perim_prompt["json_example_answer_only_pi"]))
    assert list(perim_answer_only_pi.keys()) == ["answer"]
    assert str(perim_answer_only_pi["answer"]).endswith("π")

    _length_generation, _length_rendering, length_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_2d_length",
    )
    length_example = json.loads(str(length_prompt["json_example_integer"]))
    assert list(length_example.keys()) == ["evidence", "answer"]
    length_points = [[int(point[0]), int(point[1])] for point in length_example["evidence"]]
    assert len(length_points) == 2
    dx = int(length_points[1][0]) - int(length_points[0][0])
    dy = int(length_points[1][1]) - int(length_points[0][1])
    assert int(length_example["answer"]) == int(round(math.hypot(float(dx), float(dy))))

    center_example = json.loads(str(length_prompt["json_example_center_integer"]))
    assert list(center_example.keys()) == ["evidence", "answer"]
    assert len(center_example["evidence"]) == 1
    assert len(center_example["evidence"][0]) == 2
    length_answer_only_example = json.loads(str(length_prompt["json_example_answer_only_integer"]))
    assert list(length_answer_only_example.keys()) == ["answer"]
    assert int(length_answer_only_example["answer"]) >= 0


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


def test_required_group_default_enforces_presence_and_nonempty() -> None:
    assert required_group_default({"value": 3}, "value", context="test") == 3
    with pytest.raises(ValueError):
        required_group_default({}, "value", context="test")
    with pytest.raises(ValueError):
        required_group_default({"value": "   "}, "value", context="test")


def test_required_group_defaults_enforces_all_keys() -> None:
    resolved = required_group_defaults({"a": 1, "b": "ok"}, ("a", "b"), context="test")
    assert resolved == {"a": 1, "b": "ok"}
    with pytest.raises(ValueError):
        required_group_defaults({"a": 1}, ("a", "b"), context="test")


def test_resolve_optional_int_bounds() -> None:
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


def test_resolve_required_numeric_bounds() -> None:
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
