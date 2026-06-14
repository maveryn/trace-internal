"""Count darts in one highlighted numbered sector on a simplified dartboard."""

from __future__ import annotations

from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import prepare_darts_exact_count_objective, run_darts_lifecycle
from .shared.defaults import SCENE_ID
from .shared.prompts import darts_integer_json_examples, darts_output_slots
from .shared.sampling import (
    resolve_darts_target_sector_axis,
    sector_nonqualifying_slots,
    sector_qualifying_slots,
)


TASK_ID = "task_games__darts__sector_dart_count"
QUERY_ID = "single"
PROMPT_QUERY_KEY = "sector_dart_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_sector_count_objective(
    instance_seed,
    task_params,
    _query_id,
    _query_probabilities,
    render_params,
):
    """Resolve the target sector and bind sector membership to exact count."""

    sector_axis = resolve_darts_target_sector_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
    )
    target_sector = int(sector_axis.value)
    json_example, json_example_answer_only = darts_integer_json_examples()
    prompt_dynamic_slots = darts_output_slots(
        prompt_query_key=PROMPT_QUERY_KEY,
        json_example=json_example,
        json_example_answer_only=json_example_answer_only,
        extra_slots={"target_sector_text": str(target_sector)},
    )
    return prepare_darts_exact_count_objective(
        task_params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        render_params=render_params,
        instance_seed=int(instance_seed),
        target_namespace="sector_dart_count",
        attempt_namespace=f"games.darts.sector_dart_count.{target_sector}",
        prompt_query_key=PROMPT_QUERY_KEY,
        prompt_dynamic_slots=prompt_dynamic_slots,
        qualifying_slots=sector_qualifying_slots(target_sector),
        nonqualifying_slots=sector_nonqualifying_slots(target_sector),
        extra_query_params={
            "target_sector": target_sector,
            "target_sector_support": [int(value) for value in sector_axis.support],
            "target_sector_probabilities": dict(sector_axis.probabilities),
        },
        extra_execution_params={"target_sector": target_sector},
        target_sector_value=target_sector,
    )


@register_task
class GamesDartsSectorDartCountTask:
    """Count darts landing inside one highlighted numbered sector."""

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
            prepare_objective=_prepare_sector_count_objective,
        )


__all__ = ["GamesDartsSectorDartCountTask"]
