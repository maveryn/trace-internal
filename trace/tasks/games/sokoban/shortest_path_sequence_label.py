"""Sokoban shortest-path option task."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import SokobanLifecycleTask, build_path_option_objective, run_sokoban_lifecycle
from .shared.sampling import sample_path_sequence_dataset, select_option_count
from .shared.state import PATH_MODE_SHORTEST


TASK_ID = "task_games__sokoban__shortest_path_sequence_label"
PROMPT_QUERY_KEY = "shortest_path_sequence_label"
SUPPORTED_QUERY_IDS = (DEFAULT_QUERY_ID,)


def _prepare_shortest_path_objective(
    attempt_seed: int,
    task_params: Mapping[str, Any],
    _public_query: str,
):
    """Construct shortest-path options and bind the selected option panel."""

    option_count, option_support, option_probabilities = select_option_count(
        task_params,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
        family="path",
    )
    dataset = sample_path_sequence_dataset(
        path_mode=PATH_MODE_SHORTEST,
        option_count=int(option_count),
        params=task_params,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
    )
    return build_path_option_objective(
        dataset=dataset,
        prompt_query_key=PROMPT_QUERY_KEY,
        option_count_support=[int(value) for value in option_support],
        option_count_probabilities=option_probabilities,
        trace_extra_params={"path_mode": PATH_MODE_SHORTEST},
    )


@register_task
class GamesSokobanShortestPathSequenceLabelTask(SokobanLifecycleTask):
    """Choose the shortest visible move sequence from S to G."""

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
            build_objective=_prepare_shortest_path_objective,
        )


__all__ = ["GamesSokobanShortestPathSequenceLabelTask"]
