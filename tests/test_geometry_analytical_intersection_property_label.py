"""Contract tests for analytical intersection-property label task."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.geometry.analytical.intersection_property_label import (
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    GeometryAnalyticalIntersectionPropertyLabelTask,
)


def _matching_labels(variant: str, panels_by_label: dict[str, dict], target_quadrant: str) -> list[str]:
    if variant == "line_circle_tangent_label":
        return [
            label
            for label, panel in panels_by_label.items()
            if panel["pair_kind"] == "line_circle" and panel["relation_class"] == "tangent"
        ]
    if variant == "line_circle_two_intersections_label":
        return [
            label
            for label, panel in panels_by_label.items()
            if panel["pair_kind"] == "line_circle" and int(panel["intersection_count"]) == 2
        ]
    if variant == "circle_circle_two_intersections_label":
        return [
            label
            for label, panel in panels_by_label.items()
            if panel["pair_kind"] == "circle_circle" and int(panel["intersection_count"]) == 2
        ]
    raise AssertionError(f"unsupported variant in test: {variant}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_geometry_analytical_intersection_property_label_contract(query_id: str) -> None:
    task = GeometryAnalyticalIntersectionPropertyLabelTask()
    out = task.generate(
        hash64(94210, TASK_ID, 3),
        params={"query_id": query_id, "winner_label": "C"},
        max_attempts=10,
    )

    assert out.query_id == query_id
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) >= 2
    assert out.trace_payload["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert out.trace_payload["query_spec"]["template_id"] == "geometry_analytical_intersection_property_v0"
    assert out.image.size == (1024, 1024)

    panels = out.trace_payload["execution_trace"]["panels_by_label"]
    assert set(panels.keys()) == {"A", "B", "C", "D", "E", "F", "G", "H", "I"}
    target_quadrant = out.trace_payload["execution_trace"]["target_quadrant"]
    assert _matching_labels(query_id, panels, str(target_quadrant)) == ["C"]

    c_panel_bbox = out.trace_payload["projected_evidence"]["panel_bbox_by_label"]["C"]
    c_point_bboxes = out.trace_payload["projected_evidence"]["intersection_point_bboxes_by_label"]["C"]
    assert out.evidence_gt.value == [c_panel_bbox, *c_point_bboxes]


def test_geometry_analytical_intersection_property_label_balances_variants_and_answers() -> None:
    task = GeometryAnalyticalIntersectionPropertyLabelTask()
    per_query_id_labels = {variant: Counter() for variant in SUPPORTED_QUERY_IDS}

    for index in range(99):
        out = task.generate(
            hash64(94220, TASK_ID, index),
            params={},
            max_attempts=10,
        )
        per_query_id_labels[str(out.query_id)][str(out.answer_gt.value)] += 1

    query_id_counts = {variant: sum(counter.values()) for variant, counter in per_query_id_labels.items()}
    assert set(query_id_counts) == set(SUPPORTED_QUERY_IDS)
    assert all(20 <= count <= 45 for count in query_id_counts.values())
    for counts in per_query_id_labels.values():
        assert set(counts.keys()) == {"A", "B", "C", "D", "E", "F", "G", "H", "I"}
        assert max(counts.values()) <= 8


def test_geometry_analytical_intersection_property_label_randomizes_object_colors() -> None:
    task = GeometryAnalyticalIntersectionPropertyLabelTask()
    color_orders = set()

    for index in range(18):
        out = task.generate(
            hash64(94230, TASK_ID, index),
            params={},
            max_attempts=10,
        )
        colors = out.trace_payload["render_spec"]["object_colors"]
        color_orders.add(tuple(tuple(int(channel) for channel in color) for color in colors))
        assert len(colors) >= 2
        assert all(len(color) == 3 for color in colors)
        assert out.trace_payload["render_spec"]["object_color_selection"]["palette_index"] is not None

    assert len(color_orders) >= 6
