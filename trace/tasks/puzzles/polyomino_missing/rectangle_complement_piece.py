"""Public task for selecting the polyomino piece that completes a rectangle."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import PolyominoOptionAxes, run_polyomino_option_task
from .shared.sampling import build_rectangle_complement_dataset
from .shared.state import DOMAIN, SCENE_ID


TASK_ID = "task_puzzles__polyomino_missing__rectangle_complement_piece"
EXACT_ORIENTATION_QUERY_ID = "exact_orientation"
ROTATION_REFLECTION_QUERY_ID = "rotation_reflection_allowed"
SUPPORTED_QUERY_IDS = (EXACT_ORIENTATION_QUERY_ID, ROTATION_REFLECTION_QUERY_ID)
PROMPT_TASK_KEY = "rectangle_complement_piece_query"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.rectangle_complement_piece"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesPolyominoMissingRectangleComplementPieceTask:
    """Choose the option piece that completes the rectangular target."""

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
        """Generate one rectangle-complement polyomino option task."""

        attempts = max(1, int(max_attempts))
        return _run_rectangle_complement_task(
            int(instance_seed),
            params=params,
            max_attempts=attempts,
        )


def _run_rectangle_complement_task(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Select the transform-policy branch, then run the rectangle objective."""

    matching_policy, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=EXACT_ORIENTATION_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{_NAMESPACE_BASE}.policy",
    )
    return run_polyomino_option_task(
        instance_seed=int(instance_seed),
        params={**dict(task_params), "matching_policy": str(matching_policy)},
        max_attempts=int(max_attempts),
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        prompt_defaults=_PROMPT_DEFAULTS,
        selected_branch=str(matching_policy),
        branch_probabilities=branch_probabilities,
        namespace_base=_NAMESPACE_BASE,
        option_count_min_key="complement_option_count_min",
        option_count_max_key="complement_option_count_max",
        option_count_choices_key="complement_option_count_choices",
        option_count_fallback_min=4,
        option_count_fallback_max=6,
        option_count_context=f"{TASK_ID} option count",
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=str(matching_policy),
        dataset_factory=_prepare_rectangle_dataset,
        task_field_factory=_rectangle_fields,
        question_format="rectangle_complement_piece",
        view_family="polyomino_rectangle_complement_piece_option_puzzle",
    )


def _prepare_rectangle_dataset(
    attempt_seed: int,
    params: Mapping[str, Any],
    axes: PolyominoOptionAxes,
) -> Mapping[str, Any]:
    """Construct the rectangular target and options for one transform policy."""

    matching_policy = str(params["matching_policy"])
    dataset = dict(
        build_rectangle_complement_dataset(
            params=params,
            generation_defaults=_GEN_DEFAULTS,
            instance_seed=int(attempt_seed),
            transform_allowed=matching_policy == ROTATION_REFLECTION_QUERY_ID,
            option_count=int(axes.option_count),
            answer_label=str(axes.answer_label),
            namespace_base=_NAMESPACE_BASE,
        )
    )
    dataset["matching_policy"] = matching_policy
    return dataset


def _rectangle_fields(
    axes: PolyominoOptionAxes,
    dataset: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Return objective-specific trace fields for the rectangle task."""

    del axes
    return {"matching_policy": str(dataset["matching_policy"])}


__all__ = ["PuzzlesPolyominoMissingRectangleComplementPieceTask", "TASK_ID"]
