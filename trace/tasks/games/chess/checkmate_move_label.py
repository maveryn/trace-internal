"""Select the labeled chess move that gives immediate checkmate."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.chess.shared.annotations import keyed_move_bboxes, projected_keyed_bbox_payload
from trace.tasks.games.chess.shared.output import common_checkmate_trace_sections
from trace.tasks.games.chess.shared.prompts import build_chess_prompt_artifacts
from trace.tasks.games.chess.shared.rendering import render_chess_task_scene
from trace.tasks.games.chess.shared.sampling import (
    resolve_checkmate_answer_label,
    resolve_chess_scene_axes,
    resolve_integer_axis,
    sample_checkmate_scene,
)
from trace.tasks.games.chess.shared.state import CHESS_OPTION_LABELS, SCENE_ID
from trace.tasks.games.shared.piece_board_rules import color_name, coord_to_cell_id
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__chess__checkmate_move_label"
QUERY_ID = "checkmate_move_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
OPTION_COUNT_SUPPORT: Tuple[int, ...] = (4, 6)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)

@register_task
class GamesChessCheckmateMoveLabelTask:
    """Choose the visible move option that checkmates immediately."""

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
        option_count, option_count_support, option_count_probs = resolve_integer_axis(
            instance_seed=int(instance_seed),
            params=task_params,
            support_key="checkmate_option_count_support",
            explicit_key="option_count",
            fallback_support=OPTION_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.option_count",
            balance_flag_key="balanced_checkmate_option_count_sampling",
            gen_defaults=_GEN_DEFAULTS,
        )
        option_label_support = tuple(CHESS_OPTION_LABELS[: int(option_count)])

        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{attempt_index}")
            answer_label, answer_label_probs = resolve_checkmate_answer_label(
                rng,
                params=task_params,
                labels=option_label_support,
            )
            try:
                sample = sample_checkmate_scene(
                    instance_seed=int(instance_seed),
                    rng=rng,
                    params=task_params,
                    axes=axes,
                    option_count=int(option_count),
                    option_label_support=option_label_support,
                    answer_label=str(answer_label),
                )
            except ValueError as exc:
                last_error = exc
                continue
            rendered_context = render_chess_task_scene(
                board=sample.board,
                scene_variant=sample.scene_variant,
                style_variant=sample.style_variant,
                badge_text=f"{color_name(sample.player_color)} to move",
                marked_coord=None,
                params=task_params,
                instance_seed=int(instance_seed),
                show_coordinates=True,
                move_options=tuple({"label": option.label, "text": option.text} for option in sample.options),
            )
            annotation_map = keyed_move_bboxes(
                rendered_context.rendered_scene,
                source=sample.correct_option.source,
                destination=sample.correct_option.destination,
                king=sample.defender_king_coord,
            )
            _prompt_defaults, prompt_artifacts = build_chess_prompt_artifacts(
                domain=self.domain,
                prompt_query_key=query_id,
                dynamic_slots={
                    "player_color_name": color_name(sample.player_color),
                    "defender_color_name": color_name(sample.defender_color),
                },
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="option_letter", value=str(sample.correct_option.label))
            annotation_gt = TypedValue(type="keyed_bbox_map", value=annotation_map)
            trace_payload = common_checkmate_trace_sections(sample=sample, rendered_context=rendered_context)
            trace_payload["query_spec"] = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=query_id,
                params={
                    "option_count": int(option_count),
                    "option_count_support": [int(value) for value in option_count_support],
                    "option_count_probabilities": dict(option_count_probs),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "answer_support": [str(label) for label in option_label_support],
                    "answer_label_probabilities": dict(answer_label_probs),
                    "answer_option_label": str(sample.correct_option.label),
                    "player_color": str(sample.player_color),
                },
            )
            trace_payload["execution_trace"].update(
                {
                    "query_id": str(query_id),
                    "answer": str(answer_gt.value),
                    "annotation_kind": "keyed_bbox_map",
                }
            )
            trace_payload["projected_annotation"] = projected_keyed_bbox_payload(annotation_map)
            trace_payload["witness_symbolic"] = {
                "type": "cell_map",
                "ids": {
                    "from": coord_to_cell_id(sample.correct_option.source),
                    "to": coord_to_cell_id(sample.correct_option.destination),
                    "king": coord_to_cell_id(sample.defender_king_coord),
                },
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

        raise RuntimeError(f"{self.task_id} failed to generate a chess checkmate-move scene") from last_error


__all__ = ["GamesChessCheckmateMoveLabelTask"]
