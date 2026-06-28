"""Sampling and validation primitives for rectangular-solid measurements."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.sampling import uniform_choice
from trace.core.seed import spawn_rng
from trace.tasks.shared.fixed_query import (
    geometry_selected_probability_map as _probability_map,
)

CUBOID_DIMENSION_CASES: Tuple[Tuple[int, int, int], ...] = (
    (3, 4, 5),
    (4, 5, 6),
    (3, 6, 7),
    (5, 6, 8),
    (4, 7, 9),
    (6, 8, 9),
    (5, 9, 10),
    (7, 8, 11),
    (6, 10, 12),
    (8, 9, 12),
)
CUBE_EDGE_VALUES: Tuple[int, ...] = tuple(range(2, 13))
PARTIAL_FRAME_EDGE_COUNTS: Tuple[int, ...] = (4, 5, 6, 7, 8)
OPEN_BOX_CASES: Tuple[Tuple[int, int, int], ...] = (
    (10, 8, 2),
    (12, 9, 2),
    (13, 10, 2),
    (14, 10, 3),
    (15, 11, 3),
    (16, 12, 2),
    (17, 13, 3),
    (18, 12, 3),
    (18, 15, 4),
    (20, 14, 4),
)
OPEN_BOX_DIMENSION_ROLES: Tuple[str, ...] = ("base_length", "base_width")


def cuboid_case_key(case: Sequence[int]) -> str:
    """Return a stable trace key for one cuboid dimension case."""

    length, width, height = [int(value) for value in case]
    return f"L{length}_W{width}_H{height}"


def surface_area_for_case(case: Sequence[int]) -> int:
    """Compute total surface area for one cuboid dimension case."""

    length, width, height = [int(value) for value in case]
    return int(2 * ((length * width) + (length * height) + (width * height)))


def open_box_values_for_case(case: Sequence[int]) -> tuple[int, int, int, int, int, int]:
    """Return sheet, cut, base, and volume values for one open-box case."""

    sheet_length, sheet_width, cut_size = [int(value) for value in case]
    base_length = int(sheet_length - 2 * cut_size)
    base_width = int(sheet_width - 2 * cut_size)
    volume = int(base_length * base_width * cut_size)
    return sheet_length, sheet_width, cut_size, base_length, base_width, volume


def open_box_case_key(case: Sequence[int]) -> str:
    """Return a stable trace key for one open-box net case."""

    sheet_length, sheet_width, cut_size = [int(value) for value in case]
    return f"sheet{sheet_length}x{sheet_width}_cut{cut_size}"


def probability_map_for_support(support: Sequence[int | str], *, selected: int | str) -> Dict[str, float]:
    """Return the selected-value probability map used in task traces."""

    return _probability_map(tuple(support), selected=selected)


def select_cuboid_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    sampling_label: str,
) -> tuple[Tuple[int, int, int], Dict[str, float]]:
    """Select or validate one cuboid dimension triple."""

    explicit_dimensions = params.get("dimensions")
    explicit_dimension_fields = any(key in params for key in ("length_units", "width_units", "height_units"))
    if explicit_dimensions is not None or explicit_dimension_fields:
        if explicit_dimensions is not None:
            if (
                not isinstance(explicit_dimensions, Sequence)
                or isinstance(explicit_dimensions, (str, bytes))
                or len(explicit_dimensions) != 3
            ):
                raise ValueError("dimensions must be [length, width, height]")
            length, width, height = [int(value) for value in explicit_dimensions]
        else:
            missing = [key for key in ("length_units", "width_units", "height_units") if key not in params]
            if missing:
                raise ValueError(f"explicit cuboid dimensions require all three fields; missing {missing}")
            length = int(params["length_units"])
            width = int(params["width_units"])
            height = int(params["height_units"])
        case = (length, width, height)
        validate_dimensions(case)
        return case, {cuboid_case_key(case): 1.0}

    rng = spawn_rng(int(instance_seed), f"{sampling_label}.cuboid_case")
    case = uniform_choice(rng, CUBOID_DIMENSION_CASES)
    probability = 1.0 / float(len(CUBOID_DIMENSION_CASES))
    return case, {cuboid_case_key(candidate): probability for candidate in CUBOID_DIMENSION_CASES}


def select_cube_edge(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    sampling_label: str,
) -> tuple[int, Dict[str, float]]:
    """Select or validate one cube edge length."""

    explicit_edge = params.get("edge_units")
    if explicit_edge is not None:
        edge = int(explicit_edge)
        validate_cube_edge(edge)
        return edge, {str(edge): 1.0}
    rng = spawn_rng(int(instance_seed), f"{sampling_label}.cube_edge")
    edge = int(uniform_choice(rng, CUBE_EDGE_VALUES))
    probability = 1.0 / float(len(CUBE_EDGE_VALUES))
    return edge, {str(candidate): probability for candidate in CUBE_EDGE_VALUES}


def select_partial_frame_edge_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    sampling_label: str,
) -> tuple[int, Dict[str, float]]:
    """Select or validate the number of highlighted cube-frame edges."""

    explicit_count = params.get("highlighted_edge_count")
    if explicit_count is not None:
        count = int(explicit_count)
        if count not in PARTIAL_FRAME_EDGE_COUNTS:
            raise ValueError("highlighted_edge_count must be one of 4, 5, 6, 7, or 8")
        return count, {str(count): 1.0}
    rng = spawn_rng(int(instance_seed), f"{sampling_label}.partial_frame_edge_count")
    count = int(uniform_choice(rng, PARTIAL_FRAME_EDGE_COUNTS))
    probability = 1.0 / float(len(PARTIAL_FRAME_EDGE_COUNTS))
    return count, {str(candidate): probability for candidate in PARTIAL_FRAME_EDGE_COUNTS}


def select_open_box_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    sampling_label: str,
) -> tuple[Tuple[int, int, int], Dict[str, float]]:
    """Select or validate one corner-cut open-box net case."""

    explicit_case = params.get("open_box_case")
    explicit_fields = any(key in params for key in ("sheet_length_units", "sheet_width_units", "cut_size_units"))
    if explicit_case is not None or explicit_fields:
        if explicit_case is not None:
            if not isinstance(explicit_case, Sequence) or isinstance(explicit_case, (str, bytes)) or len(explicit_case) != 3:
                raise ValueError("open_box_case must be [sheet_length, sheet_width, cut_size]")
            case = tuple(int(value) for value in explicit_case)
        else:
            missing = [key for key in ("sheet_length_units", "sheet_width_units", "cut_size_units") if key not in params]
            if missing:
                raise ValueError(f"explicit open-box dimensions require all three fields; missing {missing}")
            case = (int(params["sheet_length_units"]), int(params["sheet_width_units"]), int(params["cut_size_units"]))
        validate_open_box_case(case)
        return case, {open_box_case_key(case): 1.0}
    rng = spawn_rng(int(instance_seed), f"{sampling_label}.open_box_case")
    case = uniform_choice(rng, OPEN_BOX_CASES)
    probability = 1.0 / float(len(OPEN_BOX_CASES))
    return case, {open_box_case_key(candidate): probability for candidate in OPEN_BOX_CASES}


def select_open_box_dimension_role(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    sampling_label: str,
) -> tuple[str, Dict[str, float]]:
    """Select or validate the requested resulting base dimension role."""

    explicit_role = params.get("target_dimension_role")
    if explicit_role is not None:
        role = str(explicit_role)
        if role not in OPEN_BOX_DIMENSION_ROLES:
            raise ValueError("target_dimension_role must be base_length or base_width")
        return role, probability_map_for_support(OPEN_BOX_DIMENSION_ROLES, selected=role)
    rng = spawn_rng(int(instance_seed), f"{sampling_label}.target_dimension_role")
    role = str(uniform_choice(rng, OPEN_BOX_DIMENSION_ROLES))
    return str(role), _probability_map(OPEN_BOX_DIMENSION_ROLES)


def validate_dimensions(case: Sequence[int]) -> None:
    """Validate explicit cuboid dimensions."""

    length, width, height = [int(value) for value in case]
    if min(length, width, height) <= 0:
        raise ValueError("cuboid dimensions must be positive integers")
    if max(length, width, height) > 60:
        raise ValueError("cuboid dimensions are too large for this renderer")


def validate_cube_edge(edge: int) -> None:
    """Validate explicit cube edge length."""

    if int(edge) not in CUBE_EDGE_VALUES:
        raise ValueError("edge_units must be an integer from 2 to 12")


def validate_open_box_case(case: Sequence[int]) -> None:
    """Validate explicit open-box sheet and cut dimensions."""

    sheet_length, sheet_width, cut_size, base_length, base_width, _volume = open_box_values_for_case(case)
    if min(sheet_length, sheet_width, cut_size) <= 0:
        raise ValueError("open-box sheet dimensions and cut size must be positive integers")
    if base_length < 3 or base_width < 3:
        raise ValueError("open-box resulting base dimensions must each be at least 3")
    if max(sheet_length, sheet_width) > 40:
        raise ValueError("open-box sheet dimensions are too large for this renderer")


__all__ = [
    "CUBE_EDGE_VALUES",
    "CUBOID_DIMENSION_CASES",
    "OPEN_BOX_CASES",
    "OPEN_BOX_DIMENSION_ROLES",
    "PARTIAL_FRAME_EDGE_COUNTS",
    "cuboid_case_key",
    "open_box_case_key",
    "open_box_values_for_case",
    "probability_map_for_support",
    "select_cube_edge",
    "select_cuboid_case",
    "select_open_box_case",
    "select_open_box_dimension_role",
    "select_partial_frame_edge_count",
    "surface_area_for_case",
    "validate_cube_edge",
    "validate_dimensions",
    "validate_open_box_case",
]
