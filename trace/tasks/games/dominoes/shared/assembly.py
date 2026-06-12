"""Identity-free render and trace assembly for dominoes tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.font_assets import get_font_family_record
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .prompts import build_domino_prompt_artifacts
from .rendering import render_domino_chain_scene
from .sampling import resolve_domino_render_params
from .state import DOMINOES_NAMESPACE, SCENE_ID, DominoGeneratedComponents, DominoSceneAxes, SampledDominoScene


POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def _allowed_panel_treatments(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[str, ...] | None:
    raw = params.get("panel_scene_treatments", group_default(render_defaults, "panel_scene_treatments", None))
    if isinstance(raw, str):
        return (str(raw),)
    if raw is None:
        return None
    return tuple(str(item) for item in raw)


def build_domino_components(
    *,
    domain: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    scene_axes: DominoSceneAxes,
    sampled_scene: SampledDominoScene,
    query_params: Mapping[str, Any],
    prompt_query_key: str,
) -> DominoGeneratedComponents:
    """Render one dominoes scene and build trace components."""

    render_params = resolve_domino_render_params(params, render_defaults=render_defaults, instance_seed=int(instance_seed))
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{DOMINOES_NAMESPACE}.panel_scene_style",
        treatments=_allowed_panel_treatments(params, render_defaults),
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(render_defaults, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(render_defaults, "panel_scene_palette_weights", None)),
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    rendered_scene = render_domino_chain_scene(
        chain_tiles=list(sampled_scene.chain_tiles),
        candidate_tiles=list(sampled_scene.candidate_tiles),
        background=background,
        scene_variant=str(scene_axes.scene_variant),
        style_variant=str(scene_axes.style_variant),
        params=render_params,
        panel_style=panel_style,
    )
    annotation_bboxes = [
        list(rendered_scene.render_map["domino_bboxes_px"][str(tile_id)])
        for tile_id in sampled_scene.annotation_tile_ids
    ]
    annotation_artifacts = bbox_set_annotation_artifacts(annotation_bboxes)
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    prompt_defaults, prompt_artifacts = build_domino_prompt_artifacts(
        domain=str(domain),
        scene_variant=str(scene_axes.scene_variant),
        prompt_query_key=str(prompt_query_key),
        target_total=sampled_scene.target_total,
        instance_seed=int(instance_seed),
    )
    text_style_meta = {
        "font_family": str(render_params.font_family),
        "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
    }
    base_query_params = {
        "scene_variant": str(scene_axes.scene_variant),
        "query_id": str(query_id),
        "style_variant": str(scene_axes.style_variant),
        "scene_variant_probabilities": dict(scene_axes.scene_variant_probabilities),
        "query_id_probabilities": {str(key): float(value) for key, value in dict(query_id_probabilities).items()},
        "style_variant_probabilities": dict(scene_axes.style_variant_probabilities),
    }
    base_query_params.update(dict(query_params))
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params=base_query_params,
    )
    execution_trace = {
        "scene_variant": str(scene_axes.scene_variant),
        "query_id": str(query_id),
        "style_variant": str(scene_axes.style_variant),
        "target_answer": sampled_scene.answer_value,
        "reference_tile_id": None if sampled_scene.reference_tile_id is None else str(sampled_scene.reference_tile_id),
        "open_end_value": None if sampled_scene.open_end_value is None else int(sampled_scene.open_end_value),
        "reference_sum": None if sampled_scene.reference_sum is None else int(sampled_scene.reference_sum),
        "target_total": None if sampled_scene.target_total is None else int(sampled_scene.target_total),
        "first_step_tile_id": None if sampled_scene.first_step_tile_id is None else str(sampled_scene.first_step_tile_id),
        "second_step_tile_id": None if sampled_scene.second_step_tile_id is None else str(sampled_scene.second_step_tile_id),
        "bridge_value": None if sampled_scene.bridge_value is None else int(sampled_scene.bridge_value),
        "chain_tile_specs": [dict(spec) for spec in sampled_scene.chain_tile_specs],
        "candidate_tile_specs": [dict(spec) for spec in sampled_scene.candidate_tile_specs],
        "annotation_entity_ids": [str(tile_id) for tile_id in sampled_scene.annotation_tile_ids],
        **dict(query_params),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"games_dominoes_chain_{str(scene_axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(scene_axes.scene_variant),
                "query_id": str(query_id),
                "style_variant": str(scene_axes.style_variant),
                "target_answer": sampled_scene.answer_value,
                "reference_tile_id": None if sampled_scene.reference_tile_id is None else str(sampled_scene.reference_tile_id),
                "annotation_entity_ids": [str(tile_id) for tile_id in sampled_scene.annotation_tile_ids],
            },
        },
        "query_spec": dict(query_spec),
        "render_spec": {
            "scene_variant": str(scene_axes.scene_variant),
            "style_variant": str(scene_axes.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(panel_style_meta),
            "text_style": dict(text_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": execution_trace,
        "witness_symbolic": {"type": "object_set", "ids": [str(tile_id) for tile_id in sampled_scene.annotation_tile_ids]},
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
        "prompt_metadata": {"bundle_id": str(prompt_defaults["bundle_id"])},
    }
    return DominoGeneratedComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type="integer",
        answer_value=int(sampled_scene.answer_value),
        annotation_type=str(annotation_artifacts.annotation_type),
        annotation_value=annotation_artifacts.value,
        image=image,
        trace_payload=trace_payload,
        query_id=str(query_id),
    )


__all__ = ["build_domino_components"]
