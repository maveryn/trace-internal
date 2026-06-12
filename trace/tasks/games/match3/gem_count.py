"""Count named-color gems in a match-3 grid scope."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.scene import (
    QUERY_GRID_COLOR_GEM_COUNT,
    SCENE_ID,
    SUPPORTED_GEM_COUNT_QUERIES,
    build_components,
    sample_gem_count,
    sample_scene_variant,
    sample_style_variant,
)


TASK_ID = "task_games__match3__gem_count"
SUPPORTED_QUERY_IDS = SUPPORTED_GEM_COUNT_QUERIES
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesMatch3GemCountTask:
    """Count canonical named-color gems in the grid or one numbered row/column."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any] | None = None,
        max_attempts: int = 100,
    ) -> TaskOutput:
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params or {},
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_GRID_COLOR_GEM_COUNT,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        namespace = f"{SCENE_ID}.{query_id}"
        scene_variant, scene_variant_probabilities = sample_scene_variant(
            gen_defaults=_GEN_DEFAULTS,
            namespace=namespace,
            instance_seed=int(instance_seed),
            params=task_params,
        )
        style_variant, style_variant_probabilities = sample_style_variant(
            gen_defaults=_GEN_DEFAULTS,
            namespace=namespace,
            instance_seed=int(instance_seed),
            params=task_params,
        )

        sample = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_gem_count(
                    rng,
                    gen_defaults=_GEN_DEFAULTS,
                    namespace=namespace,
                    instance_seed=int(instance_seed),
                    params=task_params,
                    scene_variant=str(scene_variant),
                    query_id=str(query_id),
                )
            except ValueError:
                continue
            break
        if sample is None:
            raise RuntimeError(f"{TASK_ID} failed to generate after {max_attempts} attempts")

        components = build_components(
            sample=sample,
            scene_variant_probabilities=scene_variant_probabilities,
            style_variant=str(style_variant),
            style_variant_probabilities=style_variant_probabilities,
            query_id_probabilities=query_id_probabilities,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            namespace=namespace,
        )
        return TaskOutput(
            prompt=str(components.prompt),
            prompt_variants=dict(components.prompt_variants),
            answer_gt=components.answer_gt,
            annotation_gt=components.annotation_gt,
            image=components.image,
            image_id="img0",
            trace_payload=components.trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["GamesMatch3GemCountTask"]
