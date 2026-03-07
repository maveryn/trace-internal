"""Regression tests for task-group default config loading."""

from __future__ import annotations

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


def test_geometry_measurement_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")
    for section in ("generation", "rendering", "prompt", "sampling"):
        assert isinstance(cfg.get(section), dict)

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_size_min"]) > 0
    assert int(render_shared["canvas_size_max"]) >= int(render_shared["canvas_size_min"])
    assert int(render_shared["graph_cells_min"]) > 0
    assert int(render_shared["graph_cells_max"]) >= int(render_shared["graph_cells_min"])

    generation_overrides = cfg["generation"]["task_overrides"]
    assert "task_geometry_measurement_angle" in generation_overrides
    assert "allowed_sides" in cfg["generation"]["shared"]

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["task_type_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert float(cfg["sampling"]["shared"]["query_weights"]["measure"]) > 0.0

    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_angle",
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

    area_generation, area_rendering, area_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_polygon_area",
    )
    assert "allowed_sides" in area_generation
    assert sorted(int(side) for side in area_generation["allowed_sides"]) == [3, 4, 5]
    assert int(area_rendering["line_width"]) > 0
    assert str(area_prompt["question_text"]).strip()
    assert str(area_prompt["evidence_hint"]).strip()
    assert str(area_prompt["answer_hint"]).strip()
    assert str(area_prompt["json_example"]).strip()

    perim_generation, perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_measurement_polygon_perimeter",
    )
    assert "allowed_sides" in perim_generation
    assert sorted(int(side) for side in perim_generation["allowed_sides"]) == [3, 4, 5]
    assert int(perim_rendering["line_width"]) > 0
    assert str(perim_prompt["question_text"]).strip()
    assert str(perim_prompt["evidence_hint"]).strip()
    assert str(perim_prompt["answer_hint"]).strip()
    assert str(perim_prompt["json_example"]).strip()


def test_tile_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "path")
    for section in ("generation", "rendering", "visual", "sampling"):
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


def test_domain_defaults_and_missing_group_behavior() -> None:
    assert get_task_group_defaults("missing_domain", "missing_group") == {}
    domain_cfg = get_domain_defaults("geometry")
    cfg = get_task_group_defaults("geometry", "missing_group")
    assert cfg["rendering"]["shared"] == domain_cfg["rendering"]["shared"]


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
