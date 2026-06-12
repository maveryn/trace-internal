"""Identity-free render and trace assembly for Go tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.shared.annotation_artifacts import point_set_annotation_artifacts
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .mechanics import Board, Coord, GoStoneSpec
from .prompts import build_go_prompt_artifacts
from .rendering import render_go_board_scene
from .sampling import resolve_go_render_params
from .state import GO_NAMESPACE, SCENE_ID, GoGeneratedComponents, GoIntegerAxis, GoPlayerColorAxis, GoSceneAxes


POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def _allowed_panel_treatments(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[str, ...] | None:
    raw = params.get("panel_scene_treatments", group_default(render_defaults, "panel_scene_treatments", None))
    if isinstance(raw, str):
        return (str(raw),)
    if raw is None:
        return None
    return tuple(str(item) for item in raw)


def _stone_specs_for_trace(stone_specs: Sequence[GoStoneSpec]) -> list[dict[str, Any]]:
    return [
        {
            "stone_id": str(spec.stone_id),
            "point_id": str(spec.point_id),
            "row": int(spec.row),
            "col": int(spec.col),
            "color": str(spec.color),
            "is_marked_group": bool(spec.is_marked_group),
        }
        for spec in stone_specs
    ]


def _coord_list(coords: Sequence[Coord]) -> list[list[int]]:
    return [[int(row), int(col)] for row, col in coords]


def build_go_components(
    *,
    domain: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    scene_axes: GoSceneAxes,
    player_color_axis: GoPlayerColorAxis | None,
    board_size_axis: GoIntegerAxis,
    target_axis: GoIntegerAxis,
    board: Board,
    stone_specs: Sequence[GoStoneSpec],
    marked_group_coords: Sequence[Coord],
    liberty_coords: Sequence[Coord],
    annotation_point_ids: Sequence[str],
    prompt_query_key: str,
    stone_group_query: bool,
    query_params: Mapping[str, Any],
    execution_extra: Mapping[str, Any],
) -> GoGeneratedComponents:
    """Render one Go board and build trace components."""

    render_params = resolve_go_render_params(
        params,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
    )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{GO_NAMESPACE}.panel_scene_style",
        treatments=_allowed_panel_treatments(params, render_defaults),
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(render_defaults, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(render_defaults, "panel_scene_palette_weights", None)),
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    rendered_scene = render_go_board_scene(
        board=board,
        background=background,
        scene_variant=str(scene_axes.scene_variant),
        style_variant=str(scene_axes.style_variant),
        marked_group_coords=tuple(marked_group_coords),
        liberty_coords=tuple(liberty_coords),
        params=render_params,
        panel_style=panel_style,
    )
    annotation_ids = tuple(str(point_id) for point_id in annotation_point_ids)
    annotation_points = [
        list(rendered_scene.render_map["point_centers_px"][str(point_id)])
        for point_id in annotation_ids
    ]
    annotation_artifacts = point_set_annotation_artifacts(annotation_points)
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    player_color = str(player_color_axis.player_color if player_color_axis is not None else query_params.get("player_color", ""))
    prompt_defaults, prompt_artifacts = build_go_prompt_artifacts(
        domain=str(domain),
        scene_variant=str(scene_axes.scene_variant),
        prompt_query_key=str(prompt_query_key),
        player_color=str(player_color),
        stone_group_query=bool(stone_group_query),
        instance_seed=int(instance_seed),
    )
    base_query_params = {
        "scene_variant": str(scene_axes.scene_variant),
        "query_id": str(query_id),
        "player_color": str(player_color),
        "style_variant": str(scene_axes.style_variant),
        "board_size": int(board_size_axis.value),
        "board_size_support": [int(value) for value in board_size_axis.support],
        "board_size_probabilities": dict(board_size_axis.probabilities),
        "scene_variant_probabilities": dict(scene_axes.scene_variant_probabilities),
        "query_id_probabilities": {str(key): float(value) for key, value in dict(query_id_probabilities).items()},
        "style_variant_probabilities": dict(scene_axes.style_variant_probabilities),
        "target_answer": int(target_axis.value),
        "target_answer_support": [int(value) for value in target_axis.support],
        "target_answer_probabilities": dict(target_axis.probabilities),
    }
    if player_color_axis is not None:
        base_query_params["player_color_probabilities"] = dict(player_color_axis.probabilities)
    base_query_params.update(dict(query_params))
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params=base_query_params,
    )
    execution_trace = {
        "scene_variant": str(scene_axes.scene_variant),
        "query_id": str(query_id),
        "player_color": str(player_color),
        "style_variant": str(scene_axes.style_variant),
        "board_size": int(board_size_axis.value),
        "target_answer": int(target_axis.value),
        "target_answer_support": [int(value) for value in target_axis.support],
        "stone_specs": _stone_specs_for_trace(stone_specs),
        "marked_group_coords": _coord_list(tuple(marked_group_coords)),
        "liberty_coords": _coord_list(tuple(liberty_coords)),
        "annotation_entity_ids": [str(value) for value in annotation_ids],
        **dict(execution_extra),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": "games_go_single_board",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(scene_axes.scene_variant),
                "query_id": str(query_id),
                "player_color": str(player_color),
                "style_variant": str(scene_axes.style_variant),
                "target_answer": int(target_axis.value),
                "annotation_entity_ids": [str(value) for value in annotation_ids],
                "board_size": int(board_size_axis.value),
            },
        },
        "query_spec": dict(query_spec),
        "render_spec": {
            "scene_variant": str(scene_axes.scene_variant),
            "style_variant": str(scene_axes.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "board_size": int(board_size_axis.value),
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(panel_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": dict(execution_trace),
        "witness_symbolic": {
            "type": "object_set",
            "ids": [str(value) for value in annotation_ids],
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
        "prompt_metadata": {"bundle_id": str(prompt_defaults["bundle_id"])},
    }
    return GoGeneratedComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type="integer",
        answer_value=int(target_axis.value),
        annotation_type=str(annotation_artifacts.annotation_type),
        annotation_value=annotation_artifacts.value,
        image=image,
        trace_payload=trace_payload,
        query_id=str(query_id),
    )


__all__ = ["build_go_components"]
