"""Tests for shared post-image noise support across task families."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.angle_value_query import GeometryAngleValueQueryTask
from trace.tasks.tile.path.shortest_path import TileShortestPathTask


def test_geometry_measurement_default_noise_prob() -> None:
    task = GeometryAngleValueQueryTask()
    out = task.generate(
        4242,
        params={
            "query_type": "closest_to_x",
            "candidate_count": 7,
            "angle_step": 15,
            "target_x": 90,
        },
        max_attempts=200,
    )
    noise_meta = out.trace_payload["render_spec"]["post_image_noise"]
    assert noise_meta["enabled"] is True
    assert float(noise_meta["apply_prob"]) == pytest.approx(0.75, rel=1e-9)


def test_tile_post_noise_override_is_deterministic_and_changes_pixels() -> None:
    task = TileShortestPathTask()
    common = {
        "rows": 7,
        "cols": 7,
        "min_shortest_len": 5,
        "evidence_type": "point_path",
    }

    clean = task.generate(7777, params={**common, "noise_apply_prob": 0.0}, max_attempts=200)
    noisy_params = {
        **common,
        "noise_apply_prob": 1.0,
        "noise_edit_types": ["downsample"],
        "noise_edit_count_range": [1, 1],
        "noise_edit_value_ranges": {
            "downsample": {"scale": [0.65, 0.65]},
        },
    }
    noisy_a = task.generate(7777, params=noisy_params, max_attempts=200)
    noisy_b = task.generate(7777, params=noisy_params, max_attempts=200)

    assert noisy_a.image.tobytes() == noisy_b.image.tobytes()
    assert noisy_a.image.tobytes() != clean.image.tobytes()

    noise_meta = noisy_a.trace_payload["render_spec"]["post_image_noise"]
    assert noise_meta["applied"] is True
    assert len(noise_meta["edits"]) == 1
    assert noise_meta["edits"][0]["type"] == "downsample"
    assert float(noise_meta["edits"][0]["params"]["scale"]) == pytest.approx(0.65, rel=1e-9)
