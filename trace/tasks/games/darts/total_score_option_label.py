"""Choose the visible option letter for a dart score."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.assembly import build_darts_components
from .shared.sampling import (
    resolve_darts_integer_axis,
    resolve_darts_render_params,
    resolve_darts_scene_axes,
    resolve_score_option_answer_label,
    sample_darts_for_score_options,
)
from .shared.state import DEFAULTS, SCENE_ID


TASK_ID = "task_games__darts__total_score_option_label"
QUERY_ID = "total_score"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesDartsTotalScoreTask:
    """Choose the option letter matching the score of the marked dart."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        scene_axes = resolve_darts_scene_axes(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
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
        render_params = resolve_darts_render_params(
            task_params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        sampled_scene = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.darts.total_score.attempt.{int(attempt_index)}")
            try:
                sampled_scene = sample_darts_for_score_options(
                    rng,
                    dart_count=int(dart_count_axis.value),
                    render_params=render_params,
                    option_count=int(option_count_axis.value),
                    correct_label=str(answer_label),
                )
            except ValueError:
                continue
            break
        if sampled_scene is None or sampled_scene.answer_label is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid darts total-score scene after {max_attempts} attempts")
        query_params = {
            "dart_count": int(dart_count_axis.value),
            "dart_count_support": [int(value) for value in dart_count_axis.support],
            "dart_count_probabilities": dict(dart_count_axis.probabilities),
            "total_score": int(sampled_scene.total_score),
            "answer_label": str(sampled_scene.answer_label),
            "score_option_count": int(option_count_axis.value),
            "score_option_count_support": [int(value) for value in option_count_axis.support],
            "score_option_count_probabilities": dict(option_count_axis.probabilities),
            "score_options": [
                {"label": str(option.label), "score": int(option.score), "is_answer": bool(option.is_answer)}
                for option in sampled_scene.score_options
            ],
        }
        components = build_darts_components(
            domain=self.domain,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
            scene_axes=scene_axes,
            sampled_scene=sampled_scene,
            answer_type="string",
            answer_value=str(sampled_scene.answer_label),
            prompt_query_key=PROMPT_QUERY_KEY,
            query_params=query_params,
        )
        answer_gt = TypedValue(type=str(components.answer_type), value=components.answer_value)
        annotation_gt = TypedValue(type=str(components.annotation_type), value=components.annotation_value)
        return TaskOutput(
            prompt=str(components.prompt),
            prompt_variants=dict(components.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=components.image,
            image_id="img0",
            trace_payload=dict(components.trace_payload),
            task_versions=default_task_versions(),
            query_id=str(components.query_id),
            scene_id=SCENE_ID,
        )


__all__ = ["GamesDartsTotalScoreTask"]
