"""Tests for shared post-image noise support across task families."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.angle import GeometryAngleMeasure2DTask
from trace.tasks.tile.path.shortest_path import TileShortestPathTask


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
    assert background_meta_a["selected_style"] == "graph_paper"
    style_spec = background_meta_a["style_spec"]
    assert len(style_spec["base_color"]) == 3
    assert all(0 <= int(channel) <= 255 for channel in style_spec["base_color"])
    assert bool(style_spec["axis_enabled"]) is True
    assert int(style_spec["axis_line_width"]) >= 1
    assert bool(style_spec["axis_arrows_enabled"]) is True
    assert bool(style_spec["center_point_enabled"]) is True
    assert bool(style_spec["color_variation_enabled"]) is True
    assert bool(style_spec["color_variation_applied"]) is True
    assert bool(style_spec["axis_scale_labels_enabled"]) is True
    assert int(style_spec["axis_scale_label_max_abs"]) >= 0
    assert bool(style_spec["origin_label_enabled"]) is False
    line_color = [int(channel) for channel in style_spec["line_color"]]
    major_color = [int(channel) for channel in style_spec["major_line_color"]]
    axis_color = [int(channel) for channel in style_spec["axis_color"]]
    assert all(int(axis) <= int(major) <= int(line) for line, major, axis in zip(line_color, major_color, axis_color))
    assert any(int(axis) < int(line) for line, axis in zip(line_color, axis_color))
    assert background_meta_a == background_meta_b


def test_tile_post_noise_override_is_deterministic_and_changes_pixels() -> None:
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
    assert background_meta["selected_style"] == "solid_light"
