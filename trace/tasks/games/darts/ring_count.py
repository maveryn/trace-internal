"""Count marked darts in the requested dartboard ring."""

from __future__ import annotations

from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import prepare_darts_exact_count_objective, run_darts_lifecycle
from .shared.defaults import SCENE_ID
from .shared.prompts import darts_integer_count_json_examples, darts_output_slots, darts_target_ring_prompt_text
from .shared.rules import SCORE_SLOTS, score_slot_in_ring
from .shared.sampling import (
    resolve_darts_target_ring,
)


TASK_ID = "task_games__darts__ring_count"
QUERY_ID = "ring_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_ring_count_objective(
    instance_seed,
    task_params,
    _query_id,
    _query_probabilities,
    render_params,
):
    """Resolve ring membership and delegate only the exact-count mechanics."""

    target_ring, target_ring_probabilities = resolve_darts_target_ring(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
    )
    qualifying_slots = [slot for slot in SCORE_SLOTS if score_slot_in_ring(slot, target_ring=str(target_ring))]
    nonqualifying_slots = [slot for slot in SCORE_SLOTS if not score_slot_in_ring(slot, target_ring=str(target_ring))]
    json_example, json_example_answer_only = darts_integer_count_json_examples()
    prompt_dynamic_slots = {
        **darts_output_slots(
            prompt_query_key=QUERY_ID,
            json_example=json_example,
            json_example_answer_only=json_example_answer_only,
        ),
        "target_ring_text": darts_target_ring_prompt_text(str(target_ring)),
    }
    return prepare_darts_exact_count_objective(
        task_id=TASK_ID,
        task_params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        render_params=render_params,
        instance_seed=int(instance_seed),
        target_namespace="ring_count",
        attempt_namespace="games.darts.ring_count",
        prompt_query_key=QUERY_ID,
        prompt_dynamic_slots=prompt_dynamic_slots,
        qualifying_slots=tuple(qualifying_slots),
        nonqualifying_slots=tuple(nonqualifying_slots),
        extra_query_params={
            "target_ring": str(target_ring),
            "target_ring_probabilities": dict(target_ring_probabilities),
        },
        extra_execution_params={"target_ring": str(target_ring)},
        target_ring_highlight=str(target_ring),
    )


@register_task
class GamesDartsRingCountTask:
    """Count marked darts landing inside the highlighted dartboard ring."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        return run_darts_lifecycle(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            prepare_objective=_prepare_ring_count_objective,
        )


__all__ = ["GamesDartsRingCountTask"]
