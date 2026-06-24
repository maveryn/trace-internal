"""Tests for shared post-image noise support across task families."""

from __future__ import annotations

import pytest

from trace.core.scene_config import get_scene_defaults
from trace.core.scene_config import get_scene_defaults
from trace.tasks.geometry.measurement.angle import GeometryAngleMeasure2DTask
from trace.tasks.puzzles.cell_board.path_shortest_path import TileShortestPathTask


def test_domain_post_noise_policy_defaults_are_mild_and_explicit() -> None:
    expected_apply_probs = {
        ("charts", "trend"): 0.50,
        ("games", "cards"): 0.50,
        ("geometry", "measurement"): 0.50,
        ("graph", "path"): 0.50,
        ("pages", "arithmetic"): 0.50,
        ("pages", "relation"): 0.50,
        ("physics", "mechanics"): 0.50,
        ("puzzles", "counterfactual"): 0.50,
        ("puzzles", "logic"): 0.15,
        ("puzzles", "spatial"): 0.0,
        ("puzzles", "topology"): 0.15,
        ("charts", "table"): 0.50,
        ("puzzles", "clock"): 0.0,
        ("puzzles", "cell_board_count"): 0.50,
        ("puzzles", "cell_board_path"): 0.0,
    }
    coordinate_preserving_edits = {"blur", "downsample", "jpeg", "noise"}

    for (domain, scene_id), expected_prob in expected_apply_probs.items():
        cfg = get_scene_defaults(domain, scene_id)
        noise = cfg["visual"]["noise"]
        assert float(noise["apply_prob"]) == pytest.approx(expected_prob, rel=1e-9)
        edit_types = set(noise.get("edit_types", noise.get("value_ranges", {}).keys()))
        assert edit_types.issubset(coordinate_preserving_edits)
        if expected_prob > 0.0:
            assert list(noise["edit_count_range"]) == [1, 1]


def test_icon_domain_uses_per_icon_noise_not_global_post_noise() -> None:
    for scene_id in ("counting", "pattern", "relation", "sequence"):
        cfg = get_scene_defaults("icons", scene_id)
        assert "noise" not in cfg.get("visual", {})
        rendering_defaults = cfg["rendering"]["shared"]
        assert "icon_noise_edit_types" in rendering_defaults
        assert set(rendering_defaults["icon_noise_edit_types"]) == {"blur", "downsample", "jpeg", "noise"}
    for scene_id in ("pair_grid", "paired_canvas", "single_transform_options"):
        cfg = get_scene_defaults("icons", scene_id)
        assert "noise" not in cfg.get("visual", {})
        rendering_defaults = cfg["rendering"]["shared"]
        assert "icon_noise_edit_types" in rendering_defaults
        assert set(rendering_defaults["icon_noise_edit_types"]) == {"blur", "downsample", "jpeg", "noise"}


def test_geometry_measurement_default_noise_prob() -> None:
    task = GeometryAngleMeasure2DTask()
    out_a = task.generate(
        4242,
        params={
            "angle_step": 1,
        },
        max_attempts=200,
    )
    out_b = task.generate(
        4242,
        params={
            "angle_step": 1,
        },
        max_attempts=200,
    )
    noise_meta = out_a.trace_payload["render_spec"]["post_image_noise"]
    background_meta_a = out_a.trace_payload["render_spec"]["background_style"]
    background_meta_b = out_b.trace_payload["render_spec"]["background_style"]
    assert noise_meta["enabled"] is True
    assert 0.0 <= float(noise_meta["apply_prob"]) <= 1.0
    assert background_meta_a["enabled"] is True
    assert background_meta_a["selected_style"] == "graph_paper_panel"
    style_spec = background_meta_a["style_spec"]
    assert style_spec["kind"] == "bounded_graph_paper"
    assert len(style_spec["graph_panel_bbox_px"]) == 4
    assert len(style_spec["graph_content_bbox_px"]) == 4
    assert len(style_spec["base_color"]) == 3
    assert all(0 <= int(channel) <= 255 for channel in style_spec["base_color"])
    assert bool(style_spec["axis_enabled"]) is True
    assert int(style_spec["axis_line_width"]) >= 1
    assert bool(style_spec["axis_arrows_enabled"]) is True
    assert bool(style_spec["center_point_enabled"]) is True
    assert bool(style_spec["color_variation_enabled"]) is False
    assert bool(style_spec["color_variation_applied"]) is False
    technical_style = out_a.trace_payload["render_spec"]["technical_diagram_style"]
    assert technical_style["kind"] == "technical_diagram_style"
    assert technical_style["grid_style"]["kind"] == "none"
    assert technical_style["background_style"]["kind"] != "graph_paper"
    assert len(technical_style["roles_rgb"]["panel_fill"]) == 3
    assert len(technical_style["contrast_checks"]) > 0
    assert bool(style_spec["axis_scale_labels_enabled"]) is True
    assert int(style_spec["axis_scale_label_max_abs"]) >= 0
    assert bool(style_spec["origin_label_enabled"]) is False
    line_color = [int(channel) for channel in style_spec["line_color"]]
    major_color = [int(channel) for channel in style_spec["major_line_color"]]
    axis_color = [int(channel) for channel in style_spec["axis_color"]]
    assert all(int(axis) <= int(major) <= int(line) for line, major, axis in zip(line_color, major_color, axis_color))
    assert any(int(axis) < int(line) for line, axis in zip(line_color, axis_color))
    assert background_meta_a == background_meta_b


def test_cell_board_post_noise_override_is_deterministic_and_changes_pixels() -> None:
    task = TileShortestPathTask()
    common = {
        "rows": 7,
        "cols": 7,
        "target_shortest_len_min": 4,
        "target_shortest_len_max": 10,
    }

    clean = task.generate(
        7777,
        params={
            **common,
            "visual": {
                "noise": {"apply_prob": 0.0},
            },
        },
        max_attempts=200,
    )
    noisy_params = {
        **common,
        "visual": {
            "background": {
                "style_name": "solid_light",
            },
            "noise": {
                "apply_prob": 1.0,
                "edit_types": ["downsample"],
                "edit_count_range": [1, 1],
                "value_ranges": {
                    "downsample": {"scale": [0.65, 0.65]},
                },
            },
        },
    }
    noisy_a = task.generate(7777, params=noisy_params, max_attempts=200)
    noisy_b = task.generate(7777, params=noisy_params, max_attempts=200)

    assert noisy_a.image.tobytes() == noisy_b.image.tobytes()
    assert noisy_a.image.tobytes() != clean.image.tobytes()

    noise_meta = noisy_a.trace_payload["render_spec"]["post_image_noise"]
    background_meta = noisy_a.trace_payload["render_spec"]["background_style"]
    assert noise_meta["applied"] is True
    assert len(noise_meta["edits"]) == 1
    assert noise_meta["edits"][0]["type"] == "downsample"
    assert float(noise_meta["edits"][0]["params"]["scale"]) == pytest.approx(0.65, rel=1e-9)
    assert background_meta["enabled"] is True
    assert background_meta["selected_style"]
