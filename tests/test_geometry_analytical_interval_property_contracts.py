"""Contract tests for analytical function interval-property label tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.analytical.function_property_label import (
    GeometryAnalyticalFunctionPropertyLabelTask,
    GeometryAnalyticalRelationPropertyLabelTask,
)


@pytest.mark.parametrize(
    ("task_cls", "query_variant"),
    (
        (GeometryAnalyticalRelationPropertyLabelTask, "monotonic_interval_increasing_label"),
        (GeometryAnalyticalRelationPropertyLabelTask, "monotonic_interval_decreasing_label"),
        (GeometryAnalyticalRelationPropertyLabelTask, "sign_interval_positive_label"),
        (GeometryAnalyticalRelationPropertyLabelTask, "sign_interval_negative_label"),
    ),
)
def test_geometry_analytical_interval_property_tasks_emit_expected_contract(task_cls, query_variant: str) -> None:
    out = task_cls().generate(
        24011,
        params={"query_variant": query_variant, "winner_label": "C"},
        max_attempts=20,
    )

    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert out.query_variant == "default"
    assert out.query_id == query_variant
    assert out.trace_payload["query_spec"]["params"]["query_variant"] == "default"
    assert out.trace_payload["query_spec"]["params"]["query_id"] == query_variant
    expected_interval = "[-2, 2]" if "monotonic" in query_variant else "[-4, 4]"
    assert out.trace_payload["query_spec"]["params"]["target_interval"] == expected_interval
    assert out.trace_payload["execution_trace"]["target_interval"] == expected_interval
    assert out.trace_payload["projected_evidence"]["bbox_set"] == out.evidence_gt.value


def test_geometry_analytical_base_rejects_unknown_interval_property_variant() -> None:
    with pytest.raises(ValueError):
        GeometryAnalyticalFunctionPropertyLabelTask().generate(
            24012,
            params={"query_variant": "positive_interval_label"},
            max_attempts=20,
        )
