"""Sampling primitives for numbered icon pattern grids."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....shared.config_defaults import group_default
from ....shared.deterministic_sampling import resolve_selection_index, uniform_probability_map

from .defaults import DEFAULT_COLOR_LADDER_RGB, DEFAULT_COLOR_NAMES, PatternGridDefaults
from .state import ATTRIBUTE_AXES, PatternGridSpec


_DEFAULTS = PatternGridDefaults()


def _int_sequence_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[int],
    label: str,
) -> Tuple[int, ...]:
    raw = params.get(key, group_default(defaults, key, list(fallback)))
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{label} must be a sequence")
    values = tuple(int(value) for value in raw)
    if not values:
        raise ValueError(f"{label} must contain at least one value")
    return values


def _color_ladder_rgb(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Tuple[Tuple[int, int, int], ...]:
    raw = params.get("color_ladder_rgb", group_default(defaults, "color_ladder_rgb", DEFAULT_COLOR_LADDER_RGB))
    if not isinstance(raw, (list, tuple)):
        raise ValueError("color_ladder_rgb must be a sequence")
    colors: List[Tuple[int, int, int]] = []
    for color in raw:
        if not isinstance(color, (list, tuple)) or len(color) != 3:
            raise ValueError("each color_ladder_rgb entry must be an RGB triplet")
        colors.append(tuple(max(0, min(255, int(channel))) for channel in color))
    if len(colors) < 4:
        raise ValueError("color_ladder_rgb must contain at least four colors")
    return tuple(colors)


def _color_level_names(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    color_count: int,
) -> Tuple[str, ...]:
    raw = params.get("color_level_names", group_default(defaults, "color_level_names", DEFAULT_COLOR_NAMES))
    if not isinstance(raw, (list, tuple)):
        raise ValueError("color_level_names must be a sequence")
    names = tuple(str(value).strip() or f"color_{index}" for index, value in enumerate(raw))
    if len(names) < int(color_count):
        names = tuple([*names, *[f"color_{index}" for index in range(len(names), int(color_count))]])
    return tuple(names[: int(color_count)])


def _grid_pattern(
    *,
    base_level: int,
    row_step_levels: int,
    col_step_levels: int,
    grid_rows: int,
    grid_cols: int,
) -> Tuple[int, ...]:
    levels: List[int] = []
    for row in range(int(grid_rows)):
        for col in range(int(grid_cols)):
            levels.append(int(base_level) + int(row) * int(row_step_levels) + int(col) * int(col_step_levels))
    return tuple(int(value) for value in levels)


def _violation_explanations(
    observed_levels: Sequence[int],
    *,
    grid_rows: int,
    grid_cols: int,
    level_support: Sequence[int],
    base_candidates: Sequence[int],
    row_step_candidates: Sequence[int],
    col_step_candidates: Sequence[int],
) -> Tuple[bool, set[int], Dict[int, int]]:
    """Enumerate one-mismatch explanations over the configured affine grid rules.

    This keeps sampled instances visually unambiguous: a candidate is accepted
    only when exactly one numbered cell can explain every valid row/column
    pattern rule, and that cell is the intended answer.
    """

    exact_match = False
    plausible_indices: set[int] = set()
    rule_counts: Counter[int] = Counter()
    allowed = {int(level) for level in level_support}
    observed = tuple(int(value) for value in observed_levels)
    for base_level in base_candidates:
        for row_step in row_step_candidates:
            for col_step in col_step_candidates:
                if int(row_step) == 0 and int(col_step) == 0:
                    continue
                expected = _grid_pattern(
                    base_level=int(base_level),
                    row_step_levels=int(row_step),
                    col_step_levels=int(col_step),
                    grid_rows=int(grid_rows),
                    grid_cols=int(grid_cols),
                )
                if any(int(level) not in allowed for level in expected):
                    continue
                mismatches = [
                    int(index)
                    for index, (observed_level, expected_level) in enumerate(zip(observed, expected))
                    if int(observed_level) != int(expected_level)
                ]
                if not mismatches:
                    exact_match = True
                elif len(mismatches) == 1:
                    mismatch = int(mismatches[0])
                    plausible_indices.add(mismatch)
                    rule_counts[mismatch] += 1
    return bool(exact_match), plausible_indices, {int(key): int(value) for key, value in rule_counts.items()}


def _axis_support(
    attribute_axis: str,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
) -> Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], int]:
    """Resolve finite symbolic supports for a semantic visual attribute axis.

    The public task file maps query ids to the neutral ``color`` or ``size``
    axis first; shared sampling then receives only that semantic axis and never
    branches on public query ids or task identities.
    """

    if str(attribute_axis) == "size":
        level_support = tuple(
            dict.fromkeys(
                _int_sequence_param(
                    params,
                    defaults,
                    key="size_levels",
                    fallback=_DEFAULTS.size_levels,
                    label="size_levels",
                )
            )
        )
        if len(level_support) < 3:
            raise ValueError("size_levels must contain at least three distinct levels")
        base_candidates = _int_sequence_param(
            params,
            defaults,
            key="base_size_level_candidates",
            fallback=level_support,
            label="base_size_level_candidates",
        )
        base_candidates = tuple(int(value) for value in base_candidates if int(value) in set(level_support))
        row_steps = _int_sequence_param(
            params,
            defaults,
            key="row_step_size_candidates",
            fallback=_DEFAULTS.row_step_size_candidates,
            label="row_step_size_candidates",
        )
        col_steps = _int_sequence_param(
            params,
            defaults,
            key="col_step_size_candidates",
            fallback=_DEFAULTS.col_step_size_candidates,
            label="col_step_size_candidates",
        )
        min_delta = int(
            params.get(
                "min_violation_level_delta",
                group_default(defaults, "min_violation_level_delta", _DEFAULTS.min_violation_level_delta),
            )
        )
        if int(min_delta) < 1:
            raise ValueError("min_violation_level_delta must be >= 1")
        return level_support, base_candidates, row_steps, col_steps, int(min_delta)

    raise ValueError(f"unsupported pattern-grid attribute_axis: {attribute_axis}")


def _color_level_support(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
) -> Tuple[int, ...]:
    color_count = len(_color_ladder_rgb(params, defaults))
    levels = _int_sequence_param(
        params,
        defaults,
        key="color_levels",
        fallback=tuple(range(int(color_count))),
        label="color_levels",
    )
    allowed = set(range(int(color_count)))
    level_support = tuple(int(level) for level in dict.fromkeys(levels) if int(level) in allowed)
    if len(level_support) < 4:
        raise ValueError("color_levels must contain at least four valid distinct levels")
    return level_support


def _color_uniform_pattern(
    *,
    color_group_axis: str,
    grid_rows: int,
    grid_cols: int,
    violation_cell_index: int,
    level_support: Sequence[int],
    base_index: int,
    params: Mapping[str, Any],
) -> Tuple[Tuple[int, ...], Tuple[int, ...], int, Tuple[int, ...], int]:
    """Return a row- or column-uniform color pattern with one changed cell."""

    group_axis = str(color_group_axis)
    if group_axis not in {"row", "column"}:
        raise ValueError("color_group_axis must be 'row' or 'column'")
    group_count = int(grid_rows if group_axis == "row" else grid_cols)
    support = tuple(int(value) for value in level_support)
    if len(support) < int(group_count) + 1:
        raise ValueError("color_levels must include at least one spare color beyond the row/column colors")

    explicit_key = "row_color_levels" if group_axis == "row" else "column_color_levels"
    explicit_group_levels = params.get(explicit_key)
    if explicit_group_levels is not None:
        if not isinstance(explicit_group_levels, (list, tuple)):
            raise ValueError(f"{explicit_key} must be a sequence")
        group_levels = tuple(int(value) for value in explicit_group_levels)
        if len(group_levels) != int(group_count):
            raise ValueError(f"{explicit_key} must contain exactly {group_count} values")
        if len(set(group_levels)) != int(group_count) or any(level not in set(support) for level in group_levels):
            raise ValueError(f"{explicit_key} values must be distinct supported color levels")
    else:
        valid_strides = [
            int(stride)
            for stride in range(1, len(support))
            if len({int((index * stride) % len(support)) for index in range(int(group_count))}) == int(group_count)
        ]
        if not valid_strides:
            raise ValueError("no valid color sampling stride available")
        pattern_index = int(base_index)
        start = int(pattern_index % len(support))
        stride = int(valid_strides[int(pattern_index // len(support)) % len(valid_strides)])
        group_levels = tuple(
            int(support[int((start + index * stride) % len(support))])
            for index in range(int(group_count))
        )

    expected = []
    for index in range(int(grid_rows * grid_cols)):
        row = int(index // int(grid_cols))
        col = int(index % int(grid_cols))
        group_index = int(row if group_axis == "row" else col)
        expected.append(int(group_levels[int(group_index)]))

    expected_level = int(expected[int(violation_cell_index)])
    explicit_violation_level = params.get("violation_color_level")
    if explicit_violation_level is not None:
        violation_level = int(explicit_violation_level)
        if int(violation_level) not in set(support):
            raise ValueError("violation_color_level must be in color_levels")
        if int(violation_level) == int(expected_level):
            raise ValueError("violation_color_level must differ from the expected color")
    else:
        spare_levels = [int(level) for level in support if int(level) not in set(group_levels)]
        if not spare_levels:
            spare_levels = [int(level) for level in support if int(level) != int(expected_level)]
        if not spare_levels:
            raise ValueError("no valid violation color level available")
        violation_level = int(spare_levels[int(base_index // max(1, len(support))) % len(spare_levels)])

    observed = list(int(value) for value in expected)
    observed[int(violation_cell_index)] = int(violation_level)
    total_rule_support = int(len(support) * max(1, len(support) - 1))
    return (
        tuple(int(value) for value in expected),
        tuple(int(value) for value in observed),
        int(violation_level),
        tuple(int(value) for value in group_levels),
        int(total_rule_support),
    )


def resolve_pattern_grid_spec(
    *,
    attribute_axis: str,
    color_group_axis: str = "",
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    namespace: str,
) -> PatternGridSpec:
    """Resolve one unambiguous numbered grid pattern for a semantic axis."""

    axis = str(attribute_axis)
    if axis not in set(ATTRIBUTE_AXES):
        raise ValueError(f"attribute_axis must be one of {ATTRIBUTE_AXES}")

    grid_rows = int(params.get("grid_rows", group_default(generation_defaults, "grid_rows", _DEFAULTS.grid_rows)))
    grid_cols = int(params.get("grid_cols", group_default(generation_defaults, "grid_cols", _DEFAULTS.grid_cols)))
    if int(grid_rows) <= 0 or int(grid_cols) <= 0:
        raise ValueError("grid_rows and grid_cols must be positive")
    cell_count = int(grid_rows * grid_cols)
    answer_min = int(
        params.get("answer_index_min", group_default(generation_defaults, "answer_index_min", _DEFAULTS.answer_index_min))
    )
    answer_max = int(
        params.get("answer_index_max", group_default(generation_defaults, "answer_index_max", _DEFAULTS.answer_index_max))
    )
    if int(answer_min) < 1 or int(answer_max) < int(answer_min) or int(answer_max) > int(cell_count):
        raise ValueError("answer index range must be within the visible grid")
    answer_support = tuple(range(int(answer_min), int(answer_max) + 1))
    base_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.{axis}.pattern_spec",
    )

    explicit_answer_index = params.get("answer_index")
    explicit_violation_cell_index = params.get("violation_cell_index")
    if explicit_answer_index is not None and explicit_violation_cell_index is not None:
        if int(explicit_answer_index) != int(explicit_violation_cell_index) + 1:
            raise ValueError("answer_index must equal violation_cell_index + 1")
    if explicit_answer_index is not None:
        answer_index = int(explicit_answer_index)
    elif explicit_violation_cell_index is not None:
        answer_index = int(explicit_violation_cell_index) + 1
    else:
        answer_index = int(answer_support[int(base_index % len(answer_support))])
    if int(answer_index) not in set(answer_support):
        raise ValueError("answer_index is outside configured support")
    violation_cell_index = int(answer_index) - 1

    rotation_candidates = tuple(
        int(value) % 360
        for value in _int_sequence_param(
            params,
            generation_defaults,
            key="shared_rotation_candidates_degrees",
            fallback=_DEFAULTS.shared_rotation_candidates_degrees,
            label="shared_rotation_candidates_degrees",
        )
    )
    if not rotation_candidates:
        raise ValueError("shared_rotation_candidates_degrees must not be empty")

    if axis == "color":
        explicit_group_axis = params.get("color_group_axis", color_group_axis)
        if explicit_group_axis:
            group_axis = str(explicit_group_axis)
        else:
            group_axis_options = ("row", "column")
            group_axis = str(group_axis_options[int(base_index % len(group_axis_options))])
        level_support = _color_level_support(params, generation_defaults)
        expected, observed, violation_level, group_levels, total_rule_support = _color_uniform_pattern(
            color_group_axis=str(group_axis),
            grid_rows=int(grid_rows),
            grid_cols=int(grid_cols),
            violation_cell_index=int(violation_cell_index),
            level_support=level_support,
            base_index=int(base_index // max(1, len(answer_support) * max(1, 2 if not explicit_group_axis else 1))),
            params=params,
        )
        explicit_rotation = params.get("shared_rotation_degrees")
        rotation_index = int(base_index // max(1, len(answer_support) * int(total_rule_support) * max(1, 2 if not explicit_group_axis else 1))) % len(rotation_candidates)
        rotation = int(explicit_rotation) % 360 if explicit_rotation is not None else int(rotation_candidates[int(rotation_index)])
        color_ladder = _color_ladder_rgb(params, generation_defaults)
        color_names = _color_level_names(params, generation_defaults, color_count=len(color_ladder))
        pattern_rule = "row_uniform_color" if str(group_axis) == "row" else "column_uniform_color"
        return PatternGridSpec(
            attribute_axis=axis,
            grid_rows=int(grid_rows),
            grid_cols=int(grid_cols),
            answer_index=int(answer_index),
            violation_cell_index=int(violation_cell_index),
            expected_levels=tuple(int(value) for value in expected),
            observed_levels=tuple(int(value) for value in observed),
            base_level=int(group_levels[0]),
            row_step_levels=0,
            col_step_levels=0,
            violation_level=int(violation_level),
            pattern_rule=str(pattern_rule),
            shared_rotation_degrees=int(rotation),
            level_support=tuple(int(value) for value in level_support),
            plausible_rule_count=1,
            total_rule_support=int(total_rule_support * max(1, 2 if not explicit_group_axis else 1)),
            answer_index_probabilities=uniform_probability_map(answer_support),
            color_group_axis=str(group_axis),
            level_names=tuple(str(value) for value in color_names),
            color_ladder_rgb=tuple(tuple(int(channel) for channel in color) for color in color_ladder),
        )

    level_support, base_candidates, row_steps, col_steps, min_delta = _axis_support(axis, params, generation_defaults)
    if not base_candidates:
        raise ValueError("base level candidates must overlap level support")

    explicit_base = params.get("base_size_level")
    explicit_row_step = params.get("row_step_levels")
    explicit_col_step = params.get("col_step_levels")
    explicit_violation_level = params.get("violation_size_level")
    explicit_rotation = params.get("shared_rotation_degrees")

    allowed = {int(value) for value in level_support}
    feasible: List[Tuple[int, int, int, int, Tuple[int, ...], Tuple[int, ...], int]] = []
    for base_level in base_candidates:
        if explicit_base is not None and int(base_level) != int(explicit_base):
            continue
        for row_step in row_steps:
            if explicit_row_step is not None and int(row_step) != int(explicit_row_step):
                continue
            for col_step in col_steps:
                if explicit_col_step is not None and int(col_step) != int(explicit_col_step):
                    continue
                if int(row_step) == 0 and int(col_step) == 0:
                    continue
                expected = _grid_pattern(
                    base_level=int(base_level),
                    row_step_levels=int(row_step),
                    col_step_levels=int(col_step),
                    grid_rows=int(grid_rows),
                    grid_cols=int(grid_cols),
                )
                if any(int(level) not in allowed for level in expected):
                    continue
                if len(set(int(value) for value in expected)) < 3:
                    continue
                expected_level = int(expected[int(violation_cell_index)])
                for violation_level in level_support:
                    if explicit_violation_level is not None and int(violation_level) != int(explicit_violation_level):
                        continue
                    if int(violation_level) == int(expected_level):
                        continue
                    if abs(int(violation_level) - int(expected_level)) < int(min_delta):
                        continue
                    observed = list(int(value) for value in expected)
                    observed[int(violation_cell_index)] = int(violation_level)
                    exact, plausible, rule_counts = _violation_explanations(
                        observed,
                        grid_rows=int(grid_rows),
                        grid_cols=int(grid_cols),
                        level_support=level_support,
                        base_candidates=base_candidates,
                        row_step_candidates=row_steps,
                        col_step_candidates=col_steps,
                    )
                    if exact or plausible != {int(violation_cell_index)}:
                        continue
                    feasible.append(
                        (
                            int(base_level),
                            int(row_step),
                            int(col_step),
                            int(violation_level),
                            tuple(int(value) for value in expected),
                            tuple(int(value) for value in observed),
                            int(rule_counts.get(int(violation_cell_index), 0)),
                        )
                    )
    if not feasible:
        raise ValueError(f"no unambiguous {axis} pattern grid is feasible")

    combo_index = int(base_index // max(1, len(answer_support))) % len(feasible)
    rotation_index = int(base_index // max(1, len(answer_support) * len(feasible))) % len(rotation_candidates)
    base_level, row_step, col_step, violation_level, expected, observed, plausible_rule_count = feasible[int(combo_index)]
    rotation = int(explicit_rotation) % 360 if explicit_rotation is not None else int(rotation_candidates[int(rotation_index)])
    color_ladder = _color_ladder_rgb(params, generation_defaults) if axis == "color" else ()
    color_names = _color_level_names(params, generation_defaults, color_count=len(color_ladder)) if axis == "color" else ()
    return PatternGridSpec(
        attribute_axis=axis,
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
        answer_index=int(answer_index),
        violation_cell_index=int(violation_cell_index),
        expected_levels=tuple(int(value) for value in expected),
        observed_levels=tuple(int(value) for value in observed),
        base_level=int(base_level),
        row_step_levels=int(row_step),
        col_step_levels=int(col_step),
        violation_level=int(violation_level),
        pattern_rule="row_col_size_level_offsets",
        shared_rotation_degrees=int(rotation),
        level_support=tuple(int(value) for value in level_support),
        plausible_rule_count=int(plausible_rule_count),
        total_rule_support=int(len(base_candidates) * len(row_steps) * len(col_steps)),
        answer_index_probabilities=uniform_probability_map(answer_support),
        level_names=tuple(str(value) for value in color_names),
        color_ladder_rgb=tuple(tuple(int(channel) for channel in color) for color in color_ladder),
    )


__all__ = ["resolve_pattern_grid_spec"]
