"""Count moving objects that intersect the marked crossing route."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.crossing.shared.annotations import entity_bboxes_for_ids
from trace.tasks.games.crossing.shared.output import common_trace_params, common_trace_sections
from trace.tasks.games.crossing.shared.prompts import (
    build_crossing_prompt_artifacts,
    crossing_motion_rule_text,
    crossing_object_description,
    crossing_output_slots,
    json_examples_for_integer_answer,
)
from trace.tasks.games.crossing.shared.rendering import render_crossing_sample
from trace.tasks.games.crossing.shared.sampling import (
    resolve_crossing_scene_axes,
    resolve_target_answer,
    sample_crossing_scene,
)
from trace.tasks.games.crossing.shared.state import SCENE_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__crossing__moving_object_count"
QUERY_ID = "moving_object_count"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
MOVING_OBJECT_COUNT_SUPPORT: Tuple[int, ...] = (1, 2, 3, 4, 5)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesCrossingMovingObjectCountTask:
    """Count moving objects that collide with the marked route."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        target_answer, target_support, target_probabilities = resolve_target_answer(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="moving_object_count_support",
            fallback_support=MOVING_OBJECT_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.target_answer",
        )
        axes = resolve_crossing_scene_axes(
            int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            min_lane_count=min(8, int(target_answer) + 2),
            min_row_count=int(target_answer),
            namespace_suffix=str(selected_query),
        )

        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.crossing.{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_crossing_scene(
                    rng=rng,
                    axes=axes,
                    count_mode="route_intersections",
                    target_answer=int(target_answer),
                    gen_defaults=_GEN_DEFAULTS,
                )
            except ValueError as exc:
                last_error = exc
                continue

            rendered_context = render_crossing_sample(
                sample=sample,
                params=task_params,
                instance_seed=int(instance_seed),
            )
            annotation_bboxes = entity_bboxes_for_ids(
                rendered_context.rendered_scene,
                sample.annotation_entity_ids,
            )
            annotation_artifacts = bbox_set_annotation_artifacts(annotation_bboxes)
            json_example, json_example_answer_only = json_examples_for_integer_answer()
            dynamic_slots = {
                "object_description": crossing_object_description(include_route=True),
                "crossing_motion_rule_text": crossing_motion_rule_text(),
                **crossing_output_slots(
                    prompt_query_key=PROMPT_QUERY_KEY,
                    json_example=json_example,
                    json_example_answer_only=json_example_answer_only,
                ),
            }
            _prompt_defaults, prompt_artifacts = build_crossing_prompt_artifacts(
                domain=self.domain,
                prompt_query_key=PROMPT_QUERY_KEY,
                dynamic_slots=dynamic_slots,
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="integer", value=int(sample.answer))
            query_params = {
                "target_answer": int(target_answer),
                "target_answer_support": [int(value) for value in target_support],
                "target_answer_probabilities": dict(target_probabilities),
                "query_id_probabilities": dict(query_probabilities),
                "count_mode": "route_intersections",
            }
            query_spec = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=str(selected_query),
                params=common_trace_params(axes=axes, sample=sample, extra_params=query_params),
            )
            trace_payload = common_trace_sections(
                axes=axes,
                sample=sample,
                rendered_context=rendered_context,
                annotation_artifacts=annotation_artifacts,
                query_spec=query_spec,
                execution_extra={
                    "query_id": str(selected_query),
                    "target_answer": int(target_answer),
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
                query_id=str(selected_query),
            )

        raise RuntimeError(f"{TASK_ID} failed to generate a Crossing moving-object count scene") from last_error


__all__ = ["GamesCrossingMovingObjectCountTask"]
