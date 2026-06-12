"""Select the Bowling spare path that reaches all standing pins."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import point_pair_set_annotation_artifacts
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.defaults import SCENE_ID
from .shared.mechanics import sample_spare_path_scene
from .shared.output import build_bowling_common_trace_params, build_bowling_trace_payload
from .shared.prompts import build_bowling_prompt_artifacts
from .shared.sampling import (
    resolve_bowling_integer_axis,
    resolve_bowling_render_params,
    resolve_bowling_scene_axes,
)
from .shared.rendering import render_bowling_task_scene


TASK_ID = "task_games__bowling__spare_path_label"
QUERY_ID = "spare_path_label"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
PATH_OPTION_COUNT_SUPPORT = (4, 5, 6)
TARGET_PATH_INDEX_SUPPORT = tuple(range(max(PATH_OPTION_COUNT_SUPPORT)))
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesBowlingSparePathLabelTask:
    """Identify the numbered path that covers the remaining standing pins."""

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
        option_axis = resolve_bowling_integer_axis(
            int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="path_option_count_support",
            explicit_key="path_option_count",
            fallback_support=PATH_OPTION_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.path_option_count",
            balanced_flag_key="balanced_path_option_count_sampling",
        )
        target_axis = resolve_bowling_integer_axis(
            int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="target_path_index_support",
            explicit_key="target_path_index",
            fallback_support=TARGET_PATH_INDEX_SUPPORT,
            namespace=f"{TASK_ID}.target_path_index",
            balanced_flag_key="balanced_target_path_sampling",
        )
        path_option_count = max(int(option_axis.value), int(target_axis.value) + 1)

        sample = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.bowling.{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_spare_path_scene(
                    rng=rng,
                    scene_variant=str(axes.scene_variant),
                    style_variant=str(axes.style_variant),
                    path_option_count=int(path_option_count),
                    target_path_index=int(target_axis.value),
                )
            except ValueError:
                continue
            break
        if sample is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid spare-path Bowling scene after {max_attempts} attempts")
        if sample.target_path_id is None:
            raise RuntimeError("spare-path Bowling sample is missing target path id")

        render_params = resolve_bowling_render_params(task_params, instance_seed=int(instance_seed))
        rendered_context = render_bowling_task_scene(
            pins=sample.pins,
            path_options=sample.path_options,
            render_mode="path_options",
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
        annotation_artifacts = point_pair_set_annotation_artifacts(
            [
                rendered_context.rendered_scene.render_map["path_point_pairs_px"][str(sample.target_path_id)]
            ]
        )
        prompt_defaults, prompt_artifacts = build_bowling_prompt_artifacts(
            domain=self.domain,
            prompt_query_key=PROMPT_QUERY_KEY,
            instance_seed=int(instance_seed),
        )
        answer_gt = TypedValue(type="string", value=str(sample.target_path_label))
        query_params = {
            "path_option_count": int(path_option_count),
            "path_option_count_support": [int(value) for value in option_axis.support],
            "path_option_count_probabilities": dict(option_axis.probabilities),
            "target_path_index": int(target_axis.value),
            "target_path_index_support": [int(value) for value in target_axis.support],
            "target_path_index_probabilities": dict(target_axis.probabilities),
            "target_path_id": sample.target_path_id,
            "target_path_label": sample.target_path_label,
            "path_visible_fraction": sample.path_visible_fraction,
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
                "target_path_index": int(target_axis.value),
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


__all__ = ["GamesBowlingSparePathLabelTask"]
