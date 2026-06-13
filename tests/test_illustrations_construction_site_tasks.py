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


def _bbox_intersection_area(left: list[float], right: list[float]) -> float:
    x_overlap = max(0.0, min(float(left[2]), float(right[2])) - max(float(left[0]), float(right[0])))
    y_overlap = max(0.0, min(float(left[3]), float(right[3])) - max(float(left[1]), float(right[1])))
    return float(x_overlap * y_overlap)


@pytest.mark.parametrize(("task_id", "params", "seed_index"), _CONSTRUCTION_TASK_CASES)
def test_construction_site_tasks_record_zone_label_font_and_projected_annotation(
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

    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    canvas_width, canvas_height = trace["render_spec"]["canvas_size"]
    for x0, y0, x1, y1 in out.annotation_gt.value:
        assert 0.0 <= x0 < x1 <= float(canvas_width)
        assert 0.0 <= y0 < y1 <= float(canvas_height)

    if task_id == "task_illustrations__construction_site__worker_attribute_count":
        params = trace["query_spec"]["params"]
        assert params["target_color_hex"].startswith("#")
        assert params["target_color_hex"] in out.prompt


def test_construction_site_missing_patch_uses_keyed_visual_witnesses() -> None:
    out = create_task("task_illustrations__construction_site__missing_patch_label").generate(
        hash64(2026061301, "construction-site-missing-patch"),
        params={"query_id": "plain_patch_label", "correct_index": 2},
        max_attempts=120,
    )

    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"missing_region", "selected_option"}
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value

    canvas_width, canvas_height = out.trace_payload["render_spec"]["canvas_size"]
    for bbox in out.annotation_gt.value.values():
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(canvas_width)
        assert 0.0 <= y0 < y1 <= float(canvas_height)

    render_map = out.trace_payload["render_map"]
    missing = render_map["missing_region_bbox_px"]
    selected = render_map["selected_option_bbox_px"]
    assert round(float(missing[2]) - float(missing[0]), 3) == round(float(selected[2]) - float(selected[0]), 3)
    assert round(float(missing[3]) - float(missing[1]), 3) == round(float(selected[3]) - float(selected[1]), 3)
    assert out.trace_payload["render_spec"]["style"]["source_layout"]["show_zone_labels"] is False


def test_construction_site_equipment_zone_count_allows_zero_with_empty_annotation() -> None:
    out = create_task("task_illustrations__construction_site__equipment_zone_count").generate(
        hash64(2026061302, "construction-site-zero-equipment-zone"),
        params={"query_id": "vehicle_in_excavation_zone_count", "target_count": 0, "equipment_count": 5},
        max_attempts=300,
    )

    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 0
    assert out.annotation_gt.type == "bbox_set"
    assert out.annotation_gt.value == []
    assert out.trace_payload["projected_annotation"]["bbox_set"] == []
    assert out.trace_payload["render_map"]["counted_equipment_ids"] == []
    assert "0" in out.prompt


def test_construction_site_worker_attribute_count_supports_zero_and_max_five() -> None:
    zero = create_task("task_illustrations__construction_site__worker_attribute_count").generate(
        hash64(2026061304, "construction-site-zero-worker-attribute"),
        params={"query_id": "tool_holding_worker_count", "target_count": 0},
        max_attempts=300,
    )
    assert zero.answer_gt.type == "integer"
    assert zero.answer_gt.value == 0
    assert zero.annotation_gt.type == "bbox_set"
    assert zero.annotation_gt.value == []
    assert zero.trace_payload["render_map"]["counted_worker_ids"] == []
    assert "0" in zero.prompt

    max_count = create_task("task_illustrations__construction_site__worker_attribute_count").generate(
        hash64(2026061305, "construction-site-five-worker-attribute"),
        params={"query_id": "hard_hat_color_worker_count", "target_count": 5},
        max_attempts=300,
    )
    assert max_count.answer_gt.type == "integer"
    assert max_count.answer_gt.value == 5
    assert len(max_count.annotation_gt.value) == 5
    assert len(max_count.trace_payload["render_map"]["counted_worker_ids"]) == 5


def test_construction_site_equipment_zone_count_target_boxes_do_not_overlap() -> None:
    out = create_task("task_illustrations__construction_site__equipment_zone_count").generate(
        7314101157250,
        params={"query_id": "vehicle_in_excavation_zone_count", "target_count": 4, "equipment_count": 8},
        max_attempts=300,
    )

    boxes = [list(map(float, bbox)) for bbox in out.annotation_gt.value]
    assert len(boxes) == 4
    for index, left in enumerate(boxes):
        for right in boxes[index + 1 :]:
            assert _bbox_intersection_area(left, right) == 0.0


def test_construction_site_missing_patch_samples_four_and_six_options() -> None:
    seen: set[int] = set()
    for index in range(12):
        out = create_task("task_illustrations__construction_site__missing_patch_label").generate(
            hash64(2026061303, "construction-site-option-count-support", index),
            params={"query_id": "plain_patch_label"},
            max_attempts=120,
        )
        option_count = int(out.trace_payload["query_spec"]["params"]["option_count"])
        seen.add(option_count)
        assert option_count in {4, 6}
        assert set(out.trace_payload["query_spec"]["params"]["option_count_support"]) == {4, 6}
        assert len(out.trace_payload["render_map"]["option_bboxes_px_by_label"]) == option_count
    assert seen == {4, 6}
