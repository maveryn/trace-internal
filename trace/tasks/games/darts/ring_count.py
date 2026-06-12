"""Count marked darts in the requested dartboard ring."""

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
    SCORE_SLOTS,
    resolve_darts_count_target_axis,
    resolve_darts_integer_axis,
    resolve_darts_render_params,
    resolve_darts_scene_axes,
    resolve_darts_target_ring,
    sample_darts_for_count,
    score_slot_in_ring,
)
from .shared.state import DEFAULTS, SCENE_ID


TASK_ID = "task_games__darts__ring_count"
QUERY_ID = "ring_count"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesDartsRingCountTask:
    """Count marked darts landing inside the highlighted dartboard ring."""

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
            support_key="count_query_dart_count_support",
            explicit_key="dart_count",
            fallback_support=DEFAULTS.count_query_dart_count_support,
            namespace="ring_count.dart_count",
            balanced_flag_key="balanced_dart_count_sampling",
        )
        target_axis = resolve_darts_count_target_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            dart_count=int(dart_count_axis.value),
            namespace="ring_count.target_answer",
        )
        target_ring, target_ring_probabilities = resolve_darts_target_ring(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
        )
        render_params = resolve_darts_render_params(
            task_params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        qualifying_slots = [slot for slot in SCORE_SLOTS if score_slot_in_ring(slot, target_ring=str(target_ring))]
        nonqualifying_slots = [slot for slot in SCORE_SLOTS if not score_slot_in_ring(slot, target_ring=str(target_ring))]
        sampled_scene = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.darts.ring_count.attempt.{int(attempt_index)}")
            try:
                sampled_scene = sample_darts_for_count(
                    rng,
                    dart_count=int(dart_count_axis.value),
                    target_answer=int(target_axis.value),
                    render_params=render_params,
                    qualifying_slots=qualifying_slots,
                    nonqualifying_slots=nonqualifying_slots,
                )
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid darts ring-count scene after {max_attempts} attempts")
        query_params = {
            "dart_count": int(dart_count_axis.value),
            "dart_count_support": [int(value) for value in dart_count_axis.support],
            "dart_count_probabilities": dict(dart_count_axis.probabilities),
            "target_answer": int(target_axis.value),
            "target_answer_support": [int(value) for value in target_axis.support],
            "target_answer_probabilities": dict(target_axis.probabilities),
            "target_ring": str(target_ring),
            "target_ring_probabilities": dict(target_ring_probabilities),
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
            answer_type="integer",
            answer_value=int(target_axis.value),
            prompt_query_key=PROMPT_QUERY_KEY,
            query_params=query_params,
            target_ring_highlight=str(target_ring),
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


__all__ = ["GamesDartsRingCountTask"]
