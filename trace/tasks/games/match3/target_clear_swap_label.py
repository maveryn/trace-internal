"""Choose the labeled match-3 swap that clears a target number of gems."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import Match3ObjectivePlan, Match3SingleQueryTaskBase, prepare_match3_swap_option_plan, run_match3_registered_task
from .shared.defaults import DEFAULTS, SCENE_ID
from .shared.prompts import make_match3_prompt_slots
from .shared.sampling import (
    resolve_match3_integer_axis,
    select_random_outcomes,
)
from .shared.state import Match3SceneAxes, MoveOutcome


TASK_ID = "task_games__match3__target_clear_swap_label"
PROMPT_SLOTS = make_match3_prompt_slots(
    prompt_query_key="target_clear_swap_label",
    object_description_key="object_description_match3_grid",
    answer_hint_key="answer_hint_target_clear_swap_label",
    annotation_hint_key="annotation_hint_target_clear_swap_label",
    example_annotation=[[456, 284]],
    example_answer="C",
)


def _build_target_clear_selector(target_clear_count: int):
    """Return an outcome selector for one exact immediate-clear count."""

    def _select_target_clear_outcomes(outcomes: tuple[MoveOutcome, ...], rng: Any):
        """Pick one answer with the target count and nonmatching distractors."""

        matching = [outcome for outcome in outcomes if int(outcome.clear_count) == int(target_clear_count)]
        nonmatching = [outcome for outcome in outcomes if int(outcome.clear_count) != int(target_clear_count)]
        if not matching or len(nonmatching) < 3:
            raise ValueError(f"no unique target-clear option set for {int(target_clear_count)}")
        answer_outcome = rng.choice(tuple(matching))
        nonmatching = [outcome for outcome in nonmatching if outcome.move.key != answer_outcome.move.key]
        return answer_outcome, select_random_outcomes(nonmatching, rng, count=len(nonmatching)), {}

    return _select_target_clear_outcomes


def _prepare_target_clear_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    _selected_branch: str,
    _branch_probabilities: Mapping[str, float],
    _axes: Match3SceneAxes,
    gen_defaults: Mapping[str, Any],
) -> Match3ObjectivePlan:
    """Resolve target-clear and option axes for exact-count swap selection."""

    namespace = f"{SCENE_ID}.target_clear_swap"
    target_axis = resolve_match3_integer_axis(
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        params=task_params,
        support_key="target_clear_count_support",
        explicit_key="target_answer",
        fallback_support=DEFAULTS.target_clear_count_support,
        namespace=f"{namespace}.target_clear_count",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    return prepare_match3_swap_option_plan(
        instance_seed=int(instance_seed),
        task_params=task_params,
        gen_defaults=gen_defaults,
        namespace=namespace,
        prompt_slots=PROMPT_SLOTS,
        outcome_selector=_build_target_clear_selector(int(target_axis.value)),
        target_clear_count=int(target_axis.value),
        extra_params={
            "target_answer": int(target_axis.value),
            "target_answer_probabilities": dict(target_axis.probabilities),
        },
    )


@register_task
class GamesMatch3TargetClearSwapLabelTask(Match3SingleQueryTaskBase):
    """Choose the labeled match-3 swap that clears a target number of gems."""

    task_id = TASK_ID
    _namespace = f"{SCENE_ID}.target_clear_swap"
    _default_branch = "single"
    _prepare_objective = staticmethod(_prepare_target_clear_objective)

    def generate(self, instance_seed: int, *, params: dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        return run_match3_registered_task(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GamesMatch3TargetClearSwapLabelTask", "TASK_ID"]
