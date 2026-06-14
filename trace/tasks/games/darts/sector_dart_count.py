"""Count darts in one highlighted numbered sector on a simplified dartboard."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import DartsObjectivePlan, dart_point_set_attempt, run_darts_lifecycle
from .shared.defaults import SCENE_ID
from .shared.prompts import darts_integer_json_examples, darts_output_slots
from .shared.sampling import (
    resolve_darts_integer_axis,
    resolve_darts_target_sector_axis,
    sample_darts_for_count,
    sector_nonqualifying_slots,
    sector_qualifying_slots,
)


TASK_ID = "task_games__darts__sector_dart_count"
QUERY_ID = "single"
PROMPT_QUERY_KEY = "sector_dart_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
TARGET_ANSWER_SUPPORT = (0, 1, 2, 3, 4)
DISTRACTOR_COUNT_SUPPORT = (1, 2, 3, 4, 5, 6)
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
    target_answer_axis = resolve_darts_integer_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="sector_target_answer_support",
        explicit_key="target_answer",
        fallback_support=TARGET_ANSWER_SUPPORT,
        namespace="sector_count.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    distractor_axis = resolve_darts_integer_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="sector_distractor_count_support",
        explicit_key="distractor_count",
        fallback_support=DISTRACTOR_COUNT_SUPPORT,
        namespace="sector_count.distractor_count",
        balanced_flag_key="balanced_distractor_count_sampling",
    )
    json_example, json_example_answer_only = darts_integer_json_examples()
    prompt_dynamic_slots = darts_output_slots(
        prompt_query_key=PROMPT_QUERY_KEY,
        json_example=json_example,
        json_example_answer_only=json_example_answer_only,
        extra_slots={"target_sector_text": str(target_sector)},
    )

    def construct_attempt(rng, _axes):
        sample = sample_darts_for_count(
            rng,
            dart_count=int(target_answer_axis.value) + int(distractor_axis.value),
            target_answer=int(target_answer_axis.value),
            render_params=render_params,
            qualifying_slots=sector_qualifying_slots(target_sector),
            nonqualifying_slots=sector_nonqualifying_slots(target_sector),
            target_sector_value=target_sector,
        )
        return dart_point_set_attempt(
            sample=sample,
            answer_gt=TypedValue(type="integer", value=int(target_answer_axis.value)),
            execution_extra={
                "target_answer": int(target_answer_axis.value),
                "distractor_count": int(distractor_axis.value),
                "target_sector": target_sector,
            },
        )

    return DartsObjectivePlan(
        attempt_namespace=f"games.darts.sector_dart_count.{target_sector}",
        prompt_query_key=PROMPT_QUERY_KEY,
        prompt_dynamic_slots=prompt_dynamic_slots,
        query_params={
            "target_answer": int(target_answer_axis.value),
            "target_answer_support": [int(value) for value in target_answer_axis.support],
            "target_answer_probabilities": dict(target_answer_axis.probabilities),
            "distractor_count": int(distractor_axis.value),
            "distractor_count_support": [int(value) for value in distractor_axis.support],
            "distractor_count_probabilities": dict(distractor_axis.probabilities),
            "target_sector": target_sector,
            "target_sector_support": [int(value) for value in sector_axis.support],
            "target_sector_probabilities": dict(sector_axis.probabilities),
        },
        construct_attempt=construct_attempt,
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
