"""Winning-payline count task for slot-machine games."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support

from ._lifecycle import SlotMachineAttemptResult, SlotMachineObjectivePlan, run_slot_machine_lifecycle
from .shared.defaults import SCENE_ID, SCENE_NAMESPACE, WINNING_PAYLINE_COUNT_SUPPORT
from .shared.prompts import slot_integer_segment_set_json_examples, slot_output_slots
from .shared.sampling import sample_slot_machine_grid
from .shared.state import SlotMachineAxes


TASK_ID = "task_games__slot_machine__winning_payline_count"
QUERY_ID = DEFAULT_QUERY_ID
PROMPT_QUERY_KEY = "winning_payline_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _resolve_target_winning_count(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
) -> tuple[int, dict[str, float], tuple[int, ...]]:
    """Resolve the task-owned winning-payline count target."""

    support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="winning_payline_count_support",
        fallback=WINNING_PAYLINE_COUNT_SUPPORT,
    )
    target, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="winning_payline_count_support",
        explicit_key="target_winning_payline_count",
        fallback_support=support,
        namespace=f"{TASK_ID}.target_winning_payline_count",
        balanced_flag_key="balanced_winning_payline_count_sampling",
        namespace_support_permutation=True,
    )
    return int(target), dict(probabilities), tuple(int(value) for value in support)


def _prepare_winning_payline_count_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query: str,
    query_probabilities: Mapping[str, float],
    axes: SlotMachineAxes,
) -> SlotMachineObjectivePlan:
    """Bind the count target and prompt slots for winning paylines."""

    if str(selected_query) != QUERY_ID:
        raise ValueError(f"unsupported slot-machine query: {selected_query}")
    target_count, target_probabilities, target_support = _resolve_target_winning_count(
        int(instance_seed),
        params=task_params,
    )

    def construct_attempt(rng: Any, resolved_axes: SlotMachineAxes) -> SlotMachineAttemptResult:
        scene = sample_slot_machine_grid(
            rng=rng,
            axes=resolved_axes,
            target_winning_count=int(target_count),
        )
        return SlotMachineAttemptResult(
            scene=scene,
            answer_gt=TypedValue(type="integer", value=int(len(scene.winning_rows))),
            annotation_payline_rows=tuple(int(row) for row in scene.winning_rows),
            query_params={},
            execution_extra={
                "target_winning_payline_count": int(target_count),
                "winning_payline_count_support": [int(value) for value in target_support],
                "winning_payline_count_probabilities": dict(target_probabilities),
            },
        )

    json_example, json_example_answer_only = slot_integer_segment_set_json_examples()
    return SlotMachineObjectivePlan(
        attempt_namespace=f"{SCENE_NAMESPACE}.winning_payline_count.{int(target_count)}",
        prompt_query_key=PROMPT_QUERY_KEY,
        query_params={
            "target_winning_payline_count": int(target_count),
            "winning_payline_count_support": [int(value) for value in target_support],
            "winning_payline_count_probabilities": dict(target_probabilities),
            "query_id_probabilities": dict(query_probabilities),
        },
        prompt_dynamic_slots=slot_output_slots(
            prompt_query_key=PROMPT_QUERY_KEY,
            json_example=json_example,
            json_example_answer_only=json_example_answer_only,
        ),
        construct_attempt=construct_attempt,
    )


@register_task
class GamesSlotMachineWinningPaylineCountTask:
    """Count horizontal paylines whose five visible symbols all match."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_slot_machine_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=dict(params or {}),
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_winning_payline_count_objective,
        )


__all__ = ["GamesSlotMachineWinningPaylineCountTask", "TASK_ID"]
