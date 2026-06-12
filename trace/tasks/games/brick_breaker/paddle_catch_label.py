"""Identify the bottom catch lane reached by the visible ball trajectory."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import hash64, spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.defaults import SCENE_ID
from .shared.mechanics import sample_paddle_catch_scene
from .shared.output import build_brick_breaker_common_trace_params, build_brick_breaker_trace_payload
from .shared.prompts import build_brick_breaker_prompt_artifacts
from .shared.sampling import (
    resolve_brick_breaker_playfield_axes,
    resolve_brick_breaker_render_params,
    resolve_brick_breaker_scene_axes,
)
from .shared.rendering import render_brick_breaker_task_scene


TASK_ID = "task_games__brick_breaker__paddle_catch_label"
QUERY_ID = "paddle_catch_label"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
BRICK_ROW_COUNT_SUPPORT = (4, 5)
BRICK_COL_COUNT_SUPPORT = (5, 6)
CATCH_LANE_COUNT_SUPPORT = (5, 6, 7, 8)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesBrickBreakerPaddleCatchLabelTask:
    """Identify the catch lane reached by the visible ball trajectory."""

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
        axes = resolve_brick_breaker_scene_axes(int(instance_seed), params=task_params)
        playfield_axis_seed = hash64(int(instance_seed), f"{TASK_ID}.playfield_axes")
        playfield_axes = resolve_brick_breaker_playfield_axes(
            int(playfield_axis_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            brick_row_count_support=BRICK_ROW_COUNT_SUPPORT,
            brick_col_count_support=BRICK_COL_COUNT_SUPPORT,
            catch_lane_count_support=CATCH_LANE_COUNT_SUPPORT,
        )

        sample = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.brick_breaker.{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_paddle_catch_scene(
                    rng=rng,
                    scene_variant=str(axes.scene_variant),
                    brick_rows=int(playfield_axes.brick_rows.value),
                    brick_cols=int(playfield_axes.brick_cols.value),
                    lane_count=int(playfield_axes.lane_count.value),
                )
            except ValueError:
                continue
            break
        if sample is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid Brick-breaker paddle-catch scene after {max_attempts} attempts")
        if sample.target_lane_label is None:
            raise RuntimeError("paddle-catch Brick-breaker sample is missing target lane label")

        render_params = resolve_brick_breaker_render_params(task_params, instance_seed=int(instance_seed))
        rendered_context = render_brick_breaker_task_scene(
            brick_rows=int(sample.brick_rows),
            brick_cols=int(sample.brick_cols),
            lane_count=int(sample.lane_count),
            bricks=sample.bricks,
            render_mode="paddle_catch_path",
            target_brick_id=sample.target_brick_id,
            target_lane_index=sample.target_lane_index,
            ball_start_lane_index=sample.ball_start_lane_index,
            style_variant=str(axes.style_variant),
            render_params=render_params,
            params=task_params,
            instance_seed=int(instance_seed),
        )
        annotation_entity_ids = tuple(str(entity_id) for entity_id in sample.annotation_entity_ids)
        annotation_artifacts = bbox_set_annotation_artifacts(
            [
                rendered_context.rendered_scene.render_map["entity_bboxes_px"][str(entity_id)]
                for entity_id in annotation_entity_ids
            ]
        )
        prompt_defaults, prompt_artifacts = build_brick_breaker_prompt_artifacts(
            domain=self.domain,
            prompt_query_key=PROMPT_QUERY_KEY,
            instance_seed=int(instance_seed),
        )
        answer_gt = TypedValue(type="string", value=str(sample.target_lane_label))
        query_params = {
            "brick_rows": int(sample.brick_rows),
            "brick_cols": int(sample.brick_cols),
            "brick_count": int(len(sample.bricks)),
            "lane_count": int(sample.lane_count),
            "brick_row_count_support": [int(value) for value in playfield_axes.brick_rows.support],
            "brick_row_count_probabilities": dict(playfield_axes.brick_rows.probabilities),
            "brick_col_count_support": [int(value) for value in playfield_axes.brick_cols.support],
            "brick_col_count_probabilities": dict(playfield_axes.brick_cols.probabilities),
            "catch_lane_count_support": [int(value) for value in playfield_axes.lane_count.support],
            "catch_lane_count_probabilities": dict(playfield_axes.lane_count.probabilities),
            "query_id_probabilities": dict(query_id_probabilities),
            "target_lane_index": sample.target_lane_index,
            "target_lane_label": sample.target_lane_label,
        }
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params=build_brick_breaker_common_trace_params(axes=axes, extra_params=query_params),
        )
        trace_payload = build_brick_breaker_trace_payload(
            annotation_artifacts=annotation_artifacts,
            annotation_entity_ids=annotation_entity_ids,
            axes=axes,
            sample=sample,
            rendered_context=rendered_context,
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            query_spec=query_spec,
            answer_value=str(answer_gt.value),
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
            query_id=str(query_id),
        )


__all__ = ["GamesBrickBreakerPaddleCatchLabelTask"]
