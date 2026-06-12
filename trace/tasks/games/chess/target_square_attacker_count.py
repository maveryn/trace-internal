"""Count chess pieces attacking a marked square."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.chess.shared.annotations import bbox_set_for_entities, projected_bbox_payload
from trace.tasks.games.chess.shared.output import common_trace_sections
from trace.tasks.games.chess.shared.prompts import build_chess_prompt_artifacts
from trace.tasks.games.chess.shared.rendering import render_chess_task_scene
from trace.tasks.games.chess.shared.sampling import (
    resolve_chess_scene_axes,
    resolve_player_color,
    resolve_target_answer,
    sample_target_square_attacker_scene,
)
from trace.tasks.games.chess.shared.state import SCENE_ID
from trace.tasks.games.shared.piece_board_rules import color_name, opponent
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__chess__target_square_attacker_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "king_square_attacker_count",
    "white_piece_attacks_target_square_count",
    "black_piece_attacks_target_square_count",
)
TARGET_ATTACKER_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3, 4)
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
class GamesChessTargetSquareAttackerCountTask:
    """Count pieces attacking the marked king or marked target square."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected, query_probs, task_params = _select_query(int(instance_seed), params)
        axes = resolve_chess_scene_axes(int(instance_seed), params=task_params)
        target_answer, answer_support, answer_probs = resolve_target_answer(
            instance_seed=int(instance_seed),
            params=task_params,
            support_key="target_square_attacker_count_support",
            fallback_support=TARGET_ATTACKER_SUPPORT,
            namespace=f"{TASK_ID}.target_answer.{selected}",
            gen_defaults=_GEN_DEFAULTS,
        )

        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{attempt_index}")
            if selected == "king_square_attacker_count":
                defender_color = resolve_player_color(rng, params=task_params)
                attacker_color = opponent(defender_color)
                target_has_king = True
                badge_text = "Marked king"
            elif selected == "white_piece_attacks_target_square_count":
                attacker_color = "white"
                target_has_king = False
                badge_text = "Target square"
            else:
                attacker_color = "black"
                target_has_king = False
                badge_text = "Target square"

            try:
                sample = sample_target_square_attacker_scene(
                    rng=rng,
                    axes=axes,
                    attacker_color=str(attacker_color),
                    target_answer=int(target_answer),
                    target_has_king=bool(target_has_king),
                )
            except ValueError as exc:
                last_error = exc
                continue
            rendered_context = render_chess_task_scene(
                board=sample.board,
                scene_variant=sample.scene_variant,
                style_variant=sample.style_variant,
                badge_text=badge_text,
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
                prompt_query_key=selected,
                dynamic_slots={},
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="integer", value=int(target_answer))
            annotation_gt = TypedValue(type="bbox_set", value=annotation_bboxes)
            trace_payload = common_trace_sections(sample=sample, rendered_context=rendered_context)
            trace_payload["query_spec"] = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=selected,
                params={
                    "target_answer": int(target_answer),
                    "target_answer_support": [int(value) for value in answer_support],
                    "target_answer_probabilities": dict(answer_probs),
                    "query_id_probabilities": dict(query_probs),
                    "attacker_color": str(attacker_color),
                    "target_has_king": bool(target_has_king),
                },
            )
            trace_payload["execution_trace"].update(
                {
                    "query_id": str(selected),
                    "target_answer": int(target_answer),
                    "answer": int(answer_gt.value),
                    "attacker_color": str(attacker_color),
                    "target_has_king": bool(target_has_king),
                    "attacker_color_name": color_name(attacker_color),
                }
            )
            trace_payload["projected_annotation"] = projected_bbox_payload(annotation_bboxes)
            trace_payload["witness_symbolic"] = {
                "type": "piece_set",
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
                query_id=selected,
            )

        raise RuntimeError(f"{self.task_id} failed to generate a chess target-square attacker scene") from last_error


__all__ = ["GamesChessTargetSquareAttackerCountTask"]
