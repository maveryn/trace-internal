"""Sokoban ranked box-target distance option task."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import SokobanLifecycleTask, build_relation_pair_objective, run_sokoban_lifecycle
from .shared.sampling import sample_relation_dataset, select_option_count, select_rank
from .shared.state import RELATION_MODE_RANKED_PAIR


TASK_ID = "task_games__sokoban__box_target_manhattan_rank_label"
PROMPT_QUERY_KEY = "box_target_manhattan_rank_label"
SUPPORTED_QUERY_IDS = (DEFAULT_QUERY_ID,)


def _prepare_box_target_rank_objective(
    attempt_seed: int,
    task_params: Mapping[str, Any],
    _public_query: str,
):
    """Construct ranked same-letter box-target pairs and bind the chosen pair cells."""

    option_count, option_support, option_probabilities = select_option_count(
        task_params,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
        family="relation",
    )
    rank = select_rank(int(option_count), instance_seed=int(attempt_seed))
    dataset = sample_relation_dataset(
        relation_mode=RELATION_MODE_RANKED_PAIR,
        option_count=int(option_count),
        rank=int(rank),
        params=task_params,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
    )
    return build_relation_pair_objective(
        dataset=dataset,
        prompt_query_key=PROMPT_QUERY_KEY,
        option_count_support=[int(value) for value in option_support],
        option_count_probabilities=option_probabilities,
        trace_extra_params={
            "relation_mode": RELATION_MODE_RANKED_PAIR,
            "rank": int(rank),
        },
    )


@register_task
class GamesSokobanBoxTargetManhattanRankLabelTask(SokobanLifecycleTask):
    """Choose a same-letter box-target pair by Manhattan-distance rank."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_sokoban_lifecycle(
            namespace=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            default_query=DEFAULT_QUERY_ID,
            task_params=params,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
            build_objective=_prepare_box_target_rank_objective,
        )


__all__ = ["GamesSokobanBoxTargetManhattanRankLabelTask"]
