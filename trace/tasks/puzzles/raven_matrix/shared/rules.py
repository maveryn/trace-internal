"""Raven-matrix symbolic rule constructors."""

from __future__ import annotations

import json
from itertools import combinations
from typing import Any, Mapping, Sequence

from trace.tasks.puzzles.shared.symbol_rendering import PUZZLE_OBJECT_TYPES
from trace.tasks.shared.mcq import option_label_for_index


COLOR_POOL: tuple[dict[str, Any], ...] = (
    {"name": "blue", "rgb": [74, 127, 214]},
    {"name": "orange", "rgb": [214, 130, 74]},
    {"name": "green", "rgb": [64, 164, 108]},
    {"name": "red", "rgb": [196, 90, 100]},
    {"name": "purple", "rgb": [136, 100, 196]},
    {"name": "gold", "rgb": [205, 162, 62]},
)
TRANSFORM_OPS: tuple[str, ...] = (
    "identity",
    "rot90",
    "rot180",
    "flip_h",
    "flip_v",
)
TRANSFORM_RULES: tuple[tuple[tuple[str, str, str], tuple[str, str, str]], ...] = (
    (("identity", "identity", "identity"), ("identity", "rot90", "rot180")),
    (("identity", "identity", "identity"), ("identity", "flip_h", "flip_v")),
    (("identity", "rot90", "rot180"), ("identity", "identity", "identity")),
    (("identity", "flip_h", "flip_v"), ("identity", "identity", "identity")),
    (("identity", "rot90", "rot180"), ("identity", "flip_h", "flip_v")),
    (("identity", "flip_h", "flip_v"), ("identity", "rot90", "rot180")),
)
BASE_PATTERNS: tuple[tuple[tuple[int, int], ...], ...] = (
    ((0, 0), (0, 1), (1, 1), (2, 1)),
    ((0, 1), (1, 1), (1, 2), (2, 0)),
    ((0, 2), (1, 0), (1, 1), (2, 1)),
    ((0, 0), (1, 0), (1, 2), (2, 1)),
)
SET_OPERATIONS: tuple[str, ...] = ("union", "intersection", "xor")
ANALOGICAL_TRANSFORMS: tuple[str, ...] = (
    "shape_cycle",
    "color_cycle",
    "size_cycle",
)
SIZE_CYCLE: tuple[float, ...] = (0.48, 0.66, 0.84)
POSITION_STEPS: tuple[tuple[int, int], ...] = (
    (1, 0),
    (2, 0),
    (0, 1),
    (0, 2),
    (1, 1),
    (1, 2),
    (2, 1),
    (2, 2),
)


def canonical_panel_spec(panel_spec: Mapping[str, Any]) -> str:
    """Return a stable signature for one Raven panel spec."""

    return json.dumps(panel_spec, sort_keys=True, separators=(",", ":"))


def matrix_rows_from_specs(
    panel_grid: Sequence[Sequence[Mapping[str, Any]]],
) -> list[list[dict[str, Any]]]:
    """Build traced matrix rows with the lower-right cell hidden."""

    rows: list[list[dict[str, Any]]] = []
    for row_index, row in enumerate(panel_grid):
        row_cells: list[dict[str, Any]] = []
        for col_index, panel_spec in enumerate(row):
            is_unknown = bool(row_index == 2 and col_index == 2)
            row_cells.append(
                {
                    "cell_id": f"cell_{row_index}_{col_index}",
                    "row_index": int(row_index),
                    "col_index": int(col_index),
                    "is_unknown": bool(is_unknown),
                    "panel_spec": None if is_unknown else dict(panel_spec),
                }
            )
        rows.append(row_cells)
    return rows


def build_option_specs(
    *,
    correct_panel_spec: Mapping[str, Any],
    distractor_panel_specs: Sequence[Mapping[str, Any]],
    correct_option_index: int,
    option_count: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Build labeled image options with exactly one unique correct panel."""

    correct_signature = canonical_panel_spec(correct_panel_spec)
    unique_distractors: list[dict[str, Any]] = []
    seen = {correct_signature}
    for panel_spec in distractor_panel_specs:
        signature = canonical_panel_spec(panel_spec)
        if signature in seen:
            continue
        seen.add(signature)
        unique_distractors.append(dict(panel_spec))
    if len(unique_distractors) < int(option_count) - 1:
        raise ValueError("not enough unique Raven distractor panels")

    option_panel_specs = [
        dict(spec) for spec in unique_distractors[: int(option_count) - 1]
    ]
    option_panel_specs.insert(int(correct_option_index), dict(correct_panel_spec))
    option_specs: list[dict[str, Any]] = []
    option_labels: list[str] = []
    for option_index, panel_spec in enumerate(option_panel_specs):
        option_label = str(option_label_for_index(int(option_index)))
        option_labels.append(option_label)
        option_specs.append(
            {
                "option_panel_id": f"option_{option_label}",
                "option_index": int(option_index),
                "option_label": str(option_label),
                "panel_spec": dict(panel_spec),
                "panel_signature": canonical_panel_spec(panel_spec),
                "is_correct": bool(option_index == int(correct_option_index)),
            }
        )
    return option_specs, option_labels


def attribute_panel_spec(
    *,
    object_type: str,
    color: Mapping[str, Any],
    size_scale: float = 0.78,
) -> dict[str, Any]:
    """Build one shape/color/size attribute panel spec."""

    return {
        "panel_kind": "attribute",
        "object_type": str(object_type),
        "fill_name": str(color["name"]),
        "fill_rgb": [int(value) for value in color["rgb"]],
        "size_scale": round(float(size_scale), 3),
    }


def count_panel_spec(
    *,
    count: int,
    object_type: str,
    color: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one repeated-object count panel spec."""

    return {
        "panel_kind": "count",
        "object_type": str(object_type),
        "fill_name": str(color["name"]),
        "fill_rgb": [int(value) for value in color["rgb"]],
        "count": int(count),
    }


def build_count_progression_dataset(
    *,
    rng,
    count_min: int,
    count_max: int,
    option_count: int,
    correct_option_index: int,
) -> dict[str, Any]:
    """Construct an additive-count Raven matrix dataset."""

    if int(count_max - count_min + 1) < int(option_count):
        raise ValueError("count support must contain at least option_count values")
    table: list[list[int]] | None = None
    row_terms: list[int] = []
    col_terms: list[int] = []
    base_count = 1
    for _ in range(200):
        row_terms = [int(value) for value in rng.sample(range(0, 4), 3)]
        col_terms = [int(value) for value in rng.sample(range(0, 4), 3)]
        base_count = int(rng.randint(int(count_min), max(int(count_min), int(count_min) + 1)))
        candidate_table = [
            [
                int(base_count + row_terms[row_index] + col_terms[col_index])
                for col_index in range(3)
            ]
            for row_index in range(3)
        ]
        flat_counts = [int(value) for row in candidate_table for value in row]
        if min(flat_counts) >= int(count_min) and max(flat_counts) <= int(count_max):
            table = candidate_table
            break
    if table is None:
        raise RuntimeError("failed to construct count-progression Raven matrix")

    color = dict(rng.choice(COLOR_POOL))
    object_type = str(rng.choice(tuple(PUZZLE_OBJECT_TYPES)))
    panel_grid = [
        [
            count_panel_spec(
                count=int(table[row_index][col_index]),
                object_type=object_type,
                color=color,
            )
            for col_index in range(3)
        ]
        for row_index in range(3)
    ]
    answer_panel_spec = dict(panel_grid[2][2])
    answer_count = int(answer_panel_spec["count"])
    count_support = [
        int(value)
        for value in range(int(count_min), int(count_max) + 1)
        if int(value) != answer_count
    ]
    rng.shuffle(count_support)
    distractors = [
        count_panel_spec(count=int(count), object_type=object_type, color=color)
        for count in count_support
    ]
    option_specs, option_labels = build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": matrix_rows_from_specs(panel_grid),
        "matrix_panel_specs": [[dict(spec) for spec in row] for row in panel_grid],
        "answer_panel_spec": dict(answer_panel_spec),
        "answer_count": int(answer_count),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(option_specs[correct_option_index]["option_panel_id"]),
        "answer_option_label": str(option_label_for_index(correct_option_index)),
        "option_specs": option_specs,
        "option_labels": option_labels,
        "option_count": int(option_count),
        "solver_trace": {
            "rule_type": "count_progression_matrix",
            "count_rule": "count = base + row_term + column_term",
            "base_count": int(base_count),
            "row_terms": [int(value) for value in row_terms],
            "column_terms": [int(value) for value in col_terms],
            "count_table": [[int(value) for value in row] for row in table],
            "target_row_index": 2,
            "target_col_index": 2,
            "answer_count": int(answer_count),
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
        },
    }


def transform_coord(row: int, col: int, op: str) -> tuple[int, int]:
    """Apply one D4 transform to a 3x3 pattern coordinate."""

    r = int(row)
    c = int(col)
    if op == "identity":
        return r, c
    if op == "rot90":
        return c, 2 - r
    if op == "rot180":
        return 2 - r, 2 - c
    if op == "flip_h":
        return r, 2 - c
    if op == "flip_v":
        return 2 - r, c
    raise ValueError(f"unsupported Raven transform op: {op}")


def apply_transform(
    coords: Sequence[Sequence[int]],
    op: str,
) -> tuple[tuple[int, int], ...]:
    """Apply one transform op to a coordinate set."""

    return tuple(
        sorted(
            transform_coord(int(row), int(col), str(op))
            for row, col in coords
        )
    )


def apply_transform_sequence(
    coords: Sequence[Sequence[int]],
    ops: Sequence[str],
) -> tuple[tuple[int, int], ...]:
    """Apply a sequence of transform ops to a coordinate set."""

    transformed: tuple[tuple[int, int], ...] = tuple(
        sorted((int(row), int(col)) for row, col in coords)
    )
    for op in ops:
        transformed = apply_transform(transformed, str(op))
    return tuple(sorted(transformed))


def pattern_panel_spec(
    *,
    cells: Sequence[Sequence[int]],
    color: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one spatial pattern panel spec."""

    return {
        "panel_kind": "pattern",
        "grid_size": 3,
        "fill_name": str(color["name"]),
        "fill_rgb": [int(value) for value in color["rgb"]],
        "cells": [
            [int(row), int(col)]
            for row, col in sorted((int(r), int(c)) for r, c in cells)
        ],
    }


def all_grid_cells() -> list[tuple[int, int]]:
    """Return all coordinates in a 3x3 mini-grid."""

    return [(int(row), int(col)) for row in range(3) for col in range(3)]


def sample_cell_set(
    *,
    rng,
    min_count: int = 2,
    max_count: int = 5,
) -> tuple[tuple[int, int], ...]:
    """Sample one nonempty 3x3 cell subset."""

    count = int(rng.randint(int(min_count), int(max_count)))
    return tuple(sorted(rng.sample(all_grid_cells(), int(count))))


def random_pattern_distractor_specs(
    *,
    target_cells: Sequence[Sequence[int]],
    color: Mapping[str, Any],
    rng,
    min_count: int = 1,
    max_count: int = 5,
    target_count: int = 12,
) -> list[dict[str, Any]]:
    """Build unique random pattern distractor specs around a target."""

    target_spec = pattern_panel_spec(cells=target_cells, color=color)
    seen = {canonical_panel_spec(target_spec)}
    specs: list[dict[str, Any]] = []
    candidate_sets: list[tuple[tuple[int, int], ...]] = []
    for count in range(int(min_count), int(max_count) + 1):
        candidate_sets.extend(
            tuple(sorted(cells))
            for cells in combinations(all_grid_cells(), int(count))
        )
    rng.shuffle(candidate_sets)
    for cells in candidate_sets:
        spec = pattern_panel_spec(cells=cells, color=color)
        signature = canonical_panel_spec(spec)
        if signature in seen:
            continue
        seen.add(signature)
        specs.append(spec)
        if len(specs) >= int(target_count):
            break
    return specs


def spatial_distractor_specs(
    *,
    target_cells: Sequence[Sequence[int]],
    base_cells: Sequence[Sequence[int]],
    color: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build unique spatial-transform distractors."""

    target_signature = canonical_panel_spec(
        pattern_panel_spec(cells=target_cells, color=color)
    )
    specs: list[dict[str, Any]] = []
    seen = {target_signature}
    for op in TRANSFORM_OPS:
        spec = pattern_panel_spec(cells=apply_transform(base_cells, op), color=color)
        signature = canonical_panel_spec(spec)
        if signature not in seen:
            seen.add(signature)
            specs.append(spec)
    target_set = {(int(row), int(col)) for row, col in target_cells}
    for row_index in range(3):
        for col_index in range(3):
            toggled = set(target_set)
            coord = (int(row_index), int(col_index))
            if coord in toggled:
                if len(toggled) <= 3:
                    continue
                toggled.remove(coord)
            else:
                if len(toggled) >= 5:
                    continue
                toggled.add(coord)
            spec = pattern_panel_spec(cells=sorted(toggled), color=color)
            signature = canonical_panel_spec(spec)
            if signature not in seen:
                seen.add(signature)
                specs.append(spec)
    return specs


def build_spatial_transform_dataset(
    *,
    rng,
    option_count: int,
    correct_option_index: int,
) -> dict[str, Any]:
    """Construct a spatial-transform Raven matrix dataset."""

    base_cells = tuple(tuple(coord) for coord in rng.choice(BASE_PATTERNS))
    row_ops, col_ops = rng.choice(TRANSFORM_RULES)
    color = dict(rng.choice(COLOR_POOL))
    panel_grid = [
        [
            pattern_panel_spec(
                cells=apply_transform_sequence(
                    base_cells,
                    (row_ops[row_index], col_ops[col_index]),
                ),
                color=color,
            )
            for col_index in range(3)
        ]
        for row_index in range(3)
    ]
    answer_panel_spec = dict(panel_grid[2][2])
    target_cells = tuple(tuple(coord) for coord in answer_panel_spec["cells"])
    distractors = spatial_distractor_specs(
        target_cells=target_cells,
        base_cells=base_cells,
        color=color,
    )
    rng.shuffle(distractors)
    option_specs, option_labels = build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": matrix_rows_from_specs(panel_grid),
        "matrix_panel_specs": [[dict(spec) for spec in row] for row in panel_grid],
        "answer_panel_spec": dict(answer_panel_spec),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(option_specs[correct_option_index]["option_panel_id"]),
        "answer_option_label": str(option_label_for_index(correct_option_index)),
        "option_specs": option_specs,
        "option_labels": option_labels,
        "option_count": int(option_count),
        "solver_trace": {
            "rule_type": "spatial_transform_matrix",
            "base_cells": [[int(row), int(col)] for row, col in base_cells],
            "row_transforms": [str(value) for value in row_ops],
            "column_transforms": [str(value) for value in col_ops],
            "target_row_index": 2,
            "target_col_index": 2,
            "answer_cells": [[int(row), int(col)] for row, col in target_cells],
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
        },
    }


def apply_set_operation(
    left_cells: Sequence[Sequence[int]],
    right_cells: Sequence[Sequence[int]],
    operation: str,
) -> tuple[tuple[int, int], ...]:
    """Apply one cell-set operation over two 3x3 mini-grid patterns."""

    left = {(int(row), int(col)) for row, col in left_cells}
    right = {(int(row), int(col)) for row, col in right_cells}
    if operation == "union":
        result = left | right
    elif operation == "intersection":
        result = left & right
    elif operation == "xor":
        result = left ^ right
    else:
        raise ValueError(f"unsupported Raven set operation: {operation}")
    return tuple(sorted(result))


def set_operation_matches(
    left_cells: Sequence[Sequence[int]],
    right_cells: Sequence[Sequence[int]],
    result_cells: Sequence[Sequence[int]],
) -> list[str]:
    """Return set operations that map two inputs to the target result."""

    target = tuple(sorted((int(row), int(col)) for row, col in result_cells))
    return [
        str(operation)
        for operation in SET_OPERATIONS
        if apply_set_operation(left_cells, right_cells, str(operation)) == target
    ]


def build_set_operation_dataset(
    *,
    rng,
    option_count: int,
    correct_option_index: int,
) -> dict[str, Any]:
    """Construct a row-wise set-operation Raven matrix dataset."""

    operation = str(rng.choice(SET_OPERATIONS))
    color = dict(rng.choice(COLOR_POOL))
    panel_grid: list[list[dict[str, Any]]] | None = None
    row_inputs: list[dict[str, Any]] = []
    for _ in range(400):
        candidate_grid: list[list[dict[str, Any]]] = []
        candidate_inputs: list[dict[str, Any]] = []
        valid = True
        for row_index in range(3):
            row_valid = False
            for _row_attempt in range(120):
                left_cells = sample_cell_set(rng=rng, min_count=2, max_count=5)
                right_cells = sample_cell_set(rng=rng, min_count=2, max_count=5)
                result_cells = apply_set_operation(left_cells, right_cells, operation)
                if not 1 <= len(result_cells) <= 5:
                    continue
                if tuple(result_cells) in {tuple(left_cells), tuple(right_cells)}:
                    continue
                if set_operation_matches(left_cells, right_cells, result_cells) != [operation]:
                    continue
                candidate_grid.append(
                    [
                        pattern_panel_spec(cells=left_cells, color=color),
                        pattern_panel_spec(cells=right_cells, color=color),
                        pattern_panel_spec(cells=result_cells, color=color),
                    ]
                )
                candidate_inputs.append(
                    {
                        "row_index": int(row_index),
                        "left_cells": [[int(row), int(col)] for row, col in left_cells],
                        "right_cells": [[int(row), int(col)] for row, col in right_cells],
                        "result_cells": [[int(row), int(col)] for row, col in result_cells],
                    }
                )
                row_valid = True
                break
            if not row_valid:
                valid = False
                break
        if valid and len(candidate_grid) == 3:
            panel_grid = candidate_grid
            row_inputs = candidate_inputs
            break
    if panel_grid is None:
        raise RuntimeError("failed to construct set-operation Raven matrix")

    answer_panel_spec = dict(panel_grid[2][2])
    target_cells = tuple(tuple(coord) for coord in answer_panel_spec["cells"])
    distractors: list[dict[str, Any]] = []
    row2_left = tuple(tuple(coord) for coord in panel_grid[2][0]["cells"])
    row2_right = tuple(tuple(coord) for coord in panel_grid[2][1]["cells"])
    for alt_operation in SET_OPERATIONS:
        alt_cells = apply_set_operation(row2_left, row2_right, str(alt_operation))
        if 1 <= len(alt_cells) <= 5:
            distractors.append(pattern_panel_spec(cells=alt_cells, color=color))
    distractors.extend(
        dict(panel_grid[row_index][col_index])
        for row_index in range(3)
        for col_index in range(3)
        if not (row_index == 2 and col_index == 2)
    )
    distractors.extend(
        random_pattern_distractor_specs(
            target_cells=target_cells,
            color=color,
            rng=rng,
            min_count=1,
            max_count=5,
            target_count=12,
        )
    )
    rng.shuffle(distractors)
    option_specs, option_labels = build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": matrix_rows_from_specs(panel_grid),
        "matrix_panel_specs": [[dict(spec) for spec in row] for row in panel_grid],
        "answer_panel_spec": dict(answer_panel_spec),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(option_specs[correct_option_index]["option_panel_id"]),
        "answer_option_label": str(option_label_for_index(correct_option_index)),
        "option_specs": option_specs,
        "option_labels": option_labels,
        "option_count": int(option_count),
        "solver_trace": {
            "rule_type": "set_operation_matrix",
            "operation": str(operation),
            "row_inputs": list(row_inputs),
            "target_row_index": 2,
            "target_col_index": 2,
            "answer_cells": [[int(row), int(col)] for row, col in target_cells],
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
        },
    }


def color_by_name(name: str) -> dict[str, Any]:
    """Return one color record by palette name."""

    for color in COLOR_POOL:
        if str(color["name"]) == str(name):
            return dict(color)
    raise ValueError(f"unknown Raven color name: {name}")


def attribute_distractor_specs(
    *,
    target_panel_spec: Mapping[str, Any],
    rng,
) -> list[dict[str, Any]]:
    """Build unique attribute-panel distractors for analogical transforms."""

    target_signature = canonical_panel_spec(target_panel_spec)
    target_color = color_by_name(str(target_panel_spec["fill_name"]))
    target_object_type = str(target_panel_spec["object_type"])
    target_size = float(target_panel_spec.get("size_scale", 0.78))
    specs: list[dict[str, Any]] = []
    seen = {target_signature}

    candidates: list[dict[str, Any]] = []
    for shape in PUZZLE_OBJECT_TYPES:
        candidates.append(
            attribute_panel_spec(
                object_type=str(shape),
                color=target_color,
                size_scale=target_size,
            )
        )
    for color in COLOR_POOL:
        candidates.append(
            attribute_panel_spec(
                object_type=target_object_type,
                color=dict(color),
                size_scale=target_size,
            )
        )
    for size_scale in SIZE_CYCLE:
        candidates.append(
            attribute_panel_spec(
                object_type=target_object_type,
                color=target_color,
                size_scale=float(size_scale),
            )
        )
    for shape in PUZZLE_OBJECT_TYPES:
        for color in COLOR_POOL:
            candidates.append(
                attribute_panel_spec(
                    object_type=str(shape),
                    color=dict(color),
                    size_scale=target_size,
                )
            )
    rng.shuffle(candidates)
    for spec in candidates:
        signature = canonical_panel_spec(spec)
        if signature in seen:
            continue
        seen.add(signature)
        specs.append(spec)
        if len(specs) >= 16:
            break
    return specs


def build_analogical_transform_dataset(
    *,
    rng,
    option_count: int,
    correct_option_index: int,
) -> dict[str, Any]:
    """Construct a row-wise analogical-transform Raven matrix dataset."""

    transform_kind = str(rng.choice(ANALOGICAL_TRANSFORMS))
    shapes = [str(value) for value in PUZZLE_OBJECT_TYPES]
    rng.shuffle(shapes)
    shape_cycle = [str(value) for value in shapes[:3]]
    colors = [dict(value) for value in COLOR_POOL]
    rng.shuffle(colors)
    color_cycle = [dict(value) for value in colors[:3]]
    row_offsets = [0, 1, 2]
    rng.shuffle(row_offsets)

    panel_grid: list[list[dict[str, Any]]] = []
    for row_index in range(3):
        row_specs: list[dict[str, Any]] = []
        for col_index in range(3):
            offset = int((row_offsets[row_index] + col_index) % 3)
            if transform_kind == "shape_cycle":
                object_type = str(shape_cycle[offset])
                color = dict(color_cycle[row_index])
                size_scale = 0.76
            elif transform_kind == "color_cycle":
                object_type = str(shape_cycle[row_index])
                color = dict(color_cycle[offset])
                size_scale = 0.76
            else:
                object_type = str(shape_cycle[row_index])
                color = dict(color_cycle[row_index])
                size_scale = float(SIZE_CYCLE[offset])
            row_specs.append(
                attribute_panel_spec(
                    object_type=object_type,
                    color=color,
                    size_scale=float(size_scale),
                )
            )
        panel_grid.append(row_specs)

    answer_panel_spec = dict(panel_grid[2][2])
    distractors = attribute_distractor_specs(
        target_panel_spec=answer_panel_spec,
        rng=rng,
    )
    distractors.extend(
        dict(panel_grid[row_index][col_index])
        for row_index in range(3)
        for col_index in range(3)
        if not (row_index == 2 and col_index == 2)
    )
    rng.shuffle(distractors)
    option_specs, option_labels = build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": matrix_rows_from_specs(panel_grid),
        "matrix_panel_specs": [[dict(spec) for spec in row] for row in panel_grid],
        "answer_panel_spec": dict(answer_panel_spec),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(option_specs[correct_option_index]["option_panel_id"]),
        "answer_option_label": str(option_label_for_index(correct_option_index)),
        "option_specs": option_specs,
        "option_labels": option_labels,
        "option_count": int(option_count),
        "solver_trace": {
            "rule_type": "analogical_transform_matrix",
            "transform_kind": str(transform_kind),
            "shape_cycle": [str(value) for value in shape_cycle],
            "color_cycle": [str(color["name"]) for color in color_cycle],
            "size_cycle": [float(value) for value in SIZE_CYCLE],
            "row_offsets": [int(value) for value in row_offsets],
            "target_row_index": 2,
            "target_col_index": 2,
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
        },
    }


def independent_mod3_steps(left: Sequence[int], right: Sequence[int]) -> bool:
    """Return whether two 2D mod-3 steps are linearly independent."""

    determinant = (int(left[0]) * int(right[1])) - (int(left[1]) * int(right[0]))
    return int(determinant % 3) != 0


def build_position_progression_dataset(
    *,
    rng,
    option_count: int,
    correct_option_index: int,
) -> dict[str, Any]:
    """Construct a marker-position progression Raven matrix dataset."""

    color = dict(rng.choice(COLOR_POOL))
    base_position = (int(rng.randrange(3)), int(rng.randrange(3)))
    row_step = tuple(rng.choice(POSITION_STEPS))
    col_candidates = [
        step for step in POSITION_STEPS if independent_mod3_steps(row_step, step)
    ]
    col_step = tuple(rng.choice(col_candidates))

    def position_for(row_index: int, col_index: int) -> tuple[int, int]:
        return (
            int((base_position[0] + row_index * row_step[0] + col_index * col_step[0]) % 3),
            int((base_position[1] + row_index * row_step[1] + col_index * col_step[1]) % 3),
        )

    panel_grid = [
        [
            pattern_panel_spec(cells=(position_for(row_index, col_index),), color=color)
            for col_index in range(3)
        ]
        for row_index in range(3)
    ]
    answer_panel_spec = dict(panel_grid[2][2])
    target_position = tuple(answer_panel_spec["cells"][0])
    distractors = [
        pattern_panel_spec(cells=((row_index, col_index),), color=color)
        for row_index in range(3)
        for col_index in range(3)
        if (int(row_index), int(col_index)) != (
            int(target_position[0]),
            int(target_position[1]),
        )
    ]
    rng.shuffle(distractors)
    option_specs, option_labels = build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": matrix_rows_from_specs(panel_grid),
        "matrix_panel_specs": [[dict(spec) for spec in row] for row in panel_grid],
        "answer_panel_spec": dict(answer_panel_spec),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(option_specs[correct_option_index]["option_panel_id"]),
        "answer_option_label": str(option_label_for_index(correct_option_index)),
        "option_specs": option_specs,
        "option_labels": option_labels,
        "option_count": int(option_count),
        "solver_trace": {
            "rule_type": "position_progression_matrix",
            "base_position": [int(base_position[0]), int(base_position[1])],
            "row_step_mod3": [int(row_step[0]), int(row_step[1])],
            "column_step_mod3": [int(col_step[0]), int(col_step[1])],
            "target_row_index": 2,
            "target_col_index": 2,
            "answer_position": [int(target_position[0]), int(target_position[1])],
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
        },
    }


__all__ = [
    "ANALOGICAL_TRANSFORMS",
    "BASE_PATTERNS",
    "COLOR_POOL",
    "POSITION_STEPS",
    "SET_OPERATIONS",
    "SIZE_CYCLE",
    "TRANSFORM_OPS",
    "TRANSFORM_RULES",
    "build_analogical_transform_dataset",
    "build_count_progression_dataset",
    "build_position_progression_dataset",
    "build_set_operation_dataset",
    "build_spatial_transform_dataset",
    "canonical_panel_spec",
]
