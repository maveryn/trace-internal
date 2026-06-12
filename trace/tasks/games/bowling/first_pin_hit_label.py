"""Identify the first Bowling pin reached by the shown path."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.defaults import SCENE_ID
from .shared.mechanics import PIN_LABELS, sample_first_pin_hit_scene
from .shared.output import build_bowling_common_trace_params, build_bowling_trace_payload
from .shared.prompts import build_bowling_prompt_artifacts
from .shared.sampling import (
    resolve_bowling_integer_axis,
    resolve_bowling_render_params,
    resolve_bowling_scene_axes,
)
from .shared.rendering import render_bowling_task_scene


TASK_ID = "task_games__bowling__first_pin_hit_label"
QUERY_ID = "first_pin_hit_label"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
VISIBLE_PIN_COUNT_SUPPORT = (4, 5, 6, 7, 8, 9)
TARGET_PIN_INDEX_SUPPORT = tuple(range(len(PIN_LABELS)))
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesBowlingFirstPinHitLabelTask:
    """Identify the labeled pin hit first by the visible ball path."""

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
        axes = resolve_bowling_scene_axes(int(instance_seed), params=task_params)
        visible_axis = resolve_bowling_integer_axis(
            int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="visible_pin_count_support",
            explicit_key="visible_pin_count",
            fallback_support=VISIBLE_PIN_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.visible_pin_count",
            balanced_flag_key="balanced_visible_pin_count_sampling",
        )
        target_axis = resolve_bowling_integer_axis(
            int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="target_pin_index_support",
            explicit_key="target_pin_index",
            fallback_support=TARGET_PIN_INDEX_SUPPORT,
            namespace=f"{TASK_ID}.target_pin_index",
            balanced_flag_key="balanced_target_pin_sampling",
        )

        sample = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.bowling.{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_first_pin_hit_scene(
                    rng=rng,
                    scene_variant=str(axes.scene_variant),
                    style_variant=str(axes.style_variant),
                    target_pin_label_index=int(target_axis.value),
                    visible_pin_count=int(visible_axis.value),
                )
            except ValueError:
                continue
            break
        if sample is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid first-pin Bowling scene after {max_attempts} attempts")

        render_params = resolve_bowling_render_params(task_params, instance_seed=int(instance_seed))
        rendered_context = render_bowling_task_scene(
            pins=sample.pins,
            path_options=sample.path_options,
            render_mode="first_pin_path",
            ball_x_norm=float(sample.ball_x_norm),
            target_pin_id=sample.target_pin_id,
            target_path_id=sample.target_path_id,
            path_visible_fraction=sample.path_visible_fraction,
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
        prompt_defaults, prompt_artifacts = build_bowling_prompt_artifacts(
            domain=self.domain,
            prompt_query_key=PROMPT_QUERY_KEY,
            instance_seed=int(instance_seed),
        )
        answer_gt = TypedValue(type="string", value=str(sample.target_pin_label))
        query_params = {
            "visible_pin_count": int(visible_axis.value),
            "visible_pin_count_support": [int(value) for value in visible_axis.support],
            "visible_pin_count_probabilities": dict(visible_axis.probabilities),
            "target_pin_index": int(target_axis.value),
            "target_pin_label_index": int(target_axis.value),
            "target_pin_index_support": [int(value) for value in target_axis.support],
            "target_pin_index_probabilities": dict(target_axis.probabilities),
            "target_pin_id": sample.target_pin_id,
            "target_pin_label": sample.target_pin_label,
            "path_clearance_px": sample.path_clearance_px,
            "query_id_probabilities": dict(query_id_probabilities),
        }
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params=build_bowling_common_trace_params(axes=axes, extra_params=query_params),
        )
        trace_payload = build_bowling_trace_payload(
            annotation_artifacts=annotation_artifacts,
            annotation_entity_ids=annotation_entity_ids,
            axes=axes,
            sample=sample,
            rendered_context=rendered_context,
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            query_spec=query_spec,
            answer_value=str(answer_gt.value),
            execution_extra={
                "target_pin_index": int(target_axis.value),
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
            query_id=str(query_id),
        )


__all__ = ["GamesBowlingFirstPinHitLabelTask"]
