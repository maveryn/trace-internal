"""Count the minimum empty-cell gap for a Hex side-to-side connection."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.assembly import build_hex_components
from .shared.sampling import resolve_hex_integer_axis, resolve_hex_scene_axes, sample_gap_count_scene
from .shared.state import SCENE_ID


TASK_ID = "task_games__hex__connection_gap_count"
SUPPORTED_QUERY_IDS = ("connection_gap_count",)
GAP_COUNT_SUPPORT = (1, 2, 3, 4, 5)

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesHexConnectionGapCountTask:
    """Count the unique minimum empty-cell set needed to connect Hex sides."""

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
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        scene_axes = resolve_hex_scene_axes(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            namespace=TASK_ID,
        )
        target_axis = resolve_hex_integer_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="connection_gap_count_support",
            explicit_key="target_answer",
            fallback_support=GAP_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.target_answer",
            balanced_flag_key="balanced_target_answer_sampling",
        )

        sampled_scene = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = sample_gap_count_scene(
                    rng=rng,
                    scene_axes=scene_axes,
                    target_answer=int(target_axis.value),
                    params=task_params,
                    gen_defaults=_GEN_DEFAULTS,
                )
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid Hex scene after {max_attempts} attempts")

        components = build_hex_components(
            domain=self.domain,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
            prompt_query_key=str(query_id),
            scene_axes=scene_axes,
            sample=sampled_scene,
            annotation_coords=tuple(sampled_scene.annotation_coords),
            answer_type="integer",
            answer_value=int(sampled_scene.answer),
            target_axis=target_axis,
        )
        return TaskOutput(
            prompt=str(components.prompt),
            prompt_variants=dict(components.prompt_variants),
            answer_gt=TypedValue(type=str(components.answer_type), value=components.answer_value),
            annotation_gt=TypedValue(type=str(components.annotation_type), value=components.annotation_value),
            image=components.image,
            image_id="img0",
            trace_payload=dict(components.trace_payload),
            task_versions=default_task_versions(),
            query_id=str(components.query_id),
            scene_id=SCENE_ID,
        )


__all__ = ["GamesHexConnectionGapCountTask"]
