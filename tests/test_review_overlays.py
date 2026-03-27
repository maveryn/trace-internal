"""Unit tests for shared review/sample evidence overlay helpers."""

from __future__ import annotations

from PIL import Image as PILImage

from trace.core.review_overlays import render_evidence_overlay, resolve_overlay_evidence


def test_resolve_overlay_evidence_uses_pixel_projection_for_graph_point_set() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="graph_point_set",
        evidence_value=[[0, 0], [1, 1], [2, 2]],
        trace_payload={"projected_evidence": {"pixel_point_set": [[40.0, 50.0], [60.0, 70.0], [80.0, 90.0]]}},
    )
    assert evidence_type == "pixel_point_set"
    assert evidence_value == [[40.0, 50.0], [60.0, 70.0], [80.0, 90.0]]


def test_resolve_overlay_evidence_uses_pixel_projection_for_graph_point() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="graph_point",
        evidence_value=[-3, 0],
        trace_payload={"projected_evidence": {"pixel_point_set": [[120.0, 240.0]]}},
    )
    assert evidence_type == "point"
    assert evidence_value == [120.0, 240.0]


def test_resolve_overlay_evidence_uses_bbox_projection_for_label_set() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="label_set",
        evidence_value=["Q", "M"],
        trace_payload={
            "projected_evidence": {
                "bbox_set": [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]],
            }
        },
    )
    assert evidence_type == "bbox_set"
    assert evidence_value == [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]]


def test_resolve_overlay_evidence_uses_bbox_projection_for_integer_list() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="integer_list",
        evidence_value=[7, 11],
        trace_payload={
            "projected_evidence": {
                "bbox_set": [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]],
            }
        },
    )
    assert evidence_type == "bbox_set"
    assert evidence_value == [[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]]


def test_resolve_overlay_evidence_uses_bbox_projection_for_integer() -> None:
    evidence_type, evidence_value = resolve_overlay_evidence(
        evidence_type="integer",
        evidence_value=12,
        trace_payload={
            "projected_evidence": {
                "bbox_set": [[10.0, 20.0, 30.0, 40.0]],
            }
        },
    )
    assert evidence_type == "bbox_set"
    assert evidence_value == [[10.0, 20.0, 30.0, 40.0]]


def test_render_evidence_overlay_draws_visible_marker_with_expanded_radius() -> None:
    source = PILImage.new("RGB", (100, 100), color=(255, 255, 255))
    overlay = render_evidence_overlay(source, evidence_type="point", evidence_value=[50, 50])
    assert overlay.getpixel((50, 50)) != (255, 255, 255)
    assert overlay.getpixel((56, 50)) != (255, 255, 255)
