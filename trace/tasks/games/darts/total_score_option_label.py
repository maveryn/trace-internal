"""Choose the visible option letter for a dart score."""

from __future__ import annotations

from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import DartsObjectivePlan, dart_point_set_attempt, run_darts_lifecycle
from .shared.defaults import DEFAULTS, SCENE_ID
from .shared.prompts import darts_label_json_examples, darts_output_slots
from .shared.sampling import (
    resolve_darts_integer_axis,
    resolve_score_option_answer_label,
    sample_darts_for_score_options,
)
from .shared.state import DartsSceneAxes


TASK_ID = "task_games__darts__total_score_option_label"
QUERY_ID = "total_score"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_total_score_objective(
    instance_seed,
    task_params,
    _query_id,
    _query_probabilities,
    render_params,
):
    """Resolve option layout axes and bind the one-dart score sampler."""

    dart_count_axis = resolve_darts_integer_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="total_score_dart_count_support",
        explicit_key="dart_count",
        fallback_support=DEFAULTS.total_score_dart_count_support,
        namespace="total_score.dart_count",
        balanced_flag_key="balanced_dart_count_sampling",
    )
    option_count_axis = resolve_darts_integer_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="score_option_count_support",
        explicit_key="score_option_count",
        fallback_support=DEFAULTS.score_option_count_support,
        namespace="total_score.score_option_count",
        balanced_flag_key="balanced_score_option_count_sampling",
    )
    answer_label = resolve_score_option_answer_label(
        instance_seed=int(instance_seed),
        params=task_params,
        option_count=int(option_count_axis.value),
    )
    json_example, json_example_answer_only = darts_label_json_examples()
    prompt_dynamic_slots = darts_output_slots(
        prompt_query_key=QUERY_ID,
        json_example=json_example,
        json_example_answer_only=json_example_answer_only,
    )
    query_params = {
        "dart_count": int(dart_count_axis.value),
        "dart_count_support": [int(value) for value in dart_count_axis.support],
        "dart_count_probabilities": dict(dart_count_axis.probabilities),
        "score_option_count": int(option_count_axis.value),
        "score_option_count_support": [int(value) for value in option_count_axis.support],
        "score_option_count_probabilities": dict(option_count_axis.probabilities),
        "answer_label": str(answer_label),
    }

    def construct_attempt(rng, _axes: DartsSceneAxes):
        sample = sample_darts_for_score_options(
            rng,
            dart_count=int(dart_count_axis.value),
            render_params=render_params,
            option_count=int(option_count_axis.value),
            correct_label=str(answer_label),
        )
        if sample.answer_label is None:
            raise ValueError("total-score darts sample is missing answer label")
        return dart_point_set_attempt(
            sample=sample,
            answer_gt=TypedValue(type="string", value=str(sample.answer_label)),
            query_params={
                "total_score": int(sample.total_score),
                "score_options": [
                    {"label": str(option.label), "score": int(option.score), "is_answer": bool(option.is_answer)}
                    for option in sample.score_options
                ],
            },
            execution_extra={
                "total_score": int(sample.total_score),
                "answer_label": str(sample.answer_label),
            },
        )

    return DartsObjectivePlan(
        attempt_namespace="games.darts.total_score",
        prompt_query_key=QUERY_ID,
        query_params=query_params,
        prompt_dynamic_slots=prompt_dynamic_slots,
        construct_attempt=construct_attempt,
    )


@register_task
class GamesDartsTotalScoreOptionLabelTask:
    """Choose the option letter matching the score of the marked dart."""

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
            prepare_objective=_prepare_total_score_objective,
        )


__all__ = ["GamesDartsTotalScoreOptionLabelTask"]
