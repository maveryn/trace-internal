"""Diagram construction inputs for the area-partition scene."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .relations import selected_probability_map, total_area_from_unit_partition
from .state import AreaPartitionProblem, PartitionCase


PARALLELOGRAM_PARTITION_CASES: tuple[PartitionCase, ...] = (
    ("parallelogram_diagonals_midpoint_eighth", 19, 8),
    ("parallelogram_diagonals_midpoint_eighth", 23, 8),
    ("parallelogram_diagonals_midpoint_eighth", 31, 8),
    ("parallelogram_diagonals_midpoint_eighth", 43, 8),
    ("parallelogram_diagonals_quarter", 37, 4),
    ("parallelogram_diagonals_quarter", 47, 4),
    ("parallelogram_diagonals_quarter", 53, 4),
    ("parallelogram_diagonals_quarter", 61, 4),
    ("parallelogram_diagonals_quarter", 71, 4),
    ("parallelogram_diagonals_quarter", 79, 4),
)

TRIANGLE_PARTITION_CASES: tuple[PartitionCase, ...] = (
    ("triangle_median_half", 68, 2),
    ("triangle_median_half", 84, 2),
    ("triangle_midsegment_quarter", 37, 4),
    ("triangle_midsegment_quarter", 49, 4),
    ("triangle_midsegment_quarter", 62, 4),
    ("triangle_medians_sixth", 23, 6),
    ("triangle_medians_sixth", 31, 6),
    ("triangle_medians_sixth", 43, 6),
    ("triangle_medians_sixth", 57, 6),
)

AREA_PARTITION_CASES: tuple[PartitionCase, ...] = (
    *PARALLELOGRAM_PARTITION_CASES,
    *TRIANGLE_PARTITION_CASES,
)


def resolve_area_partition_problem(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    partition_cases: Sequence[PartitionCase] = AREA_PARTITION_CASES,
    sampling_namespace: str,
) -> AreaPartitionProblem:
    """Resolve one deterministic total-area partition problem."""

    cases = tuple(partition_cases)
    if not cases:
        raise ValueError("area-partition case support must be non-empty")

    case_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(sampling_namespace),
    )
    scene_variant, shaded_area, denominator = cases[int(case_index) % len(cases)]
    scene_variant = str(params.get("scene_variant", scene_variant))
    shaded_area = int(params.get("shaded_area", shaded_area))
    denominator = int(params.get("area_denominator", denominator))

    allowed_variants = {str(case[0]) for case in cases}
    if scene_variant not in allowed_variants:
        raise ValueError(f"unsupported area partition scene_variant: {scene_variant}")

    answer = total_area_from_unit_partition(
        shaded_area=int(shaded_area),
        denominator=int(denominator),
    )
    support_values = tuple(case[1] * case[2] for case in cases)
    return AreaPartitionProblem(
        scene_variant=str(scene_variant),
        answer=float(answer),
        shaded_area=int(shaded_area),
        denominator=int(denominator),
        formula=f"total area = shaded area * {int(denominator)}",
        support_probabilities=selected_probability_map(support_values, float(answer)),
    )


__all__ = [
    "AREA_PARTITION_CASES",
    "PARALLELOGRAM_PARTITION_CASES",
    "TRIANGLE_PARTITION_CASES",
    "resolve_area_partition_problem",
]
