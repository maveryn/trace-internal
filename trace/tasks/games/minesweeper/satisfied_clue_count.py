"""Count opened Minesweeper clue cells exactly matched by adjacent flags."""

from __future__ import annotations

from trace.tasks.registry import register_task

from ._lifecycle import MinesweeperObjectivePlan, minesweeper_integer_bbox_set_attempt, run_minesweeper_registered_task
from .shared.defaults import DEFAULT_BRANCH_ID
from .shared.sampling import resolve_minesweeper_axes, sample_satisfied_number_scene


TASK_ID = "task_games__minesweeper__satisfied_clue_count"
QUERY_ID = DEFAULT_BRANCH_ID
PROMPT_QUERY_KEY = "satisfied_clue_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
BOARD_SIZE_SUPPORT_KEY = "board_size_support"
BOARD_SIZE_FALLBACK_SUPPORT = (4, 5, 6, 7, 8)
TARGET_SUPPORT_KEY = "satisfied_clue_count_support"
TARGET_FALLBACK_SUPPORT = (1, 2, 3, 4, 5)


def _prepare_satisfied_clue_objective(
    instance_seed,
    task_params,
    _selected_branch,
    branch_probabilities,
    gen_defaults,
) -> MinesweeperObjectivePlan:
    """Resolve exact satisfied-number axes and bind count construction."""

    axes = resolve_minesweeper_axes(
        int(instance_seed),
        gen_defaults=gen_defaults,
        namespace="games.minesweeper.satisfied_numbers",
        params=task_params,
        branch_probabilities=branch_probabilities,
        board_size_support_key=BOARD_SIZE_SUPPORT_KEY,
        board_size_fallback_support=BOARD_SIZE_FALLBACK_SUPPORT,
        target_support_key=TARGET_SUPPORT_KEY,
        target_fallback_support=TARGET_FALLBACK_SUPPORT,
    )

    def construct_attempt(rng, resolved_axes):
        sample = sample_satisfied_number_scene(
            rng=rng,
            axes=resolved_axes,
            target_count=int(resolved_axes.target_answer or 1),
        )
        return minesweeper_integer_bbox_set_attempt(
            sample=sample,
            prompt_key=PROMPT_QUERY_KEY,
            object_description_key=f"object_description_{str(resolved_axes.scene_variant)}",
            answer_hint_key=f"answer_hint_{PROMPT_QUERY_KEY}",
            annotation_hint_key=f"annotation_hint_{PROMPT_QUERY_KEY}",
            example_annotation=[[140, 220, 210, 290], [210, 220, 280, 290], [280, 220, 350, 290]],
            example_answer=3,
            coords=sample.annotation_coords,
            extra_query_params={"prompt_query_key": PROMPT_QUERY_KEY},
        )

    return MinesweeperObjectivePlan(
        axes=axes,
        attempt_namespace="games.minesweeper.satisfied_numbers",
        construct_attempt=construct_attempt,
    )


@register_task
class GamesMinesweeperSatisfiedClueCountTask:
    """Count opened number cells whose clue equals adjacent flags."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    _default_branch = QUERY_ID
    _namespace = "games.minesweeper.satisfied_numbers"
    _prepare_objective = staticmethod(_prepare_satisfied_clue_objective)

    def generate(self, instance_seed, *, params=None, max_attempts=100):
        """Generate a satisfied opened clue count task instance."""

        return run_minesweeper_registered_task(
            self,
            int(instance_seed),
            params=params or {},
            max_attempts=int(max_attempts),
        )


__all__ = ["GamesMinesweeperSatisfiedClueCountTask"]
