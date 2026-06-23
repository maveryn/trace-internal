"""Count towers covering the marked enemy in a tower-defense map."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import TowerDefenseObjectivePlan, run_tower_defense_lifecycle
from .shared.defaults import DEFAULTS
from .shared.sampling import sample_marked_enemy_scene


TASK_ID = "task_games__tower_defense__tower_coverage_count"
PROMPT_QUERY_KEY = "marked_enemy_covered_by_tower_count"
SUPPORTED_QUERY_IDS = (DEFAULT_QUERY_ID,)


def _prepare_tower_coverage_objective(
    _instance_seed: int,
    _params: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
) -> TowerDefenseObjectivePlan:
    """Bind the marked-enemy tower-coverage count objective."""

    if str(selected_branch) != DEFAULT_QUERY_ID:
        raise ValueError(f"unsupported tower-defense tower-coverage branch: {selected_branch}")

    def construct_attempt(rng, axes, render_params, task_params):
        return sample_marked_enemy_scene(
            rng=rng,
            axes=axes,
            render_params=render_params,
            params=task_params,
        )

    return TowerDefenseObjectivePlan(
        attempt_namespace="games.tower_defense.tower_coverage_count",
        prompt_query_key=PROMPT_QUERY_KEY,
        annotation_kind="tower_bbox_set",
        tower_count_support_key="tower_count_support",
        tower_count_fallback=DEFAULTS.tower_count_support,
        target_answer_support_key="target_answer_support",
        target_answer_fallback=DEFAULTS.target_answer_support,
        construct_attempt=construct_attempt,
        trace_params={"tower_coverage_branch_probabilities": dict(branch_probabilities)},
    )


@register_task
class GamesTowerDefenseCoverageCountTask:
    """Count visible towers whose range rings cover the marked enemy."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any] | None = None, max_attempts: int = 100):
        return run_tower_defense_lifecycle(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=DEFAULT_QUERY_ID,
            instance_seed=int(instance_seed),
            params=dict(params or {}),
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_tower_coverage_objective,
        )


__all__ = ["GamesTowerDefenseCoverageCountTask", "TASK_ID"]
