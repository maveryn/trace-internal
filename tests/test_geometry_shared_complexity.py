"""Unit tests for shared geometry complexity helpers."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.geometry.shared.complexity import (
    build_geometry_comparison_complexity,
    build_geometry_counting_complexity,
    build_geometry_measurement_complexity,
)


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


def test_geometry_counting_complexity_increases_with_scan_density_and_burden() -> None:
    defaults = get_task_group_defaults("geometry", "counting")

    easier = build_geometry_counting_complexity(
        task_group_defaults=defaults,
        task_id="task_geometry_counting_angle",
        object_count=6,
        object_count_min=6,
        object_count_max=10,
        target_count=1,
        task_kind="angle",
        task_variant="acute_angle",
    )
    harder = build_geometry_counting_complexity(
        task_group_defaults=defaults,
        task_id="task_geometry_counting_angle",
        object_count=10,
        object_count_min=6,
        object_count_max=10,
        target_count=5,
        task_kind="angle",
        task_variant="right_angle",
    )

    assert 0.0 <= float(easier.complexity_score) <= 1.0
    assert 0.0 <= float(harder.complexity_score) <= 1.0
    assert float(harder.complexity_score) > float(easier.complexity_score)
    assert set(harder.complexity_components.keys()) == {
        "visual_scan",
        "classification_reasoning",
        "ambiguity",
        "output_burden",
    }


def test_geometry_measurement_complexity_weights_active_components() -> None:
    defaults = get_task_group_defaults("geometry", "measurement")

    easier = build_geometry_measurement_complexity(
        task_group_defaults=defaults,
        task_id="task_geometry_measurement_angle",
        visual_scan=0.30,
        measurement_precision=0.25,
        ambiguity=0.20,
        output_burden=0.25,
    )
    harder = build_geometry_measurement_complexity(
        task_group_defaults=defaults,
        task_id="task_geometry_measurement_angle",
        visual_scan=0.60,
        measurement_precision=0.80,
        ambiguity=0.55,
        output_burden=0.35,
    )

    assert 0.0 <= float(easier.complexity_score) <= 1.0
    assert 0.0 <= float(harder.complexity_score) <= 1.0
    assert float(harder.complexity_score) > float(easier.complexity_score)
    assert set(harder.complexity_components.keys()) == {
        "visual_scan",
        "measurement_precision",
        "ambiguity",
        "output_burden",
    }
