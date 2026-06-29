"""Public Sudoku task for counting missing digits in a highlighted unit."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import SudokuTaskRuntime, run_sudoku_single_query_lifecycle
from .shared.rules import missing_digits_in_unit, unit_coords
from .shared.sampling import (
    SudokuAxes,
    SudokuDefaults,
    finalize_highlighted_unit_board,
    make_sudoku_sample,
    populate_unit_with_missing_digits,
)
from .shared.state import DOMAIN, SCENE_ID, Board, SudokuSample

TASK_ID = "task_puzzles__sudoku__unit_missing_digits_count"
_RUNTIME = SudokuTaskRuntime(
    source_id=TASK_ID,
    support_key="unit_missing_digits_count_support",
    include_unit_type=True,
    prompt_query_key="unit_missing_digits_count",
    attempt_namespace="puzzles.sudoku.unit_missing_digits_count",
)


def _sample_unit_missing_digits(
    *,
    rng,
    solution: Board,
    target_count: int,
    scene_variant: str,
    unit_type: str,
    defaults: SudokuDefaults,
) -> SudokuSample:
    """Construct one board with a highlighted unit missing target_count digits."""

    unit_index = int(rng.randrange(9))
    unit = unit_coords(unit_type, unit_index)
    board, missing_digits = populate_unit_with_missing_digits(
        rng=rng,
        solution=solution,
        unit=unit,
        target_count=int(target_count),
    )
    frozen = finalize_highlighted_unit_board(
        rng=rng,
        board=board,
        solution=solution,
        unit=unit,
        scene_variant=str(scene_variant),
        defaults=defaults,
    )
    missing = missing_digits_in_unit(
        frozen,
        unit_type=unit_type,
        unit_index=unit_index,
    )
    _require_exact_missing_digits(missing, missing_digits)
    return make_sudoku_sample(
        board=frozen,
        solution=solution,
        answer=int(len(missing_digits)),
        annotation_coords=_visible_cells_in_unit(frozen, unit),
        highlighted_unit_type=str(unit_type),
        highlighted_unit_index=int(unit_index),
        missing_digit_values=tuple(int(value) for value in missing_digits),
        construction_mode="unit_missing_digits",
    )


def _require_exact_missing_digits(
    observed_digits: tuple[int, ...],
    expected_digits: tuple[int, ...],
) -> None:
    """Reject unit boards whose absent digit set changed during construction."""

    if tuple(observed_digits) != tuple(expected_digits):
        raise ValueError(
            "constructed Sudoku unit does not match requested missing digits"
        )


def _visible_cells_in_unit(board: Board, unit: tuple[tuple[int, int], ...]):
    """Return highlighted-unit cells that still contain visible digits."""

    return tuple(coord for coord in unit if int(board[coord[0]][coord[1]]) != 0)


@register_task
class PuzzlesSudokuUnitMissingDigitsCountTask:
    """Count missing digit values in a highlighted Sudoku unit."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = (SINGLE_QUERY_ID,)

    def _build_missing_digit_unit_sample(
        self, *, rng, solution: Board, axes: SudokuAxes, defaults: SudokuDefaults
    ) -> SudokuSample:
        """Build the missing-digit sample for the resolved unit and count."""

        if axes.unit_type is None:
            raise RuntimeError("unit-missing task did not resolve a unit type")
        return _sample_unit_missing_digits(
            rng=rng,
            solution=solution,
            target_count=int(axes.target_answer),
            scene_variant=str(axes.scene_variant),
            unit_type=str(axes.unit_type),
            defaults=defaults,
        )

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Generate one highlighted-unit missing-digit count puzzle."""

        return run_sudoku_single_query_lifecycle(
            runtime=_RUNTIME,
            params=params,
            build_sample=self._build_missing_digit_unit_sample,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "TASK_ID",
    "PuzzlesSudokuUnitMissingDigitsCountTask",
]
