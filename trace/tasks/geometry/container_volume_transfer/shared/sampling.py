"""Case pools and neutral case selection for container-transfer diagrams."""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Sequence, Tuple

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .measurements import (
    case_probability_map,
    validate_cone_fill_case,
    validate_cone_height_case,
    validate_cylinder_fill_case,
    validate_cylinder_height_case,
    validate_target_capacity_case,
    validate_transferred_volume_case,
)

CONE_FILL_CASES: Tuple[Tuple[int, int, int, int], ...] = (
    (12, 6, 8, 6),
    (9, 9, 9, 6),
    (15, 6, 10, 9),
    (12, 9, 9, 12),
    (12, 5, 10, 8),
    (15, 4, 10, 10),
    (18, 5, 12, 15),
    (21, 4, 14, 14),
    (24, 3, 12, 16),
)
CYLINDER_FILL_CASES: Tuple[Tuple[int, int, int, int, int], ...] = (
    (6, 5, 5, 4, 3),
    (8, 4, 8, 4, 3),
    (10, 3, 10, 4, 3),
    (9, 4, 9, 5, 4),
    (12, 3, 12, 6, 3),
    (14, 2, 14, 7, 2),
    (8, 5, 10, 8, 4),
)
CONE_HEIGHT_CASES: Tuple[Tuple[int, int, int, int, int], ...] = (
    (12, 6, 8, 9, 1),
    (9, 9, 9, 10, 2),
    (15, 6, 12, 10, 3),
    (12, 9, 8, 12, 2),
    (18, 5, 12, 12, 2),
    (21, 4, 14, 10, 3),
    (24, 3, 12, 10, 2),
    (15, 4, 10, 8, 1),
)
CYLINDER_HEIGHT_CASES: Tuple[Tuple[int, int, int, int, int, int], ...] = (
    (6, 5, 5, 4, 8, 2),
    (8, 4, 8, 4, 7, 2),
    (10, 3, 10, 4, 6, 5),
    (9, 4, 9, 5, 7, 5),
    (12, 3, 9, 4, 8, 5),
    (14, 2, 7, 5, 8, 4),
    (8, 5, 10, 5, 9, 3),
)
TARGET_CAPACITY_CASES: Tuple[Tuple[int, int, int, int, int], ...] = (
    (0, 0, 12, 6, 2),
    (0, 1, 9, 9, 3),
    (0, 0, 15, 6, 4),
    (0, 1, 12, 9, 2),
    (0, 0, 18, 5, 5),
    (1, 1, 7, 4, 3),
    (1, 0, 8, 5, 4),
    (1, 1, 9, 4, 5),
    (1, 0, 11, 3, 3),
    (1, 1, 12, 4, 4),
)
TRANSFERRED_VOLUME_CASES: Tuple[Tuple[int, int, int, int, int], ...] = (
    (0, 0, 12, 6, 4),
    (0, 1, 15, 6, 3),
    (0, 0, 18, 5, 5),
    (0, 1, 21, 4, 6),
    (0, 0, 24, 3, 5),
    (1, 1, 8, 5, 3),
    (1, 0, 9, 4, 5),
    (1, 1, 11, 3, 4),
    (1, 0, 12, 4, 6),
    (1, 1, 14, 3, 5),
)


def _cone_case_key(case: Sequence[int]) -> str:
    source_base_area, source_height, target_base_area, target_height = [int(value) for value in case]
    return f"cone_B{source_base_area}_H{source_height}_cyl_B{target_base_area}_H{target_height}"


def _cuboid_case_key(case: Sequence[int]) -> str:
    source_base_area, source_height, target_length, target_width, target_height = [int(value) for value in case]
    return f"cyl_B{source_base_area}_H{source_height}_cuboid_L{target_length}_W{target_width}_H{target_height}"


def _cone_height_case_key(case: Sequence[int]) -> str:
    source_base_area, source_height, target_base_area, target_height, pour_count = [int(value) for value in case]
    return f"cone_B{source_base_area}_H{source_height}_cyl_B{target_base_area}_H{target_height}_n{pour_count}"


def _cuboid_height_case_key(case: Sequence[int]) -> str:
    source_base_area, source_height, target_length, target_width, target_height, pour_count = [int(value) for value in case]
    return f"cyl_B{source_base_area}_H{source_height}_cuboid_L{target_length}_W{target_width}_H{target_height}_n{pour_count}"


def _kind_case_key(case: Sequence[int], *, total: bool = False) -> str:
    source_kind, target_kind, source_base_area, source_height, pour_count = [int(value) for value in case]
    source_prefix = "cone" if source_kind == 0 else "cyl"
    target_prefix = "cyl" if target_kind == 0 else "cuboid"
    total_part = "_total" if bool(total) else ""
    return f"{source_prefix}_B{source_base_area}_H{source_height}_{target_prefix}{total_part}_n{pour_count}"


def select_case_from_pool(
    *,
    cases: Sequence[Sequence[int]],
    keys: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    validator: Callable[[Sequence[int]], None],
    key_fn: Callable[[Sequence[int]], str],
    expected_length: int,
) -> tuple[Tuple[int, ...], Dict[str, float]]:
    explicit = params.get("transfer_case")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise ValueError("transfer_case must be a numeric sequence")
        case = tuple(int(value) for value in explicit)
        if len(case) != int(expected_length):
            raise ValueError(f"transfer_case must have {expected_length} values")
        validator(case)
        selected_key = str(key_fn(case))
        return case, case_probability_map(tuple(dict.fromkeys(tuple(keys) + (selected_key,))), selected_key)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    case = tuple(int(value) for value in cases[int(index) % len(cases)])
    return case, {str(key): 1.0 / float(max(1, len(keys))) for key in keys}


def select_cone_fill_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(CONE_FILL_CASES)
    keys = tuple(_cone_case_key(case) for case in cases)
    return select_case_from_pool(
        cases=cases,
        keys=keys,
        params=params,
        instance_seed=instance_seed,
        namespace=f"{namespace}.cone_case",
        validator=validate_cone_fill_case,
        key_fn=_cone_case_key,
        expected_length=4,
    )


def select_cylinder_fill_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(CYLINDER_FILL_CASES)
    keys = tuple(_cuboid_case_key(case) for case in cases)
    return select_case_from_pool(
        cases=cases,
        keys=keys,
        params=params,
        instance_seed=instance_seed,
        namespace=f"{namespace}.cuboid_case",
        validator=validate_cylinder_fill_case,
        key_fn=_cuboid_case_key,
        expected_length=5,
    )


def select_cone_height_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(CONE_HEIGHT_CASES)
    keys = tuple(_cone_height_case_key(case) for case in cases)
    return select_case_from_pool(
        cases=cases,
        keys=keys,
        params=params,
        instance_seed=instance_seed,
        namespace=f"{namespace}.cone_height_case",
        validator=validate_cone_height_case,
        key_fn=_cone_height_case_key,
        expected_length=5,
    )


def select_cylinder_height_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(CYLINDER_HEIGHT_CASES)
    keys = tuple(_cuboid_height_case_key(case) for case in cases)
    return select_case_from_pool(
        cases=cases,
        keys=keys,
        params=params,
        instance_seed=instance_seed,
        namespace=f"{namespace}.cuboid_height_case",
        validator=validate_cylinder_height_case,
        key_fn=_cuboid_height_case_key,
        expected_length=6,
    )


def select_target_capacity_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(TARGET_CAPACITY_CASES)
    keys = tuple(_kind_case_key(case) for case in cases)
    return select_case_from_pool(
        cases=cases,
        keys=keys,
        params=params,
        instance_seed=instance_seed,
        namespace=f"{namespace}.target_capacity_case",
        validator=validate_target_capacity_case,
        key_fn=_kind_case_key,
        expected_length=5,
    )


def select_repeated_cone_volume_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(case for case in TRANSFERRED_VOLUME_CASES if int(case[0]) == 0)
    keys = tuple(_kind_case_key(case, total=True) for case in cases)
    return select_case_from_pool(
        cases=cases,
        keys=keys,
        params=params,
        instance_seed=instance_seed,
        namespace=f"{namespace}.transferred_cone_case",
        validator=lambda case: validate_transferred_volume_case(case, required_source_kind=0),
        key_fn=lambda case: _kind_case_key(case, total=True),
        expected_length=5,
    )


def select_repeated_cylinder_volume_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(case for case in TRANSFERRED_VOLUME_CASES if int(case[0]) == 1)
    keys = tuple(_kind_case_key(case, total=True) for case in cases)
    return select_case_from_pool(
        cases=cases,
        keys=keys,
        params=params,
        instance_seed=instance_seed,
        namespace=f"{namespace}.transferred_cylinder_case",
        validator=lambda case: validate_transferred_volume_case(case, required_source_kind=1),
        key_fn=lambda case: _kind_case_key(case, total=True),
        expected_length=5,
    )


__all__ = [
    "CONE_FILL_CASES",
    "CONE_HEIGHT_CASES",
    "CYLINDER_FILL_CASES",
    "CYLINDER_HEIGHT_CASES",
    "TARGET_CAPACITY_CASES",
    "TRANSFERRED_VOLUME_CASES",
    "select_cone_fill_case",
    "select_cone_height_case",
    "select_cylinder_fill_case",
    "select_cylinder_height_case",
    "select_repeated_cone_volume_case",
    "select_repeated_cylinder_volume_case",
    "select_target_capacity_case",
]
