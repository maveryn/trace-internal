"""Public Sudoku task for counting repeated digits in a highlighted unit."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import SudokuTaskRuntime, run_sudoku_single_query_lifecycle
from .shared.rules import repeated_digits_in_unit, unit_coords
from .shared.sampling import (
    SudokuAxes,
    SudokuDefaults,
    finalize_highlighted_unit_board,
    make_sudoku_sample,
    populate_unit_with_repeated_digits,
)
from .shared.state import DOMAIN, SCENE_ID, Board, SudokuSample

TASK_ID = "task_puzzles__sudoku__repeated_digit_count"
_RUNTIME = SudokuTaskRuntime(
    source_id=TASK_ID,
    support_key="repeated_digit_count_support",
    include_unit_type=True,
    prompt_query_key="repeated_digit_count",
    attempt_namespace="puzzles.sudoku.repeated_digit_count",
)


@register_task
class PuzzlesSudokuRepeatedDigitCountTask:
    """Count repeated digit values in a highlighted Sudoku unit."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = (SINGLE_QUERY_ID,)

    def _build_repeated_digit_unit_sample(
        self, *, rng, solution: Board, axes: SudokuAxes, defaults: SudokuDefaults
    ) -> SudokuSample:
        """Build the repeat-count sample for the resolved unit and count."""

        if axes.unit_type is None:
            raise RuntimeError("repeated-digit task did not resolve a unit type")
        return _sample_repeated_digit_count(
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
        """Generate one highlighted-unit repeated-digit count puzzle."""

        return run_sudoku_single_query_lifecycle(
            runtime=_RUNTIME,
            params=params,
            build_sample=self._build_repeated_digit_unit_sample,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
        )


def _sample_repeated_digit_count(
    *,
    rng,
    solution: Board,
    target_count: int,
    scene_variant: str,
    unit_type: str,
    defaults: SudokuDefaults,
) -> SudokuSample:
    """Construct one highlighted unit with target_count repeated digit values."""

    unit_index = int(rng.randrange(9))
    unit = unit_coords(unit_type, unit_index)
    board, repeated_digits = populate_unit_with_repeated_digits(
        rng=rng,
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
    repeated = repeated_digits_in_unit(
        frozen,
        unit_type=unit_type,
        unit_index=unit_index,
    )
    _require_exact_repeated_digits(repeated, repeated_digits)
    return make_sudoku_sample(
        board=frozen,
        solution=solution,
        answer=int(len(repeated_digits)),
        annotation_coords=_cells_holding_repeated_digits(frozen, unit, repeated_digits),
        highlighted_unit_type=str(unit_type),
        highlighted_unit_index=int(unit_index),
        repeated_digit_values=tuple(int(value) for value in repeated_digits),
        construction_mode="highlighted_unit_repeats",
    )


def _require_exact_repeated_digits(
    observed_digits: tuple[int, ...],
    expected_digits: tuple[int, ...],
) -> None:
    """Reject unit boards whose duplicated digit set changed during construction."""

    if tuple(observed_digits) != tuple(expected_digits):
        raise ValueError("constructed Sudoku highlighted unit has wrong repeated count")


def _cells_holding_repeated_digits(
    board: Board,
    unit: tuple[tuple[int, int], ...],
    repeated_digits: tuple[int, ...],
):
    """Return highlighted-unit cells whose visible value is one of the repeats."""

    repeated = {int(value) for value in repeated_digits}
    return tuple(coord for coord in unit if int(board[coord[0]][coord[1]]) in repeated)


__all__ = [
    "TASK_ID",
    "PuzzlesSudokuRepeatedDigitCountTask",
]
