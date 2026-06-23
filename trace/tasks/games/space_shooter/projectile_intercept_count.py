"""Space-shooter projectile intercept count task."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import SpaceShooterLifecycleTask, SpaceShooterObjective, run_space_shooter_lifecycle
from .shared.defaults import DEFAULTS
from .shared.sampling import resolve_target_answer, sample_projectile_intercept_scene
from .shared.state import SceneAxes


TASK_ID = "task_games__space_shooter__projectile_intercept_count"
PROMPT_QUERY_KEY = "projectile_intercept_count"
SUPPORTED_QUERY_IDS = (DEFAULT_QUERY_ID,)
JSON_EXAMPLE = '{"annotation":[[318,210,346,252],[318,340,346,382]],"answer":2}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":2}'


def _prepare_projectile_intercept_objective(rng, params: Mapping[str, Any], axes: SceneAxes, instance_seed: int) -> SpaceShooterObjective:
    """Construct a scene with a controlled number of player-lane projectiles."""

    target, support, probabilities = resolve_target_answer(
        namespace=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        support_key="projectile_intercept_count_support",
        fallback_support=DEFAULTS.projectile_intercept_count_support,
    )
    sample = sample_projectile_intercept_scene(rng=rng, axes=axes, target_answer=int(target))
    sample = replace(
        sample,
        metadata={
            **dict(sample.metadata),
            "target_answer_support": [int(value) for value in support],
            "target_answer_probabilities": dict(probabilities),
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
class GamesSpaceShooterProjectileInterceptCountTask(SpaceShooterLifecycleTask):
    """Count enemy projectiles aligned with the player ship."""

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
            build_objective=_prepare_projectile_intercept_objective,
            highlight_player_lane=True,
        )


__all__ = ["GamesSpaceShooterProjectileInterceptCountTask"]
