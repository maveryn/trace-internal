"""Count visible Checkers pieces by color and board-edge state."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.checkers.shared.annotations import checkers_annotation_artifacts
from trace.tasks.games.checkers.shared.mechanics import BLACK, RED
from trace.tasks.games.checkers.shared.output import build_checkers_common_trace_payload, checkers_common_trace_params
from trace.tasks.games.checkers.shared.prompts import build_checkers_prompt_artifacts
from trace.tasks.games.checkers.shared.rendering import render_checkers_task_scene
from trace.tasks.games.checkers.shared.sampling import (
    resolve_checkers_scene_axes,
    resolve_checkers_target_answer,
    sample_piece_state_scene,
    scene_object_description,
)
from trace.tasks.games.checkers.shared.state import SCENE_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__checkers__piece_state_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "red_piece_count",
    "black_piece_count",
    "red_edge_piece_count",
    "black_edge_piece_count",
)
QUERY_SETTINGS: Mapping[str, Mapping[str, Any]] = {
    "red_piece_count": {"player": RED, "edge_only": False},
    "black_piece_count": {"player": BLACK, "edge_only": False},
    "red_edge_piece_count": {"player": RED, "edge_only": True},
    "black_edge_piece_count": {"player": BLACK, "edge_only": True},
}
PIECE_STATE_COUNT_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float], Dict[str, Any]]:
    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SUPPORTED_QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


@register_task
class GamesCheckersPieceStateCountTask:
    """Count visible Checkers pieces by color and board-edge state."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected, branch_probs, task_params = _select_query(int(instance_seed), params)
        settings = dict(QUERY_SETTINGS[selected])
        axes = resolve_checkers_scene_axes(int(instance_seed), params=task_params)
        target_axis = resolve_checkers_target_answer(
            instance_seed=int(instance_seed),
            params=task_params,
            support_key="piece_state_count_support",
            fallback_support=PIECE_STATE_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.target_answer.{selected}",
            gen_defaults=_GEN_DEFAULTS,
        )

        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_piece_state_scene(
                    rng=rng,
                    axes=axes,
                    params=task_params,
                    target_answer=int(target_axis.target_answer),
                    player=int(settings["player"]),
                    edge_only=bool(settings["edge_only"]),
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
                prompt_query_key=selected,
                dynamic_slots={
                    "object_description": scene_object_description(str(axes.scene_variant)),
                },
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="integer", value=int(target_axis.target_answer))
            query_spec = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=selected,
                params=checkers_common_trace_params(
                    axes,
                    sample,
                    extra_params={
                        "target_answer": int(target_axis.target_answer),
                        "target_answer_support": [int(value) for value in target_axis.target_answer_support],
                        "target_answer_probabilities": dict(target_axis.target_answer_probabilities),
                        "query_id_probabilities": dict(branch_probs),
                        "target_player": "red" if int(settings["player"]) == int(RED) else "black",
                        "edge_only": bool(settings["edge_only"]),
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
                    "query_id": str(selected),
                    "target_answer": int(target_axis.target_answer),
                    "answer": int(answer_gt.value),
                    "target_player": "red" if int(settings["player"]) == int(RED) else "black",
                    "edge_only": bool(settings["edge_only"]),
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
                query_id=selected,
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid Checkers piece-state scene") from last_error


__all__ = ["GamesCheckersPieceStateCountTask"]
