"""Solitaire tableau sequence count task."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import SolitaireLifecycleTask, SolitaireObjective, run_solitaire_lifecycle
from .shared.annotations import entity_bbox_set
from .shared.sampling import sample_tableau_sequence


TASK_ID = "task_games__solitaire__tableau_sequence_count"
PROMPT_QUERY_KEY = "tableau_sequence_count"
SUPPORTED_QUERY_IDS = (DEFAULT_QUERY_ID,)
JSON_EXAMPLE = '{"annotation":[[250,220,324,324],[342,220,416,324]],"answer":1}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":1}'


def _prepare_tableau_sequence_objective(rng, params: Mapping[str, Any], scene_variant: str, instance_seed: int) -> SolitaireObjective:
    """Construct columns with a controlled number of legal adjacent tableau pairs."""

    sample = sample_tableau_sequence(
        rng,
        namespace=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        scene_variant=str(scene_variant),
    )
    return SolitaireObjective(
        sample=sample,
        answer_gt=TypedValue(type="integer", value=int(sample.answer)),
        prompt_query_key=PROMPT_QUERY_KEY,
        build_annotation=entity_bbox_set,
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
    )


@register_task
class GamesSolitaireTableauSequenceCountTask(SolitaireLifecycleTask):
    """Count adjacent visible pairs that already form legal tableau sequences."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_solitaire_lifecycle(
            namespace=TASK_ID,
            prompt_query_key=PROMPT_QUERY_KEY,
            supported_queries=SUPPORTED_QUERY_IDS,
            default_query=DEFAULT_QUERY_ID,
            task_params=params,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
            build_objective=_prepare_tableau_sequence_objective,
        )


__all__ = ["GamesSolitaireTableauSequenceCountTask"]
