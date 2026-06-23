"""Space-shooter highest-threat enemy label task."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import SpaceShooterLifecycleTask, SpaceShooterObjective, run_space_shooter_lifecycle
from .shared.annotations import single_entity_bbox
from .shared.sampling import sample_unique_lowest_enemy_scene
from .shared.state import SceneAxes


TASK_ID = "task_games__space_shooter__highest_threat_label"
PROMPT_QUERY_KEY = "highest_threat_label"
SUPPORTED_QUERY_IDS = (DEFAULT_QUERY_ID,)
JSON_EXAMPLE = '{"annotation":[420,260,482,308],"answer":"C"}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":"C"}'


def _prepare_highest_threat_objective(rng, params: Mapping[str, Any], axes: SceneAxes, instance_seed: int) -> SpaceShooterObjective:
    """Construct a scene with one unique enemy closest to the player baseline."""

    sample = sample_unique_lowest_enemy_scene(rng=rng, axes=axes)
    return SpaceShooterObjective(
        sample=sample,
        answer_gt=TypedValue(type="string", value=str(sample.answer)),
        prompt_query_key=PROMPT_QUERY_KEY,
        build_annotation=single_entity_bbox,
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
    )


@register_task
class GamesSpaceShooterHighestThreatLabelTask(SpaceShooterLifecycleTask):
    """Identify the labeled enemy closest to the bottom player baseline."""

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
            build_objective=_prepare_highest_threat_objective,
        )


__all__ = ["GamesSpaceShooterHighestThreatLabelTask"]
