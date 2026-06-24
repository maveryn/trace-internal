"""Space-shooter clear-shot score sum task."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import SpaceShooterLifecycleTask, SpaceShooterObjective, run_space_shooter_lifecycle
from .shared.defaults import DEFAULTS
from .shared.sampling import resolve_target_answer, sample_clear_shot_scene
from .shared.state import SceneAxes


TASK_ID = "task_games__space_shooter__clear_shot_score_value"
PROMPT_QUERY_KEY = "clear_shot_score_value"
SUPPORTED_QUERY_IDS = (DEFAULT_QUERY_ID,)
JSON_EXAMPLE = '{"annotation":[[210,180,272,228],[480,260,542,308]],"answer":8}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":8}'


def _prepare_clear_shot_score_objective(rng, params: Mapping[str, Any], axes: SceneAxes, instance_seed: int) -> SpaceShooterObjective:
    """Construct a scored enemy scene with a controlled number of scoring enemies."""

    target, support, probabilities = resolve_target_answer(
        namespace=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        support_key="clear_shot_score_enemy_count_support",
        fallback_support=DEFAULTS.clear_shot_score_enemy_count_support,
    )
    if int(target) >= int(axes.lane_count) and params.get("lane_count") is not None:
        raise ValueError("clear_shot_score_value needs at least one blocked distractor lane")
    sample = sample_clear_shot_scene(rng=rng, axes=axes, target_answer=int(target), score_query=True)
    sample = replace(
        sample,
        metadata={
            **dict(sample.metadata),
            "target_answer_support": [int(value) for value in support],
            "target_answer_probabilities": dict(probabilities),
            "clear_shot_score_value_support": [int(value) for value in axes.clear_shot_score_value_support],
        },
    )
    return SpaceShooterObjective(
        sample=sample,
        answer_gt=TypedValue(type="integer", value=int(sample.answer)),
        prompt_query_key=PROMPT_QUERY_KEY,
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
    )


@register_task
class GamesSpaceShooterClearShotScoreValueTask(SpaceShooterLifecycleTask):
    """Sum printed scores for enemy ships not blocked by ships or player shots."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_space_shooter_lifecycle(
            namespace=TASK_ID,
            prompt_query_key=PROMPT_QUERY_KEY,
            supported_queries=SUPPORTED_QUERY_IDS,
            default_query=DEFAULT_QUERY_ID,
            task_params=params,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
            build_objective=_prepare_clear_shot_score_objective,
        )


__all__ = ["GamesSpaceShooterClearShotScoreValueTask"]
