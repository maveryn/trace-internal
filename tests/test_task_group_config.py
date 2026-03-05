"""Regression tests for task-group default config loading."""

from __future__ import annotations

from trace.core.task_group_config import get_domain_defaults, get_task_group_defaults


def test_geometry_measurement_defaults_loaded() -> None:
    cfg = get_task_group_defaults("geometry", "measurement")
    assert int(cfg["generation"]["candidate_count_min"]) == 3
    assert int(cfg["generation"]["candidate_count_max"]) == 7
    assert bool(cfg["generation"]["allow_duplicate_distractors"]) is True
    assert int(cfg["rendering"]["canvas_size_min"]) == 512
    assert int(cfg["rendering"]["canvas_size_max"]) == 1024
    assert int(cfg["rendering"]["graph_cells_min"]) == 12
    assert int(cfg["rendering"]["graph_cells_max"]) == 24
    assert int(cfg["rendering"]["ray_length"]) == 84
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


def test_tile_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("tile", "path")
    assert int(cfg["generation"]["rows"]) == 8
    assert int(cfg["rendering"]["canvas_size"]) == 640
    assert bool(cfg["visual"]["background"]["enabled"]) is True
    assert "grid_light" in cfg["visual"]["background"]["styles"]
    assert float(cfg["visual"]["noise"]["apply_prob"]) == 0.0


def test_unknown_group_returns_empty() -> None:
    assert get_task_group_defaults("missing_domain", "missing_group") == {}


def test_domain_defaults_apply_without_group_file() -> None:
    domain_cfg = get_domain_defaults("geometry")
    assert int(domain_cfg["rendering"]["canvas_size_min"]) == 512
    assert int(domain_cfg["rendering"]["canvas_size_max"]) == 1024
    cfg = get_task_group_defaults("geometry", "missing_group")
    assert int(cfg["rendering"]["canvas_size_min"]) == 512
    assert int(cfg["rendering"]["canvas_size_max"]) == 1024
    assert int(cfg["rendering"]["graph_cells_min"]) == 12
    assert int(cfg["rendering"]["graph_cells_max"]) == 24
