"""Count black or white frontier discs on a Reversi board."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import ObjectiveReversiPlan, run_reversi_lifecycle
from .shared.defaults import DEFAULTS
from .shared.sampling import resolve_reversi_target_axis, sample_frontier_disc_scene
from .shared.state import BLACK, SCENE_ID, SCENE_NAMESPACE, WHITE


TASK_ID = "task_games__reversi__frontier_disc_count"
SUPPORTED_QUERY_IDS = ("black_frontier_disc_count", "white_frontier_disc_count")
DEFAULT_QUERY_ID = "black_frontier_disc_count"

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _query_player(query_id: str) -> int:
    """Return the queried disc color for one frontier-disc branch."""

    if str(query_id) == "black_frontier_disc_count":
        return int(BLACK)
    if str(query_id) == "white_frontier_disc_count":
        return int(WHITE)
    raise ValueError(f"unsupported Reversi frontier query: {query_id}")


def _prepare_frontier_objective(
    instance_seed: int,
    params: Mapping[str, Any],
    _query_probabilities: Mapping[str, float],
    query_id: str,
) -> ObjectiveReversiPlan:
    """Prepare target support and sampler hooks for frontier-disc counts."""

    query_player = _query_player(str(query_id))
    target_axis = resolve_reversi_target_axis(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="frontier_disc_count_support",
        fallback_support=DEFAULTS.frontier_disc_count_support,
        namespace=f"{SCENE_NAMESPACE}.frontier.{query_id}.target_answer",
    )
    return ObjectiveReversiPlan(
        attempt_namespace=f"{SCENE_NAMESPACE}.frontier.{query_id}",
        prompt_query_key=str(query_id),
        target_axis=target_axis,
        annotation_kind="disc_point_set",
        query_params={"query_player": "black" if int(query_player) == int(BLACK) else "white"},
        construct_attempt=lambda rng, axes: sample_frontier_disc_scene(
            rng=rng,
            board_size=int(axes.board_size),
            query_player=int(query_player),
            target_answer=int(target_axis.target_answer),
        ),
    )


@register_task
class GamesReversiFrontierDiscCountTask:
    """Count queried-color discs touching at least one empty square."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        return run_reversi_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=DEFAULT_QUERY_ID,
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=dict(params or {}),
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_frontier_objective,
        )


__all__ = ["GamesReversiFrontierDiscCountTask", "TASK_ID"]
