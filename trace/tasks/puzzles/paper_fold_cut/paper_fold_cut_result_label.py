"""Public paper fold-cut task for selecting the unfolded result option."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
)

from ._lifecycle import (
    build_paper_fold_cut_result_label_case,
    retry_paper_fold_cut_generation,
)
from .shared.state import DOMAIN, SCENE_ID, PaperFoldCutDataset

TASK_ID = "task_puzzles__paper_fold_cut__paper_fold_cut_result_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "paper_fold_cut_result_label_query"
PROMPT_QUERY_KEY = "paper_fold_cut_result_label"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.paper_fold_cut_result_label"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesPaperFoldCutResultLabelTask:
    """Select the option showing the unfolded result after folding and cutting."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Generate one paper fold-cut result task with scalar bbox annotation."""

        return retry_paper_fold_cut_generation(
            build_case=_build_paper_fold_cut_result_case,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


def _build_paper_fold_cut_result_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Sample a fold-cut puzzle, bind the correct option, and annotate it."""

    return build_paper_fold_cut_result_label_case(
        namespace=_NAMESPACE_BASE,
        instance_seed=int(instance_seed),
        params=params,
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        validate_dataset=_validate_paper_fold_cut_dataset,
    )


def _validate_paper_fold_cut_dataset(dataset: PaperFoldCutDataset) -> None:
    """Validate the answer label matches exactly one unfolded-result option."""

    correct = [
        str(option["option_label"])
        for option in dataset.option_specs
        if bool(option.get("is_correct", False))
    ]
    if correct != [str(dataset.answer_option_label)]:
        raise ValueError("paper fold-cut answer drifted from option specs")
    correct_ids = [
        str(option["option_choice_id"])
        for option in dataset.option_specs
        if bool(option.get("is_correct", False))
    ]
    if correct_ids != [str(dataset.correct_option_choice_id)]:
        raise ValueError("paper fold-cut correct option id drifted from option specs")
    winning_option = next(
        option
        for option in dataset.option_specs
        if bool(option.get("is_correct", False))
    )
    expected_cells = sorted((int(x), int(y)) for x, y in dataset.unfolded_hole_cells)
    actual_cells = sorted(
        (int(cell[0]), int(cell[1])) for cell in winning_option.get("cells", ())
    )
    if actual_cells != expected_cells:
        raise ValueError("paper fold-cut correct option does not match unfolded holes")
    option_signatures = {
        tuple(sorted((int(cell[0]), int(cell[1])) for cell in option["cells"]))
        for option in dataset.option_specs
    }
    if len(option_signatures) != len(dataset.option_specs):
        raise ValueError("paper fold-cut options are not unique")


__all__ = [
    "PROMPT_QUERY_KEY",
    "PuzzlesPaperFoldCutResultLabelTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
