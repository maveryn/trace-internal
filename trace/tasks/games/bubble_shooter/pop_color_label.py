"""Choose the labeled Bubble-shooter color option that would make bubbles pop."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import hash64, spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import point_set_annotation_artifacts
from trace.tasks.shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec
from trace.tasks.shared.support_sampling import resolve_integer_choice

from .shared.state import BUBBLE_OPTION_LABELS
from .shared.defaults import SCENE_ID
from .shared.output import build_bubble_shooter_trace_payload, common_bubble_shooter_trace_params
from .shared.prompts import build_bubble_shooter_prompt_artifacts
from .shared.sampling import (
    bubble_entity_ids_for_coords,
    resolve_bubble_shooter_board_axes,
    resolve_bubble_shooter_integer_axis,
    resolve_bubble_shooter_render_params,
    resolve_bubble_shooter_scene_axes,
    sample_pop_color_state,
)
from .shared.rendering import render_bubble_shooter_task_scene


TASK_ID = "task_games__bubble_shooter__pop_color_label"
QUERY_ID = DEFAULT_QUERY_ID
PROMPT_QUERY_KEY = "pop_color_label"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
ROW_COUNT_SUPPORT = (7, 8, 9)
COL_COUNT_SUPPORT = (8, 9, 10)
OPTION_COUNT_SUPPORT = (4, 5, 6)
LABEL_SUPPORT = BUBBLE_OPTION_LABELS
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _string_support(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[str],
) -> Tuple[str, ...]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    if raw is None:
        raw = tuple(fallback)
    if isinstance(raw, str):
        values = (raw,)
    else:
        values = tuple(str(value) for value in raw)
    values = tuple(value for value in values if value)
    if not values:
        raise ValueError(f"{key} must contain at least one label")
    return values


def _resolve_label_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
) -> tuple[str, Dict[str, float], Tuple[str, ...]]:
    support = _string_support(params, key=str(support_key), fallback=fallback_support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"{explicit_key}={value!r} is not in {support_key}")
        return value, {str(item): (1.0 if str(item) == value else 0.0) for item in support}, support

    probabilities = {str(item): 1.0 / float(len(support)) for item in support}
    sampling_index = params.get("_sample_cursor")
    balanced = bool(params.get(str(balanced_flag_key), group_default(_GEN_DEFAULTS, str(balanced_flag_key), True)))
    if balanced and sampling_index is not None:
        return str(support[abs(int(sampling_index)) % len(support)]), probabilities, support
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(rng.choice(tuple(support))), probabilities, support


@register_task
class GamesBubbleShooterPopColorLabelTask:
    """Choose the color option that would pop bubbles at the marked landing target."""

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
        option_count_axis = resolve_bubble_shooter_integer_axis(
            int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="option_count_support",
            explicit_key="option_count",
            fallback_support=OPTION_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.option_count",
            balanced_flag_key="balanced_option_count_sampling",
        )
        target_label, target_label_probabilities, target_label_support = _resolve_label_choice(
            instance_seed=int(instance_seed),
            params=task_params,
            support_key="pop_color_label_support",
            explicit_key="target_label",
            fallback_support=LABEL_SUPPORT,
            namespace=f"{TASK_ID}.target_label",
            balanced_flag_key="balanced_target_label_sampling",
        )
        option_count = max(int(option_count_axis.value), BUBBLE_OPTION_LABELS.index(str(target_label)) + 1)

        state = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"games.bubble_shooter.{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                state = sample_pop_color_state(
                    rng=rng,
                    scene_axes=scene_axes,
                    board_axes=board_axes,
                    target_option_label=str(target_label),
                    option_count=int(option_count),
                )
            except ValueError:
                continue
            break
        if state is None:
            raise RuntimeError(f"{TASK_ID} failed to generate a valid Bubble-shooter color-option scene after {max_attempts} attempts")

        answer_options = [option for option in state.option_specs if option.is_answer]
        if len(answer_options) != 1 or str(answer_options[0].label) != str(target_label):
            raise RuntimeError("Bubble-shooter color-option state has ambiguous answer")

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
        annotation_entity_ids = bubble_entity_ids_for_coords(state.outcome.popped_coords)
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
        answer_gt = TypedValue(type="string", value=str(target_label))
        query_params = {
            "target_label": str(target_label),
            "target_label_support": [str(value) for value in target_label_support],
            "target_label_probabilities": dict(target_label_probabilities),
            "option_count": int(option_count),
            "option_count_support": [int(value) for value in option_count_axis.support],
            "option_count_probabilities": dict(option_count_axis.probabilities),
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
            execution_extra={
                "answer": str(answer_gt.value),
                "target_label": str(target_label),
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


__all__ = ["GamesBubbleShooterPopColorLabelTask"]
