"""Count loose dominoes matching the open chain end."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.assembly import build_domino_components
from .shared.sampling import (
    resolve_domino_candidate_count_axis,
    resolve_domino_scene_axes,
    resolve_domino_target_axis,
    sample_matching_end_scene,
)
from .shared.state import DEFAULTS, SCENE_ID


TASK_ID = "task_games__dominoes__matching_end_count"
QUERY_ID = "matching_end_count"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesDominoesMatchingEndCountTask:
    """Count loose dominoes that can connect to the marked reference end."""

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
        scene_axes = resolve_domino_scene_axes(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
        target_axis = resolve_domino_target_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="matching_end_target_answer_support",
            fallback_support=DEFAULTS.matching_end_target_answer_support,
            namespace=f"{QUERY_ID}.target_answer",
        )
        candidate_axis = resolve_domino_candidate_count_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            scene_variant=str(scene_axes.scene_variant),
            objective_key=QUERY_ID,
            target_answer=int(target_axis.value),
        )
        sampled_scene = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.dominoes.{QUERY_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = sample_matching_end_scene(
                    rng,
                    candidate_count=int(candidate_axis.value),
                    target_answer=int(target_axis.value),
                )
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid dominoes scene after {max_attempts} attempts")

        query_params = {
            "target_answer": int(sampled_scene.answer_value),
            "target_answer_index": int(target_axis.value),
            "target_answer_support": [int(value) for value in target_axis.support],
            "target_answer_probabilities": dict(target_axis.probabilities),
            "candidate_count": int(candidate_axis.value),
            "candidate_count_support": [int(value) for value in candidate_axis.support],
            "candidate_count_probabilities": dict(candidate_axis.probabilities),
            "target_total": None if sampled_scene.target_total is None else int(sampled_scene.target_total),
        }
        components = build_domino_components(
            domain=self.domain,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
            scene_axes=scene_axes,
            sampled_scene=sampled_scene,
            query_params=query_params,
            prompt_query_key=PROMPT_QUERY_KEY,
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


__all__ = ["GamesDominoesMatchingEndCountTask"]
