"""Count destinations or captures for one marked circular-chess piece."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.games.circular_chess.shared.annotations import annotation_from_evaluation
from trace.tasks.games.circular_chess.shared.defaults import SCENE_ID
from trace.tasks.games.circular_chess.shared.mechanics import (
    capture_destinations,
    circular_coord_to_cell_id,
    circular_piece_to_entity_id,
    empty_board,
    freeze_board,
    legal_destinations,
    max_possible_marked_destination_answer,
    target_reachers,
)
from trace.tasks.games.circular_chess.shared.output import common_trace_sections
from trace.tasks.games.circular_chess.shared.prompts import build_circular_chess_prompt_artifacts
from trace.tasks.games.circular_chess.shared.rendering import (
    render_circular_chess_scene,
    resolve_circular_chess_render_params,
    resolve_scene_background,
    text_style_metadata,
)
from trace.tasks.games.circular_chess.shared.sampling import (
    resolve_circular_chess_scene_axes,
    resolve_marked_piece_axes,
    resolve_task_target_answer,
    sample_marked_destination_scene,
)
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__circular_chess__marked_piece_destination_count"
MARKED_MOVE_QUERY_ID = "marked_piece_move_count"
MARKED_CAPTURE_QUERY_ID = "marked_piece_capture_count"
WHITE_REACHER_QUERY_ID = "white_piece_reaches_target_count"
BLACK_REACHER_QUERY_ID = "black_piece_reaches_target_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (MARKED_MOVE_QUERY_ID, MARKED_CAPTURE_QUERY_ID)
MOVE_COUNT_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8)
CAPTURE_COUNT_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> tuple[str, dict[str, float], dict[str, Any]]:
    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=MARKED_MOVE_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _query_semantics(selected: str) -> tuple[str, str, Tuple[int, ...]]:
    if str(selected) == MARKED_CAPTURE_QUERY_ID:
        return "capture", "marked_piece_capture_count_support", CAPTURE_COUNT_SUPPORT
    return "move", "marked_piece_move_count_support", MOVE_COUNT_SUPPORT


@register_task
class GamesCircularChessMarkedPieceDestinationCountTask:
    """Count legal destinations or capture destinations for a marked piece."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected, query_probs, task_params = _select_query(int(instance_seed), params)
        destination_mode, support_key, fallback_support = _query_semantics(selected)
        scene_axes = resolve_circular_chess_scene_axes(int(instance_seed), params=task_params)
        marked_axes = resolve_marked_piece_axes(int(instance_seed), params=task_params)
        possible_max = max_possible_marked_destination_answer(
            destination_mode=str(destination_mode),
            piece_kind=str(marked_axes.piece_kind),
        )
        target_answer, answer_support, answer_probs = resolve_task_target_answer(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=str(support_key),
            fallback_support=fallback_support,
            possible_max=int(possible_max),
            namespace=f"{TASK_ID}.target_answer.{selected}",
        )

        last_error: ValueError | None = None
        sample = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{attempt_index}")
            try:
                sample = sample_marked_destination_scene(
                    rng=rng,
                    scene_axes=scene_axes,
                    marked_axes=marked_axes,
                    destination_mode=str(destination_mode),
                    target_answer=int(target_answer),
                )
            except ValueError as exc:
                last_error = exc
                continue
            break
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts") from last_error

        render_params = resolve_circular_chess_render_params(task_params, instance_seed=int(instance_seed))
        background, background_meta, panel_style, panel_style_meta = resolve_scene_background(
            params=task_params,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        rendered = render_circular_chess_scene(
            board=sample.board,
            background=background,
            style_variant=str(scene_axes.style_variant),
            params=render_params,
            marked_coord=sample.evaluation.marked_coord,
            target_coord=None,
            panel_style=panel_style,
        )
        annotation_type, annotation_value, projected_annotation = annotation_from_evaluation(
            evaluation=sample.evaluation,
            render_map=rendered.render_map,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        _prompt_defaults, prompt_artifacts = build_circular_chess_prompt_artifacts(
            domain=self.domain,
            prompt_query_key=str(selected),
            scene_variant=str(scene_axes.scene_variant),
            target_color="",
            marked_piece_present=True,
            example_answer=3 if str(destination_mode) == "move" else 2,
            instance_seed=int(instance_seed),
        )
        answer_gt = TypedValue(type="integer", value=int(sample.evaluation.answer))
        annotation_gt = TypedValue(type=str(annotation_type), value=[list(item) for item in annotation_value])
        trace_payload = common_trace_sections(
            sample=sample,
            image_size=(int(image.size[0]), int(image.size[1])),
            render_map=dict(rendered.render_map),
            scene_entities=tuple(rendered.scene_entities),
            panel_style_meta=dict(panel_style_meta),
            text_style_meta=text_style_metadata(str(render_params.font_family)),
            background_meta=dict(background_meta),
            post_noise_meta=dict(post_noise_meta),
        )
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected),
            params={
                "query_id": str(selected),
                "destination_mode": str(destination_mode),
                "scene_variant": str(scene_axes.scene_variant),
                "style_variant": str(scene_axes.style_variant),
                "marked_piece_kind": str(marked_axes.piece_kind),
                "marked_piece_color": str(marked_axes.piece_color),
                "query_id_probabilities": dict(query_probs),
                "target_answer": int(sample.evaluation.answer),
                "target_answer_support": [int(v) for v in answer_support],
                "target_answer_probabilities": dict(answer_probs),
                "scene_variant_probabilities": dict(scene_axes.scene_variant_probabilities),
                "style_variant_probabilities": dict(scene_axes.style_variant_probabilities),
                "piece_kind_probabilities": dict(marked_axes.piece_kind_probabilities),
                "marked_piece_color_probabilities": dict(marked_axes.piece_color_probabilities),
            },
        )
        trace_payload["execution_trace"].update(
            {
                "query_id": str(selected),
                "destination_mode": str(destination_mode),
                "marked_piece_kind": str(marked_axes.piece_kind),
                "marked_piece_color": str(marked_axes.piece_color),
                "target_answer_support": [int(v) for v in answer_support],
                "answer": int(answer_gt.value),
            }
        )
        trace_payload["scene_ir"]["relations"].update(
            {
                "query_id": str(selected),
                "destination_mode": str(destination_mode),
                "marked_piece_kind": str(marked_axes.piece_kind),
            }
        )
        trace_payload["projected_annotation"] = dict(projected_annotation)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected),
        )


__all__ = [
    "BLACK_REACHER_QUERY_ID",
    "GamesCircularChessMarkedPieceDestinationCountTask",
    "MARKED_CAPTURE_QUERY_ID",
    "MARKED_MOVE_QUERY_ID",
    "WHITE_REACHER_QUERY_ID",
    "capture_destinations",
    "circular_coord_to_cell_id",
    "circular_piece_to_entity_id",
    "empty_board",
    "freeze_board",
    "legal_destinations",
    "target_reachers",
]
