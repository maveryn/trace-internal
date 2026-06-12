"""Identity-free render, prompt, and trace assembly for Hex tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.shared.annotation_artifacts import point_set_annotation_artifacts
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.font_assets import get_font_family_record
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .mechanics import EMPTY, Coord, HexSample, all_coords, color_name, coord_to_cell_id
from .prompts import HexPromptContext, build_hex_prompt_artifacts
from .rendering import render_hex_board_scene
from .sampling import resolve_hex_render_params
from .state import HEX_NAMESPACE, SCENE_ID, HexGeneratedComponents, HexIntegerAxis, HexSceneAxes, HexStringAxis


POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def _allowed_panel_treatments(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[str, ...] | None:
    raw = params.get("panel_scene_treatments", group_default(render_defaults, "panel_scene_treatments", None))
    if isinstance(raw, str):
        return (str(raw),)
    if raw is None:
        return None
    return tuple(str(item) for item in raw)


def _candidate_trace(sample: HexSample) -> list[dict[str, Any]]:
    return [
        {
            "label": str(spec.label),
            "coord": [int(spec.coord[0]), int(spec.coord[1])],
            "cell_id": coord_to_cell_id(spec.coord),
            "is_answer": bool(spec.is_answer),
        }
        for spec in sample.candidate_specs
    ]


def _axis_params(
    *,
    scene_axes: HexSceneAxes,
    target_axis: HexIntegerAxis | HexStringAxis | None,
    candidate_count_axis: HexIntegerAxis | None,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    sample: HexSample,
    reference_label: str,
    neighbor_state: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "scene_variant": str(scene_axes.scene_variant),
        "query_id": str(query_id),
        "style_variant": str(scene_axes.style_variant),
        "player_color": str(scene_axes.player_color),
        "board_size": int(sample.board_size),
        "candidate_count": int(len(sample.candidate_specs)),
        "scene_variant_probabilities": dict(scene_axes.scene_variant_probabilities),
        "query_id_probabilities": {str(key): float(value) for key, value in dict(query_id_probabilities).items()},
        "style_variant_probabilities": dict(scene_axes.style_variant_probabilities),
        "player_color_probabilities": dict(scene_axes.player_color_probabilities),
        "board_size_probabilities": dict(scene_axes.board_size_probabilities),
        "reference_label": str(reference_label),
        "neighbor_target_state": str(neighbor_state),
        "occupied_count": sum(1 for coord in all_coords(sample.board_size) if sample.board[coord[0]][coord[1]] != EMPTY),
    }
    if isinstance(target_axis, HexIntegerAxis):
        params.update(
            {
                "target_answer": int(target_axis.value),
                "target_answer_support": [int(value) for value in target_axis.support],
                "target_answer_probabilities": dict(target_axis.probabilities),
            }
        )
    elif isinstance(target_axis, HexStringAxis):
        params.update(
            {
                "target_label": str(target_axis.value),
                "target_label_support": [str(value) for value in target_axis.support],
                "target_label_probabilities": dict(target_axis.probabilities),
            }
        )
    if candidate_count_axis is not None:
        params["candidate_count_support"] = [int(value) for value in candidate_count_axis.support]
        params["candidate_count_probabilities"] = dict(candidate_count_axis.probabilities)
    return params


def build_hex_components(
    *,
    domain: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    prompt_query_key: str,
    scene_axes: HexSceneAxes,
    sample: HexSample,
    annotation_coords: Sequence[Coord],
    answer_type: str,
    answer_value: str | int,
    target_axis: HexIntegerAxis | HexStringAxis | None = None,
    candidate_count_axis: HexIntegerAxis | None = None,
    query_params: Mapping[str, Any] | None = None,
) -> HexGeneratedComponents:
    """Render one Hex scene and assemble prompt/trace components."""

    render_params = resolve_hex_render_params(
        params,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
    )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{HEX_NAMESPACE}.panel_scene_style",
        treatments=_allowed_panel_treatments(params, render_defaults),
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(render_defaults, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(render_defaults, "panel_scene_palette_weights", None)),
    )
    panel_render_meta = dict(panel_style_meta)
    panel_render_meta.pop("text_legibility", None)
    panel_render_meta.pop("text_color_policy", None)
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    rendered_scene = render_hex_board_scene(
        board=sample.board,
        background=background,
        scene_variant=str(scene_axes.scene_variant),
        style_variant=str(scene_axes.style_variant),
        player_color=str(scene_axes.player_color),
        candidate_labels_by_coord={tuple(spec.coord): str(spec.label) for spec in sample.candidate_specs},
        params=render_params,
        reference_labels_by_coord={
            tuple(sample.reference_coord): str(sample.reference_label)
        }
        if sample.reference_coord is not None and sample.reference_label
        else {},
        panel_style=panel_style,
    )
    annotation_entity_ids = [coord_to_cell_id(coord) for coord in annotation_coords]
    annotation_points = [
        list(rendered_scene.render_map["cell_centers_px"][str(entity_id)])
        for entity_id in annotation_entity_ids
    ]
    annotation_artifacts = point_set_annotation_artifacts(annotation_points)
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    query_player = color_name(sample.player_value)
    reference_label = str(sample.reference_label or "")
    neighbor_state = str(sample.neighbor_target_state or "")
    prompt_defaults_used, prompt_artifacts = build_hex_prompt_artifacts(
        domain=str(domain),
        prompt_defaults=prompt_defaults,
        context=HexPromptContext(
            scene_variant=str(scene_axes.scene_variant),
            prompt_query_key=str(prompt_query_key),
            query_player=str(query_player),
            reference_label=str(reference_label),
            neighbor_state=str(neighbor_state),
        ),
        answer_type=str(answer_type),
        instance_seed=int(instance_seed),
    )
    trace_query_params = _axis_params(
        scene_axes=scene_axes,
        target_axis=target_axis,
        candidate_count_axis=candidate_count_axis,
        query_id=str(query_id),
        query_id_probabilities=query_id_probabilities,
        sample=sample,
        reference_label=reference_label,
        neighbor_state=neighbor_state,
    )
    trace_query_params.update(dict(query_params or {}))
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params=trace_query_params,
    )
    text_style_meta = {
        "font_family": str(render_params.font_family),
        "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"games_hex_board_{str(scene_axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(scene_axes.scene_variant),
                "query_id": str(query_id),
                "style_variant": str(scene_axes.style_variant),
                "player_color": str(scene_axes.player_color),
                "board_size": int(sample.board_size),
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            },
        },
        "query_spec": dict(query_spec),
        "render_spec": {
            "scene_variant": str(scene_axes.scene_variant),
            "style_variant": str(scene_axes.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(panel_render_meta),
            "text_style": dict(text_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": {
            "scene_variant": str(scene_axes.scene_variant),
            "query_id": str(query_id),
            "style_variant": str(scene_axes.style_variant),
            "player_color": str(scene_axes.player_color),
            "player_value": int(sample.player_value),
            "board_size": int(sample.board_size),
            "board_rows": [[int(value) for value in row] for row in sample.board],
            "answer": answer_value,
            "candidate_specs": _candidate_trace(sample),
            "reference_coord": None
            if sample.reference_coord is None
            else [int(sample.reference_coord[0]), int(sample.reference_coord[1])],
            "reference_cell_id": None if sample.reference_coord is None else coord_to_cell_id(sample.reference_coord),
            "reference_label": reference_label,
            "neighbor_target_state": neighbor_state,
            "neighbor_match_coords": [[int(row), int(col)] for row, col in sample.neighbor_match_coords],
            "winning_move_coord": None if sample.winning_move_coord is None else [int(sample.winning_move_coord[0]), int(sample.winning_move_coord[1])],
            "completed_winning_path_coords": [[int(row), int(col)] for row, col in sample.annotation_coords],
            "min_gap_path": [[int(row), int(col)] for row, col in sample.min_gap_path],
            "min_gap_empty_coords": [[int(row), int(col)] for row, col in sample.min_gap_empty_coords],
            "annotation_coords": [[int(row), int(col)] for row, col in annotation_coords],
            "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            "construction_mode": str(sample.construction_mode),
        },
        "witness_symbolic": {
            "type": "object_set",
            "ids": [str(entity_id) for entity_id in annotation_entity_ids],
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
        "background": background_meta,
        "post_image_noise": post_noise_meta,
        "prompt_metadata": {"bundle_id": str(prompt_defaults_used["bundle_id"])},
    }
    return HexGeneratedComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type=str(answer_type),
        answer_value=answer_value,
        annotation_type=str(annotation_artifacts.annotation_type),
        annotation_value=annotation_artifacts.value,
        image=image,
        trace_payload=trace_payload,
        query_id=str(query_id),
    )


__all__ = ["build_hex_components"]
