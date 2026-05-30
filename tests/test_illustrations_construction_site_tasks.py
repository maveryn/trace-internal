"""Contract tests for construction-site illustration tasks."""

from __future__ import annotations

import pytest

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.shared.font_assets import font_asset_version, list_font_families


_CONSTRUCTION_TASK_CASES = (
    (
        "task_illustrations__construction_site__worker_attribute_count",
        {"query_id": "hard_hat_color_worker_count", "target_count": 2},
        0,
    ),
    (
        "task_illustrations__construction_site__equipment_zone_count",
        {"query_id": "vehicle_in_excavation_zone_count", "target_count": 2, "equipment_count": 5},
        2,
    ),
)


@pytest.mark.parametrize(("task_id", "params", "seed_index"), _CONSTRUCTION_TASK_CASES)
def test_construction_site_tasks_record_zone_label_font_and_projected_evidence(
    task_id: str,
    params: dict[str, object],
    seed_index: int,
) -> None:
    out = create_task(task_id).generate(
        hash64(2026052801, "construction-site-font-contract", seed_index),
        params=params,
        max_attempts=300,
    )
    trace = out.trace_payload
    font_trace = trace["render_spec"]["style"]["layout"]["zone_label_font"]
    assert font_trace["pool"] == "global_approved_font_pool"
    assert font_trace["font_family"] in set(list_font_families())
    assert font_trace["font_asset_version"] == font_asset_version()
    assert font_trace["consistent_scope"] == "construction_site_zone_labels"

    zone_fonts = [
        entity["label_font"]
        for entity in trace["scene_ir"]["entities"]
        if entity["type"] == "construction_zone"
    ]
    assert zone_fonts
    assert all(zone_font == font_trace for zone_font in zone_fonts)

    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    canvas_width, canvas_height = trace["render_spec"]["canvas_size"]
    for x0, y0, x1, y1 in out.evidence_gt.value:
        assert 0.0 <= x0 < x1 <= float(canvas_width)
        assert 0.0 <= y0 < y1 <= float(canvas_height)

    if task_id == "task_illustrations__construction_site__worker_attribute_count":
        params = trace["query_spec"]["params"]
        assert params["target_color_hex"].startswith("#")
        assert params["target_color_hex"] in out.prompt
