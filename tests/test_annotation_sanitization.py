"""Annotation sanitization contract tests."""

from __future__ import annotations

from trace.core.annotation_sanitization import (
    public_projected_annotation,
    public_witness_summary,
    sanitize_trace_payload_for_public_annotation,
)
from trace.core.prompt_annotation_contract_audit import _validate_annotation_value
from trace.core.types import TypedValue


def test_public_projected_annotation_supports_scalar_point() -> None:
    annotation = TypedValue(type="point", value=[12, 34])

    assert public_projected_annotation(annotation) == {
        "type": "point",
        "point": [12, 34],
        "pixel_point": [12, 34],
    }
    assert public_witness_summary(annotation) == {"type": "point", "count": 1}


def test_public_projected_annotation_supports_scalar_bbox() -> None:
    annotation = TypedValue(type="bbox", value=[10, 20, 30, 40])

    assert public_projected_annotation(annotation) == {
        "type": "bbox",
        "bbox": [10, 20, 30, 40],
        "pixel_bbox": [10, 20, 30, 40],
    }
    assert public_witness_summary(annotation) == {"type": "bbox", "count": 1}


def test_sanitize_trace_payload_projects_scalar_annotation() -> None:
    sanitized = sanitize_trace_payload_for_public_annotation(
        {"execution_trace": {"annotation_labels": ["hidden"], "kept": 3}},
        annotation_gt=TypedValue(type="point", value=[12, 34]),
    )

    assert sanitized["execution_trace"] == {"kept": 3}
    assert sanitized["witness_symbolic"] == {"type": "point", "count": 1}
    assert sanitized["projected_annotation"] == {
        "type": "point",
        "point": [12, 34],
        "pixel_point": [12, 34],
    }


def test_annotation_contract_audit_accepts_scalar_shapes_only() -> None:
    assert _validate_annotation_value("point", [12, 34]) == []
    assert _validate_annotation_value("bbox", [10, 20, 30, 40]) == []

    assert _validate_annotation_value("point", [[12, 34]])
    assert _validate_annotation_value("bbox", [[10, 20, 30, 40]])
