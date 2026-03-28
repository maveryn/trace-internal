"""Unit tests for shared geometry complexity helpers."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.geometry.shared.complexity import build_geometry_comparison_complexity


def test_geometry_comparison_complexity_increases_with_scan_and_ambiguity() -> None:
    defaults = get_task_group_defaults("geometry", "comparison")

    easier = build_geometry_comparison_complexity(
        task_group_defaults=defaults,
        task_id="task_geometry_comparison_length",
        object_count=4,
        object_count_min=4,
        object_count_max=6,
        gap_normalized=0.85,
        min_normalized_gap=0.2,
        comparison_kind="length",
        evidence_point_count=2,
    )
    harder = build_geometry_comparison_complexity(
        task_group_defaults=defaults,
        task_id="task_geometry_comparison_length",
        object_count=6,
        object_count_min=4,
        object_count_max=6,
        gap_normalized=0.2,
        min_normalized_gap=0.2,
        comparison_kind="length",
        evidence_point_count=2,
    )

    assert 0.0 <= float(easier.complexity_score) <= 1.0
    assert 0.0 <= float(harder.complexity_score) <= 1.0
    assert float(harder.complexity_score) > float(easier.complexity_score)
    assert set(harder.complexity_components.keys()) == {
        "visual_scan",
        "comparison_reasoning",
        "ambiguity",
        "output_burden",
    }
