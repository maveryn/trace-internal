"""Scene-private lifecycle plumbing for Go public tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import go_point_set_annotation
from .shared.output import build_go_common_trace_params, build_go_trace_payload
from .shared.prompts import build_go_prompt_artifacts
from .shared.rendering import render_go_board_scene
from .shared.rules import (
    Board,
    Coord,
    GoStoneSpec,
    build_go_board_state,
    build_go_stone_group_count_state,
    color_name,
    coord_to_point_id,
)
from .shared.sampling import (
    resolve_go_board_size_axis,
    resolve_go_render_params,
    resolve_go_scene_axes,
)
from .shared.state import GO_NAMESPACE, SCENE_ID, GoIntegerAxis, GoPlayerColorAxis, GoSceneAxes


POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)
AttemptBuilder = Callable[[Any, GoSceneAxes], "GoAttemptResult"]
ObjectivePreparer = Callable[
    [int, Mapping[str, Any], str, Mapping[str, float], GoSceneAxes, GoIntegerAxis],
    "GoObjectivePlan",
]


@dataclass(frozen=True)
class GoAttemptResult:
    """Task-owned board result plus selected point witnesses."""

    board: Board
    stone_specs: Sequence[GoStoneSpec]
    marked_group_coords: Sequence[Coord]
    liberty_coords: Sequence[Coord]
    annotation_point_ids: Sequence[str]
    execution_extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoObjectivePlan:
    """Prepared task-owned objective hooks for one Go instance."""

    prompt_query_key: str
    answer_gt: TypedValue
    target_axis: GoIntegerAxis
    player_color: str
    player_color_axis: GoPlayerColorAxis | None
    stone_group_query: bool
    query_params: Mapping[str, Any]
    attempt_namespace: str
    construct_attempt: AttemptBuilder


def make_go_marked_group_objective(
    *,
    prompt_query_key: str,
    rule_mode: str,
    target_axis: GoIntegerAxis,
    player_color_axis: GoPlayerColorAxis,
    board_size_axis: GoIntegerAxis,
    scene_axes: GoSceneAxes,
    annotation_coord_attr: str,
    attempt_namespace: str,
) -> GoObjectivePlan:
    """Prepare a marked-group count objective from task-owned semantic arguments."""

    def construct_attempt(rng, _axes: GoSceneAxes) -> GoAttemptResult:
        board_state = build_go_board_state(
            rng=rng,
            count_mode=str(rule_mode),
            player_color=str(player_color_axis.player_color),
            scene_variant=str(scene_axes.scene_variant),
            target_answer=int(target_axis.value),
            board_size=int(board_size_axis.value),
        )
        annotation_coords = tuple(getattr(board_state, str(annotation_coord_attr)))
        return GoAttemptResult(
            board=board_state.board,
            stone_specs=board_state.stone_specs,
            marked_group_coords=board_state.marked_group_coords,
            liberty_coords=board_state.liberty_coords,
            annotation_point_ids=tuple(coord_to_point_id(coord) for coord in annotation_coords),
            execution_extra={
                "marked_group_color": str(color_name(board_state.marked_group_color).lower()),
                "marked_group_point_ids": [coord_to_point_id(coord) for coord in board_state.marked_group_coords],
                "adjacent_enemy_coords": [[int(row), int(col)] for row, col in board_state.adjacent_enemy_coords],
                "shared_liberty_coords": [[int(row), int(col)] for row, col in board_state.shared_liberty_coords],
            },
        )

    return GoObjectivePlan(
        prompt_query_key=str(prompt_query_key),
        answer_gt=TypedValue(type="integer", value=int(target_axis.value)),
        target_axis=target_axis,
        player_color=str(player_color_axis.player_color),
        player_color_axis=player_color_axis,
        stone_group_query=False,
        query_params={
            "target_answer": int(target_axis.value),
            "target_answer_support": [int(value) for value in target_axis.support],
            "target_answer_probabilities": dict(target_axis.probabilities),
        },
        attempt_namespace=str(attempt_namespace),
        construct_attempt=construct_attempt,
    )


def make_go_stone_group_objective(
    *,
    prompt_query_key: str,
    rule_mode: str,
    target_axis: GoIntegerAxis,
    player_color_axis: GoPlayerColorAxis,
    board_size_axis: GoIntegerAxis,
    scene_axes: GoSceneAxes,
    attempt_namespace: str,
) -> GoObjectivePlan:
    """Prepare a whole-board same-color group count objective."""

    def construct_attempt(rng, _axes: GoSceneAxes) -> GoAttemptResult:
        board_state = build_go_stone_group_count_state(
            rng=rng,
            count_mode=str(rule_mode),
            scene_variant=str(scene_axes.scene_variant),
            target_answer=int(target_axis.value),
            board_size=int(board_size_axis.value),
        )
        annotation_ids = tuple(coord_to_point_id(coord) for coord in board_state.representative_coords)
        return GoAttemptResult(
            board=board_state.board,
            stone_specs=board_state.stone_specs,
            marked_group_coords=(),
            liberty_coords=(),
            annotation_point_ids=annotation_ids,
            execution_extra={
                "target_group_color": str(color_name(board_state.target_color).lower()),
                "target_group_coords": [
                    [[int(row), int(col)] for row, col in group]
                    for group in board_state.target_group_coords
                ],
                "representative_coords": [[int(row), int(col)] for row, col in board_state.representative_coords],
                "representative_point_ids": [str(value) for value in annotation_ids],
            },
        )

    return GoObjectivePlan(
        prompt_query_key=str(prompt_query_key),
        answer_gt=TypedValue(type="integer", value=int(target_axis.value)),
        target_axis=target_axis,
        player_color=str(player_color_axis.player_color),
        player_color_axis=player_color_axis,
        stone_group_query=True,
        query_params={
            "player_color": str(player_color_axis.player_color),
            "target_answer": int(target_axis.value),
            "target_answer_support": [int(value) for value in target_axis.support],
            "target_answer_probabilities": dict(target_axis.probabilities),
        },
        attempt_namespace=str(attempt_namespace),
        construct_attempt=construct_attempt,
    )


def _allowed_panel_treatments(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[str, ...] | None:
    raw = params.get("panel_scene_treatments", group_default(render_defaults, "panel_scene_treatments", None))
    if isinstance(raw, str):
        return (str(raw),)
    if raw is None:
        return None
    return tuple(str(item) for item in raw)


def run_go_lifecycle(
    *,
    task_id: str,
    domain: str,
    supported_query_ids: Sequence[str],
    default_query_id: str,
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    prepare_objective: ObjectivePreparer,
) -> TaskOutput:
    """Run neutral Go scene plumbing around task-owned objective hooks."""

    selected_query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(query_id) for query_id in supported_query_ids),
        default_query_id=str(default_query_id),
        task_id=str(task_id),
        namespace=f"{task_id}.query",
    )
    scene_axes = resolve_go_scene_axes(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=gen_defaults,
    )
    board_size_axis = resolve_go_board_size_axis(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=gen_defaults,
    )
    objective = prepare_objective(
        int(instance_seed),
        task_params,
        str(selected_query_id),
        dict(query_probabilities),
        scene_axes,
        board_size_axis,
    )
    render_params = resolve_go_render_params(
        task_params,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
    )

    for attempt_index in range(max(1, int(max_attempts))):
        rng = spawn_rng(int(instance_seed), f"{objective.attempt_namespace}.attempt.{int(attempt_index)}")
        try:
            attempt = objective.construct_attempt(rng, scene_axes)
        except (RuntimeError, ValueError):
            continue

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{GO_NAMESPACE}.panel_scene_style",
            treatments=_allowed_panel_treatments(task_params, render_defaults),
            treatment_weights=task_params.get(
                "panel_scene_treatment_weights",
                group_default(render_defaults, "panel_scene_treatment_weights", None),
            ),
            palette_weights=task_params.get(
                "panel_scene_palette_weights",
                group_default(render_defaults, "panel_scene_palette_weights", None),
            ),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_go_board_scene(
            board=attempt.board,
            background=background,
            scene_variant=str(scene_axes.scene_variant),
            style_variant=str(scene_axes.style_variant),
            marked_group_coords=tuple(attempt.marked_group_coords),
            liberty_coords=tuple(attempt.liberty_coords),
            params=render_params,
            panel_style=panel_style,
        )
        annotation_artifacts = go_point_set_annotation(
            rendered_scene,
            tuple(str(point_id) for point_id in attempt.annotation_point_ids),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults, prompt_artifacts = build_go_prompt_artifacts(
            domain=str(domain),
            scene_variant=str(scene_axes.scene_variant),
            prompt_query_key=str(objective.prompt_query_key),
            player_color=str(objective.player_color),
            stone_group_query=bool(objective.stone_group_query),
            instance_seed=int(instance_seed),
        )
        common_query_params = build_go_common_trace_params(
            scene_axes=scene_axes,
            player_color_axis=objective.player_color_axis,
            player_color=str(objective.player_color),
            board_size_axis=board_size_axis,
            target_axis=objective.target_axis,
            query_id_probabilities=query_probabilities,
            extra_params=objective.query_params,
        )
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params=common_query_params,
        )
        trace_payload = build_go_trace_payload(
            annotation_artifacts=annotation_artifacts,
            annotation_entity_ids=tuple(str(point_id) for point_id in attempt.annotation_point_ids),
            scene_axes=scene_axes,
            player_color=str(objective.player_color),
            board_size_axis=board_size_axis,
            target_axis=objective.target_axis,
            board=attempt.board,
            stone_specs=attempt.stone_specs,
            marked_group_coords=tuple(attempt.marked_group_coords),
            liberty_coords=tuple(attempt.liberty_coords),
            rendered_scene=rendered_scene,
            prompt_defaults=prompt_defaults,
            query_spec=query_spec,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            image_size=(int(image.size[0]), int(image.size[1])),
            execution_extra={
                "query_id": str(selected_query_id),
                **dict(objective.query_params),
                **dict(attempt.execution_extra),
            },
        )
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        trace_payload["render_spec"]["panel_scene_style"] = dict(panel_style_meta)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=objective.answer_gt,
            annotation_gt=TypedValue(type=str(annotation_artifacts.annotation_type), value=annotation_artifacts.value),
            image=image,
            image_id="img0",
            trace_payload=dict(trace_payload),
            task_versions=default_task_versions(),
            query_id=str(selected_query_id),
            scene_id=SCENE_ID,
        )

    raise RuntimeError(f"{task_id} failed to generate a valid Go board after {max_attempts} attempts")


__all__ = [
    "GoAttemptResult",
    "GoObjectivePlan",
    "make_go_marked_group_objective",
    "make_go_stone_group_objective",
    "run_go_lifecycle",
]
