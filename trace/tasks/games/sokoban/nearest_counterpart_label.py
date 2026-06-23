"""Sokoban nearest-counterpart option task."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import SokobanLifecycleTask, build_relation_cell_objective, run_sokoban_lifecycle
from .shared.sampling import sample_relation_dataset, select_option_count
from .shared.state import RELATION_MODE_NEAREST_BOX, RELATION_MODE_NEAREST_TARGET


TASK_ID = "task_games__sokoban__nearest_counterpart_label"
NEAREST_TARGET_QUERY_ID = "nearest_target_for_marked_box_label"
NEAREST_BOX_QUERY_ID = "box_closest_to_marked_target_label"
SUPPORTED_QUERY_IDS = (NEAREST_TARGET_QUERY_ID, NEAREST_BOX_QUERY_ID)


def _relation_mode_for_public_query(public_query: str) -> str:
    """Map public nearest-counterpart queries to semantic relation modes."""

    if str(public_query) == NEAREST_TARGET_QUERY_ID:
        return RELATION_MODE_NEAREST_TARGET
    if str(public_query) == NEAREST_BOX_QUERY_ID:
        return RELATION_MODE_NEAREST_BOX
    raise ValueError(f"unsupported Sokoban nearest-counterpart query: {public_query}")


def _prepare_nearest_counterpart_objective(
    attempt_seed: int,
    task_params: Mapping[str, Any],
    public_query: str,
):
    """Construct nearest-counterpart candidates and bind the selected cell."""

    option_count, option_support, option_probabilities = select_option_count(
        task_params,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
        family="relation",
    )
    relation_mode = _relation_mode_for_public_query(str(public_query))
    dataset = sample_relation_dataset(
        relation_mode=str(relation_mode),
        option_count=int(option_count),
        rank=None,
        params=task_params,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
    )
    return build_relation_cell_objective(
        dataset=dataset,
        prompt_query_key=str(public_query),
        option_count_support=[int(value) for value in option_support],
        option_count_probabilities=option_probabilities,
        trace_extra_params={"relation_mode": str(relation_mode)},
    )


@register_task
class GamesSokobanNearestCounterpartLabelTask(SokobanLifecycleTask):
    """Choose the nearest target for a box or nearest box for a target."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_sokoban_lifecycle(
            namespace=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            default_query=NEAREST_TARGET_QUERY_ID,
            task_params=params,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
            build_objective=_prepare_nearest_counterpart_objective,
        )


__all__ = ["GamesSokobanNearestCounterpartLabelTask"]
