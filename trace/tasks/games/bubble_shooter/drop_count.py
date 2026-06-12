"""Count Bubble-shooter board bubbles that drop after the marked shot."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import hash64, spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import point_set_annotation_artifacts
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support

from .shared.defaults import SCENE_ID
from .shared.output import build_bubble_shooter_trace_payload, common_bubble_shooter_trace_params
from .shared.prompts import build_bubble_shooter_prompt_artifacts
from .shared.sampling import (
    bubble_entity_ids_for_coords,
    resolve_bubble_shooter_board_axes,
    resolve_bubble_shooter_render_params,
    resolve_bubble_shooter_scene_axes,
    sample_drop_state,
)
from .shared.rendering import render_bubble_shooter_task_scene


TASK_ID = "task_games__bubble_shooter__drop_count"
QUERY_ID = DEFAULT_QUERY_ID
PROMPT_QUERY_KEY = "drop_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
ROW_COUNT_SUPPORT = (7,)
COL_COUNT_SUPPORT = (8, 9, 10)
DROP_COUNT_SUPPORT = (0, 1, 2, 3, 4)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class GamesBubbleShooterDropCountTask:
    """Count bubbles that drop because they are no longer connected to the top."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        scene_axes = resolve_bubble_shooter_scene_axes(int(instance_seed), params=task_params)
        board_axis_seed = hash64(int(instance_seed), f"{TASK_ID}.board_axes")
        board_axes = resolve_bubble_shooter_board_axes(
            int(board_axis_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            row_count_support=ROW_COUNT_SUPPORT,
            col_count_support=COL_COUNT_SUPPORT,
        )
        target_value, target_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="drop_count_support",
            explicit_key="target_answer",
            fallback_support=DROP_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.target_answer",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
        target_support = resolve_integer_support(
            task_params,
            gen_defaults=_GEN_DEFAULTS,
            key="drop_count_support",
            fallback=DROP_COUNT_SUPPORT,
        )

        state = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.bubble_shooter.{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                state = sample_drop_state(
                    rng=rng,
                    scene_axes=scene_axes,
                    board_axes=board_axes,
                    target_drop_count=int(target_value),
                )
            except ValueError:
                continue
            break
        if state is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid Bubble-shooter drop-count scene after {max_attempts} attempts")
        if state.shooter_color_key != state.outcome.color_key:
            raise RuntimeError("Bubble-shooter drop-count state has mismatched shooter color")

        render_params = resolve_bubble_shooter_render_params(task_params, instance_seed=int(instance_seed))
        rendered_context = render_bubble_shooter_task_scene(
            board=state.board,
            landing_coord=state.landing_coord,
            shooter_color_key=state.shooter_color_key,
            option_specs=state.option_specs,
            scene_variant=str(scene_axes.scene_variant),
            style_variant=str(scene_axes.style_variant),
            render_params=render_params,
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        annotation_entity_ids = bubble_entity_ids_for_coords(state.outcome.dropped_coords)
        annotation_artifacts = point_set_annotation_artifacts(
            [
                rendered_context.rendered_scene.render_map["entity_centers_px"][str(entity_id)]
                for entity_id in annotation_entity_ids
            ]
        )
        _prompt_defaults, prompt_artifacts = build_bubble_shooter_prompt_artifacts(
            domain=self.domain,
            prompt_query_key=PROMPT_QUERY_KEY,
            instance_seed=int(instance_seed),
        )
        answer_gt = TypedValue(type="integer", value=int(len(state.outcome.dropped_coords)))
        query_params = {
            "target_answer": int(target_value),
            "target_answer_support": [int(value) for value in target_support],
            "target_answer_probabilities": dict(target_probabilities),
            "row_count_support": [int(value) for value in board_axes.rows.support],
            "row_count_probabilities": dict(board_axes.rows.probabilities),
            "col_count_support": [int(value) for value in board_axes.cols.support],
            "col_count_probabilities": dict(board_axes.cols.probabilities),
            "query_id_probabilities": dict(query_id_probabilities),
        }
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query),
            params=common_bubble_shooter_trace_params(scene_axes, state, extra_params=query_params),
        )
        trace_payload = build_bubble_shooter_trace_payload(
            annotation_artifacts=annotation_artifacts,
            annotation_entity_ids=annotation_entity_ids,
            axes=scene_axes,
            state=state,
            rendered_context=rendered_context,
            prompt_artifacts=prompt_artifacts,
            query_spec=query_spec,
            execution_extra={"answer": int(answer_gt.value)},
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


__all__ = ["GamesBubbleShooterDropCountTask"]
