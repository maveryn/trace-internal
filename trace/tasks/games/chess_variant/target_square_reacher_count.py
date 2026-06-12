"""Count pieces that can reach a marked target square under a visible rule."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.games.chess_variant.shared.annotations import annotation_from_evaluation
from trace.tasks.games.chess_variant.shared.defaults import SCENE_ID
from trace.tasks.games.chess_variant.shared.output import common_trace_sections
from trace.tasks.games.chess_variant.shared.prompts import build_chess_variant_prompt_artifacts, prompt_defaults
from trace.tasks.games.chess_variant.shared.rendering import (
    draw_marked_outline,
    render_chess_variant_scene,
    resolve_chess_variant_render_params,
    resolve_scene_background,
    rule_badge_text,
    text_style_metadata,
)
from trace.tasks.games.chess_variant.shared.sampling import (
    max_possible_target_reacher_answer,
    resolve_chess_variant_scene_axes,
    resolve_task_target_answer,
    sample_target_reacher_scene,
)
from trace.tasks.games.shared.piece_board_rules import BLACK, WHITE
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__chess_variant__target_square_reacher_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "white_piece_reaches_target_count",
    "black_piece_reaches_target_count",
)
REACHER_COUNT_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3, 4)

_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> tuple[str, dict[str, float], dict[str, Any]]:
    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SUPPORTED_QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _target_color_for_query(selected: str) -> str:
    if str(selected) == "black_piece_reaches_target_count":
        return BLACK
    return WHITE


@register_task
class GamesChessVariantTargetSquareReacherCountTask:
    """Count same-side pieces that can legally move to one target square."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected, query_probs, task_params = _select_query(int(instance_seed), params)
        target_color = _target_color_for_query(selected)
        axes = resolve_chess_variant_scene_axes(int(instance_seed), params=task_params)
        possible_max = max_possible_target_reacher_answer(
            rule_family=str(axes.rule_family),
            range_k=int(axes.range_k),
        )
        target_answer, answer_support, answer_probs = resolve_task_target_answer(
            instance_seed=int(instance_seed),
            params=task_params,
            support_key=f"{str(target_color)}_piece_reaches_target_count_support",
            fallback_support=REACHER_COUNT_SUPPORT,
            possible_max=int(possible_max),
            namespace=f"{TASK_ID}.target_answer.{selected}",
        )

        last_error: ValueError | None = None
        sample = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{attempt_index}")
            try:
                sample = sample_target_reacher_scene(
                    rng=rng,
                    axes=axes,
                    target_color=str(target_color),
                    target_answer=int(target_answer),
                )
            except ValueError as exc:
                last_error = exc
                continue
            break
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts") from last_error

        render_params = resolve_chess_variant_render_params(task_params, instance_seed=int(instance_seed))
        prompt_defaults_map = prompt_defaults()
        badge_text = rule_badge_text(str(axes.rule_family), int(axes.range_k), prompt_defaults_map)
        background, background_meta, panel_style, panel_style_meta = resolve_scene_background(
            params=task_params,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        rendered_image, render_map, scene_entities = render_chess_variant_scene(
            board=sample.board,
            axes=axes,
            background=background,
            params=render_params,
            badge_text=badge_text,
            panel_style=panel_style,
        )
        draw_marked_outline(
            rendered_image,
            render_map,
            sample.evaluation.marked_coord,
            render_params,
            outline_rgb=(35, 95, 220),
        )
        annotation_type, annotation_value, projected_annotation = annotation_from_evaluation(
            evaluation=sample.evaluation,
            render_map=render_map,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        _prompt_defaults, prompt_artifacts = build_chess_variant_prompt_artifacts(
            domain=self.domain,
            prompt_query_key=str(selected),
            scene_variant=str(axes.scene_variant),
            rule_family=str(axes.rule_family),
            range_k=int(axes.range_k),
            target_color=str(target_color),
            point_annotation=True,
            example_answer=3,
            instance_seed=int(instance_seed),
        )
        answer_gt = TypedValue(type="integer", value=int(sample.evaluation.answer))
        annotation_gt = TypedValue(type=str(annotation_type), value=[list(item) for item in annotation_value])
        trace_payload = common_trace_sections(
            sample=sample,
            image_size=(int(image.size[0]), int(image.size[1])),
            render_map=dict(render_map),
            scene_entities=tuple(scene_entities),
            panel_style_meta=dict(panel_style_meta),
            text_style_meta=text_style_metadata(str(render_params.font_family)),
            background_meta=dict(background_meta),
            post_noise_meta=dict(post_noise_meta),
            rule_family=str(axes.rule_family),
            range_k=int(axes.range_k),
        )
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected),
            params={
                "query_id": str(selected),
                "target_color": str(target_color),
                "rule_family": str(axes.rule_family),
                "range_k": int(axes.range_k),
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "query_id_probabilities": dict(query_probs),
                "target_answer": int(sample.evaluation.answer),
                "target_answer_support": [int(v) for v in answer_support],
                "target_answer_probabilities": dict(answer_probs),
                "rule_family_probabilities": dict(axes.rule_family_probabilities),
                "range_k_probabilities": dict(axes.range_k_probabilities),
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
            },
        )
        trace_payload["execution_trace"].update(
            {
                "query_id": str(selected),
                "target_answer_support": [int(v) for v in answer_support],
                "answer": int(answer_gt.value),
            }
        )
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected)
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


__all__ = ["GamesChessVariantTargetSquareReacherCountTask"]
