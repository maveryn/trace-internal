"""Public overlay task for selecting the union result option."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
)

from ._lifecycle import build_overlay_result_label_case, retry_overlay_generation
from .shared.sampling import sample_overlay_dataset
from .shared.state import DOMAIN, OverlayDataset, SCENE_ID

TASK_ID = "task_puzzles__overlay__overlay_result_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "overlay_result_label_query"
PROMPT_QUERY_KEY = "overlay_result_label"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.overlay_result_label"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesOverlayResultLabelTask:
    """Select the option showing the union of two transparent source sheets."""

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
        """Generate one overlay union task with scalar bbox annotation."""

        return retry_overlay_generation(
            build_case=_build_overlay_result_case,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


def _build_overlay_result_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Sample source sheets, bind the correct option, and annotate it."""

    return build_overlay_result_label_case(
        task_id=TASK_ID,
        namespace=_NAMESPACE_BASE,
        instance_seed=int(instance_seed),
        params=params,
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        dataset_builder=sample_overlay_dataset,
        validate_dataset=_validate_overlay_dataset,
    )


def _validate_overlay_dataset(dataset: OverlayDataset) -> None:
    """Validate the answer label matches exactly one union option."""

    correct = [
        str(option["option_label"])
        for option in dataset.option_specs
        if bool(option.get("is_correct", False))
    ]
    if correct != [str(dataset.answer_option_label)]:
        raise ValueError("overlay answer drifted from option specs")
    correct_ids = [
        str(option["option_choice_id"])
        for option in dataset.option_specs
        if bool(option.get("is_correct", False))
    ]
    if correct_ids != [str(dataset.correct_option_choice_id)]:
        raise ValueError("overlay correct option id drifted from option specs")
    union = sorted(tuple(int(value) for value in cell) for cell in dataset.union_cells)
    for option in dataset.option_specs:
        option_cells = sorted(
            tuple(int(value) for value in cell)
            for cell in option.get("cells", ())
        )
        if bool(option.get("is_correct", False)) and option_cells != union:
            raise ValueError("overlay correct option does not equal source union")
        if (not bool(option.get("is_correct", False))) and option_cells == union:
            raise ValueError("overlay distractor duplicates the source union")


__all__ = [
    "PROMPT_QUERY_KEY",
    "PuzzlesOverlayResultLabelTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
