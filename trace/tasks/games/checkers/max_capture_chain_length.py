"""Find the longest capture chain for a marked Checkers king."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.checkers.shared.annotations import checkers_annotation_artifacts
from trace.tasks.games.checkers.shared.mechanics import player_name
from trace.tasks.games.checkers.shared.output import build_checkers_common_trace_payload, checkers_common_trace_params
from trace.tasks.games.checkers.shared.prompts import build_checkers_prompt_artifacts
from trace.tasks.games.checkers.shared.rendering import render_checkers_task_scene
from trace.tasks.games.checkers.shared.sampling import (
    resolve_checkers_scene_axes,
    resolve_checkers_target_answer,
    sample_king_capture_chain_scene,
    scene_object_description,
)
from trace.tasks.games.checkers.shared.state import SCENE_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__checkers__max_capture_chain_length"
QUERY_ID = DEFAULT_QUERY_ID
PROMPT_QUERY_KEY = "max_capture_chain_length"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
MAX_CAPTURE_CHAIN_LENGTH_SUPPORT: Tuple[int, ...] = (1, 2, 3, 4, 5)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesCheckersMaxCaptureChainLengthTask:
    """Find the maximum capture-chain length for the marked king checker."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        resolved, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        axes = resolve_checkers_scene_axes(int(instance_seed), params=task_params)
        target_axis = resolve_checkers_target_answer(
            instance_seed=int(instance_seed),
            params=task_params,
            support_key="max_capture_chain_length_support",
            fallback_support=MAX_CAPTURE_CHAIN_LENGTH_SUPPORT,
            namespace=f"{TASK_ID}.target_answer",
            gen_defaults=_GEN_DEFAULTS,
        )

        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_king_capture_chain_scene(
                    rng=rng,
                    axes=axes,
                    params=task_params,
                    target_answer=int(target_axis.target_answer),
                )
            except ValueError as exc:
                last_error = exc
                continue

            rendered_context = render_checkers_task_scene(
                axes=axes,
                sample=sample,
                params=task_params,
                instance_seed=int(instance_seed),
            )
            annotation_artifacts = checkers_annotation_artifacts(
                rendered_scene=rendered_context.rendered_scene,
                entity_ids=sample.evaluation.annotation_entity_ids,
                annotation_kind=sample.evaluation.annotation_kind,
            )
            prompt_defaults, prompt_artifacts = build_checkers_prompt_artifacts(
                domain=self.domain,
                prompt_query_key=PROMPT_QUERY_KEY,
                dynamic_slots={
                    "object_description": scene_object_description(str(axes.scene_variant)),
                    "current_player_name": player_name(int(sample.current_player)),
                },
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="integer", value=int(target_axis.target_answer))
            query_spec = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=str(resolved),
                params=checkers_common_trace_params(
                    axes,
                    sample,
                    extra_params={
                        "prompt_query_key": PROMPT_QUERY_KEY,
                        "target_answer": int(target_axis.target_answer),
                        "target_answer_support": [int(value) for value in target_axis.target_answer_support],
                        "target_answer_probabilities": dict(target_axis.target_answer_probabilities),
                        "query_id_probabilities": dict(query_id_probabilities),
                    },
                ),
            )
            trace_payload = build_checkers_common_trace_payload(
                annotation_artifacts=annotation_artifacts,
                axes=axes,
                sample=sample,
                rendered_context=rendered_context,
                prompt_defaults=prompt_defaults,
                prompt_artifacts=prompt_artifacts,
                prompt_query_spec=query_spec,
                execution_extra={
                    "query_id": str(resolved),
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "target_answer": int(target_axis.target_answer),
                    "answer": int(answer_gt.value),
                },
            )
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                annotation_gt=annotation_artifacts.annotation_gt,
                image=rendered_context.image,
                image_id="img0",
                trace_payload=trace_payload,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(resolved),
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid Checkers capture-chain scene") from last_error


__all__ = ["GamesCheckersMaxCaptureChainLengthTask"]
