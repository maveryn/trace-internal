"""Sokoban path-validity option task."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import SokobanLifecycleTask, build_path_option_objective, run_sokoban_lifecycle
from .shared.sampling import sample_path_sequence_dataset, select_option_count
from .shared.state import PATH_MODE_BLOCKED, PATH_MODE_VALID


TASK_ID = "task_games__sokoban__path_validity_sequence_label"
VALID_QUERY_ID = "valid_path_sequence_label"
BLOCKED_QUERY_ID = "blocked_path_sequence_label"
SUPPORTED_QUERY_IDS = (VALID_QUERY_ID, BLOCKED_QUERY_ID)


def _path_mode_for_public_query(public_query: str) -> str:
    """Map public query wording to the semantic path construction mode."""

    if str(public_query) == VALID_QUERY_ID:
        return PATH_MODE_VALID
    if str(public_query) == BLOCKED_QUERY_ID:
        return PATH_MODE_BLOCKED
    raise ValueError(f"unsupported Sokoban path-validity query: {public_query}")


def _prepare_path_validity_objective(
    attempt_seed: int,
    task_params: Mapping[str, Any],
    public_query: str,
):
    """Construct a path option set and bind the selected option-panel annotation."""

    option_count, option_support, option_probabilities = select_option_count(
        task_params,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
        family="path",
    )
    path_mode = _path_mode_for_public_query(str(public_query))
    dataset = sample_path_sequence_dataset(
        path_mode=str(path_mode),
        option_count=int(option_count),
        params=task_params,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
    )
    return build_path_option_objective(
        dataset=dataset,
        prompt_query_key=str(public_query),
        option_count_support=[int(value) for value in option_support],
        option_count_probabilities=option_probabilities,
        trace_extra_params={"path_mode": str(path_mode)},
    )


@register_task
class GamesSokobanPathValiditySequenceLabelTask(SokobanLifecycleTask):
    """Choose whether a visible move sequence reaches or fails the goal."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_sokoban_lifecycle(
            namespace=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            default_query=VALID_QUERY_ID,
            task_params=params,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
            build_objective=_prepare_path_validity_objective,
        )


__all__ = ["GamesSokobanPathValiditySequenceLabelTask"]
