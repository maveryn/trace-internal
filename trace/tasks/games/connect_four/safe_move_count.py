"""Count Connect Four legal drops that leave no immediate reply win."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.connect_four.shared.annotations import cell_bboxes_for_coords
from trace.tasks.games.connect_four.shared.output import common_trace_params, common_trace_sections
from trace.tasks.games.connect_four.shared.prompts import (
    build_connect_four_prompt_artifacts,
    connect_four_object_description,
    connect_four_output_slots,
    connect_four_rule_slots,
    json_examples_for_integer_answer,
)
from trace.tasks.games.connect_four.shared.rendering import render_connect_four_sample
from trace.tasks.games.connect_four.shared.sampling import (
    resolve_connect_four_scene_axes,
    resolve_target_answer,
    sample_count_scene,
)
from trace.tasks.games.connect_four.shared.state import SCENE_ID
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TASK_ID = "task_games__connect_four__safe_move_count"
QUERY_ID = "safe_move_count"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
SAFE_MOVE_COUNT_SUPPORT: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesConnectFourSafeMoveCountTask:
    """Count legal Connect Four drop columns that are safe."""

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
            support_key="safe_move_count_support",
            fallback_support=SAFE_MOVE_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.target_answer",
        )
        axes = resolve_connect_four_scene_axes(
            int(instance_seed),
            params=task_params,
            safe_board_defaults=True,
            target_answer=int(target_answer),
            gen_defaults=_GEN_DEFAULTS,
            namespace_suffix=str(selected_query),
        )

        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.connect_four.{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_count_scene(
                    rng=rng,
                    axes=axes,
                    params=task_params,
                    count_mode="safe",
                    target_answer=int(target_answer),
                    gen_defaults=_GEN_DEFAULTS,
                )
            except ValueError as exc:
                last_error = exc
                continue

            rendered_context = render_connect_four_sample(
                sample=sample,
                params=task_params,
                instance_seed=int(instance_seed),
            )
            annotation_bboxes = cell_bboxes_for_coords(
                rendered_context.rendered_scene,
                sample.evaluation.annotation_coords,
            )
            annotation_artifacts = bbox_set_annotation_artifacts(annotation_bboxes)
            json_example, json_example_answer_only = json_examples_for_integer_answer()
            dynamic_slots = {
                "object_description": connect_four_object_description(str(sample.scene_variant)),
                **connect_four_rule_slots(current_player=int(sample.current_player), include_safety_rule=True),
                **connect_four_output_slots(
                    prompt_query_key=PROMPT_QUERY_KEY,
                    json_example=json_example,
                    json_example_answer_only=json_example_answer_only,
                ),
            }
            _prompt_defaults, prompt_artifacts = build_connect_four_prompt_artifacts(
                domain=self.domain,
                prompt_query_key=PROMPT_QUERY_KEY,
                dynamic_slots=dynamic_slots,
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="integer", value=int(sample.evaluation.answer))
            query_params = {
                "target_answer": int(target_answer),
                "target_answer_support": [int(value) for value in target_support],
                "target_answer_probabilities": dict(target_probabilities),
                "query_id_probabilities": dict(query_probabilities),
                "count_mode": "safe",
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

        raise RuntimeError(f"{TASK_ID} failed to generate a Connect Four safe-move count scene") from last_error


__all__ = ["GamesConnectFourSafeMoveCountTask"]
