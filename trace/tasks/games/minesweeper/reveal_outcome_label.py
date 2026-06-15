"""Choose the option showing what a marked Minesweeper cell would reveal."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import MinesweeperAttemptResult, MinesweeperObjectivePlan, run_minesweeper_registered_task
from .shared.annotations import keyed_cell_ids_for_coords, minesweeper_keyed_bbox_sets_annotation
from .shared.defaults import DEFAULT_BRANCH_ID
from .shared.prompts import MinesweeperPromptSlots
from .shared.sampling import resolve_minesweeper_axes, sample_reveal_cell_scene


TASK_ID = "task_games__minesweeper__reveal_outcome_label"
QUERY_ID = DEFAULT_BRANCH_ID
PROMPT_QUERY_KEY = "reveal_outcome_label"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
BOARD_SIZE_SUPPORT_KEY = "reveal_outcome_board_size_support"
BOARD_SIZE_FALLBACK_SUPPORT = (5, 6, 7, 8)
TARGET_SUPPORT_KEY = "reveal_outcome_support"
TARGET_FALLBACK_SUPPORT = (0, 1, 2, 3, 4, 5, 6, 7, 8)
OPTION_COUNT_SUPPORT_KEY = "reveal_outcome_option_count_support"
OPTION_COUNT_FALLBACK_SUPPORT = (4, 6)


def _prepare_reveal_outcome_objective(
    instance_seed,
    task_params,
    _selected_branch,
    branch_probabilities,
    gen_defaults,
) -> MinesweeperObjectivePlan:
    """Resolve marked-hidden-cell axes and bind reveal-outcome option construction."""

    axes = resolve_minesweeper_axes(
        int(instance_seed),
        gen_defaults=gen_defaults,
        namespace="games.minesweeper.reveal_outcome",
        params=task_params,
        branch_probabilities=branch_probabilities,
        board_size_support_key=BOARD_SIZE_SUPPORT_KEY,
        board_size_fallback_support=BOARD_SIZE_FALLBACK_SUPPORT,
        target_support_key=TARGET_SUPPORT_KEY,
        target_fallback_support=TARGET_FALLBACK_SUPPORT,
        option_count_support_key=OPTION_COUNT_SUPPORT_KEY,
        option_count_fallback_support=OPTION_COUNT_FALLBACK_SUPPORT,
    )

    def construct_attempt(rng, resolved_axes):
        """Sample one reveal case and bind the target/support cells to the option label."""

        sample = sample_reveal_cell_scene(
            rng=rng,
            axes=resolved_axes,
            target_code=int(resolved_axes.target_answer or 0),
            option_count=int(resolved_axes.option_count or 4),
        )
        coords_by_role = {
            "target_cell": ((sample.target_cell_coord,) if sample.target_cell_coord is not None else ()),
            "supporting_clues": tuple(sample.supporting_clue_coords),
            "supporting_flags": tuple(sample.supporting_flag_coords),
        }
        return MinesweeperAttemptResult(
            answer_gt=TypedValue(type="option_letter", value=str(sample.answer)),
            sample=sample,
            prompt_slots=MinesweeperPromptSlots(
                prompt_query_key=PROMPT_QUERY_KEY,
                object_description_key=f"object_description_{str(resolved_axes.scene_variant)}",
                answer_hint_key=f"answer_hint_{PROMPT_QUERY_KEY}",
                annotation_hint_key=f"annotation_hint_{PROMPT_QUERY_KEY}",
                example_annotation={
                    "target_cell": [[210, 220, 280, 290]],
                    "supporting_clues": [[140, 220, 210, 290]],
                    "supporting_flags": [[140, 150, 210, 220]],
                },
                example_answer="C",
            ),
            bind_annotation=lambda rendered: minesweeper_keyed_bbox_sets_annotation(
                rendered=rendered,
                coords_by_role=coords_by_role,
            ),
            annotation_entity_ids=tuple(entity_id for ids in keyed_cell_ids_for_coords(coords_by_role).values() for entity_id in ids),
            keyed_annotation_entity_ids=keyed_cell_ids_for_coords(coords_by_role),
            highlighted_clue_coords=tuple(sample.forcing_clue_coords),
            highlighted_target_coords=((sample.target_cell_coord,) if sample.target_cell_coord is not None else ()),
            reveal_options=tuple(sample.answer_options),
            extra_query_params={
                "prompt_query_key": PROMPT_QUERY_KEY,
                "reveal_outcome": str(sample.reveal_outcome),
                "option_count": int(len(sample.answer_options)),
                "answer_options": [
                    {"label": str(label), "outcome": str(outcome)}
                    for label, outcome in sample.answer_options
                ],
            },
            execution_extra={"answer_option_letter": str(sample.answer)},
        )

    return MinesweeperObjectivePlan(
        axes=axes,
        attempt_namespace="games.minesweeper.reveal_outcome",
        construct_attempt=construct_attempt,
    )


@register_task
class GamesMinesweeperRevealOutcomeLabelTask:
    """Choose the on-image option for one marked hidden cell reveal."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    _default_branch = QUERY_ID
    _namespace = "games.minesweeper.reveal_outcome"
    _prepare_objective = staticmethod(_prepare_reveal_outcome_objective)

    def generate(self, instance_seed, *, params=None, max_attempts=100):
        """Generate a marked hidden-cell reveal outcome task instance."""

        return run_minesweeper_registered_task(
            self,
            int(instance_seed),
            params=params or {},
            max_attempts=int(max_attempts),
        )


__all__ = ["GamesMinesweeperRevealOutcomeLabelTask"]
