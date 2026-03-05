"""Regression tests for task-group default config loading."""

from __future__ import annotations

from trace.core.task_group_config import (
    get_domain_defaults,
    get_task_group_defaults,
    resolve_task_group_section_defaults,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_geometry_measurement_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")
    assert int(cfg["generation"]["shared"]["candidate_count_min"]) == 3
    assert int(cfg["generation"]["shared"]["candidate_count_max"]) == 7
    assert bool(cfg["generation"]["shared"]["allow_duplicate_distractors"]) is True
    assert int(cfg["generation"]["task_overrides"]["geometry_angle_value_query"]["min_angle"]) == 15
    assert int(cfg["rendering"]["shared"]["canvas_size_min"]) == 512
    assert int(cfg["rendering"]["shared"]["canvas_size_max"]) == 1024
    assert int(cfg["rendering"]["shared"]["graph_cells_min"]) == 12
    assert int(cfg["rendering"]["shared"]["graph_cells_max"]) == 24
    assert int(cfg["rendering"]["task_overrides"]["geometry_angle_value_query"]["ray_length"]) == 84
    assert bool(cfg["visual"]["background"]["enabled"]) is True
    assert sorted(cfg["visual"]["background"]["styles"].keys()) == ["graph_paper"]
    graph = cfg["visual"]["background"]["styles"]["graph_paper"]
    assert list(graph["base_color"]) == [255, 255, 255]
    assert bool(graph["axis_enabled"]) is True
    assert int(graph["axis_line_width"]) >= 2
    assert bool(graph["center_point_enabled"]) is True
    assert int(graph["center_point_radius"]) >= 1
    assert float(cfg["visual"]["background"]["weights"]["graph_paper"]) == 1.0
    assert float(cfg["visual"]["noise"]["apply_prob"]) == 0.5
    assert float(cfg["sampling"]["shared"]["query_weights"]["median"]) == 1.0

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="geometry_angle_value_query",
    )
    assert int(generation["candidate_count_min"]) == 3
    assert int(generation["candidate_count_max"]) == 7
    assert int(generation["min_angle"]) == 15
    assert int(generation["max_angle"]) == 165
    assert int(rendering["ray_length"]) == 84
    assert str(prompt["entity_plural"]) == "angles"


def test_tile_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "path")
    assert int(cfg["generation"]["task_overrides"]["tile_shortest_path"]["rows"]) == 8
    assert int(cfg["rendering"]["task_overrides"]["tile_shortest_path"]["canvas_size"]) == 640
    assert bool(cfg["visual"]["background"]["enabled"]) is True
    assert "grid_light" in cfg["visual"]["background"]["styles"]
    assert float(cfg["visual"]["noise"]["apply_prob"]) == 0.0
    assert float(cfg["sampling"]["shared"]["query_weights"]["shortest_path"]) == 1.0

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="tile_shortest_path",
    )
    assert int(generation["rows"]) == 8
    assert int(rendering["canvas_size"]) == 640
    assert str(prompt["bundle_id"]) == "tile_path_v1"


def test_unknown_group_returns_empty() -> None:
    assert get_task_group_defaults("missing_domain", "missing_group") == {}


def test_domain_defaults_apply_without_group_file() -> None:
    domain_cfg = get_domain_defaults("geometry")
    assert int(domain_cfg["rendering"]["shared"]["canvas_size_min"]) == 512
    assert int(domain_cfg["rendering"]["shared"]["canvas_size_max"]) == 1024
    cfg = get_task_group_defaults("geometry", "missing_group")
    assert int(cfg["rendering"]["shared"]["canvas_size_min"]) == 512
    assert int(cfg["rendering"]["shared"]["canvas_size_max"]) == 1024
    assert int(cfg["rendering"]["shared"]["graph_cells_min"]) == 12
    assert int(cfg["rendering"]["shared"]["graph_cells_max"]) == 24


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
