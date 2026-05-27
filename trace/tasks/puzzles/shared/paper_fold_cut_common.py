"""Dataset builders for paper fold-cut result puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from .common import resolve_puzzle_axis_variant


Cells = Tuple[Tuple[int, int], ...]

SUPPORTED_PUZZLE_FOLD_CUT_QUERY_VARIANTS: Tuple[str, ...] = (
    "single_vertical_fold_cut_result",
    "single_horizontal_fold_cut_result",
    "double_fold_cut_result",
)
SUPPORTED_PUZZLE_FOLD_CUT_SCENE_VARIANTS: Tuple[str, ...] = (
    "fold_strip",
    "fold_card",
    "fold_outline",
)


@dataclass(frozen=True)
class PuzzleFoldCutDefaults:
    """Default generation bounds for fold-cut spatial puzzles."""

    option_count_min: int = 6
    option_count_max: int = 6
    grid_size: int = 6
    cut_count_min: int = 1
    cut_count_max: int = 2


def _resolve_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer generation parameter."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def _canonicalize_cells(cells: Iterable[Tuple[int, int]]) -> Cells:
    """Return cells in deterministic row-major order."""

    return tuple(sorted((int(cell_x), int(cell_y)) for cell_x, cell_y in cells))


def resolve_fold_cut_query_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active fold-cut semantic variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_FOLD_CUT_QUERY_VARIANTS,
        task_id=str(task_id),
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def resolve_fold_cut_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active fold-cut scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_FOLD_CUT_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _fold_sequence_for_variant(query_variant: str, *, rng) -> List[Dict[str, Any]]:
    """Build a deterministic center-fold sequence for one query variant."""

    if str(query_variant) == "single_vertical_fold_cut_result":
        return [
            {
                "fold_index": 1,
                "fold_axis": "vertical",
                "fold_direction": str(rng.choice(("left_to_right", "right_to_left"))),
            }
        ]
    if str(query_variant) == "single_horizontal_fold_cut_result":
        return [
            {
                "fold_index": 1,
                "fold_axis": "horizontal",
                "fold_direction": str(rng.choice(("top_to_bottom", "bottom_to_top"))),
            }
        ]
    if str(query_variant) == "double_fold_cut_result":
        first_axis = str(rng.choice(("vertical", "horizontal")))
        second_axis = "horizontal" if str(first_axis) == "vertical" else "vertical"
        sequence: List[Dict[str, Any]] = []
        for index, axis in enumerate((first_axis, second_axis), start=1):
            if str(axis) == "vertical":
                direction = str(rng.choice(("left_to_right", "right_to_left")))
            else:
                direction = str(rng.choice(("top_to_bottom", "bottom_to_top")))
            sequence.append(
                {
                    "fold_index": int(index),
                    "fold_axis": str(axis),
                    "fold_direction": str(direction),
                }
            )
        return sequence
    raise ValueError(f"unsupported fold-cut variant: {query_variant}")


def _folded_dimensions(
    *,
    grid_size: int,
    fold_sequence: Sequence[Mapping[str, Any]],
) -> Tuple[int, int, Tuple[Tuple[int, int], ...]]:
    """Return final folded dimensions and dimensions before each fold."""

    dimensions: List[Tuple[int, int]] = [(int(grid_size), int(grid_size))]
    for step in fold_sequence:
        width, height = dimensions[-1]
        axis = str(step["fold_axis"])
        if axis == "vertical":
            if int(width) % 2 != 0:
                raise ValueError("vertical fold requires an even current grid width")
            dimensions.append((int(width // 2), int(height)))
        elif axis == "horizontal":
            if int(height) % 2 != 0:
                raise ValueError("horizontal fold requires an even current grid height")
            dimensions.append((int(width), int(height // 2)))
        else:
            raise ValueError(f"unsupported fold axis: {axis}")
    final_width, final_height = dimensions[-1]
    return int(final_width), int(final_height), tuple(dimensions)


def _unfold_cut_cell(
    *,
    cut_cell: Tuple[int, int],
    fold_sequence: Sequence[Mapping[str, Any]],
    dimensions: Sequence[Tuple[int, int]],
) -> Cells:
    """Expand one cut through the folded stack into full-sheet cells."""

    cells = {(int(cut_cell[0]), int(cut_cell[1]))}
    for step_index in reversed(range(len(fold_sequence))):
        step = fold_sequence[int(step_index)]
        previous_width, previous_height = dimensions[int(step_index)]
        axis = str(step["fold_axis"])
        direction = str(step["fold_direction"])
        expanded: set[Tuple[int, int]] = set()
        for cell_x, cell_y in cells:
            if axis == "vertical":
                half = int(previous_width // 2)
                if direction == "left_to_right":
                    expanded.add((int(half + cell_x), int(cell_y)))
                    expanded.add((int((half - 1) - cell_x), int(cell_y)))
                elif direction == "right_to_left":
                    expanded.add((int(cell_x), int(cell_y)))
                    expanded.add((int((previous_width - 1) - cell_x), int(cell_y)))
                else:
                    raise ValueError(f"unsupported vertical fold direction: {direction}")
            elif axis == "horizontal":
                half = int(previous_height // 2)
                if direction == "top_to_bottom":
                    expanded.add((int(cell_x), int(half + cell_y)))
                    expanded.add((int(cell_x), int((half - 1) - cell_y)))
                elif direction == "bottom_to_top":
                    expanded.add((int(cell_x), int(cell_y)))
                    expanded.add((int(cell_x), int((previous_height - 1) - cell_y)))
                else:
                    raise ValueError(f"unsupported horizontal fold direction: {direction}")
            else:
                raise ValueError(f"unsupported fold axis: {axis}")
        cells = expanded
    return _canonicalize_cells(cells)


def _unfold_cut_cells(
    *,
    cut_cells: Cells,
    fold_sequence: Sequence[Mapping[str, Any]],
    dimensions: Sequence[Tuple[int, int]],
) -> Cells:
    """Expand all folded-stack cuts into the unfolded full-sheet pattern."""

    unfolded: set[Tuple[int, int]] = set()
    for cut_cell in cut_cells:
        unfolded.update(
            _unfold_cut_cell(
                cut_cell=(int(cut_cell[0]), int(cut_cell[1])),
                fold_sequence=fold_sequence,
                dimensions=dimensions,
            )
        )
    return _canonicalize_cells(unfolded)


def _hole_specs(cells: Cells, *, prefix: str) -> List[Dict[str, Any]]:
    """Build deterministic hole specs from cells."""

    return [
        {
            "hole_id": f"{str(prefix)}_{int(index)}",
            "cell": [int(cell_x), int(cell_y)],
        }
        for index, (cell_x, cell_y) in enumerate(cells, start=1)
    ]


def _cut_specs(cells: Cells) -> List[Dict[str, Any]]:
    """Build deterministic folded-stack cut specs."""

    return [
        {
            "cut_id": f"cut_{int(index)}",
            "cell": [int(cell_x), int(cell_y)],
        }
        for index, (cell_x, cell_y) in enumerate(cells, start=1)
    ]


def _all_cells(cols: int, rows: int) -> Cells:
    """Return all cells for a rectangular folded packet."""

    return tuple((int(cell_x), int(cell_y)) for cell_y in range(int(rows)) for cell_x in range(int(cols)))


def _resolve_correct_option_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
    task_id: str,
) -> int:
    """Resolve a correct option slot while review sampling cycles past variants."""

    explicit_index = params.get("correct_option_index")
    if explicit_index is not None:
        correct_index = int(explicit_index)
        if not 0 <= int(correct_index) < int(option_count):
            raise ValueError("correct_option_index must fall inside the option-count range")
        return int(correct_index)

    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:correct_option_index",
    )
    return int(selection_index % int(option_count))


def _build_fold_cut_options(
    *,
    correct_cut_cells: Cells,
    correct_hole_cells: Cells,
    folded_grid_cols: int,
    folded_grid_rows: int,
    fold_sequence: Sequence[Mapping[str, Any]],
    dimensions: Sequence[Tuple[int, int]],
    option_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    rng,
) -> Tuple[List[Dict[str, Any]], int, str]:
    """Build six labeled unfolded-result options with one correct pattern."""

    correct_signature = _canonicalize_cells(correct_hole_cells)
    cut_count = int(len(correct_cut_cells))
    folded_cells = list(_all_cells(int(folded_grid_cols), int(folded_grid_rows)))
    seen = {correct_signature}
    distractors: List[Tuple[Cells, Cells, str]] = []

    max_attempts = 400
    for _ in range(int(max_attempts)):
        candidate_cut_cells = _canonicalize_cells(rng.sample(folded_cells, int(cut_count)))
        candidate_holes = _unfold_cut_cells(
            cut_cells=candidate_cut_cells,
            fold_sequence=fold_sequence,
            dimensions=dimensions,
        )
        candidate_signature = _canonicalize_cells(candidate_holes)
        if candidate_signature in seen:
            continue
        seen.add(candidate_signature)
        distractors.append((candidate_cut_cells, candidate_signature, "alternate_cut_location"))
        if len(distractors) >= int(option_count) - 1:
            break
    if len(distractors) < int(option_count) - 1:
        raise RuntimeError("failed to construct enough fold-cut distractors")

    correct_option_index = _resolve_correct_option_index(
        params=params,
        instance_seed=int(instance_seed),
        option_count=int(option_count),
        task_id=str(task_id),
    )
    answer_option_label = str(option_label_for_index(int(correct_option_index)))
    correct_option_choice_id = f"option_choice_{str(answer_option_label)}"

    option_payloads = list(distractors[: int(option_count) - 1])
    option_payloads.insert(int(correct_option_index), (correct_cut_cells, correct_signature, "correct_unfolded_result"))

    option_specs: List[Dict[str, Any]] = []
    for option_index, (cut_cells, hole_cells, candidate_kind) in enumerate(option_payloads):
        option_label = str(option_label_for_index(int(option_index)))
        option_choice_id = f"option_choice_{str(option_label)}"
        option_specs.append(
            {
                "option_choice_id": str(option_choice_id),
                "option_label": str(option_label),
                "hole_specs": _hole_specs(hole_cells, prefix=f"{str(option_choice_id)}_hole"),
                "cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in hole_cells],
                "source_cut_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cut_cells],
                "hole_count": int(len(hole_cells)),
                "candidate_kind": str(candidate_kind),
                "is_correct": bool(option_index == int(correct_option_index)),
            }
        )
    return list(option_specs), int(correct_option_index), str(correct_option_choice_id)


def build_fold_cut_result_dataset_for_variant(
    *,
    query_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleFoldCutDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one fold-cut puzzle with a unique unfolded-result option."""

    if str(query_variant) not in SUPPORTED_PUZZLE_FOLD_CUT_QUERY_VARIANTS:
        raise ValueError(f"unsupported fold-cut query variant: {query_variant}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    option_count_min, option_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=int(defaults.option_count_min),
        fallback_max=int(defaults.option_count_max),
        context=f"{task_id} option-count bounds",
    )
    option_count = int(option_count_min + (abs(int(instance_seed)) % (int(option_count_max) - int(option_count_min) + 1)))
    grid_size = int(_resolve_int_param(params, gen_defaults, "grid_size", int(defaults.grid_size)))
    if int(grid_size) % 2 != 0:
        raise ValueError("fold-cut puzzles require an even grid_size")

    cut_count_min, cut_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="cut_count_min",
        max_key="cut_count_max",
        fallback_min=int(defaults.cut_count_min),
        fallback_max=int(defaults.cut_count_max),
        context=f"{task_id} cut-count bounds",
    )

    fold_sequence = _fold_sequence_for_variant(str(query_variant), rng=rng)
    folded_grid_cols, folded_grid_rows, dimensions = _folded_dimensions(
        grid_size=int(grid_size),
        fold_sequence=fold_sequence,
    )
    folded_cell_capacity = int(folded_grid_cols * folded_grid_rows)
    effective_cut_count_max = min(int(cut_count_max), int(folded_cell_capacity))
    effective_cut_count_min = min(int(cut_count_min), int(effective_cut_count_max))
    if int(effective_cut_count_min) <= 0:
        raise ValueError("cut_count_min must be positive")
    cut_count = int(rng.randint(int(effective_cut_count_min), int(effective_cut_count_max)))
    folded_cells = list(_all_cells(int(folded_grid_cols), int(folded_grid_rows)))
    cut_cells = _canonicalize_cells(rng.sample(folded_cells, int(cut_count)))
    unfolded_hole_cells = _unfold_cut_cells(
        cut_cells=cut_cells,
        fold_sequence=fold_sequence,
        dimensions=dimensions,
    )

    option_specs, correct_option_index, correct_option_choice_id = _build_fold_cut_options(
        correct_cut_cells=cut_cells,
        correct_hole_cells=unfolded_hole_cells,
        folded_grid_cols=int(folded_grid_cols),
        folded_grid_rows=int(folded_grid_rows),
        fold_sequence=fold_sequence,
        dimensions=dimensions,
        option_count=int(option_count),
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        rng=rng,
    )
    answer_option_label = str(option_label_for_index(int(correct_option_index)))

    return {
        "query_variant": str(query_variant),
        "question_format": "fold_cut_unfolded_result_mcq",
        "view_family": "paper_fold_cut_result_mcq",
        "grid_size": int(grid_size),
        "folded_grid_cols": int(folded_grid_cols),
        "folded_grid_rows": int(folded_grid_rows),
        "fold_sequence": [dict(step) for step in fold_sequence],
        "fold_count": int(len(fold_sequence)),
        "folded_dimensions_by_step": [[int(width), int(height)] for width, height in dimensions],
        "cut_count": int(cut_count),
        "cut_count_range": [int(cut_count_min), int(cut_count_max)],
        "cut_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cut_cells],
        "cut_specs": _cut_specs(cut_cells),
        "unfolded_hole_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in unfolded_hole_cells],
        "unfolded_hole_specs": _hole_specs(unfolded_hole_cells, prefix="unfolded_hole"),
        "unfolded_hole_count": int(len(unfolded_hole_cells)),
        "option_count": int(option_count),
        "option_count_range": [int(option_count_min), int(option_count_max)],
        "option_specs": list(option_specs),
        "answer_option_label": str(answer_option_label),
        "correct_option_index": int(correct_option_index),
        "correct_option_choice_id": str(correct_option_choice_id),
        "valid_option_choice_ids": [str(correct_option_choice_id)],
        "solver_trace": {
            "query_variant": str(query_variant),
            "fold_sequence": [dict(step) for step in fold_sequence],
            "cut_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cut_cells],
            "unfolded_hole_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in unfolded_hole_cells],
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(answer_option_label),
            "correct_option_choice_id": str(correct_option_choice_id),
            "option_signatures": {
                str(spec["option_choice_id"]): [[int(cell[0]), int(cell[1])] for cell in spec["cells"]]
                for spec in option_specs
            },
        },
    }


__all__ = [
    "PuzzleFoldCutDefaults",
    "SUPPORTED_PUZZLE_FOLD_CUT_SCENE_VARIANTS",
    "SUPPORTED_PUZZLE_FOLD_CUT_QUERY_VARIANTS",
    "build_fold_cut_result_dataset_for_variant",
    "resolve_fold_cut_scene_variant",
    "resolve_fold_cut_query_variant",
]
