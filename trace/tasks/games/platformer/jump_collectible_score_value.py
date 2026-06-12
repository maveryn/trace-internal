"""Sum collectible scores along a shown platformer jump path."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.scene import JUMP_COLLECTIBLE_SCORE_QUERY_ID, SCENE_ID, build_components, resolve_axes, sample_scene


TASK_ID = "task_games__platformer__jump_collectible_score_value"
QUERY_ID = JUMP_COLLECTIBLE_SCORE_QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesPlatformerJumpCollectibleScoreValueTask:
    """Sum collectible scores along the shown jump arc."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        namespace = f"{SCENE_ID}.{str(query_id)}"
        axes = resolve_axes(
            int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            namespace=namespace,
            params=task_params,
            query_id=str(query_id),
            query_id_probabilities=query_probabilities,
        )
        sampled = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled = sample_scene(rng=rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid platformer scene after {max_attempts} attempts")
        components = build_components(
            sampled_scene=sampled,
            axes=axes,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            namespace=namespace,
        )
        return TaskOutput(
            prompt=components.prompt,
            prompt_variants=components.prompt_variants,
            answer_gt=components.answer_gt,
            annotation_gt=components.annotation_gt,
            image=components.image,
            image_id="img0",
            trace_payload=components.trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["GamesPlatformerJumpCollectibleScoreValueTask"]
