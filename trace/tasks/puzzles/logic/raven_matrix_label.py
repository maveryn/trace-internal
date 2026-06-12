"""Puzzle logic task that completes a Raven-style matrix using image options."""

from __future__ import annotations

import json
from dataclasses import replace
from itertools import combinations
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.common import decouple_axis_sampling, projected_puzzle_bbox_annotation, resolve_puzzle_axis_variant
from trace.tasks.shared.fixed_query import FixedPuzzleQueryVariantTaskMixin
from ..shared.logic_common import PuzzleLogicDefaults, resolve_logic_render_params
from ..shared.raven_scene import SUPPORTED_PUZZLE_RAVEN_SCENE_VARIANTS, render_puzzle_raven_scene
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.symbol_rendering import PUZZLE_OBJECT_TYPES
from ..shared.unit_size_jitter import with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


TASK_ID = "puzzles_logic_raven_matrix_internal"
RAVEN_COUNT_PROGRESSION_LABEL_TASK_ID = "task_puzzles__raven_matrix__raven_count_progression_label"
RAVEN_SPATIAL_TRANSFORM_LABEL_TASK_ID = "task_puzzles__raven_matrix__raven_spatial_transform_label"
RAVEN_SET_OPERATION_LABEL_TASK_ID = "task_puzzles__raven_matrix__raven_set_operation_label"
RAVEN_ANALOGICAL_TRANSFORM_LABEL_TASK_ID = "task_puzzles__raven_matrix__raven_analogical_transform_label"
RAVEN_POSITION_PROGRESSION_LABEL_TASK_ID = "task_puzzles__raven_matrix__raven_position_progression_label"
SCENE_ID = "raven_matrix"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "count_progression_matrix",
    "spatial_transform_matrix",
    "set_operation_matrix",
    "analogical_transform_matrix",
    "position_progression_matrix",
)
_QUERY_ID_REASONING_LOAD = {
    "count_progression_matrix": 0.56,
    "spatial_transform_matrix": 0.78,
    "set_operation_matrix": 0.72,
    "analogical_transform_matrix": 0.62,
    "position_progression_matrix": 0.66,
}
_SCENE_LOAD_BY_VARIANT = {
    "raven_strip": 0.18,
    "raven_card": 0.24,
    "raven_outline": 0.20,
}
_COLOR_POOL: Tuple[Dict[str, Any], ...] = (
    {"name": "blue", "rgb": [74, 127, 214]},
    {"name": "orange", "rgb": [214, 130, 74]},
    {"name": "green", "rgb": [64, 164, 108]},
    {"name": "red", "rgb": [196, 90, 100]},
    {"name": "purple", "rgb": [136, 100, 196]},
    {"name": "gold", "rgb": [205, 162, 62]},
)
_TRANSFORM_OPS: Tuple[str, ...] = (
    "identity",
    "rot90",
    "rot180",
    "flip_h",
    "flip_v",
)
_TRANSFORM_RULES: Tuple[Tuple[Tuple[str, str, str], Tuple[str, str, str]], ...] = (
    (("identity", "identity", "identity"), ("identity", "rot90", "rot180")),
    (("identity", "identity", "identity"), ("identity", "flip_h", "flip_v")),
    (("identity", "rot90", "rot180"), ("identity", "identity", "identity")),
    (("identity", "flip_h", "flip_v"), ("identity", "identity", "identity")),
    (("identity", "rot90", "rot180"), ("identity", "flip_h", "flip_v")),
    (("identity", "flip_h", "flip_v"), ("identity", "rot90", "rot180")),
)
_BASE_PATTERNS: Tuple[Tuple[Tuple[int, int], ...], ...] = (
    ((0, 0), (0, 1), (1, 1), (2, 1)),
    ((0, 1), (1, 1), (1, 2), (2, 0)),
    ((0, 2), (1, 0), (1, 1), (2, 1)),
    ((0, 0), (1, 0), (1, 2), (2, 1)),
)
_SET_OPERATIONS: Tuple[str, ...] = ("union", "intersection", "xor")
_ANALOGICAL_TRANSFORMS: Tuple[str, ...] = ("shape_cycle", "color_cycle", "size_cycle")
_SIZE_CYCLE: Tuple[float, ...] = (0.48, 0.66, 0.84)
_POSITION_STEPS: Tuple[Tuple[int, int], ...] = (
    (1, 0),
    (2, 0),
    (0, 1),
    (0, 2),
    (1, 1),
    (1, 2),
    (2, 1),
    (2, 2),
)

_DEFAULTS = PuzzleLogicDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("puzzles", "logic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id="logic", apply_prob=0.0)


def _canonical_panel_spec(panel_spec: Mapping[str, Any]) -> str:
    """Return a stable signature for one panel spec."""

    return json.dumps(panel_spec, sort_keys=True, separators=(",", ":"))


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the Raven matrix semantic variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the Raven matrix visual scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_RAVEN_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_correct_option_index(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    query_id: str,
    option_count: int,
) -> int:
    """Pick a deterministic correct option index with sampler-time label balance."""

    explicit = params.get("correct_option_index")
    if explicit is not None:
        index = int(explicit)
        if not 0 <= index < int(option_count):
            raise ValueError("correct_option_index must fall inside the option-count range")
        return int(index)
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:{query_id}:correct_option_index",
        )
    )
    return int(selection % int(option_count))


def _matrix_rows_from_specs(panel_grid: Sequence[Sequence[Mapping[str, Any]]]) -> List[List[Dict[str, Any]]]:
    """Build traced matrix rows with the lower-right cell hidden."""

    rows: List[List[Dict[str, Any]]] = []
    for row_index, row in enumerate(panel_grid):
        row_cells: List[Dict[str, Any]] = []
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


def _build_option_specs(
    *,
    correct_panel_spec: Mapping[str, Any],
    distractor_panel_specs: Sequence[Mapping[str, Any]],
    correct_option_index: int,
    option_count: int,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Build six labeled options with one unique correct panel."""

    correct_signature = _canonical_panel_spec(correct_panel_spec)
    unique_distractors: List[Dict[str, Any]] = []
    seen = {correct_signature}
    for panel_spec in distractor_panel_specs:
        signature = _canonical_panel_spec(panel_spec)
        if signature in seen:
            continue
        seen.add(signature)
        unique_distractors.append(dict(panel_spec))
    if len(unique_distractors) < int(option_count) - 1:
        raise ValueError("not enough unique Raven distractor panels")

    option_panel_specs = [dict(spec) for spec in unique_distractors[: int(option_count) - 1]]
    option_panel_specs.insert(int(correct_option_index), dict(correct_panel_spec))
    option_specs: List[Dict[str, Any]] = []
    option_labels: List[str] = []
    for option_index, panel_spec in enumerate(option_panel_specs):
        option_label = str(option_label_for_index(int(option_index)))
        option_labels.append(option_label)
        option_specs.append(
            {
                "option_panel_id": f"option_{option_label}",
                "option_index": int(option_index),
                "option_label": str(option_label),
                "panel_spec": dict(panel_spec),
                "panel_signature": _canonical_panel_spec(panel_spec),
                "is_correct": bool(option_index == int(correct_option_index)),
            }
        )
    return option_specs, option_labels


def _attribute_panel_spec(*, object_type: str, color: Mapping[str, Any], size_scale: float = 0.78) -> Dict[str, Any]:
    """Build one attribute-binding panel spec."""

    return {
        "panel_kind": "attribute",
        "object_type": str(object_type),
        "fill_name": str(color["name"]),
        "fill_rgb": [int(value) for value in color["rgb"]],
        "size_scale": round(float(size_scale), 3),
    }


def _count_panel_spec(*, count: int, object_type: str, color: Mapping[str, Any]) -> Dict[str, Any]:
    """Build one count-progression panel spec."""

    return {
        "panel_kind": "count",
        "object_type": str(object_type),
        "fill_name": str(color["name"]),
        "fill_rgb": [int(value) for value in color["rgb"]],
        "count": int(count),
    }


def _build_count_progression_dataset(
    *,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
) -> Dict[str, Any]:
    """Construct an additive-count Raven matrix dataset."""

    count_min = int(params.get("count_min", group_default(_GEN_DEFAULTS, "count_min", 1)))
    count_max = int(params.get("count_max", group_default(_GEN_DEFAULTS, "count_max", 8)))
    if int(count_max - count_min + 1) < int(option_count):
        raise ValueError("count support must contain at least option_count distinct values")
    table: List[List[int]] | None = None
    row_terms: List[int] = []
    col_terms: List[int] = []
    base_count = 1
    for _ in range(200):
        row_terms = [int(value) for value in rng.sample(range(0, 4), 3)]
        col_terms = [int(value) for value in rng.sample(range(0, 4), 3)]
        base_count = int(rng.randint(count_min, max(count_min, count_min + 1)))
        candidate_table = [
            [int(base_count + row_terms[row_index] + col_terms[col_index]) for col_index in range(3)]
            for row_index in range(3)
        ]
        flat_counts = [int(value) for row in candidate_table for value in row]
        if min(flat_counts) >= count_min and max(flat_counts) <= count_max:
            table = candidate_table
            break
    if table is None:
        raise RuntimeError("failed to construct count-progression Raven matrix")

    color = dict(rng.choice(_COLOR_POOL))
    object_type = str(rng.choice(tuple(PUZZLE_OBJECT_TYPES)))
    panel_grid = [
        [
            _count_panel_spec(count=int(table[row_index][col_index]), object_type=object_type, color=color)
            for col_index in range(3)
        ]
        for row_index in range(3)
    ]
    answer_panel_spec = dict(panel_grid[2][2])
    answer_count = int(answer_panel_spec["count"])
    count_support = [int(value) for value in range(count_min, count_max + 1) if int(value) != answer_count]
    rng.shuffle(count_support)
    distractors = [
        _count_panel_spec(count=int(count), object_type=object_type, color=color)
        for count in count_support
    ]
    correct_option_index = _resolve_correct_option_index(
        params,
        instance_seed=int(instance_seed),
        query_id="count_progression_matrix",
        option_count=int(option_count),
    )
    option_specs, option_labels = _build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": _matrix_rows_from_specs(panel_grid),
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


def _transform_coord(row: int, col: int, op: str) -> Tuple[int, int]:
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


def _apply_transform(coords: Sequence[Sequence[int]], op: str) -> Tuple[Tuple[int, int], ...]:
    """Apply one transform op to a coordinate set."""

    return tuple(sorted(_transform_coord(int(row), int(col), str(op)) for row, col in coords))


def _apply_transform_sequence(coords: Sequence[Sequence[int]], ops: Sequence[str]) -> Tuple[Tuple[int, int], ...]:
    """Apply a sequence of transform ops to a coordinate set."""

    transformed: Tuple[Tuple[int, int], ...] = tuple(sorted((int(row), int(col)) for row, col in coords))
    for op in ops:
        transformed = _apply_transform(transformed, str(op))
    return tuple(sorted(transformed))


def _pattern_panel_spec(*, cells: Sequence[Sequence[int]], color: Mapping[str, Any]) -> Dict[str, Any]:
    """Build one spatial-transform pattern panel spec."""

    return {
        "panel_kind": "pattern",
        "grid_size": 3,
        "fill_name": str(color["name"]),
        "fill_rgb": [int(value) for value in color["rgb"]],
        "cells": [[int(row), int(col)] for row, col in sorted((int(r), int(c)) for r, c in cells)],
    }


def _all_grid_cells() -> List[Tuple[int, int]]:
    """Return all cell coordinates in a 3x3 mini-grid."""

    return [(int(row), int(col)) for row in range(3) for col in range(3)]


def _sample_cell_set(
    *,
    rng,
    min_count: int = 2,
    max_count: int = 5,
) -> Tuple[Tuple[int, int], ...]:
    """Sample one nonempty 3x3 cell subset."""

    count = int(rng.randint(int(min_count), int(max_count)))
    return tuple(sorted(rng.sample(_all_grid_cells(), int(count))))


def _random_pattern_distractor_specs(
    *,
    target_cells: Sequence[Sequence[int]],
    color: Mapping[str, Any],
    rng,
    min_count: int = 1,
    max_count: int = 5,
    target_count: int = 12,
) -> List[Dict[str, Any]]:
    """Build unique random pattern distractor specs around a target."""

    target_spec = _pattern_panel_spec(cells=target_cells, color=color)
    seen = {_canonical_panel_spec(target_spec)}
    specs: List[Dict[str, Any]] = []
    candidate_sets: List[Tuple[Tuple[int, int], ...]] = []
    for count in range(int(min_count), int(max_count) + 1):
        candidate_sets.extend(tuple(sorted(cells)) for cells in combinations(_all_grid_cells(), int(count)))
    rng.shuffle(candidate_sets)
    for cells in candidate_sets:
        spec = _pattern_panel_spec(cells=cells, color=color)
        signature = _canonical_panel_spec(spec)
        if signature in seen:
            continue
        seen.add(signature)
        specs.append(spec)
        if len(specs) >= int(target_count):
            break
    return specs


def _spatial_distractor_specs(
    *,
    target_cells: Sequence[Sequence[int]],
    base_cells: Sequence[Sequence[int]],
    color: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Build unique spatial-transform distractors."""

    target_signature = _canonical_panel_spec(_pattern_panel_spec(cells=target_cells, color=color))
    specs: List[Dict[str, Any]] = []
    seen = {target_signature}
    for op in _TRANSFORM_OPS:
        spec = _pattern_panel_spec(cells=_apply_transform(base_cells, op), color=color)
        signature = _canonical_panel_spec(spec)
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
            spec = _pattern_panel_spec(cells=sorted(toggled), color=color)
            signature = _canonical_panel_spec(spec)
            if signature not in seen:
                seen.add(signature)
                specs.append(spec)
    return specs


def _build_spatial_transform_dataset(
    *,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
) -> Dict[str, Any]:
    """Construct a spatial-transform Raven matrix dataset."""

    base_cells = tuple(tuple(coord) for coord in rng.choice(_BASE_PATTERNS))
    row_ops, col_ops = rng.choice(_TRANSFORM_RULES)
    color = dict(rng.choice(_COLOR_POOL))
    panel_grid = [
        [
            _pattern_panel_spec(
                cells=_apply_transform_sequence(base_cells, (row_ops[row_index], col_ops[col_index])),
                color=color,
            )
            for col_index in range(3)
        ]
        for row_index in range(3)
    ]
    answer_panel_spec = dict(panel_grid[2][2])
    target_cells = tuple(tuple(coord) for coord in answer_panel_spec["cells"])
    distractors = _spatial_distractor_specs(target_cells=target_cells, base_cells=base_cells, color=color)
    rng.shuffle(distractors)
    correct_option_index = _resolve_correct_option_index(
        params,
        instance_seed=int(instance_seed),
        query_id="spatial_transform_matrix",
        option_count=int(option_count),
    )
    option_specs, option_labels = _build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": _matrix_rows_from_specs(panel_grid),
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


def _apply_set_operation(
    left_cells: Sequence[Sequence[int]],
    right_cells: Sequence[Sequence[int]],
    operation: str,
) -> Tuple[Tuple[int, int], ...]:
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


def _set_operation_matches(
    left_cells: Sequence[Sequence[int]],
    right_cells: Sequence[Sequence[int]],
    result_cells: Sequence[Sequence[int]],
) -> List[str]:
    """Return set operations that map the two inputs to the result."""

    target = tuple(sorted((int(row), int(col)) for row, col in result_cells))
    return [
        str(operation)
        for operation in _SET_OPERATIONS
        if _apply_set_operation(left_cells, right_cells, str(operation)) == target
    ]


def _build_set_operation_dataset(
    *,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
) -> Dict[str, Any]:
    """Construct a row-wise set-operation Raven matrix dataset."""

    operation = str(rng.choice(_SET_OPERATIONS))
    color = dict(rng.choice(_COLOR_POOL))
    panel_grid: List[List[Dict[str, Any]]] | None = None
    row_inputs: List[Dict[str, Any]] = []
    for _ in range(400):
        candidate_grid: List[List[Dict[str, Any]]] = []
        candidate_inputs: List[Dict[str, Any]] = []
        valid = True
        for row_index in range(3):
            row_valid = False
            for _row_attempt in range(120):
                left_cells = _sample_cell_set(rng=rng, min_count=2, max_count=5)
                right_cells = _sample_cell_set(rng=rng, min_count=2, max_count=5)
                result_cells = _apply_set_operation(left_cells, right_cells, operation)
                if not 1 <= len(result_cells) <= 5:
                    continue
                if tuple(result_cells) in {tuple(left_cells), tuple(right_cells)}:
                    continue
                if _set_operation_matches(left_cells, right_cells, result_cells) != [str(operation)]:
                    continue
                candidate_grid.append(
                    [
                        _pattern_panel_spec(cells=left_cells, color=color),
                        _pattern_panel_spec(cells=right_cells, color=color),
                        _pattern_panel_spec(cells=result_cells, color=color),
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
    distractors: List[Dict[str, Any]] = []
    row2_left = tuple(tuple(coord) for coord in panel_grid[2][0]["cells"])
    row2_right = tuple(tuple(coord) for coord in panel_grid[2][1]["cells"])
    for alt_operation in _SET_OPERATIONS:
        alt_cells = _apply_set_operation(row2_left, row2_right, str(alt_operation))
        if 1 <= len(alt_cells) <= 5:
            distractors.append(_pattern_panel_spec(cells=alt_cells, color=color))
    distractors.extend(
        dict(panel_grid[row_index][col_index])
        for row_index in range(3)
        for col_index in range(3)
        if not (row_index == 2 and col_index == 2)
    )
    distractors.extend(
        _random_pattern_distractor_specs(
            target_cells=target_cells,
            color=color,
            rng=rng,
            min_count=1,
            max_count=5,
            target_count=12,
        )
    )
    rng.shuffle(distractors)
    correct_option_index = _resolve_correct_option_index(
        params,
        instance_seed=int(instance_seed),
        query_id="set_operation_matrix",
        option_count=int(option_count),
    )
    option_specs, option_labels = _build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": _matrix_rows_from_specs(panel_grid),
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


def _color_by_name(name: str) -> Dict[str, Any]:
    """Return one color record by palette name."""

    for color in _COLOR_POOL:
        if str(color["name"]) == str(name):
            return dict(color)
    raise ValueError(f"unknown Raven color name: {name}")


def _attribute_distractor_specs(
    *,
    target_panel_spec: Mapping[str, Any],
    rng,
) -> List[Dict[str, Any]]:
    """Build unique attribute-panel distractors for analogical transforms."""

    target_signature = _canonical_panel_spec(target_panel_spec)
    target_color = _color_by_name(str(target_panel_spec["fill_name"]))
    target_object_type = str(target_panel_spec["object_type"])
    target_size = float(target_panel_spec.get("size_scale", 0.78))
    specs: List[Dict[str, Any]] = []
    seen = {target_signature}

    candidates: List[Dict[str, Any]] = []
    for shape in PUZZLE_OBJECT_TYPES:
        candidates.append(_attribute_panel_spec(object_type=str(shape), color=target_color, size_scale=target_size))
    for color in _COLOR_POOL:
        candidates.append(_attribute_panel_spec(object_type=target_object_type, color=dict(color), size_scale=target_size))
    for size_scale in _SIZE_CYCLE:
        candidates.append(_attribute_panel_spec(object_type=target_object_type, color=target_color, size_scale=float(size_scale)))
    for shape in PUZZLE_OBJECT_TYPES:
        for color in _COLOR_POOL:
            candidates.append(_attribute_panel_spec(object_type=str(shape), color=dict(color), size_scale=target_size))
    rng.shuffle(candidates)
    for spec in candidates:
        signature = _canonical_panel_spec(spec)
        if signature in seen:
            continue
        seen.add(signature)
        specs.append(spec)
        if len(specs) >= 16:
            break
    return specs


def _build_analogical_transform_dataset(
    *,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
) -> Dict[str, Any]:
    """Construct a row-wise analogical-transform Raven matrix dataset."""

    transform_kind = str(rng.choice(_ANALOGICAL_TRANSFORMS))
    shapes = [str(value) for value in PUZZLE_OBJECT_TYPES]
    rng.shuffle(shapes)
    shape_cycle = [str(value) for value in shapes[:3]]
    colors = [dict(value) for value in _COLOR_POOL]
    rng.shuffle(colors)
    color_cycle = [dict(value) for value in colors[:3]]
    row_offsets = [0, 1, 2]
    rng.shuffle(row_offsets)

    panel_grid: List[List[Dict[str, Any]]] = []
    for row_index in range(3):
        row_specs: List[Dict[str, Any]] = []
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
                size_scale = float(_SIZE_CYCLE[offset])
            row_specs.append(_attribute_panel_spec(object_type=object_type, color=color, size_scale=float(size_scale)))
        panel_grid.append(row_specs)

    answer_panel_spec = dict(panel_grid[2][2])
    distractors = _attribute_distractor_specs(target_panel_spec=answer_panel_spec, rng=rng)
    distractors.extend(
        dict(panel_grid[row_index][col_index])
        for row_index in range(3)
        for col_index in range(3)
        if not (row_index == 2 and col_index == 2)
    )
    rng.shuffle(distractors)
    correct_option_index = _resolve_correct_option_index(
        params,
        instance_seed=int(instance_seed),
        query_id="analogical_transform_matrix",
        option_count=int(option_count),
    )
    option_specs, option_labels = _build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": _matrix_rows_from_specs(panel_grid),
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
            "size_cycle": [float(value) for value in _SIZE_CYCLE],
            "row_offsets": [int(value) for value in row_offsets],
            "target_row_index": 2,
            "target_col_index": 2,
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(option_label_for_index(correct_option_index)),
        },
    }


def _independent_mod3_steps(left: Sequence[int], right: Sequence[int]) -> bool:
    """Return whether two 2D mod-3 steps are linearly independent."""

    determinant = (int(left[0]) * int(right[1])) - (int(left[1]) * int(right[0]))
    return int(determinant % 3) != 0


def _build_position_progression_dataset(
    *,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
) -> Dict[str, Any]:
    """Construct a marker-position progression Raven matrix dataset."""

    color = dict(rng.choice(_COLOR_POOL))
    base_position = (int(rng.randrange(3)), int(rng.randrange(3)))
    row_step = tuple(rng.choice(_POSITION_STEPS))
    col_candidates = [step for step in _POSITION_STEPS if _independent_mod3_steps(row_step, step)]
    col_step = tuple(rng.choice(col_candidates))

    def _position_for(row_index: int, col_index: int) -> Tuple[int, int]:
        return (
            int((base_position[0] + row_index * row_step[0] + col_index * col_step[0]) % 3),
            int((base_position[1] + row_index * row_step[1] + col_index * col_step[1]) % 3),
        )

    panel_grid = [
        [
            _pattern_panel_spec(cells=(_position_for(row_index, col_index),), color=color)
            for col_index in range(3)
        ]
        for row_index in range(3)
    ]
    answer_panel_spec = dict(panel_grid[2][2])
    target_position = tuple(answer_panel_spec["cells"][0])
    distractors = [
        _pattern_panel_spec(cells=((row_index, col_index),), color=color)
        for row_index in range(3)
        for col_index in range(3)
        if (int(row_index), int(col_index)) != (int(target_position[0]), int(target_position[1]))
    ]
    rng.shuffle(distractors)
    correct_option_index = _resolve_correct_option_index(
        params,
        instance_seed=int(instance_seed),
        query_id="position_progression_matrix",
        option_count=int(option_count),
    )
    option_specs, option_labels = _build_option_specs(
        correct_panel_spec=answer_panel_spec,
        distractor_panel_specs=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "matrix_rows": _matrix_rows_from_specs(panel_grid),
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


def _build_raven_dataset_for_variant(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Construct one deterministic Raven matrix dataset."""

    selected_variant = str(query_id)
    if selected_variant not in set(_SUPPORTED_QUERY_IDS):
        raise ValueError(f"unsupported Raven query_id: {query_id}")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    option_count = int(params.get("option_count", group_default(_GEN_DEFAULTS, "option_count", int(_DEFAULTS.option_count))))
    if int(option_count) != 6:
        raise ValueError(f"{TASK_ID} currently requires exactly 6 options for stable option-letter coverage")
    if selected_variant == "count_progression_matrix":
        dataset = _build_count_progression_dataset(
            rng=rng,
            params=params,
            instance_seed=int(instance_seed),
            option_count=int(option_count),
        )
    elif selected_variant == "spatial_transform_matrix":
        dataset = _build_spatial_transform_dataset(
            rng=rng,
            params=params,
            instance_seed=int(instance_seed),
            option_count=int(option_count),
        )
    elif selected_variant == "set_operation_matrix":
        dataset = _build_set_operation_dataset(
            rng=rng,
            params=params,
            instance_seed=int(instance_seed),
            option_count=int(option_count),
        )
    elif selected_variant == "analogical_transform_matrix":
        dataset = _build_analogical_transform_dataset(
            rng=rng,
            params=params,
            instance_seed=int(instance_seed),
            option_count=int(option_count),
        )
    else:
        dataset = _build_position_progression_dataset(
            rng=rng,
            params=params,
            instance_seed=int(instance_seed),
            option_count=int(option_count),
        )
    dataset.update(
        {
            "matrix_size": 3,
            "query_cell_id": "cell_2_2",
            "query_row_index": 2,
            "query_col_index": 2,
            "cell_count": 9,
            "visible_matrix_cell_count": 8,
            "visual_item_count": 15,
            "visual_item_count_range": [12, 15],
        }
    )
    return dataset


class _PuzzlesLogicRavenMatrixBaseTask:
    """Choose the image option that correctly completes a Raven-style matrix."""

    task_id = TASK_ID
    domain = "puzzles"
    scene_id = "logic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        query_id_axis_size = 1 if "query_id" in params else len(_SUPPORTED_QUERY_IDS)
        scene_params = decouple_axis_sampling(
            params,
            preceding_axis_size=query_id_axis_size,
            explicit_key="scene_variant",
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            scene_params,
            instance_seed=int(instance_seed),
        )
        dataset = _build_raven_dataset_for_variant(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
        )

        render_params = resolve_logic_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.raven_matrix_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            cell_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            unknown_cell_fill_rgb=tuple(int(value) for value in scene_style.step_fill_rgb),
            option_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            option_symbol_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            accent_color_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_puzzle_raven_scene(
            background,
            scene_variant=str(scene_variant),
            matrix_rows=list(dataset["matrix_rows"]),
            option_specs=list(dataset["option_specs"]),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_raven_strip",
                "object_description_raven_card",
                "object_description_raven_outline",
                "annotation_hint_count_progression_matrix",
                "annotation_hint_spatial_transform_matrix",
                "annotation_hint_set_operation_matrix",
                "annotation_hint_analogical_transform_matrix",
                "annotation_hint_position_progression_matrix",
                "json_example_count_progression_matrix",
                "json_example_spatial_transform_matrix",
                "json_example_set_operation_matrix",
                "json_example_analogical_transform_matrix",
                "json_example_position_progression_matrix",
                "json_example_answer_only_count_progression_matrix",
                "json_example_answer_only_spatial_transform_matrix",
                "json_example_answer_only_set_operation_matrix",
                "json_example_answer_only_analogical_transform_matrix",
                "json_example_answer_only_position_progression_matrix",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=None,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        correct_option_panel_id = str(dataset["correct_option_panel_id"])
        annotation_projection = projected_puzzle_bbox_annotation(
            rendered_scene.option_panel_bbox_map,
            [str(correct_option_panel_id)],
        )
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_raven_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "query_cell_id": str(dataset["query_cell_id"]),
                    "correct_option_panel_id": str(correct_option_panel_id),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "matrix_size": int(dataset["matrix_size"]),
                    "cell_count": int(dataset["cell_count"]),
                    "visible_matrix_cell_count": int(dataset["visible_matrix_cell_count"]),
                    "option_count": int(dataset["option_count"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "text_style": {
                    "value_font_size_px": int(render_params.value_font_size_px),
                    "option_label_font_size_px": int(render_params.option_label_font_size_px),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "matrix_cell_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.matrix_cell_bbox_map.items()
                },
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
            }, render_params.unit_size_jitter),
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "query_cell_id": str(dataset["query_cell_id"]),
                "query_row_index": int(dataset["query_row_index"]),
                "query_col_index": int(dataset["query_col_index"]),
                "matrix_size": int(dataset["matrix_size"]),
                "cell_count": int(dataset["cell_count"]),
                "visible_matrix_cell_count": int(dataset["visible_matrix_cell_count"]),
                "matrix_rows": [[dict(cell) for cell in row] for row in dataset["matrix_rows"]],
                "matrix_panel_specs": [[dict(spec) for spec in row] for row in dataset["matrix_panel_specs"]],
                "answer_panel_spec": dict(dataset["answer_panel_spec"]),
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_panel_id": str(correct_option_panel_id),
                "option_count": int(dataset["option_count"]),
                "option_specs": [dict(option) for option in dataset["option_specs"]],
                "solver_trace": dict(dataset["solver_trace"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_option_panel_ids": [str(correct_option_panel_id)],
                "question_format": "raven_matrix_mcq",
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": {
                "bbox_set": list(annotation_bboxes),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesLogicRavenCountProgressionLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesLogicRavenMatrixBaseTask):
    """Complete a Raven matrix governed by count progression."""

    task_id = RAVEN_COUNT_PROGRESSION_LABEL_TASK_ID
    fixed_query_id = "count_progression_matrix"
    public_scene_id = SCENE_ID


@register_task
class PuzzlesLogicRavenSpatialTransformLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesLogicRavenMatrixBaseTask):
    """Complete a Raven matrix governed by spatial transforms."""

    task_id = RAVEN_SPATIAL_TRANSFORM_LABEL_TASK_ID
    fixed_query_id = "spatial_transform_matrix"
    public_scene_id = SCENE_ID


@register_task
class PuzzlesLogicRavenSetOperationLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesLogicRavenMatrixBaseTask):
    """Complete a Raven matrix governed by set operations."""

    task_id = RAVEN_SET_OPERATION_LABEL_TASK_ID
    fixed_query_id = "set_operation_matrix"
    public_scene_id = SCENE_ID


@register_task
class PuzzlesLogicRavenAnalogicalTransformLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesLogicRavenMatrixBaseTask):
    """Complete a Raven matrix governed by analogical transforms."""

    task_id = RAVEN_ANALOGICAL_TRANSFORM_LABEL_TASK_ID
    fixed_query_id = "analogical_transform_matrix"
    public_scene_id = SCENE_ID


@register_task
class PuzzlesLogicRavenPositionProgressionLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesLogicRavenMatrixBaseTask):
    """Complete a Raven matrix governed by position progression."""

    task_id = RAVEN_POSITION_PROGRESSION_LABEL_TASK_ID
    fixed_query_id = "position_progression_matrix"
    public_scene_id = SCENE_ID


__all__ = [
    "PuzzlesLogicRavenAnalogicalTransformLabelTask",
    "PuzzlesLogicRavenCountProgressionLabelTask",
    "PuzzlesLogicRavenPositionProgressionLabelTask",
    "PuzzlesLogicRavenSetOperationLabelTask",
    "PuzzlesLogicRavenSpatialTransformLabelTask",
]
