"""Choose the marble-chain shot direction with a requested pop count."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from ._lifecycle import MarbleObjectivePlan, MarbleSingleQueryTaskBase, prepare_marble_direction_option_plan, run_marble_registered_task
from .shared.defaults import SCENE_ID
from .shared.prompts import make_marble_prompt_slots
from .shared.sampling import resolve_target_pop_axis
from .shared.state import MarbleOutcome, MarbleSceneAxes, ShotOption


TASK_ID = "task_games__marble_chain__target_pop_direction_label"
PROMPT_SLOTS = make_marble_prompt_slots(
    prompt_query_key="target_pop_direction_label",
    answer_hint_key="answer_hint_target_pop_direction_label",
    annotation_hint_key="annotation_hint_target_pop_direction_label",
    example_annotation=[465, 286],
    example_answer="B",
)


def _target_pop_slot_groups(target_pop_count: int):
    """Build a slot grouping callback for the requested pop count."""

    target = int(target_pop_count)

    def slot_groups(outcomes: Mapping[int, MarbleOutcome]) -> tuple[list[int], list[int]]:
        """Return answer and distractor slots for the target-pop objective."""

        answer_candidates = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) == int(target)]
        if int(target) == 0:
            distractor_candidates = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) > 0]
        else:
            distractor_candidates = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) != int(target)]
        return answer_candidates, distractor_candidates

    return slot_groups


def _target_pop_display_validator(target_pop_count: int):
    """Build a display validator that enforces one target-pop option."""

    target = int(target_pop_count)

    def has_unique_target(options: Sequence[ShotOption]) -> bool:
        """Check that exactly one displayed arrow has the target pop count."""

        return sum(1 for option in options if int(option.outcome.pop_count) == int(target)) == 1

    return has_unique_target


def _target_axis_trace_params(target_axis: Any) -> dict[str, Any]:
    """Serialize target-pop axis metadata owned by this target-count task."""

    return {
        "target_pop_count": int(target_axis.value),
        "target_pop_count_support": [int(value) for value in target_axis.support],
        "target_pop_count_probabilities": dict(target_axis.probabilities),
    }


def _prepare_target_pop_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    _selected_query_id: str,
    _branch_probabilities: Mapping[str, float],
    _axes: MarbleSceneAxes,
    gen_defaults: Mapping[str, Any],
) -> MarbleObjectivePlan:
    """Resolve axes and bind target-pop option semantics."""

    namespace = f"{SCENE_ID}.target_pop_direction"
    target_axis = resolve_target_pop_axis(
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        params=task_params,
        namespace=namespace,
    )
    return prepare_marble_direction_option_plan(
        instance_seed=int(instance_seed),
        task_params=task_params,
        gen_defaults=gen_defaults,
        namespace=namespace,
        prompt_slots=PROMPT_SLOTS,
        slot_group_builder=_target_pop_slot_groups(int(target_axis.value)),
        display_validator=_target_pop_display_validator(int(target_axis.value)),
        target_pop_count=int(target_axis.value),
        extra_params=_target_axis_trace_params(target_axis),
    )


@register_task
class GamesMarbleChainTargetPopDirectionLabelTask(MarbleSingleQueryTaskBase):
    """Choose the marble-chain shot direction with a requested pop count."""

    task_id = TASK_ID
    _namespace = f"{SCENE_ID}.target_pop_direction"
    _prepare_objective = staticmethod(_prepare_target_pop_objective)

    def generate(self, instance_seed: int, *, params: dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        return run_marble_registered_task(self, instance_seed, params=params, max_attempts=max_attempts)


__all__ = ["GamesMarbleChainTargetPopDirectionLabelTask", "TASK_ID"]
