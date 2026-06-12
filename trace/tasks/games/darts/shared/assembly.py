"""Identity-free render and trace assembly for darts tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.seed import spawn_rng
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.shared.annotation_artifacts import point_set_annotation_artifacts
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.font_assets import get_font_family_record
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .prompts import build_darts_prompt_artifacts
from .rendering import render_darts_scene, sample_dart_marker_color
from .state import DARTS_NAMESPACE, SCENE_ID, DartsGeneratedComponents, DartsSampledScene, DartsSceneAxes


POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def _allowed_panel_treatments(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[str, ...] | None:
    raw = params.get(
        "panel_scene_treatments",
        group_default(render_defaults, "panel_scene_treatments", None),
    )
    if isinstance(raw, str):
        return (str(raw),)
    if raw is None:
        return None
    return tuple(str(item) for item in raw)


def _dart_specs_for_trace(sampled_scene: DartsSampledScene) -> list[dict[str, Any]]:
    """Return JSON-friendly dart specs for trace payloads."""

    return [
        {
            "dart_id": str(dart.dart_id),
            "sector_value": None if dart.sector_value is None else int(dart.sector_value),
            "ring": str(dart.ring),
            "score": int(dart.score),
            "is_annotation": bool(dart.is_annotation),
        }
        for dart in sampled_scene.darts
    ]


def _score_options_for_trace(sampled_scene: DartsSampledScene) -> list[dict[str, Any]]:
    """Return JSON-friendly score options for trace payloads."""

    return [
        {
            "label": str(option.label),
            "score": int(option.score),
            "is_answer": bool(option.is_answer),
        }
        for option in sampled_scene.score_options
    ]


def build_darts_components(
    *,
    domain: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    scene_axes: DartsSceneAxes,
    sampled_scene: DartsSampledScene,
    answer_type: str,
    answer_value: int | str,
    prompt_query_key: str,
    query_params: Mapping[str, Any],
    target_ring_highlight: str | None = None,
    target_threshold: int | None = None,
) -> DartsGeneratedComponents:
    """Render one darts scene and build trace components."""

    from .sampling import resolve_darts_render_params

    render_params = resolve_darts_render_params(params, render_defaults=render_defaults, instance_seed=int(instance_seed))
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{DARTS_NAMESPACE}.panel_scene_style",
        treatments=_allowed_panel_treatments(params, render_defaults),
        treatment_weights=params.get(
            "panel_scene_treatment_weights",
            group_default(render_defaults, "panel_scene_treatment_weights", None),
        ),
        palette_weights=params.get(
            "panel_scene_palette_weights",
            group_default(render_defaults, "panel_scene_palette_weights", None),
        ),
    )
    color_rng = spawn_rng(int(instance_seed), f"{DARTS_NAMESPACE}.dart_color")
    dart_fill_color, dart_fill_min_lab_distance = sample_dart_marker_color(
        color_rng,
        style_variant=str(scene_axes.style_variant),
        min_lab_distance=40.0,
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    rendered_scene = render_darts_scene(
        darts=list(sampled_scene.darts),
        background=background,
        style_variant=str(scene_axes.style_variant),
        params=render_params,
        target_ring=target_ring_highlight,
        dart_fill_color=dart_fill_color,
        dart_fill_min_lab_distance=float(dart_fill_min_lab_distance),
        score_options=tuple(sampled_scene.score_options),
        panel_style=panel_style,
    )

    annotation_entity_ids = [str(dart_id) for dart_id in sampled_scene.annotation_dart_ids]
    annotation_points = [
        list(rendered_scene.render_map["dart_centers_px"][str(dart_id)])
        for dart_id in sampled_scene.annotation_dart_ids
    ]
    annotation_bboxes = [
        list(rendered_scene.render_map["dart_bboxes_px"][str(dart_id)])
        for dart_id in sampled_scene.annotation_dart_ids
    ]
    annotation_artifacts = point_set_annotation_artifacts(annotation_points)
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    prompt_defaults, prompt_artifacts = build_darts_prompt_artifacts(
        domain=str(domain),
        scene_variant=str(scene_axes.scene_variant),
        prompt_query_key=str(prompt_query_key),
        target_ring=target_ring_highlight,
        target_threshold=target_threshold,
        instance_seed=int(instance_seed),
    )
    text_style_meta = {
        "font_family": str(render_params.font_family),
        "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
    }

    dart_specs = _dart_specs_for_trace(sampled_scene)
    score_options = _score_options_for_trace(sampled_scene)
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
        "answer": answer_value,
        "total_score": int(sampled_scene.total_score),
        "score_options": list(score_options),
        "score_option_count": int(len(score_options)),
        "dart_fill_color": [int(v) for v in dart_fill_color],
        "dart_fill_min_lab_distance": round(float(dart_fill_min_lab_distance), 3),
        "dart_specs": list(dart_specs),
        "annotation_entity_ids": list(annotation_entity_ids),
        **dict(query_params),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"games_darts_{str(scene_axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(scene_axes.scene_variant),
                "query_id": str(query_id),
                "style_variant": str(scene_axes.style_variant),
                "answer": answer_value,
                "score_option_count": int(len(sampled_scene.score_options)),
                "annotation_entity_ids": list(annotation_entity_ids),
            },
        },
        "query_spec": dict(query_spec),
        "render_spec": {
            "scene_variant": str(scene_axes.scene_variant),
            "style_variant": str(scene_axes.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "dart_fill_color": [int(v) for v in dart_fill_color],
            "dart_fill_min_lab_distance": round(float(dart_fill_min_lab_distance), 3),
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(panel_style_meta),
            "text_style": dict(text_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": dict(execution_trace),
        "witness_symbolic": {
            "type": "object_set",
            "ids": list(annotation_entity_ids),
        },
        "projected_annotation": {
            **dict(annotation_artifacts.projected_annotation),
            "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
        },
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
        "prompt_metadata": {"bundle_id": str(prompt_defaults["bundle_id"])},
    }
    return DartsGeneratedComponents(
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


__all__ = ["build_darts_components"]
