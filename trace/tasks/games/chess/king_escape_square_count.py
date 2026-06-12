"""Count safe one-step destination squares for a marked chess king."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.chess.shared.annotations import bbox_set_for_entities, projected_bbox_payload
from trace.tasks.games.chess.shared.output import common_trace_sections
from trace.tasks.games.chess.shared.prompts import build_chess_prompt_artifacts
from trace.tasks.games.chess.shared.rendering import render_chess_task_scene
from trace.tasks.games.chess.shared.sampling import resolve_chess_scene_axes, resolve_target_answer, sample_king_escape_scene
from trace.tasks.games.chess.shared.state import SCENE_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__chess__king_escape_square_count"
QUERY_ID = "king_escape_square_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
KING_ESCAPE_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)

@register_task
class GamesChessKingEscapeSquareCountTask:
    """Count safe one-step destinations for the marked king."""

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
        axes = resolve_chess_scene_axes(int(instance_seed), params=task_params)
        target_answer, answer_support, answer_probs = resolve_target_answer(
            instance_seed=int(instance_seed),
            params=task_params,
            support_key="king_escape_square_count_support",
            fallback_support=KING_ESCAPE_SUPPORT,
            namespace=f"{TASK_ID}.target_answer",
            gen_defaults=_GEN_DEFAULTS,
        )

        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{attempt_index}")
            try:
                sample = sample_king_escape_scene(rng=rng, axes=axes, target_answer=int(target_answer))
            except ValueError as exc:
                last_error = exc
                continue
            rendered_context = render_chess_task_scene(
                board=sample.board,
                scene_variant=sample.scene_variant,
                style_variant=sample.style_variant,
                badge_text="Marked king",
                marked_coord=sample.marked_coord,
                params=task_params,
                instance_seed=int(instance_seed),
            )
            annotation_bboxes = bbox_set_for_entities(
                rendered_context.rendered_scene,
                entity_ids=sample.annotation_entity_ids,
                annotation_kind=sample.annotation_kind,
            )
            _prompt_defaults, prompt_artifacts = build_chess_prompt_artifacts(
                domain=self.domain,
                prompt_query_key=query_id,
                dynamic_slots={},
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="integer", value=int(target_answer))
            annotation_gt = TypedValue(type="bbox_set", value=annotation_bboxes)
            trace_payload = common_trace_sections(sample=sample, rendered_context=rendered_context)
            trace_payload["query_spec"] = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=query_id,
                params={
                    "target_answer": int(target_answer),
                    "target_answer_support": [int(value) for value in answer_support],
                    "target_answer_probabilities": dict(answer_probs),
                    "query_id_probabilities": dict(query_id_probabilities),
                },
            )
            trace_payload["execution_trace"].update(
                {
                    "query_id": str(query_id),
                    "target_answer": int(target_answer),
                    "answer": int(answer_gt.value),
                }
            )
            trace_payload["projected_annotation"] = projected_bbox_payload(annotation_bboxes)
            trace_payload["witness_symbolic"] = {
                "type": "cell_set",
                "ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                annotation_gt=annotation_gt,
                image=rendered_context.image,
                image_id="img0",
                trace_payload=trace_payload,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=query_id,
            )

        raise RuntimeError(f"{self.task_id} failed to generate a chess king-escape scene") from last_error


__all__ = ["GamesChessKingEscapeSquareCountTask"]
