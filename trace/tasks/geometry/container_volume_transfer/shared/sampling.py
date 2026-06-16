"""Case pools and neutral case selection for container-transfer diagrams."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .measurements import (
    case_probability_map,
    cone_source_volume,
    cylinder_source_volume,
    json_answer_value,
    resolve_cone_fill_count,
    resolve_cone_resulting_height,
    resolve_cylinder_fill_count,
    resolve_cylinder_resulting_height,
    resolve_target_capacity,
    resolve_transferred_volume,
    round1,
    validate_cone_fill_case,
    validate_cone_height_case,
    validate_cylinder_fill_case,
    validate_cylinder_height_case,
    validate_target_capacity_case,
    validate_transferred_volume_case,
)

_CASES_PER_ANSWER = 16


def _answer_key(value: int | float) -> str:
    return str(json_answer_value(value))


def _answer_sort_key(key: str) -> tuple[int, float | str]:
    try:
        return (0, float(key))
    except ValueError:
        return (1, str(key))


def _append_case(
    grouped: dict[str, list[Tuple[int, ...]]],
    answer: int | float,
    case: Sequence[int],
) -> None:
    key = _answer_key(answer)
    if len(grouped[key]) < _CASES_PER_ANSWER:
        grouped[key].append(tuple(int(value) for value in case))


def _flatten_grouped(grouped: Mapping[str, Sequence[Sequence[int]]]) -> Tuple[Tuple[int, ...], ...]:
    return tuple(
        tuple(int(value) for value in case)
        for key in sorted(grouped, key=_answer_sort_key)
        for case in tuple(grouped[str(key)])
    )


def _generate_cone_fill_cases() -> Tuple[Tuple[int, int, int, int], ...]:
    grouped: dict[str, list[Tuple[int, ...]]] = defaultdict(list)
    for fill_count in range(2, 21):
        for source_base_area in range(6, 61):
            for source_height in range(3, 31):
                if int(source_base_area * source_height) % 3:
                    continue
                source_volume = cone_source_volume(source_base_area, source_height)
                if not (12 <= int(source_volume) <= 220):
                    continue
                target_volume = int(source_volume) * int(fill_count)
                for target_base_area in range(6, 81):
                    if target_volume % target_base_area:
                        continue
                    target_height = target_volume // target_base_area
                    if 4 <= int(target_height) <= 32:
                        case = (source_base_area, source_height, target_base_area, target_height)
                        try:
                            validate_cone_fill_case(case)
                        except ValueError:
                            continue
                        _append_case(grouped, fill_count, case)
                        break
                if len(grouped[_answer_key(fill_count)]) >= _CASES_PER_ANSWER:
                    break
            if len(grouped[_answer_key(fill_count)]) >= _CASES_PER_ANSWER:
                break
    return _flatten_grouped(grouped)


def _generate_cylinder_fill_cases() -> Tuple[Tuple[int, int, int, int, int], ...]:
    grouped: dict[str, list[Tuple[int, ...]]] = defaultdict(list)
    for fill_count in range(2, 21):
        for source_base_area in range(4, 61):
            for source_height in range(2, 31):
                source_volume = cylinder_source_volume(source_base_area, source_height)
                if not (12 <= int(source_volume) <= 220):
                    continue
                target_volume = int(source_volume) * int(fill_count)
                found = False
                for target_length in range(4, 31):
                    for target_width in range(3, 18):
                        target_base_area = int(target_length) * int(target_width)
                        if target_volume % target_base_area:
                            continue
                        target_height = target_volume // target_base_area
                        if 3 <= int(target_height) <= 32:
                            case = (source_base_area, source_height, target_length, target_width, target_height)
                            try:
                                validate_cylinder_fill_case(case)
                            except ValueError:
                                continue
                            _append_case(grouped, fill_count, case)
                            found = True
                            break
                    if found:
                        break
                if len(grouped[_answer_key(fill_count)]) >= _CASES_PER_ANSWER:
                    break
            if len(grouped[_answer_key(fill_count)]) >= _CASES_PER_ANSWER:
                break
    return _flatten_grouped(grouped)


def _generate_cone_height_cases() -> Tuple[Tuple[int, int, int, int, int], ...]:
    grouped: dict[str, list[Tuple[int, ...]]] = defaultdict(list)
    for source_base_area in range(6, 91):
        for source_height in range(3, 31):
            if int(source_base_area * source_height) % 3:
                continue
            source_volume = cone_source_volume(source_base_area, source_height)
            if not (10 <= int(source_volume) <= 260):
                continue
            for pour_count in range(1, 11):
                total_volume = int(source_volume) * int(pour_count)
                for target_base_area in range(6, 101):
                    result = round1(float(total_volume) / float(target_base_area))
                    if not (1.5 <= float(result) <= 24.0):
                        continue
                    target_height = max(4, int(float(result) / 0.85) + 2)
                    if target_height <= 36:
                        case = (source_base_area, source_height, target_base_area, target_height, pour_count)
                        try:
                            validate_cone_height_case(case)
                        except ValueError:
                            continue
                        _append_case(grouped, result, case)
    return _flatten_grouped(grouped)


def _generate_cylinder_height_cases() -> Tuple[Tuple[int, int, int, int, int, int], ...]:
    grouped: dict[str, list[Tuple[int, ...]]] = defaultdict(list)
    for source_base_area in range(4, 81):
        for source_height in range(2, 31):
            source_volume = cylinder_source_volume(source_base_area, source_height)
            if not (10 <= int(source_volume) <= 260):
                continue
            for pour_count in range(1, 11):
                total_volume = int(source_volume) * int(pour_count)
                for target_length in range(4, 31):
                    for target_width in range(3, 18):
                        target_base_area = int(target_length) * int(target_width)
                        result = round1(float(total_volume) / float(target_base_area))
                        if not (1.5 <= float(result) <= 24.0):
                            continue
                        target_height = max(4, int(float(result) / 0.85) + 2)
                        if target_height <= 36:
                            case = (source_base_area, source_height, target_length, target_width, target_height, pour_count)
                            try:
                                validate_cylinder_height_case(case)
                            except ValueError:
                                continue
                            _append_case(
                                grouped,
                                result,
                                case,
                            )
    return _flatten_grouped(grouped)


def _generate_target_capacity_cases() -> Tuple[Tuple[int, int, int, int, int], ...]:
    grouped: dict[str, list[Tuple[int, ...]]] = defaultdict(list)
    for source_kind in (0, 1):
        for target_kind in (0, 1):
            for source_base_area in range(6, 81):
                for source_height in range(3, 31):
                    if int(source_kind) == 0 and int(source_base_area * source_height) % 3:
                        continue
                    source_volume = (
                        cone_source_volume(source_base_area, source_height)
                        if int(source_kind) == 0
                        else cylinder_source_volume(source_base_area, source_height)
                    )
                    if not (8 <= int(source_volume) <= 180):
                        continue
                    for pour_count in range(2, 16):
                        target_volume = int(source_volume) * int(pour_count)
                        if 40 <= int(target_volume) <= 600:
                            case = (source_kind, target_kind, source_base_area, source_height, pour_count)
                            try:
                                validate_target_capacity_case(case)
                            except ValueError:
                                continue
                            _append_case(grouped, target_volume, case)
    return _flatten_grouped(grouped)


def _generate_transferred_volume_cases() -> Tuple[Tuple[int, int, int, int, int], ...]:
    grouped: dict[str, list[Tuple[int, ...]]] = defaultdict(list)
    for source_kind in (0, 1):
        for target_kind in (0, 1):
            for source_base_area in range(6, 91):
                for source_height in range(3, 32):
                    if int(source_kind) == 0 and int(source_base_area * source_height) % 3:
                        continue
                    source_volume = (
                        cone_source_volume(source_base_area, source_height)
                        if int(source_kind) == 0
                        else cylinder_source_volume(source_base_area, source_height)
                    )
                    if not (8 <= int(source_volume) <= 180):
                        continue
                    for pour_count in range(2, 16):
                        total_volume = int(source_volume) * int(pour_count)
                        if 60 <= int(total_volume) <= 720:
                            case = (source_kind, target_kind, source_base_area, source_height, pour_count)
                            try:
                                validate_transferred_volume_case(case, required_source_kind=int(source_kind))
                            except ValueError:
                                continue
                            _append_case(grouped, total_volume, case)
    return _flatten_grouped(grouped)


CONE_FILL_CASES = _generate_cone_fill_cases()
CYLINDER_FILL_CASES = _generate_cylinder_fill_cases()
CONE_HEIGHT_CASES = _generate_cone_height_cases()
CYLINDER_HEIGHT_CASES = _generate_cylinder_height_cases()
TARGET_CAPACITY_CASES = _generate_target_capacity_cases()
TRANSFERRED_VOLUME_CASES = _generate_transferred_volume_cases()


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
    answer_fn: Callable[[Sequence[int]], int | float],
    expected_length: int,
) -> tuple[Tuple[int, ...], Dict[str, float]]:
    """Select a transfer construction by answer first, preserving explicit replay cases.

    The invariant is that normal sampling is uniform over attainable final
    answers for the objective pool, then uniform over constructions that realize
    that answer. Explicit `transfer_case` remains an exact replay override.
    """

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
    grouped: dict[str, list[Tuple[int, ...]]] = defaultdict(list)
    for candidate in cases:
        grouped[_answer_key(answer_fn(candidate))].append(tuple(int(value) for value in candidate))
    answer_keys = tuple(sorted(grouped, key=_answer_sort_key))
    if not answer_keys:
        raise ValueError("answer-first container case support must not be empty")
    explicit_answer = params.get("target_answer")
    if explicit_answer is not None:
        answer_key = _answer_key(float(explicit_answer))
        if answer_key not in grouped:
            raise ValueError(f"target_answer={explicit_answer} is not supported")
    else:
        answer_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{namespace}.answer") % len(answer_keys)
        answer_key = answer_keys[int(answer_index)]
    candidates = tuple(grouped[str(answer_key)])
    case_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{namespace}.case.{answer_key}") % len(candidates)
    case = tuple(int(value) for value in candidates[int(case_index)])
    return case, {str(key_fn(case)): 1.0}


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
        answer_fn=lambda case: resolve_cone_fill_count(case).fill_count,
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
        answer_fn=lambda case: resolve_cylinder_fill_count(case).fill_count,
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
        answer_fn=lambda case: resolve_cone_resulting_height(case).answer,
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
        answer_fn=lambda case: resolve_cylinder_resulting_height(case).answer,
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
        answer_fn=lambda case: resolve_target_capacity(case).target_volume,
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
        answer_fn=lambda case: resolve_transferred_volume(case).answer,
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
        answer_fn=lambda case: resolve_transferred_volume(case).answer,
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
