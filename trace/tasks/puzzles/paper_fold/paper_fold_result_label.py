"""Public paper-fold task for selecting the folded result option."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
)

from ._lifecycle import build_paper_fold_result_label_case, retry_paper_fold_generation
from .shared.state import DOMAIN, PaperFoldDataset, SCENE_ID

TASK_ID = "task_puzzles__paper_fold__paper_fold_result_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "paper_fold_result_label_query"
PROMPT_QUERY_KEY = "paper_fold_result_label"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.paper_fold_result_label"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesPaperFoldResultLabelTask:
    """Select the option showing the result of the indicated fold."""

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
        """Generate one paper-fold result task with scalar bbox annotation."""

        return retry_paper_fold_generation(
            build_case=_build_paper_fold_result_case,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


def _build_paper_fold_result_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Sample a fold puzzle, bind the correct option, and annotate it."""

    return build_paper_fold_result_label_case(
        namespace=_NAMESPACE_BASE,
        instance_seed=int(instance_seed),
        params=params,
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        validate_dataset=_validate_paper_fold_dataset,
    )


def _validate_paper_fold_dataset(dataset: PaperFoldDataset) -> None:
    """Validate the answer label matches exactly one folded-result option."""

    correct = [
        str(option["option_label"])
        for option in dataset.option_specs
        if bool(option.get("is_correct", False))
    ]
    if correct != [str(dataset.answer_option_label)]:
        raise ValueError("paper-fold answer drifted from option specs")
    correct_ids = [
        str(option["option_choice_id"])
        for option in dataset.option_specs
        if bool(option.get("is_correct", False))
    ]
    if correct_ids != [str(dataset.correct_option_choice_id)]:
        raise ValueError("paper-fold correct option id drifted from option specs")
    correct_option = next(
        option
        for option in dataset.option_specs
        if bool(option.get("is_correct", False))
    )
    expected_signature = sorted(
        (
            str(mark["object_type"]),
            int(mark["cell"][0]),
            int(mark["cell"][1]),
        )
        for mark in dataset.folded_result_mark_specs
    )
    correct_signature = sorted(
        (
            str(mark["object_type"]),
            int(mark["cell"][0]),
            int(mark["cell"][1]),
        )
        for mark in correct_option.get("mark_specs", ())
    )
    if correct_signature != expected_signature:
        raise ValueError("paper-fold correct option does not match folded result")


__all__ = [
    "PROMPT_QUERY_KEY",
    "PuzzlesPaperFoldResultLabelTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
